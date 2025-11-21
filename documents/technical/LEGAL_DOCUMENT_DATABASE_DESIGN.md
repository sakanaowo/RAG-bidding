# Legal Document Database Design - Best Practices

**Ngày:** 2025-11-19  
**Dựa trên:** LexisNexis, Westlaw, EUR-Lex, LawNet (Singapore), Thư viện pháp luật VN

---

## 🌍 Các hệ thống tham khảo

### 1. **LexisNexis** (Global Legal Research)
```
Structure:
├── Jurisdiction (US, UK, EU, Asia-Pacific)
│   ├── Document Type (Statute, Case Law, Regulation)
│   │   ├── Year/Session
│   │   │   └── Individual Documents
│   │   │       ├── Sections/Articles
│   │   │       └── Amendments/Versions
```

**Key Features:**
- **Hierarchical taxonomy:** Country → Type → Year → Document
- **Version tracking:** Original + All amendments
- **Citation system:** Unique identifier per document
- **Relationship mapping:** "Amends", "Repeals", "Cited by"

### 2. **EUR-Lex** (EU Official Journal)
```
Document Classification:
├── Primary Law (Treaties, Regulations)
├── Secondary Law (Directives, Decisions)
├── Case Law (Court judgments)
└── International Agreements

Metadata Schema:
- CELEX Number (unique ID)
- Document Type
- Author (Institution)
- Date of publication/effect
- Subject matter codes
- Legal status (In force, Repealed, Amended)
```

### 3. **Thư viện Pháp luật Việt Nam**
```
Hierarchy:
├── Loại văn bản (Luật, Nghị định, Thông tư, Quyết định)
│   ├── Cơ quan ban hành (Quốc hội, Chính phủ, Bộ)
│   │   ├── Lĩnh vực (Đấu thầu, Xây dựng, Y tế...)
│   │   │   └── Văn bản cụ thể
│   │   │       ├── Số/Ký hiệu
│   │   │       ├── Ngày ban hành
│   │   │       ├── Hiệu lực
│   │   │       └── Trạng thái (Còn/Hết hiệu lực)
```

### 4. **Westlaw** (Thomson Reuters)
```
Key Concepts:
- KeyCite: Citation analysis & validation
- Topic & Key Numbers: Hierarchical classification
- Headnotes: Summary of legal principles
- Related Documents: Cross-references
```

---

## 🎯 ÁP DỤNG CHO HỆ THỐNG RAG-BIDDING

### 7 Categories hiện tại

```
data/raw/
├── Luat chinh/          (4 files)   - Primary legislation
├── Nghi dinh/           (1 file)    - Government decrees
├── Thong tu/            (2 files)   - Circulars
├── Quyet dinh/          (1 file)    - Decisions
├── Ho so moi thau/      (46 files)  - Bidding documents
├── Mau bao cao/         (10 files)  - Report templates
└── Cau hoi thi/         (6 files)   - Exam questions
```

---

## 📊 DATABASE SCHEMA - BEST PRACTICES

### 1. **Documents Table (Master Registry)**

