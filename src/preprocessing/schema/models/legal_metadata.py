"""
Legal Metadata Models
Section 3.2 from DEEP_ANALYSIS_REPORT.md
"""

from typing import Optional, List
from pydantic import BaseModel, Field

from ..enums import LegalStatus, LegalLevel, DocumentDomain


class DocumentRelationship(BaseModel):
    """Relationship to another legal document"""

    related_doc_id: str = Field(
        ...,
        description="ID of the related document",
        examples=["43/2024/NĐ-CP", "98/2023/QH15"],
    )

    relation_type: str = Field(
        ..., description="Type of relationship (from RelationType enum)"
    )

    description: Optional[str] = Field(
        None, description="Optional description of the relationship"
    )


class LegalMetadata(BaseModel):
    """
    Legal-specific metadata for Vietnamese documents.
    Applies primarily to Law, Decree, Circular, Decision.
    """

    # Legal hierarchy
    legal_level: LegalLevel = Field(
        ..., description="Position in Vietnamese legal hierarchy (1-5)"
    )

    legal_status: LegalStatus = Field(
        default=LegalStatus.CON_HIEU_LUC,
        description="Current legal status of the document",
    )

    # Domain classification
    legal_domain: List[DocumentDomain] = Field(
        default_factory=list,
        description="Legal/business domains this document applies to",
    )

    # Relationships to other documents
    parent_law_id: Optional[str] = Field(
        None,
        description="ID of parent law that this document implements (for Decrees/Circulars)",
    )

    replaces_doc_ids: List[str] = Field(
        default_factory=list,
        description="List of document IDs that this document replaces",
    )

    replaced_by_doc_id: Optional[str] = Field(
        None,
        description="ID of document that replaces this one (if status=bi_thay_the)",
    )

    amends_doc_ids: List[str] = Field(
        default_factory=list,
        description="List of document IDs that this document amends",
    )

    references: List[DocumentRelationship] = Field(
        default_factory=list, description="All relationships to other documents"
    )

    # Scope
    scope_description: Optional[str] = Field(
        None, description="Textual description of document scope/applicability"
    )

    geographic_scope: Optional[str] = Field(
        None, description="Geographic applicability (e.g., 'nationwide', 'Hanoi only')"
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "legal_level": 3,
                    "legal_status": "con_hieu_luc",
                    "legal_domain": ["dau_thau", "xay_dung"],
                    "parent_law_id": "43/2013/QH13",
                    "replaces_doc_ids": ["63/2014/NĐ-CP"],
                    "replaced_by_doc_id": None,
                    "scope_description": "Áp dụng cho đấu thầu công trình xây dựng",
                    "geographic_scope": "nationwide",
                }
            ]
        }
