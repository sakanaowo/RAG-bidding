"""
Polymorphic Document Information Models
Supports all 7 document types with appropriate validation

Based on CHUNKING_ANALYSIS_AND_SOLUTIONS.md
"""

from datetime import date
from typing import Optional, Literal, Union
from pydantic import BaseModel, Field, field_validator, model_validator
import re

from ..enums import IssuingAuthority


class LegalDocumentInfo(BaseModel):
    """
    Document info for legal documents (Law/Decree/Circular/Decision).

    Strict validation:
    - doc_id must match pattern: number/year/AUTHORITY-CODE
    - issuing_authority required (from enum)
    - issue_date required
    """

    doc_type: Literal["law", "decree", "circular", "decision"] = Field(
        ..., description="Legal document type"
    )

    doc_id: str = Field(
        ...,
        description="Legal doc ID: 43/2024/NĐ-CP, 78/2023/QH15",
        examples=["43/2024/NĐ-CP", "78/2023/QH15", "12/2020/QH14"],
    )

    title: str = Field(
        ..., min_length=10, description="Full official document title in Vietnamese"
    )

    issuing_authority: IssuingAuthority = Field(
        ..., description="Government authority that issued this document"
    )

    issue_date: date = Field(
        ..., description="Date when document was officially issued"
    )

    effective_date: Optional[date] = Field(
        None,
        description="Date when document becomes legally effective",
    )

    source_file: str = Field(
        ..., description="Original source file path (DOCX, PDF, etc.)"
    )

    source_url: Optional[str] = Field(
        None, description="URL if document was crawled from web"
    )

    @field_validator("doc_id")
    @classmethod
    def validate_doc_id(cls, v: str) -> str:
        """Validate Vietnamese legal document ID format"""
        pattern = r"^\d+/\d{4}/[A-Z0-9ĐÀ-Ỹ\-]+$"
        if not re.match(pattern, v, re.IGNORECASE):
            raise ValueError(
                f"Invalid Vietnamese legal doc_id format: {v}. "
                f"Expected pattern: number/year/AUTHORITY-CODE (e.g., 43/2024/NĐ-CP)"
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
                    "doc_type": "decree",
                    "doc_id": "43/2024/NĐ-CP",
                    "title": "Nghị định số 43/2024/NĐ-CP về đấu thầu qua mạng",
                    "issuing_authority": "chinh_phu",
                    "issue_date": "2024-03-15",
                    "effective_date": "2024-05-01",
                    "source_file": "/data/raw/Nghi dinh/43-2024-ND-CP.docx",
                }
            ]
        }


class TemplateDocumentInfo(BaseModel):
    """
    Document info for templates (Bidding/Report).

    Flexible validation:
    - doc_id can be any format (e.g., bidding_15_phu_luc)
    - issue_date optional (templates may not have dates)
    - issuing_ministry instead of issuing_authority
    """

    doc_type: Literal["bidding_template", "report_template"] = Field(
        ..., description="Template document type"
    )

    doc_id: str = Field(
        ...,
        description="Template ID: bidding_15_phu_luc, report_03b_danh_sach",
        examples=["bidding_15_phu_luc", "report_03b_danh_sach_ky_thuat"],
    )

    title: str = Field(..., min_length=10, description="Template title in Vietnamese")

    template_version: str = Field(
        default="1.0",
        description="Template version number",
    )

    issuing_ministry: str = Field(
        default="bo_ke_hoach_dau_tu",
        description="Ministry issuing template (Bộ Kế hoạch và Đầu tư, etc.)",
    )

    issue_date: Optional[date] = Field(
        None,
        description="Date when template was issued (if available)",
    )

    effective_date: Optional[date] = Field(
        None,
        description="Date when template becomes effective",
    )

    source_file: str = Field(..., description="Original source file path")

    source_url: Optional[str] = Field(
        None, description="URL if template was downloaded"
    )

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
                    "doc_type": "bidding_template",
                    "doc_id": "bidding_15_phu_luc",
                    "title": "Biểu mẫu đấu thầu - Phụ lục 15",
                    "template_version": "1.0",
                    "issuing_ministry": "bo_ke_hoach_dau_tu",
                    "source_file": "/data/raw/Ho so moi thau/15. Phu luc.docx",
                }
            ]
        }


