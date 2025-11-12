# GitHub Copilot Instructions - RAG Bidding System

## 🎯 Project Overview

RAG-based Vietnamese Legal Document Q&A system với semantic search, document reranking, và multi-tier caching.

## 🏗️ Architecture & Key Components

### Core Pipeline Flow

```
Query → Enhancement (Multi-Query/HyDE/Step-Back) → Vector Retrieval → Reranking (BGE) → LLM Generation
```

**4 RAG Modes** (`src/config/models.py`):

- `fast`: No enhancement, no reranking (~1s)
- `balanced`: Multi-Query + Step-Back + BGE reranking (~2-3s) ⭐ Default
- `quality`: All 4 strategies + RRF fusion (~3-5s)
- `adaptive`: Dynamic K selection based on query complexity

### Critical Files & Patterns

**Factory Pattern** - `src/retrieval/retrievers/__init__.py::create_retriever()`:

```python
# ⚠️ MỖI REQUEST TẠO RETRIEVER MỚI (không cache)
retriever = create_retriever(mode="balanced", enable_reranking=True)
# → Mỗi lần gọi tạo BGEReranker() mới → Load model mới → Memory leak!
```

**Singleton Issue** - BGEReranker KHÔNG được cache:

- Model BAAI/bge-reranker-v2-m3 (~1GB) được load mỗi request
- Concurrent users → multiple model instances → CUDA OOM
- **Fix needed**: Implement singleton pattern hoặc FastAPI dependency injection

### Reranking Strategy (PRODUCTION)

**Currently Used**: `BGEReranker` (`src/retrieval/ranking/bge_reranker.py`)

- Model: `BAAI/bge-reranker-v2-m3` (fine-tuned cross-encoder)
- Device: Auto-detect GPU/CPU
- Batch size: 32 (GPU) / 16 (CPU)
- Latency: ~100-150ms cho 10 docs

**Alternatives** (chưa implement production):

- `cross_encoder_reranker.py`: Empty file
- `legal_score_reranker.py`: Empty file
- `llm_reranker.py`: Empty file (chỉ demo)

**Industry Practice**:

- Perplexity: Cohere Rerank API
- You.com: Custom reranker
- Typical flow: Retrieve 20-50 docs → Rerank → Top 5

## 🔧 Development Workflows

### Environment Setup

```bash
conda activate venv  # NOT rag-bidding!
./start_server.sh    # uvicorn on port 8000
```

### Running Tests

```bash
# Performance suite (cần server running)
python scripts/tests/performance/run_performance_tests.py --quick

# Integration tests
python -m pytest scripts/test/integration/ -v

# ⚠️ API tests CẦN server chạy trước:
# Terminal 1: ./start_server.sh
# Terminal 2: python scripts/tests/test_api_endpoints.py
```

### Performance Benchmarks (Current State)

- **Query Latency**: 3-10s avg (bottleneck: reranker reload)
- **Concurrent Users**: Max 5-10 stable (breaking point: model memory)
- **Cache Speedup**: 1.2x (low due to non-deterministic reranking)
- **Memory**: 10GB+ per test session (multiple BGE instances)

## ⚠️ Known Issues & Constraints

### CRITICAL: Memory Leak from Reranker

**Problem**:

```python
# src/api/main.py::ask() - Called mỗi request
retriever = create_retriever(mode=body.mode, enable_reranking=True)
# → Mỗi lần tạo BGEReranker mới
# → Load BAAI/bge-reranker-v2-m3 (1.2GB) vào memory
# → Performance test: 15 queries × 4 modes = 60 model loads → 20GB RAM + CUDA OOM
```

**Fix Strategy** (chưa implement):

```python
# Option 1: Singleton pattern
_reranker_cache = {}
def get_reranker(model_name, device):
    key = f"{model_name}_{device}"
    if key not in _reranker_cache:
        _reranker_cache[key] = BGEReranker(model_name, device)
    return _reranker_cache[key]

# Option 2: FastAPI dependency injection (preferred)
@lru_cache()
def get_shared_reranker():
    return BGEReranker()  # Singleton per worker
```

### Other Performance Bottlenecks

1. **No DB connection pooling** → Max 5 concurrent users
2. **No embedding cache** → Re-embed identical queries
3. **Sequential query enhancement** → Could parallelize

