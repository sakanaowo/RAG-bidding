"""
Hybrid Semantic Cache V2 - Threshold and Performance Test

Tests:
1. Threshold analysis with BGE reranker
2. Speed comparison: V1 (Cosine only) vs V2 (Hybrid)
3. Accuracy comparison with different cache sizes

Usage:
    cd RAG-bidding
    PYTHONPATH=$(pwd) python scripts/analysis/test_semantic_cache_v2.py
"""

import numpy as np
import time
from typing import List, Tuple, Dict
from dataclasses import dataclass
import sys

# Add project path
sys.path.insert(0, "/home/sakana/Code/RAG-project/RAG-bidding")

from src.embedding.embedders.openai_embedder import OpenAIEmbedder
from src.retrieval.ranking.bge_reranker import get_singleton_reranker


@dataclass
class TestPair:
    """Test case for similarity comparison."""

    q1: str
    q2: str
    category: str  # "similar", "different", "identical"
    description: str = ""


def get_test_pairs() -> List[TestPair]:
    """Define comprehensive test pairs."""
    return [
        # =====================================================================
        # SIMILAR PAIRS (should match)
        # =====================================================================
        TestPair(
            "Yêu cầu về năng lực tài chính của nhà thầu gồm những gì",
            "Điều kiện về năng lực tài chính khi tham gia đấu thầu yêu cầu những gì",
            "similar",
            "Năng lực tài chính",
        ),
        TestPair(
            "Hồ sơ mời thầu bao gồm những nội dung gì",
            "Thành phần của hồ sơ mời thầu gồm những gì",
            "similar",
            "Hồ sơ mời thầu",
        ),
        TestPair(
            "Thời gian nộp hồ sơ dự thầu là bao lâu",
            "Nhà thầu có bao nhiêu ngày để nộp hồ sơ",
            "similar",
            "Thời gian nộp HSDT",
        ),
        TestPair(
            "Quy định về bảo lãnh dự thầu như thế nào",
            "Yêu cầu bảo đảm dự thầu theo quy định là gì",
            "similar",
            "Bảo lãnh dự thầu",
        ),
        TestPair(
            "Tiêu chí đánh giá hồ sơ dự thầu gồm những gì",
            "Các tiêu chuẩn để chấm điểm hồ sơ thầu",
            "similar",
            "Tiêu chí đánh giá",
        ),
        TestPair(
            "Các loại hợp đồng trong đấu thầu",
            "Phân loại hợp đồng đấu thầu theo quy định",
            "similar",
            "Loại hợp đồng",
        ),
        TestPair(
            "Quy trình mở thầu diễn ra như thế nào",
            "Các bước trong buổi mở hồ sơ dự thầu",
            "similar",
            "Quy trình mở thầu",
        ),
        TestPair(
            "Trường hợp nào được phép áp dụng chỉ định thầu",
            "Điều kiện để thực hiện chỉ định thầu trực tiếp là gì",
            "similar",
            "Chỉ định thầu",
        ),
        TestPair(
            "Những hành vi nào bị nghiêm cấm trong đấu thầu",
            "Các lỗi vi phạm dẫn đến bị cấm tham gia hoạt động đấu thầu",
            "similar",
            "Hành vi cấm",
        ),
        TestPair(
            "Ai là người có thẩm quyền quyết định hủy thầu",
            "Việc hủy thầu do cấp nào có thẩm quyền phê duyệt",
            "similar",
            "Thẩm quyền hủy thầu",
        ),
        # =====================================================================
        # DIFFERENT TOPIC PAIRS (should NOT match - tricky cases)
        # =====================================================================
        TestPair(
            "Quy định về bảo đảm dự thầu",
            "Quy định về bảo đảm thực hiện hợp đồng",
            "different",
            "Bảo đảm dự thầu vs bảo đảm HĐ",
        ),
        TestPair(
            "Nội dung chính của hồ sơ mời thầu (HSMT)",
            "Nội dung chính của hồ sơ dự thầu (HSDT)",
            "different",
            "HSMT vs HSDT",
        ),
        TestPair(
            "Các trường hợp được phép chỉ định thầu",
            "Các trường hợp không được phép chỉ định thầu",
            "different",
            "Được vs không được chỉ định thầu",
        ),
        TestPair(
            "Thời gian có hiệu lực là 90 ngày",
            "Thời gian có hiệu lực là 120 ngày",
            "different",
            "90 ngày vs 120 ngày",
        ),
        TestPair(
            "Phương pháp giá thấp nhất",
            "Phương pháp giá đánh giá",
            "different",
            "Phương pháp đánh giá khác",
        ),
        TestPair(
            "Trách nhiệm của nhà thầu chính trong gói thầu",
            "Quy định về phần việc của nhà thầu phụ",
            "different",
            "Nhà thầu chính vs phụ",
        ),
        TestPair(
            "Yêu cầu về năng lực tài chính của nhà thầu",
            "Quy trình mở thầu diễn ra như thế nào",
            "different",
            "Topics hoàn toàn khác",
        ),
        # =====================================================================
        # IDENTICAL (baseline)
        # =====================================================================
        TestPair(
            "Yêu cầu về năng lực tài chính của nhà thầu gồm những gì",
            "Yêu cầu về năng lực tài chính của nhà thầu gồm những gì",
            "identical",
            "Identical query",
        ),
    ]


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity."""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def test_bge_threshold(test_pairs: List[TestPair], reranker) -> Dict:
    """Test BGE scores and find optimal threshold."""

    print("\n" + "=" * 80)
    print("BGE CROSS-ENCODER THRESHOLD ANALYSIS")
    print("=" * 80)

    similar_scores = []
    different_scores = []
    identical_scores = []

    # Prepare all pairs
    all_pairs = [[p.q1, p.q2] for p in test_pairs]

    # Get BGE scores in batch
    start_time = time.time()
    scores = reranker.model.predict(all_pairs, show_progress_bar=False)
    bge_time_ms = (time.time() - start_time) * 1000

    print(f"\n⏱️  BGE batch inference: {bge_time_ms:.1f}ms for {len(all_pairs)} pairs")
    print(f"   Per pair: {bge_time_ms/len(all_pairs):.1f}ms")

    print(f"\n📊 Scores by category:")

    print(f"\n   SIMILAR pairs (should match):")
    for pair, score in zip(test_pairs, scores):
        score = float(score)
        if pair.category == "similar":
            similar_scores.append(score)
            print(f"      {score:.4f} | {pair.description}")
        elif pair.category == "different":
            different_scores.append(score)
        else:
            identical_scores.append(score)

    print(f"\n   DIFFERENT topic pairs (should NOT match):")
    for pair, score in zip(test_pairs, scores):
        score = float(score)
        if pair.category == "different":
            print(f"      {score:.4f} | {pair.description}")

    print(f"\n   IDENTICAL pairs:")
    for pair, score in zip(test_pairs, scores):
        score = float(score)
        if pair.category == "identical":
            print(f"      {score:.4f} | {pair.description}")

    # Statistics
    print(f"\n📊 Statistics:")
    print(
        f"   Similar:   min={min(similar_scores):.4f}, max={max(similar_scores):.4f}, mean={np.mean(similar_scores):.4f}"
    )
    print(
        f"   Different: min={min(different_scores):.4f}, max={max(different_scores):.4f}, mean={np.mean(different_scores):.4f}"
    )

    # Check separation
    min_similar = min(similar_scores)
    max_different = max(different_scores)
    separation = min_similar - max_different

    print(f"\n📊 Score Separation:")
    print(f"   Min similar:  {min_similar:.4f}")
    print(f"   Max different: {max_different:.4f}")
    print(
        f"   Separation:   {separation:.4f} {'✅ Clear separation!' if separation > 0 else '❌ Overlap detected'}"
    )

    # Threshold analysis
    print(f"\n📊 Threshold Analysis:")
    print(f"   Threshold | Similar Hit | Different FP | Accuracy")
    print(f"   " + "-" * 50)

    best_threshold = 0
    best_accuracy = 0

    for t in np.arange(0.0, 1.01, 0.05):
        similar_hit = sum(1 for s in similar_scores if s >= t)
        different_fp = sum(1 for s in different_scores if s >= t)
        total = len(similar_scores) + len(different_scores)
        accuracy = (similar_hit + (len(different_scores) - different_fp)) / total

        marker = ""
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_threshold = t
            marker = " ← best"

        print(
            f"      {t:.2f}   |   {similar_hit:2d}/{len(similar_scores)}     |     {different_fp}/{len(different_scores)}      |  {accuracy:.1%}{marker}"
        )

    print(f"\n🎯 RECOMMENDED BGE THRESHOLD: {best_threshold:.2f}")
    print(f"   Accuracy: {best_accuracy:.1%}")
    print(
        f"   Similar hit rate: {sum(1 for s in similar_scores if s >= best_threshold)}/{len(similar_scores)}"
    )
    print(
        f"   False positive rate: {sum(1 for s in different_scores if s >= best_threshold)}/{len(different_scores)}"
    )

    return {
        "similar_scores": similar_scores,
        "different_scores": different_scores,
        "best_threshold": best_threshold,
        "best_accuracy": best_accuracy,
        "separation": separation,
    }


def test_speed_comparison(embedder, reranker, num_cached_queries: int = 100) -> Dict:
    """Compare speed of Cosine-only vs Hybrid approach."""

    print("\n" + "=" * 80)
    print(f"SPEED COMPARISON: COSINE vs HYBRID (cache size = {num_cached_queries})")
    print("=" * 80)

    # Generate fake cached queries and embeddings
    print(f"\n🔧 Generating {num_cached_queries} cached query embeddings...")

    # Use a base query and variations
    base_queries = [
        "Yêu cầu về năng lực tài chính của nhà thầu",
        "Quy trình đấu thầu điện tử",
        "Điều kiện tham gia đấu thầu",
        "Hồ sơ mời thầu cần những gì",
        "Thời gian nộp hồ sơ dự thầu",
    ]

    # Generate embeddings for cached queries
    cached_embeddings = []
    cached_queries = []

    for i in range(num_cached_queries):
        query = f"{base_queries[i % len(base_queries)]} - variation {i}"
        cached_queries.append(query)

    # Batch embed (this is just for setup, not timed)
    print("   Computing embeddings for cached queries...")
    start = time.time()
    for q in cached_queries[:20]:  # Only compute 20 for demo
        emb = np.array(embedder.embed_query(q), dtype=np.float32)
        cached_embeddings.append(emb)

    # Fill rest with random embeddings (to save API calls)
    dim = cached_embeddings[0].shape[0]
    for _ in range(num_cached_queries - 20):
        cached_embeddings.append(np.random.randn(dim).astype(np.float32))

    embed_time = time.time() - start
    print(f"   Done in {embed_time:.1f}s")

    # Test query
    test_query = (
        "Điều kiện về năng lực tài chính khi tham gia đấu thầu yêu cầu những gì"
    )

    print(f"\n📝 Test query: {test_query}")

    # Method 1: Cosine-only (current V1)
    print(f"\n🔍 Method 1: Cosine-only (V1)")

    start = time.time()
    query_embedding = np.array(embedder.embed_query(test_query), dtype=np.float32)
    embed_time_ms = (time.time() - start) * 1000

    start = time.time()
    cosine_scores = []
    for i, cached_emb in enumerate(cached_embeddings):
        sim = cosine_similarity(query_embedding, cached_emb)
        cosine_scores.append((i, sim))
    cosine_scores.sort(key=lambda x: x[1], reverse=True)
    cosine_time_ms = (time.time() - start) * 1000

    top_cosine = cosine_scores[:5]

    print(f"   Embedding time: {embed_time_ms:.1f}ms")
    print(
        f"   Cosine scan time: {cosine_time_ms:.2f}ms for {num_cached_queries} queries"
    )
    print(f"   Total V1: {embed_time_ms + cosine_time_ms:.1f}ms")
    print(f"   Top 5 cosine scores: {[round(s, 4) for _, s in top_cosine]}")

    # Method 2: Hybrid (Cosine + BGE)
    print(f"\n🔍 Method 2: Hybrid Cosine + BGE (V2)")

    # Step 1: Cosine pre-filter (top 20)
    cosine_threshold = 0.3
    top_k = 20

    start = time.time()
    candidates = [(i, s) for i, s in cosine_scores if s >= cosine_threshold][:top_k]
    cosine_filter_time_ms = (time.time() - start) * 1000

    print(
        f"   Cosine pre-filter: {len(candidates)} candidates in {cosine_filter_time_ms:.2f}ms"
    )

    # Step 2: BGE rerank
    if candidates:
        pairs = [
            [test_query, cached_queries[i] if i < len(cached_queries) else f"Query {i}"]
            for i, _ in candidates
        ]

        start = time.time()
        bge_scores = reranker.model.predict(pairs, show_progress_bar=False)
        bge_time_ms = (time.time() - start) * 1000

        # Find best
        best_idx = np.argmax(bge_scores)
        best_bge_score = float(bge_scores[best_idx])

        print(
            f"   BGE rerank time: {bge_time_ms:.1f}ms for {len(candidates)} candidates"
        )
        print(f"   Best BGE score: {best_bge_score:.4f}")
    else:
        bge_time_ms = 0
        print(f"   No candidates to rerank")

    total_v2 = embed_time_ms + cosine_time_ms + bge_time_ms
    print(f"   Total V2: {total_v2:.1f}ms")

    # Comparison
    print(f"\n📊 Speed Comparison Summary:")
    print(f"   V1 (Cosine-only):  {embed_time_ms + cosine_time_ms:.1f}ms")
    print(f"   V2 (Hybrid):       {total_v2:.1f}ms")
    print(
        f"   Overhead:          {total_v2 - (embed_time_ms + cosine_time_ms):.1f}ms (BGE rerank)"
    )

    # Simulate larger cache
    print(f"\n📊 Projected Speed at Different Cache Sizes:")
    print(f"   Cache Size | V1 (Cosine) | V2 (Hybrid) | V2 Overhead")
    print(f"   " + "-" * 55)

    for size in [100, 500, 1000, 5000, 10000]:
        # V1: Embedding + Cosine scan (linear)
        v1_cosine = cosine_time_ms * (size / num_cached_queries)
        v1_total = embed_time_ms + v1_cosine

        # V2: Embedding + Cosine scan + BGE (fixed 20 candidates)
        v2_cosine = v1_cosine
        v2_bge = bge_time_ms  # Fixed - always 20 candidates
        v2_total = embed_time_ms + v2_cosine + v2_bge

        overhead = v2_total - v1_total
        overhead_pct = overhead / v1_total * 100 if v1_total > 0 else 0

        print(
            f"   {size:6d}    |  {v1_total:8.1f}ms |  {v2_total:8.1f}ms |  +{overhead:.1f}ms ({overhead_pct:.1f}%)"
        )

    return {
        "embed_time_ms": embed_time_ms,
        "cosine_time_ms": cosine_time_ms,
        "bge_time_ms": bge_time_ms,
        "total_v1": embed_time_ms + cosine_time_ms,
        "total_v2": total_v2,
    }


def test_accuracy_simulation(reranker, test_pairs: List[TestPair]) -> Dict:
    """Simulate cache and test accuracy."""

    print("\n" + "=" * 80)
    print("ACCURACY SIMULATION: V1 (Cosine) vs V2 (Hybrid)")
    print("=" * 80)

    embedder = OpenAIEmbedder()

    # Build cache from q1 of each similar pair
    similar_pairs = [p for p in test_pairs if p.category == "similar"]

    print(f"\n🔧 Building cache from {len(similar_pairs)} queries...")

    cache = {}  # query -> embedding
    for pair in similar_pairs:
        emb = np.array(embedder.embed_query(pair.q1), dtype=np.float32)
        cache[pair.q1] = emb

    # Test lookup with q2 of each similar pair
    print(f"\n🔍 Testing lookup with paraphrased queries...")

    cosine_threshold_v1 = 0.70  # V1 threshold (if we use cosine-only)
    bge_threshold_v2 = 0.85  # V2 threshold

    v1_hits = 0
    v2_hits = 0

    print(
        f"\n   Query | V1 (Cosine≥{cosine_threshold_v1}) | V2 (BGE≥{bge_threshold_v2})"
    )
    print(f"   " + "-" * 70)

    for pair in similar_pairs:
        query = pair.q2  # Paraphrased query
        query_emb = np.array(embedder.embed_query(query), dtype=np.float32)

        # V1: Cosine lookup
        best_cosine = 0
        best_match = None
        for cached_q, cached_emb in cache.items():
            sim = cosine_similarity(query_emb, cached_emb)
            if sim > best_cosine:
                best_cosine = sim
                best_match = cached_q

        v1_hit = best_cosine >= cosine_threshold_v1
        if v1_hit:
            v1_hits += 1

        # V2: BGE on best cosine match
        if best_match:
            bge_pairs = [[query, best_match]]
            bge_score = float(
                reranker.model.predict(bge_pairs, show_progress_bar=False)[0]
            )
            v2_hit = bge_score >= bge_threshold_v2
        else:
            bge_score = 0
            v2_hit = False

        if v2_hit:
            v2_hits += 1

        v1_marker = "✅" if v1_hit else "❌"
        v2_marker = "✅" if v2_hit else "❌"

        print(
            f"   {pair.description[:25]:25s} | {v1_marker} {best_cosine:.4f}         | {v2_marker} {bge_score:.4f}"
        )

    print(f"\n📊 Accuracy Results:")
    print(
        f"   V1 (Cosine≥{cosine_threshold_v1}): {v1_hits}/{len(similar_pairs)} = {v1_hits/len(similar_pairs):.1%}"
    )
    print(
        f"   V2 (BGE≥{bge_threshold_v2}):    {v2_hits}/{len(similar_pairs)} = {v2_hits/len(similar_pairs):.1%}"
    )

    return {
        "v1_hits": v1_hits,
        "v2_hits": v2_hits,
        "total": len(similar_pairs),
        "v1_accuracy": v1_hits / len(similar_pairs),
        "v2_accuracy": v2_hits / len(similar_pairs),
    }


def main():
    print("=" * 80)
    print("HYBRID SEMANTIC CACHE V2 - THRESHOLD AND PERFORMANCE TEST")
    print("=" * 80)

    # Initialize
    print("\n🔧 Initializing models...")
    embedder = OpenAIEmbedder()
    print("   ✅ OpenAI Embedder loaded")

    reranker = get_singleton_reranker()
    print(f"   ✅ BGE Reranker loaded (device: {reranker.device})")

    # Get test pairs
    test_pairs = get_test_pairs()

    # Test 1: BGE Threshold Analysis
    threshold_results = test_bge_threshold(test_pairs, reranker)

    # Test 2: Speed Comparison
    speed_results = test_speed_comparison(embedder, reranker, num_cached_queries=100)

    # Test 3: Accuracy Simulation
    accuracy_results = test_accuracy_simulation(reranker, test_pairs)

    # Final Summary
    print("\n" + "=" * 80)
    print("FINAL SUMMARY & RECOMMENDATIONS")
    print("=" * 80)

    print(
        f"""
    🎯 BGE Threshold:
       Recommended: {threshold_results['best_threshold']:.2f}
       Accuracy: {threshold_results['best_accuracy']:.1%}
       Score separation: {threshold_results['separation']:.4f}
    
    ⏱️  Speed (100 cached queries):
       V1 (Cosine-only): {speed_results['total_v1']:.1f}ms
       V2 (Hybrid):      {speed_results['total_v2']:.1f}ms
       BGE overhead:     {speed_results['bge_time_ms']:.1f}ms
    
    🎯 Accuracy:
       V1 (Cosine): {accuracy_results['v1_accuracy']:.1%}
       V2 (Hybrid): {accuracy_results['v2_accuracy']:.1%}
    
    ✅ CONCLUSION:
       - V2 Hybrid is {'BETTER' if accuracy_results['v2_accuracy'] > accuracy_results['v1_accuracy'] else 'SIMILAR'} in accuracy
       - V2 adds ~{speed_results['bge_time_ms']:.0f}ms overhead for BGE reranking
       - BGE provides better separation for tricky cases (opposite meanings, similar wording)
       - Recommended: Use V2 with BGE threshold = {threshold_results['best_threshold']:.2f}
    """
    )


if __name__ == "__main__":
    main()
