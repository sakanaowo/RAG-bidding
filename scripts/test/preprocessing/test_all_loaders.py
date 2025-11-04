"""
Comprehensive Loader Tests

Test all document loaders with real documents from data/raw.
Loaders return Raw*Content objects which contain text, metadata, and structure.

Run:
    pytest scripts/test/test_all_loaders.py -v
    pytest scripts/test/test_all_loaders.py -v -s  # Show detailed output
"""

import pytest
from pathlib import Path

from src.preprocessing.loaders import (
    DocxLoader,
    BiddingLoader,
    ReportLoader,
    PdfLoader,
    RawDocxContent,
    RawBiddingContent,
    RawReportContent,
    RawPdfContent,
)


# ============================================================
# FIXTURES
# ============================================================


@pytest.fixture
def data_dir():
    """Root data directory"""
    return Path("/home/sakana/Code/RAG-bidding/data/raw")


# ============================================================
# TEST: DOCX LOADER
# ============================================================


def test_docx_loader_with_real_decree(data_dir):
    """Test DocxLoader with real decree document"""
    decree_dir = data_dir / "Nghi dinh"
    files = list(decree_dir.glob("*.docx"))

    if not files:
        pytest.skip("No decree files found")

    print(f"\nTesting: {files[0].name}")

    loader = DocxLoader()
    result = loader.load(str(files[0]))

    # Validate type
    assert isinstance(result, RawDocxContent)

    # Validate fields
    assert len(result.text) > 0
    assert isinstance(result.metadata, dict)
    assert isinstance(result.structure, list)
    assert isinstance(result.tables, list)
    assert isinstance(result.statistics, dict)

    # Print stats
    print(f"✓ Loaded decree successfully")
    print(f"  Title: {result.metadata.get('title', 'Unknown')}")
    print(f"  Content: {len(result.text):,} chars")
    print(f"  Structure elements: {len(result.structure)}")
    print(f"  Tables: {len(result.tables)}")
    print(f"  Điều count: {result.statistics.get('dieu_count', 0)}")
    print(f"  Chương count: {result.statistics.get('chuong_count', 0)}")


def test_docx_loader_batch_legal_docs(data_dir):
    """Test DocxLoader with batch of legal documents"""
    print("\n" + "=" * 70)
    print("BATCH TEST: Legal Documents (Luật, Nghị định, Thông tư)")
    print("=" * 70)

    loader = DocxLoader()

    # Test dirs
    test_dirs = [
        ("Luat chinh", "law"),
        ("Nghi dinh", "decree"),
        ("Thong tu", "circular"),
    ]

    total_loaded = 0
    total_chars = 0

    for dir_name, doc_type in test_dirs:
        doc_dir = data_dir / dir_name
        if not doc_dir.exists():
            print(f"\n{doc_type.upper()}: Directory not found - SKIP")
            continue

        files = list(doc_dir.glob("*.docx"))[:2]  # Max 2 per type

        if not files:
            print(f"\n{doc_type.upper()}: No files - SKIP")
            continue

        print(f"\n{doc_type.upper()}:")

        for file_path in files:
            try:
                result = loader.load(str(file_path))
                total_loaded += 1
                total_chars += len(result.text)

                print(f"  ✓ {file_path.name[:50]}")
                print(
                    f"    - {len(result.text):,} chars, {len(result.structure)} structure elements"
                )

            except Exception as e:
                print(f"  ✗ {file_path.name[:50]}")
                print(f"    - Error: {str(e)[:80]}")

    print(f"\n{'='*70}")
    print(f"SUMMARY: Loaded {total_loaded} documents, {total_chars:,} total chars")
    print(f"{'='*70}")

    assert total_loaded > 0, "No documents loaded"


# ============================================================
# TEST: BIDDING LOADER
# ============================================================


