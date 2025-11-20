# Simple Documents Schema Migration

**Mục đích:** Tạo bảng `documents` đơn giản để quản lý 70 documents về đấu thầu

---

## 📊 Database Schema

### Documents Table (9 fields - đơn giản)

```sql
documents (
    id                UUID PRIMARY KEY
    document_id       VARCHAR(255) UNIQUE    -- "LUA-90-2025-QH15"
    document_name     TEXT                    -- "Luật số 90/2025 về Đấu thầu"
    category          VARCHAR(100)            -- 7 categories
    document_type     VARCHAR(50)             -- law, decree, circular, etc.
    source_file       TEXT                    -- "data/raw/Luat chinh/..."
    file_name         TEXT                    -- "Luat so 90 2025.docx"
    total_chunks      INTEGER                 -- Số chunks sau khi process
    status            VARCHAR(50)             -- active/inactive/archived
    created_at        TIMESTAMP
    updated_at        TIMESTAMP
)
```

**Indexes:**
- `idx_documents_category` - Filter by category
- `idx_documents_type` - Filter by document type
- `idx_documents_status` - Toggle active/inactive
- `idx_documents_source` - Lookup by source file

---

## 🗂️ 7 Categories Mapping

| Category | Folder | Document Type | Files | Example document_id |
|----------|--------|---------------|-------|-------------------|
| Luật chính | `Luat chinh/` | `law` | 4 | `LUA-90-2025-QH15` |
| Nghị định | `Nghi dinh/` | `decree` | 1 | `ND-214-2025-CP` |
| Thông tư | `Thong tu/` | `circular` | 2 | `TT-00-QUYET-DINH` |
| Quyết định | `Quyet dinh/` | `decision` | 1 | `QD-1667-BYT` |
| Hồ sơ mời thầu | `Ho so moi thau/` | `bidding_form` | 46 | `FORM-HSYC-XAYLAP-01A` |
| Mẫu báo cáo | `Mau bao cao/` | `report_template` | 10 | `TEMPLATE-BC-01` |
| Câu hỏi thi | `Cau hoi thi/` | `exam_question` | 6 | `EXAM-CAU-HOI-01` |

**Total:** 70 documents

---

## 🚀 Migration Steps (2 giờ)

### Step 1: Extract Metadata (30 phút)

```bash
cd /home/sakana/Code/RAG-bidding

# Run extraction script
python scripts/migration/002_extract_simple_metadata.py
```

**Output:** `data/processed/documents_metadata.json`

Expected structure:
```json
[
  {
    "document_id": "LUA-90-2025-QH15",
    "document_name": "Luat so 90 2025-qh15",
    "category": "Luật chính",
    "document_type": "law",
    "source_file": "data/raw/Luat chinh/Luat so 90 2025-qh15.docx",
    "file_name": "Luat so 90 2025-qh15.docx",
    "total_chunks": 0,
    "status": "active"
  },
  ...
]
```

### Step 2: Create Table & Populate (1 giờ)

```bash
# Run migration script
python scripts/migration/003_populate_documents_table.py
```

**What it does:**
1. Creates `documents` table (if not exists)
2. Inserts 70 documents from metadata JSON
3. Verifies insertion with count queries

**Expected output:**
```
✅ Inserted: 70 documents
📊 Total documents: 70

📁 Documents by category:
   Hồ sơ mời thầu: 46 documents
   Mẫu báo cáo: 10 documents
   Câu hỏi thi: 6 documents
   Luật chính: 4 documents
   Thông tư: 2 documents
   Nghị định: 1 documents
   Quyết định: 1 documents
```

### Step 3: Verify (30 phút)

```bash
# Connect to database
psql -U sakana -d rag_bidding_v2

# Check documents table
SELECT COUNT(*) FROM documents;
-- Expected: 70

# Check by category
SELECT category, COUNT(*) 
FROM documents 
GROUP BY category 
ORDER BY COUNT(*) DESC;

# Sample documents
SELECT document_id, document_name, category 
FROM documents 
LIMIT 10;
```

---

## 📝 Usage Examples

### Query documents by category

```sql
-- Get all laws
SELECT * FROM documents 
WHERE category = 'Luật chính' 
AND status = 'active';

-- Get all bidding forms
SELECT * FROM documents 
WHERE category = 'Hồ sơ mời thầu'
ORDER BY file_name;
```

### Toggle document status

```sql
-- Deactivate a document
UPDATE documents 
SET status = 'inactive', updated_at = NOW()
WHERE document_id = 'LUA-90-2025-QH15';

-- Reactivate
UPDATE documents 
SET status = 'active', updated_at = NOW()
WHERE document_id = 'LUA-90-2025-QH15';
```

### Update chunk count (after processing)

```sql
UPDATE documents 
SET total_chunks = 255
WHERE document_id = 'LUA-90-2025-QH15';
```

---

## 🔄 Next Steps (After migration)

### 1. Update Preprocessing Pipeline

Modify `src/preprocessing/document_processor.py` to:
- Load document info from `documents` table
- Use `document_id` from table (not generated)
- Update `total_chunks` after processing

### 2. Update Chunks Metadata

When inserting chunks to `langchain_pg_embedding`:
```json
{
  "document_id": "LUA-90-2025-QH15",  // From documents table
  "source_file": "data/raw/Luat chinh/...",
  "document_name": "Luật số 90/2025",
  "category": "Luật chính",
  "status": "active"
}
```

### 3. Update API Endpoints

```python
# Get catalog from documents table
@router.get("/documents/catalog")
async def get_catalog(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(Document).where(Document.status == "active")
    if category:
        query = query.where(Document.category == category)
    
    result = await db.execute(query)
    docs = result.scalars().all()
    
    return {"documents": [doc.to_dict() for doc in docs]}

# Toggle document
@router.patch("/documents/{document_id}/status")
async def toggle_status(
    document_id: str,
    status: str,
    db: AsyncSession = Depends(get_db)
):
    await db.execute(
        update(Document)
        .where(Document.document_id == document_id)
        .values(status=status)
    )
    await db.commit()
    return {"message": f"Updated {document_id} to {status}"}
```

---

## ✅ Benefits

1. **Simple:** Only 9 fields, easy to understand
2. **Fast:** Can migrate in 2 hours
3. **Flexible:** Can add more fields later if needed
4. **Category-based:** Matches your 7 folder structure
5. **Toggle-ready:** Status field for activate/deactivate
6. **Track chunks:** total_chunks for monitoring

---

## 🎯 Timeline

| Task | Duration | Status |
|------|----------|--------|
| Extract metadata | 30 min | Ready to run |
| Create table & populate | 1 hour | Ready to run |
| Verify & test | 30 min | Ready to run |
| **Total** | **2 hours** | **Can start now** |

---

**Next:** Run `002_extract_simple_metadata.py` để bắt đầu?
