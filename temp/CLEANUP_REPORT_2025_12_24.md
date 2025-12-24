# 🧹 Báo Cáo Cleanup - RAG Bidding Project

**Ngày**: 24/12/2025  
**Trạng thái**: Phase 2 đã hoàn thành từ tháng 11/2025  
**Mục đích**: Dọn dẹp files deprecated, outdated docs, và test files không còn giá trị

---

## 📊 Tổng Quan

### ✅ Đã Hoàn Thành (Tháng 11/2025)
- **Phase 1**: Query Enhancement (Multi-Query, HyDE, Step-Back, Decomposition)
- **Phase 2**: Singleton Pattern cho BGEReranker 
- **Phase 3**: Deprecate 4 empty reranker files
- **Phase 4**: Documentation & Testing

### 🗑️ Cần Cleanup Ngay

**Files Deprecated/Outdated**:
- 📄 **70 test files** (nhiều file lỗi thời)
- 📄 **20+ documentation files** (archived reports)
- 📁 **3 deprecated folders** 
- 📁 **1 processed_old folder** với data cũ
- 📓 **5 deprecated notebooks**

---

## 🎯 Danh Sách Cleanup Chi Tiết

### 1️⃣ **Reranker Files - DEPRECATED (Giữ lại documentation)**

#### ❌ Files Cần XÓA (4 files - Empty, không dùng)
```bash
src/retrieval/ranking/cohere_reranker.py          # Empty - đã deprecate
src/retrieval/ranking/cross_encoder_reranker.py   # Empty - duplicate BGE
src/retrieval/ranking/legal_score_reranker.py     # Empty - không implement
src/retrieval/ranking/llm_reranker.py             # Empty - quá chậm
```

**Note**: Files này đã có deprecation notice từ 13/11/2025, timeline xóa là 01/03/2025.

#### ✅ Files GIỮ LẠI (Production)
```bash
src/retrieval/ranking/bge_reranker.py      # ✅ Production - BGE v2-m3
src/retrieval/ranking/base_reranker.py     # ✅ Base class
src/retrieval/ranking/__init__.py          # ✅ Exports
```

#### 📚 Documentation GIỮ LẠI (Reference)
```bash
src/retrieval/ranking/DEPRECATED_RERANKERS.md  # Migration guide
```

---

### 2️⃣ **Test Files - CẦN REVIEW (70 files)**

#### 🔴 **Priority 1 - XÓA NGAY** (Test cho deprecated features)

**Reranking Tests - Deprecated Models:**
```bash
scripts/tests/reranking/test_phobert_reranker.py   # PhoBERT không production
scripts/tests/reranking/test_phobert_setup.py      # Setup test cho PhoBERT
scripts/tests/reranking/test_model_comparison.py   # So sánh BGE vs PhoBERT
scripts/tests/reranking/test_end_to_end_reranking.py  # Old test
```
**Lý do**: PhoBERT không được dùng trong production, chỉ BGE.

**Legacy Tests:**
```bash
scripts/tests/legacy_test_upload_api.py           # Legacy API test
scripts/test_upload_v3.py                          # Old upload test
```

**Old/Duplicate Tests:**
```bash
scripts/tests/test_openai_reranker.py             # OpenAI reranker không production
scripts/tests/test_parallel_reranking.py          # Duplicate với singleton tests
```

#### 🟡 **Priority 2 - REVIEW** (Có thể lỗi thời)

**Integration Tests - Cần verify còn pass không:**
```bash
scripts/tests/integration/test_phase1_skeleton.py     # Phase 1 skeleton
scripts/tests/integration/test_enhancer_quick.py      # Quick enhancer test
scripts/tests/integration/test_edge_cases.py          # Edge cases - CÓ THỂ GIỮ
scripts/tests/integration/test_performance.py         # Performance - GIỮ LẠI
```

**Chunking Tests - Verify còn cần không:**
```bash
scripts/tests/chunking/test_chunking_strategies.py    # Strategy comparison
scripts/tests/chunking/test_chunking_integration.py   # Integration test
scripts/tests/chunking/test_bidding_hybrid_chunker.py # Hybrid chunker
scripts/tests/chunking/test_chunk_pipeline.py         # Pipeline test
```

**Pipeline Tests - Verify format tests:**
```bash
scripts/tests/pipeline/test_all_pipelines_format.py   # Format validation
scripts/tests/pipeline/test_decree_pipeline.py        # Decree-specific
scripts/tests/pipeline/test_circular_pipeline.py      # Circular-specific
scripts/tests/pipeline/test_docx_pipeline.py          # DOCX-specific
```

#### ✅ **Priority 3 - GIỮ LẠI** (Core tests)

