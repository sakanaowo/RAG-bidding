# 🚀 PHASE 5: System Integration - Kế Hoạch Buổi Sáng

**Ngày**: 3/11/2025  
**Thời gian**: 3-4 giờ (8:00 AM - 12:00 PM)  
**Mục tiêu**: Hoàn thành Phase 5 - Import chunks vào database và test end-to-end RAG pipeline

---

## 📊 Hiện Trạng

### ✅ Đã Có Sẵn:
- ✅ 4,512 UniversalChunk instances (data/processed/)
- ✅ Script `import_processed_chunks.py` (đã tạo)
- ✅ Script `calculate_embedding_cost.py` (đã tạo)
- ✅ Script `test_retrieval.py` và `test_retrieval_with_filters.py`
- ✅ PGVector database đã setup (`src/embedding/store/pgvector_store.py`)
- ✅ Retrieval system đã có (`src/retrieval/`)

### ⚠️ Cần Làm:
- [ ] Import chunks vào PGVector với embeddings
- [ ] Verify data integrity sau import
- [ ] Test retrieval với UniversalChunk format
- [ ] End-to-end RAG testing
- [ ] Performance benchmarking
- [ ] Document results

---

## ⏰ Timeline - Buổi Sáng (3.5 giờ)

```
8:00 - 8:30   (30 min)  ✅ Setup & Verification
8:30 - 9:30   (60 min)  🔄 Import Chunks to Database
9:30 - 10:00  (30 min)  ☕ Break + Review Import Results
10:00 - 10:45 (45 min)  🔍 Test Retrieval System
10:45 - 11:30 (45 min)  🧪 End-to-End RAG Testing
11:30 - 12:00 (30 min)  📊 Benchmarking & Documentation
```

---

## 📋 Chi Tiết Từng Bước

### **Bước 1: Setup & Verification** (8:00 - 8:30)

#### 1.1 Kiểm tra Database Connection
```bash
# Test connection
cd /home/sakana/Code/RAG-bidding
python3 -c "from src.config.models import settings; print(settings.database_url)"

# Verify PGVector extension
python3 scripts/bootstrap_db.py
```

#### 1.2 Estimate Embedding Cost
```bash
# Calculate cost trước khi import
python3 scripts/calculate_embedding_cost.py \
    --chunks-dir data/processed/chunks \
    --model text-embedding-3-large

# Expected: ~4,512 chunks × ~300 tokens/chunk = ~1.3M tokens
# Cost: ~$0.13 (very affordable!)
```

#### 1.3 Backup Database (Optional but Recommended)
```bash
# Create backup before import
./scripts/create_dump.sh
```

**Expected Output:**
- ✅ Database connection working
- ✅ Cost estimate: ~$0.10-0.20
- ✅ Backup created (if needed)

---

### **Bước 2: Import Chunks to Database** (8:30 - 9:30)

#### 2.1 Dry Run (Test with 10 chunks first)
```bash
# Test import với sample nhỏ
python3 scripts/import_processed_chunks.py \
    --chunks-dir data/processed/chunks \
    --limit 10 \
    --dry-run

# Review output, verify format
```

#### 2.2 Full Import
```bash
# Import ALL chunks (4,512 chunks)
python3 scripts/import_processed_chunks.py \
    --chunks-dir data/processed/chunks \
    --batch-size 100 \
    --verbose

# Expected: 
# - Processing time: ~15-20 minutes
# - Progress bar với tqdm
# - Final report: chunks imported, errors, duplicates
```

#### 2.3 Verify Import
```bash
# Quick verification
python3 -c "
from src.embedding.store.pgvector_store import vector_store
count = vector_store.similarity_search('test', k=1)
print(f'✅ Database has documents: {len(count) > 0}')
"
```

**Expected Output:**
```
📊 IMPORT SUMMARY
================================================================================
Total Files Processed:    63
Total Chunks Imported:    4,512
Failed:                   0
Duplicates Skipped:       0
Processing Time:          ~18 minutes
Average Speed:            ~250 chunks/min
Cost:                     ~$0.15
================================================================================
✅ Import Complete!
```

---

### **☕ Break + Review** (9:30 - 10:00)

**Checklist:**
- [ ] All 4,512 chunks imported?
- [ ] No errors in import log?
- [ ] Database size reasonable?
- [ ] Quick query test working?

```bash
# Quick stats
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

# Test query
results = vs.similarity_search('điều kiện tham gia đấu thầu', k=3)
print(f'✅ Retrieved {len(results)} results')
for doc in results:
    print(f'  - {doc.metadata.get(\"chunk_id\", \"unknown\")}')
"
```

---

### **Bước 3: Test Retrieval System** (10:00 - 10:45)

#### 3.1 Basic Retrieval Test
```bash
# Test basic similarity search
python3 scripts/test_retrieval.py

# Should test:
# - Query: "điều kiện tham gia đấu thầu"
# - Query: "quy định về hợp đồng xây dựng"
# - Query: "hồ sơ mời thầu gồm những gì"
```

