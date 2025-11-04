# 🏗️ PREPROCESSING PIPELINE ARCHITECTURE
## Long-term Architecture Design for RAG-Bidding System

**Ngày tạo**: 31/10/2025  
**Phiên bản**: 2.0  
**Status**: Architecture Design - Ready for Implementation

---

## 📋 MỤC LỤC

1. [Architecture Overview](#architecture-overview)
2. [Core Components](#core-components)
3. [Pipeline Design](#pipeline-design)
4. [Implementation Roadmap](#implementation-roadmap)
5. [Migration Strategy](#migration-strategy)

---

## 🎯 ARCHITECTURE OVERVIEW

### Nguyên tắc thiết kế

**1. Modular & Extensible**
- Mỗi component độc lập, dễ test và maintain
- Plugin architecture cho document types mới
- Shared base classes giảm code duplication

**2. Unified Schema-driven**
- Single source of truth: UnifiedLegalChunk
- Type-safe với Pydantic validation
- Backward compatible migration

**3. Pipeline as Code**
- Declarative configuration (YAML/Python)
- Version controlled
- Reproducible preprocessing

**4. Quality-first**
- Validation ở mọi stage
- Quality metrics tracking
- Automatic error recovery

---

## 🏛️ ARCHITECTURE LAYERS

```
┌─────────────────────────────────────────────────────────────────┐
│                     APPLICATION LAYER                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   CLI Tool   │  │  API Server  │  │  Batch Jobs  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   ORCHESTRATION LAYER                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │           PipelineOrchestrator                           │   │
│  │  - Pipeline selection & routing                          │   │
│  │  - Parallel execution management                         │   │
│  │  - Error handling & retry logic                          │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    PIPELINE LAYER (7 pipelines)                  │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌────┐ │
│  │ Law  │ │Decree│ │Circ. │ │Decis.│ │Bidd. │ │Report│ │Exam│ │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └────┘ │
│     Each pipeline extends BaseLegalPipeline                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   PROCESSING LAYER (Stages)                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  1. Ingestion    → Load documents                        │   │
│  │  2. Extraction   → Parse content & metadata              │   │
│  │  3. Validation   → Schema validation                     │   │
│  │  4. Chunking     → Split into semantic chunks            │   │
│  │  5. Enrichment   → Add metadata, semantic tags           │   │
│  │  6. Quality      → Quality checks & scoring              │   │
│  │  7. Output       → Save to database/files                │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    COMPONENT LAYER (Reusable)                    │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌─────────────┐  │
│  │  Document  │ │  Metadata  │ │  Chunking  │ │  Validation │  │
│  │  Loaders   │ │ Extractors │ │ Strategies │ │   Engine    │  │
│  └────────────┘ └────────────┘ └────────────┘ └─────────────┘  │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌─────────────┐  │
│  │  Semantic  │ │  Quality   │ │ Hierarchy  │ │  Relation   │  │
│  │  Enricher  │ │  Analyzer  │ │  Builder   │ │  Resolver   │  │
│  └────────────┘ └────────────┘ └────────────┘ └─────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     DATA LAYER                                   │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌─────────────┐  │
│  │   Schema   │ │   Vector   │ │   Graph    │ │    Cache    │  │
│  │ (Pydantic) │ │    Store   │ │     DB     │ │   (Redis)   │  │
│  └────────────┘ └────────────┘ └────────────┘ └─────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 CORE COMPONENTS

### 1. Schema Layer (`src/preprocessing/schema/`)

```python
# src/preprocessing/schema/__init__.py
from .unified_schema import (
    UnifiedLegalChunk,
    DocumentInfo,
    LegalMetadata,
    ContentStructure,
    Relationships,
    ProcessingMetadata,
    QualityMetrics,
    ExtendedMetadata
)
from .enums import DocType, LegalLevel, LegalStatus, RelationshipType
from .validators import SchemaValidator, ValidationResult

# src/preprocessing/schema/unified_schema.py
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime

class UnifiedLegalChunk(BaseModel):
    """
    Unified schema for all 7 document types in Vietnamese legal system.
    
    Version: 2.0
    Compatible with: Law, Decree, Circular, Decision, Bidding, Report, Exam
    """
    
    document_info: DocumentInfo
    legal_metadata: LegalMetadata
    content_structure: ContentStructure
    relationships: Relationships
    processing_metadata: ProcessingMetadata
    quality_metrics: QualityMetrics
    extended_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        validate_assignment = True
        extra = 'forbid'
        schema_extra = {
            "example": {
                "document_info": {
                    "doc_id": "law_43_2013_qh13_dieu_5_khoan_2_chunk_001",
                    "title": "Luật Đấu thầu",
                    "doc_type": "law",
                    "legal_code": "43/2013/QH13",
                    "source_file": "Luat_Dau_thau_43_2013.docx",
                    "source_url": "https://..."
                }
            }
        }
```

### 2. Base Pipeline (`src/preprocessing/base/`)

```python
# src/preprocessing/base/legal_pipeline.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

class BaseLegalPipeline(ABC):
    """
    Abstract base class for all document preprocessing pipelines.
    
    All 7 pipelines (Law, Decree, Circular, Decision, Bidding, Report, Exam)
    inherit from this base class.
    """
    
    def __init__(
        self,
        config: PipelineConfig,
        validator: SchemaValidator,
        logger: Optional[logging.Logger] = None
    ):
        self.config = config
        self.validator = validator
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        
        # Components
        self.loader = self._init_loader()
        self.extractor = self._init_extractor()
        self.chunker = self._init_chunker()
        self.enricher = self._init_enricher()
        self.quality_analyzer = self._init_quality_analyzer()
        
    # ========================================
    # MAIN PIPELINE EXECUTION
    # ========================================
    
    def process(self, file_path: Path) -> PipelineResult:
        """
        Main pipeline execution method.
        
        Stages:
        1. Ingestion: Load document
        2. Extraction: Extract content & metadata
        3. Validation: Validate against schema
        4. Chunking: Split into chunks
        5. Enrichment: Add semantic metadata
        6. Quality: Quality checks
        7. Output: Save results
        """
        self.logger.info(f"Processing: {file_path}")
        
        try:
            # Stage 1: Ingestion
            document = self._stage_ingest(file_path)
            
            # Stage 2: Extraction
            raw_metadata, content = self._stage_extract(document)
            
            # Stage 3: Validation
            validated_metadata = self._stage_validate(raw_metadata)
            
            # Stage 4: Chunking
            chunks = self._stage_chunk(content, validated_metadata)
            
            # Stage 5: Enrichment
            enriched_chunks = self._stage_enrich(chunks)
            
            # Stage 6: Quality
            quality_checked = self._stage_quality_check(enriched_chunks)
            
            # Stage 7: Output
            result = self._stage_output(quality_checked)
            
            self.logger.info(f"Success: {len(quality_checked)} chunks created")
            return PipelineResult(
                success=True,
                chunks=quality_checked,
                metadata=result,
                errors=[]
            )
            
        except Exception as e:
            self.logger.error(f"Pipeline failed: {str(e)}")
            return PipelineResult(
                success=False,
                chunks=[],
                metadata={},
                errors=[str(e)]
            )
    
    # ========================================
    # PIPELINE STAGES (Template Method Pattern)
    # ========================================
    
    def _stage_ingest(self, file_path: Path) -> Document:
        """Stage 1: Load document from file"""
        self.logger.debug("Stage 1: Ingestion")
        return self.loader.load(file_path)
    
    def _stage_extract(self, document: Document) -> tuple:
        """Stage 2: Extract metadata and content"""
        self.logger.debug("Stage 2: Extraction")
        metadata = self.extract_metadata(document)
        content = self.extract_content(document)
        return metadata, content
    
    def _stage_validate(self, metadata: Dict) -> Dict:
        """Stage 3: Validate metadata against schema"""
        self.logger.debug("Stage 3: Validation")
        validation_result = self.validator.validate(
            metadata, 
            doc_type=self.get_doc_type()
        )
        
        if not validation_result.is_valid:
            raise ValidationError(validation_result.errors)
        
        return validation_result.validated_data
    
    def _stage_chunk(self, content: str, metadata: Dict) -> List[Chunk]:
        """Stage 4: Split content into semantic chunks"""
        self.logger.debug("Stage 4: Chunking")
        return self.chunker.chunk(content, metadata)
    
    def _stage_enrich(self, chunks: List[Chunk]) -> List[UnifiedLegalChunk]:
        """Stage 5: Enrich chunks with semantic metadata"""
        self.logger.debug("Stage 5: Enrichment")
        enriched = []
        for chunk in chunks:
            enriched_chunk = self.enricher.enrich(chunk)
            enriched.append(enriched_chunk)
        return enriched
    
    def _stage_quality_check(
        self, 
        chunks: List[UnifiedLegalChunk]
    ) -> List[UnifiedLegalChunk]:
        """Stage 6: Quality analysis and scoring"""
        self.logger.debug("Stage 6: Quality Check")
        for chunk in chunks:
            quality_score = self.quality_analyzer.analyze(chunk)
            chunk.quality_metrics.completeness_score = quality_score.completeness
            chunk.quality_metrics.confidence_score = quality_score.confidence
        return chunks
    
    def _stage_output(self, chunks: List[UnifiedLegalChunk]) -> Dict:
        """Stage 7: Save to database/files"""
        self.logger.debug("Stage 7: Output")
        return self.save_chunks(chunks)
    
    # ========================================
    # ABSTRACT METHODS (Must be implemented by subclasses)
    # ========================================
    
    @abstractmethod
    def extract_metadata(self, document: Document) -> Dict:
        """Extract document-specific metadata"""
        pass
    
    @abstractmethod
    def extract_content(self, document: Document) -> str:
        """Extract text content from document"""
        pass
    
    @abstractmethod
    def get_doc_type(self) -> DocType:
        """Return the document type for this pipeline"""
        pass
    
    @abstractmethod
    def get_extended_metadata(self, document: Document) -> Dict:
        """Extract extended metadata specific to document type"""
        pass
    
    # ========================================
    # COMPONENT INITIALIZATION (Override if needed)
    # ========================================
    
    def _init_loader(self) -> DocumentLoader:
        """Initialize document loader"""
        return DocxLoader()  # Default, override for PDF/HTML
    
    def _init_extractor(self) -> MetadataExtractor:
        """Initialize metadata extractor"""
        return MetadataExtractor()
    
    def _init_chunker(self) -> ChunkingStrategy:
        """Initialize chunking strategy"""
        return HierarchicalChunker(
            max_tokens=self.config.chunk_size,
            overlap=self.config.chunk_overlap
        )
    
    def _init_enricher(self) -> SemanticEnricher:
        """Initialize semantic enricher"""
        return SemanticEnricher()
    
    def _init_quality_analyzer(self) -> QualityAnalyzer:
        """Initialize quality analyzer"""
        return QualityAnalyzer()
    
    # ========================================
    # HELPER METHODS
    # ========================================
    
    def save_chunks(self, chunks: List[UnifiedLegalChunk]) -> Dict:
        """Save chunks to database and/or files"""
        # TODO: Implement database save
        output_path = self.config.output_dir / f"{chunks[0].document_info.doc_id}.jsonl"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for chunk in chunks:
                f.write(chunk.json() + '\n')
        
        return {
            "output_path": str(output_path),
            "chunk_count": len(chunks),
            "avg_quality": sum(c.quality_metrics.completeness_score for c in chunks) / len(chunks)
        }
```

### 3. Document Type Pipelines (`src/preprocessing/pipelines/`)

```python
# src/preprocessing/pipelines/law_pipeline.py
from ..base import BaseLegalPipeline
from ..schema import DocType, UnifiedLegalChunk

class LawPipeline(BaseLegalPipeline):
    """
    Pipeline for processing Vietnamese Laws (Luật).
    
    Hierarchy: Phần → Chương → Mục → Điều → Khoản → Điểm
    Issuing body: Quốc hội
    Legal level: 2 (highest in system)
    """
    
    def get_doc_type(self) -> DocType:
        return DocType.LAW
    
    def extract_metadata(self, document: Document) -> Dict:
        """
        Extract Law-specific metadata.
        
        Required fields:
        - law_number: e.g., "43/2013/QH13"
        - law_name: e.g., "Luật Đấu thầu"
        - promulgation_date
        - effective_date
        - issuing_body: "Quốc hội"
        """
        metadata = {
            "document_info": {
                "doc_type": "law",
                "legal_code": self._extract_law_number(document),
                "title": self._extract_law_name(document),
                "source_file": document.file_path,
            },
            "legal_metadata": {
                "issued_by": "Quốc hội",
                "issuing_level": 2,
                "promulgation_date": self._extract_promulgation_date(document),
                "effective_date": self._extract_effective_date(document),
                "status": self._determine_status(document),
            }
        }
        
        # Add extended metadata
        metadata["extended_metadata"] = {
            "law": self.get_extended_metadata(document)
        }
        
        return metadata
    
    def get_extended_metadata(self, document: Document) -> Dict:
        """
        Extract Law-specific extended metadata.
        """
        return {
            "law_name": self._extract_law_name(document),
            "law_category": self._extract_category(document),
            "session": self._extract_session_info(document),
            "vote_result": self._extract_vote_result(document),
            "subject_area": self._extract_subject_areas(document),
        }
    
    def extract_content(self, document: Document) -> str:
        """Extract text content with hierarchy preservation"""
        return self._extract_hierarchical_content(document)
    
    def _init_chunker(self) -> ChunkingStrategy:
        """Use hierarchical chunking for laws"""
        return HierarchicalChunker(
            max_tokens=512,
            overlap=50,
            hierarchy_levels=["Phần", "Chương", "Mục", "Điều", "Khoản", "Điểm"]
        )
    
    # ========================================
    # PRIVATE HELPER METHODS
    # ========================================
    
    def _extract_law_number(self, document: Document) -> str:
        """Extract law number using regex: XX/YYYY/QHXX"""
        import re
        pattern = r'(\d+/\d{4}/QH\d+)'
        match = re.search(pattern, document.text)
        if match:
            return match.group(1)
        raise ValueError("Cannot extract law number")
    
    def _extract_law_name(self, document: Document) -> str:
        """Extract law name (usually in title)"""
        # Implementation here
        pass
    
    def _extract_promulgation_date(self, document: Document) -> str:
        """Extract promulgation date in ISO format"""
        # Implementation here
        pass
    
    def _extract_hierarchical_content(self, document: Document) -> str:
        """
        Extract content while preserving hierarchy markers.
        
        Example:
        PHẦN THỨ HAI
        CHƯƠNG II
        Điều 15. ...
        """
        # Implementation here
        pass


# src/preprocessing/pipelines/decree_pipeline.py
class DecreePipeline(BaseLegalPipeline):
    """Pipeline for Nghị định (Government Decrees)"""
    
    def get_doc_type(self) -> DocType:
        return DocType.DECREE
    
    def extract_metadata(self, document: Document) -> Dict:
        metadata = {
            "document_info": {
                "doc_type": "decree",
                "legal_code": self._extract_decree_number(document),
                "title": self._extract_decree_name(document),
            },
            "legal_metadata": {
                "issued_by": "Chính phủ",
                "issuing_level": 3,
                "signer": self._extract_signer(document),
            }
        }
        
        # Add implements relationship
        metadata["relationships"] = {
            "implements": self._extract_parent_law(document)
        }
        
        return metadata


# src/preprocessing/pipelines/circular_pipeline.py
class CircularPipeline(BaseLegalPipeline):
    """Pipeline for Thông tư (Circulars)"""
    
    def get_doc_type(self) -> DocType:
        return DocType.CIRCULAR


# src/preprocessing/pipelines/decision_pipeline.py
class DecisionPipeline(BaseLegalPipeline):
    """Pipeline for Quyết định (Decisions) - NEW"""
    
    def get_doc_type(self) -> DocType:
        return DocType.DECISION
    
    def extract_metadata(self, document: Document) -> Dict:
        metadata = {
            "document_info": {
                "doc_type": "decision",
                "legal_code": self._extract_decision_number(document),
            },
            "legal_metadata": {
                "issued_by": self._extract_issuing_authority(document),
                "issuing_level": 4,
            }
        }
        
        metadata["extended_metadata"] = {
            "decision": {
                "decision_type": self._classify_decision_type(document),
                "subject_matter": self._extract_subject_matter(document),
                "execution_deadline": self._extract_deadline(document),
                "legal_basis": self._extract_legal_basis(document),
            }
        }
        
        return metadata


# src/preprocessing/pipelines/bidding_pipeline.py
class BiddingPipeline(BaseLegalPipeline):
    """Pipeline for Bidding Templates"""
    
    def get_doc_type(self) -> DocType:
        return DocType.BIDDING
    
    def extract_metadata(self, document: Document) -> Dict:
        metadata = {
            "document_info": {
                "doc_type": "bidding_template",
                "legal_code": None,  # No legal code for templates
            },
            "legal_metadata": {
                "issued_by": "Bộ Kế hoạch và Đầu tư",
                "issuing_level": 5,
                "status": "active",
            }
        }
        
        metadata["extended_metadata"] = {
            "bidding": {
                "template_type": self._classify_template_type(document),
                "template_code": self._extract_template_code(document),
                "procurement_method": self._extract_procurement_method(document),
            }
        }
        
        return metadata


# src/preprocessing/pipelines/report_pipeline.py
class ReportPipeline(BaseLegalPipeline):
    """Pipeline for Report Templates - NEW"""
    
    def get_doc_type(self) -> DocType:
        return DocType.REPORT


# src/preprocessing/pipelines/exam_pipeline.py
class ExamPipeline(BaseLegalPipeline):
    """Pipeline for Exam Questions - NEW"""
    
    def get_doc_type(self) -> DocType:
        return DocType.EXAM
```

---

## 🔌 REUSABLE COMPONENTS

### 1. Document Loaders (`src/preprocessing/loaders/`)

```python
# src/preprocessing/loaders/base.py
from abc import ABC, abstractmethod
from pathlib import Path

class DocumentLoader(ABC):
    """Base class for document loaders"""
    
    @abstractmethod
    def load(self, file_path: Path) -> Document:
        """Load document from file"""
        pass
    
    @abstractmethod
    def supports(self, file_path: Path) -> bool:
        """Check if this loader supports the file type"""
        pass


# src/preprocessing/loaders/docx_loader.py
from docx import Document as DocxDocument

class DocxLoader(DocumentLoader):
    """Loader for .docx files"""
    
    def load(self, file_path: Path) -> Document:
        docx = DocxDocument(file_path)
        
        # Extract text with formatting
        text = self._extract_text_with_hierarchy(docx)
        
        # Extract tables
        tables = self._extract_tables(docx)
        
        # Extract metadata
        metadata = self._extract_docx_metadata(docx)
        
        return Document(
            file_path=file_path,
            text=text,
            tables=tables,
            metadata=metadata,
            format="docx"
        )
    
    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == '.docx'
    
    def _extract_text_with_hierarchy(self, docx: DocxDocument) -> str:
        """
        Extract text while preserving hierarchy markers.
        
        Identifies:
        - Phần (by style or CAPS)
        - Chương (by style or pattern)
        - Điều (by regex: "Điều \d+")
        - Khoản (by numbering)
        """
        text_parts = []
        
        for para in docx.paragraphs:
            # Check if this is a hierarchy marker
            if self._is_phan(para):
                text_parts.append(f"\n\n[PHAN] {para.text}\n")
            elif self._is_chuong(para):
                text_parts.append(f"\n[CHUONG] {para.text}\n")
            elif self._is_dieu(para):
                text_parts.append(f"\n[DIEU] {para.text}\n")
            else:
                text_parts.append(para.text)
        
        return '\n'.join(text_parts)


# src/preprocessing/loaders/pdf_loader.py
import fitz  # PyMuPDF

class PdfLoader(DocumentLoader):
    """Loader for PDF files"""
    
    def load(self, file_path: Path) -> Document:
        pdf = fitz.open(file_path)
        
        text = ""
        for page in pdf:
            text += page.get_text()
        
        return Document(
            file_path=file_path,
            text=text,
            format="pdf"
        )
    
    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == '.pdf'
```

### 2. Chunking Strategies (`src/chunking/strategies/`)

```python
# src/chunking/strategies/hierarchical_chunker.py
from typing import List
import re

class HierarchicalChunker(ChunkingStrategy):
    """
    Chunk documents based on Vietnamese legal hierarchy.
    
    Hierarchy levels:
    0. Phần (Part)
    1. Chương (Chapter)
    2. Mục (Section)
    3. Điều (Article)
    4. Khoản (Paragraph)
    5. Điểm (Point)
    """
    
    def __init__(
        self,
        max_tokens: int = 512,
        overlap: int = 50,
        hierarchy_levels: List[str] = None
    ):
        self.max_tokens = max_tokens
        self.overlap = overlap
        self.hierarchy_levels = hierarchy_levels or [
            "Phần", "Chương", "Mục", "Điều", "Khoản", "Điểm"
        ]
    
    def chunk(self, content: str, metadata: Dict) -> List[Chunk]:
        """
        Split content into chunks based on hierarchy.
        
        Strategy:
        1. Split by Điều (Article) first
        2. If Điều > max_tokens, split by Khoản (Paragraph)
        3. If Khoản > max_tokens, split by sentences
        4. Maintain hierarchy context in each chunk
        """
        chunks = []
        
        # Parse hierarchy
        hierarchy = self._parse_hierarchy(content)
        
        # Split by articles
        articles = self._split_by_pattern(content, r'Điều \d+\.')
        
        for article in articles:
            article_chunks = self._chunk_article(article, hierarchy)
            chunks.extend(article_chunks)
        
        return chunks
    
    def _parse_hierarchy(self, content: str) -> Dict:
        """
        Extract hierarchy structure from content.
        
        Returns:
        {
            "phan": "PHẦN THỨ HAI",
            "chuong": "CHƯƠNG II",
            "muc": "Mục 1",
            "dieu": "Điều 15"
        }
        """
        hierarchy = {}
        
        # Find Phần
        phan_match = re.search(r'PHẦN (THỨ )?\w+', content)
        if phan_match:
            hierarchy["phan"] = phan_match.group(0)
        
        # Find Chương
        chuong_match = re.search(r'CHƯƠNG [IVXLC]+', content)
        if chuong_match:
            hierarchy["chuong"] = chuong_match.group(0)
        
        # Find Mục
        muc_match = re.search(r'Mục \d+', content)
        if muc_match:
            hierarchy["muc"] = muc_match.group(0)
        
        return hierarchy
    
    def _chunk_article(self, article: str, hierarchy: Dict) -> List[Chunk]:
        """Chunk a single article"""
        chunks = []
        
        # Extract article number
        article_match = re.match(r'Điều (\d+)\.', article)
        article_num = article_match.group(1) if article_match else "0"
        
        # Split by paragraphs (Khoản)
        paragraphs = self._split_by_pattern(article, r'\d+\.')
        
        for idx, para in enumerate(paragraphs):
            chunk = Chunk(
                text=para,
                hierarchy_path=[
                    hierarchy.get("phan", ""),
                    hierarchy.get("chuong", ""),
                    hierarchy.get("muc", ""),
                    f"Điều {article_num}",
                    f"Khoản {idx + 1}"
                ],
                hierarchy_level=4,
                metadata={
                    "article": f"Điều {article_num}",
                    "paragraph": f"Khoản {idx + 1}"
                }
            )
            chunks.append(chunk)
        
        return chunks


# src/chunking/strategies/semantic_chunker.py
class SemanticChunker(ChunkingStrategy):
    """
    Chunk based on semantic similarity.
    
    Uses sentence embeddings to group semantically related sentences.
    """
    
    def __init__(self, embedding_model, similarity_threshold: float = 0.7):
        self.embedding_model = embedding_model
        self.similarity_threshold = similarity_threshold
    
    def chunk(self, content: str, metadata: Dict) -> List[Chunk]:
        # Split into sentences
        sentences = self._split_sentences(content)
        
        # Compute embeddings
        embeddings = self.embedding_model.encode(sentences)
        
        # Group by similarity
        chunks = self._group_by_similarity(sentences, embeddings)
        
        return chunks
```

### 3. Metadata Enrichment (`src/preprocessing/enrichment/`)

```python
# src/preprocessing/enrichment/semantic_enricher.py
class SemanticEnricher:
    """
    Add semantic metadata to chunks.
    
    Features:
    - Named entity extraction
    - Legal concept tagging
    - Keyword extraction
    - Subject area classification
    """
    
    def __init__(self):
        self.ner_model = self._load_ner_model()
        self.concept_extractor = LegalConceptExtractor()
        self.keyword_extractor = KeywordExtractor()
    
    def enrich(self, chunk: Chunk) -> UnifiedLegalChunk:
        """Add semantic metadata to chunk"""
        
        # Extract named entities
        entities = self.ner_model.extract(chunk.text)
        
        # Extract legal concepts
        concepts = self.concept_extractor.extract(chunk.text)
        
        # Extract keywords
        keywords = self.keyword_extractor.extract(chunk.text)
        
        # Add to chunk metadata
        chunk.semantic_metadata = {
            "named_entities": entities,
            "legal_concepts": concepts,
            "keywords": keywords,
            "subject_areas": self._classify_subject_areas(concepts)
        }
        
        return chunk


# src/preprocessing/enrichment/relation_resolver.py
class RelationResolver:
    """
    Resolve relationships between documents.
    
    Features:
    - Find parent laws
    - Find superseded documents
    - Find related documents
    - Build citation graph
    """
    
    def __init__(self, document_database):
        self.db = document_database
    
    def resolve_relationships(
        self, 
        chunk: UnifiedLegalChunk
    ) -> UnifiedLegalChunk:
        """
        Resolve document relationships.
        
        For Decrees/Circulars:
        - Find parent law (implements)
        
        For all:
        - Find superseded documents
        - Find related documents via citations
        """
        
        # Find parent law
        if chunk.document_info.doc_type in ["decree", "circular"]:
            parent_law = self._find_parent_law(chunk)
            chunk.relationships.implements = parent_law
        
        # Find superseded documents
        superseded = self._find_superseded_documents(chunk)
        chunk.relationships.supersedes = superseded
        
        # Extract citations
        citations = self._extract_citations(chunk.text)
        chunk.relationships.related_documents = citations
        
        return chunk
```

### 4. Quality Analysis (`src/preprocessing/quality/`)

```python
# src/preprocessing/quality/quality_analyzer.py
class QualityAnalyzer:
    """
    Analyze chunk quality.
    
    Metrics:
    - Completeness: All required metadata present
    - Confidence: Extraction confidence
    - Consistency: Cross-field validation
    - Readability: Text quality
    """
    
    def analyze(self, chunk: UnifiedLegalChunk) -> QualityScore:
        scores = {
            "completeness": self._check_completeness(chunk),
            "confidence": self._check_confidence(chunk),
            "consistency": self._check_consistency(chunk),
            "readability": self._check_readability(chunk)
        }
        
        return QualityScore(
            overall=sum(scores.values()) / len(scores),
            **scores
        )
    
    def _check_completeness(self, chunk: UnifiedLegalChunk) -> float:
        """Check if all required fields are present"""
        required_fields = [
            "document_info.doc_id",
            "document_info.title",
            "legal_metadata.issued_by",
            "legal_metadata.effective_date",
            "content_structure.hierarchy_path"
        ]
        
        present = 0
        for field_path in required_fields:
            if self._has_field(chunk, field_path):
                present += 1
        
        return present / len(required_fields)
    
    def _check_confidence(self, chunk: UnifiedLegalChunk) -> float:
        """
        Check extraction confidence.
        
        Factors:
        - Regex match confidence
        - NER model confidence
        - Validation passed
        """
        confidence_scores = []
        
        # Legal code format validation
        if chunk.legal_metadata.legal_code:
            if re.match(r'^\d+/\d{4}/[A-ZĐ\-]+$', chunk.legal_metadata.legal_code):
                confidence_scores.append(1.0)
            else:
                confidence_scores.append(0.5)
        
        # Date format validation
        if chunk.legal_metadata.effective_date:
            if re.match(r'^\d{4}-\d{2}-\d{2}$', chunk.legal_metadata.effective_date):
                confidence_scores.append(1.0)
            else:
                confidence_scores.append(0.5)
        
        # Validation passed
        if chunk.quality_metrics.validation_passed:
            confidence_scores.append(1.0)
        else:
            confidence_scores.append(0.0)
        
        return sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
```

---

## 🎛️ ORCHESTRATION

### Pipeline Orchestrator (`src/preprocessing/orchestrator.py`)

```python
class PipelineOrchestrator:
    """
    Orchestrate multiple preprocessing pipelines.
    
    Features:
    - Auto-detect document type
    - Route to appropriate pipeline
    - Parallel processing
    - Error recovery
    - Progress tracking
    """
    
    def __init__(self, config: OrchestratorConfig):
        self.config = config
        self.pipelines = self._init_pipelines()
        self.logger = logging.getLogger("Orchestrator")
    
    def _init_pipelines(self) -> Dict[DocType, BaseLegalPipeline]:
        """Initialize all 7 pipelines"""
        return {
            DocType.LAW: LawPipeline(self.config.law_config),
            DocType.DECREE: DecreePipeline(self.config.decree_config),
            DocType.CIRCULAR: CircularPipeline(self.config.circular_config),
            DocType.DECISION: DecisionPipeline(self.config.decision_config),
            DocType.BIDDING: BiddingPipeline(self.config.bidding_config),
            DocType.REPORT: ReportPipeline(self.config.report_config),
            DocType.EXAM: ExamPipeline(self.config.exam_config),
        }
    
    def process_batch(
        self, 
        file_paths: List[Path],
        parallel: bool = True
    ) -> BatchResult:
        """
        Process a batch of documents.
        
        Args:
            file_paths: List of document paths
            parallel: Enable parallel processing
        
        Returns:
            BatchResult with success/failure counts
        """
        self.logger.info(f"Processing {len(file_paths)} documents")
        
        if parallel:
            results = self._process_parallel(file_paths)
        else:
            results = self._process_sequential(file_paths)
        
        return BatchResult(
            total=len(file_paths),
            success=sum(1 for r in results if r.success),
            failed=sum(1 for r in results if not r.success),
            results=results
        )
    
    def _process_parallel(self, file_paths: List[Path]) -> List[PipelineResult]:
        """Process documents in parallel using multiprocessing"""
        from multiprocessing import Pool
        
        with Pool(processes=self.config.num_workers) as pool:
            results = pool.map(self._process_single, file_paths)
        
        return results
    
    def _process_single(self, file_path: Path) -> PipelineResult:
        """Process a single document"""
        try:
            # Auto-detect document type
            doc_type = self._detect_doc_type(file_path)
            
            # Get appropriate pipeline
            pipeline = self.pipelines[doc_type]
            
            # Process
            result = pipeline.process(file_path)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to process {file_path}: {str(e)}")
            return PipelineResult(
                success=False,
                chunks=[],
                metadata={},
                errors=[str(e)]
            )
    
    def _detect_doc_type(self, file_path: Path) -> DocType:
        """
        Auto-detect document type from filename or content.
        
        Rules:
        - Path contains "Luat chinh" → LAW
        - Path contains "Nghi dinh" → DECREE
        - Path contains "Thong tu" → CIRCULAR
        - Path contains "Quyet dinh" → DECISION
        - Path contains "Ho so moi thau" → BIDDING
        - Path contains "Mau bao cao" → REPORT
        - Path contains "Cau hoi thi" → EXAM
        """
        path_str = str(file_path).lower()
        
        if "luat" in path_str or "law" in path_str:
            return DocType.LAW
        elif "nghi dinh" in path_str or "decree" in path_str:
            return DocType.DECREE
        elif "thong tu" in path_str or "circular" in path_str:
            return DocType.CIRCULAR
        elif "quyet dinh" in path_str or "decision" in path_str:
            return DocType.DECISION
        elif "ho so" in path_str or "bidding" in path_str:
            return DocType.BIDDING
        elif "mau bao cao" in path_str or "report" in path_str:
            return DocType.REPORT
        elif "cau hoi" in path_str or "exam" in path_str:
            return DocType.EXAM
        
        # Default: try to detect from content
        return self._detect_from_content(file_path)
```

---

## 📁 DIRECTORY STRUCTURE

```
src/preprocessing/
├── __init__.py
│
├── schema/                          # Schema definitions
│   ├── __init__.py
│   ├── unified_schema.py           # UnifiedLegalChunk
│   ├── enums.py                    # DocType, LegalStatus, etc.
│   ├── validators.py               # SchemaValidator
│   └── models/                     # Pydantic models
│       ├── document_info.py
│       ├── legal_metadata.py
│       ├── content_structure.py
│       ├── relationships.py
│       ├── processing_metadata.py
│       ├── quality_metrics.py
│       └── extended/               # Extended metadata models
│           ├── law.py
│           ├── decree.py
│           ├── circular.py
│           ├── decision.py
│           ├── bidding.py
│           ├── report.py
│           └── exam.py
│
├── base/                           # Base classes
│   ├── __init__.py
│   ├── legal_pipeline.py          # BaseLegalPipeline
│   ├── document.py                # Document class
│   ├── chunk.py                   # Chunk class
│   └── config.py                  # PipelineConfig
│
├── pipelines/                      # Document-specific pipelines
│   ├── __init__.py
│   ├── law_pipeline.py            # LawPipeline
│   ├── decree_pipeline.py         # DecreePipeline
│   ├── circular_pipeline.py       # CircularPipeline
│   ├── decision_pipeline.py       # DecisionPipeline (NEW)
│   ├── bidding_pipeline.py        # BiddingPipeline
│   ├── report_pipeline.py         # ReportPipeline (NEW)
│   └── exam_pipeline.py           # ExamPipeline (NEW)
│
├── loaders/                        # Document loaders
│   ├── __init__.py
│   ├── base.py                    # DocumentLoader (ABC)
│   ├── docx_loader.py             # DocxLoader
│   ├── pdf_loader.py              # PdfLoader
│   ├── html_loader.py             # HtmlLoader
│   └── excel_loader.py            # ExcelLoader (for exam questions)
│
├── extractors/                     # Metadata extractors
│   ├── __init__.py
│   ├── metadata_extractor.py      # Base metadata extraction
│   ├── legal_code_extractor.py    # Extract legal codes
│   ├── date_extractor.py          # Extract dates
│   ├── hierarchy_extractor.py     # Extract hierarchy
│   └── table_extractor.py         # Extract tables
│
├── chunking/                       # Chunking strategies
│   ├── __init__.py
│   ├── hierarchical_chunker.py    # HierarchicalChunker
│   ├── semantic_chunker.py        # SemanticChunker
│   ├── fixed_size_chunker.py      # FixedSizeChunker
│   └── custom_chunker.py          # CustomChunker
│
├── enrichment/                     # Metadata enrichment
│   ├── __init__.py
│   ├── semantic_enricher.py       # SemanticEnricher
│   ├── relation_resolver.py       # RelationResolver
│   ├── concept_extractor.py       # LegalConceptExtractor
│   ├── keyword_extractor.py       # KeywordExtractor
│   └── ner/                       # Named Entity Recognition
│       ├── __init__.py
│       ├── legal_ner.py           # Legal NER model
│       └── entity_linker.py       # Entity linking
│
├── quality/                        # Quality analysis
│   ├── __init__.py
│   ├── quality_analyzer.py        # QualityAnalyzer
│   ├── validators/                # Specific validators
│   │   ├── date_validator.py
│   │   ├── code_validator.py
│   │   └── hierarchy_validator.py
│   └── metrics/                   # Quality metrics
│       ├── completeness.py
│       ├── confidence.py
│       └── consistency.py
│
├── orchestrator.py                 # PipelineOrchestrator
├── cli.py                         # CLI interface
└── utils/                         # Utilities
    ├── __init__.py
    ├── text_utils.py              # Text processing utils
    ├── regex_patterns.py          # Vietnamese legal regex
    └── file_utils.py              # File handling utils

```

---

## 🚀 IMPLEMENTATION ROADMAP

### Phase 1: Foundation (Week 1-2)
```python
Week 1:
□ Setup schema module
  □ Create unified_schema.py with all 21 core fields
  □ Create enums.py with Vietnamese legal enums
  □ Create Pydantic models for all 7 document types
  □ Unit tests for schema validation

Week 2:
□ Setup base module
  □ Create BaseLegalPipeline with 7 stages
  □ Create Document and Chunk classes
  □ Create PipelineConfig
  □ Integration tests for base pipeline
```

### Phase 2: Core Components (Week 3-4)
```python
Week 3:
□ Implement loaders
  □ DocxLoader with hierarchy preservation
  □ PdfLoader with OCR support
  □ ExcelLoader for exam questions
  
Week 4:
□ Implement chunking strategies
  □ HierarchicalChunker for legal documents
  □ SemanticChunker for general text
  □ Unit tests for all chunkers
```

### Phase 3: Pipeline Implementation (Week 5-8)
```python
Week 5: Law & Decree Pipelines
□ LawPipeline
  □ Metadata extraction
  □ Hierarchy parsing
  □ Extended metadata
  □ Integration tests
  
□ DecreePipeline
  □ Similar to LawPipeline
  □ Parent law detection
  
Week 6: Circular & Decision Pipelines
□ CircularPipeline
□ DecisionPipeline (NEW)
  
Week 7: Bidding & Report Pipelines
□ BiddingPipeline (refactor existing)
□ ReportPipeline (NEW)
  
Week 8: Exam Pipeline
□ ExamPipeline (NEW)
  □ Excel parsing
  □ Question extraction
  □ Answer key handling
```

### Phase 4: Enrichment & Quality (Week 9-10)
```python
Week 9:
□ Semantic enrichment
  □ Legal concept extraction
  □ Named entity recognition
  □ Keyword extraction
  
Week 10:
□ Quality analysis
  □ Completeness checker
  □ Confidence scorer
  □ Consistency validator
```

### Phase 5: Orchestration & Migration (Week 11-12)
```python
Week 11:
□ Pipeline orchestrator
  □ Auto document type detection
  □ Parallel processing
  □ Error recovery
  
Week 12:
□ Data migration
  □ Migrate existing 4 pipelines
  □ Validate migrated data
  □ Quality checks
```

### Phase 6: Testing & Documentation (Week 13-14)
```python
Week 13:
□ End-to-end testing
  □ Test all 7 pipelines
  □ Performance benchmarks
  □ Load testing
  
Week 14:
□ Documentation
  □ API documentation
  □ User guide
  □ Developer guide
□ Production deployment
```

---

## 🔄 MIGRATION STRATEGY

### Step 1: Parallel Run (Week 11)
```python
# Run both old and new pipelines
for document in documents:
    old_result = old_pipeline.process(document)
    new_result = new_pipeline.process(document)
    
    # Compare results
    differences = compare_results(old_result, new_result)
    
    # Log differences
    migration_logger.log(differences)
    
    # Use new result if validation passes
    if new_result.quality_metrics.validation_passed:
        use_result = new_result
    else:
        use_result = old_result
```

### Step 2: Gradual Cutover (Week 12)
```python
# Gradually increase traffic to new pipeline
traffic_split = {
    "old_pipeline": 80,  # Week 12, Day 1
    "new_pipeline": 20
}

# Monitor metrics
metrics = {
    "processing_time": [],
    "quality_scores": [],
    "error_rates": []
}

# Adjust split based on metrics
if metrics["error_rates"]["new_pipeline"] < 0.01:
    traffic_split["new_pipeline"] += 20
```

### Step 3: Full Cutover (Week 13)
```python
# Switch 100% to new pipeline
USE_NEW_PIPELINE = True

# Keep old pipeline for emergency rollback
ENABLE_ROLLBACK = True
ROLLBACK_THRESHOLD = 0.05  # 5% error rate
```

---

## 📊 MONITORING & METRICS

```python
# src/preprocessing/monitoring.py
class PipelineMonitor:
    """Monitor pipeline health and performance"""
    
    def __init__(self):
        self.metrics = {
            "documents_processed": 0,
            "chunks_created": 0,
            "avg_processing_time": 0.0,
            "avg_quality_score": 0.0,
            "error_count": 0,
            "validation_failures": 0,
        }
    
    def record_pipeline_run(self, result: PipelineResult):
        """Record metrics from pipeline run"""
        self.metrics["documents_processed"] += 1
        self.metrics["chunks_created"] += len(result.chunks)
        
        if result.success:
            avg_quality = sum(
                c.quality_metrics.completeness_score 
                for c in result.chunks
            ) / len(result.chunks)
            
            self.metrics["avg_quality_score"] = (
                self.metrics["avg_quality_score"] * 0.9 + avg_quality * 0.1
            )
        else:
            self.metrics["error_count"] += 1
    
    def get_dashboard_metrics(self) -> Dict:
        """Return metrics for dashboard"""
        return {
            "total_documents": self.metrics["documents_processed"],
            "total_chunks": self.metrics["chunks_created"],
            "success_rate": 1 - (self.metrics["error_count"] / max(self.metrics["documents_processed"], 1)),
            "avg_quality": self.metrics["avg_quality_score"],
            "health_status": self._get_health_status()
        }
    
    def _get_health_status(self) -> str:
        """Determine overall health status"""
        success_rate = 1 - (self.metrics["error_count"] / max(self.metrics["documents_processed"], 1))
        avg_quality = self.metrics["avg_quality_score"]
        
        if success_rate > 0.95 and avg_quality > 0.8:
            return "HEALTHY"
        elif success_rate > 0.9 and avg_quality > 0.7:
            return "WARNING"
        else:
            return "CRITICAL"
```

---

## 🎯 SUCCESS CRITERIA

### Performance Metrics
- [ ] **Processing speed**: <100ms per chunk
- [ ] **Throughput**: 1000+ documents/hour
- [ ] **Memory**: <2GB for batch processing
- [ ] **Scalability**: Linear scaling with workers

### Quality Metrics
- [ ] **Validation success**: >98%
- [ ] **Completeness score**: >0.9
- [ ] **Confidence score**: >0.85
- [ ] **Data loss**: <1%

### Business Metrics
- [ ] **Coverage**: 100% of 7 document types
- [ ] **Consistency**: 100% unified schema adoption
- [ ] **Maintainability**: <50% code duplication
- [ ] **Extensibility**: New doc type in <1 week

---

## 🔐 SECURITY & COMPLIANCE

```python
# src/preprocessing/security/

class DataProtection:
    """Protect sensitive data during preprocessing"""
    
    def __init__(self):
        self.encryption_key = self._load_encryption_key()
    
    def encrypt_sensitive_fields(self, chunk: UnifiedLegalChunk) -> UnifiedLegalChunk:
        """
        Encrypt sensitive fields.
        
        Sensitive fields:
        - Exam questions: correct_answer
        - Decisions: personal information
        """
        if chunk.document_info.doc_type == DocType.EXAM:
            # Encrypt answer key
            if "exam" in chunk.extended_metadata:
                chunk.extended_metadata["exam"]["correct_answer"] = self._encrypt(
                    chunk.extended_metadata["exam"]["correct_answer"]
                )
        
        return chunk
    
    def audit_log(self, operation: str, user: str, chunk_id: str):
        """Log all operations for audit trail"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "user": user,
            "chunk_id": chunk_id
        }
        
        # Write to audit log
        self._write_audit_log(log_entry)
```

---

**Document Status**: ✅ Architecture Design Complete  
**Next Steps**: Begin Phase 1 Implementation  
**Dependencies**: DEEP_ANALYSIS_REPORT.md, Unified Schema

