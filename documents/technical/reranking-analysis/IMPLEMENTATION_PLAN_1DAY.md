# 🚀 Kế Hoạch Triển Khai Singleton Pattern - 1 Ngày

> ⚠️ **ARCHIVED (13/11/2025)**: This plan has been **COMPLETED**.
> 
> **Status**: ✅ Phases 1-4 fully implemented and tested (100% success rate achieved).
>
> **Kết quả thực tế**: Memory 20GB → 1.75GB (11.4x), 100% success @ 5 users (vs 37% before).
>
> **Đọc thay thế**: [SINGLETON_PATTERN_GUIDE.md](./SINGLETON_PATTERN_GUIDE.md) for complete implementation guide and results.

---

**Mục tiêu**: Fix memory leak của BGEReranker bằng Singleton Pattern trong 1 ngày làm việc (8 giờ) *(Legacy plan below)*

**Expected Impact** *(Now ACHIEVED)*:
- Memory usage: 20GB → 1.5GB (13x reduction) ✅ Actual: 1.75GB (11.4x)
- Concurrent capacity: 5 → 50+ users (10x improvement) ✅ Actual: 10+ users stable
- Success rate: 36.7% → 95%+ ✅ Actual: 100% @ 5 users
- Response time: Timeout → <2s ✅ Actual: 8-25s avg (reranking overhead)

---

## 📋 TÓM TẮT EXECUTIVE

### Vấn đề hiện tại
- ❌ BGEReranker load model 1.2GB **mỗi request**
- ❌ Performance test: 60 instances = 20GB+ RAM
- ❌ CUDA OOM error khi >5 concurrent users
- ❌ 4 reranker files khác **EMPTY** (không sử dụng)

### Giải pháp
- ✅ **Phase 1** (3h): Implement Simple Singleton cho BGEReranker
- ✅ **Phase 2** (2h): Deprecate unused rerankers (Cohere, CrossEncoder, LegalScore, LLM)
- ✅ **Phase 3** (2h): Testing & verification
- ✅ **Phase 4** (1h): Documentation & commit

### Timeline
```
08:00 - 11:00  Phase 1: Singleton Implementation (3h)
11:00 - 13:00  Phase 2: Cleanup Unused Rerankers (2h)
13:00 - 14:00  BREAK
14:00 - 16:00  Phase 3: Testing & Verification (2h)
16:00 - 17:00  Phase 4: Documentation & Commit (1h)
```

---

## 🎯 PHASE 1: Singleton Implementation (3 giờ)

### Objectives
- ✅ Implement thread-safe singleton factory cho BGEReranker
- ✅ Update `create_retriever()` để sử dụng singleton
- ✅ Update API endpoint để pass reranker instance
- ✅ Add cleanup mechanism

### 📝 Step 1.1: Create Singleton Factory (45 phút)

**File: `src/retrieval/ranking/bge_reranker.py`**

**Task 1a: Add singleton globals (10 phút)**

```python
# Thêm vào đầu file, sau imports
import threading

# ==================== SINGLETON PATTERN ====================
_reranker_instance = None
_reranker_lock = threading.Lock()

def get_singleton_reranker(
    model_name: str = "BAAI/bge-reranker-v2-m3",
    device: str = "auto",
    max_length: int = 512,
    batch_size: int = 32,
) -> "BGEReranker":
    """
    Thread-safe singleton factory for BGEReranker
    
    Returns the same instance across all requests to avoid
    loading 1.2GB model multiple times.
    
    Args:
        model_name: Model name (default: BAAI/bge-reranker-v2-m3)
        device: Device to use (auto/cuda/cpu)
        max_length: Max sequence length
        batch_size: Batch size for inference
    
    Returns:
        Singleton BGEReranker instance
        
    Example:
        >>> reranker = get_singleton_reranker()
        >>> results = reranker.rerank(query, docs)
    """
    global _reranker_instance
    
    if _reranker_instance is None:
        with _reranker_lock:
            # Double-check locking
            if _reranker_instance is None:
                logger.info("🔧 Creating singleton BGEReranker instance...")
                _reranker_instance = BGEReranker(
                    model_name=model_name,
                    device=device,
                    max_length=max_length,
                    batch_size=batch_size,
                )
                logger.info("✅ Singleton BGEReranker created successfully")
    
    return _reranker_instance


def reset_singleton_reranker():
    """
    Reset singleton instance (for testing purposes)
    
    ⚠️ ONLY use this in tests or when changing model config
    """
    global _reranker_instance
    
    with _reranker_lock:
        if _reranker_instance is not None:
            logger.warning("🔄 Resetting singleton BGEReranker instance...")
            # Cleanup if needed
            if hasattr(_reranker_instance, '__del__'):
                _reranker_instance.__del__()
            _reranker_instance = None
            logger.info("✅ Singleton BGEReranker reset")
# ==================== END SINGLETON PATTERN ====================
```

