"""
Base Parser - Abstract class cho structure parsing
"""

from abc import ABC, abstractmethod
from typing import Any
from dataclasses import dataclass


@dataclass
class StructureNode:
    """
    Generic tree node cho hierarchical structures
    """

    type: str  # e.g., 'phan', 'chuong', 'dieu', 'khoan'
    level: str  # hierarchical level
    number: str = ""  # e.g., '1', '2.1', 'a'
    title: str = ""
    content: str = ""
    children: list["StructureNode"] = None
    metadata: dict = None

    def __post_init__(self):
        if self.children is None:
            self.children = []
        if self.metadata is None:
            self.metadata = {}

    def add_child(self, child: "StructureNode"):
        """Add child node"""
        self.children.append(child)

    def count_nodes(self) -> int:
        """Count total nodes in tree"""
        count = 1
        for child in self.children:
            count += child.count_nodes()
        return count

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "type": self.type,
            "level": self.level,
            "number": self.number,
            "title": self.title,
            "content": self.content,
            "children": [child.to_dict() for child in self.children],
            "metadata": self.metadata,
        }


class BaseParser(ABC):
    """
    Abstract base class cho document structure parsers
    """

    @abstractmethod
    def parse(self, text: str) -> StructureNode:
        """
        Parse text into hierarchical structure

        Args:
            text: Cleaned text to parse

        Returns:
            Root StructureNode of parsed tree

        Raises:
            ValueError: Invalid text structure
        """
        pass

    @abstractmethod
    def get_structure_levels(self) -> list[str]:
        """
        Get list of structure levels supported

        Returns:
            List of levels (e.g., ['phan', 'chuong', 'dieu', 'khoan'])
        """
        pass

    @abstractmethod
    def validate_structure(self, root: StructureNode) -> tuple[bool, list[str]]:
        """
        Validate parsed structure

        Args:
            root: Root node to validate

        Returns:
            (is_valid, list_of_warnings)
        """
        pass
