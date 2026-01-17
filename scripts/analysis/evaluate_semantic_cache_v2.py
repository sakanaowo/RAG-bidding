#!/usr/bin/env python3
"""
Comprehensive Evaluation of Semantic Cache V2 (Hybrid Cosine + BGE)

Uses all 38 test pairs from semantic_threshold_analysis.py to evaluate:
1. Accuracy: Does V2 correctly identify similar vs different queries?
2. Precision: How many "matches" are actually similar queries?
3. Recall: How many similar queries are correctly matched?
4. Speed: What's the average latency?

Usage:
    PYTHONPATH=/home/sakana/Code/RAG-project/RAG-bidding python scripts/analysis/evaluate_semantic_cache_v2.py
"""

import sys
import time
from dataclasses import dataclass
from typing import List, Tuple, Optional

sys.path.insert(0, "/home/sakana/Code/RAG-project/RAG-bidding")

from src.retrieval.semantic_cache_v2 import (
    get_semantic_cache_v2,
    reset_semantic_cache_v2,
)


# =============================================================================
# Test Data (38 pairs from semantic_threshold_analysis.py)
# =============================================================================


@dataclass
class TestPair:
    q1: str
    q2: str
    category: str  # "similar", "different", "identical"

    @property
    def should_match(self) -> bool:
        return self.category in ("similar", "identical")


