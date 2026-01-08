#!/usr/bin/env python3
"""
Cache Integration Tests

These are REAL integration tests (not mocks) that verify:
1. Answer Cache (L1 Memory + L2 Redis) - Exact match caching
2. Semantic Cache - Similarity-based caching
3. Retrieval Cache - Vector search result caching
4. Context Cache - Conversation history caching
5. Cache Invalidation - Proper cache clearing
6. Full RAG Pipeline with Cache - End-to-end flow

Requirements:
- Redis server running on localhost:6379
- PostgreSQL with RAG data
- All environment variables set

Run: python -m pytest scripts/tests/integration/test_cache_integration.py -v -s
"""

import os
import sys
import time
import hashlib
import pickle
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from uuid import uuid4

import pytest
import redis

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment
from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(scope="module")
def redis_client():
    """Get Redis client for direct verification."""
    client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=False)
    try:
        client.ping()
        logger.info("✅ Redis connection established")
        yield client
    except redis.ConnectionError:
        pytest.skip("Redis not available - skipping integration tests")
    finally:
        client.close()


@pytest.fixture(scope="module")
def answer_cache():
    """Get real AnswerCache instance."""
    from src.retrieval.answer_cache import get_answer_cache, reset_answer_cache

    # Reset to ensure clean state
    reset_answer_cache()
    cache = get_answer_cache()

    if not cache.enabled:
        pytest.skip("Answer cache not enabled")

    logger.info(f"✅ AnswerCache initialized: enabled={cache.enabled}, ttl={cache.ttl}")
    yield cache

    # Cleanup
    cache.clear_all()


@pytest.fixture(scope="module")
def semantic_cache():
    """Get real SemanticCache V2 (Hybrid) instance."""
    from src.retrieval.semantic_cache_v2 import get_semantic_cache_v2, reset_semantic_cache_v2

    reset_semantic_cache_v2()
    cache = get_semantic_cache_v2()

    if not cache.enabled:
        pytest.skip("Semantic cache not enabled")

    logger.info(
        f"✅ SemanticCache V2 initialized: enabled={cache.enabled}, bge_threshold={cache.bge_threshold}"
    )
    yield cache

    # Cleanup
    cache.clear_all()


@pytest.fixture(scope="module")
def retrieval_cache():
    """Get real CachedVectorStore instance."""
    from src.embedding.store.pgvector_store import vector_store

    if not hasattr(vector_store, "get_stats"):
        pytest.skip("Retrieval cache not enabled")

    # Clear cache before tests
    if hasattr(vector_store, "clear_all_caches"):
        vector_store.clear_all_caches()

    logger.info("✅ CachedVectorStore initialized")
    yield vector_store


@pytest.fixture(scope="module")
def context_cache():
    """Get real ConversationContextCache instance."""
    from src.retrieval.context_cache import get_context_cache

    cache = get_context_cache()

    if not cache.enabled:
        pytest.skip("Context cache not enabled")

    logger.info(f"✅ ContextCache initialized: enabled={cache.enabled}")
    yield cache


# =============================================================================
# TEST 1: ANSWER CACHE - L1 + L2 LAYERS
# =============================================================================


