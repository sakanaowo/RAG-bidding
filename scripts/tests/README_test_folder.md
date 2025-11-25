# 🧪 Test Suite Structure

This directory contains all test files organized by functionality.

## 📁 Directory Structure

### `/integration/`
**End-to-end and integration tests:**
- Cross-type batch processing tests
- Full quality tests
- Integration test runners
- Document quality tests
- Template tests (bidding, HSYC, circulars)
- Edge cases and validators
- Database tests
- Context formatting tests
- Retrieval tests (with/without filters)

**Files:** `test_e2e_pipeline.py`, `test_context_formatter.py`, `test_retrieval*.py`, etc.

### `/preprocessing/`
**Document loading and preprocessing tests:**
- Loader tests (DOCX, DOC, PDF, Bidding, Report)
- Preprocessing pipeline tests
- All loaders integration test

**Files:** `test_*_loader.py`, `test_bidding_preprocessing.py`, `test_all_loaders.py`

### `/chunking/`
**Chunking strategy tests:**
- Hybrid chunker tests
- Chunking integration tests
- Chunking strategies comparison
- Chunk pipeline tests

**Files:** `test_bidding_hybrid_chunker.py`, `test_chunking_*.py`, `test_chunk_pipeline.py`

### `/pipeline/`
**Document processing pipeline tests:**
- Decree pipeline
- Circular pipeline
- DOCX pipeline
- E2E pipeline
- All pipelines format validation

**Files:** `test_*_pipeline.py`, `test_all_pipelines_format.py`

## 🚀 Running Tests

### Quick Start

Run all integration tests at once:

```bash
cd scripts/test
python integration/run_integration_tests.py
```
- Show pass/fail status for each test
- Estimated time: ~15-30 minutes

### Individual Tests

You can also run tests individually:

```bash
# Test 1: End-to-End Pipeline (CRITICAL)
python test_e2e_pipeline.py

# Test 2: Cross-Type Batch Processing (IMPORTANT)
python test_cross_type_batch.py

# Test 3: Edge Cases & Error Handling (IMPORTANT)
python test_edge_cases.py

# Test 4: Database Basic Operations (CRITICAL)
python test_database_basic.py

# Test 5: Performance & Scalability (MEDIUM)
python test_performance.py
```

### Test Descriptions

#### 1. End-to-End Pipeline Test (`test_e2e_pipeline.py`)
- **Priority:** CRITICAL
- **Duration:** ~5 minutes
- **Purpose:** Validate complete pipeline from DOCX → UnifiedLegalChunk
- **Tests:**
  - Document extraction and parsing
  - Chunker auto-selection
  - Schema validation
  - Quality checks
- **Success Criteria:** All 4 document types process without errors

#### 2. Cross-Type Batch Test (`test_cross_type_batch.py`)
- **Priority:** IMPORTANT
- **Duration:** ~5 minutes
- **Purpose:** Test batch processing across document types
- **Tests:**
  - ChunkFactory auto-selection consistency
  - Output format uniformity
  - Batch processing efficiency
- **Success Criteria:** Same doc type → same chunker, consistent output format

#### 3. Edge Cases Test (`test_edge_cases.py`)
- **Priority:** IMPORTANT
- **Duration:** ~5 minutes
- **Purpose:** Validate error handling and robustness
- **Tests:**
  - Empty/minimal documents
  - Very large documents (>1MB)
  - Special characters & Unicode
  - Malformed metadata
  - Invalid document types
- **Success Criteria:** Graceful error handling, no crashes

#### 4. Database Basic Test (`test_database_basic.py`)
- **Priority:** CRITICAL
- **Duration:** ~5 minutes
- **Purpose:** Test chunk persistence and retrieval
- **Tests:**
  - Serialize/deserialize chunks
  - Save/load to JSON (mock DB)
  - Filter by metadata
  - Round-trip data integrity
- **Success Criteria:** No data loss, consistent format

#### 5. Performance Test (`test_performance.py`)
- **Priority:** MEDIUM
- **Duration:** ~10 minutes
- **Purpose:** Benchmark processing speed and memory usage
- **Tests:**
  - Batch processing 20+ documents
  - Memory usage tracking
  - Throughput measurement
  - Bottleneck identification
- **Success Criteria:**
  - Total time < 30s for 20 docs
  - Peak memory < 500MB
  - Throughput > 50 chunks/second

### Expected Results

All tests should **PASS** if:
- ✅ Chunkers are properly optimized (90%+ quality)
- ✅ All document types are supported
- ✅ Error handling is robust
- ✅ Performance meets requirements

### Troubleshooting

**Test fails with "File not found":**
- Ensure test data exists in `data/raw/` directories
- Check file paths in test scripts

**Memory errors:**
- Reduce `max_files` parameter in performance test
- Close other applications

**Timeout:**
- Increase `time_budget` in `run_integration_tests.py`
- Run tests individually instead of batch

### Test Output

Each test generates:
- Console output with pass/fail status
- Detailed metrics and timings
- Error messages (if any)

The integration test runner generates:
- `data/outputs/INTEGRATION_TEST_REPORT.md` - Comprehensive markdown report
- Summary of all test results
- Priority analysis
- Next steps recommendations

---

## 📝 Unit Tests (Existing)

### Document Type Tests