TEST_PAIRS: List[TestPair] = [
    # === SIMILAR PAIRS (should match) ===
    TestPair(
        "Yêu cầu về năng lực tài chính của nhà thầu gồm những gì",
        "Điều kiện về năng lực tài chính khi tham gia đấu thầu yêu cầu gì",
        "similar",
    ),
    TestPair(
        "Hồ sơ mời thầu bao gồm những nội dung gì",
        "Thành phần của hồ sơ mời thầu gồm những gì",
        "similar",
    ),
    TestPair(
        "Thời gian nộp hồ sơ dự thầu là bao lâu",
        "Nhà thầu có bao nhiêu ngày để nộp hồ sơ",
        "similar",
    ),
    TestPair(
        "Quy định về bảo lãnh dự thầu như thế nào",
        "Yêu cầu bảo đảm dự thầu theo quy định là gì",
        "similar",
    ),
    TestPair(
        "Tiêu chí đánh giá hồ sơ dự thầu gồm những gì",
        "Các tiêu chuẩn để chấm điểm hồ sơ thầu",
        "similar",
    ),
    TestPair(
        "Yêu cầu về năng lực kinh nghiệm của nhà thầu",
        "Nhà thầu cần có kinh nghiệm gì để tham gia đấu thầu",
        "similar",
    ),
    TestPair(
        "Các loại hợp đồng trong đấu thầu",
        "Phân loại hợp đồng đấu thầu theo quy định",
        "similar",
    ),
    TestPair(
        "Cách tính giá dự thầu như thế nào",
        "Phương pháp xác định giá trong hồ sơ dự thầu",
        "similar",
    ),
    TestPair(
        "Quy trình mở thầu diễn ra như thế nào",
        "Các bước trong buổi mở hồ sơ dự thầu",
        "similar",
    ),
    TestPair(
        "Quy định về sử dụng nhà thầu phụ",
        "Nhà thầu phụ được sử dụng trong trường hợp nào",
        "similar",
    ),
    TestPair(
        "Quy trình khiếu nại kết quả đấu thầu",
        "Cách thức giải quyết tranh chấp trong đấu thầu",
        "similar",
    ),
    TestPair(
        "Trường hợp nào phải hủy thầu", "Điều kiện hủy bỏ cuộc đấu thầu", "similar"
    ),
    TestPair(
        "Điều kiện tham gia đấu thầu", "Yêu cầu để được tham dự đấu thầu", "similar"
    ),
    TestPair(
        "Nhà thầu cần đáp ứng điều kiện gì",
        "Yêu cầu đối với nhà thầu khi tham gia",
        "similar",
    ),
    TestPair(
        "Bảo lãnh thực hiện hợp đồng là bao nhiêu phần trăm",
        "Tỷ lệ bảo đảm thực hiện hợp đồng theo quy định",
        "similar",
    ),
    TestPair(
        "Có bao nhiêu hình thức lựa chọn nhà thầu theo luật mới",
        "Các phương thức tuyển chọn nhà thầu hiện nay bao gồm những gì",
        "similar",
    ),
    TestPair(
        "Trường hợp nào được phép áp dụng chỉ định thầu",
        "Điều kiện để thực hiện chỉ định thầu trực tiếp là gì",
        "similar",
    ),
    TestPair(
        "Quy trình thực hiện đấu thầu qua mạng như thế nào",
        "Các bước đấu thầu trên Hệ thống mạng đấu thầu quốc gia",
        "similar",
    ),
    TestPair(
        "Đối tượng nào được hưởng ưu đãi trong lựa chọn nhà thầu",
        "Quy định về việc ưu tiên cho hàng hóa sản xuất trong nước",
        "similar",
    ),
    TestPair(
        "Tiêu chuẩn đối với thành viên tổ chuyên gia đấu thầu",
        "Quy định về năng lực và chứng chỉ của người chấm thầu",
        "similar",
    ),
    TestPair(
        "Khi nào được phép điều chỉnh giá hợp đồng đấu thầu",
        "Quy định về việc thay đổi đơn giá trong hợp đồng",
        "similar",
    ),
    TestPair(
        "Quy trình chào hàng cạnh tranh rút gọn thực hiện như thế nào",
        "Các bước làm chào hàng cạnh tranh cho gói mua sắm hàng hóa",
        "similar",
    ),
    TestPair(
        "Những hành vi nào bị nghiêm cấm trong đấu thầu",
        "Các lỗi vi phạm dẫn đến bị cấm tham gia hoạt động đấu thầu",
        "similar",
    ),
    TestPair(
        "Hiệu lực của hồ sơ dự thầu được quy định là bao nhiêu ngày",
        "Thời gian bảo đảm giá trị của hồ sơ thầu tính từ thời điểm nào",
        "similar",
    ),
    TestPair(
        "Quy trình giải quyết kiến nghị trong đấu thầu",
        "Các bước khi nhà thầu muốn khiếu nại về kết quả lựa chọn nhà thầu",
        "similar",
    ),
    TestPair(
        "Tư cách hợp lệ của nhà thầu",
        "Điều kiện để doanh nghiệp không bị loại khi xét duyệt pháp lý",
        "similar",
    ),
    TestPair(
        "Hướng dẫn nộp E-HSDT trên hệ thống",
        "Cách thức gửi hồ sơ dự thầu qua mạng",
        "similar",
    ),
    TestPair(
        "Chứng minh năng lực tài chính",
        "Cung cấp báo cáo tài chính kiểm toán trong 3 năm gần nhất",
        "similar",
    ),
    TestPair(
        "Ai là người có thẩm quyền quyết định hủy thầu",
        "Việc hủy thầu do cấp nào có thẩm quyền phê duyệt",
        "similar",
    ),
    # === IDENTICAL PAIR (baseline) ===
    TestPair(
        "Yêu cầu về năng lực tài chính của nhà thầu gồm những gì",
        "Yêu cầu về năng lực tài chính của nhà thầu gồm những gì",
        "identical",
    ),
    # === DIFFERENT TOPIC PAIRS (should NOT match) ===
    TestPair(
        "Yêu cầu về năng lực tài chính của nhà thầu",
        "Quy trình mở thầu diễn ra như thế nào",
        "different",
    ),
    TestPair(
        "Điều kiện tham gia đấu thầu", "Quy định về bảo hành công trình", "different"
    ),
    TestPair(
        "Quy định về bảo đảm dự thầu",
        "Quy định về bảo đảm thực hiện hợp đồng",
        "different",
    ),
    TestPair(
        "Nội dung chính của hồ sơ mời thầu (HSMT)",
        "Nội dung chính của hồ sơ dự thầu (HSDT)",
        "different",
    ),
    TestPair(
        "Các trường hợp được phép chỉ định thầu",
        "Các trường hợp không được phép chỉ định thầu",
        "different",
    ),
    TestPair(
        "Thời gian có hiệu lực là 90 ngày",
        "Thời gian có hiệu lực là 120 ngày",
        "different",
    ),
    TestPair(
        "Trách nhiệm của nhà thầu chính trong gói thầu",
        "Quy định về phần việc của nhà thầu phụ",
        "different",
    ),
    TestPair("Phương pháp giá thấp nhất", "Phương pháp giá đánh giá", "different"),
]


# =============================================================================
# Evaluation Functions
# =============================================================================


@dataclass
class EvalResult:
    pair: TestPair
    matched: bool
    bge_score: Optional[float]
    cosine_score: Optional[float]
    latency_ms: float
    correct: bool  # True if prediction matches expected


