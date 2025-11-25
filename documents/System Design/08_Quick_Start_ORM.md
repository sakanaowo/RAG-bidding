# 🚀 Quick Start - SQLAlchemy Implementation

## ⚡ TL;DR - Làm ngay

```bash
# 1. Cài đặt (1 phút)
conda activate venv
pip install sqlalchemy psycopg pgvector alembic

# 2. Test (30 giây)
./scripts/test_sqlalchemy.sh

# 3. Chạy examples (1 phút)
python scripts/examples/sqlalchemy_usage.py
```

## 📁 Đã tạo gì?

### Models (`/src/models/`)

```
src/models/
├── __init__.py         # Package exports
├── base.py            # Database engine & session
├── documents.py       # Document model
├── embeddings.py      # Embedding models
├── repositories.py    # Query helpers
└── db_utils.py       # Init & verification
```

### Alembic (`/alembic/`)

```
alembic/
├── env.py            # Alembic config
├── versions/         # Migration files (empty)
└── script.py.mako   # Migration template
alembic.ini           # Alembic settings
```

### Scripts

```
scripts/
├── setup_alembic.py           # Setup automation
├── test_sqlalchemy.sh         # Quick test script
└── examples/
    └── sqlalchemy_usage.py    # 6 usage examples
```

### Documentation

```
documents/System Design/
├── 06_SQLAlchemy_Implementation.md  # Usage guide
└── 07_SQLAlchemy_Roadmap.md        # Step-by-step setup
```

## 💡 Sử dụng ngay

### FastAPI Endpoint

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from src.models.base import get_db
from src.models.repositories import DocumentRepository

@app.get("/documents")
def list_documents(db: Session = Depends(get_db)):
    docs = DocumentRepository.get_all(db, limit=100)
    return [doc.to_dict() for doc in docs]
```

### Basic Query

```python
from src.models.base import SessionLocal
from src.models.repositories import DocumentRepository

db = SessionLocal()
try:
    # Get all active documents
    docs = DocumentRepository.get_all(db, status="active")

    # Search
    results = DocumentRepository.search(db, "luật")

    # Stats
    stats = DocumentRepository.get_stats(db)
    print(f"Total: {stats['total_documents']}")

finally:
    db.close()
```

## 📖 Đọc tiếp

### Ngay bây giờ

1. **Test connection**: `./scripts/test_sqlalchemy.sh`
2. **Chạy examples**: `python scripts/examples/sqlalchemy_usage.py`

### Tiếp theo

1. **Setup guide**: `documents/System Design/07_SQLAlchemy_Roadmap.md`
2. **Usage guide**: `documents/System Design/06_SQLAlchemy_Implementation.md`

## ✅ Checklist

- [x] Install SQLAlchemy, psycopg, pgvector, alembic
- [x] Create models (documents, embeddings)
- [x] Create repository pattern
- [x] Setup Alembic config
- [ ] **Test connection** ← **START HERE**
- [ ] Create initial migration
- [ ] Integrate with FastAPI
- [ ] Replace raw SQL queries

## 🆘 Có lỗi?

```bash
# Check packages
pip list | grep -E "(sqlalchemy|psycopg|pgvector|alembic)"

# Test DB connection
python -c "from src.models.base import SessionLocal; db = SessionLocal(); print('✅ OK'); db.close()"

# Run examples để xem lỗi chi tiết
python scripts/examples/sqlalchemy_usage.py
```

## 📞 Next Step

**Chạy ngay:**

```bash
./scripts/test_sqlalchemy.sh
```

**Đọc chi tiết:**

- `documents/System Design/07_SQLAlchemy_Roadmap.md` (implementation plan)
- `documents/System Design/06_SQLAlchemy_Implementation.md` (usage guide)

---

**Created:** 25/11/2025  
**Quick Reference for:** RAG Bidding System - SQLAlchemy ORM Implementation
