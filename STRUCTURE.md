# RAG-bidding Project Structure

**Last updated**: 2025-10-30  
**Restructured**: Consolidated `app/` and `config/` into `src/` for better organization

---

## 📁 Directory Layout

```
RAG-bidding/
├── src/                    # ✅ All application source code
│   ├── api/               # FastAPI application (moved from app/)
│   │   ├── main.py        # API entry point
│   │   ├── middleware/    # API middleware
│   │   ├── routers/       # API route handlers
│   │   └── schemas/       # Pydantic schemas
│   │
│   ├── config/            # Configuration (moved from config/)
│   │   ├── models.py      # Settings and models
│   │   ├── logging_config.py
│   │   ├── retrieval.py
│   │   └── legal_patterns.json
│   │
│   ├── chunking/          # Text chunking strategies
│   ├── embedding/         # Embedding and vector store
│   ├── evaluation/        # Benchmarks and metrics
│   ├── generation/        # LLM chains and prompts
│   ├── ingestion/         # Document crawling
│   ├── preprocessing/     # Data cleaning and parsing
│   ├── retrieval/         # RAG retrieval logic
│   └── utils/             # Shared utilities
│
├── scripts/               # ✅ Utility scripts (outside src)
│   ├── bootstrap_db.py    # Database initialization
│   ├── import_chunks.py   # Data import
│   └── *.sh               # Shell scripts
│
├── tests/                 # ✅ Test suite (outside src)
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   ├── fixtures/          # Test fixtures
│   └── test_*.py          # Test files
│
├── notebooks/             # ✅ Jupyter notebooks (exploration)
│   ├── ingestion/
│   └── preprocessing/
│
├── data/                  # ✅ Data storage
│   ├── raw/               # Original documents
│   ├── processed/         # Processed data
│   ├── indexes/           # Vector indexes
│   └── outputs/           # Reports and outputs
│
├── environment.yaml       # Conda environment
├── README.md              # Quick start guide
├── setup.md               # Detailed setup
└── start_server.sh        # Server startup script
```

---

## 🔄 Changes Made

### ✅ Moved Directories
- `app/api/` → `src/api/` (FastAPI application)
- `config/` → `src/config/` (Configuration)

### ✅ Updated Imports
All imports updated from:
```python
from config.models import settings      # ❌ Old
from app.api.main import app            # ❌ Old
```

To:
```python
from src.config.models import settings  # ✅ New
from src.api.main import app            # ✅ New
```

### ✅ Updated Entry Points
- `start_server.sh`: `app.api.main:app` → `src.api.main:app`
- `README.md`: Updated startup command
- `setup.md`: Updated documentation

### ✅ Removed Deprecated
- `docs/` - Old documentation
- `dev-log/` - Development logs
- `docker/` - Unused Docker configs
- `tests/test_splitter.py` - References non-existent `app.data`
- `tests/test_simple_cleaning.py` - References non-existent `app.data`
- `tests/test_enhanced_pipeline.py` - References non-existent `app.data`

---

## 🚀 Start Server

```bash
# Using script
./start_server.sh

# Manual
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 📝 Import Conventions

### Application Code (in `src/`)
```python
# Absolute imports from src
from src.config.models import settings
from src.embedding.store.pgvector_store import bootstrap
from src.retrieval.retrievers import create_retriever
```

### Scripts (outside `src/`)
```python
# Import from src package
from src.config.models import settings
from src.embedding.store.pgvector_store import bootstrap
```

### Tests
```python
# Import from src package
from src.api.main import app
from src.config.models import settings
```

---

## ✅ Benefits

1. **Consistent Structure**: All app code under `src/`
2. **Clear Separation**: 
   - `src/` = application code
   - `scripts/` = utilities
   - `tests/` = test suite
   - `notebooks/` = exploration
3. **Standard Python Layout**: Follows Python packaging best practices
4. **Easier Deployment**: Single source directory to package
5. **Better IDE Support**: Clear module boundaries

---

## 📦 Key Modules

| Module | Purpose |
|--------|---------|
| `src.api` | FastAPI REST API |
| `src.config` | Settings and configuration |
| `src.retrieval` | RAG retrieval pipeline |
| `src.generation` | LLM answer generation |
| `src.embedding` | Vector store (PGVector) |
| `src.preprocessing` | Document processing |

---

**Note**: This structure follows Python best practices and makes the codebase more maintainable.