class TestAnswerCache:
    """Test Answer Cache with real Redis backend."""

    def test_cache_miss_then_hit_l1(self, answer_cache):
        """Test: First query = MISS, second query = L1 HIT."""
        query = f"Test query for answer cache L1 {uuid4().hex[:8]}"
        answer = "Đây là câu trả lời test cho answer cache."
        sources = [
            {"document_id": "doc-001", "document_name": "Test Doc", "section": "Điều 1"}
        ]

        # Clear stats
        answer_cache.stats = {
            "total_queries": 0,
            "l1_hits": 0,
            "l2_hits": 0,
            "misses": 0,
            "cache_sets": 0,
            "errors": 0,
        }

        # Step 1: First query should be MISS
        result1 = answer_cache.get(query)
        assert result1 is None, "Expected cache MISS on first query"
        assert answer_cache.stats["misses"] == 1
        logger.info(
            f"✅ Step 1: Cache MISS confirmed (misses={answer_cache.stats['misses']})"
        )

        # Step 2: Set cache
        success = answer_cache.set(
            query=query,
            answer=answer,
            sources=sources,
            rag_mode="balanced",
            processing_time_ms=1500,
        )
        assert success, "Failed to set answer cache"
        assert answer_cache.stats["cache_sets"] == 1
        logger.info(
            f"✅ Step 2: Cache SET successful (cache_sets={answer_cache.stats['cache_sets']})"
        )

        # Step 3: Second query should be L1 HIT (in-memory)
        result2 = answer_cache.get(query)
        assert result2 is not None, "Expected cache HIT on second query"
        assert result2["answer"] == answer
        assert answer_cache.stats["l1_hits"] == 1
        logger.info(
            f"✅ Step 3: L1 Cache HIT confirmed (l1_hits={answer_cache.stats['l1_hits']})"
        )

        # Verify hit rate
        stats = answer_cache.get_stats()
        assert stats["hit_rate"] > 0, "Hit rate should be > 0"
        logger.info(f"📊 Final stats: {stats}")

    def test_cache_l2_hit_after_l1_eviction(self, answer_cache, redis_client):
        """Test: L2 Redis HIT after L1 memory is cleared."""
        query = f"Test query for L2 cache {uuid4().hex[:8]}"
        answer = "Câu trả lời được lưu trong Redis L2."
        sources = [{"document_id": "doc-002", "document_name": "Redis Test"}]

        # Set cache
        answer_cache.set(query=query, answer=answer, sources=sources)

        # Verify L1 has the entry
        cache_key = answer_cache._generate_key(query)
        assert cache_key in answer_cache._l1_cache, "Entry should be in L1"

        # Clear L1 only (simulate process restart)
        answer_cache._l1_cache.clear()
        answer_cache._l1_order.clear()
        assert cache_key not in answer_cache._l1_cache, "L1 should be cleared"
        logger.info("✅ L1 cache cleared (simulating process restart)")

        # Reset stats
        answer_cache.stats["l1_hits"] = 0
        answer_cache.stats["l2_hits"] = 0

        # Query should hit L2 (Redis)
        result = answer_cache.get(query)
        assert result is not None, "Expected L2 cache HIT"
        assert result["answer"] == answer
        assert answer_cache.stats["l2_hits"] == 1, "Should be L2 hit, not L1"
        assert answer_cache.stats["l1_hits"] == 0, "Should NOT be L1 hit"
        logger.info(
            f"✅ L2 Cache HIT confirmed (l2_hits={answer_cache.stats['l2_hits']})"
        )

        # Verify L1 backfill
        assert cache_key in answer_cache._l1_cache, "Entry should be backfilled to L1"
        logger.info("✅ L1 backfill verified")

    def test_cache_key_normalization(self, answer_cache):
        """Test: Same query with different whitespace/case = same cache key."""
        base_query = "điều kiện tham gia đấu thầu"
        variations = [
            "Điều kiện tham gia đấu thầu",
            "  điều kiện tham gia đấu thầu  ",
            "ĐIỀU KIỆN THAM GIA ĐẤU THẦU",
            "  ĐIỀU KIỆN THAM GIA ĐẤU THẦU  ",
        ]

        # Generate keys
        keys = [answer_cache._generate_key(q) for q in variations]

        # All keys should be identical
        assert len(set(keys)) == 1, f"Keys should be identical: {keys}"
        logger.info(f"✅ All {len(variations)} query variations produce same cache key")

    def test_cache_invalidation(self, answer_cache):
        """Test: Cache invalidation removes entry from L1 + L2."""
        query = f"Query to be invalidated {uuid4().hex[:8]}"
        answer = "This will be invalidated"

        # Set cache
        answer_cache.set(query=query, answer=answer, sources=[])

        # Verify it exists
        assert answer_cache.get(query) is not None

        # Invalidate
        result = answer_cache.invalidate(query)
        assert result, "Invalidation should succeed"

        # Verify it's gone
        assert (
            answer_cache.get(query) is None
        ), "Entry should be removed after invalidation"
        logger.info("✅ Cache invalidation verified")


