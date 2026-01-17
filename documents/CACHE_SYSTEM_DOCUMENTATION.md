# 📚 Hệ Thống Cache RAG - Tài Liệu Kỹ Thuật

> **Version:** 2.0  
> **Cập nhật:** 08/01/2026  
> **Tác giả:** RAG Bidding Team

---

## Mục Lục

1. [Tổng Quan Hệ Thống](#1-tổng-quan-hệ-thống)
2. [Kiến Trúc Cache Đa Tầng](#2-kiến-trúc-cache-đa-tầng)
3. [Answer Cache](#3-answer-cache)
4. [Semantic Cache](#4-semantic-cache)
5. [Retrieval Cache](#5-retrieval-cache)
6. [Context Cache](#6-context-cache)
7. [Luồng Xử Lý Request](#7-luồng-xử-lý-request)
8. [Cache Invalidation](#8-cache-invalidation)
9. [API Quản Lý Cache](#9-api-quản-lý-cache)
10. [Cấu Hình & Environment Variables](#10-cấu-hình--environment-variables)

---

## 1. Tổng Quan Hệ Thống

### 1.1. Vấn Đề Cần Giải Quyết

Hệ thống RAG thực hiện nhiều tác vụ tốn kém về thời gian và chi phí:

| Tác Vụ | Thời Gian | Chi Phí |
|--------|-----------|---------|
| Tạo Embedding (OpenAI) | 100-300ms | ~$0.0001/query |
| Vector Search (PostgreSQL) | 50-100ms | CPU/IO |
| Reranking (BGE) | 200-500ms | GPU |
| LLM Generation (GPT-4o) | 2000-8000ms | ~$0.01-0.05/query |
| **Tổng cộng** | **3-10 giây** | **$0.01-0.05** |

### 1.2. Giải Pháp: Cache Đa Tầng

Hệ thống cache được thiết kế với 4 loại cache chính:

```
┌──────────────────────────────────────────────────────────────────────┐
│                         CACHE ARCHITECTURE                            │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   User Query                                                          │
│       │                                                               │
│       ▼                                                               │
│   ┌────────────────────────────────────┐                              │
│   │  1. ANSWER CACHE (Exact Match)     │  Redis DB 2                  │
│   │     Key: SHA256(query)             │  TTL: 24h                    │
│   │     Latency: <5ms                  │                              │
│   └────────────────┬───────────────────┘                              │
│                    │ MISS                                             │
│                    ▼                                                  │
│   ┌────────────────────────────────────┐                              │
│   │  2. SEMANTIC CACHE (Similarity)    │  Redis DB 3                  │
│   │     Threshold: 0.95 cosine         │  TTL: 24h                    │
│   │     Latency: 200-500ms             │                              │
│   └────────────────┬───────────────────┘                              │
│                    │ MISS                                             │
│                    ▼                                                  │
│   ┌────────────────────────────────────┐                              │
│   │  3. RETRIEVAL CACHE                │  Redis DB 0                  │
│   │     Key: MD5(query+k+filters)      │  TTL: 1h                     │
│   │     Latency: 5-10ms                │                              │
│   └────────────────┬───────────────────┘                              │
│                    │ MISS                                             │
│                    ▼                                                  │
│   ┌────────────────────────────────────┐                              │
│   │  4. FULL RAG PIPELINE              │                              │
│   │     Vector Search → Rerank → LLM   │                              │
│   │     Latency: 3-10s                 │                              │
│   └────────────────────────────────────┘                              │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.3. Redis Database Layout

| DB | Mục Đích | Key Pattern | TTL |
|----|----------|-------------|-----|
| 0 | Retrieval Cache | `rag:retrieval:{md5}` | 1 giờ |
| 1 | Session/Context Cache | `context:{uuid}` | 1 giờ |
| 2 | Answer Cache | `rag:answer:{sha256}` | 24 giờ |
| 3 | Semantic Cache | `rag:semantic:{sha256}` | 24 giờ |

---

## 2. Kiến Trúc Cache Đa Tầng

### 2.1. L1 Cache (In-Memory)

```
┌─────────────────────────────────────────────────────────────┐
│                     L1 CACHE (Per-Worker)                    │
├─────────────────────────────────────────────────────────────┤
│  • Storage: Python Dict với LRU eviction                     │
│  • Latency: <1ms                                             │
│  • Size: 100-500 entries (configurable)                      │
│  • Scope: Single worker process                              │
│  • Persistence: None (lost on restart)                       │
│  • Thread-safe: Yes (with threading.Lock)                    │
└─────────────────────────────────────────────────────────────┘
```

**Cách hoạt động:**
1. Mỗi worker Uvicorn có L1 cache riêng
2. Sử dụng danh sách để theo dõi thứ tự LRU
3. Khi đầy, evict entry cũ nhất
4. Backfill từ L2 khi có cache hit ở Redis

### 2.2. L2 Cache (Redis)

```
┌─────────────────────────────────────────────────────────────┐
│                     L2 CACHE (Shared)                        │
├─────────────────────────────────────────────────────────────┤
│  • Storage: Redis 7+ (standalone)                            │
│  • Latency: 5-10ms                                           │
│  • Size: Unlimited (recommend 2GB maxmemory)                 │
│  • Scope: All workers (shared)                               │
│  • Persistence: Yes (RDB + AOF)                              │
│  • Serialization: pickle (binary)                            │
└─────────────────────────────────────────────────────────────┘
```

**Cách hoạt động:**
1. Tất cả workers chia sẻ cùng Redis instance
2. Mỗi loại cache dùng Redis DB riêng
3. TTL được set bằng `SETEX` command
4. Dữ liệu được pickle serialize

### 2.3. L3 (PostgreSQL - Authoritative Source)

```
┌─────────────────────────────────────────────────────────────┐
│                     L3 (PostgreSQL + pgvector)               │
├─────────────────────────────────────────────────────────────┤
│  • Vector search qua pgvector extension                      │
│  • Latency: 50-100ms                                         │
│  • Luôn được query khi L1+L2 MISS                            │
│  • Kết quả được cache lại vào L1+L2                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Answer Cache

### 3.1. Mô Tả

Answer Cache lưu trữ **kết quả cuối cùng của RAG pipeline** (answer + sources) để tránh chạy lại toàn bộ pipeline cho cùng một câu hỏi.

**File:** `src/retrieval/answer_cache.py`

### 3.2. Cache Key Generation

```python
def _generate_key(self, query: str) -> str:
    """
    Key = rag:answer:{SHA256(query.lower().strip())}
    
    Ví dụ:
    Input:  "Điều kiện tham gia đấu thầu là gì?"
    Output: "rag:answer:a1b2c3d4e5f6..."
    """
    normalized = query.lower().strip()
    query_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"rag:answer:{query_hash}"
```

**Quan trọng:** Cache sử dụng **câu hỏi gốc** (original_query) chứ không phải câu hỏi đã được enhance với conversation context.

### 3.3. Cấu Trúc Dữ Liệu Lưu Trữ

```python
@dataclass
class CachedAnswer:
    answer: str                        # Câu trả lời từ LLM
    sources: List[Dict[str, Any]]      # Danh sách sources
    rag_mode: Optional[str] = None     # Mode đã sử dụng (fast/balanced/quality/adaptive)
    processing_time_ms: Optional[int]  # Thời gian xử lý gốc
    cached_at: str = ""                # Timestamp cache
    original_query: str = ""           # Câu hỏi gốc

# Ví dụ sources:
sources = [
    {
        "document_id": "uuid-xxx",
        "document_name": "Luật Đấu thầu 2023",
        "chunk_id": "chunk-123",
        "citation_text": "Điều 5. Điều kiện tham gia...",
        "section": "Điều 5"
    }
]
```

### 3.4. Serialization

```python
# Serialize (Python → Redis)
cached_bytes = pickle.dumps(cached_answer.to_dict())
redis.setex(key, ttl, cached_bytes)

# Deserialize (Redis → Python)
cached_bytes = redis.get(key)
cached_data = pickle.loads(cached_bytes)
cached_answer = CachedAnswer.from_dict(cached_data)
```

### 3.5. Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     ANSWER CACHE FLOW                        │
└─────────────────────────────────────────────────────────────┘

GET (Read):
┌──────────┐    ┌──────────┐    ┌──────────┐
│  Query   │───▶│ L1 Check │───▶│ L2 Check │───▶ MISS
│          │    │ (Memory) │    │ (Redis)  │
└──────────┘    └──────────┘    └──────────┘
                    │ HIT           │ HIT
                    ▼               ▼
              ┌───────────────────────────┐
              │  Return cached answer     │
              │  + Backfill L1 if L2 hit  │
              └───────────────────────────┘

SET (Write):
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ RAG Result   │───▶│ Write to L1  │───▶│ Write to L2  │
│              │    │ (with LRU)   │    │ (with TTL)   │
└──────────────┘    └──────────────┘    └──────────────┘
```

### 3.6. Statistics

```python
stats = {
    "total_queries": 100,      # Tổng số queries
    "l1_hits": 30,             # Hit từ memory
    "l2_hits": 25,             # Hit từ Redis
    "misses": 45,              # Cache miss
    "cache_sets": 45,          # Số lần cache
    "errors": 0,               # Số lỗi
    "hit_rate": 0.55,          # Tỷ lệ hit (55%)
    "l1_hit_rate": 0.30,       # Tỷ lệ L1 hit
    "l2_hit_rate": 0.25,       # Tỷ lệ L2 hit
}
```

---

## 4. Semantic Cache

### 4.1. Mô Tả

Semantic Cache tìm kiếm câu hỏi **tương tự về ngữ nghĩa** khi Answer Cache không có exact match. Sử dụng embeddings và cosine similarity.

**File:** `src/retrieval/semantic_cache.py`

### 4.2. Cách Hoạt Động

```
┌─────────────────────────────────────────────────────────────┐
│                    SEMANTIC CACHE FLOW                       │
└─────────────────────────────────────────────────────────────┘

1. Answer Cache MISS
        │
        ▼
2. Compute embedding của query hiện tại
        │
        ▼
3. Scan tất cả embeddings trong Redis DB 3
        │
        ▼
4. Tính cosine similarity với từng cached embedding
        │
        ▼
5. Nếu similarity >= 0.95:
   └── Lấy answer từ Answer Cache của original query
        │
        ▼
6. Return cached answer (hoặc MISS nếu không tìm thấy)
```

### 4.3. Cache Key & Data Structure

```python
# Key generation (giống Answer Cache)
key = f"rag:semantic:{sha256(query.lower().strip())}"

# Data stored in Redis
data = {
    "query": "Điều kiện tham gia đấu thầu?",
    "embedding": numpy_array.tobytes(),     # Binary embedding
    "embedding_dim": 1536,                   # Dimension (OpenAI)
    "answer_cache_key": "rag:answer:xxx",   # Reference to answer
    "cached_at": "2026-01-08T15:30:00"
}
```

### 4.4. Cosine Similarity

```python
def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
    """
    similarity = (a · b) / (||a|| × ||b||)
    
    Returns: float từ -1 đến 1 (1 = identical)
    """
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))
```

### 4.5. Threshold Configuration

```python
# Default: 0.95 (95% similarity)
SEMANTIC_CACHE_THRESHOLD = float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.95"))

# Ví dụ:
# Query 1: "Điều kiện tham gia đấu thầu là gì?"
# Query 2: "Điều kiện để nhà thầu được tham gia đấu thầu?"
# Similarity: ~0.97 → HIT (>= 0.95)

# Query 3: "Quy trình đấu thầu online như thế nào?"
# Similarity: ~0.78 → MISS (< 0.95)
```

### 4.6. Performance Consideration

**Brute-force scan** hiện tại có O(n) complexity. Với MAX_SEMANTIC_SEARCH = 100:
- Scan tối đa 100 embeddings
- Mỗi comparison: ~0.1ms
- Total: ~10ms + embedding time (~200ms)

**TODO:** Upgrade to Redis Vector Search (HNSW index) for O(log n).

---

## 5. Retrieval Cache

### 5.1. Mô Tả

Retrieval Cache lưu trữ **kết quả vector search** từ PostgreSQL để tránh query lại database.

**File:** `src/retrieval/cached_retrieval.py`

### 5.2. Cache Key Generation

```python
def _generate_cache_key(self, query: str, k: int, filters: Optional[Dict]) -> str:
    """
    Key = rag:retrieval:{MD5(query|k|filters)}
    
    Ví dụ:
    Input:  query="đấu thầu", k=10, filters={"category": "Luật chính"}
    Output: "rag:retrieval:abc123def456..."
    """
    key_parts = [
        f"q:{query.strip().lower()}",
        f"k:{k}",
    ]
    if filters:
        filter_str = str(sorted(filters.items()))
        key_parts.append(f"f:{filter_str}")
    
    key_string = "|".join(key_parts)
    cache_key = hashlib.md5(key_string.encode()).hexdigest()
    return f"rag:retrieval:{cache_key}"
```

**Lưu ý:** Retrieval cache sử dụng **full question** (bao gồm context) vì việc retrieve cần context để tìm documents phù hợp hơn.

### 5.3. Data Structure

```python
# Cached data: List[Document]
# Mỗi Document chứa:
Document(
    page_content="Nội dung chunk...",
    metadata={
        "document_id": "uuid",
        "document_name": "Luật Đấu thầu 2023",
        "chunk_id": "chunk-123",
        "category": "Luat chinh",
        "dieu": "5",
        "khoan": "1",
        "diem": "a",
        ...
    }
)
```

### 5.4. Flow

```
similarity_search(query, k=10, filter=None)
        │
        ▼
┌───────────────────────────────────────┐
│  Generate cache key                    │
│  key = rag:retrieval:{md5}            │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   L1 Check    │───▶│   L2 Check    │───▶│  L3 Query     │
│   (Memory)    │    │   (Redis)     │    │  (pgvector)   │
└───────────────┘    └───────────────┘    └───────────────┘
     │ HIT              │ HIT                  │
     │                  │                      │
     └──────────────────┴──────────────────────┘
                        │
                        ▼
              ┌─────────────────────────┐
              │  Return List[Document]  │
              │  + Update caches        │
              └─────────────────────────┘
```

### 5.5. TTL

```python
CACHE_TTL_RETRIEVAL = 3600  # 1 giờ

# Lý do TTL ngắn hơn Answer Cache:
# - Document status có thể thay đổi (active → expired)
# - Embedding data có thể được cập nhật
# - Đảm bảo freshness của search results
```

---

## 6. Context Cache

### 6.1. Mô Tả

Context Cache lưu trữ **lịch sử hội thoại gần đây** của mỗi conversation để tránh query database.

**File:** `src/retrieval/context_cache.py`

### 6.2. Strategy: Write-Through

```
┌─────────────────────────────────────────────────────────────┐
│                   WRITE-THROUGH STRATEGY                     │
└─────────────────────────────────────────────────────────────┘

On READ:
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Check Cache  │───▶│ Cache MISS?  │───▶│ Query DB     │
│              │    │              │    │              │
└──────────────┘    └──────────────┘    └──────────────┘
     │ HIT                                    │
     ▼                                        ▼
┌──────────────┐                    ┌──────────────────────┐
│ Return cached│                    │ Populate cache +     │
│ messages     │                    │ Return messages      │
└──────────────┘                    └──────────────────────┘

On WRITE (new message):
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Write to DB  │───▶│ Update cache │───▶│ Trim to max  │
│              │    │ (append)     │    │ 20 messages  │
└──────────────┘    └──────────────┘    └──────────────┘
```

### 6.3. Cache Key & Structure

```python
# Key
key = f"context:{conversation_id}"  # e.g., "context:94b13aa3-da67-4680-..."

# Value: JSON array of recent messages
[
    {
        "id": "message-uuid",
        "role": "user",
        "content": "Điều kiện tham gia đấu thầu?",
        "created_at": "2026-01-08T15:30:00",
        "rag_mode": null
    },
    {
        "id": "message-uuid-2",
        "role": "assistant",
        "content": "Điều kiện để nhà thầu tham gia...",
        "created_at": "2026-01-08T15:30:15",
        "rag_mode": "balanced"
    }
]
```

### 6.4. Configuration

```python
MAX_CONTEXT_MESSAGES = 20  # Giữ tối đa 20 messages gần nhất
SESSION_TTL_SECONDS = 3600  # 1 giờ TTL
REDIS_DB_SESSIONS = 1       # Redis DB 1
```

---

## 7. Luồng Xử Lý Request

### 7.1. Complete Request Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        COMPLETE REQUEST FLOW                             │
└─────────────────────────────────────────────────────────────────────────┘

POST /api/conversations/{id}/messages
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. ConversationService.send_message(content, rag_mode)                  │
│    - Verify conversation ownership                                       │
│    - Determine effective_rag_mode (request → conversation → "balanced") │
│    - Create user message in DB                                          │
└─────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. Build conversation context                                            │
│    - Get recent messages from Context Cache (or DB fallback)            │
│    - Build enhanced_question with context                                │
│    - IMPORTANT: Keep original content for cache key                     │
└─────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. qa_chain.answer(question=enhanced_question, original_query=content)  │
│                                                                          │
│    ┌─────────────────────────────────────────────────────────────────┐  │
│    │ 3a. Check Answer Cache (using original_query)                    │  │
│    │     - HIT → Return immediately (<5ms)                           │  │
│    └─────────────────────────────────────────────────────────────────┘  │
│                │ MISS                                                    │
│                ▼                                                         │
│    ┌─────────────────────────────────────────────────────────────────┐  │
│    │ 3b. Check Semantic Cache (using original_query)                  │  │
│    │     - Find similar query with similarity >= 0.95                │  │
│    │     - HIT → Return cached answer (~200-500ms)                   │  │
│    └─────────────────────────────────────────────────────────────────┘  │
│                │ MISS                                                    │
│                ▼                                                         │
│    ┌─────────────────────────────────────────────────────────────────┐  │
│    │ 3c. Run full RAG pipeline                                        │  │
│    │     - Create retriever with mode settings                       │  │
│    │     - Retrieval Cache check (using enhanced_question)           │  │
│    │     - Vector search (if cache miss)                             │  │
│    │     - Reranking                                                 │  │
│    │     - LLM Generation                                            │  │
│    └─────────────────────────────────────────────────────────────────┘  │
│                │                                                         │
│                ▼                                                         │
│    ┌─────────────────────────────────────────────────────────────────┐  │
│    │ 3d. Cache result (using original_query)                          │  │
│    │     - Set Answer Cache                                          │  │
│    │     - Store Semantic Cache embedding                            │  │
│    └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. Create assistant message in DB                                        │
│    - Store answer, sources, rag_mode, tokens                            │
│    - Update Context Cache with new messages                              │
└─────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 5. Return response to client                                             │
│    - user_message, assistant_message, sources, processing_time          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.2. Cache Key Strategy

| Cache Type | Key Source | Lý Do |
|------------|------------|-------|
| Answer Cache | `original_query` | Cache cùng câu hỏi across conversations |
| Semantic Cache | `original_query` | Tìm similar questions regardless of context |
| Retrieval Cache | `enhanced_question` | Context ảnh hưởng đến retrieval relevance |
| Context Cache | `conversation_id` | Per-conversation history |

---

## 8. Cache Invalidation

### 8.1. Mô Tả

**File:** `src/retrieval/cache_invalidation.py`

Cache Invalidation đảm bảo users thấy data mới nhất khi:
- Document status thay đổi (active → expired)
- Document content được cập nhật
- Admin thực hiện reindex

### 8.2. Invalidation Service

```python
class CacheInvalidationService:
    def invalidate_on_document_change(self, document_id: str, change_type: str):
        """
        Invalidate caches when document changes.
        
        Args:
            document_id: ID của document bị thay đổi
            change_type: "status_change", "content_update", "delete"
        
        Actions:
            - Clear all retrieval caches (vì query nào cũng có thể include doc này)
        """
        
    def invalidate_on_reindex(self):
        """
        Invalidate all caches after bulk reindex.
        
        Actions:
            - Clear retrieval cache
            - (Answer + Semantic cache vẫn valid vì content không đổi)
        """
```

### 8.3. Usage Example

```python
# Trong document update endpoint
@router.put("/documents/{document_id}/status")
async def update_document_status(document_id: str, status: str, db: Session):
    # Update database
    document.status = status
    db.commit()
    
    # Invalidate cache
    from src.retrieval.cache_invalidation import invalidate_cache_for_document
    invalidate_cache_for_document(document_id, "status_change")
    
    return {"status": "updated"}
```

---

## 9. API Quản Lý Cache

### 9.1. Endpoints

**File:** `src/api/routers/cache.py`

| Endpoint | Method | Mô Tả |
|----------|--------|-------|
| `/api/cache/health` | GET | Kiểm tra Redis connection |
| `/api/cache/stats` | GET | Lấy statistics của tất cả caches |
| `/api/cache/clear` | POST | Xóa tất cả caches |
| `/api/cache/config` | GET | Lấy cấu hình cache hiện tại |

### 9.2. Example Responses

**GET /api/cache/stats**
```json
{
  "answer_cache": {
    "total_queries": 150,
    "l1_hits": 45,
    "l2_hits": 38,
    "misses": 67,
    "hit_rate": 0.5533,
    "l1_size": 45,
    "enabled": true,
    "ttl": 86400
  },
  "semantic_cache": {
    "total_searches": 67,
    "semantic_hits": 12,
    "semantic_misses": 55,
    "hit_rate": 0.1791,
    "avg_similarity": 0.9723,
    "threshold": 0.95,
    "enabled": true
  },
  "retrieval_cache": {
    "total_queries": 55,
    "l1_hits": 15,
    "l2_hits": 10,
    "l3_hits": 30,
    "hit_rate": 0.4545
  }
}
```

---

## 10. Cấu Hình & Environment Variables

### 10.1. Feature Flags

**File:** `src/config/feature_flags.py`

```python
# Redis connection
ENABLE_REDIS_CACHE = os.getenv("ENABLE_REDIS_CACHE", "false") == "true"
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# Answer Cache (Redis DB 2)
ENABLE_ANSWER_CACHE = os.getenv("ENABLE_ANSWER_CACHE", "true") == "true"
ANSWER_CACHE_TTL = int(os.getenv("ANSWER_CACHE_TTL", "86400"))
ANSWER_CACHE_DB = int(os.getenv("ANSWER_CACHE_DB", "2"))

# Semantic Cache (Redis DB 3)
ENABLE_SEMANTIC_CACHE = os.getenv("ENABLE_SEMANTIC_CACHE", "true") == "true"
SEMANTIC_CACHE_THRESHOLD = float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.95"))
SEMANTIC_CACHE_DB = int(os.getenv("SEMANTIC_CACHE_DB", "3"))
MAX_SEMANTIC_SEARCH = int(os.getenv("MAX_SEMANTIC_SEARCH", "100"))

# Context Cache (Redis DB 1)
REDIS_DB_SESSIONS = int(os.getenv("REDIS_DB_SESSIONS", "1"))
SESSION_TTL_SECONDS = 3600
SESSION_MAX_MESSAGES = 100
```

### 10.2. .env Example

```bash
# Redis Configuration
ENABLE_REDIS_CACHE=true
REDIS_HOST=localhost
REDIS_PORT=6379

# Answer Cache
ENABLE_ANSWER_CACHE=true
ANSWER_CACHE_TTL=86400
ANSWER_CACHE_DB=2

# Semantic Cache
ENABLE_SEMANTIC_CACHE=true
SEMANTIC_CACHE_THRESHOLD=0.95
SEMANTIC_CACHE_DB=3
MAX_SEMANTIC_SEARCH=100

# Session Cache
REDIS_DB_SESSIONS=1
```

### 10.3. Dependency Check

```python
# All cache modules gracefully disable if Redis unavailable
try:
    self._redis = redis.Redis(...)
    self._redis.ping()
    self.enabled = True
except Exception as e:
    logger.warning(f"Redis connection failed: {e}. Cache disabled.")
    self.enabled = False
```

---

## Appendix A: Troubleshooting

### A.1. Cache không HIT dù cùng câu hỏi

**Nguyên nhân có thể:**
1. Conversation context thay đổi → Cache key khác
2. Redis chưa start hoặc connection fail
3. TTL expired
4. Cache đã bị clear

**Kiểm tra:**
```bash
# Check Redis connection
redis-cli ping

# Check cache stats
curl http://localhost:8000/api/cache/stats

# Check server logs for cache messages
# Tìm: "✅ Answer cache L1 HIT" hoặc "❌ Answer cache MISS"
```

### A.2. Performance chậm dù cache enabled

**Kiểm tra:**
1. L1 cache size có đủ lớn?
2. Redis latency có cao không? (`redis-cli --latency`)
3. Semantic cache đang scan quá nhiều embeddings?

### A.3. Memory usage cao

**Giải pháp:**
1. Giảm L1_CACHE_SIZE (default: 100)
2. Giảm MAX_SEMANTIC_SEARCH (default: 100)
3. Set Redis maxmemory: `redis-cli CONFIG SET maxmemory 2gb`

---

## Appendix B: Performance Benchmarks

| Scenario | Cold (No Cache) | Warm (Cache Hit) | Speedup |
|----------|-----------------|------------------|---------|
| Simple question | 8-12s | <50ms | **160-240x** |
| Complex question | 12-15s | <50ms | **240-300x** |
| Semantic similar | 8-12s | 200-500ms | **16-60x** |
| Retrieval only | 50-100ms | 5-10ms | **5-20x** |

---

## Appendix C: Related Files

| File | Mô Tả |
|------|-------|
| `src/retrieval/answer_cache.py` | Answer Cache implementation |
| `src/retrieval/semantic_cache.py` | Semantic Cache implementation |
| `src/retrieval/cached_retrieval.py` | Retrieval Cache (CachedVectorStore) |
| `src/retrieval/context_cache.py` | Context/Session Cache |
| `src/retrieval/cache_invalidation.py` | Cache Invalidation Service |
| `src/api/routers/cache.py` | Cache API endpoints |
| `src/config/feature_flags.py` | Configuration & feature flags |
| `src/generation/chains/qa_chain.py` | RAG pipeline với cache integration |
