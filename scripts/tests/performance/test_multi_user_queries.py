#!/usr/bin/env python3
"""
Multi-User Query Load Test
Mô phỏng multiple concurrent users để test scalability và performance under load
"""

import time
import asyncio
import aiohttp
import json
import statistics
import random
from typing import List, Dict, Any, Tuple
from datetime import datetime
import sys
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Thêm src vào Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../.."))

# Realistic user query scenarios
USER_SCENARIOS = {
    "legal_researcher": [
        "Quy trình đấu thầu rộng rãi theo Luật đấu thầu 2023",
        "Các trường hợp được áp dụng chỉ định thầu",
        "Quy định về thẩm định kết quả lựa chọn nhà thầu",
        "Xử lý vi phạm trong hoạt động đấu thầu",
        "Trách nhiệm của chủ đầu tư trong quá trình đấu thầu",
    ],
    "bidding_consultant": [
        "Hồ sơ mời thầu cần chuẩn bị những gì?",
        "Tiêu chí đánh giá hồ sơ dự thầu",
        "Quy trình mở thầu và công bố kết quả",
        "Điều kiện tham gia đấu thầu của nhà thầu",
        "Thời hạn và địa điểm nộp hồ sơ dự thầu",
    ],
    "government_officer": [
        "Quy định về đấu thầu qua mạng",
        "Phân loại nhà thầu theo năng lực",
        "Giám sát và kiểm tra hoạt động đấu thầu",
        "Báo cáo tình hình thực hiện đấu thầu",
        "Xử lý khiếu nại trong đấu thầu",
    ],
    "contractor": [
        "Điều kiện năng lực để tham gia đấu thầu",
        "Hồ sơ dự thầu cần có những tài liệu gì?",
        "Quy trình nộp và sửa đổi hồ sơ dự thầu",
        "Quyền và nghĩa vụ của nhà thầu",
        "Bảo đảm dự thầu là gì và cách thực hiện",
    ],
    "quick_lookup": [
        "đấu thầu rộng rãi",
        "hồ sơ mời thầu",
        "nhà thầu",
        "chỉ định thầu",
        "bảo đảm dự thầu",
    ],
}

API_BASE_URL = "http://localhost:8000"


