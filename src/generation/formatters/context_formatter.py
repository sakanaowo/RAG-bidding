#!/usr/bin/env python3
"""
Context Formatter for RAG System
Formats retrieved documents with hierarchy information for LLM context.
"""
import json
from typing import List, Optional, Dict, Any
from langchain_core.documents import Document


class ContextFormatter:
    """Format retrieved documents with hierarchy and metadata for LLM."""

    def __init__(
        self,
        include_hierarchy: bool = True,
        include_metadata: bool = True,
        max_chars_per_chunk: Optional[int] = None,
    ):
        """
        Initialize context formatter.

        Args:
            include_hierarchy: Include hierarchy path in formatted context
            include_metadata: Include metadata (type, level, section) in formatted context
            max_chars_per_chunk: Maximum characters per chunk (for truncation)
        """
        self.include_hierarchy = include_hierarchy
        self.include_metadata = include_metadata
        self.max_chars_per_chunk = max_chars_per_chunk

    def format_document(self, doc: Document) -> str:
        """
        Format a single document with metadata and hierarchy.

        Args:
            doc: LangChain Document with metadata

        Returns:
            Formatted string with header and content
        """
        metadata = doc.metadata
        content = doc.page_content

        # Build header components
        header_parts = []

        # 1. Document type
        doc_type = metadata.get("document_type", "unknown")
        doc_type_display = self._format_document_type(doc_type)
        header_parts.append(f"[{doc_type_display}]")

        # 2. Document ID or title
        doc_id = metadata.get("document_id", "")
        if doc_id:
            # Clean up document ID for display
            doc_title = self._clean_document_id(doc_id)
            header_parts.append(doc_title)

        # 3. Hierarchy path (if available and enabled)
        if self.include_hierarchy:
            hierarchy = self._parse_hierarchy(metadata.get("hierarchy", "[]"))
            if hierarchy:
                hierarchy_path = " > ".join(hierarchy)
                header_parts.append(hierarchy_path)

        # 4. Section title (if available)
        section_title = metadata.get("section_title", "").strip()
        if section_title and section_title not in ["", "N/A"]:
            # Only add if not already in hierarchy
            if not self.include_hierarchy or section_title not in str(header_parts):
                header_parts.append(section_title)

        # 5. Level indicator (if metadata enabled)
        if self.include_metadata:
            level = metadata.get("level", "")
            if level:
                level_display = self._format_level(level)
                header_parts.append(f"({level_display})")

        # Build final header
        header = " ".join(header_parts)

        # Truncate content if needed
        if self.max_chars_per_chunk and len(content) > self.max_chars_per_chunk:
            content = content[: self.max_chars_per_chunk] + "..."

        # Format output
        formatted = f"{header}\n\n{content}"

        return formatted

    def format_context(
        self,
        docs: List[Document],
        query: Optional[str] = None,
        add_instructions: bool = False,
    ) -> str:
        """
        Format multiple documents into LLM context.

        Args:
            docs: List of retrieved documents
            query: Original user query (optional, for context)
            add_instructions: Add instructions for LLM at the top

        Returns:
            Formatted context string ready for LLM
        """
        parts = []

        # Add query context (optional)
        if query:
            parts.append(f"Question: {query}\n")

        # Add instructions (optional)
        if add_instructions:
            instructions = self._get_instructions()
            parts.append(instructions)

        # Add documents
        if docs:
            parts.append("Relevant Documents:\n")

            for i, doc in enumerate(docs, 1):
                formatted_doc = self.format_document(doc)
                parts.append(f"[Document {i}]")
                parts.append(formatted_doc)
                parts.append("")  # Empty line separator

        return "\n".join(parts)

    def _parse_hierarchy(self, hierarchy_json: str) -> List[str]:
        """Parse hierarchy from JSON string."""
        try:
            if isinstance(hierarchy_json, str):
                hierarchy = json.loads(hierarchy_json)
            else:
                hierarchy = hierarchy_json

            if isinstance(hierarchy, list):
                return [str(h) for h in hierarchy if h]
            return []
        except:
            return []

    def _format_document_type(self, doc_type: str) -> str:
        """Format document type for display."""
        type_mapping = {
            "law": "Luật",
            "decree": "Nghị định",
            "circular": "Thông tư",
            "decision": "Quyết định",
            "bidding": "Hồ sơ mời thầu",
        }
        return type_mapping.get(doc_type.lower(), doc_type.title())

    def _format_level(self, level: str) -> str:
        """Format level for display."""
        level_mapping = {
            "dieu": "Điều",
            "khoan": "Khoản",
            "diem": "Điểm",
            "section": "Mục",
            "form": "Biểu mẫu",
            "phan": "Phần",
            "chuong": "Chương",
            "muc": "Mục",
        }
        return level_mapping.get(level.lower(), level.title())

    def _clean_document_id(self, doc_id: str) -> str:
        """Clean document ID for display."""
        # Remove common prefixes
        doc_id = (
            doc_id.replace("law_", "").replace("decree_", "").replace("circular_", "")
        )
        doc_id = doc_id.replace("decision_", "").replace("bidding_", "")
        doc_id = doc_id.replace("untitled", "Văn bản")

        # Replace underscores with spaces
        doc_id = doc_id.replace("_", " ")

        return doc_id.strip()

    def _get_instructions(self) -> str:
        """Get LLM instructions."""
        return """Instructions: Answer the question based on the provided documents. 
Use the hierarchy information to understand the context and structure of the legal documents.
Cite specific articles (Điều), clauses (Khoản), or sections when relevant.

"""


def format_context_with_hierarchy(
    docs: List[Document],
    query: Optional[str] = None,
    include_instructions: bool = False,
) -> str:
    """
    Convenience function to format context with default settings.

    Args:
        docs: Retrieved documents
        query: User query (optional)
        include_instructions: Add LLM instructions

    Returns:
        Formatted context string
    """
    formatter = ContextFormatter(
        include_hierarchy=True,
        include_metadata=True,
        max_chars_per_chunk=None,  # No truncation
    )

    return formatter.format_context(
        docs, query=query, add_instructions=include_instructions
    )


# Example usage
if __name__ == "__main__":
    # Example document
    from langchain_core.documents import Document

    example_doc = Document(
        page_content="Nhà thầu tham dự thầu phải đáp ứng các điều kiện về năng lực và kinh nghiệm theo quy định...",
        metadata={
            "chunk_id": "law_untitled_khoan_0047",
            "document_id": "law_luat_dau_thau_2023",
            "document_type": "law",
            "hierarchy": '["Điều 5", "Khoản 2"]',
            "level": "khoan",
            "section_title": "Tư cách hợp lệ của nhà thầu",
        },
    )

    # Test formatting
    formatter = ContextFormatter()

    print("=" * 80)
    print("SINGLE DOCUMENT FORMATTING")
    print("=" * 80)
    formatted = formatter.format_document(example_doc)
    print(formatted)

    print("\n" + "=" * 80)
    print("CONTEXT FORMATTING (with query)")
    print("=" * 80)
    context = format_context_with_hierarchy(
        [example_doc],
        query="Điều kiện tham gia đấu thầu là gì?",
        include_instructions=True,
    )
    print(context)
