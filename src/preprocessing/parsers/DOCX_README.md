# DOCX Processing Module cho Văn bản Đấu thầu

**Version**: 1.0.0  
**Last updated**: 2025-10-30

Module tiền xử lý văn bản pháp luật đấu thầu từ file DOCX sang chunks tối ưu cho RAG system.

---

## 🎯 Tính năng

### 1. **DOCX Extractor** (`docx_extractor.py`)
- Extract text, tables, structure từ .docx files
- Detect metadata (doc type, number, year)
- Preserve hierarchical structure
- Export to JSON, Markdown

### 2. **Legal Document Cleaner** (`legal_cleaner.py`)
- Clean và normalize text
- Standardize bidding terms (đấu thầu, nhà thầu, etc.)
- Remove artifacts (page numbers, headers)
- Validate cleaned text

### 3. **Bidding Law Parser** (`bidding_law_parser.py`)
- Parse hierarchical structure:
  - Phần → Chương → Mục → Điều → Khoản → Điểm
- Build structure tree
- Extract metadata từ content
- Get Điều list, statistics

### 4. **DOCX Processing Pipeline** (`docx_pipeline.py`)
- End-to-end pipeline: DOCX → Structured JSON → Chunks → JSONL
- Batch processing support
- Multiple output formats
- Processing reports

---

## 🚀 Quick Start

### Dependencies

```bash
pip install python-docx
```

### Usage

#### Single File Processing

```python
from src.preprocessing.parsers.docx_pipeline import DocxProcessingPipeline

# Initialize
pipeline = DocxProcessingPipeline(
    max_chunk_size=2000,
    min_chunk_size=300,
    aggressive_clean=False
)

# Process
results = pipeline.process_single_file(
    "data/raw/Luat chinh/Luat Dau thau 2023.docx",
    output_dir="data/processed"
)

print(f"Created {len(results['chunks'])} chunks")
```

#### Batch Processing

```python
# Process all DOCX files in directory
batch_results = pipeline.process_batch(
    input_dir="data/raw/Luat chinh",
    output_dir="data/processed"
)
```

### Run Test Script

```bash
cd /home/sakana/Code/RAG-bidding
python3 scripts/test_docx_pipeline.py
```

---

## 📊 Processing Flow

```
┌─────────────┐
│   DOCX File │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│  1. Extract         │ ← DocxExtractor
│  - Text             │
│  - Tables           │
│  - Metadata         │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  2. Clean           │ ← LegalDocumentCleaner
│  - Normalize        │
│  - Remove artifacts │
│  - Validate         │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  3. Parse Structure │ ← BiddingLawParser
│  - Build tree       │
│  - Extract Điều     │
│  - Get hierarchy    │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  4. Chunk           │ ← OptimalLegalChunker
│  - By Điều/Khoản    │
│  - Add context      │
│  - Optimize size    │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  5. Export          │
│  - JSON (structured)│
│  - JSONL (chunks)   │
│  - MD (review)      │
│  - Report           │
└─────────────────────┘
```

---

## 📁 Output Formats

### 1. Structured JSON (`*_structured.json`)
```json
{
  "metadata": {
    "doc_type": "Luật",
    "doc_number": "98/2023-QH15",
    "title": "Luật Đấu thầu 2023"
  },
  "content": "...",
  "structure": {...},
  "statistics": {...}
}
```

### 2. Chunks JSONL (`*_chunks.jsonl`)
```json
{"id": "luat-98-2023_dieu_1", "text": "...", "metadata": {...}}
{"id": "luat-98-2023_dieu_2", "text": "...", "metadata": {...}}
```

### 3. Markdown (`*.md`)
```markdown
---
title: "Luật Đấu thầu 2023"
doc_type: "Luật"
---

Điều 1. Phạm vi điều chỉnh
...
```

### 4. Processing Report (`*_report.txt`)
```
================================================================================
DOCX PROCESSING REPORT
================================================================================

File: Luat Dau thau 2023.docx
Processed: 2025-10-30 15:30:00

METADATA:
----------------------------------------
  doc_type: Luật
  doc_number: 98/2023-QH15
  ...

EXTRACTION STATISTICS:
----------------------------------------
  char_count: 250,000
  dieu_count: 95
  ...
```

