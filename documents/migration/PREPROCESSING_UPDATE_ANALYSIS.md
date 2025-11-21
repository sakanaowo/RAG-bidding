# 📋 Preprocessing Update Analysis & Plan

**Date**: 2025-11-20  
**Purpose**: Phân tích upload pipeline hiện tại và plan để update cho documents table

---

## 🔍 Current State Analysis

### Upload Flow (AS-IS)

```
User Upload
    ↓
POST /api/upload/files (upload.py)
    ↓
UploadProcessingService.upload_files() (upload_service.py)
    ├─ Validate files (size, extension)
    ├─ Store temp files
    ├─ Create job tracking
    └─ Start async processing
        ↓
    _process_files_async()
        ├─ Classify document type (DocumentClassifier)
        ├─ WorkingUploadPipeline.process_file()
        │   ├─ DocxLoader/DocLoader.load() → Extract content
        │   ├─ Create ProcessedDocument
        │   ├─ ChunkFactory.chunk() → Generate chunks
        │   └─ ChunkEnricher.enrich_chunk() → Add metadata
        │
        ├─ OpenAIEmbedder.embed_chunks() → Generate vectors
        └─ PGVectorStore.add_chunks() → Insert into langchain_pg_embedding
            ↓
        ✅ DONE (no documents table insert)
```

### 🚨 KEY FINDINGS (from Database Analysis)

**CRITICAL ISSUES FOUND**:

### 1. Upload Pipeline Issue
- ✅ Chunks được lưu vào vector DB với full metadata
- ❌ **KHÔNG** có logic insert vào `documents` table
- ❌ **KHÔNG** có DocumentIDGenerator
- ❌ Upload mới sẽ KHÔNG tạo entry trong documents table

### 2. Migration Incomplete (767 chunks còn old format!)
```
🗄️ VECTOR DB (langchain_pg_embedding):
   - Total chunks: 6,242
   - Unique documents: 57
   - New format: 5,475 chunks (87.7%) ✅
   - Old format: 767 chunks (12.3%) ❌  ← "bidding_untitled"

📋 DOCUMENTS TABLE:
   - Total documents: 59
   - Documents with 0 chunks: 4 (exam PDFs chưa process)
   
🔍 CONSISTENCY:
   - Vector DB: 57 unique documents
   - Documents table: 59 documents
   - Match: ⚠️ NO
```

### 3. Missing Links (2 documents in vector DB NOT in documents table)
1. **bidding_untitled** (767 chunks) - Old format, chưa migrate xong!
2. **FORM-Bidding/2025#bee720** (3 chunks) - New format nhưng thiếu trong documents table

### 4. Zero-Chunk Documents (4 exam documents)
- EXAM-Ngân-hàng-câu-hỏi-CC
- EXAM-Ngân-hàng-câu-hỏi-th
- EXAM-NHCH_2692025_dot-2
- EXAM-NHCH_30925_bo_sung

→ Có entry trong documents table nhưng KHÔNG có chunks trong vector DB

---

## 📊 Database Tables Relationship

### After Migration (Documents Created Manually)

```
┌────────────────────────────────────┐
│   documents table                  │
│  (created manually in migration)  │
├────────────────────────────────────┤
│ - document_id (PK)                 │
│ - document_name                    │
│ - document_type                    │
│ - category                         │
│ - total_chunks                     │
│ - status                           │
│ - published_date                   │
│ - effective_date                   │
│ - source_file                      │
│ - created_at                       │
│ - updated_at                       │
└────────────────────────────────────┘
         ↑ relationship
         │ (document_id)
         │
┌────────────────────────────────────┐
│  langchain_pg_embedding            │
│  (vector DB - chunks storage)      │
├────────────────────────────────────┤
│ - id (UUID, PK)                    │
│ - embedding (vector)               │
│ - document (text content)          │
│ - cmetadata (JSONB)                │
│   ├─ document_id ◄──────────┘      │
│   ├─ chunk_id                      │
│   ├─ chunk_index                   │
│   ├─ document_type                 │
│   ├─ title                         │
│   ├─ source_file                   │
│   ├─ hierarchy                     │
│   ├─ dieu, khoan, diem             │
│   └─ ...                           │
└────────────────────────────────────┘
```

### Current Upload Flow Issue

