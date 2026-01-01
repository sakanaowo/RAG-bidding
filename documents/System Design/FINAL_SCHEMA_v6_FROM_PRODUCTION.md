# RAG Bidding System - Final Production Schema v6.0

**Database:** `temp` (Production Test)  
**Extracted Date:** December 12, 2025  
**Total Tables:** 10  
**PostgreSQL Version:** 18.1

---

## 📋 Schema Overview

This is the **actual production schema** extracted from the `temp` database, which has been tested and validated. Schema v6 simplifies document management by using category-based filtering instead of complex collections system.

### Tables Summary

| # | Table Name | Purpose | Records |
|---|------------|---------|---------|
| 1 | `users` | User authentication & profiles | Variable |
| 2 | `documents` | Document metadata with categories | ~68 docs |
| 3 | `document_chunks` | Text chunks from documents | ~8K chunks |
| 4 | `langchain_pg_embedding` | Vector embeddings (3072-dim) | ~8K vectors |
| 5 | `conversations` | Chat session management | Variable |
| 6 | `messages` | Chat messages (user + assistant) | Variable |
| 7 | `citations` | Source references in responses | Variable |
| 8 | `queries` | Query logging & analytics | Variable |
| 9 | `feedback` | User feedback on responses | Variable |
| 10 | `user_usage_metrics` | Daily usage statistics | Variable |

---

## 🗃️ Detailed Schema

### 1. Users Table

**Purpose:** User authentication, profiles, and authorization

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Authentication
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255),
    
    -- Profile
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user', -- user, admin, manager
    
    -- OAuth Support
    oauth_provider VARCHAR(50), -- google, microsoft
    oauth_id VARCHAR(255),
    
    -- User Preferences
    preferences JSONB DEFAULT '{}',
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);
```

**Indexes:**
- `users_pkey` - PRIMARY KEY on `id`
- `users_email_key` - UNIQUE on `email`
- `users_username_key` - UNIQUE on `username`
- `idx_users_role` - On `role` WHERE `deleted_at IS NULL`
- `idx_users_oauth` - On `(oauth_provider, oauth_id)`

**Triggers:**
- `trigger_users_updated_at` - Auto-update `updated_at` on UPDATE

---

### 2. Documents Table

**Purpose:** Document metadata with category-based classification

```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identifiers
    document_id VARCHAR(255) UNIQUE, -- Business ID
    document_name VARCHAR(500),
    filename VARCHAR(255),
    filepath VARCHAR(500),
    source_file TEXT,
    
    -- Classification (SIMPLIFIED in v6)
    category VARCHAR(100) NOT NULL DEFAULT 'Khác',
    document_type VARCHAR(50),
    
    -- Upload Info
    uploaded_by UUID REFERENCES users(id),
    file_hash VARCHAR(64),
    file_size_bytes BIGINT,
    
    -- Content Stats
    total_chunks INTEGER DEFAULT 0,
    
    -- Metadata
    metadata JSONB,
    
    -- Status
    status VARCHAR(50) DEFAULT 'active',
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Categories (Production Data):**
- `"Hồ sơ mời thầu"` - Bidding documents (45 docs, 66.2%)
- `"Mẫu báo cáo"` - Report templates (10 docs, 14.7%)
- `"Câu hỏi thi"` - Exam questions (5 docs, 7.4%)
- `"Luật chính"` - Primary laws (4 docs, 5.9%)
- `"Quy định khác"` - Other regulations (4 docs, 5.9%)

**Indexes:**
- `documents_pkey` - PRIMARY KEY on `id`
- `documents_document_id_key` - UNIQUE on `document_id`
- `idx_documents_category` - On `category` WHERE `status = 'active'`
- `idx_documents_type` - On `document_type`
- `idx_documents_uploader` - On `uploaded_by`
- `idx_documents_status` - On `status`

---

### 3. Document Chunks Table

**Purpose:** Text chunks extracted from documents with rich metadata

