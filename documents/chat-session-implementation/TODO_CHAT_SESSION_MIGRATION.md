# Chat Session Migration - TODO Summary

## 🎯 Quick Reference

**Goal:** Migrate chat sessions from Redis → PostgreSQL  
**Status:** 🟡 PLANNED - Ready to implement  
**Estimated Time:** 3-4 hours total  
**Full Plan:** `/documents/technical/implementation-plans/CHAT_SESSION_POSTGRESQL_PLAN.md`

---

## 📁 Files Marked with TODOs

### 🔴 HIGH PRIORITY (Blocking Migration)

#### 1. `src/api/chat_session.py`
**Status:** 🟡 Partially implemented, needs refactoring

**TODOs:**
- [ ] **[CHAT-MIGRATION]() Line 173:** Refactor PostgresChatSessionStore to async
  - Current: Uses sync SQLAlchemy sessionmaker
  - Target: Use AsyncSession from src.config.database
  - **Time:** 30 minutes

- [ ] **[CHAT-MIGRATION] Line 226:** Add session_title auto-generation
  - Generate from first user message (max 50 chars)
  - **Time:** 10 minutes

- [ ] **[CHAT-MIGRATION] Line 248:** Add statistics tracking
  - Update message_count, total_tokens in chat_sessions table
  - **Time:** 10 minutes

#### 2. `src/api/routers/documents_chat.py`
**Status:** 🔴 Using Redis, needs replacement

**TODOs:**
- [ ] **[CHAT-MIGRATION] Line 312:** Replace Redis with PostgreSQL
  - Replace RedisChatSessionStore → PostgresChatSessionStore
  - Update get_session_store() function
  - **Time:** 20 minutes

- [ ] **[CHAT-MIGRATION] Line 342:** Remove Redis dependency
  - Clean up RedisChatSessionStore imports and references
  - **Time:** 10 minutes

- [ ] **[CHAT-MIGRATION] Lines 380-643:** Update endpoints
  - Add session_title to responses
  - Add message_count metadata
  - **Time:** 30 minutes

#### 3. `.env`
**Status:** 🟡 Redis enabled, needs to disable after migration

**TODOs:**
- [ ] **[CHAT-MIGRATION] Line 47:** Disable Redis sessions
  - Change: `ENABLE_REDIS_SESSIONS=true` → `false`
  - **Only after PostgreSQL migration complete**
  - **Time:** 1 minute

---

### 🟡 MEDIUM PRIORITY (Schema & Tests)

#### 4. `scripts/migrations/001_create_chat_tables.sql`
**Status:** 🔴 NOT CREATED

**TODOs:**
- [ ] **[CHAT-MIGRATION]** Create migration SQL file
  - Copy schema from CHAT_SESSION_POSTGRESQL_PLAN.md
  - Tables: chat_sessions + chat_messages
  - Indexes: 8 indexes for performance
  - **Time:** 10 minutes

#### 5. `scripts/tests/test_postgres_chat_session.py`
**Status:** 🔴 NOT CREATED

**TODOs:**
- [ ] **[CHAT-MIGRATION]** Create unit tests
  - test_create_session()
  - test_add_message()
  - test_get_history()
  - test_delete_session()
  - **Time:** 30 minutes

#### 6. `scripts/tests/test_chat_endpoints.sh`
**Status:** 🔴 NOT CREATED

**TODOs:**
- [ ] **[CHAT-MIGRATION]** Create integration tests
  - Test POST /chat/create
  - Test POST /chat/send
  - Test GET /chat/history
  - Test DELETE /chat/delete
  - **Time:** 15 minutes

---

### 🟢 LOW PRIORITY (Future Enhancements)

#### 7. `scripts/archive_old_sessions.py`
**Status:** 🔴 NOT CREATED (Phase 5 - Future)

**TODOs:**
- [ ] **[CHAT-ARCHIVE]** Create archive script
  - Archive sessions > 90 days to S3
  - Daily cron job
  - **Time:** 1.5 hours
  - **Dependencies:** S3/MinIO setup

#### 8. Authentication Integration (Future)
**Status:** 🔴 NOT IMPLEMENTED

**TODOs:**
- [ ] **[CHAT-AUTH]** Add user_id support
  - Integrate auth provider (Firebase/Auth0)
  - Update endpoints to accept user_id
  - Migration path for anonymous → authenticated
  - **Time:** 2 hours

---

## ✅ Implementation Checklist

When ready to start, follow this order:

### Phase 1: Database (30 min)
- [ ] Create `scripts/migrations/001_create_chat_tables.sql`
- [ ] Run migration: `psql -f scripts/migrations/001_create_chat_tables.sql`
- [ ] Verify: `psql -c "\d chat_sessions"`

### Phase 2: Code (1.5 hours)
- [ ] Update `src/api/chat_session.py` (3 TODOs)
- [ ] Update `src/api/routers/documents_chat.py` (3 TODOs)
- [ ] Keep `.env` ENABLE_REDIS_SESSIONS=true (disable later)

### Phase 3: Testing (45 min)
- [ ] Create unit tests
- [ ] Create integration tests
- [ ] Run all tests

### Phase 4: Deploy (30 min)
- [ ] Update `.env`: ENABLE_REDIS_SESSIONS=false
- [ ] Restart server
- [ ] Verify all endpoints work
- [ ] Monitor PostgreSQL storage

---

## 🔍 Quick Search Commands

Find all TODOs related to chat migration:

```bash
# Search in code
grep -r "TODO \[CHAT-MIGRATION\]" src/

# Search in config
grep -r "TODO \[CHAT-MIGRATION\]" .env

# Count TODOs
grep -r "TODO \[CHAT-" . | wc -l
```

---

## 📚 Related Documents

1. **Full Implementation Plan:**  
   `/documents/technical/implementation-plans/CHAT_SESSION_POSTGRESQL_PLAN.md`
   - Complete schema details
   - User management strategy
   - Cold storage architecture
   - Query examples
   - Performance estimates

2. **Database Schema Analysis:**  
   `/documents/technical/CHAT_SESSION_DB_SCHEMA.md`
   - Current database state
   - Proposed schema comparison
   - Storage projections

3. **Current Code:**
   - Session store: `src/api/chat_session.py` (line 167-267)
   - Endpoints: `src/api/routers/documents_chat.py` (line 312-643)
   - Database config: `src/config/database.py`

---

## 🚦 Current Status

**Decision Made:**
- ✅ PostgreSQL for chat sessions (not Redis)
- ✅ Option A schema (2 tables)
- ✅ Support anonymous + authenticated users
- ✅ Archive to cold storage (S3)
- ✅ No user_ip/user_agent tracking

**Next Steps:**
1. ⏳ Wait for implementation decision
2. ⏳ Create migration SQL when ready
3. ⏳ Refactor code
4. ⏳ Test
5. ⏳ Deploy

**Blocked By:**
- Nothing - Ready to implement anytime

---

## 💡 Notes

- **Redis still used:** For retrieval cache only (ENABLE_REDIS_CACHE=true)
- **No downtime:** New tables, existing code continues working
- **Gradual migration:** Can test PostgreSQL alongside Redis
- **Rollback plan:** Keep Redis enabled until PostgreSQL proven stable

---

**Last Updated:** 2025-11-14  
**Created By:** Implementation planning session  
**Status:** 🟡 READY TO IMPLEMENT