---

## 🔧 Configuration

### Pipeline Parameters

```python
DocxProcessingPipeline(
    max_chunk_size=2000,      # Max chars per chunk
    min_chunk_size=300,       # Min chars per chunk
    aggressive_clean=False    # Apply aggressive cleaning
)
```

### Cleaner Options

```python
cleaner.clean(
    text,
    aggressive=True  # Remove short lines, duplicates
)
```

---

## 📊 Supported Document Types

✅ **Luật** (Laws)
- Pattern: `Luật số XX/YYYY-QH`
- Example: Luật Đấu thầu 2023

✅ **Nghị định** (Decrees)
- Pattern: `Nghị định số XX/YYYY-NĐ-CP`
- Example: Nghị định 214/2025-NĐ-CP

✅ **Thông tư** (Circulars)
- Pattern: `Thông tư số XX/YYYY-TT-BTC`
- Example: Thông tư 79/2025-TT-BTC

---

## 🏗️ Structure Detection

| Level | Vietnamese | Example | Pattern |
|-------|-----------|---------|---------|
| 0 | Phần | PHẦN THỨ NHẤT | `PHẦN THỨ [IVXLCDM]+` |
| 1 | Chương | CHƯƠNG I | `CHƯƠNG [IVXLCDM]+` |
| 2 | Mục | Mục 1 | `Mục \d+` |
| 3 | Điều | Điều 1 | `Điều \d+[a-z]?` |
| 4 | Khoản | 1. | `\d+\.` |
| 5 | Điểm | a) | `[a-zđ]\)` |

---

## 📈 Performance

**Test với Luật Đấu thầu 2023:**
- File size: ~437 KB
- Processing time: ~3-5 seconds
- Extracted: ~250,000 chars
- Structure: 95 Điều, 420 Khoản
- Chunks created: ~270 chunks
- Average chunk size: ~900 chars

---

## 🔍 Validation

### Text Validation
- ✅ Has Điều structure
- ✅ Has Chương structure
- ✅ Minimum length (>1000 chars)
- ✅ Legal keywords present

### Chunk Validation
- ✅ Size within limits
- ✅ Has proper hierarchy
- ✅ Contains meaningful content
- ✅ Metadata complete

---

## 🧪 Testing

```bash
# Run test script
python3 scripts/test_docx_pipeline.py

# Expected output:
# - Extracted text statistics
# - Structure statistics
# - Chunk statistics
# - Output files in data/processed/test_output/
```

---

## 🔗 Integration với RAG System

### 1. Process DOCX files
```python
pipeline = DocxProcessingPipeline()
results = pipeline.process_single_file("law.docx", "output/")
```

### 2. Load chunks vào vector store
```python
from scripts.import_chunks import import_chunks_from_jsonl

import_chunks_from_jsonl("output/law_chunks.jsonl")
```

### 3. Query RAG system
```python
from src.retrieval.retrievers import create_retriever

retriever = create_retriever(mode="balanced")
docs = retriever.get_relevant_documents("quy trình đấu thầu")
```

---

## 📝 Notes

### Bidding-Specific Terms
- `đấu thầu` (bidding)
- `nhà thầu` (contractor)
- `gói thầu` (bidding package)
- `hồ sơ mời thầu` (tender documents)
- `hồ sơ dự thầu` (bid documents)
- `kế hoạch lựa chọn nhà thầu` (contractor selection plan)

### Known Limitations
1. Tables are detected but content not fully integrated
2. Complex formatting (bold, italic) not preserved
3. Footnotes và references cần manual review
4. Some legal references cần post-processing

---

## 🛠️ Troubleshooting

### Import errors
```bash
# Install missing package
pip install python-docx
```

### File not found
```bash
# Check file path
ls -la "data/raw/Luat chinh/"
```

### Low chunk count
- Check if document has proper structure (Điều, Chương)
- Verify text was extracted correctly
- Try with `aggressive_clean=False`

---

## 📚 Examples

See:
- `scripts/test_docx_pipeline.py` - Test script
- Each module's `if __name__ == "__main__"` section

---

**Author**: RAG-bidding team  
**Contact**: See project README
