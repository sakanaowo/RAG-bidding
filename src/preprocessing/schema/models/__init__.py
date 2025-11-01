"""
Schema Models Package
Pydantic models for document metadata sections
"""

from .document_info import DocumentInfo
from .document_info_types import (
    LegalDocumentInfo,
    TemplateDocumentInfo,
    ExamDocumentInfo,
    create_document_info,
)
from .legal_metadata import LegalMetadata, DocumentRelationship
from .content_structure import ContentStructure, HierarchyPath
from .processing_metadata import ProcessingMetadata
from .quality_metrics import QualityMetrics

__all__ = [
    "DocumentInfo",
    "LegalDocumentInfo",
    "TemplateDocumentInfo",
    "ExamDocumentInfo",
    "create_document_info",
    "LegalMetadata",
    "DocumentRelationship",
    "ContentStructure",
    "HierarchyPath",
    "ProcessingMetadata",
    "QualityMetrics",
]
