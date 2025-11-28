# 🗄️ Proposed Database Schema v3.0 - RAG Bidding System

**Date:** November 27, 2025  
**Based on:** Current schema (documents + embeddings) + Industry best practices  
**References:** Perplexity, You.com, ChatGPT Enterprise, LangChain patterns

---

## 📊 Schema Overview

### Current Foundation (Existing - KEEP)
- ✅ `documents` - Document metadata management
- ✅ `langchain_pg_embedding` - Vector storage with JSONB metadata
- ✅ `langchain_pg_collection` - LangChain internal (DO NOT TOUCH)

### Proposed New Tables (v3.0)

**Core RAG Features:**
1. `users` - User management & authentication
2. `conversations` - Multi-turn chat sessions
3. `messages` - Individual messages in conversations
4. `queries` - Query analytics & logging
5. `citations` - Source tracking per answer

**Document Management:**
6. `document_chunks` - Explicit chunk metadata (denormalized from embedding)
7. `document_versions` - Version control for documents
8. `document_collections` - Group documents into collections

**Advanced Features:**
9. `feedback` - User feedback on answers
10. `bookmarks` - Save useful Q&A pairs
11. `search_filters` - Saved search preferences
12. `api_keys` - API authentication
13. `usage_metrics` - Analytics aggregation

---

## 🏗️ Detailed Schema Design

### 1. Table: `users`

**Purpose:** User authentication & profile management (like ChatGPT Enterprise)

```sql
CREATE TABLE users (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email               VARCHAR(255) UNIQUE NOT NULL,
    username            VARCHAR(100) UNIQUE,
    password_hash       VARCHAR(255),  -- For local auth
    full_name           VARCHAR(255),
    avatar_url          TEXT,
    
    -- OAuth support
    oauth_provider      VARCHAR(50),   -- 'google', 'microsoft', 'github'
    oauth_id            VARCHAR(255),
    
    -- Role-based access
    role                VARCHAR(50) DEFAULT 'user',  -- user, manager, admin, analyst
    organization_id     UUID,  -- For multi-tenant support
    
    -- Preferences
    preferences         JSONB DEFAULT '{}',  -- UI settings, default filters, etc.
    
    -- Usage tracking
    query_count         INTEGER DEFAULT 0,
    last_active_at      TIMESTAMP,
    
    -- Status
    is_active           BOOLEAN DEFAULT true,
    is_verified         BOOLEAN DEFAULT false,
    email_verified_at   TIMESTAMP,
    
    -- Audit
    created_at          TIMESTAMP DEFAULT now(),
    updated_at          TIMESTAMP DEFAULT now(),
    deleted_at          TIMESTAMP  -- Soft delete
);

-- Indexes
CREATE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_org ON users(organization_id);
CREATE INDEX idx_users_last_active ON users(last_active_at);
CREATE INDEX idx_users_oauth ON users(oauth_provider, oauth_id);

-- Preferences JSONB structure
{
  "theme": "dark",
  "language": "vi",
  "default_rag_mode": "balanced",
  "show_sources": true,
  "default_filters": {
    "document_types": ["law", "decree"],
    "date_range": "last_2_years"
  },
  "notifications": {
    "email": true,
    "new_documents": true
  }
}
```

**Use Cases:**
- UC-19: User Registration & Login
- UC-20: Profile Management
- UC-21: Multi-tenant Organization Management

---

### 2. Table: `conversations`

**Purpose:** Multi-turn chat sessions (like ChatGPT, Perplexity)

```sql
CREATE TABLE conversations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Metadata
    title               TEXT,  -- Auto-generated or user-edited
    summary             TEXT,  -- AI-generated summary
    
    -- Configuration
    rag_mode            VARCHAR(20) DEFAULT 'balanced',  -- fast, balanced, quality, adaptive
    model_config        JSONB,  -- LLM settings, temperature, etc.
    
    -- Filters applied to this conversation
    filters             JSONB DEFAULT '{}',  -- document_types, date_range, etc.
    
    -- Statistics
    message_count       INTEGER DEFAULT 0,
    total_tokens        INTEGER DEFAULT 0,
    avg_response_time   INTEGER,  -- milliseconds
    
    -- Sharing & Collaboration
    is_public           BOOLEAN DEFAULT false,
    share_url           VARCHAR(255) UNIQUE,  -- For public sharing
    shared_with         UUID[],  -- Array of user IDs
    
    -- Status
    status              VARCHAR(20) DEFAULT 'active',  -- active, archived, deleted
    pinned              BOOLEAN DEFAULT false,
    tags                TEXT[],  -- User-defined tags
    
    -- Audit
    created_at          TIMESTAMP DEFAULT now(),
    updated_at          TIMESTAMP DEFAULT now(),
    last_message_at     TIMESTAMP,
    archived_at         TIMESTAMP,
    deleted_at          TIMESTAMP
);

-- Indexes
CREATE INDEX idx_conv_user_id ON conversations(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_conv_status ON conversations(status);
CREATE INDEX idx_conv_last_msg ON conversations(last_message_at DESC);
CREATE INDEX idx_conv_share_url ON conversations(share_url) WHERE is_public = true;
CREATE INDEX idx_conv_tags ON conversations USING gin(tags);

-- Partition by created_at (for large datasets)
-- CREATE TABLE conversations_2025_q4 PARTITION OF conversations
--     FOR VALUES FROM ('2025-10-01') TO ('2026-01-01');

-- Model config JSONB structure
{
  "llm": "gpt-4o-mini",
  "temperature": 0.1,
  "max_tokens": 2000,
  "top_p": 0.95,
  "reranking_enabled": true,
  "reranker_top_k": 5,
  "retrieval_top_k": 20
}

-- Filters JSONB structure
{
  "document_types": ["law", "decree", "circular"],
  "date_range": {
    "from": "2023-01-01",
    "to": "2025-12-31"
  },
  "categories": ["legal"],
  "status": ["active"],
  "exclude_docs": ["doc_123"]
}
```

