#!/usr/bin/env python3
"""
Test Data Integrity Validator

Comprehensive test cho integrity validation
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.preprocessing.decree_preprocessing.validators import (
    DataIntegrityValidator,
    IntegrityReport,
)


def test_perfect_data():
    """Test with perfect data - should pass all checks"""
    print("\n" + "=" * 70)
    print("TEST 1: Perfect Data")
    print("=" * 70)
    
    validator = DataIntegrityValidator(min_coverage=0.75, max_duplication=0.05)
    
    original_text = """
    Điều 1. Phạm vi điều chỉnh
    1. Nghị định này quy định...
    
    Điều 2. Đối tượng áp dụng
    1. Nghị định này áp dụng...
    """
    
    chunks = [
        {
            "chunk_id": "test_001",
            "content": "Điều 1. Phạm vi điều chỉnh\n1. Nghị định này quy định...",
            "doc_id": "test",
            "doc_type": "decree",
            "doc_number": "1",
            "doc_year": "2025",
            "doc_name": "Test Decree",
            "status": "active",
            "chunk_index": 0,
            "total_chunks": 2,
        },
        {
            "chunk_id": "test_002",
            "content": "Điều 2. Đối tượng áp dụng\n1. Nghị định này áp dụng...",
            "doc_id": "test",
            "doc_type": "decree",
            "doc_number": "1",
            "doc_year": "2025",
            "doc_name": "Test Decree",
            "status": "active",
            "chunk_index": 1,
            "total_chunks": 2,
        },
    ]
    
    report = validator.validate(original_text, chunks)
    
    print(report)
    assert report.is_valid, "Perfect data should pass validation"
    print("✅ PASSED")


def test_low_coverage():
    """Test with low coverage - should fail"""
    print("\n" + "=" * 70)
    print("TEST 2: Low Coverage (Data Loss)")
    print("=" * 70)
    
    validator = DataIntegrityValidator(min_coverage=0.85)
    
    original_text = """
    Điều 1. Phạm vi điều chỉnh
    1. Nghị định này quy định...
    
    Điều 2. Đối tượng áp dụng
    1. Nghị định này áp dụng...
    
    Điều 3. Giải thích từ ngữ
    1. Trong Nghị định này...
    """
    
    # Only 1 chunk from 3 articles = ~33% coverage
    chunks = [
        {
            "chunk_id": "test_001",
            "content": "Điều 1. Phạm vi điều chỉnh",
            "doc_id": "test",
            "doc_type": "decree",
            "doc_number": "1",
            "doc_year": "2025",
            "doc_name": "Test Decree",
            "status": "active",
            "chunk_index": 0,
            "total_chunks": 1,
        },
    ]
    
    report = validator.validate(original_text, chunks)
    
    print(report)
    assert not report.is_valid, "Low coverage should fail validation"
    assert "Coverage too low" in str(report.errors), "Should report coverage issue"
    print("✅ PASSED (correctly detected low coverage)")


def test_duplication():
    """Test with duplicate chunks - should warn"""
    print("\n" + "=" * 70)
    print("TEST 3: Duplicate Chunks")
    print("=" * 70)
    
    validator = DataIntegrityValidator(max_duplication=0.05)
    
    original_text = "Điều 1. Test content"
    
    # 2 identical chunks
    chunks = [
        {
            "chunk_id": "test_001",
            "content": "Điều 1. Test content",
            "doc_id": "test",
            "doc_type": "decree",
            "doc_number": "1",
            "doc_year": "2025",
            "doc_name": "Test",
            "status": "active",
            "chunk_index": 0,
            "total_chunks": 2,
        },
        {
            "chunk_id": "test_002",
            "content": "Điều 1. Test content",  # Duplicate
            "doc_id": "test",
            "doc_type": "decree",
            "doc_number": "1",
            "doc_year": "2025",
            "doc_name": "Test",
            "status": "active",
            "chunk_index": 1,
            "total_chunks": 2,
        },
    ]
    
    report = validator.validate(original_text, chunks)
    
    print(report)
    assert len(report.warnings) > 0, "Should have duplication warning"
    print("✅ PASSED (correctly detected duplication)")


def test_missing_sections():
    """Test with missing Điều - should detect"""
    print("\n" + "=" * 70)
    print("TEST 4: Missing Sections")
    print("=" * 70)
    
    validator = DataIntegrityValidator()
    
    original_text = """
    Điều 1. First article
    Điều 2. Second article
    Điều 3. Third article
    Điều 4. Fourth article
    """
    
    # Missing Điều 2 and 3
    chunks = [
        {
            "chunk_id": "test_001",
            "content": "Điều 1. First article",
            "doc_id": "test",
            "doc_type": "decree",
            "doc_number": "1",
            "doc_year": "2025",
            "doc_name": "Test",
            "status": "active",
            "chunk_index": 0,
            "total_chunks": 2,
        },
        {
            "chunk_id": "test_002",
            "content": "Điều 4. Fourth article",
            "doc_id": "test",
            "doc_type": "decree",
            "doc_number": "1",
            "doc_year": "2025",
            "doc_name": "Test",
            "status": "active",
            "chunk_index": 1,
            "total_chunks": 2,
        },
    ]
    
    report = validator.validate(original_text, chunks)
    
    print(report)
    assert len(report.missing_sections) == 2, "Should detect 2 missing Điều"
    assert "Điều 2" in report.missing_sections
    assert "Điều 3" in report.missing_sections
    print(f"✅ PASSED (detected missing: {report.missing_sections})")


def test_incomplete_metadata():
    """Test with incomplete metadata - should fail"""
    print("\n" + "=" * 70)
    print("TEST 5: Incomplete Metadata")
    print("=" * 70)
    
    validator = DataIntegrityValidator()
    
    original_text = "Test content"
    
    chunks = [
        {
            "chunk_id": "test_001",
            "content": "Test content",
            # Missing required fields
        },
    ]
    
    report = validator.validate(original_text, chunks)
    
    print(report)
    assert not report.is_valid, "Incomplete metadata should fail"
    assert not report.metadata_complete
    print("✅ PASSED (correctly detected incomplete metadata)")


def test_chunk_quality():
    """Test chunk quality checks"""
    print("\n" + "=" * 70)
    print("TEST 6: Chunk Quality")
    print("=" * 70)
    
    validator = DataIntegrityValidator()
    
    original_text = "X" * 1000
    
    chunks = [
        {
            "chunk_id": "test_001",
            "content": "X",  # Too short
            "doc_id": "test",
            "doc_type": "decree",
            "doc_number": "1",
            "doc_year": "2025",
            "doc_name": "Test",
            "status": "active",
            "chunk_index": 0,
            "total_chunks": 1,
        },
    ]
    
    report = validator.validate(original_text, chunks)
    
    print(report)
    assert len(report.warnings) > 0, "Should warn about chunk quality"
    print("✅ PASSED (detected quality issues)")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("DATA INTEGRITY VALIDATOR - COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    
    tests = [
        test_perfect_data,
        test_low_coverage,
        test_duplication,
        test_missing_sections,
        test_incomplete_metadata,
        test_chunk_quality,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"FINAL RESULTS: {passed}/{len(tests)} tests passed")
    print("=" * 70)
    
    if failed == 0:
        print("\n✅ ALL TESTS PASSED!")
    else:
        print(f"\n❌ {failed} TESTS FAILED")
        sys.exit(1)
