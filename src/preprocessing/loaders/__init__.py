"""
Document Loaders Package

Loaders for various document types:
- DocxLoader: Legal documents (Luật, Nghị định, Thông tư, Quyết định)
- BiddingLoader: Bidding documents (Hồ sơ mời thầu)
- ReportLoader: Report templates (Mẫu báo cáo)
- PdfLoader: Exam questions, scanned documents (Câu hỏi thi)
- TxtLoader: Plain text files (.txt)
"""

from .docx_loader import DocxLoader, RawDocxContent
from .bidding_loader import BiddingLoader, RawBiddingContent
from .report_loader import ReportLoader, RawReportContent
from .pdf_loader import PdfLoader, RawPdfContent
from .txt_loader import TxtLoader, RawTxtContent

__all__ = [
    "DocxLoader",
    "RawDocxContent",
    "BiddingLoader",
    "RawBiddingContent",
    "ReportLoader",
    "RawReportContent",
    "PdfLoader",
    "RawPdfContent",
    "TxtLoader",
    "RawTxtContent",
]
