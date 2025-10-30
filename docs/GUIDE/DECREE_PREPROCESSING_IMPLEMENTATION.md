# Decree Preprocessing Module - Implementation Summary

**Date:** October 30, 2025  
**Document Type:** Nghị định (Decree)  
**Pattern:** Following Law preprocessing architecture

## ✅ Implementation Complete

Đã hoàn thành module preprocessing chuyên biệt cho văn bản Nghị định, theo mô hình modular đã thiết lập cho Luật.

---

## 📁 Module Structure

```
src/preprocessing/decree_preprocessing/
├── __init__.py                    # Package exports
├── pipeline.py                    # DecreePreprocessingPipeline (main)
├── metadata_mapper.py             # DecreeMetadataMapper (25 DB fields)
│
├── extractors/
│   ├── __init__.py
│   └── decree_extractor.py        # DecreeExtractor (kế thừa DocxExtractor)
│
├── parsers/
│   ├── __init__.py
│   └── decree_parser.py           # DecreeParser (simplified hierarchy)
│
├── cleaners/
│   ├── __init__.py
│   └── decree_cleaner.py          # DecreeCleaner (kế thừa LegalDocumentCleaner)
│
└── validators/                    # (empty - dự trữ)
```

---

## 🔧 Components Implemented

### 1. DecreeExtractor (`extractors/decree_extractor.py`)
- **Base:** Kế thừa từ `DocxExtractor` (law_preprocessing)
- **Patterns:** Simplified cho Nghị định
  - ✅ Chương (Chapter)
  - ✅ Điều (Article)
  - ✅ Khoản (Clause)
  - ✅ Điểm (Point)
  - ❌ Không có Phần, Mục (simpler than Law)
- **Metadata:** Auto-extract decree number + year từ filename/title

### 2. DecreeParser (`parsers/decree_parser.py`)
- **Base:** Kế thừa từ `BaseParser`
- **Hierarchy:** `Chương → Điều → Khoản → Điểm` (4 levels)
- **Structure Tree:** StructureNode với simplified hierarchy
- **Methods:**
  - `parse()` - Parse decree text to tree
  - `get_hierarchy_path()` - Build path string
  - `validate_structure()` - Check for valid Điều nodes
  - `get_structure_levels()` - Return ["document", "chuong", "dieu", "khoan", "diem"]

### 3. DecreeCleaner (`cleaners/decree_cleaner.py`)
- **Base:** Kế thừa từ `LegalDocumentCleaner`
- **Additions:** Decree-specific patterns
  - Remove duplicate "Nghị định số..." headers
  - Remove government signature blocks
  - Reuse legal text normalization

### 4. DecreeMetadataMapper (`metadata_mapper.py`)
- **DB Schema:** 25 required fields (same as Law)
- **Decree-Specific Logic:**
  - ⏰ **Validity:** 2 years (vs 5 years for laws)
  - 📅 **Status:** Auto-detect based on year
    - Active: ≤ 2 years old
    - Expired: > 2 years old
  - 🏢 **Agency:** Default to "Chính phủ"
- **Methods:**
  - `map_chunk_to_db()` - Single chunk mapping
  - `map_batch()` - Batch mapping
  - `validate_record()` - Check 25 fields
  - `_extract_doc_info()` - Parse decree number/year from filename
  - `_determine_status()` - Calculate status from year

### 5. DecreePreprocessingPipeline (`pipeline.py`)
- **Base:** Kế thừa từ `BaseDocumentPipeline`
- **7-Step Flow:**
  1. **Extract** - DOCX → text + metadata
  2. **Clean** - Remove noise, normalize
  3. **Parse** - Build structure tree
  4. **Chunk** - Using LegalDocumentChunker (hierarchical strategy)
  5. **Map to DB** - 25-field schema mapping
  6. **Validate** - Check all records
  7. **Export** - JSONL output
- **Abstract Methods:**
  - `process()` - Main processing method
  - `process_single_file()` - Single file wrapper
  - `process_batch()` - Batch processing
  - `validate_output()` - Output validation
  - `map_to_db_schema()` - Schema mapping (wrapper)

---

## 🏭 PipelineFactory Integration

**Updated:** `src/preprocessing/parsers/pipeline_factory.py`

```python
def _create_decree_pipeline(self, **kwargs):
    """Create pipeline cho Nghị định"""
    from ..decree_preprocessing import DecreePreprocessingPipeline

    return DecreePreprocessingPipeline(
        chunk_size=kwargs.get("chunk_size", 512),
        chunk_overlap=kwargs.get("chunk_overlap", 50),
        output_dir=kwargs.get("output_dir", None),
    )
```

**Auto-Detection Patterns:**
- Filename: `r"(?i)nghi.*dinh.*\d+.*\d{4}"`, `r"(?i)nd[-_]?\d+"`
- Content: "CHÍNH PHỦ", "Nghị định số..."

---

## 🧪 Testing Results

**Test Script:** `scripts/test_decree_pipeline.py`

**Test File:** `ND 214 - 4.8.2025 - Thay thế NĐ24-original.docx`

### ✅ Test Results:
```
Processing Steps:
[1/7] Extract: 425,702 chars
[2/7] Clean: 425,479 chars  
[3/7] Parse: 1,722 structure nodes
[4/7] Chunk: 1,068 chunks
[5/7] Map: 1,068 DB records
[6/7] Validate: 1,068/1,068 valid (100%)
[7/7] Export: ND 214...processed.jsonl

Output:
✅ 1,068 chunks total
✅ All 25 DB fields present
✅ Status: active (2025 decree)
✅ Avg: 805 chars/chunk
✅ Total: 860,089 chars
```

