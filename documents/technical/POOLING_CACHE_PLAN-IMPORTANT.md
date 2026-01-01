# Kế hoạch Tối ưu hóa Production: Connection Pooling & Redis Cache

**Ngày tạo:** 14/11/2025  
**Trạng thái:** Planning Phase  
**Mục tiêu:** Scale từ 5-10 users → 50+ concurrent users với latency <2s

---

## 🎯 Vấn đề Hiện tại

### Performance Bottlenecks (từ test results)
- **Response time:** 9.6s avg → Cần <2s
- **Concurrent users:** Max 5-10 stable → Cần 50+
- **Success rate:** 37% → Cần 95%+
- **Memory leak:** 20GB (fixed bằng singleton) → 1.75GB ✅

### Root Causes Identified
1. **No Connection Pooling** → Mỗi request tạo DB connection mới
2. **No Query Cache** → Re-embed identical queries
3. **Sequential Processing** → Reranking không parallel (fixed ✅)
4. **No Redis** → Không có L2 cache layer

---

## 📋 Kế hoạch Implementation

### Phase 1: Connection Pooling với pgBouncer (Ưu tiên: HIGH)

**Vấn đề:**
- SQLAlchemy AsyncPG không support QueuePool tốt
- Hiện dùng NullPool → Mỗi request = 1 connection mới
- PostgreSQL max_connections = 100 → Dễ exhaust

**Giải pháp: pgBouncer (External Connection Pooler)**

#### 1.1 Tại sao pgBouncer thay vì SQLAlchemy Pool?

| Feature | SQLAlchemy Pool | pgBouncer |
|---------|----------------|-----------|
| Async support | Limited (NullPool only) | Full support |
| Connection reuse | Per-process | Cross-process |
| Max connections | Limited by app | Shared pool |
| Overhead | High (Python) | Low (C) |
| Production ready | ❌ | ✅ |

**Best Practice:** SQLAlchemy NullPool + pgBouncer = Industry standard (Heroku, Railway, etc.)

#### 1.2 pgBouncer Configuration

**File:** `/etc/pgbouncer/pgbouncer.ini`

```ini
[databases]
rag_bidding_v2 = host=localhost port=5432 dbname=rag_bidding_v2

[pgbouncer]
listen_addr = 127.0.0.1
listen_port = 6432  # pgBouncer port (khác PostgreSQL 5432)
auth_type = trust    # hoặc md5/scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt

# Pool Configuration
pool_mode = transaction  # Recommended cho web apps
max_client_conn = 1000   # Max client connections
default_pool_size = 25   # Connections per database
reserve_pool_size = 10   # Reserve for urgent queries
reserve_pool_timeout = 3

# Performance Tuning
max_db_connections = 50  # Max to PostgreSQL
min_pool_size = 10       # Keep-alive connections
```

**Pool Modes:**
- `session`: 1 connection per client session (safe but limited)
- `transaction`: Reuse connection between transactions (recommended)
- `statement`: Reuse per statement (aggressive, may break some features)

#### 1.3 Application Changes

**Current:**
```python
DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5432/rag_bidding_v2"
```

**With pgBouncer:**
```python
DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:6432/rag_bidding_v2"
#                                                         ^^^^ pgBouncer port
```

**No code changes needed!** Just change port.

#### 1.4 Installation & Setup

```bash
# Install
sudo apt install pgbouncer

# Configure
sudo nano /etc/pgbouncer/pgbouncer.ini
sudo nano /etc/pgbouncer/userlist.txt  # Add: "postgres" "postgres"

# Start
sudo systemctl start pgbouncer
sudo systemctl enable pgbouncer

# Test
psql -h 127.0.0.1 -p 6432 -U postgres -d rag_bidding_v2
```

**Monitoring:**
```bash
# pgBouncer admin console
psql -h 127.0.0.1 -p 6432 -U pgbouncer pgbouncer

# Show pool status
SHOW POOLS;
SHOW STATS;
```

#### 1.5 Expected Improvements

**Before (NullPool):**
- 10 concurrent users × 1 connection each = 10 connections
- Connection time: ~50ms per request
- Total overhead: 500ms per second

