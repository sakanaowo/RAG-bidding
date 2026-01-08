"""
BGE Cross-Encoder vs OpenAI Embeddings + Cosine Similarity

So sánh 2 phương pháp cho Semantic Cache:
1. OpenAI Embeddings + Cosine Similarity (hiện tại)
2. BGE Cross-Encoder Reranker (đề xuất)

Đánh giá:
- Độ chính xác phân biệt similar vs different topic
- Thời gian xử lý
- Trade-offs

Usage:
    cd RAG-bidding
    PYTHONPATH=/home/sakana/Code/RAG-project/RAG-bidding python scripts/analysis/semantic_cache_bge_vs_cosine.py
"""

import numpy as np
import time
from typing import List, Tuple
from dataclasses import dataclass

# Import project modules
from src.embedding.embedders.openai_embedder import OpenAIEmbedder
from src.retrieval.ranking.bge_reranker import get_singleton_reranker


@dataclass
class TestPair:
    """Test case for similarity comparison."""
    q1: str
    q2: str
    category: str  # "similar", "different", "identical"
    description: str = ""


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def get_test_pairs() -> List[TestPair]:
    """Define test pairs for evaluation."""
    return [
        # =====================================================================
        # SIMILAR PAIRS (should match with semantic cache)
        # =====================================================================
        TestPair("Yêu cầu về năng lực tài chính của nhà thầu gồm những gì",
                 "Điều kiện về năng lực tài chính khi tham gia đấu thầu yêu cầu những gì",
                 "similar", "Năng lực tài chính - original case"),
        
        TestPair("Hồ sơ mời thầu bao gồm những nội dung gì",
                 "Thành phần của hồ sơ mời thầu gồm những gì",
                 "similar", "Hồ sơ mời thầu"),
        
        TestPair("Thời gian nộp hồ sơ dự thầu là bao lâu",
                 "Nhà thầu có bao nhiêu ngày để nộp hồ sơ",
                 "similar", "Thời gian nộp HSDT"),
        
        TestPair("Quy định về bảo lãnh dự thầu như thế nào",
                 "Yêu cầu bảo đảm dự thầu theo quy định là gì",
                 "similar", "Bảo lãnh dự thầu"),
        
        TestPair("Tiêu chí đánh giá hồ sơ dự thầu gồm những gì",
                 "Các tiêu chuẩn để chấm điểm hồ sơ thầu",
                 "similar", "Tiêu chí đánh giá HSDT"),
        
        TestPair("Các loại hợp đồng trong đấu thầu",
                 "Phân loại hợp đồng đấu thầu theo quy định",
                 "similar", "Loại hợp đồng"),
        
        TestPair("Quy trình mở thầu diễn ra như thế nào",
                 "Các bước trong buổi mở hồ sơ dự thầu",
                 "similar", "Quy trình mở thầu"),
        
        TestPair("Trường hợp nào được phép áp dụng chỉ định thầu",
                 "Điều kiện để thực hiện chỉ định thầu trực tiếp là gì",
                 "similar", "Chỉ định thầu"),
        
        TestPair("Những hành vi nào bị nghiêm cấm trong đấu thầu",
                 "Các lỗi vi phạm dẫn đến bị cấm tham gia hoạt động đấu thầu",
                 "similar", "Hành vi cấm"),
        
        TestPair("Ai là người có thẩm quyền quyết định hủy thầu",
                 "Việc hủy thầu do cấp nào có thẩm quyền phê duyệt",
                 "similar", "Thẩm quyền hủy thầu"),
        
        # =====================================================================
        # DIFFERENT TOPIC PAIRS (should NOT match - tricky cases)
        # =====================================================================
        TestPair("Quy định về bảo đảm dự thầu",
                 "Quy định về bảo đảm thực hiện hợp đồng",
                 "different", "Bảo đảm dự thầu vs bảo đảm HĐ - khác nhau!"),
        
        TestPair("Nội dung chính của hồ sơ mời thầu (HSMT)",
                 "Nội dung chính của hồ sơ dự thầu (HSDT)",
                 "different", "HSMT vs HSDT - khác nhau!"),
        
        TestPair("Các trường hợp được phép chỉ định thầu",
                 "Các trường hợp không được phép chỉ định thầu",
                 "different", "Được phép vs không được phép - ngược nhau!"),
        
        TestPair("Thời gian có hiệu lực là 90 ngày",
                 "Thời gian có hiệu lực là 120 ngày",
                 "different", "90 ngày vs 120 ngày - số khác nhau!"),
        
        TestPair("Phương pháp giá thấp nhất",
                 "Phương pháp giá đánh giá",
                 "different", "Phương pháp đánh giá khác nhau!"),
        
        TestPair("Trách nhiệm của nhà thầu chính trong gói thầu",
                 "Quy định về phần việc của nhà thầu phụ",
                 "different", "Nhà thầu chính vs nhà thầu phụ"),
        
        TestPair("Yêu cầu về năng lực tài chính của nhà thầu",
                 "Quy trình mở thầu diễn ra như thế nào",
                 "different", "Topics hoàn toàn khác nhau"),
        
        # =====================================================================
        # IDENTICAL PAIRS (baseline - should always match)
        # =====================================================================
        TestPair("Yêu cầu về năng lực tài chính của nhà thầu gồm những gì",
                 "Yêu cầu về năng lực tài chính của nhà thầu gồm những gì",
                 "identical", "Identical query"),
    ]


