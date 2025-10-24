# Adding Document Metadata (Status & Valid Until)

## 🎯 Overview

Add `status` (active/expired) and `valid_until` metadata to existing embedded documents **without re-embedding**.

## 📊 3 Solutions

### ✅ **Solution 1: UPDATE DB Metadata (RECOMMENDED)**

**Pros:**
- ⚡ Fast (1-2 minutes)
- 💰 Free (no re-embedding cost)
- ✅ Keeps existing vectors

**Steps:**

```bash
# 1. Update metadata in PostgreSQL
python scripts/update_metadata.py

# Output:
# ✅ Update complete!
#    📝 Total updated: 846
#    ✅ Active documents: 623
#    ❌ Expired documents: 223
```

**How it works:**
- Parses year from document URL (e.g., `Luat-Dau-thau-2023`)
- Determines validity period:
  - **Luật (Law)**: 5 years
  - **Nghị định (Decree)**: 2 years
  - **Thông tư (Circular)**: 2 years
- Updates `cmetadata` JSONB field in PostgreSQL

---

### 🔄 **Solution 2: UPDATE JSONL + Re-import (SLOW)**

**Pros:**
- ✅ Keeps JSONL and DB in sync

**Cons:**
- 🐌 Slow (10-30 minutes)
- 💸 Expensive (re-embedding cost ~$5-10)

**Steps:**

```bash
# 1. Add metadata to JSONL
python scripts/add_metadata_to_chunks.py

# 2. Re-import to database (with re-embedding)
python scripts/import_chunks.py
```

**Not recommended unless:**
- You need JSONL as source of truth
- Planning to rebuild entire index anyway

---

### 🎛️ **Solution 3: Filter at Runtime (NO UPDATE)**

**Pros:**
- ⚡ Instant (no data modification)
- 🔧 Flexible (change filter anytime)

**Cons:**
- ❌ Requires metadata to exist first (use with Solution 1)
- 📉 May reduce result quality if too many filtered out

**Usage:**

```python
from src.retrieval.retrievers import BaseVectorRetriever

# Only retrieve active documents
retriever = BaseVectorRetriever(
    k=5,
    filter_status="active"  # or "expired" or None
)

# Or custom filter
retriever = BaseVectorRetriever(
    k=5,
    filter_dict={
        "status": "active",
        "dieu": "14",  # AND Điều 14
    }
)
```

---

## 🚀 **Recommended Workflow:**

### Step 1: Update DB Metadata

```bash
python scripts/update_metadata.py
```

### Step 2: Enable Filtering in Retriever

Edit `src/retrieval/retrievers/__init__.py`:

```python
def create_retriever(mode="balanced", enable_reranking=True):
    # Add filter_status="active" to only retrieve active docs
    base = BaseVectorRetriever(k=5, filter_status="active")
    
    if mode == "fast":
        return base
    
    # ... rest of code
```

### Step 3: Test

```bash
# Test API with active documents only
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Quy định về bảo đảm dự thầu", "mode": "balanced"}'
```

---

## 📋 **Metadata Schema**

```json
{
  "status": "active" | "expired",
  "valid_until": "2028-12-31",
  "title": "Luật Đấu thầu 2023",
  "url": "https://...",
  "dieu": "14",
  "khoan": 1,
  // ... other metadata
}
```

**Rules:**
- **Luật 2023**: `valid_until = 2028-12-31` (5 years)
- **Nghị định 2025**: `valid_until = 2027-12-31` (2 years)
- **Thông tư 2024**: `valid_until = 2026-12-31` (2 years)

---

## 🔍 **Verification**

```bash
# Check status distribution
python scripts/update_metadata.py

# Output shows:
# 📊 Status breakdown:
#    active: 623 documents
#    expired: 223 documents
```

---

## ⚙️ **Configuration**

Add to `config/settings.py`:

```python
class Settings(BaseSettings):
    # ... existing settings
    
    # Metadata filtering
    filter_active_only: bool = True  # Only retrieve active documents
    include_expired_for_context: bool = False  # Include expired in "quality" mode
```

Then use in retriever factory:

```python
if settings.filter_active_only:
    filter_status = "active"
else:
    filter_status = None

base = BaseVectorRetriever(k=5, filter_status=filter_status)
```

---

## 🧪 **Testing**

Test different filter scenarios:

```python
# Test 1: Active only
retriever_active = BaseVectorRetriever(k=5, filter_status="active")
docs = retriever_active.invoke("Luật Đấu thầu 2023")
# Should return only Luật 2023 (active until 2028)

# Test 2: Expired only
retriever_expired = BaseVectorRetriever(k=5, filter_status="expired")
docs = retriever_expired.invoke("Luật Đấu thầu 2013")
# Should return only Luật 2013 (expired)

# Test 3: No filter
retriever_all = BaseVectorRetriever(k=5, filter_status=None)
docs = retriever_all.invoke("Luật Đấu thầu")
# Should return both 2013 and 2023
```

---

## 📝 **Notes**

- Metadata update does **NOT** affect embeddings
- Vectors remain unchanged → No re-computation needed
- Filter is applied at **query time** (not index time)
- PGVector natively supports JSONB metadata filtering

---

## 🎯 **Next Steps**

After adding metadata:

1. ✅ **Enable filtering** in production retriever
2. ✅ **Add UI toggle** for "include expired documents"
3. ✅ **Monitor** retrieval quality with/without filter
4. ✅ **Add expiration alerts** for soon-to-expire documents
5. ✅ **Periodic sync** from JSONL if needed (Solution 2)
