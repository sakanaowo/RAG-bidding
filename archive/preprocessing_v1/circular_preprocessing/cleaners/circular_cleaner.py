"""
Circular Document Cleaner

Clean and normalize text extracted from Vietnamese Circular documents.
Focuses on circular-specific patterns and terminology standardization.
"""

import re
from typing import Dict, List


class CircularCleaner:
    """Clean and normalize Circular documents"""

    def __init__(self):
        # Circular-specific terms to standardize
        self.circular_terms = {
            # Standardize circular terminology
            r"thông\s*tư": "thông tư",
            r"quy\s*định": "quy định",
            r"hướng\s*dẫn": "hướng dẫn",
            r"thi\s*hành": "thi hành",
            r"áp\s*dụng": "áp dụng",
            r"triển\s*khai": "triển khai",
            r"thực\s*hiện": "thực hiện",
            # Administrative terms
            r"bộ\s*trưởng": "bộ trưởng",
            r"thứ\s*trưởng": "thứ trưởng",
            r"tổng\s*cục\s*trưởng": "tổng cục trưởng",
            r"cục\s*trưởng": "cục trưởng",
            # Bidding terms (inherited from law cleaner)
            r"đấu\s*thầu": "đấu thầu",
            r"nhà\s*thầu": "nhà thầu",
            r"gói\s*thầu": "gói thầu",
            r"hồ\s*sơ\s*mời\s*thầu": "hồ sơ mời thầu",
            r"hồ\s*sơ\s*dự\s*thầu": "hồ sơ dự thầu",
        }

        # Circular structure patterns
        self.structure_patterns = {
            "circular_header": r"^(THÔNG TƯ|Thông tư)\s*$",
            "regulation": r"^(QUY ĐỊNH|Quy định)\s+(\d+)\.?\s*",
            "guidance": r"^(HƯỚNG DẪN|Hướng dẫn)\s+(\d+)\.?\s*",
            "implementation": r"^(THI HÀNH|Thi hành)\s+(\d+)\.?\s*",
        }

    def clean(self, text: str, aggressive: bool = False) -> str:
        """
        Main cleaning method for Circular documents

        Args:
            text: Raw text to clean
            aggressive: If True, apply more aggressive cleaning

        Returns:
            Cleaned text
        """
        # Step 1: Basic cleaning
        text = self._basic_clean(text)

        # Step 2: Circular-specific cleaning
        text = self._circular_clean(text)

        # Step 3: Normalize terminology
        text = self._normalize_circular_terms(text)

        # Step 4: Structure cleaning
        text = self._clean_structure(text)

        # Step 5: Aggressive cleaning (optional)
        if aggressive:
            text = self._aggressive_clean(text)

        return text

    def _basic_clean(self, text: str) -> str:
        """Basic text cleaning"""

        # Remove zero-width characters
        text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)

        # Normalize whitespace
        text = re.sub(r"[ \t]+", " ", text)  # Multiple spaces to single

        # Normalize newlines
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)  # Max 2 newlines

        # Remove trailing whitespace
        lines = [line.rstrip() for line in text.split("\n")]
        text = "\n".join(lines)

        # Remove leading/trailing whitespace
        text = text.strip()

        return text

    def _circular_clean(self, text: str) -> str:
        """Cleaning specific to Circular documents"""

        # Normalize circular headers
        text = re.sub(
            r"^(THÔNG TƯ|thông tư)\s*số\s*(\d+/[\d/A-Z-]+)",
            r"THÔNG TƯ số \2",
            text,
            flags=re.MULTILINE | re.IGNORECASE,
        )

        # Standardize regulation numbering
        text = re.sub(
            r"^(QUY ĐỊNH|Quy định)\s+(\d+)\s*[\.:]?\s*",
            r"Quy định \2. ",
            text,
            flags=re.MULTILINE,
        )

        # Standardize guidance numbering
        text = re.sub(
            r"^(HƯỚNG DẪN|Hướng dẫn)\s+(\d+)\s*[\.:]?\s*",
            r"Hướng dẫn \2. ",
            text,
            flags=re.MULTILINE,
        )

        # Clean up article references
        text = re.sub(r"Điều\s+(\d+[a-z]?)\s*[\.:]", r"Điều \1.", text)

        # Clean up clause numbering
        text = re.sub(r"^(\d+)\s*[\.:]?\s+", r"\1. ", text, flags=re.MULTILINE)

        # Clean up point lettering
        text = re.sub(r"^([a-zđ])\s*\)\s*", r"\1) ", text, flags=re.MULTILINE)

        return text

    def _normalize_circular_terms(self, text: str) -> str:
        """Normalize circular-specific terminology"""

        for pattern, replacement in self.circular_terms.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        return text

    def _clean_structure(self, text: str) -> str:
        """Clean structural elements"""

        # Remove excessive blank lines around headers
        for pattern_name, pattern in self.structure_patterns.items():
            text = re.sub(
                rf"\n\s*\n\s*({pattern})", r"\n\n\1", text, flags=re.MULTILINE
            )

        # Ensure proper spacing after structural elements
        text = re.sub(
            r"^(Điều\s+\d+[a-z]?\.)([^\s])", r"\1 \2", text, flags=re.MULTILINE
        )

        text = re.sub(r"^(\d+\.)([^\s])", r"\1 \2", text, flags=re.MULTILINE)

        text = re.sub(r"^([a-zđ]\))([^\s])", r"\1 \2", text, flags=re.MULTILINE)

        return text

    def _aggressive_clean(self, text: str) -> str:
        """More aggressive cleaning (optional)"""

        # Remove page numbers
        text = re.sub(r"^\s*Trang\s+\d+\s*$", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\s*-\s*\d+\s*-\s*$", "", text, flags=re.MULTILINE)

        # Remove headers/footers
        text = re.sub(
            r"^\s*(BỘ|TỔNG CỤC|CỤC)\s+[A-ZÀ-Ỹ\s]+\s*$", "", text, flags=re.MULTILINE
        )

        # Remove signature blocks
        text = re.sub(
            r"\n\s*(Nơi nhận:|THỦ TRƯỞNG|BỘ TRƯỞNG|TỔNG CỤC TRƯỞNG)[\s\S]*?$", "", text
        )

        # Remove document control numbers
        text = re.sub(r"^\s*[A-Z]{2,}\s*/\s*\d+\s*$", "", text, flags=re.MULTILINE)

        # Clean up resulting multiple newlines
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
        text = text.strip()

        return text

    def get_cleaning_stats(self, original: str, cleaned: str) -> Dict[str, int]:
        """Get statistics about the cleaning process"""

        return {
            "original_length": len(original),
            "cleaned_length": len(cleaned),
            "chars_removed": len(original) - len(cleaned),
            "original_lines": len(original.split("\n")),
            "cleaned_lines": len(cleaned.split("\n")),
            "lines_removed": len(original.split("\n")) - len(cleaned.split("\n")),
            "reduction_percentage": (
                round((len(original) - len(cleaned)) / len(original) * 100, 2)
                if original
                else 0
            ),
        }

    def validate_cleaning(self, original: str, cleaned: str) -> Dict[str, bool]:
        """Validate that cleaning didn't remove important content"""

        validation = {
            "has_articles": bool(re.search(r"Điều\s+\d+", cleaned)),
            "has_clauses": bool(re.search(r"^\d+\.", cleaned, re.MULTILINE)),
            "has_points": bool(re.search(r"^[a-zđ]\)", cleaned, re.MULTILINE)),
            "reasonable_length": len(cleaned)
            > len(original) * 0.5,  # At least 50% of original
            "no_excessive_whitespace": not bool(
                re.search(r"\n\s*\n\s*\n\s*\n", cleaned)
            ),
        }

        validation["overall_valid"] = all(validation.values())

        return validation
