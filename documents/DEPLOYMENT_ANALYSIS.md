# 🔍 RAG-Bidding Codebase Analysis for Cloud Deployment

> **Ngày phân tích**: 26/01/2026  
> **Mục đích**: Điều tra toàn bộ codebase để đưa ra kết luận chính xác cho deployment

---

## 📊 Tổng Quan Kiến Trúc

### 1. Entry Point & Application Structure

```
src/api/main.py
├── FastAPI App với Lifespan Context Manager
├── Middleware Stack (CORS → Logging → RateLimit → Auth)
├── Routers:
│   ├── /api/auth/* - Authentication (JWT)
│   ├── /api/conversations/* - Chat with RAG
│   ├── /api/documents/* - Document Management
│   ├── /api/analytics/* - Usage Analytics
│   ├── /api/cache/* - Cache Management
│   └── /api/user-upload/* - User Document Contribution
└── System Endpoints:
    ├── /health - DB connectivity check
    ├── /ask - Quick Q&A (no auth)
    ├── /stats - System configuration
    └── /features - Feature flags status
```

### 2. Startup Flow (Lifespan Context Manager)

```python
# src/api/main.py - Startup sequence
async def lifespan(app: FastAPI):
    # 1. Initialize database connection pool (NullPool for async)
    init_database()
    await startup_database()
    
    # 2. Bootstrap vector store (create tables, collection)
    bootstrap()  # PGVector tables + extensions
    
    # 3. Pre-load BGE Reranker (SINGLETON - ~1.2GB RAM)
    reranker = get_singleton_reranker()  # ⚠️ HEAVY OPERATION
    
    # 4. Pre-load QueryEnhancer (GPT-4o-mini API)
    enhancer = QueryEnhancer(...)  # Lightweight
    
    yield  # App runs
    
    # Shutdown
    await shutdown_database()
```

---

## 🔴 CRITICAL FINDINGS: Memory & Resource Usage

### 1. BGE Reranker - Model Loading

**File**: `src/retrieval/ranking/bge_reranker.py`

```python
# Model: BAAI/bge-reranker-v2-m3
# Size: ~1.2GB RAM/VRAM
# Pattern: SINGLETON (thread-safe với double-checked locking)

_reranker_instance = None  # Global singleton
_reranker_lock = threading.Lock()
_cuda_oom_fallback = False  # Fallback flag

def get_singleton_reranker(...):
    global _reranker_instance, _cuda_oom_fallback
    
    # Fast path - return existing instance
    if _reranker_instance is not None:
        return _reranker_instance
    
    # Slow path - create new instance (with lock)
    with _reranker_lock:
        if _reranker_instance is None:
            try:
                _reranker_instance = BGEReranker(device=device)
            except Exception as e:
                if "cuda out of memory" in str(e).lower():
                    _cuda_oom_fallback = True
                    return OpenAIReranker()  # ✅ Fallback
```

**⚠️ VẤN ĐỀ VỚI GUNICORN WORKERS**:
- Singleton chỉ hoạt động **trong cùng process**
- Gunicorn **fork** workers → mỗi worker có **memory space riêng**
- 4 workers = 4 copies của BGE model = **~4.8GB RAM chỉ cho model**

### 2. Fallback Mechanism (3 Layers)

```python
# Layer 1: Init-time fallback
try:
    _reranker_instance = BGEReranker(device="cuda")
except OOM:
    return OpenAIReranker()

# Layer 2: Runtime fallback (during rerank)
try:
    scores = model.predict(pairs)
except OOM:
    _cuda_oom_fallback = True
    return OpenAIReranker().rerank(query, docs)  # Immediate

# Layer 3: Future calls skip BGE entirely
if _cuda_oom_fallback:
    return OpenAIReranker()

# Layer 4: Final fallback (if OpenAI also fails)
return [(doc, 1.0 - i*0.1) for i, doc in enumerate(docs[:top_k])]
```

### 3. Memory Breakdown Per Worker