def evaluate_openai_cosine(
    test_pairs: List[TestPair],
    embedder: OpenAIEmbedder
) -> Tuple[List[float], List[float], List[float], float]:
    """
    Evaluate OpenAI embeddings + cosine similarity.
    
    Returns:
        (similar_scores, different_scores, identical_scores, total_time_ms)
    """
    similar_scores = []
    different_scores = []
    identical_scores = []
    
    start_time = time.time()
    
    for pair in test_pairs:
        e1 = np.array(embedder.embed_query(pair.q1))
        e2 = np.array(embedder.embed_query(pair.q2))
        sim = cosine_similarity(e1, e2)
        
        if pair.category == "similar":
            similar_scores.append(sim)
        elif pair.category == "different":
            different_scores.append(sim)
        else:
            identical_scores.append(sim)
    
    total_time_ms = (time.time() - start_time) * 1000
    
    return similar_scores, different_scores, identical_scores, total_time_ms


def evaluate_bge_crossencoder(
    test_pairs: List[TestPair],
    reranker
) -> Tuple[List[float], List[float], List[float], float]:
    """
    Evaluate BGE cross-encoder scores.
    
    Returns:
        (similar_scores, different_scores, identical_scores, total_time_ms)
    """
    similar_scores = []
    different_scores = []
    identical_scores = []
    
    start_time = time.time()
    
    # BGE CrossEncoder.predict() takes list of [query, document] pairs
    pairs = [[pair.q1, pair.q2] for pair in test_pairs]
    
    # Get scores in batch
    scores = reranker.model.predict(pairs, show_progress_bar=False)
    
    for pair, score in zip(test_pairs, scores):
        score = float(score)
        if pair.category == "similar":
            similar_scores.append(score)
        elif pair.category == "different":
            different_scores.append(score)
        else:
            identical_scores.append(score)
    
    total_time_ms = (time.time() - start_time) * 1000
    
    return similar_scores, different_scores, identical_scores, total_time_ms


