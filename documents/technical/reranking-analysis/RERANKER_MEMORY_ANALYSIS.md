# 🔍 Phân Tích Vấn Đề Memory - BGE Reranker

**Ngày**: 12/11/2025  
**Vấn đề**: CUDA OOM và memory leak khi chạy performance tests  
**Tác động**: 20GB+ RAM, test timeout, không thể scale concurrent users

---

## 📊 Tóm Tắt Vấn Đề

### Log Error
```
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 978.00 MiB. 
GPU has a total capacity of 11.62 GiB of which 57.50 MiB is free. 
Including non-PyTorch memory, this process has 10.35 GiB memory in use.
Of the allocated memory 10.23 GiB is allocated by PyTorch.

[2025-11-08 08:55:35] [INFO] src.retrieval.ranking.bge_reranker: 
Initializing reranker: BAAI/bge-reranker-v2-m3
[2025-11-08 08:55:35] [INFO] src.retrieval.ranking.bge_reranker: 
GPU detected! Using CUDA for acceleration
```

### Memory Usage Pattern
- **Một phiên test**: 20GB+ RAM
- **Single BGE model**: ~1.2GB (BAAI/bge-reranker-v2-m3)
- **Concurrent test**: Multiple model instances → Cumulative memory

---

## 🔎 Nguyên Nhân Gốc Rễ

### 1. **Reranker Được Tạo Mới Mỗi Request**

**File**: `src/api/main.py::ask()`
```python
@app.post("/ask", response_model=AskResponse)
def ask(body: AskIn):
    from src.retrieval.retrievers import create_retriever
    
    enable_reranking = settings.enable_reranking and body.mode != "fast"
    retriever = create_retriever(mode=body.mode, enable_reranking=enable_reranking)
    # ❌ MỖI REQUEST TẠO RETRIEVER MỚI!
```

**File**: `src/retrieval/retrievers/__init__.py::create_retriever()`
```python
def create_retriever(mode: str = "balanced", enable_reranking: bool = True, ...):
    if enable_reranking and reranker is None:
        reranker = BGEReranker()  # ❌ LOAD MODEL MỚI MỖI LẦN!
```

**File**: `src/generation/chains/qa_chain.py::answer()`
```python
def answer(question: str, mode: str | None = None, ...):
    retriever = create_retriever(mode=selected_mode, enable_reranking=enable_reranking)
    # ❌ CŨNG TẠO RETRIEVER MỚI!
```

### 2. **Model Loading Lifecycle**

```python
# src/retrieval/ranking/bge_reranker.py
class BGEReranker(BaseReranker):
    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3", device=None):
        # Load 1.2GB model vào memory
        self.model = CrossEncoder(
            model_name,
            device=device,  # CUDA nếu available
            max_length=512
        )
        # ❌ KHÔNG CÓ CLEANUP MECHANISM
        # ❌ KHÔNG CÓ MODEL CACHING
```

### 3. **Performance Test Amplifies Problem**

**File**: `scripts/tests/performance/run_performance_tests.py`
```python
# Test 1: Query Latency
# 15 queries × 4 modes × 3 runs = 180 requests
# → 180 BGEReranker instances → 216GB theoretical memory!

# Test 2: Multi-user Load  
# 10 concurrent users × 3 queries = 30 simultaneous requests
# → 30 BGEReranker instances → 36GB memory!
```

**Actual Impact** (từ log):
```json
{
  "users_10": {
    "query_success_rate": 0.367,  // Chỉ 36.7% thành công
    "failed_queries": 19,          // 19/30 queries failed
    "avg_response_time_ms": 9620   // Gấp 2.5x so với 5 users
  },
  "breaking_point_analysis": {
    "max_stable_concurrent_users": 5,  // Chỉ chịu được 5 users!
    "breaking_point_users": 10
  }
}
```

---

## 🏭 Reranking Strategies - Industry Best Practices

### Production Systems Comparison

| System | Reranker Type | Caching Strategy | Notes |
|--------|---------------|------------------|-------|
| **Perplexity.ai** | Cohere Rerank API | API-managed | Cloud-based, no local memory |
| **You.com** | Custom reranker | Singleton pattern | Model cached per worker |
| **ChatGPT** | Proprietary | Distributed cache | Multi-tier caching |
| **RAG Bidding** ❌ | BGE (local) | **None** | Tạo mới mỗi request! |

### Standard RAG Pipeline với Reranking

```python
# Industry Standard Flow:
# 1. Retrieve nhiều docs (k=20-50)
retriever.search(query, k=20)

# 2. Rerank với CACHED model
reranker = get_cached_reranker()  # ✅ Singleton
top_docs = reranker.rerank(query, docs, top_k=5)

# 3. Use top-k cho generation
llm.generate(query, top_docs)
```

### Các Reranker Phổ Biến

**Commercial APIs** (no memory management needed):
- Cohere Rerank API
- Voyage AI Rerank
- Jina Reranker API

**Open-source Models** (cần cache properly):
- `BAAI/bge-reranker-v2-m3` ⭐ (đang dùng, multilingual)
- `cross-encoder/ms-marco-MiniLM-L-6-v2` (English only)
- `vinai/phobert-base-v2` (Vietnamese, chưa fine-tuned)

---

## ✅ Solutions

### Solution 1: Singleton Pattern (Quick Fix)

**File**: `src/retrieval/ranking/bge_reranker.py`
```python
import threading

_reranker_instance = None
_reranker_lock = threading.Lock()

def get_singleton_reranker(
    model_name: str = "BAAI/bge-reranker-v2-m3",
    device: str = None
):
    """Get or create singleton reranker instance."""
    global _reranker_instance
    
    if _reranker_instance is None:
        with _reranker_lock:
            if _reranker_instance is None:
                _reranker_instance = BGEReranker(
                    model_name=model_name,
                    device=device
                )
                logger.info("✅ Created singleton BGEReranker")
    
    return _reranker_instance
```