```
NEW FILE UPLOAD
    ↓
WorkingUploadPipeline
    ↓
Generates chunks with metadata
    ├─ document_id: ??? (no generator!)
    ├─ chunk_id: ???
    └─ other metadata
    ↓
Inserts into langchain_pg_embedding ✅
    ↓
documents table: ❌ NOT UPDATED!
```

**Result**: New uploaded documents KHÔNG có entry trong documents table!

---

## 🎯 Required Changes

### 1. Create DocumentIDGenerator

**File**: `src/preprocessing/utils/document_id_generator.py` (NEW)

**Functionality**:
```python
class DocumentIDGenerator:
    @staticmethod
    def from_filename(filename: str, doc_type: str) -> str:
        """
        Generate document_id from filename.
        
        Examples:
            "Luật 90/2025/QH15.pdf" → "LUA-90-2025-QH15"
            "Nghị định 24/2024/NĐ-CP.pdf" → "ND-24-2024-NĐ-CP"
            "Mẫu 05 Báo cáo.docx" → "FORM-05-Báo-cáo"
        """
```

**Patterns**:
- Luật: `LUA-{số}-{năm}-{mã}` (e.g., LUA-90-2025-QH15)
- Nghị định: `ND-{số}-{năm}-{mã}` (e.g., ND-24-2024-NĐ-CP)
- Thông tư: `TT-{số}-{năm}-{mã}` (e.g., TT-03-2024-BKH)
- Quyết định: `QD-{số}-{năm}` (e.g., QD-218-2024-TTg)
- Biểu mẫu: `FORM-{descriptive-name}` (e.g., FORM-05-Mẫu-Báo-cáo)
- Mẫu: `TEMPLATE-{name}`
- Câu hỏi thi: `EXAM-{name}`

**Usage**:
```python
from src.preprocessing.utils.document_id_generator import DocumentIDGenerator

doc_id = DocumentIDGenerator.from_filename(
    filename="Luật 90/2025/QH15.pdf",
    doc_type="law"
)
# → "LUA-90-2025-QH15"
```

### 2. Update WorkingUploadPipeline

**File**: `src/preprocessing/upload_pipeline.py`

**Changes**:

```python
# ADD IMPORT
from .utils.document_id_generator import DocumentIDGenerator

class WorkingUploadPipeline:
    def process_file(self, file_path, document_type, batch_name):
        # EXISTING: Extract content, create chunks...
        
        # NEW: Generate document_id
        document_id = DocumentIDGenerator.from_filename(
            filename=file_path.name,
            doc_type=document_type
        )
        
        # ADD to processed_doc.metadata
        processed_doc.metadata['document_id'] = document_id
        
        # PROPAGATE to all chunks
        for chunk in chunks:
            chunk.metadata['document_id'] = document_id
            chunk.metadata['chunk_id'] = f"{document_id}_{chunk_type}_{index:04d}"
        
        return success, chunks, document_id  # RETURN document_id
```

### 3. Update UploadProcessingService

**File**: `src/api/services/upload_service.py`

**Add Database Session Management**:
```python
from sqlalchemy.ext.asyncio import AsyncSession
from src.config.database import get_db
from sqlalchemy import text
```

**New Method: Insert into documents table**:
```python
async def _insert_into_documents_table(
    self,
    document_id: str,
    filename: str,
    document_type: str,
    source_file: str,
    total_chunks: int
) -> None:
    """
    Insert document metadata into documents table.
    
    Called after chunks are successfully inserted into vector DB.
    """
    async with get_db() as db:
        # Extract document name from filename
        document_name = self._extract_document_name(filename)
        
        # Determine category
        category = self._determine_category(document_type, filename)
        
        query = text("""
            INSERT INTO documents (
                document_id,
                document_name,
                document_type,
                category,
                total_chunks,
                status,
                source_file,
                created_at,
                updated_at
            ) VALUES (
                :document_id,
                :document_name,
                :document_type,
                :category,
                :total_chunks,
                'active',
                :source_file,
                NOW(),
                NOW()
            )
            ON CONFLICT (document_id) DO UPDATE SET
                total_chunks = EXCLUDED.total_chunks,
                updated_at = NOW();
        """)
        
        await db.execute(query, {
            'document_id': document_id,
            'document_name': document_name,
            'document_type': document_type,
            'category': category,
            'total_chunks': total_chunks,
            'source_file': source_file
        })
        
        await db.commit()
```

