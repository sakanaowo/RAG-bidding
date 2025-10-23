# 🚀 Phase 2 Quick Start Guide

**TL;DR**: Triển khai Cross-Encoder Reranking trong 1 ngày

---

## ⚡ Fast Track (Day 1)

### **Step 1: Install Dependencies** (5 minutes)

```bash
# Activate environment
conda activate venv

# Install reranking packages
pip install sentence-transformers>=2.2.0
pip install torch>=2.0.0

# Verify installation
python -c "from sentence_transformers import CrossEncoder; print('✅ Ready')"
```

---

### **Step 2: Create Reranker** (30 minutes)

```bash
# Create files
touch src/retrieval/ranking/base_reranker.py
touch src/retrieval/ranking/cross_encoder_reranker.py
```

**Copy from plan:**
- `base_reranker.py` → Abstract class
- `cross_encoder_reranker.py` → Full implementation

---

### **Step 3: Test Reranker** (15 minutes)

```python
# Quick test in Python REPL
from src.retrieval.ranking.cross_encoder_reranker import CrossEncoderReranker
from langchain_core.documents import Document

# Initialize
reranker = CrossEncoderReranker()

# Test data
query = "Quy định về bảo đảm dự thầu"
docs = [
    Document(page_content="Điều 14. Bảo đảm dự thầu..."),
    Document(page_content="Điều 68. Bảo đảm thực hiện hợp đồng..."),
    Document(page_content="Điều 10. Ưu đãi nhà thầu...")
]

# Rerank
results = reranker.rerank(query, docs, top_k=2)

# Should see Điều 14 first (most relevant)
print(f"Top result: {results[0][0].page_content[:50]}...")
print(f"Score: {results[0][1]:.4f}")
```

---

### **Step 4: Integrate with Retriever** (1 hour)

**Update `src/retrieval/retrievers/enhanced_retriever.py`:**

Add these fields:
```python
class EnhancedRetriever(BaseRetriever):
    # ... existing fields ...
    reranker: Optional[BaseReranker] = None
    rerank_top_k: int = 10
```

Update `_get_relevant_documents`:
```python
def _get_relevant_documents(self, query: str, ...) -> List[Document]:
    # ... existing code for enhancement + retrieval ...
    
    # Step 4: Rerank (NEW)
    if self.reranker:
        doc_scores = self.reranker.rerank(query, all_docs, top_k=self.k)
        return [doc for doc, score in doc_scores]
    
    return all_docs[:self.k]
```

---

### **Step 5: Update Factory** (30 minutes)

**Edit `src/retrieval/retrievers/__init__.py`:**

```python
from src.retrieval.ranking.cross_encoder_reranker import CrossEncoderReranker

def create_retriever(mode: str = "balanced", vector_store=None, enable_reranking: bool = False):
    base_retriever = BaseVectorRetriever(vector_store=vector_store)
    
    # Initialize reranker if enabled
    reranker = None
    if enable_reranking and mode in ["balanced", "quality"]:
        reranker = CrossEncoderReranker()
    
    if mode == "quality":
        return FusionRetriever(
            base_retriever=base_retriever,
            reranker=reranker,  # NEW
            rerank_top_k=10,
            k=5
        )
    
    # ... rest of modes
```

---

### **Step 6: Test API** (15 minutes)

```bash
# Start server
cd /home/sakana/Code/RAG-bidding
python -m uvicorn app.api.main:app --reload

# In another terminal, test with Postman or curl:
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Thời hạn hiệu lực bảo đảm dự thầu là bao lâu?",
    "mode": "quality"
  }'
```

**Expected:** Response includes relevant documents about Điều 14 (bảo đảm dự thầu)

---

### **Step 7: Enable in Config** (5 minutes)

**Edit `config/models.py`:**

```python
# Change this:
enable_reranking: bool = _env_bool("ENABLE_RERANKING", False)  # OLD

# To this:
enable_reranking: bool = _env_bool("ENABLE_RERANKING", True)  # NEW - Enable by default
```

**Update presets:**
```python
@staticmethod
def get_quality_mode() -> Dict[str, object]:
    return {
        "enable_query_enhancement": True,
        "enable_reranking": True,  # ✅ NOW TRUE
        "rerank_top_k": 10,
        "final_docs_k": 5,
        # ...
    }
```

---

## ✅ Done!

**Total time:** ~3 hours for basic implementation

**What you have now:**
- ✅ Cross-encoder reranking working
- ✅ Integrated with quality mode
- ✅ Ready to test and benchmark

---

## 🧪 Next Steps (Optional - Day 2+)

### **Add Tests:**
```bash
# Create test file
touch tests/unit/test_retrieval/test_reranking.py

# Run tests
pytest tests/unit/test_retrieval/test_reranking.py -v
```

### **Benchmark Performance:**
```python
import time

# Measure latency
start = time.time()
docs = retriever.invoke("test query")
latency = (time.time() - start) * 1000

print(f"Latency: {latency:.0f}ms")
# Target: <800ms for balanced mode
```

### **A/B Test:**
```python
# Test with vs without reranking
retriever_no_rerank = create_retriever(mode="quality", enable_reranking=False)
retriever_with_rerank = create_retriever(mode="quality", enable_reranking=True)

query = "Quy trình đấu thầu rộng rãi quốc tế"

docs_baseline = retriever_no_rerank.invoke(query)
docs_reranked = retriever_with_rerank.invoke(query)

# Compare top result relevance (manual inspection)
print("Without reranking:", docs_baseline[0].page_content[:100])
print("With reranking:", docs_reranked[0].page_content[:100])
```

---

## 🐛 Troubleshooting

### **Model download fails:**
```bash
# Set HuggingFace cache
export HF_HOME=/home/sakana/.cache/huggingface
mkdir -p $HF_HOME

# Retry
python -c "from sentence_transformers import CrossEncoder; CrossEncoder('BAAI/bge-reranker-v2-m3')"
```

### **Out of memory:**
```python
# Use smaller batch size
reranker = CrossEncoderReranker(
    model_name="BAAI/bge-reranker-v2-m3",
    device="cpu"  # Use CPU instead of GPU
)
```

### **Slow performance:**
```bash
# Check if model is on CPU
nvidia-smi  # If GPU available

# Switch to GPU
reranker = CrossEncoderReranker(device="cuda")
```

---

## 📊 Expected Results

### **Latency Breakdown:**
```
Quality mode (without reranking):  ~500ms
  - Query enhancement:    50ms
  - Vector search (k=10): 150ms
  - RRF fusion:          100ms
  - Answer generation:   200ms

Quality mode (with reranking):     ~650ms (+150ms)
  - Query enhancement:    50ms
  - Vector search (k=10): 150ms
  - Cross-encoder:       100ms  ⭐ NEW
  - RRF fusion:           50ms
  - Answer generation:   300ms
```

### **Accuracy Gains:**
- **MRR**: 0.70 → 0.85 (+21%)
- **NDCG@5**: 0.75 → 0.90 (+20%)
- **User Satisfaction**: 3.5/5 → 4.2/5

---

## 🎯 Success Criteria

Check these before considering Phase 2A complete:

- [ ] Cross-encoder loads without errors
- [ ] Reranking returns documents in better order
- [ ] API /ask endpoint works with mode="quality"
- [ ] Latency < 800ms for quality mode
- [ ] Tests passing
- [ ] No crashes after 100 queries

---

**Ready to start?** Follow Step 1! 🚀

**Questions?** Check full plan in `PHASE2_RERANKING_PLAN.md`
