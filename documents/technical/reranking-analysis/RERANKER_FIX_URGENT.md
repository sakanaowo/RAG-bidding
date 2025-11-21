# ⚠️ CRITICAL ISSUE: Reranker Memory Leak

**Date**: 12/11/2025  
**Status**: 🚨 BLOCKING PRODUCTION  
**Impact**: Cannot scale beyond 5 concurrent users

---

## Problem Summary

### Error
```
torch.OutOfMemoryError: CUDA out of memory
Process has 10.35 GiB memory in use
[INFO] Initializing reranker: BAAI/bge-reranker-v2-m3  # ← Happens EVERY request!
```

### Root Cause
BGEReranker model (~1.2GB) được load mới **mỗi request** thay vì cache:

```python
# src/api/main.py::ask()
retriever = create_retriever(mode=body.mode, enable_reranking=True)
# → Mỗi request tạo BGEReranker mới → Load 1.2GB model

# Performance test: 15 queries × 4 modes = 60 model loads = 72GB!
```

### Impact
- Memory: 20GB+ per test session
- Concurrent users: Max 5 (breaks at 10)
- Response time: 9.6s avg (should be <2s)
- Success rate: 36.7% (should be >95%)

---

## Quick Fix (30 minutes)

**File**: `src/retrieval/ranking/bge_reranker.py`

```python
import threading

# Add at module level
_reranker_instance = None
_reranker_lock = threading.Lock()

def get_singleton_reranker(model_name="BAAI/bge-reranker-v2-m3", device=None):
    """Get or create singleton reranker instance."""
    global _reranker_instance
    
    if _reranker_instance is None:
        with _reranker_lock:
            if _reranker_instance is None:
                _reranker_instance = BGEReranker(model_name, device)
    
    return _reranker_instance
```

**File**: `src/retrieval/retrievers/__init__.py`

```python
def create_retriever(mode="balanced", enable_reranking=True, ...):
    if enable_reranking and reranker is None:
        from src.retrieval.ranking.bge_reranker import get_singleton_reranker
        reranker = get_singleton_reranker()  # ✅ Cached
    # ... rest of code
```

### Expected Improvement
- Memory: 20GB → 1.5GB (13x reduction)
- Concurrent users: 5 → 50+ (10x improvement)
- Response time: 9.6s → <2s (5x faster)

---

## Alternative: FastAPI Dependency Injection (Recommended)

**File**: `src/api/dependencies.py` (new)

```python
from functools import lru_cache
from src.retrieval.ranking import BGEReranker

@lru_cache()
def get_shared_reranker() -> BGEReranker:
    return BGEReranker()
```

**File**: `src/api/main.py`

```python
from fastapi import Depends
from .dependencies import get_shared_reranker

@app.post("/ask")
def ask(body: AskIn, reranker: BGEReranker = Depends(get_shared_reranker)):
    retriever = create_retriever(mode=body.mode, reranker=reranker)
```

---

## Verification

```bash
# Terminal 1: Start server
./start_server.sh

# Terminal 2: Run performance test
python scripts/tests/performance/run_performance_tests.py --quick

# Expected result:
# ✅ Max concurrent users: >50
# ✅ Memory usage: <2GB
# ✅ Response time: <2s avg
```

---

## Related Docs
- **Full Analysis**: `documents/technical/RERANKER_MEMORY_ANALYSIS.md`
- **Reranking Strategies**: `documents/technical/RERANKING_STRATEGIES.md`
- **Performance Tests**: `scripts/tests/performance/README.md`

---

**Priority**: P0 - Fix immediately  
**Estimated Time**: 30-60 minutes  
**Assignee**: @development-team
