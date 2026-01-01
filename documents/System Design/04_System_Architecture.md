# System Architecture - RAG Bidding System

**Ngày tạo:** 24/11/2025  
**Phiên bản:** 2.0  
**Tác giả:** System Architecture Team

---

## Mục Lục

1. [High-Level Architecture](#1-high-level-architecture)
2. [Component Details](#2-component-details)
3. [Data Flow](#3-data-flow)
4. [RAG Pipeline Architecture](#4-rag-pipeline-architecture)
5. [Caching Architecture](#5-caching-architecture)
6. [Deployment Architecture](#6-deployment-architecture)
7. [Security Architecture](#7-security-architecture)
8. [Performance & Scalability](#8-performance--scalability)

---

## 1. High-Level Architecture

### 1.1. System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                 │
│  - Web Browser (React/Vue - Future)                                 │
│  - Mobile App (Future)                                              │
│  - API Clients (Postman, cURL, SDKs)                                │
│  - Third-party Integrations                                         │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTP/REST
                             │ JSON payload
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      API GATEWAY LAYER                               │
│  - Rate Limiting (100 req/min per IP)                               │
│  - Authentication (JWT/OAuth2 - Future)                             │
│  - Request Validation                                               │
│  - CORS Handling                                                    │
│  - Logging & Monitoring                                             │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER (FastAPI)                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────────┐  │
│  │  Question       │  │  Document       │  │  Chat Session     │  │
│  │  Answering      │  │  Management     │  │  Management       │  │
│  │  Module         │  │  Module         │  │  Module           │  │
│  └────────┬────────┘  └────────┬────────┘  └─────────┬─────────┘  │
│           │                    │                      │             │
│           └────────────────────┼──────────────────────┘             │
│                                │                                    │
└────────────────────────────────┼────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    RAG PIPELINE LAYER                                │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐     │
│  │ Query          │→ │ Vector         │→ │ Reranking        │     │
│  │ Enhancement    │  │ Retrieval      │  │ (BGE-M3)         │     │
│  │ - Multi-Query  │  │ (PGVector)     │  │ - Cross-Encoder  │     │
│  │ - HyDE         │  │ - Cosine Sim   │  │ - Singleton      │     │
│  │ - Step-Back    │  │ - Top-K        │  │ - GPU/CPU        │     │
│  │ - RRF Fusion   │  │ - Filters      │  │                  │     │
│  └────────────────┘  └────────────────┘  └──────────────────┘     │
│                                 │                                    │
│                                 ▼                                    │
│                      ┌──────────────────┐                           │
│                      │ LLM Generation   │                           │
│                      │ (GPT-4o-mini)    │                           │
│                      │ - Context Prep   │                           │
│                      │ - Prompt Eng     │                           │
│                      └──────────────────┘                           │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    EMBEDDING LAYER                                   │
│  ┌────────────────────────────────────────────────────────┐         │
│  │  OpenAI text-embedding-3-large                         │         │
│  │  - Dimensions: 3,072 (native, no reduction)           │         │
│  │  - Context: 8,191 tokens                               │         │
│  │  - Cost: $0.13 per 1M tokens                           │         │
│  └────────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    CACHING LAYER (3-Tier)                            │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────────┐    │
│  │ L1: In-Memory│    │ L2: Redis    │    │ L3: PostgreSQL    │    │
│  │ - LRU Cache  │    │ - TTL: 1h    │    │ - Permanent       │    │
│  │ - Max: 500   │    │ - DB 0       │    │ - Vector Storage  │    │
│  │ - Hit: 40-60%│    │ - Hit: 20-30%│    │ - Always on       │    │
│  └──────────────┘    └──────────────┘    └───────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    STORAGE LAYER                                     │
│  ┌─────────────────────────────────────────────────────────┐        │
│  │  PostgreSQL 18 + pgvector 0.8.1                         │        │
│  │  ┌──────────────┐  ┌─────────────────────────────────┐ │        │
│  │  │ documents    │  │ langchain_pg_embedding          │ │        │
│  │  │ - 64 docs    │  │ - 7,892 chunks                  │ │        │
│  │  │ - Metadata   │  │ - VECTOR(3072)                  │ │        │
│  │  └──────────────┘  │ - JSONB metadata                │ │        │
│  │                    │ - HNSW/IVFFlat index            │ │        │
│  │  ┌──────────────┐  └─────────────────────────────────┘ │        │
│  │  │ Future Tables│                                       │        │
│  │  │ - users      │  Database Size: 149 MB               │        │
│  │  │ - sessions   │  Connection Pool: pgBouncer (planned)│        │
│  │  │ - query_logs │                                       │        │
│  │  └──────────────┘                                       │        │
│  └─────────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────────┐    │
│  │ OpenAI API   │    │ Redis Server │    │ Background Workers│    │
│  │ - Embeddings │    │ localhost    │    │ - Doc Processing  │    │
│  │ - GPT-4o-mini│    │ :6379        │    │ - Async Jobs      │    │
│  └──────────────┘    └──────────────┘    └───────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Details

### 2.1. API Layer (FastAPI)

**Technology:** FastAPI + Uvicorn ASGI Server  
**Port:** 8000  
**Concurrency:** Async/await pattern

**Core Modules:**

1. **Question Answering Module** (`src/api/ask.py`)

   - Endpoint: `POST /ask`
   - Handles query processing
   - Integrates RAG pipeline
   - Returns answers with sources

2. **Document Management Module** (`src/api/upload.py`)

   - Endpoint: `POST /api/upload/files`
   - Handles file uploads
   - Background processing
   - Status tracking

3. **Chat Session Module** (`src/api/chat.py`)

   - Endpoints: `/api/chat/sessions/*`
   - Session management
   - Message history
   - Context preservation

4. **System Module** (`src/api/system.py`)
   - Endpoints: `/health`, `/stats`, `/features`
   - Monitoring and diagnostics
   - Cache management

**Dependencies:**

```python
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-multipart==0.0.6
```

---

### 2.2. RAG Pipeline Layer

**Configuration:** `src/config/models.py`

**4 Pipeline Modes:**

| Mode          | Enhancement             | Reranking | Latency | Production Ready |
| ------------- | ----------------------- | --------- | ------- | ---------------- |
| `fast`        | None                    | No        | ~1s     | ✅               |
| `balanced` ⭐ | Multi-Query + Step-Back | BGE       | ~2-3s   | ✅ Default       |
| `quality`     | All 4 strategies        | BGE       | ~3-5s   | ✅               |
| `adaptive`    | Dynamic K               | BGE       | ~2-4s   | ⚠️ Experimental  |

**Query Enhancement Strategies:**

1. **Multi-Query Generation** (`src/retrieval/enhancement/multi_query.py`)

   ```python
   Original: "Quy định về thầu rộng rãi?"
   Generated:
   - "Luật đấu thầu quy định như thế nào về thầu rộng rãi?"
   - "Các điều kiện áp dụng thầu rộng rãi là gì?"
   - "Thầu rộng rãi được quy định trong luật nào?"
   ```

2. **HyDE (Hypothetical Document Embeddings)** (`src/retrieval/enhancement/hyde.py`)

   ```python
   Query: "Bảo đảm dự thầu là gì?"
   Hypothetical Answer: "Bảo đảm dự thầu là việc nhà thầu..."
   ```

3. **Step-Back Prompting** (`src/retrieval/enhancement/step_back.py`)

   ```python
   Specific: "Mức bảo đảm dự thầu cho gói thầu xây dựng?"
   Step-Back: "Quy định chung về bảo đảm dự thầu?"
   ```

4. **RRF Fusion** (`src/retrieval/fusion/rrf.py`)
   ```python
   # Combine results from all strategies
   final_score = 1/(k + rank_strategy1) + 1/(k + rank_strategy2) + ...
   ```

**Vector Retrieval:**

- **Technology:** LangChain PGVector
- **Distance Metric:** Cosine similarity
- **Top-K:** Dynamic (5-20 based on mode)
- **Filters:** Metadata-based (document_type, category, date_range)

**Reranking:**

- **Model:** BAAI/bge-reranker-v2-m3
- **Type:** Cross-encoder (pair-wise scoring)
- **Implementation:** Singleton pattern
- **Device:** Auto-detect (CUDA → CPU fallback)
- **Batch Size:** 32 (GPU) / 16 (CPU)
- **Memory:** ~1.2GB model cache

---

### 2.3. Embedding Layer

**Model:** OpenAI text-embedding-3-large

**Specifications:**

- **Dimensions:** 3,072 (native, no reduction)
- **Context Window:** 8,191 tokens
- **Cost:** $0.13 per 1M tokens
- **Latency:** 100-200ms per chunk
- **Quality:** State-of-the-art (MTEB leaderboard)

**Implementation:**

```python
from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-large",
    dimensions=3072,
    openai_api_key=os.getenv("OPENAI_API_KEY")
)
```

**Usage:**

- Document ingestion: Batch embedding (chunks)
- Query processing: Single embedding
- Cost optimization: Cache embeddings

---

### 2.4. Storage Layer

**PostgreSQL 18:**

- **Version:** 18+
- **Extension:** pgvector 0.8.1
- **Size:** 149 MB (current)
- **Estimated Max:** 200 GB (1M docs)

**Vector Index:**

```sql
-- HNSW (Hierarchical Navigable Small World)
CREATE INDEX idx_embedding_hnsw
ON langchain_pg_embedding
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

**Performance:**

- Query time: ~50ms (7,892 vectors)
- Concurrent queries: 20 (current) → 100+ (with pgBouncer)
- Index build time: ~5 minutes (HNSW)

**Connection Pooling (Planned):**

```ini
# pgBouncer config
[databases]
rag_bidding_v2 = host=localhost port=5432

[pgbouncer]
pool_mode = transaction
max_client_conn = 100
default_pool_size = 20
```

---

## 3. Data Flow

### 3.1. Query Processing Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    QUERY PROCESSING FLOW                         │
└─────────────────────────────────────────────────────────────────┘

1. USER QUERY
   ↓
   POST /ask
   {
     "question": "Quy định về thầu rộng rãi?",
     "mode": "balanced",
     "filters": {"document_type": ["law"]}
   }

2. API LAYER
   ↓
   - Validate input
   - Check authentication (future)
   - Log request

3. CACHE CHECK (L1)
   ↓
   - Hash query + filters
   - Check in-memory LRU cache (500 entries)
   - If HIT → Return cached result (latency <1ms)

4. CACHE CHECK (L2)
   ↓
   - Check Redis (DB 0)
   - TTL: 3600s
   - If HIT → Return cached result (latency ~5-10ms)

5. QUERY ENHANCEMENT (balanced mode)
   ↓
   - Multi-Query: Generate 3 variations
   - Step-Back: Generate broader query
   - Keep original

6. EMBEDDING GENERATION
   ↓
   - Call OpenAI API (text-embedding-3-large)
   - 4 embeddings (4 queries)
   - Latency: ~400ms total

7. VECTOR RETRIEVAL
   ↓
   - Query PostgreSQL with each embedding
   - Apply metadata filters (document_type = "law")
   - Top-K = 10 per query
   - Cosine similarity search
   - Latency: ~200ms (4 queries)

8. RRF FUSION
   ↓
   - Combine results from 4 queries
   - Reciprocal Rank Fusion
   - Deduplicate chunks
   - Output: 20 unique chunks

9. RERANKING (BGE)
   ↓
   - Load model (singleton)
   - Pair-wise scoring: (query, chunk)
   - Batch processing: 20 chunks
   - Sort by relevance score
   - Select top-5
   - Latency: ~150ms

10. CONTEXT PREPARATION
    ↓
    - Format chunks for LLM
    - Add metadata (document name, section)
    - Build prompt with context

11. LLM GENERATION
    ↓
    - Call OpenAI GPT-4o-mini
    - Prompt: system + context + query
    - Max tokens: 500
    - Temperature: 0.3
    - Latency: ~1000ms

12. RESPONSE FORMATTING
    ↓
    - Extract answer
    - Attach sources (document IDs, scores)
    - Calculate total latency
    - Add metadata

13. CACHE UPDATE
    ↓
    - Store in L1 (LRU)
    - Store in L2 (Redis, TTL=3600s)

14. RETURN RESPONSE
    ↓
    {
      "answer": "Thầu rộng rắi là...",
      "sources": [...],
      "latency_ms": 2345,
      "cache_hit": false,
      "mode": "balanced"
    }

Total Latency Breakdown:
  - Cache check: 1ms
  - Enhancement: 0ms (precomputed)
  - Embedding: 400ms
  - Retrieval: 200ms
  - Reranking: 150ms
  - LLM: 1000ms
  - Other: 100ms
  - TOTAL: ~2351ms ✅ Target: <3s
```

---

### 3.2. Document Upload Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                  DOCUMENT UPLOAD FLOW                            │
└─────────────────────────────────────────────────────────────────┘

1. FILE UPLOAD
   ↓
   POST /api/upload/files
   Content-Type: multipart/form-data
   - file: luat_dau_thau_2024.docx
   - category: "legal" (optional)

2. VALIDATION
   ↓
   - Check file type (DOCX/PDF)
   - Check file size (<50MB)
   - Virus scan (future)
   - Validate metadata

3. INITIAL STORAGE
   ↓
   - Generate document_id: "doc_12345"
   - Save file to disk: data/raw/
   - Create record in `documents` table:
     status = 'processing'

4. BACKGROUND JOB CREATION
   ↓
   - Create job in `document_upload_jobs` table
   - Queue job for processing
   - Return job_id to user

5. ASYNC PROCESSING START
   ↓
   - Worker picks up job
   - Update progress: 0%

6. DOCUMENT PARSING
   ↓
   - Parse DOCX/PDF structure
   - Extract hierarchical sections
     * Chapters
     * Articles
     * Clauses
     * Paragraphs
   - Preserve formatting (tables, lists)
   - Progress: 20%

7. METADATA EXTRACTION
   ↓
   - NER (Named Entity Recognition):
     * Law names
     * Decree numbers
     * Dates
     * Organizations
   - Keyword extraction (TF-IDF)
   - Document classification
   - Progress: 40%

8. SEMANTIC ENRICHMENT
   ↓
   - Extract legal concepts
   - Identify bidding terms
   - Cross-reference related laws
   - Progress: 60%

9. CHUNKING
   ↓
   - Hierarchical chunking
   - Chunk size: 1,000 characters
   - Overlap: 200 characters
   - Preserve section boundaries
   - Generate chunk metadata
   - Progress: 70%

10. EMBEDDING GENERATION
    ↓
    - Batch process chunks (10 at a time)
    - Call OpenAI API
    - Generate 3,072-dim vectors
    - Latency: ~100ms per chunk
    - Progress: 70-90%

11. STORAGE
    ↓
    - Insert chunks into `langchain_pg_embedding`
    - Bulk insert (batch of 100)
    - Update `documents.total_chunks`
    - Progress: 95%

12. INDEX CREATION
    ↓
    - Vector index auto-updated
    - JSONB index updated
    - Progress: 98%

13. FINALIZATION
    ↓
    - Update `documents.status = 'active'`
    - Update `document_upload_jobs.status = 'completed'`
    - Clear related caches
    - Progress: 100%

14. NOTIFICATION (Future)
    ↓
    - Webhook to notify uploader
    - Email notification
    - Dashboard update

Total Processing Time:
  - Small doc (10 pages): ~10 seconds
  - Medium doc (50 pages): ~35 seconds
  - Large doc (200 pages): ~2 minutes

Error Handling:
  - Parsing error → status = 'error', retry
  - API rate limit → exponential backoff
  - Network error → retry 3 times
  - Critical error → notify admin
```

---

## 4. RAG Pipeline Architecture

### 4.1. Pipeline Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    RAG PIPELINE COMPONENTS                       │
└─────────────────────────────────────────────────────────────────┘

INPUT: User Query + Filters + Mode
  ↓
┌──────────────────────────────────────┐
│  Query Enhancement Module            │
│  - Multi-Query Generator             │
│  - HyDE Generator                    │
│  - Step-Back Generator               │
│  - Original Query Keeper             │
│  Output: 1-4 enhanced queries        │
└──────────────────┬───────────────────┘
                   ↓
┌──────────────────────────────────────┐
│  Embedding Module                    │
│  - OpenAI text-embedding-3-large     │
│  - Batch processing                  │
│  - Error handling & retry            │
│  Output: Vector embeddings (3072-dim)│
└──────────────────┬───────────────────┘
                   ↓
┌──────────────────────────────────────┐
│  Vector Retrieval Module             │
│  - PGVector similarity search        │
│  - Metadata filtering                │
│  - Top-K selection (dynamic)         │
│  Output: 10-50 candidate chunks      │
└──────────────────┬───────────────────┘
                   ↓
┌──────────────────────────────────────┐
│  Fusion Module (Optional)            │
│  - Reciprocal Rank Fusion (RRF)      │
│  - Deduplication                     │
│  - Score normalization               │
│  Output: Fused + ranked chunks       │
└──────────────────┬───────────────────┘
                   ↓
┌──────────────────────────────────────┐
│  Reranking Module                    │
│  - BGE Cross-Encoder                 │
│  - Pair-wise relevance scoring       │
│  - GPU/CPU optimization              │
│  Output: Top-5 most relevant chunks  │
└──────────────────┬───────────────────┘
                   ↓
┌──────────────────────────────────────┐
│  Context Preparation Module          │
│  - Format chunks for LLM             │
│  - Add metadata annotations          │
│  - Build structured prompt           │
│  Output: Enriched context            │
└──────────────────┬───────────────────┘
                   ↓
┌──────────────────────────────────────┐
│  LLM Generation Module               │
│  - GPT-4o-mini                       │
│  - Temperature: 0.3                  │
│  - Max tokens: 500                   │
│  Output: Natural language answer     │
└──────────────────┬───────────────────┘
                   ↓
OUTPUT: Answer + Sources + Metadata
```

### 4.2. Mode Comparison

| Component       | Fast         | Balanced ⭐    | Quality         | Adaptive  |
| --------------- | ------------ | -------------- | --------------- | --------- |
| Multi-Query     | ❌           | ✅ (3 queries) | ✅ (4 queries)  | Dynamic   |
| HyDE            | ❌           | ❌             | ✅              | Dynamic   |
| Step-Back       | ❌           | ✅             | ✅              | Dynamic   |
| Original        | ✅           | ✅             | ✅              | ✅        |
| Top-K Retrieval | 5            | 10             | 20              | 5-20      |
| RRF Fusion      | ❌           | ✅             | ✅              | ✅        |
| Reranking       | ❌           | ✅ (BGE)       | ✅ (BGE)        | ✅ (BGE)  |
| Final Chunks    | 5            | 5              | 5               | 3-7       |
| Avg Latency     | ~1s          | ~2.3s          | ~3.5s           | ~2-4s     |
| Use Case        | Quick lookup | Production     | Complex queries | Auto-tune |

---

## 5. Caching Architecture

### 5.1. Three-Tier Cache System

```
┌─────────────────────────────────────────────────────────────────┐
│                   3-TIER CACHE ARCHITECTURE                      │
└─────────────────────────────────────────────────────────────────┘

Query Request
  ↓
┌────────────────────────────────────────────┐
│  L1 CACHE (In-Memory LRU)                  │
│  - Technology: functools.lru_cache         │
│  - Location: Python process memory         │
│  - Max Size: 500 entries                   │
│  - Eviction: Least Recently Used           │
│  - Hit Rate: 40-60% (single user)          │
│  - Latency: <1ms                           │
│  - Persistence: No (lost on restart)       │
│  - Scope: Per-process                      │
│  └─────────┬──────────────────────────────┘
│            │ MISS
│            ▼
│  ┌────────────────────────────────────────┐
│  │  L2 CACHE (Redis)                      │
│  │  - Technology: Redis 7+                │
│  │  - Location: localhost:6379            │
│  │  - Database: DB 0 (retrieval cache)    │
│  │  - TTL: 3600s (1 hour)                 │
│  │  - Max Memory: 2GB                     │
│  │  - Eviction: allkeys-lru               │
│  │  - Hit Rate: 20-30% (multi-user)       │
│  │  - Latency: ~5-10ms                    │
│  │  - Persistence: Optional (RDB/AOF)     │
│  │  - Scope: Cross-process                │
│  └─────────┬──────────────────────────────┘
│            │ MISS
│            ▼
│  ┌────────────────────────────────────────┐
│  │  L3 CACHE (PostgreSQL)                 │
│  │  - Technology: Native DB storage       │
│  │  - Always available (fallback)         │
│  │  - No TTL (permanent)                  │
│  │  - Hit Rate: 100% (always computed)    │
│  │  - Latency: ~50ms (vector search)      │
│  │  - Persistence: Yes                    │
│  │  - Scope: Global                       │
│  └────────────────────────────────────────┘
│            │
│            ▼
│       COMPUTE RESULT
│            │
│            ▼
│       UPDATE CACHES (L2 → L1)
│            │
│            ▼
│       RETURN TO USER
└────────────────────────────────────────────┘
```

### 5.2. Cache Key Strategy

**Key Format:**

```python
cache_key = hashlib.md5(
    json.dumps({
        "question": question,
        "mode": mode,
        "filters": filters,
        "top_k": top_k
    }, sort_keys=True).encode()
).hexdigest()
```

**Cache Value:**

```json
{
  "answer": "...",
  "sources": [...],
  "mode": "balanced",
  "timestamp": "2025-11-24T10:00:00Z",
  "latency_ms": 2345,
  "version": "2.0"
}
```

### 5.3. Cache Invalidation

**Triggers:**

1. Document status change (active → expired)
2. Document metadata update
3. Document deletion
4. Manual cache clear (`POST /clear_cache`)
5. TTL expiration (L2 only)

**Strategies:**

- **Granular:** Invalidate specific queries related to document
- **Broad:** Clear all cache when critical data changes
- **Lazy:** Let TTL handle expiration (preferred)

---

## 6. Deployment Architecture

### 6.1. Current Deployment (Development)

```
┌───────────────────────────────────────┐
│  Local Development Environment        │
│                                       │
│  ┌─────────────────────────────────┐ │
│  │  FastAPI App (Uvicorn)          │ │
│  │  - Port: 8000                   │ │
│  │  - Workers: 1                   │ │
│  │  - Reload: True                 │ │
│  └─────────────────────────────────┘ │
│                                       │
│  ┌─────────────────────────────────┐ │
│  │  PostgreSQL 18                  │ │
│  │  - localhost:5432               │ │
│  │  - Database: rag_bidding_v2     │ │
│  └─────────────────────────────────┘ │
│                                       │
│  ┌─────────────────────────────────┐ │
│  │  Redis 7                        │ │
│  │  - localhost:6379               │ │
│  │  - DB 0: Cache                  │ │
│  └─────────────────────────────────┘ │
└───────────────────────────────────────┘

Startup Command:
  ./start_server.sh
  # uvicorn src.api.main:app --reload --port 8000
```

### 6.2. Planned Production Deployment

```
┌────────────────────────────────────────────────────────────────┐
│                    PRODUCTION ARCHITECTURE                      │
└────────────────────────────────────────────────────────────────┘

Internet
  │
  ▼
┌──────────────┐
│ Load Balancer│ (Nginx/HAProxy)
│ - SSL/TLS    │
│ - Rate Limit │
└───────┬──────┘
        │
        ▼
┌─────────────────────────────────────┐
│  Application Servers (x3)           │
│  ┌───────────────────────────────┐  │
│  │ FastAPI + Gunicorn + Uvicorn  │  │
│  │ - Workers: 4 per server       │  │
│  │ - Total capacity: 12 workers  │  │
│  └───────────────────────────────┘  │
└─────────────────┬───────────────────┘
                  │
                  ▼
          ┌───────────────┐
          │  pgBouncer    │
          │  Connection   │
          │  Pooling      │
          └───────┬───────┘
                  │
        ┌─────────┴─────────┐
        │                   │
        ▼                   ▼
┌──────────────┐   ┌──────────────┐
│ PostgreSQL   │   │ Redis Cluster│
│ Primary      │   │ (Master +    │
│ + Replica    │   │  2 Replicas) │
└──────────────┘   └──────────────┘
```

**Estimated Capacity:**

- Concurrent users: 100+
- Queries per second: 50
- Documents: 1M+
- Database size: 200GB

---

## 7. Security Architecture

### 7.1. Security Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                    SECURITY ARCHITECTURE                         │
└─────────────────────────────────────────────────────────────────┘

1. NETWORK LAYER
   - TLS 1.3 encryption (HTTPS)
   - Firewall rules (ports 443, 80 only)
   - DDoS protection (Cloudflare)

2. API GATEWAY LAYER
   - Rate limiting (100 req/min per IP)
   - IP whitelisting (optional)
   - Request size limits (50MB)
   - CORS policy enforcement

3. AUTHENTICATION LAYER (Future)
   - JWT tokens (RS256)
   - OAuth2 integration (Google, Microsoft)
   - API key authentication
   - Session management

4. AUTHORIZATION LAYER (Future)
   - Role-Based Access Control (RBAC)
     * user: Query only
     * manager: Upload documents
     * admin: Full access
   - Resource-level permissions
   - API endpoint restrictions

5. DATA LAYER
   - Encrypted connections (SSL/TLS)
   - Encrypted at rest (AES-256)
   - Secrets in environment variables
   - No hardcoded credentials

6. APPLICATION LAYER
   - Input validation (Pydantic)
   - SQL injection prevention (ORM)
   - XSS prevention (sanitization)
   - CSRF protection (tokens)

7. MONITORING LAYER
   - Audit logs (all actions)
   - Anomaly detection
   - Intrusion detection (planned)
   - Security alerts
```

---

## 8. Performance & Scalability

### 8.1. Current Performance Metrics

| Metric                   | Value       | Target   | Status          |
| ------------------------ | ----------- | -------- | --------------- |
| Query Latency (fast)     | ~1s         | <1.5s    | ✅              |
| Query Latency (balanced) | ~2.3s       | <3s      | ✅              |
| Query Latency (quality)  | ~3.5s       | <5s      | ✅              |
| Cache Hit Rate (L1)      | 40-60%      | >40%     | ✅              |
| Cache Hit Rate (L2)      | 20-30%      | >20%     | ✅              |
| Vector Search Time       | ~50ms       | <100ms   | ✅              |
| Document Processing      | ~0.35s/page | <1s/page | ✅              |
| Concurrent Users         | ~10         | 100+     | ❌ Need pooling |
| Database Size            | 149MB       | <200GB   | ✅              |

### 8.2. Scalability Strategies

**Vertical Scaling:**

- ✅ Optimize SQL queries
- ✅ Add indexes (HNSW vector index)
- ✅ Connection pooling (pgBouncer)
- ✅ Increase server resources (CPU, RAM)

**Horizontal Scaling:**

- ⏳ Multiple application servers
- ⏳ Load balancer (Nginx)
- ⏳ Database replication (read replicas)
- ⏳ Redis cluster (distributed cache)

**Optimization:**

- ✅ Multi-tier caching
- ✅ Singleton pattern for models
- ✅ Batch processing
- ⏳ Query result pagination
- ⏳ Async processing (Celery)

---

## Tài Liệu Liên Quan

- `01_System_Specification.md` - System requirements
- `02_Use_Cases.md` - Use case scenarios
- `03_Database_Schema.md` - Database design
- `05_API_Specification.md` - API documentation
- `/temp/system_architecture.txt` - Current architecture reference
