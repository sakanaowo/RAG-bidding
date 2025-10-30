"""
Circular Metadata Mapper - Map extracted data to DB schema

Maps circular preprocessing output to database schema similar to law/decree mappers.
Handles circular-specific fields and administrative document metadata.
"""

from datetime import datetime
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import re


class CircularMetadataMapper:
    """
    Map circular preprocessing output to database schema
    """

    @staticmethod
    def map_chunk_to_db_schema(
        chunk: Any,
        source_metadata: Dict[str, Any],
        chunk_index: int,
        total_chunks: int,
    ) -> Dict[str, Any]:
        """
        Map single chunk to standardized embedding-ready format

        Args:
            chunk: CircularChunk object from chunker
            source_metadata: Metadata from extraction
            chunk_index: Index of this chunk
            total_chunks: Total number of chunks

        Returns:
            Dictionary with standardized format for embedding pipeline
        """
        # Create standardized chunk structure compatible with embedding pipeline
        result = {
            # Standard fields for embedding
            "id": f"circular_{source_metadata.get('filename', 'unknown').replace('.', '_').replace(' ', '_')}_{chunk_index}",
            "text": chunk.text,
            "metadata": {},
            "embedding_ready": True,
            "processing_stats": {
                "char_count": len(chunk.text),
                "quality_score": 1.0,  # Default quality score
            },
        }

        metadata = result["metadata"]

        # === CORE IDENTIFIERS ===
        metadata["chunk_id"] = chunk_index
        metadata["source"] = source_metadata.get("source", "thuvienphapluat.vn")
        metadata["source_file"] = source_metadata.get("filename", "")
        metadata["url"] = source_metadata.get("url", "")
        metadata["title"] = source_metadata.get("title", "")
        metadata["total_chunks"] = total_chunks
        metadata["doc_type"] = "circular"
        metadata["processed_at"] = datetime.now().isoformat()

        # === STRUCTURE INFO ===
        metadata["chunk_level"] = (
            chunk.level
        )  # 'regulation', 'guidance', 'article', 'clause', 'point'
        metadata["section"] = chunk.metadata.get("section", "")  # Chương, Mục
        metadata["chuong"] = chunk.metadata.get("chuong", "")
        metadata["dieu"] = chunk.metadata.get("dieu", "")
        metadata["khoan"] = chunk.metadata.get("khoan", 0)
        metadata["parent_dieu"] = chunk.metadata.get("parent_dieu", "")

        # Circular-specific structure
        metadata["regulation"] = chunk.metadata.get("regulation", "")
        metadata["guidance"] = chunk.metadata.get("guidance", "")

        # Hierarchy path (e.g., "THÔNG TƯ > Chương 1 > Quy định 2 > Khoản 1")
        metadata["hierarchy"] = CircularMetadataMapper._build_hierarchy_path(
            chunk.metadata
        )

        # === FLAGS ===
        metadata["has_khoan"] = chunk.metadata.get("has_khoan", False)
        metadata["has_diem"] = chunk.metadata.get("has_diem", False)
        metadata["has_regulations"] = chunk.metadata.get("has_regulations", False)
        metadata["has_guidance"] = chunk.metadata.get("has_guidance", False)

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
        metadata["quality_flags"] = CircularMetadataMapper._generate_quality_flags(
            chunk, metadata
        )

        # === STATUS & VALIDITY ===
        year = CircularMetadataMapper._extract_year_from_number(
            source_metadata.get("circular_number", "")
        )
        if year:
            # Circular: 3 years validity (shorter than law)
            valid_until_year = year + 3
            current_year = datetime.now().year
            metadata["status"] = (
                "active" if valid_until_year >= current_year else "expired"
            )
            metadata["valid_until"] = f"{valid_until_year}-12-31"
        else:
            metadata["status"] = "unknown"
            metadata["valid_until"] = ""

        # === CIRCULAR-SPECIFIC METADATA ===
        metadata["circular_number"] = source_metadata.get("circular_number", "")
        metadata["issuing_agency"] = source_metadata.get("issuing_agency", "")
        metadata["issue_date"] = source_metadata.get("issue_date", "")
        metadata["effective_date"] = source_metadata.get("effective_date", "")

        # === TIMESTAMPS ===
        metadata["crawled_at"] = source_metadata.get(
            "crawled_at", datetime.now().isoformat()
        )

        return result

    @staticmethod
    def _build_hierarchy_path(chunk_metadata: Dict[str, Any]) -> str:
        """
        Build hierarchy path string for circular

        Example: "THÔNG TƯ > Chương 1 > Quy định 2 > Khoản 1"
        """
        parts = []

        # Start with document type
        if circular_num := chunk_metadata.get("circular_number"):
            parts.append(f"THÔNG TƯ {circular_num}")
        elif section := chunk_metadata.get("section"):
            parts.append(section)
        else:
            parts.append("THÔNG TƯ")

        # Add structural hierarchy
        if chuong := chunk_metadata.get("chuong"):
            parts.append(f"Chương {chuong}")
        if regulation := chunk_metadata.get("regulation"):
            parts.append(f"Quy định {regulation}")
        if guidance := chunk_metadata.get("guidance"):
            parts.append(f"Hướng dẫn {guidance}")
        if dieu := chunk_metadata.get("dieu"):
            parts.append(f"Điều {dieu}")
        if khoan := chunk_metadata.get("khoan"):
            parts.append(f"Khoản {khoan}")

        return " > ".join(parts) if parts else ""

    @staticmethod
    def _extract_year_from_number(circular_number: str) -> int | None:
        """
        Extract year from circular number

        Example: "15/2023/TT-BTC" → 2023
        """
        if not circular_number:
            return None

        # Pattern: XX/YYYY/TT-XXX
        match = re.search(r"/(\d{4})/", circular_number)
        if match:
            year = int(match.group(1))
            if 1900 <= year <= 2030:
                return year

        # Pattern: XX-YYYY-XXX (alternative format)
        match = re.search(r"-(\d{4})-", circular_number)
        if match:
            year = int(match.group(1))
            if 1900 <= year <= 2030:
                return year

        return None

    @staticmethod
    def _generate_quality_flags(chunk: Any, metadata: Dict[str, Any]) -> List[str]:
        """Generate quality flags for chunk"""
        flags = []

        # Length-based flags
        char_count = metadata["char_count"]
        if char_count < 50:
            flags.append("very_short")
        elif char_count > 5000:
            flags.append("very_long")

        # Content quality flags
        text = chunk.text.lower()

        # Check for incomplete content
        if text.endswith(("...", "…", ".")):
            flags.append("potentially_incomplete")

        # Check for circular-specific terms
        circular_terms = ["quy định", "hướng dẫn", "thông tư", "thi hành", "áp dụng"]
        if not any(term in text for term in circular_terms):
            flags.append("no_circular_terms")

        # Check structure quality
        if not metadata.get("hierarchy"):
            flags.append("no_hierarchy")

        # Check for administrative language quality
        admin_terms = ["cơ quan", "tổ chức", "thực hiện", "áp dụng", "quy định"]
        admin_term_count = sum(1 for term in admin_terms if term in text)
        if admin_term_count < 2:
            flags.append("low_admin_content")

        return flags

    @staticmethod
    def _calculate_readability_score(text: str) -> float:
        """Calculate readability score for circular text"""
        if not text:
            return 0.0

        # Simple readability based on sentence and word complexity
        sentences = text.split(".")
        words = text.split()

        if not sentences or not words:
            return 0.0

        avg_words_per_sentence = len(words) / len(sentences)

        # Circular documents tend to be more complex
        # Score 0-1 where 1 is most readable
        if avg_words_per_sentence <= 15:
            return 1.0
        elif avg_words_per_sentence <= 25:
            return 0.8
        elif avg_words_per_sentence <= 35:
            return 0.6
        else:
            return 0.4

    @staticmethod
    def _extract_semantic_tags(text: str) -> List[str]:
        """Extract semantic tags from circular text"""
        tags = []
        text_lower = text.lower()

        # Implementation tags
        if any(term in text_lower for term in ["thi hành", "thực hiện", "triển khai"]):
            tags.append("implementation")

        # Guidance tags
        if any(term in text_lower for term in ["hướng dẫn", "chỉ dẫn", "hướng dẫn"]):
            tags.append("guidance")

        # Regulation tags
        if any(term in text_lower for term in ["quy định", "quy chế", "quy tắc"]):
            tags.append("regulation")

        # Administrative tags
        if any(term in text_lower for term in ["cơ quan", "bộ", "tổng cục", "cục"]):
            tags.append("administrative")

        # Procedure tags
        if any(term in text_lower for term in ["thủ tục", "quy trình", "trình tự"]):
            tags.append("procedure")

        # Timeline tags
        if any(
            term in text_lower
            for term in ["ngày", "tháng", "năm", "thời hạn", "thời gian"]
        ):
            tags.append("timeline")

        # Bidding-specific tags (since this is a bidding system)
        if any(term in text_lower for term in ["đấu thầu", "nhà thầu", "gói thầu"]):
            tags.append("bidding")

        return tags