```sql
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id VARCHAR(255) UNIQUE NOT NULL,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    
    -- Content
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    
    -- Structure
    section_title VARCHAR(500),
    hierarchy_path TEXT[], -- ["Chapter 1", "Section 1.1", "Article 5"]
    
    -- Enrichment (from metadata extraction)
    keywords TEXT[],
    concepts TEXT[],
    entities JSONB, -- Named entities
    
    -- Content Analysis
    char_count INTEGER,
    has_table BOOLEAN DEFAULT false,
    has_list BOOLEAN DEFAULT false,
    is_complete_unit BOOLEAN DEFAULT true,
    
    -- Usage Analytics
    retrieval_count INTEGER DEFAULT 0,
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes:**
- `document_chunks_pkey` - PRIMARY KEY on `id`
- `document_chunks_chunk_id_key` - UNIQUE on `chunk_id`
- `idx_document_chunks_document` - On `document_id`
- `idx_document_chunks_fts` - GIN full-text search on `content`

---

### 4. Vector Embeddings Table

**Purpose:** OpenAI embeddings for semantic search

```sql
CREATE TABLE langchain_pg_embedding (
    uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Vector (OpenAI text-embedding-3-large)
    embedding VECTOR(3072), -- 3072 dimensions
    
    -- Content
    document TEXT, -- Chunk content
    
    -- Metadata
    cmetadata JSONB, -- Rich metadata from chunks
    custom_id VARCHAR,
    
    -- Link to chunks
    chunk_id UUID REFERENCES document_chunks(id) ON DELETE SET NULL,
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes:**
- `langchain_pg_embedding_pkey` - PRIMARY KEY on `uuid`
- `idx_langchain_pg_embedding_vector` - IVFFlat vector index
  ```sql
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100)
  ```

**Note:** Using IVFFlat instead of HNSW because:
- HNSW max dimensions: 2000
- text-embedding-3-large: 3072 dimensions
- IVFFlat supports unlimited dimensions

---

### 5. Conversations Table

**Purpose:** Chat session management

```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Content
    title VARCHAR(500),
    summary TEXT,
    
    -- RAG Configuration
    rag_mode VARCHAR(50) DEFAULT 'balanced', -- fast, balanced, quality
    category_filter TEXT[], -- Categories to search
    
    -- Statistics
    message_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_cost_usd DECIMAL(10,4) DEFAULT 0,
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP,
    deleted_at TIMESTAMP
);
```

**Indexes:**
- `conversations_pkey` - PRIMARY KEY on `id`

---

### 6. Messages Table

**Purpose:** Chat messages (user queries + assistant responses)

```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    
    -- Content
    role VARCHAR(20) NOT NULL, -- 'user' or 'assistant'
    content TEXT NOT NULL,
    
    -- Sources (for assistant messages)
    sources JSONB,
    
    -- Performance Metrics
    processing_time_ms INTEGER,
    tokens_total INTEGER,
    
    -- Inline Feedback
    feedback_rating INTEGER CHECK (feedback_rating >= 1 AND feedback_rating <= 5),
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes:**
- `messages_pkey` - PRIMARY KEY on `id`

---

### 7. Citations Table

**Purpose:** Track source citations in assistant responses

```sql
CREATE TABLE citations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id),
    chunk_id UUID NOT NULL REFERENCES document_chunks(id),
    
    -- Citation Info
    citation_number INTEGER NOT NULL, -- [1], [2], [3]
    citation_text TEXT, -- Snippet shown to user
    
    -- Relevance Scores
    relevance_score DECIMAL(5,4), -- Vector similarity
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes:**
- `citations_pkey` - PRIMARY KEY on `id`

---

### 8. Queries Table

**Purpose:** Query logging and performance analytics

```sql
CREATE TABLE queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    conversation_id UUID REFERENCES conversations(id),
    message_id UUID REFERENCES messages(id),
    
    -- Query Info
    query_text TEXT NOT NULL,
    query_hash VARCHAR(64),
    rag_mode VARCHAR(50),
    
    -- Filtering Context
    categories_searched TEXT[], -- Categories included in search
    
    -- Performance Metrics
    retrieval_count INTEGER,
    total_latency_ms INTEGER,
    
    -- Cost Tracking
    tokens_total INTEGER,
    estimated_cost_usd DECIMAL(10,6),
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes:**
- `queries_pkey` - PRIMARY KEY on `id`

---

### 9. Feedback Table

**Purpose:** User feedback on assistant responses

```sql
CREATE TABLE feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    
    -- Feedback Content
    feedback_type VARCHAR(50), -- rating, issue, suggestion
    rating INTEGER,
    comment TEXT,
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes:**
- `feedback_pkey` - PRIMARY KEY on `id`

---

### 10. User Usage Metrics Table

**Purpose:** Daily aggregated usage statistics per user

```sql
CREATE TABLE user_usage_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    
    -- Time Dimension
    date DATE NOT NULL,
    
    -- Usage Metrics
    total_queries INTEGER DEFAULT 0,
    total_messages INTEGER DEFAULT 0,
    total_tokens BIGINT DEFAULT 0,
    total_cost_usd DECIMAL(10,4) DEFAULT 0,
    
    -- Usage Patterns
    categories_accessed TEXT[], -- Categories accessed today
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT user_usage_metrics_unique UNIQUE (user_id, date)
);
```

**Indexes:**
- `user_usage_metrics_pkey` - PRIMARY KEY on `id`
- `user_usage_metrics_user_id_date_key` - UNIQUE on `(user_id, date)`

---

## 🔄 Key Relationships

### Document → Chunks → Embeddings
```
documents (1) ──→ (N) document_chunks (1) ──→ (1) langchain_pg_embedding
```

### User → Conversations → Messages
```
users (1) ──→ (N) conversations (1) ──→ (N) messages
```

### Messages → Citations → Documents/Chunks
```
messages (1) ──→ (N) citations ──→ documents
                            └──→ document_chunks
```

