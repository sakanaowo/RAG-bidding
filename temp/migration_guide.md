# 🎯 Database Migration Quick Guide

**Generated:** 2025-11-25  
**Database:** rag_bidding_v2 (64 docs, 7,892 chunks, 149 MB)

---

## ✅ Dump Created Successfully!

### 📦 Files Available

```
backup/exports/
├── rag_bidding_v2_20251125_155647.dump         (119 MB) ⭐ RECOMMENDED
├── rag_bidding_v2_20251125_155647.sql.gz       (118 MB)
├── rag_bidding_v2_20251125_155647_schema.sql   (8 KB)
└── rag_bidding_v2_20251125_155647_README.txt   (Full instructions)
```

### 🎯 Which File to Use?

| File | Best For | Pros | Cons |
|------|----------|------|------|
| **.dump** ⭐ | Production migration | Fast, reliable, compressed | Requires pg_restore |
| **.sql.gz** | Cross-version migration | Human-readable, version-independent | Larger, slower |
| **_schema.sql** | Schema reference only | Quick setup | No data |

---

## 🚀 Quick Transfer Commands

### Option 1: SCP (Simple)
```bash
# On source machine
scp backup/exports/rag_bidding_v2_20251125_155647.dump user@target:/tmp/

# Also send README
scp backup/exports/rag_bidding_v2_20251125_155647_README.txt user@target:/tmp/
```

### Option 2: rsync (Resumable, Better for large files)
```bash
rsync -avz --progress \
  backup/exports/rag_bidding_v2_20251125_155647.dump \
  user@target:/tmp/
```

### Option 3: Archive All Files
```bash
# Create archive
cd backup/exports
tar -czf rag_bidding_backup_20251125.tar.gz rag_bidding_v2_20251125_155647*

# Transfer
scp rag_bidding_backup_20251125.tar.gz user@target:/tmp/

# On target, extract
tar -xzf rag_bidding_backup_20251125.tar.gz
```

---

## 🎯 Restore on Target Machine (Automated Script)

### Method 1: Using restore_dump.sh Script ⭐

```bash
# 1. Clone repository on target
git clone https://github.com/sakanaowo/RAG-bidding.git
cd RAG-bidding

# 2. Setup environment
conda env create -f environment.yaml
conda activate venv

# 3. Copy dump file to backup/exports/
mkdir -p backup/exports
cp /tmp/rag_bidding_v2_20251125_155647.dump backup/exports/

# 4. Create .env file
cp .env.example .env
nano .env  # Update DATABASE_URL and credentials

# 5. Run restore script
./scripts/restore_dump.sh backup/exports/rag_bidding_v2_20251125_155647.dump
```

**Script will automatically:**
- ✅ Check PostgreSQL connection
- ✅ Verify pgvector extension
- ✅ Drop existing database (with confirmation)
- ✅ Create new database
- ✅ Restore all data
- ✅ Grant permissions
- ✅ Verify restoration

---

## 🛠️ Manual Restore (Step by Step)

### Prerequisites
```bash
# Install PostgreSQL 18
sudo apt update
sudo apt install -y postgresql-18 postgresql-contrib-18

# Install pgvector
sudo apt install -y postgresql-18-pgvector
```

### Step 1: Create Database
```bash
# As postgres user
sudo -u postgres createdb rag_bidding_v2

# Enable pgvector
sudo -u postgres psql -d rag_bidding_v2 -c "CREATE EXTENSION vector;"
```

### Step 2: Restore Dump
```bash
# Using .dump file (RECOMMENDED)
sudo -u postgres pg_restore \
  -d rag_bidding_v2 \
  -v \
  /tmp/rag_bidding_v2_20251125_155647.dump

# OR using .sql.gz file
gunzip -c /tmp/rag_bidding_v2_20251125_155647.sql.gz | \
  sudo -u postgres psql -d rag_bidding_v2
```

### Step 3: Grant Permissions
```bash
sudo -u postgres psql -d rag_bidding_v2 << 'SQL'
-- Create user if not exists
CREATE USER sakana WITH PASSWORD 'sakana123';

-- Grant permissions
GRANT ALL ON DATABASE rag_bidding_v2 TO sakana;
GRANT ALL ON SCHEMA public TO sakana;
GRANT ALL ON ALL TABLES IN SCHEMA public TO sakana;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO sakana;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO sakana;
SQL
```