**After (pgBouncer):**
- 10 concurrent users → 2-5 active connections (reused)
- Connection time: ~1ms (pool hit)
- Total overhead: ~10ms per second
- **Speedup:** 50x connection efficiency

**Capacity:**
- Max users: 5-10 → 200+ (limited by pool_size × transaction rate)

---

### Phase 2: Redis Cache Implementation (Ưu tiên: MEDIUM)

#### 2.1 Architecture Overview

```
Query → L1 (Memory) → L2 (Redis) → L3 (PostgreSQL) → LLM
        0.1ms          0.3ms        1000ms           3000ms
```

**Cache Layers:**
- **L1 (Process Memory):** LRU cache, 100-500 items, instant
- **L2 (Redis):** Shared cache, TTL-based, cross-instance
- **L3 (PostgreSQL):** Full persistent storage

#### 2.2 Redis Setup

**Installation:**
```bash
# Install Redis
sudo apt install redis-server

# Configure
sudo nano /etc/redis/redis.conf
# Set:
# maxmemory 2gb
# maxmemory-policy allkeys-lru
# save 900 1  # Snapshot every 15min if 1+ key changed

# Start
sudo systemctl start redis
sudo systemctl enable redis

# Test
redis-cli ping  # Should return PONG
```

**Python Dependencies:**
```bash
pip install redis hiredis  # hiredis for C performance
```

#### 2.3 Cache Strategy

**What to Cache:**

1. **Embedding Results** (Highest impact)
   - Key: `embed:{hash(query)}`
   - Value: `[0.123, -0.456, ...]` (1536 floats)
   - TTL: 24 hours
   - Hit rate: 50-70% for common queries
   - **Speedup:** 150ms → 0.3ms (500x)

2. **Retrieval Results**
   - Key: `retrieval:{hash(query)}:{mode}:{k}`
   - Value: JSON of retrieved documents
   - TTL: 1 hour
   - Hit rate: 30-50%
   - **Speedup:** 1000ms → 0.3ms (3,000x)

3. **Chat Sessions**
   - Key: `session:{session_id}`
   - Value: JSON of conversation history
   - TTL: 1-24 hours
   - Hit rate: 100% (all messages)
   - **Benefit:** Persistent, multi-instance

4. **Document Metadata** (Low priority)
   - Key: `doc:{document_id}`
   - Value: JSON metadata
   - TTL: 7 days
   - **Benefit:** Reduce DB load

**What NOT to Cache:**
- LLM responses (non-deterministic)
- User-specific data (privacy)
- Frequently changing data

#### 2.4 Integration Points

**File:** `src/retrieval/cached_retrieval.py` (ALREADY EXISTS ✅)

**Current Status:**
- ✅ Code complete and tested
- ✅ 3-layer cache (L1/L2/L3) implemented
- ✅ 10,000x-140,000x speedup verified
- ❌ NOT integrated in production

**Integration Steps:**

1. **Wrap Vector Store** (30 min)
```python
# src/embedding/store/pgvector_store.py

from src.retrieval.cached_retrieval import CachedVectorStore

# Current (line 9-14):
vector_store = PGVector(...)

# After:
_raw_vector_store = PGVector(...)
vector_store = CachedVectorStore(
    vector_store=_raw_vector_store,
    redis_host="localhost",
    redis_port=6379,
    enable_l1=True,  # Memory cache
    enable_l2=True,  # Redis cache
    l1_maxsize=500,
    ttl_seconds=3600,  # 1 hour
)
```

2. **Add Feature Flag** (15 min)
```python
# src/config/models.py

class Settings(BaseModel):
    # ... existing settings ...
    
    # Cache settings
    enable_cache: bool = True  # Feature flag
    redis_host: str = "localhost"
    redis_port: int = 6379
    cache_ttl_seconds: int = 3600
```

3. **Graceful Fallback** (15 min)
```python
# If Redis fails, fallback to no cache
try:
    vector_store = CachedVectorStore(...)
except RedisConnectionError:
    logger.warning("Redis unavailable, running without cache")
    vector_store = _raw_vector_store
```

#### 2.5 Expected Improvements

**Cache Hit Scenarios:**

| Query Type | Hit Rate | Before | After | Speedup |
|-----------|----------|--------|-------|---------|
| Identical query | 70% | 3000ms | 50ms | 60x |
| Similar query | 50% | 3000ms | 1500ms | 2x |
| New query | 0% | 3000ms | 3000ms | 1x |

