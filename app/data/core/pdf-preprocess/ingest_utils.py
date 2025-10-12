import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config.models import settings
from config.logging_config import get_processing_logger, reset_processing_metrics
from app.data.cleaners import vietnamese_specific_clean, advanced_clean, basic_clean
from app.data.validators import create_default_validator, create_default_deduplicator
from app.data.exceptions import (
    FileLoadError,
    DocumentValidationError,
    SafeProcessor,
    handle_processing_error,
)

# Setup logging
logger = get_processing_logger(__name__)

ALLOWED_EXT = {e.strip().lower() for e in settings.allowed_ext}


def load_folder(
    root: str,
    clean_text: bool = True,
    validate_docs: bool = True,
    deduplicate: bool = True,
) -> Tuple[List[Document], Dict[str, Any]]:
    """
    Load documents from folder with enhanced processing.

    Args:
        root: Root folder path to scan
        clean_text: Whether to apply text cleaning
        validate_docs: Whether to validate documents
        deduplicate: Whether to remove duplicates

    Returns:
        Tuple of (documents, processing_stats)
    """
    # Reset metrics for this processing session
    reset_processing_metrics()

    start_time = time.time()
    logger.log_processing_start("folder_loading", {"root_folder": root})

    # Initialize processors
    validator = create_default_validator() if validate_docs else None
    deduplicator = create_default_deduplicator() if deduplicate else None

    docs: List[Document] = []
    stats = {
        "total_files_found": 0,
        "files_processed": 0,
        "files_failed": 0,
        "documents_created": 0,
        "processing_errors": [],
    }

    # Scan for files
    all_files = list(Path(root).rglob("*"))
    eligible_files = [
        p for p in all_files if p.is_file() and p.suffix.lower() in ALLOWED_EXT
    ]

    stats["total_files_found"] = len(eligible_files)
    logger.logger.info(f"Found {len(eligible_files)} eligible files in {root}")

    # Process each file
    for file_path in eligible_files:
        try:
            file_docs = _load_single_file(file_path, clean_text=clean_text)
            docs.extend(file_docs)
            stats["files_processed"] += 1
            stats["documents_created"] += len(file_docs)

            logger.log_document_processed(str(file_path), len(file_docs))

        except Exception as e:
            stats["files_failed"] += 1
            error_info = {
                "file": str(file_path),
                "error": str(e),
                "error_type": type(e).__name__,
            }
            stats["processing_errors"].append(error_info)

            logger.log_document_failed(
                str(file_path), str(e), error_type=type(e).__name__
            )

            # Don't stop processing, continue with other files
            continue

    # Validation step
    if validate_docs and validator and docs:
        validation_start = time.time()
        valid_docs, invalid_docs, validation_stats = validator.validate_documents(docs)
        validation_duration = time.time() - validation_start

        docs = valid_docs
        stats["validation"] = validation_stats
        stats["validation_duration"] = validation_duration

        logger.log_validation_result(
            len(valid_docs), len(invalid_docs), details=validation_stats
        )

    # Deduplication step
    if deduplicate and deduplicator and docs:
        dedup_start = time.time()
        unique_docs, duplicate_docs, dedup_stats = deduplicator.deduplicate_documents(
            docs
        )
        dedup_duration = time.time() - dedup_start

        docs = unique_docs
        stats["deduplication"] = dedup_stats
        stats["deduplication_duration"] = dedup_duration

        logger.log_deduplication_result(
            len(unique_docs), len(duplicate_docs), details=dedup_stats
        )

    # Final stats
    processing_duration = time.time() - start_time
    stats["total_processing_duration"] = processing_duration
    stats["final_document_count"] = len(docs)

    logger.log_processing_end("folder_loading", processing_duration, details=stats)
    logger.log_processing_summary()

    return docs, stats


def _load_single_file(file_path: Path, clean_text: bool = True) -> List[Document]:
    """Load a single file and return list of documents."""
    docs: List[Document] = []
    suffix = file_path.suffix.lower()

    try:
        if suffix in {".txt", ".md"}:
            # Load text files with safe encoding handling
            text = SafeProcessor.safe_file_read(str(file_path))

            if clean_text:
                if suffix == ".txt":
                    text = vietnamese_specific_clean(
                        text
                    )  # More thorough for Vietnamese docs
                else:
                    text = advanced_clean(text)

            if text.strip():  # Only create document if there's actual content
                docs.append(
                    Document(
                        page_content=text,
                        metadata={
                            "path": str(file_path.resolve()),
                            "file_type": suffix,
                            "file_size": file_path.stat().st_size,
                            "cleaned": clean_text,
                        },
                    )
                )

        elif suffix == ".pdf":
            docs.extend(_load_pdf_file(file_path, clean_text))

        elif suffix == ".docx":
            docs.extend(_load_docx_file(file_path, clean_text))

        else:
            raise FileLoadError(str(file_path), f"Unsupported file type: {suffix}")

    except Exception as e:
        # Wrap and re-raise with more context
        raise FileLoadError(
            str(file_path), f"Error loading {suffix} file: {str(e)}", original_error=e
        )

    return docs


