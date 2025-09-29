"""
Markdown Document Preprocessing Module

Module này cung cấp các công cụ để tiền xử lý văn bản pháp luật từ file .md
với YAML frontmatter thành chunks tối ưu cho hệ thống RAG.

Main Classes:
- MarkdownDocumentProcessor: Parse và xử lý .md files
- OptimalLegalChunker: Chunking strategy tối ưu cho văn bản pháp luật
- TokenChecker: Kiểm tra token limits cho embedding models
"""

from .md_processor import MarkdownDocumentProcessor
from .optimal_chunker import OptimalLegalChunker, LawChunk
from .utils import TokenChecker, process_md_documents_pipeline

__version__ = "1.0.0"
__all__ = [
    "MarkdownDocumentProcessor",
    "OptimalLegalChunker",
    "LawChunk",
    "TokenChecker",
    "process_md_documents_pipeline",
]
