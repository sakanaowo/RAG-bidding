"""
Chunking Integration Tests

Test both chunking strategies with real documents from all loaders:
- HierarchicalChunker: Legal documents (Luật, Nghị định, Thông tư)
- SemanticChunker: Bidding, Report, Exam documents

Run:
    pytest scripts/test/test_chunking_integration.py -v -s
    pytest scripts/test/test_chunking_integration.py -v -k "hierarchical"
"""

import pytest
from pathlib import Path
from typing import List

from src.preprocessing.loaders import (
    DocxLoader,
    BiddingLoader,
    ReportLoader,
    PdfLoader,
)
from src.preprocessing.base.models import ProcessedDocument
from src.chunking import (
    HierarchicalChunker,
    SemanticChunker,
    ChunkFactory,
    UniversalChunk,
)


# ============================================================
# FIXTURES
# ============================================================


@pytest.fixture
def data_dir():
    """Root data directory"""
    return Path("/home/sakana/Code/RAG-bidding/data/raw")


# ============================================================
# HELPER FUNCTIONS
# ============================================================


def raw_to_processed(raw_content, doc_type: str, file_path: str) -> ProcessedDocument:
    """Convert Raw*Content to ProcessedDocument for chunking"""
    from datetime import datetime
    import os
    import re

    metadata = {
        "document_type": doc_type,
        "file_path": file_path,
        "title": raw_content.metadata.get("title", "Unknown"),
        "processed_at": datetime.now().isoformat(),
    }

    # Copy metadata
    if hasattr(raw_content, "metadata"):
        metadata.update(raw_content.metadata)

    # Add legal_metadata for legal documents with proper legal_id
    if doc_type in ["law", "decree", "circular", "decision"]:
        filename = os.path.basename(file_path)

        # Try to extract legal_id from filename
        # Pattern: "ND 214 - 4.8.2025" → "214/2025/NĐ-CP"
        if "ND" in filename or "NĐ" in filename:
            # Extract number and year
            match = re.search(r"(\d+).*?(\d{4})", filename)
            if match:
                number = match.group(1)
                year = match.group(2)
                legal_id = f"{number}/{year}/NĐ-CP"
            else:
                legal_id = f"unknown/{datetime.now().year}/NĐ-CP"
        elif "TT" in filename:
            match = re.search(r"(\d+).*?(\d{4})", filename)
            if match:
                number = match.group(1)
                year = match.group(2)
                legal_id = f"{number}/{year}/TT-BKHĐT"
            else:
                legal_id = f"unknown/{datetime.now().year}/TT-BKHĐT"
        else:
            # Default format
            legal_id = f"1/{datetime.now().year}/QĐ-TTg"

        metadata["legal_metadata"] = {
            "legal_id": legal_id,
            "legal_level": 3,  # Decree level
            "status": "active",
            "domain": ["dau_thau"],
        }
        metadata["issued_by"] = "chinh_phu"
        metadata["issued_date"] = datetime.now().date()

    # Build content - use "full_text" key for chunkers
    content = {
        "full_text": raw_content.text,  # Changed from "text" to "full_text"
    }

    if hasattr(raw_content, "structure"):
        content["structure"] = raw_content.structure
    if hasattr(raw_content, "tables"):
        content["tables"] = raw_content.tables
    if hasattr(raw_content, "statistics"):
        content["statistics"] = raw_content.statistics

    return ProcessedDocument(metadata=metadata, content=content)


def print_chunk_stats(chunks: List[UniversalChunk], doc_type: str):
    """Print statistics about chunks"""
    if not chunks:
        print(f"  ✗ No chunks generated for {doc_type}")
        return

    sizes = [c.char_count for c in chunks]
    avg_size = sum(sizes) / len(sizes)
    in_range = sum(1 for s in sizes if 300 <= s <= 1500)
    ratio = in_range / len(sizes) * 100

    print(f"\n  Chunks: {len(chunks)}")
    print(f"  Size range: {min(sizes)} - {max(sizes)} chars")
    print(f"  Average: {avg_size:.0f} chars")
    print(f"  In range (300-1500): {in_range}/{len(chunks)} ({ratio:.0f}%)")

    # Show levels
    levels = {}
    for chunk in chunks:
        level = chunk.level
        levels[level] = levels.get(level, 0) + 1
    print(f"  Levels: {levels}")


