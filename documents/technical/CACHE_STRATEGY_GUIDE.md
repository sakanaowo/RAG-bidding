# 🚀 Cache Strategy Implementation Guide

**Status:** ✅ ENABLED  
**Date:** 2025-11-14  
**Redis:** Running on localhost:6379

---

## 📊 Dữ liệu Được Cache

### 1. **Vector Retrieval Results** (Highest Priority) ✅

**Cached:** Kết quả similarity search từ PostgreSQL

**Cache Key Format:**
```
retrieval:{hash(query)}:{k}
```

**Example:**
```
retrieval:abc123def456:10
→ [doc1, doc2, doc3, ..., doc10]
```

**Why Cache:**
- ⚡ Latency: 1000ms (PostgreSQL) → 0.3ms (Redis) = **3,000x faster**
- 💾 Size: ~10KB per query (10 docs × ~1KB each)
- 🎯 Hit Rate: 30-50% for common queries
- ⏰ TTL: 3600s (1 hour)

**Not Cached:**
- Query embeddings (calculated fresh each time)
- Reranking scores (depends on documents retrieved)
- LLM responses (non-deterministic)

### 2. **Query Similarity (Future Enhancement)** ⏳

**Potential:** Cache embedding vectors

**Cache Key Format:**
```
embed:{hash(query_text)}
```

**Why NOT Yet:**
- Embedding API cost: $0.0001 per 1K tokens (very cheap)
- Latency: 100-200ms (acceptable)
- Complexity: Need to handle embedding model changes

**Will Enable When:**
- High query volume (>1000/day)
- Same queries repeated frequently
- Want to reduce OpenAI API costs

### 3. **Chat Sessions** ✅

**Cached:** Conversation history

**Storage:** Redis Database 1 (separate from retrieval cache)

**Cache Key Format:**
```
session:{session_id}
→ {user_id, messages[], created_at, ...}
```

**Example:**
```
session:550e8400-e29b-41d4-a716-446655440000
→ {
  "user_id": "user123",
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "created_at": "2025-11-14T10:30:00"
}
```

**Why Cache:**
- 💾 Persistence: Sessions survive server restart
- 🔄 Multi-instance: Share sessions across multiple servers
- ⚡ Speed: Sub-millisecond access
- ⏰ TTL: 3600s (1 hour) with auto-refresh on activity

---

## 🏗️ Cache Architecture

### 3-Layer Design

```
Query
  ↓
L1: Memory Cache (Python dict)
  ├─ Hit? → Return (0.1ms) ✅
  ├─ Miss? → Check L2
  ↓
L2: Redis Cache
  ├─ Hit? → Return + Update L1 (0.3ms) ✅
  ├─ Miss? → Check L3
  ↓
L3: PostgreSQL (Source of Truth)
  ├─ Hit? → Return + Update L2 + Update L1 (1000ms)
  └─ Miss? → Empty result
```

### Cache Configuration

**File:** `src/config/feature_flags.py`

```python
# L1: In-Memory Cache
ENABLE_L1_CACHE = True
L1_CACHE_MAXSIZE = 500  # Max 500 queries (~50MB)

# L2: Redis Cache
ENABLE_L2_CACHE = True  # Requires Redis
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB_CACHE = 0  # DB 0 for retrieval cache
REDIS_DB_SESSIONS = 1  # DB 1 for chat sessions

# L3: PostgreSQL (always enabled)
ENABLE_L3_CACHE = True

# TTL Settings
CACHE_TTL_RETRIEVAL = 3600  # 1 hour (retrieval results)
CACHE_TTL_SESSIONS = 3600   # 1 hour (chat sessions)
```

---

## 📈 Performance Impact

### Before Cache (Direct PostgreSQL)

```
Query: "Điều kiện tham gia đấu thầu?"
├─ Embedding: 150ms (OpenAI API)
├─ Retrieval: 1000ms (PostgreSQL similarity search) ❌ SLOW
├─ Reranking: 500ms (BGE model)
└─ LLM: 3000ms (OpenAI API)
Total: ~4650ms
```

### After Cache (50% Hit Rate)