### Sample Chunk:
```json
{
  "chunk_id": "decree_214_2025_chunk_0000",
  "doc_type": "decree",
  "doc_number": "214",
  "doc_year": "2025",
  "status": "active",
  "doc_name": "...",
  "content": "Điều 1. Phạm vi điều chỉnh...",
  ...  // 25 fields total
}
```

---

## 📊 DB Schema (25 Fields)

Same as Law preprocessing:

| Field | Type | Decree-Specific |
|-------|------|-----------------|
| `chunk_id` | str | decree_{num}_{year}_chunk_{idx} |
| `content` | str | Chunk text |
| `doc_id` | str | decree_{num}_{year} |
| `doc_type` | str | "decree" |
| `doc_number` | str | "214" |
| `doc_year` | str | "2025" |
| `doc_name` | str | Full decree title |
| `issuing_agency` | str | "Chính phủ" |
| `effective_date` | str | ISO format |
| **`status`** | str | **2-year validity** |
| `source_url` | str | File path |
| `hierarchy_path` | str | Structure path |
| `parent_id` | str | Parent node ID |
| `parent_type` | str | Parent node type |
| `section_title` | str | Section title |
| `section_number` | str | Section number |
| `chunk_index` | int | 0-based index |
| `total_chunks` | int | Total chunks |
| `original_length` | int | Original char count |
| `cleaned_length` | int | Cleaned char count |
| `has_tables` | bool | Has tables |
| `confidence_score` | float | 0.0-1.0 |
| `processing_timestamp` | str | ISO timestamp |
| `metadata_version` | str | "2.0" |
| `related_docs` | list | Related doc IDs |

---

## 🔄 Reused Components

**From `law_preprocessing/`:**
- `DocxExtractor` - DOCX extraction logic
- `LegalDocumentCleaner` - Text cleaning patterns

**From `chunking/`:**
- `LegalDocumentChunker` - Hierarchical chunking strategy

**From `base/`:**
- `BaseDocumentPipeline` - Pipeline interface
- `BaseParser` - Parser interface
- `StructureNode` - Tree node structure

---

## 🎯 Key Differences: Decree vs Law

| Aspect | Decree | Law |
|--------|--------|-----|
| **Hierarchy** | Chương → Điều → Khoản → Điểm | Phần → Chương → Mục → Điều → Khoản → Điểm |
| **Levels** | 4 | 6 |
| **Validity** | 2 years | 5 years |
| **Agency** | Chính phủ | Quốc hội |
| **Complexity** | Simpler | More complex |

---

## 📝 Code Quality

**Fixes Applied During Implementation:**
1. ✅ Fixed method signatures (parent class compatibility)
2. ✅ Fixed StructureNode field names (`type` vs `node_type`)
3. ✅ Fixed chunker integration (document dict format)
4. ✅ Fixed metadata extraction (handle empty strings)
5. ✅ Implemented all abstract methods from base classes
6. ✅ Renamed `chunk-strategy.py` → `chunk_strategy.py` (import fix)

**Code Stats:**
- DecreeExtractor: ~100 lines
- DecreeParser: ~150 lines
- DecreeCleaner: ~60 lines
- DecreeMetadataMapper: ~270 lines
- DecreePreprocessingPipeline: ~220 lines
- **Total:** ~800 lines (decree module)

---

## 🚀 Usage Example

```python
from src.preprocessing.decree_preprocessing import DecreePreprocessingPipeline
from pathlib import Path

# Create pipeline
pipeline = DecreePreprocessingPipeline(
    chunk_size=512,
    chunk_overlap=50,
    output_dir=Path("data/outputs/decrees"),
)

# Process decree file
file_path = Path("data/raw/Nghi dinh/ND 214-2025.docx")
db_records = pipeline.process(file_path)

# Result: List of 25-field DB records ready for vector DB
print(f"✅ {len(db_records)} chunks ready for DB insertion")
```

---

## 🔮 Future Enhancements

**Potential TODOs:**
1. [ ] Implement validators/ module for decree-specific validation
2. [ ] Add hierarchy path tracking during chunking (match chunks to structure)
3. [ ] Add decree-to-law relationship extraction
4. [ ] Implement decree amendment detection
5. [ ] Add parallel processing for batch operations

---

## 📚 Documentation Files

**Created:**
- ✅ `src/preprocessing/decree_preprocessing/__init__.py` - Package exports
- ✅ `scripts/test_decree_pipeline.py` - Test script
- ✅ This summary document

**Referenced:**
- `docs/GUIDE/LAW_PREPROCESSING_RESTRUCTURE.md` - Law module architecture
- `docs/GUIDE/PREPROCESSING_ARCHITECTURE.md` - Multi-document design

---

## ✨ Summary

**Decree preprocessing module hoàn toàn functional và tested:**

✅ **7-step pipeline** working end-to-end  
✅ **25 DB fields** properly mapped  
✅ **2-year validity** logic implemented  
✅ **1,068 chunks** generated from test file  
✅ **100% validation** success rate  
✅ **Modular architecture** following established patterns  
✅ **PipelineFactory** integration complete  

**Ready for production use!** 🎉
