#!/usr/bin/env python3
"""
Test Singleton Pattern trong Production Environment

Script này simulate real production usage:
1. Start API server (hoặc import trực tiếp)
2. Gửi multiple requests
3. Verify memory không tăng
4. Verify response time ổn định

Chạy: python scripts/tests/test_singleton_production.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import torch
import time
import psutil
import os
from typing import List
from langchain_core.documents import Document

from src.retrieval.ranking import get_singleton_reranker, reset_singleton_reranker
from src.retrieval.retrievers import create_retriever


def get_memory_usage_mb():
    """Get current process memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


def get_gpu_memory_usage_mb():
    """Get current GPU memory usage in MB"""
    if torch.cuda.is_available():
        return torch.cuda.memory_allocated() / 1024 / 1024
    return 0


def test_singleton_reuse():
    """Test 1: Verify singleton được reuse"""
    print("\n" + "=" * 60)
    print("TEST 1: Singleton Instance Reuse")
    print("=" * 60)

    reset_singleton_reranker()

    reranker1 = get_singleton_reranker()
    id1 = id(reranker1)

    reranker2 = get_singleton_reranker()
    id2 = id(reranker2)

    reranker3 = get_singleton_reranker()
    id3 = id(reranker3)

    print(f"Instance 1 ID: {id1}")
    print(f"Instance 2 ID: {id2}")
    print(f"Instance 3 ID: {id3}")

    if id1 == id2 == id3:
        print("✅ PASS: All calls return same instance")
        return True
    else:
        print("❌ FAIL: Different instances created!")
        return False


def test_memory_stability():
    """Test 2: Memory không tăng khi gọi nhiều lần"""
    print("\n" + "=" * 60)
    print("TEST 2: Memory Stability (100 retrievals)")
    print("=" * 60)

    reset_singleton_reranker()

    # Warm up
    retriever = create_retriever(mode="balanced", enable_reranking=True)

    # Baseline
    baseline_mem = get_memory_usage_mb()
    baseline_gpu = get_gpu_memory_usage_mb()

    print(f"Baseline - RAM: {baseline_mem:.1f} MB, GPU: {baseline_gpu:.1f} MB")

    # Sample documents
    docs = [
        Document(
            page_content="Luật Đấu thầu 2023 quy định về quy trình đấu thầu.",
            metadata={},
        ),
        Document(
            page_content="Nghị định 63/2014 hướng dẫn Luật Đấu thầu.", metadata={}
        ),
        Document(page_content="Thông tư 08/2015 về mẫu hồ sơ mời thầu.", metadata={}),
    ]

    # Run 100 retrievals
    memories = []
    gpu_memories = []

    for i in range(100):
        # Create retriever (should reuse singleton reranker)
        retriever = create_retriever(mode="balanced", enable_reranking=True)

        # Get reranker and do some work
        reranker = get_singleton_reranker()
        _ = reranker.rerank("đấu thầu", docs, top_k=2)

        if i % 10 == 0:
            mem = get_memory_usage_mb()
            gpu_mem = get_gpu_memory_usage_mb()
            memories.append(mem)
            gpu_memories.append(gpu_mem)
            print(f"  Iteration {i:3d}: RAM {mem:.1f} MB, GPU {gpu_mem:.1f} MB")

    final_mem = get_memory_usage_mb()
    final_gpu = get_gpu_memory_usage_mb()

    mem_increase = final_mem - baseline_mem
    gpu_increase = final_gpu - baseline_gpu

    print(f"\nFinal - RAM: {final_mem:.1f} MB, GPU: {final_gpu:.1f} MB")
    print(f"Increase - RAM: {mem_increase:.1f} MB, GPU: {gpu_increase:.1f} MB")

    # Memory increase should be minimal
    # First load tăng ~200-300MB (model + caches), sau đó stable
    # Chỉ check từ iteration 20 onwards để bỏ qua initial load
    mem_growth_after_warmup = memories[-1] - memories[2] if len(memories) > 2 else 0
    gpu_growth_after_warmup = (
        gpu_memories[-1] - gpu_memories[2] if len(gpu_memories) > 2 else 0
    )

    print(
        f"Growth after warmup (iter 20-100): RAM {mem_growth_after_warmup:.1f}MB, GPU {gpu_growth_after_warmup:.1f}MB"
    )

    # After warmup, memory should be stable (<20MB growth)
    if mem_growth_after_warmup < 20 and gpu_growth_after_warmup < 20:
        print(
            f"✅ PASS: Memory stable after warmup (RAM +{mem_growth_after_warmup:.1f}MB, GPU +{gpu_growth_after_warmup:.1f}MB)"
        )
        return True
    else:
        print(
            f"❌ FAIL: Memory leak detected! (RAM +{mem_growth_after_warmup:.1f}MB, GPU +{gpu_growth_after_warmup:.1f}MB)"
        )
        return False


