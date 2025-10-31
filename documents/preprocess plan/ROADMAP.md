# 📅 PREPROCESSING V2 - IMPLEMENTATION ROADMAP

**Last Updated:** October 31, 2024  
**Status:** Phase 1 Complete ✅  
**Progress:** 14% (Week 2 of 14)

---

## 📊 QUICK STATUS

| Phase | Weeks | Status | Progress |
|-------|-------|--------|----------|
| Phase 1: Schema & Base | 1-2 | ✅ Done | 100% |
| Phase 2: Components | 3-4 | ⏳ Next | 0% |
| Phase 3: Pipelines | 5-8 | ⏳ TODO | 0% |
| Phase 4: Enrichment | 9-10 | ⏳ TODO | 0% |
| Phase 5: Orchestration | 11-12 | ⏳ TODO | 0% |
| Phase 6: Testing & Docs | 13-14 | ⏳ TODO | 0% |

**Overall:** 14% complete (Phase 1 of 6)

---

## 🎯 PHASE 1 RESULTS (Week 1-2) ✅ COMPLETE

### Deliverables
- **11 Python files** (~1,505 lines)
- **11 enums** for Vietnamese legal system
- **6 Pydantic models** (21 core fields)
- **BaseLegalPipeline** (7-stage Template Method)
- **LawPipeline** example
- **Test script** (3/3 tests passing ✅)
- **43 files archived** (V1 → archive/preprocessing_v1/)

### Test Results
```
✅ Test 1: Schema Creation - PASSED
✅ Test 2: LawPipeline Execution - PASSED  
✅ Test 3: Enum Values - PASSED
```

### Files Created
```
src/preprocessing/
├── schema/ (8 files, 905 lines)
│   ├── enums.py - 11 enums
│   ├── unified_schema.py - UnifiedLegalChunk
│   └── models/ - 6 Pydantic models
├── base/legal_pipeline.py (300 lines)
└── pipelines/law_pipeline.py (250 lines)

scripts/test/test_phase1_skeleton.py (150 lines)
archive/preprocessing_v1/ (43 files archived)
```

---

## Phase 1: Schema & Base ✅ COMPLETE (Week 1-2)

### Week 1: Schema Definitions ✅
```
✅ enums.py               - 11 enums (115 lines)
✅ document_info.py       - DocumentInfo model (90 lines)
✅ legal_metadata.py      - LegalMetadata model (100 lines)
✅ content_structure.py   - ContentStructure model (140 lines)
✅ processing_metadata.py - ProcessingMetadata model (95 lines)
✅ quality_metrics.py     - QualityMetrics model (105 lines)
✅ unified_schema.py      - UnifiedLegalChunk (160 lines)
```

**Deliverables:**
- ✅ 11 enums for Vietnamese legal system
- ✅ 6 Pydantic models with validation
- ✅ UnifiedLegalChunk (21 core fields)
- ✅ Vietnamese legal ID regex validator

### Week 2: Base Classes ✅
```
✅ legal_pipeline.py      - BaseLegalPipeline (300 lines)
✅ law_pipeline.py        - LawPipeline example (250 lines)
✅ test_phase1_skeleton.py - Test script (150 lines)
```

**Deliverables:**
- ✅ BaseLegalPipeline with 7 stages
- ✅ PipelineConfig & PipelineResult
- ✅ LawPipeline example implementation
- ✅ Skeleton test demonstrating flow

---

## Phase 2: Components ⏳ TODO (Week 3-4)

### Week 3: Loaders
```
⏳ loaders/
   ├── __init__.py
   ├── docx_loader.py      # Refactor from archive
   ├── pdf_loader.py       # NEW - For scanned docs
   └── excel_loader.py     # NEW - For exam questions
```

**Tasks:**
- [ ] Refactor DOCX parser from `archive/preprocessing_v1/parsers_original/`
- [ ] Extract TokenChecker, heading detection, hierarchy parsing
- [ ] Create DocxLoader class
- [ ] Integrate with LawPipeline.ingest()
- [ ] Add PDF loader (pymupdf/pdfplumber)
- [ ] Add Excel loader (openpyxl)
- [ ] Write loader unit tests

**Estimated:** 16-20 hours

### Week 4: Chunking Strategies
```
⏳ chunking/
   ├── __init__.py
   ├── hierarchical_chunker.py  # For Law/Decree/Circular
   └── semantic_chunker.py      # For Bidding/Report/Exam
```

