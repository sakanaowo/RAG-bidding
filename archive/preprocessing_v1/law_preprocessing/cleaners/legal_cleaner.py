"""
Legal Document Cleaner cho văn bản đấu thầu

Module này clean và normalize text extracted từ DOCX
với focus vào văn bản pháp luật Việt Nam về đấu thầu
"""

import re
from typing import Dict, List


class LegalDocumentCleaner:
    """Clean và normalize văn bản pháp luật"""

    def __init__(self):
        # Bidding-specific terms cần standardize
        self.bidding_terms = {
            # Standardize các thuật ngữ đấu thầu
            r"đấu\s*thầu": "đấu thầu",
            r"nhà\s*thầu": "nhà thầu",
            r"gói\s*thầu": "gói thầu",
            r"hồ\s*sơ\s*mời\s*thầu": "hồ sơ mời thầu",
            r"hồ\s*sơ\s*dự\s*thầu": "hồ sơ dự thầu",
            r"kế\s*hoạch\s*lựa\s*chọn\s*nhà\s*thầu": "kế hoạch lựa chọn nhà thầu",
            r"e[\s-]?procurement": "e-procurement",
        }

    def clean(self, text: str, aggressive: bool = False) -> str:
        """
        Main cleaning method

        Args:
            text: Raw text to clean
            aggressive: Nếu True, apply cleaning mạnh hơn

        Returns:
            Cleaned text
        """
        # Step 1: Basic cleaning
        text = self._basic_clean(text)

        # Step 2: Legal document specific cleaning
        text = self._legal_clean(text)

        # Step 3: Normalize bidding terms
        text = self._normalize_bidding_terms(text)

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

    def _legal_clean(self, text: str) -> str:
        """Cleaning đặc biệt cho văn bản pháp luật"""

        # Chuẩn hóa cấu trúc Điều
        text = re.sub(r"Điều\s+(\d+[a-z]?)\s*[:\.]", r"Điều \1.", text)

        # Chuẩn hóa CHƯƠNG
        text = re.sub(
            r"(CHƯƠNG|Chương)\s+([IVXLCDM]+)\s*[:\.]",
            r"\1 \2.",
            text,
            flags=re.I,
        )

        # Chuẩn hóa MỤC
        text = re.sub(r"(MỤC|Mục)\s+(\d+)\s*[:\.]", r"\1 \2.", text, flags=re.I)

        # Chuẩn hóa khoản (numbered lists)
        text = re.sub(r"^(\d+)\s*[\.。]\s+", r"\1. ", text, flags=re.MULTILINE)

        # Chuẩn hóa điểm (lettered lists)
        text = re.sub(r"^([a-zđ])\s*\)\s+", r"\1) ", text, flags=re.MULTILINE)

        return text

    def _normalize_bidding_terms(self, text: str) -> str:
        """Chuẩn hóa các thuật ngữ đấu thầu"""

        for pattern, replacement in self.bidding_terms.items():
            text = re.sub(pattern, replacement, text, flags=re.I)

        return text

    def _clean_structure(self, text: str) -> str:
        """Clean structural issues"""

        # Remove page numbers (isolated numbers)
        text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)

        # Remove header/footer artifacts
        artifacts = [
            r"^Trang\s+\d+\s*(/\s*\d+)?$",  # Page numbers
            r"^Bản\s+sao\s+lưu\s+trữ$",  # Archive copy markers
        ]

        for pattern in artifacts:
            text = re.sub(pattern, "", text, flags=re.MULTILINE | re.I)

        # Remove table markers
        text = re.sub(r"\[TABLE\]\s*\n", "", text)

        return text

    def _aggressive_clean(self, text: str) -> str:
        """Aggressive cleaning (có thể remove useful content)"""

        # Remove very short lines (likely artifacts)
        lines = text.split("\n")
        lines = [line for line in lines if len(line.strip()) > 5 or not line.strip()]
        text = "\n".join(lines)

        # Remove duplicate lines
        lines = text.split("\n")
        unique_lines = []
        prev_line = None

        for line in lines:
            if line != prev_line:
                unique_lines.append(line)
            prev_line = line

        text = "\n".join(unique_lines)

        return text

    def validate_cleaned_text(self, text: str) -> Dict:
        """Validate cleaned text"""

        validation = {
            "is_valid": True,
            "warnings": [],
            "errors": [],
            "statistics": {},
        }

        # Check for key legal structures
        has_dieu = bool(re.search(r"Điều\s+\d+", text))
        has_chuong = bool(re.search(r"(CHƯƠNG|Chương)\s+[IVXLCDM]+", text, re.I))

        if not has_dieu:
            validation["warnings"].append("No 'Điều' structure found")

        if not has_chuong:
            validation["warnings"].append("No 'Chương' structure found")

        # Check length
        if len(text) < 1000:
            validation["warnings"].append("Document seems too short")

        # Statistics
        validation["statistics"] = {
            "char_count": len(text),
            "line_count": len(text.split("\n")),
            "word_count": len(text.split()),
            "has_dieu": has_dieu,
            "has_chuong": has_chuong,
        }

        return validation

    def extract_metadata_from_text(self, text: str) -> Dict:
        """
        Extract metadata từ nội dung văn bản
        (tìm thông tin trong phần header/title)
        """
        metadata = {
            "effective_date": None,
            "issuing_agency": None,
            "signers": [],
        }

        # Extract effective date
        date_patterns = [
            r"(?:có\s+)?hiệu\s+lực\s+(?:từ\s+)?(?:ngày\s+)?(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
            r"(?:có\s+)?hiệu\s+lực\s+(?:từ\s+)?(?:ngày\s+)?(\d{1,2}\s+tháng\s+\d{1,2}\s+năm\s+\d{4})",
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text, re.I)
            if match:
                metadata["effective_date"] = match.group(1)
                break

        # Extract issuing agency
        agency_patterns = [
            r"(QUỐC HỘI|Quốc hội)",
            r"(CHÍNH PHỦ|Chính phủ)",
            r"(BỘ TÀI CHÍNH|Bộ Tài chính)",
            r"(BỘ KẾ HOẠCH VÀ ĐẦU TƯ|Bộ Kế hoạch và Đầu tư)",
        ]

        for pattern in agency_patterns:
            match = re.search(pattern, text[:2000], re.I)  # Check first 2000 chars
            if match:
                metadata["issuing_agency"] = match.group(1)
                break

        # Extract signers
        signer_patterns = [
            r"(?:CHỦ TỊCH|Chủ tịch)\s+(.+?)(?:\n|$)",
            r"(?:THỦ TƯỚNG|Thủ tướng)\s+(.+?)(?:\n|$)",
            r"(?:BỘ TRƯỞNG|Bộ trưởng)\s+(.+?)(?:\n|$)",
        ]

        for pattern in signer_patterns:
            match = re.search(pattern, text[-3000:], re.I)  # Check last 3000 chars
            if match:
                metadata["signers"].append(match.group(1).strip())

        return metadata


