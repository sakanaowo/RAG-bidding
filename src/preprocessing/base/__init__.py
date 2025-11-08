"""
Base classes cho document preprocessing system
"""

# V1 Base Classes (archived but kept for reference)
from .base_extractor import BaseExtractor
from .base_parser import BaseParser
from .base_cleaner import BaseCleaner
from .base_pipeline import BaseDocumentPipeline

# V2 Base Classes (new unified architecture)
from .legal_pipeline import BaseLegalPipeline, PipelineConfig, PipelineResult
from .models import ProcessedDocument

__all__ = [
    # V1 (deprecated, will be removed after migration)
    "BaseExtractor",
    "BaseParser",
    "BaseCleaner",
    "BaseDocumentPipeline",
    # V2 (use these for new pipelines)
    "ProcessedDocument",
    "BaseLegalPipeline",
    "PipelineConfig",
    "PipelineResult",
]