```bash
# Test all document types
python test_all_pipelines_format.py

# Test specific types
python test_bidding_preprocessing.py
python test_circular_pipeline.py
python test_decree_pipeline.py
python test_hsyc_templates.py

# Test all circulars
python test_all_circulars.py
python test_main_circulars.py
```

### Other Tests

```bash
# Test integrity validation
python test_integrity_validator.py

# Test DOCX processing
python test_docx_pipeline.py
```

---

## 📊 Current Test Coverage

### Phase 2B - Integration Testing (100% ✅)

- ✅ End-to-End Pipeline Testing
- ✅ Cross-Document Type Batch Processing  
- ✅ Edge Cases & Error Handling
- ✅ Database Integration (Basic)
- ✅ Performance & Scalability

### Remaining Gaps (Future Phases)

- ⏳ Full Database Integration (PostgreSQL)
- ⏳ API Integration Testing
- ⏳ Backward Compatibility Testing
- ⏳ Production Load Testing
- ⏳ Security & Validation Testing

---

## 🎯 Integration Test Plan

Detailed plan available at: `documents/INTEGRATION_TEST_PLAN_TONIGHT.md`

Timeline: 4 hours (19:00 - 23:00)
- 19:00-19:45: Test #1 - E2E Pipeline
- 19:45-20:30: Test #2 - Cross-Type Batch
- 20:30-21:15: Test #3 - Edge Cases
- 21:15-22:00: Test #4 - Database Basic
- 22:00-22:45: Test #5 - Performance
- 22:45-23:00: Generate Report

Success Criteria:
- All 5 scripts created ✅
- All tests run without crashes ✅
- E2E pipeline works for 4 types ✅
- Integration report generated ✅

---

**Last Updated:** 2024 (Phase 2B - Integration Testing Complete)

---

## 📁 Cấu trúc thư mục

### Pipeline Testing Scripts
- `test_all_pipelines_format.py` - Comprehensive testing framework cho tất cả pipeline
- `test_bidding_preprocessing.py` - Test bidding document preprocessing
- `test_circular_pipeline.py` - Test circular document pipeline
- `test_decree_pipeline.py` - Test decree document pipeline
- `test_docx_pipeline.py` - Test DOCX file processing

### Validation & Integrity Scripts  
- `test_integrity_validator.py` - Database integrity validation
- `test_all_circulars.py` - Comprehensive circular processing test
- `test_main_circulars.py` - Main circular pipeline testing
- `test_hsyc_templates.py` - HSYC template processing test

---

## 🚀 Cách sử dụng

### Chạy test cho pipeline cụ thể:
```bash
# Test bidding pipeline
python scripts/test/test_bidding_preprocessing.py

# Test circular pipeline  
python scripts/test/test_circular_pipeline.py

# Test decree pipeline
python scripts/test/test_decree_pipeline.py
```

### Chạy comprehensive testing:
```bash
# Test tất cả pipelines và format consistency
python scripts/test/test_all_pipelines_format.py

# Test circular documents comprehensive
python scripts/test/test_all_circulars.py
```

### Validate system integrity:
```bash
# Check database và data integrity
python scripts/test/test_integrity_validator.py
```

---

## 📊 Test Categories

### 1. Format Consistency Testing
- **File**: `test_all_pipelines_format.py`
- **Purpose**: Validate output format consistency across all pipelines
- **Coverage**: Bidding, Circular, Law, Decree pipelines

### 2. Pipeline-Specific Testing
- **Files**: `test_*_pipeline.py`
- **Purpose**: Deep testing cho từng pipeline riêng biệt
- **Coverage**: Input validation, processing logic, output format

### 3. Document Type Testing
- **Files**: `test_*_circulars.py`, `test_hsyc_templates.py`
- **Purpose**: Test specific document types và templates
- **Coverage**: Document parsing, metadata extraction

### 4. System Integrity Testing
- **File**: `test_integrity_validator.py`
- **Purpose**: Validate database integrity và data consistency
- **Coverage**: Database schema, data relationships, constraints

---

## 🔧 Development Guidelines

### Adding New Tests
1. **Naming Convention**: `test_[component]_[purpose].py`
2. **Location**: `/scripts/test/`
3. **Documentation**: Add description trong file này

### Test Structure
```python
#!/usr/bin/env python3
"""
Test script for [component/purpose]
Author: [Your name]
Date: [Date]
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Test implementation
def main():
    # Test logic here
    pass

if __name__ == "__main__":
    main()
```

### Best Practices
- ✅ **Comprehensive logging** cho debug
- ✅ **Clear success/failure indicators**
- ✅ **Sample data inclusion** khi cần thiết
- ✅ **Error handling** và graceful failures
- ✅ **Performance metrics** khi relevant

---

## 📝 Maintenance Notes

### Last Migration: 30/10/2025
- Moved all test files từ root directory
- Moved all test files từ `/scripts/` 
- Consolidated vào `/scripts/test/`
- Added documentation và organization

### Regular Maintenance Tasks
- [ ] Update tests khi pipeline changes
- [ ] Add new tests cho new features
- [ ] Review và refactor outdated tests
- [ ] Update documentation

---

## 🔗 Related Documents

- **Technical Analysis**: `/documents/analysis_report.md`
- **Upgrade Plan**: `/documents/UPGRADE_PLAN.md`
- **Executive Summary**: `/documents/EXECUTIVE_SUMMARY.md`

---

## 📞 Support

**Questions about tests**: Contact development team  
**New test requests**: Create issue trong project tracker  
**Bug reports**: Include test output và environment details