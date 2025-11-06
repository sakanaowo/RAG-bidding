
# 🔍 CACHE & HNSW - GIẢI THÍCH CHI TIẾT

## ✅ REDIS CACHE - ĐÃ TRIỂN KHAI

### Kiến trúc 3-layer caching:

```
Query → L1 (Memory) → L2 (Redis) → L3 (PostgreSQL)
        ↓ 0.1ms      ↓ 1-5ms      ↓ 868ms
```

### 📁 File implementation:
**`src/retrieval/cached_retrieval.py`** (369 dòng)

### 🎯 Cách hoạt động:

#### Layer 1 - Memory Cache (Fastest)
- **Storage**: Python dictionary trong RAM
- **Latency**: ~0.1ms
- **Size**: 100 queries (configurable)
- **Strategy**: LRU (Least Recently Used)
- **Lifetime**: Process lifetime

```python
cached_store = CachedVectorStore(
    vector_store,
    enable_l1_cache=True,     # ← Memory cache
    l1_cache_size=100,        # ← Max 100 queries
)
```

#### Layer 2 - Redis Cache (Fast)
- **Storage**: Redis server (in-memory database)
- **Latency**: ~1-5ms
- **Size**: Unlimited (depends on RAM)
- **Strategy**: TTL-based expiration
- **Lifetime**: Persistent, shared across processes
- **TTL**: 300s (5 phút) - configurable

```python
cached_store = CachedVectorStore(
    vector_store,
    redis_host="localhost",   # ← Redis server
    redis_port=6379,
    ttl=300,                  # ← 5 minutes expiration
)
```

#### Layer 3 - PostgreSQL (Authoritative)
- **Storage**: PostgreSQL + pgvector
- **Latency**: ~868ms (current)
- **Size**: Unlimited
- **Strategy**: Vector similarity search
- **Lifetime**: Permanent

### 🔑 Cache Key Generation:
```python
# Query: "điều kiện tham gia đấu thầu"
# K: 5
# Filter: {"document_type": "law"}

# Normalized key:
"q:điều kiện tham gia đấu thầu|k:5|f:document_type=law"
       ↓ MD5 hash
"rag:retrieval:a3f2c1d9e8b7..."
```

### 📊 Performance Impact:

| Cache Level | Latency | vs L3 | Speedup |
|-------------|---------|-------|---------|
| **L3 (PostgreSQL)** | 868ms | Baseline | 1x |
| **L2 (Redis)** | ~3ms | -865ms | **289x faster** ✅✅✅ |
| **L1 (Memory)** | ~0.1ms | -868ms | **8680x faster** ✅✅✅✅ |

### 🎯 Expected Hit Rates (Production):
```
Total queries: 1000
├── L1 hits: 50% → 500 queries @ 0.1ms
├── L2 hits: 45% → 450 queries @ 3ms
└── L3 hits: 5% → 50 queries @ 868ms

Average latency:
= (500 × 0.1ms) + (450 × 3ms) + (50 × 868ms) / 1000
= 50ms + 1350ms + 43400ms / 1000
= 44.8ms average ✅ (vs 868ms without cache)

Improvement: 19.4x faster!
```

### ✅ Đã triển khai các tính năng:

1. **Multi-layer caching** ✅
   - L1 (memory) + L2 (Redis) + L3 (PostgreSQL)

2. **LRU eviction** ✅
   - Tự động xóa queries cũ nhất khi L1 đầy

3. **Cache statistics** ✅
   - Track hits/misses, hit rate
   
4. **Cache invalidation** ✅
   - Clear all cache
   - Invalidate specific query

5. **Error handling** ✅
   - Graceful degradation nếu Redis fail

### 🧪 Test Cache (đã có):
```bash
# Chạy test
python3 src/retrieval/cached_retrieval.py

# Kết quả expected:
# Round 1: All L3 hits (~868ms mỗi query)
# Round 2: All L1 hits (~0.1ms mỗi query) 
# Round 3: All L2 hits (~3ms mỗi query)
```

---

## 🚀 HNSW - HIERARCHICAL NAVIGABLE SMALL WORLD

### HNSW là gì?

**HNSW** = **H**ierarchical **N**avigable **S**mall **W**orld graph

Một thuật toán **vector index** để tìm kiếm nearest neighbors SIÊU NHANH!

### 🎯 So sánh với IVFFlat (hiện tại):

