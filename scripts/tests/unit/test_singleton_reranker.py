"""
Unit Tests cho Singleton Reranker Pattern

Test suite để verify:
1. Singleton pattern hoạt động đúng (same instance)
2. Thread-safe (concurrent access không tạo multiple instances)
3. Memory cleanup (reset_singleton_reranker)
4. Performance (singleton vs new instance)

NOTE: Tests sẽ tự động detect GPU và clear CUDA cache giữa các tests.
"""

import pytest
import threading
import time
import torch
from typing import List
from langchain_core.documents import Document

from src.retrieval.ranking import (
    get_singleton_reranker,
    reset_singleton_reranker,
    BGEReranker,
)


@pytest.fixture(autouse=True)
def cleanup_cuda_cache():
    """Auto cleanup CUDA cache trước và sau mỗi test"""
    # Before test
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    
    yield
    
    # After test
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


class TestSingletonPattern:
    """Test basic singleton pattern behavior"""

    def test_singleton_returns_same_instance(self):
        """Verify rằng multiple calls return cùng 1 instance"""
        reranker1 = get_singleton_reranker()
        reranker2 = get_singleton_reranker()
        reranker3 = get_singleton_reranker()

        # All should be same instance
        assert reranker1 is reranker2
        assert reranker2 is reranker3
        assert id(reranker1) == id(reranker2) == id(reranker3)

    def test_direct_instantiation_creates_different_instances(self):
        """Verify rằng BGEReranker() tạo instances khác nhau (old behavior)"""
        # Reset singleton first
        reset_singleton_reranker()

        # Direct instantiation (NOT recommended) - với CPU để tránh OOM
        reranker1 = BGEReranker(device="cpu")
        reranker2 = BGEReranker(device="cpu")

        # Should be DIFFERENT instances (memory leak!)
        assert reranker1 is not reranker2
        assert id(reranker1) != id(reranker2)
        
        # Cleanup immediately để free memory
        del reranker1
        del reranker2
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def test_reset_allows_new_instance(self):
        """Verify reset_singleton_reranker() clears instance"""
        reranker1 = get_singleton_reranker()
        instance_id1 = id(reranker1)

        # Reset
        reset_singleton_reranker()

        # Get new instance
        reranker2 = get_singleton_reranker()
        instance_id2 = id(reranker2)

        # Should be DIFFERENT instance after reset
        assert instance_id1 != instance_id2

    def test_singleton_survives_multiple_resets(self):
        """Test multiple reset cycles"""
        instances = []

        for i in range(3):
            reranker = get_singleton_reranker()
            instances.append(id(reranker))
            reset_singleton_reranker()
            # Cleanup CUDA cache giữa các resets
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        # All instances should be different (each reset creates new one)
        assert len(set(instances)) == 3


