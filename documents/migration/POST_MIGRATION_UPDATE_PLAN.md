# 📋 POST-MIGRATION UPDATE PLAN
## Plan chi tiết để cập nhật tất cả endpoints, pipelines và tests sau migration document_id

**Migration Context:**
- ✅ Đã migrate 57/59 documents từ format cũ (`bidding_untitled_*`) sang format mới (FORM-*, LUA-*, TEMPLATE-*, EXAM-*)
- ✅ Vector DB: 6,242 chunks với document_id mới
- ✅ Documents table: 59 documents với metadata đầy đủ
- 🔧 **Cần update**: API endpoints, retrieval logic, preprocessing, tests

---

## 🎯 OBJECTIVES

1. **API Endpoints**: Đảm bảo tất cả endpoints trả về document_id mới (không còn `bidding_untitled`)
2. **Retrieval Pipelines**: Verify tất cả retrievers hoạt động đúng với metadata mới
3. **Context Formatting**: Hiển thị document_id theo format user-friendly
4. **Preprocessing**: Cập nhật pipeline để generate document_id mới cho documents tương lai
5. **Test Suite**: Comprehensive tests cho toàn bộ system với document_id mới
6. **Backward Compatibility**: Đảm bảo không break existing queries

---

## 📊 CURRENT STATE ANALYSIS

### ✅ Already Working (No Changes Needed)

**1. Vector Database**
- ✅ All chunks có `cmetadata->>'document_id'` mới (FORM-*, LUA-*, etc.)
- ✅ All chunks có `cmetadata->>'source_file'` để trace back to original files
- ✅ Documents table có full metadata (59 documents)

**2. API Routers - Documents Management**
- ✅ `/api/documents/catalog` - Đã query theo `document_id` mới
- ✅ `/api/documents/catalog/{document_id}` - Đã support document_id mới
- ✅ `/api/documents/catalog/{document_id}/status` - Update status cho all chunks
- ✅ Document name mapping file: `src/config/document_name_mapping.json`

**3. Basic Retrieval**
- ✅ BaseVectorRetriever query vector DB trực tiếp → tự động dùng document_id mới
- ✅ MetadataFilter đã có sẵn filter logic

### ⚠️ Need Verification (May Work But Need Testing)

**1. QA Chain (`src/generation/chains/qa_chain.py`)**
- 📍 Function `format_document_reference()` format metadata cho sources
- 📍 Function `answer()` tạo retriever động + format sources
- ⚠️ **Check**: Sources có hiển thị document_id mới đúng không?

**2. Context Formatter (`src/generation/formatters/context_formatter.py`)**
- 📍 Method `_clean_document_id()` replace old prefixes (`law_`, `decree_`, `bidding_`, `untitled`)
- ⚠️ **Risk**: Có thể vẫn expect old format → cần update regex
- ⚠️ **Check**: Format FORM-*, LUA-* có user-friendly không?

**3. All Retrievers**
- 📍 `BaseVectorRetriever` - Query PGVector
- 📍 `EnhancedRetriever` - Add query enhancement + reranking
- 📍 `FusionRetriever` - RAG-Fusion với RRF
- 📍 `AdaptiveKRetriever` - Dynamic K selection
- ⚠️ **Check**: Tất cả đều trả về chunks với document_id mới?

### 🚨 Need Updates (Confirmed Issues)

**1. Preprocessing Pipeline**
- 🔴 **Critical**: Khi upload documents mới, generate document_id theo format cũ hay mới?
- 📁 Files to check:
  - `src/preprocessing/upload_pipeline.py`
  - `src/preprocessing/base/base_pipeline.py`
  - `src/preprocessing/schema/unified_schema.py`

**2. Test Files**
- 🔴 Test assertions expect old format (`bidding_untitled`, `law_untitled`)
- 📁 Files to update:
  - `scripts/tests/test_api_endpoints.py`
  - `scripts/tests/test_core_system.py`
  - `scripts/test/integration/test_e2e_pipeline.py`
  - `scripts/tests/retrieval/test_api_with_filtering.py`

**3. Example Documents in Code**
- 🔴 Hardcoded example document_ids trong docstrings/comments
- 📁 Files:
  - `src/generation/formatters/context_formatter.py` (line 210+)
  - `src/preprocessing/schema/models/document_info_types.py`

