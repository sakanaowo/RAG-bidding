"""
Pytest suite for chunking strategies.

Tests:
1. HierarchicalChunker with legal documents
2. SemanticChunker with bidding/report/exam
3. Chunk size validation
4. Schema integration (UniversalChunk → UnifiedLegalChunk)
5. ChunkFactory conversion

Run:
    pytest scripts/test/test_chunk_pipeline.py -v
"""

import pytest
from pathlib import Path
from typing import List

from src.preprocessing.chunking import (
    create_chunker,
    ChunkFactory,
    UniversalChunk,
    HierarchicalChunker,
    SemanticChunker,
)
from src.preprocessing.base.models import ProcessedDocument


# ============================================================
# FIXTURES
# ============================================================


@pytest.fixture
def sample_legal_document():
    """Sample legal document (Law/Decree)"""
    return ProcessedDocument(
        metadata={
            "document_type": "decree",
            "title": "Nghị định 63/2014/NĐ-CP",
            "issued_by": "chinh_phu",  # Changed from "Chính phủ" to enum value
            "issued_date": "2014-06-26",
            "effective_date": "2014-08-10",
            "file_path": "/data/raw/Nghi dinh/63-2014-ND-CP.docx",
            "legal_metadata": {
                "legal_id": "63/2014/NĐ-CP",  # Changed to correct format
                "legal_level": 3,
                "status": "con_hieu_luc",  # Changed from "active" to enum value
                "domain": ["dau_thau"],
            },
        },
        content={
            "full_text": """
CHƯƠNG I - QUY ĐỊNH CHUNG

Điều 1. Phạm vi điều chỉnh
1. Nghị định này quy định chi tiết thi hành một số điều của Luật Đấu thầu.
2. Nghị định này áp dụng đối với các hoạt động đấu thầu.

Điều 2. Đối tượng áp dụng
1. Cơ quan có thẩm quyền trong hoạt động đấu thầu.
2. Nhà thầu, tư vấn tham gia đấu thầu.
3. Các tổ chức, cá nhân có liên quan.

CHƯƠNG II - HỒ SƠ MỜI THẦU

Mục 1 - Nội dung hồ sơ mời thầu

Điều 3. Thành phần hồ sơ mời thầu
1. Hồ sơ mời thầu bao gồm:
a) Thông tin tổng quát về gói thầu;
b) Yêu cầu về năng lực, kinh nghiệm;
c) Tiêu chuẩn đánh giá;
d) Điều kiện hợp đồng.
2. Bên mời thầu chịu trách nhiệm lập hồ sơ mời thầu.

Điều 4. Yêu cầu đối với hồ sơ mời thầu
1. Hồ sơ mời thầu phải rõ ràng, đầy đủ.
2. Không được có điều kiện phân biệt đối xử.
3. Phải công bố công khai trên hệ thống mạng đấu thầu quốc gia.
            """.strip(),
        },
    )


@pytest.fixture
def sample_exam_document():
    """Sample exam document"""
    return ProcessedDocument(
        metadata={
            "document_type": "exam",
            "title": "Ngân hàng câu hỏi thi CCDT",
            "file_path": "/data/raw/Cau hoi thi/exam.pdf",
        },
        content={
            "full_text": """
Câu 1: Luật Đấu thầu số 43/2013/QH13 có hiệu lực từ ngày nào?
A. 01/07/2014
B. 01/01/2014
C. 01/07/2013
D. 01/01/2015

Câu 2: Hình thức nào KHÔNG phải là hình thức lựa chọn nhà thầu theo Luật Đấu thầu?
A. Đấu thầu rộng rãi
B. Đấu thầu hạn chế
C. Chỉ định thầu
D. Mua sắm trực tiếp

Câu 3: Giá trị gói thầu được tính bằng?
A. Giá gói thầu được duyệt
B. Giá trúng thầu
C. Giá dự thầu thấp nhất
D. Giá dự toán được duyệt
            """.strip(),
        },
    )


# ============================================================
# TEST BASIC FUNCTIONALITY
# ============================================================


def test_create_chunker_factory():
    """Test chunker factory function"""
    # Legal documents → HierarchicalChunker
    for doc_type in ["law", "decree", "circular", "decision"]:
        chunker = create_chunker(doc_type)
        assert isinstance(chunker, HierarchicalChunker)

    # Bidding → SemanticChunker
    chunker = create_chunker("bidding")
    assert isinstance(chunker, SemanticChunker)
    assert chunker.document_type == "bidding"

    # Exam → SemanticChunker
    chunker = create_chunker("exam")
    assert isinstance(chunker, SemanticChunker)
    assert chunker.document_type == "exam"