class ExamDocumentInfo(BaseModel):
    """
    Document info for exam questions.

    Exam-specific fields:
    - doc_id: exam identifier (e.g., exam_ccdt_2024_dot_1)
    - exam_subject: subject/certification type
    - exam_date: when exam was conducted
    - question_count: total questions in bank
    """

    doc_type: Literal["exam_questions"] = Field(
        ..., description="Exam questions document type"
    )

    doc_id: str = Field(
        ...,
        description="Exam ID: exam_ccdt_2024_dot_1, exam_tdg_2023",
        examples=["exam_ccdt_2024_dot_1", "exam_tdg_2023_dot_2"],
    )

    title: str = Field(..., min_length=10, description="Exam title/description")

    exam_subject: str = Field(
        default="chuyen_gia_dau_thau",
        description="Exam subject: chuyen_gia_dau_thau, tham_dinh_gia, etc.",
    )

    exam_date: Optional[date] = Field(
        None,
        description="Date when exam was conducted",
    )

    question_count: int = Field(
        default=0,
        ge=0,
        description="Total number of questions in exam bank",
    )

    source_file: str = Field(..., description="Original source file path (usually PDF)")

    source_url: Optional[str] = Field(None, description="URL if exam was downloaded")

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
                    "doc_type": "exam_questions",
                    "doc_id": "exam_ccdt_2024_dot_1",
                    "title": "Ngân hàng câu hỏi thi Chuyên gia đấu thầu đợt 1/2024",
                    "exam_subject": "chuyen_gia_dau_thau",
                    "exam_date": "2024-06-15",
                    "question_count": 600,
                    "source_file": "/data/raw/Cau hoi thi/Ngân hàng câu hỏi thi CCDT đợt 1.pdf",
                }
            ]
        }


# Union type for polymorphic DocumentInfo
DocumentInfo = Union[
    LegalDocumentInfo,
    TemplateDocumentInfo,
    ExamDocumentInfo,
]


def create_document_info(
    doc_type: str, doc_id: str, title: str, source_file: str, **kwargs
) -> DocumentInfo:
    """
    Factory function to create appropriate DocumentInfo based on doc_type.

    Args:
        doc_type: One of: law, decree, circular, decision, bidding_template, report_template, exam_questions
        doc_id: Document identifier
        title: Document title
        source_file: Source file path
        **kwargs: Additional fields specific to doc_type

    Returns:
        Appropriate DocumentInfo subclass instance

    Examples:
        >>> # Legal document
        >>> info = create_document_info(
        ...     doc_type="decree",
        ...     doc_id="43/2024/NĐ-CP",
        ...     title="Nghị định về đấu thầu",
        ...     source_file="/data/decree.docx",
        ...     issuing_authority="chinh_phu",
        ...     issue_date=date(2024, 3, 15),
        ... )

        >>> # Template
        >>> info = create_document_info(
        ...     doc_type="bidding_template",
        ...     doc_id="bidding_15_phu_luc",
        ...     title="Biểu mẫu đấu thầu",
        ...     source_file="/data/template.docx",
        ... )

        >>> # Exam
        >>> info = create_document_info(
        ...     doc_type="exam_questions",
        ...     doc_id="exam_ccdt_2024_dot_1",
        ...     title="Câu hỏi thi CCDT",
        ...     source_file="/data/exam.pdf",
        ...     question_count=600,
        ... )
    """
    if doc_type in ["law", "decree", "circular", "decision"]:
        return LegalDocumentInfo(
            doc_type=doc_type,
            doc_id=doc_id,
            title=title,
            source_file=source_file,
            **kwargs,
        )

    elif doc_type in ["bidding_template", "report_template"]:
        return TemplateDocumentInfo(
            doc_type=doc_type,
            doc_id=doc_id,
            title=title,
            source_file=source_file,
            **kwargs,
        )

    elif doc_type == "exam_questions":
        return ExamDocumentInfo(
            doc_type=doc_type,
            doc_id=doc_id,
            title=title,
            source_file=source_file,
            **kwargs,
        )

    else:
        raise ValueError(
            f"Unknown document type: {doc_type}. "
            f"Expected one of: law, decree, circular, decision, "
            f"bidding_template, report_template, exam_questions"
        )
