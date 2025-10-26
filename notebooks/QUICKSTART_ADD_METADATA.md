# Quick Start: Add Metadata to Embedded Documents

## 🎯 Objective
Add `status` (active/expired) and `valid_until` to existing embedded documents **without re-embedding**.

## 📓 Using Notebook (Recommended for Safety)

### Step 1: Open Notebook
```bash
cd /home/sakana/Code/RAG-bidding
jupyter notebook notebooks/add_metadata_to_db.ipynb
```

### Step 2: Run Cells in Order

**Cell 1-6: Setup and Inspection** (Safe - Read-only)
- Import libraries
- Connect to database
- Inspect schema
- View sample metadata
- Define status logic
- Test on samples

**Cell 7: DRY RUN** ⚠️ IMPORTANT
- Shows what will be updated
- NO actual changes made
- Review results carefully

**Cell 8: BULK UPDATE** 🚨 CRITICAL
- **COMMENTED OUT by default**
- Remove triple quotes to enable
- Actually updates database
- **Run ONLY after reviewing dry-run**

**Cell 9-10: Verification**
- Check update results
- View status breakdown
- Close connection

## 📊 Expected Results

After dry-run (Cell 7):
```
📊 DRY RUN RESULTS:
Total documents: 846
✅ Will mark as ACTIVE: ~623
❌ Will mark as EXPIRED: ~223
```

## ⚠️ Safety Checklist

Before running Cell 8 (bulk update):
- [ ] Dry-run results look reasonable
- [ ] Active/expired ratio makes sense (~75% active)
- [ ] No missing documents
- [ ] Database backup taken (optional but recommended)

## 🚀 Alternative: Run Script Directly

If you prefer script over notebook:

```bash
python scripts/update_metadata.py
```

**⚠️ WARNING:** Script updates immediately, no dry-run step!

## 🎛️ Enable Filtering After Update

Edit `src/retrieval/retrievers/__init__.py`:

```python
def create_retriever(mode="balanced", enable_reranking=True):
    # Add filter_status="active"
    base = BaseVectorRetriever(k=5, filter_status="active")
    # ... rest of code
```

## 🧪 Test

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Luật Đấu thầu 2023", "mode": "balanced"}'
```

Should return only active documents (Luật 2023, not 2013).

## 📝 Metadata Schema

```json
{
  "status": "active",
  "valid_until": "2028-12-31",
  "title": "Luật Đấu thầu 2023",
  "url": "https://...",
  // ... other fields
}
```

## 🔍 Verification Queries

After update, verify in psql:

```sql
-- Count by status
SELECT 
  cmetadata->>'status' as status,
  COUNT(*) 
FROM langchain_pg_embedding 
GROUP BY status;

-- Sample active documents
SELECT 
  cmetadata->>'title',
  cmetadata->>'status',
  cmetadata->>'valid_until'
FROM langchain_pg_embedding 
WHERE cmetadata->>'status' = 'active'
LIMIT 10;
```

## 💡 Tips

- **Use notebook** for first-time update (safer with dry-run)
- **Use script** for subsequent updates or automation
- **Backup database** before bulk update (optional)
- **Test retrieval** after update to verify filtering works

## 🆘 Troubleshooting

**Issue: "Collection not found"**
- Check `settings.collection` matches your collection name
- Run: `SELECT * FROM langchain_pg_collection;`

**Issue: "Connection refused"**
- Check PostgreSQL is running
- Verify `settings.database_url` in config

**Issue: "All documents already have status"**
- Metadata already updated
- Run verification queries to check

## 📚 Full Documentation

See `/docs/GUIDE/ADD_METADATA.md` for complete guide.
