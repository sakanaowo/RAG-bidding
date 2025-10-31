# Phase 1 Skeleton Code - Unified Schema & Base Pipeline

**Status:** ✅ Complete (Week 1-2 of 14-week roadmap)

## 📁 Directory Structure Created

```
src/preprocessing/
├── schema/                          ✅ NEW - Unified schema definitions
│   ├── __init__.py
│   ├── enums.py                    # DocType, LegalStatus, etc. (115 lines)
│   ├── unified_schema.py           # UnifiedLegalChunk (160 lines)
│   └── models/                     # Pydantic models
│       ├── __init__.py
│       ├── document_info.py        # DocumentInfo (90 lines)
│       ├── legal_metadata.py       # LegalMetadata (100 lines)
│       ├── content_structure.py    # ContentStructure (140 lines)
│       ├── processing_metadata.py  # ProcessingMetadata (95 lines)
│       ├── quality_metrics.py      # QualityMetrics (105 lines)
│       └── extended/               # Extended metadata (TODO Phase 3)
│           └── __init__.py
│
├── base/                           ✅ UPDATED - V2 base classes
│   ├── __init__.py                # Updated to export V2 classes
│   ├── legal_pipeline.py          # BaseLegalPipeline (300 lines) ✨ NEW
│   ├── base_extractor.py          # V1 (kept for reference)
│   ├── base_parser.py             # V1 (kept for reference)
│   └── base_pipeline.py           # V1 (kept for reference)
│
└── pipelines/                      ✅ NEW - Document pipelines
    ├── __init__.py
    └── law_pipeline.py             # LawPipeline example (250 lines)
```

## 🎯 What Was Created

### 1. **Unified Schema** (`schema/`)
- ✅ **11 Enums** - Vietnamese legal system types
  - `DocType`: 7 document types (Law, Decree, Circular, Decision, Bidding, Report, Exam)
  - `LegalStatus`: 5 states (còn hiệu lực, hết hiệu lực, bị thay thế, bị bãi bỏ, dự thảo)
  - `LegalLevel`: 5-tier hierarchy (Hiến pháp → Luật → Nghị định → Thông tư/Quyết định → Applied)
  - `RelationType`: 6 types (hướng dẫn, thay thế, sửa đổi, bãi bỏ, tham chiếu, căn cứ)
  - `ChunkType`: 8 types (điều khoản, khoản, điểm, chương, mục, phần, table, semantic)
  - `ContentFormat`: 4 formats (plain_text, markdown, html, structured_json)
  - `ProcessingStage`: 7 stages (ingestion → extraction → validation → chunking → enrichment → quality → output)
  - `QualityLevel`: 4 levels (high >90%, medium 70-90%, low 50-70%, failed <50%)
  - `IssuingAuthority`: 8 authorities (Quốc hội, Chính phủ, Bộ, etc.)
  - `DocumentDomain`: 9 domains (đấu thầu, xây dựng, tài chính, etc.)

- ✅ **6 Pydantic Models** - Type-safe validation
  - `DocumentInfo`: 8 core fields (doc_id, doc_type, title, authority, dates, source)
  - `LegalMetadata`: 9+ legal fields (level, status, domain, relationships, scope)
  - `ContentStructure`: 12+ content fields (chunk_id, hierarchy, text, format, metrics)
  - `ProcessingMetadata`: 10+ processing fields (id, version, timestamps, config)
  - `QualityMetrics`: 12+ quality fields (confidence, completeness, validation)
  - `HierarchyPath`: Vietnamese hierarchy (Phần > Chương > Mục > Điều > Khoản > Điểm)

- ✅ **UnifiedLegalChunk** - Main schema class
  - Combines all 6 sections
  - 21 core fields + ~75 extended fields
  - Type-safe with Pydantic validation
  - Vietnamese legal ID regex: `^\d+/\d{4}/[A-ZĐ\-]+$`

### 2. **Base Pipeline** (`base/legal_pipeline.py`)
- ✅ **Template Method Pattern** - 7 processing stages
  - Stage 1: `ingest()` - Load file from disk
  - Stage 2: `extract()` - Parse metadata + content
  - Stage 3: `validate()` - Validate extracted data (optional)
  - Stage 4: `chunk()` - Split into logical chunks
  - Stage 5: `enrich()` - Add semantic metadata (optional)
  - Stage 6: `assess_quality()` - Quality checks (optional)
  - Stage 7: `format_output()` - Format and save

- ✅ **Abstract Base Class** - Forces consistency
  - 3 required methods: `ingest()`, `extract()`, `chunk()`
  - 4 optional methods with default implementations
  - Error handling and logging built-in
  - Pipeline configuration support

- ✅ **PipelineConfig** - Configurable behavior
  - Enable/disable validation, enrichment, quality checks
  - Chunking strategy selection
  - Chunk size limits

- ✅ **PipelineResult** - Standardized output
  - Success/failure status
  - List of chunks
  - Metadata (processing_id, duration, count)
  - Errors and warnings

### 3. **Example Pipeline** (`pipelines/law_pipeline.py`)
- ✅ **LawPipeline** - Complete implementation template
  - All 7 stages implemented (with TODOs)
  - Vietnamese Law-specific logic
  - Hierarchical chunking by Điều (articles)
  - Mock data for testing skeleton
  - Comments explaining each stage

## 📊 Schema Coverage