def test_performance_consistency():
    """Test 3: Performance ổn định qua nhiều calls"""
    print("\n" + "=" * 60)
    print("TEST 3: Performance Consistency (50 reranks)")
    print("=" * 60)

    reset_singleton_reranker()

    docs = [
        Document(page_content=f"Document {i} về đấu thầu công khai.", metadata={})
        for i in range(10)
    ]

    reranker = get_singleton_reranker()

    # Warm up
    _ = reranker.rerank("đấu thầu", docs, top_k=5)

    latencies = []

    for i in range(50):
        start = time.time()
        _ = reranker.rerank("quy trình đấu thầu", docs, top_k=5)
        latency = (time.time() - start) * 1000  # ms
        latencies.append(latency)

    avg_latency = sum(latencies) / len(latencies)
    min_latency = min(latencies)
    max_latency = max(latencies)
    std_dev = (sum((x - avg_latency) ** 2 for x in latencies) / len(latencies)) ** 0.5

    print(f"Latency stats (ms):")
    print(f"  Average: {avg_latency:.2f}")
    print(f"  Min:     {min_latency:.2f}")
    print(f"  Max:     {max_latency:.2f}")
    print(f"  Std Dev: {std_dev:.2f}")

    # Performance should be consistent (std dev < 30% of mean)
    if std_dev < avg_latency * 0.3:
        print(
            f"✅ PASS: Performance consistent (std dev {std_dev/avg_latency*100:.1f}% of mean)"
        )
        return True
    else:
        print(
            f"❌ FAIL: Performance unstable (std dev {std_dev/avg_latency*100:.1f}% of mean)"
        )
        return False


def test_concurrent_requests():
    """Test 4: Concurrent requests không tạo multiple instances"""
    print("\n" + "=" * 60)
    print("TEST 4: Concurrent Request Handling")
    print("=" * 60)

    reset_singleton_reranker()

    import threading

    instances = []
    lock = threading.Lock()

    def worker():
        reranker = get_singleton_reranker()
        with lock:
            instances.append(id(reranker))

    # Create 10 threads
    threads = []
    for _ in range(10):
        t = threading.Thread(target=worker)
        threads.append(t)
        t.start()

    # Wait for all
    for t in threads:
        t.join()

    unique_ids = len(set(instances))

    print(f"Total threads: {len(instances)}")
    print(f"Unique instances: {unique_ids}")

    if unique_ids == 1:
        print("✅ PASS: All threads got same instance")
        return True
    else:
        print(f"❌ FAIL: Created {unique_ids} instances instead of 1!")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("🧪 SINGLETON PATTERN - PRODUCTION TESTS")
    print("=" * 60)
    print(
        f"Device: {'CUDA (' + torch.cuda.get_device_name(0) + ')' if torch.cuda.is_available() else 'CPU'}"
    )
    print(f"PyTorch version: {torch.__version__}")

    results = []

    try:
        results.append(("Singleton Reuse", test_singleton_reuse()))
        results.append(("Memory Stability", test_memory_stability()))
        results.append(("Performance Consistency", test_performance_consistency()))
        results.append(("Concurrent Requests", test_concurrent_requests()))
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    total = len(results)
    passed = sum(1 for _, p in results if p)

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Singleton pattern working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review implementation.")
        return 1


if __name__ == "__main__":
    exit(main())
