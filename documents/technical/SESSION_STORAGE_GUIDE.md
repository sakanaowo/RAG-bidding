# 💬 Chat Sessions Storage Guide

**Status:** ✅ Redis Storage Enabled  
**Storage:** Redis Database 1 (localhost:6379)  
**Persistence:** ✅ Sessions survive server restart

---

## 🗄️ Lưu trữ Sessions Ở Đâu?

### Current Architecture: Redis Only

```
Chat Session Flow:

User sends message
    ↓
POST /api/chat/sessions/{id}/messages
    ↓
RedisChatSessionStore
    ↓
Redis DB 1 (localhost:6379)
    ├─ Key: session:{session_id}
    └─ Value: {user_id, messages[], created_at, ...}
```

**Không có PostgreSQL schema cho sessions!**
- ✅ Redis làm **source of truth** duy nhất
- ✅ TTL tự động xóa sessions cũ (1 hour)
- ✅ Đơn giản, nhanh, đủ dùng cho development

---

## 📊 Session Data Structure

### Redis Storage Format

**Key Pattern:**
```
session:{uuid}
```

**Value (JSON):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user123",
  "created_at": "2025-11-14T10:30:00Z",
  "last_activity": "2025-11-14T10:35:00Z",
  "messages": [
    {
      "role": "user",
      "content": "Điều kiện tham gia đấu thầu?",
      "timestamp": "2025-11-14T10:30:00Z",
      "metadata": {}
    },
    {
      "role": "assistant",
      "content": "Theo Luật Đấu thầu 2023...",
      "timestamp": "2025-11-14T10:30:05Z",
      "metadata": {
        "sources": ["doc1", "doc2"],
        "processing_time_ms": 3500
      }
    }
  ]
}
```

### TTL (Time-to-Live)

**Default:** 3600 seconds (1 hour)

```python
# src/config/feature_flags.py
SESSION_TTL_SECONDS = 3600
```

**Behavior:**
- Session auto-deleted after 1 hour of inactivity
- TTL refreshed on each message (sliding window)
- No manual cleanup needed

---

## 🔍 Xem Sessions Trong Redis

### Redis CLI Commands

```bash
# 1. Connect to Redis DB 1 (sessions)
redis-cli -n 1

# 2. List all active sessions
KEYS session:*

# 3. Get specific session data
GET session:550e8400-e29b-41d4-a716-446655440000

# 4. Check session TTL (remaining time)
TTL session:550e8400-e29b-41d4-a716-446655440000
# Output: 3200 (seconds remaining)

# 5. Count total sessions
DBSIZE

# 6. Delete specific session
DEL session:550e8400-e29b-41d4-a716-446655440000

# 7. Clear ALL sessions (WARNING!)
FLUSHDB
```

### Pretty Print Session Data

```bash
# Get and format session JSON
redis-cli -n 1 GET "session:550e8400-..." | python -m json.tool
```

---

## 🚀 API Usage Examples

### 1. Create Session

```bash
# Request
curl -X POST "http://localhost:8000/api/chat/sessions?user_id=user123"

# Response
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-11-14T10:30:00.123Z"
}
```

**Redis Entry Created:**
```
Key: session:550e8400-e29b-41d4-a716-446655440000
TTL: 3600 seconds
```

### 2. Send Message

```bash
# Request
curl -X POST "http://localhost:8000/api/chat/sessions/550e8400-.../messages" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Điều kiện tham gia đấu thầu?",
    "metadata": {"source": "web"}
  }'

# Response
{
  "session_id": "550e8400-...",
  "user_message": "Điều kiện tham gia đấu thầu?",
  "assistant_response": "Theo Luật Đấu thầu 2023...",
  "sources": ["doc1", "doc2", "doc3"],
  "processing_time_ms": 3500
}
```

**Redis Updated:**
- 2 messages added (user + assistant)
- TTL refreshed to 3600 seconds
- `last_activity` updated

### 3. Get History

```bash
# Request
curl "http://localhost:8000/api/chat/sessions/550e8400-.../history?max_messages=10"

