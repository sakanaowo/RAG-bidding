# Chat Session PostgreSQL Implementation Plan

## 📋 Executive Summary

**Goal:** Migrate chat sessions từ Redis sang PostgreSQL để có persistent storage, better analytics, và simpler architecture.

**Decision:** Option A - Minimal schema (2 tables: `chat_sessions` + `chat_messages`)

**Timeline:** 3-4 hours total (có thể chia làm nhiều sessions)

**Status:** 🟡 PLANNED - Chưa bắt đầu

---

## 🎯 Requirements Confirmed

1. ✅ **Schema:** Option A (2 tables, không cần `chat_session_documents` bây giờ)
2. ✅ **Privacy:** KHÔNG track user_ip/user_agent
3. ✅ **User Management:** Support CẢ authenticated users VÀ anonymous sessions
4. ✅ **Retention:** Archive to cold storage (chưa auto-delete)
5. ✅ **Fields:** Schema đã đủ như proposed

---

## 📐 Architecture Overview

### Current State (INCOMPLETE)

```
src/api/
├── chat_session.py          # ⚠️ Có 3 classes nhưng chưa dùng production
│   ├── RedisChatSessionStore        # Đang dùng (temp)
│   ├── PostgresChatSessionStore     # TODO: Enable this
│   └── HybridChatSessionStore       # TODO: Consider for future
│
└── routers/
    └── documents_chat.py     # ⚠️ Hard-coded Redis, cần refactor
        ├── /chat/create      # Endpoint tạo session
        ├── /chat/send        # Endpoint gửi message
        ├── /chat/history     # Endpoint lấy history
        └── /chat/delete      # Endpoint xóa session
```

### Target State (AFTER MIGRATION)

```
PostgreSQL Tables:
├── chat_sessions             # Session metadata
└── chat_messages            # Individual messages

Feature Flags (.env):
├── ENABLE_REDIS_CACHE=true          # Keep for retrieval cache
└── ENABLE_REDIS_SESSIONS=false      # Disable, use PostgreSQL

Code:
├── chat_session.py                  # PostgresChatSessionStore active
└── documents_chat.py                # Use PostgreSQL store
```

---

## 📊 Database Schema (Option A)

### Table 1: `chat_sessions`

```sql
CREATE TABLE chat_sessions (
    -- Primary Key
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- User Information (support both authenticated & anonymous)
    user_id VARCHAR(255),                    -- NULL = anonymous, NOT NULL = authenticated
    is_anonymous BOOLEAN DEFAULT true,       -- Explicit flag for clarity
    
    -- Session Lifecycle
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_activity TIMESTAMP NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMP,                      -- NULL = active
    
    -- Session Context
    session_title VARCHAR(500),              -- Auto-generated from first query
    session_mode VARCHAR(50) DEFAULT 'balanced',
    
    -- Statistics
    message_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    
    -- Metadata (JSONB for flexibility)
    metadata JSONB DEFAULT '{}'::jsonb,
    -- Example: {"source": "web", "language": "vi", "tags": ["bidding"]}
    
    CONSTRAINT valid_mode CHECK (session_mode IN ('fast', 'balanced', 'quality', 'adaptive'))
);

-- Indexes (NO user_ip/user_agent tracking)
CREATE INDEX idx_session_user ON chat_sessions(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_session_anonymous ON chat_sessions(is_anonymous) WHERE is_anonymous = true;
CREATE INDEX idx_session_created ON chat_sessions(created_at DESC);
CREATE INDEX idx_session_last_activity ON chat_sessions(last_activity DESC);
CREATE INDEX idx_session_active ON chat_sessions(ended_at) WHERE ended_at IS NULL;
CREATE INDEX idx_session_metadata_gin ON chat_sessions USING gin(metadata jsonb_path_ops);
```

### Table 2: `chat_messages`

