"""
Base models for preprocessing pipeline.

Provides:
- ProcessedDocument: Standard output from loaders
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class ProcessedDocument:
    """
    Standard document format output from loaders.

    This is the intermediate format between loaders and chunkers:
    Loader → ProcessedDocument → Chunker → UniversalChunk → UnifiedLegalChunk

    Attributes:
        metadata: Document metadata (type, title, dates, legal info, etc.)
        content: Document content (full_text, structure, tables, etc.)
    """

    metadata: Dict[str, Any]
    content: Dict[str, Any]

    def __post_init__(self):
        """Validate required fields"""
        # Ensure full_text exists
        if "full_text" not in self.content:
            self.content["full_text"] = ""

        # Ensure document_type exists
        if "document_type" not in self.metadata:
            self.metadata["document_type"] = "unknown"
