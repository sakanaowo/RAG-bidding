# Postman Test Guide - Reranking Integration

## 🎯 Mục đích
Test reranking integration trên production API với Postman.

## 🚀 Setup

1. **Khởi động server:**
```bash
cd /home/sakana/Code/RAG-bidding
./start_server.sh
```

Server chạy tại: `http://localhost:8000`

2. **Import Postman Collection:**
- File: `postman_collection.json` (đã có sẵn)
- Hoặc tạo request mới theo hướng dẫn dưới

---

## 📋 Test Cases

### Test 1: Health Check
**Verify server đang chạy**

```
GET http://localhost:8000/health
```

**Expected Response:**
```json
{
    "db": true
}
```

---

### Test 2: Stats - Check Reranking Config
**Kiểm tra reranking đã enabled**

```
GET http://localhost:8000/stats
```

**Expected Response:**
```json
{
    "vector_store": {...},
    "llm": {...},
    "phase1_features": {
        "adaptive_retrieval": true,
        "enhanced_prompts": true,
        "query_enhancement": true,
        "reranking": true,  ← ✅ Should be true
        "answer_validation": false
    },
    ...
}
```

---

### Test 3: Balanced Mode WITH Reranking
**Test câu hỏi về bảo đảm dự thầu (Điều 14 phải rank #1)**

**Request:**
```http
POST http://localhost:8000/ask
Content-Type: application/json

{
    "question": "Quy định về thời gian hiệu lực bảo đảm dự thầu trong Luật Đấu thầu 2023",
    "mode": "balanced"
}
```

**Expected Response:**
```json
{
    "answer": "Theo Luật Đấu thầu 2023, thời gian hiệu lực bảo đảm dự thầu được quy định cụ thể tại Điều 14...",
    "sources": [
        "Điều 14. Bảo đảm dự thầu...",  ← ✅ Điều 14 phải xuất hiện đầu tiên (reranked)
        ...
    ],
    "adaptive_retrieval": {...},
    "enhanced_features": ["query_enhancement", "reranking"],  ← ✅ Có reranking
    "processing_time_ms": 800  ← ~500-1000ms (có reranking)
}
```

**Verify:**
- ✅ `sources[0]` chứa "Điều 14" về bảo đảm dự thầu
- ✅ `enhanced_features` có "reranking"
- ✅ `processing_time_ms` khoảng 500-1000ms (có reranking thêm ~100-400ms)

---

### Test 4: Fast Mode WITHOUT Reranking
**Fast mode không dùng reranking → Nhanh hơn**

**Request:**
```http
POST http://localhost:8000/ask
Content-Type: application/json

{
    "question": "Quy định về thời gian hiệu lực bảo đảm dự thầu trong Luật Đấu thầu 2023",
    "mode": "fast"
}
```

**Expected Response:**
```json
{
    "answer": "...",
    "sources": [...],  ← Có thể không có Điều 14 ở vị trí #1 (no reranking)
    "enhanced_features": [],  ← ❌ Không có reranking
    "processing_time_ms": 300  ← ~200-400ms (fast, no reranking)
}
```

**Verify:**
- ✅ `processing_time_ms` nhanh hơn balanced (~200-400ms)
- ✅ `enhanced_features` không có "reranking"
- ⚠️ Ranking có thể kém chính xác hơn (không có reranking)

---

### Test 5: Quality Mode WITH Reranking + RRF
**Quality mode: RAG-Fusion + Reranking (chất lượng cao nhất)**

**Request:**
```http
POST http://localhost:8000/ask
Content-Type: application/json

{
    "question": "So sánh bảo đảm dự thầu và bảo đảm thực hiện hợp đồng",
    "mode": "quality"
}
```

**Expected Response:**
```json
{
    "answer": "Bảo đảm dự thầu và bảo đảm thực hiện hợp đồng là hai loại bảo đảm khác nhau...",
    "sources": [
        "Điều 14. Bảo đảm dự thầu...",
        "Điều 68. Bảo đảm thực hiện hợp đồng...",
        ...
    ],
    "enhanced_features": ["query_enhancement", "rag_fusion", "reranking"],
    "processing_time_ms": 1500  ← ~1000-2000ms (quality mode + reranking)
}
```

**Verify:**
- ✅ Answer bao quát cả 2 khía cạnh
- ✅ Sources có cả Điều 14 và Điều 68
- ✅ `enhanced_features` có "reranking"
- ✅ Thời gian xử lý cao hơn (chất lượng đổi lại tốc độ)

---

### Test 6: Complex Query - Multi-aspect
**Test câu hỏi phức tạp với nhiều khía cạnh**

**Request:**
```http
POST http://localhost:8000/ask
Content-Type: application/json

{
    "question": "Phân tích chi tiết điều kiện tham gia đấu thầu và quy trình đánh giá hồ sơ dự thầu theo Luật Đấu thầu 2023",
    "mode": "quality"
}
```

**Expected:**
- Sources bao gồm nhiều điều liên quan (Điều 5, 12, 18, 25...)
- Reranking giúp xếp hạng đúng các điều quan trọng nhất lên đầu
- Processing time: ~1500-2500ms

---

### Test 7: Edge Case - Abbreviation
**Test với từ viết tắt (query enhancement + reranking)**

**Request:**
```http
POST http://localhost:8000/ask
Content-Type: application/json

{
    "question": "HSMT là gì?",
    "mode": "balanced"
}
```

**Expected:**
- Query enhancement expand: HSMT → Hồ sơ mời thầu
- Reranking rank đúng các điều về HSMT
- Answer giải thích "Hồ sơ mời thầu"

---

## 🧪 Performance Comparison

### Benchmark: Cùng 1 câu hỏi, các mode khác nhau

**Query:** "Quy định về bảo đảm dự thầu"

| Mode | Reranking | Processing Time | Top Source |
|------|-----------|-----------------|------------|
| **fast** | ❌ | ~200-400ms | Random |
| **balanced** | ✅ | ~500-1000ms | Điều 14 ✅ |
| **quality** | ✅ + RRF | ~1000-2000ms | Điều 14 ✅ |
| **adaptive** | ✅ | ~300-1500ms | Điều 14 ✅ |

**Kết luận:**
- Fast: Nhanh nhưng ranking kém
- Balanced: Cân bằng tốt (recommended) ⭐
- Quality: Chậm nhưng chất lượng cao nhất
- Adaptive: Tự động điều chỉnh theo query

---

## 🔍 How to Verify Reranking is Working

### 1. Check Enhanced Features
```json
"enhanced_features": ["query_enhancement", "reranking"]
```
✅ Phải có "reranking" trong balanced/quality/adaptive mode

### 2. Check Processing Time
- **Without reranking (fast):** ~200-400ms
- **With reranking (balanced):** ~500-1000ms (+100-400ms overhead)
- **With reranking + RRF (quality):** ~1000-2000ms

### 3. Check Source Ranking Quality
Test với câu hỏi "bảo đảm dự thầu":
- ✅ **With reranking:** Điều 14 xuất hiện đầu tiên (score 0.9859)
- ❌ **Without reranking:** Có thể Điều 25 hoặc Điều 68 lên đầu (sai)

### 4. Server Logs
Khi reranking enabled, server logs sẽ có:
```
🔧 Initializing reranker: BAAI/bge-reranker-v2-m3
💻 No GPU detected, using CPU
(hoặc 🎮 GPU detected! Using CUDA for acceleration)
```

---

## 🐛 Troubleshooting

### Issue 1: Reranking Not Applied
**Symptoms:** 
- `enhanced_features` không có "reranking"
- Processing time nhanh (~200-400ms)
- Sources ranking không chính xác

**Solutions:**
1. Check config: `config/models.py` → `enable_reranking = True`
2. Check mode: Fast mode không dùng reranking (by design)
3. Restart server: `Ctrl+C` và `./start_server.sh` lại

### Issue 2: CUDA Warning
**Warning:**
```
CUDA initialization: CUDA unknown error...
```

**Fix:** Đã xử lý! Reranker tự động fallback sang CPU. Warning không ảnh hưởng chức năng.

### Issue 3: Slow Processing
**If processing time > 3000ms:**
- Check network: OpenAI API có chậm không?
- Check query complexity: Query quá dài (>200 words)?
- Check mode: Quality mode chậm nhất (expected)

---

## 📊 Expected Results Summary

### ✅ Success Indicators

1. **Config OK:**
   - `GET /stats` → `reranking: true`

2. **Balanced Mode:**
   - Processing time: 500-1000ms
   - Enhanced features: ["query_enhancement", "reranking"]
   - Top source: Điều 14 cho query về "bảo đảm dự thầu"

3. **Quality Mode:**
   - Processing time: 1000-2000ms
   - Enhanced features: ["query_enhancement", "rag_fusion", "reranking"]
   - Comprehensive sources

4. **Fast Mode:**
   - Processing time: 200-400ms
   - Enhanced features: [] (empty)
   - No reranking (by design)

---

## 🎯 Quick Test Checklist

```
□ Server đang chạy (GET /health → db: true)
□ Reranking enabled (GET /stats → reranking: true)
□ Balanced mode có reranking (POST /ask với mode=balanced)
□ Fast mode không có reranking (POST /ask với mode=fast)
□ Sources ranking chính xác (Điều 14 lên đầu cho query "bảo đảm dự thầu")
□ Processing time hợp lý (balanced: 500-1000ms, fast: 200-400ms)
```

---

## 📝 Notes

- **GPU Support:** Hiện tại chạy CPU, khi deploy lên máy có GPU sẽ nhanh hơn 3-5x
- **Model Size:** BGE model 2.27GB, đã download sẵn trong `~/.cache/huggingface/`
- **Backward Compatible:** Có thể tắt reranking bằng `enable_reranking=False` trong config

---

*Last updated: October 23, 2025*
*Server: http://localhost:8000*
*Model: BAAI/bge-reranker-v2-m3*