def analyze_threshold(similar: List[float], different: List[float], method_name: str):
    """Analyze optimal threshold for a method."""
    
    max_different = max(different)
    min_similar = min(similar)
    
    # Check if there's a clear separation
    has_clear_separation = min_similar > max_different
    
    print(f"\n  📊 {method_name} Threshold Analysis:")
    print(f"     Similar range:   [{min(similar):.4f}, {max(similar):.4f}]")
    print(f"     Different range: [{min(different):.4f}, {max(different):.4f}]")
    
    if has_clear_separation:
        optimal_threshold = (max_different + min_similar) / 2
        print(f"     ✅ Clear separation! Optimal threshold: {optimal_threshold:.4f}")
        print(f"        → Would catch 100% similar, 0% false positives")
    else:
        overlap = max_different - min_similar
        print(f"     ❌ Overlap detected: {overlap:.4f}")
        
        # Find threshold that minimizes errors
        all_scores = [(s, 'similar') for s in similar] + [(s, 'different') for s in different]
        all_scores.sort(key=lambda x: x[0])
        
        best_threshold = 0
        best_accuracy = 0
        
        for threshold in np.arange(min(similar) - 0.1, max(different) + 0.1, 0.01):
            similar_caught = sum(1 for s in similar if s >= threshold)
            different_rejected = sum(1 for s in different if s < threshold)
            accuracy = (similar_caught + different_rejected) / (len(similar) + len(different))
            
            if accuracy > best_accuracy:
                best_accuracy = accuracy
                best_threshold = threshold
        
        print(f"     Best threshold: {best_threshold:.4f} (accuracy: {best_accuracy:.1%})")
        
        # Calculate recall at best threshold
        similar_caught = sum(1 for s in similar if s >= best_threshold)
        false_positives = sum(1 for s in different if s >= best_threshold)
        print(f"     At {best_threshold:.4f}: {similar_caught}/{len(similar)} similar caught, {false_positives}/{len(different)} false positives")


