# Document Structure Redesign - Hệ thống Document Management đúng chuẩn

**Ngày tạo:** 2025-11-14  
**Vấn đề:** Database hiện tại gộp nhiều files thành 1 document_id, không thể quản lý từng văn bản riêng lẻ  
**Mục tiêu:** Thiết kế lại cấu trúc document từ đầu để hỗ trợ đầy đủ document management

---

## 🔴 Vấn đề hiện tại (Root Cause Analysis)

### Database Structure (Hiện tại - SAI)

```
Database: 5 "documents" (thực ra là 5 COLLECTIONS)
├── FORM-Bidding/2025#bee720 (2831 chunks)
│   ├── 01A. Mẫu HSYC Xây lắp.docx
│   ├── 01B. Mẫu HSYC hàng hóa.docx  
│   ├── 01C. Mẫu HSYC Phi tư vấn.docx
│   ├── ... (70+ files gộp chung!)
│   └── NO WAY to distinguish individual files
│
├── LAW-Law/2025#cd5116 (1154 chunks)
│   ├── Luật đấu thầu 2023.docx
│   ├── Luật số 57 2024 QH15.docx
│   ├── Luật số 90 2025-qh15.docx
│   ├── HỢP NHẤT 126 2025 về Luật đấu thầu.docx
│   └── NO source_file tracking!
│
└── ... (3 more collections)
```

**Chunk metadata:**
```json
{
  "document_id": "law_untitled",  // ❌ Generic ID
  "chunk_id": "law_untitled_dieu_0001",
  "source_file": null,  // ❌ NULL!
  "document_name": null,  // ❌ NULL!
  // Không có cách nào biết chunk này thuộc file nào
}
```

### Hậu quả

1. ❌ **Không thể toggle status** của 1 văn bản cụ thể (VD: "Luật số 90/2025")
2. ❌ **Không thể track version** (Luật 2023 vs 2024 vs 2025)
3. ❌ **Không thể show document list** riêng lẻ trong UI
4. ❌ **Catalog API trả về 5 items** thay vì 80+ documents thực tế
5. ❌ **Không biết chunk nào thuộc file nào** khi debug/audit

---

## ✅ Thiết kế đúng (Proper Document Management)

### 1. Document Hierarchy (3 levels)

```
Level 1: CATEGORY (Logical grouping)
├── Luật chính
├── Nghị định  
├── Thông tư
├── Quyết định
└── Hồ sơ mời thầu

Level 2: DOCUMENT (Individual file)
├── Luật đấu thầu 2023
├── Luật số 57/2024
├── Luật số 90/2025
├── HỢP NHẤT 126/2025
└── ... (80+ documents)

Level 3: CHUNK (Text segments)
├── Chunk 1: Điều 1. Phạm vi...
├── Chunk 2: Điều 2. Đối tượng...
└── ... (4708 chunks total)
```

### 2. New Database Schema

**Thêm bảng mới: `documents` (Master table)**

```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id VARCHAR(255) UNIQUE NOT NULL,  -- "LAW-2025-luat90"
    
    -- File information
    source_file TEXT NOT NULL,  -- "data/raw/Luat chinh/Luat so 90 2025-qh15.docx"
    file_name TEXT NOT NULL,    -- "Luat so 90 2025-qh15.docx"
    file_hash VARCHAR(64),      -- SHA256 for change detection
    file_size_bytes BIGINT,
    
    -- Document metadata
    document_name TEXT NOT NULL,     -- "Luật số 90/2025/QH15"
    document_type VARCHAR(50),       -- "law"
    category VARCHAR(100),           -- "Luật chính"
    
    -- Legal metadata
    document_number VARCHAR(100),    -- "90/2025/QH15"
    issued_by TEXT,                  -- "Quốc hội"
    published_date DATE,
    effective_date DATE,
    expiry_date DATE,
    
    -- Processing metadata
    total_chunks INTEGER DEFAULT 0,
    processing_status VARCHAR(50) DEFAULT 'pending',
    processed_at TIMESTAMP,
    
    -- Document status (for toggle functionality)
    status VARCHAR(50) DEFAULT 'active',  -- active/inactive/archived
    visibility VARCHAR(50) DEFAULT 'public',  -- public/internal/restricted
    
    -- Versioning
    version VARCHAR(50),             -- "1.0", "2.0"
    replaces_document_id VARCHAR(255),  -- Link to old version
    replaced_by_document_id VARCHAR(255),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Indexes
    CONSTRAINT fk_replaces FOREIGN KEY (replaces_document_id) 
        REFERENCES documents(document_id),
    CONSTRAINT fk_replaced_by FOREIGN KEY (replaced_by_document_id) 
        REFERENCES documents(document_id)
);

CREATE INDEX idx_documents_type ON documents(document_type);
CREATE INDEX idx_documents_category ON documents(category);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_source_file ON documents(source_file);
```

**Update chunk metadata trong `langchain_pg_embedding`:**