**Update _process_files_async()**:
```python
async def _process_files_async(self, upload_id: str):
    # EXISTING: Process each file...
    
    # After WorkingUploadPipeline.process_file()
    success, chunks, document_id = self.working_pipeline.process_file(...)
    
    if success:
        # EXISTING: Embed and store chunks
        self.vector_store.add_chunks(chunks)
        
        # NEW: Insert into documents table
        await self._insert_into_documents_table(
            document_id=document_id,
            filename=file_path.name,
            document_type=classified_type,
            source_file=str(file_path),
            total_chunks=len(chunks)
        )
```

### 4. Add Helper Methods

```python
def _extract_document_name(self, filename: str) -> str:
    """Extract readable document name from filename."""
    # Remove extension
    name = Path(filename).stem
    
    # Clean up common patterns
    name = re.sub(r'^\d+[_\-\s]+', '', name)  # Remove leading numbers
    name = re.sub(r'[_\-]+', ' ', name)       # Replace separators
    
    # Truncate if too long
    if len(name) > 200:
        name = name[:200]
    
    return name.strip()


def _determine_category(self, doc_type: str, filename: str) -> str:
    """Determine document category."""
    category_mapping = {
        'law': 'Luật chính',
        'decree': 'Nghị định',
        'circular': 'Thông tư',
        'decision': 'Quyết định',
        'bidding': 'Hồ sơ mời thầu',
        'template': 'Mẫu báo cáo',
        'exam': 'Câu hỏi thi'
    }
    
    return category_mapping.get(doc_type, 'Khác')
```

---

## 🔄 Updated Upload Flow (TO-BE)

```
User Upload
    ↓
POST /api/upload/files
    ↓
UploadProcessingService.upload_files()
    ├─ Validate files
    ├─ Store temp files
    └─ Start async processing
        ↓
    _process_files_async()
        ├─ Classify document type
        │
        ├─ WorkingUploadPipeline.process_file()
        │   ├─ 🆕 Generate document_id (DocumentIDGenerator)
        │   ├─ Extract content
        │   ├─ Create ProcessedDocument (with document_id)
        │   ├─ Generate chunks (with document_id in metadata)
        │   └─ Enrich chunks
        │
        ├─ Embed chunks
        │
        ├─ PGVectorStore.add_chunks() → langchain_pg_embedding ✅
        │
        └─ 🆕 _insert_into_documents_table()
            ├─ Extract document_name from filename
            ├─ Determine category
            ├─ INSERT INTO documents (...)
            └─ Update total_chunks
                ↓
            ✅ COMPLETE (both tables updated)
```

---

## 📋 Implementation Checklist

### Phase 1: Create DocumentIDGenerator (30 min)
- [ ] Create `src/preprocessing/utils/document_id_generator.py`
- [ ] Implement `from_filename()` method
- [ ] Add pattern matching for each document type
- [ ] Write unit tests
- [ ] Verify with sample filenames

### Phase 2: Update WorkingUploadPipeline (30 min)
- [ ] Import DocumentIDGenerator
- [ ] Generate document_id in `process_file()`
- [ ] Add document_id to ProcessedDocument.metadata
- [ ] Propagate document_id to all chunks
- [ ] Update chunk_id format: `{document_id}_{type}_{index}`
- [ ] Return document_id from `process_file()`

### Phase 3: Update UploadProcessingService (1 hour)
- [ ] Add database session management imports
- [ ] Create `_insert_into_documents_table()` method
- [ ] Create `_extract_document_name()` helper
- [ ] Create `_determine_category()` helper
- [ ] Update `_process_files_async()` to call insert method
- [ ] Add error handling for DB insert failures
- [ ] Add rollback logic if insert fails

### Phase 4: Testing (1 hour)
- [ ] Create test file (e.g., sample law PDF)
- [ ] Test upload via API: `POST /api/upload/files`
- [ ] Verify chunks in langchain_pg_embedding
- [ ] Verify entry in documents table
- [ ] Check document_id format matches pattern
- [ ] Check total_chunks value
- [ ] Test with different document types
- [ ] Test error cases (duplicate document_id, etc.)

### Phase 5: Validation (30 min)
- [ ] Query both tables to verify consistency
- [ ] Check document_id in both tables match
- [ ] Verify total_chunks matches chunk count
- [ ] Test retrieval with new document_id
- [ ] Test /documents/catalog API with new document
- [ ] Run full test suite

---

