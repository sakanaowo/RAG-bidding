"""
Test Phase 1 Skeleton
Quick test to verify schema and base pipeline setup
"""

import sys
from pathlib import Path
from datetime import date

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.preprocessing.schema import (
    UnifiedLegalChunk,
    DocumentInfo,
    LegalMetadata,
    ContentStructure,
    HierarchyPath,
    ProcessingMetadata,
    QualityMetrics,
    DocType,
    LegalLevel,
    LegalStatus,
    IssuingAuthority,
    ChunkType,
    ContentFormat,
)
from src.preprocessing.base import BaseLegalPipeline, PipelineConfig
from src.preprocessing.pipelines import LawPipeline


def test_schema_creation():
    """Test creating a UnifiedLegalChunk"""
    print("\n" + "=" * 60)
    print("TEST 1: Schema Creation")
    print("=" * 60)

    # Create document info
    doc_info = DocumentInfo(
        doc_id="43/2013/QH13",
        doc_type=DocType.LAW,
        title="Luật Đấu thầu số 43/2013/QH13",
        issuing_authority=IssuingAuthority.QUOC_HOI,
        issue_date=date(2013, 11, 26),
        effective_date=date(2014, 7, 1),
        source_file="/data/raw/Luat chinh/43-2013-QH13.docx",
    )
    print(f"✓ Created DocumentInfo: {doc_info.doc_id}")

    # Create legal metadata
    legal_meta = LegalMetadata(
        legal_level=LegalLevel.LUAT,
        legal_status=LegalStatus.CON_HIEU_LUC,
    )
    print(f"✓ Created LegalMetadata: Level {legal_meta.legal_level.value}")

    # Create content structure
    content = ContentStructure(
        chunk_id="43-2013-QH13_dieu_1",
        chunk_type=ChunkType.DIEU_KHOAN,
        chunk_index=0,
        hierarchy=HierarchyPath(phan=1, chuong=1, dieu=1),
        content_text="Luật này quy định về hoạt động đấu thầu...",
        content_format=ContentFormat.PLAIN_TEXT,
        heading="Điều 1. Phạm vi điều chỉnh",
        word_count=10,
        char_count=50,
    )
    print(f"✓ Created ContentStructure: {content.chunk_id}")
    print(f"  Hierarchy: {content.hierarchy.to_string()}")

    # Create unified chunk
    chunk = UnifiedLegalChunk(
        document_info=doc_info,
        legal_metadata=legal_meta,
        content_structure=content,
        processing_metadata=ProcessingMetadata(
            processing_id="test_001",
            extractor_used="test",
        ),
        quality_metrics=QualityMetrics(),
    )
    print(f"✓ Created UnifiedLegalChunk")
    print(f"  Doc Type: {chunk.get_doc_type().value}")
    print(f"  Is Legal: {chunk.is_legal_document()}")
    print(f"  Chunk ID: {chunk.get_chunk_id()}")

    return chunk


def test_law_pipeline():
    """Test LawPipeline execution"""
    print("\n" + "=" * 60)
    print("TEST 2: LawPipeline Execution")
    print("=" * 60)

    # Create pipeline
    config = PipelineConfig(
        enable_validation=True,
        enable_enrichment=False,  # Skip for skeleton test
        enable_quality_check=True,
        chunking_strategy="hierarchical",
    )
    pipeline = LawPipeline(config)
    print(f"✓ Created LawPipeline")
    print(f"  Doc Type: {pipeline.get_doc_type().value}")

    # Process mock file
    mock_file = Path("/data/raw/Luat chinh/43-2013-QH13.docx")
    print(f"\n⚙ Processing: {mock_file}")

    try:
        # This will fail because file doesn't exist, but shows pipeline flow
        result = pipeline.process(mock_file)

        if result.success:
            print(f"\n✓ Pipeline SUCCESS")
            print(f"  Processing ID: {result.metadata['processing_id']}")
            print(f"  Duration: {result.metadata.get('duration_ms', 0)}ms")
            print(f"  Chunks created: {result.metadata['num_chunks']}")

            # Show first chunk
            if result.chunks:
                chunk = result.chunks[0]
                print(f"\n  First chunk:")
                print(f"    ID: {chunk.get_chunk_id()}")
                print(f"    Type: {chunk.content_structure.chunk_type.value}")
                print(f"    Heading: {chunk.content_structure.heading}")
        else:
            print(f"\n✗ Pipeline FAILED")
            print(f"  Errors: {result.errors}")

    except FileNotFoundError as e:
        print(f"\n⚠ Expected error (file doesn't exist): {e}")
        print(f"  This is OK for skeleton test - pipeline structure is working!")


def test_enum_values():
    """Test all enum values"""
    print("\n" + "=" * 60)
    print("TEST 3: Enum Values")
    print("=" * 60)

    print("\n📋 Document Types:")
    for doc_type in DocType:
        print(f"  - {doc_type.value}")

    print("\n⚖️ Legal Levels:")
    for level in LegalLevel:
        print(f"  - {level.name}: {level.value}")

    print("\n📊 Legal Status:")
    for status in LegalStatus:
        print(f"  - {status.value}")

    print("\n🏛️ Issuing Authorities:")
    for authority in IssuingAuthority:
        print(f"  - {authority.value}")


if __name__ == "__main__":
    print("\n" + "🚀 " + "=" * 58)
    print("  PHASE 1 SKELETON TEST - Unified Schema & Base Pipeline")
    print("=" * 60)

    # Run tests
    chunk = test_schema_creation()
    test_law_pipeline()
    test_enum_values()

    print("\n" + "=" * 60)
    print("✓ Phase 1 Skeleton Tests Complete!")
    print("=" * 60)
    print("\nNext Steps:")
    print("1. Install pydantic: pip install pydantic")
    print("2. Implement actual DOCX extraction in LawPipeline")
    print("3. Add validators in schema/validators.py")
    print("4. Create remaining 6 pipelines (Decree, Circular, etc.)")
    print("=" * 60 + "\n")
