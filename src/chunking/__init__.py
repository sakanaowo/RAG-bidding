"""
Chunking module for RAG-bidding.

Provides:
- BaseLegalChunker: Abstract base class
- HierarchicalChunker: For legal documents (Điều-based)
- SemanticChunker: For bidding/report/exam (section-based)
- ChunkFactory: Convert UniversalChunk → UnifiedLegalChunk
- create_chunker: Factory function

Usage:
    from src.chunking import create_chunker, ChunkFactory

    # Create chunker
    chunker = create_chunker("law")

    # Chunk document
    universal_chunks = chunker.chunk(document)

    # Convert to UnifiedLegalChunk
    factory = ChunkFactory()
    unified_chunks = factory.convert_batch(universal_chunks, document)
"""

from src.chunking.base_chunker import BaseLegalChunker, UniversalChunk
from src.chunking.hierarchical_chunker import HierarchicalChunker
from src.chunking.semantic_chunker import SemanticChunker
from src.chunking.chunk_factory import ChunkFactory, create_chunker

__all__ = [
    "BaseLegalChunker",
    "UniversalChunk",
    "HierarchicalChunker",
    "SemanticChunker",
    "ChunkFactory",
    "create_chunker",
]