| Feature | IVFFlat (Current) | HNSW (Recommended) |
|---------|-------------------|-------------------|
| **Build Time** | Fast (~10s) | Slower (~1-2 min) |
| **Search Speed** | Slow (868ms) | **Fast (100-200ms)** ✅ |
| **Accuracy** | Medium (85-95%) | **High (95-99%)** ✅ |
| **Memory** | Low | Medium |
| **Index Type** | Cluster-based | Graph-based |
| **Best For** | Small datasets | **Productionping 2>/dev/null || echo "Redis chưa chạy"* ✅ |

### 📐 Cách HNSW hoạt động:

#### 1. IVFFlat (Current method):
```
Tất cả 4,640 embeddings
    ↓ Cluster thành 100 lists (IVF)
    
List 1: [vec1, vec2, vec3, ...]  ← 46 vectors
List 2: [vec10, vec11, ...]      ← 46 vectors
List 3: [vec20, vec21, ...]      ← 46 vectors
...
List 100: [vec4600, ...]         ← 46 vectors

Search process:
1. Find closest list (fast)
2. Search ALL vectors in that list (slow!)
3. Return top-k

Problem: Phải scan 46-92 vectors (nếu probes=1-2)
→ Slow: 868ms
```

#### 2. HNSW (Graph-based):
```
Layer 3 (top):    A -------- B
                  |          |
                  |          |
Layer 2:      A - C - D ---- B - E
              |   |   |      |   |
Layer 1:  A - C - D - F - G - B - E - H
          |||||||||||||||||||||||||||||
Layer 0:  [All 4,640 vectors connected]

Search process:
1. Start at top layer (long jumps)
2. Navigate to approximate area (fast!)
3. Drop to lower layer (shorter jumps)
4. Repeat until Layer 0
5. Refine locally
6. Return top-k

Benefit: Logarithmic search time O(log N)
→ Fast: 100-200ms ✅
```

### 🎛️ HNSW Parameters:

#### **m** (number of connections per node)
```
m = 4:   Fewer connections → faster build, less accurate
m = 16:  Balanced → RECOMMENDED ✅
m = 32:  More connections → slower build, more accurate
m = 64:  Maximum accuracy, highest memory
```

**Recommendation cho 4,640 embeddings**: `m = 16`

#### **ef_construction** (build quality)
```
ef_construction = 32:  Fast build, lower quality
ef_construction = 64:  Balanced → RECOMMENDED ✅
ef_construction = 128: Slow build, high quality
ef_construction = 200: Maximum quality
```

**Recommendation**: `ef_construction = 64`

#### **ef_search** (search quality at runtime)
```
ef_search = 10:  Fast, less accurate (85%)
ef_search = 40:  Balanced → RECOMMENDED ✅ (95% accuracy)
ef_search = 100: Slow, very accurate (99%)
```

**Recommendation**: `ef_search = 40`

### 💾 Memory Usage:

```
IVFFlat:
- Lists metadata: ~10 KB
- Overhead: ~20 MB
Total: ~20 MB

HNSW:
- Graph structure: ~50 MB
- Connections: m × 4,640 × 8 bytes
  = 16 × 4,640 × 8 = 595 KB
Total: ~51 MB

Impact: +31 MB (acceptable!)
```

### 🚀 Migration Commands:

#### Step 1: Check current index
```sql
-- Connect to database
psql postgresql://localhost:5432/rag_bidding_v2

-- List indexes
\d langchain_pg_embedding

-- Should see:
-- langchain_pg_embedding_embedding_idx (ivfflat)
```

#### Step 2: Drop IVFFlat index
```sql
DROP INDEX IF EXISTS langchain_pg_embedding_embedding_idx;
```

#### Step 3: Create HNSW index
```sql
CREATE INDEX langchain_pg_embedding_embedding_idx 
ON langchain_pg_embedding 
USING hnsw (embedding vector_cosine_ops)
WITH (
    m = 16,              -- 16 connections per node
    ef_construction = 64  -- Build quality
);

-- This takes ~1-2 minutes for 4,640 embeddings
```

#### Step 4: Set runtime parameters
```sql
-- In PostgreSQL config or session
SET hnsw.ef_search = 40;  -- Search quality (95% recall)
```

#### Step 5: Verify
```sql
-- Check index exists
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'langchain_pg_embedding';

-- Should show HNSW index
```

### 📊 Expected Performance Improvement:

```
BEFORE (IVFFlat):
  Mean:     868ms
  P95:      1304ms
  P99:      1552ms
  Accuracy: ~92%

AFTER (HNSW):
  Mean:     150-200ms  ← 4.3-5.8x faster ✅
  P95:      250-300ms  ← 4.3-5.2x faster ✅
  P99:      350-400ms  ← 3.9-4.4x faster ✅
  Accuracy: ~96%       ← Better! ✅
```

### 🎯 When to use HNSW vs IVFFlat?

#### Use **HNSW** when:
- ✅ Production deployment
- ✅ Need fast queries (<200ms)
- ✅ Need high accuracy (>95%)
- ✅ Dataset > 1,000 vectors
- ✅ Have enough memory

#### Use **IVFFlat** when:
- 🟡 Development/testing only
- 🟡 Fast rebuild needed
- 🟡 Low memory constraints
- 🟡 Dataset < 1,000 vectors

**Your case (4,640 embeddings)**: HNSW là lựa chọn tốt nhất! ✅

---

## 🎯 COMBINED: Cache + HNSW

### Performance với cả 2 optimizations:

```
Scenario 1: Cache MISS (cold query)
  Query → L1 miss → L2 miss → L3 (HNSW)
  Latency: 150-200ms (vs 868ms before)
  Improvement: 4.3-5.8x faster ✅

Scenario 2: Cache HIT (L2 Redis)
  Query → L1 miss → L2 HIT
  Latency: ~3ms
  Improvement: 289x faster ✅✅

Scenario 3: Cache HIT (L1 Memory)
  Query → L1 HIT
  Latency: ~0.1ms
  Improvement: 8680x faster ✅✅✅

Production (95% cache hit rate):
  Average: ~44.8ms (vs 868ms)
  Improvement: 19.4x faster ✅✅
```

### 🚀 Implementation Checklist:

#### ✅ Cache (Already Done!)
- [x] Redis running
- [x] CachedVectorStore implemented
- [x] Multi-layer (L1 + L2 + L3)
- [x] LRU eviction
- [x] Statistics tracking
- [ ] Integrate into production code

#### ⏳ HNSW (To Do)
- [ ] Drop IVFFlat index
- [ ] Create HNSW index (1-2 min)
- [ ] Set ef_search=40
- [ ] Re-benchmark
- [ ] Compare results

---

## 🧪 NEXT STEPS: Test Both Optimizations

### Step 1: Test Cache (5 phút)
```bash
# Run cache test
python3 src/retrieval/cached_retrieval.py

# Expected output:
# Round 1: 3 queries @ ~868ms each (L3)
# Round 2: 3 queries @ ~0.1ms each (L1)
# Round 3: 3 queries @ ~3ms each (L2)
# Hit rate: 66.7%
```

### Step 2: Migrate to HNSW (2 phút)
```bash
# Connect to database
psql postgresql://localhost:5432/rag_bidding_v2

# Run migration SQL (see above)
# Wait 1-2 minutes for index build
```

### Step 3: Benchmark HNSW (3 phút)
```bash
# Re-run benchmark
python3 scripts/benchmark_retrieval.py

# Expected improvement:
# Mean: 868ms → 150-200ms ✅
```

### Step 4: Test Cache + HNSW (5 phút)
```bash
# Create combined test script
# Expected:
# Cold queries: ~150-200ms (HNSW)
# Warm queries: ~3ms (Redis) or ~0.1ms (Memory)
```

---

## 📌 TÓM TẮT

### Redis Cache:
- ✅ **Đã triển khai** từ hôm qua
- ✅ 3-layer: Memory + Redis + PostgreSQL
- ✅ Expected: 19.4x faster (average)
- ⚠️ Chưa integrate vào production code

### HNSW Index:
- ❌ **Chưa migrate** (vẫn dùng IVFFlat)
- 🎯 Thuật toán graph-based search
- 🎯 Expected: 4.3-5.8x faster than IVFFlat
- 🎯 Build time: ~1-2 minutes
- 🎯 Memory: +31 MB (acceptable)

### Combined (Cache + HNSW):
- 🚀 Cold queries: 150-200ms (HNSW)
- 🚀 Warm queries: 0.1-3ms (Cache)
- 🚀 Average: ~44.8ms (95% cache hit)
- 🚀 Total improvement: **19.4x faster!**

---

**Created**: 3/11/2025 08:30 AM  
**Status**: Cache ready, HNSW pending migration  
**Next**: Test cache, then migrate to HNSW

