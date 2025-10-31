"""
Decree Parser - Parse decree structure

Nghị định structure: Chương → Điều → Khoản → Điểm
(Simpler than Law: no Phần, Mục)
"""

import re
from typing import List, Optional
from dataclasses import dataclass

from ...base.base_parser import BaseParser, StructureNode


class DecreeParser(BaseParser):
    """
    Parser cho Nghị định (Decree documents)

    Simplified hierarchy:
    - Chương (Chapter)
    - Điều (Article)
    - Khoản (Clause)
    - Điểm (Point)
    """

    # Regex patterns for decree structure
    PATTERNS = {
        "chuong": re.compile(
            r"^(CHƯƠNG|Chương)\s+([IVXLCDM]+|[0-9]+)[:\s.]?\s*(.*?)$", re.IGNORECASE
        ),
        "dieu": re.compile(r"^Điều\s+(\d+[a-z]?)[:\s.]?\s*(.*?)$"),
        "khoan": re.compile(r"^(\d+)\.\s+(.*?)$"),
        "diem": re.compile(r"^([a-zđ])\)\s+(.*?)$"),
    }

    def __init__(self):
        """Initialize parser với decree patterns"""
        self.structure_tree = None
        print("✅ DecreeParser initialized")

    def parse(self, text: str, metadata: dict = None) -> StructureNode:
        """
        Parse decree text into hierarchical structure

        Args:
            text: Full decree text
            metadata: Optional metadata từ extractor

        Returns:
            Root StructureNode với decree hierarchy
        """
        lines = text.split("\n")

        # Create root node
        doc_title = metadata.get("title", "Nghị định") if metadata else "Nghị định"
        root = StructureNode(
            type="document",
            level="root",
            number="",
            title=doc_title,
            content="",
        )

        # Parse hierarchy
        current_chuong = None
        current_dieu = None
        current_khoan = None

        pending_content = []  # Nội dung chờ gán cho node

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for Chương
            if match := self.PATTERNS["chuong"].match(line):
                # Save pending content to previous node
                if current_dieu:
                    current_dieu.content += "\n".join(pending_content)
                    pending_content = []

                current_chuong = StructureNode(
                    type="chuong",
                    level="chuong",
                    number=match.group(2),
                    title=match.group(3).strip() if match.group(3) else "",
                    content="",
                )
                root.children.append(current_chuong)
                current_dieu = None
                current_khoan = None
                continue

            # Check for Điều
            if match := self.PATTERNS["dieu"].match(line):
                # Save pending content
                if current_dieu:
                    current_dieu.content += "\n".join(pending_content)
                    pending_content = []

                parent = current_chuong if current_chuong else root
                current_dieu = StructureNode(
                    type="dieu",
                    level="dieu",
                    number=match.group(1),
                    title=match.group(2).strip() if match.group(2) else "",
                    content="",
                )
                parent.children.append(current_dieu)
                current_khoan = None
                continue

            # Check for Khoản
            if match := self.PATTERNS["khoan"].match(line):
                # Save pending content
                if current_khoan:
                    current_khoan.content += "\n".join(pending_content)
                elif current_dieu:
                    current_dieu.content += "\n".join(pending_content)
                pending_content = []

                if current_dieu:
                    current_khoan = StructureNode(
                        type="khoan",
                        level="khoan",
                        number=match.group(1),
                        title="",
                        content=match.group(2).strip(),
                    )
                    current_dieu.children.append(current_khoan)
                continue

            # Check for Điểm
            if match := self.PATTERNS["diem"].match(line):
                if current_khoan:
                    diem_node = StructureNode(
                        type="diem",
                        level="diem",
                        number=match.group(1),
                        title="",
                        content=match.group(2).strip(),
                    )
                    current_khoan.children.append(diem_node)
                continue

            # Regular content
            pending_content.append(line)

        # Save final pending content
        if current_khoan:
            current_khoan.content += "\n".join(pending_content)
        elif current_dieu:
            current_dieu.content += "\n".join(pending_content)

        self.structure_tree = root
        return root

    def get_hierarchy_path(self, node: StructureNode) -> str:
        """
        Get full hierarchy path for a node

        Example: "Chương I > Điều 5 > Khoản 2"
        """
        # Note: StructureNode doesn't have parent, so this is simplified
        # In production, you'd need to track parent during parsing
        path_parts = []

        if node.type == "chuong":
            path_parts.append(f"Chương {node.number}")
        elif node.type == "dieu":
            path_parts.append(f"Điều {node.number}")
        elif node.type == "khoan":
            path_parts.append(f"Khoản {node.number}")
        elif node.type == "diem":
            path_parts.append(f"Điểm {node.number}")

        return " > ".join(path_parts)

    def validate_structure(self) -> bool:
        """
        Validate decree structure

        Returns:
            True if structure is valid
        """
        if not self.structure_tree:
            return False

        # Check for at least one Điều
        def has_dieu(node):
            if node.type == "dieu":
                return True
            return any(has_dieu(child) for child in node.children)

        return has_dieu(self.structure_tree)

    def get_structure_levels(self) -> List[str]:
        """
        Required by BaseParser

        Get supported structure levels for decrees

        Returns:
            List of structure levels
        """
        return ["document", "chuong", "dieu", "khoan", "diem"]