## 🧪 Test Plan

### Test Case 1: Upload Law Document

**Input**:
```bash
curl -X POST http://localhost:8000/api/upload/files \
  -F "files=@Luật 90/2025/QH15.pdf" \
  -F "override_type=law"
```

**Expected**:
1. Document processed successfully
2. `langchain_pg_embedding`:
   - Chunks inserted with `document_id: LUA-90-2025-QH15`
   - chunk_ids format: `LUA-90-2025-QH15_dieu_0001`, etc.
3. `documents` table:
   - Row created with `document_id: LUA-90-2025-QH15`
   - `document_name: Luật 90 2025 QH15`
   - `document_type: law`
   - `category: Luật chính`
   - `total_chunks: {actual count}`
   - `status: active`

**Verification**:
```sql
-- Check vector DB
SELECT 
    cmetadata->>'document_id',
    cmetadata->>'chunk_id',
    COUNT(*)
FROM langchain_pg_embedding
WHERE cmetadata->>'document_id' = 'LUA-90-2025-QH15'
GROUP BY cmetadata->>'document_id', cmetadata->>'chunk_id';

-- Check documents table
SELECT * FROM documents WHERE document_id = 'LUA-90-2025-QH15';

-- Consistency check
SELECT 
    d.document_id,
    d.total_chunks as table_count,
    COUNT(e.id) as vector_count
FROM documents d
LEFT JOIN langchain_pg_embedding e 
    ON d.document_id = e.cmetadata->>'document_id'
WHERE d.document_id = 'LUA-90-2025-QH15'
GROUP BY d.document_id, d.total_chunks;
```

### Test Case 2: Upload Bidding Form

**Input**:
```bash
curl -X POST http://localhost:8000/api/upload/files \
  -F "files=@Mẫu 05 - Báo cáo đấu thầu.docx" \
  -F "override_type=bidding"
```

**Expected**:
- `document_id: FORM-05-Báo-cáo-đấu-thầu`
- Category: `Hồ sơ mời thầu`
- Both tables updated

### Test Case 3: Error Handling

**Input**: Upload file với duplicate document_id

**Expected**:
- Existing document should be updated (ON CONFLICT DO UPDATE)
- total_chunks should be updated to new value
- updated_at timestamp should change

---

## ⚠️ Potential Issues & Solutions

### Issue 1: Document ID Collision

**Problem**: Two files generate same document_id

**Solution**:
```python
# Add timestamp suffix if collision detected
if document_id_exists(document_id):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    document_id = f"{document_id}-{timestamp}"
```

### Issue 2: Transaction Failure

**Problem**: Chunks inserted but documents table insert fails

**Solution**:
```python
# Use transaction
async with db.begin():
    # Insert chunks
    vector_store.add_chunks(chunks)
    
    # Insert documents table
    await _insert_into_documents_table(...)
    
    # Both succeed or both rollback
```

### Issue 3: Metadata Extraction Failure

**Problem**: Cannot extract dates or other metadata from document

**Solution**:
```python
# Use nullable fields with defaults
published_date = extract_date(content) or None
effective_date = extract_date(content) or None

# Store in documents table with NULL values
```

---

## 📊 Success Metrics

After implementation:

1. **Consistency**: 100% of uploaded documents have entries in both tables
2. **Format**: All new document_ids follow pattern (LUA-, ND-, FORM-, etc.)
3. **Accuracy**: total_chunks matches actual chunk count
4. **Performance**: Upload time increase < 10% (DB insert is fast)
5. **Reliability**: No orphaned chunks or documents

---

## 🚀 Next Steps

1. **Run database visualization notebook** để confirm current state
2. **Implement DocumentIDGenerator** (Phase 1)
3. **Update upload pipeline** (Phase 2-3)
4. **Test with sample files** (Phase 4)
5. **Deploy to production** after validation

---

## 🔧 URGENT FIX REQUIRED

### Issue 1: Complete Migration (767 old format chunks)

**Problem**: Document `bidding_untitled` chưa được migrate, còn 767 chunks dùng old format