**Overall:**
- Average latency: 9.6s → 2-4s (2-4x improvement)
- Cache memory: ~100MB for 1000 queries
- Redis CPU: <5% on modern server

---

### Phase 3: Monitoring & Observability (Ưu tiên: MEDIUM)

#### 3.1 Metrics to Track

**pgBouncer Metrics:**
```sql
-- Check pool status
SHOW POOLS;
-- Output: cl_active, cl_waiting, sv_active, sv_idle, sv_used, maxwait

-- Check stats
SHOW STATS;
-- Output: total_xact_count, total_query_count, total_received, total_sent

-- Alerts:
-- cl_waiting > 10 → Pool exhaustion
-- maxwait > 5s → Slow queries blocking pool
```

**Redis Metrics:**
```bash
redis-cli INFO stats
# keyspace_hits / (keyspace_hits + keyspace_misses) = Hit rate
# Target: >50%

redis-cli INFO memory
# used_memory_human, maxmemory_human
# Alert if >80% maxmemory
```

**Application Metrics:**
```python
# Add to src/retrieval/cached_retrieval.py (already exists)
logger.info(f"Cache stats: L1 hit={l1_hits}/{total} ({hit_rate:.1%})")
logger.info(f"Cache stats: L2 hit={l2_hits}/{total} ({hit_rate:.1%})")
```

#### 3.2 Dashboard (Optional - FastAPI endpoint)

**Add to `src/api/main.py`:**
```python
@app.get("/metrics")
async def get_metrics():
    return {
        "database": await get_db_config().get_pool_status(),
        "cache": vector_store.get_cache_stats(),  # If enabled
        "reranker": {
            "singleton_memory": "1.2GB",  # vs 20GB before
        }
    }
```

---

## 🚀 Rollout Plan

### Week 1: Foundation (Current)
- [x] Fix memory leak (singleton pattern) ✅
- [x] Add OpenAI reranker ✅
- [x] Parallel reranking ✅
- [x] Document + Chat endpoints ✅
- [x] Async database setup ✅

### Week 2: Connection Pooling
- [ ] Day 1-2: Install & configure pgBouncer
- [ ] Day 3: Update DATABASE_URL to use port 6432
- [ ] Day 4: Load testing (50 concurrent users)
- [ ] Day 5: Monitor & tune pool_size

**Success Criteria:**
- ✅ 50+ concurrent users without errors
- ✅ Connection time <10ms (vs 50ms)
- ✅ Success rate >95%

### Week 3: Redis Cache
- [ ] Day 1: Install Redis + test connectivity
- [ ] Day 2: Integrate CachedVectorStore
- [ ] Day 3: Add feature flags + fallback logic
- [ ] Day 4: A/B test (cache on vs off)
- [ ] Day 5: Monitor hit rates & tune TTL

**Success Criteria:**
- ✅ Cache hit rate >50%
- ✅ Average latency <3s (vs 9.6s)
- ✅ Zero cache-related errors

### Week 4: Optimization
- [ ] Tune pgBouncer pool_size based on load
- [ ] Optimize Redis memory (maxmemory-policy)
- [ ] Add monitoring dashboard
- [ ] Load test 100+ users

---

## 🔧 Implementation Checklist

### pgBouncer Setup
```bash
# 1. Install
sudo apt update
sudo apt install pgbouncer

# 2. Configure
sudo tee /etc/pgbouncer/pgbouncer.ini > /dev/null <<EOF
[databases]
rag_bidding_v2 = host=localhost port=5432 dbname=rag_bidding_v2

[pgbouncer]
listen_addr = 127.0.0.1
listen_port = 6432
auth_type = trust
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
reserve_pool_size = 10
max_db_connections = 50
min_pool_size = 10
EOF

# 3. Create userlist
echo '"postgres" "postgres"' | sudo tee /etc/pgbouncer/userlist.txt

# 4. Start
sudo systemctl start pgbouncer
sudo systemctl enable pgbouncer

# 5. Test
psql -h 127.0.0.1 -p 6432 -U postgres -d rag_bidding_v2 -c "SELECT 1;"
```

