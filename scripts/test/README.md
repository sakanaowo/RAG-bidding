# Test & Debug Scripts Directory
## Thư mục chứa các script test và debug cho RAG-Bidding system

**Ngày cập nhật**: 30/10/2025  
**Mục đích**: Tập trung tất cả test scripts và debug tools

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