**Core System Tests:**
```bash
scripts/test_db_connection.py                    # ✅ DB connection test
scripts/tests/test_db_connection.py              # ✅ Duplicate?
scripts/tests/test_core_system.py                # ✅ Core system test
scripts/tests/test_database_init.py              # ✅ DB init test
scripts/tests/test_api_server.py                 # ✅ API test
scripts/tests/test_rag_queries.py                # ✅ RAG query test
scripts/tests/test_quick_retrieval.py            # ✅ Quick retrieval
```

**Singleton Tests (Phase 2 results):**
```bash
scripts/tests/unit/test_singleton_reranker.py    # ✅ 11/11 PASSED
scripts/tests/test_singleton_production.py       # ✅ 4/4 PASSED
```

**Performance Tests:**
```bash
scripts/tests/performance/run_performance_tests.py    # ✅ Performance suite
scripts/tests/performance/test_query_latency.py       # ✅ Latency tests
scripts/tests/performance/test_cache_effectiveness.py # ✅ Cache tests
scripts/tests/performance/test_multi_user_queries.py  # ✅ Multi-user
```

**Document Management Tests:**
```bash
scripts/tests/test_document_status_api.py        # ✅ Document status API
scripts/tests/test_status_filter.py              # ✅ Status filtering
scripts/tests/test_upload_workflow.py            # ✅ Upload workflow
```

**Retrieval Tests:**
```bash
scripts/tests/retrieval/test_api_with_filtering.py    # ✅ API filtering
scripts/tests/retrieval/test_status_filtering.py      # ✅ Status filter
```

---

### 3️⃣ **Documentation - ARCHIVED (20+ files)**

#### 🔴 **XÓA - Archived Reports (Đã superseded)**

**Phase 1-2 Reports (Superseded by SINGLETON_PATTERN_GUIDE.md):**
```bash
documents/technical/implementation-plans/PHASE_1_2_COMPLETION_SUMMARY.md  # ⚠️ ARCHIVED 13/11/2025
documents/technical/reranking-analysis/IMPLEMENTATION_PLAN_1DAY.md        # Detailed plan
documents/technical/reranking-analysis/RERANKER_MEMORY_ANALYSIS.md        # Memory analysis
```
**Superseded by**: `documents/technical/reranking-analysis/SINGLETON_PATTERN_GUIDE.md`

**Old System Design Docs:**
```bash
documents/System Design/03_Database_Schema.md     # Old schema - có v3
temp/proposed_schema_v3.md                        # Temp proposal
temp/detailed_schema_analysis.md                  # Analysis notes
temp/schema_columns_detail.txt                    # Detail dump
temp/schema_detailed_descriptions.txt             # Descriptions
temp/schema_from_temp_db.sql                      # Temp schema
temp/make.sql                                     # Temp SQL
```

**Conversation Logs & Summaries:**
```bash
temp/CONVERSATION_SUMMARY_DETAILED.md            # 814 lines - conversation log
temp/REFACTORING_PLAN_REVIEW_VI.md               # Refactoring plan
temp/REFACTORING_PLAN.md                         # English version
temp/step4_completion_report.md                  # Step 4 report
```

#### 🟡 **REVIEW - Có thể còn giá trị**

**Technical Docs - Kiểm tra còn cần không:**
```bash
documents/technical/reranking-analysis/RERANKING_STRATEGIES.md    # Strategy comparison - GIỮ
documents/technical/reranking-analysis/TOM_TAT_TIENG_VIET.md      # Vietnamese summary - GIỮ
documents/technical/reranking-analysis/README.md                  # Index - GIỮ
```

**Verification Docs:**
```bash
documents/verification/*  # Cần check còn relevant không
```

#### ✅ **GIỮ LẠI - Active Documentation**

**Core Docs:**
```bash
.github/copilot-instructions.md                  # ✅ Copilot context
documents/README.md                              # ✅ Main README
documents/SETUP_ENVIRONMENT_DATABASE.md          # ✅ Setup guide
documents/System Design/                         # ✅ Active design docs
  - 01_System_Specification.md
  - 02_Use_Cases.md
  - 03_Database_Schema_v3.md (active)
  - 04_System_Architecture.md
  - 05_API_Specification.md
  - 06_SQLAlchemy_Implementation.md
```

**Migration Guides:**
```bash
src/retrieval/ranking/DEPRECATED_RERANKERS.md    # ✅ Migration guide
documents/technical/reranking-analysis/SINGLETON_PATTERN_GUIDE.md  # ✅ Complete guide
documents/technical/implementation-plans/SINGLETON_IMPLEMENTATION_RESULTS.md  # ✅ Results
```

**Chat Session Implementation:**
```bash
documents/chat-session-implementation/           # ✅ Active work
  - CHAT_SESSION_DB_SCHEMA.md
  - CHAT_SESSION_POSTGRESQL_PLAN.md
  - TODO_CHAT_SESSION_MIGRATION.md
```

