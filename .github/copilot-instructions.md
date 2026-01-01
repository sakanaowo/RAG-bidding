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
conda activate venv
./start_server.sh    # uvicorn on port 8000
```

### Configuration Management

**Settings**: `src/config/models.py`

- Dataclass-based settings
- Environment variables via `.env`
- Preset modes: `RAGPresets.get_balanced_mode()`

## 🚫 Avoid These Mistakes

1. **Không cần modify code trong `*-deprecated` folders**
2. **Không tạo retriever/reranker mới mỗi request** (memory leak)
3. **Không run API tests mà không start server trước**
4. **Không assume environment name là "rag-bidding"** (thực tế là "venv")
5. **Không skip reranker singleton khi optimize performance**

## 🔍 Debugging Tips

- Tạo log debug trong folder `temp/<debug-name>/...`

### Performance Profiling

```python
# Logs hiện có timing info:
# [2025-11-08 08:55:35] [INFO] src.retrieval.ranking.bge_reranker:
# Initializing reranker: BAAI/bge-reranker-v2-m3
```

## Quy tắc cần tuân thủ:

- Khi có lỗi xảy ra, kiểm tra code logic liên quan để hiểu nguyên nhân gốc rễ
- Ưu tiên singleton pattern cho heavy resources (embeddings, rerankers)
- Performance tests phải được monitor memory usage
- API changes cần update cả test suite
- Nếu tạo file test thì đặt trong `scripts/tests/` folder với tên rõ ràng
- Khi tạo file test, KHÔNG ĐƯỢC PHÉP ĐƯA TRỰC TIẾP KEY TỪ `.env` VÀO MÃ NGUỒN
- Nếu thêm một dependency mới thì update `environment.yml`

## 🔒 Quy Định Bắt Buộc - SQLAlchemy & Database

### 1. Raw SQL Commands - SQLAlchemy 2.0

**MUST**: Wrap ALL raw SQL với `text()` wrapper

```python
# ❌ WRONG - Will fail in SQLAlchemy 2.0+
db.execute("SELECT 1")
db.execute("SELECT COUNT(*) FROM documents")

# ✅ CORRECT
from sqlalchemy import text
db.execute(text("SELECT 1"))
db.execute(text("SELECT COUNT(*) FROM documents"))
```

### 2. Module Imports - Python Path

**MUST**: Thêm project root vào `sys.path` khi import `src.*` modules

```python
# ❌ WRONG - Sẽ fail với "No module named 'src'"
from src.models.base import SessionLocal

# ✅ CORRECT - Thêm project root vào path trước
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))  # Adjust based on file location
from src.models.base import SessionLocal
```

**Path calculation:**

- File ở `/scripts/`: `Path(__file__).parent.parent` (lên 1 cấp)
- File ở `/scripts/examples/`: `Path(__file__).parent.parent.parent` (lên 2 cấp)
- File ở `/scripts/tests/`: `Path(__file__).parent.parent.parent` (lên 2 cấp)

### 3. Database Session Management

**MUST**: Luôn sử dụng context manager hoặc try/finally

```python
# ✅ CORRECT - Context manager (recommended)
with SessionLocal() as db:
    docs = db.query(Document).all()
    # Auto-close

# ✅ CORRECT - Manual close
db = SessionLocal()
try:
    docs = db.query(Document).all()
finally:
    db.close()

# ❌ WRONG - Session leak
db = SessionLocal()
docs = db.query(Document).all()
# db never closed!
```

### 4. FastAPI Dependency Injection

**MUST**: Sử dụng `Depends(get_db)` cho database sessions

```python
# ✅ CORRECT
from fastapi import Depends
from sqlalchemy.orm import Session
from src.models.base import get_db

@app.get("/documents")
def list_docs(db: Session = Depends(get_db)):
    return db.query(Document).all()
    # Session auto-closes after request

# ❌ WRONG - Manual session in endpoint
@app.get("/documents")
def list_docs():
    db = SessionLocal()  # Session leak!
    return db.query(Document).all()
```

### 5. pgvector Version Check

**MUST**: Không rely vào `pgvector.__version__` (không tồn tại)

```python
# ❌ WRONG
import pgvector
print(pgvector.__version__)  # AttributeError!

# ✅ CORRECT - Chỉ check import
try:
    import pgvector
    print("✅ pgvector installed")
except ImportError:
    print("❌ pgvector not installed")
```

### 6. Repository Pattern

**SHOULD**: Sử dụng Repository thay vì raw queries

```python
# ✅ RECOMMENDED
from src.models.repositories import DocumentRepository
docs = DocumentRepository.get_all(db, status="active")

# ⚠️ OK but less maintainable
docs = db.query(Document).filter(Document.status == "active").all()
```

### 7. Transaction Handling

**MUST**: Rollback on errors

```python
# ✅ CORRECT
try:
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
except Exception as e:
    db.rollback()
    raise
finally:
    db.close()
```

### 8. Testing Scripts Location

**MUST**: Đặt test scripts vào đúng folder

- Database tests → `scripts/tests/test_db_*.py`
- API tests → `scripts/tests/test_api_*.py`
- Examples → `scripts/examples/example_*.py`
- Utilities → `scripts/*.py`

### 9. Dependencies Update

**MUST**: Update `environment.yml` khi thêm package mới

```yaml
# Thêm vào dependencies:
- sqlalchemy=2.0.23
- psycopg=3.1.13
- alembic=1.13.0
# pip dependencies:
- pip:
    - pgvector==0.2.4
```

### 10. Alembic Migrations

**MUST**: Không modify database schema bằng raw SQL trong production

```bash
# ✅ CORRECT - Use Alembic
alembic revision --autogenerate -m "Add new column"
alembic upgrade head

# ❌ WRONG - Raw SQL
psql -c "ALTER TABLE documents ADD COLUMN new_field TEXT"
```

## 🧪 Testing Checklist

Trước khi commit code liên quan database:

- [ ] Chạy `python scripts/test_db_connection.py` - PASS
- [ ] Chạy `python scripts/examples/sqlalchemy_usage.py` - No errors
- [ ] Verify no SQLAlchemy warnings trong logs
- [ ] Check session leaks với `engine.pool.status()`
- [ ] Test rollback behavior
-
