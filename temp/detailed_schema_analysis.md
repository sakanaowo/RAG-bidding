# 📊 Database Schema Details - RAG Bidding System

**Generated:** November 27, 2025  
**Database:** rag_bidding_v2  
**Migration:** 0dd6951d6844 (Initial schema)

---

## 📋 Table 1: `documents`

**Purpose:** Application-level document management table  
**Rows:** 64 documents  
**Table comment:** "Application-level document management table"

### Columns (11)

| Column | Type | Nullable | Default | Comment |
|--------|------|----------|---------|---------|
| `id` | UUID | NOT NULL | `gen_random_uuid()` | Primary key |
| `document_id` | VARCHAR(255) | NOT NULL | - | Unique document identifier |
| `document_name` | TEXT | NOT NULL | - | Document title/name |
| `category` | VARCHAR(100) | NOT NULL | - | Category: legal, bidding, etc. |
| `document_type` | VARCHAR(50) | NOT NULL | - | Type: law, decree, circular, bidding_form, etc. |
| `source_file` | TEXT | NOT NULL | - | Path to source file |
| `file_name` | TEXT | NOT NULL | - | Original filename |
| `total_chunks` | INTEGER | NULL | `0` | Number of chunks/embeddings |
| `status` | VARCHAR(50) | NULL | `'active'` | Status: active, processing, expired, deleted |
| `created_at` | TIMESTAMP | NOT NULL | `now()` | Creation timestamp |
| `updated_at` | TIMESTAMP | NOT NULL | `now()` | Last update timestamp |

### Primary Key

- **documents_pkey** ON (id)

### Indexes (7)

**Composite Indexes (2):**
- `idx_documents_category_status` - NON-UNIQUE ON (category, status)
- `idx_documents_status_type` - NON-UNIQUE ON (status, document_type)

**Single Column Indexes (5):**
- `ix_documents_category` - NON-UNIQUE ON (category)
- `ix_documents_document_id` - **UNIQUE** ON (document_id) ⭐ Main lookup
- `ix_documents_document_type` - NON-UNIQUE ON (document_type)
- `ix_documents_source_file` - NON-UNIQUE ON (source_file)
- `ix_documents_status` - NON-UNIQUE ON (status)

### Data Distribution (8 types)

| Document Type | Count | Percentage |
|---------------|-------|------------|
| bidding_form | 37 | 57.8% |
| report_template | 10 | 15.6% |
| law | 6 | 9.4% |
| exam_question | 4 | 6.3% |
| bidding | 2 | 3.1% |
| circular | 2 | 3.1% |
| decree | 2 | 3.1% |
| decision | 1 | 1.6% |

### Migration Changes

**Indexes Removed (4):**
- `idx_documents_category` → Replaced with composite
- `idx_documents_source` → Replaced with `ix_documents_source_file`
- `idx_documents_status` → Replaced with composite
- `idx_documents_type` → Replaced with `ix_documents_document_type`

**Indexes Added (7):**
- All indexes listed above

**Constraints Removed:**
- `documents_document_id_key` (UNIQUE) → Replaced with unique index

**Comments Updated:**
- All 11 column comments added
- Table comment updated from "Master table..." to "Application-level..."

---

## 📋 Table 2: `langchain_pg_collection`

**Purpose:** LangChain internal collection management - DO NOT modify directly  
**Rows:** 1 collection  
**Table comment:** "LangChain internal collection management - DO NOT modify directly"

### Columns (3)

| Column | Type | Nullable | Default | Comment |
|--------|------|----------|---------|---------|
| `uuid` | UUID | NOT NULL | - | Collection UUID |
| `name` | VARCHAR | **NULL** | - | Collection name (e.g., 'docs') |
| `cmetadata` | **JSONB** | NULL | - | Collection metadata |

### Primary Key

- **langchain_pg_collection_pkey** ON (uuid)

### Indexes (1)

- `langchain_pg_collection_name_key` - **UNIQUE** ON (name)

### Migration Changes

**Type Changes:**
- `cmetadata`: JSON → **JSONB** (better performance, supports indexing)
- `name`: VARCHAR NOT NULL → VARCHAR **NULL** (allows null values)

**Constraint Changes:**
- Removed: `langchain_pg_collection_name_key` (UNIQUE constraint)
- Added: `langchain_pg_collection_name_key` (UNIQUE index)

**Comments Added:**
- All 3 column comments
- Table comment added

### Current Data

```
uuid                                  name    cmetadata
------------------------------------  ------  ----------
3f2e421c-2ae0-4e94-a6dc-e8b8f8e8e8e8  docs    {"hnsw_ef_construction": 32, ...}
```

---

## 📋 Table 3: `langchain_pg_embedding`