**Solution**: Re-run migration cho document này
```sql
-- Check current state
SELECT 
    cmetadata->>'document_id' as old_id,
    cmetadata->>'chunk_id' as old_chunk_id,
    COUNT(*) as chunks
FROM langchain_pg_embedding
WHERE cmetadata->>'document_id' = 'bidding_untitled'
GROUP BY cmetadata->>'document_id', cmetadata->>'chunk_id';

-- Option 1: Update to proper format
-- Determine proper document_id from metadata/filename
UPDATE langchain_pg_embedding
SET cmetadata = jsonb_set(
    jsonb_set(
        cmetadata,
        '{document_id}',
        '"FORM-Bidding-HSMT"'  -- Replace with proper ID
    ),
    '{chunk_id}',
    -- Update chunk_id accordingly
)
WHERE cmetadata->>'document_id' = 'bidding_untitled';

-- Option 2: Delete if not needed
DELETE FROM langchain_pg_embedding
WHERE cmetadata->>'document_id' = 'bidding_untitled';
```

### Issue 2: Backfill Missing Documents

**Problem**: 2 documents có chunks nhưng không có trong documents table

**Solution**: 
```python
# Script: backfill_missing_documents.py

import psycopg2
from datetime import datetime

def backfill_missing_documents():
    conn = psycopg2.connect(...)
    cursor = conn.cursor()
    
    # Get documents in vector DB but not in documents table
    query = """
    WITH vector_docs AS (
        SELECT 
            cmetadata->>'document_id' as document_id,
            cmetadata->>'document_type' as document_type,
            cmetadata->>'title' as title,
            cmetadata->>'source_file' as source_file,
            COUNT(*) as total_chunks
        FROM langchain_pg_embedding
        GROUP BY 
            cmetadata->>'document_id',
            cmetadata->>'document_type',
            cmetadata->>'title',
            cmetadata->>'source_file'
    )
    SELECT v.*
    FROM vector_docs v
    LEFT JOIN documents d ON v.document_id = d.document_id
    WHERE d.document_id IS NULL;
    """
    
    missing = cursor.execute(query).fetchall()
    
    for row in missing:
        doc_id, doc_type, title, source, chunks = row
        
        # Insert into documents table
        insert_query = """
        INSERT INTO documents (
            document_id, document_name, document_type,
            category, total_chunks, status,
            source_file, created_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        ON CONFLICT (document_id) DO UPDATE SET
            total_chunks = EXCLUDED.total_chunks,
            updated_at = NOW();
        """
        
        cursor.execute(insert_query, (
            doc_id,
            title or doc_id,  # Use title or fallback to doc_id
            doc_type or 'unknown',
            determine_category(doc_type),
            chunks,
            'active',
            source
        ))
    
    conn.commit()
    print(f"✅ Backfilled {len(missing)} documents")

def determine_category(doc_type):
    mapping = {
        'law': 'Luật chính',
        'decree': 'Nghị định',
        'circular': 'Thông tư',
        'decision': 'Quyết định',
        'bidding': 'Hồ sơ mời thầu',
        'template': 'Mẫu báo cáo',
        'exam': 'Câu hỏi thi'
    }
    return mapping.get(doc_type, 'Khác')
```

### Issue 3: Handle Zero-Chunk Documents

**Options**:
1. **Delete from documents table** (if they're not real documents)
2. **Mark as 'pending'** (if they need to be processed)
3. **Process them** (if source files exist)

```sql
-- Option 1: Delete
DELETE FROM documents WHERE total_chunks = 0;

-- Option 2: Mark as pending
UPDATE documents 
SET status = 'pending'
WHERE total_chunks = 0;

-- Option 3: Check if source files exist and reprocess
SELECT document_id, source_file
FROM documents
WHERE total_chunks = 0;
```

---

## 📝 Related Files

**Current Implementation**:
- `src/preprocessing/upload_pipeline.py` - Main pipeline
- `src/api/services/upload_service.py` - Upload service
- `src/api/routers/upload.py` - API endpoints

**To Create**:
- `src/preprocessing/utils/document_id_generator.py` - NEW
- `src/preprocessing/utils/__init__.py` - NEW (if doesn't exist)

**To Update**:
- `src/preprocessing/upload_pipeline.py` - Add document_id generation
- `src/api/services/upload_service.py` - Add documents table insert

**For Testing**:
- `notebooks/analysis/database-structure-visualization.ipynb` - DB inspection
- `notebooks/testing/test-upload-endpoint.ipynb` - NEW (will create)

**Documentation**:
- `documents/migration/POST_MIGRATION_UPDATE_PLAN.md` - Overall plan
- `documents/migration/PREPROCESSING_UPDATE_PLAN.md` - This document