---

## 📅 IMPLEMENTATION PLAN

### **Phase 1: Verification & Quick Wins** (2 giờ)

#### Task 1.1: Test Current API Endpoints ⏱️ 30 phút
```bash
# Khởi động server
./start_server.sh

# Test health check
curl http://localhost:8000/health

# Test /ask endpoint
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Luật đấu thầu 2025 quy định gì?", "mode": "balanced"}'

# Verify sources có document_id mới
# Expected: FORM-*, LUA-*, không có bidding_untitled
```

**Success Criteria:**
- ✅ Response có `sources` với document_id format mới
- ✅ `detailed_sources` hiển thị document name rõ ràng
- ✅ Không có `bidding_untitled` hoặc `law_untitled` trong output

#### Task 1.2: Test Documents Management API ⏱️ 30 phút
```bash
# List all documents
curl "http://localhost:8000/api/documents/catalog?limit=100"

# Get specific document
curl "http://localhost:8000/api/documents/catalog/LUA-90-2025-QH15"

# Get document stats
curl "http://localhost:8000/api/documents/catalog/LUA-90-2025-QH15/stats"
```

**Success Criteria:**
- ✅ Catalog trả về 57-59 documents với document_id mới
- ✅ Mỗi document có `title` từ mapping file
- ✅ Status filtering hoạt động (default: `active`)

#### Task 1.3: Update Context Formatter ⏱️ 1 giờ

**File**: `src/generation/formatters/context_formatter.py`

**Changes:**

```python
# OLD (line 172):
def _clean_document_id(self, doc_id: str) -> str:
    """Clean document ID for display."""
    doc_id = (
        doc_id.replace("law_", "").replace("decree_", "").replace("circular_", "")
    )
    doc_id = doc_id.replace("decision_", "").replace("bidding_", "")
    doc_id = doc_id.replace("untitled", "Văn bản")
    doc_id = doc_id.replace("_", " ")
    return doc_id.strip()

# NEW:
def _clean_document_id(self, doc_id: str) -> str:
    """
    Clean document ID for display.
    
    Handles new format: FORM-*, LUA-*, TEMPLATE-*, EXAM-*
    """
    import re
    
    # New format patterns
    patterns = {
        r'^FORM-(.+)': lambda m: f"Biểu mẫu: {m.group(1).replace('-', ' ')}",
        r'^LUA-(.+)': lambda m: f"Luật: {m.group(1).replace('-', ' ')}",
        r'^ND-(.+)': lambda m: f"Nghị định: {m.group(1).replace('-', ' ')}",
        r'^TT-(.+)': lambda m: f"Thông tư: {m.group(1).replace('-', ' ')}",
        r'^QD-(.+)': lambda m: f"Quyết định: {m.group(1).replace('-', ' ')}",
        r'^TEMPLATE-(.+)': lambda m: f"Mẫu: {m.group(1).replace('-', ' ')}",
        r'^EXAM-(.+)': lambda m: f"Câu hỏi thi: {m.group(1).replace('-', ' ')}",
    }
    
    for pattern, formatter in patterns.items():
        match = re.match(pattern, doc_id)
        if match:
            return formatter(match)
    
    # Fallback for old format (backward compatibility)
    doc_id = (
        doc_id.replace("law_", "Luật ")
        .replace("decree_", "Nghị định ")
        .replace("circular_", "Thông tư ")
        .replace("bidding_", "Hồ sơ ")
        .replace("untitled", "Văn bản")
        .replace("_", " ")
    )
    
    return doc_id.strip()

# Update example document (line 210+)
if __name__ == "__main__":
    from langchain_core.documents import Document

    example_doc = Document(
        page_content="Nhà thầu tham dự thầu phải đáp ứng các điều kiện về năng lực và kinh nghiệm theo quy định...",
        metadata={
            "chunk_id": "LUA-90-2025-QH15_dieu_0047",  # NEW FORMAT
            "document_id": "LUA-90-2025-QH15",  # NEW FORMAT
            "document_type": "law",
            "title": "Luật Đấu thầu 2025",
            "dieu": "47",
            "khoan": "1",
            # ...
```

