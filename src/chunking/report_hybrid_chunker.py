"""
Report Hybrid Chunker - Optimized for Bidding Report Documents

Strategy:
- Chunk by PHẦN (Part) and sections
- Preserve tables completely
- Merge small chunks recursively to reach min_size
- Target: 80%+ chunks in optimal range (300-1500 chars)

Supports:
- Báo cáo đánh giá (BC_DANH_GIA)
- Báo cáo kết quả (BC_KET_QUA)
- Mẫu báo cáo (Mau bao cao)
"""

import re
from typing import List, Dict, Optional, Tuple, Union
from datetime import datetime

from src.chunking.base_chunker import BaseLegalChunker, UniversalChunk
from src.preprocessing.base.models import ProcessedDocument


class ReportHybridChunker(BaseLegalChunker):
    """
    Hybrid chunker for bidding reports.

    Combines:
    1. Structural chunking (PHẦN, sections)
    2. Table preservation
    3. Recursive merging (BiddingHybridChunker strategy)

    Key improvements over SemanticChunker:
    - min_size enforced via recursive merge
    - Better table handling
    - Optimal chunk size distribution
    """

    PATTERNS = {
        "phan": r"^(PHẦN|Phần)\s+([IVXLCDM]+|[A-Z])[:\.]?\s*(.+)$",
        "section": r"^(\d+)\.\s+(.+)$",  # 1., 2., 3.
        "subsection": r"^(\d+\.\d+)\.\s+(.+)$",  # 1.1., 2.1.
        "form": r"^(Biểu mẫu|Mẫu số|Phụ lục)\s+(\d+[A-Z]?)[:\.]?\s*(.*)$",
        "table_start": r"^(Bảng|Table)\s+(\d+)",
    }

    def __init__(
        self,
        min_size: int = 300,
        max_size: int = 1500,
        target_size: int = 800,
        overlap: int = 100,
        preserve_context: bool = True,
        preserve_tables: bool = True,
    ):
        super().__init__(min_size, max_size, target_size, overlap, preserve_context)
        self.preserve_tables = preserve_tables

    def chunk(self, document: ProcessedDocument) -> List[UniversalChunk]:
        """
        Chunk report document.

        Args:
            document: ProcessedDocument from DocxLoader

        Returns:
            List of UniversalChunk objects
        """
        # Get full text
        full_text = document.content.get("full_text", "")
        if not full_text:
            return []

        # Clean text
        full_text = self._clean_text(full_text)

        # Parse structure
        structure = self._parse_structure(full_text)

        # Generate document ID
        doc_id = self._generate_document_id(document)

        # Build initial chunks
        chunks = self._build_chunks_from_structure(
            structure=structure,
            document=document,
            doc_id=doc_id,
        )

        # Merge small chunks recursively (KEY OPTIMIZATION!)
        chunks = self._merge_small_chunks_recursive(chunks, document, doc_id)

        # Update chunk indices and total
        for idx, chunk in enumerate(chunks):
            chunk.chunk_index = idx
            chunk.total_chunks = len(chunks)

        # Update statistics
        self._update_statistics(chunks)

        return chunks

    def _parse_structure(self, text: str) -> List[Dict]:
        """
        Parse report structure.

        Identifies:
        - PHẦN (Part)
        - Section (1., 2., 3.)
        - Subsection (1.1, 1.2)
        - Forms/Tables

        Args:
            text: Full document text

        Returns:
            List of structured elements
        """
        lines = text.split("\n")
        structure = []

        # Current hierarchy context
        current_phan = None
        current_section = None
        in_table = False

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if not line:
                i += 1
                continue

            # Check PHẦN
            phan_match = re.match(self.PATTERNS["phan"], line)
            if phan_match:
                current_phan = {
                    "type": "phan",
                    "number": phan_match.group(2),
                    "title": phan_match.group(3).strip(),
                    "full_title": line,
                }
                structure.append(current_phan)
                i += 1
                continue

            # Check Table
            table_match = re.match(self.PATTERNS["table_start"], line)
            if table_match:
                # Extract complete table
                table_content, next_i = self._extract_table(lines, i)

                structure.append(
                    {
                        "type": "table",
                        "number": table_match.group(2),
                        "content": table_content,
                        "phan": current_phan["full_title"] if current_phan else None,
                    }
                )

                i = next_i
                continue

            # Check Section (1., 2., 3.)
            section_match = re.match(self.PATTERNS["section"], line)
            if section_match and not re.match(self.PATTERNS["subsection"], line):
                # Collect section content
                content_lines = [line]
                j = i + 1

                while j < len(lines):
                    next_line = lines[j].strip()

                    # Stop at next major element
                    if (
                        re.match(self.PATTERNS["phan"], next_line)
                        or re.match(self.PATTERNS["section"], next_line)
                        or re.match(self.PATTERNS["table_start"], next_line)
                    ):
                        break

                    content_lines.append(lines[j])
                    j += 1

                current_section = {
                    "type": "section",
                    "number": section_match.group(1),
                    "title": section_match.group(2).strip(),
                    "full_title": line,
                    "content": "\n".join(content_lines),
                    "phan": current_phan["full_title"] if current_phan else None,
                }

                structure.append(current_section)
                i = j
                continue

            i += 1

        return structure

    def _extract_table(self, lines: List[str], start_idx: int) -> Tuple[str, int]:
        """
        Extract complete table from lines.

        Args:
            lines: Document lines
            start_idx: Table start index

        Returns:
            (table_content, next_index)
        """
        table_lines = [lines[start_idx]]
        i = start_idx + 1

        # Heuristic: table ends when we see 2+ blank lines or next section
        blank_count = 0

        while i < len(lines):
            line = lines[i].strip()

            # Stop at next major element
            if re.match(self.PATTERNS["phan"], line) or re.match(
                self.PATTERNS["section"], line
            ):
                break

            if not line:
                blank_count += 1
                if blank_count >= 2:
                    break
            else:
                blank_count = 0
                table_lines.append(lines[i])

            i += 1

        return "\n".join(table_lines), i

    def _build_chunks_from_structure(
        self,
        structure: List[Dict],
        document: ProcessedDocument,
        doc_id: str,
    ) -> List[UniversalChunk]:
        """
        Build initial chunks from structure.

        Args:
            structure: Parsed structure
            document: Original ProcessedDocument
            doc_id: Document ID

        Returns:
            List of chunks (before merging)
        """
        chunks = []
        chunk_index = 0

        for element in structure:
            element_type = element["type"]

            if element_type == "phan":
                # PHẦN is just context, not a chunk
                continue

            elif element_type == "section":
                # Create chunk(s) from section
                section_chunks = self._create_chunk_from_section(
                    element, document, doc_id, chunk_index
                )

                # Handle both single chunk and list of chunks
                if isinstance(section_chunks, list):
                    chunks.extend(section_chunks)
                    chunk_index += len(section_chunks)
                else:
                    chunks.append(section_chunks)
                    chunk_index += 1

            elif element_type == "table":
                # Create chunk(s) from table
                table_chunks = self._create_chunk_from_table(
                    element, document, doc_id, chunk_index
                )

                # Handle both single chunk and list of chunks
                if isinstance(table_chunks, list):
                    chunks.extend(table_chunks)
                    chunk_index += len(table_chunks)
                else:
                    chunks.append(table_chunks)
                    chunk_index += 1

        return chunks

    def _create_chunk_from_section(
        self,
        section: Dict,
        document: ProcessedDocument,
        doc_id: str,
        chunk_index: int,
    ) -> Union[UniversalChunk, List[UniversalChunk]]:
        """Create chunk(s) from section element. Returns single chunk or list if split."""
        content = section["content"]

        # If section too large, split by paragraphs
        if len(content) > self.max_size:
            return self._split_large_section(section, document, doc_id, chunk_index)

        # Build hierarchy
        hierarchy = []
        if section.get("phan"):
            hierarchy.append(section["phan"])
        hierarchy.append(section["full_title"])

        # Parent context
        parent_context = section.get("phan")

        # Enhanced content with context
        enhanced_content = self._add_parent_context(
            chunk_content=content,
            parent_title=parent_context,
            section_title=section["full_title"],
        )

        # Chunk ID
        chunk_id = self._generate_chunk_id(
            document_id=doc_id,
            chunk_index=chunk_index,
            level="section",
        )

        # Detect special content
        special_flags = self._detect_special_content(content)

        return UniversalChunk(
            content=enhanced_content,
            chunk_id=chunk_id,
            document_id=doc_id,
            document_type=document.metadata.get("document_type", "report"),
            hierarchy=hierarchy,
            level="section",
            parent_context=parent_context,
            section_title=section["title"],
            char_count=len(enhanced_content),
            chunk_index=chunk_index,
            total_chunks=0,
            is_complete_unit=True,
            has_table=special_flags["has_table"],
            has_list=special_flags["has_list"],
            extra_metadata={
                "section_number": section["number"],
                "phan": section.get("phan"),
            },
        )

    def _split_large_section(
        self,
        section: Dict,
        document: ProcessedDocument,
        doc_id: str,
        chunk_index: int,
    ) -> List[UniversalChunk]:
        """
        Split large section into multiple chunks.

        Strategy: Use overlap splitting for large sections.
        """
        content = section["content"]

        # Split with overlap
        sub_texts = self._split_with_overlap(
            text=content,
            max_size=self.max_size,
            overlap=self.overlap,
        )

        chunks = []
        for idx, sub_text in enumerate(sub_texts):
            # Build hierarchy
            hierarchy = []
            if section.get("phan"):
                hierarchy.append(section["phan"])
            hierarchy.append(f"{section['full_title']} (phần {idx+1})")

            parent_context = section.get("phan")

            # Enhanced content
            enhanced_content = self._add_parent_context(
                chunk_content=sub_text,
                parent_title=parent_context,
                section_title=section["full_title"],
            )

            # Chunk ID
            chunk_id = self._generate_chunk_id(
                document_id=doc_id,
                chunk_index=chunk_index + idx,
                level="section_part",
            )

            # Detect special content
            special_flags = self._detect_special_content(sub_text)

            chunk = UniversalChunk(
                content=enhanced_content,
                chunk_id=chunk_id,
                document_id=doc_id,
                document_type=document.metadata.get("document_type", "report"),
                hierarchy=hierarchy,
                level="section_part",
                parent_context=parent_context,
                section_title=f"{section['title']} (phần {idx+1})",
                char_count=len(enhanced_content),
                chunk_index=chunk_index + idx,
                total_chunks=0,
                is_complete_unit=False,  # Split section
                has_table=special_flags["has_table"],
                has_list=special_flags["has_list"],
                extra_metadata={
                    "section_number": section["number"],
                    "phan": section.get("phan"),
                    "part_index": idx,
                },
            )
            chunks.append(chunk)

        return chunks

    def _create_chunk_from_table(
        self,
        table: Dict,
        document: ProcessedDocument,
        doc_id: str,
        chunk_index: int,
    ) -> Union[UniversalChunk, List[UniversalChunk]]:
        """Create chunk(s) from table element. Split if too large."""
        content = table["content"]

        # If table too large, split it
        if len(content) > self.max_size:
            return self._split_large_table(table, document, doc_id, chunk_index)

        # Build hierarchy
        hierarchy = []
        if table.get("phan"):
            hierarchy.append(table["phan"])
        hierarchy.append(f"Bảng {table['number']}")

        parent_context = table.get("phan")

        # Chunk ID
        chunk_id = self._generate_chunk_id(
            document_id=doc_id,
            chunk_index=chunk_index,
            level="table",
        )

        return UniversalChunk(
            content=content,
            chunk_id=chunk_id,
            document_id=doc_id,
            document_type=document.metadata.get("document_type", "report"),
            hierarchy=hierarchy,
            level="table",
            parent_context=parent_context,
            section_title=f"Bảng {table['number']}",
            char_count=len(content),
            chunk_index=chunk_index,
            total_chunks=0,
            is_complete_unit=True,
            has_table=True,
            has_list=False,
            extra_metadata={
                "table_number": table["number"],
                "phan": table.get("phan"),
            },
        )

    def _split_large_table(
        self,
        table: Dict,
        document: ProcessedDocument,
        doc_id: str,
        chunk_index: int,
    ) -> List[UniversalChunk]:
        """Split large table into multiple chunks."""
        content = table["content"]

        # Split with overlap
        sub_texts = self._split_with_overlap(
            text=content,
            max_size=self.max_size,
            overlap=self.overlap,
        )

        chunks = []
        for idx, sub_text in enumerate(sub_texts):
            hierarchy = []
            if table.get("phan"):
                hierarchy.append(table["phan"])
            hierarchy.append(f"Bảng {table['number']} (phần {idx+1})")

            parent_context = table.get("phan")

            chunk_id = self._generate_chunk_id(
                document_id=doc_id,
                chunk_index=chunk_index + idx,
                level="table_part",
            )

            chunk = UniversalChunk(
                content=sub_text,
                chunk_id=chunk_id,
                document_id=doc_id,
                document_type=document.metadata.get("document_type", "report"),
                hierarchy=hierarchy,
                level="table_part",
                parent_context=parent_context,
                section_title=f"Bảng {table['number']} (phần {idx+1})",
                char_count=len(sub_text),
                chunk_index=chunk_index + idx,
                total_chunks=0,
                is_complete_unit=False,
                has_table=True,
                has_list=False,
                extra_metadata={
                    "table_number": table["number"],
                    "phan": table.get("phan"),
                    "part_index": idx,
                },
            )
            chunks.append(chunk)

        return chunks

    def _merge_small_chunks_recursive(
        self,
        chunks: List[UniversalChunk],
        document: ProcessedDocument,
        doc_id: str,
    ) -> List[UniversalChunk]:
        """
        Recursively merge small chunks.

        Same strategy as BiddingHybridChunker and HierarchicalChunker.
        """
        if not chunks:
            return chunks

        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            merged_any = False
            new_chunks = []
            i = 0

            while i < len(chunks):
                current = chunks[i]

                # Check if too small
                if len(current.content) < self.min_size and i < len(chunks) - 1:
                    next_chunk = chunks[i + 1]

                    # Check if can merge
                    if self._can_merge_chunks(current, next_chunk):
                        combined_size = len(current.content) + len(next_chunk.content)

                        if combined_size <= self.max_size:
                            # Merge
                            merged = self._merge_two_chunks(current, next_chunk, doc_id)
                            new_chunks.append(merged)
                            merged_any = True
                            i += 2
                            continue

                # Keep as-is
                new_chunks.append(current)
                i += 1

            chunks = new_chunks
            iteration += 1

            if not merged_any:
                break

        return chunks

    def _can_merge_chunks(self, chunk1: UniversalChunk, chunk2: UniversalChunk) -> bool:
        """Check if two chunks can be merged."""
        # Same document
        if chunk1.document_id != chunk2.document_id:
            return False

        # Same parent (PHẦN)
        if chunk1.parent_context != chunk2.parent_context:
            return False

        # Allow merging incomplete units (split sections) MORE AGGRESSIVELY
        # Only block if BOTH are tables (preserve table integrity)
        if chunk1.has_table and chunk2.has_table:
            return False

        return True

    def _merge_two_chunks(
        self,
        chunk1: UniversalChunk,
        chunk2: UniversalChunk,
        doc_id: str,
    ) -> UniversalChunk:
        """Merge two chunks."""
        # Combine content
        combined_content = f"{chunk1.content}\n\n{chunk2.content}"

        # Merge hierarchy
        merged_hierarchy = chunk1.hierarchy.copy()
        for item in chunk2.hierarchy:
            if item not in merged_hierarchy:
                merged_hierarchy.append(item)

        # Combine titles
        merged_title = f"{chunk1.section_title} + {chunk2.section_title}"

        # Merge metadata
        merged_metadata = chunk1.extra_metadata.copy()
        merged_metadata["merged_with"] = chunk2.extra_metadata.get("section_number", "")
        merged_metadata["is_merged"] = True

        # Detect special content
        special_flags = self._detect_special_content(combined_content)

        return UniversalChunk(
            content=combined_content,
            chunk_id=f"{chunk1.chunk_id}_merged",
            document_id=doc_id,
            document_type=chunk1.document_type,
            hierarchy=merged_hierarchy,
            level=chunk1.level,
            parent_context=chunk1.parent_context,
            section_title=merged_title,
            char_count=len(combined_content),
            chunk_index=chunk1.chunk_index,
            total_chunks=0,
            is_complete_unit=True,
            has_table=special_flags["has_table"],
            has_list=special_flags["has_list"],
            extra_metadata=merged_metadata,
        )

    def _generate_document_id(self, document: ProcessedDocument) -> str:
        """Generate document ID."""
        doc_type = document.metadata.get("document_type", "report")
        title = document.metadata.get("title", "untitled")
        title_slug = re.sub(r"[^a-z0-9]+", "_", title.lower())[:50]
        return f"{doc_type}_{title_slug}"