**Task 1b: Add cleanup to BGEReranker class (10 phút)**

Thêm method `__del__` vào class `BGEReranker`:

```python
class BGEReranker(BaseReranker):
    # ... existing code ...
    
    def __del__(self):
        """Cleanup model resources when instance is deleted"""
        try:
            if hasattr(self, 'model'):
                # Clear CUDA cache if using GPU
                if self.device == "cuda":
                    import torch
                    torch.cuda.empty_cache()
                    logger.debug("🧹 Cleared CUDA cache")
                
                # Delete model reference
                del self.model
                logger.debug("🧹 BGEReranker cleanup completed")
        except Exception as e:
            logger.warning(f"⚠️  Cleanup error (non-critical): {e}")
```

**Task 1c: Update module exports (5 phút)**

**File: `src/retrieval/ranking/__init__.py`**

```python
"""
Document Reranking Module

Cung cấp các reranker implementations để cải thiện
ranking quality của retrieved documents.
"""

from .base_reranker import BaseReranker
from .bge_reranker import BGEReranker, get_singleton_reranker, reset_singleton_reranker

# ⚠️ DEPRECATED: Unused reranker implementations (empty files)
# These will be removed in future versions
# - cohere_reranker.py
# - cross_encoder_reranker.py  
# - legal_score_reranker.py
# - llm_reranker.py

__all__ = [
    "BaseReranker",
    "BGEReranker",
    "get_singleton_reranker",  # ✅ NEW: Singleton factory
    "reset_singleton_reranker",  # ✅ NEW: For testing
]
```

**Verification (10 phút):**
```bash
# Test import
python -c "from src.retrieval.ranking import get_singleton_reranker; print('✅ Import OK')"

# Test singleton creation
python -c "
from src.retrieval.ranking import get_singleton_reranker
r1 = get_singleton_reranker()
r2 = get_singleton_reranker()
assert r1 is r2, 'Singleton failed!'
print('✅ Singleton works')
"
```

---

### 📝 Step 1.2: Update Retriever Factory (45 phút)

**File: `src/retrieval/retrievers/__init__.py`**

**Task 2a: Import singleton factory (5 phút)**

```python
# Thêm vào phần imports
from src.retrieval.ranking import get_singleton_reranker
```

**Task 2b: Update create_retriever (20 phút)**

Tìm function `create_retriever()` và update:

```python
def create_retriever(
    mode: str = "balanced",
    enable_reranking: bool = True,
    reranker: Optional[BaseReranker] = None,  # ✅ NEW: Allow injecting reranker
) -> BaseRetriever:
    """
    Factory function to create retriever based on mode
    
    Args:
        mode: RAG mode (fast/balanced/quality/adaptive)
        enable_reranking: Whether to enable reranking
        reranker: Optional pre-created reranker instance (for testing/DI)
                  If None, will use singleton factory
    
    Returns:
        Configured retriever instance
    """
    # Apply preset settings
    apply_preset(mode)
    
    # ✅ NEW: Use singleton reranker thay vì tạo mới
    if enable_reranking:
        if reranker is None:
            # Use singleton factory
            reranker = get_singleton_reranker()
            logger.debug("✅ Using singleton BGEReranker")
        else:
            logger.debug("✅ Using injected reranker instance")
    else:
        reranker = None
    
    # ❌ OLD CODE - XÓA ĐI:
    # if enable_reranking:
    #     from src.retrieval.ranking.bge_reranker import BGEReranker
    #     reranker = BGEReranker()  # ← Memory leak!
    # else:
    #     reranker = None
    
    # ... rest of function unchanged ...
```

**Task 2c: Update imports và cleanup (10 phút)**

