"""
Law Metadata Mapper - Map extracted data to DB schema

DB Schema (25 fields từ notebook):
- char_count, chunk_id, chunk_level, chunking_strategy
- chuong, crawled_at, dieu, has_diem, has_khoan
- hierarchy, is_within_token_limit, khoan
- parent_dieu, quality_flags, readability_score
- section, semantic_tags, source, source_file
- status, structure_score, title
- token_count, token_ratio, url, valid_until
"""

from datetime import datetime
from typing import Dict, Any
import re


class LawMetadataMapper:
    """
    Map law preprocessing output to database schema
    """

    @staticmethod
    def map_chunk_to_db_schema(
        chunk: Any,
        source_metadata: Dict[str, Any],
        chunk_index: int,
        total_chunks: int,
    ) -> Dict[str, Any]:
        """
        Map single chunk to DB schema

        Args:
            chunk: LawChunk object from chunker
            source_metadata: Metadata from extraction
            chunk_index: Index of this chunk
            total_chunks: Total number of chunks

        Returns:
            Dictionary với 25 fields theo DB schema
        """
        metadata = {}

        # === CORE IDENTIFIERS ===
        metadata["chunk_id"] = chunk_index
        metadata["source"] = source_metadata.get("source", "thuvienphapluat.vn")
        metadata["source_file"] = source_metadata.get("filename", "")
        metadata["url"] = source_metadata.get("url", "")
        metadata["title"] = source_metadata.get("title", "")

        # === STRUCTURE INFO ===
        metadata["chunk_level"] = chunk.level  # 'dieu', 'khoan', 'diem'
        metadata["section"] = chunk.metadata.get("section", "")  # Phần, Chương
        metadata["chuong"] = chunk.metadata.get("chuong", "")
        metadata["dieu"] = chunk.metadata.get("dieu", "")
        metadata["khoan"] = chunk.metadata.get("khoan", 0)
        metadata["parent_dieu"] = chunk.metadata.get("parent_dieu", "")

        # Hierarchy path (e.g., "Phần I > Chương 1 > Điều 2 > Khoản 1")
        metadata["hierarchy"] = LawMetadataMapper._build_hierarchy_path(chunk.metadata)

        # === FLAGS ===
        metadata["has_khoan"] = chunk.metadata.get("has_khoan", False)
        metadata["has_diem"] = chunk.metadata.get("has_diem", False)

        # === CHUNKING INFO ===
        metadata["chunking_strategy"] = chunk.metadata.get(
            "chunking_strategy", "optimal_hybrid"
        )
        metadata["char_count"] = len(chunk.text)
        metadata["token_count"] = chunk.metadata.get("token_count", 0)
        metadata["token_ratio"] = chunk.metadata.get("token_ratio", 0.0)
        metadata["is_within_token_limit"] = (
            metadata["token_count"] <= 2000
        )  # Assuming 2000 token limit

        # === QUALITY METRICS ===
        metadata["readability_score"] = chunk.metadata.get("readability_score", 0.0)
        metadata["structure_score"] = chunk.metadata.get("structure_score", 0.0)
        metadata["semantic_tags"] = chunk.metadata.get("semantic_tags", [])
        metadata["quality_flags"] = LawMetadataMapper._generate_quality_flags(
            chunk, metadata
        )

        # === STATUS & VALIDITY ===
        year = LawMetadataMapper._extract_year_from_url(metadata["url"])
        if year:
            # Law: 5 years validity
            valid_until_year = year + 5
            current_year = datetime.now().year
            metadata["status"] = (
                "active" if valid_until_year >= current_year else "expired"
            )
            metadata["valid_until"] = f"{valid_until_year}-12-31"
        else:
            metadata["status"] = "unknown"
            metadata["valid_until"] = ""

        # === TIMESTAMPS ===
        metadata["crawled_at"] = source_metadata.get(
            "created", datetime.now().isoformat()
        )

        return metadata

    @staticmethod
    def _build_hierarchy_path(chunk_metadata: Dict[str, Any]) -> str:
        """
        Build hierarchy path string

        Example: "Phần I > Chương 1 > Điều 2 > Khoản 1"
        """
        parts = []

        if section := chunk_metadata.get("section"):
            parts.append(section)
        if chuong := chunk_metadata.get("chuong"):
            parts.append(f"Chương {chuong}")
        if dieu := chunk_metadata.get("dieu"):
            parts.append(f"Điều {dieu}")
        if khoan := chunk_metadata.get("khoan"):
            parts.append(f"Khoản {khoan}")

        return " > ".join(parts) if parts else ""

    @staticmethod
    def _extract_year_from_url(url: str) -> int | None:
        """
        Extract year from URL

        Example: "Luat-Dau-thau-2023-22-2023-QH15" → 2023
        """
        if not url:
            return None

        # Pattern: Luat-XXX-YYYY-
        match = re.search(r"Luat.*-(\d{4})-", url)
        if match:
            year = int(match.group(1))
            if 1900 <= year <= 2030:
                return year

        # Pattern: -YYYY- (generic)
        match = re.search(r"-(\d{4})-", url)
        if match:
            year = int(match.group(1))
            if 1900 <= year <= 2030:
                return year

        return None

    @staticmethod
    def _generate_quality_flags(chunk: Any, metadata: Dict[str, Any]) -> list[str]:
        """
        Generate quality warning flags

        Returns:
            List of quality issues (empty if all good)
        """
        flags = []

        # Check chunk size
        if metadata["char_count"] < 100:
            flags.append("too_short")
        if metadata["char_count"] > 5000:
            flags.append("too_long")

        # Check token limit
        if not metadata["is_within_token_limit"]:
            flags.append("exceeds_token_limit")

        # Check readability
        if metadata["readability_score"] < 0.3:
            flags.append("low_readability")

        # Check structure
        if not metadata["dieu"]:
            flags.append("missing_dieu")

        return flags

    @staticmethod
    def map_document_metadata(extracted_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map document-level metadata (for full document, not chunks)

        Args:
            extracted_metadata: Metadata from DocxExtractor

        Returns:
            Document-level metadata
        """
        doc_meta = {}

        # Basic info
        doc_meta["title"] = extracted_metadata.get("title", "")
        doc_meta["source"] = "thuvienphapluat.vn"
        doc_meta["source_file"] = extracted_metadata.get("filename", "")
        doc_meta["url"] = extracted_metadata.get("url", "")

        # Document type
        doc_meta["doc_type"] = extracted_metadata.get("doc_type", "law")
        doc_meta["doc_number"] = extracted_metadata.get("doc_number", "")
        doc_meta["doc_year"] = extracted_metadata.get("doc_year", "")

        # Author info
        doc_meta["author"] = extracted_metadata.get("author", "")
        doc_meta["created"] = extracted_metadata.get("created", "")
        doc_meta["modified"] = extracted_metadata.get("modified", "")

        # Statistics
        doc_meta["char_count"] = extracted_metadata.get("char_count", 0)
        doc_meta["word_count"] = extracted_metadata.get("word_count", 0)
        doc_meta["dieu_count"] = extracted_metadata.get("dieu_count", 0)

        return doc_meta