def evaluate_pair(cache, pair: TestPair) -> EvalResult:
    """Evaluate a single test pair."""
    # Store q1 first
    cache.store_embedding(query=pair.q1, answer_cache_key=f"eval:{hash(pair.q1)}")

    # Small delay for Redis
    time.sleep(0.05)

    # Search with q2
    start = time.time()
    match = cache.find_similar(pair.q2)
    latency_ms = (time.time() - start) * 1000

    matched = match is not None
    bge_score = match.bge_score if match else None
    cosine_score = match.cosine_similarity if match else None

    # Determine if prediction is correct
    if pair.should_match:
        correct = matched  # Should match -> matched = correct
    else:
        correct = not matched  # Should NOT match -> not matched = correct

    return EvalResult(
        pair=pair,
        matched=matched,
        bge_score=bge_score,
        cosine_score=cosine_score,
        latency_ms=latency_ms,
        correct=correct,
    )


def run_evaluation(bge_threshold: float = 0.85, verbose: bool = True):
    """Run full evaluation on all test pairs."""
    if verbose:
        print("=" * 80)
        print("SEMANTIC CACHE V2 COMPREHENSIVE EVALUATION")
        print("=" * 80)
        print()

    # Initialize cache
    reset_semantic_cache_v2()
    cache = get_semantic_cache_v2()

    # Override BGE threshold for testing
    cache.bge_threshold = bge_threshold

    if not cache.enabled:
        print("❌ Semantic cache is disabled!")
        return None

    if verbose:
        print(f"Cache Config:")
        print(f"  - Cosine pre-filter threshold: {cache.cosine_threshold}")
        print(f"  - Cosine top-k: {cache.cosine_top_k}")
        print(f"  - BGE rerank threshold: {cache.bge_threshold}")
        print()

    # Clear cache before evaluation
    cache.clear_all()

    # Run evaluation
    results: List[EvalResult] = []

    if verbose:
        print("Running evaluation on 38 test pairs...")
        print("-" * 80)

    for i, pair in enumerate(TEST_PAIRS, 1):
        # Clear cache between pairs to ensure isolation
        cache.clear_all()

        result = evaluate_pair(cache, pair)
        results.append(result)

        if verbose:
            # Print result
            status = "✅" if result.correct else "❌"
            match_str = (
                f"MATCH (bge={result.bge_score:.4f})" if result.matched else "NO MATCH"
            )
            expected = "should match" if pair.should_match else "should NOT match"

            print(
                f"Pair {i:2d} [{pair.category.upper():9s}] {status} {match_str:30s} ({expected})"
            )
            if not result.correct:
                print(f"         Q1: {pair.q1[:60]}...")
                print(f"         Q2: {pair.q2[:60]}...")

    # Calculate metrics
    if verbose:
        print()
        print("=" * 80)
        print("EVALUATION RESULTS")
        print("=" * 80)

    # Overall accuracy
    correct_count = sum(1 for r in results if r.correct)
    total_count = len(results)
    accuracy = correct_count / total_count * 100

    if verbose:
        print(f"\n📊 OVERALL ACCURACY: {correct_count}/{total_count} = {accuracy:.1f}%")

    # By category
    similar_results = [r for r in results if r.pair.category == "similar"]
    different_results = [r for r in results if r.pair.category == "different"]
    identical_results = [r for r in results if r.pair.category == "identical"]

    # Recall (for similar + identical)
    similar_correct = sum(1 for r in similar_results if r.correct)
    identical_correct = sum(1 for r in identical_results if r.correct)
    recall = (
        (similar_correct + identical_correct)
        / (len(similar_results) + len(identical_results))
        * 100
    )

    if verbose:
        print(f"\n📊 SIMILAR QUERIES (Recall):")
        print(
            f"   - Similar matched: {similar_correct}/{len(similar_results)} = {similar_correct/len(similar_results)*100:.1f}%"
        )
        print(
            f"   - Identical matched: {identical_correct}/{len(identical_results)} = {identical_correct/len(identical_results)*100:.1f}%"
        )
        print(f"   - Total recall: {recall:.1f}%")

    # Precision (for different topics - should NOT match)
    different_correct = sum(1 for r in different_results if r.correct)
    false_positive_rate = (
        (len(different_results) - different_correct) / len(different_results) * 100
    )

    if verbose:
        print(f"\n📊 DIFFERENT TOPICS (Precision):")
        print(
            f"   - Correctly rejected: {different_correct}/{len(different_results)} = {different_correct/len(different_results)*100:.1f}%"
        )
        print(f"   - False positive rate: {false_positive_rate:.1f}%")

    # Speed stats
    latencies = [r.latency_ms for r in results]
    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    min_latency = min(latencies)

    if verbose:
        print(f"\n📊 SPEED:")
        print(f"   - Average latency: {avg_latency:.1f}ms")
        print(f"   - Min latency: {min_latency:.1f}ms")
        print(f"   - Max latency: {max_latency:.1f}ms")

    # BGE score distribution for matches
    bge_scores = [r.bge_score for r in results if r.bge_score is not None]
    if bge_scores:
        if verbose:
            print(f"\n📊 BGE SCORE DISTRIBUTION (for matches):")
            print(f"   - Min: {min(bge_scores):.4f}")
            print(f"   - Max: {max(bge_scores):.4f}")
            print(f"   - Mean: {sum(bge_scores)/len(bge_scores):.4f}")

    # Show failed cases
    failed = [r for r in results if not r.correct]
    if verbose:
        if failed:
            print(f"\n⚠️ FAILED CASES ({len(failed)}):")
            for r in failed:
                expected = "should match" if r.pair.should_match else "should NOT match"
                got = f"MATCHED (bge={r.bge_score:.4f})" if r.matched else "NO MATCH"
                print(f"   - [{r.pair.category}] {expected} but got {got}")
                print(f"     Q1: {r.pair.q1[:50]}...")
                print(f"     Q2: {r.pair.q2[:50]}...")
        else:
            print(f"\n🎉 ALL TEST CASES PASSED!")

    # Cleanup
    cache.clear_all()

    # Final summary
    if verbose:
        print()
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(
            f"""
  Semantic Cache V2 (Hybrid Cosine + BGE) Evaluation:
  
  ✅ Accuracy:     {accuracy:.1f}% ({correct_count}/{total_count})
  ✅ Recall:       {recall:.1f}% (similar queries correctly matched)
  ✅ Precision:    {100-false_positive_rate:.1f}% (different topics correctly rejected)
  ✅ Avg Latency:  {avg_latency:.1f}ms
  
  Config: cosine_threshold={cache.cosine_threshold}, bge_threshold={cache.bge_threshold}
"""
        )

    return {
        "accuracy": accuracy,
        "recall": recall,
        "precision": 100 - false_positive_rate,
        "avg_latency_ms": avg_latency,
        "failed_count": len(failed),
        "bge_threshold": bge_threshold,
    }