| Component | RAM Usage | Notes |
|-----------|-----------|-------|
| Python Runtime | ~100MB | Base Python interpreter |
| FastAPI + Dependencies | ~200MB | LangChain, SQLAlchemy, etc. |
| BGE Reranker Model | ~1.2-1.5GB | CrossEncoder weights |
| OpenAI Embeddings | ~50MB | Tokenizer only (API-based) |
| PostgreSQL Connections | ~50MB | With NullPool |
| Redis Connections | ~10MB | 5 databases |
| Request Processing | ~100MB | Buffers, temp data |
| **Total per Worker** | **~1.7-2GB** | Without heavy requests |

**4 Workers Total**: ~6.8-8GB RAM

---

## 🗄️ Database Configuration

### File: `src/config/database.py`

```python
class DatabaseConfig:
    def _setup_engine(self):
        self._engine = create_async_engine(
            self.database_url,
            poolclass=NullPool,  # ⚠️ NO CONNECTION POOLING
            pool_pre_ping=True,
            echo=False,
            future=True,
        )
```

**⚠️ QUAN TRỌNG**: Sử dụng **NullPool** - mỗi request tạo connection mới

**Lý do**: NullPool tương thích với async engine, nhưng cho production nên:
- Option 1: Dùng pgBouncer external
- Option 2: Cloud SQL Proxy handles pooling

---

## 🔄 Cache Architecture (5 Redis Databases)

### File: `src/config/feature_flags.py`

```python
# Redis Database Assignments
REDIS_DB_CACHE = 0      # General retrieval cache (L2)
REDIS_DB_SESSIONS = 1   # Chat sessions (if enabled)
ANSWER_CACHE_DB = 2     # Final RAG answers
SEMANTIC_CACHE_DB = 3   # Query embeddings for similarity
RATE_LIMIT_REDIS_DB = 4 # Rate limiting counters

# Feature Flags
ENABLE_REDIS_CACHE = os.getenv("ENABLE_REDIS_CACHE", "false")
ENABLE_ANSWER_CACHE = os.getenv("ENABLE_ANSWER_CACHE", "true")
ENABLE_SEMANTIC_CACHE = os.getenv("ENABLE_SEMANTIC_CACHE", "true")
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true")
```

### Cache Layers

```
Request Flow:
┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌──────────────┐
│  L1 Cache   │ → │ Answer Cache│ → │Semantic Cache│ → │ RAG Pipeline │
│ (In-Memory) │   │  (Redis:2)  │   │   (Redis:3)  │   │   (Full)     │
└─────────────┘   └─────────────┘   └─────────────┘   └──────────────┘
    LRU 100          Exact Match      Cosine+BGE          GPT + DB
    ~1ms              ~5ms             ~450ms              ~3000ms
```

---

## 🔐 Authentication Flow

### File: `src/api/middleware/auth_middleware.py`

```python
class AuthMiddleware(BaseHTTPMiddleware):
    SKIP_PATHS = [
        "/health", "/docs", "/redoc", "/openapi.json",
        "/api/auth/login", "/api/auth/register", "/api/auth/refresh",
    ]
    
    # Extracts JWT → adds to request.state
    # Does NOT block - just enriches request
```

### File: `src/auth/jwt_handler.py`

```python
# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE = 30 minutes
REFRESH_TOKEN_EXPIRE = 7 days
```

---

## 📡 RAG Pipeline Flow

### File: `src/generation/chains/qa_chain.py`

```python
def answer(question, mode="balanced", reranker_type="bge"):
    # 1. Check casual query (greetings, thanks, etc.)
    is_casual, response = is_casual_query(question)
    if is_casual:
        return response
    
    # 2. Check Answer Cache (exact match)
    cache = get_answer_cache()
    cached = cache.get(question)
    if cached:
        return cached  # ⚡ ~5ms
    
    # 3. Check Semantic Cache (similar queries)
    semantic_cache = get_semantic_cache_v2()
    match = semantic_cache.find_similar(question)
    if match:
        return answer_cache.get(match.answer_cache_key)  # ⚡ ~450ms
    
    # 4. Run full RAG pipeline
    retriever = create_retriever(mode=mode, reranker_type=reranker_type)
    docs = retriever.retrieve(question)
    answer = llm.generate(question, docs)
    
    # 5. Cache result
    cache.set(question, answer)
    semantic_cache.store_embedding(question, embedding, cache_key)
    
    return answer  # ⏱️ ~2-5s
```

