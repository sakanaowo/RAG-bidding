"""
Bidding Document Parser

Parses Vietnamese bidding document structure and hierarchy.
Handles various bidding document formats and organizational patterns.
"""

import re
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass


@dataclass
class BiddingSection:
    """Represents a section in a bidding document"""

    level: str  # part, chapter, section, article, etc.
    number: str  # section number
    title: str  # section title
    content: str  # section content
    subsections: List["BiddingSection"]
    start_position: int
    end_position: int
    parent_section: Optional[str] = None


class BiddingParser:
    """
    Parser for Vietnamese bidding documents (Hồ sơ mời thầu)
    Extracts document structure, hierarchy, and organizes content
    """

    def __init__(self):
        """Initialize bidding document parser"""

        # Structure hierarchy levels (from highest to lowest)
        self.hierarchy_levels = [
            "part",  # Phần
            "chapter",  # Chương
            "section",  # Mục
            "article",  # Điều
            "clause",  # Khoản
            "point",  # Điểm
            "subpoint",  # Tiểu điểm
        ]

        # Patterns for each hierarchy level
        self.structure_patterns = {
            "part": [
                r"^(PHẦN|Phần)\s+([IVXLCDM]+|\d+)[\.\:]?\s*(.*)$",
                r"^(PART|Part)\s+([IVXLCDM]+|\d+)[\.\:]?\s*(.*)$",
            ],
            "chapter": [
                r"^(CHƯƠNG|Chương)\s+([IVXLCDM]+|\d+)[\.\:]?\s*(.*)$",
                r"^(CHAPTER|Chapter)\s+([IVXLCDM]+|\d+)[\.\:]?\s*(.*)$",
            ],
            "section": [
                r"^(MỤC|Mục)\s+([IVXLCDM]+|\d+)[\.\:]?\s*(.*)$",
                r"^(SECTION|Section)\s+([IVXLCDM]+|\d+)[\.\:]?\s*(.*)$",
                r"^(\d+)[\.\)]?\s+([A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴ][^\.]{10,})$",
            ],
            "article": [
                r"^(ĐIỀU|Điều)\s+(\d+[a-z]?)[\.\:]?\s*(.*)$",
                r"^(ARTICLE|Article)\s+(\d+[a-z]?)[\.\:]?\s*(.*)$",
            ],
            "clause": [
                r"^(\d+)[\.\)]?\s+([A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴ][^\.]{5,})$",
            ],
            "point": [
                r"^([a-zđ])\)\s*(.+)$",
                r"^-\s+([A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴ][^\.]{5,})$",
            ],
            "subpoint": [
                r"^([a-zđ])\.\d+\)\s*(.+)$",
                r"^\*\s+(.+)$",
            ],
        }

        # Special section patterns for bidding documents
        self.bidding_sections = {
            "general_info": [
                r"thông\s*tin\s*chung",
                r"general\s*information",
                r"^I\.\s*thông\s*tin",
            ],
            "technical_requirements": [
                r"yêu\s*cầu\s*kỹ\s*thuật",
                r"technical\s*requirements",
                r"thông\s*số\s*kỹ\s*thuật",
                r"specification",
            ],
            "evaluation_criteria": [
                r"tiêu\s*chí\s*đánh\s*giá",
                r"evaluation\s*criteria",
                r"phương\s*pháp\s*đánh\s*giá",
            ],
            "contract_conditions": [
                r"điều\s*kiện\s*hợp\s*đồng",
                r"contract\s*conditions",
                r"điều\s*khoản\s*hợp\s*đồng",
            ],
            "bidding_process": [
                r"quy\s*trình\s*đấu\s*thầu",
                r"bidding\s*process",
                r"thủ\s*tục\s*dự\s*thầu",
            ],
            "forms": [
                r"biểu\s*mẫu",
                r"forms",
                r"mẫu\s*đơn",
                r"appendix",
                r"phụ\s*lục",
            ],
            "drawings": [
                r"bản\s*vẽ",
                r"drawings",
                r"sơ\s*đồ",
                r"thiết\s*kế",
            ],
            "bill_of_quantities": [
                r"bảng\s*khối\s*lượng",
                r"bill\s*of\s*quantities",
                r"BOQ",
                r"danh\s*mục\s*khối\s*lượng",
            ],
        }

        # Table detection patterns
        self.table_patterns = [
            r"^\|.*\|$",  # Markdown-style table
            r"^\+[-+\s]+\+$",  # ASCII table border
            r"^\s*\d+\s*[\|\t]\s*.*[\|\t]",  # Numbered table rows
            r"TT|STT|Số\s*TT",  # Vietnamese table headers
        ]

    def parse(self, text: str, bidding_type: str = None) -> Dict[str, Any]:
        """
        Parse bidding document text into structured format

        Args:
            text: Text to parse
            bidding_type: Type of bidding document for specialized parsing

        Returns:
            Dictionary with parsed structure
        """
        if not text or not text.strip():
            return {"sections": [], "tables": [], "metadata": {}, "structure_stats": {}}

        # Step 1: Detect and extract tables
        tables = self._extract_tables(text)

        # Step 2: Parse document structure
        sections = self._parse_structure(text, bidding_type)

        # Step 3: Extract metadata
        metadata = self._extract_metadata(text, sections, bidding_type)

        # Step 4: Generate structure statistics
        structure_stats = self._generate_structure_stats(sections, tables)

        return {
            "sections": [self._section_to_dict(section) for section in sections],
            "tables": tables,
            "metadata": metadata,
            "structure_stats": structure_stats,
        }

    def _parse_structure(
        self, text: str, bidding_type: str = None
    ) -> List[BiddingSection]:
        """Parse document structure into hierarchical sections"""
        lines = text.split("\n")
        sections = []
        current_sections = {}  # Track current section at each level

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Try to match against structure patterns
            section_info = self._match_structure_pattern(line)

            if section_info:
                level, number, title = section_info

                # Find content for this section
                content_start = i + 1
                content_end = self._find_section_end(lines, content_start, level)
                content_lines = lines[content_start:content_end]
                content = "\n".join(content_lines).strip()

                # Create section
                section = BiddingSection(
                    level=level,
                    number=number,
                    title=title,
                    content=content,
                    subsections=[],
                    start_position=i,
                    end_position=content_end,
                    parent_section=self._find_parent_section(current_sections, level),
                )

                # Update current sections
                level_index = self.hierarchy_levels.index(level)
                current_sections[level] = section

                # Clear lower level sections
                for lower_level in self.hierarchy_levels[level_index + 1 :]:
                    current_sections.pop(lower_level, None)

                # Add to appropriate parent or root
                parent_level = self._get_parent_level(level)
                if parent_level and parent_level in current_sections:
                    current_sections[parent_level].subsections.append(section)
                else:
                    sections.append(section)

        return sections

    def _match_structure_pattern(self, line: str) -> Optional[Tuple[str, str, str]]:
        """Match line against structure patterns"""
        for level, patterns in self.structure_patterns.items():
            for pattern in patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    groups = match.groups()
                    if len(groups) >= 3:
                        return level, groups[1], groups[2].strip()
                    elif len(groups) == 2:
                        return level, groups[0], groups[1].strip()

        return None

    def _find_section_end(
        self, lines: List[str], start: int, current_level: str
    ) -> int:
        """Find the end position of a section"""
        current_level_index = self.hierarchy_levels.index(current_level)

        for i in range(start, len(lines)):
            line = lines[i].strip()
            if not line:
                continue

            section_info = self._match_structure_pattern(line)
            if section_info:
                section_level = section_info[0]
                section_level_index = self.hierarchy_levels.index(section_level)

                # If we found a section at the same or higher level, stop here
                if section_level_index <= current_level_index:
                    return i

        return len(lines)

    def _find_parent_section(
        self, current_sections: Dict[str, BiddingSection], level: str
    ) -> Optional[str]:
        """Find the parent section for a given level"""
        level_index = self.hierarchy_levels.index(level)

        for i in range(level_index - 1, -1, -1):
            parent_level = self.hierarchy_levels[i]
            if parent_level in current_sections:
                return current_sections[parent_level].number

        return None

    def _get_parent_level(self, level: str) -> Optional[str]:
        """Get the parent level for a given level"""
        level_index = self.hierarchy_levels.index(level)
        if level_index > 0:
            return self.hierarchy_levels[level_index - 1]
        return None

    def _extract_tables(self, text: str) -> List[Dict[str, Any]]:
        """Extract tables from text"""
        tables = []
        lines = text.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Check if this line starts a table
            if self._is_table_line(line):
                table_start = i
                table_end = self._find_table_end(lines, i)

                if table_end > table_start:
                    table_lines = lines[table_start:table_end]
                    table_content = "\n".join(table_lines)

                    table = {
                        "start_line": table_start,
                        "end_line": table_end,
                        "content": table_content,
                        "type": self._detect_table_type(table_content),
                        "rows": self._parse_table_rows(table_lines),
                    }

                    tables.append(table)
                    i = table_end
                else:
                    i += 1
            else:
                i += 1

        return tables

    def _is_table_line(self, line: str) -> bool:
        """Check if a line is part of a table"""
        for pattern in self.table_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        return False

    def _find_table_end(self, lines: List[str], start: int) -> int:
        """Find the end of a table"""
        for i in range(start + 1, len(lines)):
            line = lines[i].strip()
            if not line:
                # Check next non-empty line
                for j in range(i + 1, min(i + 3, len(lines))):
                    if lines[j].strip() and not self._is_table_line(lines[j]):
                        return i
            elif not self._is_table_line(line):
                return i

        return len(lines)

    def _detect_table_type(self, table_content: str) -> str:
        """Detect the type of table"""
        content_lower = table_content.lower()

        if any(
            keyword in content_lower for keyword in ["khối lượng", "quantities", "boq"]
        ):
            return "bill_of_quantities"
        elif any(keyword in content_lower for keyword in ["giá", "price", "cost"]):
            return "pricing"
        elif any(
            keyword in content_lower for keyword in ["tiêu chí", "criteria", "đánh giá"]
        ):
            return "evaluation"
        elif any(
            keyword in content_lower
            for keyword in ["kỹ thuật", "technical", "thông số"]
        ):
            return "technical"
        else:
            return "general"

    def _parse_table_rows(self, table_lines: List[str]) -> List[List[str]]:
        """Parse table rows into structured format"""
        rows = []

        for line in table_lines:
            line = line.strip()
            if not line:
                continue

            # Try different separators
            if "|" in line:
                cells = [cell.strip() for cell in line.split("|") if cell.strip()]
            elif "\t" in line:
                cells = [cell.strip() for cell in line.split("\t") if cell.strip()]
            else:
                # Try to split on multiple spaces
                cells = re.split(r"\s{2,}", line)

            if cells and len(cells) > 1:
                rows.append(cells)

        return rows

    def _extract_metadata(
        self, text: str, sections: List[BiddingSection], bidding_type: str = None
    ) -> Dict[str, Any]:
        """Extract metadata from parsed document"""
        metadata = {
            "bidding_type": bidding_type,
            "detected_sections": {},
            "document_info": {},
            "statistics": {},
        }

        # Detect special bidding sections
        for section_type, patterns in self.bidding_sections.items():
            found_sections = []
            for section in sections:
                section_text = f"{section.title} {section.content}".lower()
                for pattern in patterns:
                    if re.search(pattern, section_text, re.IGNORECASE):
                        found_sections.append(
                            {
                                "level": section.level,
                                "number": section.number,
                                "title": section.title,
                            }
                        )
                        break
            metadata["detected_sections"][section_type] = found_sections

        # Extract document information
        text_lower = text.lower()

        # Extract project information
        project_match = re.search(r"(dự án|project)[\s:]*([^\n]{10,100})", text_lower)
        if project_match:
            metadata["document_info"]["project_name"] = project_match.group(2).strip()

        # Extract contract information
        contract_match = re.search(
            r"(gói thầu|package)[\s:]*([^\n]{10,100})", text_lower
        )
        if contract_match:
            metadata["document_info"]["package_name"] = contract_match.group(2).strip()

        # Extract owner information
        owner_match = re.search(r"(chủ đầu tư|owner)[\s:]*([^\n]{10,100})", text_lower)
        if owner_match:
            metadata["document_info"]["owner"] = owner_match.group(2).strip()

        return metadata

    def _generate_structure_stats(
        self, sections: List[BiddingSection], tables: List[Dict]
    ) -> Dict[str, Any]:
        """Generate statistics about document structure"""
        stats = {
            "total_sections": len(sections),
            "sections_by_level": {},
            "total_tables": len(tables),
            "tables_by_type": {},
            "max_depth": 0,
            "avg_section_length": 0,
        }

        # Count sections by level
        for section in sections:
            level = section.level
            stats["sections_by_level"][level] = (
                stats["sections_by_level"].get(level, 0) + 1
            )

        # Count tables by type
        for table in tables:
            table_type = table.get("type", "unknown")
            stats["tables_by_type"][table_type] = (
                stats["tables_by_type"].get(table_type, 0) + 1
            )

        # Calculate depth and average length
        if sections:
            depths = []
            lengths = []

            def calculate_depth(section_list, current_depth=1):
                max_depth = current_depth
                for section in section_list:
                    depths.append(current_depth)
                    lengths.append(len(section.content))
                    if section.subsections:
                        subsection_depth = calculate_depth(
                            section.subsections, current_depth + 1
                        )
                        max_depth = max(max_depth, subsection_depth)
                return max_depth

            stats["max_depth"] = calculate_depth(sections)
            stats["avg_section_length"] = sum(lengths) / len(lengths) if lengths else 0

        return stats

    def _section_to_dict(self, section: BiddingSection) -> Dict[str, Any]:
        """Convert BiddingSection to dictionary"""
        return {
            "level": section.level,
            "number": section.number,
            "title": section.title,
            "content": section.content,
            "subsections": [self._section_to_dict(sub) for sub in section.subsections],
            "start_position": section.start_position,
            "end_position": section.end_position,
            "parent_section": section.parent_section,
        }

    def get_section_by_path(
        self, sections: List[BiddingSection], path: List[str]
    ) -> Optional[BiddingSection]:
        """
        Get a section by its hierarchical path

        Args:
            sections: List of sections to search
            path: List of section numbers representing the path

        Returns:
            BiddingSection if found, None otherwise
        """
        if not path:
            return None

        current_sections = sections
        current_section = None

        for section_number in path:
            found = False
            for section in current_sections:
                if section.number == section_number:
                    current_section = section
                    current_sections = section.subsections
                    found = True
                    break

            if not found:
                return None

        return current_section
