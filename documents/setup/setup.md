# RAG Bidding System - Setup Guide
**Last updated**: 2025-10-26  
**Python Version**: 3.10.18  
**OS**: Linux (Ubuntu)

---

## 📊 System Requirements

- Python 3.10+
- PostgreSQL 16+ with pgvector extension
- 8GB+ RAM (16GB recommended for reranking)
- GPU optional (CPU mode supported)

---

## 🗄️ Database Setup

### 1. Install PostgreSQL & pgvector

```bash
sudo apt update
sudo apt install postgresql postgresql-18-pgvector
```

### 2. Create Database & User

```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Create user (role)
CREATE ROLE rag WITH LOGIN PASSWORD 'your-password' NOSUPERUSER NOCREATEDB NOCREATEROLE;

# Create database
CREATE DATABASE ragdb OWNER rag ENCODING 'UTF8' TEMPLATE template0;

# Exit psql
\q
```

### 3. Enable pgvector Extension

```bash
sudo -u postgres psql -d ragdb -c 'CREATE EXTENSION IF NOT EXISTS vector;'
```

### 4. Verify Installation

```bash
sudo -u postgres psql -d ragdb -c '\dx'
```

**Expected output**: Should show `plpgsql` and `vector` extensions.

---

## 🐍 Python Environment Setup

### Option 1: Using Conda (Recommended)

```bash
# Create environment
conda env create -f environment.yaml

# Activate environment
conda activate bidding

# Verify installation
python -c "import langchain; print(langchain.__version__)"  # Should print 0.3.27
```

### Option 2: Using pip + venv

```bash
# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
pip list | grep langchain
```

---

## ⚙️ Environment Configuration

Create a `.env` file in the project root:

```bash
# OpenAI API
OPENAI_API_KEY=sk-...

# Database (PostgreSQL + pgvector)
DATABASE_URL=postgresql+psycopg://rag:your-password@localhost:5432/ragdb

# Models
EMBED_MODEL=text-embedding-3-large
LLM_MODEL=gpt-4o-mini
RERANKER_MODEL=BAAI/bge-reranker-v2-m3

# Collection name
LC_COLLECTION=docs

# Retrieval settings
RETRIEVAL_K=5
ENABLE_RERANKING=true
ENABLE_QUERY_ENHANCEMENT=true
RAG_MODE=balanced  # Options: fast, balanced, quality, adaptive

# Reranker settings (for BGE)
RERANKER_DEVICE=cpu  # Options: cuda, cpu, auto
RERANKER_BATCH_SIZE=32
RERANK_TOP_K=10
FINAL_DOCS_K=5

# Document filtering (Phase 1 enhancement)
# Status filtering: active, expired, or leave empty for no filter
# Default is "active" to only retrieve current legal documents
```

---

## 📦 Key Dependencies (Installed)

| Package | Version | Purpose |
|---------|---------|---------|
| `langchain` | 0.3.27 | Core RAG framework |
| `langchain-openai` | 0.3.33 | OpenAI integration |
| `langchain-postgres` | 0.0.15 | PGVector store |
| `openai` | 1.109.1 | OpenAI API client |
| `fastapi` | 0.112.4 | REST API framework |
| `psycopg` | 3.2.10 | PostgreSQL driver |
| `pgvector` | 0.3.6 | Vector similarity |
| `sentence-transformers` | 5.1.2 | Reranking models |
| `transformers` | 4.56.2 | NLP models (BGE) |
| `torch` | 2.8.0 | ML framework |

---

## 🚀 Database Initialization

### Import existing dump (if available)

```bash
# Restore from backup
psql -h localhost -U rag -d ragdb < ragdb_dump_20251026_220426.pg
```

### Bootstrap fresh database

```bash
# Run bootstrap script (creates schema + imports documents)
python scripts/bootstrap_db.py
```

---

## ✅ Verification

### 1. Test database connection

```bash
python -c "from config.models import settings; print(settings.database_url)"
```

### 2. Check document count

```bash
python -c "
from langchain_postgres import PGVector
from config.models import settings
store = PGVector(
    embeddings=None,
    collection_name=settings.collection,
    connection=settings.database_url,
    use_jsonb=True
)
print(f'Documents: {len(store.get())}')
"
```

### 3. Run API server

```bash
# Start server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Test endpoint (in another terminal)
curl http://localhost:8000/health
```

---

## 📝 Notes

- **Current setup**: Using CPU for reranking (set `RERANKER_DEVICE=cuda` if GPU available)
- **Document filtering**: Database contains only legal documents (845 docs) after cleanup
- **Metadata schema**: All documents have `status` (active/expired) and `valid_until` fields
- **Reranker**: BGE-reranker-v2-m3 supports Vietnamese text natively

---

## 🔧 Troubleshooting

### Database connection errors
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Restart if needed
sudo systemctl restart postgresql
```

### Import errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### GPU/CUDA errors (if using GPU)
```bash
# Switch to CPU mode
export RERANKER_DEVICE=cpu
``` 