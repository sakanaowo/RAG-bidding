# 🚀 Tài Liệu Setup Môi Trường & Database - RAG Bidding System

> **Phiên bản:** 2.0.0  
> **Ngày cập nhật:** 24/11/2025  
> **Tác giả:** System Analysis

---

## 📋 Mục Lục

1. [Tổng Quan Hệ Thống](#-tổng-quan-hệ-thống)
2. [Yêu Cầu Hệ Thống](#-yêu-cầu-hệ-thống)
3. [Setup PostgreSQL Database](#-setup-postgresql-database)
4. [Setup Conda Environment](#-setup-conda-environment)
5. [Cấu Hình Environment Variables](#-cấu-hình-environment-variables)
6. [Setup Redis (Optional)](#-setup-redis-optional)
7. [Khởi Tạo Database](#-khởi-tạo-database)
8. [Import Dữ Liệu](#-import-dữ-liệu)
9. [Kiểm Tra & Verification](#-kiểm-tra--verification)
10. [Troubleshooting](#-troubleshooting)

---

## 🎯 Tổng Quan Hệ Thống

### Kiến Trúc Hệ Thống

```
┌─────────────────────────────────────────────────────────────┐
│                    RAG Bidding System                        │
├─────────────────────────────────────────────────────────────┤
│  FastAPI (Port 8000)                                         │
│    ↓                                                         │
│  LangChain Pipeline                                          │
│    ├── Query Enhancement (Multi-Query/HyDE/Step-Back)       │
│    ├── Vector Retrieval (PGVector + OpenAI Embeddings)      │
│    ├── Reranking (BGE-reranker-v2-m3)                       │
│    └── Generation (GPT-4o-mini)                              │
├─────────────────────────────────────────────────────────────┤
│  Storage Layer:                                              │
│    • PostgreSQL 18 + pgvector (Vector DB)                   │
│    • Redis (Cache L2 - Optional)                            │
│    • In-Memory LRU (Cache L1 - Always enabled)              │
├─────────────────────────────────────────────────────────────┤
│  Data:                                                       │
│    • 7,892 chunks                                            │
│    • 3,072-dim embeddings (text-embedding-3-large)          │
│    • 149 MB database size                                    │
└─────────────────────────────────────────────────────────────┘
```

### Tech Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **Python** | CPython | 3.10.18 |
| **Framework** | FastAPI | 0.112.4 |
| **LangChain** | langchain-core | 0.3.76 |
| **Database** | PostgreSQL | 18+ |
| **Vector Extension** | pgvector | 0.8.1 |
| **Embeddings** | OpenAI text-embedding-3-large | 3072-dim |
| **LLM** | GPT-4o-mini | Latest |
| **Reranker** | BAAI/bge-reranker-v2-m3 | Multilingual |
| **Cache** | Redis (Optional) | 7.0+ |
| **Deep Learning** | PyTorch | 2.8.0 |
| **NLP** | sentence-transformers | 5.1.2 |

---

## 💻 Yêu Cầu Hệ Thống

### Phần Cứng

**Minimum:**
- CPU: 4 cores
- RAM: 8 GB
- Disk: 10 GB free space
- GPU: Optional (CPU works fine)

**Recommended:**
- CPU: 8+ cores
- RAM: 16 GB
- Disk: 20 GB SSD
- GPU: NVIDIA with CUDA 12.1+ (for faster reranking)

### Phần Mềm

**Required:**
- Ubuntu 20.04+ / macOS 11+ / Windows 10+ (WSL2)
- Anaconda/Miniconda
- PostgreSQL 18+
- Git

**Optional:**
- Redis 7.0+
- CUDA Toolkit 12.1 (for GPU acceleration)
- pgBouncer (for production deployment)

---

## 🗄️ Setup PostgreSQL Database

### Bước 1: Cài Đặt PostgreSQL 18

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y postgresql-18 postgresql-contrib-18

# macOS (Homebrew)
brew install postgresql@18

# Kiểm tra version
psql --version
# Expected: psql (PostgreSQL) 18.x
```

### Bước 2: Cài Đặt pgvector Extension

```bash
# Ubuntu/Debian
sudo apt install -y postgresql-18-pgvector

# macOS
brew install pgvector

# Kiểm tra
sudo -u postgres psql -c "SELECT * FROM pg_available_extensions WHERE name = 'vector';"
```

### Bước 3: Tạo Database & User

**Option A: Sử dụng Script Tự Động (Recommended)**

```bash
cd /path/to/RAG-bidding
chmod +x setup_db.sh

# Chỉnh sửa credentials trong setup_db.sh
nano setup_db.sh
# Thay đổi:
# DB_NAME="rag_bidding_v2"
# DB_USER="sakana"
# DB_PASSWORD="sakana123"

# Chạy script
./setup_db.sh
```

**Option B: Setup Thủ Công**

```bash
# 1. Truy cập PostgreSQL
sudo -u postgres psql

# 2. Tạo user
CREATE USER sakana WITH PASSWORD 'sakana123';

# 3. Tạo database
CREATE DATABASE rag_bidding_v2;

# 4. Cấp quyền
GRANT ALL PRIVILEGES ON DATABASE rag_bidding_v2 TO sakana;

# 5. Connect vào database mới
\c rag_bidding_v2

# 6. Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

# 7. Cấp quyền schema
GRANT ALL ON SCHEMA public TO sakana;
GRANT ALL ON ALL TABLES IN SCHEMA public TO sakana;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO sakana;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO sakana;

# 8. Thoát
\q
```

### Bước 4: Verify Database Setup

```bash
# Test connection
PGPASSWORD=sakana123 psql -U sakana -d rag_bidding_v2 -h localhost -p 5432 -c "\dx"

# Expected output:
#                                       List of installed extensions
#   Name   | Version |   Schema   |                     Description                      
# ---------+---------+------------+------------------------------------------------------
#  plpgsql | 1.0     | pg_catalog | PL/pgSQL procedural language
#  vector  | 0.8.1   | public     | vector data type and ivfflat and hnsw access methods
```

### Bước 5: Optimize PostgreSQL Configuration (Optional)

```bash
# Copy optimized config
sudo cp postgresql.conf.optimized /etc/postgresql/18/main/postgresql.conf

# Hoặc chỉnh sửa thủ công
sudo nano /etc/postgresql/18/main/postgresql.conf

# Key settings for vector search:
# shared_buffers = 4GB
# effective_cache_size = 12GB
# maintenance_work_mem = 2GB
# max_parallel_workers_per_gather = 4

# Restart PostgreSQL
sudo systemctl restart postgresql
```

---

## 🐍 Setup Conda Environment

### Bước 1: Clone Repository

```bash
git clone https://github.com/sakanaowo/RAG-bidding.git
cd RAG-bidding
```

### Bước 2: Tạo Conda Environment

```bash
# Tạo environment từ file YAML
conda env create -f environment.yaml

# Environment name sẽ là "bidding" (theo file YAML)
# NHƯNG trong thực tế đang dùng "venv"

# Nếu muốn đổi tên:
conda create -n venv python=3.10
conda activate venv

# Install dependencies
pip install -r <(grep "      -" environment.yaml | sed 's/      - //')
```

### Bước 3: Verify Installation

```bash
# Activate environment
conda activate venv

# Check Python version
python --version
# Expected: Python 3.10.18

# Check key packages
python -c "import langchain; print(f'LangChain: {langchain.__version__}')"
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import sentence_transformers; print('Sentence-Transformers: OK')"

# Check CUDA (if using GPU)
python -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}')"
```

### Package Versions (Reference)

```
fastapi==0.112.4
langchain==0.3.27
langchain-core==0.3.76
langchain-openai==0.3.33
langchain-postgres==0.0.15
openai==1.109.1
psycopg==3.2.10
pgvector==0.3.6
sentence-transformers==5.1.2
transformers==4.56.2
torch==2.8.0
uvicorn==0.30.6
```

---

## 🔐 Cấu Hình Environment Variables

### Bước 1: Tạo File `.env`

```bash
cd /path/to/RAG-bidding
cp .env.example .env
nano .env
```

### Bước 2: Cấu Hình Required Variables

```bash
# ===== OPENAI API (REQUIRED) =====
OPENAI_API_KEY=sk-proj-your-openai-api-key-here

# ===== DATABASE (REQUIRED) =====
DB_USER=sakana
DB_PASSWORD=sakana123
DB_NAME=rag_bidding_v2
DB_HOST=localhost
DB_PORT=5432
DATABASE_URL=postgresql+psycopg://sakana:sakana123@localhost:5432/rag_bidding_v2

# ===== EMBEDDINGS & LLM =====
LC_COLLECTION=docs
EMBED_PROVIDER=openai
EMBED_MODEL=text-embedding-3-large  # 3072 dimensions (native)
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini

# ===== CHUNKING =====
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
ALLOWED_EXT=.pdf,.docx,.txt,.md

# ===== RAG PERFORMANCE =====
ENABLE_RERANKING=true
ENABLE_ADAPTIVE_RETRIEVAL=true
ENABLE_QUERY_ENHANCEMENT=true
RAG_MODE=balanced  # fast, balanced, quality, adaptive

# ===== REDIS CACHE (OPTIONAL) =====
ENABLE_REDIS_CACHE=true
ENABLE_REDIS_SESSIONS=true
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB_CACHE=0          # Database 0 for retrieval cache
REDIS_DB_SESSIONS=1       # Database 1 for chat sessions
CACHE_TTL=3600           # 1 hour

# ===== API CONFIGURATION =====
API_HOST=0.0.0.0
API_PORT=8000
MAX_UPLOAD_SIZE=52428800  # 50MB
MAX_FILES_PER_BATCH=10

# ===== LOGGING =====
LOG_LEVEL=INFO
LOG_JSON=False
LOG_FILE=logs/server-log.txt
```

### Bước 3: Verify Environment Variables

```bash
# Load .env và check
source .env
echo $DATABASE_URL
echo $OPENAI_API_KEY

# Hoặc dùng Python
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('DATABASE_URL'))"
```

---

## 🔴 Setup Redis (Optional)

### Cài Đặt Redis

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y redis-server

# macOS
brew install redis

# Start Redis
sudo systemctl start redis-server  # Linux
brew services start redis          # macOS

# Enable auto-start
sudo systemctl enable redis-server
```

### Cấu Hình Redis

```bash
# Edit config
sudo nano /etc/redis/redis.conf

# Key settings:
# maxmemory 2gb
# maxmemory-policy allkeys-lru
# save ""  # Disable persistence if cache-only

# Restart
sudo systemctl restart redis-server
```

### Verify Redis

```bash
# Test connection
redis-cli ping
# Expected: PONG

# Check info
redis-cli INFO stats

# Monitor in real-time
redis-cli MONITOR
```

**Note:** Redis là OPTIONAL. Hệ thống vẫn chạy tốt với L1 cache (in-memory) và L3 cache (PostgreSQL).

---

## 🔧 Khởi Tạo Database

### Bước 1: Bootstrap Database Tables

```bash
cd /path/to/RAG-bidding
conda activate venv

# Run bootstrap script
python scripts/bootstrap_db.py
```

**Script này sẽ:**
- Tạo extension `vector` nếu chưa có
- Tạo bảng `documents` (document management)
- Tạo bảng `langchain_pg_collection` (internal)
- Tạo bảng `langchain_pg_embedding` (vector storage)
- Tạo collection `docs` (internal collection name)

### Bước 2: Verify Tables Created

```bash
PGPASSWORD=sakana123 psql -U sakana -d rag_bidding_v2 -h localhost -c "\dt"

# Expected output:
#                   List of tables
#  Schema |          Name           | Type  | Owner  
# --------+-------------------------+-------+--------
#  public | documents               | table | sakana
#  public | langchain_pg_collection | table | sakana
#  public | langchain_pg_embedding  | table | sakana
```

### Bước 3: Check Table Schemas

```bash
# Check embedding table schema
PGPASSWORD=sakana123 psql -U sakana -d rag_bidding_v2 -h localhost -c "\d+ langchain_pg_embedding"

# Key columns:
# - id: UUID primary key
# - collection_id: UUID foreign key to langchain_pg_collection
# - embedding: vector(3072)  ← Native OpenAI embedding dimensions
# - document: text
# - cmetadata: jsonb  ← Rich metadata for filtering
```

---

## 📥 Import Dữ Liệu

### Option 1: Import Processed Chunks (Recommended)

Hệ thống đã có **7,892 chunks** được pre-processed và enriched.

```bash
cd /path/to/RAG-bidding
conda activate venv

# Import tất cả chunks từ data/processed/chunks/
python scripts/import_processed_chunks.py

# Hoặc import selective
python scripts/import_processed_chunks.py \
  --chunks-dir data/processed/chunks \
  --file-pattern "Luat*.jsonl" \
  --batch-size 50

# Dry run để preview
python scripts/import_processed_chunks.py --dry-run
```

**Import Process:**
1. Load JSONL files từ `data/processed/chunks/`
2. Convert UniversalChunk → LangChain Document
3. Generate embeddings (OpenAI text-embedding-3-large)
4. Store vào PostgreSQL với metadata

**Time:** ~6-8 minutes cho 7,892 chunks (~20 chunks/second)

### Option 2: Process Raw Documents

Nếu có tài liệu mới trong `data/raw/`:

```bash
# Process documents với enrichment
python scripts/batch_reprocess_all.py \
  --raw-dir data/raw \
  --output-dir data/processed

# Import vào database
python scripts/import_processed_chunks.py
```

### Verify Import

```bash
# Check total chunks
PGPASSWORD=sakana123 psql -U sakana -d rag_bidding_v2 -h localhost -c \
  "SELECT COUNT(*) as total_chunks FROM langchain_pg_embedding;"

# Expected: 7892 chunks

# Check database size
PGPASSWORD=sakana123 psql -U sakana -d rag_bidding_v2 -h localhost -c \
  "SELECT pg_size_pretty(pg_database_size('rag_bidding_v2')) as db_size;"

# Expected: ~149 MB

# Sample data
PGPASSWORD=sakana123 psql -U sakana -d rag_bidding_v2 -h localhost -c \
  "SELECT document, cmetadata->>'chunk_id', cmetadata->>'document_type' 
   FROM langchain_pg_embedding 
   LIMIT 3;"
```

---

## ✅ Kiểm Tra & Verification

### 1. Start API Server

```bash
cd /path/to/RAG-bidding
conda activate venv

# Start server
./start_server.sh

# Hoặc manual
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Health Check

```bash
# API health
curl http://localhost:8000/health

# Expected:
# {"db": true}

# System stats
curl http://localhost:8000/stats

# Expected:
# {
#   "vector_store": {
#     "collection": "docs",
#     "embedding_model": "text-embedding-3-large"
#   },
#   "llm": {"model": "gpt-4o-mini"},
#   ...
# }
```

### 3. Test Query

```bash
# Simple query
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quy trình đấu thầu rộng rãi là gì?",
    "mode": "balanced"
  }'

# Expected response:
# {
#   "answer": "...",
#   "sources": [...],
#   "adaptive_retrieval": {...},
#   "processing_time_ms": 250
# }
```

### 4. Test All RAG Modes

```bash
# Fast mode (no enhancement, no reranking)
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Thời hạn nộp hồ sơ dự thầu?", "mode": "fast"}'

# Balanced mode (multi-query + BGE reranking) ⭐ Default
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Thời hạn nộp hồ sơ dự thầu?", "mode": "balanced"}'

# Quality mode (all enhancements + reranking)
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Thời hạn nộp hồ sơ dự thầu?", "mode": "quality"}'

# Adaptive mode (dynamic K selection)
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Thời hạn nộp hồ sơ dự thầu?", "mode": "adaptive"}'
```

### 5. Verify Cache (if Redis enabled)

```bash
# Monitor Redis
redis-cli MONITOR

# Run query (should cache result)
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Test caching", "mode": "balanced"}'

# Run same query again (should hit cache - faster)
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Test caching", "mode": "balanced"}'

# Check cache stats
redis-cli INFO stats | grep cache
```

### 6. Performance Benchmarks

```bash
# Run performance test
python scripts/benchmark_retrieval.py

# Expected results:
# Fast mode: ~1s
# Balanced mode: ~2-3s ⭐
# Quality mode: ~3-5s
# Adaptive mode: ~2-4s
```

---

## 🔧 Troubleshooting

### Database Connection Issues

**Problem:** `psycopg.OperationalError: connection failed`

```bash
# 1. Check PostgreSQL service
sudo systemctl status postgresql

# 2. Check port listening
sudo netstat -tulpn | grep 5432

# 3. Test direct connection
psql -U sakana -d rag_bidding_v2 -h localhost -p 5432

# 4. Check pg_hba.conf
sudo nano /etc/postgresql/18/main/pg_hba.conf
# Ensure line: host all all 127.0.0.1/32 md5

# 5. Restart PostgreSQL
sudo systemctl restart postgresql
```

### OpenAI API Errors

**Problem:** `openai.error.AuthenticationError`

```bash
# 1. Verify API key
echo $OPENAI_API_KEY

# 2. Test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# 3. Check .env file loaded
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('OPENAI_API_KEY'))"
```

### Redis Connection Issues

**Problem:** `redis.exceptions.ConnectionError`

```bash
# 1. Check Redis service
sudo systemctl status redis-server

# 2. Test connection
redis-cli ping

# 3. Disable Redis cache (fallback)
nano .env
# Set: ENABLE_REDIS_CACHE=false
```

### Import Errors

**Problem:** No chunks imported

```bash
# 1. Check chunks directory
ls -lh data/processed/chunks/

# 2. Verify JSONL format
head -n 1 data/processed/chunks/*.jsonl | python -m json.tool

# 3. Run dry-run
python scripts/import_processed_chunks.py --dry-run

# 4. Check database permissions
PGPASSWORD=sakana123 psql -U sakana -d rag_bidding_v2 -c "\du"
```

### Memory Issues (BGE Reranker)

**Problem:** `RuntimeError: CUDA out of memory`

```bash
# 1. Force CPU mode
export RERANKER_DEVICE=cpu

# 2. Reduce batch size
nano .env
# Set: RERANKER_BATCH_SIZE=8

# 3. Clear CUDA cache
python -c "import torch; torch.cuda.empty_cache()"
```

### Slow Query Performance

**Checklist:**
- ✅ Reranking enabled: `ENABLE_RERANKING=true`
- ✅ Cache enabled: `ENABLE_REDIS_CACHE=true`
- ✅ Adaptive retrieval: `ENABLE_ADAPTIVE_RETRIEVAL=true`
- ✅ Use balanced mode: `RAG_MODE=balanced`
- ✅ PostgreSQL optimized: Check `postgresql.conf`

```bash
# Check current settings
curl http://localhost:8000/features
```

---

## 📊 Database Statistics (Current State)

```
Total Chunks:       7,892
Database Size:      149 MB
Embedding Dims:     3,072 (native text-embedding-3-large)
Extensions:         pgvector 0.8.1
Tables:
  - langchain_pg_collection
  - langchain_pg_embedding
  - documents

Collections:        docs (1 collection)
```

---

## 🚀 Next Steps

### Production Deployment

1. **Enable pgBouncer** (Connection Pooling)
   - See: `documents/technical/POOLING_CACHE_PLAN.md`
   - Install: `sudo apt install pgbouncer`
   - Config: `/etc/pgbouncer/pgbouncer.ini`

2. **Enable Redis Cache** (L2 Cache)
   - Set `ENABLE_REDIS_CACHE=true`
   - Configure max memory: `maxmemory 2gb`

3. **Optimize PostgreSQL**
   - Use `postgresql.conf.optimized`
   - Enable HNSW index for faster vector search
   - Monitor with `pg_stat_statements`

4. **Load Testing**
   ```bash
   python scripts/test/performance/test_load_simulation.py
   ```

### Development

1. **Add New Documents**
   ```bash
   # Add to data/raw/
   python scripts/batch_reprocess_all.py
   python scripts/import_processed_chunks.py
   ```

2. **Run Tests**
   ```bash
   pytest scripts/test/ -v
   pytest tests/reranking/ -v
   ```

3. **Monitor Logs**
   ```bash
   tail -f logs/server-log.txt
   ```

---

## 📚 Additional Documentation

- [Quick Setup Guide](documents/setup/QUICK_SETUP.md)
- [Database Setup](documents/setup/DATABASE_SETUP.md)
- [Pooling & Cache Plan](documents/technical/POOLING_CACHE_PLAN.md)
- [Pipeline Integration](documents/technical/PIPELINE_INTEGRATION_SUMMARY.md)
- [Test Suite](scripts/test/README.md)

---

## ✅ Setup Checklist

- [ ] PostgreSQL 18 installed
- [ ] pgvector extension enabled
- [ ] Database `rag_bidding_v2` created
- [ ] User `sakana` with correct permissions
- [ ] Conda environment `venv` created
- [ ] All packages installed from `environment.yaml`
- [ ] `.env` file configured with OpenAI API key
- [ ] Redis installed (optional but recommended)
- [ ] Database tables bootstrapped
- [ ] 7,892 chunks imported
- [ ] API server starts successfully
- [ ] Health check passes
- [ ] Test query returns results
- [ ] Cache working (if enabled)

---

**🎉 Setup Complete!**

Hệ thống RAG Bidding đã sẵn sàng để sử dụng. Truy cập API documentation tại: http://localhost:8000/docs