class MultiUserTester:
    """Simulates multiple concurrent users querying the RAG system"""

    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.results = {
            "test_start": datetime.now().isoformat(),
            "test_config": {},
            "load_tests": {},
            "summary": {},
        }

    def test_server_health(self) -> bool:
        """Kiểm tra server có hoạt động không"""
        try:
            import requests

            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Server không hoạt động: {e}")
            return False

    async def single_user_session(
        self,
        session: aiohttp.ClientSession,
        user_type: str,
        session_id: int,
        queries_per_user: int,
        delay_range: Tuple[float, float],
    ) -> Dict[str, Any]:
        """Mô phỏng một user session với multiple queries"""
        user_queries = USER_SCENARIOS.get(user_type, USER_SCENARIOS["quick_lookup"])
        session_results = []

        for i in range(queries_per_user):
            # Random query từ user type
            query = random.choice(user_queries)
            mode = random.choice(["fast", "balanced", "quality"])

            start_time = time.time()

            try:
                async with session.post(
                    f"{self.base_url}/ask",
                    json={"question": query, "mode": mode},
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:

                    total_time = time.time() - start_time

                    if response.status == 200:
                        data = await response.json()
                        result = {
                            "success": True,
                            "query": query,
                            "mode": mode,
                            "query_index": i,
                            "total_time_ms": int(total_time * 1000),
                            "server_time_ms": data.get("processing_time_ms", 0),
                            "answer_length": len(data.get("answer", "")),
                            "sources_count": len(data.get("sources", [])),
                            "timestamp": datetime.now().isoformat(),
                        }
                    else:
                        result = {
                            "success": False,
                            "query": query,
                            "mode": mode,
                            "query_index": i,
                            "error": f"HTTP {response.status}",
                            "total_time_ms": int(total_time * 1000),
                            "timestamp": datetime.now().isoformat(),
                        }

            except Exception as e:
                result = {
                    "success": False,
                    "query": query,
                    "mode": mode,
                    "query_index": i,
                    "error": str(e),
                    "total_time_ms": int((time.time() - start_time) * 1000),
                    "timestamp": datetime.now().isoformat(),
                }

            session_results.append(result)

            # Random delay between queries (simulate user thinking time)
            if i < queries_per_user - 1:
                delay = random.uniform(delay_range[0], delay_range[1])
                await asyncio.sleep(delay)

        # Session summary
        successful_queries = [r for r in session_results if r["success"]]
        failed_queries = [r for r in session_results if not r["success"]]

        session_summary = {
            "user_type": user_type,
            "session_id": session_id,
            "total_queries": len(session_results),
            "successful_queries": len(successful_queries),
            "failed_queries": len(failed_queries),
            "success_rate": (
                len(successful_queries) / len(session_results) if session_results else 0
            ),
            "queries": session_results,
        }

        if successful_queries:
            response_times = [r["total_time_ms"] for r in successful_queries]
            session_summary.update(
                {
                    "avg_response_time_ms": statistics.mean(response_times),
                    "median_response_time_ms": statistics.median(response_times),
                    "min_response_time_ms": min(response_times),
                    "max_response_time_ms": max(response_times),
                }
            )

        return session_summary

    async def concurrent_load_test(
        self,
        num_users: int,
        queries_per_user: int,
        user_distribution: Dict[str, float] = None,
        delay_range: Tuple[float, float] = (1.0, 3.0),
    ) -> Dict[str, Any]:
        """Chạy concurrent load test với multiple user types"""

        if user_distribution is None:
            # Default distribution
            user_distribution = {
                "legal_researcher": 0.3,
                "bidding_consultant": 0.25,
                "government_officer": 0.2,
                "contractor": 0.15,
                "quick_lookup": 0.1,
            }

        print(
            f"🚀 Starting load test: {num_users} users, {queries_per_user} queries each"
        )
        print(f"📊 User distribution: {user_distribution}")
        print(f"⏱️  Delay range: {delay_range[0]:.1f}s - {delay_range[1]:.1f}s")

        # Assign user types based on distribution
        user_assignments = []
        for user_type, ratio in user_distribution.items():
            count = int(num_users * ratio)
            user_assignments.extend([user_type] * count)

        # Fill remaining slots with random types
        while len(user_assignments) < num_users:
            user_assignments.append(random.choice(list(user_distribution.keys())))

        random.shuffle(user_assignments)

        start_time = time.time()

        # Create concurrent sessions
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i, user_type in enumerate(user_assignments):
                task = self.single_user_session(
                    session, user_type, i, queries_per_user, delay_range
                )
                tasks.append(task)

            # Run all sessions concurrently
            print(f"⚡ Launching {len(tasks)} concurrent user sessions...")
            session_results = await asyncio.gather(*tasks, return_exceptions=True)

        total_time = time.time() - start_time

        # Process results
        successful_sessions = []
        failed_sessions = []

        for i, result in enumerate(session_results):
            if isinstance(result, Exception):
                failed_sessions.append({"session_id": i, "error": str(result)})
            else:
                successful_sessions.append(result)

        return self.analyze_load_test_results(
            successful_sessions,
            failed_sessions,
            total_time,
            {
                "num_users": num_users,
                "queries_per_user": queries_per_user,
                "user_distribution": user_distribution,
                "delay_range": delay_range,
            },
        )

    def analyze_load_test_results(
        self,
        successful_sessions: List[Dict],
        failed_sessions: List[Dict],
        total_time: float,
        test_config: Dict,
    ) -> Dict[str, Any]:
        """Phân tích kết quả load test"""

        if not successful_sessions:
            return {
                "error": "No successful sessions",
                "failed_sessions": len(failed_sessions),
                "test_config": test_config,
            }

        # Aggregate all queries from all sessions
        all_queries = []
        for session in successful_sessions:
            all_queries.extend(session["queries"])

        successful_queries = [q for q in all_queries if q["success"]]
        failed_queries = [q for q in all_queries if not q["success"]]

        # Response time analysis
        response_times = [q["total_time_ms"] for q in successful_queries]

        # Session analysis
        session_success_rates = [s["success_rate"] for s in successful_sessions]
        session_avg_times = [
            s.get("avg_response_time_ms", 0)
            for s in successful_sessions
            if s.get("avg_response_time_ms")
        ]

        # User type analysis
        user_type_stats = {}
        for session in successful_sessions:
            user_type = session["user_type"]
            if user_type not in user_type_stats:
                user_type_stats[user_type] = {
                    "sessions": 0,
                    "total_queries": 0,
                    "successful_queries": 0,
                    "response_times": [],
                }

            stats = user_type_stats[user_type]
            stats["sessions"] += 1
            stats["total_queries"] += session["total_queries"]
            stats["successful_queries"] += session["successful_queries"]

            # Add response times from this session
            for query in session["queries"]:
                if query["success"]:
                    stats["response_times"].append(query["total_time_ms"])

        # Calculate user type averages
        for user_type, stats in user_type_stats.items():
            if stats["response_times"]:
                stats["avg_response_time_ms"] = statistics.mean(stats["response_times"])
                stats["success_rate"] = (
                    stats["successful_queries"] / stats["total_queries"]
                )

        analysis = {
            "test_config": test_config,
            "overall_metrics": {
                "total_time_s": total_time,
                "total_sessions": len(successful_sessions) + len(failed_sessions),
                "successful_sessions": len(successful_sessions),
                "failed_sessions": len(failed_sessions),
                "session_success_rate": len(successful_sessions)
                / (len(successful_sessions) + len(failed_sessions)),
                "total_queries": len(all_queries),
                "successful_queries": len(successful_queries),
                "failed_queries": len(failed_queries),
                "query_success_rate": (
                    len(successful_queries) / len(all_queries) if all_queries else 0
                ),
                "queries_per_second": len(successful_queries) / total_time,
                "concurrent_users": test_config["num_users"],
            },
            "response_time_metrics": {
                "avg_ms": statistics.mean(response_times) if response_times else 0,
                "median_ms": statistics.median(response_times) if response_times else 0,
                "min_ms": min(response_times) if response_times else 0,
                "max_ms": max(response_times) if response_times else 0,
                "std_ms": (
                    statistics.stdev(response_times) if len(response_times) > 1 else 0
                ),
                "percentile_95_ms": (
                    self.percentile(response_times, 0.95) if response_times else 0
                ),
                "percentile_99_ms": (
                    self.percentile(response_times, 0.99) if response_times else 0
                ),
            },
            "session_metrics": {
                "avg_session_success_rate": (
                    statistics.mean(session_success_rates)
                    if session_success_rates
                    else 0
                ),
                "avg_session_response_time_ms": (
                    statistics.mean(session_avg_times) if session_avg_times else 0
                ),
            },
            "user_type_breakdown": user_type_stats,
            "performance_indicators": {
                "system_stable": len(failed_sessions) == 0,
                "acceptable_response_time": (
                    statistics.mean(response_times) < 5000 if response_times else False
                ),  # <5s
                "high_throughput": (len(successful_queries) / total_time)
                > 1,  # >1 query/sec
                "low_error_rate": (
                    (len(failed_queries) / len(all_queries)) < 0.05
                    if all_queries
                    else True
                ),  # <5% error
            },
        }

        return analysis

    def percentile(self, data: List[float], p: float) -> float:
        """Calculate percentile"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(p * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]

    async def run_escalating_load_test(
        self, max_users: int = 20, step_size: int = 5, queries_per_user: int = 3
    ) -> Dict[str, Any]:
        """Chạy escalating load test để tìm breaking point"""
        print(
            f"📈 Running escalating load test: 1 -> {max_users} users (step: {step_size})"
        )

        escalating_results = {}

        for num_users in range(step_size, max_users + 1, step_size):
            print(f"\n🎯 Testing with {num_users} concurrent users...")

            result = await self.concurrent_load_test(
                num_users=num_users,
                queries_per_user=queries_per_user,
                delay_range=(0.5, 1.5),  # Shorter delays for load testing
            )

            escalating_results[f"users_{num_users}"] = result

            # Print quick summary
            if "error" not in result:
                metrics = result["overall_metrics"]
                perf = result["performance_indicators"]
                print(f"   ✅ Success rate: {metrics['query_success_rate']:.1%}")
                print(
                    f"   ⚡ Throughput: {metrics['queries_per_second']:.1f} queries/sec"
                )
                print(
                    f"   ⏱️  Avg response: {result['response_time_metrics']['avg_ms']:.0f}ms"
                )
                print(f"   🎯 System stable: {perf['system_stable']}")

                # Break if system becomes unstable
                if not perf["system_stable"] or not perf["acceptable_response_time"]:
                    print(f"⚠️  System performance degraded at {num_users} users")
                    break
            else:
                print(f"   ❌ Test failed: {result['error']}")
                break

            # Short break between load levels
            await asyncio.sleep(2)

        return {
            "escalating_test": escalating_results,
            "breaking_point_analysis": self.analyze_breaking_point(escalating_results),
        }

    def analyze_breaking_point(
        self, escalating_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Phân tích breaking point từ escalating test"""
        breaking_point = None
        max_stable_users = 0
        performance_degradation = []

        for test_key, result in escalating_results.items():
            if "error" in result:
                continue

            num_users = int(test_key.split("_")[1])
            perf = result["performance_indicators"]
            metrics = result["overall_metrics"]

            performance_degradation.append(
                {
                    "num_users": num_users,
                    "query_success_rate": metrics["query_success_rate"],
                    "avg_response_time_ms": result["response_time_metrics"]["avg_ms"],
                    "queries_per_second": metrics["queries_per_second"],
                    "system_stable": perf["system_stable"],
                }
            )

            if perf["system_stable"] and perf["acceptable_response_time"]:
                max_stable_users = num_users
            elif breaking_point is None:
                breaking_point = num_users

        return {
            "max_stable_concurrent_users": max_stable_users,
            "breaking_point_users": breaking_point,
            "performance_degradation": performance_degradation,
            "recommendations": self.generate_load_recommendations(
                performance_degradation
            ),
        }

    def generate_load_recommendations(self, performance_data: List[Dict]) -> List[str]:
        """Generate recommendations based on load test results"""
        recommendations = []

        if not performance_data:
            return ["No performance data available for analysis"]

        # Analyze trends
        latest = performance_data[-1]

        if latest["query_success_rate"] < 0.9:
            recommendations.append(
                "High error rate detected. Check database connection limits and error handling."
            )

        if latest["avg_response_time_ms"] > 3000:
            recommendations.append(
                "High response times. Consider implementing connection pooling and query optimization."
            )

        if latest["queries_per_second"] < 2:
            recommendations.append(
                "Low throughput. Database connection pooling recommended."
            )

        # Check for degradation trends
        if len(performance_data) > 1:
            response_time_trend = (
                performance_data[-1]["avg_response_time_ms"]
                / performance_data[0]["avg_response_time_ms"]
            )
            if response_time_trend > 2:
                recommendations.append(
                    f"Response time increased {response_time_trend:.1f}x under load. Scaling improvements needed."
                )

        if not recommendations:
            recommendations.append("System performing well under tested load levels.")

        return recommendations

    def print_summary(self, results: Dict[str, Any]):
        """Print comprehensive test summary"""
        print("\n" + "=" * 80)
        print("👥 MULTI-USER LOAD TEST SUMMARY")
        print("=" * 80)

        if "escalating_test" in results:
            escalating = results["escalating_test"]
            breaking_point = results["breaking_point_analysis"]

            print("📈 ESCALATING LOAD TEST RESULTS:")
            print(
                f"   Max Stable Users: {breaking_point['max_stable_concurrent_users']}"
            )
            if breaking_point["breaking_point_users"]:
                print(
                    f"   Breaking Point: {breaking_point['breaking_point_users']} users"
                )
            else:
                print("   Breaking Point: Not reached in test range")

            # Show performance at different load levels
            print(f"\n📊 PERFORMANCE AT DIFFERENT LOAD LEVELS:")
            print(
                f"{'Users':<8} {'Success Rate':<12} {'Avg Response':<12} {'Throughput':<12} {'Stable':<8}"
            )
            print("-" * 60)

            for perf in breaking_point["performance_degradation"]:
                print(
                    f"{perf['num_users']:<8} "
                    f"{perf['query_success_rate']:<11.1%} "
                    f"{perf['avg_response_time_ms']:<11.0f}ms "
                    f"{perf['queries_per_second']:<11.1f}/s "
                    f"{'✅' if perf['system_stable'] else '❌':<8}"
                )

            recommendations = breaking_point.get("recommendations", [])
            if recommendations:
                print(f"\n💡 RECOMMENDATIONS:")
                for i, rec in enumerate(recommendations, 1):
                    print(f"   {i}. {rec}")

        elif "load_tests" in results:
            # Single load test results
            for test_name, test_result in results["load_tests"].items():
                if "error" not in test_result:
                    metrics = test_result["overall_metrics"]
                    response = test_result["response_time_metrics"]

                    print(f"\n📊 {test_name.upper()} RESULTS:")
                    print(f"   Concurrent Users: {metrics['concurrent_users']}")
                    print(f"   Total Queries: {metrics['total_queries']}")
                    print(f"   Success Rate: {metrics['query_success_rate']:.1%}")
                    print(
                        f"   Throughput: {metrics['queries_per_second']:.1f} queries/sec"
                    )
                    print(f"   Avg Response: {response['avg_ms']:.0f}ms")
                    print(f"   95th Percentile: {response['percentile_95_ms']:.0f}ms")

    def save_results(self, filename: str = None):
        """Lưu kết quả vào file JSON"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"logs/multi_user_load_test_{timestamp}.json"

        os.makedirs(os.path.dirname(filename), exist_ok=True)

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Kết quả đã lưu: {filename}")


async def main():
    """Main async function"""
    import argparse

    parser = argparse.ArgumentParser(description="Multi-User Load Test for RAG System")
    parser.add_argument(
        "--url",
        default=API_BASE_URL,
        help="API base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--users", type=int, default=10, help="Number of concurrent users (default: 10)"
    )
    parser.add_argument(
        "--queries", type=int, default=3, help="Queries per user (default: 3)"
    )
    parser.add_argument(
        "--escalating", action="store_true", help="Run escalating load test"
    )
    parser.add_argument(
        "--max-users",
        type=int,
        default=20,
        help="Max users for escalating test (default: 20)",
    )
    parser.add_argument("--output", help="Output JSON file path")

    args = parser.parse_args()

    tester = MultiUserTester(args.url)

    if not tester.test_server_health():
        print("❌ Server not available")
        sys.exit(1)

    if args.escalating:
        print("🚀 Running Escalating Load Test")
        results = await tester.run_escalating_load_test(
            max_users=args.max_users, queries_per_user=args.queries
        )
        tester.results.update(results)
    else:
        print("🚀 Running Single Load Test")
        result = await tester.concurrent_load_test(
            num_users=args.users, queries_per_user=args.queries
        )
        tester.results["load_tests"] = {"main_test": result}

    tester.print_summary(tester.results)
    tester.save_results(args.output)


if __name__ == "__main__":
    asyncio.run(main())
