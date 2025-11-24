# 📚 Database Documentation - Quick Reference

**Generated:** 2025-11-24  
**Purpose:** Quick reference cho database schema và setup

---

## 📁 Files in temp/ Directory

### 1. **database_schema_explained.txt** ⭐ MUST READ
Comprehensive guide về database schema:
- Table relationships và roles
- Detailed schema cho mỗi table
- Usage examples (SQL queries)
- Best practices
- Cache invalidation strategy
- Migration guide

**Key Points:**
- ✅ `documents` là PRIMARY table cho document management
- ⚠️ `langchain_pg_collection` là INTERNAL (LangChain only)
- ✅ `langchain_pg_embedding` lưu vector + chunks

---

### 2. **database_summary.txt**
Quick overview của database:
- Connection info
- Extensions (pgvector 0.8.1)
- Table list với mô tả
- Database statistics (64 docs, 7,892 chunks, 149 MB)
- Cache configuration (L1/L2/L3)
- Backup & restore commands

---

### 3. **system_architecture.txt**
Full system architecture documentation:
- High-level architecture diagram
- RAG pipeline modes (fast/balanced/quality/adaptive)
- Reranking architecture (BGE singleton)
- 3-tier cache architecture
- Performance benchmarks
- Production deployment checklist
- Security considerations
- Tech stack summary

---

### 4. **update_log.txt**
Log of changes made today:
- Clarified table roles
- Updated documentation files
- Database statistics collected
- Key insights về documents table

---

### 5. Supporting Files

**documents_table_schema.txt**
- Full schema của `documents` table
- Indexes, triggers, constraints
- Row count

**documents_by_type.txt**
- Breakdown of 64 documents by type
- bidding_form (37), report_template (10), law (6), etc.

**db_full_analysis.txt**
- Combined analysis từ multiple queries
- Tables, extensions, stats, size

---

## 🎯 Quick Facts

### Database
- **Name:** rag_bidding_v2
- **User:** sakana
- **Size:** 149 MB
- **PostgreSQL:** 18+
- **Extension:** pgvector 0.8.1

### Data
- **Documents:** 64 (in `documents` table)
- **Chunks:** 7,892 (in `langchain_pg_embedding`)
- **Embeddings:** 3,072 dimensions (text-embedding-3-large)

### Tables
1. **documents** ⭐ Primary table
   - Document management
   - Status tracking (active/expired)
   - 64 documents total

2. **langchain_pg_embedding**
   - Vector storage
   - 7,892 chunks with embeddings
   - JSONB metadata

3. **langchain_pg_collection** ⚠️ Internal only
   - LangChain bookkeeping
   - Collection: "docs"
   - Don't use in app logic!

---

## 🔗 Table Relationships

```
documents (64 docs)
    │
    │ 1:N via document_id
    ▼
langchain_pg_embedding (7,892 chunks)
    │
    │ FK: collection_id
    ▼
langchain_pg_collection (1 collection) ⚠️ Internal
```

---

## 📊 Document Types (Top 5)

| Type             | Count |
|------------------|-------|
| bidding_form     | 37    |
| report_template  | 10    |
| law              | 6     |
| exam_question    | 4     |
| circular         | 2     |

---

## ⚠️ Important Notes

### DO ✅
- Use `documents` table for document management
- Filter by `status = 'active'` in production
- Clear cache after status changes
- Join `documents` + `langchain_pg_embedding` for rich queries

### DON'T ❌
- Don't modify `langchain_pg_collection` directly
- Don't assume `collection_id` is meaningful for app logic
- Don't forget cache invalidation after metadata changes
- Don't skip status filtering in queries

---

## 🚀 Common Queries

### Get active documents by type
```sql
SELECT * FROM documents 
WHERE document_type = 'law' AND status = 'active';
```

### Get document with chunks
```sql
SELECT 
  d.document_id,
  d.document_name,
  COUNT(e.id) as embedded_chunks
FROM documents d
LEFT JOIN langchain_pg_embedding e 
  ON d.document_id = e.cmetadata->>'document_id'
GROUP BY d.id;
```

### Search with document filtering
```python
# Via LangChain PGVector
vector_store.similarity_search(
    query="...",
    k=10,
    filter={"document_type": "law", "status": "active"}
)
```

---

## 📚 Full Documentation

Main setup guide: `/home/sakana/Code/RAG-bidding/SETUP_ENVIRONMENT_DATABASE.md`

Technical docs:
- `documents/technical/PIPELINE_INTEGRATION_SUMMARY.md`
- `documents/technical/POOLING_CACHE_PLAN.md`
- `documents/setup/DATABASE_SETUP.md`

---

**Last Updated:** 2025-11-24  
**Maintainer:** System Analysis
