"""
Example Usage: DocumentStatus Field

Demonstrates how to use document_status to track document validity/effectiveness
across all document types (Legal, Bidding, Report, Exam).

Different from ProcessingStatus:
- ProcessingStatus = pipeline execution (pending/in_progress/completed/failed)
- DocumentStatus = document validity (active/outdated/superseded/expired)
- LegalStatus = legal validity (còn hiệu lực/hết hiệu lực - ONLY for legal docs)
"""

from datetime import date
from src.preprocessing.schema import (
    DocumentStatus,
    LegalStatus,
    ProcessingStatus,
)
from src.preprocessing.schema.models.document_info_types import (
    LegalDocumentInfo,
    TemplateDocumentInfo,
    ExamDocumentInfo,
)


# ============================================================
# EXAMPLE 1: Legal Document Status (Law/Decree/Circular)
# ============================================================


def example_legal_document_status():
    """
    Legal documents have BOTH:
    - LegalStatus (legal validity - trong LegalMetadata)
    - DocumentStatus (document validity - trong DocumentInfo)
    """

    print("=== Legal Document Status Example ===\n")

    # Old decree that was replaced
    old_decree = LegalDocumentInfo(
        doc_type="decree",
        doc_id="63/2014/NĐ-CP",
        title="Nghị định 63/2014/NĐ-CP về đấu thầu (cũ)",
        issuing_authority="chinh_phu",
        issue_date=date(2014, 6, 26),
        effective_date=date(2014, 8, 15),
        source_file="/data/raw/Nghi dinh/63-2014-ND-CP.docx",
        document_status=DocumentStatus.SUPERSEDED,  # 🆕 Bị thay thế
    )

    # New decree that replaces old one
    new_decree = LegalDocumentInfo(
        doc_type="decree",
        doc_id="43/2024/NĐ-CP",
        title="Nghị định 43/2024/NĐ-CP về đấu thầu qua mạng (mới)",
        issuing_authority="chinh_phu",
        issue_date=date(2024, 3, 15),
        effective_date=date(2024, 5, 1),
        source_file="/data/raw/Nghi dinh/43-2024-ND-CP.docx",
        document_status=DocumentStatus.ACTIVE,  # 🆕 Đang có hiệu lực
    )

    print(f"Old decree: {old_decree.doc_id}")
    print(f"  DocumentStatus: {old_decree.document_status.value}")
    print(f"  → User sees: 'Tài liệu này đã bị thay thế bởi 43/2024/NĐ-CP'\n")

    print(f"New decree: {new_decree.doc_id}")
    print(f"  DocumentStatus: {new_decree.document_status.value}")
    print(f"  → User sees: 'Tài liệu hiện hành'\n")


# ============================================================
# EXAMPLE 2: Bidding Template Status
# ============================================================


def example_bidding_template_status():
    """
    Bidding templates can be updated/replaced with new versions
    """

    print("\n=== Bidding Template Status Example ===\n")

    # Old template version (2023)
    old_template = TemplateDocumentInfo(
        doc_type="bidding_template",
        doc_id="HSMT_2023",
        title="Hồ sơ mời thầu (Phiên bản 2023)",
        template_version="1.0",
        issuing_ministry="bo_ke_hoach_dau_tu",
        issue_date=date(2023, 1, 15),
        source_file="/data/raw/HSMT_2023.docx",
        document_status=DocumentStatus.OUTDATED,  # 🆕 Đã lỗi thời
    )

    # New template version (2024)
    new_template = TemplateDocumentInfo(
        doc_type="bidding_template",
        doc_id="HSMT_2024",
        title="Hồ sơ mời thầu (Phiên bản 2024 - cập nhật)",
        template_version="2.0",
        issuing_ministry="bo_ke_hoach_dau_tu",
        issue_date=date(2024, 1, 15),
        source_file="/data/raw/HSMT_2024.docx",
        document_status=DocumentStatus.ACTIVE,  # 🆕 Phiên bản hiện hành
    )

    # Draft template for 2025
    draft_template = TemplateDocumentInfo(
        doc_type="bidding_template",
        doc_id="HSMT_2025_DRAFT",
        title="Hồ sơ mời thầu (Dự thảo 2025)",
        template_version="3.0-draft",
        issuing_ministry="bo_ke_hoach_dau_tu",
        source_file="/data/raw/HSMT_2025_draft.docx",
        document_status=DocumentStatus.DRAFT,  # 🆕 Bản dự thảo
    )

    print(f"Old template (2023): {old_template.document_status.value}")
    print(f"  → Warning: 'Mẫu này đã lỗi thời, vui lòng dùng phiên bản 2024'\n")

    print(f"Current template (2024): {new_template.document_status.value}")
    print(f"  → Recommended for use\n")

    print(f"Draft template (2025): {draft_template.document_status.value}")
    print(f"  → Not yet official\n")


# ============================================================
# EXAMPLE 3: Exam Question Bank Status
# ============================================================


