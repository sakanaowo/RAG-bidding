# KẾ HOẠCH MIGRATION CỤ THỂ - KHÔNG CẦN REPROCESS CHUNKS

**Ngày:** 2025-11-19  
**Phân tích:** Chunks hiện tại ĐÃ CÓ đủ thông tin, chỉ cần UPDATE metadata

---

## 📊 PHÂN TÍCH HIỆN TRẠNG

### ✅ Chunk Files (data/processed/chunks/)
```json
{
  "document_id": "law_untitled",  // ❌ Generic
  "chunk_id": "law_untitled_khoan_0000",
  "document_type": "law",         // ✅ OK
  "content": "...",               // ✅ OK
  "hierarchy": [...],             // ✅ OK
  "section_title": "...",         // ✅ OK
  "chunk_index": 0,               // ✅ OK
  "total_chunks": 255             // ✅ OK
}
```

**Kết luận:** Chunks có đầy đủ content, hierarchy, metadata → **KHÔNG CẦN reprocess**

### ❌ Database (langchain_pg_embedding)
```
5 collections (merged):
- LAW-Law/2025#cd5116 (1154 chunks) - Gộp 4 law files
- ND-Decree/2025#95b863 (595 chunks)
- TT-Circular/2025#3be8b6 (123 chunks)
- FORM-Bidding/2025#bee720 (2831 chunks) - Gộp 46 files
- DOC-Document/2025#787999 (5 chunks)
```

**Vấn đề:**
- Generic document_ids (5 collections thay vì 70 documents)
- Không có source_file tracking
- Không thể toggle từng document riêng lẻ

---

## 🎯 KẾ HOẠCH: UPDATE METADATA ONLY (2 ngày)

### ✅ APPROACH: Không reprocess, chỉ update metadata

**Lý do:**
1. Content đã đúng, hierarchy đã tốt
2. Embeddings đã có trong database
3. Chỉ cần map chunks → documents mới
4. Tiết kiệm 80% thời gian

---

## 📅 CHI TIẾT KẾ HOẠCH

### **NGÀY 1: Setup Documents Table + Mapping (4 giờ)**

#### Sáng (2 giờ)

**1. Create documents table** ⏱️ 30 phút
```bash
# Run migration scripts
python scripts/migration/002_extract_simple_metadata.py
python scripts/migration/003_populate_documents_table.py
```

**Expected:**
- ✅ Documents table với 70 records
- ✅ Mapping: 7 categories
- ✅ Document_ids generated

**2. Build mapping: chunk files → document_id** ⏱️ 1.5 giờ

```python
# scripts/migration/004_build_chunk_to_document_mapping.py

def build_mapping():
    """
    Map existing chunks to new document_ids
    Using metadata files as bridge
    """
    
    mapping = {}  # {old_chunk_path: new_document_id}
    
    # Load documents table
    documents = get_all_documents()
    
    for doc in documents:
        # Find corresponding metadata file
        metadata_file = find_metadata_file(doc.source_file)
        
        if metadata_file:
            # Get chunk file path from metadata
            chunk_file = metadata_file["output_file"]
            
            # Map chunk_file → new document_id
            mapping[chunk_file] = doc.document_id
    
    return mapping

# Example output:
# {
#   "data/processed/chunks/Luat_so_90_2025.jsonl": "LUA-90-2025-QH15",
#   "data/processed/chunks/01A_Mau_HSYC.jsonl": "FORM-HSYC-XAYLAP-01A",
#   ...
# }
```

#### Chiều (2 giờ)

**3. Update database chunks with new document_ids** ⏱️ 2 giờ

