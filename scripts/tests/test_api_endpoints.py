#!/usr/bin/env python3
"""
Comprehensive API endpoint tests for RAG Bidding System
"""
import json
import time
import requests
from typing import Dict, Any

BASE_URL = "http://localhost:8000"


class APITester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = {}

    def test_health_endpoint(self) -> bool:
        """Test /health endpoint"""
        print("🏥 Testing /health endpoint...")

        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)

            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ Status: {response.status_code}")
                print(f"  📊 Response: {data}")
                return data.get("db", False) and data.get("status") == "healthy"
            else:
                print(f"  ❌ Failed with status: {response.status_code}")
                return False

        except Exception as e:
            print(f"  ❌ Error: {e}")
            return False

    def test_stats_endpoint(self) -> bool:
        """Test /stats endpoint"""
        print("\n📊 Testing /stats endpoint...")

        try:
            response = self.session.get(f"{self.base_url}/stats", timeout=10)

            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ Status: {response.status_code}")
                print(f"  🤖 LLM Model: {data.get('llm', {}).get('model')}")
                print(
                    f"  🔄 Embedding Model: {data.get('vector_store', {}).get('embedding_model')}"
                )
                print(f"  🎛️  Current Mode: {data.get('current_mode')}")
                print(
                    f"  🧩 Features Enabled: {sum(data.get('phase1_features', {}).values())}/5"
                )
                return True
            else:
                print(f"  ❌ Failed with status: {response.status_code}")
                return False

        except Exception as e:
            print(f"  ❌ Error: {e}")
            return False

    def test_retrieval_endpoint(self) -> bool:
        """Test /test/retrieval endpoint"""
        print("\n🔍 Testing /test/retrieval endpoint...")

        test_cases = [
            {"query": "Luật đầu tư", "mode": "fast"},
            {"query": "Quy định về đăng ký kinh doanh", "mode": "balanced"},
            {"query": "Thủ tục mời thầu", "mode": "fast"},
        ]

        success_count = 0

        for case in test_cases:
            try:
                params = case
                response = self.session.get(
                    f"{self.base_url}/test/retrieval", params=params, timeout=15
                )

                if response.status_code == 200:
                    data = response.json()
                    docs_found = data.get("documents_found", 0)

                    print(f"  📋 Query: '{case['query']}' ({case['mode']})")
                    print(f"     📄 Documents found: {docs_found}")

                    if docs_found > 0:
                        first_result = data.get("results", [{}])[0]
                        content_preview = first_result.get("content_preview", "")[:80]
                        metadata = first_result.get("metadata", {})
                        doc_type = metadata.get("document_type", "unknown")

                        print(f"     📝 Top result: {content_preview}...")
                        print(f"     🏷️  Type: {doc_type}")
                        success_count += 1
                    else:
                        print(f"     ⚠️  No documents found")
                else:
                    print(
                        f"  ❌ Query '{case['query']}' failed: {response.status_code}"
                    )
                    print(f"     Error: {response.text}")

            except Exception as e:
                print(f"  ❌ Query '{case['query']}' error: {e}")

        return success_count > 0

    def test_ask_endpoint(self) -> bool:
        """Test /ask endpoint (Q&A)"""
        print("\n❓ Testing /ask endpoint...")

        test_questions = [
            {
                "question": "Luật đầu tư quy định gì về thủ tục đăng ký kinh doanh?",
                "mode": "fast",
            },
            {
                "question": "Điều kiện để được cấp giấy phép đầu tư là gì?",
                "mode": "balanced",
            },
        ]

        success_count = 0

        for case in test_questions:
            try:
                payload = case
                response = self.session.post(
                    f"{self.base_url}/ask", json=payload, timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    answer = data.get("answer", "")
                    sources = data.get("sources", [])
                    features = data.get("enhanced_features", [])
                    processing_time = data.get("processing_time_ms", 0)

                    print(f"  🤔 Question: '{case['question'][:60]}...'")
                    print(f"     💡 Answer: {answer[:100]}...")
                    print(f"     📚 Sources: {len(sources)} documents")
                    print(f"     🔧 Features: {features}")
                    print(f"     ⏱️  Time: {processing_time}ms")

                    if len(sources) > 0:
                        success_count += 1
                    else:
                        print(f"     ⚠️  No sources found")
                else:
                    print(f"  ❌ Question failed: {response.status_code}")
                    print(f"     Error: {response.text}")

            except Exception as e:
                print(f"  ❌ Question error: {e}")

        return success_count > 0

    def run_all_tests(self) -> Dict[str, bool]:
        """Run all API tests"""
        print("🚀 RAG Bidding API - Comprehensive Tests")
        print("=" * 60)

        # Check if server is running
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            print(
                f"🌐 Server Status: {'✅ Running' if response.status_code == 200 else '❌ Error'}"
            )
        except:
            print("❌ Server not accessible at http://localhost:8000")
            print(
                "💡 Please start the server first: python scripts/tests/test_api_server.py"
            )
            return {}

        # Run tests
        tests = [
            ("Health Endpoint", self.test_health_endpoint),
            ("Stats Endpoint", self.test_stats_endpoint),
            ("Retrieval Endpoint", self.test_retrieval_endpoint),
            ("Ask Endpoint (Q&A)", self.test_ask_endpoint),
        ]

        results = {}

        for test_name, test_func in tests:
            try:
                start_time = time.time()
                success = test_func()
                test_time = time.time() - start_time
                results[test_name] = {"success": success, "time": test_time}
            except KeyboardInterrupt:
                print(f"\n⏹️  Tests interrupted by user")
                break
            except Exception as e:
                print(f"\n❌ Test '{test_name}' crashed: {e}")
                results[test_name] = {"success": False, "time": 0, "error": str(e)}

        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY:")

        total_tests = len(results)
        passed_tests = sum(1 for r in results.values() if r["success"])

        for test_name, result in results.items():
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            time_str = f"({result['time']:.1f}s)" if result["time"] > 0 else ""
            print(f"   {test_name}: {status} {time_str}")

            if not result["success"] and "error" in result:
                print(f"      Error: {result['error']}")

        print(f"\n🎯 Overall: {passed_tests}/{total_tests} tests passed")

        if passed_tests == total_tests:
            print("\n🎉 All API tests passed! Server is working correctly.")
        else:
            print(
                f"\n⚠️  {total_tests - passed_tests} tests failed. Check the errors above."
            )

        return results


def main():
    """Main test runner"""
    tester = APITester()
    results = tester.run_all_tests()

    # Exit with appropriate code
    if all(r["success"] for r in results.values()):
        exit(0)
    else:
        exit(1)


if __name__ == "__main__":
    main()