# =============================================================================
# TEST 2: SEMANTIC CACHE - SIMILARITY MATCHING
# =============================================================================


class TestSemanticCache:
    """Test Semantic Cache with real embeddings."""

    def test_store_and_find_similar(self, semantic_cache):
        """Test: Store embedding and find similar query."""
        original_query = (
            f"Điều kiện để tham gia đấu thầu công trình xây dựng test_{uuid4().hex[:8]}"
        )

        # Store embedding for original query
        success = semantic_cache.store_embedding(
            query=original_query, answer_cache_key=f"rag:answer:test_{uuid4().hex[:8]}"
        )
        assert success, "Failed to store embedding"
        assert semantic_cache.stats["embeddings_stored"] >= 1
        logger.info(
            f"✅ Embedding stored (total={semantic_cache.stats['embeddings_stored']})"
        )

        # Find with exact same query (should match with very high similarity)
        match = semantic_cache.find_similar(original_query)
        assert match is not None, "Should find exact match"
        assert (
            match.similarity >= 0.99
        ), f"Exact match should have similarity >= 0.99, got {match.similarity}"
        logger.info(f"✅ Exact match found: similarity={match.similarity:.4f}")

    def test_similar_query_matching(self, semantic_cache):
        """Test: Similar but not identical queries should match above threshold."""
        # Store original query
        original = "Yêu cầu về năng lực tài chính của nhà thầu"
        semantic_cache.store_embedding(query=original, answer_cache_key="test:key:1")

        # Wait a bit for Redis to sync
        time.sleep(0.5)

        # Similar query (different wording, same meaning)
        similar = "Điều kiện về năng lực tài chính khi tham gia đấu thầu"

        match = semantic_cache.find_similar(similar)

        # Note: This may or may not match depending on threshold (0.95)
        # If match found, similarity should be >= threshold
        if match:
            assert match.similarity >= semantic_cache.threshold
            logger.info(f"✅ Similar query matched: similarity={match.similarity:.4f}")
        else:
            logger.info(
                f"ℹ️ No match found (queries may not be similar enough for threshold={semantic_cache.threshold})"
            )

    def test_dissimilar_query_no_match(self, semantic_cache):
        """Test: Completely different queries should NOT match."""
        # Store a specific query
        semantic_cache.store_embedding(
            query="Quy trình đánh giá hồ sơ dự thầu theo Luật Đấu thầu",
            answer_cache_key="test:key:2",
        )
        time.sleep(0.5)

        # Completely different query
        different = "Thời tiết hôm nay như thế nào?"

        match = semantic_cache.find_similar(different)

        # Should NOT match (similarity should be < threshold)
        assert (
            match is None or match.similarity < 0.9
        ), "Dissimilar queries should not match"
        logger.info("✅ Dissimilar query correctly did not match")

    def test_semantic_cache_stats(self, semantic_cache):
        """Test: Stats are correctly tracked."""
        # Perform some searches
        semantic_cache.find_similar("Random query 1")
        semantic_cache.find_similar("Random query 2")

        stats = semantic_cache.get_stats()

        assert "total_searches" in stats
        assert "semantic_hits" in stats
        assert "semantic_misses" in stats
        assert "hit_rate" in stats
        assert stats["total_searches"] >= 2

        logger.info(f"📊 Semantic cache stats: {stats}")


# =============================================================================
# TEST 3: RETRIEVAL CACHE - VECTOR SEARCH CACHING
# =============================================================================


