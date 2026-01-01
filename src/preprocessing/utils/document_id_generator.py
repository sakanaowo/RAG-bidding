"""
DocumentIDGenerator - Generate structured document IDs from filenames

Generates document IDs following new format:
- LUA-{số}-{năm}-{mã cơ quan}  (e.g., LUA-43-2024-QH15)
- ND-{số}-{năm}-{mã}           (e.g., ND-78-2023-ND-CP)
- TT-{số}-{năm}-{mã}           (e.g., TT-102-2023-TT-BTC)
- QD-{số}-{năm}-{mã}           (e.g., QD-456-2024-QD-TTg)
- FORM-{tên}                   (e.g., FORM-HSMT-2024)
- TEMPLATE-{tên}               (e.g., TEMPLATE-BC-01)
- EXAM-{tên}                   (e.g., EXAM-NHCH-2024)

For documents that don't match patterns, falls back to sanitized filename.
"""

import re
from pathlib import Path
from typing import Tuple, Optional
from datetime import datetime
import unicodedata


class DocumentIDGenerator:
    """
    Generate standardized document IDs from filenames and document types.

    Usage:
        generator = DocumentIDGenerator()
        doc_id = generator.generate(
            filename="Luật số 43-2024-QH15.docx",
            doc_type="law"
        )
        # Returns: "LUA-43-2024-QH15"
    """

    # Patterns for extracting document info from filenames
    LAW_PATTERNS = [
        r"[Ll]uật\s+số?\s*(\d+)[/-](\d{4})[/-]?([\w-]+)?",  # Luật số 43/2024/QH15
        r"Law\s+No\.?\s*(\d+)[/-](\d{4})[/-]?([\w-]+)?",  # Law No. 43/2024/QH15
    ]

    DECREE_PATTERNS = [
        r"[Nn]ghị\s*định\s+số?\s*(\d+)[/-](\d{4})[/-]?([\w-]+)",  # Nghị định số 78/2023/NĐ-CP
        r"Decree\s+No\.?\s*(\d+)[/-](\d{4})[/-]?([\w-]+)?",
    ]

    CIRCULAR_PATTERNS = [
        r"[Tt]hông\s*tư\s+số?\s*(\d+)[/-](\d{4})[/-]?([\w-]+)",  # Thông tư số 102/2023/TT-BTC
        r"Circular\s+No\.?\s*(\d+)[/-](\d{4})[/-]?([\w-]+)?",
    ]

    DECISION_PATTERNS = [
        r"[Qq]uyết\s*định\s+số?\s*(\d+)[/-](\d{4})[/-]?([\w-]+)",  # Quyết định số 456/2024/QĐ-TTg
        r"Decision\s+No\.?\s*(\d+)[/-](\d{4})[/-]?([\w-]+)?",
    ]

    def __init__(self):
        """Initialize generator."""
        pass

    def generate(
        self, filename: str, doc_type: str, title: Optional[str] = None
    ) -> str:
        """
        Generate document ID from filename and type.

        Args:
            filename: Original filename (e.g., "Luật số 43-2024-QH15.docx")
            doc_type: Document type (law, decree, circular, decision, bidding, template, exam, other)
            title: Optional document title for better extraction

        Returns:
            Generated document ID (e.g., "LUA-43-2024-QH15")
        """
        # Remove extension
        name_no_ext = Path(filename).stem

        # Try type-specific extraction
        if doc_type == "law":
            doc_id = self._extract_law_id(name_no_ext)
        elif doc_type == "decree":
            doc_id = self._extract_decree_id(name_no_ext)
        elif doc_type == "circular":
            doc_id = self._extract_circular_id(name_no_ext)
        elif doc_type == "decision":
            doc_id = self._extract_decision_id(name_no_ext)
        elif doc_type == "bidding":
            doc_id = self._extract_bidding_id(name_no_ext, title)
        elif doc_type == "template":
            doc_id = self._extract_template_id(name_no_ext, title)
        elif doc_type == "exam":
            doc_id = self._extract_exam_id(name_no_ext, title)
        else:
            doc_id = None

        # Fallback to sanitized filename if extraction failed
        if not doc_id:
            doc_id = self._sanitize_filename(name_no_ext, doc_type)

        return doc_id

    def _extract_law_id(self, text: str) -> Optional[str]:
        """
        Extract law ID from filename.

        Examples:
            "Luật số 43/2024/QH15" → "LUA-43-2024-QH15"
            "Law 43-2024" → "LUA-43-2024"
        """
        for pattern in self.LAW_PATTERNS:
            match = re.search(pattern, text)
            if match:
                number, year = match.group(1), match.group(2)
                authority = match.group(3) if match.lastindex >= 3 else None

                if authority:
                    return f"LUA-{number}-{year}-{authority}"
                else:
                    return f"LUA-{number}-{year}"

        return None

    def _extract_decree_id(self, text: str) -> Optional[str]:
        """
        Extract decree ID from filename.

        Examples:
            "Nghị định 78/2023/NĐ-CP" → "ND-78-2023-ND-CP"
        """
        for pattern in self.DECREE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                number, year = match.group(1), match.group(2)
                authority = match.group(3) if match.lastindex >= 3 else "ND-CP"

                return f"ND-{number}-{year}-{authority}"

        return None

    def _extract_circular_id(self, text: str) -> Optional[str]:
        """
        Extract circular ID from filename.

        Examples:
            "Thông tư 102/2023/TT-BTC" → "TT-102-2023-TT-BTC"
        """
        for pattern in self.CIRCULAR_PATTERNS:
            match = re.search(pattern, text)
            if match:
                number, year = match.group(1), match.group(2)
                authority = match.group(3) if match.lastindex >= 3 else None

                if authority:
                    return f"TT-{number}-{year}-{authority}"
                else:
                    return f"TT-{number}-{year}"

        return None

    def _extract_decision_id(self, text: str) -> Optional[str]:
        """
        Extract decision ID from filename.

        Examples:
            "Quyết định 456/2024/QĐ-TTg" → "QD-456-2024-QD-TTg"
        """
        for pattern in self.DECISION_PATTERNS:
            match = re.search(pattern, text)
            if match:
                number, year = match.group(1), match.group(2)
                authority = match.group(3) if match.lastindex >= 3 else None

                if authority:
                    return f"QD-{number}-{year}-{authority}"
                else:
                    return f"QD-{number}-{year}"

        return None

    def _extract_bidding_id(self, text: str, title: Optional[str] = None) -> str:
        """
        Extract bidding document ID.

        Examples:
            "HSMT-2024-001.docx" → "FORM-Bidding-HSMT-2024-001"
            "Tender Package ABC" → "FORM-Bidding-ABC"
        """
        # Try to extract meaningful identifier
        sanitized = self._sanitize_text(text)

        # Check for HSMT pattern
        if "hsmt" in sanitized.lower():
            return f"FORM-Bidding-{sanitized}"

        # Check for year pattern
        year_match = re.search(r"(\d{4})", sanitized)
        if year_match:
            year = year_match.group(1)
            return f"FORM-Bidding-{year}-{sanitized[:20]}"

        return f"FORM-Bidding-{sanitized[:30]}"

    def _extract_template_id(self, text: str, title: Optional[str] = None) -> str:
        """
        Extract template/form ID.

        Examples:
            "Mẫu BC-01.docx" → "TEMPLATE-BC-01"
            "Form Template 2024" → "TEMPLATE-Form-2024"
        """
        sanitized = self._sanitize_text(text)

        # Check for common template patterns
        template_match = re.search(
            r"(BC|HSDT|QT|TK|HD|PL)[- ]?(\d+)", sanitized, re.IGNORECASE
        )
        if template_match:
            prefix = template_match.group(1).upper()
            number = template_match.group(2)
            return f"TEMPLATE-{prefix}-{number}"

        return f"TEMPLATE-{sanitized[:30]}"

    def _extract_exam_id(self, text: str, title: Optional[str] = None) -> str:
        """
        Extract exam question ID.

        Examples:
            "Ngân hàng câu hỏi CC.docx" → "EXAM-NHCH-CC"
            "Quiz 2024.docx" → "EXAM-Quiz-2024"
        """
        sanitized = self._sanitize_text(text)

        # Check for NHCH pattern
        if "ngan" in text.lower() and "cau" in text.lower():
            # Extract acronym
            words = sanitized.split("-")
            acronym = "".join([w[0].upper() for w in words if w])[:10]
            return f"EXAM-{acronym}"

        return f"EXAM-{sanitized[:30]}"

    def _sanitize_text(self, text: str) -> str:
        """
        Sanitize text for use in document ID.

        - Remove accents
        - Replace spaces with hyphens
        - Remove special characters
        - Lowercase
        """
        # Remove accents
        text = (
            unicodedata.normalize("NFKD", text)
            .encode("ascii", "ignore")
            .decode("ascii")
        )

        # Replace spaces and underscores with hyphens
        text = re.sub(r"[\s_]+", "-", text)

        # Remove special characters except hyphens
        text = re.sub(r"[^\w-]", "", text)

        # Remove multiple consecutive hyphens
        text = re.sub(r"-+", "-", text)

        # Remove leading/trailing hyphens
        text = text.strip("-")

        return text

    def _sanitize_filename(self, filename: str, doc_type: str) -> str:
        """
        Fallback: Create ID from sanitized filename.

        Examples:
            "Document ABC 2024.docx" → "Document-ABC-2024"
        """
        sanitized = self._sanitize_text(filename)

        # Limit length
        if len(sanitized) > 50:
            sanitized = sanitized[:50]

        # Add timestamp if too generic
        if len(sanitized) < 5:
            timestamp = datetime.now().strftime("%Y%m%d%H%M")
            sanitized = f"{doc_type}-{timestamp}"

        return sanitized

    def extract_metadata_from_id(self, document_id: str) -> dict:
        """
        Extract metadata from document ID (reverse operation).

        Args:
            document_id: Document ID (e.g., "LUA-43-2024-QH15")

        Returns:
            Dict with extracted metadata
        """
        parts = document_id.split("-")
        metadata = {"document_id": document_id}

        if len(parts) >= 3:
            prefix = parts[0]
            metadata["prefix"] = prefix

            # Try to extract number and year
            if parts[1].isdigit():
                metadata["number"] = parts[1]
            if parts[2].isdigit() and len(parts[2]) == 4:
                metadata["year"] = parts[2]

            # Map prefix to document type
            type_mapping = {
                "LUA": "law",
                "ND": "decree",
                "TT": "circular",
                "QD": "decision",
                "FORM": "bidding",
                "TEMPLATE": "template",
                "EXAM": "exam",
            }
            metadata["document_type"] = type_mapping.get(prefix, "other")

            # Extract authority (if exists)
            if len(parts) >= 4:
                metadata["authority"] = "-".join(parts[3:])

        return metadata