---

### 4️⃣ **Notebooks - DEPRECATED (5 files)**

#### 🔴 **XÓA NGAY**
```bash
notebooks/add_metadata_to_db-deprecated.ipynb    # ⚠️ -deprecated suffix
```

#### 🟡 **REVIEW - Có thể lỗi thời**
```bash
notebooks/fix-source-for-metadata-in-chunk.ipynb  # One-time fix?
notebooks/update-document-id.ipynb                # One-time update?
notebooks/update-metadata.ipynb                   # One-time update?
```

#### ✅ **GIỮ - Analysis/Active notebooks**
```bash
notebooks/analysis/      # ✅ Analysis notebooks
notebooks/ingestion/     # ✅ Ingestion notebooks
notebooks/migration/     # ✅ Migration notebooks
notebooks/preprocessing/ # ✅ Preprocessing notebooks
notebooks/testing/       # ✅ Testing notebooks
```

---

### 5️⃣ **Data Folders - OLD DATA (1 folder)**

#### 🔴 **XÓA HOẶC ARCHIVE**
```bash
data/processed_old/                     # Old processed data
  - batch_processing_report.txt
  - chunks/
  - metadata/
```
**Action**: Move to `data/archive/` hoặc xóa nếu không cần.

#### ✅ **GIỮ - Active data**
```bash
data/processed/          # ✅ Current processed data
data/raw/                # ✅ Raw legal documents
data/outputs/            # ✅ Processing outputs
```

---

## 🎯 Cleanup Actions - Priority Order

### 🔴 **IMMEDIATE - Xóa ngay (Low risk)**

1. **Empty reranker files** (4 files):
   ```bash
   rm src/retrieval/ranking/{cohere,cross_encoder,legal_score,llm}_reranker.py
   ```

2. **Deprecated tests** (8 files):
   ```bash
   rm scripts/tests/reranking/test_phobert_*.py
   rm scripts/tests/reranking/test_model_comparison.py
   rm scripts/tests/reranking/test_end_to_end_reranking.py
   rm scripts/tests/legacy_test_upload_api.py
   rm scripts/tests/test_openai_reranker.py
   rm scripts/tests/test_parallel_reranking.py
   rm scripts/test_upload_v3.py
   ```

3. **Deprecated notebooks** (1 file):
   ```bash
   rm notebooks/add_metadata_to_db-deprecated.ipynb
   ```

4. **Archived docs** (3 major files):
   ```bash
   rm documents/technical/implementation-plans/PHASE_1_2_COMPLETION_SUMMARY.md
   # Giữ lại IMPLEMENTATION_PLAN_1DAY.md & RERANKER_MEMORY_ANALYSIS.md cho reference
   ```

5. **Temp files** (11 files):
   ```bash
   rm temp/CONVERSATION_SUMMARY_DETAILED.md
   rm temp/detailed_schema_analysis.md
   rm temp/make.sql
   rm temp/proposed_schema_v3.md
   rm temp/REFACTORING_PLAN*.md
   rm temp/schema_*.{txt,sql}
   rm temp/step4_completion_report.md
   ```

6. **Old data** (1 folder):
   ```bash
   mkdir -p data/archive
   mv data/processed_old/ data/archive/processed_$(date +%Y%m%d)/
   ```

### 🟡 **MEDIUM PRIORITY - Review trước khi xóa**

1. **Chunking tests** (4 files) - Run tests trước khi xóa:
   ```bash
   # Test xem còn pass không
   python scripts/tests/chunking/test_*.py
   # Nếu fail hoặc không cần → xóa
   ```

2. **Pipeline tests** (4 files) - Verify còn cần không:
   ```bash
   # Check xem pipeline tests còn relevant không
   python scripts/tests/pipeline/test_*.py
   ```

3. **Integration tests** (10+ files) - Review từng file:
   ```bash
   # Test phase1 skeleton
   python scripts/tests/integration/test_phase1_skeleton.py
   # Nếu lỗi thời → xóa
   ```

4. **One-time fix notebooks** (3 files):
   ```bash
   # Nếu đã chạy xong và không cần lại
   rm notebooks/{fix-source,update-document-id,update-metadata}.ipynb
   ```

### ✅ **KEEP - Không xóa**

**Core tests** (25+ files) - Essential cho CI/CD
**Performance tests** (4 files) - Monitoring
**Documentation** (10+ files) - Active references
**Active notebooks** (20+ files) - Analysis/development

---

## 📋 Cleanup Commands

### Quick Cleanup Script

