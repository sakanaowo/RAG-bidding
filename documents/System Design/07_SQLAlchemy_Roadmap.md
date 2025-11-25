# 🚀 SQLAlchemy Implementation Roadmap

## Tổng quan

Triển khai SQLAlchemy ORM cho RAG Bidding System để:

- ✅ Quản lý database schema với type safety
- ✅ Migration tự động với Alembic
- ✅ Code dễ maintain và test hơn raw SQL
- ✅ Tích hợp tốt với FastAPI

---

## 📦 Bước 1: Cài đặt Dependencies (5 phút)

```bash
conda activate venv

# Install core packages
pip install sqlalchemy==2.0.23
pip install psycopg[binary]==3.1.13  # PostgreSQL adapter
pip install pgvector==0.2.4          # Vector type support
pip install alembic==1.13.0          # Migration tool

# Verify installation
python -c "import sqlalchemy; print(sqlalchemy.__version__)"
python -c "import psycopg; print(psycopg.__version__)"
python -c "import pgvector; print(pgvector.__version__)"
python -c "import alembic; print(alembic.__version__)"
```

**Expected output:**

```
2.0.23
3.1.13
0.2.4
1.13.0
```

---

## 📁 Bước 2: Verify File Structure (2 phút)

Kiểm tra các file đã tạo:

```bash
# Models
ls -la src/models/
# Should see:
# - __init__.py
# - base.py
# - documents.py
# - embeddings.py
# - repositories.py
# - db_utils.py

# Alembic
ls -la alembic/
# Should see:
# - env.py
# - versions/

# Scripts
ls -la scripts/
# Should see:
# - setup_alembic.py
# - test_sqlalchemy.sh
# - examples/sqlalchemy_usage.py
```

---

## 🧪 Bước 3: Test Database Connection (5 phút)

### 3.1. Quick test

```bash
# Run automated test script
./scripts/test_sqlalchemy.sh
```

### 3.2. Manual verification

```python
# Test connection
python -c "
from src.models.base import SessionLocal, engine

# Test engine
print('Testing engine...')
with engine.connect() as conn:
    result = conn.execute('SELECT 1')
    print(f'✅ Engine works: {result.scalar()}')

# Test session
print('Testing session...')
with SessionLocal() as db:
    result = db.execute('SELECT COUNT(*) FROM documents').scalar()
    print(f'✅ Found {result} documents')
"
```

### 3.3. Verify schema

```python
python -c "
from src.models.db_utils import verify_schema, get_database_stats

# Check schema
print('Verifying schema...')
verify_schema()

# Get stats
print('\nDatabase stats:')
import json
stats = get_database_stats()
print(json.dumps(stats, indent=2, default=str))
"
```

**Expected output:**

```json
{
  "total_documents": 64,
  "total_embeddings": 7892,
  "database_size": "149 MB",
  "document_types": [
    {"type": "bidding_form", "count": 37},
    {"type": "law", "count": 6},
    ...
  ]
}
```

---

## 🔄 Bước 4: Setup Alembic Migrations (10 phút)

### 4.1. Initialize Alembic (done)

```bash
# Already configured, just verify
python scripts/setup_alembic.py init
```

### 4.2. Create initial migration

```bash
# Generate migration from current schema
python scripts/setup_alembic.py create
# Or manually:
alembic revision --autogenerate -m "Initial schema with documents and embeddings"
```

**Expected output:**

```
Generating alembic/versions/20251125_1234_5678abc_initial_schema.py
  - Detected table documents
  - Detected table langchain_pg_embedding
  - Detected table langchain_pg_collection
  - Detected indexes
Done
```

### 4.3. Review migration

```bash
# Open the generated file
code alembic/versions/202511*.py

# Should contain:
# - create_table('documents')
# - create_table('langchain_pg_embedding')
# - create_table('langchain_pg_collection')
# - create indexes
```

### 4.4. Apply migration (mark as applied)

