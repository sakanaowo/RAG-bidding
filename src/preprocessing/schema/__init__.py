"""
Schema Module - Unified Legal Document Schema
Phase 1: Schema & Base (Week 1-2)
"""

from .unified_schema import UnifiedLegalChunk
from .enums import (
    DocType,
    LegalStatus,
    DocumentStatus,  # 🆕 NEW - Document validity status
    LegalLevel,
    RelationType,
    ChunkType,
    ContentFormat,
    ProcessingStage,
    ProcessingStatus,  # Processing execution status
    QualityLevel,
    IssuingAuthority,
    DocumentDomain,
)
from .models.document_info import DocumentInfo
from .models.legal_metadata import LegalMetadata, DocumentRelationship
from .models.content_structure import ContentStructure, HierarchyPath
from .models.processing_metadata import ProcessingMetadata
from .models.quality_metrics import QualityMetrics

__all__ = [
    # Main schema
    "UnifiedLegalChunk",
    # Enums
    "DocType",
    "LegalStatus",
    "DocumentStatus",  # 🆕 NEW - Document validity status
    "LegalLevel",
    "RelationType",
    "ChunkType",
    "ContentFormat",
    "ProcessingStage",
    "ProcessingStatus",  # Processing execution status
    "QualityLevel",
    "IssuingAuthority",
    "DocumentDomain",
    # Models
    "DocumentInfo",
    "LegalMetadata",
    "DocumentRelationship",
    "ContentStructure",
    "HierarchyPath",
    "ProcessingMetadata",
    "QualityMetrics",
]