---

### **Phase 2: Update Preprocessing Pipeline** (3 giờ)

#### Task 2.1: Analyze Upload Pipeline ⏱️ 1 giờ

**Goal**: Hiểu flow tạo document_id khi upload documents mới

**Files to Read:**
```
src/preprocessing/upload_pipeline.py
src/preprocessing/base/base_pipeline.py
src/preprocessing/schema/unified_schema.py
src/preprocessing/schema/models/document_info_types.py
```

**Questions to Answer:**
1. Khi upload file mới, document_id được generate ở đâu?
2. Format hiện tại là gì? (Có phải vẫn dùng `{type}_untitled_{name}`?)
3. Có logic detect document type (law, decree, bidding, template)?
4. Metadata extraction có đúng với new schema không?

#### Task 2.2: Update Document ID Generation ⏱️ 1 giờ

**Tạo hoặc update file**: `src/preprocessing/utils/document_id_generator.py`

```python
"""
Generate document_id theo format mới sau migration.

Format chuẩn:
- Luật: LUA-{số}-{năm}-{mã QH/CP} (e.g., LUA-90-2025-QH15)
- Nghị định: ND-{số}-{năm}-{CP/NĐ} (e.g., ND-24-2024-NĐ-CP)
- Thông tư: TT-{số}-{năm}-{TT} (e.g., TT-03-2024-BKH)
- Quyết định: QD-{số}-{năm} (e.g., QD-218-2024-TTg)
- Biểu mẫu: FORM-{descriptive-name} (e.g., FORM-05-Mẫu-Báo-cáo-đấu-thầu)
- Mẫu báo cáo: TEMPLATE-{descriptive-name}
- Câu hỏi thi: EXAM-{tên-ngắn}
"""

import re
from typing import Optional
from datetime import datetime


class DocumentIDGenerator:
    """Generate standardized document_id for new uploads."""
    
    @staticmethod
    def from_filename(filename: str, doc_type: str) -> str:
        """
        Generate document_id from filename.
        
        Args:
            filename: Original filename (e.g., "Luật 90/2025/QH15.pdf")
            doc_type: Document type (law, decree, circular, bidding, template, exam)
            
        Returns:
            Standardized document_id
        """
        # Remove extension
        name_base = filename.rsplit('.', 1)[0]
        
        # Detect document type from filename patterns
        if doc_type == "law" or "luật" in filename.lower():
            return DocumentIDGenerator._generate_law_id(name_base)
        
        elif doc_type == "decree" or "nghị định" in filename.lower():
            return DocumentIDGenerator._generate_decree_id(name_base)
        
        elif doc_type == "circular" or "thông tư" in filename.lower():
            return DocumentIDGenerator._generate_circular_id(name_base)
        
        elif doc_type == "decision" or "quyết định" in filename.lower():
            return DocumentIDGenerator._generate_decision_id(name_base)
        
        elif doc_type in ["bidding", "bidding_template"]:
            return DocumentIDGenerator._generate_form_id(name_base)
        
        elif doc_type in ["template", "report_template"]:
            return DocumentIDGenerator._generate_template_id(name_base)
        
        elif doc_type == "exam_questions":
            return DocumentIDGenerator._generate_exam_id(name_base)
        
        else:
            # Fallback: sanitize filename
            return DocumentIDGenerator._sanitize_id(name_base)
    
    @staticmethod
    def _generate_law_id(name: str) -> str:
        """
        Generate law ID from name.
        
        Examples:
            "Luật 90/2025/QH15" → "LUA-90-2025-QH15"
            "Luật Đấu thầu 2025" → "LUA-Đấu-thầu-2025"
        """
        # Pattern 1: "Luật {số}/{năm}/{mã}"
        match = re.search(r'(\d+)[/\-](\d{4})[/\-]([A-Z0-9\-]+)', name, re.IGNORECASE)
        if match:
            num, year, code = match.groups()
            return f"LUA-{num}-{year}-{code}"
        
        # Pattern 2: "Luật {tên} {năm}"
        match = re.search(r'luật\s+(.+?)\s+(\d{4})', name, re.IGNORECASE)
        if match:
            title, year = match.groups()
            title_slug = title.replace(' ', '-')
            return f"LUA-{title_slug}-{year}"
        
        # Fallback: clean name
        clean = name.replace('Luật', '').replace('luật', '').strip()
        return f"LUA-{DocumentIDGenerator._sanitize_id(clean)}"
    
    @staticmethod
    def _generate_decree_id(name: str) -> str:
        """
        Generate decree ID.
        
        Examples:
            "Nghị định 24/2024/NĐ-CP" → "ND-24-2024-NĐ-CP"
        """
        match = re.search(r'(\d+)[/\-](\d{4})[/\-](.+)', name, re.IGNORECASE)
        if match:
            num, year, code = match.groups()
            code = code.replace('/', '-').upper()
            return f"ND-{num}-{year}-{code}"
        
        clean = name.replace('Nghị định', '').replace('nghị định', '').strip()
        return f"ND-{DocumentIDGenerator._sanitize_id(clean)}"
    
    @staticmethod
    def _generate_circular_id(name: str) -> str:
        """Generate circular ID."""
        match = re.search(r'(\d+)[/\-](\d{4})[/\-](.+)', name, re.IGNORECASE)
        if match:
            num, year, code = match.groups()
            code = code.replace('/', '-').upper()
            return f"TT-{num}-{year}-{code}"
        
        clean = name.replace('Thông tư', '').replace('thông tư', '').strip()
        return f"TT-{DocumentIDGenerator._sanitize_id(clean)}"
    
    @staticmethod
    def _generate_decision_id(name: str) -> str:
        """Generate decision ID."""
        match = re.search(r'(\d+)[/\-](\d{4})', name, re.IGNORECASE)
        if match:
            num, year = match.groups()
            return f"QD-{num}-{year}"
        
        clean = name.replace('Quyết định', '').replace('quyết định', '').strip()
        return f"QD-{DocumentIDGenerator._sanitize_id(clean)}"
    
    @staticmethod
    def _generate_form_id(name: str) -> str:
        """
        Generate form/bidding template ID.
        
        Examples:
            "Mẫu 05 - Báo cáo đấu thầu" → "FORM-05-Báo-cáo-đấu-thầu"
        """
        # Remove common prefixes
        clean = re.sub(r'^(Mẫu|Biểu mẫu|Form)\s*', '', name, flags=re.IGNORECASE)
        clean = DocumentIDGenerator._sanitize_id(clean)
        return f"FORM-{clean}"
    
    @staticmethod
    def _generate_template_id(name: str) -> str:
        """Generate template ID for report templates."""
        clean = DocumentIDGenerator._sanitize_id(name)
        return f"TEMPLATE-{clean}"
    
    @staticmethod
    def _generate_exam_id(name: str) -> str:
        """Generate exam questions ID."""
        clean = DocumentIDGenerator._sanitize_id(name)
        return f"EXAM-{clean}"
    
    @staticmethod
    def _sanitize_id(text: str) -> str:
        """
        Sanitize text to valid ID format.
        
        Rules:
        - Replace spaces with hyphens
        - Remove special chars except hyphens
        - Limit length to 100 chars
        """
        # Replace spaces with hyphens
        text = text.replace(' ', '-')
        
        # Remove special characters except Vietnamese, numbers, hyphens
        text = re.sub(r'[^\w\-]', '', text, flags=re.UNICODE)
        
        # Remove multiple consecutive hyphens
        text = re.sub(r'-+', '-', text)
        
        # Truncate to 100 chars
        if len(text) > 100:
            text = text[:100].rstrip('-')
        
        return text.strip('-')


# Tests
if __name__ == "__main__":
    gen = DocumentIDGenerator()
    
    test_cases = [
        ("Luật 90/2025/QH15.pdf", "law", "LUA-90-2025-QH15"),
        ("Nghị định 24/2024/NĐ-CP.pdf", "decree", "ND-24-2024-NĐ-CP"),
        ("Thông tư 03/2024/TT-BKH.pdf", "circular", "TT-03-2024-TT-BKH"),
        ("Mẫu 05 - Báo cáo đấu thầu.docx", "bidding", "FORM-05-Báo-cáo-đấu-thầu"),
        ("Ngân hàng câu hỏi CCDT.pdf", "exam_questions", "EXAM-Ngân-hàng-câu-hỏi-CCDT"),
    ]
    
    print("🧪 Testing DocumentIDGenerator:")
    for filename, doc_type, expected in test_cases:
        result = gen.from_filename(filename, doc_type)
        status = "✅" if result == expected else "❌"
        print(f"{status} {filename} ({doc_type})")
        print(f"   Generated: {result}")
        if result != expected:
            print(f"   Expected:  {expected}")
        print()
```

