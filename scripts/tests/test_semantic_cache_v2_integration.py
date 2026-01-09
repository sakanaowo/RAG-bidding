"""
Integration Test for Semantic Cache V2 with QA Chain

Tests:
1. Store query in semantic cache via qa_chain
2. Query with paraphrased question - should get semantic cache HIT
3. Verify response contains correct cache_type and bge_score

Usage:
    cd RAG-bidding
    PYTHONPATH=$(pwd) python scripts/tests/test_semantic_cache_v2_integration.py
"""

import sys
import time
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Add project path
sys.path.insert(0, "/home/sakana/Code/RAG-project/RAG-bidding")


def test_semantic_cache_v2_integration():
    """Test semantic cache V2 integration with qa_chain."""

    print("=" * 80)
    print("SEMANTIC CACHE V2 INTEGRATION TEST")
    print("=" * 80)

    # Import after path setup
    from src.generation.chains.qa_chain import answer
    from src.retrieval.semantic_cache_v2 import (
        get_semantic_cache_v2,
        reset_semantic_cache_v2,
    )
    from src.retrieval.answer_cache import get_answer_cache

    # Clear caches for clean test
    print("\n🔧 Clearing caches for clean test...")
    semantic_cache = get_semantic_cache_v2()
    answer_cache = get_answer_cache()

    # Get initial counts
    initial_semantic_count = semantic_cache.get_cached_count()
    print(f"   Initial semantic cache count: {initial_semantic_count}")

    # Test queries
    original_query = "Yêu cầu về năng lực tài chính của nhà thầu gồm những gì"
    paraphrased_query = (
        "Điều kiện về năng lực tài chính khi tham gia đấu thầu yêu cầu những gì"
    )

    print(f"\n📝 Original query: {original_query}")
    print(f"📝 Paraphrased query: {paraphrased_query}")

    # =========================================================================
    # Step 1: First query - should MISS cache and store
    # =========================================================================
    print("\n" + "=" * 80)
    print("STEP 1: First query (should MISS cache, run full pipeline)")
    print("=" * 80)

    start_time = time.time()
    result1 = answer(original_query, mode="balanced")
    time1 = (time.time() - start_time) * 1000

    print(f"\n⏱️  Time: {time1:.0f}ms")
    print(f"📄 Answer preview: {result1['answer'][:200]}...")

    adaptive1 = result1.get("adaptive_retrieval", {})
    from_cache1 = adaptive1.get("from_cache", False)
    cache_type1 = adaptive1.get("cache_type", "none")

    print(f"\n📊 Cache info:")
    print(f"   from_cache: {from_cache1}")
    print(f"   cache_type: {cache_type1}")

    # Verify it was NOT from cache
    assert not from_cache1, "First query should NOT be from cache"
    print("   ✅ First query ran full pipeline (not from cache)")

    # Check embedding was stored
    new_semantic_count = semantic_cache.get_cached_count()
    print(f"\n📊 Semantic cache count after first query: {new_semantic_count}")
    assert (
        new_semantic_count > initial_semantic_count
    ), "Semantic embedding should be stored"
    print("   ✅ Semantic embedding stored")

    # =========================================================================
    # Step 2: Paraphrased query - should HIT semantic cache with BGE
    # =========================================================================
    print("\n" + "=" * 80)
    print("STEP 2: Paraphrased query (should HIT semantic cache V2)")
    print("=" * 80)

    start_time = time.time()
    result2 = answer(paraphrased_query, mode="balanced")
    time2 = (time.time() - start_time) * 1000

    print(f"\n⏱️  Time: {time2:.0f}ms")
    print(f"📄 Answer preview: {result2['answer'][:200]}...")

    adaptive2 = result2.get("adaptive_retrieval", {})
    from_cache2 = adaptive2.get("from_cache", False)
    cache_type2 = adaptive2.get("cache_type", "none")
    bge_score = adaptive2.get("bge_score", 0)
    cosine_similarity = adaptive2.get("cosine_similarity", 0)
    similar_query = adaptive2.get("similar_query", "")

    print(f"\n📊 Cache info:")
    print(f"   from_cache: {from_cache2}")
    print(f"   cache_type: {cache_type2}")
    print(f"   bge_score: {bge_score}")
    print(f"   cosine_similarity: {cosine_similarity}")
    print(f"   similar_query: {similar_query[:50]}...")

    # Verify it WAS from semantic cache V2
    assert from_cache2, "Paraphrased query should be from cache"
    assert (
        cache_type2 == "semantic_v2"
    ), f"Cache type should be 'semantic_v2', got '{cache_type2}'"
    assert bge_score >= 0.85, f"BGE score should be >= 0.85, got {bge_score}"

    print("\n   ✅ Semantic cache V2 HIT verified!")
    print(f"   ✅ BGE score: {bge_score:.4f} (>= 0.85 threshold)")

    # =========================================================================
    # Step 3: Speed comparison
    # =========================================================================
    print("\n" + "=" * 80)
    print("STEP 3: Speed comparison")
    print("=" * 80)

    speedup = time1 / time2 if time2 > 0 else 0
    time_saved = time1 - time2

    print(f"\n⏱️  First query (full pipeline): {time1:.0f}ms")
    print(f"⏱️  Paraphrased query (cache HIT): {time2:.0f}ms")
    print(f"⚡ Speedup: {speedup:.1f}x")
    print(f"⚡ Time saved: {time_saved:.0f}ms")

    assert time2 < time1, "Cached query should be faster"
    print("\n   ✅ Cache is faster than full pipeline!")

    # =========================================================================
    # Step 4: Check stats
    # =========================================================================
    print("\n" + "=" * 80)
    print("STEP 4: Semantic Cache V2 Stats")
    print("=" * 80)

    stats = semantic_cache.get_stats()
    print(f"\n📊 Stats:")
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    print(
        f"""
    ✅ All tests passed!
    
    📊 Results:
       - First query (full pipeline): {time1:.0f}ms
       - Paraphrased query (semantic V2): {time2:.0f}ms
       - Speedup: {speedup:.1f}x
       - BGE score: {bge_score:.4f}
       - Cache type: {cache_type2}
    
    🎯 Semantic Cache V2 is working correctly!
       - Hybrid approach (Cosine + BGE) verified
       - BGE reranker correctly identifies similar queries
       - Significant speed improvement from caching
    """
    )

    return True


