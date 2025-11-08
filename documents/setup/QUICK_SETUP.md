# ⚡ QUICK SETUP GUIDE

Fast track setup for RAG Bidding System - Get running in 10 minutes!

---

## 🎯 Prerequisites

- Ubuntu 20.04+ or macOS 12+
- sudo access
- OpenAI API key

---

## 🚀 5-Step Setup

### 1️⃣ Install PostgreSQL + pgvector

```bash
# Run automated setup
chmod +x setup_db.sh
./setup_db.sh
```

### 2️⃣ Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your credentials
nano .env
```

**Minimum required:**
```env
DATABASE_URL=postgresql://superuser:rag-bidding@localhost:5432/ragdb
OPENAI_API_KEY=sk-your-key-here
```

### 3️⃣ Create Python Environment

```bash
# Create conda environment
conda env create -f environment.yaml

# Activate environment
conda activate rag-bidding
```

### 4️⃣ Initialize Database

```bash
# Create tables and collections
python scripts/bootstrap_db.py
```

### 5️⃣ Import Data

```bash
# Import preprocessed chunks (4,512 chunks with enrichment)
python scripts/import_processed_chunks.py \
  --chunks-dir data/processed/chunks \
  --batch-size 50
```

**Expected:** ~4 minutes import time

---

## ✅ Verify Installation

```bash
# Test retrieval
python -c "
from src.embedding.store.pgvector_store import vector_store
results = vector_store.similarity_search('đấu thầu', k=3)
print(f'✅ Found {len(results)} documents')
for doc in results:
    print(f'  - {doc.page_content[:80]}...')
"
```

---

## 🔗 Next Steps

- **Full Guide:** See [DATABASE_SETUP.md](DATABASE_SETUP.md) for detailed setup
- **API Server:** Run `uvicorn src.api.main:app --reload`
- **Documentation:** Check `documents/` for technical docs

---

## 🆘 Common Issues

**Connection refused?**
```bash
sudo systemctl start postgresql
```

**Extension not found?**
```bash
sudo apt-get install postgresql-18-pgvector
```