### RAG Modes

```python
# File: src/retrieval/retrievers/__init__.py

def create_retriever(mode, enable_reranking=True, reranker_type="bge"):
    # Base retriever (always)
    base = BaseVectorRetriever(k=5)
    
    if mode == "fast":
        # No enhancement, no reranking
        return base  # ~1s
    
    elif mode == "balanced":  # DEFAULT
        # Multi-Query + Step-Back + BGE Reranking
        return EnhancedRetriever(
            strategies=[MULTI_QUERY, STEP_BACK],
            reranker=get_singleton_reranker(),
        )  # ~2-3s
    
    elif mode == "quality":
        # All 4 strategies + RRF fusion
        return FusionRetriever(
            strategies=[MULTI_QUERY, HYDE, STEP_BACK, DECOMPOSITION],
            reranker=reranker,
        )  # ~3-5s
```

---

## 🌐 API Endpoints Summary

| Endpoint | Auth Required | Heavy Operations | Memory Impact |
|----------|---------------|------------------|---------------|
| `POST /ask` | ❌ No | BGE + GPT + DB | High |
| `POST /api/conversations/{id}/messages` | ✅ Yes | BGE + GPT + DB | High |
| `GET /api/conversations` | ✅ Yes | DB only | Low |
| `GET /api/documents` | ✅ Yes | DB only | Low |
| `POST /api/auth/login` | ❌ No | JWT only | Low |
| `GET /health` | ❌ No | DB ping | Very Low |

---

## 📋 Environment Variables Required

### Critical (Must Have)

```bash
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/rag_bidding_v3
OPENAI_API_KEY=sk-proj-...
JWT_SECRET_KEY=your-256-bit-secret
```

### Feature Flags

```bash
# RAG Configuration
RAG_MODE=balanced                    # fast, balanced, quality
ENABLE_RERANKING=true               # Enable BGE/OpenAI reranking
ENABLE_QUERY_ENHANCEMENT=true       # Multi-Query, Step-Back

# Cache Settings
ENABLE_REDIS_CACHE=true             # Enable Redis for retrieval cache
ENABLE_ANSWER_CACHE=true            # Cache final answers (Redis:2)
ENABLE_SEMANTIC_CACHE=true          # Semantic similarity cache (Redis:3)
RATE_LIMIT_ENABLED=true             # Rate limiting (Redis:4)

# Redis Connection
REDIS_HOST=10.0.0.3
REDIS_PORT=6379

# CORS
CORS_ORIGINS=https://your-frontend.com

# Gunicorn
GUNICORN_WORKERS=1                  # ⚠️ CRITICAL for memory
GUNICORN_TIMEOUT=300
```

---

## 🎯 DEPLOYMENT CONCLUSIONS

### Option 1: Minimal Memory (RECOMMENDED for Cloud Run)

```bash
# Configuration
GUNICORN_WORKERS=1
ENABLE_RERANKING=false    # Skip BGE model
ENABLE_REDIS_CACHE=false  # Skip Redis dependency

# Cloud Run Settings
--memory=2Gi
--cpu=1
--min-instances=0
--max-instances=10
--concurrency=80
```

**Pros**: Simple, cheap, fast cold starts  
**Cons**: Lower quality RAG (no reranking)

### Option 2: BGE Reranking with Auto-Fallback (BALANCED)

```bash
# Configuration
GUNICORN_WORKERS=1        # Single worker
ENABLE_RERANKING=true     # BGE enabled
ENABLE_REDIS_CACHE=true   # Full caching

# Cloud Run Settings
--memory=4Gi              # Enough for 1 BGE instance
--cpu=2
--min-instances=1         # Avoid cold start (model loading)
--max-instances=5
--concurrency=50
--timeout=300
```