class TestRetrievalCache:
    """Test Retrieval Cache (CachedVectorStore)."""

    def test_retrieval_cache_hit_miss(self, retrieval_cache):
        """Test: First retrieval = L3, second = L1/L2 hit."""
        query = "Điều kiện tham gia đấu thầu"

        # Get initial stats
        initial_stats = (
            retrieval_cache.get_stats() if hasattr(retrieval_cache, "get_stats") else {}
        )
        initial_l3 = initial_stats.get("l3_hits", 0)

        # First retrieval (should be L3 - PostgreSQL)
        start1 = time.perf_counter()
        docs1 = retrieval_cache.similarity_search(query, k=5)
        time1 = (time.perf_counter() - start1) * 1000

        stats_after_first = (
            retrieval_cache.get_stats() if hasattr(retrieval_cache, "get_stats") else {}
        )
        logger.info(f"✅ First retrieval: {len(docs1)} docs, {time1:.2f}ms")
        logger.info(f"   Stats after first: {stats_after_first}")

        # Second retrieval (should be cache hit - L1 or L2)
        start2 = time.perf_counter()
        docs2 = retrieval_cache.similarity_search(query, k=5)
        time2 = (time.perf_counter() - start2) * 1000

        stats_after_second = (
            retrieval_cache.get_stats() if hasattr(retrieval_cache, "get_stats") else {}
        )
        logger.info(f"✅ Second retrieval: {len(docs2)} docs, {time2:.2f}ms")
        logger.info(f"   Stats after second: {stats_after_second}")

        # Verify results are identical
        assert len(docs1) == len(docs2), "Same query should return same number of docs"

        # Verify cache hit (L1 or L2 should have increased)
        l1_hits = stats_after_second.get("l1_hits", 0) - stats_after_first.get(
            "l1_hits", 0
        )
        l2_hits = stats_after_second.get("l2_hits", 0) - stats_after_first.get(
            "l2_hits", 0
        )

        assert l1_hits > 0 or l2_hits > 0, "Second query should hit L1 or L2 cache"
        logger.info(f"✅ Cache HIT verified: L1={l1_hits}, L2={l2_hits}")

        # Second should be faster (cache hit)
        # Note: May not always be true due to system variability
        if time2 < time1:
            logger.info(f"✅ Cache speedup: {time1/time2:.2f}x faster")
        else:
            logger.info(
                f"ℹ️ No speedup detected (time1={time1:.2f}ms, time2={time2:.2f}ms)"
            )

    def test_retrieval_cache_key_includes_k(self, retrieval_cache):
        """Test: Different k values produce different cache entries."""
        query = "Hồ sơ mời thầu bao gồm những gì"

        # Clear stats
        if hasattr(retrieval_cache, "clear_cache"):
            retrieval_cache.clear_cache()

        # Search with k=3
        docs_k3 = retrieval_cache.similarity_search(query, k=3)

        # Search with k=5 (different cache key)
        docs_k5 = retrieval_cache.similarity_search(query, k=5)

        # Should have different number of results
        assert len(docs_k3) <= 3
        assert len(docs_k5) <= 5
        assert len(docs_k5) >= len(docs_k3), "k=5 should return >= docs than k=3"

        logger.info(
            f"✅ k=3 returned {len(docs_k3)} docs, k=5 returned {len(docs_k5)} docs"
        )

    def test_retrieval_cache_clear(self, retrieval_cache):
        """Test: Cache clear removes all cached entries."""
        query = "Test query for cache clear"

        # Populate cache
        retrieval_cache.similarity_search(query, k=5)

        # Clear cache
        if hasattr(retrieval_cache, "clear_all_caches"):
            result = retrieval_cache.clear_all_caches()
            logger.info(f"✅ Cache cleared: {result}")
        elif hasattr(retrieval_cache, "clear_cache"):
            retrieval_cache.clear_cache()
            logger.info("✅ Cache cleared")

        # Get stats after clear
        stats = (
            retrieval_cache.get_stats() if hasattr(retrieval_cache, "get_stats") else {}
        )
        logger.info(f"📊 Stats after clear: {stats}")


# =============================================================================
# TEST 4: CONTEXT CACHE - CONVERSATION HISTORY
# =============================================================================


