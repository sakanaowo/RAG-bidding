# Quick Start Guide
**RAG Bidding System** - Fast setup for development

## ⚡ TL;DR

```bash
# 1. Setup database
sudo apt install postgresql postgresql-16-pgvector
sudo -u postgres psql -c "CREATE ROLE rag WITH LOGIN PASSWORD 'your-password';"
sudo -u postgres psql -c "CREATE DATABASE ragdb OWNER rag;"
sudo -u postgres psql -d ragdb -c "CREATE EXTENSION vector;"

# 2. Setup Python environment
conda env create -f environment.yaml
conda activate bidding

# 3. Configure .env
cp .env.example .env  # Edit with your API keys

# 4. Import database
psql -h localhost -U rag -d ragdb < ragdb_dump_20251026_220426.pg

# 5. Start server
uvicorn app.api.main:app --reload
```

## 🔑 Essential Environment Variables

```bash
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql+psycopg://rag:password@localhost:5432/ragdb
EMBED_MODEL=text-embedding-3-large
LLM_MODEL=gpt-4o-mini
RAG_MODE=balanced
```

## 📚 Documentation

- **Full setup guide**: [setup.md](setup.md)
- **Dependencies**: [DEPENDENCIES.md](DEPENDENCIES.md)
- **Update log**: [UPDATE_SUMMARY.md](UPDATE_SUMMARY.md)

## 🧪 Quick Test

```bash
# Test retrieval
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Quy trình đấu thầu là gì?"}'
```

## 📊 Current Stats

- **Documents**: 845 legal documents
- **Status filtering**: Active/expired support
- **Reranking**: BGE-reranker-v2-m3 (Vietnamese)
- **Database size**: 34MB

---

**Need help?** Check [setup.md](setup.md) for detailed instructions.