# ============================================================
# TEST: HIERARCHICAL CHUNKER
# ============================================================


def test_hierarchical_chunker_decree(data_dir):
    """Test HierarchicalChunker with real decree document"""
    print("\n" + "=" * 70)
    print("TEST: HierarchicalChunker - Decree Document")
    print("=" * 70)

    # Load decree
    decree_dir = data_dir / "Nghi dinh"
    files = list(decree_dir.glob("*.docx"))

    if not files:
        pytest.skip("No decree files found")

    loader = DocxLoader()
    raw = loader.load(str(files[0]))
    doc = raw_to_processed(raw, "decree", str(files[0]))

    print(f"\nDocument: {doc.metadata.get('title', 'Unknown')}")
    print(f"File: {files[0].name}")
    print(f"Content: {len(doc.content['full_text']):,} chars")

    # Chunk
    chunker = HierarchicalChunker(min_size=300, max_size=1500, target_size=800)
    chunks = chunker.chunk(doc)

    # Validate
    assert len(chunks) > 0, "No chunks generated"
    assert all(isinstance(c, UniversalChunk) for c in chunks)
    assert all(c.document_type == "decree" for c in chunks)

    # Print stats
    print_chunk_stats(chunks, "decree")

    # Check hierarchy
    has_hierarchy = sum(1 for c in chunks if c.hierarchy)
    print(f"  Chunks with hierarchy: {has_hierarchy}/{len(chunks)}")

    # Check for Điều level
    dieu_chunks = [c for c in chunks if c.level == "dieu"]
    print(f"  Điều chunks: {len(dieu_chunks)}")

    assert len(dieu_chunks) > 0, "No Điều-level chunks found"


def test_hierarchical_chunker_circular(data_dir):
    """Test HierarchicalChunker with circular document"""
    print("\n" + "=" * 70)
    print("TEST: HierarchicalChunker - Circular Document")
    print("=" * 70)

    circular_dir = data_dir / "Thong tu"
    files = list(circular_dir.glob("*.docx"))

    if not files:
        pytest.skip("No circular files found")

    loader = DocxLoader()
    raw = loader.load(str(files[0]))
    doc = raw_to_processed(raw, "circular", str(files[0]))

    print(f"\nDocument: {doc.metadata.get('title', 'Unknown')}")

    chunker = HierarchicalChunker()
    chunks = chunker.chunk(doc)

    assert len(chunks) > 0
    print_chunk_stats(chunks, "circular")


def test_hierarchical_chunker_batch(data_dir):
    """Test HierarchicalChunker with batch of legal documents"""
    print("\n" + "=" * 70)
    print("TEST: HierarchicalChunker - Batch Processing")
    print("=" * 70)

    loader = DocxLoader()
    chunker = HierarchicalChunker()

    # Test decree and circular
    test_dirs = [
        ("Nghi dinh", "decree"),
        ("Thong tu", "circular"),
    ]

    total_chunks = 0
    total_docs = 0

    for dir_name, doc_type in test_dirs:
        doc_dir = data_dir / dir_name
        if not doc_dir.exists():
            continue

        files = list(doc_dir.glob("*.docx"))[:2]  # Max 2 per type

        for file_path in files:
            try:
                raw = loader.load(str(file_path))
                doc = raw_to_processed(raw, doc_type, str(file_path))
                chunks = chunker.chunk(doc)

                total_chunks += len(chunks)
                total_docs += 1

                print(f"\n  ✓ {doc_type}: {file_path.name[:40]}")
                print(f"    Chunks: {len(chunks)}")

            except Exception as e:
                print(f"\n  ✗ {doc_type}: {file_path.name[:40]}")
                print(f"    Error: {str(e)[:80]}")

    print(f"\n{'='*70}")
    print(f"BATCH SUMMARY:")
    print(f"  Documents processed: {total_docs}")
    print(f"  Total chunks: {total_chunks}")
    if total_docs > 0:
        print(f"  Average chunks/doc: {total_chunks/total_docs:.1f}")
    print(f"{'='*70}")

    assert total_docs > 0, "No documents processed"
    assert total_chunks > 0, "No chunks generated"


