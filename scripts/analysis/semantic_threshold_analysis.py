"""
Semantic Similarity Threshold Analysis Script

This script tests multiple pairs of semantically similar questions
to determine the optimal threshold for the semantic cache.

Usage:
    cd RAG-bidding
    source .venv/bin/activate
    python scripts/analysis/semantic_threshold_analysis.py
"""

import numpy as np
from src.embedding.embedders.openai_embedder import OpenAIEmbedder


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def main():
    embedder = OpenAIEmbedder()

    # Test cases: pairs of semantically similar questions about bidding law
    test_pairs = [
        # =====================================================================
        # SIMILAR PAIRS (should match with semantic cache)
        # =====================================================================
        # Pair 1 - Năng lực tài chính (original case)
        (
            "Yêu cầu về năng lực tài chính của nhà thầu gồm những gì",
            "Điều kiện về năng lực tài chính khi tham gia đấu thầu yêu cầu những gì",
            "similar",
        ),
        # Pair 2 - Hồ sơ mời thầu
        (
            "Hồ sơ mời thầu bao gồm những nội dung gì",
            "Thành phần của hồ sơ mời thầu gồm những gì",
            "similar",
        ),
        # Pair 3 - Thời gian đấu thầu
        (
            "Thời gian nộp hồ sơ dự thầu là bao lâu",
            "Nhà thầu có bao nhiêu ngày để nộp hồ sơ",
            "similar",
        ),
        # Pair 4 - Bảo lãnh dự thầu
        (
            "Quy định về bảo lãnh dự thầu như thế nào",
            "Yêu cầu bảo đảm dự thầu theo quy định là gì",
            "similar",
        ),
        # Pair 5 - Đánh giá hồ sơ
        (
            "Tiêu chí đánh giá hồ sơ dự thầu gồm những gì",
            "Các tiêu chuẩn để chấm điểm hồ sơ thầu",
            "similar",
        ),
        # Pair 6 - Năng lực kinh nghiệm
        (
            "Yêu cầu về năng lực kinh nghiệm của nhà thầu",
            "Nhà thầu cần có kinh nghiệm gì để tham gia đấu thầu",
            "similar",
        ),
        # Pair 7 - Hợp đồng
        (
            "Các loại hợp đồng trong đấu thầu",
            "Phân loại hợp đồng đấu thầu theo quy định",
            "similar",
        ),
        # Pair 8 - Giá dự thầu
        (
            "Cách tính giá dự thầu như thế nào",
            "Phương pháp xác định giá trong hồ sơ dự thầu",
            "similar",
        ),
        # Pair 9 - Mở thầu
        (
            "Quy trình mở thầu diễn ra như thế nào",
            "Các bước trong buổi mở hồ sơ dự thầu",
            "similar",
        ),
        # Pair 10 - Nhà thầu phụ
        (
            "Quy định về sử dụng nhà thầu phụ",
            "Nhà thầu phụ được sử dụng trong trường hợp nào",
            "similar",
        ),
        # Pair 11 - Khiếu nại
        (
            "Quy trình khiếu nại kết quả đấu thầu",
            "Cách thức giải quyết tranh chấp trong đấu thầu",
            "similar",
        ),
        # Pair 12 - Hủy thầu
        ("Trường hợp nào phải hủy thầu", "Điều kiện hủy bỏ cuộc đấu thầu", "similar"),
        # =====================================================================
        # DIFFERENT TOPIC PAIRS (should NOT match)
        # =====================================================================
        # Pair 13 - Different topics
        (
            "Yêu cầu về năng lực tài chính của nhà thầu",
            "Quy trình mở thầu diễn ra như thế nào",
            "different",
        ),
        # Pair 14 - Very different topics
        ("Điều kiện tham gia đấu thầu", "Quy định về bảo hành công trình", "different"),
        # =====================================================================
        # IDENTICAL PAIRS (should always match - baseline)
        # =====================================================================
        # Pair 15 - Identical
        (
            "Yêu cầu về năng lực tài chính của nhà thầu gồm những gì",
            "Yêu cầu về năng lực tài chính của nhà thầu gồm những gì",
            "identical",
        ),
        # =====================================================================
        # SLIGHTLY DIFFERENT WORDING (edge cases)
        # =====================================================================
        # Pair 16
        ("Điều kiện tham gia đấu thầu", "Yêu cầu để được tham dự đấu thầu", "similar"),
        # Pair 17 - Synonym usage
        (
            "Nhà thầu cần đáp ứng điều kiện gì",
            "Yêu cầu đối với nhà thầu khi tham gia",
            "similar",
        ),
        # Pair 18 - Question form variation
        (
            "Bảo lãnh thực hiện hợp đồng là bao nhiêu phần trăm",
            "Tỷ lệ bảo đảm thực hiện hợp đồng theo quy định",
            "similar",
        ),
        (
            "Có bao nhiêu hình thức lựa chọn nhà thầu theo luật mới",
            "Các phương thức tuyển chọn nhà thầu hiện nay bao gồm những gì",
            "similar",
        ),
        # Pair 20 - Chỉ định thầu (Trường hợp áp dụng)
        (
            "Trường hợp nào được phép áp dụng chỉ định thầu",
            "Điều kiện để thực hiện chỉ định thầu trực tiếp là gì",
            "similar",
        ),
        # Pair 21 - Đấu thầu qua mạng
        (
            "Quy trình thực hiện đấu thầu qua mạng như thế nào",
            "Các bước đấu thầu trên Hệ thống mạng đấu thầu quốc gia",
            "similar",
        ),
        # Pair 22 - Ưu đãi trong đấu thầu
        (
            "Đối tượng nào được hưởng ưu đãi trong lựa chọn nhà thầu",
            "Quy định về việc ưu tiên cho hàng hóa sản xuất trong nước",
            "similar",
        ),
        # Pair 23 - Tổ chuyên gia
        (
            "Tiêu chuẩn đối với thành viên tổ chuyên gia đấu thầu",
            "Quy định về năng lực và chứng chỉ của người chấm thầu",
            "similar",
        ),
        # Pair 24 - Điều chỉnh hợp đồng
        (
            "Khi nào được phép điều chỉnh giá hợp đồng đấu thầu",
            "Quy định về việc thay đổi đơn giá trong hợp đồng",
            "similar",
        ),
        # Pair 25 - Chào hàng cạnh tranh
        (
            "Quy trình chào hàng cạnh tranh rút gọn thực hiện như thế nào",
            "Các bước làm chào hàng cạnh tranh cho gói mua sắm hàng hóa",
            "similar",
        ),
        # Pair 26 - Các hành vi bị cấm
        (
            "Những hành vi nào bị nghiêm cấm trong đấu thầu",
            "Các lỗi vi phạm dẫn đến bị cấm tham gia hoạt động đấu thầu",
            "similar",
        ),
        # Pair 27 - Thời gian có hiệu lực của hồ sơ
        (
            "Hiệu lực của hồ sơ dự thầu được quy định là bao nhiêu ngày",
            "Thời gian bảo đảm giá trị của hồ sơ thầu tính từ thời điểm nào",
            "similar",
        ),
        # Pair 28 - Giải quyết kiến nghị
        (
            "Quy trình giải quyết kiến nghị trong đấu thầu",
            "Các bước khi nhà thầu muốn khiếu nại về kết quả lựa chọn nhà thầu",
            "similar",
        ),
        # Pair 29 - Cùng từ khóa nhưng đối tượng khác nhau (DIFFERENT)
        (
            "Quy định về bảo đảm dự thầu",
            "Quy định về bảo đảm thực hiện hợp đồng",
            "different",
        ),
        # Pair 30 - Cùng từ khóa nhưng giai đoạn khác nhau (DIFFERENT)
        (
            "Nội dung chính của hồ sơ mời thầu (HSMT)",
            "Nội dung chính của hồ sơ dự thầu (HSDT)",
            "different",
        ),
        # Pair 31 - Từ ngữ khác hoàn toàn nhưng cùng ý nghĩa (SIMILAR)
        (
            "Tư cách hợp lệ của nhà thầu",
            "Điều kiện để doanh nghiệp không bị loại khi xét duyệt pháp lý",
            "similar",
        ),
        # Pair 32 - Phủ định/Khẳng định (DIFFERENT)
        (
            "Các trường hợp được phép chỉ định thầu",
            "Các trường hợp không được phép chỉ định thầu",
            "different",
        ),
        # Pair 33 - Viết tắt vs Viết đầy đủ (SIMILAR)
        (
            "Hướng dẫn nộp E-HSDT trên hệ thống",
            "Cách thức gửi hồ sơ dự thầu qua mạng",
            "similar",
        ),
        # Pair 34 - Khác biệt về đơn vị thời gian (DIFFERENT)
        (
            "Thời gian có hiệu lực là 90 ngày",
            "Thời gian có hiệu lực là 120 ngày",
            "different",
        ),
        # Pair 35 - Nhà thầu chính vs Nhà thầu phụ (DIFFERENT)
        (
            "Trách nhiệm của nhà thầu chính trong gói thầu",
            "Quy định về phần việc của nhà thầu phụ",
            "different",
        ),
        # Pair 36 - Tổng quát vs Chi tiết (SIMILAR - Thường bị điểm thấp)
        (
            "Chứng minh năng lực tài chính",
            "Cung cấp báo cáo tài chính kiểm toán trong 3 năm gần nhất",
            "similar",
        ),
        # Pair 37 - Đảo cấu trúc câu (SIMILAR)
        (
            "Ai là người có thẩm quyền quyết định hủy thầu",
            "Việc hủy thầu do cấp nào có thẩm quyền phê duyệt",
            "similar",
        ),
        # Pair 38 - Thay đổi thuật ngữ chuyên môn (DIFFERENT)
        ("Phương pháp giá thấp nhất", "Phương pháp giá đánh giá", "different"),
    ]

    print("=" * 80)
    print("SEMANTIC SIMILARITY ANALYSIS FOR THRESHOLD OPTIMIZATION")
    print("=" * 80)
    print()

    similar_sims = []
    different_sims = []
    identical_sims = []

    for i, (q1, q2, category) in enumerate(test_pairs):
        e1 = np.array(embedder.embed_query(q1))
        e2 = np.array(embedder.embed_query(q2))
        sim = cosine_similarity(e1, e2)

        # Categorize
        if category == "similar":
            similar_sims.append(sim)
            marker = "[SIMILAR]"
        elif category == "different":
            different_sims.append(sim)
            marker = "[DIFFERENT TOPIC]"
        else:
            identical_sims.append(sim)
            marker = "[IDENTICAL]"

        print(f"Pair {i+1}: {marker}")
        print(f"  Q1: {q1[:60]}{'...' if len(q1) > 60 else ''}")
        print(f"  Q2: {q2[:60]}{'...' if len(q2) > 60 else ''}")
        print(f"  Similarity: {sim:.4f}")
        print()

    print("=" * 80)
    print("STATISTICS")
    print("=" * 80)

    print(f"\n📊 SIMILAR pairs (should match): {len(similar_sims)}")
    print(f"   Min:    {min(similar_sims):.4f}")
    print(f"   Max:    {max(similar_sims):.4f}")
    print(f"   Mean:   {np.mean(similar_sims):.4f}")
    print(f"   Median: {np.median(similar_sims):.4f}")
    print(f"   Std:    {np.std(similar_sims):.4f}")

    print(f"\n📊 DIFFERENT topic pairs (should NOT match): {len(different_sims)}")
    print(f"   Max:    {max(different_sims):.4f}")
    print(f"   Mean:   {np.mean(different_sims):.4f}")

    print(f"\n📊 IDENTICAL pairs (baseline): {len(identical_sims)}")
    print(f"   Mean:   {np.mean(identical_sims):.4f}")

    print("\n" + "=" * 80)
    print("THRESHOLD ANALYSIS")
    print("=" * 80)

    # Calculate how many similar pairs would be caught at different thresholds
    thresholds = [0.95, 0.90, 0.85, 0.80, 0.75, 0.70, 0.65]

    print("\nThreshold | Similar Caught | Different Caught | Recommendation")
    print("-" * 65)

    for t in thresholds:
        similar_caught = sum(1 for s in similar_sims if s >= t)
        similar_pct = similar_caught / len(similar_sims) * 100
        different_caught = sum(1 for s in different_sims if s >= t)
        different_pct = different_caught / len(different_sims) * 100

        recommendation = ""
        if different_pct > 0:
            recommendation = "❌ Too low (false positives)"
        elif similar_pct < 50:
            recommendation = "❌ Too high (misses most)"
        elif similar_pct < 80:
            recommendation = "⚠️ High (misses some)"
        else:
            recommendation = "✅ Good"

        print(
            f"   {t:.2f}   |     {similar_caught:2d}/{len(similar_sims)} ({similar_pct:5.1f}%) |      {different_caught}/{len(different_sims)} ({different_pct:5.1f}%)  | {recommendation}"
        )

    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)

    # Find optimal threshold
    # Should catch most similar pairs but not different topic pairs
    max_different = max(different_sims)
    safe_margin = 0.03  # 3% margin above max different

    # Threshold should be above max_different + margin
    min_safe_threshold = max_different + safe_margin

    # Find threshold that catches at least 70% of similar pairs
    sorted_similar = sorted(similar_sims)
    threshold_70pct = sorted_similar[
        int(len(sorted_similar) * 0.30)
    ]  # 30th percentile = catches 70%
    threshold_80pct = sorted_similar[
        int(len(sorted_similar) * 0.20)
    ]  # 20th percentile = catches 80%

    print(f"\n  Max 'different topic' similarity: {max_different:.4f}")
    print(f"  Min safe threshold (max + 3%):    {min_safe_threshold:.4f}")
    print(f"  Threshold for 70% recall:         {threshold_70pct:.4f}")
    print(f"  Threshold for 80% recall:         {threshold_80pct:.4f}")

    # Recommended threshold
    recommended = max(min_safe_threshold, threshold_70pct)

    print(f"\n  🎯 RECOMMENDED THRESHOLD: {recommended:.2f}")
    print(f"     (Ensures no false positives while catching ~70%+ of similar queries)")

    # Show what current 0.95 threshold would catch
    current_caught = sum(1 for s in similar_sims if s >= 0.95)
    print(
        f"\n  ⚠️ Current threshold (0.95) catches only {current_caught}/{len(similar_sims)} similar pairs ({current_caught/len(similar_sims)*100:.1f}%)"
    )


if __name__ == "__main__":
    main()
