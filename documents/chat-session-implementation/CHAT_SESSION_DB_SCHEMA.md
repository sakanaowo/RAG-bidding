# Chat Session Database Schema Analysis & Proposal

## 📊 Current Database State

### Existing Tables (2 tables)

#### 1. `langchain_pg_collection`
```sql
Column    | Type              | Purpose
----------|-------------------|------------------
uuid      | UUID (PK)         | Collection ID
name      | VARCHAR (UNIQUE)  | Collection name (e.g., "docs")
cmetadata | JSON              | Collection metadata
```

**Current data:** 1 collection (name="docs")

#### 2. `langchain_pg_embedding`
```sql
Column        | Type              | Purpose
--------------|-------------------|---------------------------
id            | VARCHAR (PK)      | Chunk ID (not UUID!)
collection_id | UUID (FK)         | → langchain_pg_collection
embedding     | VECTOR(3072)      | OpenAI text-embedding-3-large
document      | VARCHAR           | Chunk text content
cmetadata     | JSONB             | Document metadata
```

**Current data:**
- 4,708 total chunks
- 5 unique documents (document_id)
- 5 document types: bidding, law, decree, circular, decision

**Metadata structure** (JSONB):
```json
{
  "document_id": "FORM-Bidding/2025#bee720",
  "document_type": "bidding",
  "chunk_id": "bidding_untitled_form_0102",
  "chunk_index": 102,
  "total_chunks": 104,
  "level": "form",
  "hierarchy": "[\"Mẫu số 17\"]",
  "section_title": "",
  "char_count": 2021,
  "is_complete_unit": true,
  "has_table": false,
  "has_list": false,
  "document_info": {
    "document_status": "active",
    "superseded_by": "bidding_new_2024"
  },
  "processing_metadata": {
    "processing_status": "completed",
    "last_processed_at": "2025-11-09T14:06:20.876510",
    "retry_count": 0,
    "error_message": null,
    "status_change_history": [...]
  },
  "extra_metadata": "{...}"  // JSON string với entities, keywords, concepts
}
```

---

## 🎯 Proposed Chat Session Schema

### Design Principles

