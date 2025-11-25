# 🔧 Fix Log - SQLAlchemy Implementation Issues

**Ngày:** 25/11/2025  
**Status:** ✅ RESOLVED

---

## 🐛 Issues Found

### Issue 1: pgvector.**version** AttributeError ⚠️ Minor

**Error:**

```
AttributeError: module 'pgvector' has no attribute '__version__'
```

**Root Cause:**

- `pgvector` package không expose `__version__` attribute
- Test script cố gắng print version bằng `pgvector.__version__`

**Fix:**

```python
# ❌ BEFORE
print(f'✅ pgvector {pgvector.__version__}')

# ✅ AFTER - Chỉ check import
import pgvector
print(f'✅ pgvector installed')
```

**Files Changed:**

- `scripts/test_sqlalchemy.sh`

---

### Issue 2: SQLAlchemy 2.0 text() Wrapper Missing ❌ CRITICAL

**Error:**

```
Textual SQL expression 'SELECT 1' should be explicitly declared as text('SELECT 1')
```

**Root Cause:**

- SQLAlchemy 2.0+ requires ALL raw SQL phải wrap với `text()`
- Test script và nhiều files khác dùng raw string

**Fix:**

```python
# ❌ BEFORE - Fails in SQLAlchemy 2.0+
db.execute("SELECT 1")
db.execute("SELECT COUNT(*) FROM documents")

# ✅ AFTER - Proper SQLAlchemy 2.0
from sqlalchemy import text
db.execute(text("SELECT 1"))
db.execute(text("SELECT COUNT(*) FROM documents"))
```

**Files Changed:**

- `scripts/test_sqlalchemy.sh`
- `scripts/setup_alembic.py`
- Added rule to `.github/copilot-instructions.md`

**Impact:**

- 🔴 HIGH - Affects all raw SQL queries
- Required for SQLAlchemy 2.0+ compatibility

---

### Issue 3: Module Import Error - sys.path ❌ CRITICAL

**Error:**

```
ModuleNotFoundError: No module named 'src'
```

**Root Cause:**

- Scripts trong `scripts/examples/` không thêm project root vào `sys.path`
- Python không tìm thấy `src` module

**Fix:**

```python
# ❌ BEFORE
from src.models.base import SessionLocal

# ✅ AFTER - Add project root to path first
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # 2 cấp cho examples/
from src.models.base import SessionLocal
```

**Path Calculation Rules:**

- `/scripts/*.py`: `parent.parent` (lên 1 cấp)
- `/scripts/examples/*.py`: `parent.parent.parent` (lên 2 cấp)
- `/scripts/tests/*.py`: `parent.parent.parent` (lên 2 cấp)

**Files Changed:**

- `scripts/examples/sqlalchemy_usage.py`
- `scripts/setup_alembic.py`

**Impact:**

- 🔴 HIGH - All scripts using `src.*` imports failed

---

## 📋 Quy Định Mới (Added to copilot-instructions.md)

### 1. ✅ MANDATORY: text() Wrapper cho Raw SQL

```python
from sqlalchemy import text
db.execute(text("SELECT 1"))  # ALWAYS wrap raw SQL
```

### 2. ✅ MANDATORY: sys.path Setup

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

### 3. ✅ MANDATORY: Session Management

```python
# Use context manager
with SessionLocal() as db:
    # work
    pass  # auto-close
```

### 4. ✅ MANDATORY: FastAPI Dependency Injection

```python
from fastapi import Depends
from src.models.base import get_db

@app.get("/endpoint")
def endpoint(db: Session = Depends(get_db)):
    # db auto-closes after request
    pass
```

### 5. ⚠️ AVOID: pgvector.**version**

```python
# Just check import, không check version
import pgvector
print("✅ pgvector installed")
```

### 6. ✅ SHOULD: Repository Pattern

```python
from src.models.repositories import DocumentRepository
docs = DocumentRepository.get_all(db, status="active")
```

### 7. ✅ MANDATORY: Transaction Rollback

```python
try:
    db.commit()
except:
    db.rollback()
    raise
finally:
    db.close()
```

### 8. ✅ MANDATORY: Testing Location

- Database tests → `scripts/tests/test_db_*.py`
- API tests → `scripts/tests/test_api_*.py`
- Examples → `scripts/examples/example_*.py`

### 9. ✅ MANDATORY: Dependencies Update

Update `environment.yml` khi thêm package:

```yaml
dependencies:
  - sqlalchemy=2.0.23
  - psycopg=3.1.13
  - pip:
      - pgvector==0.2.4
```

### 10. ✅ MANDATORY: Alembic for Schema Changes

```bash
# Use Alembic, NOT raw SQL
alembic revision --autogenerate -m "..."
alembic upgrade head
```

---

## ✅ Testing Checklist

Trước khi commit:

- [x] `python scripts/test_db_connection.py` - PASS
- [x] `./scripts/test_sqlalchemy.sh` - PASS
- [x] `python scripts/examples/sqlalchemy_usage.py` - PASS
- [x] No SQLAlchemy warnings
- [x] Session management correct
- [x] All imports work

---

## 📊 Test Results

### Before Fix ❌

```
✅ SQLAlchemy 2.0.44
✅ psycopg 3.2.10
❌ AttributeError: module 'pgvector' has no attribute '__version__'
❌ Database connection failed: Textual SQL expression 'SELECT 1' should be...
✅ Schema verification passed (but with warnings)
❌ ModuleNotFoundError: No module named 'src'
```

### After Fix ✅

```
=== Testing SQLAlchemy Setup ===
✅ SQLAlchemy 2.0.44
✅ psycopg 3.2.10
✅ pgvector installed
✅ Alembic 1.17.2
✅ Database connection successful
✅ Schema verification passed
✅ Database stats retrieved
✅ All 6 examples passed
```

---

## 📁 Files Modified

1. **scripts/test_sqlalchemy.sh**

   - Fixed pgvector version check
   - Added `text()` wrapper for SQL

2. **scripts/examples/sqlalchemy_usage.py**

   - Fixed sys.path calculation (parent.parent.parent)

3. **scripts/setup_alembic.py**

   - Added `text` import
   - Reordered imports

4. **scripts/test_db_connection.py** (NEW)

   - Created proper test script with text() wrappers
   - Better error handling

5. **.github/copilot-instructions.md**
   - Added 10 mandatory rules
   - Added testing checklist
   - Added code examples

---

## 🎯 Lessons Learned

1. **SQLAlchemy 2.0 Breaking Change**: text() wrapper is MANDATORY

   - Affects ALL raw SQL in codebase
   - Must update old scripts

2. **Module Import Path**: Always calculate correctly

   - Different depths for different script locations
   - Use Path(**file**).parent chain

3. **Package Version Checks**: Not all packages expose **version**

   - Just check import success
   - Don't assume version attribute exists

4. **Testing is Critical**:
   - Test immediately after creating files
   - Catch errors early
   - Document rules to prevent recurrence

---

## 🚀 Next Steps

1. ✅ All tests passing
2. ✅ Rules documented in copilot-instructions.md
3. ⏳ Ready for FastAPI integration
4. ⏳ Ready to create Alembic migrations

---

**Fixed by:** System  
**Verified:** 25/11/2025 20:35 GMT+7  
**Status:** ✅ ALL ISSUES RESOLVED
