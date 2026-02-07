"""
Semantic Cache V2 - Hybrid Approach (Cosine Pre-filter + BGE Rerank)

Improved semantic cache that combines:
1. Fast cosine similarity pre-filtering (using stored embeddings)
2. Accurate BGE cross-encoder reranking (using singleton instance)

Performance:
- Cosine filter: O(n) but very fast (~5ms for 1000 queries)
- BGE rerank: Only top-K candidates (~180ms for 30 candidates)
- Total: ~450ms vs 9000ms for direct BGE on 1000 queries

Architecture:
```
Query → OpenAI Embedding → Cosine Filter (top 30) → BGE Rerank → Best Match
                                    ↓
                          Redis DB 3 (embeddings)
```

Configuration (via feature_flags.py):
- SEMANTIC_CACHE_COSINE_THRESHOLD: 0.25 (low to avoid missing candidates)
- SEMANTIC_CACHE_COSINE_TOP_K: 30 (max candidates for BGE)
- SEMANTIC_CACHE_BGE_THRESHOLD: 0.55 (optimized: 78.9% accuracy)

Key Features:
- Reuses BGE singleton instance (no model loading per request)
- Centralized config in feature_flags.py
- Thread-safe with proper locking
- Detailed statistics and logging

Usage:
    from src.retrieval.semantic_cache_v2 import get_semantic_cache_v2

    cache = get_semantic_cache_v2()

    # Find similar cached query
    match = cache.find_similar(query)
    if match:
        return cached_answer[match.answer_cache_key]

    # Store after caching new answer
    cache.store_embedding(query, embedding, answer_cache_key)
"""

import hashlib
import pickle
import logging
import time
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime
import threading

import redis