Xóa hoặc comment out các import không cần thiết:

```python
# ❌ REMOVE this import (không cần nữa):
# from src.retrieval.ranking.bge_reranker import BGEReranker
```

**Verification (10 phút):**
```bash
# Test retriever creation
python -c "
from src.retrieval.retrievers import create_retriever
r1 = create_retriever(mode='balanced', enable_reranking=True)
r2 = create_retriever(mode='quality', enable_reranking=True)
print('✅ Retriever creation OK')
"
```

---

### 📝 Step 1.3: Update API Endpoint (30 phút)

**File: `src/api/main.py`**

**Task 3a: Remove duplicate retriever creation (15 phút)**

Tìm function `ask()` và xóa duplicate code:

```python
@app.post("/ask", response_model=AskResponse)
def ask(body: AskIn):
    # ❌ XÓA ĐOẠN NÀY (duplicate với qa_chain.py):
    # from src.retrieval.retrievers import create_retriever
    # enable_reranking = settings.enable_reranking and body.mode != "fast"
    # retriever = create_retriever(mode=body.mode, enable_reranking=enable_reranking)
    
    if not body.question or not body.question.strip():
        raise HTTPException(400, detail="question is required")
    
    try:
        import time
        start_time = time.time()
        
        # ✅ qa_chain.answer() tự tạo retriever với singleton
        result = answer(body.question, mode=body.mode, use_enhancement=True)
        
        processing_time = int((time.time() - start_time) * 1000)
        result["processing_time_ms"] = processing_time
        return result
    except Exception as e:
        raise HTTPException(500, detail=str(e))
```

**Task 3b: Add health check endpoint (15 phút)**

Thêm endpoint mới để monitor reranker status:

```python
@app.get("/health/reranker")
def health_reranker():
    """
    Health check for BGEReranker singleton
    
    Returns:
        - model_name: Model being used
        - device: CPU/CUDA
        - memory_usage: Approximate model size
        - singleton_initialized: Whether singleton exists
    """
    from src.retrieval.ranking import get_singleton_reranker
    
    try:
        # This will create singleton if not exists
        reranker = get_singleton_reranker()
        
        return {
            "status": "healthy",
            "model_name": reranker.model_name,
            "device": reranker.device,
            "max_length": reranker.max_length,
            "batch_size": reranker.batch_size,
            "singleton_initialized": True,
            "estimated_memory_mb": 1200,  # ~1.2GB for BGE-m3
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "singleton_initialized": False,
        }
```

**Verification (10 phút):**
```bash
# Start server
./start_server.sh

# Test health endpoint (in another terminal)
curl http://localhost:8000/health/reranker

# Expected output:
# {
#   "status": "healthy",
#   "model_name": "BAAI/bge-reranker-v2-m3",
#   "device": "cuda",
#   ...
# }
```

---

### 📝 Step 1.4: Update qa_chain.py (30 phút)

**File: `src/generation/chains/qa_chain.py`**

**Task 4: Verify singleton usage (30 phút)**

Check function `answer()` - Nó đã gọi `create_retriever()` nên sẽ tự động dùng singleton:

```python
def answer(question: str, mode: str | None = None, use_enhancement: bool = True) -> Dict:
    selected_mode = mode or settings.rag_mode or "balanced"
    apply_preset(selected_mode)

    # ✅ create_retriever() giờ dùng singleton
    enable_reranking = settings.enable_reranking and selected_mode != "fast"
    retriever = create_retriever(mode=selected_mode, enable_reranking=enable_reranking)
    
    # ... rest unchanged ...
```

**Không cần thay đổi gì** - Chỉ cần verify logic OK.

---

### 📝 Step 1.5: Git Commit Phase 1 (30 phút)

```bash
# Stage changes
git add src/retrieval/ranking/bge_reranker.py
git add src/retrieval/ranking/__init__.py
git add src/retrieval/retrievers/__init__.py
git add src/api/main.py

# Commit
git commit -m "feat: implement singleton pattern for BGEReranker

- Add get_singleton_reranker() factory with thread-safe locking
- Add reset_singleton_reranker() for testing
- Add __del__ cleanup method to BGEReranker
- Update create_retriever() to use singleton
- Remove duplicate retriever creation in API endpoint
- Add /health/reranker endpoint for monitoring

Expected impact:
- Memory: 20GB → 1.5GB (13x reduction)
- Capacity: 5 → 50+ concurrent users

Related: Memory leak analysis in docs/technical/reranking-analysis/"

# Push to branch
git push origin optimization
```

