#!/usr/bin/env python3
"""
Test enhanced source references
"""
import sys
from pathlib import Path

# Add app directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.rag.chain import answer


def test_enhanced_sources():
    """Test enhanced source references."""
    
    print("🔍 TESTING ENHANCED SOURCE REFERENCES")
    print("="*50)
    
    question = "Điều kiện tham gia đấu thầu là gì?"
    
    print(f"📝 Question: {question}")
    print("⏳ Processing...")
    
    try:
        result = answer(question, "balanced")
        
        print(f"\n🎯 ANSWER WITH ENHANCED SOURCES:")
        print(result['answer'])
        
        print(f"\n📊 DETAILED SOURCES:")
        for source in result['detailed_sources']:
            print(source)
            print()
        
        print(f"\n📋 SIMPLE SOURCES (for API):")
        for source in result['sources']:
            print(f"   {source}")
        
        print(f"\n✅ Enhanced source references working!")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_enhanced_sources()
    exit(0 if success else 1)