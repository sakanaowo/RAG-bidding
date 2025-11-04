# ✅ Phase 5 Checklist - Buổi Sáng (3.5h)

**Ngày**: 3/11/2025  
**Mục tiêu**: Import 4,512 chunks vào database + test retrieval

---

## 🎯 Mục Tiêu Chính

- [ ] Import tất cả 4,512 chunks vào PGVector
- [ ] Test retrieval hoạt động tốt
- [ ] Verify metadata được preserve
- [ ] Benchmark performance

---

## ⏰ Timeline

```
8:00-8:30   Setup & Cost Estimation
8:30-9:30   Import Chunks (main task)
9:30-10:00  Break + Verify
10:00-10:45 Test Retrieval
10:45-11:30 E2E Testing
11:30-12:00 Benchmark + Commit
```

---

## 📝 Checklist Chi Tiết

### 1️⃣ Setup (8:00-8:30) - 30 phút

```bash
cd /home/sakana/Code/RAG-bidding
```

- [ ] Test database connection
  ```bash
  python3 -c "from src.config.models import settings; print(settings.database_url)"
  ```

- [ ] Bootstrap database
  ```bash
  python3 scripts/bootstrap_db.py
  ```

- [ ] Estimate cost
  ```bash
  python3 scripts/calculate_embedding_cost.py \
      --chunks-dir data/processed/chunks \
      --model text-embedding-3-large
  ```
  Expected: ~$0.15

- [ ] (Optional) Create backup
  ```bash
  ./scripts/create_dump.sh
  ```

**Checkpoint**: ✅ Cost < $0.20, Database ready

---

### 2️⃣ Import (8:30-9:30) - 60 phút

- [ ] Test với 10 chunks
  ```bash
  python3 scripts/import_processed_chunks.py \
      --chunks-dir data/processed/chunks \
      --limit 10 \
      --dry-run
  ```

- [ ] Full import (4,512 chunks)
  ```bash
  python3 scripts/import_processed_chunks.py \
      --chunks-dir data/processed/chunks \
      --batch-size 100 \
      --verbose
  ```
  Expected: ~15-20 minutes

- [ ] Verify import
  ```bash
  python3 -c "
  from src.embedding.store.pgvector_store import vector_store
  results = vector_store.similarity_search('test', k=1)
  print(f'✅ Found {len(results)} documents')
  "
  ```

**Checkpoint**: ✅ 4,512/4,512 chunks imported

---

### 3️⃣ Break + Review (9:30-10:00) - 30 phút

☕ Coffee break!

- [ ] Review import logs
- [ ] Check for errors
- [ ] Quick query test

```bash
python3 -c "
from langchain_postgres import PGVector
from langchain_openai import OpenAIEmbeddings
from src.config.models import settings

embeddings = OpenAIEmbeddings(model=settings.embed_model)
vs = PGVector(
    embeddings=embeddings,
    collection_name=settings.collection,
    connection=settings.database_url,
    use_jsonb=True
)

results = vs.similarity_search('điều kiện tham gia đấu thầu', k=3)
print(f'✅ Retrieved {len(results)} results')
for doc in results:
    print(f'  - {doc.metadata.get(\"chunk_id\", \"unknown\")}')
"
```

**Checkpoint**: ✅ Queries returning results

---

### 4️⃣ Test Retrieval (10:00-10:45) - 45 phút

- [ ] Basic retrieval
  ```bash
  python3 scripts/test_retrieval.py
  ```

- [ ] Filtered retrieval
  ```bash
  python3 scripts/test_retrieval_with_filters.py
  ```

- [ ] Create comprehensive test (nếu chưa có)
  ```bash
  python3 scripts/test_phase5_retrieval.py
  ```

**Checkpoint**: ✅ All retrieval tests passed

---

### 5️⃣ E2E Testing (10:45-11:30) - 45 phút

- [ ] Test adaptive retriever
  ```bash
  python3 scripts/test_e2e_pipeline.py
  ```

- [ ] Test với real queries
  - "Điều kiện tham gia đấu thầu là gì?"
  - "Hồ sơ yêu cầu hàng hóa gồm những gì?"
  - "Quy định về hợp đồng xây dựng"

- [ ] Verify metadata preserved
  - document_type
  - hierarchy
  - level
  - chunk_id

**Checkpoint**: ✅ E2E pipeline working

---

### 6️⃣ Benchmark + Document (11:30-12:00) - 30 phút

- [ ] Run benchmark
  ```bash
  python3 scripts/benchmark_retrieval.py \
      --queries 20 \
      --k 5
  ```

- [ ] Document results
  - Edit `documents/PHASE_5_INTEGRATION_REPORT.md`
  - Add statistics
  - Add test results

- [ ] Git commit
  ```bash
  git add .
  git commit -m "feat: Complete Phase 5 - System Integration
  
  - Imported 4,512 UniversalChunk instances to PGVector
  - All retrieval tests passed
  - Performance: <1s per query
  - Ready for Phase 6"
  
  git push origin data-preprocess
  ```

**Checkpoint**: ✅ Phase 5 complete, documented, committed

---

## 🎯 Success Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| Chunks Imported | 4,512 | ____ |
| Import Errors | 0 | ____ |
| Retrieval Tests Passed | 100% | ____ |
| Average Query Time | <1s | ____ ms |
| Embedding Cost | <$0.20 | $____ |

---

## 🐛 Quick Troubleshooting

**Import fails?**
```bash
# Check connection
python3 scripts/bootstrap_db.py

# Check chunks format
head -1 data/processed/chunks/Luat_so_90_2025-qh15.jsonl | python3 -m json.tool
```

**No results?**
```bash
# Verify collection
python3 -c "
from src.embedding.store.pgvector_store import vector_store
print(vector_store.similarity_search('test', k=1))
"
```

**Slow queries?**
```bash
# Tune pgvector
python3 scripts/explain_optimizations.py
```

---

## ✅ Kết Luận

Sau 3.5 giờ:

```
✅ Phase 5 COMPLETE!

- 4,512 chunks imported
- All tests passed
- Performance excellent
- Ready for production!

Next: Phase 6 - Production Deployment
```

---

**Tip**: Làm theo đúng thứ tự, không skip bước nào! 🚀
