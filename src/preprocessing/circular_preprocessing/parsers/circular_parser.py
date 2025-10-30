"""
Circular Structure Parser

Parse Vietnamese Circular documents into hierarchical structure.
Handles circular-specific patterns and administrative document organization.
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class StructureNode:
    """Represents a node in the document structure tree"""
    type: str           # 'circular', 'chapter', 'section', 'article', 'clause', 'point'
    number: str         # Number/identifier
    title: str          # Title/content
    level: int          # Hierarchy level (1=highest)
    parent: Optional['StructureNode'] = None
    children: List['StructureNode'] = None
    text_content: str = ""
    metadata: Dict = None

    def __post_init__(self):
        if self.children is None:
            self.children = []
        if self.metadata is None:
            self.metadata = {}


class CircularParser:
    """Parse Circular documents into structured hierarchy"""

    def __init__(self):
        # Structure patterns for Vietnamese Circulars
        self.patterns = {
            # Main document header
            "circular_header": (
                r"^(THÔNG TƯ|Thông tư)\s*(?:số\s*(\d+/[\d/A-Z-]+))?\s*(?:ngày\s*([\d/]+))?\s*(.*)$",
                1
            ),
            
            # Main sections
            "chapter": (
                r"^(CHƯƠNG|Chương)\s+([IVXLCDM]+|\d+)[\.\:]?\s*(.*)$",
                2
            ),
            
            "section": (
                r"^(MỤC|Mục)\s+(\d+)[\.\:]?\s*(.*)$", 
                3
            ),
            
            # Content structure
            "regulation": (
                r"^(QUY ĐỊNH|Quy định)\s+(\d+)[\.\:]?\s*(.*)$",
                4
            ),
            
            "guidance": (
                r"^(HƯỚNG DẪN|Hướng dẫn)\s+(\d+)[\.\:]?\s*(.*)$",
                4
            ),
            
            "article": (
                r"^Điều\s+(\d+[a-z]?)[\.\:]?\s*(.*)$",
                4
            ),
            
            "clause": (
                r"^(\d+)[\.\:]?\s+(.+)$",
                5
            ),
            
            "point": (
                r"^([a-zđ])\)\s*(.+)$",
                6
            ),
            
            "sub_point": (
                r"^-\s*(.+)$",
                7
            )
        }

        # Pattern priority (higher number = higher priority)
        self.pattern_priority = {
            "circular_header": 10,
            "chapter": 9,
            "section": 8, 
            "regulation": 7,
            "guidance": 7,
            "article": 7,
            "clause": 6,
            "point": 5,
            "sub_point": 4
        }

    def parse(self, text: str) -> StructureNode:
        """
        Parse circular text into structured hierarchy

        Args:
            text: Cleaned circular text

        Returns:
            Root StructureNode containing the document structure
        """
        lines = text.split('\n')
        
        # Create root node
        root = StructureNode(
            type="circular_root",
            number="",
            title="Circular Document", 
            level=0,
            metadata={"total_lines": len(lines)}
        )

        # Parse lines into structure
        current_path = [root]  # Stack of current hierarchy path
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue

            # Try to match against structure patterns
            node = self._parse_line(line, line_num)
            
            if node:
                # Find appropriate parent in current path
                parent = self._find_parent(current_path, node.level)
                
                # Add to parent
                node.parent = parent
                parent.children.append(node)
                
                # Update current path
                current_path = current_path[:node.level] + [node]
                
            else:
                # Regular text content - add to current node
                if current_path:
                    current_node = current_path[-1]
                    if current_node.text_content:
                        current_node.text_content += "\n" + line
                    else:
                        current_node.text_content = line

        # Post-process to add metadata
        self._add_metadata(root)
        
        return root

    def _parse_line(self, line: str, line_num: int) -> Optional[StructureNode]:
        """Parse a single line to identify structure"""
        
        # Try each pattern in priority order
        best_match = None
        best_priority = -1
        
        for pattern_name, (pattern, level) in self.patterns.items():
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                priority = self.pattern_priority.get(pattern_name, 0)
                if priority > best_priority:
                    best_priority = priority
                    best_match = (pattern_name, match, level)

        if not best_match:
            return None

        pattern_name, match, level = best_match
        groups = match.groups()
        
        # Extract components based on pattern
        if pattern_name == "circular_header":
            number = groups[1] if len(groups) > 1 and groups[1] else ""
            date = groups[2] if len(groups) > 2 and groups[2] else ""
            title = groups[3] if len(groups) > 3 and groups[3] else ""
            
            return StructureNode(
                type="circular",
                number=number,
                title=title.strip(),
                level=level,
                metadata={
                    "issue_date": date,
                    "line_number": line_num,
                    "raw_text": line
                }
            )
            
        elif pattern_name in ["chapter", "section", "regulation", "guidance", "article"]:
            number = groups[1] if len(groups) > 1 else groups[0]
            title = groups[2] if len(groups) > 2 else ""
            
            return StructureNode(
                type=pattern_name,
                number=str(number),
                title=title.strip(),
                level=level,
                metadata={
                    "line_number": line_num,
                    "raw_text": line
                }
            )
            
        elif pattern_name in ["clause", "point", "sub_point"]:
            if pattern_name == "sub_point":
                number = ""
                title = groups[0]
            else:
                number = groups[0]
                title = groups[1] if len(groups) > 1 else ""
            
            return StructureNode(
                type=pattern_name,
                number=str(number),
                title=title.strip(),
                level=level,
                metadata={
                    "line_number": line_num,
                    "raw_text": line
                }
            )

        return None

    def _find_parent(self, current_path: List[StructureNode], level: int) -> StructureNode:
        """Find appropriate parent node for given level"""
        
        # Go up the path until we find a node with level < target level
        for i in range(len(current_path) - 1, -1, -1):
            if current_path[i].level < level:
                return current_path[i]
        
        # If no appropriate parent found, use root
        return current_path[0]

    def _add_metadata(self, root: StructureNode):
        """Add metadata to all nodes"""
        
        def process_node(node: StructureNode):
            # Count children by type
            child_counts = {}
            for child in node.children:
                child_type = child.type
                child_counts[child_type] = child_counts.get(child_type, 0) + 1
                process_node(child)  # Recursive
            
            node.metadata.update({
                "child_count": len(node.children),
                "child_types": child_counts,
                "has_content": bool(node.text_content.strip()),
                "content_length": len(node.text_content) if node.text_content else 0
            })

        process_node(root)

    def get_structure_summary(self, root: StructureNode) -> Dict:
        """Get summary statistics of document structure"""
        
        def count_nodes(node: StructureNode, counts: Dict[str, int]):
            counts[node.type] = counts.get(node.type, 0) + 1
            for child in node.children:
                count_nodes(child, counts)
        
        counts = {}
        count_nodes(root, counts)
        
        return {
            "total_nodes": sum(counts.values()),
            "node_counts": counts,
            "max_depth": self._get_max_depth(root),
            "has_chapters": "chapter" in counts,
            "has_sections": "section" in counts,
            "has_articles": "article" in counts,
            "has_regulations": "regulation" in counts,
            "has_guidance": "guidance" in counts,
        }

    def _get_max_depth(self, node: StructureNode) -> int:
        """Get maximum depth of structure tree"""
        if not node.children:
            return node.level
        
        return max(self._get_max_depth(child) for child in node.children)

    def export_structure_tree(self, root: StructureNode, indent: str = "") -> str:
        """Export structure tree as readable text"""
        
        lines = []
        
        # Current node
        node_info = f"{indent}{root.type}"
        if root.number:
            node_info += f" {root.number}"
        if root.title:
            node_info += f": {root.title}"
        
        lines.append(node_info)
        
        # Children
        for child in root.children:
            child_lines = self.export_structure_tree(child, indent + "  ")
            lines.append(child_lines)
        
        return "\n".join(lines)