---

## 🗑️ PHASE 2: Cleanup Unused Rerankers (2 giờ)

### Objectives
- ✅ Deprecate 4 empty reranker files
- ✅ Add deprecation notices
- ✅ Update documentation
- ✅ Clean up imports

### 📝 Step 2.1: Add Deprecation Notices (30 phút)

**Task 1: Update empty files với deprecation notice**

**File: `src/retrieval/ranking/cohere_reranker.py`**
```python
"""
⚠️ DEPRECATED - Empty file, not implemented

This reranker was planned but never implemented.
Use BGEReranker instead (production-ready, multilingual).

Alternative for Cohere:
- If you need Cohere Rerank API, use their official client:
  https://docs.cohere.com/reference/rerank-1
  
Migration:
>>> from cohere import Client
>>> co = Client(api_key="YOUR_KEY")
>>> results = co.rerank(query=query, documents=docs)

This file will be removed in v3.0.0
"""

# Empty - do not use
```

**File: `src/retrieval/ranking/cross_encoder_reranker.py`**
```python
"""
⚠️ DEPRECATED - Empty file, not implemented

This reranker was planned but never implemented.
Use BGEReranker instead (already uses CrossEncoder internally).

Note:
- BGEReranker uses sentence_transformers.CrossEncoder
- Model: BAAI/bge-reranker-v2-m3 (fine-tuned cross-encoder)
- Already optimized for reranking task

This file will be removed in v3.0.0
"""

# Empty - do not use
```

**File: `src/retrieval/ranking/legal_score_reranker.py`**
```python
"""
⚠️ DEPRECATED - Empty file, not implemented

This custom legal scoring reranker was planned but never implemented.

Alternative approach:
- Use BGEReranker (works well with Vietnamese legal documents)
- Fine-tune BGE model on legal corpus if needed
- Add legal keyword boosting in query enhancement

This file will be removed in v3.0.0
"""

# Empty - do not use
```

**File: `src/retrieval/ranking/llm_reranker.py`**
```python
"""
⚠️ DEPRECATED - Empty file, not implemented

LLM-based reranking was planned but not implemented due to:
- High latency (LLM call per document)
- High cost (API calls)
- BGEReranker already provides good quality

Alternative:
- Use BGEReranker for production
- Use LLM for answer generation (already implemented in qa_chain.py)

This file will be removed in v3.0.0
"""

# Empty - do not use
```

---

### 📝 Step 2.2: Update Documentation (45 phút)

**Task 1: Create deprecation notice document (20 phút)**

**File: `src/retrieval/ranking/DEPRECATED_RERANKERS.md`**
```markdown
# Deprecated Reranker Files

**Status**: DEPRECATED - Will be removed in v3.0.0

## Summary

The following reranker files are **empty** and **not used** in production:
- `cohere_reranker.py` - Planned Cohere API integration (never implemented)
- `cross_encoder_reranker.py` - Redundant with BGEReranker
- `legal_score_reranker.py` - Custom legal scoring (never implemented)
- `llm_reranker.py` - LLM-based reranking (too slow/expensive)

## Production Reranker

**✅ BGEReranker** (`bge_reranker.py`) is the ONLY reranker in production:
- Model: `BAAI/bge-reranker-v2-m3`
- Status: Active, optimized, production-ready
- Performance: ~100-150ms for 10 docs
- Quality: State-of-the-art multilingual reranking

## Migration Guide

### If you planned to use Cohere:
```python
# Instead of (not implemented):
# from src.retrieval.ranking import CohereReranker

# Use Cohere official client:
from cohere import Client
co = Client(api_key="YOUR_KEY")
results = co.rerank(query=query, documents=docs, top_n=5)
```

### If you need custom legal scoring:
```python
# Use BGE + custom boosting in query enhancement
from src.retrieval.ranking import get_singleton_reranker

reranker = get_singleton_reranker()
results = reranker.rerank(query, docs, top_k=10)

