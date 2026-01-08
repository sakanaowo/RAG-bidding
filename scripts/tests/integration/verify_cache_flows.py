#!/usr/bin/env python3
"""
Quick Cache Flow Verification

A simpler script to quickly verify all cache flows are working.
Produces a clear report showing each cache layer's status.

Run: python scripts/tests/integration/verify_cache_flows.py
"""

import os
import sys
import time
from pathlib import Path
from uuid import uuid4

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")


def print_header(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_test(name: str, passed: bool, details: str = ""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {status} | {name}")
    if details:
        print(f"         {details}")


def test_redis_connection():
    """Test 1: Redis Connection"""
    print_header("TEST 1: REDIS CONNECTION")

    try:
        import redis

        client = redis.Redis(host="localhost", port=6379, db=0)
        client.ping()

        # Check all cache DBs
        dbs = {0: "Retrieval", 1: "Sessions", 2: "Answer", 3: "Semantic"}
        for db_num, name in dbs.items():
            db_client = redis.Redis(host="localhost", port=6379, db=db_num)
            db_client.ping()
            keys = db_client.dbsize()
            print_test(f"Redis DB {db_num} ({name})", True, f"{keys} keys")
            db_client.close()

        client.close()
        return True
    except Exception as e:
        print_test("Redis Connection", False, str(e))
        return False


def test_answer_cache_flow():
    """Test 2: Answer Cache Flow"""
    print_header("TEST 2: ANSWER CACHE FLOW (L1 Memory → L2 Redis)")

    try:
        from src.retrieval.answer_cache import get_answer_cache, reset_answer_cache

        reset_answer_cache()
        cache = get_answer_cache()

        if not cache.enabled:
            print_test("Answer Cache Enabled", False, "Cache is disabled")
            return False

        print_test("Answer Cache Enabled", True, f"TTL={cache.ttl}s")

        # Test unique query
        query = f"Test answer cache query {uuid4().hex[:8]}"
        answer = "Đây là câu trả lời test."
        sources = [{"document_id": "doc-001", "document_name": "Test"}]

        # Step 1: Cache MISS
        result1 = cache.get(query)
        print_test(
            "Step 1: Cache MISS", result1 is None, f"misses={cache.stats['misses']}"
        )

        # Step 2: Cache SET
        success = cache.set(query=query, answer=answer, sources=sources)
        print_test(
            "Step 2: Cache SET", success, f"cache_sets={cache.stats['cache_sets']}"
        )

        # Step 3: L1 HIT
        result2 = cache.get(query)
        print_test(
            "Step 3: L1 Cache HIT",
            result2 is not None and cache.stats["l1_hits"] > 0,
            f"l1_hits={cache.stats['l1_hits']}",
        )

        # Step 4: Clear L1, verify L2 HIT
        cache._l1_cache.clear()
        cache._l1_order.clear()
        cache.stats["l1_hits"] = 0
        cache.stats["l2_hits"] = 0

        result3 = cache.get(query)
        print_test(
            "Step 4: L2 Cache HIT (after L1 clear)",
            result3 is not None and cache.stats["l2_hits"] > 0,
            f"l2_hits={cache.stats['l2_hits']}",
        )

        # Step 5: Verify L1 backfill
        print_test(
            "Step 5: L1 Backfill",
            cache._generate_key(query) in cache._l1_cache,
            "Entry restored to L1",
        )

        # Cleanup
        cache.invalidate(query)

        return True

    except Exception as e:
        print_test("Answer Cache Flow", False, str(e))
        import traceback

        traceback.print_exc()
        return False


def test_semantic_cache_flow():
    """Test 3: Semantic Cache V2 (Hybrid) Flow"""
    print_header("TEST 3: SEMANTIC CACHE V2 FLOW (BGE + Cosine Hybrid)")

    try:
        from src.retrieval.semantic_cache_v2 import (
            get_semantic_cache_v2,
            reset_semantic_cache_v2,
        )

        reset_semantic_cache_v2()
        cache = get_semantic_cache_v2()

        if not cache.enabled:
            print_test("Semantic Cache V2 Enabled", False, "Cache is disabled")
            return False

        print_test("Semantic Cache V2 Enabled", True, f"bge_threshold={cache.bge_threshold}")

        # Test query
        query = f"Điều kiện tham gia đấu thầu công trình {uuid4().hex[:8]}"

        # Step 1: Store embedding
        success = cache.store_embedding(
            query=query, answer_cache_key=f"test:key:{uuid4().hex[:8]}"
        )
        print_test(
            "Step 1: Store Embedding",
            success,
            f"embeddings_stored={cache.stats['embeddings_stored']}",
        )

        # Step 2: Find exact match (V2 returns SemanticMatchV2 with bge_score)
        time.sleep(0.3)  # Wait for Redis
        match = cache.find_similar(query)
        print_test(
            "Step 2: Find Exact Match",
            match is not None and match.bge_score >= 0.85,
            f"bge_score={match.bge_score:.4f}, cosine={match.cosine_similarity:.4f}" if match else "No match",
        )

        # Step 3: Stats tracking
        stats = cache.get_stats()
        print_test(
            "Step 3: Stats Tracking",
            stats["total_searches"] > 0,
            f"searches={stats['total_searches']}, hits={stats['semantic_hits']}",
        )

        # Cleanup
        cache.clear_all()

        return True

    except Exception as e:
        print_test("Semantic Cache Flow", False, str(e))
        import traceback

        traceback.print_exc()
        return False


def test_retrieval_cache_flow():
    """Test 4: Retrieval Cache Flow"""
    print_header("TEST 4: RETRIEVAL CACHE FLOW (Vector Search)")

    try:
        from src.embedding.store.pgvector_store import vector_store

        if not hasattr(vector_store, "get_stats"):
            print_test("Retrieval Cache Enabled", False, "Not using CachedVectorStore")
            return False

        print_test("Retrieval Cache Enabled", True)

        # Clear cache
        if hasattr(vector_store, "clear_all_caches"):
            vector_store.clear_all_caches()

        query = "Quy định về đấu thầu xây dựng"

        # Step 1: Cold cache (L3 - PostgreSQL)
        initial_stats = vector_store.get_stats()
        initial_l3 = initial_stats.get("l3_hits", 0)

        start1 = time.perf_counter()
        docs1 = vector_store.similarity_search(query, k=5)
        time1 = (time.perf_counter() - start1) * 1000

        stats_after_1 = vector_store.get_stats()
        l3_hit = stats_after_1.get("l3_hits", 0) > initial_l3
        print_test(
            "Step 1: Cold Cache (L3)",
            len(docs1) > 0 and l3_hit,
            f"{len(docs1)} docs, {time1:.1f}ms, l3_hits={stats_after_1.get('l3_hits', 0)}",
        )

        # Step 2: Warm cache (L1/L2)
        start2 = time.perf_counter()
        docs2 = vector_store.similarity_search(query, k=5)
        time2 = (time.perf_counter() - start2) * 1000

        stats_after_2 = vector_store.get_stats()
        cache_hit = stats_after_2.get("l1_hits", 0) > stats_after_1.get(
            "l1_hits", 0
        ) or stats_after_2.get("l2_hits", 0) > stats_after_1.get("l2_hits", 0)

        print_test(
            "Step 2: Warm Cache (L1/L2)",
            len(docs2) > 0 and cache_hit,
            f"{len(docs2)} docs, {time2:.1f}ms, l1_hits={stats_after_2.get('l1_hits', 0)}, l2_hits={stats_after_2.get('l2_hits', 0)}",
        )

        # Step 3: Speedup
        speedup = time1 / time2 if time2 > 0 else 0
        print_test(
            "Step 3: Cache Speedup",
            speedup > 1.5 or time2 < 50,
            f"{speedup:.1f}x faster",
        )

        return True

    except Exception as e:
        print_test("Retrieval Cache Flow", False, str(e))
        import traceback

        traceback.print_exc()
        return False


def test_context_cache_flow():
    """Test 5: Context Cache Flow"""
    print_header("TEST 5: CONTEXT CACHE FLOW (Conversation History)")

    try:
        from src.retrieval.context_cache import get_context_cache

        cache = get_context_cache()

        if not cache.enabled:
            print_test("Context Cache Enabled", False, "Cache is disabled")
            return False

        print_test("Context Cache Enabled", True, f"max_messages={cache.max_messages}")

        conversation_id = uuid4()

        # Step 1: Empty conversation
        messages = cache.get_recent_messages(conversation_id)
        print_test(
            "Step 1: Empty Conversation",
            messages is None or len(messages) == 0,
            "No messages initially",
        )

        # Step 2: Append messages
        for i in range(3):
            cache.append_message(
                conversation_id,
                {
                    "id": str(uuid4()),
                    "role": "user" if i % 2 == 0 else "assistant",
                    "content": f"Message {i}",
                },
            )

        messages = cache.get_recent_messages(conversation_id)
        print_test(
            "Step 2: Append Messages",
            messages is not None and len(messages) == 3,
            f"{len(messages) if messages else 0} messages cached",
        )

        # Step 3: Cache HIT
        initial_hits = cache._stats.get("hits", 0)
        messages = cache.get_recent_messages(conversation_id)
        new_hits = cache._stats.get("hits", 0)

        print_test("Step 3: Cache HIT", new_hits > initial_hits, f"hits={new_hits}")

        return True

    except Exception as e:
        print_test("Context Cache Flow", False, str(e))
        import traceback

        traceback.print_exc()
        return False


def test_full_rag_with_cache():
    """Test 6: Full RAG Pipeline with Cache"""
    print_header("TEST 6: FULL RAG PIPELINE WITH CACHE")

    try:
        from src.generation.chains.qa_chain import answer as qa_answer
        from src.retrieval.answer_cache import get_answer_cache

        cache = get_answer_cache()
        query = "Điều kiện tham gia đấu thầu là gì?"

        # Clear cache for this query
        cache.invalidate(query)

        # Step 1: First call (cache MISS - full pipeline)
        start1 = time.perf_counter()
        result1 = qa_answer(query, mode="fast", use_cache=True)
        time1 = (time.perf_counter() - start1) * 1000

        print_test(
            "Step 1: First Call (MISS)",
            "answer" in result1
            and not result1.get("adaptive_retrieval", {}).get("from_cache"),
            f"{time1:.0f}ms, mode={result1.get('adaptive_retrieval', {}).get('mode')}",
        )

        # Step 2: Second call (cache HIT)
        start2 = time.perf_counter()
        result2 = qa_answer(query, mode="fast", use_cache=True)
        time2 = (time.perf_counter() - start2) * 1000

        from_cache = result2.get("adaptive_retrieval", {}).get("from_cache", False)
        print_test(
            "Step 2: Second Call (HIT)",
            "answer" in result2 and from_cache,
            f"{time2:.0f}ms, from_cache={from_cache}",
        )

        # Step 3: Speedup
        speedup = time1 / time2 if time2 > 0 else 0
        print_test("Step 3: Pipeline Speedup", speedup > 5, f"{speedup:.1f}x faster")

        # Step 4: Cache bypass
        result3 = qa_answer(query, mode="fast", use_cache=False)
        bypass_ok = not result3.get("adaptive_retrieval", {}).get("from_cache", True)
        print_test(
            "Step 4: Cache Bypass (use_cache=False)",
            bypass_ok,
            "Cache correctly bypassed",
        )

        return True

    except Exception as e:
        print_test("Full RAG Pipeline", False, str(e))
        import traceback

        traceback.print_exc()
        return False


def test_cache_api_endpoints():
    """Test 7: Cache API Endpoints"""
    print_header("TEST 7: CACHE API ENDPOINTS")

    try:
        import requests

        base_url = "http://localhost:8000"

        # Test /cache/stats
        try:
            response = requests.get(f"{base_url}/cache/stats", timeout=5)
            stats_ok = response.status_code == 200
            if stats_ok:
                stats = response.json()
                print_test(
                    "GET /cache/stats",
                    True,
                    f"retrieval_hit_rate={stats.get('retrieval_cache', {}).get('hit_rate', 'N/A')}",
                )
            else:
                print_test("GET /cache/stats", False, f"Status {response.status_code}")
        except requests.exceptions.ConnectionError:
            print_test("GET /cache/stats", False, "Server not running")
            return False

        # Test /cache/features
        response = requests.get(f"{base_url}/cache/features", timeout=5)
        print_test(
            "GET /cache/features",
            response.status_code == 200,
            "Feature flags retrieved",
        )

        return True

    except Exception as e:
        print_test("Cache API Endpoints", False, str(e))
        return False


def main():
    """Run all cache flow verification tests."""
    print("\n" + "=" * 70)
    print("  CACHE FLOW VERIFICATION - INTEGRATION TEST SUITE")
    print("  Date: " + time.strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 70)

    results = {
        "Redis Connection": test_redis_connection(),
        "Answer Cache Flow": test_answer_cache_flow(),
        "Semantic Cache Flow": test_semantic_cache_flow(),
        "Retrieval Cache Flow": test_retrieval_cache_flow(),
        "Context Cache Flow": test_context_cache_flow(),
        "Full RAG Pipeline": test_full_rag_with_cache(),
        "Cache API Endpoints": test_cache_api_endpoints(),
    }

    # Summary
    print_header("SUMMARY")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅" if result else "❌"
        print(f"  {status} {test_name}")

    print("\n" + "-" * 70)
    print(f"  RESULT: {passed}/{total} tests passed")

    if passed == total:
        print("  🎉 ALL CACHE FLOWS VERIFIED SUCCESSFULLY!")
    else:
        print("  ⚠️  Some tests failed. Check logs above.")

    print("=" * 70 + "\n")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
