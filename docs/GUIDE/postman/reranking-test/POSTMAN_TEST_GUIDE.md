# Postman Test Guide - Reranking Integration

## 📦 Import Collection

**File:** `postman_reranking_tests.json`

**Cách import:**
1. Mở Postman
2. Click "Import" (góc trên bên trái)
3. Chọn file `postman_reranking_tests.json`
4. Collection "RAG-Bidding - Reranking Integration Tests" sẽ xuất hiện

## 🎯 Test Structure

### 📁 Folder 1: Setup & Health (2 tests)
Kiểm tra server và config trước khi test

1. **Health Check** - Verify API server đang chạy
2. **Get System Stats** - Verify reranking enabled trong config

### 📁 Folder 2: Reranking Tests (4 tests)
Test các modes khác nhau với/không có reranking

3. **Balanced Mode - WITH Reranking** ⭐ Main test
   - Query: "Quy định về thời gian hiệu lực bảo đảm dự thầu"
   - Expected: Điều 14 rank #1, có reranking
   - Time: ~500-1000ms

4. **Fast Mode - WITHOUT Reranking**
   - Same query
   - Expected: Nhanh hơn, KHÔNG có reranking
   - Time: ~200-400ms

5. **Quality Mode - WITH Reranking + RRF**
   - Query: "So sánh bảo đảm dự thầu và bảo đảm thực hiện hợp đồng"
   - Expected: RAG-Fusion + Reranking, chất lượng cao nhất
   - Time: ~1000-2000ms

6. **Adaptive Mode - WITH Reranking**
   - Query: "Điều kiện tham gia đấu thầu?"
   - Expected: Tự động điều chỉnh K + reranking

### 📁 Folder 3: Ranking Quality Tests (3 tests)
Verify reranking cải thiện ranking quality

7. **Test - Điều 14 Ranking** (Bảo đảm dự thầu)
   - Verify Điều 14 xuất hiện trong top 3
   - BGE score: 0.9859 (excellent)

8. **Test - Multi-aspect Query**
   - Query có 2 khía cạnh: bảo lãnh dự thầu + thực hiện
   - Verify cả 2 aspects được cover

9. **Test - Complex Legal Query**
   - Query phức tạp với nhiều yêu cầu
   - Verify answer comprehensive

### 📁 Folder 4: Performance & Edge Cases (4 tests)
Test performance và edge cases

10. **Performance - Same Query All Modes**
    - Benchmark cùng 1 query với các modes
    - Compare processing times

11. **Edge Case - Short Query** (HSMT?)
    - Test với abbreviation
    - Query enhancement + reranking

12. **Edge Case - Empty Question**
    - Test error handling
    - Expected: 400 Bad Request

13. **Stress Test - Very Long Query**
    - Query >100 words
    - Test reranking với query phức tạp

### 📁 Folder 5: Comparison Tests (1 test)
So sánh trực tiếp giữa modes

14. **Compare - Balanced vs Fast**
    - Run 2 lần với modes khác nhau
    - So sánh results

## 🚀 Cách Chạy Tests

### Option 1: Run từng test (Recommended)
1. Click vào test muốn chạy
2. Click "Send"
3. Xem results trong "Test Results" tab
4. Check logs trong Console (View → Show Postman Console)

### Option 2: Run toàn bộ collection
1. Click vào collection name
2. Click "Run" button (góc phải)
3. Select tests muốn run
4. Click "Run RAG-Bidding - Reranking..."
5. Xem results summary

### Option 3: Run từng folder
1. Click vào folder (vd: "Reranking Tests")
2. Click "Run" button
3. Chạy tất cả tests trong folder

## ✅ Expected Test Results

### All Tests Should Pass ✅

**Setup & Health:**
- ✅ Health check returns `{db: true}`
- ✅ Stats shows `reranking: true`

**Reranking Tests:**
- ✅ Balanced mode: ~500-1000ms, has "reranking" feature
- ✅ Fast mode: ~200-400ms, NO "reranking"
- ✅ Quality mode: ~1000-2000ms, has "reranking" + "rag_fusion"
- ✅ Adaptive mode: Variable time, has "reranking"

**Ranking Quality:**
- ✅ Điều 14 in top 3 for "bảo đảm dự thầu" query
- ✅ Multi-aspect query covered comprehensively
- ✅ Complex query returns detailed answer

**Edge Cases:**
- ✅ Short query handled correctly
- ✅ Empty query returns 400 error
- ✅ Long query processed within 5 seconds

## 📊 Performance Benchmarks

### Expected Processing Times

| Mode | Reranking | Typical Time | Use Case |
|------|-----------|--------------|----------|
| **Fast** | ❌ | 200-400ms | Simple queries, speed priority |
| **Balanced** | ✅ | 500-1000ms | Most queries, balanced ⭐ |
| **Quality** | ✅ + RRF | 1000-2000ms | Complex queries, quality priority |
| **Adaptive** | ✅ | 300-1500ms | Auto-adjust based on complexity |

### Reranking Overhead
- **Without reranking (fast):** Baseline
- **With reranking (balanced):** +100-400ms overhead
- **GPU acceleration:** Expected ~3-5x faster (not on this machine)

## 🔍 How to Verify Reranking Works

