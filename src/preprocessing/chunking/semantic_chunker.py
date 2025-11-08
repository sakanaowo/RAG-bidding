"""
Semantic Chunker for Non-Legal Documents
Strategy: Sliding window with semantic boundary detection

For: Bidding documents, Reports, Exam questions
Refactored from: archive/preprocessing_v1/bidding_preprocessing/chunkers/simple_chunker.py

Integrated with V2 Unified Schema
"""

from __future__ import annotations
import re
from typing import List, Dict, Optional
from dataclasses import dataclass

from ..schema import UnifiedLegalChunk, ContentStructure


class SemanticChunker:
    """
    Semantic chunking strategy for documents without strict legal hierarchy.

    Strategy:
    1. Split by paragraphs (natural semantic boundaries)
    2. Combine paragraphs into chunks up to max_chunk_size
    3. Add overlap between chunks for context continuity
    4. Detect section headers if present

    Use cases:
    - Bidding documents (HSYC, E-HSDT, etc.)
    - Reports and summaries
    - Exam questions and answers
    - General text documents

    Example:
        Input: Long bidding document
        Output: Chunks of ~1000-2000 chars with 200 char overlap
    """

    def __init__(
        self,
        chunk_size: int = 1500,
        min_chunk_size: int = 500,
        overlap_size: int = 200,
        detect_sections: bool = True,
    ):
        """
        Args:
            chunk_size: Target chunk size in characters
            min_chunk_size: Minimum chunk size (avoid too small chunks)
            overlap_size: Overlap between consecutive chunks
            detect_sections: Attempt to detect section headers
        """
        self.chunk_size = chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap_size = overlap_size
        self.detect_sections = detect_sections

        # Section header patterns (common in bidding docs)
        self.section_patterns = [
            re.compile(r"^PHẦN\s+[IVXLCDM0-9]+[:\.]?\s*(.+)$", re.IGNORECASE),
            re.compile(r"^CHƯƠNG\s+[IVXLCDM0-9]+[:\.]?\s*(.+)$", re.IGNORECASE),
            re.compile(r"^[A-Z][:\.]?\s+(.+)$"),  # Single letter sections
            re.compile(
                r"^(\d+)\.\s*([A-ZĐÀÁẢÃẠÂẦẤẨẪẬĂẰẮẲẴẶÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ].+)$"
            ),  # Numbered sections with title
        ]

    def chunk(
        self,
        text: str,
        doc_id: str,
        base_metadata: Dict,
    ) -> List[UnifiedLegalChunk]:
        """
        Main chunking method.

        Args:
            text: Full document text
            doc_id: Document ID
            base_metadata: Base metadata to include in all chunks

        Returns:
            List of UnifiedLegalChunk objects
        """
        if not text or not text.strip():
            return []

        # Step 1: Split into paragraphs
        paragraphs = self._split_paragraphs(text)

        # Step 2: Detect sections if enabled
        sections = self._detect_sections(paragraphs) if self.detect_sections else None

        # Step 3: Build chunks
        chunks = self._build_chunks(
            paragraphs=paragraphs,
            sections=sections,
            doc_id=doc_id,
            base_metadata=base_metadata,
        )

        return chunks

    def _split_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs"""
        # Split by double newlines (paragraph breaks)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        # If no double newlines, split by single newlines
        if len(paragraphs) <= 1:
            paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

        return paragraphs

    def _detect_sections(self, paragraphs: List[str]) -> Optional[Dict[int, str]]:
        """
        Detect section headers in paragraphs.

        Returns:
            Dict mapping paragraph index -> section title
        """
        sections = {}

        for idx, para in enumerate(paragraphs):
            # Check each pattern
            for pattern in self.section_patterns:
                match = pattern.match(para)
                if match:
                    # Extract section title
                    if len(match.groups()) >= 1:
                        sections[idx] = match.group(0).strip()
                    break

        return sections if sections else None

    def _build_chunks(
        self,
        paragraphs: List[str],
        sections: Optional[Dict[int, str]],
        doc_id: str,
        base_metadata: Dict,
    ) -> List[UnifiedLegalChunk]:
        """Build chunks from paragraphs with overlap"""
        chunks = []
        current_chunk_paras = []
        current_size = 0
        current_section = None
        chunk_index = 0

        for idx, para in enumerate(paragraphs):
            para_size = len(para)

            # Check if this is a section header
            if sections and idx in sections:
                # Save current chunk if any
                if current_chunk_paras and current_size >= self.min_chunk_size:
                    chunk = self._create_chunk(
                        paragraphs=current_chunk_paras,
                        doc_id=doc_id,
                        chunk_index=chunk_index,
                        section_title=current_section,
                        base_metadata=base_metadata,
                    )
                    chunks.append(chunk)
                    chunk_index += 1

                    # Start new chunk with overlap
                    current_chunk_paras = self._get_overlap_paragraphs(
                        current_chunk_paras
                    )
                    current_size = sum(len(p) for p in current_chunk_paras)
                else:
                    # Clear if too small
                    current_chunk_paras = []
                    current_size = 0

                # Update current section
                current_section = sections[idx]

            # Check if adding this paragraph would exceed chunk size
            if current_size + para_size > self.chunk_size and current_chunk_paras:
                # Only create chunk if it meets minimum size
                if current_size >= self.min_chunk_size:
                    chunk = self._create_chunk(
                        paragraphs=current_chunk_paras,
                        doc_id=doc_id,
                        chunk_index=chunk_index,
                        section_title=current_section,
                        base_metadata=base_metadata,
                    )
                    chunks.append(chunk)
                    chunk_index += 1

                    # Start new chunk with overlap
                    current_chunk_paras = self._get_overlap_paragraphs(
                        current_chunk_paras
                    )
                    current_size = sum(len(p) for p in current_chunk_paras)
                else:
                    # Too small, keep accumulating
                    pass

            # Add paragraph to current chunk
            current_chunk_paras.append(para)
            current_size += para_size

        # Add final chunk if any content remains
        if current_chunk_paras and current_size >= self.min_chunk_size:
            chunk = self._create_chunk(
                paragraphs=current_chunk_paras,
                doc_id=doc_id,
                chunk_index=chunk_index,
                section_title=current_section,
                base_metadata=base_metadata,
            )
            chunks.append(chunk)

        return chunks

    def _get_overlap_paragraphs(self, paragraphs: List[str]) -> List[str]:
        """Get overlap paragraphs from end of chunk"""
        if not paragraphs:
            return []

        overlap_paras = []
        overlap_size = 0

        # Take paragraphs from end until we reach overlap_size
        for para in reversed(paragraphs):
            if overlap_size + len(para) > self.overlap_size:
                break
            overlap_paras.insert(0, para)
            overlap_size += len(para)

        return overlap_paras

    def _create_chunk(
        self,
        paragraphs: List[str],
        doc_id: str,
        chunk_index: int,
        section_title: Optional[str],
        base_metadata: Dict,
    ) -> UnifiedLegalChunk:
        """Create UnifiedLegalChunk from paragraphs"""

        # Join paragraphs
        text = "\n\n".join(paragraphs)

        # Build ContentStructure
        content_structure = ContentStructure(
            hierarchy_path=[section_title] if section_title else [],
            level="paragraph",
            section_title=section_title,
            parent_sections=[],
        )

        # Create chunk
        chunk = UnifiedLegalChunk(
            chunk_id=f"{doc_id}_chunk_{chunk_index}",
            content=text,
            char_count=len(text),
            structure=content_structure,
        )

        # Copy base metadata fields
        for key, value in base_metadata.items():
            if hasattr(chunk, key):
                setattr(chunk, key, value)

        return chunk