## 📝 Code Conventions

### Language

- Code comments: Tiếng Việt
- Docstrings: Tiếng Việt
- Variable names: English
- Test descriptions: Tiếng Việt

### File Naming

- `*-deprecated`: Ignore completely (legacy OCR code)
- `test_*.py`: Test files (150+ files)
- `*_test.py`: Alternative test naming

### Testing Patterns

**Reference**: `scripts/tests/TEST_README.md`

```python
# API tests cần server running
def test_api_endpoint():
    response = requests.post("http://localhost:8000/ask", ...)
    assert response.status_code == 200
```

### Configuration Management

**Settings**: `src/config/models.py`

- Dataclass-based settings
- Environment variables via `.env`
- Preset modes: `RAGPresets.get_balanced_mode()`

## 🚫 Avoid These Mistakes

1. **Không modify code trong `*-deprecated` folders**
2. **Không tạo retriever/reranker mới mỗi request** (memory leak)
3. **Không run API tests mà không start server trước**
4. **Không assume environment name là "rag-bidding"** (thực tế là "venv")
5. **Không skip reranker singleton khi optimize performance**

## 🔍 Debugging Tips

### Memory Issues

```bash
# Check model cache
ls -lh ~/.cache/huggingface/hub/  # BGE model ~1.2GB

# Monitor GPU memory
nvidia-smi -l 1

# Clear CUDA cache (nếu OOM)
# Thêm vào BGEReranker.rerank():
torch.cuda.empty_cache()
```

### Performance Profiling

```python
# Logs hiện có timing info:
# [2025-11-08 08:55:35] [INFO] src.retrieval.ranking.bge_reranker:
# Initializing reranker: BAAI/bge-reranker-v2-m3
```

## 📚 Reference Documentation

### 🚨 **CRITICAL ISSUES - READ FIRST:**
1. **Memory Leak (BLOCKING)**: `documents/technical/reranking-analysis/` - 20GB RAM, 5 users max
2. **Performance Issues**: `documents/technical/performance-analysis/` - 37% success rate, 9.6s latency

### Core Architecture
- Pipeline Integration: `documents/technical/system-architecture/PIPELINE_INTEGRATION_SUMMARY.md`
- Technical Index: `documents/technical/README.md` (full navigation)

### Setup & Configuration
- Quick Setup: `documents/setup/QUICK_SETUP.md`
- Database Setup: `documents/setup/DATABASE_SETUP.md`

### Performance & Optimization
- **Non-Invasive Plan** (recommended): `documents/technical/implementation-plans/NON_INVASIVE_PERFORMANCE_PLAN.md`
- Executive Summary: `documents/technical/executive-summaries/EXECUTIVE_SUMMARY_PERFORMANCE_PLAN.md`
- Connection Pooling: `documents/technical/optimization-strategies/CONNECTION_POOLING_STRATEGY.md`

### Reranking (Memory Leak Issue) 🚨 **CRITICAL - READ FIRST**
**⭐ Start Here**: `documents/technical/reranking-analysis/TOM_TAT_TIENG_VIET.md` (Vietnamese comprehensive guide)
- **Fix Urgent** (3 min English): `documents/technical/reranking-analysis/RERANKER_FIX_URGENT.md`
- **Root Cause** (15 min deep-dive): `documents/technical/reranking-analysis/RERANKER_MEMORY_ANALYSIS.md`
- **Strategies** (20 min comparison): `documents/technical/reranking-analysis/RERANKING_STRATEGIES.md`
- **Navigation Guide**: `documents/technical/reranking-analysis/README.md`

**Quick Summary:**
- **Problem**: BGEReranker loads 1.2GB model per request → 20GB RAM usage → CUDA OOM
- **Impact**: Max 5 concurrent users, 36.7% success rate, production blocking
- **Solution**: Implement singleton pattern (30 min) or FastAPI DI (1 hour)
- **Expected**: 20GB → 1.5GB (13x), 5 → 50+ users (10x)

---

## Những điều cần lưu ý:

- Khi có lỗi xảy ra, kiểm tra code logic liên quan để hiểu nguyên nhân gốc rễ
- Ưu tiên singleton pattern cho heavy resources (embeddings, rerankers)
- Performance tests phải được monitor memory usage
- API changes cần update cả test suite