#### Task 2.3: Update Upload Pipeline ⏱️ 1 giờ

**File**: `src/preprocessing/upload_pipeline.py`

**Changes:**
1. Import `DocumentIDGenerator`
2. Replace hardcoded `{type}_untitled_{name}` logic với generator
3. Update metadata để include document_id mới

```python
# ADD IMPORT
from src.preprocessing.utils.document_id_generator import DocumentIDGenerator

# UPDATE trong process() hoặc extract_metadata()
def extract_metadata(file_path: str, doc_type: str) -> dict:
    """Extract metadata and generate document_id."""
    filename = Path(file_path).name
    
    # NEW: Generate document_id từ filename
    document_id = DocumentIDGenerator.from_filename(filename, doc_type)
    
    # OLD code đã generate doc_id như thế nào → replace
    
    metadata = {
        "document_id": document_id,  # NEW FORMAT
        "document_type": doc_type,
        "source_file": file_path,
        "filename": filename,
        # ... other metadata
    }
    
    return metadata
```

---

### **Phase 3: Update Test Suite** (3 giờ)

#### Task 3.1: Update API Endpoint Tests ⏱️ 1 giờ

**File**: `scripts/tests/test_api_endpoints.py`

**Changes:**
```python
# OLD assertions expecting bidding_untitled
assert "bidding_untitled" in sources[0]

# NEW assertions với document_id format mới
def test_ask_endpoint():
    response = requests.post(
        "http://localhost:8000/ask",
        json={"question": "Luật đấu thầu 2025 quy định gì?", "mode": "balanced"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify new document_id format
    assert "sources" in data
    sources = data["sources"]
    
    # Check at least one source uses new format
    has_new_format = any(
        re.match(r'^(LUA|ND|TT|QD|FORM|TEMPLATE|EXAM)-', src) 
        for src in sources
    )
    assert has_new_format, f"Expected new document_id format, got: {sources}"
    
    # Should NOT contain old format
    has_old_format = any(
        "untitled" in src.lower() or "_untitled_" in src
        for src in sources
    )
    assert not has_old_format, f"Found old format in sources: {sources}"


def test_documents_catalog():
    response = requests.get("http://localhost:8000/api/documents/catalog?limit=100")
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) >= 57  # Should have at least 57 documents
    
    # Verify all document_ids use new format
    for doc in data:
        doc_id = doc["document_id"]
        assert re.match(r'^(LUA|ND|TT|QD|FORM|TEMPLATE|EXAM)-', doc_id), \
            f"Invalid document_id format: {doc_id}"
        
        # Should have title from mapping
        assert len(doc["title"]) > 5, f"Missing title for {doc_id}"


def test_get_specific_document():
    """Test getting specific document with new document_id."""
    # Use actual document_id from migration
    doc_id = "LUA-90-2025-QH15"
    
    response = requests.get(f"http://localhost:8000/api/documents/catalog/{doc_id}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["document_id"] == doc_id
    assert data["total_chunks"] > 0
    assert "chunks" in data
```

