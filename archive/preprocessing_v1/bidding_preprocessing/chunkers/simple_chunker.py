"""
Simple Text Chunker for Bidding Documents

Alternative chunker when OptimalLegalChunker doesn't work with bidding documents.
"""

import re
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class SimpleChunk:
    """Simple chunk representation"""

    content: str
    metadata: Dict[str, Any]
    chunk_id: str
    char_count: int


class SimpleBiddingChunker:
    """
    Simple text chunker for bidding documents
    Fallback when legal chunker doesn't work
    """

    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        """
        Initialize simple chunker

        Args:
            chunk_size: Target chunk size in characters
            overlap: Overlap between chunks
        """
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_text(
        self, text: str, metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Chunk text into simple overlapping chunks

        Args:
            text: Text to chunk
            metadata: Optional metadata to add to chunks

        Returns:
            List of chunk dictionaries
        """
        if not text or not text.strip():
            return []

        if metadata is None:
            metadata = {}

        chunks = []

        # Split by paragraphs first for better boundaries
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        current_chunk = ""
        chunk_id = 0

        for paragraph in paragraphs:
            # If adding this paragraph would exceed chunk size
            if (
                len(current_chunk) + len(paragraph) + 2 > self.chunk_size
                and current_chunk
            ):
                # Save current chunk
                chunk = self._create_chunk(current_chunk, chunk_id, metadata)
                chunks.append(chunk)
                chunk_id += 1

                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk)
                current_chunk = overlap_text + paragraph
            else:
                # Add to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph

        # Add final chunk if any content remains
        if current_chunk.strip():
            chunk = self._create_chunk(current_chunk, chunk_id, metadata)
            chunks.append(chunk)

        return chunks

    def _create_chunk(
        self, content: str, chunk_id: int, base_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create chunk dictionary"""
        chunk_metadata = base_metadata.copy()
        chunk_metadata.update(
            {
                "chunk_index": chunk_id,
                "char_count": len(content),
                "word_count": len(content.split()),
                "paragraph_count": len([p for p in content.split("\n\n") if p.strip()]),
            }
        )

        return {
            "content": content.strip(),
            "metadata": chunk_metadata,
            "chunk_id": f"chunk_{chunk_id:03d}",
            "char_count": len(content),
            "level": "paragraph",
            "hierarchy": [],
            "parent_id": None,
        }

    def _get_overlap_text(self, text: str) -> str:
        """Get overlap text from end of current chunk"""
        if len(text) <= self.overlap:
            return text

        # Try to find a good break point (sentence or paragraph end)
        overlap_start = len(text) - self.overlap

        # Look for sentence breaks
        sentence_breaks = [".", "!", "?", "\n"]
        best_break = overlap_start

        for i in range(overlap_start, len(text)):
            if text[i] in sentence_breaks:
                best_break = i + 1
                break

        return text[best_break:] + " "

    def optimal_chunk_document(self, document: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Interface compatible with OptimalLegalChunker

        Args:
            document: Document dictionary with 'content' key

        Returns:
            List of chunk dictionaries
        """
        content = document.get("content", "")
        metadata = document.get("metadata", {})

        return self.chunk_text(content, metadata)