### Redis Setup
```bash
# 1. Install
sudo apt install redis-server

# 2. Configure
sudo tee -a /etc/redis/redis.conf > /dev/null <<EOF
maxmemory 2gb
maxmemory-policy allkeys-lru
EOF

# 3. Start
sudo systemctl start redis
sudo systemctl enable redis

# 4. Test
redis-cli ping  # Should return PONG
redis-cli set test "hello"
redis-cli get test  # Should return "hello"
```

### Application Updates

**1. Update DATABASE_URL** (when pgBouncer ready):
```bash
# .env file
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:6432/rag_bidding_v2
```

**2. Enable cache** (when Redis ready):
```python
# src/embedding/store/pgvector_store.py
from src.retrieval.cached_retrieval import CachedVectorStore

def bootstrap():
    # ... existing code ...
    
    # Wrap with cache if Redis available
    try:
        global vector_store
        _raw_store = vector_store
        vector_store = CachedVectorStore(
            vector_store=_raw_store,
            redis_host=os.getenv("REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("REDIS_PORT", "6379")),
            enable_l1=True,
            enable_l2=True,
            l1_maxsize=500,
            ttl_seconds=3600,
        )
        logger.info("✅ Vector store cache enabled (L1 + L2)")
    except Exception as e:
        logger.warning(f"⚠️ Running without cache: {e}")
```

---

## 📊 Performance Projections

### Current State (Post-Singleton)
- Latency: 9.6s avg
- Concurrent users: 5-10 max
- Success rate: 37%
- Memory: 1.75GB (good!)

### After pgBouncer (Week 2)
- Latency: 7-8s (connection overhead removed)
- Concurrent users: 50+
- Success rate: 90%+
- Memory: 1.75GB

### After Redis Cache (Week 3)
- Latency: 2-4s (50% cache hits)
- Concurrent users: 100+
- Success rate: 95%+
- Memory: 1.75GB + 100MB cache

### Optimized (Week 4)
- Latency: <2s target
- Concurrent users: 200+
- Success rate: 98%+
- Memory: <2GB total

---

## ⚠️ Risks & Mitigation

### Risk 1: pgBouncer Breaks Existing Features
**Mitigation:**
- Use `transaction` mode (safest)
- Test all endpoints before production
- Keep fallback: `postgresql://localhost:5432` (direct)

### Risk 2: Redis Memory Exhaustion
**Mitigation:**
- Set `maxmemory 2gb` hard limit
- Use `allkeys-lru` eviction policy
- Monitor with `INFO memory`

### Risk 3: Cache Invalidation Issues
**Mitigation:**
- Short TTL (1 hour) for retrieval cache
- Longer TTL (24 hours) for embeddings (immutable)
- Manual flush endpoint: `redis-cli FLUSHDB`

### Risk 4: Stale Cache After Data Updates
**Mitigation:**
- Add cache invalidation hook in document upload
- Or just use short TTL (1 hour acceptable)

---

## 🎓 References & Resources

### pgBouncer
- Docs: https://www.pgbouncer.org/config.html
- Best practices: https://wiki.postgresql.org/wiki/PgBouncer
- Heroku guide: https://devcenter.heroku.com/articles/best-practices-pgbouncer-configuration

### Redis
- Docs: https://redis.io/docs/
- LRU eviction: https://redis.io/docs/reference/eviction/
- Python client: https://redis-py.readthedocs.io/

### SQLAlchemy + Async
- AsyncPG driver: https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.asyncpg
- Pooling: https://docs.sqlalchemy.org/en/20/core/pooling.html

---

## 📝 Notes

- **pgBouncer vs SQLAlchemy Pool:** Dùng cả hai! pgBouncer ở network level, SQLAlchemy pool ở application level
- **Redis Persistence:** Mặc định Redis có RDB snapshots, nhưng cache có thể rebuild từ PostgreSQL
- **Cost:** pgBouncer + Redis chạy trên cùng server → Không tăng chi phí
- **Alternative:** Nếu deploy lên cloud (Heroku, Railway), họ có managed pooling + Redis addon

---

**Status:** 📋 PLANNING  
**Next Action:** Install pgBouncer (Week 2) sau khi test current endpoints  
**Owner:** @sakanaowo  
**Last Updated:** 2025-11-14
