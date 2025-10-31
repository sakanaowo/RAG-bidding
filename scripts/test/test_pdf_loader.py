"""
Tests for PDF Loader

Tests:
1. Load exam PDF successfully
2. Metadata extraction
3. Question detection
4. Statistics calculation
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.preprocessing.loaders.pdf_loader import PdfLoader


def test_pdf_loader_basic():
    """Test loading a PDF exam document"""
    print("\n=== Test 1: Load PDF Exam Document ===")

    # Use first PDF exam file
    test_file = (
        project_root / "data/raw/Cau hoi thi/Ngân hàng câu hỏi thi CCDT đợt 1.pdf"
    )

    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return False

    try:
        loader = PdfLoader()
        content = loader.load(str(test_file))

        print(f"✅ Loaded: {content.metadata['filename']}")
        print(f"   Pages: {len(content.pages)}")
        print(f"   Total chars: {content.statistics['char_count']:,}")
        print(f"   Document type: {content.statistics['document_type']}")

        # Check basic structure
        assert len(content.text) > 0, "Text should not be empty"
        assert len(content.pages) > 0, "Should have at least 1 page"
        # Note: page_count from metadata may differ from extracted pages (blank pages skipped)
        assert content.metadata["page_count"] >= len(
            content.pages
        ), "Metadata page count should be >= extracted pages"

        print("✅ Test 1 passed")
        return True

    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_pdf_metadata():
    """Test PDF metadata extraction"""
    print("\n=== Test 2: PDF Metadata Extraction ===")

    test_file = (
        project_root / "data/raw/Cau hoi thi/Ngân hàng câu hỏi thi CCDT đợt 1.pdf"
    )

    if not test_file.exists():
        print(f"❌ Test file not found")
        return False

    try:
        loader = PdfLoader()
        content = loader.load(str(test_file))

        metadata = content.metadata

        print("📊 Metadata:")
        print(f"   Title: {metadata.get('title', 'N/A')}")
        print(f"   Author: {metadata.get('author', 'N/A')}")
        print(f"   Page count: {metadata['page_count']}")
        print(f"   Creator: {metadata.get('creator', 'N/A')}")

        # Check required fields
        assert "filename" in metadata
        assert "page_count" in metadata
        assert metadata["page_count"] > 0

        print("✅ Test 2 passed")
        return True

    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_question_detection():
    """Test exam question detection"""
    print("\n=== Test 3: Question Detection ===")

    test_file = (
        project_root / "data/raw/Cau hoi thi/Ngân hàng câu hỏi thi CCDT đợt 1.pdf"
    )

    if not test_file.exists():
        print(f"❌ Test file not found")
        return False

    try:
        loader = PdfLoader()
        content = loader.load(str(test_file))

        stats = content.statistics

        print("📝 Question Statistics:")
        print(f"   Document type: {stats['document_type']}")
        print(f"   Question count: {stats['question_count']}")
        print(f"   Answer count: {stats['answer_count']}")

        # If exam document, should detect questions
        if stats["document_type"] == "exam":
            print(f"   ✅ Detected as exam document")

            # Try to extract individual questions
            questions = loader.extract_questions(content.text)
            if questions:
                print(f"   Extracted {len(questions)} questions")

                # Show first question
                if len(questions) > 0:
                    q = questions[0]
                    print(f"\n   📌 First question:")
                    print(f"      Number: {q['number']}")
                    print(f"      Text: {q['text'][:100]}...")
                    print(f"      Options: {len(q['options'])} choices")
                    if q["answer"]:
                        print(f"      Answer: {q['answer']}")

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
        project_root / "data/raw/Cau hoi thi/Ngân hàng câu hỏi thi CCDT đợt 1.pdf"
    )

    if not test_file.exists():
        print(f"❌ Test file not found")
        return False

    try:
        loader = PdfLoader()
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
            "page_count",
            "document_type",
            "question_count",
            "answer_count",
            "avg_chars_per_page",
        ]

        for stat in required_stats:
            assert stat in stats, f"Missing statistic: {stat}"

        assert stats["page_count"] == len(content.pages)
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
    """Run all PDF loader tests"""
    print("\n" + "=" * 60)
    print("PDF LOADER TESTS")
    print("=" * 60)

    tests = [
        test_pdf_loader_basic,
        test_pdf_metadata,
        test_question_detection,
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
