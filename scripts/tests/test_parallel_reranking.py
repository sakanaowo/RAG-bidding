"""
Test Parallel vs Sequential OpenAI Reranking Performance

So sánh:
1. Sequential reranking (original): ~300ms × N docs
2. Parallel reranking (new): ~500ms for all docs
3. Expected speedup: 10-20x

Yêu cầu: OPENAI_API_KEY environment variable
"""

import os
import sys
import time

import pytest
from langchain_core.documents import Document

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.retrieval.ranking import OpenAIReranker


def test_parallel_vs_sequential_performance():
    """
    Test chính: So sánh performance parallel vs sequential.

    Expected:
    - Sequential: ~300ms × 10 docs = 3000ms (3 giây)
    - Parallel: ~500-800ms cho 10 docs
    - Speedup: 4-6x (minimum)
    """

    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    # Prepare test documents
    docs = [
        Document(
            page_content="Luật Đấu thầu 2023 quy định về quy trình đấu thầu công khai.",
            metadata={"title": "Luật Đấu thầu 2023", "dieu": "10"},
        ),
        Document(
            page_content="Nghị định 24/2024 hướng dẫn chi tiết Luật Đấu thầu.",
            metadata={"title": "Nghị định 24/2024", "dieu": "5"},
        ),
        Document(
            page_content="Quy trình mua sắm công được quy định tại Luật Đấu thầu.",
            metadata={"title": "Luật Đấu thầu 2023", "dieu": "15"},
        ),
        Document(
            page_content="Thông tư 05/2024 quy định chi tiết về hồ sơ mời thầu.",
            metadata={"title": "Thông tư 05/2024", "dieu": "3"},
        ),
        Document(
            page_content="Điều kiện tham gia đấu thầu được quy định rõ ràng.",
            metadata={"title": "Luật Đấu thầu 2023", "dieu": "6"},
        ),
        Document(
            page_content="Hồ sơ dự thầu phải đảm bảo đầy đủ các yêu cầu.",
            metadata={"title": "Nghị định 24/2024", "dieu": "8"},
        ),
        Document(
            page_content="Đánh giá hồ sơ dự thầu theo quy trình chuẩn.",
            metadata={"title": "Thông tư 05/2024", "dieu": "12"},
        ),
        Document(
            page_content="Công bố kết quả đấu thầu trên hệ thống mạng.",
            metadata={"title": "Luật Đấu thầu 2023", "dieu": "45"},
        ),
        Document(
            page_content="Ký kết hợp đồng với nhà thầu trúng thầu.",
            metadata={"title": "Nghị định 24/2024", "dieu": "20"},
        ),
        Document(
            page_content="Giám sát thực hiện hợp đồng đấu thầu.",
            metadata={"title": "Luật Đấu thầu 2023", "dieu": "50"},
        ),
    ]

    query = "quy trình đấu thầu công khai"

    print("\n" + "=" * 70)
    print("🧪 PARALLEL vs SEQUENTIAL PERFORMANCE TEST")
    print("=" * 70)

    # Test 1: Sequential (use_parallel=False)
    print("\n📊 Test 1: Sequential Reranking")
    print("-" * 70)

    reranker_seq = OpenAIReranker(use_parallel=False)

    start_seq = time.time()
    results_seq = reranker_seq.rerank(query, docs, top_k=5)
    time_seq = (time.time() - start_seq) * 1000

    print(f"   ⏱️  Sequential time: {time_seq:.1f}ms")
    print(f"   📄 Results: {len(results_seq)} documents")
    print(f"   🏆 Top score: {results_seq[0][1]:.4f}")

    # Test 2: Parallel (use_parallel=True)
    print("\n📊 Test 2: Parallel Reranking")
    print("-" * 70)

    reranker_par = OpenAIReranker(use_parallel=True)

    start_par = time.time()
    results_par = reranker_par.rerank(query, docs, top_k=5)
    time_par = (time.time() - start_par) * 1000

    print(f"   ⏱️  Parallel time: {time_par:.1f}ms")
    print(f"   📄 Results: {len(results_par)} documents")
    print(f"   🏆 Top score: {results_par[0][1]:.4f}")

    # Compare
    print("\n" + "=" * 70)
    print("📈 PERFORMANCE COMPARISON")
    print("=" * 70)

    speedup = time_seq / time_par if time_par > 0 else 0
    time_saved = time_seq - time_par

    print(f"\n   Sequential:  {time_seq:>8.1f}ms")
    print(f"   Parallel:    {time_par:>8.1f}ms")
    print(f"   ─────────────────────────")
    print(f"   Speedup:     {speedup:>8.2f}x")
    print(f"   Time saved:  {time_saved:>8.1f}ms")

    if speedup >= 3.0:
        print(f"\n   ✅ EXCELLENT! {speedup:.1f}x speedup achieved!")
    elif speedup >= 2.0:
        print(f"\n   ✅ GOOD! {speedup:.1f}x speedup")
    elif speedup >= 1.5:
        print(f"\n   ⚠️  MODERATE! {speedup:.1f}x speedup (expected >3x)")
    else:
        print(f"\n   ❌ POOR! {speedup:.1f}x speedup (expected >3x)")

    print("\n" + "=" * 70)

    # Assertions
    assert len(results_seq) == 5, "Sequential should return 5 docs"
    assert len(results_par) == 5, "Parallel should return 5 docs"
    assert speedup >= 2.0, f"Expected at least 2x speedup, got {speedup:.2f}x"

    # Scores should be similar (might differ slightly due to API variance)
    score_diff = abs(results_seq[0][1] - results_par[0][1])
    assert score_diff < 0.3, f"Scores differ too much: {score_diff:.4f}"

    print("✅ All assertions passed!")


