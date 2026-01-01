"""
Base Extractor - Abstract class cho document extraction
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class ExtractedContent:
    """
    Generic extracted content structure
    """

    full_text: str
    metadata: Dict[str, Any]
    statistics: Dict[str, Any]
    raw_data: Any = None  # Type-specific raw data (e.g., docx.Document, PDF object)


class BaseExtractor(ABC):
    """
    Abstract base class cho tất cả document extractors
    """

    @abstractmethod
    def extract(self, file_path: str | Path) -> ExtractedContent:
        """
        Extract content từ file

        Args:
            file_path: Path to document file

        Returns:
            ExtractedContent với text, metadata, statistics

        Raises:
            FileNotFoundError: File không tồn tại
            ValueError: File format không hợp lệ
        """
        pass

    @abstractmethod
    def validate_file(self, file_path: str | Path) -> bool:
        """
        Validate file có hợp lệ không

        Args:
            file_path: Path to file

        Returns:
            True if valid, False otherwise
        """
        pass

    @abstractmethod
    def get_supported_extensions(self) -> list[str]:
        """
        Get list of supported file extensions

        Returns:
            List of extensions (e.g., ['.docx', '.doc'])
        """
        pass