def example_exam_questions_status():
    """
    Exam question banks can be retired/archived when new versions come out
    """

    print("\n=== Exam Question Bank Status Example ===\n")

    # Archived old question bank
    old_exam = ExamDocumentInfo(
        doc_type="exam_questions",
        doc_id="exam_ccdt_2023",
        title="Ngân hàng câu hỏi thi CCDT 2023",
        exam_subject="chuyen_gia_dau_thau",
        exam_date=date(2023, 6, 15),
        question_count=500,
        source_file="/data/raw/CCDT_2023.pdf",
        document_status=DocumentStatus.ARCHIVED,  # 🆕 Đã lưu trữ
    )

    # Current question bank
    current_exam = ExamDocumentInfo(
        doc_type="exam_questions",
        doc_id="exam_ccdt_2024",
        title="Ngân hàng câu hỏi thi CCDT 2024",
        exam_subject="chuyen_gia_dau_thau",
        exam_date=date(2024, 6, 15),
        question_count=600,
        source_file="/data/raw/CCDT_2024.pdf",
        document_status=DocumentStatus.ACTIVE,  # 🆕 Đang sử dụng
    )

    # Question bank under revision
    updating_exam = ExamDocumentInfo(
        doc_type="exam_questions",
        doc_id="exam_ccdt_2024_v2",
        title="Ngân hàng câu hỏi thi CCDT 2024 (đang cập nhật)",
        exam_subject="chuyen_gia_dau_thau",
        question_count=650,
        source_file="/data/raw/CCDT_2024_v2.pdf",
        document_status=DocumentStatus.UNDER_REVISION,  # 🆕 Đang sửa đổi
    )

    print(f"Old exam bank (2023): {old_exam.document_status.value}")
    print(f"  → Kept for reference only\n")

    print(f"Current exam bank (2024): {current_exam.document_status.value}")
    print(f"  → Use for practice\n")

    print(f"Updating exam bank (2024 v2): {updating_exam.document_status.value}")
    print(f"  → Not finalized yet\n")


# ============================================================
# EXAMPLE 4: Query Documents by Status
# ============================================================


def example_query_by_status():
    """
    Example database queries to filter documents by status
    """

    print("\n=== Query by Document Status Examples ===\n")

    queries = {
        "Find all active documents": """
            SELECT doc_id, title, doc_type
            FROM chunks
            WHERE document_info->>'document_status' = 'active';
        """,
        "Find superseded legal documents": """
            SELECT doc_id, title
            FROM chunks
            WHERE document_info->>'doc_type' IN ('law', 'decree', 'circular')
              AND document_info->>'document_status' = 'superseded';
        """,
        "Find outdated bidding templates": """
            SELECT doc_id, title, template_version
            FROM chunks
            WHERE document_info->>'doc_type' = 'bidding_template'
              AND document_info->>'document_status' = 'outdated';
        """,
        "Find documents ready for review (drafts + under revision)": """
            SELECT doc_id, title, doc_type
            FROM chunks
            WHERE document_info->>'document_status' IN ('draft', 'under_revision')
            ORDER BY created_at DESC;
        """,
        "Count documents by status": """
            SELECT 
                document_info->>'document_status' as status,
                doc_type,
                COUNT(*) as count
            FROM chunks
            GROUP BY status, doc_type
            ORDER BY doc_type, count DESC;
        """,
    }

    for description, query in queries.items():
        print(f"📊 {description}:")
        print(query)
        print()


# ============================================================
# EXAMPLE 5: Status vs LegalStatus vs ProcessingStatus
# ============================================================


def example_status_comparison():
    """
    Clarify differences between 3 status fields
    """

    print("\n=== Three Types of Status ===\n")

    comparison = """
    ┌─────────────────────┬──────────────────────────┬─────────────────────────┐
    │ Field               │ Purpose                  │ Applies To              │
    ├─────────────────────┼──────────────────────────┼─────────────────────────┤
    │ DocumentStatus      │ Document validity        │ ALL document types      │
    │ (document_info)     │ (active/outdated/etc.)   │ (Law, Bidding, etc.)    │
    ├─────────────────────┼──────────────────────────┼─────────────────────────┤
    │ LegalStatus         │ Legal validity           │ Legal docs ONLY         │
    │ (legal_metadata)    │ (còn hiệu lực/hết HLực)  │ (Law/Decree/Circular)   │
    ├─────────────────────┼──────────────────────────┼─────────────────────────┤
    │ ProcessingStatus    │ Pipeline execution       │ ALL documents           │
    │ (processing_meta)   │ (pending/completed/etc.) │ (runtime tracking)      │
    └─────────────────────┴──────────────────────────┴─────────────────────────┘
    
    Example: Old Decree that was replaced:
    ┌────────────────────┬────────────────────────────────────────────────┐
    │ document_status    │ SUPERSEDED (replaced by newer decree)          │
    │ legal_status       │ BI_THAY_THE (legal validity)                   │
    │ processing_status  │ COMPLETED (pipeline processed successfully)    │
    └────────────────────┴────────────────────────────────────────────────┘
    """

    print(comparison)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    example_legal_document_status()
    example_bidding_template_status()
    example_exam_questions_status()
    example_query_by_status()
    example_status_comparison()

    print("\n" + "=" * 70)
    print("✅ All examples completed!")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("  • DocumentStatus = document validity (active/outdated/superseded/etc.)")
    print("  • LegalStatus = legal validity (còn hiệu lực/hết hiệu lực)")
    print("  • ProcessingStatus = pipeline execution (pending/completed/failed)")
    print("\n  Use DocumentStatus to track if a document is current or outdated!")
