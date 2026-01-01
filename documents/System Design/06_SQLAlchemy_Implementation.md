# SQLAlchemy Implementation Guide

## 📦 Installation

```bash
# Install required packages
pip install sqlalchemy psycopg pgvector alembic

# Or add to requirements.txt:
sqlalchemy==2.0.23
psycopg[binary]==3.1.13
pgvector==0.2.4
alembic==1.13.0
```

## 🏗️ Cấu trúc Project

```
RAG-bidding/
├── src/
│   └── models/
│       ├── __init__.py           # Package exports
│       ├── base.py               # Database engine & session
│       ├── documents.py          # Document model
│       ├── embeddings.py         # Embedding models
│       ├── repositories.py       # Query helpers
│       └── db_utils.py          # Init & migration utils
├── alembic/
│   ├── env.py                   # Alembic environment
│   ├── versions/                # Migration files
│   └── script.py.mako          # Migration template
├── alembic.ini                  # Alembic config
└── scripts/
    └── setup_alembic.py        # Setup automation
```

## 🚀 Quick Start

### 1. Cài đặt dependencies

```bash
conda activate venv
pip install sqlalchemy psycopg pgvector alembic
```

### 2. Verify database connection

```python
from src.models.base import engine, SessionLocal
from src.models.db_utils import verify_schema, get_database_stats

# Test connection
with SessionLocal() as db:
    print("✅ Database connected")

# Check current schema
verify_schema()

# Get stats
stats = get_database_stats()
print(stats)
```

### 3. Setup Alembic migrations

```bash
# Initialize (already configured)
python scripts/setup_alembic.py init

# Create initial migration from current schema
python scripts/setup_alembic.py create

# Review migration in alembic/versions/
# Then apply:
python scripts/setup_alembic.py upgrade

# Check status
python scripts/setup_alembic.py status
```

## 📝 Usage Examples

### Basic CRUD Operations

```python
from src.models.base import SessionLocal
from src.models.documents import Document
from src.models.repositories import DocumentRepository

# Create session
db = SessionLocal()

try:
    # CREATE
    new_doc = DocumentRepository.create(
        db,
        document_id="doc_new_001",
        document_name="Nghị định mới 2025",
        category="legal",
        document_type="decree",
        source_file="/data/processed/new_decree.json",
        file_name="new_decree.pdf",
        total_chunks=50,
        status="processing"
    )
    print(f"Created: {new_doc.document_id}")

    # READ
    doc = DocumentRepository.get_by_id(db, "doc_new_001")
    print(f"Found: {doc.document_name}")

    # LIST with filters
    laws = DocumentRepository.get_all(
        db,
        document_type="law",
        status="active",
        limit=10
    )
    print(f"Found {len(laws)} active laws")

    # UPDATE
    updated = DocumentRepository.update(
        db,
        "doc_new_001",
        status="active",
        total_chunks=55
    )
    print(f"Updated status: {updated.status}")

    # DELETE (soft)
    DocumentRepository.delete(db, "doc_new_001", soft=True)

    # SEARCH
    results = DocumentRepository.search(db, "nghị định")
    print(f"Search found {len(results)} results")

    # STATS
    stats = DocumentRepository.get_stats(db)
    print(f"Total documents: {stats['total_documents']}")
    print(f"By type: {stats['by_type']}")

finally:
    db.close()
```

### Using with FastAPI Dependency Injection

```python
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from src.models.base import get_db
from src.models.repositories import DocumentRepository

app = FastAPI()

@app.get("/documents")
def list_documents(
    skip: int = 0,
    limit: int = 100,
    document_type: str = None,
    db: Session = Depends(get_db)
):
    """List documents with pagination"""
    docs = DocumentRepository.get_all(
        db,
        skip=skip,
        limit=limit,
        document_type=document_type
    )
    return [doc.to_dict() for doc in docs]

@app.get("/documents/{document_id}")
def get_document(document_id: str, db: Session = Depends(get_db)):
    """Get single document"""
    doc = DocumentRepository.get_by_id(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc.to_dict()

@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get document statistics"""
    return DocumentRepository.get_stats(db)
```

### Query Embeddings

