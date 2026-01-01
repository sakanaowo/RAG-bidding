"""
Tests for Bidding Loader

Tests:
1. Load bidding DOCX successfully
2. Bidding type detection
3. Package info extraction
4. Statistics calculation
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.preprocessing.loaders.bidding_loader import BiddingLoader


def test_bidding_loader_basic():
    """Test loading a bidding DOCX document"""
    print("\n=== Test 1: Load Bidding DOCX Document ===")

    # Use bidding DOCX file
    test_file = (
        project_root
        / "data/raw/Ho so moi thau/13. Mua sắm trực tuyến/13. Mẫu số 13_ Mua sắm trực tuyến.docx"
    )

    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return False

    try:
        loader = BiddingLoader()
        content = loader.load(str(test_file))

        print(f"✅ Loaded: {content.metadata['filename']}")
        print(f"   Total chars: {content.statistics['char_count']:,}")
        print(f"   Bidding type: {content.metadata.get('bidding_type', 'N/A')}")

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


def test_bidding_type_detection():
    """Test bidding type detection"""
    print("\n=== Test 2: Bidding Type Detection ===")

    # Test different bidding types
    test_files = [
        "13. Mua sắm trực tuyến/13. Mẫu số 13_ Mua sắm trực tuyến.docx",  # Online procurement
        "7. EP (tư vấn_hàng hóa)/7. Mẫu số 7C. E-HSMST_EP sơ tuyển.docx",  # EP
        "5. Phi TV/5. Mẫu số 5B E-HSMT Phi tư vấn 2 túi.docx",  # Non-consulting
    ]

    loader = BiddingLoader()
    detected_types = []

    for file_path in test_files:
        full_path = project_root / "data/raw/Ho so moi thau" / file_path

        if not full_path.exists():
            print(f"⚠️  File not found: {file_path}")
            continue

        try:
            content = loader.load(str(full_path))
            bidding_type = content.metadata.get("bidding_type", "unknown")
            detected_types.append(bidding_type)

            print(f"📄 {full_path.name}")
            print(f"   Bidding type: {bidding_type}")

        except Exception as e:
            print(f"❌ Failed to load {file_path}: {e}")
            return False

    # Check that we detected at least some types
    assert len(detected_types) > 0, "Should detect at least one bidding type"

    print(f"✅ Test 2 passed - Detected {len(detected_types)} bidding types")
    return True


def test_package_info():
    """Test package information extraction"""
    print("\n=== Test 3: Package Info Extraction ===")

    test_file = (
        project_root
        / "data/raw/Ho so moi thau/13. Mua sắm trực tuyến/13. Mẫu số 13_ Mua sắm trực tuyến.docx"
    )

    if not test_file.exists():
        print(f"❌ Test file not found")
        return False

    try:
        loader = BiddingLoader()
        content = loader.load(str(test_file))

        package_info = content.metadata.get("package_info", {})

        print("📦 Package Information:")
        print(f"   Name: {package_info.get('package_name', 'N/A')}")
        print(f"   Code: {package_info.get('package_code', 'N/A')}")
        print(f"   Owner: {package_info.get('owner', 'N/A')}")

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
        / "data/raw/Ho so moi thau/13. Mua sắm trực tuyến/13. Mẫu số 13_ Mua sắm trực tuyến.docx"
    )

    if not test_file.exists():
        print(f"❌ Test file not found")
        return False

    try:
        loader = BiddingLoader()
        content = loader.load(str(test_file))

        stats = content.statistics

        print("📊 Statistics:")
        for key, value in stats.items():
            if isinstance(value, int) and value > 1000:
                print(f"   {key}: {value:,}")
            elif isinstance(value, bool):
                print(f"   {key}: {'Yes' if value else 'No'}")
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
    """Run all bidding loader tests"""
    print("\n" + "=" * 60)
    print("BIDDING LOADER TESTS")
    print("=" * 60)

    tests = [
        test_bidding_loader_basic,
        test_bidding_type_detection,
        test_package_info,
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
