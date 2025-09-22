"""Simple test for the enhanced data cleaning functions."""

import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.data.cleaners import (
    basic_clean,
    advanced_clean,
    vietnamese_specific_clean,
    validate_cleaned_text,
)


def test_basic_clean():
    """Test basic cleaning function."""
    print("🧹 Testing basic_clean()...")

    test_input = "Hello   world!\t\n\n\n\nThis is a test.\u00a0Multiple spaces."
    result = basic_clean(test_input)

    print(f"  Input:  {repr(test_input)}")
    print(f"  Output: {repr(result)}")
    print(f"  Length: {len(test_input)} → {len(result)}")

    # Check if basic cleaning worked
    assert "\t" not in result, "Tabs should be removed"
    assert "\u00a0" not in result, "Non-breaking spaces should be removed"
    assert result.count("\n") < test_input.count(
        "\n"
    ), "Excessive newlines should be reduced"

    print("  ✅ basic_clean() test passed")


def test_advanced_clean():
    """Test advanced cleaning function."""
    print("🧹 Testing advanced_clean()...")

    test_input = "Check this email: user@example.com and URL: https://example.com\n\n\n••• Bullet point text"
    result = advanced_clean(test_input)

    print(f"  Input:  {repr(test_input[:60])}...")
    print(f"  Output: {repr(result[:60])}...")
    print(f"  Length: {len(test_input)} → {len(result)}")

    # Check if advanced cleaning worked
    assert len(result) > 0, "Should not return empty string"
    assert result.strip() == result, "Should be stripped"

    print("  ✅ advanced_clean() test passed")


def test_vietnamese_specific_clean():
    """Test Vietnamese-specific cleaning."""
    print("🇻🇳 Testing vietnamese_specific_clean()...")

    test_input = (
        "Trang 1\n\nĐây là văn bản tiếng Việt.\n\nChương I: Tổng quan\n\nTrang 2"
    )
    result = vietnamese_specific_clean(test_input)

    print(f"  Input:  {repr(test_input)}")
    print(f"  Output: {repr(result)}")
    print(f"  Length: {len(test_input)} → {len(result)}")

    # Check if Vietnamese cleaning worked
    assert (
        "Trang 1" not in result or "Trang 2" not in result
    ), "Page numbers should be removed"
    assert len(result) > 0, "Should not return empty string"

    print("  ✅ vietnamese_specific_clean() test passed")


def test_validate_cleaned_text():
    """Test text validation function."""
    print("✅ Testing validate_cleaned_text()...")

    test_cases = [
        ("This is a good text with sufficient content.", True, "Good text"),
        ("Short", False, "Too short"),
        ("", False, "Empty text"),
        ("!@#$%^&*()" * 15, False, "Mostly symbols"),
        ("This text has good variety of words and characters.", True, "Good variety"),
    ]

    for text, expected, description in test_cases:
        result = validate_cleaned_text(text, min_length=10)
        print(f"  {description}: {result} (expected: {expected})")
        assert result == expected, f"Validation failed for: {description}"

    print("  ✅ validate_cleaned_text() test passed")


def main():
    """Run all simple tests."""
    print("🔧 Starting Simple Data Cleaning Tests")
    print("=" * 50)

    try:
        test_basic_clean()
        print()
        test_advanced_clean()
        print()
        test_vietnamese_specific_clean()
        print()
        test_validate_cleaned_text()

        print("\n" + "=" * 50)
        print("🎉 All simple tests passed successfully!")

        return 0

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
