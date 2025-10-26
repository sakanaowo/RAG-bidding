# 🚀 Phase 2 - Hướng Dẫn Bắt Đầu Nhanh

**TL;DR**: Triển khai Cross-Encoder Reranking trong 1 ngày

---

## ⚡ Lộ Trình Nhanh (Ngày 1)

### **Bước 1: Cài Đặt Dependencies** (5 phút)

```bash
# Kích hoạt environment
conda activate venv

# Cài đặt packages reranking
pip install sentence-transformers>=2.2.0
pip install torch>=2.0.0

# Xác nhận cài đặt
python -c "from sentence_transformers import CrossEncoder; print('✅ Sẵn sàng')"
```

---

### **Bước 2: Tạo Reranker** (30 phút)

```bash
# Tạo files
touch src/retrieval/ranking/base_reranker.py
touch src/retrieval/ranking/cross_encoder_reranker.py
```

**Copy từ kế hoạch:**
- `base_reranker.py` → Abstract class
- `cross_encoder_reranker.py` → Triển khai đầy đủ

---

### **Bước 3: Test Reranker** (15 phút)

```python
# Test nhanh trong Python REPL
from src/retrieval/ranking.cross_encoder_reranker import CrossEncoderReranker
from langchain_core.documents import Document

# Khởi tạo
reranker = CrossEncoderReranker()

# Dữ liệu test
query = "Quy định về bảo đảm dự thầu"
docs = [
    Document(page_content="Điều 14. Bảo đảm dự thầu..."),
    Document(page_content="Điều 68. Bảo đảm thực hiện hợp đồng..."),
    Document(page_content="Điều 10. Ưu đãi nhà thầu...")
]

# Rerank
results = reranker.rerank(query, docs, top_k=2)

# Nên thấy Điều 14 đầu tiên (liên quan nhất)
print(f"Kết quả top: {results[0][0].page_content[:50]}...")
print(f"Điểm: {results[0][1]:.4f}")
```

---

### **Bước 4: Tích Hợp Với Retriever** (1 giờ)

**Cập nhật `src/retrieval/retrievers/enhanced_retriever.py`:**

Thêm các trường:

```python
class EnhancedRetriever(BaseRetriever):
    # ... existing fields ...
    reranker: Optional[BaseReranker] = None
    rerank_top_k: int = 10
```

Cập nhật `_get_relevant_documents`:

```python
def _get_relevant_documents(self, query: str, ...) -> List[Document]:
    # ... code hiện tại cho enhancement + retrieval ...
    
    # Bước 4: Rerank (MỚI)
    if self.reranker:
        doc_scores = self.reranker.rerank(query, all_docs, top_k=self.k)
        return [doc for doc, score in doc_scores]
    
    return all_docs[:self.k]
```

---

### **Bước 5: Cập Nhật Factory** (30 phút)

**Sửa `src/retrieval/retrievers/__init__.py`:**

```python
from src.retrieval.ranking.cross_encoder_reranker import CrossEncoderReranker

def create_retriever(mode: str = "balanced", vector_store=None, enable_reranking: bool = False):
    base_retriever = BaseVectorRetriever(vector_store=vector_store)
    
    # Khởi tạo reranker nếu enabled
    reranker = None
    if enable_reranking and mode in ["balanced", "quality"]:
        reranker = CrossEncoderReranker()
    
    if mode == "quality":
        return FusionRetriever(
            base_retriever=base_retriever,
            reranker=reranker,  # MỚI
            rerank_top_k=10,
            k=5
        )
    
    # ... các modes còn lại
```

---

### **Bước 6: Test API** (15 phút)

```bash
# Khởi động server
cd /home/sakana/Code/RAG-bidding
python -m uvicorn app.api.main:app --reload

# Trong terminal khác, test với curl:
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Thời hạn hiệu lực bảo đảm dự thầu là bao lâu?",
    "mode": "quality"
  }'
```

**Kỳ vọng:** Response bao gồm tài liệu liên quan về Điều 14 (bảo đảm dự thầu)

---

### **Bước 7: Bật Trong Config** (5 phút)

**Sửa `config/models.py`:**

```python
# Đổi:
enable_reranking: bool = _env_bool("ENABLE_RERANKING", False)  # CŨ

# Thành:
enable_reranking: bool = _env_bool("ENABLE_RERANKING", True)  # MỚI - Bật mặc định
```