# Response
{
  "session_id": "550e8400-...",
  "messages": [
    {
      "role": "user",
      "content": "Điều kiện tham gia đấu thầu?",
      "timestamp": "2025-11-14T10:30:00Z"
    },
    {
      "role": "assistant",
      "content": "Theo Luật Đấu thầu 2023...",
      "timestamp": "2025-11-14T10:30:05Z",
      "metadata": {
        "sources": ["doc1", "doc2"]
      }
    }
  ],
  "total_messages": 2
}
```

### 4. List Active Sessions

```bash
# Request
curl "http://localhost:8000/api/chat/sessions?user_id=user123"

# Response
{
  "sessions": [
    {
      "session_id": "550e8400-...",
      "created_at": "2025-11-14T10:30:00Z"
    },
    {
      "session_id": "660f9500-...",
      "created_at": "2025-11-14T09:15:00Z"
    }
  ],
  "total": 2
}
```

### 5. Delete Session

```bash
# Request
curl -X DELETE "http://localhost:8000/api/chat/sessions/550e8400-..."

# Response
{
  "message": "Session 550e8400-... deleted"
}
```

---

## 🔄 Multi-turn Conversation Example

```bash
# 1. Create session
SESSION_ID=$(curl -s -X POST "http://localhost:8000/api/chat/sessions?user_id=user123" | jq -r '.session_id')
echo "Session created: $SESSION_ID"

# 2. First message
curl -X POST "http://localhost:8000/api/chat/sessions/$SESSION_ID/messages" \
  -H "Content-Type: application/json" \
  -d '{"message": "Điều kiện tham gia đấu thầu?"}'

# 3. Follow-up message (context-aware)
curl -X POST "http://localhost:8000/api/chat/sessions/$SESSION_ID/messages" \
  -H "Content-Type: application/json" \
  -d '{"message": "Giải thích rõ hơn về điều kiện tài chính"}'

# 4. Check full conversation
curl "http://localhost:8000/api/chat/sessions/$SESSION_ID/history" | jq .

# 5. Clean up
curl -X DELETE "http://localhost:8000/api/chat/sessions/$SESSION_ID"
```

---

## 📊 Monitoring Sessions

### Check Active Sessions Count

```bash
# Redis DB 1
redis-cli -n 1 DBSIZE
# Output: (integer) 15  → 15 active sessions
```

### Memory Usage

```bash
redis-cli -n 1 INFO memory | grep used_memory_human
# Output: used_memory_human:2.45M
```

### Session Activity

```bash
# Watch sessions being created/deleted
redis-cli -n 1 MONITOR | grep session
```

### Export All Sessions (Backup)

```bash
# Get all session keys
redis-cli -n 1 KEYS "session:*" > session_keys.txt

# Export each session
while read key; do
  redis-cli -n 1 GET "$key" >> sessions_backup.json
  echo "" >> sessions_backup.json
done < session_keys.txt
```

---

## ⚙️ Configuration

### File: `src/config/feature_flags.py`

```python
# Session settings
ENABLE_REDIS_SESSIONS = True  # ✅ Enabled
SESSION_TTL_SECONDS = 3600  # 1 hour
SESSION_MAX_MESSAGES = 100  # Max messages per session
REDIS_DB_SESSIONS = 1  # Separate DB from cache
```

### File: `src/api/chat_session.py`

```python
class RedisChatSessionStore:
    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 1,  # DB 1 for sessions
        session_ttl: int = 3600,  # 1 hour
    ):
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True,
        )