**Use Cases:**
- UC-4: Create Chat Session
- UC-5: Continue Chat Conversation
- UC-6: Manage Chat History
- UC-22: Share Conversation (NEW)
- UC-23: Collaborate on Research (NEW)

---

### 3. Table: `messages`

**Purpose:** Individual messages in conversations (like ChatGPT message history)

```sql
CREATE TABLE messages (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id     UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id             UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Message content
    role                VARCHAR(20) NOT NULL,  -- user, assistant, system
    content             TEXT NOT NULL,
    content_type        VARCHAR(20) DEFAULT 'text',  -- text, markdown, code
    
    -- For assistant messages
    sources             JSONB,  -- Array of source citations
    confidence_score    FLOAT,  -- 0.0-1.0
    
    -- Processing metadata
    processing_time_ms  INTEGER,
    tokens_used         INTEGER,
    cache_hit           BOOLEAN DEFAULT false,
    cache_layer         VARCHAR(10),  -- L1, L2, L3
    
    -- RAG pipeline details
    retrieval_metadata  JSONB,  -- Query enhancement, vector search results
    reranking_metadata  JSONB,  -- Reranking scores, methods used
    
    -- User interaction
    feedback            VARCHAR(20),  -- thumbs_up, thumbs_down, null
    feedback_comment    TEXT,
    is_edited           BOOLEAN DEFAULT false,
    edit_history        JSONB[],  -- Array of previous versions
    
    -- Status
    is_error            BOOLEAN DEFAULT false,
    error_message       TEXT,
    retry_count         INTEGER DEFAULT 0,
    
    -- Audit
    created_at          TIMESTAMP DEFAULT now(),
    updated_at          TIMESTAMP DEFAULT now(),
    deleted_at          TIMESTAMP
);

-- Indexes
CREATE INDEX idx_msg_conversation ON messages(conversation_id, created_at);
CREATE INDEX idx_msg_user ON messages(user_id);
CREATE INDEX idx_msg_role ON messages(role);
CREATE INDEX idx_msg_feedback ON messages(feedback) WHERE feedback IS NOT NULL;
CREATE INDEX idx_msg_cache ON messages(cache_hit, cache_layer);

-- GIN index for sources JSONB
CREATE INDEX idx_msg_sources_gin ON messages USING gin(sources jsonb_path_ops);

-- Sources JSONB structure
[
  {
    "document_id": "doc_001",
    "chunk_id": "doc_001_chunk_005",
    "chunk_index": 5,
    "content": "Thầu rộng rãi là...",
    "section_title": "Điều 5. Hình thức đấu thầu",
    "document_name": "Luật đấu thầu 2023",
    "document_type": "law",
    "relevance_score": 0.89,
    "rerank_score": 0.95,
    "distance": 0.234,
    "used_in_answer": true
  }
]

-- Retrieval metadata JSONB
{
  "query_original": "thầu rộng rãi là gì",
  "query_enhanced": [
    "định nghĩa thầu rộng rãi",
    "hình thức đấu thầu rộng rãi",
    "điều kiện áp dụng thầu rộng rãi"
  ],
  "enhancement_method": "multi_query",
  "vector_search": {
    "top_k": 20,
    "filters_applied": ["document_type=law"],
    "search_time_ms": 45
  },
  "reranking": {
    "enabled": true,
    "model": "bge-reranker-v2-m3",
    "rerank_time_ms": 120,
    "scores_before": [0.78, 0.75, 0.72],
    "scores_after": [0.95, 0.89, 0.85]
  }
}
```

**Use Cases:**
- UC-1: Ask Simple Question
- UC-2: Ask with Context
- UC-3: Advanced Query with Filters
- UC-24: Review Source Citations (NEW)
- UC-25: Provide Feedback on Answer (NEW)

---

### 4. Table: `queries`

**Purpose:** Analytics & monitoring (like Perplexity analytics dashboard)

