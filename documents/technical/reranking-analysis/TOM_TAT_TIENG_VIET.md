# 🇻🇳 TÓM TẮT VẤN ĐỀ RERANKER - TIẾNG VIỆT

**Ngày tạo**: 12/11/2025  
**Vấn đề**: Memory leak nghiêm trọng khi chạy performance tests  
**Độ ưu tiên**: 🚨 CRITICAL

---

## 📖 Giải Thích Dễ Hiểu

### Vấn Đề Là Gì?

Hệ thống RAG của chúng ta có **4 bước** chính:

```
1. User hỏi câu hỏi
   ↓
2. Tìm kiếm 20 documents liên quan (retrieval)
   ↓
3. Xếp hạng lại để lấy 5 docs tốt nhất (reranking) ← ĐÂY LÀ VẤN ĐỀ!
   ↓
4. LLM tạo câu trả lời từ 5 docs đó
```

**Bước 3 (reranking)** đang gặp vấn đề nghiêm trọng:
- Mỗi khi user hỏi → Load lại model BGE (1.2GB) vào RAM
- 10 users cùng hỏi → 10 models → 12GB RAM!
- Performance test: 60 requests → 72GB RAM → CRASH!

### Tại Sao Lại Như Vậy?

**Code hiện tại** (SAI):
```python
# File: src/api/main.py
@app.post("/ask")
def ask(body: AskIn):
    # Mỗi request tạo retriever mới
    retriever = create_retriever(mode=body.mode)
    # → Bên trong nó tạo BGEReranker mới
    # → Load 1.2GB model vào RAM
    # → KHÔNG BAO GIỜ XÓA!
```

**Lý do** mỗi request tạo mới:
1. `create_retriever()` được gọi trong hàm `ask()`
2. Mỗi lần gọi tạo `BGEReranker()` mới
3. Python GC (garbage collector) không cleanup kịp
4. Model cũ vẫn nằm trong RAM → Memory leak

### Ảnh Hưởng Thế Nào?

**Test Results** (từ file performance log):

| Metric | Trước | Mục tiêu | Chênh lệch |
|--------|-------|----------|------------|
| **RAM Usage** | 20GB+ | <2GB | Gấp 10 lần! |
| **Concurrent Users** | 5 max | 50+ | Chỉ 10% capacity |
| **Response Time** | 9.6s | <2s | Gấp 5 lần! |
| **Success Rate** | 36.7% | >95% | Fail 2/3 queries! |

**Ví dụ cụ thể**:
- Chỉ **5 users** đồng thời → Hệ thống ổn
- **10 users** → 63% queries FAIL, response time x2.5
- Performance test → 20GB RAM → Server crash

---

## 🔧 Giải Pháp

### Giải Pháp 1: Singleton Pattern (Nhanh - 30 phút)

**Ý tưởng**: Chỉ load model **1 lần duy nhất**, sau đó **tái sử dụng**

**Code fix**:

```python
# File: src/retrieval/ranking/bge_reranker.py
# Thêm vào đầu file

_reranker_instance = None  # Biến global lưu model
_lock = threading.Lock()   # Đảm bảo thread-safe

def get_singleton_reranker():
    """Lấy hoặc tạo reranker (chỉ tạo 1 lần)"""
    global _reranker_instance
    
    if _reranker_instance is None:  # Chưa có → tạo mới
        with _lock:  # Lock để tránh race condition
            if _reranker_instance is None:
                _reranker_instance = BGEReranker()
                print("✅ Model loaded (chỉ 1 lần)")
    
    return _reranker_instance  # Trả về instance đã có
```

**Sửa code sử dụng**:

```python
# File: src/retrieval/retrievers/__init__.py
def create_retriever(mode="balanced", enable_reranking=True):
    if enable_reranking:
        # TRƯỚC (SAI):
        # reranker = BGEReranker()  # Tạo mới mỗi lần!
        
        # SAU (ĐÚNG):
        reranker = get_singleton_reranker()  # Dùng lại instance cũ
    
    # ... rest of code
```

**Kết quả mong đợi**:
- ✅ RAM: 20GB → 1.5GB (giảm 13 lần)
- ✅ Concurrent users: 5 → 50+ (tăng 10 lần)
- ✅ Response time: 9.6s → <2s (nhanh 5 lần)

---

### Giải Pháp 2: FastAPI Dependency Injection (Tốt hơn - 1 giờ)

**Ý tưởng**: Dùng cơ chế của FastAPI để quản lý lifecycle

**Tạo file mới**:

