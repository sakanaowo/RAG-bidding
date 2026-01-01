#!/usr/bin/env python3
"""
Test runner script - orchestrates all tests
"""
import sys
import subprocess
import time
from pathlib import Path


def run_test(script_name: str, description: str) -> bool:
    """Run a test script and return success status"""
    print(f"\n🚀 Running {description}...")
    print("=" * 60)

    try:
        # Ensure we're in the correct directory
        project_root = Path(__file__).parent.parent.parent
        script_path = project_root / "scripts" / "tests" / script_name

        if not script_path.exists():
            print(f"❌ Test script not found: {script_path}")
            return False

        # Run the test
        result = subprocess.run(
            ["python", str(script_path)], cwd=project_root, capture_output=False
        )

        success = result.returncode == 0
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"\n{description}: {status}")

        return success

    except Exception as e:
        print(f"❌ Error running {description}: {e}")
        return False


def check_server_status() -> bool:
    """Check if API server is running"""
    try:
        import requests

        response = requests.get("http://localhost:8000/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def main():
    """Main test orchestrator"""
    print("🧪 RAG Bidding System - Test Suite")
    print("=" * 80)

    # Test sequence
    tests = [
        ("test_core_system.py", "Core System Tests (Database, Vector Store, Q&A)"),
    ]

    results = {}

    # Run core tests first
    for script, description in tests:
        success = run_test(script, description)
        results[description] = success

        if not success:
            print(f"\n⚠️  {description} failed. Skipping API tests.")
            break

    # If core tests pass, check for API server
    if all(results.values()):
        print(f"\n{'='*80}")
        print("🌐 Checking API Server Status...")

        server_running = check_server_status()

        if server_running:
            print("✅ API Server is running")

            # Run API tests
            api_success = run_test("test_api_endpoints.py", "API Endpoint Tests")
            results["API Endpoint Tests"] = api_success

        else:
            print("⚠️  API Server not running")
            print("💡 To test API endpoints:")
            print("   1. Start server: python scripts/tests/test_api_server.py")
            print("   2. Run API tests: python scripts/tests/test_api_endpoints.py")

            results["API Server"] = False

    # Final summary
    print(f"\n{'='*80}")
    print("📊 FINAL TEST SUMMARY:")

    total_tests = len(results)
    passed_tests = sum(results.values())

    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {test_name}: {status}")

    print(f"\n🎯 Overall Result: {passed_tests}/{total_tests} test suites passed")

    if passed_tests == total_tests:
        print("\n🎉 All tests passed! RAG system is fully operational.")
        exit(0)
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test suite(s) failed.")
        print("🔧 Please fix the issues and run tests again.")
        exit(1)


if __name__ == "__main__":
    main()
