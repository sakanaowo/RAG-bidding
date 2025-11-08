"""
Text File Loader
Simple loader for plain text files (.txt)
"""

from pathlib import Path
from typing import Dict, Any
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RawTxtContent:
    """Raw text file content"""

    content: str
    filename: str
    file_size: int
    encoding: str = "utf-8"

    def __str__(self) -> str:
        return self.content


class TxtLoader:
    """
    Simple loader for plain text files.

    Supports:
    - UTF-8 and common encodings
    - Auto-encoding detection
    - Large file handling
    """

    def __init__(self):
        self.supported_encodings = ["utf-8", "utf-16", "cp1252", "latin-1"]

    def load(self, file_path: str) -> RawTxtContent:
        """
        Load text file content.

        Args:
            file_path: Path to text file

        Returns:
            RawTxtContent object with file content and metadata
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if file_path.suffix.lower() != ".txt":
            raise ValueError(f"Expected .txt file, got: {file_path.suffix}")

        # Try to detect encoding and load content
        content, encoding = self._load_with_encoding_detection(file_path)

        return RawTxtContent(
            content=content,
            filename=file_path.name,
            file_size=file_path.stat().st_size,
            encoding=encoding,
        )

    def _load_with_encoding_detection(self, file_path: Path) -> tuple[str, str]:
        """Load file with automatic encoding detection"""

        # Try each encoding until one works
        for encoding in self.supported_encodings:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    content = f.read()
                logger.info(f"Loaded {file_path.name} with encoding: {encoding}")
                return content, encoding
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.warning(
                    f"Error loading {file_path.name} with {encoding}: {str(e)}"
                )
                continue

        # If all encodings fail, try with error handling
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            logger.warning(f"Loaded {file_path.name} with UTF-8 and error replacement")
            return content, "utf-8-replace"
        except Exception as e:
            raise RuntimeError(f"Failed to load {file_path.name}: {str(e)}")
