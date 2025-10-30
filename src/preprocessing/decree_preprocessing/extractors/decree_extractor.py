"""
Decree Extractor - Extract content from Decree DOCX files

Nghị định có structure đơn giản hơn Luật:
- Không có Phần, Mục
- Hierarchy: Chương → Điều → Khoản → Điểm
"""

from pathlib import Path
from typing import Dict
from dataclasses import dataclass

# Reuse base DOCX extractor from law_preprocessing
from ...law_preprocessing.extractors.docx_extractor import (
    DocxExtractor as BaseDocxExtractor,
    ExtractedContent,
)


class DecreeExtractor(BaseDocxExtractor):
    """
    Extract content từ Nghị định DOCX files
    
    Kế thừa từ Law's DocxExtractor nhưng với decree-specific patterns
    """

    def __init__(self, preserve_formatting: bool = False):
        """
        Args:
            preserve_formatting: Có giữ formatting không
        """
        super().__init__(preserve_formatting)
        
        # Override patterns cho Nghị định (simpler structure)
        self.patterns = {
            "chuong": r"^(CHƯƠNG|Chương)\s+([IVXLCDM]+|[0-9]+)[:\s.]",
            "dieu": r"^Điều\s+(\d+[a-z]?)[:\s.]",
            "khoan": r"^\d+\.\s+",
            "diem": r"^[a-zđ]\)\s+",
            # No Phần, Mục for decrees
        }
        
        print("✅ DecreeExtractor initialized (simplified structure)")

    def _detect_structure(self, text, current_hierarchy=None) -> dict:
        """
        Detect structure elements (override to match decree patterns)
        
        Args:
            text: Text to analyze
            current_hierarchy: Current hierarchy context (unused for decrees)
            
        Returns:
            Dictionary with structure info
        """
        # Simple structure detection for decrees
        struct_info = {"type": None, "number": None, "title": None}
        
        # Check for Chương
        if match := self._match_pattern("chuong", text):
            struct_info["type"] = "chuong"
            struct_info["number"] = match.group(2)
            struct_info["title"] = match.group(0)
        
        # Check for Điều
        elif match := self._match_pattern("dieu", text):
            struct_info["type"] = "dieu"
            struct_info["number"] = match.group(1)
            struct_info["title"] = text
        
        return struct_info

    def _match_pattern(self, pattern_name: str, text: str):
        """Match regex pattern"""
        import re
        pattern = self.patterns.get(pattern_name)
        if pattern:
            return re.match(pattern, text.strip())
        return None

    def _extract_metadata(self, doc, docx_path=None) -> Dict:
        """
        Extract decree-specific metadata
        
        Returns:
            Dictionary với decree metadata
        """
        metadata = super()._extract_metadata(doc, docx_path)
        
        # Override doc_type
        metadata["doc_type"] = "decree"
        
        # Extract decree number from title (e.g., "Nghị định 214/2025/NĐ-CP")
        title = metadata.get("title", "")
        import re
        
        if match := re.search(r"Nghị định\s+(\d+)/(\d{4})/NĐ-CP", title):
            metadata["doc_number"] = match.group(1)
            metadata["doc_year"] = match.group(2)
        elif match := re.search(r"NĐ[-\s]?(\d+)", title):
            metadata["doc_number"] = match.group(1)
        
        return metadata
