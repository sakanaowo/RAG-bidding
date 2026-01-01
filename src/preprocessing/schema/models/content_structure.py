"""
Content Structure Models
Section 3.3 from DEEP_ANALYSIS_REPORT.md
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from ..enums import ChunkType, ContentFormat


class HierarchyPath(BaseModel):
    """Hierarchical position within document structure"""

    phan: Optional[int] = Field(None, description="Part number (Phần)")
    chuong: Optional[int] = Field(None, description="Chapter number (Chương)")
    muc: Optional[int] = Field(None, description="Section number (Mục)")
    dieu: Optional[int] = Field(None, description="Article number (Điều)")
    khoan: Optional[int] = Field(None, description="Clause number (Khoản)")
    diem: Optional[str] = Field(None, description="Point letter (Điểm a, b, c)")

    def to_string(self) -> str:
        """Convert hierarchy to human-readable string"""
        parts = []
        if self.phan:
            parts.append(f"Phần {self.phan}")
        if self.chuong:
            parts.append(f"Chương {self.chuong}")
        if self.muc:
            parts.append(f"Mục {self.muc}")
        if self.dieu:
            parts.append(f"Điều {self.dieu}")
        if self.khoan:
            parts.append(f"Khoản {self.khoan}")
        if self.diem:
            parts.append(f"Điểm {self.diem}")

        return " > ".join(parts) if parts else "Root"


class ContentStructure(BaseModel):
    """
    Content organization and hierarchical structure.
    Critical for legal documents (Law, Decree, Circular, Decision).
    """

    # Chunk identification
    chunk_id: str = Field(
        ..., description="Unique identifier for this chunk within the document"
    )

    chunk_type: ChunkType = Field(
        ..., description="Type of content chunk (article, clause, point, etc.)"
    )

    # Position in document
    chunk_index: int = Field(
        ..., ge=0, description="Sequential index of this chunk (0-based)"
    )

    hierarchy: HierarchyPath = Field(
        ...,
        description="Hierarchical position (Phần > Chương > Mục > Điều > Khoản > Điểm)",
    )

    # Content
    content_text: str = Field(
        ..., min_length=1, description="The actual text content of this chunk"
    )

    content_format: ContentFormat = Field(
        default=ContentFormat.PLAIN_TEXT,
        description="Format of the content (plain_text, markdown, html, etc.)",
    )

    # Context
    heading: Optional[str] = Field(
        None, description="Section/article heading if applicable"
    )

    parent_chunk_id: Optional[str] = Field(
        None, description="ID of parent chunk in hierarchy (e.g., Điều for a Khoản)"
    )

    child_chunk_ids: List[str] = Field(
        default_factory=list,
        description="IDs of child chunks (e.g., Khoản within a Điều)",
    )

    # Size metrics
    word_count: int = Field(
        default=0, ge=0, description="Number of words in content_text"
    )

    char_count: int = Field(
        default=0, ge=0, description="Number of characters in content_text"
    )

    # Extracted entities (optional)
    tables: List[Dict[str, Any]] = Field(
        default_factory=list, description="Extracted tables from this chunk"
    )

    lists: List[List[str]] = Field(
        default_factory=list, description="Extracted lists from this chunk"
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "chunk_id": "43-2024-ND-CP_dieu_5_khoan_2",
                    "chunk_type": "khoan",
                    "chunk_index": 15,
                    "hierarchy": {"phan": 2, "chuong": 1, "dieu": 5, "khoan": 2},
                    "content_text": "Nhà thầu phải nộp hồ sơ dự thầu trước thời hạn qui định...",
                    "content_format": "plain_text",
                    "heading": "Điều 5. Hồ sơ dự thầu",
                    "word_count": 45,
                    "char_count": 287,
                }
            ]
        }