```sql
CREATE TABLE documents (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Unique Identifier (Following Vietnamese legal citation)
    document_id VARCHAR(255) UNIQUE NOT NULL,
    -- Examples:
    -- "LUA-90-2025-QH15"        (Luật 90/2025/QH15)
    -- "ND-43-2024-CP"           (Nghị định 43/2024/NĐ-CP)
    -- "TT-05-2023-BKH"          (Thông tư 05/2023/TT-BKH)
    -- "FORM-HSYC-XAYLAP-2025"   (Mẫu HSYC Xây lắp)
    
    -- Document Classification (7 categories)
    category VARCHAR(100) NOT NULL,
    -- "Luật chính", "Nghị định", "Thông tư", "Quyết định",
    -- "Hồ sơ mời thầu", "Mẫu báo cáo", "Câu hỏi thi"
    
    document_type VARCHAR(50) NOT NULL,
    -- "law", "decree", "circular", "decision",
    -- "bidding_form", "report_template", "exam_question"
    
    -- Document Identity
    document_number VARCHAR(100),
    -- "90/2025/QH15", "43/2024/NĐ-CP", "05/2023/TT-BKH"
    
    document_name TEXT NOT NULL,
    -- "Luật số 90/2025/QH15 về sửa đổi, bổ sung một số điều của Luật Đấu thầu"
    
    short_name VARCHAR(255),
    -- "Luật Đấu thầu 2025" (for display)
    
    -- Issuing Authority (Vietnamese context)
    issuing_authority VARCHAR(100),
    -- "Quốc hội", "Chính phủ", "Bộ Kế hoạch và Đầu tư", etc.
    
    issuing_authority_code VARCHAR(50),
    -- "QH" (Quốc hội), "CP" (Chính phủ), "BKH" (Bộ KH&ĐT)
    
    -- Legal Dates
    issued_date DATE,           -- Ngày ban hành
    signed_date DATE,           -- Ngày ký
    published_date DATE,        -- Ngày công báo
    effective_date DATE,        -- Ngày có hiệu lực
    expiry_date DATE,           -- Ngày hết hiệu lực (nếu có)
    
    -- Legal Status
    legal_status VARCHAR(50) DEFAULT 'in_force',
    -- "in_force"      (Còn hiệu lực)
    -- "repealed"      (Đã bị bãi bỏ)
    -- "amended"       (Đã được sửa đổi)
    -- "superseded"    (Đã bị thay thế)
    -- "draft"         (Dự thảo)
    
    -- Subject/Domain Classification
    subject_area VARCHAR(100),
    -- "Đấu thầu", "Xây dựng", "Y tế", etc.
    
    keywords TEXT[],
    -- {"đấu thầu", "mua sắm công", "hồ sơ dự thầu"}
    
    -- Document Relationships (Legal hierarchy)
    parent_document_id VARCHAR(255),
    -- Nghị định → References parent Luật
    -- Thông tư → References parent Nghị định
    
    replaces_document_id VARCHAR(255),
    -- Links to document being replaced
    
    replaced_by_document_id VARCHAR(255),
    -- Links to newer version
    
    amends_document_ids TEXT[],
    -- Array of document_ids being amended
    
    repeals_document_ids TEXT[],
    -- Array of document_ids being repealed
    
    -- File Information
    source_file TEXT NOT NULL,
    -- "data/raw/Luat chinh/Luat so 90 2025-qh15.docx"
    
    file_name TEXT NOT NULL,
    -- "Luat so 90 2025-qh15.docx"
    
    file_type VARCHAR(20),
    -- "docx", "pdf", "doc"
    
    file_size_bytes BIGINT,
    file_hash VARCHAR(64),
    -- SHA256 for version control
    
    -- Processing Metadata
    total_chunks INTEGER DEFAULT 0,
    total_pages INTEGER,
    total_characters BIGINT,
    
    processing_status VARCHAR(50) DEFAULT 'pending',
    -- "pending", "processing", "completed", "failed"
    
    processed_at TIMESTAMP,
    processing_duration_seconds INTEGER,
    
    -- Access Control
    status VARCHAR(50) DEFAULT 'active',
    -- "active", "inactive", "archived", "deleted"
    
    visibility VARCHAR(50) DEFAULT 'public',
    -- "public", "internal", "restricted", "confidential"
    
    access_level INTEGER DEFAULT 0,
    -- 0: Public, 1: Registered users, 2: Premium, 3: Admin only
    
    -- Versioning
    version VARCHAR(50) DEFAULT '1.0',
    version_notes TEXT,
    is_latest_version BOOLEAN DEFAULT true,
    
    -- Audit Trail
    created_by VARCHAR(255),
    updated_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Search & Metadata
    metadata JSONB,
    -- Flexible field for additional data:
    -- {
    --   "signer": "Chủ tịch Quốc hội",
    --   "session": "Kỳ họp thứ 10",
    --   "gazette_number": "Số 123",
    --   "related_laws": ["Luật Đấu thầu 2013", "Luật Xây dựng 2014"]
    -- }
    
    -- Full-text search vector (PostgreSQL)
    search_vector tsvector,
    
    -- Foreign Key Constraints
    CONSTRAINT fk_parent FOREIGN KEY (parent_document_id) 
        REFERENCES documents(document_id) ON DELETE SET NULL,
    CONSTRAINT fk_replaces FOREIGN KEY (replaces_document_id) 
        REFERENCES documents(document_id) ON DELETE SET NULL,
    CONSTRAINT fk_replaced_by FOREIGN KEY (replaced_by_document_id) 
        REFERENCES documents(document_id) ON DELETE SET NULL
);

-- Indexes for Performance
CREATE INDEX idx_documents_category ON documents(category);
CREATE INDEX idx_documents_type ON documents(document_type);
CREATE INDEX idx_documents_status ON documents(status, legal_status);
CREATE INDEX idx_documents_dates ON documents(issued_date, effective_date);
CREATE INDEX idx_documents_authority ON documents(issuing_authority_code);
CREATE INDEX idx_documents_subject ON documents(subject_area);
CREATE INDEX idx_documents_search ON documents USING GIN(search_vector);
CREATE INDEX idx_documents_keywords ON documents USING GIN(keywords);
CREATE INDEX idx_documents_metadata ON documents USING GIN(metadata);
```