1. **Separation of Concerns**: Sessions ≠ Documents (don't mix with langchain tables)
2. **Relational Integrity**: FK constraints với CASCADE delete
3. **Query Performance**: Indexes cho common queries
4. **Audit Trail**: Timestamps cho mọi operations
5. **Flexibility**: JSONB metadata cho future extensions
6. **Analytics Ready**: Có thể query usage patterns, popular topics

### Table 1: `chat_sessions`

**Purpose:** Track conversation sessions, users, và session-level metadata

```sql
CREATE TABLE chat_sessions (
    -- Primary Key
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- User Information (optional for anonymous chats)
    user_id VARCHAR(255),                    -- User identifier (can be NULL)
    user_ip VARCHAR(45),                     -- IPv4/IPv6 for analytics
    user_agent TEXT,                         -- Browser info
    
    -- Session Lifecycle
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_activity TIMESTAMP NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMP,                      -- NULL = active, NOT NULL = closed
    
    -- Session Context
    session_title VARCHAR(500),              -- Auto-generated or user-set title
    session_mode VARCHAR(50) DEFAULT 'balanced',  -- RAG mode: fast/balanced/quality
    
    -- Statistics
    message_count INTEGER DEFAULT 0,         -- Total messages in session
    total_tokens INTEGER DEFAULT 0,          -- Token usage tracking
    
    -- Metadata (JSONB for flexibility)
    metadata JSONB DEFAULT '{}'::jsonb,
    -- Example metadata:
    -- {
    --   "source": "web" | "api" | "mobile",
    --   "language": "vi" | "en",
    --   "tags": ["legal", "bidding"],
    --   "rating": 5,  // User satisfaction (1-5)
    --   "feedback": "Very helpful"
    -- }
    
    CONSTRAINT valid_mode CHECK (session_mode IN ('fast', 'balanced', 'quality', 'adaptive'))
);

-- Indexes
CREATE INDEX idx_session_user ON chat_sessions(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_session_created ON chat_sessions(created_at DESC);
CREATE INDEX idx_session_last_activity ON chat_sessions(last_activity DESC);
CREATE INDEX idx_session_active ON chat_sessions(ended_at) WHERE ended_at IS NULL;
CREATE INDEX idx_session_metadata_gin ON chat_sessions USING gin(metadata jsonb_path_ops);
```

**Rationale:**
- `session_id` UUID: Industry standard, globally unique
- `user_id` nullable: Support anonymous users
- `last_activity`: Auto-update để cleanup inactive sessions
- `ended_at` nullable: Distinguish active vs historical sessions
- `metadata` JSONB: Flexible cho tags, ratings, custom fields

---

### Table 2: `chat_messages`

**Purpose:** Store individual messages (user questions + AI responses)

```sql
CREATE TABLE chat_messages (
    -- Primary Key
    id BIGSERIAL PRIMARY KEY,                -- Auto-increment (not UUID - performance)
    
    -- Foreign Key
    session_id UUID NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    
    -- Message Content
    role VARCHAR(20) NOT NULL,               -- 'user' or 'assistant'
    content TEXT NOT NULL,                   -- Message text
    
    -- Timestamps
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- RAG Context (for assistant messages)
    retrieved_docs JSONB,                    -- Documents used for this response
    -- Example:
    -- [
    --   {"document_id": "LAW-123", "chunk_id": "...", "score": 0.95},
    --   {"document_id": "DECREE-456", "chunk_id": "...", "score": 0.87}
    -- ]
    
    reranker_used VARCHAR(50),               -- 'bge' | 'openai' | null
    tokens_used INTEGER,                     -- Tokens for this message
    latency_ms INTEGER,                      -- Response time in milliseconds
    
    -- Metadata (JSONB)
    metadata JSONB DEFAULT '{}'::jsonb,
    -- Example metadata:
    -- {
    --   "query_enhancement": "multi_query",
    --   "retrieval_k": 10,
    --   "reranking_enabled": true,
    --   "cache_hit": false,
    --   "error": null,
    --   "edited_by_user": false
    -- }
    
    CONSTRAINT valid_role CHECK (role IN ('user', 'assistant', 'system'))
);

-- Indexes
CREATE INDEX idx_messages_session ON chat_messages(session_id, timestamp);
CREATE INDEX idx_messages_timestamp ON chat_messages(timestamp DESC);
CREATE INDEX idx_messages_role ON chat_messages(role);
CREATE INDEX idx_messages_retrieved_gin ON chat_messages USING gin(retrieved_docs jsonb_path_ops);
```

**Rationale:**
- `id` BIGSERIAL: Faster than UUID cho sequential data, billions of messages support
- `session_id` FK CASCADE: Xóa session → auto xóa messages
- `retrieved_docs` JSONB: Track which documents were used (citation, analytics)
- `latency_ms`: Monitor performance over time
- Separate indexes cho session queries vs global analytics

---

### Table 3 (Optional): `chat_session_documents`

**Purpose:** Link sessions to documents được tham chiếu (many-to-many)

```sql
CREATE TABLE chat_session_documents (
    session_id UUID NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    document_id VARCHAR(255) NOT NULL,       -- From cmetadata->>'document_id'
    first_mentioned TIMESTAMP NOT NULL DEFAULT NOW(),
    mention_count INTEGER DEFAULT 1,
    
    PRIMARY KEY (session_id, document_id)
);

-- Index
CREATE INDEX idx_session_docs_doc ON chat_session_documents(document_id);
```

**Use cases:**
- "Show me all sessions that discussed Law XYZ"
- "Top 10 most-discussed documents this month"
- Auto-suggest related documents based on session history

---

## 🔍 Schema Comparison

### Option A: Minimal Schema (Recommended for MVP)
**Tables:** `chat_sessions` + `chat_messages` (2 tables)

**Pros:**
- ✅ Simple to implement
- ✅ Low maintenance
- ✅ Covers 95% of use cases

**Cons:**
- ⚠️ Limited analytics on document usage

### Option B: Full Schema
**Tables:** `chat_sessions` + `chat_messages` + `chat_session_documents` (3 tables)

**Pros:**
- ✅ Rich analytics
- ✅ Document tracking
- ✅ Better for recommendations

**Cons:**
- ⚠️ Extra write operations
- ⚠️ Maintenance overhead

---

## 📈 Query Examples

### Common Queries

```sql
-- 1. Get all messages for a session (most common)
SELECT role, content, timestamp, metadata
FROM chat_messages
WHERE session_id = '123e4567-e89b-12d3-a456-426614174000'
ORDER BY timestamp ASC;

-- 2. Recent active sessions
SELECT session_id, user_id, session_title, last_activity, message_count
FROM chat_sessions
WHERE ended_at IS NULL
ORDER BY last_activity DESC
LIMIT 20;

-- 3. User's conversation history
SELECT s.session_id, s.session_title, s.created_at, s.message_count
FROM chat_sessions s
WHERE s.user_id = 'user123'
ORDER BY s.created_at DESC;

-- 4. Most discussed documents (with Option B)
SELECT document_id, SUM(mention_count) as total_mentions
FROM chat_session_documents
GROUP BY document_id
ORDER BY total_mentions DESC
LIMIT 10;

-- 5. Average response time per day
SELECT 
    DATE(timestamp) as date,
    AVG(latency_ms) as avg_latency,
    COUNT(*) as total_responses
FROM chat_messages
WHERE role = 'assistant'
GROUP BY DATE(timestamp)
ORDER BY date DESC;

-- 6. Sessions by RAG mode
SELECT session_mode, COUNT(*) as count
FROM chat_sessions
GROUP BY session_mode;

-- 7. Find sessions with errors
SELECT DISTINCT m.session_id, s.session_title
FROM chat_messages m
JOIN chat_sessions s ON m.session_id = s.session_id
WHERE m.metadata->>'error' IS NOT NULL;
```

---

## 🚀 Migration Strategy

### Step 1: Create Tables (10 minutes)
```sql
-- Run SQL file: scripts/migrations/001_create_chat_tables.sql
```

### Step 2: Update Code (30 minutes)
- Enable `PostgresChatSessionStore` (already exists in `src/api/chat_session.py`)
- Update `documents_chat.py` to use PostgreSQL store
- Remove Redis session references

### Step 3: Test (15 minutes)
- Create session
- Send messages
- Retrieve history
- Delete session

### Step 4: Deploy
- No downtime (new tables, existing code still works)
- Gradual rollout with feature flag

---

## 💾 Storage Estimates

### Assumptions:
- Average message: 500 chars × 2 bytes = 1 KB
- Metadata: ~500 bytes
- **Total per message:** ~1.5 KB

### Projections:

| Sessions/day | Messages/session | Daily Storage | Monthly Storage |
|--------------|------------------|---------------|-----------------|
| 100          | 10               | 1.5 MB        | 45 MB           |
| 1,000        | 10               | 15 MB         | 450 MB          |
| 10,000       | 10               | 150 MB        | 4.5 GB          |

**Cleanup strategy:**
- Auto-delete sessions older than 90 days (configurable)
- Archive to S3/cold storage for compliance
- Vacuum regularly to reclaim space

---

## 🎯 Recommendation

**Implement Option A (Minimal Schema):**

1. ✅ Create `chat_sessions` + `chat_messages` tables
2. ✅ Use existing `PostgresChatSessionStore` class
3. ✅ Add indexes for performance
4. ✅ Auto-cleanup với `ended_at > NOW() - INTERVAL '90 days'`
5. ⏳ Add `chat_session_documents` later if analytics needed

**Benefits over Redis:**
- Persistent storage (no data loss)
- Query history by user/date/document
- ACID guarantees
- Better for compliance/audit
- Same infrastructure (no new Redis dependency)

**Trade-off:**
- 50ms latency vs 1ms (acceptable for chat)
- Simpler architecture (one less system to maintain)

---

## 📝 Next Steps

1. **Review schema** - Bạn OK với design này không?
2. **Modify if needed** - Thêm/bớt fields nào?
3. **Create migration SQL** - Tạo file `001_create_chat_tables.sql`
4. **Update code** - Switch từ Redis → PostgreSQL
5. **Test** - Verify all endpoints work

**Questions for you:**
- ✅ Có cần track `user_ip` và `user_agent` không? (for analytics/abuse prevention)
- ✅ Auto-delete sessions sau bao lâu? (90 days? 1 year? never?)
- ✅ Implement Option A hay Option B? (tôi recommend Option A)
- ✅ Có cần thêm fields nào khác không?