| Document Type | Schema Status | Pipeline Status |
|--------------|---------------|-----------------|
| Law (Luật) | ✅ Complete | ✅ Skeleton done |
| Decree (Nghị định) | ✅ Complete | ⏳ TODO Phase 3 |
| Circular (Thông tư) | ✅ Complete | ⏳ TODO Phase 3 |
| Decision (Quyết định) | ✅ Complete | ⏳ TODO Phase 3 |
| Bidding (Hồ sơ mời thầu) | ✅ Complete | ⏳ TODO Phase 3 |
| Report (Mẫu báo cáo) | ✅ Complete | ⏳ TODO Phase 3 |
| Exam (Câu hỏi thi) | ✅ Complete | ⏳ TODO Phase 3 |

## 🚀 Quick Start

### Install Dependencies
```bash
pip install pydantic
```

### Run Skeleton Test
```bash
cd /home/sakana/Code/RAG-bidding
python scripts/test/test_phase1_skeleton.py
```

Expected output:
```
🚀 ===========================================================
  PHASE 1 SKELETON TEST - Unified Schema & Base Pipeline
==============================================================

TEST 1: Schema Creation
✓ Created DocumentInfo: 43/2013/QH13
✓ Created LegalMetadata: Level 2
✓ Created ContentStructure: 43-2013-QH13_dieu_1
  Hierarchy: Phần 1 > Chương 1 > Điều 1
✓ Created UnifiedLegalChunk
  Doc Type: law
  Is Legal: True
  Chunk ID: 43-2013-QH13_dieu_1

TEST 2: LawPipeline Execution
✓ Created LawPipeline
  Doc Type: law
⚠ Expected error (file doesn't exist)
  This is OK for skeleton test - pipeline structure is working!

TEST 3: Enum Values
📋 Document Types: law, decree, circular, decision, bidding, report, exam
⚖️ Legal Levels: HIEN_PHAP(1), LUAT(2), NGHI_DINH(3), THONG_TU_QUYET_DINH(4), VAN_BAN_AP_DUNG(5)
...
```

## 📋 Phase 1 Checklist

**Week 1: Schema Definitions** ✅
- [x] Create enums for Vietnamese legal system
- [x] Create Pydantic models for 6 sections
- [x] Create UnifiedLegalChunk main schema
- [x] Add Vietnamese legal ID validation
- [x] Add field validators and examples

**Week 2: Base Classes** ✅
- [x] Create BaseLegalPipeline with 7 stages
- [x] Implement Template Method Pattern
- [x] Add PipelineConfig and PipelineResult
- [x] Create LawPipeline example
- [x] Write skeleton test script

## 🎯 Next Steps (Phase 2: Week 3-4)

### Week 3: Loaders & Extractors
```python
src/preprocessing/loaders/
├── __init__.py
├── docx_loader.py      # Reuse from archive/preprocessing_v1/parsers_original/
├── pdf_loader.py       # TODO: Implement PDF extraction
└── excel_loader.py     # TODO: For exam questions
```

**Tasks:**
- [ ] Refactor DOCX parser from archived code
- [ ] Create DocxLoader class
- [ ] Integrate with LawPipeline.ingest()
- [ ] Add PDF loader (for scanned documents)
- [ ] Add Excel loader (for exam questions)

### Week 4: Chunking Strategies
```python
src/preprocessing/chunking/
├── __init__.py
├── hierarchical_chunker.py  # For Law/Decree/Circular (Điều > Khoản > Điểm)
└── semantic_chunker.py      # For Bidding/Report/Exam
```

**Tasks:**
- [ ] Implement HierarchicalChunker
- [ ] Implement SemanticChunker
- [ ] Integrate with BaseLegalPipeline.chunk()
- [ ] Add chunking tests

## 📝 Code Statistics

| Component | Files | Lines | Status |
|-----------|-------|-------|--------|
| Schema (enums) | 1 | 115 | ✅ Complete |
| Schema (models) | 6 | 630 | ✅ Complete |
| Schema (main) | 1 | 160 | ✅ Complete |
| Base pipeline | 1 | 300 | ✅ Complete |
| Example pipeline | 1 | 250 | ✅ Complete |
| Test script | 1 | 150 | ✅ Complete |
| **Total** | **11** | **1,605** | **✅ Phase 1 Done** |

## 🔗 Related Documentation

- **Deep Analysis**: `documents/preprocess plan/phase 1 report/DEEP_ANALYSIS_REPORT.md`
  - Section 3: Unified Schema Proposal (reference for all fields)
  - Section 4: Legal RAG Systems Benchmark

- **Architecture Design**: `documents/preprocess plan/PREPROCESSING_ARCHITECTURE.md`
  - Section 5: BaseLegalPipeline Design
  - Section 6: Document-Specific Pipelines
  - Section 8: Implementation Roadmap

- **Schema Implementation Guide**: `documents/preprocess plan/phase 1 report/SCHEMA_IMPLEMENTATION_GUIDE.md`
  - Pydantic models with full examples
  - Migration mappings from V1 pipelines

## 🎉 Key Achievements

1. ✅ **Type-Safe Schema** - All fields validated with Pydantic
2. ✅ **Vietnamese Legal Support** - Custom enums, hierarchy, validation
3. ✅ **Extensible Architecture** - Easy to add new document types
4. ✅ **Template Method Pattern** - Consistent 7-stage pipeline
5. ✅ **Complete Example** - LawPipeline shows how to implement
6. ✅ **Backward Compatible** - V1 classes still available during migration

---

**Status:** Phase 1 (Week 1-2) ✅ COMPLETE  
**Next:** Phase 2 (Week 3-4) - Loaders & Chunkers  
**Goal:** Complete 14-week roadmap by Week 14 (Jan 2025)