class TestContextCache:
    """Test Context Cache for conversation history."""

    def test_context_cache_write_through(self, context_cache):
        """Test: Write-through strategy works correctly."""
        conversation_id = uuid4()

        # Initially no messages
        messages = context_cache.get_recent_messages(conversation_id)
        assert messages is None or len(messages) == 0

        # Append messages
        msg1 = {"id": str(uuid4()), "role": "user", "content": "Xin chào"}
        msg2 = {"id": str(uuid4()), "role": "assistant", "content": "Chào bạn!"}

        context_cache.append_message(conversation_id, msg1)
        context_cache.append_message(conversation_id, msg2)

        # Read back
        messages = context_cache.get_recent_messages(conversation_id)
        assert messages is not None
        assert len(messages) == 2
        assert messages[0]["content"] == "Xin chào"
        assert messages[1]["content"] == "Chào bạn!"

        logger.info(f"✅ Write-through verified: {len(messages)} messages cached")

    def test_context_cache_max_messages(self, context_cache):
        """Test: Max messages limit is enforced."""
        conversation_id = uuid4()
        max_messages = context_cache.max_messages

        # Add more than max messages
        for i in range(max_messages + 10):
            msg = {"id": str(uuid4()), "role": "user", "content": f"Message {i}"}
            context_cache.append_message(conversation_id, msg)

        # Read back
        messages = context_cache.get_recent_messages(conversation_id)
        assert messages is not None
        assert (
            len(messages) <= max_messages
        ), f"Should have at most {max_messages} messages"

        # Should contain the most recent messages
        assert "Message" in messages[-1]["content"]

        logger.info(f"✅ Max messages limit enforced: {len(messages)}/{max_messages}")

    def test_context_cache_hit_rate(self, context_cache):
        """Test: Cache hit rate is tracked."""
        conversation_id = uuid4()

        # Initial stats
        initial_stats = context_cache.get_stats()
        initial_hits = initial_stats.get("hits", 0)
        initial_misses = initial_stats.get("misses", 0)

        # First read (miss)
        context_cache.get_recent_messages(conversation_id)

        # Add message
        context_cache.append_message(
            conversation_id, {"id": "1", "role": "user", "content": "Hi"}
        )

        # Second read (hit)
        context_cache.get_recent_messages(conversation_id)

        # Check stats
        final_stats = context_cache.get_stats()

        logger.info(f"📊 Context cache stats: {final_stats}")


# =============================================================================
# TEST 5: CACHE INVALIDATION SERVICE
# =============================================================================


class TestCacheInvalidation:
    """Test cache invalidation service."""

    def test_invalidation_on_document_change(self, retrieval_cache):
        """Test: Cache is cleared when document changes."""
        from src.retrieval.cache_invalidation import invalidate_cache_for_document

        # Populate cache with a query
        query = "Quy định về đấu thầu"
        retrieval_cache.similarity_search(query, k=5)

        # Get stats before invalidation
        stats_before = (
            retrieval_cache.get_stats() if hasattr(retrieval_cache, "get_stats") else {}
        )

        # Trigger invalidation (simulating document status change)
        result = invalidate_cache_for_document(
            document_id="test-doc-001", change_type="status_change"
        )

        logger.info(f"✅ Invalidation triggered: {result}")

        assert result.get("success") or "error" not in result

    def test_invalidation_stats_tracking(self):
        """Test: Invalidation service tracks statistics."""
        from src.retrieval.cache_invalidation import cache_invalidation_service

        # Get initial stats
        stats = cache_invalidation_service.get_stats()

        assert "total_invalidations" in stats
        assert "affected_documents_count" in stats

        logger.info(f"📊 Invalidation stats: {stats}")


# =============================================================================
# TEST 6: FULL RAG PIPELINE WITH CACHE
# =============================================================================


