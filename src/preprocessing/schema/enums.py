"""
Enums for Vietnamese Legal Document Processing System
Based on DEEP_ANALYSIS_REPORT.md - Unified Schema Design
"""

from enum import Enum


class DocType(str, Enum):
    """Document types in Vietnamese legal system"""

    LAW = "law"  # Luật - từ Quốc hội
    DECREE = "decree"  # Nghị định - từ Chính phủ
    CIRCULAR = "circular"  # Thông tư - từ Bộ
    DECISION = "decision"  # Quyết định - từ Bộ/cơ quan
    BIDDING = "bidding"  # Hồ sơ mời thầu
    REPORT = "report"  # Mẫu báo cáo
    EXAM = "exam"  # Câu hỏi thi


class LegalStatus(str, Enum):
    """Legal status of documents in Vietnamese legal system"""

    CON_HIEU_LUC = "con_hieu_luc"  # Still in effect
    HET_HIEU_LUC = "het_hieu_luc"  # No longer in effect
    BI_THAY_THE = "bi_thay_the"  # Replaced by another document
    BI_BAI_BO = "bi_bai_bo"  # Repealed/abrogated
    DU_THAO = "du_thao"  # Draft (not yet effective)


class DocumentStatus(str, Enum):
    """
    Document validity/effectiveness status - applies to ALL document types.

    Tracks whether a document is still valid, expired, superseded, etc.
    Different from ProcessingStatus (which tracks pipeline execution).

    Use cases:
    - Legal docs (Law/Decree/Circular): Use LegalStatus for legal validity
    - Bidding docs: Use DocumentStatus for template validity (e.g., HSMT 2024 replaces HSMT 2023)
    - Report templates: Track if template is current or outdated
    - Exam questions: Track if question bank is current or retired

    Examples:
        - Bidding template HSMT 2024 replaces HSMT 2023: old template = SUPERSEDED
        - Report template updated with new format: old version = OUTDATED
        - Exam question bank version 2: old version = ARCHIVED
    """

    ACTIVE = "active"  # Hiện đang có hiệu lực/đang dùng
    DRAFT = "draft"  # Bản dự thảo (chưa chính thức)
    OUTDATED = "outdated"  # Đã lỗi thời (có phiên bản mới hơn)
    SUPERSEDED = "superseded"  # Bị thay thế bởi tài liệu khác
    EXPIRED = "expired"  # Hết hạn hiệu lực (có ngày hết hạn cụ thể)
    ARCHIVED = "archived"  # Đã lưu trữ (không còn sử dụng nhưng giữ lại tham khảo)
    DEPRECATED = "deprecated"  # Không khuyến khích dùng nữa
    UNDER_REVISION = "under_revision"  # Đang được sửa đổi/cập nhật


class LegalLevel(int, Enum):
    """
    Vietnamese legal hierarchy levels (5 tiers)
    Based on Constitution → Laws → Decrees → Circulars/Decisions → Applied docs
    """

    HIEN_PHAP = 1  # Constitution (Hiến pháp)
    LUAT = 2  # Laws from National Assembly (Luật/Quốc hội)
    NGHI_DINH = 3  # Government Decrees (Nghị định/Chính phủ)
    THONG_TU_QUYET_DINH = 4  # Ministry Circulars/Decisions (Thông tư/Quyết định/Bộ)
    VAN_BAN_AP_DUNG = 5  # Applied documents (Bidding, Reports, Exams)


class RelationType(str, Enum):
    """Relationship types between legal documents"""

    HUONG_DAN_THI_HANH = "huong_dan_thi_hanh"  # Guides implementation of
    THAY_THE = "thay_the"  # Replaces
    SUA_DOI_BO_SUNG = "sua_doi_bo_sung"  # Amends/supplements
    BAI_BO = "bai_bo"  # Repeals/abrogates
    THAM_CHIEU = "tham_chieu"  # References
    CAN_CU = "can_cu"  # Based on (legal basis)


class ChunkType(str, Enum):
    """Types of content chunks"""

    DIEU_KHOAN = "dieu_khoan"  # Article (điều khoản)
    KHOAN = "khoan"  # Clause (khoản)
    DIEM = "diem"  # Point (điểm)
    CHUONG = "chuong"  # Chapter (chương)
    MUC = "muc"  # Section (mục)
    PHAN = "phan"  # Part (phần)
    TABLE = "table"  # Table
    SEMANTIC = "semantic"  # Semantic chunk (AI-based)


class ContentFormat(str, Enum):
    """Content format types"""

    PLAIN_TEXT = "plain_text"
    MARKDOWN = "markdown"
    HTML = "html"
    STRUCTURED_JSON = "structured_json"


class ProcessingStage(str, Enum):
    """Pipeline processing stages"""

    INGESTION = "ingestion"
    EXTRACTION = "extraction"
    VALIDATION = "validation"
    CHUNKING = "chunking"
    ENRICHMENT = "enrichment"
    QUALITY_CHECK = "quality_check"
    OUTPUT = "output"


class ProcessingStatus(str, Enum):
    """
    Status of document processing through pipeline.

    Tracks how processing went at each stage (different from ProcessingStage which tracks WHERE).
    Use this to identify failed/stuck documents and implement retry logic.

    Examples:
        - Document enters pipeline: PENDING
        - During chunking: IN_PROGRESS
        - Chunking completes successfully: COMPLETED
        - Chunking fails: FAILED (with error_message in ProcessingMetadata)
        - Document duplicate detected: SKIPPED
        - Failed document ready for retry: RETRY
    """

    PENDING = "pending"  # Chưa xử lý
    IN_PROGRESS = "in_progress"  # Đang xử lý
    COMPLETED = "completed"  # Hoàn thành thành công
    FAILED = "failed"  # Thất bại (có error_message)
    PARTIAL = "partial"  # Một phần thành công (some chunks failed)
    SKIPPED = "skipped"  # Bỏ qua (duplicate, blacklist, etc.)
    RETRY = "retry"  # Cần retry (after failed)


class QualityLevel(str, Enum):
    """Quality assessment levels"""

    HIGH = "high"  # >90% confidence
    MEDIUM = "medium"  # 70-90% confidence
    LOW = "low"  # 50-70% confidence
    FAILED = "failed"  # <50% confidence


class IssuingAuthority(str, Enum):
    """Vietnamese government authorities that issue legal documents"""

    QUOC_HOI = "quoc_hoi"  # National Assembly
    CHINH_PHU = "chinh_phu"  # Government
    BO_KE_HOACH_DAU_TU = "bo_ke_hoach_dau_tu"  # Ministry of Planning & Investment
    BO_TAI_CHINH = "bo_tai_chinh"  # Ministry of Finance
    BO_XAY_DUNG = "bo_xay_dung"  # Ministry of Construction
    BO_GIAO_THONG_VAN_TAI = "bo_giao_thong_van_tai"  # Ministry of Transport
    BO_KHOA_HOC_CONG_NGHE = "bo_khoa_hoc_cong_nghe"  # Ministry of Science & Technology
    KHAC = "khac"  # Other authority


class DocumentDomain(str, Enum):
    """Legal/business domains"""

    DAU_THAU = "dau_thau"  # Bidding
    XAY_DUNG = "xay_dung"  # Construction
    TAI_CHINH = "tai_chinh"  # Finance
    GIAO_THONG = "giao_thong"  # Transportation
    CONG_NGHE = "cong_nghe"  # Technology
    THUONG_MAI = "thuong_mai"  # Commerce
    LAO_DONG = "lao_dong"  # Labor
    BAO_HIEM = "bao_hiem"  # Insurance
    KHAC = "khac"  # Other