# Post-process with legal keyword boosting if needed
```

## Removal Timeline

- **v2.1.0** (Current): Deprecation notices added
- **v2.5.0**: Warnings when importing deprecated modules
- **v3.0.0**: Files removed completely

## Questions?

See `documents/technical/reranking-analysis/RERANKING_STRATEGIES.md` for alternatives.
```

**Task 2: Update main README (15 phút)**

Add deprecation notice to `src/retrieval/ranking/README.md` if exists, or create it.

---

### 📝 Step 2.3: Git Commit Phase 2 (30 phút)

```bash
# Stage changes
git add src/retrieval/ranking/*.py
git add src/retrieval/ranking/DEPRECATED_RERANKERS.md

# Commit
git commit -m "docs: deprecate unused reranker files

- Add deprecation notices to 4 empty reranker files:
  - cohere_reranker.py
  - cross_encoder_reranker.py
  - legal_score_reranker.py
  - llm_reranker.py
  
- Create DEPRECATED_RERANKERS.md with migration guide
- BGEReranker is the ONLY production reranker

Files will be removed in v3.0.0

Related: Cleanup as part of singleton implementation"

# Push
git push origin optimization
```

---

## 🧪 PHASE 3: Testing & Verification (2 giờ)

### Objectives
- ✅ Verify singleton works correctly
- ✅ Run performance test suite
- ✅ Verify memory reduction
- ✅ Test concurrent requests

### 📝 Step 3.1: Unit Tests (45 phút)

**File: `scripts/tests/test_singleton_reranker.py` (NEW)**

```python
"""
Unit tests for Singleton BGEReranker

Test coverage:
- Singleton factory creates same instance
- Thread-safe singleton creation
- Reset singleton for testing
- Memory cleanup
"""

import pytest
import threading
from src.retrieval.ranking import (
    get_singleton_reranker,
    reset_singleton_reranker,
    BGEReranker,
)


def test_singleton_returns_same_instance():
    """Test that singleton factory returns same instance"""
    reset_singleton_reranker()  # Clean state
    
    r1 = get_singleton_reranker()
    r2 = get_singleton_reranker()
    
    assert r1 is r2, "Singleton should return same instance"
    print("✅ Singleton returns same instance")


def test_singleton_thread_safety():
    """Test that singleton is thread-safe"""
    reset_singleton_reranker()  # Clean state
    
    instances = []
    
    def create_reranker():
        r = get_singleton_reranker()
        instances.append(r)
    
    # Create 10 threads
    threads = []
    for _ in range(10):
        t = threading.Thread(target=create_reranker)
        threads.append(t)
        t.start()
    
    # Wait for all threads
    for t in threads:
        t.join()
    
    # All instances should be the same
    first_instance = instances[0]
    for instance in instances:
        assert instance is first_instance, "All threads should get same instance"
    
    print(f"✅ Thread-safe: {len(instances)} threads got same instance")


def test_singleton_reset():
    """Test that reset_singleton_reranker works"""
    reset_singleton_reranker()
    
    r1 = get_singleton_reranker()
    reset_singleton_reranker()
    r2 = get_singleton_reranker()
    
    # After reset, should get different instance
    assert r1 is not r2, "Reset should create new instance"
    print("✅ Singleton reset works")


def test_reranker_functionality():
    """Test that singleton reranker works correctly"""
    from langchain_core.documents import Document
    
    reranker = get_singleton_reranker()
    
    # Create test documents
    docs = [
        Document(page_content="Luật đấu thầu quy định về quy trình đấu thầu"),
        Document(page_content="Ngày mai trời mưa"),
        Document(page_content="Điều 10 quy định về hồ sơ dự thầu"),
    ]
    
    # Rerank
    results = reranker.rerank("Luật đấu thầu", docs, top_k=2)
    
    assert len(results) == 2, "Should return top 2 docs"
    assert all(isinstance(r, tuple) for r in results), "Should return tuples"
    assert all(len(r) == 2 for r in results), "Each tuple should have (doc, score)"
    
    # Scores should be descending
    scores = [r[1] for r in results]
    assert scores[0] >= scores[1], "Scores should be descending"
    
    print(f"✅ Reranker works: Top score = {scores[0]:.4f}")


if __name__ == "__main__":
    test_singleton_returns_same_instance()
    test_singleton_thread_safety()
    test_singleton_reset()
    test_reranker_functionality()
    print("\n🎉 All tests passed!")
```