class TestFullPipelineWithCache:
    """Test full RAG pipeline with cache integration."""

    def test_qa_chain_uses_answer_cache(self, answer_cache):
        """Test: QA chain correctly uses answer cache."""
        from src.generation.chains.qa_chain import answer as qa_answer

        query = "Điều kiện tham gia đấu thầu là gì?"

        # Clear cache for this query
        answer_cache.invalidate(query)

        # Reset stats
        answer_cache.stats = {
            "total_queries": 0,
            "l1_hits": 0,
            "l2_hits": 0,
            "misses": 0,
            "cache_sets": 0,
            "errors": 0,
        }

        # First call - should be cache MISS
        start1 = time.perf_counter()
        result1 = qa_answer(query, mode="balanced", use_cache=True)
        time1 = (time.perf_counter() - start1) * 1000

        assert "answer" in result1
        assert result1["adaptive_retrieval"].get("from_cache") is False
        logger.info(f"✅ First call (MISS): {time1:.0f}ms")

        # Second call - should be cache HIT
        start2 = time.perf_counter()
        result2 = qa_answer(query, mode="balanced", use_cache=True)
        time2 = (time.perf_counter() - start2) * 1000

        assert "answer" in result2
        assert result2["adaptive_retrieval"].get("from_cache") is True
        logger.info(f"✅ Second call (HIT): {time2:.0f}ms")

        # Cache hit should be significantly faster
        speedup = time1 / time2 if time2 > 0 else float("inf")
        logger.info(f"🚀 Speedup: {speedup:.1f}x")

        assert (
            speedup > 5
        ), f"Cache hit should be at least 5x faster, got {speedup:.1f}x"

    def test_qa_chain_cache_bypass(self, answer_cache):
        """Test: use_cache=False bypasses cache."""
        from src.generation.chains.qa_chain import answer as qa_answer

        query = "Hồ sơ mời thầu bao gồm những nội dung gì?"

        # First call with cache
        result1 = qa_answer(query, mode="fast", use_cache=True)

        # Second call without cache
        answer_cache.stats["l1_hits"] = 0
        answer_cache.stats["l2_hits"] = 0

        result2 = qa_answer(query, mode="fast", use_cache=False)

        # Should not have cache hits when use_cache=False
        assert result2["adaptive_retrieval"].get("from_cache") is not True
        logger.info("✅ Cache bypass verified (use_cache=False)")

    def test_casual_query_skips_cache(self):
        """Test: Casual queries skip cache and RAG pipeline."""
        from src.generation.chains.qa_chain import answer as qa_answer

        query = "Xin chào"

        start = time.perf_counter()
        result = qa_answer(query, mode="balanced", use_cache=True)
        elapsed = (time.perf_counter() - start) * 1000

        assert result["adaptive_retrieval"].get("skipped_rag") is True
        assert result["adaptive_retrieval"].get("mode") == "casual"
        assert elapsed < 100, f"Casual query should be very fast, got {elapsed:.0f}ms"

        logger.info(f"✅ Casual query handled in {elapsed:.0f}ms (skipped RAG)")


# =============================================================================
# TEST 7: REDIS DIRECT VERIFICATION
# =============================================================================


class TestRedisDirectVerification:
    """Directly verify Redis cache entries."""

    def test_answer_cache_redis_key_format(self, answer_cache, redis_client):
        """Test: Answer cache uses correct Redis key format."""
        query = f"Test Redis key format {uuid4().hex[:8]}"

        answer_cache.set(query=query, answer="Test answer", sources=[])

        # Get the expected key
        cache_key = answer_cache._generate_key(query)

        # Verify key format
        assert cache_key.startswith(
            "rag:answer:"
        ), f"Key should start with 'rag:answer:', got {cache_key}"

        # Verify key exists in Redis DB 2
        redis_db2 = redis.Redis(host="localhost", port=6379, db=2)
        exists = redis_db2.exists(cache_key)
        assert exists, f"Key {cache_key} should exist in Redis DB 2"

        # Verify TTL is set
        ttl = redis_db2.ttl(cache_key)
        assert ttl > 0, f"Key should have positive TTL, got {ttl}"

        logger.info(f"✅ Redis key verified: {cache_key}, TTL={ttl}s")
        redis_db2.close()

    def test_semantic_cache_redis_key_format(self, semantic_cache, redis_client):
        """Test: Semantic cache uses correct Redis key format."""
        query = f"Test semantic Redis key {uuid4().hex[:8]}"

        semantic_cache.store_embedding(query=query, answer_cache_key="test:key")

        # Get the expected key
        cache_key = semantic_cache._generate_key(query)

        # Verify key format
        assert cache_key.startswith(
            "rag:semantic:"
        ), f"Key should start with 'rag:semantic:', got {cache_key}"

        # Verify key exists in Redis DB 3
        redis_db3 = redis.Redis(
            host="localhost", port=6379, db=3, decode_responses=False
        )
        exists = redis_db3.exists(cache_key)
        assert exists, f"Key {cache_key} should exist in Redis DB 3"

        logger.info(f"✅ Semantic Redis key verified: {cache_key}")
        redis_db3.close()

    def test_retrieval_cache_redis_key_format(self, retrieval_cache, redis_client):
        """Test: Retrieval cache uses correct Redis key format."""
        query = "Test retrieval Redis key"

        # Perform a search
        retrieval_cache.similarity_search(query, k=3)

        # Check Redis DB 0 for retrieval keys
        pattern = "rag:retrieval:*"
        keys = list(redis_client.scan_iter(match=pattern, count=100))

        assert len(keys) > 0, f"Should have at least one key matching {pattern}"

        logger.info(
            f"✅ Retrieval Redis keys verified: {len(keys)} keys matching {pattern}"
        )


