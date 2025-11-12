# 📁 Reranking Analysis - Phân Tích Vấn Đề Memory Leak

**Thư mục này chứa**: Phân tích chi tiết về vấn đề memory leak của BGE Reranker và các giải pháp

**🎯 Đọc file nào trước?**
- 🇻🇳 **Nếu bạn muốn đọc tiếng Việt**: Bắt đầu với [TOM_TAT_TIENG_VIET.md](./TOM_TAT_TIENG_VIET.md)
- 🔥 **Nếu server crash, cần fix GẤP**: Đọc [RERANKER_FIX_URGENT.md](./RERANKER_FIX_URGENT.md)
- 📖 **Nếu muốn hiểu chi tiết kỹ thuật**: Đọc file này tiếp

---

## 📚 Tài Liệu Trong Folder (4 Files)

### 🇻🇳 [TOM_TAT_TIENG_VIET.md](./TOM_TAT_TIENG_VIET.md) ⭐ BẮT ĐẦU TỪ ĐÂY
**Mục đích**: Giải thích toàn bộ vấn đề bằng tiếng Việt dễ hiểu  
**Thời gian đọc**: 10 phút  
**Dành cho**: Mọi người (developer, tech lead, PM)

**Nội dung**:
- Giải thích vấn đề bằng ví dụ đơn giản
- So sánh "trước - sau" rõ ràng
- Code fix với comment tiếng Việt
- FAQ (Câu hỏi thường gặp)
- Checklist hành động

**Khi nào đọc**:
- ✅ Lần đầu tìm hiểu vấn đề
- ✅ Muốn giải thích cho người khác
- ✅ Cần overview nhanh bằng tiếng Việt

---

### 🚨 [RERANKER_FIX_URGENT.md](./RERANKER_FIX_URGENT.md)
**Mục đích**: Hướng dẫn fix nhanh cho production (English)  
**Thời gian đọc**: 3 phút  
**Dành cho**: Developer cần fix ngay lập tức

**Nội dung chính**:
- Tóm tắt vấn đề (CUDA OOM, 20GB memory leak)
- Code fix nhanh (30 phút implement)
- Cách verify fix đã hoạt động
- Expected improvements

**Khi nào đọc**: 
- ✅ Server đang bị crash vì OOM
- ✅ Cần fix nhanh để deploy
- ✅ Muốn hiểu vấn đề trong 5 phút

---

### 🔍 [RERANKER_MEMORY_ANALYSIS.md](./RERANKER_MEMORY_ANALYSIS.md)
**Mục đích**: Phân tích kỹ thuật chi tiết  
**Thời gian đọc**: 15 phút  
**Dành cho**: Tech lead, developer muốn hiểu sâu

**Nội dung chính**:
- **Root Cause Analysis**: Tại sao BGEReranker leak memory
  - Code flow từ API → Retriever → Reranker
  - Lifecycle của model loading
  - Performance test amplifies problem
  
- **Industry Best Practices**: Production systems khác làm thế nào
  - Perplexity.ai: Cohere API
  - You.com: Singleton pattern
  - ChatGPT: Distributed cache
  
- **3 Solutions** với code chi tiết:
  1. Singleton pattern (quick fix)
  2. FastAPI Dependency Injection (recommended)
  3. Manual cleanup (temporary)

- **Implementation Roadmap**:
  - Phase 1: Immediate fix (1-2h)
  - Phase 2: Production-ready (1 day)
  - Phase 3: Full optimization (1 week)

**Khi nào đọc**:
- ✅ Muốn hiểu nguyên nhân gốc rễ
- ✅ Cần chọn solution phù hợp
- ✅ Planning refactor/optimization

---

### 🎯 [RERANKING_STRATEGIES.md](./RERANKING_STRATEGIES.md)
**Mục đích**: So sánh các chiến lược reranking  
**Thời gian đọc**: 20 phút  
**Dành cho**: Architect, senior dev planning features