```json
{
  "document_id": "LAW-2025-luat90",  // ✅ Unique per file
  "chunk_id": "LAW-2025-luat90_dieu_0001",
  
  // Link to master document
  "source_file": "data/raw/Luat chinh/Luat so 90 2025-qh15.docx",
  "document_name": "Luật số 90/2025/QH15",
  
  // Existing fields
  "document_type": "law",
  "hierarchy": ["Điều 1. Phạm vi điều chỉnh"],
  "section_title": "Phạm vi điều chỉnh",
  
  // Processing metadata
  "chunk_index": 0,
  "total_chunks": 274,
  "processed_at": "2025-11-14T10:00:00"
}
```

### 3. Document ID Convention (NEW)

**Format:** `{TYPE}-{YEAR}-{IDENTIFIER}`

Examples:
```
LAW-2025-luat90          // Luật số 90/2025
LAW-2024-luat57          // Luật số 57/2024
ND-2024-43CP             // Nghị định 43/2024/NĐ-CP
TT-2023-05BKH            // Thông tư 05/2023/TT-BKH
FORM-2025-hsyc-xaylap    // Mẫu HSYC Xây lắp
```

**Quy tắc:**
- Ngắn gọn, dễ đọc
- Unique per document
- Sortable by year
- Human-readable

### 4. Migration Strategy

#### Phase 1: Create Master Documents Table ⏱️ 2 giờ

```python
# scripts/migration/create_documents_table.py
async def migrate_phase1():
    """Tạo bảng documents và populate từ raw files"""
    
    # 1. Create documents table
    await create_documents_table()
    
    # 2. Scan raw files và extract metadata
    documents = []
    for category_folder in ["Luat chinh", "Nghi dinh", "Thong tu", ...]:
        for file_path in glob(f"data/raw/{category_folder}/*.docx"):
            doc_metadata = extract_document_metadata(file_path)
            documents.append(doc_metadata)
    
    # 3. Insert into documents table
    await bulk_insert_documents(documents)
    
    print(f"✅ Created {len(documents)} document records")
```

**Expected output:**
```
Documents table: 80+ records
├── 4 law documents
├── 10+ decree documents  
├── 5+ circular documents
├── 50+ bidding forms
└── ...
```

#### Phase 2: Reprocess Files with New Document IDs ⏱️ 4 giờ

```python
# scripts/migration/reprocess_with_document_ids.py
async def migrate_phase2():
    """Reprocess tất cả files với document_id mới"""
    
    # 1. Load document registry
    documents = await load_documents_from_db()
    
    # 2. Reprocess mỗi file
    for doc in documents:
        # Generate new document_id
        new_doc_id = generate_document_id(doc)
        
        # Process file với metadata đầy đủ
        chunks = await process_document(
            file_path=doc.source_file,
            document_id=new_doc_id,
            document_metadata={
                "document_name": doc.document_name,
                "source_file": doc.source_file,
                "category": doc.category,
                "published_date": doc.published_date,
                ...
            }
        )
        
        # Upsert to vector DB
        await upsert_chunks(chunks)
        
        # Update documents table
        await update_document_stats(new_doc_id, total_chunks=len(chunks))
    
    print(f"✅ Reprocessed {len(documents)} documents")
```

#### Phase 3: Update API Endpoints ⏱️ 1 giờ

```python
# src/api/routers/documents_management.py

@router.get("/documents/catalog")
async def get_document_catalog(
    category: Optional[str] = None,
    document_type: Optional[str] = None,
    status: str = "active",
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get document catalog from master documents table"""
    
    query = select(Document).where(Document.status == status)
    
    if category:
        query = query.where(Document.category == category)
    if document_type:
        query = query.where(Document.document_type == document_type)
    
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    documents = result.scalars().all()
    
    return {
        "total": len(documents),
        "documents": [doc.to_dict() for doc in documents]
    }

@router.patch("/documents/{document_id}/status")
async def toggle_document_status(
    document_id: str,
    status: str,  # active/inactive/archived
    db: AsyncSession = Depends(get_db)
):
    """Toggle status của 1 document cụ thể"""
    
    # Update master table
    await db.execute(
        update(Document)
        .where(Document.document_id == document_id)
        .values(status=status, updated_at=datetime.now())
    )
    
    # Update all chunks
    await db.execute(
        text("""
            UPDATE langchain_pg_embedding
            SET cmetadata = jsonb_set(cmetadata, '{status}', :status)
            WHERE cmetadata->>'document_id' = :doc_id
        """),
        {"status": f'"{status}"', "doc_id": document_id}
    )
    
    await db.commit()
    
    return {"message": f"Document {document_id} status updated to {status}"}
```

---

## 📊 Impact Analysis

### Before (Hiện tại)

```
Catalog API: 5 "documents" (actually collections)
Toggle: KHÔNG THỂ toggle riêng lẻ
Search: Trả về chunks không biết thuộc document nào
Management: KHÔNG CÓ document-level operations
```

### After (Sau redesign)