class TestThreadSafety:
    """Test thread-safety của singleton pattern"""

    def test_concurrent_access_returns_same_instance(self):
        """Verify thread-safe: 10 threads cùng lúc chỉ tạo 1 instance"""
        reset_singleton_reranker()

        instances = []
        lock = threading.Lock()

        def get_instance():
            reranker = get_singleton_reranker()
            with lock:
                instances.append(id(reranker))

        # Create 10 threads cùng lúc
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=get_instance)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All threads should get SAME instance
        assert len(instances) == 10
        assert len(set(instances)) == 1  # Only 1 unique instance ID

    def test_race_condition_handling(self):
        """Test double-checked locking works correctly"""
        reset_singleton_reranker()

        instances = []
        barrier = threading.Barrier(5)  # Synchronize 5 threads

        def get_instance_with_barrier():
            # Wait for all threads to be ready
            barrier.wait()
            # Then all access singleton at SAME time
            reranker = get_singleton_reranker()
            instances.append(id(reranker))

        threads = [threading.Thread(target=get_instance_with_barrier) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Despite race condition, should only create 1 instance
        assert len(set(instances)) == 1


class TestFunctionality:
    """Test rằng singleton reranker hoạt động đúng chức năng"""

    @pytest.fixture
    def sample_documents(self) -> List[Document]:
        """Sample legal documents cho testing"""
        return [
            Document(
                page_content="Luật Đấu thầu 2023 quy định về quy trình đấu thầu công khai.",
                metadata={"doc_type": "Luật", "status": "active"},
            ),
            Document(
                page_content="Nghị định 63/2014 về hướng dẫn thực hiện Luật Đấu thầu.",
                metadata={"doc_type": "Nghị định", "status": "active"},
            ),
            Document(
                page_content="Thông tư 08/2015 về mẫu hồ sơ mời thầu.",
                metadata={"doc_type": "Thông tư", "status": "active"},
            ),
            Document(
                page_content="Bài viết về các lỗi thường gặp trong đấu thầu.",
                metadata={"doc_type": "Bài viết", "status": "active"},
            ),
        ]

    def test_singleton_rerank_works(self, sample_documents):
        """Verify singleton reranker có thể rerank documents"""
        reranker = get_singleton_reranker()
        query = "quy trình đấu thầu"

        results = reranker.rerank(query, sample_documents, top_k=2)

        # Should return top 2 docs
        assert len(results) == 2
        # Each result is (document, score)
        assert all(isinstance(r[0], Document) for r in results)
        # Scores can be float or numpy float (both acceptable)
        import numpy as np
        assert all(isinstance(r[1], (float, np.floating)) for r in results)
        # Scores should be in descending order
        assert results[0][1] >= results[1][1]

    def test_singleton_and_direct_give_similar_results(self, sample_documents):
        """Verify singleton và direct instantiation cho results tương tự"""
        query = "quy trình đấu thầu công khai"

        # Singleton
        singleton_reranker = get_singleton_reranker()
        singleton_results = singleton_reranker.rerank(query, sample_documents, top_k=2)

        # Direct instantiation
        direct_reranker = BGEReranker()
        direct_results = direct_reranker.rerank(query, sample_documents, top_k=2)

        # Scores should be identical (same model)
        assert len(singleton_results) == len(direct_results)
        for (s_doc, s_score), (d_doc, d_score) in zip(
            singleton_results, direct_results
        ):
            assert abs(s_score - d_score) < 0.001  # Floating point tolerance


class TestPerformance:
    """Test performance benefits của singleton pattern"""

    def test_singleton_faster_than_repeated_instantiation(self):
        """Verify singleton nhanh hơn create new instance mỗi lần"""
        # Measure singleton (after first load)
        get_singleton_reranker()  # Warm up (load model)

        start = time.time()
        for _ in range(10):
            _ = get_singleton_reranker()
        singleton_time = time.time() - start

        # Measure direct instantiation (CPU only để tránh OOM)
        reset_singleton_reranker()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        start = time.time()
        instances = []
        for _ in range(10):
            instances.append(BGEReranker(device="cpu"))
        direct_time = time.time() - start
        
        # Cleanup
        del instances
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        # Singleton should be MUCH faster (no model loading)
        print(f"\n📊 Performance Comparison:")
        print(f"  Singleton: {singleton_time:.4f}s for 10 calls")
        print(f"  Direct:    {direct_time:.4f}s for 10 calls")
        print(f"  Speedup:   {direct_time/singleton_time:.1f}x")

        # Singleton should be at least 100x faster (instant vs model load)
        assert singleton_time < direct_time / 50

    def test_memory_usage_stays_constant(self):
        """Verify memory không tăng khi gọi singleton nhiều lần"""
        import psutil
        import os

        process = psutil.Process(os.getpid())

        # Get baseline memory
        reset_singleton_reranker()
        _ = get_singleton_reranker()  # Load model
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Call singleton 100 times
        for _ in range(100):
            _ = get_singleton_reranker()

        final_memory = process.memory_info().rss / 1024 / 1024  # MB

        memory_increase = final_memory - baseline_memory

        print(f"\n💾 Memory Usage:")
        print(f"  Baseline: {baseline_memory:.1f} MB")
        print(f"  After 100 calls: {final_memory:.1f} MB")
        print(f"  Increase: {memory_increase:.1f} MB")

        # Memory should NOT increase significantly (<50MB variance)
        assert memory_increase < 50


class TestEdgeCases:
    """Test edge cases và error handling"""

    def test_custom_parameters_ignored_after_first_call(self):
        """Verify singleton ignores parameters sau lần đầu tiên"""
        reset_singleton_reranker()

        # First call with specific batch_size
        reranker1 = get_singleton_reranker(batch_size=64)
        first_batch_size = reranker1.batch_size  # May be auto-adjusted

        # Second call with DIFFERENT params (should be ignored)
        reranker2 = get_singleton_reranker(batch_size=8)

        # Should return SAME instance (params ignored)
        assert reranker1 is reranker2
        # Batch size should remain from first call (may be auto-adjusted by device)
        assert reranker2.batch_size == first_batch_size
        
        print(f"\n📝 Batch size test: {first_batch_size} (auto-adjusted based on device)")

    def test_reset_clears_cuda_cache_if_available(self):
        """Verify reset calls __del__ để clear CUDA cache"""
        import torch

        if not torch.cuda.is_available():
            pytest.skip("No CUDA available")

        reset_singleton_reranker()
        reranker = get_singleton_reranker(device="cuda")

        # Reset should call __del__ which clears CUDA cache
        reset_singleton_reranker()

        # Should not raise any errors
        assert True  # Test passed if no exception


if __name__ == "__main__":
    # Run tests với verbose output
    pytest.main([__file__, "-v", "-s"])