### Analytics Flow
```
users (1) ──→ (N) queries
      └──→ (N) feedback
      └──→ (N) user_usage_metrics (daily aggregation)
```

---

## ⚙️ Functions & Triggers

### Update Timestamp Function
```sql
CREATE FUNCTION update_updated_at_column() 
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

**Applied to:**
- `users.updated_at`

---

## 📊 Production Statistics

From database `temp` (as of Dec 12, 2025):

| Metric | Value |
|--------|-------|
| **Total Documents** | 68 |
| **Total Chunks** | ~8,000 |
| **Vector Embeddings** | ~8,000 |
| **Vector Dimensions** | 3,072 |
| **Embedding Model** | text-embedding-3-large |
| **Vector Index Type** | IVFFlat (lists=100) |
| **Database Size** | ~500 MB |

---

## 🎯 Design Decisions

### 1. Category-based Filtering (Removed Collections)
**Rationale:** Specialized bidding system doesn't need complex M:N collection relationships. Simple category filtering is sufficient and more performant.

### 2. IVFFlat vs HNSW Index
**Decision:** IVFFlat  
**Reason:** HNSW max dimensions = 2000, but text-embedding-3-large = 3072 dims

### 3. Soft Delete on Users
**Implementation:** `deleted_at` timestamp  
**Benefit:** Preserve conversation/analytics history

### 4. Inline Feedback in Messages
**Rationale:** Quick ratings (1-5 stars) directly on messages, with detailed feedback in separate table

### 5. Daily Usage Metrics
**Aggregation:** Daily rollup per user for cost tracking and analytics

---

## 🚀 Performance Optimizations

### Indexes Strategy

1. **Vector Search:** IVFFlat index on embeddings
2. **Category Filtering:** Partial index on `documents.category WHERE status = 'active'`
3. **Full-Text Search:** GIN index on `document_chunks.content`
4. **Relationships:** Foreign key indexes auto-created

### Query Patterns

```sql
-- Category-based document search
SELECT * FROM documents 
WHERE category = 'Hồ sơ mời thầu' 
AND status = 'active';

-- Vector similarity search
SELECT * FROM langchain_pg_embedding 
ORDER BY embedding <=> '[vector]' 
LIMIT 10;

-- User analytics
SELECT date, total_queries, total_cost_usd 
FROM user_usage_metrics 
WHERE user_id = '...' 
ORDER BY date DESC 
LIMIT 30;
```

---

## 📝 Migration Notes

### From v5 to v6

**Removed:**
- `document_collections` table
- `collection_documents` junction table
- Collections management complexity

**Added:**
- `documents.category` field
- Simplified filtering in `conversations.category_filter`
- Category tracking in `queries.categories_searched`

**Migration Script:**
```sql
-- Add category field
ALTER TABLE documents ADD COLUMN category VARCHAR(100) NOT NULL DEFAULT 'Khác';

-- Migrate data based on filepath patterns
UPDATE documents SET category = 
    CASE 
        WHEN filepath LIKE '%Ho so moi thau%' THEN 'Hồ sơ mời thầu'
        WHEN filepath LIKE '%Mau bao cao%' THEN 'Mẫu báo cáo'
        WHEN filepath LIKE '%Cau hoi thi%' THEN 'Câu hỏi thi'
        WHEN filepath LIKE '%Luat chinh%' THEN 'Luật chính'
        WHEN document_type IN ('decree', 'circular') THEN 'Quy định khác'
        ELSE 'Khác'
    END;

-- Drop collections tables
DROP TABLE collection_documents;
DROP TABLE document_collections;
```

---

## ✅ Production Readiness Checklist

- [x] All tables created successfully
- [x] Foreign key constraints validated
- [x] Indexes created and optimized
- [x] Vector index functional (IVFFlat)
- [x] Triggers working correctly
- [x] Category migration completed
- [x] Production data imported (68 docs, ~8K chunks)
- [x] Extensions enabled (vector, pg_trgm, uuid-ossp)
- [x] Performance tested with actual queries

---

## 🔧 Maintenance Commands

### Database Statistics
```sql
-- Table sizes
SELECT schemaname, tablename, 
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- Vector index stats
SELECT * FROM pg_indexes 
WHERE tablename = 'langchain_pg_embedding';
```

### Backup & Restore
```bash
# Backup schema only
pg_dump temp --schema-only > schema_backup.sql

# Backup with data
pg_dump temp > full_backup.sql

# Restore
psql rag_bidding_production < schema_backup.sql
```

---

## 📚 References

- **Schema Version:** 6.0 (Final)
- **Source Database:** `temp` (Production Test)
- **Documentation Files:**
  - Full SQL: `schema_from_temp_db.sql`
  - Table Details: `schema_detailed_descriptions.txt`
  - Column Info: `schema_columns_detail.txt`
- **Related Docs:** `14_Database_Schema_v6.md`

---

**Status:** ✅ Production Ready  
**Last Updated:** December 12, 2025  
**Next Review:** Q1 2026
