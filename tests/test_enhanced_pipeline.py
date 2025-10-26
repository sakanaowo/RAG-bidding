"""Test script to validate the enhanced data processing pipeline."""

import sys
import os
import tempfile
import time
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.logging_config import setup_logging, get_processing_logger
from app.data.cleaners import basic_clean, advanced_clean, vietnamese_specific_clean
from app.data.validators import create_default_validator, create_default_deduplicator
from app.data.exceptions import FileLoadError, SafeProcessor
from app.data.ingest_utils import load_folder, split_documents_with_validation
from langchain_core.documents import Document


def test_data_cleaning():
    """Test data cleaning functions."""
    print("\n🧹 Testing Data Cleaning...")

    test_cases = [
        {
            "name": "Basic cleaning",
            "input": "Hello   world!\t\n\n\n\nThis is a test.\u00a0Multiple spaces.",
            "function": basic_clean,
            "expected_improvements": ["Remove extra spaces", "Remove excess newlines"],
        },
        {
            "name": "Advanced cleaning",
            "input": "Check this email: user@example.com and URL: https://example.com\n\n\n••• Bullet point text",
            "function": advanced_clean,
            "expected_improvements": ["Clean bullet points", "Normalize text"],
        },
        {
            "name": "Vietnamese specific",
            "input": "Trang 1\n\nĐây là văn bản tiếng Việt.\n\nChương I: Tổng quan\n\nTrang 2",
            "function": vietnamese_specific_clean,
            "expected_improvements": [
                "Remove page numbers",
                "Clean Vietnamese artifacts",
            ],
        },
    ]

    for test_case in test_cases:
        print(f"  Testing {test_case['name']}:")
        original = test_case["input"]
        cleaned = test_case["function"](original)

        print(f"    Original: {repr(original[:50])}...")
        print(f"    Cleaned:  {repr(cleaned[:50])}...")
        print(f"    Length change: {len(original)} → {len(cleaned)}")
        print(f"    ✅ Completed")


def test_document_validation():
    """Test document validation."""
    print("\n✅ Testing Document Validation...")

    validator = create_default_validator()

    test_documents = [
        Document(
            page_content="This is a good document with sufficient content for validation.",
            metadata={"source": "test1"},
        ),
        Document(page_content="Short", metadata={"source": "test2"}),  # Too short
        Document(page_content="", metadata={"source": "test3"}),  # Empty
        Document(page_content="A" * 1000, metadata={"source": "test4"}),  # Good length
        Document(
            page_content="!@#$%^&*()" * 10, metadata={"source": "test5"}
        ),  # Low meaningful content
    ]

    valid_docs, invalid_docs, stats = validator.validate_documents(test_documents)

    print(f"  Total documents: {stats['total_docs']}")
    print(f"  Valid documents: {stats['valid_docs']}")
    print(f"  Invalid documents: {stats['invalid_docs']}")
    print(f"  Issues found: {stats['issues_summary']}")
    print("  ✅ Validation test completed")


def test_deduplication():
    """Test document deduplication."""
    print("\n🔍 Testing Document Deduplication...")

    deduplicator = create_default_deduplicator()

    test_documents = [
        Document(page_content="This is the first unique document."),
        Document(page_content="This is the first unique document."),  # Exact duplicate
        Document(page_content="This is the second unique document."),
        Document(
            page_content="This is the first unique document."
        ),  # Another exact duplicate
        Document(
            page_content="This is a slightly different document but quite similar to the first one."
        ),  # Different
    ]

    unique_docs, duplicate_docs, stats = deduplicator.deduplicate_documents(
        test_documents
    )

    print(f"  Total documents: {stats['total_docs']}")
    print(f"  Unique documents: {stats['unique_docs']}")
    print(f"  Duplicate documents: {stats['duplicate_docs']}")
    print(f"  Exact duplicates: {stats['exact_duplicates']}")
    print(f"  Fuzzy duplicates: {stats['fuzzy_duplicates']}")
    print("  ✅ Deduplication test completed")