**Tasks:**
- [ ] Implement HierarchicalChunker
  - [ ] Parse Vietnamese hierarchy (Phần > Chương > Mục > Điều > Khoản > Điểm)
  - [ ] Build parent-child relationships
  - [ ] Handle malformed hierarchies
- [ ] Implement SemanticChunker
  - [ ] Sliding window chunking
  - [ ] Semantic boundary detection
- [ ] Integrate with BaseLegalPipeline.chunk()
- [ ] Write chunking tests

**Estimated:** 16-20 hours

---

## Phase 3: Pipeline Implementation (Week 5-8)

### Week 5: Law & Decree Pipelines
```
⏳ pipelines/
   ├── law_pipeline.py       # ENHANCE existing skeleton
   └── decree_pipeline.py    # NEW
```

**LawPipeline Tasks:**
- [ ] Replace mock data with real DOCX extraction
- [ ] Implement hierarchy parsing (Phần > Chương > Điều)
- [ ] Add legal metadata extraction (parent laws, status)
- [ ] Add validation (check Điều numbering, hierarchy)
- [ ] Write integration tests

**DecreePipeline Tasks:**
- [ ] Similar to LawPipeline
- [ ] Add parent law detection (e.g., "Căn cứ Luật Đấu thầu...")
- [ ] Handle "hướng dẫn thi hành" relationships
- [ ] Write tests

**Estimated:** 24-32 hours

### Week 6: Circular & Decision Pipelines
```
⏳ pipelines/
   ├── circular_pipeline.py   # NEW
   └── decision_pipeline.py   # NEW
```

**CircularPipeline Tasks:**
- [ ] Similar to DecreePipeline
- [ ] Handle ministry-specific formats
- [ ] Extract issuing authority (Bộ Kế hoạch, Bộ Tài chính, etc.)
- [ ] Write tests

**DecisionPipeline Tasks:**
- [ ] NEW document type (7th type)
- [ ] Design extended metadata schema
- [ ] Implement pipeline
- [ ] Write tests

**Estimated:** 20-24 hours

### Week 7: Bidding & Report Pipelines
```
⏳ pipelines/
   ├── bidding_pipeline.py    # REFACTOR from archive
   └── report_pipeline.py     # NEW
```

**BiddingPipeline Tasks:**
- [ ] Migrate from `archive/preprocessing_v1/bidding_preprocessing/`
- [ ] Adapt to UnifiedLegalChunk schema
- [ ] Reuse existing chunking logic
- [ ] Add new quality checks
- [ ] Write migration tests

**ReportPipeline Tasks:**
- [ ] NEW document type
- [ ] Parse report templates (DOCX/Excel)
- [ ] Extract form fields, tables
- [ ] Write tests

**Estimated:** 20-24 hours

### Week 8: Exam Pipeline
```
⏳ pipelines/
   └── exam_pipeline.py       # NEW
```

**ExamPipeline Tasks:**
- [ ] NEW document type
- [ ] Parse Excel files (questions, answers, metadata)
- [ ] Extract question bank structure
- [ ] Handle multiple choice answers
- [ ] Write tests

**Estimated:** 12-16 hours

---

## Phase 4: Enrichment & Quality (Week 9-10)

### Week 9: Semantic Enrichment
```
⏳ enrichment/
   ├── __init__.py
   ├── ner_extractor.py       # Legal entity extraction
   ├── concept_extractor.py   # Legal concepts
   └── keyword_extractor.py   # Keywords
```

**Tasks:**
- [ ] Legal concept extraction (e.g., "đấu thầu rộng rãi")
- [ ] Named entity recognition (laws, decrees, dates)
- [ ] Keyword extraction
- [ ] Integrate with BaseLegalPipeline.enrich()
- [ ] Write enrichment tests

**Estimated:** 16-20 hours

### Week 10: Quality Analysis
```
⏳ quality/
   ├── __init__.py
   ├── completeness_checker.py
   ├── confidence_scorer.py
   └── consistency_validator.py
```

**Tasks:**
- [ ] Completeness checker (metadata fields populated)
- [ ] Confidence scorer (extraction quality)
- [ ] Consistency validator (hierarchy, references)
- [ ] Integrate with BaseLegalPipeline.assess_quality()
- [ ] Write quality tests

