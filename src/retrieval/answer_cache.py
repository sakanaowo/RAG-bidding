"""
Answer Cache for RAG Pipeline

Caches final RAG answers (answer + sources) keyed by original query hash.
This provides the highest cache hit rate by caching at the answer level
rather than at intermediate steps (retrieval, generation).

Cache Strategy:
- Key: rag:answer:{sha256(query.lower().strip())}
- Value: Pickled dict with answer, sources, metadata
- TTL: 24 hours (configurable)
- Layers: L1 (in-memory) → L2 (Redis)

Usage:
    from src.retrieval.answer_cache import get_answer_cache

    cache = get_answer_cache()

    # Check cache
    cached = cache.get(query)
    if cached:
        return cached

    # Run pipeline...
    result = run_rag_pipeline(query)

    # Cache result
    cache.set(query, result)
"""

import hashlib
import pickle
import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
import threading

import redis

from src.config.feature_flags import (
    ENABLE_REDIS_CACHE,
    REDIS_HOST,
    REDIS_PORT,
    ENABLE_ANSWER_CACHE,
    ANSWER_CACHE_TTL,
    ANSWER_CACHE_DB,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration (imported from feature_flags)
# =============================================================================
L1_CACHE_SIZE = 100  # Max queries in memory


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class CachedAnswer:
    """Cached answer with metadata."""

    answer: str
    sources: List[Dict[str, Any]]
    rag_mode: Optional[str] = None
    processing_time_ms: Optional[int] = None
    cached_at: str = ""
    original_query: str = ""

    def __post_init__(self):
        if not self.cached_at:
            self.cached_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CachedAnswer":
        return cls(**data)


# =============================================================================
# Answer Cache Class
# =============================================================================


class AnswerCache:
    """
    Two-tier cache for RAG answers.

    L1: In-memory LRU cache (per-worker, fastest)
    L2: Redis cache (shared across workers, persistent)
    """

    def __init__(
        self,
        enabled: bool = ENABLE_ANSWER_CACHE,
        redis_host: str = REDIS_HOST,
        redis_port: int = REDIS_PORT,
        redis_db: int = ANSWER_CACHE_DB,
        ttl: int = ANSWER_CACHE_TTL,
        l1_size: int = L1_CACHE_SIZE,
    ):
        """
        Initialize answer cache.

        Args:
            enabled: Enable/disable cache
            redis_host: Redis server host
            redis_port: Redis server port
            redis_db: Redis database number
            ttl: Cache TTL in seconds
            l1_size: Max entries in L1 memory cache
        """
        self.enabled = enabled and ENABLE_REDIS_CACHE
        self.ttl = ttl
        self.l1_size = l1_size

        # L1: In-memory cache
        self._l1_cache: Dict[str, CachedAnswer] = {}
        self._l1_order: List[str] = []
        self._l1_lock = threading.Lock()

        # L2: Redis cache
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
                # Test connection
                self._redis.ping()
                logger.info(
                    f"✅ AnswerCache initialized: "
                    f"Redis={redis_host}:{redis_port}/db{redis_db}, "
                    f"TTL={ttl}s, L1_size={l1_size}"
                )
            except Exception as e:
                logger.warning(
                    f"⚠️ Redis connection failed: {e}. Answer cache disabled."
                )
                self._redis = None
                self.enabled = False
        else:
            logger.info(
                "ℹ️ AnswerCache disabled (ENABLE_ANSWER_CACHE=false or ENABLE_REDIS_CACHE=false)"
            )

        # Statistics
        self.stats = {
            "total_queries": 0,
            "l1_hits": 0,
            "l2_hits": 0,
            "misses": 0,
            "cache_sets": 0,
            "errors": 0,
        }

    def _generate_key(self, query: str) -> str:
        """
        Generate cache key from query.

        Normalizes query (lowercase, strip whitespace) and hashes.

        Args:
            query: User query

        Returns:
            Cache key: rag:answer:{sha256_hash}
        """
        normalized = query.lower().strip()
        query_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return f"rag:answer:{query_hash}"

    def get(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Get cached answer for query.

        Checks L1 (memory) first, then L2 (Redis).

        Args:
            query: User query

        Returns:
            Cached answer dict or None if not found
        """
        if not self.enabled:
            return None

        self.stats["total_queries"] += 1
        cache_key = self._generate_key(query)

        # L1: Check memory cache
        with self._l1_lock:
            if cache_key in self._l1_cache:
                self.stats["l1_hits"] += 1
                # Move to end (LRU)
                self._l1_order.remove(cache_key)
                self._l1_order.append(cache_key)
                cached = self._l1_cache[cache_key]
                logger.info(f"✅ Answer cache L1 HIT: {query[:50]}...")
                return cached.to_dict()

        # L2: Check Redis
        if self._redis:
            try:
                cached_bytes = self._redis.get(cache_key)
                if cached_bytes:
                    self.stats["l2_hits"] += 1
                    cached_data = pickle.loads(cached_bytes)
                    cached_answer = CachedAnswer.from_dict(cached_data)

                    # Backfill L1
                    self._set_l1(cache_key, cached_answer)

                    logger.info(f"✅ Answer cache L2 HIT: {query[:50]}...")
                    return cached_answer.to_dict()
            except Exception as e:
                self.stats["errors"] += 1
                logger.warning(f"⚠️ Redis get error: {e}")

        self.stats["misses"] += 1
        logger.debug(f"❌ Answer cache MISS: {query[:50]}...")
        return None

    def set(
        self,
        query: str,
        answer: str,
        sources: List[Dict[str, Any]],
        rag_mode: Optional[str] = None,
        processing_time_ms: Optional[int] = None,
    ) -> bool:
        """
        Cache answer for query.

        Stores in both L1 (memory) and L2 (Redis).

        Args:
            query: Original user query
            answer: Generated answer
            sources: Source documents
            rag_mode: RAG mode used
            processing_time_ms: Processing time

        Returns:
            True if cached successfully
        """
        if not self.enabled:
            return False

        cache_key = self._generate_key(query)

        cached_answer = CachedAnswer(
            answer=answer,
            sources=sources,
            rag_mode=rag_mode,
            processing_time_ms=processing_time_ms,
            original_query=query,
        )

        # L1: Store in memory
        self._set_l1(cache_key, cached_answer)

        # L2: Store in Redis
        if self._redis:
            try:
                cached_bytes = pickle.dumps(cached_answer.to_dict())
                self._redis.setex(cache_key, self.ttl, cached_bytes)
                self.stats["cache_sets"] += 1
                logger.info(f"📦 Answer cached: {query[:50]}... (TTL={self.ttl}s)")
                return True
            except Exception as e:
                self.stats["errors"] += 1
                logger.warning(f"⚠️ Redis set error: {e}")
                return False

        return True

    def _set_l1(self, cache_key: str, cached_answer: CachedAnswer):
        """Set entry in L1 cache with LRU eviction."""
        with self._l1_lock:
            # Evict if full
            while len(self._l1_cache) >= self.l1_size and self._l1_order:
                oldest = self._l1_order.pop(0)
                self._l1_cache.pop(oldest, None)

            # Add new entry
            if cache_key in self._l1_cache:
                self._l1_order.remove(cache_key)
            self._l1_cache[cache_key] = cached_answer
            self._l1_order.append(cache_key)

    def invalidate(self, query: str) -> bool:
        """
        Invalidate cache for specific query.

        Args:
            query: Query to invalidate

        Returns:
            True if invalidated
        """
        cache_key = self._generate_key(query)

        # Remove from L1
        with self._l1_lock:
            self._l1_cache.pop(cache_key, None)
            if cache_key in self._l1_order:
                self._l1_order.remove(cache_key)

        # Remove from L2
        if self._redis:
            try:
                self._redis.delete(cache_key)
                logger.info(f"🗑️ Answer cache invalidated: {query[:50]}...")
                return True
            except Exception as e:
                logger.warning(f"⚠️ Redis delete error: {e}")
                return False

        return True

    def clear_all(self) -> Dict[str, int]:
        """
        Clear all cached answers.

        Returns:
            Dict with counts of cleared entries
        """
        # Clear L1
        with self._l1_lock:
            l1_count = len(self._l1_cache)
            self._l1_cache.clear()
            self._l1_order.clear()

        # Clear L2
        l2_count = 0
        if self._redis:
            try:
                pattern = "rag:answer:*"
                for key in self._redis.scan_iter(match=pattern):
                    self._redis.delete(key)
                    l2_count += 1
            except Exception as e:
                logger.warning(f"⚠️ Redis clear error: {e}")

        logger.info(f"🗑️ Answer cache cleared: L1={l1_count}, L2={l2_count}")
        return {"l1_cleared": l1_count, "l2_cleared": l2_count}

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with hit rates and counts
        """
        total = self.stats["total_queries"]
        if total == 0:
            hit_rate = 0.0
        else:
            hits = self.stats["l1_hits"] + self.stats["l2_hits"]
            hit_rate = hits / total

        return {
            **self.stats,
            "hit_rate": round(hit_rate, 4),
            "l1_hit_rate": round(self.stats["l1_hits"] / max(total, 1), 4),
            "l2_hit_rate": round(self.stats["l2_hits"] / max(total, 1), 4),
            "l1_size": len(self._l1_cache),
            "enabled": self.enabled,
            "ttl": self.ttl,
        }


# =============================================================================
# Singleton Instance
# =============================================================================

_answer_cache_instance: Optional[AnswerCache] = None
_answer_cache_lock = threading.Lock()


def get_answer_cache() -> AnswerCache:
    """
    Get singleton AnswerCache instance.

    Thread-safe lazy initialization.

    Returns:
        AnswerCache instance
    """
    global _answer_cache_instance

    if _answer_cache_instance is not None:
        return _answer_cache_instance

    with _answer_cache_lock:
        if _answer_cache_instance is None:
            _answer_cache_instance = AnswerCache()
        return _answer_cache_instance


def reset_answer_cache():
    """Reset singleton instance (for testing only)."""
    global _answer_cache_instance
    with _answer_cache_lock:
        if _answer_cache_instance:
            _answer_cache_instance.clear_all()
        _answer_cache_instance = None
