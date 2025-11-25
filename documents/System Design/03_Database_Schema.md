# Database Schema Design - RAG Bidding System

**Ngày tạo:** 24/11/2025  
**Phiên bản:** 2.0  
**Tác giả:** System Architecture Team

---

## Mục Lục

1. [Overview](#1-overview)
2. [Current Tables](#2-current-tables)
3. [Proposed New Tables](#3-proposed-new-tables)
4. [Complete Schema Diagram](#4-complete-schema-diagram)
5. [Indexes & Constraints](#5-indexes--constraints)
6. [Migration Plan](#6-migration-plan)
7. [Performance Optimization](#7-performance-optimization)

---

## 1. Overview

### 1.1. Database Information

- **Database:** PostgreSQL 18+
- **Extensions:**
  - `pgvector` 0.8.1 (vector data type, IVFFlat/HNSW)
  - `plpgsql` 1.0 (procedural language)
- **Connection:** `postgresql+psycopg://sakana:***@localhost:5432/rag_bidding_v2`
- **Current Size:** 149 MB
- **Total Documents:** 64
- **Total Chunks:** 7,892

### 1.2. Design Principles

- **Normalization:** 3NF cho metadata tables
- **Denormalization:** JSONB cho flexible metadata
- **Indexing:** B-tree cho filters, GIN cho JSONB, Vector index cho similarity search
- **Soft Delete:** Preserve audit trail
- **Timestamps:** Track creation and updates
- **UUIDs:** Globally unique identifiers
- **Foreign Keys:** Enforce referential integrity

---

## 2. Current Tables

### 2.1. Table: `documents` ⭐ PRIMARY

**Purpose:** Application-level document management

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
    created_at      TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
    updated_at      TIMESTAMP WITHOUT TIME ZONE DEFAULT now()
);
```

**Columns:**
| Column | Type | Description | Constraints |
|--------|------|-------------|-------------|
| id | UUID | Primary key | PK, NOT NULL |
| document_id | VARCHAR(255) | Unique identifier | UNIQUE, NOT NULL |
| document_name | TEXT | Document title | NOT NULL |
| category | VARCHAR(100) | Category (legal, bidding, etc.) | NOT NULL |
| document_type | VARCHAR(50) | Type (law, decree, circular, etc.) | NOT NULL |
| source_file | TEXT | Path to source file | NOT NULL |
| file_name | TEXT | Original filename | NOT NULL |
| total_chunks | INTEGER | Number of chunks | DEFAULT 0 |
| status | VARCHAR(50) | active/expired/deleted/processing | DEFAULT 'active' |
| created_at | TIMESTAMP | Creation time | DEFAULT now() |
| updated_at | TIMESTAMP | Last update time | DEFAULT now() |

**Indexes:**

```sql
CREATE INDEX idx_documents_category ON documents(category);
CREATE INDEX idx_documents_type ON documents(document_type);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_source ON documents(source_file);
CREATE INDEX idx_documents_created_at ON documents(created_at);
```

**Triggers:**

```sql
CREATE TRIGGER trigger_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_documents_updated_at();
```

**Current Data:**
| document_type | count |
|---------------|-------|
| bidding_form | 37 |
| report_template | 10 |
| law | 6 |
| exam_question | 4 |
| circular | 2 |
| decree | 2 |
| bidding | 2 |
| decision | 1 |

---

### 2.2. Table: `langchain_pg_embedding`

**Purpose:** Vector storage for semantic search

```sql
CREATE TABLE langchain_pg_embedding (
    id              VARCHAR NOT NULL PRIMARY KEY,
    collection_id   UUID REFERENCES langchain_pg_collection(uuid) ON DELETE CASCADE,
    embedding       VECTOR(3072),
    document        TEXT,
    cmetadata       JSONB
);
```

**Columns:**
| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR | Chunk ID (UUID format) |
| collection_id | UUID | FK to langchain_pg_collection |
| embedding | VECTOR(3072) | OpenAI text-embedding-3-large |
| document | TEXT | Chunk content |
| cmetadata | JSONB | Rich metadata |

**Metadata Structure (cmetadata):**

```json
{
  "chunk_id": "doc_001_chunk_005",
  "document_id": "doc_001",
  "document_type": "Law",
  "hierarchy": "[\"Chapter 1\", \"Article 5\"]",
  "level": 2,
  "section_title": "Regulations on...",
  "char_count": 850,
  "chunk_index": 5,
  "total_chunks": 45,
  "is_complete_unit": true,
  "has_table": false,
  "has_list": true,
  "extra_metadata": "{...}"
}
```

**Indexes:**

```sql
-- Primary key
CREATE UNIQUE INDEX langchain_pg_embedding_pkey ON langchain_pg_embedding(id);

-- Vector index for similarity search (auto-created by pgvector)
CREATE INDEX ON langchain_pg_embedding USING ivfflat (embedding vector_cosine_ops);
-- OR for better performance:
CREATE INDEX ON langchain_pg_embedding USING hnsw (embedding vector_cosine_ops);

-- JSONB metadata index
CREATE INDEX ix_cmetadata_gin ON langchain_pg_embedding USING gin (cmetadata jsonb_path_ops);

-- Frequently queried metadata fields
CREATE INDEX idx_embedding_document_id ON langchain_pg_embedding ((cmetadata->>'document_id'));
CREATE INDEX idx_embedding_document_type ON langchain_pg_embedding ((cmetadata->>'document_type'));
CREATE INDEX idx_embedding_chunk_index ON langchain_pg_embedding (((cmetadata->>'chunk_index')::int));
```

**Current Data:**

- Total chunks: 7,892
- Embedding dimensions: 3,072
- Average chunk size: ~850 characters

---

### 2.3. Table: `langchain_pg_collection` ⚠️ INTERNAL

**Purpose:** LangChain internal bookkeeping (DO NOT use in application)

```sql
CREATE TABLE langchain_pg_collection (
    uuid        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR,
    cmetadata   JSONB
);
```

**Note:**

- ⚠️ Managed by LangChain library
- Use `documents` table for document management
- Only 1 collection: "docs"

---

## 3. Proposed New Tables

### 3.1. Table: `users` (Future)

**Purpose:** User authentication and authorization

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username        VARCHAR(50) UNIQUE NOT NULL,
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(20) DEFAULT 'user',  -- user, manager, admin
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMP DEFAULT now(),
    updated_at      TIMESTAMP DEFAULT now(),
    last_login_at   TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_is_active ON users(is_active);
```

---

### 3.2. Table: `chat_sessions`

**Purpose:** Persistent chat session storage (migrate from Redis)

```sql
CREATE TABLE chat_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      VARCHAR(255) UNIQUE NOT NULL,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    title           TEXT,
    status          VARCHAR(20) DEFAULT 'active',  -- active, archived, deleted
    created_at      TIMESTAMP DEFAULT now(),
    updated_at      TIMESTAMP DEFAULT now(),
    last_message_at TIMESTAMP,
    message_count   INTEGER DEFAULT 0
);

CREATE INDEX idx_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX idx_sessions_status ON chat_sessions(status);
CREATE INDEX idx_sessions_created_at ON chat_sessions(created_at);
CREATE INDEX idx_sessions_last_message ON chat_sessions(last_message_at);
```

---

### 3.3. Table: `chat_messages`

**Purpose:** Store individual messages in chat sessions

```sql
CREATE TABLE chat_messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL,  -- user, assistant, system
    content         TEXT NOT NULL,
    sources         JSONB,  -- Array of source documents
    metadata        JSONB,  -- Query metadata (mode, latency, etc.)
    created_at      TIMESTAMP DEFAULT now(),

    CONSTRAINT check_role CHECK (role IN ('user', 'assistant', 'system'))
);

CREATE INDEX idx_messages_session_id ON chat_messages(session_id);
CREATE INDEX idx_messages_created_at ON chat_messages(created_at);
CREATE INDEX idx_messages_role ON chat_messages(role);
```

**Example Data:**

```json
{
  "role": "assistant",
  "content": "Thầu rộng rãi là...",
  "sources": [
    {
      "document_id": "doc_001",
      "chunk_id": "doc_001_chunk_005",
      "score": 0.89,
      "section_title": "Article 5"
    }
  ],
  "metadata": {
    "mode": "balanced",
    "latency_ms": 2345,
    "cache_hit": false,
    "reranked": true
  }
}
```

---

### 3.4. Table: `query_logs`

**Purpose:** Analytics and monitoring

```sql
CREATE TABLE query_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    session_id      UUID REFERENCES chat_sessions(id) ON DELETE SET NULL,
    query_text      TEXT NOT NULL,
    answer_text     TEXT,
    mode            VARCHAR(20),  -- fast, balanced, quality, adaptive
    filters         JSONB,
    top_k           INTEGER,
    latency_ms      INTEGER,
    cache_hit       BOOLEAN,
    cache_layer     VARCHAR(10),  -- L1, L2, L3
    sources_count   INTEGER,
    created_at      TIMESTAMP DEFAULT now(),
    ip_address      INET,
    user_agent      TEXT
);

CREATE INDEX idx_query_logs_user_id ON query_logs(user_id);
CREATE INDEX idx_query_logs_created_at ON query_logs(created_at);
CREATE INDEX idx_query_logs_mode ON query_logs(mode);
CREATE INDEX idx_query_logs_cache_hit ON query_logs(cache_hit);
CREATE INDEX idx_query_logs_latency ON query_logs(latency_ms);
```

---

### 3.5. Table: `document_upload_jobs`

**Purpose:** Track async document processing

```sql
CREATE TABLE document_upload_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id          VARCHAR(255) UNIQUE NOT NULL,
    document_id     VARCHAR(255) REFERENCES documents(document_id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    file_name       TEXT NOT NULL,
    file_size_bytes BIGINT,
    status          VARCHAR(20) DEFAULT 'queued',  -- queued, processing, completed, failed
    progress        INTEGER DEFAULT 0,  -- 0-100
    error_message   TEXT,
    started_at      TIMESTAMP,
    completed_at    TIMESTAMP,
    created_at      TIMESTAMP DEFAULT now(),

    CONSTRAINT check_progress CHECK (progress BETWEEN 0 AND 100),
    CONSTRAINT check_status CHECK (status IN ('queued', 'processing', 'completed', 'failed'))
);

CREATE INDEX idx_jobs_document_id ON document_upload_jobs(document_id);
CREATE INDEX idx_jobs_status ON document_upload_jobs(status);
CREATE INDEX idx_jobs_created_at ON document_upload_jobs(created_at);
```

---

### 3.6. Table: `api_keys`

**Purpose:** API key management

```sql
CREATE TABLE api_keys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    key_hash        VARCHAR(255) UNIQUE NOT NULL,
    key_prefix      VARCHAR(10) NOT NULL,  -- First 8 chars for identification
    name            VARCHAR(100),
    scopes          JSONB,  -- Permissions
    rate_limit      INTEGER DEFAULT 1000,  -- Requests per hour
    is_active       BOOLEAN DEFAULT true,
    expires_at      TIMESTAMP,
    last_used_at    TIMESTAMP,
    created_at      TIMESTAMP DEFAULT now(),

    CONSTRAINT check_rate_limit CHECK (rate_limit > 0)
);

CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_is_active ON api_keys(is_active);
```

---

### 3.7. Table: `feedback`

**Purpose:** User feedback on answers

```sql
CREATE TABLE feedback (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    query_log_id    UUID REFERENCES query_logs(id) ON DELETE CASCADE,
    rating          INTEGER CHECK (rating BETWEEN 1 AND 5),
    feedback_type   VARCHAR(20),  -- helpful, incorrect, incomplete, etc.
    comment         TEXT,
    created_at      TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_feedback_user_id ON feedback(user_id);
CREATE INDEX idx_feedback_query_log_id ON feedback(query_log_id);
CREATE INDEX idx_feedback_rating ON feedback(rating);
CREATE INDEX idx_feedback_created_at ON feedback(created_at);
```

---

### 3.8. Table: `document_versions`

**Purpose:** Track document changes over time

```sql
CREATE TABLE document_versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     VARCHAR(255) REFERENCES documents(document_id) ON DELETE CASCADE,
    version_number  INTEGER NOT NULL,
    source_file     TEXT NOT NULL,
    total_chunks    INTEGER,
    changes_summary TEXT,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMP DEFAULT now(),

    UNIQUE(document_id, version_number)
);

CREATE INDEX idx_versions_document_id ON document_versions(document_id);
CREATE INDEX idx_versions_created_at ON document_versions(created_at);
```

---

## 4. Complete Schema Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                     DATABASE SCHEMA v2.0                             │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────┐         ┌──────────────────┐         ┌──────────────┐
│    users     │         │ chat_sessions    │         │  api_keys    │
├──────────────┤         ├──────────────────┤         ├──────────────┤
│ id (PK)      │←────┐   │ id (PK)          │         │ id (PK)      │
│ username     │     │   │ session_id       │         │ user_id (FK) │
│ email        │     └───│ user_id (FK)     │         │ key_hash     │
│ password_hash│         │ title            │         │ scopes       │
│ role         │         │ status           │         └──────────────┘
│ is_active    │         │ created_at       │
└──────────────┘         └──────────────────┘
      │                           │
      │                           │
      ▼                           ▼
┌──────────────┐         ┌──────────────────┐
│ query_logs   │         │ chat_messages    │
├──────────────┤         ├──────────────────┤
│ id (PK)      │         │ id (PK)          │
│ user_id (FK) │         │ session_id (FK)  │
│ query_text   │         │ role             │
│ mode         │         │ content          │
│ latency_ms   │         │ sources (JSONB)  │
│ cache_hit    │         │ metadata (JSONB) │
└──────────────┘         └──────────────────┘
      │
      │
      ▼
┌──────────────┐
│  feedback    │
├──────────────┤
│ id (PK)      │
│ query_log_id │
│ rating       │
│ comment      │
└──────────────┘

┌────────────────────┐         ┌──────────────────────────┐
│    documents       │         │ langchain_pg_embedding   │
├────────────────────┤         ├──────────────────────────┤
│ id (PK)            │    ┌────│ id (PK)                  │
│ document_id (UK)   │◄───┘    │ collection_id (FK)       │
│ document_name      │   (via  │ embedding (VECTOR)       │
│ category           │ JSONB)  │ document (TEXT)          │
│ document_type      │         │ cmetadata (JSONB) ──┐    │
│ source_file        │         │  - document_id      │    │
│ total_chunks       │         │  - chunk_id         │    │
│ status             │         │  - document_type    │    │
└────────────────────┘         │  - hierarchy        │    │
      │                        │  - section_title    │    │
      │                        └──────────────────────────┘
      ▼                                   │
┌────────────────────┐                   │
│document_versions   │                   ▼
├────────────────────┤         ┌──────────────────────┐
│ id (PK)            │         │langchain_pg_collection│
│ document_id (FK)   │         ├──────────────────────┤
│ version_number     │         │ uuid (PK)            │
│ source_file        │         │ name                 │
│ changes_summary    │         │ cmetadata (JSONB)    │
└────────────────────┘         └──────────────────────┘
      │
      │
      ▼
┌────────────────────┐
│document_upload_jobs│
├────────────────────┤
│ id (PK)            │
│ document_id (FK)   │
│ status             │
│ progress           │
│ error_message      │
└────────────────────┘

LEGEND:
  ────  One-to-Many relationship
  (PK)  Primary Key
  (FK)  Foreign Key
  (UK)  Unique Key
```

---

## 5. Indexes & Constraints

### 5.1. Primary Indexes (Auto-created)

- All tables have UUID primary keys với B-tree index
- Unique constraints có implicit indexes

### 5.2. Foreign Key Indexes

```sql
-- Chat sessions
CREATE INDEX idx_sessions_user_id ON chat_sessions(user_id);

-- Chat messages
CREATE INDEX idx_messages_session_id ON chat_messages(session_id);

-- Query logs
CREATE INDEX idx_query_logs_user_id ON query_logs(user_id);
CREATE INDEX idx_query_logs_session_id ON query_logs(session_id);

-- Document upload jobs
CREATE INDEX idx_jobs_document_id ON document_upload_jobs(document_id);

-- API keys
CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);

-- Feedback
CREATE INDEX idx_feedback_query_log_id ON feedback(query_log_id);

-- Document versions
CREATE INDEX idx_versions_document_id ON document_versions(document_id);
```

### 5.3. Query Optimization Indexes

```sql
-- Frequently filtered columns
CREATE INDEX idx_documents_status_type ON documents(status, document_type);
CREATE INDEX idx_sessions_user_status ON chat_sessions(user_id, status);
CREATE INDEX idx_query_logs_date_mode ON query_logs(created_at, mode);

-- Full-text search (future)
CREATE INDEX idx_documents_name_fts ON documents USING gin(to_tsvector('english', document_name));
```

### 5.4. Vector Index Tuning

```sql
-- HNSW recommended for production (better performance)
CREATE INDEX idx_embedding_hnsw
ON langchain_pg_embedding
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- IVFFlat for smaller datasets
CREATE INDEX idx_embedding_ivfflat
ON langchain_pg_embedding
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

---

## 6. Migration Plan

### 6.1. Phase 1: User Management (v2.1)

```sql
-- Step 1: Create users table
CREATE TABLE users (...);

-- Step 2: Migrate existing implicit users
INSERT INTO users (username, email, role)
SELECT DISTINCT
    COALESCE(session_metadata->>'user', 'anonymous'),
    COALESCE(session_metadata->>'email', 'unknown@example.com'),
    'user'
FROM redis_chat_sessions;  -- Export from Redis

-- Step 3: Add user_id to existing tables
ALTER TABLE query_logs ADD COLUMN user_id UUID REFERENCES users(id);
```

### 6.2. Phase 2: Chat Session Migration (v2.2)

```sql
-- Step 1: Create tables
CREATE TABLE chat_sessions (...);
CREATE TABLE chat_messages (...);

-- Step 2: Migrate from Redis to PostgreSQL
-- Python script: scripts/migration/migrate_redis_to_postgres.py

-- Step 3: Deprecate Redis DB 1
-- Keep Redis DB 0 for caching only
```

### 6.3. Phase 3: Analytics & Monitoring (v2.3)

```sql
-- Create tables
CREATE TABLE query_logs (...);
CREATE TABLE feedback (...);

-- Start logging all queries
-- Enable feedback UI
```

### 6.4. Phase 4: Document Versioning (v2.4)

```sql
CREATE TABLE document_versions (...);
CREATE TABLE document_upload_jobs (...);

-- Backfill existing documents as version 1
INSERT INTO document_versions (document_id, version_number, source_file, total_chunks)
SELECT document_id, 1, source_file, total_chunks
FROM documents;
```

---

## 7. Performance Optimization

### 7.1. Connection Pooling

```sql
-- pgBouncer configuration
[databases]
rag_bidding_v2 = host=localhost port=5432 dbname=rag_bidding_v2

[pgbouncer]
pool_mode = transaction
max_client_conn = 100
default_pool_size = 20
```

### 7.2. Query Optimization

```sql
-- Use EXPLAIN ANALYZE to tune queries
EXPLAIN ANALYZE
SELECT * FROM langchain_pg_embedding
WHERE cmetadata->>'document_type' = 'law'
ORDER BY embedding <=> '[...]'::vector
LIMIT 10;

-- Materialize frequent filters
CREATE MATERIALIZED VIEW mv_law_chunks AS
SELECT * FROM langchain_pg_embedding
WHERE cmetadata->>'document_type' = 'law';

CREATE INDEX ON mv_law_chunks USING hnsw (embedding vector_cosine_ops);
```

### 7.3. Partitioning (Future)

```sql
-- Partition chat_messages by created_at
CREATE TABLE chat_messages (
    ...
) PARTITION BY RANGE (created_at);

CREATE TABLE chat_messages_2025_q4 PARTITION OF chat_messages
    FOR VALUES FROM ('2025-10-01') TO ('2026-01-01');

CREATE TABLE chat_messages_2026_q1 PARTITION OF chat_messages
    FOR VALUES FROM ('2026-01-01') TO ('2026-04-01');
```

### 7.4. Vacuum & Analyze

```sql
-- Regular maintenance
VACUUM ANALYZE documents;
VACUUM ANALYZE langchain_pg_embedding;
REINDEX INDEX CONCURRENTLY idx_embedding_hnsw;
```

---

## Tài Liệu Liên Quan

- `01_System_Specification.md` - Đặc tả hệ thống
- `02_Use_Cases.md` - Use cases chi tiết
- `/temp/database_schema_explained.txt` - Current schema reference