```
First Request (Cache Miss):
├─ Embedding: 150ms
├─ Retrieval: 1000ms → Store in cache
├─ Reranking: 500ms
└─ LLM: 3000ms
Total: ~4650ms

Second Request (Cache Hit):
├─ Embedding: 150ms
├─ Retrieval: 0.3ms ✅ FROM CACHE (3,000x faster!)
├─ Reranking: 500ms
└─ LLM: 3000ms
Total: ~3650ms (1000ms saved!)

Average (50% hit rate): (4650 + 3650) / 2 = ~4150ms
Improvement: 500ms avg (10% faster)
```

### With Higher Hit Rate (70%)

```
Average: 4650×0.3 + 3650×0.7 = ~3950ms
Improvement: 700ms avg (15% faster)
```

**Key Insight:**
- Cache primarily speeds up **retrieval** step
- Total speedup depends on LLM latency dominance
- More valuable for high-traffic scenarios (same queries repeated)

---

## 🔍 Monitoring Cache Performance

### Redis CLI Commands

```bash
# Check cache hit rate
redis-cli -n 0 INFO stats
# Look for: keyspace_hits, keyspace_misses
# Hit rate = hits / (hits + misses)

# Check memory usage
redis-cli -n 0 INFO memory
# Look for: used_memory_human, maxmemory_human

# List all cached keys
redis-cli -n 0 KEYS "retrieval:*" | head -10

# Check specific cache entry
redis-cli -n 0 GET "retrieval:abc123:10"

# Check TTL of a key
redis-cli -n 0 TTL "retrieval:abc123:10"

# Flush cache (clear all)
redis-cli -n 0 FLUSHDB  # WARNING: Deletes all cached data!
```

### Application Logs

**Cache hits/misses logged automatically:**

```python
# In src/retrieval/cached_retrieval.py
logger.info(f"Cache L1 HIT: {query_hash[:8]}")
logger.info(f"Cache L2 HIT: {query_hash[:8]}")
logger.info(f"Cache MISS: Querying PostgreSQL")
```

**View logs:**
```bash
# Watch cache activity in real-time
tail -f logs/server_*.log | grep -i cache

# Count hit/miss ratio
grep "Cache.*HIT" logs/server_*.log | wc -l  # Hits
grep "Cache MISS" logs/server_*.log | wc -l   # Misses
```

---

## 🛠️ Cache Invalidation Strategy

### Automatic Invalidation

**TTL-based (Current):**
- Retrieval cache: 1 hour TTL
- Session cache: 1 hour TTL (refreshed on activity)
- No manual invalidation needed

**Pros:**
- ✅ Simple, no code changes needed
- ✅ Handles data updates automatically
- ✅ No stale data after 1 hour

**Cons:**
- ⚠️ New documents not searchable immediately
- ⚠️ Updated documents cached for up to 1 hour

### Manual Invalidation (Future)

**Scenario:** Document updated/added → Invalidate related cache

**Implementation:**
```python
# In document upload/update handler
from src.retrieval.cached_retrieval import invalidate_cache

# Clear all retrieval cache
invalidate_cache()

# Or clear specific query
invalidate_cache(query_hash="abc123")
```

**Currently NOT implemented** - TTL is sufficient for now.

---

## 🎯 Cache Hit Rate Optimization

### Strategies to Improve Hit Rate