# ============================================================
# TEST: SEMANTIC CHUNKER
# ============================================================


def test_semantic_chunker_bidding(data_dir):
    """Test SemanticChunker with bidding document"""
    print("\n" + "=" * 70)
    print("TEST: SemanticChunker - Bidding Document")
    print("=" * 70)

    bidding_dir = data_dir / "Ho so moi thau"
    files = list(bidding_dir.rglob("*.docx"))

    if not files:
        pytest.skip("No bidding files found")

    loader = BiddingLoader()
    raw = loader.load(str(files[0]))
    doc = raw_to_processed(raw, "bidding", str(files[0]))

    print(f"\nDocument: {doc.metadata.get('title', 'Unknown')}")
    print(f"File: {files[0].name}")

    chunker = SemanticChunker(min_size=300, max_size=1500, target_size=800)
    chunks = chunker.chunk(doc)

    assert len(chunks) > 0
    assert all(c.document_type == "bidding" for c in chunks)

    print_chunk_stats(chunks, "bidding")


def test_semantic_chunker_report(data_dir):
    """Test SemanticChunker with report document"""
    print("\n" + "=" * 70)
    print("TEST: SemanticChunker - Report Document")
    print("=" * 70)

    report_dir = data_dir / "Mau bao cao"
    files = list(report_dir.rglob("*.docx"))

    if not files:
        pytest.skip("No report files found")

    loader = ReportLoader()
    raw = loader.load(str(files[0]))
    doc = raw_to_processed(raw, "report", str(files[0]))

    print(f"\nDocument: {doc.metadata.get('title', 'Unknown')}")

    chunker = SemanticChunker()
    chunks = chunker.chunk(doc)

    assert len(chunks) > 0
    assert all(c.document_type == "report" for c in chunks)

    print_chunk_stats(chunks, "report")


def test_semantic_chunker_exam(data_dir):
    """Test SemanticChunker with exam document"""
    print("\n" + "=" * 70)
    print("TEST: SemanticChunker - Exam Document")
    print("=" * 70)

    exam_dir = data_dir / "Cau hoi thi"
    files = list(exam_dir.glob("*.pdf"))

    if not files:
        pytest.skip("No exam files found")

    loader = PdfLoader()
    raw = loader.load(str(files[0]))
    doc = raw_to_processed(raw, "exam_questions", str(files[0]))

    print(f"\nDocument: {doc.metadata.get('title', 'Unknown')}")

    chunker = SemanticChunker()
    chunks = chunker.chunk(doc)

    assert len(chunks) > 0
    assert all(c.document_type == "exam_questions" for c in chunks)

    print_chunk_stats(chunks, "exam_questions")

    # Check for question chunks
    question_chunks = [c for c in chunks if c.level == "question"]
    print(f"  Question chunks: {len(question_chunks)}")


def test_semantic_chunker_batch(data_dir):
    """Test SemanticChunker with batch of non-legal documents"""
    print("\n" + "=" * 70)
    print("TEST: SemanticChunker - Batch Processing")
    print("=" * 70)

    chunker = SemanticChunker()

    # Test different document types
    tests = [
        ("Ho so moi thau", BiddingLoader(), "bidding_template", True),
        ("Mau bao cao", ReportLoader(), "report_template", True),
        ("Cau hoi thi", PdfLoader(), "exam_questions", False),
    ]

    total_chunks = 0
    total_docs = 0

    for dir_name, loader, doc_type, recursive in tests:
        doc_dir = data_dir / dir_name
        if not doc_dir.exists():
            continue

        if recursive:
            files = list(
                doc_dir.rglob("*.docx" if doc_type != "exam_questions" else "*.pdf")
            )[:2]
        else:
            files = list(doc_dir.glob("*.pdf"))[:1]

        for file_path in files:
            try:
                raw = loader.load(str(file_path))
                doc = raw_to_processed(raw, doc_type, str(file_path))
                chunks = chunker.chunk(doc)

                total_chunks += len(chunks)
                total_docs += 1

                print(f"\n  ✓ {doc_type}: {file_path.name[:40]}")
                print(f"    Chunks: {len(chunks)}")

            except Exception as e:
                print(f"\n  ✗ {doc_type}: {file_path.name[:40]}")
                print(f"    Error: {str(e)[:80]}")

    print(f"\n{'='*70}")
    print(f"BATCH SUMMARY:")
    print(f"  Documents processed: {total_docs}")
    print(f"  Total chunks: {total_chunks}")
    if total_docs > 0:
        print(f"  Average chunks/doc: {total_chunks/total_docs:.1f}")
    print(f"{'='*70}")

    assert total_docs > 0, "No documents processed"
    assert total_chunks > 0, "No chunks generated"


