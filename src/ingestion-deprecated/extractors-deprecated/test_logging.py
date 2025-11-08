#!/usr/bin/env python3
"""
Test script để kiểm tra hệ thống OCR logging
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import our OCR module
sys.path.append(str(Path(__file__).parent))

from vintern_batch_ocr import OCRLogger, validate_ocr_output


def test_validation():
    """Test OCR output validation function"""
    print("🧪 Testing OCR validation function...")

    test_cases = [
        ("", "empty_output"),
        ("   ", "empty_output"),
        ("55", "too_short"),
        ("98", "too_short"),
        ("1234567890", "mostly_numbers"),
        ("Đây là văn bản tiếng Việt hoàn chỉnh với nhiều từ.", "valid"),
        ("[OCR_ERROR: Some error]", "error_pattern_match"),
        ("a b c", "too_few_words"),
        ("Hello world English text", "insufficient_vietnamese_content"),
    ]

    for i, (text, expected_error) in enumerate(test_cases, 1):
        is_valid, error_reason = validate_ocr_output(text)
        status = (
            "✓"
            if (not is_valid and error_reason == expected_error)
            or (is_valid and expected_error == "valid")
            else "✗"
        )
        print(
            f"{status} Test {i}: '{text[:30]}...' -> {error_reason} (expected: {expected_error})"
        )


def test_logger():
    """Test OCR logger functionality"""
    print("\n📊 Testing OCR logger...")

    # Create temporary log file
    log_file = "/tmp/test_ocr_log.json"
    logger = OCRLogger(log_file)

    # Simulate various scenarios
    logger.update_total()
    logger.log_success()

    logger.update_total()
    logger.log_error(2, "/path/to/page2.jpg", "empty_content", "No text extracted", "")

    logger.update_total()
    logger.log_error(
        3, "/path/to/page3.jpg", "low_quality", "Too few words", "chỉ có vài từ"
    )

    logger.update_total()
    logger.log_error(4, "/path/to/page4.jpg", "runtime_error", "GPU out of memory")

    logger.update_total()
    logger.log_success()

    # Save and display results
    logger.save_log()

    print(f"Log file created: {log_file}")
    print("You can check the JSON file for detailed error information.")


def test_existing_pages():
    """Test validation on existing OCR output files"""
    print("\n🔍 Testing validation on existing OCR files...")

    # Path to existing processed files
    processed_dir = (
        Path(__file__).parent.parent / "processed" / "Decreee-24-27-02-2024-processed"
    )

    if not processed_dir.exists():
        print(f"Processed directory not found: {processed_dir}")
        return

    # Test a few existing files
    test_files = ["page_055.txt", "page_098.txt"]

    for filename in test_files:
        filepath = processed_dir / filename
        if filepath.exists():
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                is_valid, error_reason = validate_ocr_output(content)
                status = "✓" if is_valid else "⚠"
                print(
                    f"{status} {filename}: {error_reason} (length: {len(content)} chars)"
                )
                if not is_valid:
                    print(f"   Content preview: '{content[:100]}...'")
            except Exception as e:
                print(f"✗ Error reading {filename}: {e}")
        else:
            print(f"File not found: {filename}")


if __name__ == "__main__":
    test_validation()
    test_logger()
    test_existing_pages()