```

---

## 🎯 Production Considerations

### Persistence Options

**Current: Redis Only** ✅
- Pros: Fast, simple, TTL auto-cleanup
- Cons: Lost if Redis crashes (rare)

**Option 1: Redis with RDB Snapshots** (Recommended)
```bash
# /etc/redis/redis.conf
save 900 1      # Save after 15 min if ≥1 key changed
save 300 10     # Save after 5 min if ≥10 keys changed
save 60 10000   # Save after 1 min if ≥10000 keys changed
```

**Option 2: Hybrid (Redis + PostgreSQL)**
- Write to both: Fast Redis + Persistent PostgreSQL
- Read from: Redis (fast path)
- Fallback to: PostgreSQL if Redis miss
- **Not implemented yet** - Redis-only is sufficient

### Redis High Availability

**For production at scale:**

```bash
# Option 1: Redis Sentinel (auto-failover)
# - Master-Replica setup
# - Auto-promote replica if master fails

# Option 2: Redis Cluster (horizontal scaling)
# - Shard sessions across multiple nodes
# - Handle millions of sessions

# Option 3: Managed Redis (AWS ElastiCache, Redis Cloud)
# - Automatic backups
# - Multi-AZ replication
```

**Current setup:** Single Redis instance (fine for <10K sessions)

---

## 🚨 Troubleshooting

### Session Not Found

**Symptom:** `404 Session not found`

**Causes:**
1. Session TTL expired (>1 hour inactive)
2. Server restarted without Redis persistence
3. Wrong session_id

**Debug:**
```bash
# Check if session exists in Redis
redis-cli -n 1 EXISTS session:550e8400-...
# 1 = exists, 0 = not found

# Check TTL
redis-cli -n 1 TTL session:550e8400-...
# -2 = expired/deleted, -1 = no TTL, >0 = seconds remaining
```

### Sessions Disappearing Too Fast

**Problem:** TTL too short

**Solution:**
```python
# src/config/feature_flags.py
SESSION_TTL_SECONDS = 7200  # 2 hours instead of 1
```

### Redis Out of Memory

**Symptom:** `OOM command not allowed`

**Solution 1: Increase maxmemory**
```bash
redis-cli CONFIG SET maxmemory 1gb
```

**Solution 2: Enable eviction policy**
```bash
# Evict sessions with nearest expiry
redis-cli CONFIG SET maxmemory-policy volatile-ttl
```

**Solution 3: Reduce TTL**
```python
SESSION_TTL_SECONDS = 1800  # 30 min
```

---

## 📋 Testing Sessions

### Manual Test Script

```bash
#!/bin/bash
# test_sessions.sh

BASE_URL="http://localhost:8000/api"

echo "1. Creating session..."
SESSION=$(curl -s -X POST "$BASE_URL/chat/sessions?user_id=test" | jq -r '.session_id')
echo "   Session ID: $SESSION"

echo "2. Sending message..."
curl -s -X POST "$BASE_URL/chat/sessions/$SESSION/messages" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}' | jq .

echo "3. Checking Redis..."
redis-cli -n 1 EXISTS "session:$SESSION"
redis-cli -n 1 TTL "session:$SESSION"

echo "4. Getting history..."
curl -s "$BASE_URL/chat/sessions/$SESSION/history" | jq .

echo "5. Deleting session..."
curl -s -X DELETE "$BASE_URL/chat/sessions/$SESSION"

echo "6. Verify deleted..."
redis-cli -n 1 EXISTS "session:$SESSION"
```

---

## 🎓 Summary

**Câu hỏi: Sessions được lưu ở đâu?**

**Trả lời:**
- ✅ **Redis Database 1** (localhost:6379, DB=1)
- ✅ Key format: `session:{uuid}`
- ✅ TTL: 3600 seconds (1 hour)
- ✅ Persistent qua Redis RDB snapshots
- ❌ **KHÔNG có PostgreSQL schema**
- ❌ Không cần tạo table `chat_sessions`

**Trade-offs:**
- ✅ Pro: Nhanh (sub-ms), đơn giản, auto-cleanup
- ⚠️ Con: Lost nếu Redis crash mà không có backup
- 💡 Giải pháp: Enable Redis persistence (RDB/AOF)

**For production:** Enable Redis persistence trong `/etc/redis/redis.conf`

---

**Last Updated:** 2025-11-14  
**Status:** ✅ Production Ready (with Redis persistence enabled)