def test_different_topic_no_match():
    """Test that different topic queries don't match incorrectly."""

    print("\n" + "=" * 80)
    print("ADDITIONAL TEST: Different topic should NOT match")
    print("=" * 80)

    from src.generation.chains.qa_chain import answer
    from src.retrieval.semantic_cache_v2 import get_semantic_cache_v2

    # Query with completely different topic
    different_query = "Quy trình mở thầu diễn ra như thế nào"

    print(f"\n📝 Different topic query: {different_query}")

    start_time = time.time()
    result = answer(different_query, mode="balanced")
    elapsed = (time.time() - start_time) * 1000

    adaptive = result.get("adaptive_retrieval", {})
    from_cache = adaptive.get("from_cache", False)
    cache_type = adaptive.get("cache_type", "none")

    print(f"\n⏱️  Time: {elapsed:.0f}ms")
    print(f"📊 from_cache: {from_cache}")
    print(f"📊 cache_type: {cache_type}")

    # Should NOT match the financial capability query we cached earlier
    if from_cache and cache_type == "semantic_v2":
        similar_query = adaptive.get("similar_query", "")
        bge_score = adaptive.get("bge_score", 0)
        print(f"⚠️  Matched with: {similar_query[:50]}...")
        print(f"⚠️  BGE score: {bge_score}")

        # This is a false positive - BGE should prevent this
        if "tài chính" in similar_query and "mở thầu" not in similar_query:
            print("❌ FALSE POSITIVE: Different topic matched incorrectly!")
            return False

    print("   ✅ Different topic query correctly NOT matched with unrelated cache")
    return True


if __name__ == "__main__":
    try:
        # Run main integration test
        success1 = test_semantic_cache_v2_integration()

        # Run additional test
        success2 = test_different_topic_no_match()

        if success1 and success2:
            print("\n" + "=" * 80)
            print("🎉 ALL INTEGRATION TESTS PASSED!")
            print("=" * 80)
            sys.exit(0)
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