**Run tests:**
```bash
python scripts/tests/test_singleton_reranker.py
```

---

### 📝 Step 3.2: Performance Test (45 phút)

**Run existing performance test:**

```bash
# Start server
./start_server.sh

# In another terminal
cd scripts/tests/performance
python run_performance_tests.py --quick

# Monitor memory
watch -n 1 'free -h'
```

**Expected results:**
- Memory usage: <2GB (vs 20GB+ before)
- Success rate: >95% (vs 36.7% before)
- Response time: <2s avg (vs timeout before)
- Concurrent capacity: 20-50 users stable

**Verification checklist:**
- [ ] Memory stays below 2GB during test
- [ ] No CUDA OOM errors
- [ ] All 15 queries complete successfully
- [ ] Reranker model loaded only ONCE (check logs)

---

### 📝 Step 3.3: Integration Test (30 phút)

**Test concurrent requests:**

```bash
# Test script: scripts/tests/test_concurrent_singleton.sh
#!/bin/bash

echo "🧪 Testing concurrent requests with singleton..."

# Start 5 concurrent requests
for i in {1..5}; do
  (
    curl -X POST http://localhost:8000/ask \
      -H "Content-Type: application/json" \
      -d "{\"question\": \"Test query $i\", \"mode\": \"balanced\"}" \
      -s -o /dev/null -w "Request $i: %{http_code} in %{time_total}s\n"
  ) &
done

wait
echo "✅ All concurrent requests completed"
```

**Run test:**
```bash
chmod +x scripts/tests/test_concurrent_singleton.sh
./scripts/tests/test_concurrent_singleton.sh
```

**Expected:**
- All requests return 200 OK
- Response time <2s each
- Memory stable (check with `free -h`)

---

## 📝 PHASE 4: Documentation & Commit (1 giờ)

### 📝 Step 4.1: Update Documentation (30 phút)

**Task 1: Update copilot instructions (10 phút)**

**File: `.github/copilot-instructions.md`**

Add to "CRITICAL ISSUES" section:

```markdown
### ✅ FIXED: Memory Leak (November 13, 2025)

**Solution Implemented**: Singleton Pattern for BGEReranker
- Memory: 20GB → 1.5GB (13x reduction)
- Capacity: 5 → 50+ users (10x improvement)
- Implementation: `get_singleton_reranker()` factory function
- Files updated: `bge_reranker.py`, `__init__.py`, `retrievers/__init__.py`

**Before:**
```python
# ❌ OLD: Create new instance per request (memory leak)
reranker = BGEReranker()
```

**After:**
```python
# ✅ NEW: Use singleton
from src.retrieval.ranking import get_singleton_reranker
reranker = get_singleton_reranker()
```

**Deprecated Files:**
- `cohere_reranker.py` - Empty, not implemented
- `cross_encoder_reranker.py` - Empty, redundant
- `legal_score_reranker.py` - Empty, not implemented
- `llm_reranker.py` - Empty, too slow/expensive

**See**: `documents/technical/reranking-analysis/IMPLEMENTATION_PLAN_1DAY.md`
```

**Task 2: Create implementation summary (20 phút)**

**File: `documents/technical/reranking-analysis/IMPLEMENTATION_SUMMARY.md`**

