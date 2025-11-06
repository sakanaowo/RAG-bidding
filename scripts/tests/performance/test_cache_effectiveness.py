#!/usr/bin/env python3
"""
Test Cache Effectiveness
Đánh giá hiệu quả cache system (Redis + in-memory) của RAG system
"""

import time
import json
import statistics
from typing import List, Dict, Any, Tuple
import requests
from datetime import datetime
import sys
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Thêm src vào Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../.."))

# Test queries để đánh giá cache
CACHE_TEST_QUERIES = [
    # Repeated queries for cache testing
    "Quy trình đấu thầu rộng rãi là gì?",
    "Thời hạn nộp hồ sơ dự thầu theo quy định",
    "Các loại hình đấu thầu trong Luật đấu thầu",
    "Điều kiện tham gia đấu thầu của nhà thầu",
    "Hồ sơ mời thầu bao gồm những gì?",
    # Variations for partial cache hits
    "Quy trình đấu thầu rộng rãi",
    "Quy trình đấu thầu hạn chế",
    "Thời hạn nộp hồ sơ mời thầu",
    "Điều kiện tham gia đấu thầu",
    "Hồ sơ dự thầu bao gồm gì?",
]

API_BASE_URL = "http://localhost:8000"


class CacheEffectivenessTester:
    """Test cache effectiveness của RAG system"""

    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.results = {
            "test_start": datetime.now().isoformat(),
            "cache_tests": {},
            "summary": {},
        }

    def test_server_health(self) -> bool:
        """Kiểm tra server có hoạt động không"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Server không hoạt động: {e}")
            return False

    def clear_cache_if_possible(self) -> bool:
        """Cố gắng clear cache nếu có endpoint"""
        try:
            # Thử gọi cache clear endpoint (nếu có)
            response = requests.post(f"{self.base_url}/admin/clear-cache", timeout=5)
            return response.status_code == 200
        except:
            print("ℹ️  Không tìm thấy cache clear endpoint (bình thường)")
            return False

    def run_query_with_timing(
        self, question: str, mode: str = "balanced"
    ) -> Dict[str, Any]:
        """Chạy query và đo timing detail"""
        start_time = time.time()

        try:
            response = requests.post(
                f"{self.base_url}/ask",
                json={"question": question, "mode": mode},
                timeout=30,
            )

            total_time = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "total_time_ms": int(total_time * 1000),
                    "server_time_ms": data.get("processing_time_ms", 0),
                    "answer_length": len(data.get("answer", "")),
                    "sources_count": len(data.get("sources", [])),
                    "adaptive_retrieval": data.get("adaptive_retrieval", {}),
                    "response": data,
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "total_time_ms": int(total_time * 1000),
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "total_time_ms": int((time.time() - start_time) * 1000),
            }

    def test_cold_vs_warm_cache(self, query: str, warm_runs: int = 5) -> Dict[str, Any]:
        """Test performance difference between cold và warm cache"""
        print(f"🧊 Testing cold vs warm cache: {query[:50]}...")

        # Cold cache run (first time)
        cold_result = self.run_query_with_timing(query)

        if not cold_result["success"]:
            return {"error": f"Cold run failed: {cold_result['error']}"}

        # Warm cache runs (repeated)
        warm_results = []
        for i in range(warm_runs):
            warm_result = self.run_query_with_timing(query)
            if warm_result["success"]:
                warm_results.append(warm_result)

            # Small delay between runs
            time.sleep(0.2)

        if not warm_results:
            return {"error": "All warm runs failed"}

        # Analysis
        cold_time = cold_result["total_time_ms"]
        warm_times = [r["total_time_ms"] for r in warm_results]
        avg_warm_time = statistics.mean(warm_times)

        speedup = cold_time / avg_warm_time if avg_warm_time > 0 else 1
        cache_improvement_pct = ((cold_time - avg_warm_time) / cold_time) * 100

        result = {
            "query": query,
            "cold_run": {
                "time_ms": cold_time,
                "server_time_ms": cold_result["server_time_ms"],
            },
            "warm_runs": {
                "count": len(warm_results),
                "times_ms": warm_times,
                "avg_time_ms": avg_warm_time,
                "min_time_ms": min(warm_times),
                "max_time_ms": max(warm_times),
                "std_time_ms": (
                    statistics.stdev(warm_times) if len(warm_times) > 1 else 0
                ),
            },
            "cache_analysis": {
                "speedup_factor": speedup,
                "improvement_percent": cache_improvement_pct,
                "cache_effective": speedup
                > 1.2,  # Consider effective if >20% improvement
            },
        }

        print(f"   ❄️  Cold: {cold_time}ms")
        print(
            f"   🔥 Warm: {avg_warm_time:.0f}ms avg ({min(warm_times)}-{max(warm_times)}ms)"
        )
        print(f"   ⚡ Speedup: {speedup:.1f}x ({cache_improvement_pct:.1f}% faster)")

        return result

    def test_cache_hit_patterns(self) -> Dict[str, Any]:
        """Test cache hit patterns với different query variations"""
        print("\n🎯 Testing cache hit patterns...")

        patterns_results = {}

        # Group similar queries to test partial cache hits
        query_groups = [
            ["Quy trình đấu thầu rộng rãi là gì?", "Quy trình đấu thầu rộng rãi"],
            ["Thời hạn nộp hồ sơ dự thầu", "Thời hạn nộp hồ sơ mời thầu"],
            ["Điều kiện tham gia đấu thầu của nhà thầu", "Điều kiện tham gia đấu thầu"],
        ]

        for i, group in enumerate(query_groups):
            print(f"\n  Group {i+1}: Testing similar queries")
            group_results = []

            for query in group:
                result = self.test_cold_vs_warm_cache(query, warm_runs=3)
                if "error" not in result:
                    group_results.append(result)

            if group_results:
                patterns_results[f"group_{i+1}"] = {
                    "queries": group,
                    "results": group_results,
                    "analysis": self.analyze_group_cache_patterns(group_results),
                }

        return patterns_results

    def analyze_group_cache_patterns(self, group_results: List[Dict]) -> Dict[str, Any]:
        """Phân tích cache patterns trong một group queries"""
        if not group_results:
            return {}

        speedups = [r["cache_analysis"]["speedup_factor"] for r in group_results]
        improvements = [
            r["cache_analysis"]["improvement_percent"] for r in group_results
        ]

        return {
            "avg_speedup": statistics.mean(speedups),
            "avg_improvement_pct": statistics.mean(improvements),
            "cache_effective_count": sum(
                1 for r in group_results if r["cache_analysis"]["cache_effective"]
            ),
            "total_queries": len(group_results),
        }

    def test_concurrent_cache_access(
        self, num_threads: int = 5, queries_per_thread: int = 3
    ) -> Dict[str, Any]:
        """Test cache performance under concurrent access"""
        print(
            f"\n🔄 Testing concurrent cache access: {num_threads} threads, {queries_per_thread} queries each"
        )

        # Use a subset of queries for concurrent testing
        test_queries = CACHE_TEST_QUERIES[:5]

        def thread_worker(thread_id: int) -> List[Dict[str, Any]]:
            """Worker function for each thread"""
            thread_results = []
            for i in range(queries_per_thread):
                query = test_queries[i % len(test_queries)]
                result = self.run_query_with_timing(query)
                result["thread_id"] = thread_id
                result["query_index"] = i
                thread_results.append(result)
                time.sleep(0.1)  # Small delay between queries
            return thread_results

        # Run concurrent threads
        start_time = time.time()
        all_results = []

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = {executor.submit(thread_worker, i): i for i in range(num_threads)}

            for future in as_completed(futures):
                thread_id = futures[future]
                try:
                    thread_results = future.result()
                    all_results.extend(thread_results)
                    print(
                        f"   Thread {thread_id} completed: {len(thread_results)} queries"
                    )
                except Exception as e:
                    print(f"   Thread {thread_id} failed: {e}")

        total_time = time.time() - start_time

        # Analyze concurrent performance
        successful_results = [r for r in all_results if r.get("success")]
        failed_results = [r for r in all_results if not r.get("success")]

        if successful_results:
            response_times = [r["total_time_ms"] for r in successful_results]

            analysis = {
                "total_queries": len(all_results),
                "successful_queries": len(successful_results),
                "failed_queries": len(failed_results),
                "success_rate": len(successful_results) / len(all_results),
                "total_test_time_s": total_time,
                "queries_per_second": len(successful_results) / total_time,
                "response_times": {
                    "avg_ms": statistics.mean(response_times),
                    "median_ms": statistics.median(response_times),
                    "min_ms": min(response_times),
                    "max_ms": max(response_times),
                    "std_ms": (
                        statistics.stdev(response_times)
                        if len(response_times) > 1
                        else 0
                    ),
                },
                "concurrent_performance": {
                    "cache_contention_detected": max(response_times)
                    > 2 * statistics.median(response_times),
                    "performance_degradation_pct": 0,  # Would need baseline to calculate
                },
            }

            print(
                f"   📊 Success: {analysis['success_rate']:.1%} ({len(successful_results)}/{len(all_results)})"
            )
            print(f"   ⏱️  Avg response: {analysis['response_times']['avg_ms']:.0f}ms")
            print(f"   🚀 Throughput: {analysis['queries_per_second']:.1f} queries/sec")

            return analysis
        else:
            return {"error": "No successful queries in concurrent test"}

    def run_all_cache_tests(self) -> Dict[str, Any]:
        """Chạy tất cả cache tests"""
        if not self.test_server_health():
            return {"error": "Server không hoạt động"}

        print("🗄️ Bắt đầu Cache Effectiveness Test")
        print(f"📝 Test queries: {len(CACHE_TEST_QUERIES)}")

        # Test 1: Cold vs Warm cache for individual queries
        print("\n" + "=" * 60)
        print("🧊 TEST 1: Cold vs Warm Cache Performance")
        print("=" * 60)

        individual_tests = {}
        for i, query in enumerate(CACHE_TEST_QUERIES[:7]):  # Test first 7 queries
            result = self.test_cold_vs_warm_cache(query, warm_runs=4)
            if "error" not in result:
                individual_tests[f"query_{i+1}"] = result

        self.results["cache_tests"]["individual_tests"] = individual_tests

        # Test 2: Cache hit patterns
        print("\n" + "=" * 60)
        print("🎯 TEST 2: Cache Hit Patterns")
        print("=" * 60)

        pattern_tests = self.test_cache_hit_patterns()
        self.results["cache_tests"]["pattern_tests"] = pattern_tests

        # Test 3: Concurrent cache access
        print("\n" + "=" * 60)
        print("🔄 TEST 3: Concurrent Cache Access")
        print("=" * 60)

        concurrent_test = self.test_concurrent_cache_access(
            num_threads=4, queries_per_thread=3
        )
        self.results["cache_tests"]["concurrent_test"] = concurrent_test

        # Generate summary
        self.generate_cache_summary()

        return self.results

    def generate_cache_summary(self):
        """Tạo summary cho cache test results"""
        individual_tests = self.results["cache_tests"].get("individual_tests", {})
        pattern_tests = self.results["cache_tests"].get("pattern_tests", {})
        concurrent_test = self.results["cache_tests"].get("concurrent_test", {})

        summary = {
            "total_tests": len(individual_tests),
            "cache_effectiveness": {},
            "performance_metrics": {},
            "recommendations": [],
        }

        if individual_tests:
            # Calculate overall cache effectiveness
            speedups = []
            improvements = []
            effective_count = 0

            for test in individual_tests.values():
                if "cache_analysis" in test:
                    speedups.append(test["cache_analysis"]["speedup_factor"])
                    improvements.append(test["cache_analysis"]["improvement_percent"])
                    if test["cache_analysis"]["cache_effective"]:
                        effective_count += 1

            if speedups:
                summary["cache_effectiveness"] = {
                    "avg_speedup": statistics.mean(speedups),
                    "avg_improvement_pct": statistics.mean(improvements),
                    "effective_rate": effective_count / len(speedups),
                    "best_speedup": max(speedups),
                    "worst_speedup": min(speedups),
                }

        if concurrent_test and "error" not in concurrent_test:
            summary["performance_metrics"] = {
                "concurrent_success_rate": concurrent_test["success_rate"],
                "queries_per_second": concurrent_test["queries_per_second"],
                "avg_response_time_ms": concurrent_test["response_times"]["avg_ms"],
            }

        # Generate recommendations
        recommendations = []

        cache_eff = summary.get("cache_effectiveness", {})
        if cache_eff.get("avg_speedup", 0) < 1.5:
            recommendations.append(
                "Cache effectiveness below optimal. Consider tuning cache TTL or size."
            )
        if cache_eff.get("effective_rate", 0) < 0.7:
            recommendations.append(
                "Low cache hit rate. Review caching strategy and query patterns."
            )

        perf_metrics = summary.get("performance_metrics", {})
        if perf_metrics.get("concurrent_success_rate", 1) < 0.9:
            recommendations.append(
                "High failure rate under concurrent load. Check connection pooling."
            )
        if perf_metrics.get("queries_per_second", 0) < 5:
            recommendations.append(
                "Low throughput detected. Consider optimizing database connections."
            )

        summary["recommendations"] = recommendations
        self.results["summary"] = summary

    def print_summary(self):
        """In cache test summary"""
        print("\n" + "=" * 80)
        print("🗄️ CACHE EFFECTIVENESS TEST SUMMARY")
        print("=" * 80)

        summary = self.results.get("summary", {})
        cache_eff = summary.get("cache_effectiveness", {})
        perf_metrics = summary.get("performance_metrics", {})

        if cache_eff:
            print("📊 CACHE EFFECTIVENESS:")
            print(f"   Average Speedup: {cache_eff['avg_speedup']:.1f}x")
            print(f"   Average Improvement: {cache_eff['avg_improvement_pct']:.1f}%")
            print(f"   Effective Rate: {cache_eff['effective_rate']:.1%}")
            print(f"   Best Speedup: {cache_eff['best_speedup']:.1f}x")

        if perf_metrics:
            print("\n⚡ PERFORMANCE METRICS:")
            print(
                f"   Concurrent Success Rate: {perf_metrics['concurrent_success_rate']:.1%}"
            )
            print(
                f"   Throughput: {perf_metrics['queries_per_second']:.1f} queries/sec"
            )
            print(f"   Avg Response Time: {perf_metrics['avg_response_time_ms']:.0f}ms")

        recommendations = summary.get("recommendations", [])
        if recommendations:
            print("\n💡 RECOMMENDATIONS:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
        else:
            print("\n✅ Cache system performing well!")

    def save_results(self, filename: str = None):
        """Lưu kết quả vào file JSON"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"logs/cache_effectiveness_test_{timestamp}.json"

        os.makedirs(os.path.dirname(filename), exist_ok=True)

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Kết quả đã lưu: {filename}")


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="Test Cache Effectiveness")
    parser.add_argument(
        "--url",
        default=API_BASE_URL,
        help="API base URL (default: http://localhost:8000)",
    )
    parser.add_argument("--output", help="Output JSON file path")
    parser.add_argument(
        "--threads",
        type=int,
        default=4,
        help="Number of concurrent threads (default: 4)",
    )

    args = parser.parse_args()

    tester = CacheEffectivenessTester(args.url)
    results = tester.run_all_cache_tests()

    if "error" not in results:
        tester.print_summary()
        tester.save_results(args.output)
    else:
        print(f"❌ Test failed: {results['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