**Purpose:** Vector embeddings storage with metadata  
**Rows:** 7,892 chunks  
**Table comment:** "Vector embeddings storage with metadata"

### Columns (5)

| Column | Type | Nullable | Default | Comment |
|--------|------|----------|---------|---------|
| `id` | VARCHAR | NOT NULL | - | Chunk ID (UUID format) |
| `collection_id` | UUID | NULL | - | Reference to collection |
| `embedding` | VECTOR(3072) | NULL | - | OpenAI text-embedding-3-large vector (3072-dim) |
| `document` | **TEXT** | NULL | - | Chunk text content |
| `cmetadata` | JSONB | NULL | - | Chunk metadata: document_id, chunk_index, hierarchy, etc. |

### Primary Key

- **langchain_pg_embedding_pkey** ON (id)

### Indexes (2)

- `langchain_pg_embedding_collection_id_idx` - NON-UNIQUE ON (collection_id)
- `idx_embedding_document_type` - NON-UNIQUE ON **((cmetadata->>'document_type'))** ⭐ Functional index

### Foreign Keys (1)

- **langchain_pg_embedding_collection_id_fkey**  
  collection_id → langchain_pg_collection.uuid

### Migration Changes

**Type Changes:**
- `document`: VARCHAR → **TEXT** (allows longer chunk content)

**Indexes Added:**
- `idx_embedding_document_type` - Functional index on JSONB field for fast filtering by document type

**Comments Added:**
- All 5 column comments
- Table comment added

### Metadata Structure (cmetadata JSONB)

```json
{
  "document_id": "string",           // Reference to documents.document_id
  "chunk_index": 0,                  // Position in document
  "chunk_id": "string",              // Unique chunk identifier
  "total_chunks": 0,                 // Total chunks in document
  "document_type": "string",         // law, decree, circular, etc.
  "status": "active",                // Document status
  "hierarchy": ["array"],            // Document structure path
  "level": "string",                 // dieu, khoan, phan, etc.
  "section_title": "string",         // Section heading
  "char_count": 0,                   // Character count
  "has_table": false,                // Contains table
  "has_list": false,                 // Contains list
  "is_complete_unit": true,          // Complete semantic unit
  "extra_metadata": {                // Additional enrichment
    "concepts": [],                  // Extracted concepts
    "keywords": [],                  // Keywords
    "legal_terms": [],               // Legal terminology
    "entities": {},                  // Named entities
    "enrichment_version": "1.0.0",   // Processing version
    ...
  },
  "document_info": {                 // Document-level info
    "document_status": "active"
  },
  "processing_metadata": {           // Status tracking
    "processing_status": "active",
    "status_change_history": []
  }
}
```

### Vector Statistics

- **Dimensions:** 3,072 (OpenAI text-embedding-3-large)
- **Total vectors:** 7,892
- **Average chunks per document:** ~123 chunks
- **Embedding size:** ~12 KB per vector (3,072 floats × 4 bytes)
- **Total embedding storage:** ~95 MB

### Chunk Distribution by Type

| Document Type | Chunks | Avg per Doc |
|---------------|--------|-------------|
| law | 2,798 | ~467 |
| bidding_form | 3,500+ | ~95 |
| decree | ~600 | ~300 |
| circular | ~400 | ~200 |
| Others | ~594 | varies |

---

## 🔗 Table Relationships

```
documents (PRIMARY)
    ↓ 1:N (via document_id in metadata)
langchain_pg_embedding
    ↓ N:1 (via collection_id FK)
langchain_pg_collection (INTERNAL)
```

### Relationship Details

**documents → langchain_pg_embedding:**
- Type: 1:N (One document has many chunks)
- Join: `documents.document_id = langchain_pg_embedding.cmetadata->>'document_id'`
- Note: Soft relationship via JSONB, not enforced FK

**langchain_pg_embedding → langchain_pg_collection:**
- Type: N:1 (Many embeddings belong to one collection)
- Join: `langchain_pg_embedding.collection_id = langchain_pg_collection.uuid`
- Constraint: Foreign Key enforced

---

## 📊 Schema Statistics

### Table Sizes

| Table | Size | Percentage |
|-------|------|------------|
| langchain_pg_embedding | ~118 MB | 93.7% |
| documents | ~64 KB | 0.1% |
| langchain_pg_collection | ~8 KB | <0.1% |
| **Total** | **~126 MB** | **100%** |

### Row Counts

| Table | Rows | Growth Rate |
|-------|------|-------------|
| documents | 64 | +1-2/week |
| langchain_pg_embedding | 7,892 | +120-240/week |
| langchain_pg_collection | 1 | Static |

### Index Usage (Estimated)