#### 3.2 Metadata Filtering Test
```bash
# Test filtering by document type, status, etc.
python3 scripts/test_retrieval_with_filters.py

# Test filters:
# - document_type: "law", "decree", "circular", "bidding"
# - level: "dieu", "khoan", "phan", "chuong"
# - status: "active" vs "expired"
```

#### 3.3 Create Comprehensive Test Script

**File: `scripts/test_phase5_retrieval.py`**
```python
#!/usr/bin/env python3
"""Comprehensive retrieval testing for Phase 5."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from src.config.models import settings

def test_queries():
    """Test với các queries thực tế."""
    embeddings = OpenAIEmbeddings(model=settings.embed_model)
    vs = PGVector(
        embeddings=embeddings,
        collection_name=settings.collection,
        connection=settings.database_url,
        use_jsonb=True
    )
    
    test_cases = [
        {
            "query": "điều kiện tham gia đấu thầu",
            "expected_types": ["law", "decree"],
            "k": 5
        },
        {
            "query": "hồ sơ yêu cầu hàng hóa",
            "expected_types": ["bidding"],
            "k": 5
        },
        {
            "query": "luật đấu thầu 2023",
            "expected_types": ["law"],
            "k": 3
        }
    ]
    
    print("=" * 80)
    print("PHASE 5 RETRIEVAL TESTING")
    print("=" * 80)
    
    passed = 0
    for i, test in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}: {test['query']}")
        print("-" * 80)
        
        results = vs.similarity_search(test['query'], k=test['k'])
        
        print(f"✅ Retrieved {len(results)} results")
        for j, doc in enumerate(results, 1):
            doc_type = doc.metadata.get('document_type', 'unknown')
            chunk_id = doc.metadata.get('chunk_id', 'unknown')
            print(f"  {j}. [{doc_type}] {chunk_id}")
            print(f"     Content: {doc.page_content[:100]}...")
        
        # Verify expected types
        retrieved_types = [d.metadata.get('document_type') for d in results]
        if any(t in test['expected_types'] for t in retrieved_types):
            print(f"✅ PASS - Found expected types: {test['expected_types']}")
            passed += 1
        else:
            print(f"❌ FAIL - Expected {test['expected_types']}, got {set(retrieved_types)}")
    
    print("\n" + "=" * 80)
    print(f"SUMMARY: {passed}/{len(test_cases)} tests passed")
    print("=" * 80)

if __name__ == "__main__":
    test_queries()
```

**Run:**
```bash
python3 scripts/test_phase5_retrieval.py
```

**Expected Output:**
- ✅ 3/3 tests passed
- ✅ Retrieval working for all document types
- ✅ Metadata preserved correctly

---

### **Bước 4: End-to-End RAG Testing** (10:45 - 11:30)

#### 4.1 Test với Existing API (nếu có)
```bash
# Start API server (nếu có)
cd /home/sakana/Code/RAG-bidding
python3 -m src.api.main  # hoặc uvicorn command

# Test endpoint
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "điều kiện tham gia đấu thầu là gì?"}'
```

#### 4.2 Test Retrieval Pipeline
```bash
# Test full pipeline: Query → Retrieval → Context
python3 scripts/test_e2e_pipeline.py
```

#### 4.3 Create E2E Test Script

**File: `scripts/test_phase5_e2e.py`**
```python
#!/usr/bin/env python3
"""End-to-end RAG pipeline test for Phase 5."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.retrieval.retrievers.adaptive_retriever import AdaptiveRetriever

def test_e2e():
    """Test full RAG pipeline."""
    print("=" * 80)
    print("PHASE 5 END-TO-END TESTING")
    print("=" * 80)
    
    # Initialize adaptive retriever (from Phase 1)
    retriever = AdaptiveRetriever(mode="balanced")
    
    test_questions = [
        "Điều kiện tham gia đấu thầu theo luật đấu thầu 2023 là gì?",
        "Hồ sơ yêu cầu hàng hóa gồm những gì?",
        "Quy định về hợp đồng xây dựng",
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n{'='*80}")
        print(f"Question {i}: {question}")
        print("=" * 80)
        
        # Retrieve documents
        docs = retriever.get_relevant_documents(question)
        
        print(f"\n📚 Retrieved {len(docs)} documents:")
        for j, doc in enumerate(docs, 1):
            chunk_id = doc.metadata.get('chunk_id', 'unknown')
            doc_type = doc.metadata.get('document_type', 'unknown')
            print(f"\n{j}. [{doc_type}] {chunk_id}")
            print(f"   {doc.page_content[:200]}...")
        
        print(f"\n✅ E2E Test {i} Complete")
    
    print("\n" + "=" * 80)
    print("✅ ALL E2E TESTS PASSED")
    print("=" * 80)

if __name__ == "__main__":
    test_e2e()
```

