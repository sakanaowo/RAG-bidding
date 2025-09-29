"""Custom exceptions for data processing pipeline."""

import logging
from typing import Optional, Any, Dict

logger = logging.getLogger(__name__)


class DataProcessingError(Exception):
    """Base exception for data processing errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def log_error(self):
        """Log the error with details."""
        logger.error(f"{self.__class__.__name__}: {self.message}")
        if self.details:
            for key, value in self.details.items():
                logger.error(f"  {key}: {value}")


class FileLoadError(DataProcessingError):
    """Exception raised when file loading fails."""

    def __init__(
        self, file_path: str, reason: str, original_error: Optional[Exception] = None
    ):
        details = {
            "file_path": file_path,
            "reason": reason,
            "original_error": str(original_error) if original_error else None,
        }
        super().__init__(f"Failed to load file: {file_path}", details)


class DocumentValidationError(DataProcessingError):
    """Exception raised when document validation fails."""

    def __init__(self, document_info: str, validation_issues: list):
        details = {
            "document_info": document_info,
            "validation_issues": validation_issues,
        }
        super().__init__(f"Document validation failed: {document_info}", details)


class TextCleaningError(DataProcessingError):
    """Exception raised when text cleaning fails."""

    def __init__(self, reason: str, text_preview: Optional[str] = None):
        details = {
            "reason": reason,
            "text_preview": (
                text_preview[:200] + "..."
                if text_preview and len(text_preview) > 200
                else text_preview
            ),
        }
        super().__init__(f"Text cleaning failed: {reason}", details)


class VectorStoreError(DataProcessingError):
    """Exception raised when vector store operations fail."""

    def __init__(self, operation: str, reason: str):
        details = {"operation": operation, "reason": reason}
        super().__init__(f"Vector store {operation} failed: {reason}", details)


class ChunkingError(DataProcessingError):
    """Exception raised when text splitting/chunking fails."""

    def __init__(self, reason: str, document_info: Optional[str] = None):
        details = {"reason": reason, "document_info": document_info}
        super().__init__(f"Text chunking failed: {reason}", details)


def handle_processing_error(
    error: Exception, context: str = "", reraise: bool = True
) -> Optional[Exception]:
    """
    Handle processing errors with consistent logging and optional re-raising.

    Args:
        error: The exception that occurred
        context: Additional context about where the error occurred
        reraise: Whether to re-raise the exception after logging

    Returns:
        The exception if not re-raised, None otherwise
    """
    # Log the error
    if isinstance(error, DataProcessingError):
        error.log_error()
    else:
        logger.error(f"Unexpected error in {context}: {str(error)}", exc_info=True)

    if reraise:
        raise error

    return error


class SafeProcessor:
    """A wrapper class for safe processing with error handling."""

    @staticmethod
    def safe_file_read(
        file_path: str, encoding: str = "utf-8", fallback_encodings: list = None
    ) -> str:
        """Safely read file with fallback encodings."""
        fallback_encodings = fallback_encodings or ["latin1", "cp1252", "iso-8859-1"]

        # Try primary encoding
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError as e:
            logger.warning(f"Failed to read {file_path} with {encoding}: {e}")

        # Try fallback encodings
        for fallback_encoding in fallback_encodings:
            try:
                with open(file_path, "r", encoding=fallback_encoding) as f:
                    content = f.read()
                    logger.info(
                        f"Successfully read {file_path} with fallback encoding: {fallback_encoding}"
                    )
                    return content
            except UnicodeDecodeError:
                continue

        # If all encodings fail, raise error
        raise FileLoadError(
            file_path=file_path,
            reason=f"Failed to decode with encodings: {[encoding] + fallback_encodings}",
        )

    @staticmethod
    def safe_process_with_retry(func, *args, max_retries: int = 3, **kwargs):
        """Execute function with retry mechanism."""
        last_error = None

        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    import time

                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff

        # All attempts failed
        raise last_error