### 2. **Document Sections Table** (Optional - for structured navigation)

```sql
CREATE TABLE document_sections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id VARCHAR(255) NOT NULL,
    
    -- Section Hierarchy
    section_type VARCHAR(50),
    -- "chapter", "section", "article", "clause", "paragraph"
    -- "chuong", "muc", "dieu", "khoan", "diem"
    
    section_number VARCHAR(50),
    -- "Điều 1", "Khoản 2", "Điểm a"
    
    section_title TEXT,
    -- "Phạm vi điều chỉnh"
    
    section_content TEXT,
    
    -- Hierarchy
    parent_section_id UUID,
    hierarchy_level INTEGER,
    display_order INTEGER,
    
    -- Processing
    chunk_start_index INTEGER,
    chunk_end_index INTEGER,
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE,
    FOREIGN KEY (parent_section_id) REFERENCES document_sections(id) ON DELETE CASCADE
);

CREATE INDEX idx_sections_document ON document_sections(document_id);
CREATE INDEX idx_sections_hierarchy ON document_sections(parent_section_id, display_order);
```

### 3. **Document Relationships Table**

```sql
CREATE TABLE document_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    source_document_id VARCHAR(255) NOT NULL,
    target_document_id VARCHAR(255) NOT NULL,
    
    relationship_type VARCHAR(50) NOT NULL,
    -- "amends", "repeals", "supersedes", "references",
    -- "implements", "cited_by", "related_to"
    
    relationship_details TEXT,
    -- "Điều 5 của NĐ 43/2024 sửa đổi Điều 10 của Luật 90/2025"
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    FOREIGN KEY (source_document_id) REFERENCES documents(document_id) ON DELETE CASCADE,
    FOREIGN KEY (target_document_id) REFERENCES documents(document_id) ON DELETE CASCADE,
    
    UNIQUE(source_document_id, target_document_id, relationship_type)
);

CREATE INDEX idx_relationships_source ON document_relationships(source_document_id);
CREATE INDEX idx_relationships_target ON document_relationships(target_document_id);
CREATE INDEX idx_relationships_type ON document_relationships(relationship_type);
```

### 4. **Document Versions Table** (Track amendments)

```sql
CREATE TABLE document_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    document_id VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    
    version_date DATE NOT NULL,
    version_type VARCHAR(50),
    -- "original", "amendment", "consolidation"
    
    amended_by_document_id VARCHAR(255),
    -- Document that introduced this version
    
    changes_summary TEXT,
    -- "Sửa đổi Điều 5, bổ sung Điều 15, bãi bỏ Điều 20"
    
    source_file TEXT,
    -- Path to this version's file
    
    is_current_version BOOLEAN DEFAULT false,
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE,
    FOREIGN KEY (amended_by_document_id) REFERENCES documents(document_id) ON DELETE SET NULL
);

CREATE INDEX idx_versions_document ON document_versions(document_id, version_date DESC);
```