```bash
# Mark current schema as baseline
alembic stamp head

# Check status
python scripts/setup_alembic.py status
# Or:
alembic current
```

**Expected output:**

```
Current revision: 5678abc (head)
Database is up to date
```

---

## 🎯 Bước 5: Test ORM Operations (10 phút)

### 5.1. Run example script

```bash
# Run all examples
python scripts/examples/sqlalchemy_usage.py
```

### 5.2. Test individual operations

```python
# Test basic CRUD
python -c "
from src.models.base import SessionLocal
from src.models.repositories import DocumentRepository

db = SessionLocal()

# Get all documents
docs = DocumentRepository.get_all(db, limit=5)
print(f'Found {len(docs)} documents:')
for doc in docs:
    print(f'  - {doc.document_name} ({doc.document_type})')

# Get stats
stats = DocumentRepository.get_stats(db)
print(f'\nTotal: {stats[\"total_documents\"]}')
print(f'By type: {stats[\"by_type\"]}')

db.close()
"
```

### 5.3. Test embedding queries

```python
python -c "
from src.models.base import SessionLocal
from src.models.embeddings import LangchainPGEmbedding

db = SessionLocal()

# Count embeddings
total = db.query(LangchainPGEmbedding).count()
print(f'Total embeddings: {total}')

# Get sample chunk
chunk = db.query(LangchainPGEmbedding).first()
if chunk:
    print(f'\nSample chunk:')
    print(f'  ID: {chunk.id}')
    print(f'  Content: {chunk.document[:100]}...')
    print(f'  Metadata: {chunk.cmetadata}')

db.close()
"
```

---

## 🔌 Bước 6: Integrate với FastAPI (15 phút)

### 6.1. Update API imports

```python
# In src/api/ask.py, src/api/upload.py, etc.
# Add at the top:

from sqlalchemy.orm import Session
from src.models.base import get_db
from src.models.repositories import DocumentRepository
```

### 6.2. Add dependency to routes

```python
# Example endpoint
from fastapi import Depends

@router.get("/documents")
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    document_type: str = None,
    db: Session = Depends(get_db)  # 👈 Add this
):
    """List documents with pagination"""
    docs = DocumentRepository.get_all(
        db,
        skip=skip,
        limit=limit,
        document_type=document_type
    )
    return [doc.to_dict() for doc in docs]
```

### 6.3. Replace raw SQL queries

**Before:**

```python
import psycopg
conn = psycopg.connect(...)
cursor = conn.cursor()
cursor.execute("SELECT * FROM documents WHERE status = 'active'")
results = cursor.fetchall()
```

**After:**

```python
from sqlalchemy.orm import Session
from src.models.base import get_db
from src.models.repositories import DocumentRepository

def my_function(db: Session = Depends(get_db)):
    results = DocumentRepository.get_all(db, status="active")
    return results
```

### 6.4. Test API with ORM

```bash
# Start server
./start_server.sh

# Test in another terminal
curl http://localhost:8000/documents?limit=5
curl http://localhost:8000/stats
```

---

## 📊 Bước 7: Verify Performance (5 phút)

### 7.1. Enable SQL logging (debug)

```python
# In src/models/base.py, temporarily set:
engine = create_engine(
    DATABASE_URL,
    echo=True,  # 👈 Enable SQL logging
)
```

### 7.2. Check query performance

```python
import time
from src.models.base import SessionLocal
from src.models.repositories import DocumentRepository

db = SessionLocal()

# Benchmark query
start = time.time()
docs = DocumentRepository.get_all(db, limit=100)
elapsed = time.time() - start

print(f"Query took {elapsed*1000:.2f}ms for {len(docs)} documents")
# Expected: < 10ms

db.close()
```

### 7.3. Monitor connection pool