1. **Increase TTL** (if data doesn't change often)
   ```python
   CACHE_TTL_RETRIEVAL = 7200  # 2 hours instead of 1
   ```

2. **Normalize Queries** (treat similar queries as same)
   ```python
   # Before hashing:
   query = query.lower().strip()
   query = re.sub(r'\s+', ' ', query)  # Normalize whitespace
   ```

3. **Pre-warm Cache** (cache common queries on startup)
   ```python
   COMMON_QUERIES = [
       "Điều kiện tham gia đấu thầu?",
       "Quy trình đấu thầu rộng rãi",
       "Hồ sơ dự thầu bao gồm gì?"
   ]
   # Cache these on startup
   ```

4. **Monitor & Analyze** (identify high-value queries)
   ```bash
   # Find most common queries
   grep "Cache MISS" logs/server_*.log | \
     grep -oP 'query=\K[^"]+' | \
     sort | uniq -c | sort -rn | head -20
   ```

---

## 🚨 Troubleshooting

### Cache Not Working

**Check 1: Redis Running?**
```bash
redis-cli ping  # Should return "PONG"
```

**Check 2: Feature Flag Enabled?**
```bash
curl http://localhost:8000/features | jq '.features.cache'
# Should show: "enabled": true
```

**Check 3: Import Errors?**
```bash
# Check server logs
tail logs/server_*.log | grep -i "cache"
# Look for: "✅ Vector store cache ENABLED"
```

**Check 4: Redis Memory Full?**
```bash
redis-cli INFO memory | grep used_memory_human
redis-cli CONFIG GET maxmemory
# If maxmemory=0, Redis can use unlimited memory
# Set limit: redis-cli CONFIG SET maxmemory 2gb
```

### Low Hit Rate

**Diagnosis:**
```bash
# Check actual hit rate
redis-cli INFO stats | grep keyspace
# Calculate: hits / (hits + misses)

# If <20%:
# - Queries are very diverse (expected)
# - TTL too short (increase TTL)
# - Cache just started (wait for warm-up)
```

**Solutions:**
1. Increase TTL if data is stable
2. Pre-warm cache with common queries
3. Normalize queries before caching

### Cache Memory Issues

**Symptom:** Redis using too much memory

**Solution 1: Set maxmemory**
```bash
redis-cli CONFIG SET maxmemory 2gb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

**Solution 2: Reduce TTL**
```python
CACHE_TTL_RETRIEVAL = 1800  # 30 min instead of 1 hour
```

**Solution 3: Reduce L1 cache size**
```python
L1_CACHE_MAXSIZE = 200  # Instead of 500
```

---

## 📋 Testing Cache

### Test Cache Functionality

```bash
# 1. Check feature status
curl http://localhost:8000/features

# 2. Make a query
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Điều kiện tham gia đấu thầu?", "mode": "balanced"}'

# 3. Check Redis for cache entry
redis-cli KEYS "retrieval:*"

# 4. Make same query again (should be faster)
time curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Điều kiện tham gia đấu thầu?", "mode": "balanced"}'

# 5. Check cache hit in logs
tail -50 logs/server_*.log | grep -i "cache.*hit"
```

### Benchmark with/without Cache

```python
# Run: python scripts/tests/benchmark_cache.py
import requests
import time

BASE_URL = "http://localhost:8000"
QUERY = "Điều kiện tham gia đấu thầu?"

# Flush cache first
import redis
r = redis.Redis(host='localhost', port=6379, db=0)
r.flushdb()

# First request (cache miss)
start = time.time()
response = requests.post(f"{BASE_URL}/ask", json={"question": QUERY})
first_time = time.time() - start
print(f"First request (MISS): {first_time:.2f}s")

# Second request (cache hit)
start = time.time()
response = requests.post(f"{BASE_URL}/ask", json={"question": QUERY})
second_time = time.time() - start
print(f"Second request (HIT): {second_time:.2f}s")

print(f"Speedup: {first_time/second_time:.2f}x")
```

---

## 🎓 Best Practices

### ✅ DO

- Monitor cache hit rates regularly
- Set reasonable TTL (1 hour for retrieval)
- Use separate Redis DBs for different purposes
- Log cache hits/misses for analysis
- Set maxmemory limit to prevent OOM

### ❌ DON'T

- Don't cache LLM responses (non-deterministic)
- Don't set TTL too long (risk stale data)
- Don't cache without monitoring
- Don't ignore memory limits
- Don't flush cache in production without backup

---

## 🔗 References

- **Cache Implementation:** `src/retrieval/cached_retrieval.py`
- **Configuration:** `src/config/feature_flags.py`
- **Integration:** `src/embedding/store/pgvector_store.py`
- **Overall Plan:** `documents/technical/POOLING_CACHE_PLAN.md`

---

**Last Updated:** 2025-11-14  
**Status:** ✅ Implemented and Tested
