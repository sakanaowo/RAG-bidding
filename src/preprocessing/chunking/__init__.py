"""
Chunking Module for Vietnamese Legal Documents
Consolidated from src/chunking (Nov 2025)

Provides:
- BaseLegalChunker: Base class với utilities
- HierarchicalChunker: Chunking cho legal docs (Điều-based)
- SemanticChunker: Chunking cho bidding/report/exam
- BiddingHybridChunker: Hybrid strategy cho bidding
- ReportHybridChunker: Hybrid strategy cho reports
- ChunkFactory: Convert UniversalChunk → UnifiedLegalChunk
- create_chunker: Factory function tự động chọn chunker
"""

from .base_chunker import BaseLegalChunker, UniversalChunk
from .hierarchical_chunker import HierarchicalChunker
from .semantic_chunker import SemanticChunker
from .bidding_hybrid_chunker import BiddingHybridChunker
from .report_hybrid_chunker import ReportHybridChunker
from .chunk_factory import ChunkFactory, create_chunker

__all__ = [
    "BaseLegalChunker",
    "UniversalChunk",
    "HierarchicalChunker",
    "SemanticChunker",
    "BiddingHybridChunker",
    "ReportHybridChunker",
    "ChunkFactory",
    "create_chunker",
]

from src.preprocessing.chunking.base_chunker import BaseLegalChunker, UniversalChunk
from src.preprocessing.chunking.hierarchical_chunker import HierarchicalChunker
from src.preprocessing.chunking.semantic_chunker import SemanticChunker
from src.preprocessing.chunking.chunk_factory import ChunkFactory, create_chunker

__all__ = [
    "BaseLegalChunker",
    "UniversalChunk",
    "HierarchicalChunker",
    "SemanticChunker",
    "ChunkFactory",
    "create_chunker",
]
