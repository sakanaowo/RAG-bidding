"""
Processing Metadata Models
Section 3.5 from DEEP_ANALYSIS_REPORT.md
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from ..enums import ProcessingStage


class ProcessingMetadata(BaseModel):
    """
    Metadata about the preprocessing pipeline execution.
    Tracks processing history and technical details.
    """

    # Processing identification
    processing_id: str = Field(..., description="Unique ID for this processing run")

    pipeline_version: str = Field(
        default="2.0.0", description="Version of preprocessing pipeline used"
    )

    # Timestamps
    processed_at: datetime = Field(
        default_factory=datetime.now, description="When this document was processed"
    )

    processing_duration_ms: Optional[int] = Field(
        None, ge=0, description="Processing time in milliseconds"
    )

    # Stage tracking
    current_stage: ProcessingStage = Field(
        default=ProcessingStage.INGESTION, description="Current pipeline stage"
    )

    completed_stages: List[ProcessingStage] = Field(
        default_factory=list, description="List of completed pipeline stages"
    )

    # Technical details
    extractor_used: str = Field(
        default="unknown",
        description="Extraction tool/method used (docx, pdf, excel, etc.)",
    )

    chunking_strategy: str = Field(
        default="hierarchical",
        description="Chunking strategy applied (hierarchical, semantic, hybrid)",
    )

    embedding_model: Optional[str] = Field(
        None, description="Embedding model used (if any)"
    )

    # Processing context
    config_snapshot: Dict[str, Any] = Field(
        default_factory=dict, description="Snapshot of pipeline configuration used"
    )

    errors_encountered: List[str] = Field(
        default_factory=list, description="List of errors encountered during processing"
    )

    warnings: List[str] = Field(
        default_factory=list, description="List of warnings during processing"
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "processing_id": "proc_20241031_abc123",
                    "pipeline_version": "2.0.0",
                    "processed_at": "2024-10-31T10:30:00",
                    "processing_duration_ms": 2500,
                    "current_stage": "output",
                    "completed_stages": [
                        "ingestion",
                        "extraction",
                        "validation",
                        "chunking",
                        "enrichment",
                        "quality_check",
                    ],
                    "extractor_used": "docx",
                    "chunking_strategy": "hierarchical",
                    "embedding_model": "bge-m3",
                }
            ]
        }