**Estimated:** 16-20 hours

---

## Phase 5: Orchestration & Migration (Week 11-12)

### Week 11: Pipeline Orchestrator
```
⏳ orchestration/
   ├── __init__.py
   ├── orchestrator.py        # PipelineOrchestrator
   └── doc_type_detector.py   # Auto document type detection
```

**Tasks:**
- [ ] PipelineOrchestrator implementation
- [ ] Auto document type detection (from path/content)
- [ ] Parallel processing support
- [ ] Error recovery and retry logic
- [ ] Write orchestration tests

**Estimated:** 16-20 hours

### Week 12: Data Migration
```
⏳ migration/
   ├── __init__.py
   ├── migrate_existing_data.py
   └── validation/
       ├── compare_v1_v2.py
       └── quality_validator.py
```

**Tasks:**
- [ ] Migrate existing 4 pipeline data
- [ ] Run parallel V1/V2 comparison
- [ ] Validate migrated data quality
- [ ] Generate migration report
- [ ] Fix discrepancies

**Estimated:** 20-24 hours

---

## Phase 6: Testing & Documentation (Week 13-14)

### Week 13: End-to-End Testing
```
⏳ tests/
   ├── integration/
   │   ├── test_law_e2e.py
   │   ├── test_decree_e2e.py
   │   ├── test_circular_e2e.py
   │   ├── test_decision_e2e.py
   │   ├── test_bidding_e2e.py
   │   ├── test_report_e2e.py
   │   └── test_exam_e2e.py
   └── performance/
       ├── test_load.py
       └── benchmark.py
```

**Tasks:**
- [ ] E2E tests for all 7 pipelines
- [ ] Performance benchmarks
- [ ] Load testing (1000+ documents)
- [ ] Memory profiling
- [ ] Generate test report

**Estimated:** 20-24 hours

### Week 14: Documentation & Deployment
```
⏳ Documentation
   ├── API_REFERENCE.md       # Auto-generated from docstrings
   ├── USER_GUIDE.md          # How to use pipelines
   ├── DEVELOPER_GUIDE.md     # How to add new pipelines
   └── MIGRATION_GUIDE.md     # V1 → V2 migration
```

**Tasks:**
- [ ] Generate API documentation (Sphinx/MkDocs)
- [ ] Write user guide with examples
- [ ] Write developer guide for extending
- [ ] Write migration guide for V1 users
- [ ] Production deployment checklist
- [ ] Create release notes
- [ ] Deploy to production

**Estimated:** 16-20 hours

---

## 📊 Effort Summary

| Phase | Weeks | Hours | Status |
|-------|-------|-------|--------|
| Phase 1: Schema & Base | 1-2 | 32-40 | ✅ DONE |
| Phase 2: Components | 3-4 | 32-40 | ⏳ Next |
| Phase 3: Pipelines | 5-8 | 76-96 | ⏳ TODO |
| Phase 4: Enrichment | 9-10 | 32-40 | ⏳ TODO |
| Phase 5: Orchestration | 11-12 | 36-44 | ⏳ TODO |
| Phase 6: Testing & Docs | 13-14 | 36-44 | ⏳ TODO |
| **Total** | **14** | **244-304** | **14% done** |

## 🎯 Key Milestones

- **✅ Week 2** - Phase 1 complete, schema validated
- **⏳ Week 4** - All loaders and chunkers ready
- **⏳ Week 8** - All 7 pipelines implemented
- **⏳ Week 10** - Quality and enrichment complete
- **⏳ Week 12** - Data migration complete
- **⏳ Week 14** - Production ready! 🚀

## 🔄 Current Status (Week 2 End)

**Completed:**
- ✅ 11 enums defined
- ✅ 6 Pydantic models created
- ✅ UnifiedLegalChunk schema validated
- ✅ BaseLegalPipeline with 7 stages
- ✅ LawPipeline skeleton implemented
- ✅ Test script demonstrating flow

**Next Up (Week 3):**
- ⏳ Refactor DOCX loader from archive
- ⏳ Create DocxLoader class
- ⏳ Add PDF loader
- ⏳ Add Excel loader
- ⏳ Write loader tests

**Blockers:** None! 🎉

---

**Last Updated:** October 31, 2024  
**Progress:** 14% (Phase 1 of 6 complete)  
**On Track:** ✅ Yes
