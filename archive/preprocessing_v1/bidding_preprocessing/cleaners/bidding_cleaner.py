"""
Bidding Document Cleaner

Cleans and normalizes Vietnamese bidding document text.
Handles bidding-specific terminology, formatting, and document structure.
"""

import re
import unicodedata
from typing import Dict, List, Tuple, Any


class BiddingCleaner:
    """
    Cleaner for Vietnamese bidding documents (Hồ sơ mời thầu)
    Normalizes bidding terminology, formatting, and document structure
    """

    def __init__(self):
        """Initialize bidding document cleaner"""

        # Bidding terminology standardization
        self.bidding_terminology = {
            # Contractor terms
            "nhà thầu": [
                "nhà thầu",
                "đơn vị thầu",
                "doanh nghiệp thầu",
                "tổ chức thầu",
            ],
            "thầu phụ": ["thầu phụ", "nhà thầu phụ", "đối tác thầu phụ"],
            "liên danh": ["liên danh", "liên doanh", "hợp tác liên danh"],
            # Owner terms
            "chủ đầu tư": ["chủ đầu tư", "bên mời thầu", "chủ dự án", "đơn vị chủ trì"],
            "bên mời thầu": ["bên mời thầu", "đơn vị mời thầu"],
            # Contract terms
            "hợp đồng": ["hợp đồng", "hợp đồng thầu"],
            "gói thầu": ["gói thầu", "lô thầu", "package"],
            "dự án": ["dự án", "công trình", "project"],
            # Bidding process terms
            "đấu thầu": ["đấu thầu", "đấu thầu cạnh tranh"],
            "mời thầu": ["mời thầu", "mời chào thầu"],
            "dự thầu": ["dự thầu", "tham gia thầu", "tham dự thầu"],
            "trúng thầu": ["trúng thầu", "được lựa chọn", "thắng thầu"],
            # Evaluation terms
            "đánh giá": ["đánh giá", "xem xét", "thẩm định", "chấm thầu"],
            "xét thầu": ["xét thầu", "xét duyệt", "thẩm tra"],
            "lựa chọn": ["lựa chọn", "tuyển chọn", "chọn lựa"],
            # Technical terms
            "kỹ thuật": ["kỹ thuật", "technical", "công nghệ"],
            "thông số kỹ thuật": ["thông số kỹ thuật", "specification", "spec"],
            "yêu cầu kỹ thuật": ["yêu cầu kỹ thuật", "technical requirement"],
            # Financial terms
            "tài chính": ["tài chính", "financial", "kinh tế"],
            "giá thầu": ["giá thầu", "bid price", "giá dự thầu"],
            "chi phí": ["chi phí", "cost", "phí tổn"],
            # Document terms
            "hồ sơ": ["hồ sơ", "tài liệu", "document"],
            "biểu mẫu": ["biểu mẫu", "mẫu đơn", "form"],
            "phụ lục": ["phụ lục", "appendix", "attachment"],
        }

        # Document structure standardization
        self.structure_terms = {
            "phần": ["phần", "part", "section"],
            "chương": ["chương", "chapter"],
            "mục": ["mục", "section", "item"],
            "điều": ["điều", "article", "clause"],
            "khoản": ["khoản", "paragraph", "sub-article"],
            "điểm": ["điểm", "point", "sub-paragraph"],
            "tiểu điểm": ["tiểu điểm", "sub-point"],
        }

        # Common cleaning patterns
        self.cleaning_patterns = [
            # Remove excessive whitespace
            (r"\s+", " "),
            # Clean up line breaks
            (r"\n\s*\n\s*\n+", "\n\n"),
            # Fix punctuation spacing
            (r"\s+([,.;:!?])", r"\1"),
            (r"([,.;:!?])\s*([^\s])", r"\1 \2"),
            # Clean up quotation marks
            (r'"\s*([^"]*?)\s*"', r'"\1"'),
            (r"'\s*([^']*?)\s*'", r"'\1'"),
            # Clean up parentheses
            (r"\(\s+", "("),
            (r"\s+\)", ")"),
            # Clean up brackets
            (r"\[\s+", "["),
            (r"\s+\]", "]"),
            # Remove extra dots in numbering
            (r"(\d+)\.+(\d+)", r"\1.\2"),
            # Clean up currency formatting
            (r"(\d+)\s*(VNĐ|VND|đồng)", r"\1 VNĐ"),
            (r"(\d+)\s*(USD|Dollar)", r"\1 USD"),
        ]

        # Bidding-specific patterns
        self.bidding_patterns = [
            # Standardize time expressions
            (r"(\d+)\s*ngày\s*làm\s*việc", r"\1 ngày làm việc"),
            (r"(\d+)\s*tuần", r"\1 tuần"),
            (r"(\d+)\s*tháng", r"\1 tháng"),
            # Standardize percentage
            (r"(\d+)\s*%", r"\1%"),
            (r"(\d+)\s*phần\s*trăm", r"\1%"),
            # Standardize document references
            (r"(Điều|điều)\s+(\d+)", r"Điều \2"),
            (r"(Khoản|khoản)\s+(\d+)", r"Khoản \2"),
            (r"(Phụ\s*lục|phụ\s*lục)\s+(\w+)", r"Phụ lục \2"),
            # Clean up form references
            (r"(Mẫu|mẫu)\s*(số\s*)?(\d+[A-Z]?)", r"Mẫu \3"),
            (r"(Biểu\s*mẫu|biểu\s*mẫu)\s*(số\s*)?(\d+[A-Z]?)", r"Biểu mẫu \3"),
        ]

    def clean(self, text: str, aggressive: bool = False) -> str:
        """
        Clean bidding document text

        Args:
            text: Raw text to clean
            aggressive: Whether to apply aggressive cleaning

        Returns:
            Cleaned text
        """
        if not text or not text.strip():
            return ""

        # Start with the original text
        cleaned_text = text

        # Step 1: Unicode normalization
        cleaned_text = self._normalize_unicode(cleaned_text)

        # Step 2: Basic cleaning
        cleaned_text = self._basic_clean(cleaned_text)

        # Step 3: Bidding-specific cleaning
        cleaned_text = self._bidding_clean(cleaned_text)

        # Step 4: Structure normalization
        cleaned_text = self._normalize_structure(cleaned_text)

        # Step 5: Terminology standardization
        cleaned_text = self._standardize_terminology(cleaned_text)

        # Step 6: Aggressive cleaning if requested
        if aggressive:
            cleaned_text = self._aggressive_clean(cleaned_text)

        # Step 7: Final cleanup
        cleaned_text = self._final_cleanup(cleaned_text)

        return cleaned_text.strip()

    def _normalize_unicode(self, text: str) -> str:
        """Normalize Unicode characters"""
        # Normalize to NFC form
        text = unicodedata.normalize("NFC", text)

        # Replace common problematic characters
        replacements = {
            '"': '"',  # Curly quotes
            '"': '"',
            """: "'",
            """: "'",
            "–": "-",  # Em dash
            "—": "-",
            "…": "...",
            "\u00a0": " ",  # Non-breaking space
            "\u2009": " ",  # Thin space
            "\u200b": "",  # Zero-width space
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        return text

    def _basic_clean(self, text: str) -> str:
        """Apply basic cleaning patterns"""
        for pattern, replacement in self.cleaning_patterns:
            text = re.sub(pattern, replacement, text)
        return text

    def _bidding_clean(self, text: str) -> str:
        """Apply bidding-specific cleaning patterns"""
        for pattern, replacement in self.bidding_patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

    def _normalize_structure(self, text: str) -> str:
        """Normalize document structure elements"""
        # Normalize section headers
        text = re.sub(
            r"^(PHẦN|Phần)\s+([IVXLCDM]+|\d+)[\.\:]?\s*",
            r"PHẦN \2: ",
            text,
            flags=re.MULTILINE,
        )

        text = re.sub(
            r"^(CHƯƠNG|Chương)\s+([IVXLCDM]+|\d+)[\.\:]?\s*",
            r"CHƯƠNG \2: ",
            text,
            flags=re.MULTILINE,
        )

        # Normalize article numbering
        text = re.sub(
            r"^(Điều|ĐIỀU)\s+(\d+[a-z]?)[\.\:]?\s*",
            r"Điều \2. ",
            text,
            flags=re.MULTILINE,
        )

        # Normalize clause numbering
        text = re.sub(r"^(\d+)[\.\)]?\s+", r"\1. ", text, flags=re.MULTILINE)

        # Normalize point numbering
        text = re.sub(r"^([a-zđ])\)\s*", r"\1) ", text, flags=re.MULTILINE)

        return text

    def _standardize_terminology(self, text: str) -> str:
        """Standardize bidding terminology"""
        # Convert to lowercase for matching, but preserve original case in replacements
        for standard_term, variations in self.bidding_terminology.items():
            for variation in variations:
                if variation != standard_term:
                    # Case-insensitive replacement
                    pattern = re.escape(variation)
                    text = re.sub(
                        f"\\b{pattern}\\b", standard_term, text, flags=re.IGNORECASE
                    )

        return text

    def _aggressive_clean(self, text: str) -> str:
        """Apply aggressive cleaning for better processing"""
        # Remove form placeholders
        text = re.sub(r"\[.*?\]", "", text)
        text = re.sub(r"\.{4,}", "", text)
        text = re.sub(r"_{4,}", "", text)

        # Remove page numbers and headers/footers
        text = re.sub(r"^\s*Trang\s+\d+.*$", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\s*Page\s+\d+.*$", "", text, flags=re.MULTILINE)

        # Remove excessive formatting artifacts
        text = re.sub(r"\*{3,}", "", text)
        text = re.sub(r"-{4,}", "", text)
        text = re.sub(r"={4,}", "", text)

        return text

    def _final_cleanup(self, text: str) -> str:
        """Final cleanup pass"""
        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)

        # Clean up start and end
        text = text.strip()

        # Ensure proper line ending
        if text and not text.endswith((".", "!", "?", ":")):
            if text.endswith(","):
                text = text[:-1] + "."

        return text

    def get_cleaning_stats(
        self, original_text: str, cleaned_text: str
    ) -> Dict[str, Any]:
        """
        Get statistics about the cleaning process

        Args:
            original_text: Original text before cleaning
            cleaned_text: Text after cleaning

        Returns:
            Dictionary with cleaning statistics
        """
        original_chars = len(original_text)
        cleaned_chars = len(cleaned_text)
        chars_removed = original_chars - cleaned_chars

        original_lines = len(original_text.split("\n"))
        cleaned_lines = len(cleaned_text.split("\n"))

        stats = {
            "original_chars": original_chars,
            "cleaned_chars": cleaned_chars,
            "chars_removed": chars_removed,
            "reduction_percentage": (
                (chars_removed / original_chars * 100) if original_chars > 0 else 0
            ),
            "original_lines": original_lines,
            "cleaned_lines": cleaned_lines,
            "lines_removed": original_lines - cleaned_lines,
        }

        return stats

    def validate_cleaning(
        self, original_text: str, cleaned_text: str
    ) -> Dict[str, bool]:
        """
        Validate that cleaning didn't remove important content

        Args:
            original_text: Original text before cleaning
            cleaned_text: Text after cleaning

        Returns:
            Dictionary with validation results
        """
        validation = {
            "has_content": len(cleaned_text.strip()) > 0,
            "reasonable_length": len(cleaned_text) > len(original_text) * 0.5,
            "contains_bidding_terms": self._contains_bidding_terms(cleaned_text),
            "maintains_structure": self._maintains_structure(cleaned_text),
            "no_excessive_reduction": len(cleaned_text) > len(original_text) * 0.3,
        }

        validation["is_valid"] = all(validation.values())

        return validation

    def _contains_bidding_terms(self, text: str) -> bool:
        """Check if text contains bidding-related terms"""
        bidding_keywords = [
            "thầu",
            "đầu tư",
            "dự án",
            "hợp đồng",
            "gói thầu",
            "mời thầu",
            "dự thầu",
            "nhà thầu",
            "chủ đầu tư",
        ]

        text_lower = text.lower()
        return any(keyword in text_lower for keyword in bidding_keywords)

    def _maintains_structure(self, text: str) -> bool:
        """Check if text maintains document structure"""
        structure_indicators = [
            r"(phần|chương|mục|điều|khoản)",
            r"\d+\.",
            r"[a-z]\)",
        ]

        return any(
            re.search(pattern, text, re.IGNORECASE) for pattern in structure_indicators
        )
