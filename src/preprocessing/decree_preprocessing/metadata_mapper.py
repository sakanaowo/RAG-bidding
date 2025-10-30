"""
Decree Metadata Mapper - Map decree chunks to DB schema

25 required DB fields với decree-specific logic:
- Validity period: 2 years (vs 5 years for laws)
- Status: Based on year extraction
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path


class DecreeMetadataMapper:
    """
    Map decree chunks to 25-field DB schema

    Decree-specific logic:
    - 2-year validity period
    - Auto-detect status from year
    """

    # 25 required DB fields
    REQUIRED_FIELDS = [
        "chunk_id",
        "content",
        "doc_id",
        "doc_type",
        "doc_number",
        "doc_year",
        "doc_name",
        "issuing_agency",
        "effective_date",
        "status",
        "source_url",
        "hierarchy_path",
        "parent_id",
        "parent_type",
        "section_title",
        "section_number",
        "chunk_index",
        "total_chunks",
        "original_length",
        "cleaned_length",
        "has_tables",
        "confidence_score",
        "processing_timestamp",
        "metadata_version",
        "related_docs",
    ]

    def __init__(self):
        """Initialize mapper"""
        self.validity_years = 2  # Nghị định có hiệu lực 2 năm
        print(
            f"✅ DecreeMetadataMapper initialized (validity: {self.validity_years} years)"
        )

    def map_chunk_to_db(
        self,
        chunk_text: str,
        chunk_index: int,
        total_chunks: int,
        file_metadata: Dict,
        hierarchy_path: str = "",
        parent_info: Optional[Dict] = None,
    ) -> Dict:
        """
        Map single chunk to 25-field DB schema

        Args:
            chunk_text: Chunk content
            chunk_index: Chunk index (0-based)
            total_chunks: Total number of chunks
            file_metadata: Metadata từ extractor
            hierarchy_path: Path trong structure tree
            parent_info: Info về parent node

        Returns:
            Dictionary với 25 DB fields
        """
        # Extract doc info
        doc_number, doc_year = self._extract_doc_info(file_metadata)
        effective_date = self._extract_effective_date(file_metadata, doc_year)
        status = self._determine_status(doc_year)

        # Generate unique chunk_id
        doc_id = f"decree_{doc_number}_{doc_year}"
        chunk_id = f"{doc_id}_chunk_{chunk_index:04d}"

        # Parent info
        parent_id = parent_info.get("id", "") if parent_info else ""
        parent_type = parent_info.get("type", "") if parent_info else ""
        section_title = parent_info.get("title", "") if parent_info else ""
        section_number = parent_info.get("number", "") if parent_info else ""

        # Build 25-field record
        db_record = {
            # Core fields
            "chunk_id": chunk_id,
            "content": chunk_text.strip(),
            "doc_id": doc_id,
            "doc_type": "decree",
            "doc_number": doc_number,
            "doc_year": str(doc_year),
            "doc_name": file_metadata.get(
                "title", f"Nghị định {doc_number}/{doc_year}"
            ),
            # Legal metadata
            "issuing_agency": file_metadata.get("agency", "Chính phủ"),
            "effective_date": effective_date,
            "status": status,
            "source_url": file_metadata.get("source_url", ""),
            # Structure metadata
            "hierarchy_path": hierarchy_path,
            "parent_id": parent_id,
            "parent_type": parent_type,
            "section_title": section_title,
            "section_number": section_number,
            # Chunk metadata
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
            "original_length": len(chunk_text),
            "cleaned_length": len(chunk_text.strip()),
            "has_tables": file_metadata.get("has_tables", False),
            # Quality metadata
            "confidence_score": self._calculate_confidence(chunk_text),
            "processing_timestamp": datetime.now().isoformat(),
            "metadata_version": "2.0",
            "related_docs": file_metadata.get("related_docs", []),
        }

        return db_record

    def _extract_doc_info(self, metadata: Dict) -> tuple:
        """
        Extract decree number and year

        Returns:
            (doc_number, doc_year)
        """
        # Try from metadata
        if "doc_number" in metadata and "doc_year" in metadata:
            doc_num = metadata["doc_number"]
            doc_year = metadata["doc_year"]

            # Handle empty strings
            if doc_num and doc_year:
                try:
                    return str(doc_num), int(doc_year)
                except (ValueError, TypeError):
                    pass

        # Parse from title or filename
        title = metadata.get("title", "")
        filename = metadata.get("filename", "")

        # Pattern: "Nghị định 214/2025/NĐ-CP"
        for text in [title, filename]:
            if match := re.search(r"(\d+)/(\d{4})", text):
                return match.group(1), int(match.group(2))

            # Pattern: "ND 214 - 4.8.2025"
            if match := re.search(r"ND\s*(\d+).*?(\d{4})", text, re.IGNORECASE):
                return match.group(1), int(match.group(2))

        return "unknown", datetime.now().year

    def _extract_effective_date(self, metadata: Dict, doc_year: int) -> str:
        """
        Extract hoặc estimate effective date

        Returns:
            ISO format date string
        """
        # Try from metadata
        if "effective_date" in metadata:
            return metadata["effective_date"]

        # Estimate: Usually Jan 1 of doc_year
        estimated_date = datetime(doc_year, 1, 1)
        return estimated_date.isoformat()

    def _determine_status(self, doc_year: int) -> str:
        """
        Determine decree status based on year

        Nghị định có hiệu lực 2 năm

        Returns:
            "active" or "expired"
        """
        current_year = datetime.now().year
        years_since_issue = current_year - doc_year

        if years_since_issue <= self.validity_years:
            return "active"
        else:
            return "expired"

    def _calculate_confidence(self, text: str) -> float:
        """
        Calculate confidence score cho chunk quality

        Returns:
            Score from 0.0 to 1.0
        """
        score = 1.0

        # Penalize very short chunks
        if len(text.strip()) < 50:
            score -= 0.3

        # Penalize chunks with too many special chars
        special_chars = len(re.findall(r"[^\w\s\u00C0-\u1EF9]", text))
        if special_chars > len(text) * 0.3:
            score -= 0.2

        # Reward chunks with proper structure markers
        if any(marker in text for marker in ["Điều", "Khoản", "Chương"]):
            score += 0.1

        return max(0.0, min(1.0, score))

    def validate_record(self, record: Dict) -> bool:
        """
        Validate that record has all 25 required fields

        Returns:
            True if valid
        """
        missing = [field for field in self.REQUIRED_FIELDS if field not in record]

        if missing:
            print(f"❌ Missing fields: {missing}")
            return False

        return True

    def map_batch(
        self,
        chunks: List[str],
        file_metadata: Dict,
        hierarchy_paths: List[str] = None,
        parent_infos: List[Dict] = None,
    ) -> List[Dict]:
        """
        Map multiple chunks to DB records

        Args:
            chunks: List of chunk texts
            file_metadata: Metadata cho toàn bộ file
            hierarchy_paths: Optional hierarchy paths per chunk
            parent_infos: Optional parent info per chunk

        Returns:
            List of DB records (25 fields each)
        """
        total = len(chunks)
        records = []

        for i, chunk in enumerate(chunks):
            path = hierarchy_paths[i] if hierarchy_paths else ""
            parent = parent_infos[i] if parent_infos else None

            record = self.map_chunk_to_db(
                chunk_text=chunk,
                chunk_index=i,
                total_chunks=total,
                file_metadata=file_metadata,
                hierarchy_path=path,
                parent_info=parent,
            )

            if self.validate_record(record):
                records.append(record)
            else:
                print(f"⚠️  Skipping invalid chunk {i}")

        return records
