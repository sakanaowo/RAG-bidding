# 🗄️ DATABASE SETUP GUIDE

Complete guide for setting up PostgreSQL database with pgvector extension for the RAG Bidding System.

**Last Updated:** November 4, 2025  
**PostgreSQL Version:** 18  
**pgvector Version:** 0.7.0+

---

## 📋 TABLE OF CONTENTS

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Manual Setup](#manual-setup)
4. [Environment Configuration](#environment-configuration)
5. [Database Bootstrap](#database-bootstrap)
6. [Data Import](#data-import)
7. [Verification](#verification)
8. [Troubleshooting](#troubleshooting)
9. [Advanced Configuration](#advanced-configuration)

---

## 🎯 PREREQUISITES

### System Requirements

- **OS:** Ubuntu 20.04+ / Debian 11+ / macOS 12+
- **RAM:** Minimum 8GB (16GB recommended for production)
- **Disk:** 20GB free space
- **Permissions:** sudo access for PostgreSQL installation

### Software Requirements

- **PostgreSQL:** 14+ (18 recommended)
- **Python:** 3.10+
- **Conda:** Miniconda or Anaconda
- **Git:** For cloning the repository

---

## 🚀 QUICK START

### Option 1: Automated Setup (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/sakanaowo/RAG-bidding.git
cd RAG-bidding

# 2. Run automated database setup
chmod +x setup_db.sh
./setup_db.sh

# 3. Create environment file
cp .env.example .env
# Edit .env with your database credentials

# 4. Create conda environment
conda env create -f environment.yaml
conda activate rag-bidding

# 5. Bootstrap database tables
python scripts/bootstrap_db.py

# 6. Import processed data
python scripts/import_processed_chunks.py --chunks-dir data/processed/chunks
```

**Expected time:** 5-10 minutes

---

## 🔧 MANUAL SETUP

### Step 1: Install PostgreSQL

#### Ubuntu/Debian

```bash
# Update package lists
sudo apt-get update

# Install PostgreSQL 18
sudo apt-get install -y postgresql-18 postgresql-contrib-18

# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Verify installation
psql --version
# Expected: psql (PostgreSQL) 18.x
```

#### macOS (via Homebrew)

```bash
# Install PostgreSQL
brew install postgresql@18

# Start PostgreSQL service
brew services start postgresql@18

# Verify installation
psql --version
```

### Step 2: Install pgvector Extension

#### Ubuntu/Debian

```bash
# Install pgvector
sudo apt-get install -y postgresql-18-pgvector

# Verify installation
dpkg -l | grep pgvector
```

#### macOS

```bash
# Install pgvector
brew install pgvector

# Or build from source
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
make install
```

### Step 3: Create Database and User

```bash
# Switch to postgres user
sudo -u postgres psql

# Inside psql shell:
```

```sql
-- Create database user
CREATE USER rag_user WITH PASSWORD 'your_secure_password';

-- Create database
CREATE DATABASE rag_bidding_v2;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE rag_bidding_v2 TO rag_user;

-- Connect to new database
\c rag_bidding_v2

-- Enable pgvector extension
CREATE EXTENSION vector;

-- Grant schema permissions
GRANT ALL ON SCHEMA public TO rag_user;
GRANT ALL ON ALL TABLES IN SCHEMA public TO rag_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO rag_user;

-- Exit psql
\q
```

### Step 4: Verify Database Setup

```bash
# Test connection
psql -U rag_user -d rag_bidding_v2 -h localhost

# Inside psql, verify extension
\dx
# Should show "vector" extension

# Check version
SELECT extversion FROM pg_extension WHERE extname = 'vector';

# Exit
\q
```

---

## ⚙️ ENVIRONMENT CONFIGURATION

### Create `.env` File

Create a `.env` file in the project root:

```bash
# Database Configuration
DATABASE_URL=postgresql://rag_user:your_secure_password@localhost:5432/rag_bidding_v2
LC_COLLECTION=docs

# OpenAI API (Required for embeddings)
OPENAI_API_KEY=sk-your-openai-api-key-here

# Embedding Model (3072 dimensions - native)
EMBED_MODEL=text-embedding-3-large

# LLM Model
LLM_MODEL=gpt-4o-mini

# Chunking Configuration
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Retrieval Configuration
RETRIEVAL_K=5
MIN_RELEVANCE_SCORE=0.7

# Reranking (Optional)
ENABLE_RERANKING=true
RERANKER_MODEL=BAAI/bge-reranker-v2-m3
RERANKER_DEVICE=cpu
RERANK_TOP_K=10
FINAL_DOCS_K=5

# Logging
LOG_LEVEL=INFO
LOG_JSON=false
```

### Environment Variables Explained

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection string | - | ✅ Yes |
| `LC_COLLECTION` | Vector store collection name | `docs` | No |
| `OPENAI_API_KEY` | OpenAI API key for embeddings | - | ✅ Yes |
| `EMBED_MODEL` | Embedding model name | `text-embedding-3-large` | No |
| `LLM_MODEL` | LLM model for generation | `gpt-4o-mini` | No |
| `RETRIEVAL_K` | Number of documents to retrieve | `5` | No |
| `ENABLE_RERANKING` | Enable BGE reranking | `true` | No |

---

## 🗃️ DATABASE BOOTSTRAP

### Create Tables and Collections

```bash
# Activate conda environment
conda activate rag-bidding

# Bootstrap database
python scripts/bootstrap_db.py
```

**What this does:**
1. Creates `vector` extension (if not exists)
2. Creates `langchain_pg_collection` table
3. Creates `langchain_pg_embedding` table with vector column
4. Creates initial collection named `docs`

### Verify Tables

```bash
psql -U rag_user -d rag_bidding_v2 -h localhost
```

```sql
-- List all tables
\dt

-- Expected output:
--  langchain_pg_collection
--  langchain_pg_embedding

-- Check collection
SELECT * FROM langchain_pg_collection;

-- Check embedding table structure
\d langchain_pg_embedding

-- Exit
\q
```

---

## 📥 DATA IMPORT

### Option 1: Import Preprocessed Chunks (Recommended)

If you have processed data ready:

```bash
# Import all chunks with enrichment
python scripts/import_processed_chunks.py \
  --chunks-dir data/processed/chunks \
  --batch-size 50
```

**Progress output:**
```
📊 Embedding Model: text-embedding-3-large
🔢 Embedding Dimensions: 3072 (native)
📦 Collection: docs

Found 63 chunk files
Processing: data/processed/chunks/Luat_dau_thau_2023.jsonl

Importing: 100% 4512/4512 [03:41<00:00, 20.34chunks/s]

✅ Chunks imported: 4,512
⏱️  Total time: 3m 41s
📊 Throughput: 20.34 chunks/s
```

### Option 2: Process and Import Raw Documents

If starting from scratch:

```bash
# Step 1: Process raw documents with enrichment
python scripts/batch_reprocess_all.py \
  --raw-dir data/raw \
  --output-dir data/processed \
  --max-workers 1

# Step 2: Import processed chunks
python scripts/import_processed_chunks.py \
  --chunks-dir data/processed/chunks \
  --batch-size 50
```

### Batch Processing Options

```bash
# Process specific document type
python scripts/batch_reprocess_all.py \
  --raw-dir data/raw \
  --output-dir data/processed \
  --doc-type law

# Process without enrichment (faster, but no metadata)
python scripts/batch_reprocess_all.py \
  --raw-dir data/raw \
  --output-dir data/processed \
  --no-enrichment

# Dry run to preview files
python scripts/batch_reprocess_all.py \
  --raw-dir data/raw \
  --dry-run
```

---

## ✅ VERIFICATION

### Check Database Status

```bash
# Run verification script
python -c "
from src.embedding.store.pgvector_store import vector_store
from langchain_core.documents import Document

# Check collection
print('📊 Collection:', vector_store.collection_name)

# Count embeddings
result = vector_store._make_session().execute(
    'SELECT COUNT(*) FROM langchain_pg_embedding'
).scalar()
print('📈 Total embeddings:', result)

# Test retrieval
results = vector_store.similarity_search('đấu thầu', k=3)
print(f'🔍 Retrieved {len(results)} documents')
for i, doc in enumerate(results, 1):
    print(f'  {i}. {doc.page_content[:100]}...')
"
```

### Expected Output

```
📊 Collection: docs
📈 Total embeddings: 4512
🔍 Retrieved 3 documents
  1. Điều 1. Phạm vi điều chỉnh Luật này quy định về lựa chọn nhà thầu, nhà đầu tư...
  2. Gói thầu là một phần công việc của dự án đầu tư hoặc dự toán mua sắm được...
  3. Đấu thầu rộng rãi là hình thức lựa chọn nhà thầu mà bên mời thầu mời...
```

### Database Health Check

```sql
-- Connect to database
psql -U rag_user -d rag_bidding_v2 -h localhost

-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check embedding dimensions
SELECT 
    COUNT(*) as total_embeddings,
    vector_dims(embedding) as dimensions
FROM langchain_pg_embedding
GROUP BY vector_dims(embedding);

-- Check metadata
SELECT 
    jsonb_object_keys(cmetadata) as metadata_key,
    COUNT(*) as count
FROM langchain_pg_embedding
GROUP BY jsonb_object_keys(cmetadata)
ORDER BY count DESC;

-- Exit
\q
```

---

## 🔧 TROUBLESHOOTING

### Common Issues

#### 1. Connection Refused

**Error:**
```
psycopg.OperationalError: connection to server at "localhost" (127.0.0.1), port 5432 failed: Connection refused
```

**Solution:**
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Start PostgreSQL
sudo systemctl start postgresql

# Check port
sudo netstat -plnt | grep 5432
```

#### 2. Extension Not Found

**Error:**
```
ERROR: could not open extension control file "/usr/share/postgresql/18/extension/vector.control"
```

**Solution:**
```bash
# Reinstall pgvector
sudo apt-get remove postgresql-18-pgvector
sudo apt-get install postgresql-18-pgvector

# Or build from source
cd /tmp
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

#### 3. Permission Denied

**Error:**
```
ERROR: permission denied for schema public
```

**Solution:**
```sql
-- As postgres user
sudo -u postgres psql -d rag_bidding_v2

GRANT ALL ON SCHEMA public TO rag_user;
GRANT ALL ON ALL TABLES IN SCHEMA public TO rag_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO rag_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO rag_user;
```

#### 4. Out of Memory

**Error:**
```
ERROR: out of memory
DETAIL: Failed on request of size XXX in memory context
```

**Solution:**
```bash
# Edit PostgreSQL config
sudo nano /etc/postgresql/18/main/postgresql.conf

# Increase memory settings
shared_buffers = 2GB
work_mem = 256MB
maintenance_work_mem = 1GB
effective_cache_size = 8GB

# Restart PostgreSQL
sudo systemctl restart postgresql
```

#### 5. Slow Import Performance

**Symptoms:** Import taking longer than 5 minutes per 1000 chunks

**Solution:**
```bash
# 1. Disable fsync during bulk import (faster, but less safe)
sudo -u postgres psql -d rag_bidding_v2 -c "ALTER SYSTEM SET fsync = off;"
sudo systemctl restart postgresql

# 2. Import data
python scripts/import_processed_chunks.py --chunks-dir data/processed/chunks

# 3. Re-enable fsync (IMPORTANT!)
sudo -u postgres psql -d rag_bidding_v2 -c "ALTER SYSTEM SET fsync = on;"
sudo systemctl restart postgresql

# 4. Create indexes if needed (see Advanced Configuration)
```

---

## 🚀 ADVANCED CONFIGURATION

### Performance Tuning

#### PostgreSQL Configuration

Edit `/etc/postgresql/18/main/postgresql.conf`:

```ini
# Memory Settings (for 16GB RAM)
shared_buffers = 4GB
effective_cache_size = 12GB
maintenance_work_mem = 2GB
work_mem = 256MB

# Parallel Query
max_parallel_workers_per_gather = 4
max_parallel_workers = 8

# WAL Settings
wal_buffers = 16MB
checkpoint_completion_target = 0.9

# Query Planner
random_page_cost = 1.1  # For SSD
effective_io_concurrency = 200
```

Restart PostgreSQL:
```bash
sudo systemctl restart postgresql
```

### Index Optimization

Currently the system uses **native vector search** without indexes for maximum quality (3072-dim embeddings).

If you need faster search at the cost of some accuracy, you can add HNSW index:

```sql
-- Connect to database
psql -U rag_user -d rag_bidding_v2

-- Create HNSW index (may take 10-30 minutes for large datasets)
CREATE INDEX ON langchain_pg_embedding 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- For faster index creation (less accurate)
CREATE INDEX ON langchain_pg_embedding 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 8, ef_construction = 32);
```

**Note:** HNSW index parameters:
- `m`: Max connections per layer (higher = more accurate but slower)
- `ef_construction`: Size of dynamic candidate list (higher = better quality but slower build)

### Connection Pooling

For production deployments with high concurrent requests:

```python
# src/config/models.py
DATABASE_URL=postgresql://rag_user:password@localhost:5432/rag_bidding_v2?options=-c%20jit=off&pool_size=20&max_overflow=10
```

### Backup and Restore

#### Backup Database

```bash
# Full database backup
pg_dump -U rag_user -d rag_bidding_v2 -F c -f rag_bidding_backup.dump

# Backup only data
pg_dump -U rag_user -d rag_bidding_v2 -F c -f rag_bidding_data.dump --data-only

# Compressed backup
pg_dump -U rag_user -d rag_bidding_v2 | gzip > rag_bidding_backup.sql.gz
```

#### Restore Database

```bash
# Restore from custom format
pg_restore -U rag_user -d rag_bidding_v2 -c rag_bidding_backup.dump

# Restore from SQL
gunzip < rag_bidding_backup.sql.gz | psql -U rag_user -d rag_bidding_v2
```

### Monitoring

#### Check Database Size

```sql
SELECT pg_size_pretty(pg_database_size('rag_bidding_v2'));
```

#### Check Table Bloat

```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS indexes_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

#### Monitor Queries

```sql
-- Enable query logging
ALTER DATABASE rag_bidding_v2 SET log_min_duration_statement = 1000; -- Log queries > 1s

-- View slow queries
SELECT 
    pid,
    now() - query_start as duration,
    query,
    state
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC;
```

---

## 📚 ADDITIONAL RESOURCES

### Documentation

- [PostgreSQL Official Docs](https://www.postgresql.org/docs/18/)
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [LangChain PostgreSQL Integration](https://python.langchain.com/docs/integrations/vectorstores/pgvector)

### Related Files

- [`setup_db.sh`](../../setup_db.sh) - Automated database setup script
- [`environment.yaml`](../../environment.yaml) - Conda environment specification
- [`scripts/bootstrap_db.py`](../../scripts/bootstrap_db.py) - Database bootstrap script
- [`scripts/import_processed_chunks.py`](../../scripts/import_processed_chunks.py) - Data import script
- [`scripts/batch_reprocess_all.py`](../../scripts/batch_reprocess_all.py) - Batch processing script

### Support

For issues and questions:
1. Check [Troubleshooting](#troubleshooting) section
2. Review GitHub Issues
3. Check project documentation in `documents/`

---

**Last Updated:** November 4, 2025  
**Maintained by:** RAG Bidding Team  
**Status:** ✅ Production Ready