Most used indexes:
1. `ix_documents_document_id` - Used in every chunk lookup
2. `langchain_pg_embedding_collection_id_idx` - Used in vector queries
3. `idx_documents_status_type` - Used in document filtering
4. `idx_embedding_document_type` - Used in type-specific queries

---

## 🎯 Query Patterns

### Pattern 1: Get Document with Chunks

```sql
-- Get document info
SELECT * FROM documents WHERE document_id = 'DOC123';

-- Get all chunks for document
SELECT * FROM langchain_pg_embedding 
WHERE cmetadata->>'document_id' = 'DOC123'
ORDER BY (cmetadata->>'chunk_index')::int;
```

### Pattern 2: Vector Similarity Search

```sql
SELECT 
    e.document,
    e.cmetadata->>'document_id' as doc_id,
    e.cmetadata->>'section_title' as section,
    e.embedding <=> :query_vector as distance
FROM langchain_pg_embedding e
WHERE e.cmetadata->>'document_type' = 'law'
ORDER BY e.embedding <=> :query_vector
LIMIT 10;
```

### Pattern 3: Document Statistics

```sql
SELECT 
    d.document_type,
    COUNT(DISTINCT d.document_id) as num_docs,
    SUM(d.total_chunks) as total_chunks,
    AVG(d.total_chunks) as avg_chunks
FROM documents d
WHERE d.status = 'active'
GROUP BY d.document_type
ORDER BY num_docs DESC;
```

### Pattern 4: Active Documents Only

```sql
-- Using composite index idx_documents_status_type
SELECT * FROM documents 
WHERE status = 'active' AND document_type = 'law'
ORDER BY created_at DESC;
```

---

## 🔧 Performance Optimization

### Current Optimizations

1. **Composite Indexes:**
   - `idx_documents_category_status` - Filter by category AND status
   - `idx_documents_status_type` - Filter by status AND type

2. **JSONB Functional Index:**
   - `idx_embedding_document_type` - Fast filtering on metadata field

3. **Unique Indexes:**
   - `ix_documents_document_id` - Fast document lookups
   - `langchain_pg_collection_name_key` - Fast collection lookups

4. **Vector Index (HNSW):**
   - Collection metadata: `{"hnsw_ef_construction": 32}`
   - Enables fast approximate nearest neighbor search

### Recommended Future Optimizations

1. **Add GIN Index on JSONB:**
   ```sql
   CREATE INDEX idx_embedding_metadata_gin 
   ON langchain_pg_embedding USING GIN (cmetadata);
   ```

2. **Partial Indexes for Active Documents:**
   ```sql
   CREATE INDEX idx_documents_active 
   ON documents (document_type) 
   WHERE status = 'active';
   ```

3. **Expression Index for Chunk Count:**
   ```sql
   CREATE INDEX idx_embedding_chunk_index 
   ON langchain_pg_embedding ((cmetadata->>'chunk_index')::int);
   ```

---

## 🚨 Important Notes

### For Application Developers

1. **NEVER modify `langchain_pg_collection` directly**
   - Managed by LangChain internally
   - Changes may break vector store functionality

2. **Use Repository pattern for `documents` table**
   - Defined in `src/models/repositories.py`
   - Handles status transitions, validation

3. **Access embeddings via LangChain methods**
   - Use `PGVector` store for vector operations
   - Direct SQL queries for metadata filtering only

### For Database Administrators

1. **Monitor index usage:**
   ```sql
   SELECT * FROM pg_stat_user_indexes 
   WHERE schemaname = 'public' 
   ORDER BY idx_scan DESC;
   ```

2. **Watch table bloat:**
   ```sql
   SELECT schemaname, tablename, 
          pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
   FROM pg_tables WHERE schemaname = 'public';
   ```

3. **Regular VACUUM:**
   - `VACUUM ANALYZE` weekly
   - `VACUUM FULL` monthly (with downtime)

---

## 📝 Schema Evolution History

### Migration: 0dd6951d6844 (Initial - Nov 27, 2025)

**Created:**
- Baseline schema from existing tables
- Added comprehensive column comments
- Added table-level comments

**Modified:**
- documents: Reorganized indexes (4 removed, 7 added)
- langchain_pg_collection: JSON → JSONB, constraint → index
- langchain_pg_embedding: VARCHAR → TEXT, added functional index

**Impact:**
- ✅ Better query performance (composite indexes)
- ✅ Improved metadata queries (JSONB, functional index)
- ✅ Self-documenting schema (comments)
- ⚠️ No data migration required (stamp only)

---

**Last Updated:** November 27, 2025  
**Migration Version:** 0dd6951d6844 (head)  
**Database Size:** 126 MB  
**Total Records:** 7,957 (64 docs + 7,892 chunks + 1 collection)
