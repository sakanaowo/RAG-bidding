#!/usr/bin/env python3
"""
Test enhanced sources với nhiều câu hỏi khác nhau
"""
import sys
from pathlib import Path

# Add app directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.rag.chain import answer


def test_multiple_questions():
    """Test với nhiều loại câu hỏi khác nhau."""
    
    print("🔍 TESTING ENHANCED SOURCES - MULTIPLE QUESTIONS")
    print("="*60)
    
    questions = [
        {
            "q": "Thông tư 22/2024 quy định gì về hệ thống mạng đấu thầu quốc gia?",
            "mode": "quality",
            "description": "Câu hỏi về thông tư cụ thể"
        },
        {
            "q": "So sánh đấu thầu rộng rãi và đấu thầu hạn chế?", 
            "mode": "balanced",
            "description": "Câu hỏi so sánh"
        }
    ]
    
    for i, test_case in enumerate(questions, 1):
        print(f"\n{'='*20} TEST {i}/{len(questions)} {'='*20}")
        print(f"📝 Question: {test_case['q']}")
        print(f"🎛️ Mode: {test_case['mode']}")
        print(f"💭 Type: {test_case['description']}")
        print("-" * 60)
        
        try:
            result = answer(test_case['q'], test_case['mode'])
            
            print(f"\n🎯 ANSWER:")
            # Chỉ hiển thị 300 ký tự đầu của answer để không quá dài
            answer_text = result['answer']
            if len(answer_text) > 300:
                answer_preview = answer_text[:300] + "... (truncated)"
            else:
                answer_preview = answer_text
            print(answer_preview)
            
            print(f"\n📊 RETRIEVAL INFO:")
            adaptive_info = result['adaptive_retrieval']
            print(f"   Complexity: {adaptive_info['complexity']}")
            print(f"   K Used: {adaptive_info['k_used']}")
            print(f"   Docs Retrieved: {adaptive_info['docs_retrieved']}")
            
            print(f"\n📋 DETAILED SOURCES:")
            for j, source in enumerate(result['detailed_sources'][:2], 1):  # Chỉ hiển thị 2 sources đầu
                print(f"{j}. {source}")
            
            if len(result['detailed_sources']) > 2:
                print(f"... và {len(result['detailed_sources']) - 2} sources khác")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    print(f"\n🎯 Enhanced source references test completed!")


if __name__ == "__main__":
    test_multiple_questions()