"""
Bidding Law Structure Parser

Parse cấu trúc phân cấp của văn bản pháp luật đấu thầu:
Phần → Chương → Mục → Điều → Khoản → Điểm
"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class StructureNode:
    """Node trong cây cấu trúc văn bản"""

    type: str  # 'phan', 'chuong', 'muc', 'dieu', 'khoan', 'diem'
    number: str  # Số thứ tự (I, 1, a, etc.)
    title: str  # Tiêu đề
    content: str  # Nội dung
    level: int  # Level trong hierarchy (0=phan, 1=chuong, ..., 5=diem)
    parent: Optional["StructureNode"] = None
    children: List["StructureNode"] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def get_hierarchy_path(self) -> List[str]:
        """Get hierarchy path from root to this node"""
        path = []
        current = self
        while current:
            if current.type != "root":
                path.insert(0, f"{current.type.title()} {current.number}")
            current = current.parent
        return path

    def get_full_context(self) -> str:
        """Get full context including parent titles"""
        context_parts = []

        # Add hierarchy path
        path = self.get_hierarchy_path()
        if path:
            context_parts.append(" → ".join(path))

        # Add title if exists
        if self.title:
            context_parts.append(self.title)

        # Add content
        context_parts.append(self.content)

        return "\n\n".join(context_parts)


class BiddingLawParser:
    """Parser cho cấu trúc văn bản pháp luật đấu thầu"""

    def __init__(self):
        # Patterns để detect từng cấp độ
        self.patterns = {
            "phan": r"^(PHẦN\s+(?:THỨ\s+)?([IVXLCDM]+)|Phần\s+([IVXLCDM]+))[:\s.]?\s*(.*)$",
            "chuong": r"^(CHƯƠNG|Chương)\s+([IVXLCDM]+|[0-9]+)[:\s.]?\s*(.*)$",
            "muc": r"^(MỤC|Mục)\s+(\d+)[:\s.]?\s*(.*)$",
            "dieu": r"^Điều\s+(\d+[a-z]?)[:\s.]?\s*(.*)$",
            "khoan": r"^(\d+)\.\s+(.+)$",
            "diem": r"^([a-zđ])\)\s+(.+)$",
        }

        # Level mapping
        self.level_map = {"phan": 0, "chuong": 1, "muc": 2, "dieu": 3, "khoan": 4, "diem": 5}

    def parse(self, text: str, metadata: Dict = None) -> StructureNode:
        """
        Parse văn bản thành cây cấu trúc

        Args:
            text: Cleaned text của văn bản
            metadata: Document metadata

        Returns:
            Root StructureNode với full hierarchy
        """
        # Create root node
        root = StructureNode(
            type="root",
            number="0",
            title="Document Root",
            content="",
            level=-1,
            metadata=metadata or {},
        )

        # Split into lines
        lines = text.split("\n")

        # Track current parent for each level
        current_parents = {-1: root}  # level -> node

        # Temporary buffer để accumulate content
        current_node = None
        content_buffer = []

        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Try to match structural patterns
            matched = False

            for struct_type, pattern in self.patterns.items():
                match = re.match(pattern, line, re.I)

                if match:
                    # Save previous node's content
                    if current_node and content_buffer:
                        current_node.content = "\n".join(content_buffer).strip()
                        content_buffer = []

                    # Extract components
                    if struct_type == "phan":
                        number = match.group(2) or match.group(3)
                        title = match.group(4)
                    elif struct_type == "chuong":
                        number = match.group(2)
                        title = match.group(3)
                    elif struct_type == "muc":
                        number = match.group(2)
                        title = match.group(3)
                    elif struct_type == "dieu":
                        number = match.group(1)
                        title = match.group(2)
                    elif struct_type == "khoan":
                        number = match.group(1)
                        title = ""
                        # Khoản không có title riêng, content là sau số
                        content_buffer.append(match.group(2))
                    elif struct_type == "diem":
                        number = match.group(1)
                        title = ""
                        content_buffer.append(match.group(2))

                    # Create new node
                    level = self.level_map[struct_type]

                    # Find parent (closest ancestor with lower level)
                    parent_level = level - 1
                    while parent_level >= -1:
                        if parent_level in current_parents:
                            parent = current_parents[parent_level]
                            break
                        parent_level -= 1
                    else:
                        parent = root

                    new_node = StructureNode(
                        type=struct_type,
                        number=number,
                        title=title.strip(),
                        content="",
                        level=level,
                        parent=parent,
                        metadata={"line_number": line_num},
                    )

                    # Add to parent
                    parent.children.append(new_node)

                    # Update current_parents
                    current_parents[level] = new_node

                    # Clear higher levels
                    keys_to_remove = [k for k in current_parents.keys() if k > level]
                    for k in keys_to_remove:
                        del current_parents[k]

                    current_node = new_node
                    matched = True
                    break

            # If no match, add to content buffer
            if not matched and line:
                content_buffer.append(line)

        # Save last node's content
        if current_node and content_buffer:
            current_node.content = "\n".join(content_buffer).strip()

        return root

    def get_flat_structure(self, root: StructureNode) -> List[Dict]:
        """Convert tree sang flat list để dễ process"""
        flat_list = []

        def traverse(node: StructureNode):
            if node.type != "root":
                flat_list.append(
                    {
                        "type": node.type,
                        "number": node.number,
                        "title": node.title,
                        "content": node.content,
                        "level": node.level,
                        "hierarchy": node.get_hierarchy_path(),
                        "full_context": node.get_full_context(),
                        "metadata": node.metadata,
                    }
                )

            for child in node.children:
                traverse(child)

        traverse(root)
        return flat_list

    def get_dieu_list(self, root: StructureNode) -> List[Dict]:
        """Extract list tất cả các Điều (quan trọng nhất)"""
        dieu_list = []

        def find_dieu(node: StructureNode):
            if node.type == "dieu":
                dieu_list.append(
                    {
                        "dieu_number": node.number,
                        "dieu_title": node.title,
                        "content": node.content,
                        "hierarchy": node.get_hierarchy_path(),
                        "parent_chuong": self._get_parent_by_type(node, "chuong"),
                        "parent_muc": self._get_parent_by_type(node, "muc"),
                        "parent_phan": self._get_parent_by_type(node, "phan"),
                        "khoan_count": len([c for c in node.children if c.type == "khoan"]),
                    }
                )

            for child in node.children:
                find_dieu(child)

        find_dieu(root)
        return dieu_list

    def _get_parent_by_type(self, node: StructureNode, parent_type: str) -> Optional[str]:
        """Get parent node's number by type"""
        current = node.parent
        while current:
            if current.type == parent_type:
                return f"{parent_type.title()} {current.number}"
            current = current.parent
        return None

    def get_statistics(self, root: StructureNode) -> Dict:
        """Get statistics về cấu trúc văn bản"""
        stats = {
            "phan_count": 0,
            "chuong_count": 0,
            "muc_count": 0,
            "dieu_count": 0,
            "khoan_count": 0,
            "diem_count": 0,
            "total_nodes": 0,
        }

        def count_nodes(node: StructureNode):
            if node.type != "root":
                stats["total_nodes"] += 1
                stats[f"{node.type}_count"] += 1

            for child in node.children:
                count_nodes(child)

        count_nodes(root)
        return stats

    def to_json(self, root: StructureNode) -> Dict:
        """Convert structure tree sang JSON format"""

        def node_to_dict(node: StructureNode) -> Dict:
            return {
                "type": node.type,
                "number": node.number,
                "title": node.title,
                "content": node.content,
                "level": node.level,
                "hierarchy": node.get_hierarchy_path(),
                "metadata": node.metadata,
                "children": [node_to_dict(child) for child in node.children],
            }

        return node_to_dict(root)


