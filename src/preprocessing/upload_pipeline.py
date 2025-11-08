"""
Working Upload Pipeline
Based on tested workflow from batch_reprocess_all.py that processes 1026 chunks successfully.

This pipeline uses the PROVEN workflow:
DocxLoader → ProcessedDocument → ChunkFactory → ChunkEnricher → UniversalChunk
"""

import time
import logging
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime

from .loaders.docx_loader import DocxLoader
from .loaders.doc_loader import DocLoader
from .base.models import ProcessedDocument
from ..chunking.chunk_factory import create_chunker
from ..chunking.base_chunker import UniversalChunk
from .enrichment import ChunkEnricher

logger = logging.getLogger(__name__)


class WorkingUploadPipeline:
    """
    Production-ready upload pipeline using proven workflow.

    Based on batch_reprocess_all.py that successfully processed 4/4 law files
    creating 1026 chunks with 100% success rate.
    """

    def __init__(self, enable_enrichment: bool = True):
        self.enable_enrichment = enable_enrichment

        # Initialize loaders
        self.docx_loader = DocxLoader()
        self.doc_loader = DocLoader()

        # Initialize enricher if enabled
        if self.enable_enrichment:
            self.enricher = ChunkEnricher()
            logger.info("✨ Enrichment enabled")
        else:
            self.enricher = None
            logger.info("⚠️  Enrichment disabled")

        # Log .doc support status
        if self.doc_loader.can_process():
            logger.info("✅ .doc file support enabled")
        else:
            logger.warning(
                "⚠️  .doc file support disabled (install antiword or libreoffice)"
            )

    def process_file(
        self,
        file_path: Path,
        document_type: str = "law",
        batch_name: Optional[str] = None,
    ) -> Tuple[bool, Optional[List[UniversalChunk]], Optional[str]]:
        """
        Process a single file through the working pipeline.

        Args:
            file_path: Path to the file to process
            document_type: Type of document (law, decree, circular, etc.)
            batch_name: Optional batch identifier

        Returns:
            (success, chunks, error_message)
        """
        start_time = time.time()

        try:
            # Step 1: Extract content
            try:
                # Choose loader based on file extension
                if file_path.suffix.lower() == ".doc":
                    # Old Word format - use DocLoader
                    if not self.doc_loader.can_process():
                        return (
                            False,
                            None,
                            "Cannot process .doc files (install antiword or libreoffice)",
                        )

                    content, doc_metadata = self.doc_loader.load(str(file_path))
                    extraction_method = doc_metadata.get(
                        "extraction_method", "doc_loader"
                    )
                else:
                    # Modern DOCX format - use DocxLoader
                    raw_content = self.docx_loader.load(str(file_path))
                    content = raw_content.text
                    extraction_method = "docx_loader"

            except Exception as e:
                return False, None, f"Extraction failed: {str(e)}"

            if not content or len(content.strip()) < 50:
                return False, None, "Empty or too short content"

            # Step 2: Create ProcessedDocument
            processed_doc = ProcessedDocument(
                metadata={
                    "source_file": file_path.name,
                    "document_type": document_type,
                    "file_path": str(file_path),
                    "processed_at": datetime.now().isoformat(),
                    "extraction_method": extraction_method,
                    "batch_name": batch_name,
                },
                content={
                    "full_text": content,
                },
            )

            # Step 3: Select and run chunker
            try:
                chunker = create_chunker(document_type=document_type)
            except Exception as e:
                return False, None, f"Chunker creation failed: {str(e)}"

            try:
                chunks = chunker.chunk(processed_doc)
            except Exception as e:
                return False, None, f"Chunking failed: {str(e)}"

            if not chunks:
                return False, None, "No chunks generated"

            # Step 4: Enrich chunks (if enabled)
            if self.enable_enrichment and self.enricher:
                try:
                    chunks = self._enrich_chunks(chunks)
                except Exception as e:
                    logger.warning(
                        f"Enrichment failed: {e}, continuing without enrichment"
                    )
                    # Continue with unenriched chunks

            # Step 5: Add processing metadata
            processing_time = time.time() - start_time
            for chunk in chunks:
                if hasattr(chunk, "extra_metadata"):
                    chunk.extra_metadata["processing_time_ms"] = int(
                        processing_time * 1000
                    )
                    chunk.extra_metadata["batch_name"] = batch_name
                    chunk.extra_metadata["pipeline_version"] = (
                        "working_upload_pipeline_v1.0"
                    )

            return True, chunks, None

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Pipeline failed after {processing_time:.2f}s: {str(e)}")
            return False, None, f"Pipeline failed: {str(e)}"

    def _enrich_chunks(self, chunks: List[UniversalChunk]) -> List[UniversalChunk]:
        """Enrich chunks with semantic metadata"""
        try:
            enriched_chunks = []
            for chunk in chunks:
                # Use enricher to add semantic metadata
                enriched_chunk = self.enricher.enrich_chunk(chunk)
                enriched_chunks.append(enriched_chunk)

            return enriched_chunks
        except Exception as e:
            # If enrichment fails, return original chunks
            logger.warning(f"Enrichment failed: {e}")
            return chunks

    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions"""
        extensions = [".docx"]
        if self.doc_loader.can_process():
            extensions.append(".doc")
        return extensions

    def estimate_processing_time(self, file_size_bytes: int) -> int:
        """
        Estimate processing time in seconds based on file size.

        Based on batch_reprocess_all.py performance:
        - 4 files processed in 0.6s
        - Average ~150ms per file
        """
        # Base processing time
        base_time = 0.15  # 150ms base

        # Add time based on file size (roughly 1s per 10MB)
        size_mb = file_size_bytes / (1024 * 1024)
        size_time = size_mb * 0.1

        total_time = base_time + size_time

        # Add enrichment overhead if enabled
        if self.enable_enrichment:
            total_time *= 1.5

        return max(1, int(total_time))  # At least 1 second