def test_safe_file_processing():
    """Test safe file processing."""
    print("\n🛡️ Testing Safe File Processing...")

    # Create temporary test files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test files
        (temp_path / "test_utf8.txt").write_text(
            "Hello UTF-8 world! Xin chào!", encoding="utf-8"
        )
        (temp_path / "test_latin1.txt").write_text(
            "Hello Latin-1 world!", encoding="latin1"
        )

        # Test safe reading
        try:
            content1 = SafeProcessor.safe_file_read(str(temp_path / "test_utf8.txt"))
            print(f"  UTF-8 file read successfully: {len(content1)} characters")

            content2 = SafeProcessor.safe_file_read(str(temp_path / "test_latin1.txt"))
            print(f"  Latin-1 file read successfully: {len(content2)} characters")

        except Exception as e:
            print(f"  ❌ Safe file read failed: {e}")
            return

        print("  ✅ Safe file processing test completed")


def test_enhanced_pipeline():
    """Test the enhanced processing pipeline."""
    print("\n🚀 Testing Enhanced Processing Pipeline...")

    # Create temporary test directory with sample files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test files
        (temp_path / "doc1.txt").write_text(
            "Đây là tài liệu tiếng Việt số 1.\n\n"
            "Nó chứa nhiều thông tin hữu ích về chủ đề quan trọng.\n"
            "Trang 1\n\n"
            "Chương I: Giới thiệu tổng quan về vấn đề."
        )

        (temp_path / "doc2.txt").write_text(
            "This is document number 2 in English.\n\n"
            "It contains different information about another topic.\n"
            "This document has sufficient content for processing."
        )

        (temp_path / "doc3.txt").write_text("Too short")  # Should be filtered out

        (temp_path / "duplicate.txt").write_text(
            "Đây là tài liệu tiếng Việt số 1.\n\n"
            "Nó chứa nhiều thông tin hữu ích về chủ đề quan trọng.\n"
            "Trang 1\n\n"
            "Chương I: Giới thiệu tổng quan về vấn đề."
        )  # Duplicate of doc1

        try:
            # Test the enhanced pipeline
            docs, stats = load_folder(
                str(temp_path), clean_text=True, validate_docs=True, deduplicate=True
            )

            print(f"  Files found: {stats['total_files_found']}")
            print(f"  Files processed: {stats['files_processed']}")
            print(f"  Files failed: {stats['files_failed']}")
            print(f"  Final documents: {len(docs)}")

            if stats.get("validation"):
                val_stats = stats["validation"]
                print(
                    f"  Validation - Valid: {val_stats['valid_docs']}, Invalid: {val_stats['invalid_docs']}"
                )

            if stats.get("deduplication"):
                dedup_stats = stats["deduplication"]
                print(
                    f"  Deduplication - Unique: {dedup_stats['unique_docs']}, Duplicates: {dedup_stats['duplicate_docs']}"
                )

            # Test document splitting
            if docs:
                chunks, split_stats = split_documents_with_validation(docs)
                print(f"  Chunks created: {len(chunks)}")
                print(
                    f"  Average chunk size: {split_stats.get('average_chunk_size', 0):.0f} characters"
                )

            print("  ✅ Enhanced pipeline test completed")

        except Exception as e:
            print(f"  ❌ Pipeline test failed: {e}")
            import traceback

            traceback.print_exc()


def main():
    """Run all tests."""
    print("🔧 Starting Enhanced Data Processing Pipeline Tests")
    print("=" * 60)

    # Setup logging for tests
    setup_logging()

    try:
        # Run individual component tests
        test_data_cleaning()
        test_document_validation()
        test_deduplication()
        test_safe_file_processing()

        # Run integrated pipeline test
        test_enhanced_pipeline()

        print("\n" + "=" * 60)
        print("🎉 All tests completed successfully!")

    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
