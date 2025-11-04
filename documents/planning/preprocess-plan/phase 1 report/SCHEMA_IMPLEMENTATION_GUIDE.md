# 📐 SCHEMA IMPLEMENTATION GUIDE
## Hướng dẫn chi tiết triển khai Unified Schema

**Ngày tạo**: 31/10/2025  
**Phiên bản**: 1.0  
**Liên kết**: DEEP_ANALYSIS_REPORT.md

---

## 📋 MỤC LỤC

1. [Unified Schema Definition](#unified-schema-definition)
2. [Implementation Examples](#implementation-examples)
3. [Migration Mappings](#migration-mappings)
4. [Validation Rules](#validation-rules)
5. [Code Samples](#code-samples)

---

## 🎯 UNIFIED SCHEMA DEFINITION

### Complete Schema Specification v1.0

```python
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class DocType(str, Enum):
    """Document type enumeration"""
    LAW = "law"
    DECREE = "decree"
    CIRCULAR = "circular"
    BIDDING_TEMPLATE = "bidding_template"

class LegalStatus(str, Enum):
    """Legal document status"""
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REVOKED = "revoked"
    DRAFT = "draft"

class CitationType(str, Enum):
    """Citation relationship types"""
    IMPLEMENTS = "implements"
    REFERENCES = "references"
    SUPERSEDES = "supersedes"
    AMENDS = "amends"

# ========== NESTED MODELS ==========

class Citation(BaseModel):
    """Citation to another document"""
    cited_doc_id: str = Field(..., description="ID of cited document")
    citation_type: CitationType
    cited_article: Optional[str] = Field(None, description="Specific article cited")
    citation_context: Optional[str] = Field(None, max_length=500)

class RelatedDocument(BaseModel):
    """Related document reference"""
    doc_id: str
    relationship: str = Field(..., description="Type of relationship")
    description: Optional[str] = None

class StatusHistoryEntry(BaseModel):
    """Status change history"""
    status: LegalStatus
    date: datetime
    note: Optional[str] = None

# ========== MAIN SECTIONS ==========

class DocumentInfo(BaseModel):
    """Core document identification"""
    id: str = Field(..., description="Unique document identifier")
    title: str = Field(..., min_length=1, max_length=500)
    doc_type: DocType
    legal_code: Optional[str] = Field(None, description="Official code (e.g., 43/2013/QH13)")
    source: str = Field(..., description="File path or data source")
    url: Optional[str] = Field(None, description="Original URL if crawled")
    
    @validator('legal_code')
    def validate_legal_code(cls, v, values):
        """Validate legal code format"""
        if v and values.get('doc_type') in [DocType.LAW, DocType.DECREE, DocType.CIRCULAR]:
            # Basic format check for Vietnamese legal codes
            import re
            if not re.match(r'\d+/\d{4}/[A-Z\-]+', v):
                raise ValueError(f"Invalid legal code format: {v}")
        return v

class LegalMetadata(BaseModel):
    """Legal document metadata"""
    issued_by: str = Field(..., description="Issuing authority")
    effective_date: datetime = Field(..., description="When document takes effect")
    expiry_date: Optional[datetime] = Field(None, description="When document expires")
    status: LegalStatus = Field(default=LegalStatus.ACTIVE)
    legal_level: int = Field(..., ge=1, le=5, description="1=highest (Law), 5=lowest")
    subject_area: List[str] = Field(default_factory=list, description="Topics covered")
    keywords: List[str] = Field(default_factory=list, description="Searchable keywords")
    
    # Temporal validity tracking
    status_history: List[StatusHistoryEntry] = Field(default_factory=list)
    
    @validator('expiry_date')
    def expiry_after_effective(cls, v, values):
        """Ensure expiry date is after effective date"""
        if v and 'effective_date' in values and v <= values['effective_date']:
            raise ValueError("Expiry date must be after effective date")
        return v

class ContentStructure(BaseModel):
    """Hierarchical structure of document"""
    chapter: Optional[str] = Field(None, description="Chapter (Chương)")
    section: Optional[str] = Field(None, description="Section (Mục)")
    article: Optional[str] = Field(None, description="Article (Điều)")
    paragraph: Optional[str] = Field(None, description="Paragraph (Khoản)")
    point: Optional[str] = Field(None, description="Point (Điểm)")
    
    hierarchy_level: int = Field(..., ge=0, le=5, description="Depth in hierarchy")
    hierarchy_path: List[str] = Field(
        default_factory=list,
        description="Full path: ['Chương II', 'Điều 15', 'Khoản 2']"
    )
    
    # Structured IDs for easy querying
    chapter_id: Optional[str] = None
    article_id: Optional[str] = None
    paragraph_id: Optional[str] = None
    point_id: Optional[str] = None

class Relationships(BaseModel):
    """Document relationships"""
    supersedes: List[str] = Field(default_factory=list, description="Documents this replaces")
    implements: Optional[str] = Field(None, description="Parent law implemented")
    related_documents: List[RelatedDocument] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)

class ProcessingMetadata(BaseModel):
    """Processing and chunking metadata"""
    chunk_id: str = Field(..., description="Unique chunk identifier")
    chunk_index: int = Field(..., ge=0, description="Position in document")
    processing_date: datetime = Field(default_factory=datetime.utcnow)
    pipeline_version: str = Field(..., description="Pipeline version used")
    chunking_strategy: str = Field(..., description="Strategy used for chunking")

class QualityMetrics(BaseModel):
    """Quality and confidence metrics"""
    text_length: int = Field(..., ge=0, description="Character count")
    token_count: Optional[int] = Field(None, ge=0, description="Token count for embedding")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence")
    quality_flags: Dict[str, bool] = Field(default_factory=dict)
    semantic_tags: List[str] = Field(default_factory=list)

class SemanticEnrichment(BaseModel):
    """Semantic analysis results (optional, for advanced features)"""
    legal_concepts: List[str] = Field(default_factory=list)
    named_entities: Dict[str, List[str]] = Field(default_factory=dict)
    key_phrases: List[str] = Field(default_factory=list)

# ========== EXTENDED METADATA ==========

class BiddingExtendedMetadata(BaseModel):
    """Bidding-specific fields"""
    template_type: Optional[str] = None
    section_type: Optional[str] = None
    requirements_level: Optional[str] = None
    evaluation_criteria: Optional[List[str]] = None
    contractor_type: Optional[str] = None
    procurement_method: Optional[str] = None
    technical_complexity: Optional[str] = None

class CircularExtendedMetadata(BaseModel):
    """Circular-specific fields"""
    regulation_type: Optional[str] = None
    guidance_scope: Optional[str] = None

class DecreeExtendedMetadata(BaseModel):
    """Decree-specific fields"""
    signer: Optional[str] = None
    scope_of_application: Optional[str] = None
    target_entities: List[str] = Field(default_factory=list)
    regulatory_level: Optional[str] = None

# ========== MAIN UNIFIED CHUNK MODEL ==========

class UnifiedLegalChunk(BaseModel):
    """
    Unified schema for all legal document chunks
    Version 1.0.0
    """
    schema_version: str = Field(default="1.0.0", const=True)
    
    # Core sections (required)
    document_info: DocumentInfo
    legal_metadata: LegalMetadata
    content_structure: ContentStructure
    relationships: Relationships
    processing_metadata: ProcessingMetadata
    quality_metrics: QualityMetrics
    
    # Chunk content
    text: str = Field(..., min_length=1, description="Chunk text content")
    
    # Optional advanced features
    semantic_enrichment: Optional[SemanticEnrichment] = None
    
    # Extended metadata (document-type specific)
    extended_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Pipeline-specific additional fields"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "schema_version": "1.0.0",
                "document_info": {
                    "id": "law_43_2013_qh13",
                    "title": "Luật Đấu thầu",
                    "doc_type": "law",
                    "legal_code": "43/2013/QH13",
                    "source": "/data/processed/laws/law_43_2013.md",
                    "url": "https://thuvienphapluat.vn/..."
                },
                "legal_metadata": {
                    "issued_by": "Quốc hội",
                    "effective_date": "2014-07-01T00:00:00Z",
                    "status": "active",
                    "legal_level": 1,
                    "subject_area": ["đấu thầu", "mua sắm công"]
                },
                # ... other fields
            }
        }
```

---

## 💻 IMPLEMENTATION EXAMPLES

### Example 1: Law Document Chunk

```json
{
  "schema_version": "1.0.0",
  "document_info": {
    "id": "law_43_2013_qh13",
    "title": "Luật Đấu thầu",
    "doc_type": "law",
    "legal_code": "43/2013/QH13",
    "source": "/data/processed/laws/law_43_2013.md",
    "url": "https://thuvienphapluat.vn/van-ban/Dau-thau/Luat-Dau-thau-2013-193569.aspx"
  },
  "legal_metadata": {
    "issued_by": "Quốc hội",
    "effective_date": "2014-07-01T00:00:00Z",
    "expiry_date": null,
    "status": "active",
    "legal_level": 1,
    "subject_area": ["đấu thầu", "mua sắm công", "xây dựng"],
    "keywords": ["nhà thầu", "hồ sơ dự thầu", "đánh giá"],
    "status_history": [
      {
        "status": "draft",
        "date": "2013-06-20T00:00:00Z"
      },
      {
        "status": "active",
        "date": "2014-07-01T00:00:00Z"
      }
    ]
  },
  "content_structure": {
    "chapter": "CHƯƠNG II",
    "section": "Mục 1",
    "article": "Điều 5",
    "paragraph": "Khoản 2",
    "point": null,
    "hierarchy_level": 3,
    "hierarchy_path": ["CHƯƠNG II", "Mục 1", "Điều 5", "Khoản 2"],
    "chapter_id": "chuong-02",
    "article_id": "dieu-05",
    "paragraph_id": "khoan-02",
    "point_id": null
  },
  "relationships": {
    "supersedes": ["38/2009/QH12"],
    "implements": null,
    "related_documents": [
      {
        "doc_id": "decree_63_2014_nd_cp",
        "relationship": "implemented_by",
        "description": "Nghị định hướng dẫn thi hành"
      }
    ],
    "citations": []
  },
  "processing_metadata": {
    "chunk_id": "law_43_2013_qh13_dieu_05_khoan_02",
    "chunk_index": 15,
    "processing_date": "2025-10-31T10:30:00Z",
    "pipeline_version": "2.0.0",
    "chunking_strategy": "optimal_hybrid"
  },
  "quality_metrics": {
    "text_length": 456,
    "token_count": 342,
    "confidence_score": 0.98,
    "quality_flags": {
      "good_size": true,
      "good_tokens": true,
      "has_structure": true
    },
    "semantic_tags": ["quyền_và_nghĩa_vụ", "nhà_thầu"]
  },
  "text": "[CHƯƠNG II - CÁC NGUYÊN TẮC ĐẤU THẦU]\n[Mục 1 - Nguyên tắc chung]\n\nĐiều 5. Quyền và nghĩa vụ của nhà thầu\n\nKhoản 2. Nhà thầu có các nghĩa vụ sau đây:\n\na) Tuân thủ quy định của pháp luật về đấu thầu;\n\nb) Chịu trách nhiệm về tính chính xác, trung thực của hồ sơ dự thầu;\n\nc) Bảo đảm thực hiện đúng cam kết trong hồ sơ dự thầu.",
  "semantic_enrichment": {
    "legal_concepts": [
      "quyền_và_nghĩa_vụ_của_nhà_thầu",
      "tuân_thủ_pháp_luật",
      "trách_nhiệm_hồ_sơ"
    ],
    "named_entities": {
      "legal_terms": ["nhà thầu", "hồ sơ dự thầu", "pháp luật đấu thầu"]
    },
    "key_phrases": [
      "nhà thầu có các nghĩa vụ",
      "tuân thủ quy định của pháp luật",
      "chịu trách nhiệm"
    ]
  },
  "extended_metadata": {}
}
```

### Example 2: Bidding Template Chunk

```json
{
  "schema_version": "1.0.0",
  "document_info": {
    "id": "bidding_hsyc_tu_van_2025",
    "title": "Mẫu HSYC Tư vấn 2025",
    "doc_type": "bidding_template",
    "legal_code": null,
    "source": "/data/processed/bidding/hsyc_tu_van.docx",
    "url": null
  },
  "legal_metadata": {
    "issued_by": "Bộ Kế hoạch và Đầu tư",
    "effective_date": "2025-01-01T00:00:00Z",
    "expiry_date": null,
    "status": "active",
    "legal_level": 4,
    "subject_area": ["đấu thầu", "tư vấn", "mẫu hồ sơ"],
    "keywords": ["HSYC", "tư vấn", "yêu cầu kỹ thuật"],
    "status_history": []
  },
  "content_structure": {
    "chapter": null,
    "section": "PHẦN II - YÊU CẦU CỤ THỂ",
    "article": null,
    "paragraph": null,
    "point": null,
    "hierarchy_level": 1,
    "hierarchy_path": ["PHẦN II - YÊU CẦU CỤ THỂ"],
    "chapter_id": null,
    "article_id": null,
    "paragraph_id": null,
    "point_id": null
  },
  "relationships": {
    "supersedes": [],
    "implements": "circular_05_2025_tt_bkhdt",
    "related_documents": [
      {
        "doc_id": "decree_63_2014_nd_cp",
        "relationship": "complies_with",
        "description": "Tuân thủ Nghị định 63"
      }
    ],
    "citations": [
      {
        "cited_doc_id": "circular_05_2025_tt_bkhdt",
        "citation_type": "implements",
        "cited_article": "Điều 10",
        "citation_context": "Theo quy định tại Điều 10"
      }
    ]
  },
  "processing_metadata": {
    "chunk_id": "bidding_hsyc_tu_van_2025_chunk_0003",
    "chunk_index": 3,
    "processing_date": "2025-10-31T11:00:00Z",
    "pipeline_version": "2.0.0",
    "chunking_strategy": "section_based"
  },
  "quality_metrics": {
    "text_length": 823,
    "token_count": 615,
    "confidence_score": 0.95,
    "quality_flags": {
      "good_size": true,
      "good_tokens": true,
      "has_structure": true,
      "template_compliant": true
    },
    "semantic_tags": ["yêu_cầu_kỹ_thuật", "tư_vấn"]
  },
  "text": "[PHẦN II - YÊU CẦU CỤ THỂ]\n\n2.1. Yêu cầu về năng lực và kinh nghiệm\n\na) Nhà thầu phải có tư cách pháp nhân được thành lập và hoạt động hợp pháp theo quy định của pháp luật...",
  "extended_metadata": {
    "bidding": {
      "template_type": "consultant",
      "section_type": "specific_requirements",
      "requirements_level": "mandatory",
      "evaluation_criteria": ["technical", "experience"],
      "contractor_type": "enterprise",
      "procurement_method": "open",
      "technical_complexity": "moderate"
    }
  }
}
```

---

## 🔄 MIGRATION MAPPINGS

### Mapping Table: Old → New Schema

#### Bidding Pipeline Migration

```python
BIDDING_FIELD_MAPPING = {
    # Document Info
    "filename": "document_info.source",
    "doc_type": "document_info.doc_type",  # value = "bidding_template"
    
    # No direct legal_code for templates
    # "template_type" → "extended_metadata.bidding.template_type"
    
    # Legal Metadata
    "processed_at": "processing_metadata.processing_date",
    
    # Content Structure
    "section_type": "content_structure.section",  # Transform value
    
    # Processing
    "chunk_id": "processing_metadata.chunk_id",
    "chunk_index": "processing_metadata.chunk_index",
    
    # Quality
    "char_count": "quality_metrics.text_length",
    "quality_score": "quality_metrics.confidence_score",
    
    # Extended
    "template_type": "extended_metadata.bidding.template_type",
    "requirements_level": "extended_metadata.bidding.requirements_level",
    "evaluation_criteria": "extended_metadata.bidding.evaluation_criteria",
    "contractor_type": "extended_metadata.bidding.contractor_type",
    "procurement_method": "extended_metadata.bidding.procurement_method",
    "technical_complexity": "extended_metadata.bidding.technical_complexity"
}
```

#### Circular Pipeline Migration

```python
CIRCULAR_FIELD_MAPPING = {
    # Document Info
    "circular_number": "document_info.legal_code",
    "title": "document_info.title",
    "url": "document_info.url",
    
    # Legal Metadata
    "issuing_agency": "legal_metadata.issued_by",
    "effective_date": "legal_metadata.effective_date",
    "status": "legal_metadata.status",
    "subject_area": "legal_metadata.subject_area",
    
    # Content Structure
    "article_number": "content_structure.article",
    "clause_number": "content_structure.paragraph",
    "hierarchy_level": "content_structure.hierarchy_level",
    
    # Relationships
    "supersedes": "relationships.supersedes",
    
    # Processing
    "chunk_id": "processing_metadata.chunk_id",
    "chunk_index": "processing_metadata.chunk_index",
    
    # Quality
    "char_count": "quality_metrics.text_length",
    
    # Extended
    "regulation_type": "extended_metadata.circular.regulation_type"
}
```

#### Law Pipeline Migration

```python
LAW_FIELD_MAPPING = {
    # Document Info
    "law_number": "document_info.legal_code",
    "law_name": "document_info.title",
    
    # Legal Metadata
    "issuing_body": "legal_metadata.issued_by",
    "promulgation_date": "legal_metadata.effective_date",  # Usually same
    "effective_date": "legal_metadata.effective_date",
    "legal_force": "legal_metadata.legal_level",  # Transform to 1-5 scale
    
    # Content Structure
    "chapter": "content_structure.chapter",
    "section": "content_structure.section",
    "article": "content_structure.article",
    "paragraph": "content_structure.paragraph",
    "point": "content_structure.point",
    "hierarchy_level": "content_structure.hierarchy_level",
    
    # Relationships
    "amendment_history": "relationships.supersedes",
    
    # Processing & Quality
    "chunk_id": "processing_metadata.chunk_id",
    "char_count": "quality_metrics.text_length",
    
    # Extended - most fields fit in core schema
}
```

#### Decree Pipeline Migration

```python
DECREE_FIELD_MAPPING = {
    # Document Info
    "decree_number": "document_info.legal_code",
    "title": "document_info.title",
    
    # Legal Metadata
    "issuing_authority": "legal_metadata.issued_by",
    "effective_date": "legal_metadata.effective_date",
    
    # Relationships
    "implements_law": "relationships.implements",
    "related_decrees": "relationships.related_documents",
    
    # Content Structure
    "article": "content_structure.article",
    "clause": "content_structure.paragraph",
    
    # Processing
    "chunk_id": "processing_metadata.chunk_id",
    "chunk_index": "processing_metadata.chunk_index",
    
    # Quality
    "char_count": "quality_metrics.text_length",
    
    # Extended
    "signer": "extended_metadata.decree.signer",
    "scope_of_application": "extended_metadata.decree.scope_of_application",
    "target_entities": "extended_metadata.decree.target_entities",
    "regulatory_level": "extended_metadata.decree.regulatory_level"
}
```

---

## ✅ VALIDATION RULES

### Validation Rule Set

```python
from typing import Any, Dict
import re
from datetime import datetime

class SchemaValidator:
    """Validator for UnifiedLegalChunk"""
    
    @staticmethod
    def validate_legal_code(code: str, doc_type: str) -> bool:
        """Validate legal code format based on document type"""
        patterns = {
            "law": r'^\d+/\d{4}/QH\d+$',  # e.g., 43/2013/QH13
            "decree": r'^\d+/\d{4}/NĐ-CP$',  # e.g., 63/2014/NĐ-CP
            "circular": r'^\d+/\d{4}/TT-[A-Z]+$'  # e.g., 05/2025/TT-BKHĐT
        }
        
        if doc_type not in patterns:
            return True  # No specific pattern
        
        return bool(re.match(patterns[doc_type], code))
    
    @staticmethod
    def validate_hierarchy_consistency(structure: Dict[str, Any]) -> bool:
        """Ensure hierarchy_path matches individual fields"""
        path = structure.get('hierarchy_path', [])
        level = structure.get('hierarchy_level', 0)
        
        # Path length should match or exceed hierarchy level
        if len(path) < level:
            return False
        
        # Check that path elements are present in individual fields
        has_chapter = structure.get('chapter') is not None
        has_article = structure.get('article') is not None
        has_paragraph = structure.get('paragraph') is not None
        
        # If article exists, level should be >= 3 (assuming standard hierarchy)
        if has_article and level < 3:
            return False
        
        return True
    
    @staticmethod
    def validate_date_range(effective: datetime, expiry: datetime = None) -> bool:
        """Ensure dates are logical"""
        if expiry and expiry <= effective:
            return False
        return True
    
    @staticmethod
    def validate_quality_score(score: float) -> bool:
        """Quality score should be 0.0 to 1.0"""
        return 0.0 <= score <= 1.0
    
    @staticmethod
    def validate_chunk_size(text: str, min_size: int = 50, max_size: int = 10000) -> bool:
        """Validate chunk text length"""
        length = len(text)
        return min_size <= length <= max_size

# Usage example
validator = SchemaValidator()

# Validate legal code
is_valid = validator.validate_legal_code("43/2013/QH13", "law")  # True
is_valid = validator.validate_legal_code("invalid", "law")  # False

# Validate hierarchy
structure = {
    "chapter": "CHƯƠNG II",
    "article": "Điều 5",
    "hierarchy_level": 3,
    "hierarchy_path": ["CHƯƠNG II", "Điều 5", "Khoản 2"]
}
is_valid = validator.validate_hierarchy_consistency(structure)  # True
```

---

## 🛠️ CODE SAMPLES

### Migration Script Example

```python
import json
from typing import Dict, Any
from datetime import datetime
from pathlib import Path

class PipelineMigrator:
    """Migrate old format to unified schema"""
    
    def __init__(self, pipeline_type: str):
        self.pipeline_type = pipeline_type
        self.mapping = self._load_mapping(pipeline_type)
    
    def _load_mapping(self, pipeline_type: str) -> Dict:
        """Load appropriate field mapping"""
        mappings = {
            "bidding": BIDDING_FIELD_MAPPING,
            "circular": CIRCULAR_FIELD_MAPPING,
            "law": LAW_FIELD_MAPPING,
            "decree": DECREE_FIELD_MAPPING
        }
        return mappings.get(pipeline_type, {})
    
    def migrate_chunk(self, old_chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate a single chunk to unified format"""
        new_chunk = {
            "schema_version": "1.0.0",
            "document_info": {},
            "legal_metadata": {},
            "content_structure": {},
            "relationships": {},
            "processing_metadata": {},
            "quality_metrics": {},
            "text": old_chunk.get("text", old_chunk.get("content", "")),
            "extended_metadata": {}
        }
        
        # Map fields based on pipeline type
        for old_field, new_path in self.mapping.items():
            if old_field in old_chunk:
                self._set_nested_value(new_chunk, new_path, old_chunk[old_field])
        
        # Add default values for missing required fields
        self._fill_defaults(new_chunk)
        
        # Validate result
        if not self._validate_chunk(new_chunk):
            raise ValueError(f"Migration failed validation for chunk: {old_chunk.get('chunk_id')}")
        
        return new_chunk
    
    def _set_nested_value(self, obj: Dict, path: str, value: Any):
        """Set value in nested dict using dot notation path"""
        parts = path.split('.')
        for part in parts[:-1]:
            obj = obj.setdefault(part, {})
        obj[parts[-1]] = value
    
    def _fill_defaults(self, chunk: Dict[str, Any]):
        """Fill in default values for required fields"""
        # Document info defaults
        if not chunk["document_info"].get("id"):
            chunk["document_info"]["id"] = f"{self.pipeline_type}_{datetime.now().timestamp()}"
        
        if not chunk["document_info"].get("doc_type"):
            type_mapping = {
                "bidding": "bidding_template",
                "circular": "circular",
                "law": "law",
                "decree": "decree"
            }
            chunk["document_info"]["doc_type"] = type_mapping[self.pipeline_type]
        
        # Legal metadata defaults
        if not chunk["legal_metadata"].get("issued_by"):
            chunk["legal_metadata"]["issued_by"] = "Unknown"
        
        if not chunk["legal_metadata"].get("effective_date"):
            chunk["legal_metadata"]["effective_date"] = datetime.now().isoformat()
        
        if not chunk["legal_metadata"].get("status"):
            chunk["legal_metadata"]["status"] = "active"
        
        if not chunk["legal_metadata"].get("legal_level"):
            # Default legal levels by type
            level_mapping = {"law": 1, "decree": 2, "circular": 3, "bidding": 4}
            chunk["legal_metadata"]["legal_level"] = level_mapping[self.pipeline_type]
        
        # Processing metadata defaults
        if not chunk["processing_metadata"].get("chunk_id"):
            chunk["processing_metadata"]["chunk_id"] = chunk["document_info"]["id"]
        
        if "chunk_index" not in chunk["processing_metadata"]:
            chunk["processing_metadata"]["chunk_index"] = 0
        
        if not chunk["processing_metadata"].get("processing_date"):
            chunk["processing_metadata"]["processing_date"] = datetime.now().isoformat()
        
        if not chunk["processing_metadata"].get("pipeline_version"):
            chunk["processing_metadata"]["pipeline_version"] = "2.0.0"
        
        if not chunk["processing_metadata"].get("chunking_strategy"):
            chunk["processing_metadata"]["chunking_strategy"] = "optimal_hybrid"
        
        # Quality metrics defaults
        if not chunk["quality_metrics"].get("text_length"):
            chunk["quality_metrics"]["text_length"] = len(chunk["text"])
        
        if "confidence_score" not in chunk["quality_metrics"]:
            chunk["quality_metrics"]["confidence_score"] = 0.9  # Default high confidence
    
    def _validate_chunk(self, chunk: Dict[str, Any]) -> bool:
        """Basic validation of migrated chunk"""
        # Use UnifiedLegalChunk Pydantic model for validation
        try:
            UnifiedLegalChunk(**chunk)
            return True
        except Exception as e:
            print(f"Validation error: {e}")
            return False
    
    def migrate_file(self, input_path: Path, output_path: Path):
        """Migrate entire JSONL file"""
        migrated_count = 0
        error_count = 0
        
        with open(input_path, 'r', encoding='utf-8') as fin, \
             open(output_path, 'w', encoding='utf-8') as fout:
            
            for line_num, line in enumerate(fin, 1):
                try:
                    old_chunk = json.loads(line)
                    new_chunk = self.migrate_chunk(old_chunk)
                    fout.write(json.dumps(new_chunk, ensure_ascii=False) + '\n')
                    migrated_count += 1
                except Exception as e:
                    print(f"Error on line {line_num}: {e}")
                    error_count += 1
        
        print(f"Migration complete: {migrated_count} successful, {error_count} errors")
        return migrated_count, error_count

# Usage
if __name__ == "__main__":
    migrator = PipelineMigrator("law")
    migrator.migrate_file(
        input_path=Path("data/processed/law_old_format.jsonl"),
        output_path=Path("data/processed/law_unified_format.jsonl")
    )
```

---

## 📈 TESTING & VALIDATION

### Test Suite Structure

```python
import pytest
from datetime import datetime

class TestUnifiedSchema:
    """Test suite for unified schema"""
    
    def test_valid_law_chunk(self):
        """Test valid law chunk creation"""
        chunk_data = {
            "schema_version": "1.0.0",
            "document_info": {
                "id": "law_43_2013",
                "title": "Luật Đấu thầu",
                "doc_type": "law",
                "legal_code": "43/2013/QH13",
                "source": "test.md"
            },
            "legal_metadata": {
                "issued_by": "Quốc hội",
                "effective_date": datetime(2014, 7, 1),
                "status": "active",
                "legal_level": 1
            },
            "content_structure": {
                "hierarchy_level": 2
            },
            "relationships": {},
            "processing_metadata": {
                "chunk_id": "test_001",
                "chunk_index": 0,
                "pipeline_version": "2.0.0",
                "chunking_strategy": "optimal"
            },
            "quality_metrics": {
                "text_length": 100,
                "confidence_score": 0.95
            },
            "text": "Test content"
        }
        
        chunk = UnifiedLegalChunk(**chunk_data)
        assert chunk.document_info.doc_type == "law"
        assert chunk.legal_metadata.legal_level == 1
    
    def test_invalid_legal_code(self):
        """Test invalid legal code format"""
        # Test implementation...
        pass
    
    def test_date_validation(self):
        """Test date range validation"""
        # Test implementation...
        pass
    
    def test_migration_bidding_to_unified(self):
        """Test migration from bidding format"""
        # Test implementation...
        pass

# Run tests
pytest.main([__file__, "-v"])
```

---

## 📚 REFERENCES

### Related Documents
- [DEEP_ANALYSIS_REPORT.md](./DEEP_ANALYSIS_REPORT.md) - Main analysis document
- [UPGRADE_PLAN.md](../UPGRADE_PLAN.md) - Full upgrade timeline
- [EXECUTIVE_SUMMARY.md](../EXECUTIVE_SUMMARY.md) - Business overview

### External Resources
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [JSON Schema Specification](https://json-schema.org/)
- [Vietnamese Legal Code Standards](https://thuvienphapluat.vn/)

---

**Document Version**: 1.0  
**Last Updated**: 31/10/2025  
**Status**: Ready for Implementation