### Step 4: Verify
```bash
psql -U sakana -d rag_bidding_v2 -h localhost << 'SQL'
-- Check extensions
\dx

-- Check tables
\dt

-- Check data counts
SELECT COUNT(*) as documents FROM documents;
SELECT COUNT(*) as chunks FROM langchain_pg_embedding;
SELECT pg_size_pretty(pg_database_size('rag_bidding_v2')) as size;
SQL
```

Expected output:
```
 documents 
-----------
        64

 chunks 
--------
   7892

  size   
---------
 149 MB
```

---

## ⚙️ Application Setup on Target

### 1. Update .env File
```bash
nano .env
```

Required variables:
```bash
# Database
DATABASE_URL=postgresql+psycopg://sakana:sakana123@localhost:5432/rag_bidding_v2
DB_USER=sakana
DB_PASSWORD=sakana123
DB_NAME=rag_bidding_v2
DB_HOST=localhost
DB_PORT=5432

# OpenAI API
OPENAI_API_KEY=sk-your-key-here

# Models
EMBED_MODEL=text-embedding-3-large
LLM_MODEL=gpt-4o-mini

# Cache (optional)
ENABLE_REDIS_CACHE=true
REDIS_HOST=localhost
REDIS_PORT=6379
```

### 2. Install Redis (Optional but Recommended)
```bash
sudo apt install -y redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### 3. Test Connection
```bash
# Activate environment
conda activate venv

# Test database connection
python -c "from src.config.models import settings; print(settings.database_url)"

# Test import
python -c "from src.embedding.store.pgvector_store import vector_store; print('✅ Connection OK')"
```

### 4. Start Server
```bash
./start_server.sh

# Or manually
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Verify API
```bash
# Health check
curl http://localhost:8000/health
# Expected: {"db": true}

# System stats
curl http://localhost:8000/stats

# Test query
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Test query", "mode": "fast"}'
```

---

## 🔍 Troubleshooting

### Issue: Cannot connect to database
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check port is listening
sudo netstat -tulpn | grep 5432

# Check pg_hba.conf
sudo nano /etc/postgresql/18/main/pg_hba.conf
# Ensure: host all all 127.0.0.1/32 md5
```

### Issue: pgvector extension not found
```bash
# Install pgvector
sudo apt install postgresql-18-pgvector

# Verify available
psql -U postgres -c "SELECT * FROM pg_available_extensions WHERE name = 'vector';"

# Enable in database
psql -U postgres -d rag_bidding_v2 -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Issue: Permission denied
```bash
# Re-grant permissions
sudo -u postgres psql -d rag_bidding_v2 << 'SQL'
GRANT ALL ON SCHEMA public TO sakana;
GRANT ALL ON ALL TABLES IN SCHEMA public TO sakana;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO sakana;
SQL
```

### Issue: Different database size after restore
```bash
# Run ANALYZE to update statistics
psql -U sakana -d rag_bidding_v2 -c "ANALYZE;"

# Run VACUUM to reclaim space
psql -U sakana -d rag_bidding_v2 -c "VACUUM FULL;"
```

---

## 📋 Checklist

### On Source Machine ✅
- [x] Database dump created (119 MB)
- [x] README with instructions included
- [x] Files ready for transfer

### On Target Machine ⬜
- [ ] PostgreSQL 18+ installed
- [ ] pgvector extension installed
- [ ] Database restored
- [ ] Permissions granted
- [ ] .env file configured
- [ ] Conda environment created
- [ ] Dependencies installed
- [ ] API server running
- [ ] Health check passing

---

## 📚 Related Documentation

- **Full Setup Guide:** `SETUP_ENVIRONMENT_DATABASE.md`
- **Database Schema:** `temp/database_schema_explained.txt`
- **System Architecture:** `temp/system_architecture.txt`
- **Restore README:** `backup/exports/rag_bidding_v2_20251125_155647_README.txt`

---

## ⏱️ Estimated Timeline

| Task | Time |
|------|------|
| Transfer dump (119 MB) | 1-5 min (depends on network) |
| Install PostgreSQL | 5-10 min |
| Restore database | 2-3 min |
| Setup environment | 5-10 min |
| Install dependencies | 10-15 min |
| **Total** | **~30-45 min** |

---

**Last Updated:** 2025-11-25  
**Dump Timestamp:** 20251125_155647  
**Source Database:** rag_bidding_v2 (localhost:5432)