**File**: `src/retrieval/retrievers/__init__.py`
```python
def create_retriever(mode: str = "balanced", enable_reranking: bool = True, ...):
    if enable_reranking and reranker is None:
        # ✅ Use singleton instead of creating new instance
        from src.retrieval.ranking.bge_reranker import get_singleton_reranker
        reranker = get_singleton_reranker()
    
    # ... rest of code
```

**Expected Impact**:
- Memory: 20GB → 1.5GB (13x reduction)
- Concurrent users: 5 → 50+ (10x improvement)
- Response time: 9.6s → <2s (5x faster)

### Solution 2: FastAPI Dependency Injection (Recommended)

**File**: `src/api/dependencies.py` (new file)
```python
from functools import lru_cache
from src.retrieval.ranking import BGEReranker

@lru_cache()
def get_shared_reranker() -> BGEReranker:
    """
    FastAPI dependency: Singleton reranker per worker process.
    
    Benefits:
    - Automatic lifecycle management
    - Thread-safe by default
    - Compatible with uvicorn workers
    """
    return BGEReranker()
```

**File**: `src/api/main.py`
```python
from fastapi import Depends
from .dependencies import get_shared_reranker

@app.post("/ask")
def ask(
    body: AskIn,
    reranker: BGEReranker = Depends(get_shared_reranker)  # ✅ Injected
):
    retriever = create_retriever(
        mode=body.mode,
        enable_reranking=settings.enable_reranking,
        reranker=reranker  # ✅ Pass cached instance
    )
    # ... rest of code
```

**Benefits**:
- ✅ Automatic cleanup khi worker restart
- ✅ Compatible với multi-worker deployment
- ✅ Testable (có thể mock dependency)

### Solution 3: Manual Memory Cleanup (Temporary)

**File**: `src/retrieval/ranking/bge_reranker.py`
```python
import gc

class BGEReranker(BaseReranker):
    def __del__(self):
        """Cleanup when instance is destroyed."""
        if hasattr(self, 'model') and self.model is not None:
            del self.model
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()
            logger.info("🧹 Cleaned up BGEReranker resources")
    
    def rerank(self, query: str, documents: List[Document], top_k: int = 5):
        # ... existing code ...
        
        # Clear cache after heavy operation
        if self.device == "cuda" and len(documents) > 20:
            torch.cuda.empty_cache()
        
        return doc_scores[:top_k]
```

**Limitations**:
- ⚠️ Không giải quyết root cause
- ⚠️ Vẫn load model nhiều lần
- ⚠️ Chỉ giảm memory footprint, không cải thiện performance

---

## 🎯 Khuyến Nghị Triển Khai

### Phase 1: Immediate Fix (1-2 hours)
1. ✅ Implement Solution 1 (Singleton pattern)
2. ✅ Add manual cleanup (`__del__`)
3. ✅ Test với performance suite
4. ✅ Monitor memory usage

### Phase 2: Production-ready (1 day)
1. ✅ Migrate to Solution 2 (FastAPI DI)
2. ✅ Add health check endpoint cho reranker status
3. ✅ Implement graceful degradation (fallback to no-rerank)
4. ✅ Add metrics (reranker latency, cache hit rate)

### Phase 3: Optimization (1 week)
1. ✅ Evaluate alternative rerankers (lighter models)
2. ✅ Implement result caching (cache reranked results)
3. ✅ Add connection pooling cho DB
4. ✅ Load testing với 50+ concurrent users

---

## 📈 Expected Performance Improvements

| Metric | Before | After (Singleton) | After (Full Optimization) |
|--------|--------|-------------------|---------------------------|
| **Memory per test** | 20GB | 1.5GB | 1GB |
| **Concurrent users** | 5 | 30 | 50+ |
| **Avg response time** | 9.6s | 3s | <2s |
| **Query success rate** | 36.7% | 90% | 95%+ |
| **GPU utilization** | OOM crash | 80% | 85% |

---

## 🔗 Related Files

**Problem Files**:
- `src/api/main.py::ask()` - Creates retriever per request
- `src/retrieval/retrievers/__init__.py::create_retriever()` - Creates reranker
- `src/generation/chains/qa_chain.py::answer()` - Also creates retriever

**Solution Files** (need to create/modify):
- `src/api/dependencies.py` - New file for FastAPI dependencies
- `src/retrieval/ranking/bge_reranker.py` - Add singleton getter
- `src/config/models.py` - Add reranker cache settings

**Test Files** (verify fix):
- `scripts/tests/performance/run_performance_tests.py`
- `scripts/tests/performance/test_multi_user_queries.py`

---

## 📚 References

**Industry Articles**:
- [Building Scalable RAG Systems](https://www.deepset.ai/blog/scalable-rag)
- [Reranking Best Practices](https://cohere.com/blog/rerank)
- [Memory Management in PyTorch](https://pytorch.org/docs/stable/notes/cuda.html)

**Similar Issues**:
- [Hugging Face Forum: Model Caching](https://discuss.huggingface.co/t/how-to-cache-model)
- [FastAPI: Singleton Dependencies](https://fastapi.tiangolo.com/advanced/dependencies-with-cache/)

---

**Status**: 🚨 CRITICAL - Blocking production scaling  
**Priority**: P0 - Fix immediately  
**Assignee**: Development team  
**Estimated effort**: 1-2 days for complete fix