```python
from src.models.embeddings import LangchainPGEmbedding
from sqlalchemy import select, func

db = SessionLocal()

# Get all chunks for a document
chunks = db.query(LangchainPGEmbedding).filter(
    LangchainPGEmbedding.cmetadata['document_id'].astext == 'doc_001'
).all()

print(f"Document has {len(chunks)} chunks")

# Filter by document type
law_chunks = db.query(LangchainPGEmbedding).filter(
    LangchainPGEmbedding.cmetadata['document_type'].astext == 'law'
).limit(10).all()

# Get chunk with specific index
chunk = db.query(LangchainPGEmbedding).filter(
    LangchainPGEmbedding.cmetadata['chunk_id'].astext == 'doc_001_chunk_005'
).first()

if chunk:
    print(f"Content: {chunk.document[:100]}...")
    print(f"Metadata: {chunk.cmetadata}")

db.close()
```

## 🔧 Migration Workflow

### Creating New Migrations

```bash
# After modifying models, create migration
alembic revision --autogenerate -m "Add users table"

# Review generated file in alembic/versions/
# Make manual adjustments if needed

# Apply migration
alembic upgrade head

# Rollback one version
alembic downgrade -1

# Check current version
alembic current

# View history
alembic history --verbose
```

### Manual Migration Example

```bash
# Create empty migration
alembic revision -m "Add vector index"

# Edit the file and add:
```

```python
def upgrade():
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_embedding_hnsw
        ON langchain_pg_embedding
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_embedding_hnsw")
```

## 🎯 Integration với Existing Code

### Replace direct psycopg queries

**Before:**

```python
import psycopg
conn = psycopg.connect("...")
cursor = conn.cursor()
cursor.execute("SELECT * FROM documents WHERE status = 'active'")
results = cursor.fetchall()
```

**After:**

```python
from src.models.base import SessionLocal
from src.models.repositories import DocumentRepository

db = SessionLocal()
results = DocumentRepository.get_all(db, status="active")
```

### Use with LangChain PGVector (No change needed!)

```python
from langchain_postgres import PGVector
from src.models.base import DATABASE_URL

# LangChain sẽ tự động sử dụng existing tables
vector_store = PGVector(
    connection=DATABASE_URL,
    collection_name="docs",
    embeddings=embeddings,
    # SQLAlchemy models đã define schema
)
```

## 🐛 Debugging

### Enable SQL logging

```python
# In src/models/base.py, change:
engine = create_engine(
    DATABASE_URL,
    echo=True,  # Print all SQL queries
)
```

### Check connection pool

```python
from src.models.base import engine

print(f"Pool size: {engine.pool.size()}")
print(f"Checked out: {engine.pool.checkedout()}")
print(f"Overflow: {engine.pool.overflow()}")
```

### Inspect schema

```python
from src.models.db_utils import verify_schema, get_database_stats

verify_schema()
stats = get_database_stats()
print(stats)
```

## ⚠️ Best Practices

1. **Always use sessions with context manager:**

   ```python
   with SessionLocal() as db:
       # Do work
       pass  # Auto-close
   ```

2. **Use FastAPI dependency injection:**

   ```python
   def endpoint(db: Session = Depends(get_db)):
       # db auto-closes after request
   ```

3. **Use Repository pattern for complex queries**

   - Keep business logic in repositories
   - Models only define schema

4. **Use Alembic for schema changes**

   - Never modify production DB manually
   - Always create migrations
   - Test migrations on staging first

5. **Handle errors properly:**
   ```python
   try:
       db.add(obj)
       db.commit()
   except Exception as e:
       db.rollback()
       raise
   finally:
       db.close()
   ```

## 🚀 Next Steps

1. **Install dependencies:**

   ```bash
   pip install sqlalchemy psycopg pgvector alembic
   ```

2. **Test connection:**

   ```bash
   python -c "from src.models.db_utils import verify_schema; verify_schema()"
   ```

3. **Create initial migration:**

   ```bash
   python scripts/setup_alembic.py create
   ```

4. **Update API to use ORM:**

   - Replace raw SQL with Repository methods
   - Use `get_db()` dependency in FastAPI routes

5. **Add future models (v2.1+):**
   - Create `src/models/users.py`
   - Create migration with `alembic revision --autogenerate`
   - Apply with `alembic upgrade head`

## 📚 References

- [SQLAlchemy 2.0 Docs](https://docs.sqlalchemy.org/en/20/)
- [Alembic Docs](https://alembic.sqlalchemy.org/)
- [pgvector-python](https://github.com/pgvector/pgvector-python)
- [FastAPI with SQLAlchemy](https://fastapi.tiangolo.com/tutorial/sql-databases/)
