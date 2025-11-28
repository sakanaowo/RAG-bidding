# Database Schema v3.0 - RAG Bidding System

**Ngày cập nhật:** 27/11/2025  
**Phiên bản:** 3.0  
**Tác giả:** System Architecture Team  
**Based on:** Perplexity, ChatGPT Enterprise, Notion best practices

> 📌 **IMPORTANT:** This is the OFFICIAL schema v3.0 proposal
> 
> **Detailed Design:** See `10_Analysis_Design_Report.md` for:
> - Full use case analysis (50 use cases)
> - PlantUML class diagrams
> - Complete terminology (50 terms)
> - Migration roadmap (5 phases, 8 weeks)

---

## Quick Navigation

1. [Schema Overview](#1-schema-overview)
2. [Current Tables (v2.0)](#2-current-tables-v20)
3. [New Tables (v3.0)](#3-new-tables-v30)
4. [Migration Strategy](#4-migration-strategy)
5. [Performance Improvements](#5-performance-improvements)

---

## 1. Schema Overview

### 1.1. Current State (Production)

**Database:** PostgreSQL 18.1  
**Extension:** pgvector 0.8.1  
**Size:** 149 MB  
**Documents:** 64  
**Chunks:** 7,892  
**Alembic Baseline:** 0dd6951d6844 (stamped Nov 27, 2025)

**Existing Tables (3):**
- ✅ `documents` - Document metadata
- ✅ `langchain_pg_embedding` - Vector storage (VECTOR 3072)
- ✅ `langchain_pg_collection` - LangChain internal

### 1.2. Proposed v3.0 Architecture

**New Tables (14):**

**User Management (2 tables):**
1. `users` - Authentication & profiles
2. `api_keys` - API key management

**Conversations (3 tables):**
3. `conversations` - Chat sessions
4. `messages` - Chat messages
5. `citations` - Source tracking

**Documents Advanced (4 tables):**
6. `document_chunks` - Chunk metadata
7. `document_versions` - Version control
8. `document_collections` - Collections
9. `collection_documents` - M:N junction

**Analytics & Features (5 tables):**
10. `queries` - Query analytics
11. `feedback` - User feedback
12. `bookmarks` - Saved Q&A
13. `search_filters` - Saved searches
14. `usage_metrics` - Aggregated metrics

**Total:** 17 tables (3 existing + 14 new)

---

## 2. Current Tables (v2.0)

### 2.1. `documents` - Document Metadata

```sql
CREATE TABLE documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     VARCHAR(255) UNIQUE NOT NULL,
    document_name   TEXT NOT NULL,
    category        VARCHAR(100) NOT NULL,
    document_type   VARCHAR(50) NOT NULL,
    source_file     TEXT NOT NULL,
    file_name       TEXT NOT NULL,
    total_chunks    INTEGER DEFAULT 0,
    status          VARCHAR(50) DEFAULT 'active',
    created_at      TIMESTAMP DEFAULT now(),
    updated_at      TIMESTAMP DEFAULT now()
);

-- Indexes
CREATE INDEX idx_documents_category ON documents(category);
CREATE INDEX idx_documents_type ON documents(document_type);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_created ON documents(created_at DESC);
```

**Current Data:**
- 64 documents
- 8 types: law, decree, bidding_form, report, etc.
- Status: active (default), expired, archived, deleted

### 2.2. `langchain_pg_embedding` - Vector Storage

```sql
CREATE TABLE langchain_pg_embedding (
    id              VARCHAR(255) PRIMARY KEY,
    collection_id   UUID REFERENCES langchain_pg_collection(uuid),
    document        TEXT,
    cmetadata       JSONB,
    embedding       VECTOR(3072)
);

-- Indexes
CREATE INDEX idx_embedding_collection ON langchain_pg_embedding(collection_id);
CREATE INDEX idx_embedding_metadata ON langchain_pg_embedding USING gin(cmetadata);
CREATE INDEX idx_embedding_vector ON langchain_pg_embedding 
    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
```

**Current Data:**
- 7,892 chunks
- Embedding model: text-embedding-3-large (3072 dim)
- Metadata: document_id, chunk_index, section_title, hierarchy, etc.

### 2.3. `langchain_pg_collection` - LangChain Internal

```sql
CREATE TABLE langchain_pg_collection (
    uuid        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(255) UNIQUE,
    cmetadata   JSONB
);
```

**⚠️ DO NOT MODIFY:** LangChain managed table

---

## 3. New Tables (v3.0)

> **Detailed Schema:** See `temp/proposed_schema_v3.md` for full DDL with all columns, indexes, and constraints

### 3.1. User Management

**Table: `users`**
- Purpose: User authentication, profiles, preferences
- Key Fields: email, username, role, oauth_provider, preferences (JSONB)
- Features: RBAC (admin/manager/staff/user), multi-tenant support

**Table: `api_keys`**
- Purpose: API authentication, rate limiting
- Key Fields: key_hash, scopes[], rate_limit_rpm, usage tracking
- Features: Granular permissions, cost tracking per key

### 3.2. Conversations

**Table: `conversations`**
- Purpose: Multi-turn chat sessions (like ChatGPT)
- Key Fields: title, rag_mode, filters, is_public, share_url
- Features: Session sharing, model config per conversation

**Table: `messages`**
- Purpose: Individual messages (user/assistant)
- Key Fields: role, content, sources (JSONB), confidence_score
- Features: Feedback tracking, cache hit monitoring

**Table: `citations`**
- Purpose: Explicit source attribution (like Perplexity)
- Key Fields: document_id, chunk_id, rerank_score, clicked
- Features: Citation click tracking, relevance scores

### 3.3. Documents Advanced

**Table: `document_chunks`**
- Purpose: Denormalized chunk metadata (faster queries)
- Key Fields: chunk_id, content, keywords, retrieval_count
- Features: Usage statistics, quality metrics

**Table: `document_versions`**
- Purpose: Git-like version control
- Key Fields: version_number, is_current, diff_stats
- Features: Compare versions, rollback

**Table: `document_collections`**
- Purpose: Group documents (like Notion)
- Key Fields: name, auto_include_rules (JSONB), is_public
- Features: Smart filters, team sharing

**Table: `collection_documents`**
- Purpose: M:N junction for collections
- Key Fields: collection_id, document_id, sort_order

### 3.4. Analytics & Features

**Table: `queries`**
- Purpose: Query logging & analytics
- Key Fields: query_text, latency_ms, tokens_total, estimated_cost_usd
- Features: Performance tracking, cost analysis

**Table: `feedback`**
- Purpose: User feedback system
- Key Fields: rating (1-5), issues[], comment, resolved
- Features: Quality improvement workflow

**Table: `bookmarks`**
- Purpose: Save Q&A pairs
- Key Fields: title, notes, tags[], folder_path, is_favorite
- Features: Organization, sharing

**Table: `search_filters`**
- Purpose: Saved search configurations
- Key Fields: name, filters (JSONB), is_default
- Features: Quick access, sharing

**Table: `usage_metrics`**
- Purpose: Pre-aggregated analytics
- Key Fields: date, hour, total_queries, avg_latency, total_cost
- Features: Dashboard data, performance trends

---

## 4. Migration Strategy

### 4.1. 5-Phase Roadmap

**Phase 1: User & Auth (v3.1)** - 2 weeks
```sql
-- Create tables
CREATE TABLE users (...);
CREATE TABLE api_keys (...);

-- Alembic migration
alembic revision --autogenerate -m "Add user management"
alembic upgrade head
```

**Phase 2: Conversations (v3.2)** - 2 weeks
```sql
-- Create tables
CREATE TABLE conversations (...);
CREATE TABLE messages (...);
CREATE TABLE citations (...);

-- Migrate from Redis
-- python scripts/migration/migrate_redis_to_postgres.py
```

**Phase 3: Analytics (v3.3)** - 1 week
```sql
CREATE TABLE queries (...);
CREATE TABLE usage_metrics (...);

-- Start logging
-- Update answer() function to log all queries
```

**Phase 4: Document Advanced (v3.4)** - 2 weeks
```sql
CREATE TABLE document_chunks (...);
CREATE TABLE document_versions (...);
CREATE TABLE document_collections (...);
CREATE TABLE collection_documents (...);

-- Backfill chunks
-- python scripts/migration/backfill_document_chunks.py
```

**Phase 5: User Features (v3.5)** - 1 week
```sql
CREATE TABLE feedback (...);
CREATE TABLE bookmarks (...);
CREATE TABLE search_filters (...);
```

**Total Timeline:** 8 weeks

### 4.2. Alembic Commands

```bash
# Generate migration
alembic revision --autogenerate -m "Schema v3.1 - User management"

# Review generated migration
cat alembic/versions/[timestamp]_schema_v31_user_management.py

# Apply migration
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

### 4.3. Data Migration Scripts

**Location:** `scripts/migration/`

- `migrate_redis_to_postgres.py` - Chat sessions
- `backfill_document_chunks.py` - Chunk metadata
- `generate_initial_metrics.py` - Historical analytics

---

## 5. Performance Improvements

### 5.1. Expected Impact

**Chunk Queries:**
- Before: Join embedding table, parse JSONB (~200ms)
- After: Direct query document_chunks (~100ms)
- **Improvement:** 50% faster

**Analytics:**
- Before: Aggregate from queries table (~5s)
- After: Query usage_metrics (~500ms)
- **Improvement:** 10x faster

**Cache Hit Rate:**
- Current: 80% (L1 + L2)
- Target: 90% (with better tracking)
- **Improvement:** +10-15%

### 5.2. Indexing Strategy

**Composite Indexes:**
```sql
-- Conversations
CREATE INDEX idx_conv_user_recent 
    ON conversations(user_id, last_message_at DESC);

-- Messages
CREATE INDEX idx_msg_conv_time 
    ON messages(conversation_id, created_at);

-- Citations
CREATE INDEX idx_cite_doc_score 
    ON citations(document_id, final_score DESC);

-- Queries
CREATE INDEX idx_query_user_time 
    ON queries(user_id, created_at DESC);
```

**Partial Indexes:**
```sql
-- Active users only
CREATE INDEX idx_users_active 
    ON users(email) WHERE is_active = true;

-- Current document versions
CREATE INDEX idx_versions_current 
    ON document_versions(document_id) WHERE is_current = true;

-- Unresolved feedback
CREATE INDEX idx_feedback_unresolved 
    ON feedback(created_at) WHERE resolved = false;
```

### 5.3. Partitioning (Future)

**Time-based Partitioning:**
```sql
-- Partition queries by month
CREATE TABLE queries_2025_11 PARTITION OF queries
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');

-- Partition messages by quarter
CREATE TABLE messages_2025_q4 PARTITION OF messages
    FOR VALUES FROM ('2025-10-01') TO ('2026-01-01');
```

**Benefits:**
- Faster queries (scan less data)
- Easier archival (drop old partitions)
- Better maintenance (vacuum specific partitions)

---

## 6. Quick Reference

### 6.1. Table Categories

| Category | Tables | Count |
|----------|--------|-------|
| **Current (v2.0)** | documents, langchain_pg_embedding, langchain_pg_collection | 3 |
| **User Mgmt** | users, api_keys | 2 |
| **Conversations** | conversations, messages, citations | 3 |
| **Documents** | document_chunks, document_versions, document_collections, collection_documents | 4 |
| **Analytics** | queries, feedback, bookmarks, search_filters, usage_metrics | 5 |
| **TOTAL** | | **17** |

### 6.2. Key Relationships

```
users (1) ─── (N) conversations ─── (N) messages ─── (N) citations ─── (1) documents
  │                                      │
  ├─── (N) api_keys                      └─── (N) queries
  ├─── (N) bookmarks                     
  └─── (N) search_filters

documents (1) ─── (N) document_chunks ─── (1) embeddings
          │
          ├─── (N) document_versions
          └─── (M:N) document_collections
```

### 6.3. Migration Checklist

- [ ] **Phase 1:** User management (2 weeks)
  - [ ] Create users, api_keys tables
  - [ ] Implement JWT authentication
  - [ ] Migrate implicit users
  
- [ ] **Phase 2:** Conversations (2 weeks)
  - [ ] Create conversations, messages, citations tables
  - [ ] Migrate Redis sessions to PostgreSQL
  - [ ] Implement sharing features
  
- [ ] **Phase 3:** Analytics (1 week)
  - [ ] Create queries, usage_metrics tables
  - [ ] Start query logging
  - [ ] Build dashboard
  
- [ ] **Phase 4:** Document Advanced (2 weeks)
  - [ ] Create document_chunks, versions, collections tables
  - [ ] Backfill chunk metadata
  - [ ] Implement version control
  
- [ ] **Phase 5:** User Features (1 week)
  - [ ] Create feedback, bookmarks, search_filters tables
  - [ ] Implement bookmark system
  - [ ] Saved filter UI

---

## 7. Related Documents

- **`10_Analysis_Design_Report.md`** - Full design analysis with use cases, class diagrams, terminology
- **`temp/proposed_schema_v3.md`** - Detailed schema with full DDL, JSONB structures, examples
- **`06_SQLAlchemy_Implementation.md`** - ORM usage guide
- **`07_SQLAlchemy_Roadmap.md`** - Implementation phases

**Last Updated:** November 27, 2025  
**Status:** ✅ v2.0 Production | ⏳ v3.0 Proposed  
**Next Review:** After team feedback
