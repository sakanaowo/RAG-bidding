"""
Document ID Generator - For future document uploads

Tự động tạo document_id theo Hybrid System khi upload văn bản mới
Format: {type_code}-{số_hiệu}/{năm}#{hash_short}
"""

import re
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict


class DocumentIDGenerator:
    """
    Generator cho document_id theo Hybrid System

    Usage:
        generator = DocumentIDGenerator()
        doc_id = generator.generate("43-2022-ND-CP.pdf", "decree")
        # Output: ND-43/2022#a7f3c9
    """

    # Type code mapping
    TYPE_CODE_MAP = {
        "law": "LAW",
        "decree": "ND",
        "circular": "TT",
        "decision": "QD",
        "bidding": "FORM",
        "report": "RPT",
        "exam": "EXAM",
        "document": "DOC",
    }

    # Regex patterns để extract số hiệu và năm từ filename
    PATTERNS = {
        "decree": [
            r"(\d+)[-_/](\d{4})[-_/](?:NĐ|ND)[-_]?(?:CP|TTg)?",  # 43-2022-ND-CP
            r"(?:NĐ|ND)[-_](\d+)[-_/](\d{4})",  # ND-43-2022
            r"Nghi[-_]?dinh[-_](\d+)[-_/](\d{4})",  # Nghi-dinh-43-2022
        ],
        "circular": [
            r"(\d+)[-_/](\d{4})[-_/]TT",  # 20-2020-TT-BTC
            r"TT[-_](\d+)[-_/](\d{4})",  # TT-20-2020
            r"Thong[-_]?tu[-_](\d+)[-_/](\d{4})",  # Thong-tu-20-2020
        ],
        "decision": [
            r"(\d+)[-_/](\d{4})[-_/](?:QĐ|QD)",  # 123-2021-QD-TTg
            r"(?:QĐ|QD)[-_](\d+)[-_/](\d{4})",  # QD-123-2021
            r"Quyet[-_]?dinh[-_](\d+)[-_/](\d{4})",  # Quyet-dinh-123-2021
        ],
        "law": [
            r"Luat[-_].*?[-_](\d+)[-_/](\d{4})",  # Luat-Xay-dung-59-2020
            r"Law[-_](\d+)[-_/](\d{4})",  # Law-59-2020
            r"(\d+)[-_/](\d{4})[-_/](?:QH\d+)",  # 59-2020-QH14
        ],
    }

    def __init__(self):
        pass

    def _extract_from_filename(
        self, filename: str, doc_type: str
    ) -> Optional[Dict[str, str]]:
        """
        Extract số hiệu và năm từ filename

        Returns:
            Dict với keys: number, year hoặc None nếu không extract được
        """
        # Get patterns cho doc_type
        patterns = self.PATTERNS.get(doc_type, [])

        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                return {"number": match.group(1), "year": match.group(2)}

        # Fallback: try extract year only
        year_match = re.search(r"(20\d{2})", filename)
        if year_match:
            return {"number": None, "year": year_match.group(1)}

        return None

    def _generate_hash(self, source: str) -> str:
        """Generate short hash từ source string"""
        hash_obj = hashlib.md5(source.encode())
        return hash_obj.hexdigest()[:6]

    def generate(
        self,
        file_path: str,
        doc_type: str,
        force_number: Optional[str] = None,
        force_year: Optional[str] = None,
    ) -> str:
        """
        Generate document_id từ file_path và doc_type

        Args:
            file_path: Path tới file (có thể relative hoặc absolute)
            doc_type: Loại document (law, decree, circular, etc.)
            force_number: Force số hiệu cụ thể (override auto-detect)
            force_year: Force năm cụ thể (override auto-detect)

        Returns:
            Document ID theo format: {type_code}-{number}/{year}#{hash}

        Examples:
            >>> gen = DocumentIDGenerator()
            >>> gen.generate("43-2022-ND-CP.pdf", "decree")
            'ND-43/2022#a7f3c9'

            >>> gen.generate("Thong-tu-20-2020.pdf", "circular")
            'TT-20/2020#b4d8e1'

            >>> gen.generate("mau-ho-so.pdf", "bidding")
            'FORM-20251109/2024#c9a2d7'
        """
        # Get filename
        filename = Path(file_path).stem

        # Get type code
        type_code = self.TYPE_CODE_MAP.get(doc_type, "DOC")

        # Extract number và year
        extracted = self._extract_from_filename(filename, doc_type)

        if force_number:
            number = force_number
        elif extracted and extracted.get("number"):
            number = extracted["number"]
        else:
            # Fallback: use timestamp as number
            number = datetime.now().strftime("%Y%m%d")

        if force_year:
            year = force_year
        elif extracted and extracted.get("year"):
            year = extracted["year"]
        else:
            # Fallback: current year
            year = datetime.now().strftime("%Y")

        # Generate hash từ full file_path để uniqueness
        hash_short = self._generate_hash(file_path)

        # Build document_id
        doc_id = f"{type_code}-{number}/{year}#{hash_short}"

        return doc_id

    def batch_generate(
        self, file_paths: list[str], doc_types: list[str]
    ) -> Dict[str, str]:
        """
        Generate document_ids cho nhiều files cùng lúc

        Args:
            file_paths: List các file paths
            doc_types: List các doc types (cùng length với file_paths)

        Returns:
            Dict mapping file_path → document_id
        """
        if len(file_paths) != len(doc_types):
            raise ValueError("file_paths and doc_types must have same length")

        results = {}
        for file_path, doc_type in zip(file_paths, doc_types):
            doc_id = self.generate(file_path, doc_type)
            results[file_path] = doc_id

        return results


def demo():
    """Demo usage"""
    generator = DocumentIDGenerator()

    print("=" * 80)
    print("Document ID Generator - Demo")
    print("=" * 80)
    print()

    # Test cases
    test_cases = [
        # (file_path, doc_type)
        ("43-2022-ND-CP.pdf", "decree"),
        ("Nghi-dinh-50-2024-ND-CP.pdf", "decree"),
        ("20-2020-TT-BTC.pdf", "circular"),
        ("Thong-tu-15-2023.pdf", "circular"),
        ("123-2021-QD-TTg.pdf", "decision"),
        ("Luat-Xay-dung-59-2020.pdf", "law"),
        ("mau-ho-so-dau-thau.pdf", "bidding"),
        ("bao-cao-thang-11.pdf", "report"),
        ("de-thi-chuyen-vien.pdf", "exam"),
    ]

    for file_path, doc_type in test_cases:
        doc_id = generator.generate(file_path, doc_type)
        print(f"[{doc_type:10s}] {file_path:40s} → {doc_id}")

    print()
    print("=" * 80)
    print("✅ Demo completed!")
    print("=" * 80)


if __name__ == "__main__":
    demo()
