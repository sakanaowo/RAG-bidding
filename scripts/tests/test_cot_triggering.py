"""
Test Script: Verify CoT triggering based on query complexity
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.retrieval.query_processing.complexity_analyzer import (
    QuestionComplexityAnalyzer,
)


def should_use_cot(query: str) -> bool:
    """
    Replica of conversation_service._should_use_cot() for testing.
    """
    analyzer = QuestionComplexityAnalyzer()
    analysis = analyzer.analyze_question_complexity(query)

    complexity = analysis.get("complexity", "simple")
    question_type = analysis.get("question_type", "general")

    should_enable = complexity == "complex" or question_type in [
        "analytical",
        "comparative",
        "evaluative",
    ]

    print(f"Query: {query[:60]}...")
    print(f"  Complexity: {complexity}")
    print(f"  Type: {question_type}")
    print(f"  Confidence: {analysis.get('confidence_score', 0):.2f}")
    print(f"  → CoT Enabled: {should_enable}")
    print(f"  Reasoning: {analysis.get('reasoning', 'N/A')}")
    print()

    return should_enable


if __name__ == "__main__":
    print("=" * 70)
    print("CoT TRIGGERING TEST - Vietnamese Bidding Law Queries")
    print("=" * 70)
    print()

    # Test queries from production logs
    test_queries = [
        # Simple factual (should NOT trigger CoT)
        "đấu thầu là gì",
        "thành viên tổ chuyên gia là ai",
        "bảo lãnh dự thầu là gì",
        # Moderate (depends on type)
        "quy trình đấu thầu rút gọn như thế nào",
        "điều kiện hủy thầu là gì",
        # Complex/Analytical (SHOULD trigger CoT)
        "phân tích so sánh ưu nhược điểm giữa đấu thầu rộng rãi và đấu thầu hạn chế",
        "tại sao cần phải đấu thầu rộng rãi thay vì chỉ định thầu",
        "đánh giá tác động của việc thay đổi HSMT đến quyền lợi nhà thầu",
        "giải thích mối quan hệ giữa bảo lãnh dự thầu và bảo lãnh thực hiện hợp đồng",
        # Comparative (SHOULD trigger CoT)
        "so sánh đấu thầu rộng rãi và đấu thầu hạn chế",
        "khác biệt giữa chỉ định thầu và chỉ định thầu rút gọn",
    ]

    results = []
    for query in test_queries:
        use_cot = should_use_cot(query)
        results.append((query, use_cot))

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total queries: {len(results)}")
    print(f"CoT triggered: {sum(1 for _, cot in results if cot)}")
    print(f"CoT skipped: {sum(1 for _, cot in results if not cot)}")
    print()

    print("Queries triggering CoT:")
    for query, cot in results:
        if cot:
            print(f"  ✅ {query[:60]}...")
