# 🚨 IMPORTANT: Chat Session Implementation

**Status:** 🟡 READY TO IMPLEMENT  
**Priority:** HIGH  
**Estimated Time:** 3-4 hours

---

## 📋 Quick Start

**Bắt đầu từ đâu?**

1. ⭐ **[TODO_CHAT_SESSION_MIGRATION.md](./TODO_CHAT_SESSION_MIGRATION.md)** - Checklist & TODOs
2. 📘 **[CHAT_SESSION_POSTGRESQL_PLAN.md](./CHAT_SESSION_POSTGRESQL_PLAN.md)** - Full implementation plan
3. 📊 **[CHAT_SESSION_DB_SCHEMA.md](./CHAT_SESSION_DB_SCHEMA.md)** - Database schema details

---

## 🎯 What is This?

Migration plan để chuyển chat sessions từ **Redis** sang **PostgreSQL**:

- ✅ Persistent storage (không mất data khi restart)
- ✅ Queryable history (search, filter conversations)
- ✅ Support anonymous + authenticated users
- ✅ Archive to cold storage (S3) after 90 days
- ✅ ACID guarantees

---

## 📁 Files in This Folder

### 1. `TODO_CHAT_SESSION_MIGRATION.md` ⭐ START HERE
**Purpose:** Quick reference checklist

**Content:**
- All TODOs marked in code
- File-by-file breakdown
- Implementation order
- Time estimates

**When to use:** Daily checklist khi implement

---

### 2. `CHAT_SESSION_POSTGRESQL_PLAN.md` 📘 FULL PLAN
**Purpose:** Complete implementation guide

**Content:**
- Architecture overview (750+ lines)
- User management strategy (anonymous vs authenticated)
- Cold storage architecture (S3 archiving)
- Phase-by-phase implementation steps
- Code examples, queries, testing strategy

**When to use:** Reference khi implement từng phase

---

### 3. `CHAT_SESSION_DB_SCHEMA.md` 📊 SCHEMA DETAILS
**Purpose:** Database design analysis

**Content:**
- Current database state (langchain_pg_embedding analysis)
- Proposed schema (Option A vs Option B)
- Query examples
- Storage projections
- Performance estimates

**When to use:** Khi tạo migration SQL hoặc query database

---

## ✅ Implementation Checklist

### Phase 1: Database Setup (30 min)
- [ ] Create `scripts/migrations/001_create_chat_tables.sql`
- [ ] Run migration
- [ ] Verify tables created

### Phase 2: Code Refactoring (1.5 hours)
- [ ] Update `src/api/chat_session.py` (3 TODOs)
- [ ] Update `src/api/routers/documents_chat.py` (3 TODOs)
- [ ] Keep Redis enabled during testing

### Phase 3: Testing (45 min)
- [ ] Create unit tests
- [ ] Create integration tests
- [ ] Performance testing

### Phase 4: Deploy (30 min)
- [ ] Disable Redis sessions in `.env`
- [ ] Restart server
- [ ] Monitor PostgreSQL

---

## 🔗 Related Code Files

**Marked with TODOs:**
- `src/api/chat_session.py` - Line 173, 226, 248
- `src/api/routers/documents_chat.py` - Line 312, 342, 380-643
- `.env` - Line 47

**Search TODOs:**
```bash
grep -r "TODO \[CHAT-MIGRATION\]" src/
```

---

## 📊 Key Decisions Made

1. ✅ **PostgreSQL** (NOT Redis) for sessions
2. ✅ **Option A schema** (2 tables: chat_sessions + chat_messages)
3. ✅ **Support both** anonymous + authenticated users
4. ✅ **No tracking** of user_ip/user_agent (privacy)
5. ✅ **Archive to S3** after 90 days

---

## 🚦 Current Status

**What's Done:**
- ✅ Schema designed and approved
- ✅ Implementation plan complete
- ✅ TODOs marked in code
- ✅ User management strategy defined
- ✅ Archive strategy planned

**What's Next:**
- ⏳ Create migration SQL file
- ⏳ Refactor code to async
- ⏳ Test thoroughly
- ⏳ Deploy to production

---

## ⚠️ Important Notes

- **Redis still used for:** Retrieval cache (keep ENABLE_REDIS_CACHE=true)
- **No downtime deployment:** New tables, existing code continues
- **Rollback plan:** Keep Redis enabled until PostgreSQL proven stable
- **Time estimate:** 3-4 hours total (can split into multiple sessions)

---

## 📞 Need Help?

1. Read TODO_CHAT_SESSION_MIGRATION.md for quick reference
2. Check CHAT_SESSION_POSTGRESQL_PLAN.md for detailed steps
3. Review CHAT_SESSION_DB_SCHEMA.md for schema questions

---

**Created:** 2025-11-14  
**Status:** 🟡 READY - Chưa bắt đầu implement  
**Next Action:** Create migration SQL when ready