def run_threshold_sweep():
    """Test multiple BGE thresholds to find optimal."""
    print("=" * 80)
    print("BGE THRESHOLD SWEEP ANALYSIS")
    print("=" * 80)
    print()

    thresholds = [0.95, 0.90, 0.85, 0.80, 0.75, 0.70, 0.65, 0.60, 0.55, 0.50]
    results = []

    for threshold in thresholds:
        print(f"Testing BGE threshold = {threshold}...", end=" ", flush=True)
        result = run_evaluation(bge_threshold=threshold, verbose=False)
        if result:
            results.append(result)
            print(
                f"Accuracy={result['accuracy']:.1f}%, Recall={result['recall']:.1f}%, Precision={result['precision']:.1f}%"
            )

    print()
    print("=" * 80)
    print("THRESHOLD COMPARISON")
    print("=" * 80)
    print()
    print(
        f"{'Threshold':<10} {'Accuracy':<12} {'Recall':<12} {'Precision':<12} {'Failed':<8}"
    )
    print("-" * 60)

    best_accuracy = 0
    best_threshold = 0.85

    for r in results:
        print(
            f"{r['bge_threshold']:<10.2f} {r['accuracy']:<12.1f} {r['recall']:<12.1f} {r['precision']:<12.1f} {r['failed_count']:<8}"
        )
        if r["accuracy"] > best_accuracy:
            best_accuracy = r["accuracy"]
            best_threshold = r["bge_threshold"]

    print()
    print(f"🎯 BEST THRESHOLD: {best_threshold} (Accuracy: {best_accuracy:.1f}%)")
    print()

    return best_threshold


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--sweep":
        # Run threshold sweep
        best = run_threshold_sweep()
        print(f"\nRe-running with best threshold ({best})...")
        run_evaluation(bge_threshold=best, verbose=True)
    else:
        # Default: run single evaluation
        run_evaluation()