```sql
CREATE TABLE queries (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID REFERENCES users(id) ON DELETE SET NULL,
    conversation_id     UUID REFERENCES conversations(id) ON DELETE SET NULL,
    message_id          UUID REFERENCES messages(id) ON DELETE SET NULL,
    
    -- Query details
    query_text          TEXT NOT NULL,
    query_hash          VARCHAR(64),  -- MD5 hash for deduplication
    query_language      VARCHAR(10) DEFAULT 'vi',
    
    -- Classification
    query_type          VARCHAR(50),  -- definition, comparison, how_to, etc.
    query_intent        VARCHAR(50),  -- informational, navigational, transactional
    query_complexity    VARCHAR(20),  -- simple, medium, complex
    
    -- RAG configuration
    rag_mode            VARCHAR(20),
    filters_applied     JSONB,
    
    -- Results
    answer_text         TEXT,
    sources_count       INTEGER,
    chunks_retrieved    INTEGER,
    chunks_reranked     INTEGER,
    
    -- Performance metrics
    total_latency_ms    INTEGER,
    embedding_time_ms   INTEGER,
    search_time_ms      INTEGER,
    rerank_time_ms      INTEGER,
    llm_time_ms         INTEGER,
    
    -- Cache performance
    cache_hit           BOOLEAN,
    cache_layer         VARCHAR(10),
    cache_key           VARCHAR(255),
    
    -- Quality metrics
    answer_length       INTEGER,
    confidence_score    FLOAT,
    user_feedback       VARCHAR(20),
    feedback_score      INTEGER,  -- 1-5 stars
    
    -- Cost tracking
    tokens_prompt       INTEGER,
    tokens_completion   INTEGER,
    tokens_total        INTEGER,
    estimated_cost_usd  DECIMAL(10, 6),
    
    -- Context
    user_agent          TEXT,
    ip_address          INET,
    session_id          VARCHAR(255),
    referrer            TEXT,
    
    -- Status
    is_successful       BOOLEAN DEFAULT true,
    error_type          VARCHAR(100),
    error_message       TEXT,
    
    -- Audit
    created_at          TIMESTAMP DEFAULT now(),
    updated_at          TIMESTAMP DEFAULT now()
);

-- Indexes
CREATE INDEX idx_queries_user ON queries(user_id, created_at DESC);
CREATE INDEX idx_queries_conv ON queries(conversation_id);
CREATE INDEX idx_queries_hash ON queries(query_hash);
CREATE INDEX idx_queries_created ON queries(created_at DESC);
CREATE INDEX idx_queries_rag_mode ON queries(rag_mode);
CREATE INDEX idx_queries_cache ON queries(cache_hit, cache_layer);
CREATE INDEX idx_queries_feedback ON queries(user_feedback) WHERE user_feedback IS NOT NULL;

-- GIN index for filters
CREATE INDEX idx_queries_filters_gin ON queries USING gin(filters_applied jsonb_path_ops);

-- Partial index for errors
CREATE INDEX idx_queries_errors ON queries(error_type, created_at) WHERE is_successful = false;

-- Materialized view for analytics
CREATE MATERIALIZED VIEW query_analytics_daily AS
SELECT 
    date_trunc('day', created_at) as date,
    rag_mode,
    COUNT(*) as total_queries,
    AVG(total_latency_ms) as avg_latency,
    AVG(confidence_score) as avg_confidence,
    SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END)::FLOAT / COUNT(*) as cache_hit_rate,
    SUM(tokens_total) as total_tokens,
    SUM(estimated_cost_usd) as total_cost
FROM queries
WHERE is_successful = true
GROUP BY date, rag_mode;

CREATE UNIQUE INDEX ON query_analytics_daily(date, rag_mode);
```

**Use Cases:**
- UC-14: View System Metrics
- UC-15: Monitor Performance
- UC-26: Analytics Dashboard (NEW)
- UC-27: Cost Tracking (NEW)
- UC-28: Query Pattern Analysis (NEW)

---

### 5. Table: `citations`