```sql
CREATE TABLE chat_messages (
    -- Primary Key
    id BIGSERIAL PRIMARY KEY,
    
    -- Foreign Key
    session_id UUID NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    
    -- Message Content
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    
    -- Timestamps
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- RAG Context (for assistant messages)
    retrieved_docs JSONB,
    reranker_used VARCHAR(50),
    tokens_used INTEGER,
    latency_ms INTEGER,
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    
    CONSTRAINT valid_role CHECK (role IN ('user', 'assistant', 'system'))
);

-- Indexes
CREATE INDEX idx_messages_session ON chat_messages(session_id, timestamp);
CREATE INDEX idx_messages_timestamp ON chat_messages(timestamp DESC);
CREATE INDEX idx_messages_retrieved_gin ON chat_messages USING gin(retrieved_docs jsonb_path_ops);
```

---

## 👤 User Management Strategy

### Scenario 1: Anonymous Users (Default)

**Flow:**
1. User opens chatbot → No login required
2. Frontend generates `client_session_id` (UUID, stored in localStorage/cookie)
3. First message → Backend creates session with `user_id=NULL`, `is_anonymous=true`
4. Return `session_id` to frontend
5. Subsequent messages use same `session_id`

**Benefits:**
- ✅ Zero friction onboarding
- ✅ Works immediately
- ✅ Can convert to authenticated later

**Limitations:**
- ⚠️ Session lost if localStorage cleared
- ⚠️ Cannot access from different device
- ⚠️ Limited to single browser

### Scenario 2: Authenticated Users (Future)

**Flow:**
1. User logs in → Get `user_id` from auth system
2. Create session with `user_id='user123'`, `is_anonymous=false`
3. Can access sessions from any device
4. Can query: "Show all my conversations"

**Migration Path (Anonymous → Authenticated):**
```sql
-- When user logs in, link anonymous sessions to user_id
UPDATE chat_sessions
SET user_id = 'user123',
    is_anonymous = false,
    metadata = metadata || '{"converted_at": "2025-11-14T20:00:00"}'::jsonb
WHERE session_id IN (
    -- Sessions from same client (tracked via metadata->client_id)
    SELECT session_id FROM chat_sessions
    WHERE metadata->>'client_id' = 'abc-xyz-123'
    AND is_anonymous = true
);
```

### Implementation Phases

**Phase 1 (NOW):** Anonymous only
- Frontend: No auth required
- Backend: Always `user_id=NULL`, `is_anonymous=true`
- Simplest implementation

**Phase 2 (FUTURE):** Add authentication
- Integrate với auth provider (Firebase/Auth0/custom)
- Support `user_id` parameter in endpoints
- Migrate anonymous sessions on login

**Phase 3 (FUTURE):** User profiles
- Link sessions to user accounts
- Show conversation history
- Export conversations

---

## 🗄️ Cold Storage Archive Strategy

### Retention Policy

**Active Storage (PostgreSQL):**
- Sessions từ last 90 days
- Fast access, full query capabilities
- Current `chat_sessions` + `chat_messages` tables

**Cold Storage (S3/Object Storage):**
- Sessions older than 90 days
- Archived as JSON files
- Read-only, slower access
- Cost-effective ($0.01/GB/month vs PostgreSQL $0.10/GB/month)

### Archive Process

**1. Daily Cron Job** (runs at 2 AM):
```sql
-- Find sessions to archive (ended > 90 days ago)
SELECT session_id, user_id, created_at, ended_at, message_count
FROM chat_sessions
WHERE ended_at < NOW() - INTERVAL '90 days'
AND archived = false  -- TODO: Add this column
LIMIT 1000;
```

**2. Export to JSON:**
```python
# scripts/archive_old_sessions.py
def archive_session(session_id):
    # Get session + all messages
    session_data = {
        "session": get_session_metadata(session_id),
        "messages": get_all_messages(session_id),
        "archived_at": datetime.now().isoformat()
    }
    
    # Upload to S3
    s3_key = f"chat_archives/{year}/{month}/{session_id}.json.gz"
    upload_to_s3(json.dumps(session_data), s3_key)
    
    # Mark as archived in DB
    mark_session_archived(session_id, s3_key)
```

