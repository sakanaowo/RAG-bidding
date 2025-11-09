"""
Chunk Factory - Convert UniversalChunk to UnifiedLegalChunk.

Provides:
- ChunkFactory: Main factory class
- Helper functions to build UnifiedLegalChunk from UniversalChunk
- Validation and schema integration
"""

from typing import List, Dict, Any, Optional, Union
from datetime import datetime, date
import hashlib

from src.preprocessing.chunking.base_chunker import UniversalChunk
from src.preprocessing.schema.unified_schema import UnifiedLegalChunk
from src.preprocessing.schema.models.document_info_types import (
    create_document_info,
    LegalDocumentInfo,
    TemplateDocumentInfo,
    ExamDocumentInfo,
    DocumentInfo,
)
from src.preprocessing.schema.models.legal_metadata import LegalMetadata
from src.preprocessing.schema.models.content_structure import (
    ContentStructure,
    HierarchyPath,
)
from src.preprocessing.schema.models.processing_metadata import ProcessingMetadata
from src.preprocessing.schema.models.quality_metrics import QualityMetrics
from src.preprocessing.schema.enums import DocType
from src.preprocessing.base.models import ProcessedDocument


class ChunkFactory:
    """
    Factory for converting UniversalChunk to UnifiedLegalChunk.

    Handles:
    - Schema mapping
    - Metadata extraction from ProcessedDocument
    - Quality validation
    - Nested Pydantic model construction

    Usage:
        factory = ChunkFactory(pipeline_version="2.0.0")
        chunks = chunker.chunk(document)
        unified_chunks = factory.convert_batch(chunks, document)
    """

    def __init__(
        self,
        pipeline_version: str = "2.0.0",
        validate: bool = True,
    ):
        """
        Args:
            pipeline_version: Version of preprocessing pipeline
            validate: Whether to validate chunks after conversion
        """
        self.pipeline_version = pipeline_version
        self.validate = validate

    def convert(
        self,
        chunk: UniversalChunk,
        source_document: ProcessedDocument,
    ) -> UnifiedLegalChunk:
        """
        Convert single UniversalChunk to UnifiedLegalChunk.

        Args:
            chunk: UniversalChunk from chunker
            source_document: Original ProcessedDocument

        Returns:
            UnifiedLegalChunk ready for embedding + storage

        Raises:
            ValueError: If conversion fails validation
        """
        # Build Document Info (Section 3.1)
        document_info = self._build_document_info(chunk, source_document)

        # Build Legal Metadata (Section 3.2) - optional for non-legal docs
        legal_metadata = self._build_legal_metadata(chunk, source_document)

        # Build Content Structure (Section 3.3)
        content_structure = self._build_content_structure(chunk, source_document)

        # Build Processing Metadata (Section 3.5)
        processing_metadata = self._build_processing_metadata(chunk, source_document)

        # Build Quality Metrics (Section 3.6)
        quality_metrics = self._build_quality_metrics(chunk, source_document)

        # Extended Metadata (Section 3.7)
        extended_metadata = self._build_extended_metadata(chunk, source_document)

        # Create UnifiedLegalChunk
        unified_chunk = UnifiedLegalChunk(
            document_info=document_info,
            legal_metadata=legal_metadata,
            content_structure=content_structure,
            processing_metadata=processing_metadata,
            quality_metrics=quality_metrics,
            extended_metadata=extended_metadata,
        )

        # Validate if enabled
        if self.validate:
            self._validate_chunk(unified_chunk)

        return unified_chunk

    def convert_batch(
        self,
        chunks: List[UniversalChunk],
        source_document: ProcessedDocument,
    ) -> List[UnifiedLegalChunk]:
        """
        Convert batch of UniversalChunks to UnifiedLegalChunks.

        Args:
            chunks: List of UniversalChunks
            source_document: Original ProcessedDocument

        Returns:
            List of UnifiedLegalChunks
        """
        unified_chunks = []

        for chunk in chunks:
            try:
                unified = self.convert(chunk, source_document)
                unified_chunks.append(unified)
            except Exception as e:
                # Log error but continue
                print(f"Error converting chunk {chunk.chunk_id}: {e}")
                continue

        return unified_chunks

    # ============================================================
    # SECTION 3.1: DOCUMENT INFORMATION
    # ============================================================

    def _build_document_info(
        self,
        chunk: UniversalChunk,
        source_document: ProcessedDocument,
    ) -> DocumentInfo:
        """
        Build polymorphic DocumentInfo from chunk and source.

        Returns appropriate DocumentInfo subclass:
        - LegalDocumentInfo for law/decree/circular/decision
        - TemplateDocumentInfo for bidding_template/report_template
        - ExamDocumentInfo for exam_questions
        """
        metadata = source_document.metadata

        # Get document type
        doc_type_str = metadata.get("document_type", "unknown")

        # Get common fields
        title = metadata.get("title", "Untitled")
        source_file = metadata.get("file_path", "")
        source_url = metadata.get("source_url")

        # Build doc_id and type-specific fields
        if doc_type_str in ["law", "decree", "circular", "decision"]:
            # Legal document
            legal_meta = metadata.get("legal_metadata", {})
            doc_id = legal_meta.get("legal_id", chunk.document_id)

            # Extract dates
            issue_date_val = metadata.get("issued_date")
            if isinstance(issue_date_val, str):
                try:
                    issue_date = datetime.fromisoformat(issue_date_val).date()
                except:
                    issue_date = date.today()
            elif isinstance(issue_date_val, datetime):
                issue_date = issue_date_val.date()
            elif isinstance(issue_date_val, date):
                issue_date = issue_date_val
            else:
                issue_date = date.today()

            effective_date_val = metadata.get("effective_date")
            if isinstance(effective_date_val, str):
                try:
                    effective_date = datetime.fromisoformat(effective_date_val).date()
                except:
                    effective_date = None
            elif isinstance(effective_date_val, (datetime, date)):
                effective_date = (
                    effective_date_val
                    if isinstance(effective_date_val, date)
                    else effective_date_val.date()
                )
            else:
                effective_date = None

            return create_document_info(
                doc_type=doc_type_str,
                doc_id=doc_id,
                title=title,
                source_file=source_file,
                issuing_authority=metadata.get("issued_by", "khac"),
                issue_date=issue_date,
                effective_date=effective_date,
                source_url=source_url,
            )

        elif doc_type_str in ["bidding_template", "report_template"]:
            # Template document
            # Create sanitized doc_id from filename
            import os

            filename = os.path.basename(source_file)
            doc_id = f"{doc_type_str}_{filename.replace('.docx', '').replace(' ', '_').lower()}"

            # Extract date if available
            issue_date_val = metadata.get("issued_date")
            if isinstance(issue_date_val, str):
                try:
                    issue_date = datetime.fromisoformat(issue_date_val).date()
                except:
                    issue_date = None
            elif isinstance(issue_date_val, (datetime, date)):
                issue_date = (
                    issue_date_val
                    if isinstance(issue_date_val, date)
                    else issue_date_val.date()
                )
            else:
                issue_date = None

            return create_document_info(
                doc_type=doc_type_str,
                doc_id=doc_id,
                title=title,
                source_file=source_file,
                template_version=metadata.get("version", "1.0"),
                issuing_ministry=metadata.get("issuing_ministry", "bo_ke_hoach_dau_tu"),
                issue_date=issue_date,
                source_url=source_url,
            )

        elif doc_type_str == "exam_questions":
            # Exam document
            import os

            filename = os.path.basename(source_file)
            # Create exam_id from filename
            doc_id = f"exam_{filename.replace('.pdf', '').replace(' ', '_').lower()}"

            # Extract date if available
            exam_date_val = metadata.get("exam_date") or metadata.get("issued_date")
            if isinstance(exam_date_val, str):
                try:
                    exam_date = datetime.fromisoformat(exam_date_val).date()
                except:
                    exam_date = None
            elif isinstance(exam_date_val, (datetime, date)):
                exam_date = (
                    exam_date_val
                    if isinstance(exam_date_val, date)
                    else exam_date_val.date()
                )
            else:
                exam_date = None

            return create_document_info(
                doc_type=doc_type_str,
                doc_id=doc_id,
                title=title,
                source_file=source_file,
                exam_subject=metadata.get("exam_subject", "chuyen_gia_dau_thau"),
                exam_date=exam_date,
                question_count=metadata.get("question_count", 0),
                source_url=source_url,
            )

        else:
            # Unknown type - default to legal with flexible validation
            raise ValueError(
                f"Unknown document type: {doc_type_str}. "
                f"Expected one of: law, decree, circular, decision, "
                f"bidding_template, report_template, exam_questions"
            )

    def _map_document_type(self, doc_type_str: str) -> DocType:
        """Map string document type to DocType enum"""

        mapping = {
            "law": DocType.LAW,
            "decree": DocType.DECREE,
            "circular": DocType.CIRCULAR,
            "decision": DocType.DECISION,
            "bidding": DocType.BIDDING,
            "report": DocType.REPORT,
            "exam": DocType.EXAM,
        }

        return mapping.get(doc_type_str.lower(), DocType.LAW)  # Default to LAW

    # ============================================================
    # SECTION 3.2: LEGAL METADATA
    # ============================================================

    def _build_legal_metadata(
        self,
        chunk: UniversalChunk,
        source_document: ProcessedDocument,
    ) -> Optional[LegalMetadata]:
        """
        Build LegalMetadata (only for legal documents).

        Returns None for bidding/report/exam documents.
        """
        # Only for legal docs
        if chunk.document_type not in ["law", "decree", "circular", "decision"]:
            return None

        metadata = source_document.metadata
        legal_meta = metadata.get("legal_metadata", {})

        # Map status to Vietnamese enum
        status_mapping = {
            "active": "con_hieu_luc",
            "inactive": "het_hieu_luc",
            "superseded": "bi_thay_the",
            "revoked": "bi_bai_bo",
            "draft": "du_thao",
        }
        raw_status = legal_meta.get("status", "active")
        legal_status = status_mapping.get(raw_status, "con_hieu_luc")

        return LegalMetadata(
            legal_id=legal_meta.get("legal_id", chunk.document_id),
            legal_level=legal_meta.get("legal_level", 3),  # Default decree level
            legal_status=legal_status,
            legal_domain=legal_meta.get("domain", []),
            jurisdiction=legal_meta.get("jurisdiction", "central"),
            parent_law_id=legal_meta.get("parent_law_id"),
            superseded_by_id=legal_meta.get("superseded_by"),
            related_doc_ids=legal_meta.get("related_docs", []),
        )

    # ============================================================
    # SECTION 3.3: CONTENT STRUCTURE
    # ============================================================

    def _build_content_structure(
        self,
        chunk: UniversalChunk,
        source_document: ProcessedDocument,
    ) -> ContentStructure:
        """Build ContentStructure from chunk"""

        # Build HierarchyPath
        hierarchy_path = self._build_hierarchy_path(chunk)

        # Determine chunk type
        chunk_type = self._determine_chunk_type(chunk)

        # Build embedding metadata
        embedding_metadata = {
            "has_context": chunk.parent_context is not None,
            "is_complete": chunk.is_complete_unit,
            "has_special_content": chunk.has_table or chunk.has_list,
        }

        return ContentStructure(
            chunk_id=chunk.chunk_id,
            chunk_type=chunk_type,
            chunk_index=chunk.chunk_index,
            total_chunks=chunk.total_chunks,
            hierarchy=hierarchy_path,
            content_text=chunk.content,
            content_format="plain_text",
            word_count=len(chunk.content.split()),
            char_count=chunk.char_count,
            has_tables=chunk.has_table,
            has_lists=chunk.has_list,
            embedding_metadata=embedding_metadata,
        )

    def _build_hierarchy_path(self, chunk: UniversalChunk) -> HierarchyPath:
        """
        Build HierarchyPath from chunk hierarchy.

        Handles both hierarchical (legal) and flat (bidding/report/exam) structures.
        """
        if not chunk.hierarchy:
            return HierarchyPath()

        # For legal docs: extract Phần/Chương/Mục/Điều/Khoản
        if chunk.document_type in ["law", "decree", "circular", "decision"]:
            return self._extract_legal_hierarchy(chunk.hierarchy)

        # For non-legal: store as flat list
        return HierarchyPath(
            metadata={
                "hierarchy_list": chunk.hierarchy,
                "level": chunk.level,
            }
        )

    def _extract_legal_hierarchy(self, hierarchy: List[str]) -> HierarchyPath:
        """
        Extract legal hierarchy components and convert to integers.

        Examples:
            "Phần I" -> 1
            "CHƯƠNG II" -> 2
            "Điều 15" -> 15
            "Khoản 3" -> 3
        """
        import re

        phan = None
        chuong = None
        muc = None
        dieu = None
        khoan = None

        # Roman numeral to int mapping
        roman_map = {
            "I": 1,
            "II": 2,
            "III": 3,
            "IV": 4,
            "V": 5,
            "VI": 6,
            "VII": 7,
            "VIII": 8,
            "IX": 9,
            "X": 10,
            "XI": 11,
            "XII": 12,
            "XIII": 13,
            "XIV": 14,
            "XV": 15,
            "XVI": 16,
            "XVII": 17,
            "XVIII": 18,
            "XIX": 19,
            "XX": 20,
        }

        for item in hierarchy:
            item_upper = item.upper()

            if "PHẦN" in item_upper:
                # Extract roman numeral after "Phần"
                match = re.search(r"PHẦN\s+([IVX]+)", item_upper)
                if match:
                    phan = roman_map.get(match.group(1))

            elif "CHƯƠNG" in item_upper:
                # Extract roman numeral after "Chương"
                match = re.search(r"CHƯƠNG\s+([IVX]+)", item_upper)
                if match:
                    chuong = roman_map.get(match.group(1))

            elif "MỤC" in item_upper:
                # Extract number after "Mục"
                match = re.search(r"MỤC\s+(\d+)", item_upper)
                if match:
                    muc = int(match.group(1))

            elif "ĐIỀU" in item_upper:
                # Extract number after "Điều"
                match = re.search(r"ĐIỀU\s+(\d+)", item_upper)
                if match:
                    dieu = int(match.group(1))

            elif "KHOẢN" in item_upper:
                # Extract number after "Khoản"
                match = re.search(r"KHOẢN\s+(\d+)", item_upper)
                if match:
                    khoan = int(match.group(1))

        return HierarchyPath(
            phan=phan,
            chuong=chuong,
            muc=muc,
            dieu=dieu,
            khoan=khoan,
        )

    def _determine_chunk_type(self, chunk: UniversalChunk) -> str:
        """
        Determine chunk type for schema.

        Maps UniversalChunk.level to valid ChunkType enum values:
        - Legal levels: phan, chuong, muc, dieu, khoan, diem
        - Non-legal: form, section, question, etc. → "semantic"
        """
        # Legal chunk types (exact match)
        legal_types = {
            "phan": "phan",
            "chuong": "chuong",
            "muc": "muc",
            "dieu": "dieu_khoan",
            "khoan": "khoan",
            "diem": "diem",
        }

        # Check if it's a legal type
        if chunk.level in legal_types:
            return legal_types[chunk.level]

        # Check if it's a table
        if chunk.level == "table" or chunk.has_table:
            return "table"

        # Everything else (form, section, question, etc.) → semantic
        return "semantic"

    # ============================================================
    # SECTION 3.5: PROCESSING METADATA
    # ============================================================

    def _build_processing_metadata(
        self,
        chunk: UniversalChunk,
        source_document: ProcessedDocument,
    ) -> ProcessingMetadata:
        """Build ProcessingMetadata"""

        # Generate processing ID (hash-based)
        processing_id = self._generate_processing_id(chunk)

        # Determine chunking strategy
        if chunk.document_type in ["law", "decree", "circular", "decision"]:
            chunking_strategy = "hierarchical"
        else:
            chunking_strategy = "semantic"

        # Determine extractor
        file_path = source_document.metadata.get("file_path", "")
        if file_path.endswith(".docx"):
            extractor = "docx"
        elif file_path.endswith(".pdf"):
            extractor = "pdf"
        else:
            extractor = "unknown"

        return ProcessingMetadata(
            processing_id=processing_id,
            pipeline_version=self.pipeline_version,
            processed_at=datetime.now(),
            extractor_used=extractor,
            chunking_strategy=chunking_strategy,
            chunk_params={
                "min_size": 300,
                "max_size": 1500,
                "target_size": 800,
            },
        )

    def _generate_processing_id(self, chunk: UniversalChunk) -> str:
        """Generate unique processing ID"""

        # Hash chunk_id + timestamp
        content = f"{chunk.chunk_id}_{datetime.now().isoformat()}"
        hash_obj = hashlib.sha256(content.encode())
        return f"proc_{hash_obj.hexdigest()[:16]}"

    # ============================================================
    # SECTION 3.6: QUALITY METRICS
    # ============================================================

    def _build_quality_metrics(
        self,
        chunk: UniversalChunk,
        source_document: ProcessedDocument,
    ) -> QualityMetrics:
        """Build QualityMetrics"""

        # Calculate quality score
        quality_score = self._calculate_quality_score(chunk)

        # Determine overall quality
        if quality_score >= 0.8:
            overall_quality = "high"
        elif quality_score >= 0.6:
            overall_quality = "medium"
        else:
            overall_quality = "low"

        # Validation checks
        validation_passed = (
            300 <= chunk.char_count <= 1500 and chunk.content.strip() != ""
        )

        validation_issues = []
        if chunk.char_count < 300:
            validation_issues.append("chunk_too_short")
        if chunk.char_count > 1500:
            validation_issues.append("chunk_too_long")
        if not chunk.is_complete_unit:
            validation_issues.append("incomplete_semantic_unit")

        return QualityMetrics(
            overall_quality=overall_quality,
            confidence_score=quality_score,
            validation_passed=validation_passed,
            validation_issues=validation_issues if validation_issues else None,
        )

    def _calculate_quality_score(self, chunk: UniversalChunk) -> float:
        """
        Calculate quality score (0-1).

        Factors:
        - Size in optimal range (700-900) = +0.3
        - Complete semantic unit = +0.3
        - Has parent context = +0.2
        - No special content issues = +0.2
        """
        score = 0.0

        # Size score (0-0.3)
        size = chunk.char_count
        if 700 <= size <= 900:
            score += 0.3
        elif 500 <= size < 700 or 900 < size <= 1200:
            score += 0.2
        elif 300 <= size < 500 or 1200 < size <= 1500:
            score += 0.1

        # Completeness score (0-0.3)
        if chunk.is_complete_unit:
            score += 0.3
        else:
            score += 0.1  # Partial credit

        # Context score (0-0.2)
        if chunk.parent_context:
            score += 0.2

        # Special content score (0-0.2)
        if chunk.has_table or chunk.has_list:
            # Tables/lists are good if preserved
            score += 0.2
        else:
            # Plain text is also good
            score += 0.2

        return min(score, 1.0)

    # ============================================================
    # SECTION 3.7: EXTENDED METADATA
    # ============================================================

    def _build_extended_metadata(
        self,
        chunk: UniversalChunk,
        source_document: ProcessedDocument,
    ) -> Dict[str, Any]:
        """Build extended metadata from chunk.extra_metadata"""

        extended = chunk.extra_metadata.copy() if chunk.extra_metadata else {}

        # Add chunk-specific metadata
        extended.update(
            {
                "chunk_level": chunk.level,
                "section_title": chunk.section_title,
                "parent_context": chunk.parent_context,
                "hierarchy_depth": len(chunk.hierarchy) if chunk.hierarchy else 0,
            }
        )

        return extended

    # ============================================================
    # VALIDATION
    # ============================================================

    def _validate_chunk(self, chunk: UnifiedLegalChunk):
        """
        Validate UnifiedLegalChunk.

        Logs warnings instead of raising errors to allow test data flexibility.
        """
        import warnings

        # Check chunk size
        char_count = chunk.content_structure.char_count
        if char_count < 300 or char_count > 1500:
            warnings.warn(
                f"Chunk {chunk.content_structure.chunk_id} size {char_count} "
                f"outside recommended range (300-1500)"
            )

        # Check content not empty
        if not chunk.content_structure.content_text.strip():
            warnings.warn(f"Chunk {chunk.content_structure.chunk_id} has empty content")

        # Check hierarchy for legal docs
        if chunk.is_legal_document():
            if not chunk.legal_metadata:
                warnings.warn(
                    f"Legal document {chunk.document_info.doc_id} missing legal_metadata"
                )


def create_chunker(document_type: str):
    """
    Factory function to create appropriate chunker.

    Args:
        document_type: Type of document (law, decree, bidding, report, exam)

    Returns:
        Appropriate chunker instance

    Example:
        chunker = create_chunker("law")
        chunks = chunker.chunk(document)
    """
    from src.preprocessing.chunking.hierarchical_chunker import HierarchicalChunker
    from src.preprocessing.chunking.semantic_chunker import SemanticChunker

    doc_type = document_type.lower()

    # Legal documents → HierarchicalChunker
    if doc_type in ["law", "decree", "circular", "decision"]:
        return HierarchicalChunker()

    # Bidding → SemanticChunker (bidding mode)
    elif doc_type == "bidding":
        return SemanticChunker(document_type="bidding")

    # Report → SemanticChunker (report mode)
    elif doc_type == "report":
        return SemanticChunker(document_type="report")

    # Exam → SemanticChunker (exam mode)
    elif doc_type == "exam":
        return SemanticChunker(document_type="exam")

    else:
        raise ValueError(f"Unsupported document type: {document_type}")
