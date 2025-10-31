"""
PDF Loader for Vietnamese Documents
Handles: Exam questions (Câu hỏi thi), Scanned legal documents, etc.

Uses pypdf for PDF text extraction
Integrated with V2 Unified Schema
"""

from __future__ import annotations
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

try:
    from pypdf import PdfReader

    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


@dataclass
class RawPdfContent:
    """
    Raw extracted content from PDF documents.
    Pre-schema data structure.
    """

    text: str
    metadata: Dict
    pages: List[Dict]  # Per-page content
    statistics: Dict


class PdfLoader:
    """
    Loader for PDF documents.

    Primary use cases:
    - Exam questions (Câu hỏi thi)
    - Scanned legal documents
    - PDF reports

    Note: For scanned PDFs, OCR may be needed (not included).
    This loader works best with text-based PDFs.

    Example:
        loader = PdfLoader()
        content = loader.load("path/to/exam.pdf")
        print(f"Pages: {len(content.pages)}")
        print(f"Questions found: {content.statistics['question_count']}")
    """

    def __init__(self, extract_images: bool = False):
        """
        Args:
            extract_images: Whether to attempt image extraction (not implemented yet)
        """
        if not PDF_AVAILABLE:
            raise ImportError("pypdf is required. Install with: pip install pypdf")

        self.extract_images = extract_images

        # Patterns for exam question detection
        self.question_patterns = {
            "numbered": re.compile(r"^(Câu|CÂU)\s+(\d+)[:\.\)]?\s*(.*)$", re.MULTILINE),
            "simple_number": re.compile(r"^(\d+)[:\.\)]\s+(.+)$", re.MULTILINE),
            "letter": re.compile(r"^([A-D])[:\.\)]\s+(.+)$", re.MULTILINE),
        }

        # Patterns for answer detection
        self.answer_patterns = {
            "answer_key": re.compile(
                r"(?i)(đáp\s*án|trả\s*lời)[:\s]+([A-D])", re.MULTILINE
            ),
            "correct_answer": re.compile(
                r"(?i)(đúng|correct)[:\s]*([A-D])", re.MULTILINE
            ),
        }

    def load(self, file_path: str) -> RawPdfContent:
        """
        Load and extract PDF document.

        Args:
            file_path: Path to PDF file

        Returns:
            RawPdfContent with extracted text, metadata, pages
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if file_path.suffix.lower() != ".pdf":
            raise ValueError(f"Only PDF files supported. Got: {file_path.suffix}")

        return self._extract_pdf(file_path)

    def _extract_pdf(self, file_path: Path) -> RawPdfContent:
        """Extract content from PDF file"""
        reader = PdfReader(str(file_path))

        # Extract metadata from PDF
        metadata = self._extract_metadata(reader, file_path)

        # Extract text from all pages
        pages = []
        all_text_parts = []

        for page_num, page in enumerate(reader.pages):
            page_text = page.extract_text()

            if page_text.strip():
                pages.append(
                    {
                        "page_number": page_num + 1,
                        "text": page_text,
                        "char_count": len(page_text),
                    }
                )
                all_text_parts.append(page_text)

        full_text = "\n\n".join(all_text_parts)

        # Calculate statistics
        statistics = self._calculate_statistics(full_text, pages, metadata)

        return RawPdfContent(
            text=full_text,
            metadata=metadata,
            pages=pages,
            statistics=statistics,
        )

    def _extract_metadata(self, reader: PdfReader, file_path: Path) -> Dict:
        """Extract PDF metadata"""
        pdf_metadata = reader.metadata if reader.metadata else {}

        metadata = {
            "filename": file_path.name,
            "file_path": str(file_path.absolute()),
            "title": pdf_metadata.get("/Title", "") or file_path.stem,
            "author": pdf_metadata.get("/Author", "") or "",
            "subject": pdf_metadata.get("/Subject", "") or "",
            "creator": pdf_metadata.get("/Creator", "") or "",
            "producer": pdf_metadata.get("/Producer", "") or "",
            "creation_date": str(pdf_metadata.get("/CreationDate", "")) or None,
            "modification_date": str(pdf_metadata.get("/ModDate", "")) or None,
            "page_count": len(reader.pages),
        }

        return metadata

    def _calculate_statistics(
        self, text: str, pages: List[Dict], metadata: Dict
    ) -> Dict:
        """Calculate document statistics"""

        # Detect document type
        doc_type = self._detect_document_type(text)

        # Count questions if exam document
        question_count = 0
        answer_count = 0
        if doc_type == "exam":
            question_count = self._count_questions(text)
            answer_count = self._count_answers(text)

        return {
            "char_count": len(text),
            "word_count": len(text.split()),
            "page_count": len(pages),
            "document_type": doc_type,
            "question_count": question_count,
            "answer_count": answer_count,
            "avg_chars_per_page": len(text) // len(pages) if pages else 0,
        }

    def _detect_document_type(self, text: str) -> str:
        """Detect type of PDF document"""
        text_lower = text.lower()

        # Check for exam indicators
        exam_keywords = [
            "câu hỏi thi",
            "ngân hàng câu hỏi",
            "đề thi",
            "bài thi",
            "kiểm tra",
        ]
        if any(keyword in text_lower for keyword in exam_keywords):
            return "exam"

        # Check for legal document indicators
        legal_keywords = ["luật", "nghị định", "thông tư", "quyết định"]
        if any(keyword in text_lower for keyword in legal_keywords):
            return "legal"

        # Check for bidding document indicators
        bidding_keywords = ["mời thầu", "đấu thầu", "gói thầu"]
        if any(keyword in text_lower for keyword in bidding_keywords):
            return "bidding"

        # Check for report indicators
        report_keywords = ["báo cáo", "đánh giá", "thẩm định"]
        if any(keyword in text_lower for keyword in report_keywords):
            return "report"

        return "general"

    def _count_questions(self, text: str) -> int:
        """Count number of questions in exam document"""
        max_count = 0

        # Try each question pattern
        for pattern_type, pattern in self.question_patterns.items():
            matches = pattern.findall(text)
            if matches:
                count = len(matches)
                max_count = max(max_count, count)

        return max_count

    def _count_answers(self, text: str) -> int:
        """Count number of answer keys found"""
        count = 0

        for pattern in self.answer_patterns.values():
            matches = pattern.findall(text)
            count += len(matches)

        return count

    def extract_questions(self, text: str) -> List[Dict]:
        """
        Extract individual questions from exam text.

        Returns:
            List of question dictionaries with number, text, options, answer
        """
        questions = []

        # Try to find questions using numbered pattern first
        numbered_matches = self.question_patterns["numbered"].finditer(text)

        for match in numbered_matches:
            question_num = match.group(2)
            question_text = match.group(3) if len(match.groups()) >= 3 else ""

            # Extract question block (until next question)
            start_pos = match.start()
            # Find next question
            next_match = self.question_patterns["numbered"].search(text, match.end())
            end_pos = next_match.start() if next_match else len(text)

            question_block = text[start_pos:end_pos]

            # Extract options (A, B, C, D)
            options = self._extract_options(question_block)

            # Extract answer if present
            answer = self._extract_answer(question_block)

            questions.append(
                {
                    "number": question_num,
                    "text": question_text,
                    "options": options,
                    "answer": answer,
                    "full_text": question_block.strip(),
                }
            )

        return questions

    def _extract_options(self, question_block: str) -> Dict[str, str]:
        """Extract answer options (A, B, C, D) from question block"""
        options = {}

        letter_pattern = self.question_patterns["letter"]
        matches = letter_pattern.finditer(question_block)

        for match in matches:
            letter = match.group(1)
            option_text = match.group(2)
            options[letter] = option_text.strip()

        return options

    def _extract_answer(self, question_block: str) -> Optional[str]:
        """Extract correct answer from question block"""
        for pattern in self.answer_patterns.values():
            match = pattern.search(question_block)
            if match:
                return match.group(2)  # The letter (A, B, C, or D)

        return None
