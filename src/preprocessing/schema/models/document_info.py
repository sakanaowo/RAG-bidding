"""
Document Information Models
Section 3.1 from DEEP_ANALYSIS_REPORT.md
"""

from datetime import date
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re

from ..enums import DocType, IssuingAuthority


class DocumentInfo(BaseModel):
    """
    Core document identification information.
    Required for all 7 document types.
    """

    # Core identifiers
    doc_id: str = Field(
        ...,
        description="Unique document identifier (e.g., '43/2024/NĐ-CP')",
        examples=["43/2024/NĐ-CP", "78/2023/QH15"],
    )

    doc_type: DocType = Field(
        ..., description="Document type from Vietnamese legal system"
    )

    title: str = Field(
        ..., min_length=10, description="Full official document title in Vietnamese"
    )

    # Issuing information
    issuing_authority: IssuingAuthority = Field(
        ..., description="Government authority that issued this document"
    )

    issue_date: date = Field(
        ..., description="Date when document was officially issued"
    )

    effective_date: Optional[date] = Field(
        None,
        description="Date when document becomes legally effective (may differ from issue_date)",
    )

    # Source tracking
    source_file: str = Field(
        ..., description="Original source file path (DOCX, PDF, Excel, etc.)"
    )

    source_url: Optional[str] = Field(
        None, description="URL if document was crawled from web"
    )

    @field_validator("doc_id")
    @classmethod
    def validate_doc_id(cls, v: str) -> str:
        """
        Validate Vietnamese legal document ID format.
        Pattern: {number}/{year}/{authority-code}
        Examples: 43/2024/NĐ-CP, 78/2023/QH15, 12/2020/QH14

        Authority codes:
        - QH{number}: Quốc hội (National Assembly) - e.g., QH13, QH14, QH15
        - NĐ-CP: Nghị định Chính phủ (Government Decree)
        - TT-{ministry}: Thông tư (Circular) - e.g., TT-BXD, TT-BKHĐT
        - QĐ-{authority}: Quyết định (Decision)
        """
        # More flexible pattern to accept all Vietnamese legal doc formats
        pattern = r"^\d+/\d{4}/[A-Z0-9ĐÀ-Ỹ\-]+$"
        if not re.match(pattern, v, re.IGNORECASE):
            raise ValueError(
                f"Invalid Vietnamese legal doc_id format: {v}. "
                f"Expected pattern: number/year/AUTHORITY-CODE (e.g., 43/2024/NĐ-CP, 78/2023/QH15)"
            )
        return v

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Ensure title is meaningful"""
        if len(v.strip()) < 10:
            raise ValueError("Title must be at least 10 characters")
        return v.strip()

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "doc_id": "43/2024/NĐ-CP",
                    "doc_type": "decree",
                    "title": "Nghị định số 43/2024/NĐ-CP về đấu thầu qua mạng",
                    "issuing_authority": "chinh_phu",
                    "issue_date": "2024-03-15",
                    "effective_date": "2024-05-01",
                    "source_file": "/data/raw/Nghi dinh/43-2024-ND-CP.docx",
                    "source_url": "https://thuvienphapluat.vn/...",
                }
            ]
        }