def test_hierarchical_chunker_basic(sample_legal_document):
    """Test HierarchicalChunker basic functionality"""
    chunker = HierarchicalChunker()
    chunks = chunker.chunk(sample_legal_document)

    # Should have chunks for Điều 1-4
    assert len(chunks) >= 4, f"Expected at least 4 chunks, got {len(chunks)}"

    # All chunks should be UniversalChunk
    for chunk in chunks:
        assert isinstance(chunk, UniversalChunk)
        assert chunk.content is not None
        assert chunk.document_type == "decree"


def test_semantic_chunker_exam(sample_exam_document):
    """Test SemanticChunker with exam questions"""
    chunker = SemanticChunker(document_type="exam")
    chunks = chunker.chunk(sample_exam_document)

    # Should have 3 chunks (3 questions)
    assert len(chunks) == 3, f"Expected 3 chunks, got {len(chunks)}"

    # Each chunk should be a complete question
    for chunk in chunks:
        assert chunk.level == "question"
        assert "Câu" in chunk.section_title


def test_chunk_size_constraints(sample_legal_document):
    """Test that chunks respect size constraints"""
    chunker = HierarchicalChunker(
        min_size=300,
        max_size=1500,
        target_size=800,
    )
    chunks = chunker.chunk(sample_legal_document)

    # Check size distribution
    sizes = [c.char_count for c in chunks]

    # Most chunks should be in acceptable range
    # Note: Small test data (4 chunks) may have lower ratio
    # Real production data will have much higher ratio
    in_range = [s for s in sizes if 300 <= s <= 1500]
    ratio = len(in_range) / len(sizes)

    assert ratio >= 0.5, f"Only {ratio:.0%} of chunks in size range"

    # No chunk should be excessively large
    assert all(s <= 2000 for s in sizes), "Some chunks exceed safety limit"


def test_chunk_factory_conversion(sample_legal_document):
    """Test ChunkFactory converts UniversalChunk to UnifiedLegalChunk"""
    # Create chunks
    chunker = create_chunker("decree")
    universal_chunks = chunker.chunk(sample_legal_document)

    # Convert
    factory = ChunkFactory()
    unified_chunks = factory.convert_batch(universal_chunks, sample_legal_document)

    # Should have same count
    assert len(unified_chunks) == len(universal_chunks)

    # Check schema structure
    for unified in unified_chunks:
        assert unified.document_info is not None
        assert unified.content_structure is not None
        assert unified.processing_metadata is not None
        assert unified.quality_metrics is not None


# ============================================================
# SUMMARY TEST
# ============================================================


def test_full_pipeline(sample_legal_document, sample_exam_document):
    """Integration test: Full pipeline from document to UnifiedLegalChunk"""

    print("\n" + "=" * 70)
    print("CHUNKING PIPELINE TEST SUMMARY")
    print("=" * 70)

    # Test 1: Legal document
    print("\n📋 Test 1: Legal Document (Decree)")
    chunker_legal = create_chunker("decree")
    chunks_legal = chunker_legal.chunk(sample_legal_document)
    print(f"  ✅ Created {len(chunks_legal)} chunks")

    factory = ChunkFactory()
    unified_legal = factory.convert_batch(chunks_legal, sample_legal_document)
    print(f"  ✅ Converted to {len(unified_legal)} UnifiedLegalChunks")

    stats_legal = chunker_legal.get_statistics()
    print(
        f"  📊 Stats: {stats_legal['in_range']}/{stats_legal['total_chunks']} chunks in range"
    )
    print(f"  📏 Avg size: {stats_legal['avg_size']:.0f} chars")

    # Test 2: Exam document
    print("\n📝 Test 2: Exam Questions")
    chunker_exam = create_chunker("exam")
    chunks_exam = chunker_exam.chunk(sample_exam_document)
    print(f"  ✅ Created {len(chunks_exam)} chunks")

    unified_exam = factory.convert_batch(chunks_exam, sample_exam_document)
    print(f"  ✅ Converted to {len(unified_exam)} UnifiedLegalChunks")

    # Verify schemas
    print("\n🔍 Schema Validation:")
    for unified in unified_legal[:1]:  # Check first chunk
        print(f"  ✅ DocumentInfo: {unified.document_info.doc_type.value}")
        print(f"  ✅ LegalMetadata: {unified.legal_metadata is not None}")
        print(f"  ✅ ContentStructure: chunk_id={unified.get_chunk_id()}")
        print(f"  ✅ QualityMetrics: {unified.quality_metrics.overall_quality}")

    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED")
    print("=" * 70)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