def test_parallel_scaling():
    """
    Test scalability: 5, 10, 15, 20 documents.

    Expected: Parallel time should stay relatively constant (~500-800ms)
    while sequential time grows linearly.
    """

    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    print("\n" + "=" * 70)
    print("📊 PARALLEL SCALING TEST")
    print("=" * 70)

    # Create 20 test documents
    all_docs = []
    for i in range(20):
        all_docs.append(
            Document(
                page_content=f"Văn bản pháp luật số {i+1} về đấu thầu và mua sắm công.",
                metadata={"doc_id": i + 1},
            )
        )

    query = "quy trình đấu thầu"

    reranker = OpenAIReranker(use_parallel=True)

    doc_counts = [5, 10, 15, 20]
    times = []

    print(f"\n{'Docs':<10} {'Time (ms)':<15} {'Time/Doc (ms)'}")
    print("-" * 70)

    for count in doc_counts:
        docs = all_docs[:count]

        start = time.time()
        results = reranker.rerank(query, docs, top_k=5)
        elapsed = (time.time() - start) * 1000
        times.append(elapsed)

        time_per_doc = elapsed / count

        print(f"{count:<10} {elapsed:<15.1f} {time_per_doc:.1f}")

    print("\n" + "=" * 70)
    print("📈 SCALING ANALYSIS")
    print("=" * 70)

    # Check that time doesn't grow linearly
    # Linear: time(20) / time(5) = 4x
    # Parallel: time(20) / time(5) should be < 2x

    scaling_factor = times[-1] / times[0]

    print(f"\n   Time for 5 docs:  {times[0]:.1f}ms")
    print(f"   Time for 20 docs: {times[-1]:.1f}ms")
    print(f"   Scaling factor:   {scaling_factor:.2f}x")
    print(f"\n   Expected linear:  4.0x (bad)")
    print(f"   Expected parallel: <2.0x (good)")

    if scaling_factor < 2.0:
        print(f"\n   ✅ EXCELLENT! Parallel scaling works! ({scaling_factor:.2f}x)")
    elif scaling_factor < 3.0:
        print(f"\n   ⚠️  MODERATE! Some parallelism ({scaling_factor:.2f}x)")
    else:
        print(f"\n   ❌ POOR! Nearly linear scaling ({scaling_factor:.2f}x)")

    print("\n" + "=" * 70)

    assert scaling_factor < 3.0, f"Scaling too linear: {scaling_factor:.2f}x"


def test_parallel_correctness():
    """
    Test correctness: Parallel và sequential phải cho kết quả tương tự.
    """

    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    docs = [
        Document(
            page_content="Luật Đấu thầu 2023 quy định về quy trình đấu thầu công khai."
        ),
        Document(page_content="Nghị định 24/2024 hướng dẫn chi tiết Luật Đấu thầu."),
        Document(page_content="Thông tư 05/2024 quy định về hồ sơ mời thầu."),
    ]

    query = "quy trình đấu thầu công khai"

    # Sequential
    reranker_seq = OpenAIReranker(use_parallel=False)
    results_seq = reranker_seq.rerank(query, docs, top_k=3)

    # Parallel
    reranker_par = OpenAIReranker(use_parallel=True)
    results_par = reranker_par.rerank(query, docs, top_k=3)

    print("\n" + "=" * 70)
    print("🔍 CORRECTNESS TEST")
    print("=" * 70)

    print("\nSequential scores:")
    for i, (doc, score) in enumerate(results_seq, 1):
        print(f"  [{i}] {score:.4f} - {doc.page_content[:50]}...")

    print("\nParallel scores:")
    for i, (doc, score) in enumerate(results_par, 1):
        print(f"  [{i}] {score:.4f} - {doc.page_content[:50]}...")

    # Scores should be similar (allow some variance due to API randomness)
    for i in range(len(results_seq)):
        score_seq = results_seq[i][1]
        score_par = results_par[i][1]
        diff = abs(score_seq - score_par)

        print(f"\nDoc {i+1} score difference: {diff:.4f}")
        assert diff < 0.5, f"Score difference too large: {diff:.4f}"

    print("\n✅ Correctness verified!")


if __name__ == "__main__":
    print("=" * 70)
    print("🧪 OpenAI Parallel Reranking Performance Tests")
    print("=" * 70)

    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not set!")
        print("   Set it with: export OPENAI_API_KEY=sk-...")
        sys.exit(1)

    print(f"✅ API key found: {os.getenv('OPENAI_API_KEY')[:20]}...")
    print()

    # Run tests
    pytest.main([__file__, "-v", "-s"])