**3. Cleanup PostgreSQL:**
```sql
-- After successful S3 upload, delete from PostgreSQL
DELETE FROM chat_sessions
WHERE session_id = '...'
AND archived = true;
-- Messages auto-deleted via CASCADE
```

**4. Restore if Needed:**
```python
# API endpoint: GET /chat/archived/{session_id}
def get_archived_session(session_id):
    # Download from S3
    s3_key = f"chat_archives/{year}/{month}/{session_id}.json.gz"
    data = download_from_s3(s3_key)
    return json.loads(data)
```

### Schema Updates for Archiving

```sql
-- Add to chat_sessions table
ALTER TABLE chat_sessions
ADD COLUMN archived BOOLEAN DEFAULT false,
ADD COLUMN archive_location TEXT;  -- S3 key

CREATE INDEX idx_session_archived ON chat_sessions(archived, ended_at)
WHERE archived = false;
```

---

## 🚀 Implementation Steps

### Phase 1: Database Setup (30 minutes)

**Step 1.1:** Create migration SQL file
- File: `scripts/migrations/001_create_chat_tables.sql`
- Contains: CREATE TABLE statements, indexes, constraints

**Step 1.2:** Run migration
```bash
PGPASSWORD=sakana123 psql -h localhost -U sakana -d rag_bidding_v2 \
  -f scripts/migrations/001_create_chat_tables.sql
```

**Step 1.3:** Verify tables
```bash
psql -c "\d chat_sessions"
psql -c "\d chat_messages"
```

**Files to create:**
- ✅ `scripts/migrations/001_create_chat_tables.sql`

---

### Phase 2: Code Refactoring (1.5 hours)

**Step 2.1:** Update feature flags (5 min)
```python
# .env
ENABLE_REDIS_SESSIONS=false  # Disable Redis sessions

# src/config/feature_flags.py - Already reads from .env ✅
```

**Step 2.2:** Update chat_session.py (15 min)
```python
# TODO: Fix PostgresChatSessionStore to use async SQLAlchemy
# Current: Uses sync sessionmaker
# Target: Use AsyncSession from src.config.database
```

**Step 2.3:** Update documents_chat.py (45 min)
```python
# TODO: Replace RedisChatSessionStore with PostgresChatSessionStore
# Current: Lines 316-330
# Target: 
#   from src.api.chat_session import PostgresChatSessionStore
#   session_store = PostgresChatSessionStore(settings.database_url)
```

**Step 2.4:** Add session title auto-generation (15 min)
```python
# TODO: Generate session_title from first user message
# Example: "Câu hỏi về đấu thầu công trình" (first 50 chars)
```

**Step 2.5:** Add message statistics tracking (10 min)
```python
# TODO: Update message_count, total_tokens in chat_sessions
# After each add_message(), increment counters
```

**Files to modify:**
- ⚠️ `src/api/chat_session.py` (PostgresChatSessionStore class)
- ⚠️ `src/api/routers/documents_chat.py` (endpoints)
- ⚠️ `.env` (ENABLE_REDIS_SESSIONS=false)

---

### Phase 3: Testing (45 minutes)

**Step 3.1:** Unit tests (20 min)
```python
# tests/test_postgres_chat_session.py
def test_create_session():
    store = PostgresChatSessionStore(db_url)
    session_id = store.create_session()
    assert session_id is not None

def test_add_message():
    store.add_message(session_id, "user", "Test message")
    messages = store.get_history(session_id)
    assert len(messages) == 1
```

**Step 3.2:** Integration tests (15 min)
```bash
# Test with running server
curl -X POST http://localhost:8000/chat/create
curl -X POST http://localhost:8000/chat/send -d '{"session_id": "...", "message": "..."}'
curl -X GET http://localhost:8000/chat/history/SESSION_ID
```

**Step 3.3:** Performance tests (10 min)
```python
# Verify < 100ms for typical operations
- create_session: < 50ms
- add_message: < 80ms
- get_history (10 messages): < 100ms
```

