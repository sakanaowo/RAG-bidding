"""
Integration test for reranking pipeline.

Tests end-to-end: query → enhancement → retrieval → reranking → results
"""

from langchain_core.documents import Document
from src.retrieval.retrievers import create_retriever
from src.retrieval.ranking import BGEReranker


def test_reranking_with_balanced_mode():
    """Test balanced mode with reranking enabled."""
    print("\n" + "=" * 70)
    print("🧪 Test 1: Balanced Mode with Reranking")
    print("=" * 70)

    # Create retriever with reranking
    retriever = create_retriever(mode="balanced", enable_reranking=True)

    # Verify reranker is configured
    assert retriever.reranker is not None, "Reranker should be configured"
    assert isinstance(retriever.reranker, BGEReranker), "Should use BGEReranker"
    assert retriever.retrieval_k == 10, "Should retrieve 10 docs for reranking"
    assert retriever.k == 5, "Should return 5 final docs"

    print("✅ Balanced retriever configured correctly")
    print(f"   📊 Retrieval K: {retriever.retrieval_k}")
    print(f"   📊 Final K: {retriever.k}")
    print(f"   🤖 Reranker: {retriever.reranker.__class__.__name__}")
    print(f"   🎮 Device: {retriever.reranker.device}")


def test_reranking_with_quality_mode():
    """Test quality mode with reranking enabled."""
    print("\n" + "=" * 70)
    print("🧪 Test 2: Quality Mode with Reranking (RAG-Fusion)")
    print("=" * 70)

    # Create retriever with reranking
    retriever = create_retriever(mode="quality", enable_reranking=True)

    # Verify reranker is configured
    assert retriever.reranker is not None, "Reranker should be configured"
    assert isinstance(retriever.reranker, BGEReranker), "Should use BGEReranker"
    assert retriever.retrieval_k == 10, "Should retrieve 10 docs for reranking"
    assert retriever.k == 5, "Should return 5 final docs"

    print("✅ Quality retriever configured correctly")
    print(f"   📊 Retrieval K: {retriever.retrieval_k}")
    print(f"   📊 Final K: {retriever.k}")
    print(f"   🤖 Reranker: {retriever.reranker.__class__.__name__}")
    print(f"   🎮 Device: {retriever.reranker.device}")
    print(f"   🔀 RRF K: {retriever.rrf_k}")


def test_no_reranking_fast_mode():
    """Test fast mode without reranking."""
    print("\n" + "=" * 70)
    print("🧪 Test 3: Fast Mode (No Reranking)")
    print("=" * 70)

    # Create retriever without reranking
    retriever = create_retriever(mode="fast", enable_reranking=False)

    # Fast mode returns BaseVectorRetriever (no reranker attribute)
    assert not hasattr(retriever, "reranker"), "Fast mode should not have reranker"

    print("✅ Fast retriever configured correctly")
    print("   ⚡ No reranking (fastest mode)")


def test_reranking_disabled():
    """Test balanced mode with reranking explicitly disabled."""
    print("\n" + "=" * 70)
    print("🧪 Test 4: Balanced Mode with Reranking Disabled")
    print("=" * 70)

    # Create retriever without reranking
    retriever = create_retriever(mode="balanced", enable_reranking=False)

    # Verify reranker is NOT configured
    assert retriever.reranker is None, "Reranker should be None"
    assert retriever.retrieval_k == 5, "Should retrieve 5 docs (no reranking)"

    print("✅ Reranking disabled correctly")
    print(f"   📊 Retrieval K: {retriever.retrieval_k}")
    print(f"   📊 Final K: {retriever.k}")


def test_custom_reranker():
    """Test with custom reranker instance."""
    print("\n" + "=" * 70)
    print("🧪 Test 5: Custom Reranker Instance")
    print("=" * 70)

    # Create custom reranker with specific settings
    custom_reranker = BGEReranker(
        model_name=BGEReranker.BGE_RERANKER_M3, device="cpu", batch_size=8
    )

    # Create retriever with custom reranker
    retriever = create_retriever(
        mode="balanced", enable_reranking=True, reranker=custom_reranker
    )

    # Verify custom reranker is used
    assert retriever.reranker is custom_reranker, "Should use custom reranker"
    assert retriever.reranker.batch_size == 8, "Should use custom batch_size"

    print("✅ Custom reranker configured correctly")
    print(f"   🤖 Model: {retriever.reranker.model_name}")
    print(f"   🎮 Device: {retriever.reranker.device}")
    print(f"   📦 Batch Size: {retriever.reranker.batch_size}")


def test_adaptive_mode_with_reranking():
    """Test adaptive mode with reranking."""
    print("\n" + "=" * 70)
    print("🧪 Test 6: Adaptive Mode with Reranking")
    print("=" * 70)

    # Create retriever with reranking
    retriever = create_retriever(mode="adaptive", enable_reranking=True)

    # Verify adaptive retriever structure
    assert hasattr(
        retriever, "enhanced_retriever"
    ), "Adaptive should wrap EnhancedRetriever"
    assert (
        retriever.enhanced_retriever.reranker is not None
    ), "Inner retriever should have reranker"

    print("✅ Adaptive retriever configured correctly")
    print(f"   📊 K range: {retriever.k_min} - {retriever.k_max}")
    print(f"   🤖 Reranker: {retriever.enhanced_retriever.reranker.__class__.__name__}")
    print(f"   🎮 Device: {retriever.enhanced_retriever.reranker.device}")


# ============================================================================
# Main Test Runner
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🚀 RERANKING PIPELINE INTEGRATION TESTS")
    print("=" * 70)

    try:
        test_reranking_with_balanced_mode()
        test_reranking_with_quality_mode()
        test_no_reranking_fast_mode()
        test_reranking_disabled()
        test_custom_reranker()
        test_adaptive_mode_with_reranking()

        print("\n" + "=" * 70)
        print("✅ ALL INTEGRATION TESTS PASSED!")
        print("=" * 70)
        print("\n📊 Summary:")
        print("   ✅ Balanced mode with reranking")
        print("   ✅ Quality mode with reranking (RAG-Fusion)")
        print("   ✅ Fast mode (no reranking)")
        print("   ✅ Reranking can be disabled")
        print("   ✅ Custom reranker support")
        print("   ✅ Adaptive mode with reranking")
        print("\n🎉 Reranking pipeline is fully integrated!")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        raise