### 1. Check Enhanced Features
Look for `"enhanced_features"` in response:
```json
{
    "enhanced_features": ["query_enhancement", "reranking"]
}
```
✅ Balanced/Quality/Adaptive should have "reranking"
❌ Fast should NOT have "reranking"

### 2. Check Processing Time
- Fast mode: ~200-400ms (no reranking)
- Balanced mode: ~500-1000ms (with reranking)
- Difference ~100-400ms = reranking overhead

### 3. Check Ranking Quality
Query: "Quy định về bảo đảm dự thầu"

**With reranking (Balanced):**
```json
{
    "sources": [
        "Điều 14. Bảo đảm dự thầu...",  ← ✅ Correct!
        "Điều 25...",
        "Điều 68..."
    ]
}
```

**Without reranking (Fast):**
```json
{
    "sources": [
        "Điều 25...",  ← ❌ Không chính xác
        "Điều 68...",
        "Điều 14..."
    ]
}
```

### 4. Server Logs
Check server console for reranking initialization:
```
🔧 Initializing reranker: BAAI/bge-reranker-v2-m3
💻 No GPU detected, using CPU
```

## 🎨 Postman Test Scripts

Collection có automated test assertions:

**Example test script:**
```javascript
pm.test("Top source contains 'Điều 14'", function () {
    var jsonData = pm.response.json();
    var topSource = jsonData.sources[0];
    pm.expect(topSource).to.include('Điều 14');
});
```

**Variables tracked:**
- `balanced_time`: Processing time cho balanced mode
- `fast_time`: Processing time cho fast mode
- `quality_time`: Processing time cho quality mode

## 🐛 Troubleshooting

### ❌ Test Failed: "Connection refused"
**Problem:** Server không chạy

**Solution:**
```bash
# Terminal 1
cd /home/sakana/Code/RAG-bidding
source ~/anaconda3/etc/profile.d/conda.sh
conda activate venv
python -m uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

### ❌ Test Failed: "Reranking not enabled"
**Problem:** Config có `enable_reranking = False`

**Solution:**
Check `config/models.py`:
```python
enable_reranking: bool = _env_bool("ENABLE_RERANKING", True)  # Should be True
```

### ⚠️ Warning: "CUDA initialization error"
**Status:** Not a problem! ✅

**Explanation:**
- Máy này không có GPU
- Reranker tự động fallback sang CPU
- Vẫn hoạt động bình thường, chỉ chậm hơn

### ❌ Test Failed: "Processing time too slow"
**Possible causes:**
1. OpenAI API chậm (network issue)
2. Database query chậm
3. CPU overloaded

**Check:**
- Server logs for specific bottleneck
- Network connection to OpenAI
- System resources (htop/top)

## 📝 Test Checklist

Run tests theo thứ tự:

```
□ 1. Health Check (verify server running)
□ 2. Get System Stats (verify reranking enabled)
□ 3. Balanced Mode (main reranking test)
□ 4. Fast Mode (verify no reranking)
□ 5. Quality Mode (verify RRF + reranking)
□ 6. Adaptive Mode (verify dynamic K)
□ 7. Điều 14 Ranking (verify ranking quality)
□ 8. Multi-aspect Query (verify comprehensive)
□ 9. Complex Query (verify handles complexity)
□ 10. Performance Benchmark (compare modes)
□ 11. Short Query (verify expansion)
□ 12. Empty Query (verify error handling)
□ 13. Long Query (stress test)
□ 14. Comparison Test (direct comparison)
```

## 📚 Additional Resources

- **API Documentation:** `/docs` endpoint (Swagger UI)
- **Config File:** `config/models.py`
- **Reranker Implementation:** `src/retrieval/ranking/bge_reranker.py`
- **Integration Summary:** `docs/GUIDE/phase 2/RERANKING_INTEGRATION_SUMMARY.md`
- **Test Guide:** `docs/GUIDE/phase 2/POSTMAN_RERANKING_TEST.md`

## 🎯 Quick Start

```bash
# 1. Start server
cd /home/sakana/Code/RAG-bidding
./start_server.sh

# 2. Open Postman and import postman_reranking_tests.json

# 3. Run "Setup & Health" folder first

# 4. Run "Reranking Tests" folder to verify integration

# 5. Check results in Test Results tab
```

## ✨ Key Test Cases to Focus On

### 🔥 Must-Pass Tests:
1. **Test #3: Balanced Mode** - Main reranking test
   - Verify Điều 14 ranks #1
   - Verify "reranking" in enhanced_features
   
2. **Test #4: Fast Mode** - Verify no reranking
   - Verify faster than balanced
   - Verify NO "reranking" in features

3. **Test #7: Điều 14 Ranking** - Quality check
   - Verify correct article ranked top
   - Validate BGE reranker working

### 📈 Performance Tests:
- **Test #10:** Compare all modes with same query
- **Test #14:** Direct comparison balanced vs fast

### 🧪 Edge Cases:
- **Test #11:** Short query (abbreviation)
- **Test #12:** Error handling (empty query)
- **Test #13:** Stress test (long query)

---

**Last Updated:** October 23, 2025  
**Model:** BAAI/bge-reranker-v2-m3  
**Collection Version:** 1.0  
**Total Tests:** 14
