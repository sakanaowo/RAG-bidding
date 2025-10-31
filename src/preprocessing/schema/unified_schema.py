"""
Unified Legal Chunk Schema
Main schema model combining all sections (3.1-3.6)
Based on DEEP_ANALYSIS_REPORT.md
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from .enums import DocType
from .models.document_info import DocumentInfo
from .models.legal_metadata import LegalMetadata
from .models.content_structure import ContentStructure
from .models.processing_metadata import ProcessingMetadata
from .models.quality_metrics import QualityMetrics


class UnifiedLegalChunk(BaseModel):
    """
    Unified schema for all Vietnamese legal document chunks.

    This is the main data model used across all 7 document pipelines:
    - Law (Luật)
    - Decree (Nghị định)
    - Circular (Thông tư)
    - Decision (Quyết định)
    - Bidding Templates (Hồ sơ mời thầu)
    - Report Templates (Mẫu báo cáo)
    - Exam Questions (Câu hỏi thi)

    Structure (21 core fields across 6 sections):
    1. Document Info (8 fields) - Section 3.1
    2. Legal Metadata (9+ fields) - Section 3.2
    3. Content Structure (12+ fields) - Section 3.3
    4. Relationships (in Legal Metadata) - Section 3.4
    5. Processing Metadata (10+ fields) - Section 3.5
    6. Quality Metrics (12+ fields) - Section 3.6

    Plus extended metadata specific to each document type (Section 3.7).
    """

    # ============================================================
    # SECTION 3.1: DOCUMENT INFORMATION
    # ============================================================
    document_info: DocumentInfo = Field(
        ..., description="Core document identification (8 fields)"
    )

    # ============================================================
    # SECTION 3.2: LEGAL METADATA
    # ============================================================
    legal_metadata: Optional[LegalMetadata] = Field(
        None,
        description="Legal-specific metadata (applies to Law/Decree/Circular/Decision)",
    )

    # ============================================================
    # SECTION 3.3: CONTENT STRUCTURE
    # ============================================================
    content_structure: ContentStructure = Field(
        ..., description="Content organization and hierarchy (12+ fields)"
    )

    # ============================================================
    # SECTION 3.5: PROCESSING METADATA
    # ============================================================
    processing_metadata: ProcessingMetadata = Field(
        ..., description="Pipeline execution metadata (10+ fields)"
    )

    # ============================================================
    # SECTION 3.6: QUALITY METRICS
    # ============================================================
    quality_metrics: QualityMetrics = Field(
        default_factory=QualityMetrics,
        description="Quality assessment and validation (12+ fields)",
    )

    # ============================================================
    # SECTION 3.7: EXTENDED METADATA
    # ============================================================
    extended_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Document type-specific extended metadata (varies by doc_type)",
    )

    def get_doc_type(self) -> DocType:
        """Helper to get document type"""
        return self.document_info.doc_type

    def get_chunk_id(self) -> str:
        """Helper to get chunk ID"""
        return self.content_structure.chunk_id

    def is_legal_document(self) -> bool:
        """Check if this is a legal document (Law/Decree/Circular/Decision)"""
        return self.document_info.doc_type in [
            DocType.LAW,
            DocType.DECREE,
            DocType.CIRCULAR,
            DocType.DECISION,
        ]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return self.model_dump(mode="json")

    class Config:
        json_schema_extra = {
            "description": "Unified schema for Vietnamese legal document chunks - 21 core fields + extended metadata",
            "examples": [
                {
                    "document_info": {
                        "doc_id": "43/2024/NĐ-CP",
                        "doc_type": "decree",
                        "title": "Nghị định về đấu thầu qua mạng",
                        "issuing_authority": "chinh_phu",
                        "issue_date": "2024-03-15",
                        "effective_date": "2024-05-01",
                        "source_file": "/data/raw/Nghi dinh/43-2024-ND-CP.docx",
                    },
                    "legal_metadata": {
                        "legal_level": 3,
                        "legal_status": "con_hieu_luc",
                        "legal_domain": ["dau_thau"],
                        "parent_law_id": "43/2013/QH13",
                    },
                    "content_structure": {
                        "chunk_id": "43-2024-ND-CP_dieu_5",
                        "chunk_type": "dieu_khoan",
                        "chunk_index": 4,
                        "hierarchy": {"dieu": 5},
                        "content_text": "Điều 5. Hồ sơ dự thầu...",
                        "content_format": "plain_text",
                        "word_count": 150,
                    },
                    "processing_metadata": {
                        "processing_id": "proc_20241031_001",
                        "pipeline_version": "2.0.0",
                        "processed_at": "2024-10-31T10:30:00",
                        "extractor_used": "docx",
                        "chunking_strategy": "hierarchical",
                    },
                    "quality_metrics": {
                        "overall_quality": "high",
                        "confidence_score": 0.92,
                        "validation_passed": True,
                    },
                }
            ],
        }
