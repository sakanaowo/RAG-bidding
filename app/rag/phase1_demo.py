"""
Phase 1 Demo - Quick Wins Implementation
Test và demo các cải tiến nhanh của hệ thống RAG
"""

import sys
from pathlib import Path
from typing import Dict

# Add app directory to Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.generation.chains.qa_chain import answer

BASELINE_MODE = "fast"
PHASE1_MODE = "quality"


def phase1_enhanced_answer(question: str, mode: str = "balanced") -> Dict:
    """Trả lời câu hỏi với Phase 1 pipeline (cho demo)."""
    if mode not in {"fast", "balanced", "quality"}:
        mode = "balanced"
    return answer(question, mode=mode)


def compare_basic_vs_phase1(
    question: str,
    baseline_mode: str = BASELINE_MODE,
    phase1_mode: str = PHASE1_MODE,
) -> Dict:
    """So sánh giữa chế độ baseline và chế độ Phase 1 chất lượng."""
    print(f"\n🔍 Testing question: {question}")
    print("=" * 60)

    # Baseline (giả lập fixed k bằng fast mode)
    basic_result = answer(question, mode=baseline_mode)

    # Phase 1 Enhanced
    enhanced_result = phase1_enhanced_answer(question, mode=phase1_mode)

    comparison = {
        "question": question,
        "basic": {
            "answer_length": len(basic_result["answer"]),
            "sources_count": len(basic_result["sources"]),
            "mode": baseline_mode,
            "retrieval_method": f"Adaptive k={basic_result['adaptive_retrieval']['k_used']}",
        },
        "phase1_enhanced": {
            "answer_length": len(enhanced_result["answer"]),
            "sources_count": len(enhanced_result["sources"]),
            "retrieval_method": f"Adaptive k={enhanced_result['adaptive_retrieval']['k_used']}",
            "complexity": enhanced_result["adaptive_retrieval"]["complexity"],
            "mode": enhanced_result["phase1_mode"],
        },
    }

    return comparison


def demo_phase1():
    """Demo Phase 1 quick wins"""
    print("🚀 RAG System Phase 1 - Quick Wins Demo")
    print("=" * 50)

    # Test questions với luật đấu thầu (matching với data thực)
    test_questions = [
        "Điều kiện tham gia đấu thầu là gì?",  # Simple factual
        "So sánh quy trình đấu thầu rộng rãi và đấu thầu hạn chế trong luật đấu thầu 2023",  # Complex
        "Nhà thầu là gì?",  # Very simple
        "Phân tích vai trò của hệ thống mạng đấu thầu quốc gia theo thông tư 22/2024",  # Complex analytical
    ]

    for question in test_questions:
        comparison = compare_basic_vs_phase1(question)

        print(f"\n📊 Question: {question}")
        print(
            f"   Baseline mode ({comparison['basic']['mode']}): {comparison['basic']['retrieval_method']}"
        )
        print(
            f"   Enhanced: {comparison['phase1_enhanced']['retrieval_method']} (Complexity: {comparison['phase1_enhanced']['complexity']})"
        )
        print()

    print("✅ Phase 1 Demo completed!")
    print("\n🎯 Key Improvements Delivered:")
    print("   • Dynamic document retrieval (k=2-8 based on complexity)")
    print("   • Vietnamese question analysis")
    print("   • Configurable RAG modes (fast/balanced/quality)")
    print("   • 845 legal documents embedded and searchable")
    print("   • Ready foundation for Phase 2")


if __name__ == "__main__":
    demo_phase1()
