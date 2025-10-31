"""
Law Preprocessing Package - Chuyên xử lý văn bản Luật

Modules:
- extractors/: DOCX extraction
- parsers/: Hierarchical structure parsing (Phần→Chương→Mục→Điều→Khoản→Điểm)
- cleaners/: Legal text cleaning
- validators/: Quality validation
"""

from .pipeline import LawPreprocessingPipeline
from .metadata_mapper import LawMetadataMapper

__all__ = [
    "LawPreprocessingPipeline",
    "LawMetadataMapper",
]