# ============================================================
# TEST: FULL PIPELINE
# ============================================================


def test_full_pipeline_all_types(data_dir):
    """
    Full pipeline integration test:
    1. Load documents with appropriate loaders
    2. Chunk with appropriate chunker
    3. Convert to UnifiedLegalChunk
    """
    print("\n" + "=" * 70)
    print("FULL PIPELINE INTEGRATION TEST")
    print("=" * 70)

    hierarchical_chunker = HierarchicalChunker()
    semantic_chunker = SemanticChunker()
    factory = ChunkFactory()

    # Test cases
    test_cases = [
        ("Nghi dinh", DocxLoader(), hierarchical_chunker, "decree", "*.docx", False),
        ("Thong tu", DocxLoader(), hierarchical_chunker, "circular", "*.docx", False),
        (
            "Ho so moi thau",
            BiddingLoader(),
            semantic_chunker,
            "bidding_template",
            "*.docx",
            True,
        ),
        (
            "Mau bao cao",
            ReportLoader(),
            semantic_chunker,
            "report_template",
            "*.docx",
            True,
        ),
        (
            "Cau hoi thi",
            PdfLoader(),
            semantic_chunker,
            "exam_questions",
            "*.pdf",
            False,
        ),
    ]

    results = {}

    for dir_name, loader, chunker, doc_type, pattern, recursive in test_cases:
        doc_dir = data_dir / dir_name

        if not doc_dir.exists():
            print(f"\n{doc_type.upper()}: Directory not found - SKIP")
            continue

        print(f"\n{doc_type.upper()}:")

        # Find file
        if recursive:
            files = list(doc_dir.rglob(pattern))
        else:
            files = list(doc_dir.glob(pattern))

        if not files:
            print(f"  No files found - SKIP")
            continue

        try:
            # 1. Load
            raw = loader.load(str(files[0]))
            doc = raw_to_processed(raw, doc_type, str(files[0]))
            print(f"  ✓ Load: {files[0].name[:40]}")

            # 2. Chunk
            chunks = chunker.chunk(doc)
            print(f"  ✓ Chunk: {len(chunks)} chunks")

            # 3. Convert
            unified = factory.convert_batch(chunks, doc)
            print(f"  ✓ Convert: {len(unified)} unified chunks")

            results[doc_type] = {
                "file": files[0].name,
                "chunks": len(chunks),
                "unified": len(unified),
                "chunker": chunker.__class__.__name__,
            }

        except Exception as e:
            print(f"  ✗ ERROR: {str(e)[:80]}")

    # Summary
    print("\n" + "=" * 70)
    print("PIPELINE SUMMARY:")
    print("=" * 70)

    for doc_type, result in results.items():
        print(f"\n{doc_type.upper()}:")
        print(f"  File: {result['file'][:50]}")
        print(f"  Chunker: {result['chunker']}")
        print(f"  Chunks: {result['chunks']} → {result['unified']} unified")

    print(f"\n{'='*70}")
    print(f"Total document types processed: {len(results)}/5")
    print(f"{'='*70}")

    # Should process at least 3 types
    assert len(results) >= 3, f"Only processed {len(results)} document types"


if __name__ == "__main__":
    # Run with: python scripts/test/test_chunking_integration.py
    pytest.main([__file__, "-v", "-s"])