```python
# File: src/api/dependencies.py (FILE MỚI)
from functools import lru_cache
from src.retrieval.ranking import BGEReranker

@lru_cache()  # FastAPI cache dependency
def get_shared_reranker() -> BGEReranker:
    """
    Dependency: Trả về singleton reranker
    FastAPI tự động:
    - Tạo 1 lần khi app start
    - Reuse cho mọi requests
    - Cleanup khi app shutdown
    """
    return BGEReranker()
```

**Sử dụng trong API**:

```python
# File: src/api/main.py
from fastapi import Depends
from .dependencies import get_shared_reranker

@app.post("/ask")
def ask(
    body: AskIn,
    reranker: BGEReranker = Depends(get_shared_reranker)  # Inject
):
    # Reranker được FastAPI inject tự động
    retriever = create_retriever(
        mode=body.mode,
        reranker=reranker  # Dùng instance đã inject
    )
    # ... rest of code
```

**Ưu điểm**:
- ✅ Tự động cleanup khi restart server
- ✅ Compatible với multi-worker (uvicorn)
- ✅ Dễ test (có thể mock dependency)
- ✅ Best practice của FastAPI

---

## 🎯 Nên Làm Gì?

### Ngay Lập Tức (Hôm Nay)

1. **Implement Giải Pháp 1** (30 phút)
   - Thêm `get_singleton_reranker()` vào `bge_reranker.py`
   - Sửa `create_retriever()` để dùng singleton
   - Test bằng `run_performance_tests.py --quick`

2. **Verify Fix Hoạt Động**
   ```bash
   # Terminal 1: Start server
   ./start_server.sh
   
   # Terminal 2: Run test
   python scripts/tests/performance/run_performance_tests.py --quick
   
   # Terminal 3: Monitor RAM
   watch -n 1 'free -h'
   
   # Kết quả mong đợi:
   # - RAM stable ở ~1.5GB
   # - 10 concurrent users thành công
   # - Response time <3s
   ```

### Tuần Này

1. **Migrate sang Giải Pháp 2** (1 giờ)
   - Tạo `src/api/dependencies.py`
   - Update `main.py` dùng `Depends()`
   - Test lại với 20+ users

2. **Add Monitoring**
   ```python
   @app.get("/health/reranker")
   def reranker_health():
       reranker = get_shared_reranker()
       return {
           "model": reranker.model_name,
           "device": reranker.device,
           "memory_mb": get_memory_usage()
       }
   ```

---

## 📊 So Sánh Các Reranking Strategies

### Hiện Tại Có Gì?

**Folder**: `src/retrieval/ranking/`

| File | Tình trạng | Mô tả |
|------|------------|-------|
| `bge_reranker.py` | ✅ Đang dùng | Model BGE - multilingual, tốt cho tiếng Việt |
| `cohere_reranker.py` | ⚠️ Empty | Cohere API - tốt nhưng tốn tiền |
| `cross_encoder_reranker.py` | ⚠️ Empty | Generic cross-encoder |
| `legal_score_reranker.py` | ⚠️ Empty | Custom cho văn bản pháp luật |
| `llm_reranker.py` | ⚠️ Empty | Dùng LLM để rerank |

### Các Dự Án Khác Làm Gì?

**Perplexity.ai**:
```
Retrieval (50 docs) → Cohere Rerank API → Top 5 → LLM
Ưu: Nhanh (50ms), không lo memory
Nhược: Tốn $2 per 1000 requests
```

**You.com**:
```
Retrieval (20 docs) → Custom Model (singleton) → Top 5 → LLM
Ưu: Miễn phí, control được model
Nhược: Phải quản lý model lifecycle
```

**ChatGPT**:
```
Retrieval (50 docs) → Fast filter (→20) → Rerank (→5) → LLM
Ưu: 2 stages, balance speed & quality
Nhược: Phức tạp
```

### So Sánh Options

| Option | Chi phí/tháng | Tốc độ | Chất lượng | Tiếng Việt |
|--------|---------------|--------|------------|------------|
| **BGE-v2-m3** (hiện tại) | $0 | 120ms | ⭐⭐⭐⭐ (85%) | ✅ Tốt |
| **Cohere API** | $1,200 | 50ms | ⭐⭐⭐⭐⭐ (88%) | ✅ Tốt |
| **ms-marco** | $0 | 40ms | ⭐⭐⭐ (72%) | ❌ English only |
| **PhoBERT** | $0 | 90ms | ⭐⭐⭐ (76%) | ✅✅ Tốt nhất |
| **Không rerank** | $0 | 0ms | ⭐⭐ (68%) | - |

