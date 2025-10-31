"""
Hierarchical chunking for legal documents.

Strategy:
- Chunk by Điều (Article) as primary unit
- Preserve hierarchy: Phần → Chương → Mục → Điều → Khoản
- Add parent context for better retrieval
- Split large Điều by Khoản if needed

Supports:
- Luật (Law)
- Nghị định (Decree)
- Thông tư (Circular)
- Quyết định (Decision)
"""

import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from src.chunking.base_chunker import BaseLegalChunker, UniversalChunk
from src.preprocessing.base.models import ProcessedDocument


class HierarchicalChunker(BaseLegalChunker):
    """
    Hierarchical chunking for legal documents.

    Refactored from chunk_strategy.py with improvements:
    - Uses UniversalChunk format
    - Supports Phần/Mục (previously only Chương/Điều)
    - Better Khoản splitting logic
    - Consistent with V2 UnifiedLegalChunk schema

    Chunking unit: Điều (Article)
    - Optimal size: 500-1,500 chars
    - If Điều too long (>1,500 chars): split by Khoản
    - If Khoản too long: use overlap splitting

    Hierarchy structure:
    Luật/Nghị định/Thông tư
    ├── PHẦN I (optional)
    │   ├── CHƯƠNG I
    │   │   ├── Mục 1 (optional)
    │   │   │   ├── Điều 1
    │   │   │   │   ├── Khoản 1
    │   │   │   │   │   ├── Điểm a
    """

    # Regex patterns for legal structure
    PATTERNS = {
        "phan": r"^(PHẦN|Phần)\s+([IVXLCDM]+|THỨ\s+[A-Z]+)[:\.]?\s*(.+?)$",
        "chuong": r"^(CHƯƠNG|Chương)\s+([IVXLCDM]+)[:\.]?\s*(.+?)$",
        "muc": r"^(MỤC|Mục)\s+(\d+)[:\.]?\s*(.+?)$",
        "dieu": r"^Điều\s+(\d+[a-z]?)[:\.]?\s*(.+?)$",
        "khoan": r"^(\d+)\.\s+(.+)",
        "diem": r"^([a-zđ])\)\s+(.+)",
    }

    def __init__(
        self,
        min_size: int = 300,
        max_size: int = 1500,
        target_size: int = 800,
        overlap: int = 100,
        preserve_context: bool = True,
        split_large_dieu: bool = True,
    ):
        """
        Args:
            split_large_dieu: If True, split Điều larger than max_size by Khoản
        """
        super().__init__(min_size, max_size, target_size, overlap, preserve_context)
        self.split_large_dieu = split_large_dieu

    def chunk(self, document: ProcessedDocument) -> List[UniversalChunk]:
        """
        Chunk legal document hierarchically.

        Args:
            document: ProcessedDocument from DocxLoader

        Returns:
            List of UniversalChunk objects

        Raises:
            ValueError: If document type not legal
        """
        # Validate document type
        doc_type = document.metadata.get("document_type", "")
        if doc_type not in ["law", "decree", "circular", "decision"]:
            raise ValueError(
                f"HierarchicalChunker only supports legal documents, got: {doc_type}"
            )

        # Get full text
        full_text = document.content.get("full_text", "")
        if not full_text:
            return []

        # Clean text
        full_text = self._clean_text(full_text)

        # Parse hierarchical structure
        structure = self._parse_structure(full_text)

        # Generate document ID
        doc_id = self._generate_document_id(document)

        # Build chunks
        chunks = self._build_chunks_from_structure(
            structure=structure,
            document=document,
            doc_id=doc_id,
        )

        # Update statistics
        self._update_statistics(chunks)

        return chunks

    def _parse_structure(self, text: str) -> List[Dict]:
        """
        Parse legal document structure.

        Identifies:
        - Phần (Part)
        - Chương (Chapter)
        - Mục (Section)
        - Điều (Article)
        - Khoản (Clause)
        - Điểm (Point)

        Args:
            text: Full document text

        Returns:
            List of structured elements with hierarchy
        """
        lines = text.split("\n")
        structure = []

        # Current hierarchy context
        current_phan = None
        current_chuong = None
        current_muc = None
        current_dieu = None

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if not line:
                i += 1
                continue

            # Check Phần
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

            # Check Chương
            chuong_match = re.match(self.PATTERNS["chuong"], line)
            if chuong_match:
                current_chuong = {
                    "type": "chuong",
                    "number": chuong_match.group(2),
                    "title": chuong_match.group(3).strip(),
                    "full_title": line,
                    "phan": current_phan["full_title"] if current_phan else None,
                }
                structure.append(current_chuong)
                i += 1
                continue

            # Check Mục
            muc_match = re.match(self.PATTERNS["muc"], line)
            if muc_match:
                current_muc = {
                    "type": "muc",
                    "number": muc_match.group(2),
                    "title": muc_match.group(3).strip(),
                    "full_title": line,
                    "chuong": current_chuong["full_title"] if current_chuong else None,
                    "phan": current_phan["full_title"] if current_phan else None,
                }
                structure.append(current_muc)
                i += 1
                continue

            # Check Điều
            dieu_match = re.match(self.PATTERNS["dieu"], line)
            if dieu_match:
                dieu_num = dieu_match.group(1)
                dieu_title = dieu_match.group(2).strip()

                # Collect Điều content (until next Điều/Chương/Mục)
                content_lines = [line]
                j = i + 1

                while j < len(lines):
                    next_line = lines[j].strip()

                    # Stop at next structural element
                    if (
                        re.match(self.PATTERNS["phan"], next_line)
                        or re.match(self.PATTERNS["chuong"], next_line)
                        or re.match(self.PATTERNS["muc"], next_line)
                        or re.match(self.PATTERNS["dieu"], next_line)
                    ):
                        break

                    content_lines.append(lines[j])
                    j += 1

                current_dieu = {
                    "type": "dieu",
                    "number": dieu_num,
                    "title": dieu_title,
                    "full_title": line,
                    "content": "\n".join(content_lines),
                    "muc": current_muc["full_title"] if current_muc else None,
                    "chuong": current_chuong["full_title"] if current_chuong else None,
                    "phan": current_phan["full_title"] if current_phan else None,
                }

                structure.append(current_dieu)
                i = j
                continue

            i += 1

        return structure

    def _build_chunks_from_structure(
        self,
        structure: List[Dict],
        document: ProcessedDocument,
        doc_id: str,
    ) -> List[UniversalChunk]:
        """
        Build chunks from parsed structure.

        Strategy:
        1. Each Điều = 1 chunk (primary unit)
        2. If Điều > max_size: split by Khoản
        3. If Khoản > max_size: use overlap splitting
        4. Add parent context (Chương/Mục title)

        Args:
            structure: Parsed structure from _parse_structure
            document: Original ProcessedDocument
            doc_id: Generated document ID

        Returns:
            List of UniversalChunk objects
        """
        chunks = []
        chunk_index = 0

        # Filter only Điều elements
        dieu_elements = [item for item in structure if item["type"] == "dieu"]
        total_dieu = len(dieu_elements)

        for dieu in dieu_elements:
            dieu_chunks = self._chunk_dieu(
                dieu=dieu,
                document=document,
                doc_id=doc_id,
                chunk_index=chunk_index,
            )

            chunks.extend(dieu_chunks)
            chunk_index += len(dieu_chunks)

        # Update total_chunks for all chunks
        for chunk in chunks:
            chunk.total_chunks = chunk_index

        return chunks

    def _chunk_dieu(
        self,
        dieu: Dict,
        document: ProcessedDocument,
        doc_id: str,
        chunk_index: int,
    ) -> List[UniversalChunk]:
        """
        Chunk a single Điều.

        Logic:
        - If Điều size <= max_size: return as single chunk
        - If Điều size > max_size AND split_large_dieu: split by Khoản
        - Otherwise: use overlap splitting

        Args:
            dieu: Điều element from structure
            document: Original ProcessedDocument
            doc_id: Document ID
            chunk_index: Current chunk index

        Returns:
            List of chunks (usually 1, sometimes multiple)
        """
        content = dieu["content"]
        size = len(content)

        # Case 1: Điều fits in one chunk
        if size <= self.max_size:
            return [
                self._create_chunk(
                    content=content,
                    dieu=dieu,
                    document=document,
                    doc_id=doc_id,
                    chunk_index=chunk_index,
                    khoan_number=None,
                )
            ]

        # Case 2: Điều too large, try splitting by Khoản
        if self.split_large_dieu:
            khoan_chunks = self._split_by_khoan(
                dieu=dieu,
                document=document,
                doc_id=doc_id,
                chunk_index=chunk_index,
            )

            if khoan_chunks:
                return khoan_chunks

        # Case 3: Fallback to overlap splitting
        return self._split_by_overlap(
            content=content,
            dieu=dieu,
            document=document,
            doc_id=doc_id,
            chunk_index=chunk_index,
        )

    def _split_by_khoan(
        self,
        dieu: Dict,
        document: ProcessedDocument,
        doc_id: str,
        chunk_index: int,
    ) -> List[UniversalChunk]:
        """
        Split Điều by Khoản (clauses).

        Args:
            dieu: Điều element
            document: ProcessedDocument
            doc_id: Document ID
            chunk_index: Starting chunk index

        Returns:
            List of chunks (one per Khoản), or empty list if no Khoản found
        """
        content = dieu["content"]
        lines = content.split("\n")

        # Find Khoản boundaries
        khoan_starts = []
        for i, line in enumerate(lines):
            if re.match(self.PATTERNS["khoan"], line):
                khoan_match = re.match(self.PATTERNS["khoan"], line)
                khoan_num = int(khoan_match.group(1))
                khoan_starts.append((i, khoan_num))

        # No Khoản found
        if not khoan_starts:
            return []

        # Build chunks for each Khoản
        chunks = []

        for idx, (start_line, khoan_num) in enumerate(khoan_starts):
            # Determine end line (next Khoản or end of content)
            if idx + 1 < len(khoan_starts):
                end_line = khoan_starts[idx + 1][0]
            else:
                end_line = len(lines)

            # Extract Khoản content
            khoan_lines = lines[start_line:end_line]
            khoan_content = "\n".join(khoan_lines)

            # Add Điều title for context
            dieu_title = dieu["full_title"]
            full_content = f"{dieu_title}\n\n{khoan_content}"

            # Check if Khoản still too large
            if len(full_content) > self.max_size:
                # Further split with overlap
                sub_chunks = self._split_with_overlap(
                    text=full_content,
                    max_size=self.max_size,
                    overlap=self.overlap,
                )

                for sub_idx, sub_content in enumerate(sub_chunks):
                    chunk = self._create_chunk(
                        content=sub_content,
                        dieu=dieu,
                        document=document,
                        doc_id=doc_id,
                        chunk_index=chunk_index + len(chunks),
                        khoan_number=f"{khoan_num}.{sub_idx+1}",
                    )
                    chunks.append(chunk)
            else:
                # Khoản fits in one chunk
                chunk = self._create_chunk(
                    content=full_content,
                    dieu=dieu,
                    document=document,
                    doc_id=doc_id,
                    chunk_index=chunk_index + len(chunks),
                    khoan_number=str(khoan_num),
                )
                chunks.append(chunk)

        return chunks

    def _split_by_overlap(
        self,
        content: str,
        dieu: Dict,
        document: ProcessedDocument,
        doc_id: str,
        chunk_index: int,
    ) -> List[UniversalChunk]:
        """
        Split content using overlap strategy (fallback).

        Used when:
        - Điều has no Khoản structure
        - Khoản too large to fit in max_size

        Args:
            content: Content to split
            dieu: Điều element
            document: ProcessedDocument
            doc_id: Document ID
            chunk_index: Starting chunk index

        Returns:
            List of overlapping chunks
        """
        sub_texts = self._split_with_overlap(
            text=content,
            max_size=self.max_size,
            overlap=self.overlap,
        )

        chunks = []
        for idx, sub_text in enumerate(sub_texts):
            chunk = self._create_chunk(
                content=sub_text,
                dieu=dieu,
                document=document,
                doc_id=doc_id,
                chunk_index=chunk_index + idx,
                khoan_number=f"part{idx+1}",
                is_complete_unit=False,  # Overlap split = incomplete unit
            )
            chunks.append(chunk)

        return chunks

    def _create_chunk(
        self,
        content: str,
        dieu: Dict,
        document: ProcessedDocument,
        doc_id: str,
        chunk_index: int,
        khoan_number: Optional[str] = None,
        is_complete_unit: bool = True,
    ) -> UniversalChunk:
        """
        Create a UniversalChunk from Điều/Khoản content.

        Args:
            content: Chunk content
            dieu: Điều element with hierarchy info
            document: Original ProcessedDocument
            doc_id: Document ID
            chunk_index: Chunk position
            khoan_number: Khoản number if applicable
            is_complete_unit: Whether chunk is semantically complete

        Returns:
            UniversalChunk object
        """
        # Build hierarchy path
        hierarchy = []
        if dieu.get("phan"):
            hierarchy.append(dieu["phan"])
        if dieu.get("chuong"):
            hierarchy.append(dieu["chuong"])
        if dieu.get("muc"):
            hierarchy.append(dieu["muc"])
        hierarchy.append(dieu["full_title"])
        if khoan_number:
            hierarchy.append(f"Khoản {khoan_number}")

        # Parent context (for embedding)
        parent_titles = []
        if dieu.get("chuong"):
            parent_titles.append(dieu["chuong"])
        if dieu.get("muc"):
            parent_titles.append(dieu["muc"])

        parent_context = " > ".join(parent_titles) if parent_titles else None

        # Add context to content
        enhanced_content = self._add_parent_context(
            chunk_content=content,
            parent_title=parent_context,
            section_title=dieu["full_title"],
        )

        # Generate chunk ID
        level = "khoan" if khoan_number else "dieu"
        chunk_id = self._generate_chunk_id(
            document_id=doc_id,
            chunk_index=chunk_index,
            level=level,
        )

        # Detect special content
        special_flags = self._detect_special_content(content)

        # Create chunk
        chunk = UniversalChunk(
            content=enhanced_content,
            chunk_id=chunk_id,
            document_id=doc_id,
            document_type=document.metadata.get("document_type", ""),
            hierarchy=hierarchy,
            level=level,
            parent_context=parent_context,
            section_title=dieu["title"],
            char_count=len(enhanced_content),
            chunk_index=chunk_index,
            total_chunks=0,  # Will be updated later
            is_complete_unit=is_complete_unit,
            has_table=special_flags["has_table"],
            has_list=special_flags["has_list"],
            extra_metadata={
                "dieu_number": dieu["number"],
                "khoan_number": khoan_number,
                "phan": dieu.get("phan"),
                "chuong": dieu.get("chuong"),
                "muc": dieu.get("muc"),
            },
        )

        return chunk

    def _generate_document_id(self, document: ProcessedDocument) -> str:
        """
        Generate document ID from metadata.

        Format: {doc_type}_{legal_id}
        Example: law_43_2013, decree_63_2014

        Args:
            document: ProcessedDocument

        Returns:
            Document ID string
        """
        doc_type = document.metadata.get("document_type", "unknown")

        # Try to get legal ID
        legal_metadata = document.metadata.get("legal_metadata", {})
        legal_id = legal_metadata.get("legal_id", "")

        if legal_id:
            # Clean legal ID (replace / with _)
            legal_id_clean = legal_id.replace("/", "_").replace(" ", "_")
            return f"{doc_type}_{legal_id_clean}"

        # Fallback: use title slug
        title = document.metadata.get("title", "untitled")
        title_slug = re.sub(r"[^a-z0-9]+", "_", title.lower())[:50]

        return f"{doc_type}_{title_slug}"
