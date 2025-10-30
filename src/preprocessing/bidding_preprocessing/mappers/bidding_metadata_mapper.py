"""
Bidding Document Metadata Mapper

Maps processed bidding document chunks to standardized metadata format.
Handles document structure, hierarchy, and bidding-specific information.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import re


class BiddingMetadataMapper:
    """
    Maps bidding document chunks to standardized metadata format

    Extracts and standardizes:
    - Document hierarchy and structure
    - Bidding-specific information
    - Project and contract details
    - Section relationships
    """

    def __init__(self):
        """Initialize bidding metadata mapper"""

        # Bidding document types and their indicators
        self.bidding_types = {
            "construction": ["xây dựng", "construction", "công trình"],
            "goods": ["mua sắm", "hàng hóa", "goods", "thiết bị"],
            "services": ["dịch vụ", "services", "tư vấn"],
            "mixed": ["hỗn hợp", "mixed", "kết hợp"],
            "epc": ["EPC", "thiết kế", "cung cấp", "lắp đặt"],
            "maintenance": ["bảo trì", "maintenance", "duy tu"],
            "supply": ["cung cấp", "supply", "phân phối"],
        }

        # Section type patterns
        self.section_types = {
            "general_info": ["thông tin chung", "general information"],
            "scope_of_work": [
                "phạm vi công việc",
                "scope of work",
                "nội dung công việc",
            ],
            "technical_specs": [
                "yêu cầu kỹ thuật",
                "technical requirements",
                "thông số kỹ thuật",
            ],
            "evaluation": ["đánh giá", "evaluation", "tiêu chí"],
            "contract_terms": [
                "điều kiện hợp đồng",
                "contract conditions",
                "điều khoản",
            ],
            "forms": ["biểu mẫu", "forms", "mẫu đơn"],
            "appendix": ["phụ lục", "appendix", "attachment"],
            "drawings": ["bản vẽ", "drawings", "sơ đồ"],
            "boq": ["khối lượng", "quantities", "BOQ"],
        }

        # Key entity patterns
        self.entity_patterns = {
            "project_name": [
                r"(dự án|project)[\s:]*([^\n]{10,150})",
                r"tên\s*dự\s*án[\s:]*([^\n]{10,150})",
            ],
            "package_name": [
                r"(gói thầu|package)[\s:]*([^\n]{10,150})",
                r"tên\s*gói\s*thầu[\s:]*([^\n]{10,150})",
            ],
            "owner": [
                r"(chủ đầu tư|owner)[\s:]*([^\n]{10,150})",
                r"bên\s*mời\s*thầu[\s:]*([^\n]{10,150})",
            ],
            "contract_value": [
                r"giá\s*trị\s*hợp\s*đồng[\s:]*([^\n]{5,50})",
                r"contract\s*value[\s:]*([^\n]{5,50})",
            ],
            "duration": [
                r"thời\s*gian\s*thực\s*hiện[\s:]*([^\n]{5,50})",
                r"duration[\s:]*([^\n]{5,50})",
            ],
        }

    def map_chunks(
        self, chunks: List[Dict[str, Any]], document_metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Map list of chunks with bidding-specific metadata

        Args:
            chunks: List of processed chunks
            document_metadata: Optional document-level metadata

        Returns:
            List of chunks with standardized metadata
        """
        if not chunks:
            return []

        mapped_chunks = []

        # Extract document-level information
        doc_info = self._extract_document_info(chunks, document_metadata)

        for i, chunk in enumerate(chunks):
            mapped_chunk = self._map_single_chunk(chunk, i, doc_info)
            mapped_chunks.append(mapped_chunk)

        return mapped_chunks

    def _map_single_chunk(
        self, chunk: Dict[str, Any], index: int, doc_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Map a single chunk with bidding metadata to standardized format"""

        # Create standardized chunk structure compatible with embedding pipeline
        mapped_chunk = {
            # Standard fields for embedding
            "id": f"bidding_{doc_info.get('source_file', 'unknown').replace('.', '_').replace(' ', '_')}_{index}",
            "text": chunk.get("content", ""),
            "metadata": {},
            "embedding_ready": True,
            "processing_stats": {
                "char_count": chunk.get("char_count", len(chunk.get("content", ""))),
                "quality_score": 1.0,  # Default quality score
            },
        }

        metadata = mapped_chunk["metadata"]

        # Core metadata
        metadata.update(
            {
                "doc_type": "bidding",
                "chunk_index": index,
                "processed_at": datetime.now().isoformat(),
                "total_chunks": 1,  # Will be updated by pipeline
                "chunking_strategy": "simple_bidding",
            }
        )

        # Document information
        metadata.update(doc_info)

        # Extract hierarchy
        hierarchy = self._extract_hierarchy(chunk)
        if hierarchy:
            metadata["hierarchy"] = hierarchy

        # Extract section information
        section_info = self._extract_section_info(chunk)
        metadata.update(section_info)

        # Extract bidding-specific metadata
        bidding_meta = self._extract_bidding_metadata(chunk)
        metadata.update(bidding_meta)

        # Extract entities
        entities = self._extract_entities(chunk)
        if entities:
            metadata["entities"] = entities

        # Content statistics
        content_stats = self._calculate_content_stats(chunk)
        metadata["content_stats"] = content_stats

        # Add original chunk fields that might be useful
        if chunk.get("chunk_id"):
            metadata["original_chunk_id"] = chunk["chunk_id"]
        if chunk.get("level"):
            metadata["level"] = chunk["level"]
        if chunk.get("hierarchy"):
            metadata["original_hierarchy"] = chunk["hierarchy"]

        return mapped_chunk

    def _extract_document_info(
        self, chunks: List[Dict[str, Any]], document_metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Extract document-level information"""
        doc_info = {
            "total_chunks": len(chunks),
            "document_type": "bidding_document",
        }

        # Add provided document metadata
        if document_metadata:
            doc_info.update(document_metadata)

        # Extract information from first chunk or aggregate
        all_content = " ".join(
            [chunk.get("content", "") for chunk in chunks[:5]]
        )  # First 5 chunks

        # Extract key document entities
        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, all_content, re.IGNORECASE)
                if match:
                    if len(match.groups()) >= 2:
                        doc_info[entity_type] = match.group(2).strip()
                    else:
                        doc_info[entity_type] = match.group(1).strip()
                    break

        # Detect bidding type
        bidding_type = self._detect_bidding_type(all_content)
        if bidding_type:
            doc_info["bidding_type"] = bidding_type

        return doc_info

    def _extract_hierarchy(self, chunk: Dict[str, Any]) -> Optional[str]:
        """Extract hierarchy path from chunk"""

        # Check if already exists
        if isinstance(chunk.get("metadata"), dict):
            existing_hierarchy = chunk["metadata"].get("hierarchy")
            if existing_hierarchy:
                return existing_hierarchy

        # Try to build from parsed sections (if available)
        if "parsed_sections" in chunk:
            sections = chunk["parsed_sections"]
            if sections:
                hierarchy_parts = []

                # Build hierarchy from section structure
                def build_hierarchy(section_list, prefix="HỒ SƠ MỜI THẦU"):
                    parts = [prefix] if prefix else []
                    for section in section_list:
                        if section.get("level") and section.get("number"):
                            level_name = self._get_level_name(section["level"])
                            parts.append(f"{level_name} {section['number']}")
                        if section.get("title"):
                            parts.append(section["title"][:50])  # Truncate long titles
                        break  # Only take first section for hierarchy
                    return parts

                hierarchy_parts = build_hierarchy(sections)
                return " > ".join(hierarchy_parts)

        # Try to extract from content
        content = chunk.get("content", "")
        if content:
            return self._extract_hierarchy_from_content(content)

        return None

    def _get_level_name(self, level: str) -> str:
        """Get Vietnamese name for hierarchy level"""
        level_names = {
            "part": "Phần",
            "chapter": "Chương",
            "section": "Mục",
            "article": "Điều",
            "clause": "Khoản",
            "point": "Điểm",
            "subpoint": "Tiểu điểm",
        }
        return level_names.get(level, level.title())

    def _extract_hierarchy_from_content(self, content: str) -> Optional[str]:
        """Extract hierarchy from content text"""
        hierarchy_patterns = [
            r"(PHẦN|Phần)\s+([IVXLCDM]+|\d+)",
            r"(CHƯƠNG|Chương)\s+([IVXLCDM]+|\d+)",
            r"(MỤC|Mục)\s+([IVXLCDM]+|\d+)",
            r"(ĐIỀU|Điều)\s+(\d+)",
        ]

        found_parts = []
        for pattern in hierarchy_patterns:
            match = re.search(pattern, content)
            if match:
                found_parts.append(f"{match.group(1)} {match.group(2)}")

        if found_parts:
            return "HỒ SƠ MỜI THẦU > " + " > ".join(found_parts)

        return None

    def _extract_section_info(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Extract section-level information"""
        section_info = {}

        content = chunk.get("content", "").lower()

        # Detect section type
        for section_type, indicators in self.section_types.items():
            for indicator in indicators:
                if indicator.lower() in content:
                    section_info["section_type"] = section_type
                    break
            if "section_type" in section_info:
                break

        # Extract section title if available
        if "parsed_sections" in chunk and chunk["parsed_sections"]:
            first_section = chunk["parsed_sections"][0]
            if first_section.get("title"):
                section_info["section_title"] = first_section["title"]
            if first_section.get("level"):
                section_info["section_level"] = first_section["level"]
            if first_section.get("number"):
                section_info["section_number"] = first_section["number"]

        return section_info

    def _extract_bidding_metadata(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Extract bidding-specific metadata"""
        bidding_meta = {}

        content = chunk.get("content", "")
        content_lower = content.lower()

        # Check for tables (BOQ, evaluation criteria, etc.)
        if "tables" in chunk and chunk["tables"]:
            bidding_meta["has_tables"] = True
            bidding_meta["table_count"] = len(chunk["tables"])

            # Classify table types
            table_types = []
            for table in chunk["tables"]:
                table_type = table.get("type", "general")
                table_types.append(table_type)
            bidding_meta["table_types"] = list(set(table_types))

        # Check for forms
        form_indicators = ["biểu mẫu", "mẫu đơn", "form", "đơn dự thầu"]
        if any(indicator in content_lower for indicator in form_indicators):
            bidding_meta["contains_forms"] = True

        # Check for technical specifications
        tech_indicators = ["thông số kỹ thuật", "yêu cầu kỹ thuật", "specification"]
        if any(indicator in content_lower for indicator in tech_indicators):
            bidding_meta["contains_technical_specs"] = True

        # Check for evaluation criteria
        eval_indicators = ["tiêu chí đánh giá", "phương pháp đánh giá", "evaluation"]
        if any(indicator in content_lower for indicator in eval_indicators):
            bidding_meta["contains_evaluation"] = True

        # Extract monetary values
        money_pattern = (
            r"(\d+(?:\.\d+)?)\s*(triệu|tỷ|million|billion)?\s*(VNĐ|VND|USD|đồng)"
        )
        money_matches = re.findall(money_pattern, content, re.IGNORECASE)
        if money_matches:
            bidding_meta["contains_monetary_values"] = True
            bidding_meta["monetary_value_count"] = len(money_matches)

        # Extract time references
        time_pattern = r"(\d+)\s*(ngày|tháng|năm|tuần|days?|months?|years?|weeks?)"
        time_matches = re.findall(time_pattern, content, re.IGNORECASE)
        if time_matches:
            bidding_meta["contains_time_references"] = True
            bidding_meta["time_reference_count"] = len(time_matches)

        return bidding_meta

    def _extract_entities(self, chunk: Dict[str, Any]) -> Dict[str, List[str]]:
        """Extract named entities from chunk"""
        entities = {}
        content = chunk.get("content", "")

        # Extract organizations
        org_pattern = r"(Công ty|Tổng công ty|Tập đoàn|Corporation|Company|Ltd|Co\.)\s+([A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴ][^\n]{5,100})"
        org_matches = re.findall(org_pattern, content)
        if org_matches:
            entities["organizations"] = [
                f"{match[0]} {match[1]}".strip() for match in org_matches
            ]

        # Extract locations
        location_pattern = r"(tại|ở|at)\s+([A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴ][^\n]{5,50})"
        location_matches = re.findall(location_pattern, content, re.IGNORECASE)
        if location_matches:
            entities["locations"] = [match[1].strip() for match in location_matches]

        # Extract regulations/standards
        regulation_pattern = r"(TCVN|QCVN|ISO|ASTM|BS|DIN|JIS)\s*(\d+[:\-\d]*)"
        regulation_matches = re.findall(regulation_pattern, content)
        if regulation_matches:
            entities["standards"] = [
                f"{match[0]} {match[1]}" for match in regulation_matches
            ]

        return entities

    def _detect_bidding_type(self, content: str) -> Optional[str]:
        """Detect bidding document type from content"""
        content_lower = content.lower()

        for bidding_type, indicators in self.bidding_types.items():
            for indicator in indicators:
                if indicator.lower() in content_lower:
                    return bidding_type

        return None

    def _calculate_content_stats(self, chunk: Dict[str, Any]) -> Dict[str, int]:
        """Calculate content statistics"""
        content = chunk.get("content", "")

        stats = {
            "char_count": len(content),
            "word_count": len(content.split()),
            "line_count": len(content.split("\n")),
            "paragraph_count": len([p for p in content.split("\n\n") if p.strip()]),
        }

        # Count sentences (approximate)
        sentence_endings = content.count(".") + content.count("!") + content.count("?")
        stats["sentence_count"] = max(1, sentence_endings)

        return stats

    def validate_mapping(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate mapped chunks"""
        validation = {
            "total_chunks": len(chunks),
            "chunks_with_hierarchy": 0,
            "chunks_with_section_info": 0,
            "chunks_with_bidding_meta": 0,
            "issues": [],
        }

        for i, chunk in enumerate(chunks):
            metadata = chunk.get("metadata", {})

            # Check hierarchy
            if metadata.get("hierarchy"):
                validation["chunks_with_hierarchy"] += 1

            # Check section info
            if any(
                key in metadata
                for key in ["section_type", "section_title", "section_level"]
            ):
                validation["chunks_with_section_info"] += 1

            # Check bidding metadata
            bidding_keys = [
                "contains_forms",
                "contains_technical_specs",
                "contains_evaluation",
                "has_tables",
            ]
            if any(key in metadata for key in bidding_keys):
                validation["chunks_with_bidding_meta"] += 1

            # Check for required fields
            if not metadata.get("doc_type"):
                validation["issues"].append(f"Chunk {i}: Missing doc_type")

            if not chunk.get("content"):
                validation["issues"].append(f"Chunk {i}: Missing content")

        # Calculate percentages
        if chunks:
            validation["hierarchy_coverage"] = (
                validation["chunks_with_hierarchy"] / len(chunks)
            ) * 100
            validation["section_coverage"] = (
                validation["chunks_with_section_info"] / len(chunks)
            ) * 100
            validation["bidding_coverage"] = (
                validation["chunks_with_bidding_meta"] / len(chunks)
            ) * 100

        validation["is_valid"] = len(validation["issues"]) == 0

        return validation