#### Task 3.2: Update E2E Pipeline Tests ⏱️ 1 giờ

**File**: `scripts/test/integration/test_e2e_pipeline.py`

**Changes:**
```python
def test_retrieval_returns_new_format():
    """Test that retrieval returns chunks with new document_id."""
    pipeline = RAGPipeline()
    
    result = pipeline.run(
        query="Luật đấu thầu 2025",
        k=5
    )
    
    docs = result["docs"]
    assert len(docs) > 0, "No documents retrieved"
    
    for doc in docs:
        doc_id = doc.metadata.get("document_id")
        chunk_id = doc.metadata.get("chunk_id")
        
        # Verify new format
        assert doc_id, f"Missing document_id in metadata: {doc.metadata}"
        assert re.match(r'^(LUA|ND|TT|QD|FORM|TEMPLATE|EXAM)-', doc_id), \
            f"Invalid document_id format: {doc_id}"
        
        # Verify chunk_id matches document_id
        assert chunk_id.startswith(doc_id), \
            f"chunk_id {chunk_id} doesn't start with document_id {doc_id}"
        
        # Should NOT have old format
        assert "untitled" not in doc_id.lower()


def test_context_formatting():
    """Test that context formatter displays document_id correctly."""
    from src.generation.formatters.context_formatter import ContextFormatter
    from langchain_core.documents import Document
    
    formatter = ContextFormatter()
    
    test_doc = Document(
        page_content="Test content",
        metadata={
            "document_id": "LUA-90-2025-QH15",
            "chunk_id": "LUA-90-2025-QH15_dieu_0047",
            "title": "Luật Đấu thầu 2025",
            "dieu": "47",
            "khoan": "1"
        }
    )
    
    formatted = formatter.format([test_doc])
    
    # Should display user-friendly format
    assert "Luật: 90 2025 QH15" in formatted or "Luật Đấu thầu" in formatted
    assert "Điều 47" in formatted
    
    # Should NOT show raw document_id
    assert "LUA-90-2025-QH15" not in formatted  # Raw format hidden
```

