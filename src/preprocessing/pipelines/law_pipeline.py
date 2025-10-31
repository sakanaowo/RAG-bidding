"""
Law Document Pipeline
Example implementation of BaseLegalPipeline for Law documents (Luật)
This serves as a template for other pipelines.
"""

import re
from pathlib import Path
from typing import List, Any
from datetime import date

from ..base import BaseLegalPipeline, PipelineConfig
from ..loaders import DocxLoader, RawDocxContent
from ..schema import (
    UnifiedLegalChunk,
    DocumentInfo,
    LegalMetadata,
    ContentStructure,
    ProcessingMetadata,
    QualityMetrics,
    HierarchyPath,
    DocType,
    LegalLevel,
    LegalStatus,
    IssuingAuthority,
    ChunkType,
    ContentFormat,
)


class LawPipeline(BaseLegalPipeline):
    """
    Pipeline for processing Vietnamese Law documents (Luật).

    Law documents have:
    - Strict hierarchical structure: Phần > Chương > Mục > Điều > Khoản > Điểm
    - Issued by National Assembly (Quốc hội)
    - Legal level = 2
    - DOCX format (typically)

    Processing stages:
    1. Ingest: Load DOCX file
    2. Extract: Parse metadata + hierarchical content
    3. Validate: Check legal ID format, hierarchy
    4. Chunk: Split by Điều (articles)
    5. Enrich: Extract legal concepts, references
    6. Quality: Validate completeness
    7. Output: Create UnifiedLegalChunk objects
    """

    def get_doc_type(self) -> DocType:
        """Return LAW document type"""
        return DocType.LAW

    # ============================================================
    # STAGE 1: INGESTION
    # ============================================================

    def ingest(self, file_path: Path) -> RawDocxContent:
        """
        Load DOCX file from disk using DocxLoader.

        Returns:
            RawDocxContent with extracted text, metadata, structure
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Use DocxLoader to extract content
        loader = DocxLoader(preserve_formatting=False)
        raw_content = loader.load(file_path)

        return raw_content

    # ============================================================
    # STAGE 2: EXTRACTION
    # ============================================================

    def extract(self, raw_data: RawDocxContent) -> tuple[DocumentInfo, Any]:
        """
        Extract metadata and content from RawDocxContent.

        For Law documents:
        - Parse legal ID from metadata
        - Extract title, dates
        - Prepare hierarchical structure for chunking
        """
        metadata = raw_data.metadata

        # Create DocumentInfo from extracted metadata
        # Determine legal ID (try doc_number from metadata first)
        doc_id = metadata.get("doc_number", "")
        if not doc_id:
            # Fallback: try to extract from filename
            # e.g., "43-2013-QH13.docx" → "43/2013/QH13"
            filename = metadata["filename"]
            match = re.match(r"(\d+)-(\d{4})-(.+)\.docx", filename, re.I)
            if match:
                doc_id = f"{match.group(1)}/{match.group(2)}/{match.group(3).upper()}"
            else:
                doc_id = filename.replace(".docx", "")

        # Determine dates (mock for now - should be extracted from document)
        # TODO: Extract actual dates from document content
        import datetime

        issue_date = datetime.date.today()  # Placeholder
        effective_date = None  # Should be extracted

        document_info = DocumentInfo(
            doc_id=doc_id,
            doc_type=DocType.LAW,
            title=metadata.get("title", ""),
            issuing_authority=IssuingAuthority.QUOC_HOI,  # Laws are from National Assembly
            issue_date=issue_date,
            effective_date=effective_date,
            source_file=metadata["file_path"],
        )

        # Prepare content for chunking
        # Structure contains detected hierarchy (Phần, Chương, Điều, etc.)
        content = {
            "text": raw_data.text,
            "structure": raw_data.structure,
            "tables": raw_data.tables,
            "statistics": raw_data.statistics,
        }

        return document_info, content

    # ============================================================
    # STAGE 3: VALIDATION
    # ============================================================

    def validate(self, document_info: DocumentInfo, content: Any) -> Any:
        """
        Validate extracted Law document data.

        Checks:
        - Legal ID matches pattern: number/year/QH{number}
        - Issue date < Effective date
        - Hierarchy is complete
        """
        # Validate legal ID pattern for Laws
        if not document_info.doc_id.endswith(
            "QH" + document_info.doc_id.split("/")[1][-2:]
        ):
            self.add_warning(
                f"Legal ID {document_info.doc_id} may not match Law pattern (should end with QH{{number}})"
            )

        # Validate dates
        if (
            document_info.effective_date
            and document_info.issue_date > document_info.effective_date
        ):
            self.add_error("Issue date cannot be after effective date")

        # TODO: Validate hierarchy structure

        return content

    # ============================================================
    # STAGE 4: CHUNKING
    # ============================================================

    def chunk(
        self, document_info: DocumentInfo, content: Any
    ) -> List[UnifiedLegalChunk]:
        """
        Split Law document into chunks.

        Chunking strategy for Laws:
        - Primary chunks: Điều (articles)
        - Each Điều becomes one chunk
        - Preserve hierarchy: Phần > Chương > Mục > Điều

        TODO: Implement hierarchical chunking.
        Returns mock chunks for skeleton.
        """
        chunks = []
        chunk_index = 0

        # Iterate through sections and create chunks
        for section in content.get("sections", []):
            for chuong in section.get("chuongs", []):
                for dieu in chuong.get("dieus", []):

                    # Create hierarchy path
                    hierarchy = HierarchyPath(
                        phan=section.get("phan"),
                        chuong=chuong.get("chuong"),
                        dieu=dieu.get("dieu"),
                    )

                    # Create content structure
                    content_structure = ContentStructure(
                        chunk_id=f"{document_info.doc_id}_dieu_{dieu['dieu']}",
                        chunk_type=ChunkType.DIEU_KHOAN,
                        chunk_index=chunk_index,
                        hierarchy=hierarchy,
                        content_text=dieu.get("content", ""),
                        content_format=ContentFormat.PLAIN_TEXT,
                        heading=f"Điều {dieu['dieu']}. {dieu.get('title', '')}",
                        word_count=len(dieu.get("content", "").split()),
                        char_count=len(dieu.get("content", "")),
                    )

                    # Create legal metadata
                    legal_metadata = LegalMetadata(
                        legal_level=LegalLevel.LUAT,
                        legal_status=LegalStatus.CON_HIEU_LUC,
                        legal_domain=[],
                    )

                    # Create processing metadata
                    processing_metadata = ProcessingMetadata(
                        processing_id=self.processing_id,
                        extractor_used="docx",
                        chunking_strategy=self.config.chunking_strategy,
                    )

                    # Create chunk
                    chunk = UnifiedLegalChunk(
                        document_info=document_info,
                        legal_metadata=legal_metadata,
                        content_structure=content_structure,
                        processing_metadata=processing_metadata,
                        quality_metrics=QualityMetrics(),
                    )

                    chunks.append(chunk)
                    chunk_index += 1

        return chunks

    # ============================================================
    # STAGE 5: ENRICHMENT (Optional)
    # ============================================================

    def enrich(self, chunks: List[UnifiedLegalChunk]) -> List[UnifiedLegalChunk]:
        """
        Add semantic enrichment to Law chunks.

        Enrichment for Laws:
        - Extract legal concepts (e.g., "đấu thầu rộng rãi")
        - Detect references to other laws
        - Extract key terms

        TODO: Implement NER, concept extraction.
        """
        # For now, use default implementation (no-op)
        return super().enrich(chunks)

    # ============================================================
    # STAGE 6: QUALITY CHECK
    # ============================================================

    def assess_quality(
        self, chunks: List[UnifiedLegalChunk]
    ) -> List[UnifiedLegalChunk]:
        """
        Assess quality of Law chunks.

        Quality checks for Laws:
        - All Điều have content
        - Hierarchy is sequential
        - No missing articles
        """
        # Use base implementation + add Law-specific checks
        chunks = super().assess_quality(chunks)

        # TODO: Add Law-specific quality checks
        # - Check for sequential Điều numbering
        # - Validate hierarchy completeness

        return chunks
