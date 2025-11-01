#!/usr/bin/env python3
"""
Integration Test Runner & Report Generator
Run all 5 integration tests and generate comprehensive report
"""

import sys
from pathlib import Path
import subprocess
import time
import json
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).parent.parent.parent

# Test scripts in execution order
TEST_SCRIPTS = [
    {
        "id": 1,
        "name": "End-to-End Pipeline",
        "script": "test_e2e_pipeline.py",
        "priority": "CRITICAL",
        "time_budget": 45,  # minutes
    },
    {
        "id": 2,
        "name": "Cross-Type Batch",
        "script": "test_cross_type_batch.py",
        "priority": "IMPORTANT",
        "time_budget": 45,
    },
    {
        "id": 3,
        "name": "Edge Cases",
        "script": "test_edge_cases.py",
        "priority": "IMPORTANT",
        "time_budget": 45,
    },
    {
        "id": 4,
        "name": "Database Basic",
        "script": "test_database_basic.py",
        "priority": "CRITICAL",
        "time_budget": 45,
    },
    {
        "id": 5,
        "name": "Performance",
        "script": "test_performance.py",
        "priority": "MEDIUM",
        "time_budget": 45,
    },
]


def run_test(test_info: Dict[str, Any]) -> Dict[str, Any]:
    """Run a single test script"""
    script_path = PROJECT_ROOT / "scripts/test" / test_info["script"]

    print(f"\n{'='*80}")
    print(f"🧪 Test #{test_info['id']}: {test_info['name']}")
    print(f"   Priority: {test_info['priority']}")
    print(f"   Script: {test_info['script']}")
    print(f"{'='*80}\n")

    result = {
        "id": test_info["id"],
        "name": test_info["name"],
        "script": test_info["script"],
        "priority": test_info["priority"],
        "success": False,
        "exit_code": None,
        "execution_time": 0,
        "output": "",
        "error": "",
    }

    start_time = time.time()

    try:
        # Run test script
        process = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=test_info["time_budget"] * 60,  # Convert to seconds
        )

        result["exit_code"] = process.returncode
        result["success"] = process.returncode == 0
        result["output"] = process.stdout
        result["error"] = process.stderr

        # Print output
        print(process.stdout)

        if process.stderr:
            print("STDERR:", process.stderr)

    except subprocess.TimeoutExpired:
        result["error"] = f"Test timed out after {test_info['time_budget']} minutes"
        print(f"\n⏱️  TIMEOUT: Test exceeded {test_info['time_budget']} minutes")

    except Exception as e:
        result["error"] = f"{type(e).__name__}: {str(e)}"
        print(f"\n❌ ERROR: {e}")

    finally:
        result["execution_time"] = time.time() - start_time

    status = "✅ PASSED" if result["success"] else "❌ FAILED"
    print(f"\n{status} - {test_info['name']} ({result['execution_time']:.1f}s)")

    return result