def main():
    print("=" * 80)
    print("BGE CROSS-ENCODER vs OPENAI EMBEDDINGS + COSINE SIMILARITY")
    print("=" * 80)
    
    # Initialize
    print("\n🔧 Initializing models...")
    embedder = OpenAIEmbedder()
    print("   ✅ OpenAI Embedder loaded")
    
    reranker = get_singleton_reranker()
    print("   ✅ BGE Reranker loaded")
    
    # Get test pairs
    test_pairs = get_test_pairs()
    num_similar = sum(1 for p in test_pairs if p.category == "similar")
    num_different = sum(1 for p in test_pairs if p.category == "different")
    num_identical = sum(1 for p in test_pairs if p.category == "identical")
    
    print(f"\n📋 Test pairs: {len(test_pairs)} total")
    print(f"   - Similar (should match): {num_similar}")
    print(f"   - Different (should NOT match): {num_different}")
    print(f"   - Identical (baseline): {num_identical}")
    
    # =========================================================================
    # Evaluate OpenAI + Cosine
    # =========================================================================
    print("\n" + "=" * 80)
    print("METHOD 1: OpenAI Embeddings + Cosine Similarity (CURRENT)")
    print("=" * 80)
    
    cosine_similar, cosine_different, cosine_identical, cosine_time = evaluate_openai_cosine(
        test_pairs, embedder
    )
    
    print(f"\n⏱️  Time: {cosine_time:.1f}ms ({len(test_pairs)} pairs)")
    print(f"   Per pair: {cosine_time/len(test_pairs):.1f}ms")
    
    print(f"\n📊 Scores by category:")
    print(f"   Similar pairs:")
    for pair, score in zip([p for p in test_pairs if p.category == "similar"], cosine_similar):
        print(f"      {score:.4f} | {pair.description}")
    
    print(f"\n   Different topic pairs:")
    for pair, score in zip([p for p in test_pairs if p.category == "different"], cosine_different):
        print(f"      {score:.4f} | {pair.description}")
    
    print(f"\n   Identical pairs:")
    for pair, score in zip([p for p in test_pairs if p.category == "identical"], cosine_identical):
        print(f"      {score:.4f} | {pair.description}")
    
    analyze_threshold(cosine_similar, cosine_different, "Cosine")
    
    # =========================================================================
    # Evaluate BGE Cross-Encoder
    # =========================================================================
    print("\n" + "=" * 80)
    print("METHOD 2: BGE Cross-Encoder (PROPOSED)")
    print("=" * 80)
    
    bge_similar, bge_different, bge_identical, bge_time = evaluate_bge_crossencoder(
        test_pairs, reranker
    )
    
    print(f"\n⏱️  Time: {bge_time:.1f}ms ({len(test_pairs)} pairs)")
    print(f"   Per pair: {bge_time/len(test_pairs):.1f}ms")
    
    print(f"\n📊 Scores by category:")
    print(f"   Similar pairs:")
    for pair, score in zip([p for p in test_pairs if p.category == "similar"], bge_similar):
        print(f"      {score:.4f} | {pair.description}")
    
    print(f"\n   Different topic pairs:")
    for pair, score in zip([p for p in test_pairs if p.category == "different"], bge_different):
        print(f"      {score:.4f} | {pair.description}")
    
    print(f"\n   Identical pairs:")
    for pair, score in zip([p for p in test_pairs if p.category == "identical"], bge_identical):
        print(f"      {score:.4f} | {pair.description}")
    
    analyze_threshold(bge_similar, bge_different, "BGE")
    
    # =========================================================================
    # Comparison Summary
    # =========================================================================
    print("\n" + "=" * 80)
    print("COMPARISON SUMMARY")
    print("=" * 80)
    
    # Separation quality
    cosine_separation = min(cosine_similar) - max(cosine_different)
    bge_separation = min(bge_similar) - max(bge_different)
    
    print(f"\n📊 Score Separation (min_similar - max_different):")
    print(f"   Cosine:  {cosine_separation:.4f} {'✅' if cosine_separation > 0 else '❌ OVERLAP'}")
    print(f"   BGE:     {bge_separation:.4f} {'✅' if bge_separation > 0 else '❌ OVERLAP'}")
    
    print(f"\n⏱️  Speed Comparison:")
    print(f"   Cosine:  {cosine_time:.1f}ms total, {cosine_time/len(test_pairs):.1f}ms/pair")
    print(f"   BGE:     {bge_time:.1f}ms total, {bge_time/len(test_pairs):.1f}ms/pair")
    print(f"   Winner:  {'Cosine' if cosine_time < bge_time else 'BGE'} ({abs(cosine_time - bge_time):.1f}ms faster)")
    
    print(f"\n🎯 Accuracy Comparison:")
    
    # For Cosine - try multiple thresholds
    print(f"   Cosine thresholds:")
    for t in [0.95, 0.90, 0.85, 0.80, 0.75]:
        similar_hit = sum(1 for s in cosine_similar if s >= t)
        false_pos = sum(1 for s in cosine_different if s >= t)
        print(f"      {t:.2f}: {similar_hit}/{len(cosine_similar)} similar, {false_pos}/{len(cosine_different)} false positives")
    
    # For BGE - scores are not normalized, need to find threshold
    print(f"\n   BGE thresholds:")
    bge_min = min(min(bge_similar), min(bge_different))
    bge_max = max(max(bge_similar), max(bge_different))
    for t in np.linspace(bge_min, bge_max, 6):
        similar_hit = sum(1 for s in bge_similar if s >= t)
        false_pos = sum(1 for s in bge_different if s >= t)
        print(f"      {t:.2f}: {similar_hit}/{len(bge_similar)} similar, {false_pos}/{len(bge_different)} false positives")
    
    # =========================================================================
    # Recommendation
    # =========================================================================
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    if bge_separation > cosine_separation:
        print(f"""
    ✅ BGE Cross-Encoder BETTER for semantic cache:
       - Score separation: {bge_separation:.4f} (Cosine: {cosine_separation:.4f})
       - Can distinguish similar vs different topics more accurately
       
    ⚠️  Trade-offs:
       - Speed: {'Slower' if bge_time > cosine_time else 'Faster'} by {abs(bge_time - cosine_time):.1f}ms
       - BGE runs locally (no API cost)
       - OpenAI requires API call
       
    💡 Suggested Implementation:
       1. For SMALL cache (< 100 entries): Use BGE directly
       2. For LARGE cache: Hybrid approach
          - First: Cosine filter to top 10-20 candidates
          - Then: BGE rerank for final decision
""")
    else:
        print(f"""
    ℹ️  Results inconclusive or Cosine performs similarly.
       
    Current issues:
       - Cosine separation: {cosine_separation:.4f}
       - BGE separation: {bge_separation:.4f}
       
    Consider:
       - Adding more diverse test cases
       - Fine-tuning BGE on bidding domain
       - Using hybrid approach
""")


if __name__ == "__main__":
    main()
