"""
DOC Loader for Legacy Microsoft Word Documents (.doc)
Handles old binary Word format that python-docx cannot process directly

Strategies:
1. Try antiword (if available) - converts .doc to plain text
2. Try LibreOffice/unoconv (if available) - converts .doc to .docx
3. Fallback: Skip with clear error message

Author: Development Team
Date: 2025-11-02
"""

import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class DocLoader:
    """
    Load content from legacy .doc (binary Word) files.

    This handles old Microsoft Word binary format (.doc) which is different
    from modern Office Open XML format (.docx).
    """

    def __init__(self):
        """Initialize and check available converters"""
        self.antiword_available = self._check_antiword()
        self.libreoffice_available = self._check_libreoffice()

        if not self.antiword_available and not self.libreoffice_available:
            logger.warning(
                "No .doc converters found. Install 'antiword' or 'libreoffice' "
                "to process legacy .doc files"
            )

    def _check_antiword(self) -> bool:
        """Check if antiword is available"""
        try:
            # antiword -v returns exit code 1 but shows version
            # So we just check if the command exists
            result = subprocess.run(
                ["which", "antiword"], capture_output=True, timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _check_libreoffice(self) -> bool:
        """Check if LibreOffice is available"""
        try:
            result = subprocess.run(
                ["libreoffice", "--version"], capture_output=True, timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def extract_text_with_antiword(self, file_path: Path) -> Optional[str]:
        """
        Extract text using antiword

        Args:
            file_path: Path to .doc file

        Returns:
            Extracted text or None if failed
        """
        if not self.antiword_available:
            return None

        try:
            logger.info(f"Extracting text from {file_path.name} using antiword...")

            result = subprocess.run(
                ["antiword", "-t", str(file_path)],  # -t for UTF-8 output
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0 and result.stdout:
                logger.info(f"✅ Successfully extracted {len(result.stdout)} chars")
                return result.stdout
            else:
                logger.warning(f"antiword failed: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            logger.error(f"antiword timeout for {file_path.name}")
            return None
        except Exception as e:
            logger.error(f"antiword error: {e}")
            return None

    def convert_to_docx_with_libreoffice(
        self, file_path: Path, output_dir: Optional[Path] = None
    ) -> Optional[Path]:
        """
        Convert .doc to .docx using LibreOffice

        Args:
            file_path: Path to .doc file
            output_dir: Directory for output (default: temp dir)

        Returns:
            Path to converted .docx file or None if failed
        """
        if not self.libreoffice_available:
            return None

        # Use temp directory if not specified
        if output_dir is None:
            output_dir = Path(tempfile.mkdtemp())
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        try:
            logger.info(f"Converting {file_path.name} to .docx using LibreOffice...")

            # LibreOffice command to convert to docx
            result = subprocess.run(
                [
                    "libreoffice",
                    "--headless",
                    "--convert-to",
                    "docx",
                    "--outdir",
                    str(output_dir),
                    str(file_path),
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                # Find the converted file
                docx_filename = file_path.stem + ".docx"
                docx_path = output_dir / docx_filename

                if docx_path.exists():
                    logger.info(f"✅ Successfully converted to {docx_path}")
                    return docx_path
                else:
                    logger.warning(
                        f"Conversion succeeded but file not found: {docx_path}"
                    )
                    return None
            else:
                logger.warning(f"LibreOffice conversion failed: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            logger.error(f"LibreOffice timeout for {file_path.name}")
            return None
        except Exception as e:
            logger.error(f"LibreOffice error: {e}")
            return None

    def load(self, file_path: str | Path) -> Tuple[str, dict]:
        """
        Load content from .doc file

        Args:
            file_path: Path to .doc file

        Returns:
            Tuple of (text content, metadata)

        Raises:
            ValueError: If file cannot be processed
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise ValueError(f"File not found: {file_path}")

        if file_path.suffix.lower() != ".doc":
            raise ValueError(f"Not a .doc file: {file_path}")

        # Strategy 1: Try antiword (fastest, direct text extraction)
        if self.antiword_available:
            text = self.extract_text_with_antiword(file_path)
            if text and len(text.strip()) > 50:
                return text, {
                    "extraction_method": "antiword",
                    "source_file": file_path.name,
                    "source_format": "doc",
                }

        # Strategy 2: Try LibreOffice conversion
        if self.libreoffice_available:
            with tempfile.TemporaryDirectory() as temp_dir:
                docx_path = self.convert_to_docx_with_libreoffice(
                    file_path, Path(temp_dir)
                )

                if docx_path:
                    # Now use DocxLoader to extract from converted file
                    try:
                        from src.preprocessing.loaders.docx_loader import DocxLoader

                        docx_loader = DocxLoader()
                        raw_content = docx_loader.load(docx_path)

                        return raw_content.text, {
                            "extraction_method": "libreoffice_conversion",
                            "source_file": file_path.name,
                            "source_format": "doc",
                            "converted_via": "docx",
                        }
                    except Exception as e:
                        logger.error(f"Failed to load converted docx: {e}")

        # No conversion method worked
        raise ValueError(
            f"Cannot process .doc file: {file_path.name}. "
            f"antiword: {'✅' if self.antiword_available else '❌'}, "
            f"libreoffice: {'✅' if self.libreoffice_available else '❌'}. "
            f"Install 'antiword' or 'libreoffice' to process .doc files."
        )

    def can_process(self) -> bool:
        """Check if this loader can process .doc files"""
        return self.antiword_available or self.libreoffice_available


def install_antiword_instructions():
    """Print installation instructions for antiword"""
    print(
        """
To process .doc files, install antiword:

Ubuntu/Debian:
    sudo apt-get update
    sudo apt-get install antiword

macOS (Homebrew):
    brew install antiword

CentOS/RHEL:
    sudo yum install antiword

Or install LibreOffice as alternative:
    Ubuntu/Debian: sudo apt-get install libreoffice
    macOS: brew install --cask libreoffice
    """
    )


if __name__ == "__main__":
    # Test the loader
    import sys

    loader = DocLoader()

    print("=" * 80)
    print("DOC Loader Test")
    print("=" * 80)
    print(f"antiword available: {loader.antiword_available}")
    print(f"LibreOffice available: {loader.libreoffice_available}")
    print(f"Can process .doc files: {loader.can_process()}")
    print("=" * 80)

    if not loader.can_process():
        install_antiword_instructions()
        sys.exit(1)

    # Test with a file if provided
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        try:
            text, metadata = loader.load(test_file)
            print(f"\n✅ Successfully loaded: {test_file}")
            print(f"Method: {metadata['extraction_method']}")
            print(f"Content length: {len(text)} chars")
            print(f"\nFirst 500 chars:\n{text[:500]}")
        except Exception as e:
            print(f"\n❌ Failed to load: {e}")
            sys.exit(1)
