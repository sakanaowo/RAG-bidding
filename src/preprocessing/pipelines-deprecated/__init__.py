"""
Pipelines Module
Document-specific preprocessing pipelines
"""

from .law_pipeline import LawPipeline

__all__ = [
    "LawPipeline",
    # TODO: Add other pipelines
    # "DecreePipeline",
    # "CircularPipeline",
    # "DecisionPipeline",
    # "BiddingPipeline",
    # "ReportPipeline",
    # "ExamPipeline",
]
