"""
Base Legal Document Pipeline
Template Method Pattern with 7 Processing Stages
Based on PREPROCESSING_ARCHITECTURE.md
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from ..schema import (
    UnifiedLegalChunk,
    DocumentInfo,
    LegalMetadata,
    ContentStructure,
    ProcessingMetadata,
    QualityMetrics,
    ProcessingStage,
    DocType,
)


class PipelineConfig:
    """Configuration for pipeline execution"""

    def __init__(
        self,
        enable_validation: bool = True,
        enable_enrichment: bool = True,
        enable_quality_check: bool = True,
        chunking_strategy: str = "hierarchical",
        max_chunk_size: int = 1000,
        min_chunk_size: int = 100,
    ):
        self.enable_validation = enable_validation
        self.enable_enrichment = enable_enrichment
        self.enable_quality_check = enable_quality_check
        self.chunking_strategy = chunking_strategy
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size


class PipelineResult:
    """Result of pipeline execution"""

    def __init__(
        self,
        success: bool,
        chunks: List[UnifiedLegalChunk],
        metadata: Dict[str, Any],
        errors: List[str] = None,
        warnings: List[str] = None,
    ):
        self.success = success
        self.chunks = chunks
        self.metadata = metadata
        self.errors = errors or []
        self.warnings = warnings or []


class BaseLegalPipeline(ABC):
    """
    Abstract base class for all legal document preprocessing pipelines.

    Implements Template Method Pattern with 7 stages:
    1. Ingestion - Load file from disk
    2. Extraction - Extract text and structure
    3. Validation - Validate extracted data
    4. Chunking - Split into logical chunks
    5. Enrichment - Add semantic metadata
    6. Quality Check - Assess quality
    7. Output - Format and save

    Each document-specific pipeline (Law, Decree, etc.) extends this
    and implements the abstract methods.
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self.processing_id = (
            f"proc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        )
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.start_time: Optional[datetime] = None

    # ============================================================
    # TEMPLATE METHOD - Main Pipeline Flow
    # ============================================================

    def process(self, file_path: Path) -> PipelineResult:
        """
        Main template method - orchestrates the 7-stage pipeline.

        This is the public API. Subclasses should NOT override this.
        Instead, implement the abstract methods for each stage.
        """
        self.start_time = datetime.now()
        self.errors = []
        self.warnings = []

        try:
            # Stage 1: Ingestion
            raw_data = self._execute_stage(
                ProcessingStage.INGESTION, lambda: self.ingest(file_path)
            )

            # Stage 2: Extraction
            document_info, raw_content = self._execute_stage(
                ProcessingStage.EXTRACTION, lambda: self.extract(raw_data)
            )

            # Stage 3: Validation (optional)
            if self.config.enable_validation:
                validated_content = self._execute_stage(
                    ProcessingStage.VALIDATION,
                    lambda: self.validate(document_info, raw_content),
                )
            else:
                validated_content = raw_content

            # Stage 4: Chunking
            chunks = self._execute_stage(
                ProcessingStage.CHUNKING,
                lambda: self.chunk(document_info, validated_content),
            )

            # Stage 5: Enrichment (optional)
            if self.config.enable_enrichment:
                enriched_chunks = self._execute_stage(
                    ProcessingStage.ENRICHMENT, lambda: self.enrich(chunks)
                )
            else:
                enriched_chunks = chunks

            # Stage 6: Quality Check (optional)
            if self.config.enable_quality_check:
                quality_checked_chunks = self._execute_stage(
                    ProcessingStage.QUALITY_CHECK,
                    lambda: self.assess_quality(enriched_chunks),
                )
            else:
                quality_checked_chunks = enriched_chunks

            # Stage 7: Output
            final_chunks = self._execute_stage(
                ProcessingStage.OUTPUT,
                lambda: self.format_output(quality_checked_chunks),
            )

            # Calculate processing duration
            duration_ms = int((datetime.now() - self.start_time).total_seconds() * 1000)

            return PipelineResult(
                success=True,
                chunks=final_chunks,
                metadata={
                    "processing_id": self.processing_id,
                    "duration_ms": duration_ms,
                    "num_chunks": len(final_chunks),
                    "source_file": str(file_path),
                },
                errors=self.errors,
                warnings=self.warnings,
            )

        except Exception as e:
            self.errors.append(f"Pipeline failed: {str(e)}")
            return PipelineResult(
                success=False,
                chunks=[],
                metadata={"processing_id": self.processing_id},
                errors=self.errors,
                warnings=self.warnings,
            )

    def _execute_stage(self, stage: ProcessingStage, func):
        """Execute a pipeline stage with error handling"""
        try:
            return func()
        except Exception as e:
            error_msg = f"Stage {stage.value} failed: {str(e)}"
            self.errors.append(error_msg)
            raise RuntimeError(error_msg) from e

    # ============================================================
    # ABSTRACT METHODS - Must be implemented by subclasses
    # ============================================================

    @abstractmethod
    def ingest(self, file_path: Path) -> Any:
        """
        Stage 1: Load raw file from disk.

        Returns:
            Raw data (bytes, file handle, etc.)
        """
        pass

    @abstractmethod
    def extract(self, raw_data: Any) -> tuple[DocumentInfo, Any]:
        """
        Stage 2: Extract document metadata and content.

        Args:
            raw_data: Output from ingest()

        Returns:
            (DocumentInfo, raw_content)
        """
        pass

    @abstractmethod
    def chunk(
        self, document_info: DocumentInfo, content: Any
    ) -> List[UnifiedLegalChunk]:
        """
        Stage 4: Split content into logical chunks.

        Args:
            document_info: Extracted document metadata
            content: Validated content

        Returns:
            List of UnifiedLegalChunk objects
        """
        pass

    # ============================================================
    # OPTIONAL METHODS - Default implementations provided
    # ============================================================

    def validate(self, document_info: DocumentInfo, content: Any) -> Any:
        """
        Stage 3: Validate extracted data.

        Default implementation: No-op (returns content as-is).
        Override to add validation logic.
        """
        return content

    def enrich(self, chunks: List[UnifiedLegalChunk]) -> List[UnifiedLegalChunk]:
        """
        Stage 5: Add semantic enrichment (NER, keywords, etc.).

        Default implementation: No-op.
        Override to add enrichment logic.
        """
        return chunks

    def assess_quality(
        self, chunks: List[UnifiedLegalChunk]
    ) -> List[UnifiedLegalChunk]:
        """
        Stage 6: Assess chunk quality and set metrics.

        Default implementation: Basic quality checks.
        Override for advanced quality analysis.
        """
        for chunk in chunks:
            # Basic completeness check
            has_required = all(
                [
                    chunk.document_info.doc_id,
                    chunk.document_info.title,
                    chunk.content_structure.content_text,
                ]
            )

            chunk.quality_metrics.has_required_metadata = has_required
            chunk.quality_metrics.validation_passed = has_required

        return chunks

    def format_output(self, chunks: List[UnifiedLegalChunk]) -> List[UnifiedLegalChunk]:
        """
        Stage 7: Format output (add processing metadata, etc.).

        Default implementation: Adds processing metadata.
        """
        for chunk in chunks:
            chunk.processing_metadata.processing_id = self.processing_id
            chunk.processing_metadata.current_stage = ProcessingStage.OUTPUT
            chunk.processing_metadata.chunking_strategy = self.config.chunking_strategy

        return chunks

    # ============================================================
    # HELPER METHODS
    # ============================================================

    @abstractmethod
    def get_doc_type(self) -> DocType:
        """Return the document type this pipeline handles"""
        pass

    def add_error(self, error: str):
        """Add an error message"""
        self.errors.append(error)

    def add_warning(self, warning: str):
        """Add a warning message"""
        self.warnings.append(warning)