```markdown
# Implementation Summary - Singleton Pattern

**Date**: November 13, 2025  
**Implemented By**: Development Team  
**Time Taken**: 6 hours (1 working day)

## Changes Made

### Phase 1: Singleton Implementation (3h)
- ✅ Added `get_singleton_reranker()` factory with thread-safe locking
- ✅ Added `reset_singleton_reranker()` for testing
- ✅ Added `__del__` cleanup to BGEReranker class
- ✅ Updated `create_retriever()` to use singleton
- ✅ Removed duplicate retriever creation in API endpoint
- ✅ Added `/health/reranker` monitoring endpoint

### Phase 2: Cleanup (2h)
- ✅ Deprecated 4 unused reranker files
- ✅ Added deprecation notices and migration guide
- ✅ Created DEPRECATED_RERANKERS.md documentation

### Phase 3: Testing (2h)
- ✅ Unit tests: Singleton behavior verification
- ✅ Performance tests: Memory and concurrency
- ✅ Integration tests: Concurrent API requests

## Results

### Before Implementation
- Memory: 20GB+ during performance tests
- Concurrent capacity: Max 5 users
- Success rate: 36.7%
- CUDA OOM errors frequent

### After Implementation
- Memory: 1.5GB stable
- Concurrent capacity: 50+ users
- Success rate: 95%+
- No CUDA OOM errors

### Performance Metrics
- Memory reduction: **13x** (20GB → 1.5GB)
- Capacity improvement: **10x** (5 → 50 users)
- Success rate improvement: **2.6x** (36.7% → 95%)
- Response time: <2s avg (vs timeout)

## Files Modified

### Core Changes
- `src/retrieval/ranking/bge_reranker.py` - Singleton implementation
- `src/retrieval/ranking/__init__.py` - Export singleton factory
- `src/retrieval/retrievers/__init__.py` - Use singleton
- `src/api/main.py` - Add health endpoint

### Documentation
- `src/retrieval/ranking/DEPRECATED_RERANKERS.md` - New
- `.github/copilot-instructions.md` - Updated
- `documents/technical/reranking-analysis/IMPLEMENTATION_PLAN_1DAY.md` - New
- `documents/technical/reranking-analysis/IMPLEMENTATION_SUMMARY.md` - This file

### Tests
- `scripts/tests/test_singleton_reranker.py` - New

## Commits

1. `feat: implement singleton pattern for BGEReranker`
2. `docs: deprecate unused reranker files`
3. `test: add singleton reranker tests`
4. `docs: update implementation summary`

## Next Steps (Future)

### Phase 2: FastAPI Dependency Injection (Optional)
- Migrate to `@lru_cache()` pattern
- Better testability
- Multi-worker ready
- Timeline: 1 week

### Phase 3: Model Pool (If needed)
- For >100 concurrent users
- GPU optimization
- Timeline: 1 month

## Lessons Learned

1. **Singleton is sufficient** for current scale (50 users)
2. **Thread-safe locking is critical** for web services
3. **Health endpoints are valuable** for monitoring
4. **Deprecation notices help** prevent confusion
5. **Performance tests reveal issues** before production

## References

- Analysis: `SINGLETON_AND_CONCURRENCY_ANALYSIS.md`
- FAQ: `FAQ_CONCURRENCY_VIETNAMESE.md`
- Urgent fix guide: `RERANKER_FIX_URGENT.md`
```

---

### 📝 Step 4.2: Final Commit & Push (30 phút)

```bash
# Stage all remaining changes
git add scripts/tests/test_singleton_reranker.py
git add .github/copilot-instructions.md
git add documents/technical/reranking-analysis/IMPLEMENTATION_PLAN_1DAY.md
git add documents/technical/reranking-analysis/IMPLEMENTATION_SUMMARY.md

# Final commit
git commit -m "docs: add implementation plan and summary for singleton pattern

- Add IMPLEMENTATION_PLAN_1DAY.md (detailed 1-day roadmap)
- Add IMPLEMENTATION_SUMMARY.md (results and metrics)
- Add test_singleton_reranker.py (unit tests)
- Update copilot-instructions.md with fix status

Implementation complete:
- Memory: 20GB → 1.5GB (13x)
- Capacity: 5 → 50+ users (10x)
- Success rate: 36.7% → 95%+

All tests passing ✅"

# Push to remote
git push origin optimization

# Create PR (optional)
gh pr create \
  --title "Fix: Implement Singleton Pattern for BGEReranker (Memory Leak Fix)" \
  --body "
## Summary
Implements singleton pattern to fix critical memory leak in BGEReranker.

## Problem
- BGEReranker loaded 1.2GB model per request
- Memory usage: 20GB+ during tests
- CUDA OOM errors with >5 concurrent users
- Success rate: 36.7%

## Solution
- Implemented thread-safe singleton factory
- Deprecated 4 unused reranker files
- Added health check endpoint
- Comprehensive testing

## Results
- ✅ Memory: 20GB → 1.5GB (13x reduction)
- ✅ Capacity: 5 → 50+ users (10x improvement)
- ✅ Success rate: 36.7% → 95%+
- ✅ Response time: Timeout → <2s

## Testing
- Unit tests: Singleton behavior ✅
- Performance tests: Memory reduction ✅
- Integration tests: Concurrent requests ✅

## Documentation
- Implementation plan: docs/technical/reranking-analysis/IMPLEMENTATION_PLAN_1DAY.md
- Summary: docs/technical/reranking-analysis/IMPLEMENTATION_SUMMARY.md
- Analysis: docs/technical/reranking-analysis/

## Breaking Changes
None - backward compatible

## Migration
Automatic - no code changes needed for users
  "
```

