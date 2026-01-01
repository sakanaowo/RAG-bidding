#!/usr/bin/env python3
"""
Test Query Latency cho các RAG modes
Đánh giá performance của fast, balanced, quality, adaptive modes
"""

import time
import asyncio
import statistics
import json
from typing import List, Dict, Any
import requests
from datetime import datetime
import sys
import os

# Thêm src vào Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../.."))

# Test queries cho các domain khác nhau
TEST_QUERIES = [
    # Legal queries
    "Quy trình đấu thầu rộng rãi là gì?",
    "Thời hạn nộp hồ sơ dự thầu theo quy định",
    "Các loại hình đấu thầu trong Luật đấu thầu",
    "Điều kiện tham gia đấu thầu của nhà thầu",
    "Quy định về thẩm định kết quả lựa chọn nhà thầu",
    # Bidding queries
    "Hồ sơ mời thầu bao gồm những gì?",
    "Tiêu chí đánh giá hồ sơ dự thầu",
    "Quy trình mở thầu và đánh giá hồ sơ",
    "Trách nhiệm của chủ đầu tư trong đấu thầu",
    "Xử lý vi phạm trong hoạt động đấu thầu",
    # Short queries
    "đấu thầu",
    "nhà thầu",
    "hồ sơ dự thầu",
    # Complex queries
    "So sánh quy trình đấu thầu rộng rãi và đấu thầu hạn chế theo Luật đấu thầu 2023",
    "Trường hợp nào được áp dụng chỉ định thầu và quy trình thực hiện như thế nào?",
]

RAG_MODES = ["fast", "balanced", "quality", "adaptive"]
API_BASE_URL = "http://localhost:8000"