**Nội dung chính**:
- **Current Implementation Status**:
  - BGEReranker: Production (có bug)
  - Alternatives: Empty files (chưa implement)
  
- **Industry Comparison**:
  - Perplexity / You.com / ChatGPT làm gì
  - Standard pipeline patterns
  - Key principles

- **Reranker Options**:
  | Option | Cost | Speed | Quality | Vietnamese |
  |--------|------|-------|---------|------------|
  | BGE-v2-m3 | $0 | 120ms | 85% | ✅ |
  | Cohere API | $1.2K/mo | 50ms | 88% | ✅ |
  | ms-marco | $0 | 40ms | 72% | ❌ |
  | PhoBERT | $0 | 90ms | 76% | ✅ |

- **Performance Benchmark**: Internal test results với 15 queries
  
- **Recommended Strategy**:
  - Immediate: Fix memory leak
  - Short-term: Evaluate Cohere
  - Long-term: Fine-tune PhoBERT

**Khi nào đọc**:
- ✅ Planning reranking improvements
- ✅ Evaluating alternatives (Cohere, PhoBERT)
- ✅ Cost vs quality analysis

---

## 🎯 Đọc Tài Liệu Theo Tình Huống

### Tình huống 1: 🔥 Server crash, cần fix GẤP
```
1. Đọc RERANKER_FIX_URGENT.md (3 phút)
2. Copy code fix vào project
3. Test bằng performance suite
4. Deploy
```

### Tình huống 2: 🤔 Muốn hiểu vấn đề đầy đủ
```
1. RERANKER_FIX_URGENT.md - Hiểu overview (3 phút)
2. RERANKER_MEMORY_ANALYSIS.md - Hiểu root cause (15 phút)
3. RERANKING_STRATEGIES.md - Hiểu alternatives (20 phút)
```

### Tình huống 3: 📊 Planning improvements
```
1. RERANKING_STRATEGIES.md - Compare options (20 phút)
2. RERANKER_MEMORY_ANALYSIS.md - Implementation roadmap (10 phút)
3. Decide: Fix current vs migrate to Cohere
```

---

## 🔗 Liên Kết Với Code

### Files bị ảnh hưởng:
```
src/api/main.py::ask()                          # Tạo retriever mỗi request
src/retrieval/retrievers/__init__.py            # create_retriever()
src/retrieval/ranking/bge_reranker.py           # BGEReranker class
src/generation/chains/qa_chain.py::answer()     # Cũng tạo retriever
```

### Files cần tạo/sửa:
```
src/api/dependencies.py                         # NEW - FastAPI DI
src/retrieval/ranking/bge_reranker.py           # ADD - get_singleton_reranker()
```

### Test files:
```
scripts/tests/performance/run_performance_tests.py      # Verify fix
scripts/tests/performance/test_multi_user_queries.py    # Load test
```

---

## 📈 Metrics Tracking

### Before Fix (Current State):
- Memory usage: 20GB+ per test
- Concurrent users: Max 5 (breaks at 10)
- Response time: 9.6s avg
- Success rate: 36.7%

### After Fix (Expected):
- Memory usage: <2GB
- Concurrent users: 50+
- Response time: <2s avg
- Success rate: >95%

---

## 🚀 Quick Actions

```bash
# 1. Verify current issue
python scripts/tests/performance/run_performance_tests.py --quick

# 2. Monitor memory during test
watch -n 1 'nvidia-smi'  # GPU
watch -n 1 'free -h'     # RAM

# 3. After fix, verify improvement
python scripts/tests/performance/test_multi_user_queries.py --max-users 20

# 4. Check reranker status
curl http://localhost:8000/health/reranker  # After adding health endpoint
```

---

**Maintainer**: Development Team  
**Created**: 12/11/2025  
**Last Updated**: 12/11/2025  
**Status**: 🚨 CRITICAL - Cần fix ngay