```python
from src.models.base import engine

print(f"Pool size: {engine.pool.size()}")
print(f"Checked out: {engine.pool.checkedout()}")
print(f"Overflow: {engine.pool.overflow()}")

# Expected:
# Pool size: 10
# Checked out: 0 (when idle)
# Overflow: 0 (when idle)
```

---

## 🚀 Bước 8: Production Deployment

### 8.1. Update requirements.txt

```bash
# Add to requirements.txt
echo "sqlalchemy==2.0.23" >> requirements.txt
echo "psycopg[binary]==3.1.13" >> requirements.txt
echo "pgvector==0.2.4" >> requirements.txt
echo "alembic==1.13.0" >> requirements.txt
```

### 8.2. Create deployment migration script

```bash
# scripts/deploy_migrations.sh
#!/bin/bash
set -e

echo "Running database migrations..."

# Backup database first
pg_dump $DATABASE_URL > backup/pre_migration_$(date +%Y%m%d_%H%M%S).sql

# Run migrations
alembic upgrade head

# Verify
alembic current

echo "✅ Migrations applied successfully"
```

### 8.3. Update deployment docs

Add to deployment guide:

```markdown
## Database Migration

Before deploying new version:

1. Backup database: `./scripts/create_dump.sh`
2. Apply migrations: `alembic upgrade head`
3. Verify schema: `alembic current`
4. Test application
```

---

## 📝 Checklist

### Phase 1: Setup (CURRENT)

- [x] Install SQLAlchemy, psycopg, pgvector, alembic
- [x] Create models (documents, embeddings)
- [x] Create repository pattern
- [x] Setup Alembic configuration
- [ ] Test database connection ← **START HERE**
- [ ] Create initial migration
- [ ] Run example scripts

### Phase 2: Integration (NEXT)

- [ ] Add `get_db()` dependency to FastAPI routes
- [ ] Replace raw SQL with Repository methods
- [ ] Test API endpoints with ORM
- [ ] Monitor performance
- [ ] Update documentation

### Phase 3: Future Features (v2.1+)

- [ ] Create User model
- [ ] Create ChatSession/ChatMessage models
- [ ] Create QueryLog model
- [ ] Migrate Redis sessions to PostgreSQL
- [ ] Add full-text search indexes
- [ ] Setup connection pooling (pgBouncer)

---

## 🆘 Troubleshooting

### Import errors

```bash
# Make sure packages are installed
pip list | grep -E "(sqlalchemy|psycopg|pgvector|alembic)"

# Reinstall if needed
pip install --force-reinstall sqlalchemy psycopg pgvector alembic
```

### Connection errors

```bash
# Test PostgreSQL connection
PGPASSWORD=sakana123 psql -U sakana -h localhost -d rag_bidding_v2 -c "SELECT 1"

# Check .env file
cat .env | grep DATABASE_URL
```

### Alembic errors

```bash
# Reset Alembic (only in dev!)
rm -rf alembic/versions/*.py
alembic revision --autogenerate -m "Initial schema"

# Stamp current schema
alembic stamp head
```

### Performance issues

```python
# Enable SQL logging to debug slow queries
from src.models.base import engine
engine.echo = True

# Check connection pool
print(engine.pool.status())
```

---

## 📚 Next Steps

1. **Run tests**: `./scripts/test_sqlalchemy.sh`
2. **Review examples**: `python scripts/examples/sqlalchemy_usage.py`
3. **Create migration**: `python scripts/setup_alembic.py create`
4. **Update API**: Add `Depends(get_db)` to routes
5. **Deploy**: Follow deployment guide

---

## 📖 References

- [SQLAlchemy 2.0 Tutorial](https://docs.sqlalchemy.org/en/20/tutorial/)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [FastAPI SQL Databases](https://fastapi.tiangolo.com/tutorial/sql-databases/)
- [pgvector Python](https://github.com/pgvector/pgvector-python)

---

**Created:** 25/11/2025  
**Author:** System Architecture Team  
**Version:** 1.0