**Pros**: Good quality, auto-fallback to OpenAI if OOM  
**Cons**: 30-60s cold start, higher cost

### Option 3: OpenAI Reranker Only (HIGH QUALITY, NO LOCAL MODEL)

```bash
# Configuration
GUNICORN_WORKERS=2
RERANKER_TYPE=openai      # Skip BGE entirely
ENABLE_REDIS_CACHE=true

# Cloud Run Settings
--memory=2Gi
--cpu=2
--min-instances=0
--max-instances=10
--concurrency=80
```

**Pros**: Fast cold start, high quality (GPT-4o-mini)  
**Cons**: Higher API costs, API latency

### Option 4: Production Grade (MAXIMUM PERFORMANCE)

```bash
# Configuration
GUNICORN_WORKERS=1        # Per container
ENABLE_RERANKING=true
ENABLE_REDIS_CACHE=true
ENABLE_ANSWER_CACHE=true
ENABLE_SEMANTIC_CACHE=true

# Cloud Run Settings
--memory=8Gi              # Safe margin
--cpu=4
--min-instances=2         # Always warm
--max-instances=20
--concurrency=30
--timeout=300
--cpu-boost
```

**Pros**: Maximum performance, warm instances  
**Cons**: Highest cost

---

## ⚠️ CRITICAL WARNINGS

### 1. Gunicorn Workers vs BGE Model

```
⚠️ QUAN TRỌNG: Mỗi Gunicorn worker load BGE model RIÊNG!

4 workers × 1.5GB = 6GB RAM chỉ cho model
→ LUÔN dùng GUNICORN_WORKERS=1 cho Cloud Run

Cloud Run handles scaling bằng cách spawn nhiều container instances,
KHÔNG phải nhiều workers trong 1 container.
```

### 2. Cold Start Time

```
Startup sequence:
1. Container start: ~5s
2. Python import: ~10s (heavy dependencies)
3. Database init: ~2s
4. Vector store bootstrap: ~3s
5. BGE model loading: ~30-40s (⚠️ HEAVIEST)
6. Total: 50-60s cold start

→ Set min-instances=1 để avoid cold start
```

### 3. Database Connection

```
Using NullPool (no connection pooling in app)
→ Cloud SQL Proxy handles pooling externally
→ Or add pgBouncer sidecar container
```

### 4. Redis Dependency

```
If ENABLE_REDIS_CACHE=true:
- MUST have Memorystore Redis
- MUST have VPC Connector
- Redis uses 5 separate databases (0-4)
```

---

## 📊 Final Recommendation Matrix

| Scenario | Workers | Memory | CPU | Reranking | Min Instances | Cost |
|----------|---------|--------|-----|-----------|---------------|------|
| **Dev/Test** | 1 | 2Gi | 1 | false | 0 | $ |
| **Staging** | 1 | 4Gi | 2 | bge (auto-fallback) | 0 | $$ |
| **Production Light** | 1 | 4Gi | 2 | openai | 1 | $$$ |
| **Production Full** | 1 | 8Gi | 4 | bge | 2 | $$$$ |

---

## ✅ Checklist Before Deployment

- [ ] Set `GUNICORN_WORKERS=1` (CRITICAL)
- [ ] Verify DATABASE_URL format: `postgresql+psycopg://...`
- [ ] Set OPENAI_API_KEY
- [ ] Set JWT_SECRET_KEY (64+ chars recommended)
- [ ] Configure CORS_ORIGINS for frontend domain
- [ ] If using Redis: Create Memorystore + VPC Connector
- [ ] If using Cloud SQL: Enable pgvector extension
- [ ] Test health endpoint after deploy: `curl $SERVICE_URL/health`
- [ ] Check logs for BGE loading: `"BGEReranker loaded successfully"`

---

*Document generated: 26/01/2026*
