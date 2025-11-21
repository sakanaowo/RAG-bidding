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

## Những điều cần lưu ý:

- Khi có lỗi xảy ra, kiểm tra code logic liên quan để hiểu nguyên nhân gốc rễ
- Ưu tiên singleton pattern cho heavy resources (embeddings, rerankers)
- Performance tests phải được monitor memory usage
- API changes cần update cả test suite