**Purpose:** Explicit source tracking (inspired by Perplexity's citation system)

```sql
CREATE TABLE citations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id          UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    query_id            UUID REFERENCES queries(id) ON DELETE SET NULL,
    
    -- Source document
    document_id         VARCHAR(255) NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    chunk_id            VARCHAR(255) NOT NULL,  -- From langchain_pg_embedding
    chunk_index         INTEGER,
    
    -- Citation details
    citation_number     INTEGER,  -- [1], [2], [3] in answer
    citation_text       TEXT,  -- Excerpt used
    citation_context    TEXT,  -- Surrounding text
    
    -- Relevance scores
    initial_score       FLOAT,  -- Cosine similarity
    rerank_score        FLOAT,  -- After reranking
    final_score         FLOAT,  -- Combined score
    distance            FLOAT,  -- Vector distance
    
    -- Usage tracking
    used_in_answer      BOOLEAN DEFAULT true,
    position_in_answer  INTEGER,  -- Where cited in answer
    
    -- User interaction
    clicked             BOOLEAN DEFAULT false,
    click_count         INTEGER DEFAULT 0,
    time_spent_viewing  INTEGER,  -- seconds
    
    -- Metadata
    section_title       TEXT,
    hierarchy_path      TEXT[],  -- ['Chapter 1', 'Article 5', 'Clause 1']
    document_metadata   JSONB,  -- Denormalized for performance
    
    -- Audit
    created_at          TIMESTAMP DEFAULT now(),
    updated_at          TIMESTAMP DEFAULT now()
);

-- Indexes
CREATE INDEX idx_citations_message ON citations(message_id, citation_number);
CREATE INDEX idx_citations_query ON citations(query_id);
CREATE INDEX idx_citations_document ON citations(document_id);
CREATE INDEX idx_citations_chunk ON citations(chunk_id);
CREATE INDEX idx_citations_score ON citations(final_score DESC);
CREATE INDEX idx_citations_clicked ON citations(clicked, click_count);
```

**Use Cases:**
- UC-29: View Citation Details (NEW)
- UC-30: Track Citation Usage (NEW)
- UC-31: Citation Analytics (NEW)

---

### 6. Table: `document_chunks`

**Purpose:** Explicit chunk metadata (denormalized from embedding for faster queries)

```sql
CREATE TABLE document_chunks (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id            VARCHAR(255) UNIQUE NOT NULL,  -- Same as embedding.id
    document_id         VARCHAR(255) NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    
    -- Chunk content
    content             TEXT NOT NULL,
    content_length      INTEGER,
    content_hash        VARCHAR(64),  -- For deduplication
    
    -- Position
    chunk_index         INTEGER NOT NULL,
    total_chunks        INTEGER,
    page_number         INTEGER,
    
    -- Structure
    section_title       TEXT,
    hierarchy_path      TEXT[],
    level               VARCHAR(50),  -- dieu, khoan, phan, chuong
    
    -- Content analysis
    has_table           BOOLEAN DEFAULT false,
    has_list            BOOLEAN DEFAULT false,
    has_code            BOOLEAN DEFAULT false,
    has_formula         BOOLEAN DEFAULT false,
    
    -- Semantic metadata
    keywords            TEXT[],
    concepts            TEXT[],
    legal_terms         TEXT[],
    entities            JSONB,  -- Named entities
    
    -- Quality metrics
    is_complete_unit    BOOLEAN DEFAULT true,
    quality_score       FLOAT,  -- Content quality estimation
    
    -- Usage statistics
    retrieval_count     INTEGER DEFAULT 0,
    citation_count      INTEGER DEFAULT 0,
    avg_relevance_score FLOAT,
    last_retrieved_at   TIMESTAMP,
    
    -- Status
    status              VARCHAR(20) DEFAULT 'active',
    
    -- Audit
    created_at          TIMESTAMP DEFAULT now(),
    updated_at          TIMESTAMP DEFAULT now()
);

-- Indexes
CREATE INDEX idx_chunks_document ON document_chunks(document_id, chunk_index);
CREATE INDEX idx_chunks_content_hash ON document_chunks(content_hash);
CREATE INDEX idx_chunks_section ON document_chunks(section_title);
CREATE INDEX idx_chunks_keywords ON document_chunks USING gin(keywords);
CREATE INDEX idx_chunks_concepts ON document_chunks USING gin(concepts);
CREATE INDEX idx_chunks_retrieval ON document_chunks(retrieval_count DESC);
CREATE INDEX idx_chunks_quality ON document_chunks(quality_score DESC);

-- Full-text search index
CREATE INDEX idx_chunks_content_fts ON document_chunks USING gin(to_tsvector('vietnamese', content));
```

**Use Cases:**
- UC-7: Upload Document
- UC-8: Process Document
- UC-32: Chunk Analytics (NEW)
- UC-33: Content Quality Monitoring (NEW)

---

### 7. Table: `document_versions`

**Purpose:** Version control for documents (like Git for documents)

```sql
CREATE TABLE document_versions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id         VARCHAR(255) NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    
    -- Version info
    version_number      INTEGER NOT NULL,
    version_label       VARCHAR(100),  -- v1.0, draft, final, etc.
    
    -- File details
    source_file         TEXT NOT NULL,
    file_name           TEXT NOT NULL,
    file_size_bytes     BIGINT,
    file_hash           VARCHAR(64),  -- SHA-256
    
    -- Processing results
    total_chunks        INTEGER,
    processing_time_ms  INTEGER,
    processing_status   VARCHAR(20),  -- success, failed, partial
    
    -- Changes
    changes_summary     TEXT,
    diff_stats          JSONB,  -- Added, modified, deleted chunks
    is_major_change     BOOLEAN DEFAULT false,
    
    -- Metadata
    uploaded_by         UUID REFERENCES users(id) ON DELETE SET NULL,
    notes               TEXT,
    tags                TEXT[],
    
    -- Lifecycle
    is_current          BOOLEAN DEFAULT false,  -- Only one version is current
    published_at        TIMESTAMP,
    deprecated_at       TIMESTAMP,
    
    -- Audit
    created_at          TIMESTAMP DEFAULT now(),
    updated_at          TIMESTAMP DEFAULT now(),
    
    UNIQUE(document_id, version_number)
);

-- Indexes
CREATE INDEX idx_versions_document ON document_versions(document_id, version_number DESC);
CREATE INDEX idx_versions_current ON document_versions(document_id) WHERE is_current = true;
CREATE INDEX idx_versions_published ON document_versions(published_at DESC);
CREATE INDEX idx_versions_uploaded_by ON document_versions(uploaded_by);

-- Diff stats JSONB structure
{
  "chunks_added": 5,
  "chunks_modified": 12,
  "chunks_deleted": 3,
  "sections_added": ["Điều 15"],
  "sections_removed": [],
  "significant_changes": [
    {
      "section": "Điều 5",
      "type": "modified",
      "summary": "Updated penalty amounts"
    }
  ]
}
```

**Use Cases:**
- UC-34: Document Version Control (NEW)
- UC-35: Compare Document Versions (NEW)
- UC-36: Rollback Document (NEW)

---

### 8. Table: `document_collections`

**Purpose:** Group documents into collections (like Notion databases)

```sql
CREATE TABLE document_collections (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                VARCHAR(255) NOT NULL,
    description         TEXT,
    slug                VARCHAR(255) UNIQUE,
    
    -- Ownership
    owner_id            UUID REFERENCES users(id) ON DELETE SET NULL,
    organization_id     UUID,
    
    -- Collection type
    collection_type     VARCHAR(50) DEFAULT 'custom',  -- custom, system, shared
    
    -- Filters & Rules
    auto_include_rules  JSONB,  -- Automatic inclusion rules
    manual_documents    VARCHAR(255)[],  -- Manually added document IDs
    excluded_documents  VARCHAR(255)[],  -- Manually excluded
    
    -- Statistics
    document_count      INTEGER DEFAULT 0,
    total_chunks        INTEGER DEFAULT 0,
    last_updated_at     TIMESTAMP,
    
    -- Sharing
    is_public           BOOLEAN DEFAULT false,
    shared_with         UUID[],  -- User IDs
    permissions         JSONB,  -- View, edit permissions
    
    -- Display
    icon                VARCHAR(50),
    color               VARCHAR(20),
    sort_order          INTEGER,
    
    -- Status
    is_active           BOOLEAN DEFAULT true,
    
    -- Audit
    created_at          TIMESTAMP DEFAULT now(),
    updated_at          TIMESTAMP DEFAULT now(),
    deleted_at          TIMESTAMP
);

-- Junction table for many-to-many
CREATE TABLE collection_documents (
    collection_id       UUID REFERENCES document_collections(id) ON DELETE CASCADE,
    document_id         VARCHAR(255) REFERENCES documents(document_id) ON DELETE CASCADE,
    added_at            TIMESTAMP DEFAULT now(),
    added_by            UUID REFERENCES users(id) ON DELETE SET NULL,
    sort_order          INTEGER,
    
    PRIMARY KEY (collection_id, document_id)
);

-- Indexes
CREATE INDEX idx_collections_owner ON document_collections(owner_id);
CREATE INDEX idx_collections_type ON document_collections(collection_type);
CREATE INDEX idx_collections_public ON document_collections(is_public) WHERE is_public = true;
CREATE INDEX idx_col_docs_collection ON collection_documents(collection_id);
CREATE INDEX idx_col_docs_document ON collection_documents(document_id);

-- Auto-include rules JSONB
{
  "document_types": ["law", "decree"],
  "categories": ["legal"],
  "date_range": {
    "from": "2023-01-01"
  },
  "tags": ["important"],
  "status": ["active"]
}
```

**Use Cases:**
- UC-37: Create Document Collection (NEW)
- UC-38: Search within Collection (NEW)
- UC-39: Share Collection (NEW)

---

### 9. Table: `feedback`

**Purpose:** User feedback on answers (improve system quality)

```sql
CREATE TABLE feedback (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID REFERENCES users(id) ON DELETE SET NULL,
    message_id          UUID REFERENCES messages(id) ON DELETE CASCADE,
    query_id            UUID REFERENCES queries(id) ON DELETE SET NULL,
    
    -- Feedback type
    feedback_type       VARCHAR(50) NOT NULL,  -- rating, flag, suggestion, correction
    
    -- Rating (1-5 stars)
    rating              INTEGER CHECK (rating BETWEEN 1 AND 5),
    
    -- Specific issues
    issues              TEXT[],  -- ['incorrect', 'incomplete', 'outdated', 'irrelevant']
    
    -- User comments
    comment             TEXT,
    suggested_answer    TEXT,
    suggested_sources   JSONB,
    
    -- Context
    was_helpful         BOOLEAN,
    reason              TEXT,
    
    -- Follow-up
    resolved            BOOLEAN DEFAULT false,
    resolution_notes    TEXT,
    resolved_by         UUID REFERENCES users(id) ON DELETE SET NULL,
    resolved_at         TIMESTAMP,
    
    -- Audit
    created_at          TIMESTAMP DEFAULT now(),
    updated_at          TIMESTAMP DEFAULT now()
);

-- Indexes
CREATE INDEX idx_feedback_user ON feedback(user_id);
CREATE INDEX idx_feedback_message ON feedback(message_id);
CREATE INDEX idx_feedback_type ON feedback(feedback_type);
CREATE INDEX idx_feedback_rating ON feedback(rating);
CREATE INDEX idx_feedback_unresolved ON feedback(resolved) WHERE resolved = false;
CREATE INDEX idx_feedback_issues ON feedback USING gin(issues);
```

**Use Cases:**
- UC-25: Provide Feedback on Answer
- UC-40: Review Feedback Queue (NEW)
- UC-41: Improve Answer Quality (NEW)

---

### 10. Table: `bookmarks`

**Purpose:** Save useful Q&A pairs (like browser bookmarks)

```sql
CREATE TABLE bookmarks (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message_id          UUID REFERENCES messages(id) ON DELETE CASCADE,
    conversation_id     UUID REFERENCES conversations(id) ON DELETE CASCADE,
    
    -- Bookmark details
    title               TEXT,
    notes               TEXT,
    tags                TEXT[],
    
    -- Organization
    folder_path         TEXT,  -- '/Work/Legal/Bidding'
    is_favorite         BOOLEAN DEFAULT false,
    
    -- Sharing
    is_public           BOOLEAN DEFAULT false,
    share_url           VARCHAR(255) UNIQUE,
    
    -- Audit
    created_at          TIMESTAMP DEFAULT now(),
    updated_at          TIMESTAMP DEFAULT now(),
    
    UNIQUE(user_id, message_id)
);

-- Indexes
CREATE INDEX idx_bookmarks_user ON bookmarks(user_id, created_at DESC);
CREATE INDEX idx_bookmarks_conv ON bookmarks(conversation_id);
CREATE INDEX idx_bookmarks_tags ON bookmarks USING gin(tags);
CREATE INDEX idx_bookmarks_public ON bookmarks(is_public) WHERE is_public = true;
CREATE INDEX idx_bookmarks_favorite ON bookmarks(user_id) WHERE is_favorite = true;
```

**Use Cases:**
- UC-42: Bookmark Answer (NEW)
- UC-43: Organize Bookmarks (NEW)
- UC-44: Share Bookmark (NEW)

---

### 11. Table: `search_filters`

**Purpose:** Save frequently used search filters (like saved searches)

```sql
CREATE TABLE search_filters (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Filter details
    name                VARCHAR(255) NOT NULL,
    description         TEXT,
    
    -- Filter configuration
    filters             JSONB NOT NULL,
    rag_mode            VARCHAR(20),
    
    -- Usage
    use_count           INTEGER DEFAULT 0,
    last_used_at        TIMESTAMP,
    
    -- Organization
    is_default          BOOLEAN DEFAULT false,  -- Auto-apply
    sort_order          INTEGER,
    
    -- Sharing
    is_public           BOOLEAN DEFAULT false,
    shared_with         UUID[],
    
    -- Audit
    created_at          TIMESTAMP DEFAULT now(),
    updated_at          TIMESTAMP DEFAULT now()
);

-- Indexes
CREATE INDEX idx_filters_user ON search_filters(user_id);
CREATE INDEX idx_filters_default ON search_filters(user_id) WHERE is_default = true;
CREATE INDEX idx_filters_public ON search_filters(is_public) WHERE is_public = true;
```

**Use Cases:**
- UC-45: Save Search Filter (NEW)
- UC-46: Quick Filter Access (NEW)

---

### 12. Table: `api_keys`

**Purpose:** API authentication & rate limiting

```sql
CREATE TABLE api_keys (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Key details
    key_hash            VARCHAR(255) UNIQUE NOT NULL,  -- Hashed API key
    key_prefix          VARCHAR(10) NOT NULL,  -- First 8 chars for display (e.g., 'sk-12345...')
    name                VARCHAR(255),  -- User-friendly name
    description         TEXT,
    
    -- Permissions
    scopes              TEXT[],  -- ['read:documents', 'write:queries', 'admin:all']
    allowed_ips         INET[],  -- IP whitelist
    allowed_origins     TEXT[],  -- CORS origins
    
    -- Rate limiting
    rate_limit_rpm      INTEGER DEFAULT 60,  -- Requests per minute
    rate_limit_rph      INTEGER DEFAULT 1000,  -- Requests per hour
    rate_limit_rpd      INTEGER DEFAULT 10000,  -- Requests per day
    
    -- Usage tracking
    total_requests      INTEGER DEFAULT 0,
    total_tokens        INTEGER DEFAULT 0,
    total_cost_usd      DECIMAL(10, 6) DEFAULT 0,
    last_used_at        TIMESTAMP,
    
    -- Lifecycle
    is_active           BOOLEAN DEFAULT true,
    expires_at          TIMESTAMP,
    
    -- Audit
    created_at          TIMESTAMP DEFAULT now(),
    updated_at          TIMESTAMP DEFAULT now(),
    revoked_at          TIMESTAMP,
    revoked_by          UUID REFERENCES users(id) ON DELETE SET NULL,
    revoke_reason       TEXT
);

-- Indexes
CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash) WHERE revoked_at IS NULL;
CREATE INDEX idx_api_keys_user ON api_keys(user_id);
CREATE INDEX idx_api_keys_active ON api_keys(is_active) WHERE is_active = true;
CREATE INDEX idx_api_keys_expires ON api_keys(expires_at) WHERE expires_at IS NOT NULL;
```

**Use Cases:**
- UC-47: Generate API Key (NEW)
- UC-48: Manage API Keys (NEW)
- UC-49: API Rate Limiting (NEW)

---

### 13. Table: `usage_metrics`

**Purpose:** Aggregated analytics (pre-computed for dashboards)

```sql
CREATE TABLE usage_metrics (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Time dimension
    date                DATE NOT NULL,
    hour                INTEGER,  -- 0-23, null for daily aggregation
    
    -- Dimensions
    user_id             UUID REFERENCES users(id) ON DELETE CASCADE,
    organization_id     UUID,
    rag_mode            VARCHAR(20),
    document_type       VARCHAR(50),
    
    -- Metrics
    total_queries       INTEGER DEFAULT 0,
    successful_queries  INTEGER DEFAULT 0,
    failed_queries      INTEGER DEFAULT 0,
    cached_queries      INTEGER DEFAULT 0,
    
    -- Performance
    avg_latency_ms      INTEGER,
    p50_latency_ms      INTEGER,
    p95_latency_ms      INTEGER,
    p99_latency_ms      INTEGER,
    
    -- Quality
    avg_confidence      FLOAT,
    avg_sources_count   FLOAT,
    feedback_count      INTEGER DEFAULT 0,
    avg_rating          FLOAT,
    
    -- Cost
    total_tokens        INTEGER DEFAULT 0,
    total_cost_usd      DECIMAL(10, 6) DEFAULT 0,
    
    -- Cache performance
    l1_hit_rate         FLOAT,
    l2_hit_rate         FLOAT,
    l3_hit_rate         FLOAT,
    
    -- Audit
    created_at          TIMESTAMP DEFAULT now(),
    updated_at          TIMESTAMP DEFAULT now(),
    
    UNIQUE(date, hour, user_id, organization_id, rag_mode, document_type)
);

-- Indexes
CREATE INDEX idx_metrics_date ON usage_metrics(date DESC, hour DESC);
CREATE INDEX idx_metrics_user ON usage_metrics(user_id, date DESC);
CREATE INDEX idx_metrics_org ON usage_metrics(organization_id, date DESC);
CREATE INDEX idx_metrics_mode ON usage_metrics(rag_mode, date DESC);
```

**Use Cases:**
- UC-26: Analytics Dashboard
- UC-27: Cost Tracking
- UC-50: Performance Monitoring (NEW)

---

## 🔗 Enhanced Schema Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RAG BIDDING SYSTEM v3.0                              │
│                         Complete Database Schema                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ AUTHENTICATION & USER MANAGEMENT                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  users                   api_keys                  usage_metrics             │
│  - Email/OAuth login     - API authentication      - Analytics aggregation  │
│  - Role-based access     - Rate limiting           - Performance tracking   │
│  - Preferences           - Scopes & permissions    - Cost monitoring        │
└────────┬────────────────────────┬──────────────────────────────────────┬────┘
         │                        │                                      │
         ├────────────────────────┼──────────────────────────────────────┘
         │                        │
         ▼                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ CONVERSATION & MESSAGE MANAGEMENT                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  conversations           messages                  bookmarks                │
│  - Multi-turn chat       - User/Assistant msgs     - Save Q&A pairs         │
│  - RAG config            - Sources & citations     - Organize by folder     │
│  - Sharing & collab      - Feedback tracking       - Tags & notes           │
│         │                       │                          │                 │
│         └───────────┬───────────┴──────────────────────────┘                │
│                     │                                                        │
└─────────────────────┼────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ QUERY PROCESSING & ANALYTICS                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  queries                 citations                  feedback                │
│  - Query logging         - Source tracking          - User ratings          │
│  - Performance metrics   - Relevance scores         - Quality improvement  │
│  - Cost tracking         - Click analytics          - Issue reporting       │
└────────┬────────────────────────┬──────────────────────────┬────────────────┘
         │                        │                          │
         └────────────────────────┼──────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ DOCUMENT MANAGEMENT (CORE)                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  documents ⭐             document_chunks           document_versions        │
│  - Metadata              - Explicit chunk info     - Version control        │
│  - Status tracking       - Quality metrics         - Change tracking        │
│  - 64 docs               - Usage statistics        - Rollback support       │
│         │                       │                          │                 │
│         └───────────┬───────────┴──────────────────────────┘                │
│                     │                                                        │
└─────────────────────┼────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ VECTOR STORAGE (EXISTING)                                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  langchain_pg_embedding ⭐    langchain_pg_collection                        │
│  - VECTOR(3072)                - LangChain internal                         │
│  - 7,892 chunks                - DO NOT MODIFY                              │
│  - JSONB metadata                                                            │
└─────────────────────────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ ORGANIZATION & COLLECTIONS                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  document_collections      collection_documents     search_filters          │
│  - Group documents          - Junction table        - Saved searches        │
│  - Auto-include rules       - M:N relationship      - Quick access          │
│  - Sharing                                                                   │
└─────────────────────────────────────────────────────────────────────────────┘

RELATIONSHIPS:
━━━━  One-to-Many (1:N)
════  Many-to-Many (M:N)
┈┈┈┈  Optional/Nullable FK
```

---

## 📊 Use Cases Summary

### Core RAG Features (UC-1 to UC-18) - EXISTING ✅

**Question Answering:**
- UC-1: Ask Simple Question
- UC-2: Ask with Context
- UC-3: Advanced Query with Filters

**Chat Sessions:**
- UC-4: Create Chat Session
- UC-5: Continue Chat Conversation
- UC-6: Manage Chat History

**Document Management:**
- UC-7: Upload Document
- UC-8: Process Document
- UC-9: List Documents
- UC-10: Search Documents
- UC-11: View Document Details
- UC-12: Update Document Status
- UC-13: Delete Document

**System Admin:**
- UC-14: View System Metrics
- UC-15: Monitor Performance
- UC-16: Manage Cache
- UC-17: Health Check
- UC-18: Clear Cache

### New Use Cases (UC-19 to UC-50) - PROPOSED ⭐

**User Management (UC-19 to UC-21):**
- UC-19: User Registration & Login
- UC-20: Profile Management
- UC-21: Multi-tenant Organization Management

**Collaboration (UC-22 to UC-23):**
- UC-22: Share Conversation
- UC-23: Collaborate on Research

**Source Citations (UC-24, UC-29 to UC-31):**
- UC-24: Review Source Citations
- UC-29: View Citation Details
- UC-30: Track Citation Usage
- UC-31: Citation Analytics

**Feedback & Quality (UC-25, UC-40 to UC-41):**
- UC-25: Provide Feedback on Answer
- UC-40: Review Feedback Queue
- UC-41: Improve Answer Quality

**Analytics & Monitoring (UC-26 to UC-28, UC-50):**
- UC-26: Analytics Dashboard
- UC-27: Cost Tracking
- UC-28: Query Pattern Analysis
- UC-50: Performance Monitoring

**Document Advanced Features (UC-32 to UC-36):**
- UC-32: Chunk Analytics
- UC-33: Content Quality Monitoring
- UC-34: Document Version Control
- UC-35: Compare Document Versions
- UC-36: Rollback Document

**Collections (UC-37 to UC-39):**
- UC-37: Create Document Collection
- UC-38: Search within Collection
- UC-39: Share Collection

**User Productivity (UC-42 to UC-46):**
- UC-42: Bookmark Answer
- UC-43: Organize Bookmarks
- UC-44: Share Bookmark
- UC-45: Save Search Filter
- UC-46: Quick Filter Access

**API Management (UC-47 to UC-49):**
- UC-47: Generate API Key
- UC-48: Manage API Keys
- UC-49: API Rate Limiting

---

## 🚀 Migration Roadmap

### Phase 1: User & Auth (v3.1) - 2 weeks
- Create `users` table
- Create `api_keys` table
- Implement JWT authentication
- Migrate implicit users from session data

### Phase 2: Conversations (v3.2) - 2 weeks
- Create `conversations`, `messages` tables
- Migrate chat sessions from Redis DB 1 to PostgreSQL
- Implement conversation sharing

### Phase 3: Analytics (v3.3) - 1 week
- Create `queries`, `citations`, `usage_metrics` tables
- Start logging all queries
- Build analytics dashboard

### Phase 4: Document Advanced (v3.4) - 2 weeks
- Create `document_chunks`, `document_versions`, `document_collections` tables
- Implement version control
- Build collection management UI

### Phase 5: User Features (v3.5) - 1 week
- Create `feedback`, `bookmarks`, `search_filters` tables
- Implement bookmark system
- Saved filter quick access

---

## 🎯 Key Improvements over v2.0

### 1. **Explicit Chunk Management**
- `document_chunks` table separates chunk metadata from vector storage
- Better performance for chunk-level queries
- Usage statistics per chunk

### 2. **Enhanced Citation System**
- Dedicated `citations` table (inspired by Perplexity)
- Track citation clicks and usage
- Better source attribution

### 3. **Conversation-First Design**
- `conversations` + `messages` (like ChatGPT)
- Support for sharing and collaboration
- Better context preservation

### 4. **Comprehensive Analytics**
- `queries` table logs everything
- `usage_metrics` for pre-aggregated data
- Cost tracking and optimization

### 5. **Document Versioning**
- Git-like version control for documents
- Compare versions, rollback changes
- Track document evolution

### 6. **Collection Management**
- Group documents logically
- Auto-include rules (like smart playlists)
- Share collections with teams

### 7. **User Productivity**
- Bookmarks for important Q&A
- Saved search filters
- Personalized preferences

### 8. **API-First**
- Dedicated API key management
- Granular permissions (scopes)
- Rate limiting per key

---

## 📈 Expected Impact

### Performance
- **Chunk queries**: 50% faster (dedicated table vs JSONB parsing)
- **Analytics**: 10x faster (pre-aggregated metrics)
- **Cache hit rate**: +10-15% (better tracking)

### User Experience
- **Conversation continuity**: Full chat history
- **Source transparency**: Clear citations
- **Personalization**: Saved preferences & filters

### Business Metrics
- **Cost visibility**: Track every dollar spent
- **Quality metrics**: Feedback-driven improvements
- **Usage insights**: Understand user patterns

---

**Created:** November 27, 2025  
**Status:** Proposed - Pending Review  
**Next Steps:** Review with team → Prioritize phases → Start Phase 1 implementation