---

## 🏗️ CATEGORY MAPPING - 7 LOẠI VĂN BẢN

### 1. **Luật chính** (4 files)
```python
{
    "category": "Luật chính",
    "document_type": "law",
    "issuing_authority": "Quốc hội",
    "issuing_authority_code": "QH",
    "subject_area": "Đấu thầu",
    
    # Document ID format: LUA-{number}-{year}-{code}
    # Example: "LUA-90-2025-QH15"
    
    # Hierarchy level: 1 (Highest)
    # Can be amended by: Luật
    # Implements: Constitution
}
```

**Files:**
- Luật đấu thầu 2023.docx → `LUA-43-2023-QH14`
- Luật số 57 2024 QH15.docx → `LUA-57-2024-QH15`
- Luật số 90 2025-qh15.docx → `LUA-90-2025-QH15`
- HỢP NHẤT 126 2025 → `LUA-126-2025-QH15-HOPNHAT`

### 2. **Nghị định** (1 file)
```python
{
    "category": "Nghị định",
    "document_type": "decree",
    "issuing_authority": "Chính phủ",
    "issuing_authority_code": "CP",
    
    # Document ID: ND-{number}-{year}-CP
    # Example: "ND-214-2025-CP"
    
    # Hierarchy level: 2
    # Implements: Luật
    # Can be amended by: Nghị định
}
```

**Files:**
- ND 214 - 4.8.2025 - Thay thế NĐ24-original.docx → `ND-214-2025-CP`

### 3. **Thông tư** (2 files)
```python
{
    "category": "Thông tư",
    "document_type": "circular",
    "issuing_authority": "Bộ Kế hoạch và Đầu tư",
    "issuing_authority_code": "BKH",
    
    # Document ID: TT-{number}-{year}-{ministry}
    # Example: "TT-05-2023-BKH"
    
    # Hierarchy level: 3
    # Implements: Nghị định, Luật
    # Guides: Implementation details
}
```

### 4. **Quyết định** (1 file)
```python
{
    "category": "Quyết định",
    "document_type": "decision",
    "issuing_authority": "Bộ Y tế",
    "issuing_authority_code": "BYT",
    
    # Document ID: QD-{number}-{year}-{ministry}
    # Example: "QD-1667-2024-BYT"
    
    # Hierarchy level: 3-4
}
```

### 5. **Hồ sơ mời thầu** (46 files)
```python
{
    "category": "Hồ sơ mời thầu",
    "document_type": "bidding_form",
    "issuing_authority": "Bộ Kế hoạch và Đầu tư",
    "issuing_authority_code": "BKH",
    
    # Document ID: FORM-{type}-{subtype}-{year}
    # Examples:
    # "FORM-HSYC-XAYLAP-2025"    (Mẫu HSYC Xây lắp)
    # "FORM-HSYC-HANGHOA-2025"   (Mẫu HSYC Hàng hóa)
    
    # Hierarchy level: 5 (Reference documents)
    # Attached to: Thông tư, Nghị định
}
```

### 6. **Mẫu báo cáo** (10 files)
```python
{
    "category": "Mẫu báo cáo",
    "document_type": "report_template",
    "issuing_authority": "Bộ Kế hoạch và Đầu tư",
    "issuing_authority_code": "BKH",
    
    # Document ID: TEMPLATE-{type}-{number}-{year}
    # Example: "TEMPLATE-BAOCAO-01-2025"
    
    # Hierarchy level: 5 (Supporting documents)
}
```

### 7. **Câu hỏi thi** (6 files)
```python
{
    "category": "Câu hỏi thi",
    "document_type": "exam_question",
    "issuing_authority": "Cục Quản lý đấu thầu",
    "issuing_authority_code": "CQLDT",
    
    # Document ID: EXAM-{topic}-{set}-{year}
    # Example: "EXAM-DAUTHAU-SET01-2025"
    
    # Hierarchy level: 6 (Educational materials)
}
```

---

## 🎯 RECOMMENDED IMPLEMENTATION

