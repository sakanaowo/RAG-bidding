"""
Cached Retrieval Implementation with Redis
Implements multi-layer caching for vector search optimization.
"""

import hashlib
import pickle
from typing import List, Dict, Any, Optional
import redis
from langchain_core.documents import Document
from langchain_postgres import PGVector


class CachedVectorStore:
    """
    Vector store wrapper with Redis caching.

    Caching strategy:
    - L1: In-memory cache (Python dict) - fastest, limited size
    - L2: Redis cache - fast, persistent, shared across processes
    - L3: PostgreSQL + pgvector - slowest, authoritative source
    """

    def __init__(
        self,
        vector_store: PGVector,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        ttl: int = 3600,  # 1 hour default
        enable_l1_cache: bool = True,
        l1_cache_size: int = 100,  # Max queries in memory
    ):
        """
        Initialize cached vector store.

        Args:
            vector_store: Underlying PGVector store
            redis_host: Redis server host
            redis_port: Redis server port
            redis_db: Redis database number
            ttl: Cache TTL in seconds
            enable_l1_cache: Enable in-memory L1 cache
            l1_cache_size: Max number of queries in L1 cache
        """
        self.vector_store = vector_store
        self.ttl = ttl

        # Redis connection (L2 cache)
        self.redis = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=False,  # Store binary data
        )

        # In-memory cache (L1)
        self.enable_l1_cache = enable_l1_cache
        self.l1_cache_size = l1_cache_size
        self.l1_cache: Dict[str, List[Document]] = {}
        self.l1_cache_order: List[str] = []  # LRU tracking

        # Statistics
        self.stats = {
            "total_queries": 0,
            "l1_hits": 0,
            "l2_hits": 0,
            "l3_hits": 0,
        }

    def _generate_cache_key(
        self, query: str, k: int, filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate unique cache key for query.

        Args:
            query: Search query
            k: Number of results
            filters: Metadata filters

        Returns:
            Cache key (MD5 hash)
        """
        # Normalize query
        query_normalized = query.strip().lower()

        # Create cache key components
        key_parts = [
            f"q:{query_normalized}",
            f"k:{k}",
        ]

        if filters:
            # Sort filters for consistent hashing
            filter_str = str(sorted(filters.items()))
            key_parts.append(f"f:{filter_str}")

        # Generate MD5 hash
        key_string = "|".join(key_parts)
        cache_key = hashlib.md5(key_string.encode()).hexdigest()

        return f"rag:retrieval:{cache_key}"

    def _get_from_l1_cache(self, cache_key: str) -> Optional[List[Document]]:
        """Get from L1 (memory) cache."""
        if not self.enable_l1_cache:
            return None

        if cache_key in self.l1_cache:
            # Move to end (most recently used)
            self.l1_cache_order.remove(cache_key)
            self.l1_cache_order.append(cache_key)
            return self.l1_cache[cache_key]

        return None

    def _set_to_l1_cache(self, cache_key: str, docs: List[Document]):
        """Set to L1 (memory) cache with LRU eviction."""
        if not self.enable_l1_cache:
            return

        # Evict oldest if cache full
        if len(self.l1_cache) >= self.l1_cache_size:
            oldest_key = self.l1_cache_order.pop(0)
            del self.l1_cache[oldest_key]

        self.l1_cache[cache_key] = docs
        self.l1_cache_order.append(cache_key)

    def _get_from_l2_cache(self, cache_key: str) -> Optional[List[Document]]:
        """Get from L2 (Redis) cache."""
        try:
            cached_bytes = self.redis.get(cache_key)
            if cached_bytes:
                return pickle.loads(cached_bytes)
        except Exception as e:
            print(f"⚠️  Redis get error: {e}")
            return None

        return None

    def _set_to_l2_cache(self, cache_key: str, docs: List[Document]):
        """Set to L2 (Redis) cache."""
        try:
            docs_bytes = pickle.dumps(docs)
            self.redis.setex(cache_key, self.ttl, docs_bytes)
        except Exception as e:
            print(f"⚠️  Redis set error: {e}")

    def similarity_search(
        self, query: str, k: int = 5, filter: Optional[Dict[str, Any]] = None, **kwargs
    ) -> List[Document]:
        """
        Similarity search with multi-layer caching.

        Args:
            query: Search query
            k: Number of results
            filter: Metadata filters
            **kwargs: Additional arguments for vector store

        Returns:
            List of documents
        """
        self.stats["total_queries"] += 1

        # Generate cache key
        cache_key = self._generate_cache_key(query, k, filter)

        # Try L1 cache (memory)
        docs = self._get_from_l1_cache(cache_key)
        if docs is not None:
            self.stats["l1_hits"] += 1
            return docs

        # Try L2 cache (Redis)
        docs = self._get_from_l2_cache(cache_key)
        if docs is not None:
            self.stats["l2_hits"] += 1
            # Backfill L1 cache
            self._set_to_l1_cache(cache_key, docs)
            return docs

        # L3: Query vector store (PostgreSQL)
        docs = self.vector_store.similarity_search(query, k=k, filter=filter, **kwargs)
        self.stats["l3_hits"] += 1

        # Update caches
        self._set_to_l2_cache(cache_key, docs)
        self._set_to_l1_cache(cache_key, docs)

        return docs

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with cache hit rates and counts
        """
        total = self.stats["total_queries"]
        if total == 0:
            return {**self.stats, "hit_rate": 0.0}

        cache_hits = self.stats["l1_hits"] + self.stats["l2_hits"]
        hit_rate = cache_hits / total

        return {
            **self.stats,
            "cache_hits": cache_hits,
            "hit_rate": hit_rate,
            "l1_hit_rate": self.stats["l1_hits"] / total,
            "l2_hit_rate": self.stats["l2_hits"] / total,
        }

    def clear_cache(self):
        """Clear all caches."""
        # Clear L1
        self.l1_cache.clear()
        self.l1_cache_order.clear()

        # Clear L2 (only keys with our prefix)
        try:
            pattern = "rag:retrieval:*"
            for key in self.redis.scan_iter(match=pattern):
                self.redis.delete(key)
        except Exception as e:
            print(f"⚠️  Redis clear error: {e}")

    def clear_all_caches(self):
        """
        Clear all caches globally.

        Use this when document status changes or data updates affect
        multiple queries (e.g., admin sets document to expired/active).

        This ensures users see fresh data after admin operations.
        """
        import logging

        logger = logging.getLogger(__name__)

        try:
            # Clear L1
            l1_size = len(self.l1_cache)
            self.l1_cache.clear()
            self.l1_cache_order.clear()

            # Clear L2 (Redis)
            pattern = "rag:retrieval:*"
            deleted_count = 0
            for key in self.redis.scan_iter(match=pattern):
                self.redis.delete(key)
                deleted_count += 1

            logger.info(
                f"🗑️  Cache cleared: L1={l1_size} queries, L2={deleted_count} keys"
            )
            return {"l1_cleared": l1_size, "l2_cleared": deleted_count}

        except Exception as e:
            logger.error(f"❌ Failed to clear cache: {e}", exc_info=True)
            raise

    def invalidate_query(
        self, query: str, k: int = 5, filters: Optional[Dict[str, Any]] = None
    ):
        """
        Invalidate cache for specific query.

        Args:
            query: Query to invalidate
            k: Number of results
            filters: Metadata filters
        """
        cache_key = self._generate_cache_key(query, k, filters)

        # Remove from L1
        if cache_key in self.l1_cache:
            self.l1_cache_order.remove(cache_key)
            del self.l1_cache[cache_key]

        # Remove from L2
        try:
            self.redis.delete(cache_key)
        except Exception as e:
            print(f"⚠️  Redis delete error: {e}")


def test_cached_retrieval():
    """Test cached retrieval implementation."""
    import sys
    from pathlib import Path
    from dotenv import load_dotenv
    import time

    # Add project root to path
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    load_dotenv()

    from src.config.models import settings
    from src.config.embedding_provider import get_default_embeddings

    print("=" * 80)
    print("CACHED RETRIEVAL TESTING")
    print("=" * 80)

    # Initialize vector store with provider-based embeddings
    from src.config.database import get_effective_database_url

    embeddings = get_default_embeddings()
    vector_store = PGVector(
        embeddings=embeddings,
        collection_name=settings.collection,
        connection=get_effective_database_url(),
        use_jsonb=True,
    )

    # Wrap with cache
    cached_store = CachedVectorStore(
        vector_store,
        redis_host="localhost",
        redis_port=6379,
        ttl=300,  # 5 minutes
        enable_l1_cache=True,
        l1_cache_size=50,
    )

    # Clear existing cache
    print("\n🧹 Clearing cache...")
    cached_store.clear_cache()

    # Test queries
    test_queries = [
        "Điều kiện tham gia đấu thầu là gì?",
        "Hồ sơ mời thầu bao gồm những nội dung gì?",
        "Quy trình đánh giá hồ sơ dự thầu?",
    ]

    print("\n" + "=" * 80)
    print("ROUND 1: Cold cache (all L3 hits)")
    print("=" * 80)

    for i, query in enumerate(test_queries, 1):
        start = time.perf_counter()
        docs = cached_store.similarity_search(query, k=5)
        elapsed = (time.perf_counter() - start) * 1000

        print(f"\n{i}. Query: {query}")
        print(f"   Latency: {elapsed:.2f}ms")
        print(f"   Results: {len(docs)}")

    stats = cached_store.get_stats()
    print(f"\n📊 Cache Stats: {stats}")

    print("\n" + "=" * 80)
    print("ROUND 2: Warm cache (all L1 hits)")
    print("=" * 80)

    for i, query in enumerate(test_queries, 1):
        start = time.perf_counter()
        docs = cached_store.similarity_search(query, k=5)
        elapsed = (time.perf_counter() - start) * 1000

        print(f"\n{i}. Query: {query}")
        print(f"   Latency: {elapsed:.2f}ms (L1 cache)")
        print(f"   Results: {len(docs)}")

    stats = cached_store.get_stats()
    print(f"\n📊 Cache Stats: {stats}")
    print(f"   Hit Rate: {stats['hit_rate']*100:.1f}%")
    print(f"   L1 Hits: {stats['l1_hits']} ({stats['l1_hit_rate']*100:.1f}%)")
    print(f"   L2 Hits: {stats['l2_hits']} ({stats['l2_hit_rate']*100:.1f}%)")
    print(f"   L3 Hits: {stats['l3_hits']}")

    print("\n" + "=" * 80)
    print("ROUND 3: Clear L1, test L2 cache")
    print("=" * 80)

    # Clear only L1
    cached_store.l1_cache.clear()
    cached_store.l1_cache_order.clear()

    for i, query in enumerate(test_queries, 1):
        start = time.perf_counter()
        docs = cached_store.similarity_search(query, k=5)
        elapsed = (time.perf_counter() - start) * 1000

        print(f"\n{i}. Query: {query}")
        print(f"   Latency: {elapsed:.2f}ms (L2 cache)")
        print(f"   Results: {len(docs)}")

    stats = cached_store.get_stats()
    print(f"\n📊 Final Cache Stats: {stats}")
    print(f"   Overall Hit Rate: {stats['hit_rate']*100:.1f}%")

    print("\n" + "=" * 80)
    print("✅ CACHED RETRIEVAL TEST COMPLETE!")
    print("=" * 80)


if __name__ == "__main__":
    test_cached_retrieval()