# ============ USAGE EXAMPLE ============

if __name__ == "__main__":
    sample_text = """
    CHƯƠNG   I:  QUY   ĐỊNH  CHUNG
    
    Điều  1  .  Phạm  vi  điều  chỉnh
    
    1.  Luật này quy định về   đấu   thầu   và lựa chọn   nhà   thầu .
    
    2.  Quy định về   hồ   sơ   mời   thầu  và   hồ   sơ   dự   thầu  .
    
    a)  Yêu cầu về năng lực của   nhà   thầu
    
    b)  Tiêu chí đánh giá
    
    
    
    
    Trang 1
    
    Điều  2  .  Đối tượng áp dụng
    """

    cleaner = LegalDocumentCleaner()

    print("=" * 80)
    print("LEGAL DOCUMENT CLEANER")
    print("=" * 80)

    print("\n📄 Original text:")
    print(sample_text)

    cleaned = cleaner.clean(sample_text, aggressive=True)

    print("\n✨ Cleaned text:")
    print(cleaned)

    validation = cleaner.validate_cleaned_text(cleaned)
    print(f"\n✅ Validation:")
    print(f"   Valid: {validation['is_valid']}")
    print(f"   Warnings: {validation['warnings']}")
    print(f"   Stats: {validation['statistics']}")

    metadata = cleaner.extract_metadata_from_text(cleaned)
    print(f"\n📋 Extracted metadata:")
    for key, value in metadata.items():
        print(f"   {key}: {value}")