#### Task 3.3: Create Comprehensive Test Notebook ⏱️ 1 giờ

**File**: `notebooks/testing/post-migration-endpoint-tests.ipynb`

Tạo notebook mới với các test cases:

1. **Test /ask endpoint với các modes**
   - Fast, Balanced, Quality, Adaptive
   - Verify sources hiển thị document_id mới

2. **Test /documents/catalog**
   - List all documents
   - Filter by type, status
   - Verify 57-59 documents

3. **Test retrieval với filters**
   - Filter by document_id
   - Filter by document_type
   - Filter by status

4. **Test context formatting**
   - Verify hierarchy display
   - Verify document name từ mapping
   - Verify không còn "untitled"

5. **Performance tests**
   - Query latency với document_id mới
   - Cache effectiveness
   - Memory usage

---

### **Phase 4: Documentation & Cleanup** (2 giờ)

#### Task 4.1: Update Documentation ⏱️ 1 giờ

**Files to Update:**

1. **README.md**
   - Add note về migration completion
   - Update example queries với document_id mới

2. **API Documentation**
   ```markdown
   ## Document ID Format
   
   Sau migration (Nov 2025), tất cả document_id theo format:
   
   - **Luật**: LUA-{số}-{năm}-{mã} (e.g., LUA-90-2025-QH15)
   - **Nghị định**: ND-{số}-{năm}-{mã} (e.g., ND-24-2024-NĐ-CP)
   - **Thông tư**: TT-{số}-{năm}-{mã} (e.g., TT-03-2024-BKH)
   - **Quyết định**: QD-{số}-{năm} (e.g., QD-218-2024-TTg)
   - **Biểu mẫu**: FORM-{tên} (e.g., FORM-05-Mẫu-Báo-cáo)
   - **Mẫu**: TEMPLATE-{tên}
   - **Câu hỏi thi**: EXAM-{tên}
   
   Old format (`bidding_untitled_*`, `law_untitled_*`) đã deprecated.
   ```

3. **documents/technical/API_DOCUMENT_MANAGEMENT_GUIDE.md**
   - Update examples với document_id mới
   - Remove references to old format

#### Task 4.2: Clean Up Old Code ⏱️ 30 phút

**Remove/Archive:**
1. Old migration scripts (nếu không cần reference)
2. Deprecated notebooks trong `notebooks/ingestion/`
3. Old test data với format cũ

**Mark as deprecated:**
1. Functions xử lý old format (add deprecation warning)
2. Legacy endpoints (nếu có)

#### Task 4.3: Create Migration Summary Report ⏱️ 30 phút

**File**: `documents/migration/MIGRATION_COMPLETION_SUMMARY.md`