**Files to create:**
- ✅ `scripts/tests/test_postgres_chat_session.py`
- ✅ `scripts/tests/test_chat_endpoints.sh`

---

### Phase 4: Cleanup & Documentation (30 minutes)

**Step 4.1:** Remove Redis session code (10 min)
```python
# TODO: Clean up unused RedisChatSessionStore references
# Keep Redis only for retrieval cache
```

**Step 4.2:** Update API documentation (10 min)
```python
# Update docstrings in documents_chat.py
# Mention PostgreSQL storage, persistence
```

**Step 4.3:** Update README (10 min)
```markdown
# Chat Sessions
- Storage: PostgreSQL (persistent)
- Retention: 90 days active + S3 archive
- User types: Anonymous (default) + Authenticated (future)
```

---

### Phase 5 (FUTURE): Cold Storage (2 hours)

**Step 5.1:** Add archive columns
```sql
ALTER TABLE chat_sessions
ADD COLUMN archived BOOLEAN DEFAULT false,
ADD COLUMN archive_location TEXT;
```

**Step 5.2:** Create archive script
```python
# scripts/archive_old_sessions.py
# Daily cron: archive sessions > 90 days to S3
```

**Step 5.3:** Setup S3/MinIO
```bash
# Configure object storage
# Add credentials to .env
```

**Files to create:**
- ⏳ `scripts/archive_old_sessions.py`
- ⏳ `scripts/restore_archived_session.py`

---

## 📁 File Status & TODOs

### 🔴 HIGH PRIORITY - Blocking Migration

#### `src/api/chat_session.py`
**Status:** 🟡 Partially implemented
**TODOs:**
```python
# TODO [CHAT-MIGRATION]: Refactor PostgresChatSessionStore to use async
# Current: Uses sync SQLAlchemy sessionmaker
# Issue: Conflicts with FastAPI async endpoints
# Fix: Use AsyncSession from src.config.database.get_session()
# Estimated: 30 minutes
# Line: 167-267

# TODO [CHAT-MIGRATION]: Add session_title auto-generation
# Generate from first user message (max 50 chars)
# Line: 219 (in create_session method)

# TODO [CHAT-MIGRATION]: Add message_count and total_tokens tracking
# Update chat_sessions after each add_message()
# Line: 237 (in add_message method)
```

#### `src/api/routers/documents_chat.py`
**Status:** 🔴 Using Redis (needs replacement)
**TODOs:**
```python
# TODO [CHAT-MIGRATION]: Replace RedisChatSessionStore with PostgresChatSessionStore
# Line: 316-330
# Current:
#   if ENABLE_REDIS_SESSIONS:
#       session_store = RedisChatSessionStore(...)
# Target:
#   if True:  # Always use PostgreSQL
#       session_store = PostgresChatSessionStore(settings.database_url)
# Estimated: 20 minutes

# TODO [CHAT-MIGRATION]: Update endpoint responses to include session metadata
# Add session_title, message_count to responses
# Lines: 380-450 (all chat endpoints)

# TODO [CHAT-MIGRATION]: Fix uuid → id in SQL queries (DONE earlier)
# Verify all queries use 'id' column not 'uuid'
# Lines: 115, 207
```

#### `.env`
**Status:** 🟡 Has ENABLE_REDIS_SESSIONS=true (needs false)
**TODOs:**
```bash
# TODO [CHAT-MIGRATION]: Disable Redis sessions after PostgreSQL migration
# Change: ENABLE_REDIS_SESSIONS=true → false
# Keep: ENABLE_REDIS_CACHE=true (for retrieval cache)
# Line: 47
```

---

### 🟡 MEDIUM PRIORITY - Schema & Scripts

#### `scripts/migrations/001_create_chat_tables.sql`
**Status:** 🔴 NOT CREATED
**TODOs:**
```sql
-- TODO [CHAT-MIGRATION]: Create this file with schema from plan
-- Contains: chat_sessions + chat_messages tables
-- Run: psql -f scripts/migrations/001_create_chat_tables.sql
-- Estimated: 10 minutes to create + test
```