from src.config.feature_flags import (
    ENABLE_REDIS_CACHE,
    REDIS_HOST,
    REDIS_PORT,
    ENABLE_SEMANTIC_CACHE,
    SEMANTIC_CACHE_DB,
    MAX_SEMANTIC_SEARCH,
    SEMANTIC_CACHE_COSINE_THRESHOLD,
    SEMANTIC_CACHE_COSINE_TOP_K,
    SEMANTIC_CACHE_BGE_THRESHOLD,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class SemanticMatchV2:
    """Result of semantic similarity search with BGE score."""

    original_query: str
    cosine_similarity: float  # From pre-filter
    bge_score: float  # From BGE reranker (final decision)
    answer_cache_key: str
    cached_at: str


@dataclass
class CacheStats:
    """Statistics for semantic cache."""

    total_searches: int = 0
    semantic_hits: int = 0
    semantic_misses: int = 0
    embeddings_stored: int = 0
    avg_bge_score: float = 0.0
    avg_cosine_prefilter_time_ms: float = 0.0
    avg_bge_rerank_time_ms: float = 0.0
    avg_total_time_ms: float = 0.0


# =============================================================================
# Hybrid Semantic Cache Class
# =============================================================================


class HybridSemanticCache:
    """
    Hybrid Semantic Cache using Cosine pre-filter + BGE reranker.

    This approach provides:
    - Fast filtering via cosine similarity on embeddings
    - Accurate final matching via BGE cross-encoder
    - Scalable to thousands of cached queries

    Configuration (via feature_flags.py or env vars):
    - SEMANTIC_CACHE_COSINE_THRESHOLD: Min cosine for pre-filter (default: 0.25)
    - SEMANTIC_CACHE_COSINE_TOP_K: Max candidates for BGE (default: 30)
    - SEMANTIC_CACHE_BGE_THRESHOLD: Min BGE score for match (default: 0.55)
    """

    def __init__(
        self,
        enabled: bool = ENABLE_SEMANTIC_CACHE,
        redis_host: str = REDIS_HOST,
        redis_port: int = REDIS_PORT,
        redis_db: int = SEMANTIC_CACHE_DB,
        cosine_threshold: float = SEMANTIC_CACHE_COSINE_THRESHOLD,
        cosine_top_k: int = SEMANTIC_CACHE_COSINE_TOP_K,
        bge_threshold: float = SEMANTIC_CACHE_BGE_THRESHOLD,
        max_scan: int = MAX_SEMANTIC_SEARCH,
    ):
        """
        Initialize hybrid semantic cache.

        Args:
            enabled: Enable/disable semantic cache
            redis_host: Redis server host
            redis_port: Redis server port
            redis_db: Redis database number
            cosine_threshold: Min cosine similarity for pre-filter (default: 0.25)
            cosine_top_k: Max candidates for BGE reranking (default: 30)
            bge_threshold: Min BGE score for final match (default: 0.55)
            max_scan: Maximum cached queries to scan
        """
        self.enabled = enabled and ENABLE_REDIS_CACHE
        self.cosine_threshold = cosine_threshold
        self.cosine_top_k = cosine_top_k
        self.bge_threshold = bge_threshold
        self.max_scan = max_scan

        # Lazy load components
        self._embedder = None
        self._reranker = None

        # Redis connection
        self._redis: Optional[redis.Redis] = None
        if self.enabled:
            try:
                self._redis = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    decode_responses=False,
                    socket_connect_timeout=5,
                )
                self._redis.ping()
                logger.info(
                    f"✅ HybridSemanticCache initialized: "
                    f"Redis={redis_host}:{redis_port}/db{redis_db}, "
                    f"cosine_threshold={cosine_threshold}, "
                    f"bge_threshold={bge_threshold}"
                )
            except Exception as e:
                logger.warning(
                    f"⚠️ Redis connection failed: {e}. Semantic cache disabled."
                )
                self._redis = None
                self.enabled = False
        else:
            logger.info("ℹ️ HybridSemanticCache disabled")

        # Statistics
        self._stats = CacheStats()
        self._lock = threading.Lock()

    def _get_embedder(self):
        """Lazy load embedder from provider factory (supports OpenAI, Vertex, etc)."""
        if self._embedder is None:
            try:
                from src.config.embedding_provider import get_default_embeddings
                
                self._embedder = get_default_embeddings()
                logger.debug("✅ Embedder loaded for semantic cache from provider factory")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load embedder: {e}")
        return self._embedder

    def _get_reranker(self):
        """Get reranker based on DEFAULT_RERANKER_TYPE config using provider factory."""
        if self._reranker is None:
            try:
                from src.config.reranker_provider import get_default_reranker
                
                self._reranker = get_default_reranker()
                logger.debug(f"✅ Reranker obtained for semantic cache: {type(self._reranker).__name__}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to get reranker: {e}")
        return self._reranker

    def _compute_embedding(self, text: str) -> Optional[np.ndarray]:
        """Compute embedding for text using OpenAI."""
        embedder = self._get_embedder()
        if embedder is None:
            return None

        try:
            embedding = embedder.embed_query(text)
            return np.array(embedding, dtype=np.float32)
        except Exception as e:
            logger.warning(f"⚠️ Failed to compute embedding: {e}")
            return None

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def _generate_key(self, query: str) -> str:
        """Generate Redis key for query embedding."""
        normalized = query.lower().strip()
        query_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return f"rag:semantic:v2:{query_hash}"

    def _cosine_prefilter(
        self,
        query_embedding: np.ndarray,
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Pre-filter cached queries using cosine similarity.

        Returns:
            List of (key, cosine_score, cached_data) sorted by score descending
        """
        candidates = []
        pattern = "rag:semantic:v2:*"
        scanned = 0

        for key in self._redis.scan_iter(match=pattern, count=100):
            if scanned >= self.max_scan:
                break
            scanned += 1

            try:
                cached_bytes = self._redis.get(key)
                if not cached_bytes:
                    continue

                cached_data = pickle.loads(cached_bytes)
                cached_embedding = np.frombuffer(
                    cached_data["embedding"],
                    dtype=np.float32,
                )

                similarity = self._cosine_similarity(query_embedding, cached_embedding)

                if similarity >= self.cosine_threshold:
                    candidates.append((key, similarity, cached_data))

            except Exception as e:
                logger.debug(f"Error processing cached embedding: {e}")
                continue

        # Sort by similarity descending and take top-k
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[: self.cosine_top_k]

    def _rerank_candidates(
        self,
        query: str,
        candidates: List[Tuple[str, float, Dict[str, Any]]],
    ) -> Optional[Tuple[Dict[str, Any], float, float]]:
        """
        Rerank candidates using configured reranker (BGE or OpenAI).

        Returns:
            (cached_data, rerank_score, cosine_score) of best match, or None
        """
        if not candidates:
            return None

        reranker = self._get_reranker()
        if reranker is None:
            # Fallback to cosine-only if reranker unavailable
            logger.warning("⚠️ Reranker unavailable, using cosine-only")
            best = candidates[0]
            if best[1] >= 0.85:  # Higher threshold for cosine-only fallback
                return (best[2], best[1], best[1])
            return None

        # Prepare pairs for reranking
        pairs = [[query, data["query"]] for _, _, data in candidates]

        try:
            # Detect reranker type and call appropriate method
            if hasattr(reranker, "model") and hasattr(reranker.model, "predict"):
                # BGE path - use model.predict directly
                scores = reranker.model.predict(pairs, show_progress_bar=False)
            elif hasattr(reranker, "score_pairs"):
                # OpenAI path - use score_pairs method
                scores = reranker.score_pairs(pairs)
            else:
                logger.warning("⚠️ Reranker has no compatible scoring method")
                return None

            # Find best match above threshold
            best_idx = -1
            best_score = 0.0

            for idx, score in enumerate(scores):
                score = float(score)
                if score > best_score and score >= self.bge_threshold:
                    best_score = score
                    best_idx = idx

            if best_idx >= 0:
                cached_data = candidates[best_idx][2]
                cosine_score = candidates[best_idx][1]
                return (cached_data, best_score, cosine_score)

            return None

        except Exception as e:
            logger.warning(f"⚠️ Reranking failed: {e}")
            # Fallback to cosine-only on error
            best = candidates[0]
            if best[1] >= 0.85:
                logger.info("📊 Falling back to cosine-only match")
                return (best[2], best[1], best[1])
            return None

    def find_similar(
        self,
        query: str,
        bge_threshold: Optional[float] = None,
    ) -> Optional[SemanticMatchV2]:
        """
        Find semantically similar cached query using hybrid approach.

        Args:
            query: The query to search for
            bge_threshold: Override default BGE threshold

        Returns:
            SemanticMatchV2 if found, None otherwise
        """
        if not self.enabled or not self._redis:
            return None

        bge_threshold = bge_threshold or self.bge_threshold
        start_time = time.time()

        with self._lock:
            self._stats.total_searches += 1

        # Step 1: Compute query embedding
        query_embedding = self._compute_embedding(query)
        if query_embedding is None:
            return None

        embedding_time = time.time()

        # Step 2: Cosine pre-filter
        cosine_start = time.time()
        candidates = self._cosine_prefilter(query_embedding)
        cosine_time_ms = (time.time() - cosine_start) * 1000

        if not candidates:
            with self._lock:
                self._stats.semantic_misses += 1
            logger.debug(f"🔍 Semantic cache MISS: no cosine candidates")
            return None

        logger.debug(
            f"🔍 Cosine pre-filter: {len(candidates)} candidates "
            f"(threshold={self.cosine_threshold}, time={cosine_time_ms:.1f}ms)"
        )

        # Step 3: Rerank with configured reranker (BGE or OpenAI)
        rerank_start = time.time()
        result = self._rerank_candidates(query, candidates)
        rerank_time_ms = (time.time() - rerank_start) * 1000

        total_time_ms = (time.time() - start_time) * 1000

        # Update stats
        with self._lock:
            n = self._stats.total_searches
            self._stats.avg_cosine_prefilter_time_ms = (
                self._stats.avg_cosine_prefilter_time_ms * (n - 1) + cosine_time_ms
            ) / n
            self._stats.avg_bge_rerank_time_ms = (
                self._stats.avg_bge_rerank_time_ms * (n - 1) + rerank_time_ms
            ) / n
            self._stats.avg_total_time_ms = (
                self._stats.avg_total_time_ms * (n - 1) + total_time_ms
            ) / n

        if result is None:
            with self._lock:
                self._stats.semantic_misses += 1
            logger.debug(
                f"🔍 Semantic cache MISS: no rerank match above {bge_threshold} "
                f"(cosine={cosine_time_ms:.1f}ms, rerank={rerank_time_ms:.1f}ms)"
            )
            return None

        cached_data, rerank_score, cosine_score = result

        with self._lock:
            self._stats.semantic_hits += 1
            n = self._stats.semantic_hits
            self._stats.avg_bge_score = (
                self._stats.avg_bge_score * (n - 1) + rerank_score
            ) / n

        match = SemanticMatchV2(
            original_query=cached_data["query"],
            cosine_similarity=cosine_score,
            bge_score=rerank_score,  # Keep field name for compatibility
            answer_cache_key=cached_data.get("answer_cache_key", ""),
            cached_at=cached_data.get("cached_at", ""),
        )

        logger.info(
            f"🔍 Semantic cache HIT: rerank_score={rerank_score:.4f}, "
            f"cosine={cosine_score:.4f}, "
            f"time={total_time_ms:.1f}ms, "
            f"original='{match.original_query[:50]}...'"
        )

        return match

    def store_embedding(
        self,
        query: str,
        embedding: Optional[np.ndarray] = None,
        answer_cache_key: str = "",
    ) -> bool:
        """
        Store query embedding for future similarity searches.

        Args:
            query: The original query
            embedding: Pre-computed embedding (will compute if None)
            answer_cache_key: Key to the cached answer

        Returns:
            True if stored successfully
        """
        if not self.enabled or not self._redis:
            return False

        # Compute embedding if not provided
        if embedding is None:
            embedding = self._compute_embedding(query)
            if embedding is None:
                return False

        try:
            key = self._generate_key(query)

            data = {
                "query": query,
                "embedding": embedding.tobytes(),
                "embedding_dim": len(embedding),
                "answer_cache_key": answer_cache_key,
                "cached_at": datetime.utcnow().isoformat(),
            }

            # Store with TTL matching answer cache (24 hours)
            self._redis.setex(
                key,
                86400,  # 24 hours
                pickle.dumps(data),
            )

            with self._lock:
                self._stats.embeddings_stored += 1

            logger.debug(f"📦 Stored embedding for: {query[:50]}...")
            return True

        except Exception as e:
            logger.warning(f"⚠️ Failed to store embedding: {e}")
            return False

    def clear_all(self) -> Dict[str, int]:
        """Clear all cached embeddings."""
        count = 0
        if self._redis:
            try:
                pattern = "rag:semantic:v2:*"
                for key in self._redis.scan_iter(match=pattern):
                    self._redis.delete(key)
                    count += 1
            except Exception as e:
                logger.warning(f"⚠️ Error clearing semantic cache: {e}")

        logger.info(f"🗑️ Semantic cache V2 cleared: {count} embeddings")
        return {"cleared": count}

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._stats.total_searches
        hit_rate = self._stats.semantic_hits / total if total > 0 else 0.0

        return {
            "total_searches": self._stats.total_searches,
            "semantic_hits": self._stats.semantic_hits,
            "semantic_misses": self._stats.semantic_misses,
            "embeddings_stored": self._stats.embeddings_stored,
            "hit_rate": round(hit_rate, 4),
            "avg_bge_score": round(self._stats.avg_bge_score, 4),
            "avg_cosine_prefilter_time_ms": round(
                self._stats.avg_cosine_prefilter_time_ms, 2
            ),
            "avg_bge_rerank_time_ms": round(self._stats.avg_bge_rerank_time_ms, 2),
            "avg_total_time_ms": round(self._stats.avg_total_time_ms, 2),
            "config": {
                "cosine_threshold": self.cosine_threshold,
                "cosine_top_k": self.cosine_top_k,
                "bge_threshold": self.bge_threshold,
            },
            "enabled": self.enabled,
        }

    def get_cached_count(self) -> int:
        """Get number of cached embeddings."""
        if not self._redis:
            return 0

        count = 0
        try:
            for _ in self._redis.scan_iter(match="rag:semantic:v2:*", count=100):
                count += 1
        except Exception:
            pass
        return count


# =============================================================================
# Singleton Instance
# =============================================================================

_semantic_cache_v2_instance: Optional[HybridSemanticCache] = None
_semantic_cache_v2_lock = threading.Lock()


def get_semantic_cache_v2() -> HybridSemanticCache:
    """
    Get singleton HybridSemanticCache instance.

    Thread-safe lazy initialization.
    """
    global _semantic_cache_v2_instance

    if _semantic_cache_v2_instance is not None:
        return _semantic_cache_v2_instance

    with _semantic_cache_v2_lock:
        if _semantic_cache_v2_instance is None:
            _semantic_cache_v2_instance = HybridSemanticCache()
        return _semantic_cache_v2_instance


def reset_semantic_cache_v2():
    """Reset singleton instance (for testing only)."""
    global _semantic_cache_v2_instance
    with _semantic_cache_v2_lock:
        if _semantic_cache_v2_instance:
            _semantic_cache_v2_instance.clear_all()
        _semantic_cache_v2_instance = None
