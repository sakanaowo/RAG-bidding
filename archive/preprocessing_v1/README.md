# 📦 Preprocessing V1 Archive

**Ngày archive**: 31/10/2025  
**Lý do**: Migration sang Preprocessing Architecture V2 với Unified Schema

---

## 📂 Nội dung Archive

### 1. **Pipeline-specific Code (Đã di chuyển)**
- `bidding_preprocessing/` - Pipeline xử lý Hồ sơ mời thầu
- `circular_preprocessing/` - Pipeline xử lý Thông tư
- `decree_preprocessing/` - Pipeline xử lý Nghị định
- `law_preprocessing/` - Pipeline xử lý Luật

### 2. **Base Classes (Sao lưu để tham khảo)**
- `base_original/` - Base classes cho document preprocessing
  - `base_extractor.py`
  - `base_parser.py`
  - `base_cleaner.py`
  - `base_pipeline.py`

### 3. **Validators (Sao lưu để tham khảo)**
- `validators_original/` - Validation logic
  - Có thể tái sử dụng trong V2

### 4. **Parsers (Sao lưu để tham khảo)**
- `parsers_original/` - Document parsers
  - `docx_pipeline.py` - Logic xử lý DOCX (tốt, nên tham khảo)
  - `md_processor.py` - Logic xử lý Markdown
  - `utils.py` - TokenChecker và utilities (sẽ tái sử dụng)

---

## 🎯 Tại sao Archive?

### ✅ **Lợi ích**:
1. **Safety net**: Có thể rollback nếu V2 có vấn đề
2. **Learning**: Tham khảo logic đã được test (DOCX parsing, regex patterns)
3. **Validation**: So sánh output V1 vs V2
4. **Documentation**: Hiểu được cách hệ thống cũ hoạt động

### ❌ **Vấn đề của V1**:
1. **Fragmented schema**: 4 pipelines với 55 fields khác nhau
2. **No schema validation**: Không có Pydantic validation
3. **Hard to extend**: Thêm document type mới mất nhiều thời gian
4. **Low reusability**: Code duplication cao

---

## 🚀 V2 Improvements

### **Architecture V2**:
```
src/preprocessing/
├── schema/              # Unified schema (21 core fields)
├── base/                # BaseLegalPipeline (7 stages)
├── pipelines/           # 7 document-specific pipelines
├── loaders/             # DOCX, PDF, Excel loaders
├── chunking/            # Chunking strategies
├── enrichment/          # Semantic enrichment
├── quality/             # Quality analysis
└── orchestrator.py      # Pipeline orchestration
```

### **Key Improvements**:
- ✅ **Unified Schema**: 21 core fields cho tất cả 7 loại văn bản
- ✅ **Pydantic Validation**: Type-safe với automatic validation
- ✅ **Extensible**: Thêm document type mới <1 tuần
- ✅ **Reusable**: 60-70% code reuse
- ✅ **Quality-first**: Validation ở mọi stage
- ✅ **Vietnam-specific**: Enums phù hợp với hệ thống pháp luật VN

---

## 📊 Migration Timeline

- **Week 1-2**: Implement schema + base classes
- **Week 3-4**: Implement core components (loaders, chunkers)
- **Week 5-8**: Implement 7 pipelines
- **Week 9-10**: Enrichment + Quality
- **Week 11-12**: Parallel run V1 + V2, validation
- **Week 13**: Full cutover to V2
- **Week 14**: Archive cleanup (optional)

---

## 🔗 Tham khảo

- **V2 Architecture**: `/documents/preprocess plan/PREPROCESSING_ARCHITECTURE.md`
- **Deep Analysis**: `/documents/preprocess plan/phase 1 report/DEEP_ANALYSIS_REPORT.md`
- **Unified Schema**: `/documents/preprocess plan/phase 1 report/SCHEMA_IMPLEMENTATION_GUIDE.md`

---

## ⚠️ Lưu ý

**KHÔNG XÓA** archive này cho đến khi:
1. ✅ V2 đã chạy ổn định >1 tháng trong production
2. ✅ Tất cả test cases đều pass
3. ✅ Quality metrics V2 >= V1
4. ✅ Stakeholders approve

**Nếu cần rollback**:
```bash
# Restore V1
mv archive/preprocessing_v1/bidding_preprocessing src/preprocessing/
mv archive/preprocessing_v1/circular_preprocessing src/preprocessing/
mv archive/preprocessing_v1/decree_preprocessing src/preprocessing/
mv archive/preprocessing_v1/law_preprocessing src/preprocessing/
```

---

**Status**: ✅ Archived  
**Last used**: 31/10/2025  
**Next review**: After V2 production deployment