class QueryLatencyTester:
    """Test query latency cho các RAG modes"""

    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.results = {
            "test_start": datetime.now().isoformat(),
            "modes": {},
            "queries": TEST_QUERIES,
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

    def run_single_query(self, question: str, mode: str) -> Dict[str, Any]:
        """Chạy một query và đo thời gian"""
        start_time = time.time()

        try:
            response = requests.post(
                f"{self.base_url}/ask",
                json={"question": question, "mode": mode},
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                processing_time = time.time() - start_time

                return {
                    "success": True,
                    "response_time_ms": int(processing_time * 1000),
                    "server_processing_ms": data.get("processing_time_ms", 0),
                    "answer_length": len(data.get("answer", "")),
                    "sources_count": len(data.get("sources", [])),
                    "enhanced_features": data.get("enhanced_features", []),
                    "adaptive_retrieval": data.get("adaptive_retrieval", {}),
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "response_time_ms": int((time.time() - start_time) * 1000),
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_time_ms": int((time.time() - start_time) * 1000),
            }

    def test_mode_performance(self, mode: str, num_runs: int = 3) -> Dict[str, Any]:
        """Test performance của một mode với tất cả queries"""
        print(f"\n🔍 Testing mode: {mode.upper()}")
        mode_results = {"mode": mode, "queries": {}, "statistics": {}}

        all_response_times = []
        all_server_times = []
        successful_queries = 0

        for i, query in enumerate(TEST_QUERIES):
            print(f"  Query {i+1:2d}: {query[:50]}{'...' if len(query) > 50 else ''}")

            query_times = []
            server_times = []

            # Chạy mỗi query nhiều lần để có kết quả ổn định
            for run in range(num_runs):
                result = self.run_single_query(query, mode)
                if result["success"]:
                    query_times.append(result["response_time_ms"])
                    server_times.append(result.get("server_processing_ms", 0))
                    successful_queries += 1

                # Delay nhỏ giữa các lần chạy
                time.sleep(0.5)

            if query_times:
                avg_time = statistics.mean(query_times)
                avg_server_time = statistics.mean(server_times)
                print(
                    f"           Avg: {avg_time:.0f}ms (server: {avg_server_time:.0f}ms)"
                )

                mode_results["queries"][query] = {
                    "response_times": query_times,
                    "server_times": server_times,
                    "avg_response_time": avg_time,
                    "avg_server_time": avg_server_time,
                    "success_rate": len(query_times) / num_runs,
                }

                all_response_times.extend(query_times)
                all_server_times.extend(server_times)
            else:
                print(f"           ❌ Failed all attempts")
                mode_results["queries"][query] = {
                    "success_rate": 0,
                    "error": "All attempts failed",
                }

        # Tính thống kê tổng quan
        if all_response_times:
            mode_results["statistics"] = {
                "total_queries": len(TEST_QUERIES),
                "successful_queries": successful_queries,
                "success_rate": successful_queries / (len(TEST_QUERIES) * num_runs),
                "avg_response_time": statistics.mean(all_response_times),
                "median_response_time": statistics.median(all_response_times),
                "min_response_time": min(all_response_times),
                "max_response_time": max(all_response_times),
                "std_response_time": (
                    statistics.stdev(all_response_times)
                    if len(all_response_times) > 1
                    else 0
                ),
                "avg_server_time": statistics.mean(all_server_times),
                "median_server_time": statistics.median(all_server_times),
            }

            stats = mode_results["statistics"]
            print(
                f"  📊 Stats: {stats['avg_response_time']:.0f}ms avg, "
                f"{stats['median_response_time']:.0f}ms median, "
                f"{stats['success_rate']:.1%} success"
            )

        return mode_results

    def run_all_tests(self, num_runs: int = 3) -> Dict[str, Any]:
        """Chạy test cho tất cả modes"""
        if not self.test_server_health():
            return {"error": "Server không hoạt động"}

        print("🚀 Bắt đầu Query Latency Test")
        print(f"📝 Số queries: {len(TEST_QUERIES)}")
        print(f"🔄 Số lần chạy mỗi query: {num_runs}")
        print(f"📊 Tổng requests: {len(TEST_QUERIES) * len(RAG_MODES) * num_runs}")

        for mode in RAG_MODES:
            mode_result = self.test_mode_performance(mode, num_runs)
            self.results["modes"][mode] = mode_result

        # So sánh performance giữa các modes
        self.generate_comparison()

        return self.results

    def generate_comparison(self):
        """Tạo bảng so sánh performance giữa các modes"""
        comparison = {}

        for mode, data in self.results["modes"].items():
            if "statistics" in data and data["statistics"]:
                stats = data["statistics"]
                comparison[mode] = {
                    "avg_response_time": stats["avg_response_time"],
                    "median_response_time": stats["median_response_time"],
                    "success_rate": stats["success_rate"],
                    "std_response_time": stats["std_response_time"],
                }

        self.results["summary"]["comparison"] = comparison

        # Xếp hạng modes theo performance
        if comparison:
            # Fastest by average time
            fastest_mode = min(
                comparison.keys(), key=lambda x: comparison[x]["avg_response_time"]
            )

            # Most reliable by success rate
            most_reliable = max(
                comparison.keys(), key=lambda x: comparison[x]["success_rate"]
            )

            # Most consistent (lowest std dev)
            most_consistent = min(
                comparison.keys(), key=lambda x: comparison[x]["std_response_time"]
            )

            self.results["summary"]["rankings"] = {
                "fastest": fastest_mode,
                "most_reliable": most_reliable,
                "most_consistent": most_consistent,
            }

    def print_summary(self):
        """In summary kết quả"""
        print("\n" + "=" * 80)
        print("📊 QUERY LATENCY TEST SUMMARY")
        print("=" * 80)

        comparison = self.results["summary"].get("comparison", {})
        if not comparison:
            print("❌ Không có dữ liệu để so sánh")
            return

        print(
            f"{'Mode':<12} {'Avg Time':<10} {'Median':<8} {'Success':<8} {'Std Dev':<8}"
        )
        print("-" * 60)

        for mode, stats in comparison.items():
            print(
                f"{mode:<12} {stats['avg_response_time']:>8.0f}ms "
                f"{stats['median_response_time']:>6.0f}ms "
                f"{stats['success_rate']:>6.1%} "
                f"{stats['std_response_time']:>6.0f}ms"
            )

        rankings = self.results["summary"].get("rankings", {})
        if rankings:
            print(f"\n🏆 RANKINGS:")
            print(f"   ⚡ Fastest: {rankings['fastest']}")
            print(f"   🎯 Most Reliable: {rankings['most_reliable']}")
            print(f"   📏 Most Consistent: {rankings['most_consistent']}")

    def save_results(self, filename: str = None):
        """Lưu kết quả vào file JSON"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"logs/query_latency_test_{timestamp}.json"

        os.makedirs(os.path.dirname(filename), exist_ok=True)

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Kết quả đã lưu: {filename}")


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="Test Query Latency for RAG modes")
    parser.add_argument(
        "--runs", type=int, default=3, help="Number of runs per query (default: 3)"
    )
    parser.add_argument(
        "--url",
        default=API_BASE_URL,
        help="API base URL (default: http://localhost:8000)",
    )
    parser.add_argument("--output", help="Output JSON file path")

    args = parser.parse_args()

    tester = QueryLatencyTester(args.url)
    results = tester.run_all_tests(args.runs)

    if "error" not in results:
        tester.print_summary()
        tester.save_results(args.output)
    else:
        print(f"❌ Test failed: {results['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