**Khuyến nghị**:
1. **Ngắn hạn**: Fix bug BGE (giải pháp 1 hoặc 2)
2. **Trung hạn**: Test Cohere API (pilot 100 queries)
3. **Dài hạn**: Fine-tune PhoBERT trên legal data

---

## 📁 Tài Liệu Liên Quan

Tất cả tài liệu đã được tổ chức trong folder:
**`documents/technical/reranking-analysis/`**

```
reranking-analysis/
├── README.md                          # ← Đọc đầu tiên (hướng dẫn đọc)
├── RERANKER_FIX_URGENT.md            # ← Fix nhanh (3 phút)
├── RERANKER_MEMORY_ANALYSIS.md       # ← Phân tích chi tiết (15 phút)
└── RERANKING_STRATEGIES.md           # ← So sánh options (20 phút)
```

### Đọc Theo Tình Huống

**🔥 Server crash ngay, cần fix GẤP**:
1. Đọc `RERANKER_FIX_URGENT.md` (3 phút)
2. Copy code → Paste → Test → Deploy

**🤔 Muốn hiểu tại sao lại như vậy**:
1. Đọc file này (10 phút)
2. Đọc `RERANKER_MEMORY_ANALYSIS.md` (15 phút)
3. Implement fix từ `RERANKER_FIX_URGENT.md`

**📊 Planning cải thiện reranking**:
1. Đọc `RERANKING_STRATEGIES.md` (20 phút)
2. So sánh BGE vs Cohere vs PhoBERT
3. Quyết định: Fix hiện tại hay migrate?

---

## ❓ FAQ - Câu Hỏi Thường Gặp

### Q1: Tại sao không dùng Cohere API cho đơn giản?
**A**: Cohere tốt nhưng:
- Chi phí: $1,200/tháng cho 1000 queries/ngày
- Data privacy: Gửi documents lên server của họ
- Dependency: API down → service của ta down

BGE free, local, nhưng cần fix memory leak.

### Q2: Memory leak có ảnh hưởng đến chức năng không?
**A**: CÓ! Ảnh hưởng nghiêm trọng:
- Single user: OK
- 5 users: Chậm nhưng vẫn chạy
- 10+ users: 60%+ queries FAIL
- Performance test: Server CRASH

### Q3: Fix xong có cần deploy lại không?
**A**: CÓ! Cần:
1. Commit code fix
2. Restart server (hoặc deploy mới)
3. Verify bằng performance test
4. Monitor RAM usage 24h đầu

### Q4: Có thể vừa dùng BGE vừa Cohere được không?
**A**: ĐƯỢC! Implement fallback:
```python
try:
    # Dùng BGE local (free)
    results = bge_reranker.rerank(query, docs)
except OutOfMemoryError:
    # Fallback sang Cohere API
    results = cohere_reranker.rerank(query, docs)
```

### Q5: Khi nào nên fine-tune PhoBERT?
**A**: Khi:
- Đã collect được 1000+ query-document pairs
- BGE performance không đủ tốt cho legal domain
- Có resource để train & maintain model

---

## 🚀 Checklist Thực Hiện

### Phase 1: Fix Urgent (Hôm Nay) ✅
- [ ] Đọc `RERANKER_FIX_URGENT.md`
- [ ] Implement singleton pattern
- [ ] Test với `run_performance_tests.py --quick`
- [ ] Verify RAM usage <2GB
- [ ] Commit & deploy

### Phase 2: Production-Ready (Tuần Này) ✅
- [ ] Migrate sang FastAPI Dependency Injection
- [ ] Add health check endpoint `/health/reranker`
- [ ] Test với 20+ concurrent users
- [ ] Setup monitoring (Prometheus/Grafana)
- [ ] Document changes

### Phase 3: Evaluate Alternatives (Tháng Này) 🔄
- [ ] Test Cohere API với 100 queries
- [ ] Compare cost: Cohere vs BGE hosting
- [ ] Benchmark performance: BGE vs Cohere
- [ ] Decision: Stay with BGE hoặc migrate

### Phase 4: Long-term (Quý Tới) 📅
- [ ] Collect training data (1000+ pairs)
- [ ] Fine-tune PhoBERT cho legal domain
- [ ] A/B test: PhoBERT vs BGE
- [ ] Optimize infrastructure (separate reranker service)

---

**Người tạo**: Development Team  
**Liên hệ**: @team trong Slack  
**Status**: 🚨 Cần fix ngay - Blocking production scaling