def test_bidding_loader_with_real_template(data_dir):
    """Test BiddingLoader with real bidding template"""
    bidding_dir = data_dir / "Ho so moi thau"
    files = list(bidding_dir.rglob("*.docx"))

    if not files:
        pytest.skip("No bidding files found")

    print(f"\nTesting: {files[0].name}")

    loader = BiddingLoader()
    result = loader.load(str(files[0]))

    # Validate type
    assert isinstance(result, RawBiddingContent)

    # Validate fields
    assert len(result.text) > 0
    assert isinstance(result.metadata, dict)

    # Print stats
    print(f"✓ Loaded bidding template")
    print(f"  Title: {result.metadata.get('title', 'Unknown')}")
    print(f"  Content: {len(result.text):,} chars")


def test_bidding_loader_batch(data_dir):
    """Test BiddingLoader with multiple templates"""
    print("\n" + "=" * 70)
    print("BATCH TEST: Bidding Templates")
    print("=" * 70)

    bidding_dir = data_dir / "Ho so moi thau"

    if not bidding_dir.exists():
        pytest.skip("Bidding directory not found")

    loader = BiddingLoader()
    files = list(bidding_dir.rglob("*.docx"))[:5]  # Max 5

    if not files:
        pytest.skip("No bidding files found")

    total_loaded = 0

    for file_path in files:
        try:
            result = loader.load(str(file_path))
            total_loaded += 1

            print(f"  ✓ {file_path.name[:60]}")
            print(f"    - {len(result.text):,} chars")

        except Exception as e:
            print(f"  ✗ {file_path.name[:60]}")
            print(f"    - Error: {str(e)[:80]}")

    print(f"\n{'='*70}")
    print(f"SUMMARY: Loaded {total_loaded}/{len(files)} bidding templates")
    print(f"{'='*70}")

    assert total_loaded > 0


# ============================================================
# TEST: REPORT LOADER
# ============================================================


def test_report_loader_with_real_template(data_dir):
    """Test ReportLoader with real report template"""
    report_dir = data_dir / "Mau bao cao"
    files = list(report_dir.rglob("*.docx"))

    if not files:
        pytest.skip("No report files found")

    print(f"\nTesting: {files[0].name}")

    loader = ReportLoader()
    result = loader.load(str(files[0]))

    # Validate type
    assert isinstance(result, RawReportContent)

    # Validate fields
    assert len(result.text) > 0
    assert isinstance(result.metadata, dict)

    # Print stats
    print(f"✓ Loaded report template")
    print(f"  Title: {result.metadata.get('title', 'Unknown')}")
    print(f"  Content: {len(result.text):,} chars")


def test_report_loader_batch(data_dir):
    """Test ReportLoader with multiple templates"""
    print("\n" + "=" * 70)
    print("BATCH TEST: Report Templates")
    print("=" * 70)

    report_dir = data_dir / "Mau bao cao"

    if not report_dir.exists():
        pytest.skip("Report directory not found")

    loader = ReportLoader()
    files = list(report_dir.rglob("*.docx"))[:5]  # Max 5

    if not files:
        pytest.skip("No report files found")

    total_loaded = 0

    for file_path in files:
        try:
            result = loader.load(str(file_path))
            total_loaded += 1

            print(f"  ✓ {file_path.name[:60]}")
            print(f"    - {len(result.text):,} chars")

        except Exception as e:
            print(f"  ✗ {file_path.name[:60]}")
            print(f"    - Error: {str(e)[:80]}")

    print(f"\n{'='*70}")
    print(f"SUMMARY: Loaded {total_loaded}/{len(files)} report templates")
    print(f"{'='*70}")

    assert total_loaded > 0


# ============================================================
# TEST: PDF LOADER
# ============================================================


def test_pdf_loader_with_real_exam(data_dir):
    """Test PdfLoader with real exam questions"""
    exam_dir = data_dir / "Cau hoi thi"
    files = list(exam_dir.glob("*.pdf"))

    if not files:
        pytest.skip("No exam PDF files found")

    print(f"\nTesting: {files[0].name}")

    loader = PdfLoader()
    result = loader.load(str(files[0]))

    # Validate type
    assert isinstance(result, RawPdfContent)

    # Validate fields
    assert len(result.text) > 0
    assert isinstance(result.metadata, dict)

    # Print stats
    print(f"✓ Loaded exam PDF")
    print(f"  Title: {result.metadata.get('title', 'Unknown')}")
    print(f"  Content: {len(result.text):,} chars")