```python
# scripts/migration/005_update_chunk_document_ids.py

async def update_chunk_document_ids():
    """
    Update existing chunks in database với document_id mới
    KHÔNG reprocess, chỉ update metadata
    """
    
    # Load mapping
    mapping = load_chunk_to_document_mapping()
    
    # Load metadata files
    metadata_files = load_all_metadata()
    
    for meta_file in metadata_files:
        chunk_file = meta_file["output_file"]
        new_doc_id = mapping.get(chunk_file)
        
        if not new_doc_id:
            continue
        
        # Read chunks from file
        chunks = read_chunks_from_file(chunk_file)
        
        for chunk in chunks:
            old_chunk_id = chunk["chunk_id"]
            
            # Generate new chunk_id
            # "law_untitled_khoan_0000" → "LUA-90-2025-QH15_khoan_0000"
            chunk_suffix = old_chunk_id.split("_", 2)[-1]  # "khoan_0000"
            new_chunk_id = f"{new_doc_id}_{chunk_suffix}"
            
            # Update database
            await db.execute(text("""
                UPDATE langchain_pg_embedding
                SET cmetadata = jsonb_set(
                    jsonb_set(
                        jsonb_set(
                            cmetadata,
                            '{document_id}',
                            to_jsonb(:new_doc_id::text)
                        ),
                        '{chunk_id}',
                        to_jsonb(:new_chunk_id::text)
                    ),
                    '{source_file}',
                    to_jsonb(:source_file::text)
                )
                WHERE cmetadata->>'chunk_id' = :old_chunk_id
            """), {
                "new_doc_id": new_doc_id,
                "new_chunk_id": new_chunk_id,
                "source_file": meta_file["source_file"],
                "old_chunk_id": old_chunk_id
            })
        
        print(f"✅ Updated {len(chunks)} chunks for {new_doc_id}")
```

**Key Points:**
- ✅ Giữ nguyên embeddings (không recompute)
- ✅ Giữ nguyên content, hierarchy
- ✅ Chỉ update: document_id, chunk_id, source_file
- ✅ Fast: ~10-15 phút cho 4700 chunks

---

### **NGÀY 2: Verification + API Update (4 giờ)**

#### Sáng (2 giờ)

**4. Verify migration** ⏱️ 1 giờ

```sql
-- Check document count
SELECT COUNT(DISTINCT cmetadata->>'document_id') 
FROM langchain_pg_embedding;
-- Expected: 70 (not 5!)

-- Check sample document_ids
SELECT DISTINCT cmetadata->>'document_id', COUNT(*) 
FROM langchain_pg_embedding 
GROUP BY cmetadata->>'document_id'
ORDER BY cmetadata->>'document_id'
LIMIT 10;
-- Expected: LUA-90-2025-QH15, LUA-57-2024-QH15, etc.

-- Verify source_file populated
SELECT COUNT(*) 
FROM langchain_pg_embedding 
WHERE cmetadata->>'source_file' IS NOT NULL;
-- Expected: 4708 (100%)

-- Check chunk_id format
SELECT cmetadata->>'chunk_id' 
FROM langchain_pg_embedding 
LIMIT 5;
-- Expected: LUA-90-2025-QH15_khoan_0000, etc.
```

**5. Update documents.total_chunks** ⏱️ 30 phút

```python
# Update chunk counts in documents table
async def update_chunk_counts():
    for doc in documents:
        count = await db.execute(text("""
            SELECT COUNT(*) 
            FROM langchain_pg_embedding
            WHERE cmetadata->>'document_id' = :doc_id
        """), {"doc_id": doc.document_id})
        
        await db.execute(text("""
            UPDATE documents
            SET total_chunks = :count
            WHERE document_id = :doc_id
        """), {"count": count, "doc_id": doc.document_id})
```

**6. Test retrieval** ⏱️ 30 phút

```python
# Test that retrieval still works
results = retriever.retrieve(
    query="luật đấu thầu 2025",
    filters={"document_id": "LUA-90-2025-QH15"}
)

# Should return chunks from Luật 90/2025 only
```

#### Chiều (2 giờ)

**7. Update API endpoints** ⏱️ 1 giờ

```python
# src/api/routers/documents_management.py

@router.get("/documents/catalog")
async def get_catalog(
    category: Optional[str] = None,
    status: str = "active",
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get 70 documents (not 5!)"""
    query = select(Document).where(Document.status == status)
    
    if category:
        query = query.where(Document.category == category)
    
    result = await db.execute(query)
    docs = result.scalars().all()
    
    return {
        "total": len(docs),
        "documents": [
            {
                "document_id": doc.document_id,
                "document_name": doc.document_name,
                "category": doc.category,
                "total_chunks": doc.total_chunks,
                "status": doc.status
            }
            for doc in docs
        ]
    }

@router.patch("/documents/{document_id}/status")
async def toggle_status(
    document_id: str,
    status: str,
    db: AsyncSession = Depends(get_db)
):
    """Toggle specific document"""
    
    # Update documents table
    await db.execute(
        update(Document)
        .where(Document.document_id == document_id)
        .values(status=status)
    )
    
    # Update chunks (for filtering during retrieval)
    await db.execute(text("""
        UPDATE langchain_pg_embedding
        SET cmetadata = jsonb_set(
            cmetadata,
            '{status}',
            to_jsonb(:status::text)
        )
        WHERE cmetadata->>'document_id' = :doc_id
    """), {"status": status, "doc_id": document_id})
    
    await db.commit()
    return {"message": f"Updated {document_id} to {status}"}
```

