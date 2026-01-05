#!/usr/bin/env python3
"""
Test CUDA OOM fallback mechanism

Kiểm tra:
1. BGE reranker hoạt động bình thường
2. Khi CUDA OOM → set flag và fallback
3. Lần gọi tiếp theo → dùng OpenAI reranker
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import logging
from unittest.mock import MagicMock, patch
from langchain_core.documents import Document
from src.retrieval.ranking import get_singleton_reranker, reset_singleton_reranker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Mock OpenAIReranker để test không cần API key
class MockOpenAIReranker:
    """Mock OpenAI reranker for testing"""
    def __init__(self, *args, **kwargs):
        logger.info("✅ MockOpenAIReranker created (no API key needed)")
    
    def rerank(self, query, documents, top_k=5):
        return [(doc, 0.9) for doc in documents[:top_k]]

def test_normal_operation():
    """Test BGE reranker hoạt động bình thường"""
    print("\n" + "=" * 70)
    print("TEST 1: Normal BGE operation")
    print("=" * 70)
    
    reset_singleton_reranker()
    
    reranker = get_singleton_reranker()
    print(f"✅ Reranker type: {type(reranker).__name__}")
    
    # Test rerank
    docs = [
        Document(page_content="Điều kiện tham gia đấu thầu theo Luật Đấu thầu"),
        Document(page_content="Thời hạn nộp hồ sơ dự thầu"),
        Document(page_content="Cách tính giá dự thầu"),
    ]
    
    query = "Điều kiện đấu thầu là gì?"
    results = reranker.rerank(query, docs, top_k=2)
    
    print(f"✅ Reranked {len(results)} docs")
    for doc, score in results:
        print(f"   Score: {score:.4f} - {doc.page_content[:50]}...")
    
    return True


def test_oom_simulation():
    """
    Test OOM fallback (manual simulation)
    
    Trong production, flag sẽ được set khi CUDA OOM xảy ra.
    Ở đây ta set manually để test logic.
    """
    print("\n" + "=" * 70)
    print("TEST 2: OOM Fallback Simulation")
    print("=" * 70)
    
    # Mock OpenAIReranker ở module thật, không qua bge_reranker
    with patch('src.retrieval.ranking.openai_reranker.OpenAIReranker', MockOpenAIReranker):
        # Simulate OOM by setting flag
        import src.retrieval.ranking.bge_reranker as bge_module
        bge_module._cuda_oom_fallback = True
        
        print("🔥 Simulated CUDA OOM (set flag = True)")
        
        # Reset singleton để force re-create
        reset_singleton_reranker()
        
        # Try to get reranker - should fallback to OpenAI
        reranker = get_singleton_reranker()
        reranker_type = type(reranker).__name__
        print(f"✅ Reranker type after OOM: {reranker_type}")
        
        if reranker_type == "MockOpenAIReranker":
            print("✅ FALLBACK WORKED! Using Mock OpenAI reranker")
        else:
            print(f"❌ FALLBACK FAILED! Got {reranker_type}")
            return False
        
        # Reset flag
        bge_module._cuda_oom_fallback = False
        reset_singleton_reranker()
    
    return True


def test_flag_persistence():
    """Test flag được giữ lại giữa các lần gọi"""
    print("\n" + "=" * 70)
    print("TEST 3: Flag Persistence")
    print("=" * 70)
    
    # Mock ở module thật
    with patch('src.retrieval.ranking.openai_reranker.OpenAIReranker', MockOpenAIReranker):
        import src.retrieval.ranking.bge_reranker as bge_module
        
        # Set flag
        bge_module._cuda_oom_fallback = True
        print("🔥 Set OOM flag = True")
        
        # Reset singleton
        reset_singleton_reranker()
        
        # Multiple calls should all return Mock OpenAI
        for i in range(3):
            reranker = get_singleton_reranker()
            reranker_type = type(reranker).__name__
            print(f"   Call {i+1}: {reranker_type}")
            
            if reranker_type != "MockOpenAIReranker":
                print(f"❌ Call {i+1} failed - got {reranker_type}")
                return False
        
        print("✅ Flag persisted correctly!")
        
        # Reset
        bge_module._cuda_oom_fallback = False
        reset_singleton_reranker()
    
    return True


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🧪 CUDA OOM FALLBACK TESTS")
    print("=" * 70)
    
    tests = [
        ("Normal Operation", test_normal_operation),
        ("OOM Fallback", test_oom_simulation),
        ("Flag Persistence", test_flag_persistence),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {name} PASSED")
            else:
                failed += 1
                print(f"❌ {name} FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {name} FAILED with error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print(f"📊 RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)
    
    sys.exit(0 if failed == 0 else 1)
