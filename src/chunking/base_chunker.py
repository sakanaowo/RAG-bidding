"""
Base chunking infrastructure for all document types.

Provides:
- BaseLegalChunker: Abstract base class with common utilities
- UniversalChunk: Unified chunk representation
- Common utilities: overlap splitting, context preservation, validation
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime

from src.preprocessing.base.models import ProcessedDocument


@dataclass
class UniversalChunk:
    """
    Universal chunk representation for ALL document types.

    This is the intermediate format before converting to UnifiedLegalChunk.
    Provides flexibility for different chunking strategies while maintaining
    consistency for embedding.
    """

    # Core content
    content: str
    chunk_id: str

    # Document context
    document_id: str
    document_type: str  # law, decree, circular, decision, bidding, report, exam

    # Hierarchy (optional - only for hierarchical docs)
    hierarchy: Optional[List[str]] = None  # ["Chương I", "Điều 15", "Khoản 1"]
    level: Optional[str] = None  # "dieu", "khoan", "section", "question"

    # Semantic context (for all types)
    parent_context: Optional[str] = None  # Title of parent section
    section_title: Optional[str] = None  # Current section/Điều title

    # Metadata
    char_count: int = 0
    chunk_index: int = 0  # Position in document
    total_chunks: int = 0

    # Quality markers
    is_complete_unit: bool = True  # False if split across semantic boundary
    has_table: bool = False
    has_list: bool = False

    # Additional metadata (flexible)
    extra_metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Auto-calculate char_count if not provided"""
        if self.char_count == 0:
            self.char_count = len(self.content)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for easy JSON serialization"""
        return {
            "content": self.content,
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "document_type": self.document_type,
            "hierarchy": self.hierarchy,
            "level": self.level,
            "parent_context": self.parent_context,
            "section_title": self.section_title,
            "char_count": self.char_count,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "is_complete_unit": self.is_complete_unit,
            "has_table": self.has_table,
            "has_list": self.has_list,
            "extra_metadata": self.extra_metadata,
        }


class BaseLegalChunker(ABC):
    """
    Abstract base class for all chunking strategies.

    Enforces:
    - Size consistency (300-1,500 chars, target 800)
    - Semantic boundary preservation
    - Context preservation
    - Unified chunk format

    Subclasses implement:
    - HierarchicalChunker: For legal docs (Điều-based)
    - SemanticChunker: For bidding/report/exam (section-based)
    """

    # Global constraints (from CHUNKING_EMBEDDING_IMPACT.md)
    MIN_CHUNK_SIZE = 300  # Below this = too short, loses context
    MAX_CHUNK_SIZE = 1500  # Above this = too long, adds noise
    TARGET_SIZE = 800  # Optimal for retrieval (700-900 range)

    # Overlap for context continuity
    DEFAULT_OVERLAP = 100  # Characters to overlap between chunks

    def __init__(
        self,
        min_size: int = MIN_CHUNK_SIZE,
        max_size: int = MAX_CHUNK_SIZE,
        target_size: int = TARGET_SIZE,
        overlap: int = DEFAULT_OVERLAP,
        preserve_context: bool = True,
    ):
        """
        Args:
            min_size: Minimum chunk size (chars)
            max_size: Maximum chunk size (chars)
            target_size: Target chunk size (chars)
            overlap: Overlap between consecutive chunks
            preserve_context: Add parent context to chunks
        """
        self.min_size = min_size
        self.max_size = max_size
        self.target_size = target_size
        self.overlap = overlap
        self.preserve_context = preserve_context

        # Statistics tracking
        self.stats = {
            "total_chunks": 0,
            "too_short": 0,
            "too_long": 0,
            "in_range": 0,
            "avg_size": 0,
            "total_chars": 0,
        }

    @abstractmethod
    def chunk(self, document: ProcessedDocument) -> List[UniversalChunk]:
        """
        Main chunking method to be implemented by subclasses.

        Args:
            document: ProcessedDocument from loader pipeline

        Returns:
            List of UniversalChunk objects

        Raises:
            ValueError: If document type not supported
        """
        pass

    def chunk_batch(self, documents: List[ProcessedDocument]) -> List[UniversalChunk]:
        """
        Chunk multiple documents in batch.

        Args:
            documents: List of ProcessedDocuments

        Returns:
            Flattened list of all chunks
        """
        all_chunks = []
        for doc in documents:
            chunks = self.chunk(doc)
            all_chunks.extend(chunks)

        return all_chunks

    def get_statistics(self) -> Dict[str, Any]:
        """Get chunking statistics"""
        if self.stats["total_chunks"] > 0:
            self.stats["avg_size"] = (
                self.stats["total_chars"] / self.stats["total_chunks"]
            )
        return self.stats.copy()

    def reset_statistics(self):
        """Reset statistics counters"""
        self.stats = {
            "total_chunks": 0,
            "too_short": 0,
            "too_long": 0,
            "in_range": 0,
            "avg_size": 0,
            "total_chars": 0,
        }

    # ============================================================
    # COMMON UTILITIES (reusable across all chunkers)
    # ============================================================

    def _validate_chunk(self, chunk: UniversalChunk) -> bool:
        """
        Validate chunk meets requirements.

        Checks:
        1. Size in acceptable range (MIN-MAX)
        2. Ends at semantic boundary (sentence/paragraph)
        3. Has non-empty content

        Args:
            chunk: UniversalChunk to validate

        Returns:
            True if valid, False otherwise
        """
        size = chunk.char_count

        # 1. Size check
        if size < self.min_size:
            self.stats["too_short"] += 1
            return False

        if size > self.max_size:
            self.stats["too_long"] += 1
            return False

        # 2. Content check
        if not chunk.content.strip():
            return False

        # 3. Semantic boundary check (optional - for logging only)
        content = chunk.content.rstrip()
        if not self._ends_at_boundary(content):
            # Still valid, but mark as incomplete unit
            chunk.is_complete_unit = False

        # Update stats
        self.stats["in_range"] += 1
        self.stats["total_chars"] += size

        return True

    def _ends_at_boundary(self, text: str) -> bool:
        """
        Check if text ends at a semantic boundary.

        Boundaries:
        - Sentence: . ! ? ; :
        - List item: ending with number/letter
        - Paragraph: double newline

        Args:
            text: Text to check

        Returns:
            True if ends at boundary
        """
        text = text.rstrip()

        if not text:
            return False

        # Sentence endings
        if text[-1] in ".!?;:":
            return True

        # List item endings (e.g., "1.", "a)", "- Item")
        if re.search(r"[\d\w]\)$|[\d\w]\.$", text):
            return True

        # Paragraph ending (double newline before strip)
        if text.endswith("\n\n"):
            return True

        return False

    def _split_with_overlap(
        self,
        text: str,
        max_size: int,
        overlap: int = 0,
    ) -> List[str]:
        """
        Split long text into chunks with overlap.

        Reused from chunk_strategy.py with improvements:
        - Prefer splitting at sentence boundaries
        - Maintain overlap for context continuity
        - Avoid orphan words

        Args:
            text: Text to split
            max_size: Maximum chunk size
            overlap: Characters to overlap

        Returns:
            List of text chunks
        """
        if len(text) <= max_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            # Calculate end position
            end = start + max_size

            if end >= len(text):
                # Last chunk
                chunks.append(text[start:])
                break

            # Try to find sentence boundary near end
            chunk_text = text[start:end]

            # Look for last sentence ending
            last_period = max(
                chunk_text.rfind(". "),
                chunk_text.rfind(".\n"),
                chunk_text.rfind("! "),
                chunk_text.rfind("? "),
            )

            if last_period > max_size * 0.5:  # At least 50% of max_size
                # Split at sentence boundary
                end = start + last_period + 1
            else:
                # No good boundary, try word boundary
                last_space = chunk_text.rfind(" ")
                if last_space > max_size * 0.3:  # At least 30% of max_size
                    end = start + last_space

            chunks.append(text[start:end])

            # Move start with overlap
            start = end - overlap

            # Ensure we make progress
            if start <= chunks[-1][:10]:  # Stuck in loop
                start = end

        return chunks

    def _add_parent_context(
        self,
        chunk_content: str,
        parent_title: Optional[str] = None,
        section_title: Optional[str] = None,
    ) -> str:
        """
        Add parent context to chunk for better retrieval.

        Format:
        ```
        [Parent: {parent_title}]
        [Section: {section_title}]

        {chunk_content}
        ```

        Args:
            chunk_content: Original chunk content
            parent_title: Title of parent section (e.g., "CHƯƠNG I - ...")
            section_title: Title of current section (e.g., "Điều 15 - ...")

        Returns:
            Chunk with context prepended
        """
        if not self.preserve_context:
            return chunk_content

        context_parts = []

        if parent_title:
            context_parts.append(f"[Parent: {parent_title}]")

        if section_title:
            context_parts.append(f"[Section: {section_title}]")

        if context_parts:
            context_header = "\n".join(context_parts) + "\n\n"
            return context_header + chunk_content

        return chunk_content

    def _generate_chunk_id(
        self,
        document_id: str,
        chunk_index: int,
        level: Optional[str] = None,
    ) -> str:
        """
        Generate unique chunk ID.

        Format: {document_id}_{level}_{index:04d}
        Example: "law_43_2013_dieu_0001"

        Args:
            document_id: Base document ID
            chunk_index: Sequential index
            level: Optional level (dieu, khoan, section)

        Returns:
            Unique chunk ID
        """
        level_part = f"{level}_" if level else ""
        return f"{document_id}_{level_part}{chunk_index:04d}"

    def _detect_special_content(self, text: str) -> Dict[str, bool]:
        """
        Detect special content types in text.

        Detects:
        - Tables (markdown or text-based)
        - Lists (numbered or bulleted)
        - Code blocks

        Args:
            text: Text to analyze

        Returns:
            Dict with boolean flags
        """
        return {
            "has_table": self._has_table(text),
            "has_list": self._has_list(text),
            "has_code": self._has_code(text),
        }

    def _has_table(self, text: str) -> bool:
        """Check if text contains a table"""
        # Markdown table
        if re.search(r"\|.*\|.*\|", text):
            return True

        # Text table (multiple aligned columns)
        lines = text.split("\n")
        tabular_lines = [
            line for line in lines if line.count("  ") >= 2 or line.count("\t") >= 1
        ]

        return len(tabular_lines) >= 3  # At least 3 rows

    def _has_list(self, text: str) -> bool:
        """Check if text contains a list"""
        # Numbered list
        if re.search(r"^\d+\.\s+", text, re.MULTILINE):
            return True

        # Bulleted list
        if re.search(r"^[-*•]\s+", text, re.MULTILINE):
            return True

        # Lettered list
        if re.search(r"^[a-z]\)\s+", text, re.MULTILINE):
            return True

        return False

    def _has_code(self, text: str) -> bool:
        """Check if text contains code blocks"""
        # Markdown code fence
        if "```" in text:
            return True

        # Indented code (4+ spaces at line start)
        if re.search(r"^    \S", text, re.MULTILINE):
            return True

        return False

    def _clean_text(self, text: str) -> str:
        """
        Clean text for chunking.

        Operations:
        - Normalize whitespace
        - Remove excessive newlines
        - Trim leading/trailing space

        Args:
            text: Text to clean

        Returns:
            Cleaned text
        """
        # Normalize newlines
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Remove excessive blank lines (max 2 consecutive)
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Normalize spaces (but preserve intentional indentation)
        lines = text.split("\n")
        cleaned_lines = []
        for line in lines:
            # Keep leading spaces for indentation
            leading_spaces = len(line) - len(line.lstrip())
            content = " ".join(line.split())  # Normalize internal spaces
            cleaned_lines.append(" " * leading_spaces + content)

        text = "\n".join(cleaned_lines)

        # Trim
        return text.strip()

    def _update_statistics(self, chunks: List[UniversalChunk]):
        """Update statistics after chunking"""
        self.stats["total_chunks"] += len(chunks)

        for chunk in chunks:
            size = chunk.char_count
            self.stats["total_chars"] += size

            if size < self.min_size:
                self.stats["too_short"] += 1
            elif size > self.max_size:
                self.stats["too_long"] += 1
            else:
                self.stats["in_range"] += 1