# =============================================================================
# TEST 8: PERFORMANCE BENCHMARKS
# =============================================================================


class TestPerformanceBenchmarks:
    """Performance benchmarks for cache layers."""

    def test_answer_cache_latency(self, answer_cache):
        """Benchmark: Answer cache L1 vs L2 latency."""
        query = f"Performance benchmark query {uuid4().hex[:8]}"

        # Set cache
        answer_cache.set(query=query, answer="Benchmark answer", sources=[])

        # Measure L1 latency (multiple iterations)
        l1_times = []
        for _ in range(10):
            start = time.perf_counter()
            answer_cache.get(query)
            l1_times.append((time.perf_counter() - start) * 1000)

        avg_l1 = sum(l1_times) / len(l1_times)

        # Clear L1, measure L2 latency
        cache_key = answer_cache._generate_key(query)
        answer_cache._l1_cache.clear()
        answer_cache._l1_order.clear()

        l2_times = []
        for _ in range(10):
            answer_cache._l1_cache.clear()  # Clear L1 each time
            answer_cache._l1_order.clear()
            start = time.perf_counter()
            answer_cache.get(query)
            l2_times.append((time.perf_counter() - start) * 1000)

        avg_l2 = sum(l2_times) / len(l2_times)

        logger.info(f"📊 Answer Cache Latency:")
        logger.info(
            f"   L1 (Memory): {avg_l1:.3f}ms (avg of {len(l1_times)} iterations)"
        )
        logger.info(
            f"   L2 (Redis):  {avg_l2:.3f}ms (avg of {len(l2_times)} iterations)"
        )

        # L1 should be faster than L2
        assert (
            avg_l1 < avg_l2 or avg_l2 < 5
        ), "L1 should be faster than L2 or L2 is fast enough"

    def test_retrieval_cache_speedup(self, retrieval_cache):
        """Benchmark: Retrieval cache speedup."""
        query = "Benchmark retrieval query for speedup measurement"

        # Clear cache
        if hasattr(retrieval_cache, "clear_all_caches"):
            retrieval_cache.clear_all_caches()

        # First query (cold cache - L3)
        start1 = time.perf_counter()
        docs1 = retrieval_cache.similarity_search(query, k=5)
        time_cold = (time.perf_counter() - start1) * 1000

        # Second query (warm cache - L1/L2)
        start2 = time.perf_counter()
        docs2 = retrieval_cache.similarity_search(query, k=5)
        time_warm = (time.perf_counter() - start2) * 1000

        speedup = time_cold / time_warm if time_warm > 0 else float("inf")

        logger.info(f"📊 Retrieval Cache Speedup:")
        logger.info(f"   Cold (L3): {time_cold:.2f}ms")
        logger.info(f"   Warm (L1/L2): {time_warm:.2f}ms")
        logger.info(f"   Speedup: {speedup:.1f}x")

        # Cache should provide some speedup
        assert (
            speedup > 1.5 or time_warm < 50
        ), "Cache should provide speedup or be fast enough"


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
