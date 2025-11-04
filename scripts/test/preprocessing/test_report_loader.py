"""
Tests for Report Loader

Tests:
1. Load report DOCX successfully
2. Report type detection
3. Report info extraction
4. Statistics calculation
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.preprocessing.loaders.report_loader import ReportLoader


def test_report_loader_basic():
    """Test loading a report DOCX document"""
    print("\n=== Test 1: Load Report DOCX Document ===")

    # Use report DOCX file
    test_file = (
        project_root
        / "data/raw/Mau bao cao/2. Báo cáo đánh giá/02A. Mẫu BCĐG cho 1 giai đoạn 1 túi.docx"
    )

    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return False

    try:
        loader = ReportLoader()
        content = loader.load(str(test_file))

        print(f"✅ Loaded: {content.metadata['filename']}")
        print(f"   Total chars: {content.statistics['char_count']:,}")
        print(f"   Report type: {content.metadata.get('report_type', 'N/A')}")

        # Check basic structure
        assert len(content.text) > 0, "Text should not be empty"
        assert content.metadata["filename"].endswith(".docx")

        print("✅ Test 1 passed")
        return True

    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_report_type_detection():
    """Test report type detection"""
    print("\n=== Test 2: Report Type Detection ===")

    # Test different report types
    test_files = [
        "2. Báo cáo đánh giá/02A. Mẫu BCĐG cho 1 giai đoạn 1 túi.docx",  # Evaluation
        "3. Báo cáo thẩm định/03A. Mẫu BCTĐ HSMT.docx",  # Appraisal
    ]

    loader = ReportLoader()
    detected_types = []

    for file_path in test_files:
        full_path = project_root / "data/raw/Mau bao cao" / file_path

        if not full_path.exists():
            print(f"⚠️  File not found: {file_path}")
            continue

        try:
            content = loader.load(str(full_path))
            report_type = content.metadata.get("report_type", "unknown")
            detected_types.append(report_type)

            print(f"📄 {full_path.name}")
            print(f"   Report type: {report_type}")

        except Exception as e:
            print(f"❌ Failed to load {file_path}: {e}")
            return False

    # Check that we detected at least some types
    assert len(detected_types) > 0, "Should detect at least one report type"

    print(f"✅ Test 2 passed - Detected {len(detected_types)} report types")
    return True


def test_report_info():
    """Test report information extraction"""
    print("\n=== Test 3: Report Info Extraction ===")

    test_file = (
        project_root
        / "data/raw/Mau bao cao/2. Báo cáo đánh giá/02A. Mẫu BCĐG cho 1 giai đoạn 1 túi.docx"
    )

    if not test_file.exists():
        print(f"❌ Test file not found")
        return False

    try:
        loader = ReportLoader()
        content = loader.load(str(test_file))

        report_info = content.metadata.get("report_info", {})

        print("📋 Report Information:")
        print(f"   Title: {report_info.get('report_title', 'N/A')}")
        print(f"   Package: {report_info.get('package_name', 'N/A')}")
        print(f"   Evaluator: {report_info.get('evaluator', 'N/A')}")

        print("✅ Test 3 passed")
        return True

    except Exception as e:
        print(f"❌ Test 3 failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_statistics():
    """Test statistics calculation"""
    print("\n=== Test 4: Statistics Calculation ===")

    test_file = (
        project_root
        / "data/raw/Mau bao cao/2. Báo cáo đánh giá/02A. Mẫu BCĐG cho 1 giai đoạn 1 túi.docx"
    )

    if not test_file.exists():
        print(f"❌ Test file not found")
        return False

    try:
        loader = ReportLoader()
        content = loader.load(str(test_file))

        stats = content.statistics

        print("📊 Statistics:")
        for key, value in stats.items():
            if isinstance(value, int) and value > 1000:
                print(f"   {key}: {value:,}")
            else:
                print(f"   {key}: {value}")

        # Check required stats
        required_stats = [
            "char_count",
            "word_count",
            "line_count",
            "table_count",
        ]

        for stat in required_stats:
            assert stat in stats, f"Missing statistic: {stat}"

        assert stats["char_count"] > 0
        assert stats["word_count"] > 0

        print("✅ Test 4 passed")
        return True

    except Exception as e:
        print(f"❌ Test 4 failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def run_all_tests():
    """Run all report loader tests"""
    print("\n" + "=" * 60)
    print("REPORT LOADER TESTS")
    print("=" * 60)

    tests = [
        test_report_loader_basic,
        test_report_type_detection,
        test_report_info,
        test_statistics,
    ]

    results = []
    for test in tests:
        results.append(test())

    print("\n" + "=" * 60)
    print(f"RESULTS: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)

    return all(results)


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