# ============ USAGE EXAMPLE ============

if __name__ == "__main__":
    sample_text = """
PHẦN THỨ NHẤT. QUY ĐỊNH CHUNG

CHƯƠNG I. QUY ĐỊNH CHUNG

Điều 1. Phạm vi điều chỉnh

Luật này quy định về đấu thầu, lựa chọn nhà thầu trong hoạt động đầu tư, xây dựng và mua sắm công.

1. Quy định về tổ chức đấu thầu

a) Hình thức lựa chọn nhà thầu

b) Trình tự, thủ tục đấu thầu

2. Quy định về nhà thầu

Điều 2. Đối tượng áp dụng

1. Chủ đầu tư

2. Nhà thầu

CHƯƠNG II. CÁC HÌNH THỨC LỰA CHỌN NHÀ THẦU

Mục 1. Đấu thầu rộng rãi

Điều 3. Điều kiện áp dụng

Đấu thầu rộng rãi được áp dụng trong các trường hợp sau:

1. Gói thầu có giá trị lớn

2. Gói thầu quan trọng
"""

    parser = BiddingLawParser()

    print("=" * 80)
    print("BIDDING LAW STRUCTURE PARSER")
    print("=" * 80)

    # Parse structure
    root = parser.parse(sample_text, metadata={"doc_type": "Luật", "doc_year": "2023"})

    # Get statistics
    stats = parser.get_statistics(root)
    print("\n📊 Structure Statistics:")
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Get flat structure
    flat = parser.get_flat_structure(root)
    print(f"\n📝 Flat structure: {len(flat)} elements")

    # Get Điều list
    dieu_list = parser.get_dieu_list(root)
    print(f"\n⚖️ Found {len(dieu_list)} Điều:")
    for dieu in dieu_list:
        print(f"   Điều {dieu['dieu_number']}: {dieu['dieu_title']}")
        print(f"      Hierarchy: {' → '.join(dieu['hierarchy'])}")
        print(f"      Khoản: {dieu['khoan_count']}")

    # Show full context for first Điều
    if flat:
        first_dieu = [f for f in flat if f["type"] == "dieu"][0]
        print(f"\n📄 Full context example (Điều {first_dieu['number']}):")
        print(first_dieu["full_context"][:300] + "...")
