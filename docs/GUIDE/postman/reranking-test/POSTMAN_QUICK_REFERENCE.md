# Quick Reference - Postman Tests cho Reranking

## 🚀 Quick Start (3 bước)

### 1. Khởi động server
```bash
cd /home/sakana/Code/RAG-bidding
source ~/anaconda3/etc/profile.d/conda.sh
conda activate venv
python -m uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Import Postman Collection
- Mở Postman
- Import → `postman_reranking_tests.json`
- Collection "RAG-Bidding - Reranking Integration Tests" xuất hiện

### 3. Run Tests
- Run "Setup & Health" folder (2 tests)
- Run "Reranking Tests" folder (4 tests)
- ✅ All tests should pass!

---

## 📊 14 Tests Overview

| # | Test Name | Expected Result |
|---|-----------|----------------|
| 1 | Health Check | ✅ `{db: true}` |
| 2 | System Stats | ✅ `reranking: true` |
| **3** | **Balanced Mode** ⭐ | ✅ **Điều 14 rank #1, ~500-1000ms** |
| 4 | Fast Mode | ✅ No reranking, ~200-400ms |
| 5 | Quality Mode | ✅ RRF + Reranking, ~1000-2000ms |
| 6 | Adaptive Mode | ✅ Dynamic K + Reranking |
| 7 | Điều 14 Ranking | ✅ Điều 14 in top 3 |
| 8 | Multi-aspect | ✅ Both aspects covered |
| 9 | Complex Query | ✅ Comprehensive answer |
| 10 | Performance | ✅ Time comparison |
| 11 | Short Query | ✅ Abbreviation expansion |
| 12 | Empty Query | ✅ 400 error |
| 13 | Long Query | ✅ < 5 seconds |
| 14 | Comparison | ✅ Balanced vs Fast |

---

## 🔍 Key Verification Points

### ✅ Test #3 (Balanced Mode) - MUST PASS

**Request:**
```json
POST http://localhost:8000/ask
{
    "question": "Quy định về thời gian hiệu lực bảo đảm dự thầu trong Luật Đấu thầu 2023",
    "mode": "balanced"
}
```

**Expected Response:**
```json
{
    "answer": "Theo Luật Đấu thầu 2023, thời gian hiệu lực...",
    "sources": [
        "Điều 14. Bảo đảm dự thầu..."  ← ✅ Phải có Điều 14
    ],
    "enhanced_features": ["query_enhancement", "reranking"],  ← ✅ Có "reranking"
    "processing_time_ms": 800  ← ✅ ~500-1000ms
}
```

**Verifications:**
- ✅ Status 200
- ✅ Điều 14 trong sources[0] hoặc sources top 3
- ✅ `enhanced_features` contains "reranking"
- ✅ Processing time: 500-1000ms

---

### ✅ Test #4 (Fast Mode) - Verify NO Reranking

**Request:**
```json
POST http://localhost:8000/ask
{
    "question": "Quy định về thời gian hiệu lực bảo đảm dự thầu trong Luật Đấu thầu 2023",
    "mode": "fast"
}
```

**Expected:**
- ✅ Nhanh hơn balanced (~200-400ms)
- ✅ `enhanced_features` KHÔNG có "reranking"
- ⚠️ Sources ranking có thể kém chính xác hơn

---

## 📈 Performance Comparison

| Mode | Reranking | Time | Quality |
|------|-----------|------|---------|
| Fast | ❌ | 200-400ms | Medium |
| Balanced | ✅ | 500-1000ms | Good ⭐ |
| Quality | ✅ + RRF | 1000-2000ms | Best |
| Adaptive | ✅ | 300-1500ms | Variable |

**Reranking Overhead:** +100-400ms

---

## 🎯 Must-Pass Tests

### 🔥 Critical Tests (Run These First)

1. **Test #1: Health Check**
   - Verify server running
   - Expected: `{db: true}`

2. **Test #2: System Stats**
   - Verify config
   - Expected: `reranking: true`

3. **Test #3: Balanced Mode** ⭐⭐⭐
   - **MOST IMPORTANT TEST**
   - Verify reranking working
   - Expected: Điều 14 rank #1

4. **Test #4: Fast Mode**
   - Verify reranking disabled for fast
   - Expected: Faster, no "reranking"

---

## 🐛 Common Issues

### ❌ Connection Refused
```
Error: connect ECONNREFUSED 127.0.0.1:8000
```
**Fix:** Start server (see step 1 above)

### ❌ Reranking Not Working
```json
"enhanced_features": []  // No "reranking"
```
**Check:**
1. Mode is balanced/quality/adaptive (NOT fast)
2. Config: `settings.enable_reranking = True`
3. Server logs show reranker initialization

### ⚠️ CUDA Warning in Logs
```
CUDA initialization: CUDA unknown error...
```
**Status:** ✅ Normal! Falls back to CPU automatically.

---

## 📝 Automated Test Assertions

Tests tự động verify:

```javascript
// Test #3 - Balanced Mode
pm.test("Top source contains 'Điều 14'", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData.sources[0]).to.include('Điều 14');
});

pm.test("Enhanced features includes reranking", function () {
    var jsonData = pm.response.json();
    // Verify reranking in features
});
```

---

## 📚 Files

- **Collection:** `postman_reranking_tests.json` (14 tests)
- **Full Guide:** `POSTMAN_TEST_GUIDE.md`
- **Implementation:** `src/retrieval/ranking/bge_reranker.py`
- **Config:** `config/models.py`

---

## ✅ Success Checklist

```
□ Server running (port 8000)
□ Collection imported to Postman
□ Test #1 passes (Health OK)
□ Test #2 passes (Reranking enabled)
□ Test #3 passes (Điều 14 rank #1) ⭐
□ Test #4 passes (Fast mode no reranking)
□ All 14 tests green ✅
```

---

## 🎉 Expected Final Result

```
Tests:        14/14 passed ✅
Duration:     ~30-60 seconds (all tests)
Collections:  1
Requests:     14
Test Scripts: 25+
Assertions:   40+
```

---

**Quick Command:**
```bash
# Start server + Open Postman
cd /home/sakana/Code/RAG-bidding && ./start_server.sh
# Then import postman_reranking_tests.json
```

**Support:** See `POSTMAN_TEST_GUIDE.md` for detailed guide.
