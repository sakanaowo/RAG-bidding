"""
Semantic Cache for RAG Pipeline (Phase 2)

Extends answer caching with semantic similarity matching.
When an exact match is not found, searches for semantically similar queries
that have been cached and returns the cached answer if similarity > threshold.

Cache Strategy:
- Primary: Exact match via hash (from Phase 1 AnswerCache)
- Secondary: Semantic similarity via embeddings (this module)
- Similarity threshold: 0.95 (configurable)

How it works:
1. On cache MISS from exact match:
   - Compute embedding of query
   - Search Redis for similar queries (cosine similarity > threshold)
   - If found, return cached answer
2. On cache SET:
   - Store query embedding in Redis for future similarity searches

Usage:
    from src.retrieval.semantic_cache import get_semantic_cache

    cache = get_semantic_cache()

    # Check semantic similarity (after exact match fails)
    similar = cache.find_similar(query, threshold=0.95)
    if similar:
        return similar.cached_answer

    # Store embedding after caching answer
    cache.store_embedding(query, query_embedding)
"""

import hashlib
import pickle
import logging
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import threading
import os

import redis

from src.config.feature_flags import (
    ENABLE_REDIS_CACHE,
    REDIS_HOST,
    REDIS_PORT,
    ENABLE_SEMANTIC_CACHE,
    SEMANTIC_CACHE_THRESHOLD,
    SEMANTIC_CACHE_DB,
    MAX_SEMANTIC_SEARCH,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration (imported from feature_flags)
# =============================================================================

# Re-export for backward compatibility
SIMILARITY_THRESHOLD = SEMANTIC_CACHE_THRESHOLD


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class SemanticMatch:
    """Result of semantic similarity search."""

    original_query: str
    similarity: float
    answer_cache_key: str
    cached_at: str


# =============================================================================
# Semantic Cache Class
# =============================================================================


class SemanticCache:
    """
    Semantic similarity cache using query embeddings.

    Stores query embeddings and enables similarity-based cache lookup
    when exact match fails.
    """

    def __init__(
        self,
        enabled: bool = ENABLE_SEMANTIC_CACHE,
        redis_host: str = REDIS_HOST,
        redis_port: int = REDIS_PORT,
        redis_db: int = SEMANTIC_CACHE_DB,
        threshold: float = SIMILARITY_THRESHOLD,
        max_scan: int = MAX_SEMANTIC_SEARCH,
    ):
        """
        Initialize semantic cache.

        Args:
            enabled: Enable/disable semantic cache
            redis_host: Redis server host
            redis_port: Redis server port
            redis_db: Redis database number
            threshold: Minimum cosine similarity for match
            max_scan: Maximum cached queries to scan
        """
        self.enabled = enabled and ENABLE_REDIS_CACHE
        self.threshold = threshold
        self.max_scan = max_scan
        self._embedder = None  # Lazy load

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
                    f"✅ SemanticCache initialized: "
                    f"Redis={redis_host}:{redis_port}/db{redis_db}, "
                    f"threshold={threshold}"
                )
            except Exception as e:
                logger.warning(
                    f"⚠️ Redis connection failed: {e}. Semantic cache disabled."
                )
                self._redis = None
                self.enabled = False
        else:
            logger.info("ℹ️ SemanticCache disabled")

        # Statistics
        self.stats = {
            "total_searches": 0,
            "semantic_hits": 0,
            "semantic_misses": 0,
            "embeddings_stored": 0,
            "avg_similarity": 0.0,
        }
        self._lock = threading.Lock()

    def _get_embedder(self):
        """Lazy load embedder to avoid startup cost."""
        if self._embedder is None:
            try:
                from src.embedding.embedders.openai_embedder import OpenAIEmbedder

                self._embedder = OpenAIEmbedder()
                logger.info("✅ Embedder loaded for semantic cache")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load embedder: {e}")
        return self._embedder

    def _compute_embedding(self, text: str) -> Optional[np.ndarray]:
        """Compute embedding for text."""
        embedder = self._get_embedder()
        if embedder is None:
            return None

        try:
            # Use the embedder's embed_query method
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
        return f"rag:semantic:{query_hash}"

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
                self.stats["embeddings_stored"] += 1

            logger.debug(f"📦 Stored embedding for: {query[:50]}...")
            return True

        except Exception as e:
            logger.warning(f"⚠️ Failed to store embedding: {e}")
            return False

    def find_similar(
        self,
        query: str,
        threshold: Optional[float] = None,
    ) -> Optional[SemanticMatch]:
        """
        Find semantically similar cached query.

        Args:
            query: The query to search for
            threshold: Override default similarity threshold

        Returns:
            SemanticMatch if found, None otherwise
        """
        if not self.enabled or not self._redis:
            return None

        threshold = threshold or self.threshold

        with self._lock:
            self.stats["total_searches"] += 1

        # Compute embedding for input query
        query_embedding = self._compute_embedding(query)
        if query_embedding is None:
            return None

        try:
            # Scan all cached embeddings (brute force for now)
            # TODO: Use Redis Vector Search for better performance
            pattern = "rag:semantic:*"
            best_match = None
            best_similarity = 0.0

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

                    # Compute similarity
                    similarity = self._cosine_similarity(
                        query_embedding, cached_embedding
                    )

                    if similarity > best_similarity and similarity >= threshold:
                        best_similarity = similarity
                        best_match = SemanticMatch(
                            original_query=cached_data["query"],
                            similarity=similarity,
                            answer_cache_key=cached_data.get("answer_cache_key", ""),
                            cached_at=cached_data.get("cached_at", ""),
                        )

                except Exception as e:
                    logger.debug(f"Error processing cached embedding: {e}")
                    continue

            # Update stats
            with self._lock:
                if best_match:
                    self.stats["semantic_hits"] += 1
                    # Update rolling average similarity
                    n = self.stats["semantic_hits"]
                    self.stats["avg_similarity"] = (
                        self.stats["avg_similarity"] * (n - 1) + best_similarity
                    ) / n
                else:
                    self.stats["semantic_misses"] += 1

            if best_match:
                logger.info(
                    f"🔍 Semantic cache HIT: similarity={best_similarity:.4f}, "
                    f"original='{best_match.original_query[:50]}...'"
                )

            return best_match

        except Exception as e:
            logger.warning(f"⚠️ Semantic search failed: {e}")
            return None

    def clear_all(self) -> Dict[str, int]:
        """Clear all cached embeddings."""
        count = 0
        if self._redis:
            try:
                pattern = "rag:semantic:*"
                for key in self._redis.scan_iter(match=pattern):
                    self._redis.delete(key)
                    count += 1
            except Exception as e:
                logger.warning(f"⚠️ Error clearing semantic cache: {e}")

        logger.info(f"🗑️ Semantic cache cleared: {count} embeddings")
        return {"cleared": count}

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self.stats["total_searches"]
        hit_rate = self.stats["semantic_hits"] / total if total > 0 else 0.0

        return {
            **self.stats,
            "hit_rate": round(hit_rate, 4),
            "threshold": self.threshold,
            "enabled": self.enabled,
        }


# =============================================================================
# Singleton Instance
# =============================================================================

_semantic_cache_instance: Optional[SemanticCache] = None
_semantic_cache_lock = threading.Lock()


def get_semantic_cache() -> SemanticCache:
    """
    Get singleton SemanticCache instance.

    Thread-safe lazy initialization.
    """
    global _semantic_cache_instance

    if _semantic_cache_instance is not None:
        return _semantic_cache_instance

    with _semantic_cache_lock:
        if _semantic_cache_instance is None:
            _semantic_cache_instance = SemanticCache()
        return _semantic_cache_instance


def reset_semantic_cache():
    """Reset singleton instance (for testing only)."""
    global _semantic_cache_instance
    with _semantic_cache_lock:
        if _semantic_cache_instance:
            _semantic_cache_instance.clear_all()
        _semantic_cache_instance = None
