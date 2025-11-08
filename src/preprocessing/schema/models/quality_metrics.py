"""
Quality Metrics Models
Section 3.6 from DEEP_ANALYSIS_REPORT.md
"""

from typing import Optional, List
from pydantic import BaseModel, Field

from ..enums import QualityLevel


class QualityMetrics(BaseModel):
    """
    Quality assessment metrics for processed chunks.
    Used for validation and confidence scoring.
    """

    # Overall quality
    overall_quality: QualityLevel = Field(
        default=QualityLevel.MEDIUM,
        description="Overall quality assessment (high/medium/low/failed)",
    )

    confidence_score: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Overall confidence score (0.0-1.0)"
    )

    # Completeness checks
    has_required_metadata: bool = Field(
        default=False, description="Whether all required metadata fields are present"
    )

    metadata_completeness: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Percentage of metadata fields populated (0.0-1.0)",
    )

    # Content quality
    content_readability_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Text readability/clarity score"
    )

    has_extraction_errors: bool = Field(
        default=False, description="Whether extraction errors were detected"
    )

    extraction_confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Confidence in text extraction quality"
    )

    # Validation
    validation_passed: bool = Field(
        default=False, description="Whether this chunk passed all validation checks"
    )

    validation_errors: List[str] = Field(
        default_factory=list, description="List of validation error messages"
    )

    validation_warnings: List[str] = Field(
        default_factory=list, description="List of validation warning messages"
    )

    # Consistency
    hierarchy_valid: bool = Field(
        default=True, description="Whether hierarchy structure is valid"
    )

    references_resolved: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Percentage of references successfully resolved",
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "overall_quality": "high",
                    "confidence_score": 0.92,
                    "has_required_metadata": True,
                    "metadata_completeness": 0.95,
                    "content_readability_score": 0.88,
                    "has_extraction_errors": False,
                    "extraction_confidence": 0.95,
                    "validation_passed": True,
                    "validation_errors": [],
                    "hierarchy_valid": True,
                    "references_resolved": 0.85,
                }
            ]
        }