```
Catalog API: 80+ real documents với metadata đầy đủ
Toggle: Toggle bất kỳ document nào theo document_id
Search: Mỗi chunk có link rõ ràng đến source document
Management: CRUD operations cho documents

Filter by:
- Category: "Luật chính", "Nghị định", "Thông tư"
- Type: law, decree, circular, bidding
- Status: active, inactive, archived
- Date range: published_date, effective_date
- Version: List all versions of a document
```

### API Examples

```bash
# 1. List all documents
GET /api/documents/catalog?limit=100

# 2. Filter by category
GET /api/documents/catalog?category=Luật chính

# 3. Get specific document
GET /api/documents/LAW-2025-luat90

# 4. Toggle document status
PATCH /api/documents/LAW-2025-luat90/status
Body: {"status": "inactive"}

# 5. Search within document
GET /api/documents/LAW-2025-luat90/search?q=đấu thầu

# 6. Get document versions
GET /api/documents/LAW-2025-luat90/versions
→ Returns: [LAW-2023-luat43, LAW-2024-luat57, LAW-2025-luat90]

# 7. Compare documents
GET /api/documents/compare?doc1=LAW-2024-luat57&doc2=LAW-2025-luat90
```

---

## ⏱️ Implementation Timeline

### Week 1: Database Redesign (12 giờ)
- [ ] Design documents table schema
- [ ] Write migration scripts
- [ ] Create documents table
- [ ] Extract metadata from raw files
- [ ] Populate documents table
- [ ] Add indexes and constraints

### Week 2: Reprocessing (20 giờ)
- [ ] Update preprocessing pipeline
- [ ] Generate new document_ids
- [ ] Reprocess all 80+ files
- [ ] Verify chunk counts
- [ ] Update embeddings if needed
- [ ] Data validation

### Week 3: API Development (16 giờ)
- [ ] Create Document model (SQLAlchemy)
- [ ] Implement catalog endpoints
- [ ] Implement toggle/CRUD endpoints
- [ ] Add filtering and pagination
- [ ] Write API tests
- [ ] Update API documentation

### Week 4: Testing & Deployment (8 giờ)
- [ ] Integration testing
- [ ] Performance testing
- [ ] Data migration to production
- [ ] Update frontend (if any)
- [ ] Documentation
- [ ] Deployment

**Total:** ~56 giờ (7 ngày làm việc)

---

## 🎯 Decision Point

**Câu hỏi:** Có nên làm redesign toàn bộ không?

### ✅ Arguments FOR (Khuyến nghị)

1. **Scalability:** Hiện tại có 80+ documents, tương lai có thể lên 500+
2. **Management:** KHÔNG THỂ quản lý documents với structure hiện tại
3. **User Experience:** Catalog API trả về 5 items thay vì 80+ là vô nghĩa
4. **Data Integrity:** source_file=NULL làm mất traceability
5. **Long-term:** Sớm muộn cũng phải làm, làm sớm ít technical debt hơn

### ❌ Arguments AGAINST

1. **Time:** 7 ngày làm việc
2. **Risk:** Reprocess toàn bộ data (4708 chunks)
3. **Compatibility:** Phải update mọi code dùng document_id cũ

### 🤔 Compromise Option (Hybrid)

Giữ cấu trúc hiện tại NHƯNG:
- Thêm `source_file` vào chunk metadata (Phase 2 của plan cũ)
- Toggle theo `source_file` thay vì document_id
- KHÔNG tạo documents table
- KHÔNG change document_id format

**Trade-off:**
- ✅ Faster (2 giờ thay vì 56 giờ)
- ❌ Vẫn có 5 "pseudo-documents" trong catalog
- ❌ Không có document-level metadata table
- ❌ Phải query chunks để biết có bao nhiêu documents

---

## 💡 Recommendation

**TÔI KHUYẾN NGHỊ: Full Redesign (Option 1)**

**Lý do:**
1. Bạn đã nói "cần hệ thống thực sự hoạt động chứ không phải chắp vá"
2. Document management là core feature, không phải nice-to-have
3. 80+ documents cần proper structure, không thể fake bằng 5 collections
4. Source_file tracking alone KHÔNG ĐỦ cho full document management
5. Technical debt sẽ tích lũy nhanh nếu không fix ngay

**Nhưng có thể chia nhỏ:**

### Minimal Viable Product (MVP) - 2 ngày

1. **Day 1:** Tạo documents table + populate 80+ records
2. **Day 2:** Update catalog API dùng documents table

→ Có ngay document catalog đúng (80+ items) KHÔNG CẦN reprocess chunks

### Full Implementation - 7 ngày

3-5: Reprocess chunks với document_id mới
6-7: Toggle functionality + testing

---

## ❓ Next Steps

**Quyết định cần làm:**

1. Full redesign (56h) hay Compromise (2h)?
2. Có reprocess chunks không hay chỉ add documents table?
3. Timeline: Làm ngay hay để sau?

**Nếu GO AHEAD với full redesign, tôi sẽ:**

1. Tạo migration scripts
2. Design document_id convention chi tiết
3. Update preprocessing pipeline
4. Implement documents table
5. Test với 1-2 files trước
6. Roll out toàn bộ

**Bạn muốn đi theo hướng nào?**
