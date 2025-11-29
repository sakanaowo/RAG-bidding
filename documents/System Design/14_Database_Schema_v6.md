# RAG Bidding System - Database Schema v6.0

**Ngày tạo:** 29/11/2025  
**Phiên bản:** 6.0 (Simplified Production)  
**Mô tả:** Schema đơn giản hóa cho hệ thống đấu thầu chuyên biệt

---

## 🎯 Triết lý thiết kế v6

Schema v6 được thiết kế dựa trên **thực tế hệ thống đấu thầu chuyên biệt**:

- ❌ **Loại bỏ Collections system** phức tạp (document_collections, collection_documents)
- ✅ **Category-based filtering** đơn giản trong documents table
- 📊 **Dựa trên data thực tế**: 68 documents với 5 categories cố định
- 🚀 **Production-ready**: Tối ưu cho specialized bidding use case

---

## 📊 Phân tích dữ liệu hiện tại

**68 documents** thuộc 5 categories chính:

- **Hồ sơ mời thầu**: 45 docs (66.2%)
- **Mẫu báo cáo**: 10 docs (14.7%)
- **Câu hỏi thi**: 5 docs (7.4%)
- **Luật chính**: 4 docs (5.9%)
- **Quy định khác**: 4 docs (5.9%) - Nghị định, Quyết định, Thông tư

---

## 🏗️ Kiến trúc tổng quan

### Core Components (10 Tables)

```
📋 User Management (1)     📄 Document System (2)     💬 Conversations (3)     📊 Analytics (3)     🔍 Vector Storage (1)
├─ users                   ├─ documents                ├─ conversations         ├─ queries           ├─ langchain_pg_embedding
                          └─ document_chunks          ├─ messages              ├─ feedback
                                                      └─ citations             └─ user_usage_metrics
```

### Simplified Document Flow

```
Document Upload → Category Assignment → Chunk Extraction → Vector Embedding → Search & RAG
```

---

## 🗂️ Bảng chi tiết

### 1. User Management

#### `users`

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Authentication
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255), -- NULL for OAuth users

    -- Profile
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user', -- user, admin, manager

    -- OAuth
    oauth_provider VARCHAR(50), -- google, microsoft
    oauth_id VARCHAR(255),

    -- Settings
    preferences JSONB DEFAULT '{}', -- UI preferences, default filters

    -- Status
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,

    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP -- Soft delete
);
```

**Indexes:**

- `idx_users_role` - Query by role
- `idx_users_oauth` - OAuth lookup
- `idx_users_active` - Active users only

---

### 2. Document System

#### `documents`

```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- File info
    document_id VARCHAR(255) UNIQUE NOT NULL, -- Business ID từ data hiện tại
    document_name VARCHAR(500) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    filepath VARCHAR(1000) NOT NULL,
    source_file TEXT, -- Path từ data/raw/

    -- Classification (SIMPLIFIED)
    category VARCHAR(100) NOT NULL, -- "Hồ sơ mời thầu", "Mẫu báo cáo", etc.
    document_type VARCHAR(100), -- law, decree, bidding_form, report_template

    -- Upload info
    uploaded_by UUID REFERENCES users(id),
    file_hash VARCHAR(64),
    file_size_bytes BIGINT,

    -- Content stats
    total_chunks INTEGER DEFAULT 0,

    -- Rich metadata (from current system)
    metadata JSONB, -- File-specific metadata

    -- Status
    status VARCHAR(50) DEFAULT 'active', -- active, archived, deleted

    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Categories (Fixed Enum-like):**

- `"Hồ sơ mời thầu"` - Bidding documents (45 docs)
- `"Mẫu báo cáo"` - Report templates (10 docs)
- `"Câu hỏi thi"` - Exam questions (5 docs)
- `"Luật chính"` - Primary laws (4 docs)
- `"Quy định khác"` - Other regulations (4 docs)

**Indexes:**

- `idx_documents_category` - Fast category filtering
- `idx_documents_type` - Document type search
- `idx_documents_uploader` - User's documents
- `idx_documents_status` - Active documents only

#### `document_chunks`