```bash
#!/bin/bash
# cleanup_phase2.sh - Xóa files deprecated sau Phase 2

echo "🧹 Starting Phase 2 Cleanup..."

# 1. Empty reranker files
echo "1️⃣ Removing empty reranker files..."
rm -f src/retrieval/ranking/cohere_reranker.py
rm -f src/retrieval/ranking/cross_encoder_reranker.py
rm -f src/retrieval/ranking/legal_score_reranker.py
rm -f src/retrieval/ranking/llm_reranker.py
echo "   ✅ Removed 4 reranker files"

# 2. Deprecated tests
echo "2️⃣ Removing deprecated test files..."
rm -f scripts/tests/reranking/test_phobert_reranker.py
rm -f scripts/tests/reranking/test_phobert_setup.py
rm -f scripts/tests/reranking/test_model_comparison.py
rm -f scripts/tests/reranking/test_end_to_end_reranking.py
rm -f scripts/tests/legacy_test_upload_api.py
rm -f scripts/tests/test_openai_reranker.py
rm -f scripts/tests/test_parallel_reranking.py
rm -f scripts/test_upload_v3.py
echo "   ✅ Removed 8 test files"

# 3. Deprecated notebooks
echo "3️⃣ Removing deprecated notebooks..."
rm -f notebooks/add_metadata_to_db-deprecated.ipynb
echo "   ✅ Removed 1 notebook"

# 4. Temp files
echo "4️⃣ Cleaning temp folder..."
cd temp/
rm -f CONVERSATION_SUMMARY_DETAILED.md
rm -f detailed_schema_analysis.md
rm -f make.sql
rm -f proposed_schema_v3.md
rm -f REFACTORING_PLAN*.md
rm -f schema_*.txt schema_*.sql
rm -f step4_completion_report.md
cd ..
echo "   ✅ Cleaned temp folder"

# 5. Archived docs
echo "5️⃣ Removing archived documentation..."
rm -f documents/technical/implementation-plans/PHASE_1_2_COMPLETION_SUMMARY.md
echo "   ✅ Removed 1 archived doc"

# 6. Old data
echo "6️⃣ Archiving old processed data..."
mkdir -p data/archive
mv data/processed_old/ "data/archive/processed_$(date +%Y%m%d)/"
echo "   ✅ Archived old data"

echo ""
echo "✅ Cleanup completed!"
echo ""
echo "📊 Summary:"
echo "   - 4 empty reranker files removed"
echo "   - 8 deprecated test files removed"
echo "   - 1 deprecated notebook removed"
echo "   - 11 temp files removed"
echo "   - 1 archived doc removed"
echo "   - Old data archived"
echo ""
echo "🔄 Next steps:"
echo "   1. Run tests: python scripts/tests/run_all_tests.py"
echo "   2. Verify API: ./start_server.sh"
echo "   3. Git commit: git add -A && git commit -m 'chore: cleanup phase 2 deprecated files'"
```

---

## 🧪 Verification Steps

### After Cleanup

1. **Run core tests**:
   ```bash
   python scripts/tests/test_core_system.py
   python scripts/tests/test_singleton_production.py
   python scripts/tests/unit/test_singleton_reranker.py
   ```

2. **Run API server**:
   ```bash
   ./start_server.sh
   # Test API endpoints
   curl http://localhost:8000/health
   curl http://localhost:8000/health/reranker
   ```

3. **Test retrieval**:
   ```bash
   python scripts/tests/test_quick_retrieval.py
   python scripts/tests/test_rag_queries.py
   ```

4. **Check imports**:
   ```bash
   python -c "from src.retrieval.ranking import get_singleton_reranker; print('✅ OK')"
   python -c "from src.retrieval.ranking import BGEReranker; print('✅ OK')"
   ```

---

## 📈 Estimated Impact

### Files Removed
- **Immediate cleanup**: ~30 files (18MB)
- **Medium priority**: ~20 files (12MB)
- **Total potential**: ~50 files (30MB)

### Benefits
- ✅ Cleaner codebase
- ✅ Easier navigation
- ✅ Reduced confusion
- ✅ Faster CI/CD
- ✅ Better maintainability

### Risks
- ⚠️ Mất historical context (mitigate: keep docs in archive/)
- ⚠️ Test coverage giảm (mitigate: verify core tests pass)

---

## ✅ Completion Checklist

### Phase 2 Cleanup
- [ ] Review cleanup report này
- [ ] Backup project (git commit trước khi cleanup)
- [ ] Run cleanup script `cleanup_phase2.sh`
- [ ] Verify tests pass
- [ ] Test API server
- [ ] Update README nếu cần
- [ ] Git commit cleanup changes
- [ ] Update `.github/copilot-instructions.md` if needed

---

**Generated**: 24/12/2025  
**By**: GitHub Copilot  
**Context**: Phase 2 completed (Nov 2025), cleanup deprecated files