### Phase 1: Simplified Schema (MVP - 2 days)

Start với **essential fields only**:

```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id VARCHAR(255) UNIQUE NOT NULL,
    
    -- Classification (7 categories)
    category VARCHAR(100) NOT NULL,
    document_type VARCHAR(50) NOT NULL,
    
    -- Identity
    document_number VARCHAR(100),
    document_name TEXT NOT NULL,
    short_name VARCHAR(255),
    
    -- Authority
    issuing_authority VARCHAR(100),
    issuing_authority_code VARCHAR(50),
    
    -- Dates
    issued_date DATE,
    effective_date DATE,
    
    -- Status
    legal_status VARCHAR(50) DEFAULT 'in_force',
    status VARCHAR(50) DEFAULT 'active',
    
    -- File
    source_file TEXT NOT NULL,
    file_name TEXT NOT NULL,
    
    -- Processing
    total_chunks INTEGER DEFAULT 0,
    
    -- Relationships
    parent_document_id VARCHAR(255),
    replaces_document_id VARCHAR(255),
    
    -- Audit
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Phase 2: Add Relationships (Week 2)
- Document relationships table
- Version tracking
- Section navigation

### Phase 3: Advanced Features (Week 3-4)
- Full-text search
- Citation analysis
- Timeline view
- Compliance checking

---

## 📋 MIGRATION CHECKLIST

### Day 1: Schema Setup
- [ ] Create documents table với MVP schema
- [ ] Create category mapping configuration
- [ ] Script to extract metadata from 70 files
- [ ] Validate document_id generation

### Day 2: Data Population
- [ ] Batch insert 70 documents
- [ ] Verify all 7 categories populated
- [ ] Check relationships (parent documents)
- [ ] Generate document statistics

### Day 3: Reprocessing
- [ ] Update preprocessing pipeline
- [ ] Reprocess with new document_ids
- [ ] Validate chunk counts
- [ ] Test retrieval by category

### Day 4: API & Testing
- [ ] Update catalog API
- [ ] Add filter by category
- [ ] Add toggle by document_id
- [ ] Integration tests
- [ ] Documentation

---

## 🔍 EXAMPLE QUERIES

```sql
-- 1. List all laws in force
SELECT document_id, document_name, effective_date
FROM documents
WHERE category = 'Luật chính' 
  AND legal_status = 'in_force'
  AND status = 'active'
ORDER BY effective_date DESC;

-- 2. Find all implementing decrees for a law
SELECT d.*
FROM documents d
WHERE d.parent_document_id = 'LUA-90-2025-QH15'
  AND d.category = 'Nghị định';

-- 3. Get document hierarchy
WITH RECURSIVE doc_tree AS (
    SELECT *, 1 as level
    FROM documents
    WHERE document_id = 'LUA-90-2025-QH15'
    
    UNION ALL
    
    SELECT d.*, dt.level + 1
    FROM documents d
    INNER JOIN doc_tree dt ON d.parent_document_id = dt.document_id
)
SELECT * FROM doc_tree ORDER BY level, category;

-- 4. Count documents by category
SELECT 
    category,
    COUNT(*) as total_docs,
    SUM(total_chunks) as total_chunks
FROM documents
WHERE status = 'active'
GROUP BY category
ORDER BY total_docs DESC;

-- 5. Find related bidding forms for a circular
SELECT d.*
FROM documents d
WHERE d.category = 'Hồ sơ mời thầu'
  AND d.parent_document_id IN (
      SELECT document_id 
      FROM documents 
      WHERE category = 'Thông tư'
  );
```

---

## ✅ ADVANTAGES của design này

1. **Standards-based:** Follows international legal database best practices
2. **Scalable:** Can handle 1000+ documents easily
3. **Flexible:** 7 categories với room for expansion
4. **Traceable:** Full audit trail and version history
5. **Searchable:** Multiple indexes for fast retrieval
6. **Hierarchical:** Proper legal document relationships
7. **Vietnamese-friendly:** Supports Vietnamese legal system structure

---

**Next Steps:** Xác nhận để tôi tạo migration scripts cho schema này?