```sql
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id VARCHAR(255) UNIQUE NOT NULL, -- From existing cmetadata
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    -- Content
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,

    -- Structure (from cmetadata analysis)
    section_title VARCHAR(500),
    hierarchy_path TEXT[], -- Document structure path

    -- Enrichment (from current extra_metadata)
    keywords TEXT[], -- Key terms
    concepts TEXT[], -- Legal concepts
    entities JSONB, -- Named entities (people, places, organizations)

    -- Content analysis
    char_count INTEGER,
    has_table BOOLEAN DEFAULT false,
    has_list BOOLEAN DEFAULT false,
    is_complete_unit BOOLEAN DEFAULT true,

    -- Usage analytics
    retrieval_count INTEGER DEFAULT 0,

    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes:**

- `idx_document_chunks_document` - Document's chunks
- `idx_document_chunks_index` - Ordered chunks
- `idx_document_chunks_keywords` - GIN index for keywords search
- `idx_document_chunks_fts` - Full-text search

---

### 3. Vector Storage (Simplified)

#### `langchain_pg_embedding`

```sql
-- Enhanced existing table
ALTER TABLE langchain_pg_embedding
ADD COLUMN IF NOT EXISTS chunk_id UUID REFERENCES document_chunks(id) ON DELETE SET NULL;

-- Main structure:
-- uuid UUID PRIMARY KEY
-- embedding VECTOR(3072) -- OpenAI text-embedding-3-large
-- document TEXT -- Chunk content
-- cmetadata JSONB -- Current rich metadata
-- chunk_id UUID -- Link to document_chunks
```

**Indexes:**

- `idx_langchain_pg_embedding_vector` - HNSW vector similarity
- `idx_langchain_pg_embedding_chunk` - Chunk relationship

---

### 4. Conversation Management

#### `conversations`

```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Content
    title VARCHAR(500),
    summary TEXT,

    -- RAG configuration
    rag_mode VARCHAR(50) DEFAULT 'balanced', -- fast, balanced, quality
    category_filter TEXT[], -- Which categories to search

    -- Stats
    message_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_cost_usd DECIMAL(10,4) DEFAULT 0,

    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP,
    deleted_at TIMESTAMP
);
```

#### `messages`

```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),

    -- Content
    role VARCHAR(20) NOT NULL, -- 'user' or 'assistant'
    content TEXT NOT NULL,

    -- Sources (for assistant messages)
    sources JSONB, -- Array of source references

    -- Performance metrics
    processing_time_ms INTEGER,
    tokens_prompt INTEGER,
    tokens_completion INTEGER,
    tokens_total INTEGER,

    -- Caching
    cache_hit BOOLEAN DEFAULT false,

    -- Inline feedback
    feedback_rating INTEGER CHECK (feedback_rating >= 1 AND feedback_rating <= 5),

    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `citations`

```sql
CREATE TABLE citations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id),
    chunk_id UUID NOT NULL REFERENCES document_chunks(id),

    -- Citation info
    citation_number INTEGER NOT NULL, -- [1], [2], [3]
    citation_text TEXT, -- Snippet shown to user

    -- Relevance scores
    relevance_score DECIMAL(5,4), -- Initial vector similarity
    rerank_score DECIMAL(5,4), -- BGE reranker score

    -- User interaction
    clicked BOOLEAN DEFAULT false,

    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### 5. Analytics & Logging

#### `queries`

```sql
CREATE TABLE queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    conversation_id UUID REFERENCES conversations(id),
    message_id UUID REFERENCES messages(id),

    -- Query info
    query_text TEXT NOT NULL,
    query_hash VARCHAR(64) NOT NULL, -- For deduplication
    rag_mode VARCHAR(50),

    -- Filtering context
    categories_searched TEXT[], -- Which categories were included

    -- Performance metrics
    retrieval_count INTEGER, -- Number of chunks retrieved
    rerank_count INTEGER, -- Number of chunks reranked
    total_latency_ms INTEGER,

    -- Caching
    cache_hit BOOLEAN DEFAULT false,

    -- Cost tracking
    tokens_total INTEGER,
    estimated_cost_usd DECIMAL(10,6),

    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `feedback`

