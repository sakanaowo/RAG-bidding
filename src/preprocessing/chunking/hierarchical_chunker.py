"""
Hierarchical Chunker for Vietnamese Legal Documents
Strategy: Chunk by Điều with parent-child hierarchy preservation

Refactored from:
- src/chunking/strategies/chunk_strategy.py (LegalDocumentChunker)
- archive/preprocessing_v1/parsers_original/optimal_chunker.py

Integrated with V2 Unified Schema
"""

from __future__ import annotations
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from ..loaders import RawDocxContent
from ..schema import UnifiedLegalChunk, ContentStructure, ProcessingMetadata


@dataclass
class HierarchyNode:
    """Represents a node in Vietnamese legal document hierarchy"""

    type: str  # 'phan', 'chuong', 'muc', 'dieu', 'khoan', 'diem'
    number: str  # e.g., "I", "1", "a"
    title: str
    content: str
    parent_path: List[str]  # Hierarchy path from root
    start_pos: int
    end_pos: int
    children: List["HierarchyNode"] = None

    def __post_init__(self):
        if self.children is None:
            self.children = []


class HierarchicalChunker:
    """
    Hierarchical chunking strategy for Vietnamese legal documents.

    Strategy:
    1. Parse document into hierarchy tree (Phần > Chương > Mục > Điều > Khoản > Điểm)
    2. Primary chunking level: Điều (Article)
    3. Split large Điều by Khoản (Clause) if needed
    4. Preserve parent context in metadata
    5. Build parent-child relationships

    Example:
        Chương I -> QUY ĐỊNH CHUNG
            Điều 1 -> Phạm vi điều chỉnh
                Khoản 1 -> ...
                Khoản 2 -> ...
            Điều 2 -> Đối tượng áp dụng
    """

    def __init__(
        self,
        max_chunk_size: int = 2000,
        min_chunk_size: int = 300,
        overlap_size: int = 150,
        preserve_parent_context: bool = True,
        split_large_dieu: bool = True,
    ):
        """
        Args:
            max_chunk_size: Maximum characters per chunk
            min_chunk_size: Minimum characters per chunk (avoid tiny chunks)
            overlap_size: Overlap between consecutive chunks (for context)
            preserve_parent_context: Include parent titles in chunk text
            split_large_dieu: Split Điều by Khoản if exceeds max_chunk_size
        """
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap_size = overlap_size
        self.preserve_parent_context = preserve_parent_context
        self.split_large_dieu = split_large_dieu

        # Vietnamese legal structure regex patterns
        self.patterns = {
            "phan": re.compile(
                r"^PHẦN\s+(THỨ\s+)?([IVXLCDM]+|MỘT|HAI|BA|BỐN|NÃM|SÁU|BẢY|TÁM|CHÍN|MƯỜI)[:\.]?\s*(.+?)$",
                re.IGNORECASE,
            ),
            "chuong": re.compile(
                r"^CHƯƠNG\s+([IVXLCDM]+|[0-9]+)[:\.]?\s*(.+?)$", re.IGNORECASE
            ),
            "muc": re.compile(
                r"^MỤC\s+([0-9]+|[IVXLCDM]+)[:\.]?\s*(.+?)$", re.IGNORECASE
            ),
            "dieu": re.compile(r"^Điều\s+(\d+[a-z]?)\.\s*(.+?)$"),
            "khoan": re.compile(r"^(\d+)\.\s+(.+)"),
            "diem": re.compile(r"^([a-zđ])\)\s+(.+)"),
        }

    def chunk(
        self,
        raw_content: RawDocxContent,
        doc_id: str,
        base_metadata: Dict,
    ) -> List[UnifiedLegalChunk]:
        """
        Main chunking method.

        Args:
            raw_content: RawDocxContent from DocxLoader
            doc_id: Document ID (e.g., "43/2013/QH13")
            base_metadata: Base metadata to include in all chunks

        Returns:
            List of UnifiedLegalChunk objects
        """
        # Step 1: Build hierarchy tree from structure
        hierarchy_tree = self._build_hierarchy_tree(raw_content.structure)

        # Step 2: Extract all Điều nodes
        dieu_nodes = self._extract_dieu_nodes(hierarchy_tree)

        # Step 3: Create chunks from Điều
        chunks = []
        for idx, dieu_node in enumerate(dieu_nodes):
            dieu_chunks = self._chunk_dieu(
                dieu_node=dieu_node,
                doc_id=doc_id,
                chunk_index=idx,
                base_metadata=base_metadata,
            )
            chunks.extend(dieu_chunks)

        # Step 4: Add parent-child relationships
        chunks = self._build_relationships(chunks)

        return chunks

    def _build_hierarchy_tree(self, structure: List[Dict]) -> List[HierarchyNode]:
        """
        Build hierarchy tree from RawDocxContent.structure.

        Args:
            structure: List of structure dicts from DocxLoader

        Returns:
            List of top-level HierarchyNode objects (Phần or Chương)
        """
        nodes = []
        current_phan = None
        current_chuong = None
        current_muc = None
        current_dieu = None
        current_khoan = None

        for item in structure:
            item_type = item["type"]

            if item_type == "phan":
                current_phan = HierarchyNode(
                    type="phan",
                    number=item.get("number", ""),
                    title=item["text"],
                    content="",
                    parent_path=[],
                    start_pos=0,
                    end_pos=0,
                )
                nodes.append(current_phan)
                current_chuong = None
                current_muc = None
                current_dieu = None

            elif item_type == "chuong":
                parent = current_phan if current_phan else None
                parent_path = [current_phan.title] if current_phan else []

                current_chuong = HierarchyNode(
                    type="chuong",
                    number=item.get("number", ""),
                    title=item["text"],
                    content="",
                    parent_path=parent_path,
                    start_pos=0,
                    end_pos=0,
                )

                if parent:
                    parent.children.append(current_chuong)
                else:
                    nodes.append(current_chuong)

                current_muc = None
                current_dieu = None

            elif item_type == "muc":
                parent = current_chuong if current_chuong else current_phan
                parent_path = []
                if current_phan:
                    parent_path.append(current_phan.title)
                if current_chuong:
                    parent_path.append(current_chuong.title)

                current_muc = HierarchyNode(
                    type="muc",
                    number=item.get("number", ""),
                    title=item["text"],
                    content="",
                    parent_path=parent_path,
                    start_pos=0,
                    end_pos=0,
                )

                if parent:
                    parent.children.append(current_muc)
                else:
                    nodes.append(current_muc)

                current_dieu = None

            elif item_type == "dieu":
                parent = (
                    current_muc
                    if current_muc
                    else (current_chuong if current_chuong else current_phan)
                )
                parent_path = []
                if current_phan:
                    parent_path.append(current_phan.title)
                if current_chuong:
                    parent_path.append(current_chuong.title)
                if current_muc:
                    parent_path.append(current_muc.title)

                current_dieu = HierarchyNode(
                    type="dieu",
                    number=item.get("number", ""),
                    title=item["text"],
                    content=item.get("content", ""),
                    parent_path=parent_path,
                    start_pos=0,
                    end_pos=0,
                )

                if parent:
                    parent.children.append(current_dieu)
                else:
                    nodes.append(current_dieu)

                current_khoan = None

            elif item_type == "khoan" and current_dieu:
                parent_path = current_dieu.parent_path + [current_dieu.title]

                khoan_node = HierarchyNode(
                    type="khoan",
                    number=item.get("number", ""),
                    title=f"Khoản {item.get('number', '')}",
                    content=item["text"],
                    parent_path=parent_path,
                    start_pos=0,
                    end_pos=0,
                )

                current_dieu.children.append(khoan_node)
                current_khoan = khoan_node

            elif item_type == "diem" and current_khoan:
                parent_path = current_khoan.parent_path + [current_khoan.title]

                diem_node = HierarchyNode(
                    type="diem",
                    number=item.get("number", ""),
                    title=f"Điểm {item.get('number', '')}",
                    content=item["text"],
                    parent_path=parent_path,
                    start_pos=0,
                    end_pos=0,
                )

                current_khoan.children.append(diem_node)

        return nodes

    def _extract_dieu_nodes(self, tree: List[HierarchyNode]) -> List[HierarchyNode]:
        """Extract all Điều nodes from hierarchy tree (DFS)"""
        dieu_nodes = []

        def traverse(node: HierarchyNode):
            if node.type == "dieu":
                dieu_nodes.append(node)
            for child in node.children:
                traverse(child)

        for root in tree:
            traverse(root)

        return dieu_nodes

    def _chunk_dieu(
        self,
        dieu_node: HierarchyNode,
        doc_id: str,
        chunk_index: int,
        base_metadata: Dict,
    ) -> List[UnifiedLegalChunk]:
        """
        Create chunk(s) from a Điều node.

        If Điều is small enough: return 1 chunk
        If Điều is too large: split by Khoản and return multiple chunks
        """
        # Build full text with context
        chunk_text = self._build_chunk_text(dieu_node)

        # If within size limit, return single chunk
        if len(chunk_text) <= self.max_chunk_size or not self.split_large_dieu:
            return [
                self._create_chunk(
                    chunk_id=f"{doc_id}_dieu_{dieu_node.number}",
                    text=chunk_text,
                    dieu_node=dieu_node,
                    chunk_index=chunk_index,
                    base_metadata=base_metadata,
                )
            ]

        # Split by Khoản
        return self._split_dieu_by_khoan(
            dieu_node=dieu_node,
            doc_id=doc_id,
            chunk_index=chunk_index,
            base_metadata=base_metadata,
        )

    def _build_chunk_text(self, dieu_node: HierarchyNode) -> str:
        """Build chunk text with optional parent context"""
        parts = []

        # Add parent context if enabled
        if self.preserve_parent_context and dieu_node.parent_path:
            parts.append(" > ".join(dieu_node.parent_path))
            parts.append("")  # Empty line

        # Add Điều title
        parts.append(f"Điều {dieu_node.number}. {dieu_node.title}")
        parts.append("")  # Empty line

        # Add Điều content
        if dieu_node.content:
            parts.append(dieu_node.content)

        # Add Khoản content
        for khoan in dieu_node.children:
            if khoan.type == "khoan":
                parts.append(f"{khoan.number}. {khoan.content}")

                # Add Điểm content
                for diem in khoan.children:
                    if diem.type == "diem":
                        parts.append(f"{diem.number}) {diem.content}")

        return "\n".join(parts)

    def _split_dieu_by_khoan(
        self,
        dieu_node: HierarchyNode,
        doc_id: str,
        chunk_index: int,
        base_metadata: Dict,
    ) -> List[UnifiedLegalChunk]:
        """Split large Điều into multiple chunks by Khoản"""
        chunks = []

        # If no Khoản children, return as single chunk anyway
        khoan_children = [c for c in dieu_node.children if c.type == "khoan"]
        if not khoan_children:
            chunk_text = self._build_chunk_text(dieu_node)
            return [
                self._create_chunk(
                    chunk_id=f"{doc_id}_dieu_{dieu_node.number}",
                    text=chunk_text,
                    dieu_node=dieu_node,
                    chunk_index=chunk_index,
                    base_metadata=base_metadata,
                )
            ]

        # Create one chunk per Khoản
        for khoan_idx, khoan in enumerate(khoan_children, 1):
            chunk_parts = []

            # Context
            if self.preserve_parent_context and dieu_node.parent_path:
                chunk_parts.append(" > ".join(dieu_node.parent_path))
                chunk_parts.append("")

            # Điều header
            chunk_parts.append(f"Điều {dieu_node.number}. {dieu_node.title}")
            chunk_parts.append("")

            # Khoản content
            chunk_parts.append(f"{khoan.number}. {khoan.content}")

            # Điểm content
            for diem in khoan.children:
                if diem.type == "diem":
                    chunk_parts.append(f"{diem.number}) {diem.content}")

            chunk_text = "\n".join(chunk_parts)

            chunk = self._create_chunk(
                chunk_id=f"{doc_id}_dieu_{dieu_node.number}_khoan_{khoan.number}",
                text=chunk_text,
                dieu_node=dieu_node,
                khoan_node=khoan,
                chunk_index=chunk_index * 1000 + khoan_idx,  # Unique index
                base_metadata=base_metadata,
            )

            chunks.append(chunk)

        return chunks

    def _create_chunk(
        self,
        chunk_id: str,
        text: str,
        dieu_node: HierarchyNode,
        chunk_index: int,
        base_metadata: Dict,
        khoan_node: Optional[HierarchyNode] = None,
    ) -> UnifiedLegalChunk:
        """Create UnifiedLegalChunk from Điều/Khoản node"""

        # Build hierarchy path
        hierarchy_path = dieu_node.parent_path + [f"Điều {dieu_node.number}"]
        if khoan_node:
            hierarchy_path.append(f"Khoản {khoan_node.number}")

        # Build ContentStructure
        content_structure = ContentStructure(
            hierarchy_path=hierarchy_path,
            level=khoan_node.type if khoan_node else dieu_node.type,
            section_title=dieu_node.title,
            parent_sections=dieu_node.parent_path,
        )

        # Create chunk
        chunk = UnifiedLegalChunk(
            chunk_id=chunk_id,
            content=text,
            char_count=len(text),
            structure=content_structure,
        )

        # Copy base metadata fields
        for key, value in base_metadata.items():
            if hasattr(chunk, key):
                setattr(chunk, key, value)

        return chunk

    def _build_relationships(
        self, chunks: List[UnifiedLegalChunk]
    ) -> List[UnifiedLegalChunk]:
        """Build parent-child relationships and update metadata"""

        # TODO: Add parent_chunk_id, child_chunk_ids if needed in schema
        # For now, parent-child info is preserved in hierarchy_path

        return chunks