**8. Update retriever to respect status** ⏱️ 30 phút

```python
# src/retrieval/retrievers/base.py

def retrieve(self, query: str, filters: dict = None):
    # Add status filter
    if filters is None:
        filters = {}
    
    if "status" not in filters:
        filters["status"] = "active"
    
    # Retrieval với filter
    results = self.vector_store.similarity_search(
        query,
        filter={"status": filters["status"]}
    )
    
    return results
```

**9. Integration testing** ⏱️ 30 phút

```bash
# Test catalog
curl http://localhost:8000/api/documents/catalog
# Expected: 70 documents

# Test toggle
curl -X PATCH http://localhost:8000/api/documents/LUA-90-2025-QH15/status \
  -d '{"status": "inactive"}'

# Test retrieval excludes inactive
curl -X POST http://localhost:8000/api/ask \
  -d '{"query": "luật đấu thầu 2025"}'
# Should NOT return chunks from LUA-90-2025-QH15
```

---

## 📊 SO SÁNH: REPROCESS vs UPDATE ONLY

| Aspect | Reprocess Approach | Update Metadata Only |
|--------|-------------------|---------------------|
| **Thời gian** | 3-4 ngày | **2 ngày** ✅ |
| **Embeddings** | Recompute (~2 giờ) | Giữ nguyên ✅ |
| **Content** | Reprocess files | Giữ nguyên ✅ |
| **Risk** | High (có thể break) | Low (chỉ update IDs) |
| **Testing** | Toàn bộ pipeline | Chỉ API endpoints |
| **Rollback** | Khó (cần backup) | Dễ (chỉ revert IDs) |

**Recommendation:** **UPDATE METADATA ONLY** ✅

---

## ✅ KẾT QUẢ MONG ĐỢI

### Trước Migration
```
Database: 5 "documents" (collections)
├── LAW-Law/2025#cd5116 (1154 chunks - 4 files gộp)
├── FORM-Bidding/2025#bee720 (2831 chunks - 46 files gộp)
└── ... (3 more collections)

Catalog API: Returns 5 items
Toggle: KHÔNG THỂ toggle riêng lẻ
source_file: NULL cho tất cả chunks
```

### Sau Migration (2 ngày)
```
Database: 70 real documents
├── LUA-90-2025-QH15 (255 chunks)
├── LUA-57-2024-QH15 (280 chunks)
├── FORM-HSYC-XAYLAP-01A (42 chunks)
└── ... (67 more documents)

Catalog API: Returns 70 documents ✅
Toggle: Toggle bất kỳ document nào ✅
source_file: Populated cho tất cả chunks ✅
```

---

## 🎯 EXECUTION CHECKLIST

### Day 1 Morning
- [ ] Run `002_extract_simple_metadata.py`
- [ ] Run `003_populate_documents_table.py`
- [ ] Verify: 70 documents in table

### Day 1 Afternoon
- [ ] Create `004_build_chunk_to_document_mapping.py`
- [ ] Run mapping script
- [ ] Verify: mapping.json with 70 entries

### Day 1 Evening
- [ ] Create `005_update_chunk_document_ids.py`
- [ ] Run update script
- [ ] Monitor progress (4708 chunks)

### Day 2 Morning
- [ ] Verify document_ids in database (should be 70)
- [ ] Verify source_file populated
- [ ] Update documents.total_chunks
- [ ] Test retrieval with new IDs

### Day 2 Afternoon
- [ ] Update catalog API endpoint
- [ ] Update toggle API endpoint
- [ ] Update retriever filter logic
- [ ] Integration testing
- [ ] Documentation

---

## 🚀 BẮT ĐẦU NGAY

```bash
# Step 1: Extract metadata
cd /home/sakana/Code/RAG-bidding
python scripts/migration/002_extract_simple_metadata.py

# Expected output:
# ✅ Found 70 documents
# 📁 Hồ sơ mời thầu: 46 documents
# 📁 Mẫu báo cáo: 10 documents
# ...
# 💾 Saved to: data/processed/documents_metadata.json
```

**Xác nhận để tiếp tục?**