```markdown
# Migration Completion Summary

## Overview
- **Date Completed**: 2025-11-20
- **Total Documents Migrated**: 57 (active) + 2 (inactive) = 59
- **Total Chunks**: 6,242
- **Old Format**: bidding_untitled_*, law_untitled_*
- **New Format**: LUA-*, ND-*, TT-*, FORM-*, etc.

## Changes Made

### 1. Database
- ✅ Updated all chunks with new document_id
- ✅ Updated all chunks with source_file metadata
- ✅ Created documents table with full metadata

### 2. API Endpoints
- ✅ /ask - Returns sources với document_id mới
- ✅ /documents/catalog - Lists documents theo document_id mới
- ✅ /documents/catalog/{id} - Get document by new ID
- ✅ /documents/catalog/{id}/status - Update status

### 3. Pipelines
- ✅ Updated preprocessing để generate new document_id
- ✅ Updated context formatter để display user-friendly names
- ✅ All retrievers hoạt động với metadata mới

### 4. Tests
- ✅ Updated test assertions để expect new format
- ✅ Created comprehensive test notebook
- ✅ All tests passing với document_id mới

## Backward Compatibility

Old document_id format vẫn được support trong:
- Context formatter (fallback logic)
- Test data (archived)

## Next Steps

1. Monitor production queries for any issues
2. Preprocess 4 exam question PDFs (optional)
3. Consider deprecating old format support sau 3 months
```

---

## 🚀 EXECUTION CHECKLIST

### Before Starting
- [ ] Backup current database
- [ ] Create git branch: `feature/post-migration-updates`
- [ ] Document current system state

### Phase 1: Verification ✅
- [ ] Test current /ask endpoint
- [ ] Test /documents/catalog API
- [ ] Update context_formatter.py
- [ ] Verify sources display correctly

### Phase 2: Preprocessing ✅
- [ ] Create DocumentIDGenerator
- [ ] Update upload_pipeline.py
- [ ] Test with sample file upload
- [ ] Verify new documents get correct ID

### Phase 3: Tests ✅
- [ ] Update test_api_endpoints.py
- [ ] Update test_e2e_pipeline.py
- [ ] Create comprehensive test notebook
- [ ] Run full test suite
- [ ] All tests passing

### Phase 4: Cleanup ✅
- [ ] Update README.md
- [ ] Update API documentation
- [ ] Create migration summary
- [ ] Archive old code
- [ ] Commit all changes

### Post-Deployment
- [ ] Monitor API logs for errors
- [ ] Check query performance
- [ ] Verify user-facing sources
- [ ] Collect feedback

---

## 📊 SUCCESS METRICS

### Functional
- ✅ 100% API tests passing
- ✅ Zero old format (bidding_untitled) in responses
- ✅ All document_ids follow new pattern
- ✅ Context formatter displays user-friendly names

### Performance
- ⏱️ Query latency unchanged (<3s p95)
- 📊 No increase in error rate
- 💾 Memory usage stable

### User Experience
- 📚 Document names readable (từ mapping file)
- 🔍 Sources include proper hierarchy (Điều, Khoản)
- ⚡ Response times acceptable

---

## ⚠️ RISKS & MITIGATION

### Risk 1: Breaking Existing Queries
**Mitigation:**
- Keep backward compatibility trong context formatter
- Test với sample queries trước khi deploy
- Monitor error logs post-deployment

### Risk 2: Performance Degradation
**Mitigation:**
- Profile code changes
- Test với concurrent users
- Keep reranker singleton fix

### Risk 3: Missing Edge Cases
**Mitigation:**
- Comprehensive test coverage
- Test với real production queries
- Gradual rollout

---

## 📞 SUPPORT

**Issues or Questions:**
- Check `documents/technical/` for detailed guides
- Review migration notebook: `notebooks/migration/document-structure-migration.ipynb`
- Test notebook: `notebooks/testing/post-migration-endpoint-tests.ipynb`

**Related Documents:**
- `documents/migration/MIGRATION_PLAN_UPDATE_METADATA_ONLY.md`
- `documents/technical/API_DOCUMENT_MANAGEMENT_GUIDE.md`
- `documents/technical/PIPELINE_INTEGRATION_SUMMARY.md`