**Cập nhật presets:**

```python
@staticmethod
def get_quality_mode() -> Dict[str, object]:
    return {
        "enable_query_enhancement": True,
        "enable_reranking": True,  # ✅ BÂY GIỜ TRUE
        "rerank_top_k": 10,
        "final_docs_k": 5,
        # ...
    }
```

---

## ✅ Hoàn Tất!

**Tổng thời gian:** ~3 giờ cho triển khai cơ bản

**Bạn hiện có:**
- ✅ Cross-encoder reranking hoạt động
- ✅ Tích hợp với quality mode
- ✅ Sẵn sàng test và đo hiệu suất

---

## 🧪 Các Bước Tiếp Theo (Tùy chọn - Ngày 2+)

### **Thêm Tests:**

```bash
# Tạo file test
touch tests/unit/test_retrieval/test_reranking.py

# Chạy tests
pytest tests/unit/test_retrieval/test_reranking.py -v
```

### **Đo Hiệu Suất:**

```python
import time

# Đo độ trễ
start = time.time()
docs = retriever.invoke("test query")
latency = (time.time() - start) * 1000

print(f"Độ trễ: {latency:.0f}ms")
# Mục tiêu: <800ms cho balanced mode
```

### **A/B Test:**

```python
# Test với và không có reranking
retriever_no_rerank = create_retriever(mode="quality", enable_reranking=False)
retriever_with_rerank = create_retriever(mode="quality", enable_reranking=True)

query = "Quy trình đấu thầu rộng rãi quốc tế"

docs_baseline = retriever_no_rerank.invoke(query)
docs_reranked = retriever_with_rerank.invoke(query)

# So sánh độ liên quan kết quả top (kiểm tra thủ công)
print("Không reranking:", docs_baseline[0].page_content[:100])
print("Có reranking:", docs_reranked[0].page_content[:100])
```

---

## 🐛 Xử Lý Lỗi

### **Download model thất bại:**

```bash
# Đặt cache HuggingFace
export HF_HOME=/home/sakana/.cache/huggingface
mkdir -p $HF_HOME

# Thử lại
python -c "from sentence_transformers import CrossEncoder; CrossEncoder('BAAI/bge-reranker-v2-m3')"
```

### **Hết bộ nhớ:**

```python
# Dùng batch size nhỏ hơn
reranker = CrossEncoderReranker(
    model_name="BAAI/bge-reranker-v2-m3",
    device="cpu"  # Dùng CPU thay vì GPU
)
```

### **Hiệu suất chậm:**

```bash
# Kiểm tra nếu model trên CPU
nvidia-smi  # Nếu GPU có sẵn

# Chuyển sang GPU
reranker = CrossEncoderReranker(device="cuda")
```

---

## 📊 Kết Quả Kỳ Vọng

### **Phân Tích Độ Trễ:**

```
Quality mode (không reranking):  ~500ms
  - Query enhancement:    50ms
  - Vector search (k=10): 150ms
  - RRF fusion:          100ms
  - Answer generation:   200ms

Quality mode (có reranking):     ~650ms (+150ms)
  - Query enhancement:    50ms
  - Vector search (k=10): 150ms
  - Cross-encoder:       100ms  ⭐ MỚI
  - RRF fusion:           50ms
  - Answer generation:   300ms
```

### **Cải Thiện Độ Chính Xác:**

- **MRR**: 0.70 → 0.85 (+21%)
- **NDCG@5**: 0.75 → 0.90 (+20%)
- **Sự hài lòng người dùng**: 3.5/5 → 4.2/5

---

## 🎯 Tiêu Chí Thành Công

Kiểm tra những điều này trước khi coi Phase 2A hoàn thành:

- [ ] Cross-encoder load không lỗi
- [ ] Reranking trả về tài liệu theo thứ tự tốt hơn
- [ ] API /ask endpoint hoạt động với mode="quality"
- [ ] Độ trễ < 800ms cho quality mode
- [ ] Tests pass
- [ ] Không crash sau 100 truy vấn

---

**Sẵn sàng bắt đầu?** Làm theo Bước 1! 🚀

**Có câu hỏi?** Xem kế hoạch đầy đủ trong `PHASE2_RERANKING_PLAN_VI.md`