```sql
CREATE TABLE feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,

    -- Feedback content
    feedback_type VARCHAR(50) DEFAULT 'rating', -- rating, issue, suggestion
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    issues TEXT[], -- incorrect, incomplete, outdated, irrelevant

    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `user_usage_metrics`

```sql
CREATE TABLE user_usage_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),

    -- Time dimension
    date DATE NOT NULL,

    -- Usage metrics
    total_queries INTEGER DEFAULT 0,
    total_messages INTEGER DEFAULT 0,
    total_tokens BIGINT DEFAULT 0,
    total_cost_usd DECIMAL(10,4) DEFAULT 0,

    -- Usage patterns (simplified)
    categories_accessed TEXT[], -- Which categories accessed today

    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT user_usage_metrics_unique UNIQUE (user_id, date)
);
```

---

## 🔄 Migration từ v5 → v6

### Removed Components

- ❌ `document_collections` table
- ❌ `collection_documents` table
- ❌ `langchain_pg_collection` table

### Added/Modified

- ✅ `documents.category` field
- ✅ Simplified filtering logic
- ✅ Category-based search in conversations

### Migration Script

```sql
-- Add category field to documents
ALTER TABLE documents ADD COLUMN category VARCHAR(100);

-- Update categories based on existing data
UPDATE documents SET category =
    CASE
        WHEN document_name LIKE '%Hồ sơ%' OR filepath LIKE '%Ho so moi thau%' THEN 'Hồ sơ mời thầu'
        WHEN document_name LIKE '%báo cáo%' OR filepath LIKE '%Mau bao cao%' THEN 'Mẫu báo cáo'
        WHEN document_name LIKE '%câu hỏi%' OR filepath LIKE '%Cau hoi thi%' THEN 'Câu hỏi thi'
        WHEN document_type IN ('law') OR filepath LIKE '%Luat chinh%' THEN 'Luật chính'
        WHEN document_type IN ('decree', 'circular') THEN 'Quy định khác'
        ELSE 'Khác'
    END;

-- Drop collections tables
DROP TABLE IF EXISTS collection_documents CASCADE;
DROP TABLE IF EXISTS document_collections CASCADE;
```

---

## 🎯 Use Cases

### Document Filtering

```sql
-- Filter by category
SELECT * FROM documents WHERE category = 'Hồ sơ mời thầu';

-- Search in specific categories
SELECT * FROM documents WHERE category IN ('Luật chính', 'Quy định khác');
```

### RAG Pipeline

```sql
-- Search chunks in bidding documents
SELECT dc.*, d.category
FROM document_chunks dc
JOIN documents d ON d.id = dc.document_id
WHERE d.category = 'Hồ sơ mời thầu'
AND dc.content ILIKE '%đấu thầu%';
```

### Analytics

```sql
-- Most accessed categories
SELECT
    UNNEST(categories_accessed) as category,
    COUNT(*) as access_count
FROM user_usage_metrics
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY category
ORDER BY access_count DESC;
```

---

## 📈 Performance Optimizations

### Essential Indexes

```sql
-- Document filtering
CREATE INDEX idx_documents_category ON documents(category) WHERE status = 'active';
CREATE INDEX idx_documents_category_type ON documents(category, document_type);

-- Chunk search
CREATE INDEX idx_document_chunks_category ON document_chunks(document_id)
    INCLUDE (content, keywords) WHERE EXISTS (
        SELECT 1 FROM documents WHERE id = document_id AND status = 'active'
    );

-- Vector search optimization
CREATE INDEX idx_langchain_embedding_metadata_category ON langchain_pg_embedding
    USING GIN((cmetadata->'document_category'));
```

---

## 🏷️ Schema v6 Summary

| Component           | Tables        | Purpose                                    |
| ------------------- | ------------- | ------------------------------------------ |
| **User Management** | 1             | Authentication & authorization             |
| **Document System** | 2             | Document + chunk storage with categories   |
| **Vector Storage**  | 1             | Semantic search (existing langchain table) |
| **Conversations**   | 3             | Chat history + citations                   |
| **Analytics**       | 3             | Usage tracking + feedback                  |
| **Total**           | **10 tables** | **Simplified production system**           |

### Key Improvements v5 → v6

- ✅ **50% fewer tables** (12 → 10)
- ✅ **Simpler queries** - no complex JOINs
- ✅ **Better performance** - category indexes
- ✅ **Easier maintenance** - no collection management overhead
- ✅ **Focused on bidding domain** - specialized for use case

---

## 🚀 Ready for Production

Schema v6 được tối ưu cho **hệ thống đấu thầu chuyên biệt** với:

- **68 documents** hiện tại + scalable cho tương lai
- **Category-based filtering** thay vì collections phức tạp
- **Rich metadata** từ hệ thống hiện tại
- **Full RAG pipeline** support với vector search
- **Analytics** cho business intelligence

**Kết luận:** Schema v6 = Production-ready + Simple + Efficient! 🎯
