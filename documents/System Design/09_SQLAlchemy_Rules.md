# ⚡ SQLAlchemy Quick Rules - MUST FOLLOW

## 🔴 CRITICAL - Always Do These

### 1. Wrap Raw SQL với text()

```python
from sqlalchemy import text
db.execute(text("SELECT 1"))  # ✅
db.execute("SELECT 1")        # ❌ FAILS in SQLAlchemy 2.0+
```

### 2. Add sys.path Before Imports

```python
import sys
from pathlib import Path

# Calculate based on file location:
# scripts/*.py → parent.parent
# scripts/examples/*.py → parent.parent.parent
# scripts/tests/*.py → parent.parent.parent

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.models.base import SessionLocal
```

### 3. Use Context Manager for Sessions

```python
# ✅ CORRECT
with SessionLocal() as db:
    docs = db.query(Document).all()
    # auto-close

# ❌ WRONG - Session leak
db = SessionLocal()
docs = db.query(Document).all()
# forgot to close!
```

### 4. FastAPI: Use Depends(get_db)

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from src.models.base import get_db

@app.get("/endpoint")
def endpoint(db: Session = Depends(get_db)):
    # db auto-closes after request
    return DocumentRepository.get_all(db)
```

### 5. Always Rollback on Error

```python
try:
    db.add(obj)
    db.commit()
    db.refresh(obj)
except Exception as e:
    db.rollback()  # ✅ CRITICAL
    raise
finally:
    db.close()
```

## ⚠️ Common Mistakes

### ❌ WRONG: No text() wrapper

```python
db.execute("SELECT COUNT(*) FROM documents")
# Error: Textual SQL expression should be explicitly declared as text()
```

### ❌ WRONG: Missing sys.path

```python
from src.models.base import SessionLocal
# Error: ModuleNotFoundError: No module named 'src'
```

### ❌ WRONG: Session leak

```python
@app.get("/docs")
def get_docs():
    db = SessionLocal()
    return db.query(Document).all()
    # db never closed! Memory leak!
```

### ❌ WRONG: pgvector version check

```python
import pgvector
print(pgvector.__version__)
# Error: AttributeError: module 'pgvector' has no attribute '__version__'
```

### ❌ WRONG: No rollback

```python
try:
    db.commit()
except:
    pass  # ❌ Should rollback!
```

## ✅ Best Practices

### Use Repository Pattern

```python
from src.models.repositories import DocumentRepository

# ✅ Clean, reusable
docs = DocumentRepository.get_all(db, status="active")

# ⚠️ OK but less maintainable
docs = db.query(Document).filter(Document.status == "active").all()
```

### Alembic for Schema Changes

```bash
# ✅ CORRECT
alembic revision --autogenerate -m "Add column"
alembic upgrade head

# ❌ WRONG - Direct SQL in production
psql -c "ALTER TABLE documents ADD COLUMN x TEXT"
```

### Test Before Commit

```bash
# Run these before committing database changes:
python scripts/test_db_connection.py
python scripts/examples/sqlalchemy_usage.py
```

## 📁 File Locations

- Database tests → `scripts/tests/test_db_*.py`
- API tests → `scripts/tests/test_api_*.py`
- Examples → `scripts/examples/example_*.py`
- Utilities → `scripts/*.py`

## 🆘 Quick Debug

```bash
# Test connection
python scripts/test_db_connection.py

# Run examples
python scripts/examples/sqlalchemy_usage.py

# Check packages
pip list | grep -E "(sqlalchemy|psycopg|pgvector)"
```

## 📖 Full Documentation

- **Quick Start**: `QUICKSTART_ORM.md`
- **Roadmap**: `documents/System Design/07_SQLAlchemy_Roadmap.md`
- **Usage Guide**: `documents/System Design/06_SQLAlchemy_Implementation.md`
- **Rules**: `.github/copilot-instructions.md` (Section: SQLAlchemy & Database)

---

**Print this and stick on your monitor! 📌**