#### `scripts/tests/test_postgres_chat_session.py`
**Status:** 🔴 NOT CREATED
**TODOs:**
```python
# TODO [CHAT-MIGRATION]: Create unit tests for PostgresChatSessionStore
# Tests: create_session, add_message, get_history, delete_session
# Estimated: 30 minutes
```

#### `scripts/tests/test_chat_endpoints.sh`
**Status:** 🔴 NOT CREATED
**TODOs:**
```bash
# TODO [CHAT-MIGRATION]: Create integration tests for chat endpoints
# Test: POST /chat/create, POST /chat/send, GET /chat/history
# Estimated: 15 minutes
```

---

### 🟢 LOW PRIORITY - Future Enhancements

#### `scripts/archive_old_sessions.py`
**Status:** 🔴 NOT CREATED (Phase 5)
**TODOs:**
```python
# TODO [CHAT-ARCHIVE]: Create cron script for S3 archiving
# Archive sessions older than 90 days
# Estimated: 1.5 hours
# Dependencies: S3/MinIO setup
```

#### `src/api/routers/documents_chat.py` (Authentication)
**Status:** 🔴 NOT IMPLEMENTED (Phase 2 of user management)
**TODOs:**
```python
# TODO [CHAT-AUTH]: Add user_id parameter to chat endpoints
# Support authenticated users
# Estimated: 2 hours
# Dependencies: Auth system (Firebase/Auth0)
```

---

## 🎯 Quick Start Checklist

When ready to implement, follow this order:

- [ ] **Step 1:** Create migration SQL file
  - File: `scripts/migrations/001_create_chat_tables.sql`
  - Copy schema from this document
  
- [ ] **Step 2:** Run migration
  ```bash
  psql -f scripts/migrations/001_create_chat_tables.sql
  ```

- [ ] **Step 3:** Update `chat_session.py`
  - Fix async/sync issues
  - Add session_title generation
  - Add statistics tracking

- [ ] **Step 4:** Update `documents_chat.py`
  - Replace RedisChatSessionStore → PostgresChatSessionStore
  - Test all 4 endpoints

- [ ] **Step 5:** Update `.env`
  - Set `ENABLE_REDIS_SESSIONS=false`

- [ ] **Step 6:** Test
  - Run unit tests
  - Test integration
  - Verify performance

- [ ] **Step 7:** Deploy
  - Restart server
  - Monitor logs
  - Check PostgreSQL storage

---

## 📊 Success Metrics

After migration:
- ✅ All chat endpoints work với PostgreSQL
- ✅ Sessions persist across server restarts
- ✅ Can query sessions by date/user
- ✅ < 100ms latency for typical operations
- ✅ Zero Redis dependency for sessions
- ✅ Anonymous users work out of box

---

## 🔗 Related Documents

- **Schema Details:** `/documents/technical/CHAT_SESSION_DB_SCHEMA.md`
- **Current Code:** `src/api/chat_session.py` (line 167-267)
- **Endpoints:** `src/api/routers/documents_chat.py` (line 316-643)
- **Database Config:** `src/config/database.py`
- **Feature Flags:** `src/config/feature_flags.py`

---

## ⏱️ Time Estimate

| Phase | Task | Time |
|-------|------|------|
| 1 | Database setup | 30 min |
| 2 | Code refactoring | 1.5 hours |
| 3 | Testing | 45 min |
| 4 | Cleanup | 30 min |
| **TOTAL** | **Phase 1-4** | **3h 15min** |
| 5 (Future) | Cold storage | 2 hours |

**Can be done in multiple sessions:**
- Session 1: Phase 1 (30 min)
- Session 2: Phase 2 (1.5 hours)
- Session 3: Phase 3-4 (1h 15min)

---

## 🚦 Status: READY TO IMPLEMENT

All decisions made, schema approved, plan complete. TODOs marked in relevant files.

**Next action:** Create migration SQL file when ready to start.