def _load_pdf_file(file_path: Path, clean_text: bool = True) -> List[Document]:
    """Load PDF file with error handling."""
    try:
        from langchain_community.document_loaders import PyPDFLoader

        loader = PyPDFLoader(str(file_path.resolve()))
        docs = loader.load()

        # Clean text if requested
        if clean_text:
            for doc in docs:
                if doc.page_content:
                    doc.page_content = vietnamese_specific_clean(doc.page_content)

                    # Add cleaning metadata
                    if not doc.metadata:
                        doc.metadata = {}
                    doc.metadata.update(
                        {
                            "cleaned": True,
                            "file_size": file_path.stat().st_size,
                            "file_type": ".pdf",
                        }
                    )

        return docs

    except ImportError:
        raise FileLoadError(
            str(file_path), "PyPDFLoader not available. Install langchain-community."
        )
    except Exception as e:
        raise FileLoadError(
            str(file_path), f"PDF loading failed: {str(e)}", original_error=e
        )


def _load_docx_file(file_path: Path, clean_text: bool = True) -> List[Document]:
    """Load DOCX file with error handling."""
    try:
        from langchain_community.document_loaders import Docx2txtLoader

        loader = Docx2txtLoader(str(file_path.resolve()))
        docs = loader.load()

        # Clean text if requested
        if clean_text:
            for doc in docs:
                if doc.page_content:
                    doc.page_content = vietnamese_specific_clean(doc.page_content)

                    # Add cleaning metadata
                    if not doc.metadata:
                        doc.metadata = {}
                    doc.metadata.update(
                        {
                            "cleaned": True,
                            "file_size": file_path.stat().st_size,
                            "file_type": ".docx",
                        }
                    )

        return docs

    except ImportError:
        raise FileLoadError(
            str(file_path), "Docx2txtLoader not available. Install langchain-community."
        )
    except Exception as e:
        raise FileLoadError(
            str(file_path), f"DOCX loading failed: {str(e)}", original_error=e
        )


def create_enhanced_text_splitter() -> RecursiveCharacterTextSplitter:
    """Create text splitter with enhanced settings for Vietnamese text."""

    # Vietnamese-specific separators (in addition to defaults)
    vietnamese_separators = [
        "\n\n",  # Paragraph breaks
        "\n",  # Line breaks
        ". ",  # Sentence endings
        ".\n",  # Sentence endings with newline
        "! ",  # Exclamation
        "? ",  # Questions
        "; ",  # Semicolons
        ", ",  # Commas (as last resort)
        " ",  # Spaces
        "",  # Character level
    ]

    return RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=vietnamese_separators,
        keep_separator=True,
        is_separator_regex=False,
        length_function=len,
    )


# Create enhanced text splitter instance
text_splitter = create_enhanced_text_splitter()


def split_documents_with_validation(
    docs: List[Document],
) -> Tuple[List[Document], Dict[str, Any]]:
    """Split documents into chunks with validation and stats."""
    start_time = time.time()
    logger.log_processing_start("document_splitting", {"input_documents": len(docs)})

    chunks = []
    stats = {
        "input_documents": len(docs),
        "output_chunks": 0,
        "failed_splits": 0,
        "empty_chunks_removed": 0,
        "average_chunk_size": 0,
        "processing_errors": [],
    }

    for i, doc in enumerate(docs):
        try:
            doc_chunks = text_splitter.split_documents([doc])

            # Filter out empty or very small chunks
            valid_chunks = []
            for chunk in doc_chunks:
                if chunk.page_content and len(chunk.page_content.strip()) >= 20:
                    valid_chunks.append(chunk)
                else:
                    stats["empty_chunks_removed"] += 1

            chunks.extend(valid_chunks)

        except Exception as e:
            stats["failed_splits"] += 1
            error_info = {
                "document_index": i,
                "error": str(e),
                "error_type": type(e).__name__,
            }
            stats["processing_errors"].append(error_info)

            logger.logger.warning(f"Failed to split document {i}: {e}")
            continue

    # Calculate stats
    stats["output_chunks"] = len(chunks)
    if chunks:
        stats["average_chunk_size"] = sum(
            len(chunk.page_content) for chunk in chunks
        ) / len(chunks)

    processing_duration = time.time() - start_time
    logger.log_processing_end("document_splitting", processing_duration, details=stats)

    return chunks, stats