def test_pdf_loader_batch(data_dir):
    """Test PdfLoader with multiple exam PDFs"""
    print("\n" + "=" * 70)
    print("BATCH TEST: Exam PDFs")
    print("=" * 70)

    exam_dir = data_dir / "Cau hoi thi"

    if not exam_dir.exists():
        pytest.skip("Exam directory not found")

    loader = PdfLoader()
    files = list(exam_dir.glob("*.pdf"))[:3]  # Max 3

    if not files:
        pytest.skip("No exam PDF files found")

    total_loaded = 0

    for file_path in files:
        try:
            result = loader.load(str(file_path))
            total_loaded += 1

            print(f"  ✓ {file_path.name[:60]}")
            print(f"    - {len(result.text):,} chars")

        except Exception as e:
            print(f"  ✗ {file_path.name[:60]}")
            print(f"    - Error: {str(e)[:80]}")

    print(f"\n{'='*70}")
    print(f"SUMMARY: Loaded {total_loaded}/{len(files)} exam PDFs")
    print(f"{'='*70}")

    assert total_loaded > 0


# ============================================================
# TEST: ALL LOADERS INTEGRATION
# ============================================================


def test_all_loaders_integration(data_dir):
    """Integration test: Load samples from all document types"""
    print("\n" + "=" * 70)
    print("INTEGRATION TEST: All Loaders")
    print("=" * 70)

    loaders_and_dirs = [
        (DocxLoader(), data_dir / "Luat chinh", "*.docx", "LAW", RawDocxContent),
        (DocxLoader(), data_dir / "Nghi dinh", "*.docx", "DECREE", RawDocxContent),
        (DocxLoader(), data_dir / "Thong tu", "*.docx", "CIRCULAR", RawDocxContent),
        (
            BiddingLoader(),
            data_dir / "Ho so moi thau",
            "*.docx",
            "BIDDING",
            RawBiddingContent,
        ),
        (
            ReportLoader(),
            data_dir / "Mau bao cao",
            "*.docx",
            "REPORT",
            RawReportContent,
        ),
        (PdfLoader(), data_dir / "Cau hoi thi", "*.pdf", "EXAM", RawPdfContent),
    ]

    results = {}

    for loader, doc_dir, pattern, doc_type, expected_type in loaders_and_dirs:
        if not doc_dir.exists():
            print(f"\n{doc_type}: Directory not found - SKIP")
            continue

        print(f"\n{doc_type}:")

        # Find files
        if doc_type in ["BIDDING", "REPORT"]:
            files = list(doc_dir.rglob(pattern))
        else:
            files = list(doc_dir.glob(pattern))

        if not files:
            print(f"  No files found - SKIP")
            continue

        # Load first file
        try:
            result = loader.load(str(files[0]))

            # Validate type
            assert isinstance(result, expected_type)

            results[doc_type] = result

            print(f"  ✓ File: {files[0].name[:50]}")
            print(f"  ✓ Title: {result.metadata.get('title', 'Unknown')[:50]}")
            print(f"  ✓ Content: {len(result.text):,} chars")

        except Exception as e:
            print(f"  ✗ ERROR: {str(e)[:80]}")

    # Summary
    print("\n" + "=" * 70)
    print(f"SUMMARY: Successfully loaded {len(results)}/6 document types")
    print("=" * 70)

    for doc_type in results:
        print(f"  ✓ {doc_type}")

    # Should have loaded at least 3 types
    assert len(results) >= 3, f"Only loaded {len(results)} document types"


if __name__ == "__main__":
    # Run with: python scripts/test/test_all_loaders.py
    pytest.main([__file__, "-v", "-s"])