---

## ✅ COMPLETION CHECKLIST

### Phase 1: Singleton Implementation
- [ ] Created `get_singleton_reranker()` factory
- [ ] Added `reset_singleton_reranker()` for testing
- [ ] Added `__del__` cleanup to BGEReranker
- [ ] Updated `create_retriever()` to use singleton
- [ ] Removed duplicate code in `main.py`
- [ ] Added `/health/reranker` endpoint
- [ ] Committed changes to git

### Phase 2: Cleanup
- [ ] Added deprecation notices to 4 empty files
- [ ] Created `DEPRECATED_RERANKERS.md`
- [ ] Updated module exports
- [ ] Committed deprecation changes

### Phase 3: Testing
- [ ] Created unit tests
- [ ] Ran performance test suite
- [ ] Verified memory reduction (<2GB)
- [ ] Tested concurrent requests (5-10 users)
- [ ] No CUDA OOM errors
- [ ] Success rate >95%

### Phase 4: Documentation
- [ ] Updated `.github/copilot-instructions.md`
- [ ] Created `IMPLEMENTATION_PLAN_1DAY.md`
- [ ] Created `IMPLEMENTATION_SUMMARY.md`
- [ ] Updated README files
- [ ] Final commit and push
- [ ] Created PR (optional)

---

## 📊 SUCCESS METRICS

### Memory Usage
- **Before**: 20GB+ during tests
- **After**: <2GB stable
- **Reduction**: 13x (90% reduction)

### Concurrent Capacity
- **Before**: Max 5 users (crashes at 10)
- **After**: 50+ users stable
- **Improvement**: 10x capacity

### Success Rate
- **Before**: 36.7% (performance test)
- **After**: 95%+ (all tests pass)
- **Improvement**: 2.6x reliability

### Response Time
- **Before**: Timeout (>10 minutes)
- **After**: <2s average
- **Improvement**: >300x faster

---

## 🚨 TROUBLESHOOTING

### Issue 1: Import Error
```python
ImportError: cannot import name 'get_singleton_reranker'
```
**Solution**: Restart server to reload modules

### Issue 2: Singleton Not Working
```python
r1 is not r2  # Different instances!
```
**Solution**: Check thread-safe locking in `get_singleton_reranker()`

### Issue 3: Memory Still High
**Solution**: 
1. Check logs for "Creating singleton" messages (should appear only ONCE)
2. Verify no old `BGEReranker()` calls remain in code
3. Run `reset_singleton_reranker()` to clear

### Issue 4: Tests Fail
**Solution**:
1. Check Python environment: `conda activate venv`
2. Verify server running: `./start_server.sh`
3. Clear cache: `python -c "import torch; torch.cuda.empty_cache()"`

---

## 📚 REFERENCES

### Implementation Guides
- `RERANKER_FIX_URGENT.md` - Quick fix guide (3 min)
- `SINGLETON_AND_CONCURRENCY_ANALYSIS.md` - Technical deep-dive (30 min)
- `FAQ_CONCURRENCY_VIETNAMESE.md` - Concurrency FAQ (10 min)

### Related Documentation
- `TOM_TAT_TIENG_VIET.md` - Vietnamese summary
- `RERANKING_STRATEGIES.md` - Alternative strategies
- `RERANKER_MEMORY_ANALYSIS.md` - Root cause analysis

### Test Files
- `scripts/tests/test_singleton_reranker.py` - Unit tests
- `scripts/tests/performance/run_performance_tests.py` - Performance suite
- `scripts/tests/test_concurrent_singleton.sh` - Concurrent test

---

**📅 Plan Created**: November 13, 2025  
**⏱️ Estimated Time**: 8 hours (1 working day)  
**🎯 Success Criteria**: Memory <2GB, 50+ concurrent users, >95% success rate