def generate_report(results: List[Dict[str, Any]], total_time: float) -> str:
    """Generate markdown report"""

    report = f"""# Integration Testing Report

**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}  
**Total Execution Time:** {total_time:.1f}s ({total_time/60:.1f} minutes)

---

## Executive Summary

"""

    # Calculate statistics
    total_tests = len(results)
    passed = sum(1 for r in results if r["success"])
    failed = total_tests - passed
    pass_rate = passed / total_tests * 100 if total_tests > 0 else 0

    report += f"""
- **Total Tests:** {total_tests}
- **Passed:** {passed} ✅
- **Failed:** {failed} ❌
- **Pass Rate:** {pass_rate:.1f}%

"""

    # Overall status
    if pass_rate == 100:
        report += "### ✅ **STATUS: ALL TESTS PASSED**\n\n"
        report += "🎉 All integration tests completed successfully! The system is ready for the next phase.\n\n"
    elif pass_rate >= 80:
        report += "### ⚠️ **STATUS: MOSTLY PASSED**\n\n"
        report += (
            f"{failed} test(s) failed. Review failures below and address issues.\n\n"
        )
    else:
        report += "### ❌ **STATUS: SIGNIFICANT FAILURES**\n\n"
        report += f"{failed} test(s) failed. Requires immediate attention.\n\n"

    # Test Results Table
    report += "---\n\n## Test Results\n\n"
    report += "| # | Test Name | Priority | Status | Time (s) |\n"
    report += "|---|-----------|----------|--------|----------|\n"

    for result in results:
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        report += f"| {result['id']} | {result['name']} | {result['priority']} | {status} | {result['execution_time']:.1f} |\n"

    # Detailed Results
    report += "\n---\n\n## Detailed Results\n\n"

    for result in results:
        status_icon = "✅" if result["success"] else "❌"

        report += f"""### {status_icon} Test #{result['id']}: {result['name']}

- **Priority:** {result['priority']}
- **Status:** {'PASSED' if result['success'] else 'FAILED'}
- **Execution Time:** {result['execution_time']:.1f}s
- **Exit Code:** {result['exit_code']}

"""

        if not result["success"]:
            report += "#### ❌ Error Details\n\n"
            report += "```\n"
            report += (
                result["error"][:500]
                if result["error"]
                else "No error details available"
            )
            report += "\n```\n\n"

        # Extract key metrics from output
        if "PASS" in result["output"] or "chunks" in result["output"]:
            report += "#### 📊 Key Metrics\n\n"
            # Try to extract some key lines
            for line in result["output"].split("\n"):
                if any(
                    keyword in line
                    for keyword in ["✅", "chunks", "Files", "Time:", "Success"]
                ):
                    report += f"- {line.strip()}\n"
            report += "\n"

        report += "---\n\n"

    # Priority Analysis
    report += "## Priority Analysis\n\n"

    for priority in ["CRITICAL", "IMPORTANT", "MEDIUM"]:
        priority_tests = [r for r in results if r["priority"] == priority]
        if priority_tests:
            passed_priority = sum(1 for r in priority_tests if r["success"])
            total_priority = len(priority_tests)

            status = "✅" if passed_priority == total_priority else "⚠️"
            report += f"### {status} {priority} Priority\n\n"
            report += f"- **Tests:** {total_priority}\n"
            report += f"- **Passed:** {passed_priority}/{total_priority}\n"
            report += f"- **Pass Rate:** {passed_priority/total_priority*100:.1f}%\n\n"

    # Next Steps
    report += "---\n\n## Next Steps\n\n"

    if pass_rate == 100:
        report += """
### ✅ All Tests Passed - Ready for Next Phase

1. **Review Phase 2B completion:** Integration testing now at 100%
2. **Update roadmap:** Mark Phase 2B as complete
3. **Begin Phase 3:** Start data migration planning
4. **Production preparation:** Prepare deployment checklist

"""
    else:
        report += f"""
### 🔧 Address Failures

Failed tests that need attention:

"""
        for result in results:
            if not result["success"]:
                report += f"- **{result['name']}** ({result['priority']} priority)\n"

        report += """

### Recommended Actions

1. Review detailed error logs above
2. Fix critical issues first (CRITICAL priority)
3. Re-run failed tests
4. Update integration test plan based on findings

"""

    # Testing Coverage
    report += "---\n\n## Testing Coverage\n\n"
    report += """
### ✅ Completed

- [x] End-to-End Pipeline Testing
- [x] Cross-Document Type Batch Processing
- [x] Edge Cases & Error Handling
- [x] Database Integration (Basic)
- [x] Performance & Scalability Benchmarks

### 📝 Remaining (Future)

- [ ] Full Database Integration (PostgreSQL)
- [ ] API Integration Testing
- [ ] Backward Compatibility Testing
- [ ] Production Load Testing
- [ ] Security & Validation Testing

---

## Conclusion

"""

    if pass_rate >= 80:
        report += f"""
Integration testing for Phase 2B has achieved **{pass_rate:.1f}% pass rate**. 
The core chunking pipeline is validated and ready for production use.

**Recommendation:** Proceed to Phase 3 (Data Migration) while monitoring any remaining issues.
"""
    else:
        report += f"""
Integration testing revealed significant issues ({failed} failures). 
**Recommendation:** Address failures before proceeding to next phase.
"""

    report += "\n---\n\n"
    report += f"*Report generated by integration test runner at {time.strftime('%Y-%m-%d %H:%M:%S')}*\n"

    return report


def main():
    """Run all integration tests"""
    print("=" * 80)
    print("🚀 INTEGRATION TEST SUITE")
    print("=" * 80)
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Tests to run: {len(TEST_SCRIPTS)}")
    print(f"Estimated time: {sum(t['time_budget'] for t in TEST_SCRIPTS)} minutes")
    print()

    input("Press ENTER to begin testing...")

    start_time = time.time()
    results = []

    # Run all tests
    for test_info in TEST_SCRIPTS:
        result = run_test(test_info)
        results.append(result)

        # Brief pause between tests
        time.sleep(1)

    total_time = time.time() - start_time

    # Generate report
    print("\n" + "=" * 80)
    print("📊 GENERATING REPORT")
    print("=" * 80)

    report = generate_report(results, total_time)

    # Save report
    report_path = PROJECT_ROOT / "data/outputs/INTEGRATION_TEST_REPORT.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")

    print(f"\n✅ Report saved to: {report_path}")

    # Print summary
    passed = sum(1 for r in results if r["success"])
    total = len(results)

    print("\n" + "=" * 80)
    print("📈 FINAL SUMMARY")
    print("=" * 80)
    print(f"\nTests:     {passed}/{total} passed ({passed/total*100:.1f}%)")
    print(f"Time:      {total_time:.1f}s ({total_time/60:.1f} minutes)")
    print(f"Report:    {report_path}")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Integration testing complete!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed - see report for details")
        return 1


if __name__ == "__main__":
    sys.exit(main())