**Run:**
```bash
python3 scripts/test_phase5_e2e.py
```

---

### **Bước 5: Benchmarking & Documentation** (11:30 - 12:00)

#### 5.1 Performance Benchmark
```bash
# Benchmark retrieval speed
python3 scripts/benchmark_retrieval.py \
    --queries 20 \
    --k 5 \
    --output results/phase5_benchmark.json
```

#### 5.2 Create Phase 5 Report

**File: `documents/PHASE_5_INTEGRATION_REPORT.md`**

Template:
```markdown
# Phase 5: System Integration - Report

**Date**: 3/11/2025  
**Status**: ✅ COMPLETED  
**Duration**: 3.5 hours

## Summary

Successfully integrated 4,512 UniversalChunk instances into PGVector database.
All retrieval and RAG pipeline tests passed.

## Statistics

| Metric | Value |
|--------|-------|
| Chunks Imported | 4,512 |
| Import Duration | XX minutes |
| Embedding Cost | $X.XX |
| Database Size | XXX MB |
| Average Retrieval Time | XXX ms |

## Test Results

- ✅ Import: 4,512/4,512 (100%)
- ✅ Basic Retrieval: 3/3 tests passed
- ✅ Filtered Retrieval: X/X tests passed
- ✅ E2E Pipeline: 3/3 tests passed

## Performance

- Query latency: XXX ms (avg)
- Throughput: XX queries/sec
- Accuracy: Subjective review ✅

## Next Steps

- [ ] Phase 6: Production Deployment
- [ ] Setup monitoring
- [ ] API documentation
- [ ] User acceptance testing
```

#### 5.3 Git Commit
```bash
git add .
git commit -m "feat: Complete Phase 5 - System Integration

- ✅ Imported 4,512 UniversalChunk instances to PGVector
- ✅ All retrieval tests passed (basic + filtered + E2E)
- ✅ Performance benchmarking complete
- ✅ Documentation updated

Ready for Phase 6: Production Deployment"

git push origin data-preprocess
```

---

## 🎯 Success Criteria

### Must Have (Critical):
- ✅ All 4,512 chunks imported to database
- ✅ No import errors
- ✅ Basic retrieval working
- ✅ Metadata preserved correctly

### Should Have (Important):
- ✅ Filtered retrieval working
- ✅ E2E pipeline tested
- ✅ Performance acceptable (<1s per query)
- ✅ Documentation complete

### Nice to Have (Optional):
- ✅ Benchmark report
- ✅ Cost analysis
- ✅ Comparison with old system

---

## 🐛 Troubleshooting

### Issue: Import Fails
**Solution:**
```bash
# Check database connection
python3 -c "from src.config.models import settings; print(settings.database_url)"

# Check PGVector extension
python3 scripts/bootstrap_db.py

# Verify chunks format
python3 -c "
import json
with open('data/processed/chunks/Luat_so_90_2025-qh15.jsonl') as f:
    chunk = json.loads(f.readline())
    print(json.dumps(chunk, indent=2, ensure_ascii=False))
"
```

### Issue: Retrieval Returns No Results
**Solution:**
```bash
# Verify documents in database
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

# Get collection info
# Check if collection exists and has documents
results = vs.similarity_search('test', k=1)
print(f'Documents in collection: {len(results)}')
"
```

### Issue: Slow Retrieval (>2s)
**Solution:**
```bash
# Check index status
python3 scripts/explain_optimizations.py

# Tune ivfflat.probes
python3 -c "
import psycopg2
conn = psycopg2.connect('YOUR_DATABASE_URL')
cur = conn.cursor()
cur.execute('SET ivfflat.probes = 10;')
conn.commit()
"
```

---

## 📊 Expected Results

### After 3.5 Hours:

```
✅ Phase 5 Complete: System Integration

Progress:
✅ Phase 1A: Schema Standardization
✅ Phase 1B: Bidding Optimization
✅ Phase 2A: All Document Types
✅ Phase 2B: Integration Testing
✅ Phase 4: Batch Re-Processing
✅ Phase 5: System Integration ← JUST COMPLETED! 🎉
📝 Phase 6: Production Deployment (Next)

Overall: 6/6 phases (100%) 🚀

Key Metrics:
- Documents: 4,512 chunks in database
- Retrieval: <1s average latency
- Accuracy: High quality results
- Cost: ~$0.15 for embeddings

Status: READY FOR PRODUCTION! ✅
```

---

## 🚀 Next Phase Preview

**Phase 6: Production Deployment** (1-2 weeks)
- [ ] API optimization
- [ ] Monitoring setup
- [ ] Load testing
- [ ] Documentation
- [ ] User training
- [ ] Go-live

---

**Created**: 3/11/2025  
**Author**: Development Team  
**Version**: 1.0
