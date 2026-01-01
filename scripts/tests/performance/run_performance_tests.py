#!/usr/bin/env python3
"""
Performance Test Suite Runner
Chạy tất cả performance tests cho RAG system và generate comprehensive report
"""

import asyncio
import subprocess
import sys
import os
import json
import time
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path

# Test script paths
SCRIPT_DIR = Path(__file__).parent
TEST_SCRIPTS = {
    "query_latency": SCRIPT_DIR / "test_query_latency.py",
    "cache_effectiveness": SCRIPT_DIR / "test_cache_effectiveness.py",
    "multi_user_load": SCRIPT_DIR / "test_multi_user_queries.py",
}


class PerformanceTestRunner:
    """Orchestrates all performance tests and generates unified report"""

    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.test_results = {
            "test_suite_start": datetime.now().isoformat(),
            "api_url": api_url,
            "tests": {},
            "summary": {},
            "recommendations": [],
        }

    def check_server_health(self) -> bool:
        """Kiểm tra server có hoạt động không"""
        try:
            import requests

            response = requests.get(f"{self.api_url}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Server không hoạt động: {e}")
            return False

    def run_query_latency_test(self, runs: int = 3) -> Dict[str, Any]:
        """Run query latency test"""
        print("\n🔍 RUNNING QUERY LATENCY TEST")
        print("=" * 60)

        cmd = [
            sys.executable,
            str(TEST_SCRIPTS["query_latency"]),
            "--runs",
            str(runs),
            "--url",
            self.api_url,
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            if result.returncode == 0:
                print("✅ Query latency test completed successfully")

                # Try to find và read the generated JSON file
                output_lines = result.stdout.split("\n")
                json_file = None
                for line in output_lines:
                    if "Kết quả đã lưu:" in line:
                        json_file = line.split(": ")[-1].strip()
                        break

                if json_file and os.path.exists(json_file):
                    with open(json_file, "r", encoding="utf-8") as f:
                        return json.load(f)
                else:
                    return {"status": "completed", "output": result.stdout}
            else:
                print(f"❌ Query latency test failed: {result.stderr}")
                return {"status": "failed", "error": result.stderr}

        except subprocess.TimeoutExpired:
            return {"status": "failed", "error": "Test timeout after 10 minutes"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    def run_cache_effectiveness_test(self) -> Dict[str, Any]:
        """Run cache effectiveness test"""
        print("\n🗄️ RUNNING CACHE EFFECTIVENESS TEST")
        print("=" * 60)

        cmd = [
            sys.executable,
            str(TEST_SCRIPTS["cache_effectiveness"]),
            "--url",
            self.api_url,
            "--threads",
            "4",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)

            if result.returncode == 0:
                print("✅ Cache effectiveness test completed successfully")

                # Try to find và read the generated JSON file
                output_lines = result.stdout.split("\n")
                json_file = None
                for line in output_lines:
                    if "Kết quả đã lưu:" in line:
                        json_file = line.split(": ")[-1].strip()
                        break

                if json_file and os.path.exists(json_file):
                    with open(json_file, "r", encoding="utf-8") as f:
                        return json.load(f)
                else:
                    return {"status": "completed", "output": result.stdout}
            else:
                print(f"❌ Cache effectiveness test failed: {result.stderr}")
                return {"status": "failed", "error": result.stderr}

        except subprocess.TimeoutExpired:
            return {"status": "failed", "error": "Test timeout after 15 minutes"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def run_multi_user_test(self, max_users: int = 15) -> Dict[str, Any]:
        """Run multi-user load test"""
        print("\n👥 RUNNING MULTI-USER LOAD TEST")
        print("=" * 60)

        cmd = [
            sys.executable,
            str(TEST_SCRIPTS["multi_user_load"]),
            "--url",
            self.api_url,
            "--escalating",
            "--max-users",
            str(max_users),
            "--queries",
            "3",
        ]

        try:
            # Run async subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=1200)

            if process.returncode == 0:
                print("✅ Multi-user load test completed successfully")

                # Try to find và read the generated JSON file
                output_lines = stdout.decode().split("\n")
                json_file = None
                for line in output_lines:
                    if "Kết quả đã lưu:" in line:
                        json_file = line.split(": ")[-1].strip()
                        break

                if json_file and os.path.exists(json_file):
                    with open(json_file, "r", encoding="utf-8") as f:
                        return json.load(f)
                else:
                    return {"status": "completed", "output": stdout.decode()}
            else:
                print(f"❌ Multi-user load test failed: {stderr.decode()}")
                return {"status": "failed", "error": stderr.decode()}

        except asyncio.TimeoutError:
            return {"status": "failed", "error": "Test timeout after 20 minutes"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def run_all_tests(
        self, query_runs: int = 3, max_users: int = 15
    ) -> Dict[str, Any]:
        """Run all performance tests"""
        if not self.check_server_health():
            return {"error": "Server not available for testing"}

        print("🚀 STARTING COMPREHENSIVE PERFORMANCE TEST SUITE")
        print(f"📊 Target API: {self.api_url}")
        print(f"🔄 Query test runs: {query_runs}")
        print(f"👥 Max concurrent users: {max_users}")
        print("⏱️  Estimated time: 15-25 minutes")

        start_time = time.time()

        # Test 1: Query Latency
        self.test_results["tests"]["query_latency"] = self.run_query_latency_test(
            query_runs
        )

        # Test 2: Cache Effectiveness
        self.test_results["tests"][
            "cache_effectiveness"
        ] = self.run_cache_effectiveness_test()

        # Test 3: Multi-User Load Test
        self.test_results["tests"]["multi_user_load"] = await self.run_multi_user_test(
            max_users
        )

        total_time = time.time() - start_time
        self.test_results["total_test_time_s"] = total_time
        self.test_results["test_suite_end"] = datetime.now().isoformat()

        # Generate comprehensive summary
        self.generate_comprehensive_summary()

        return self.test_results

    def generate_comprehensive_summary(self):
        """Generate unified summary from all test results"""
        summary = {
            "overall_status": "unknown",
            "key_metrics": {},
            "performance_indicators": {},
            "system_capacity": {},
            "bottlenecks_identified": [],
            "priority_recommendations": [],
        }

        # Analyze Query Latency Results
        query_test = self.test_results["tests"].get("query_latency", {})
        if query_test.get("status") != "failed" and "summary" in query_test:
            comparison = query_test["summary"].get("comparison", {})
            if comparison:
                fastest_mode = None
                best_avg_time = float("inf")

                for mode, stats in comparison.items():
                    avg_time = stats.get("avg_response_time", float("inf"))
                    if avg_time < best_avg_time:
                        best_avg_time = avg_time
                        fastest_mode = mode

                summary["key_metrics"]["fastest_query_mode"] = fastest_mode
                summary["key_metrics"]["best_avg_response_time_ms"] = best_avg_time
                summary["key_metrics"]["query_modes_tested"] = len(comparison)

        # Analyze Cache Effectiveness Results
        cache_test = self.test_results["tests"].get("cache_effectiveness", {})
        if cache_test.get("status") != "failed" and "summary" in cache_test:
            cache_summary = cache_test["summary"]
            cache_eff = cache_summary.get("cache_effectiveness", {})

            if cache_eff:
                summary["key_metrics"]["avg_cache_speedup"] = cache_eff.get(
                    "avg_speedup", 1
                )
                summary["key_metrics"]["cache_hit_effectiveness"] = cache_eff.get(
                    "effective_rate", 0
                )
                summary["performance_indicators"]["cache_working"] = (
                    cache_eff.get("avg_speedup", 1) > 1.2
                )

        # Analyze Multi-User Load Results
        load_test = self.test_results["tests"].get("multi_user_load", {})
        if load_test.get("status") != "failed":
            if "breaking_point_analysis" in load_test:
                bp_analysis = load_test["breaking_point_analysis"]
                summary["system_capacity"]["max_concurrent_users"] = bp_analysis.get(
                    "max_stable_concurrent_users", 0
                )
                summary["system_capacity"]["breaking_point"] = bp_analysis.get(
                    "breaking_point_users"
                )

                # Get performance at max stable load
                perf_data = bp_analysis.get("performance_degradation", [])
                if perf_data:
                    max_stable_perf = None
                    for p in perf_data:
                        if p.get("system_stable", False):
                            max_stable_perf = p

                    if max_stable_perf:
                        summary["key_metrics"]["max_stable_qps"] = max_stable_perf.get(
                            "queries_per_second", 0
                        )
                        summary["key_metrics"]["max_stable_response_time"] = (
                            max_stable_perf.get("avg_response_time_ms", 0)
                        )

        # Identify Bottlenecks
        bottlenecks = []

        if summary["key_metrics"].get("best_avg_response_time_ms", 0) > 3000:
            bottlenecks.append("High query latency (>3s) - Database or LLM bottleneck")

        if not summary["performance_indicators"].get("cache_working", True):
            bottlenecks.append(
                "Cache not providing significant speedup - Configuration issue"
            )

        if summary["system_capacity"].get("max_concurrent_users", 0) < 10:
            bottlenecks.append(
                "Low concurrent user capacity - Connection pooling needed"
            )

        summary["bottlenecks_identified"] = bottlenecks

        # Priority Recommendations
        recommendations = []

        if "Connection pooling needed" in str(bottlenecks):
            recommendations.append(
                "CRITICAL: Implement database connection pooling (see CONNECTION_POOLING_STRATEGY.md)"
            )

        if "Cache not providing" in str(bottlenecks):
            recommendations.append("HIGH: Review and optimize cache configuration")

        if "High query latency" in str(bottlenecks):
            recommendations.append(
                "HIGH: Optimize database queries and consider query optimization"
            )

        if summary["system_capacity"].get("max_concurrent_users", 0) > 20:
            recommendations.append("GOOD: System handles concurrent load well")

        if not recommendations:
            recommendations.append("System performing within acceptable parameters")

        summary["priority_recommendations"] = recommendations

        # Overall Status
        critical_issues = len([r for r in recommendations if r.startswith("CRITICAL")])
        high_issues = len([r for r in recommendations if r.startswith("HIGH")])

        if critical_issues > 0:
            summary["overall_status"] = "critical_issues_found"
        elif high_issues > 0:
            summary["overall_status"] = "optimization_needed"
        else:
            summary["overall_status"] = "performing_well"

        self.test_results["summary"] = summary

        # Add consolidated recommendations from all tests
        all_recommendations = []
        for test_name, test_data in self.test_results["tests"].items():
            if isinstance(test_data, dict) and "recommendations" in test_data:
                test_recs = test_data["recommendations"]
                if isinstance(test_recs, list):
                    all_recommendations.extend(
                        [f"[{test_name}] {rec}" for rec in test_recs]
                    )

        self.test_results["recommendations"] = all_recommendations

    def print_comprehensive_report(self):
        """Print comprehensive performance test report"""
        print("\n" + "=" * 100)
        print("📊 COMPREHENSIVE PERFORMANCE TEST REPORT")
        print("=" * 100)

        summary = self.test_results.get("summary", {})

        # Overall Status
        status = summary.get("overall_status", "unknown")
        status_emoji = {
            "performing_well": "✅",
            "optimization_needed": "⚠️",
            "critical_issues_found": "❌",
            "unknown": "❓",
        }

        print(
            f"\n🎯 OVERALL STATUS: {status_emoji.get(status, '❓')} {status.replace('_', ' ').title()}"
        )

        # Key Metrics Summary
        metrics = summary.get("key_metrics", {})
        if metrics:
            print(f"\n📈 KEY PERFORMANCE METRICS:")
            print(f"   Fastest Query Mode: {metrics.get('fastest_query_mode', 'N/A')}")
            print(
                f"   Best Response Time: {metrics.get('best_avg_response_time_ms', 0):.0f}ms"
            )
            print(f"   Cache Speedup: {metrics.get('avg_cache_speedup', 1):.1f}x")
            print(
                f"   Cache Effectiveness: {metrics.get('cache_hit_effectiveness', 0):.1%}"
            )
            print(f"   Max Concurrent Users: {metrics.get('max_concurrent_users', 0)}")
            print(f"   Max Stable QPS: {metrics.get('max_stable_qps', 0):.1f}")

        # System Capacity
        capacity = summary.get("system_capacity", {})
        if capacity:
            print(f"\n🏗️ SYSTEM CAPACITY:")
            print(f"   Max Stable Users: {capacity.get('max_concurrent_users', 0)}")
            if capacity.get("breaking_point"):
                print(f"   Breaking Point: {capacity['breaking_point']} users")
            else:
                print(f"   Breaking Point: Not reached in test")

        # Bottlenecks
        bottlenecks = summary.get("bottlenecks_identified", [])
        if bottlenecks:
            print(f"\n🚫 BOTTLENECKS IDENTIFIED:")
            for i, bottleneck in enumerate(bottlenecks, 1):
                print(f"   {i}. {bottleneck}")

        # Priority Recommendations
        priority_recs = summary.get("priority_recommendations", [])
        if priority_recs:
            print(f"\n💡 PRIORITY RECOMMENDATIONS:")
            for i, rec in enumerate(priority_recs, 1):
                print(f"   {i}. {rec}")

        # Test Details
        print(f"\n📋 TEST EXECUTION DETAILS:")
        total_time = self.test_results.get("total_test_time_s", 0)
        print(f"   Total Test Duration: {total_time/60:.1f} minutes")
        print(f"   Tests Completed: {len(self.test_results.get('tests', {}))}")

        for test_name, test_data in self.test_results["tests"].items():
            status_symbol = "✅" if test_data.get("status") != "failed" else "❌"
            print(f"   {status_symbol} {test_name.replace('_', ' ').title()}")

    def save_report(self, filename: str = None):
        """Save comprehensive report to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"logs/performance_test_report_{timestamp}.json"

        os.makedirs(os.path.dirname(filename), exist_ok=True)

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Comprehensive report saved: {filename}")


async def main():
    """Main async function"""
    import argparse

    parser = argparse.ArgumentParser(description="Comprehensive Performance Test Suite")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--query-runs",
        type=int,
        default=3,
        help="Number of runs per query (default: 3)",
    )
    parser.add_argument(
        "--max-users",
        type=int,
        default=15,
        help="Max concurrent users for load test (default: 15)",
    )
    parser.add_argument("--output", help="Output JSON file path")
    parser.add_argument(
        "--quick", action="store_true", help="Quick test mode (fewer runs)"
    )

    args = parser.parse_args()

    if args.quick:
        args.query_runs = 2
        args.max_users = 10
        print("🏃‍♂️ Quick test mode enabled")

    runner = PerformanceTestRunner(args.url)

    try:
        results = await runner.run_all_tests(args.query_runs, args.max_users)

        if "error" not in results:
            runner.print_comprehensive_report()
            runner.save_report(args.output)
        else:
            print(f"❌ Test suite failed: {results['error']}")
            sys.exit(1)

    except KeyboardInterrupt:
        print(f"\n⚠️ Test suite interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Make scripts executable
    for script_path in TEST_SCRIPTS.values():
        if script_path.exists():
            os.chmod(script_path, 0o755)

    asyncio.run(main())
