# OpenAI Reranker - Setup & Usage Guide

**Created**: 2025-11-13  
**Status**: ✅ Implemented, Ready for Testing

## 🎯 Overview

OpenAI Reranker là tùy chọn reranking thứ 2 bên cạnh BGE Reranker, sử dụng GPT-4o-mini API để đánh giá độ liên quan của documents.

### So sánh BGE vs OpenAI Reranker

| Feature | BGE Reranker (Default) | OpenAI Reranker |
|---------|------------------------|-----------------|
| **Model** | BAAI/bge-reranker-v2-m3 | GPT-4o-mini |
| **Type** | Cross-encoder (local) | API-based (cloud) |
| **Memory** | 1.2GB GPU/RAM | 0 (no model loading) |
| **Latency** | 25-50ms (GPU) | 200-500ms (network) |
| **Cost** | Free | ~$0.01-0.05 per 1000 tokens |
| **Quality** | Excellent (multilingual) | Excellent (GPT understanding) |
| **Offline** | ✅ Yes | ❌ No (requires internet) |
| **Rate Limit** | None | OpenAI API limits |

### Khi nào dùng BGE vs OpenAI?

**Use BGE (Default)** khi:
- Production deployment với high throughput
- Cần low latency (<50ms)
- Không muốn phụ thuộc external API
- Có GPU available (RTX 3060+)

**Use OpenAI** khi:
- Testing/prototyping
- Low query volume (<100/day)
- Không có GPU mạnh
- Cần GPT-level understanding cho complex queries

---

## 📦 Implementation Files

### 1. Core Implementation

**File**: `src/retrieval/ranking/openai_reranker.py` (240 lines)

```python
class OpenAIReranker(BaseReranker):
    """
    OpenAI-based reranker using GPT-4o-mini.
    
    Features:
    - Scores documents 0-10 based on query relevance
    - Vietnamese language support
    - Automatic truncation to avoid token limits
    - Error handling for API failures
    """
    
    def __init__(
        self,
        model_name: str = "gpt-4o-mini",  # Default model
        api_key: Optional[str] = None,
        temperature: float = 0.0,  # Deterministic
        max_tokens: int = 10,  # Only need score
    )
```

**Key Methods**:
- `rerank(query, documents, top_k)`: Main reranking function
- `_score_document(query, doc)`: Score single document 0-1
- `rerank_batch(...)`: Batch processing (sequential)

### 2. Integration Points

**Retriever Factory** - `src/retrieval/retrievers/__init__.py`:

```python
def create_retriever(
    mode: str = "balanced",
    enable_reranking: bool = True,
    reranker_type: Literal["bge", "openai"] = "bge",  # 🆕
    ...
):
    if enable_reranking and reranker is None:
        if reranker_type == "bge":
            reranker = get_singleton_reranker()  # Singleton
        elif reranker_type == "openai":
            reranker = OpenAIReranker()  # New instance (no state)
```

**QA Chain** - `src/generation/chains/qa_chain.py`:

```python
def answer(
    question: str,
    mode: str | None = None,
    use_enhancement: bool = True,
    reranker_type: str = "bge",  # 🆕
) -> Dict:
    retriever = create_retriever(
        mode=selected_mode,
        enable_reranking=enable_reranking,
        reranker_type=reranker_type,  # Pass through
    )
```

**API Endpoint** - `src/api/main.py`:

```python
class AskIn(BaseModel):
    question: str
    mode: Literal["fast", "balanced", "quality", "adaptive"] = "balanced"
    reranker: Literal["bge", "openai"] = "bge"  # 🆕

@app.post("/ask")
def ask(body: AskIn):
    result = answer(
        body.question,
        mode=body.mode,
        reranker_type=body.reranker,  # 🆕
    )
```

---

## 🔧 Setup Instructions

### Step 1: Get OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Create new secret key
3. Copy the key (starts with `sk-...`)

### Step 2: Set Environment Variable

**Option A: Temporary (current terminal session)**

```bash
export OPENAI_API_KEY=sk-your-key-here
```

**Option B: Permanent (.env file)**

```bash
# Add to .env file
OPENAI_API_KEY=sk-your-key-here
```

**Option C: Permanent (.bashrc/.zshrc)**

```bash
echo 'export OPENAI_API_KEY=sk-your-key-here' >> ~/.zshrc
source ~/.zshrc
```

### Step 3: Install Dependencies

OpenAI Python library should already be installed (used for LLM). Verify:

```bash
python3 -c "import openai; print('✅ OpenAI installed')"
```

If not:

```bash
pip install openai
```

### Step 4: Restart Server

```bash
# Kill old server
pkill -f uvicorn

# Start with new env var
./start_server.sh
```

---

## 🚀 Usage Examples

### Example 1: Basic API Call with OpenAI Reranker

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "quy trình đấu thầu công khai",
    "mode": "balanced",
    "reranker": "openai"
  }'
```

**Response**:
```json
{
  "answer": "Quy trình đấu thầu công khai được quy định...",
  "sources": ["Luật Đấu thầu 2023, Điều 10", ...],
  "processing_time_ms": 3200
}
```

### Example 2: Compare BGE vs OpenAI

```python
import requests

url = "http://localhost:8000/ask"
query = "điều kiện tham gia đấu thầu"

# Test BGE
resp_bge = requests.post(url, json={
    "question": query,
    "mode": "balanced",
    "reranker": "bge"
})

# Test OpenAI
resp_openai = requests.post(url, json={
    "question": query,
    "mode": "balanced",
    "reranker": "openai"
})

print(f"BGE time:    {resp_bge.json()['processing_time_ms']}ms")
print(f"OpenAI time: {resp_openai.json()['processing_time_ms']}ms")
```

### Example 3: Programmatic Usage

```python
from src.retrieval.ranking import OpenAIReranker
from langchain_core.documents import Document

# Initialize reranker
reranker = OpenAIReranker(model_name="gpt-4o-mini")

# Mock documents
docs = [
    Document(page_content="Luật Đấu thầu quy định..."),
    Document(page_content="Nghị định 24/2024 hướng dẫn..."),
]

# Rerank
results = reranker.rerank(
    query="quy trình đấu thầu",
    documents=docs,
    top_k=5
)

for doc, score in results:
    print(f"{score:.4f} - {doc.page_content[:60]}...")
```

---

## 🧪 Testing

### Test Suite

**File**: `scripts/tests/test_openai_reranker.py`

```bash
# Run all tests
python3 scripts/tests/test_openai_reranker.py

# Run specific test
pytest scripts/tests/test_openai_reranker.py::test_openai_reranker_initialization -v
```

**Tests included**:
1. ✅ Initialization test
2. ✅ Scoring functionality
3. ✅ API integration
4. ✅ BGE vs OpenAI comparison

### Manual Testing

**Test 1: Check API Key**

```bash
python3 -c "
import os
from src.retrieval.ranking import OpenAIReranker

if not os.getenv('OPENAI_API_KEY'):
    print('❌ API key not set')
else:
    print('✅ API key found')
    reranker = OpenAIReranker()
    print(f'✅ Reranker initialized: {reranker.model_name}')
"
```

**Test 2: Basic Reranking**

```bash
python3 -c "
from src.retrieval.ranking import OpenAIReranker
from langchain_core.documents import Document

reranker = OpenAIReranker()
docs = [
    Document(page_content='Luật Đấu thầu 2023 quy định quy trình đấu thầu công khai.'),
    Document(page_content='Nghị định 24/2024 hướng dẫn chi tiết Luật Đấu thầu.'),
]

results = reranker.rerank('quy trình đấu thầu công khai', docs, top_k=2)
for i, (doc, score) in enumerate(results, 1):
    print(f'[{i}] {score:.4f} - {doc.page_content[:50]}...')
"
```

**Test 3: API Endpoint**

```bash
# Ensure server is running
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "quy trình đấu thầu công khai là gì?",
    "mode": "fast",
    "reranker": "openai"
  }' | python3 -m json.tool
```

---

## 💰 Cost Estimation

### OpenAI Pricing (as of 2025-11)

**GPT-4o-mini** (recommended):
- Input: $0.15 / 1M tokens
- Output: $0.60 / 1M tokens

### Example Calculation

**Scenario**: 100 queries/day, 10 docs/query, avg 200 tokens/doc

```
Input tokens:
- Query: 50 tokens × 100 queries = 5,000 tokens
- Documents: 200 tokens × 10 docs × 100 queries = 200,000 tokens
- Prompt overhead: ~50 tokens × 10 × 100 = 50,000 tokens
Total input: ~255,000 tokens/day

Output tokens:
- Score only: 5 tokens × 10 × 100 = 5,000 tokens/day

Daily cost:
- Input: 255k × $0.15 / 1M = $0.038
- Output: 5k × $0.60 / 1M = $0.003
Total: ~$0.04/day = $1.20/month
```

**For 1000 queries/day**: ~$12/month

### Cost Comparison

| Queries/Day | OpenAI Cost | BGE Cost | Savings with BGE |
|-------------|-------------|----------|------------------|
| 100 | $1.20/mo | $0 | $1.20 |
| 1,000 | $12/mo | $0 | $12 |
| 10,000 | $120/mo | $0 | $120 |

**Conclusion**: BGE is **free** and faster, but OpenAI offers easier setup (no GPU).

---

## 📊 Performance Characteristics

### Latency Breakdown

**BGE Reranker** (GPU):
```
Query enhancement:    200ms
Vector retrieval:     150ms
BGE reranking:        25-50ms   ← Fast!
LLM generation:       2000ms
──────────────────────────────
Total:                2375-2400ms
```

**OpenAI Reranker** (API):
```
Query enhancement:    200ms
Vector retrieval:     150ms
OpenAI reranking:     200-500ms ← Slower (network)
LLM generation:       2000ms
──────────────────────────────
Total:                2550-2850ms
```

**Impact**: +7-18% latency vs BGE

### Throughput

**BGE**: 
- Single instance: ~40 queries/sec (with GPU)
- Bottleneck: Vector retrieval, not reranking

**OpenAI**:
- Rate limit: 3,500 requests/min (GPT-4o-mini)
- Practical: ~10-20 queries/sec (network latency)
- Bottleneck: API rate limits

---

## 🔧 Configuration Options

### Model Selection

```python
# Default: GPT-4o-mini (recommended)
reranker = OpenAIReranker(model_name="gpt-4o-mini")

# Premium: GPT-4 Turbo (higher quality, 10x cost)
reranker = OpenAIReranker(model_name="gpt-4-turbo-preview")

# Budget: GPT-3.5 Turbo (lower quality, cheaper)
reranker = OpenAIReranker(model_name="gpt-3.5-turbo")
```

### Temperature & Tokens

```python
reranker = OpenAIReranker(
    temperature=0.0,    # Deterministic (recommended for ranking)
    max_tokens=10,      # Only need score number
)
```

### Document Truncation

Default: 2000 characters (~500 tokens) per document

```python
# In openai_reranker.py
max_doc_chars = 2000  # Adjust if needed
```

---

## 🐛 Troubleshooting

### Error 1: "OpenAI API key required"

```
ValueError: OpenAI API key required!
Set OPENAI_API_KEY environment variable or pass api_key parameter.
```

**Solution**:
```bash
export OPENAI_API_KEY=sk-your-key-here
./start_server.sh
```

### Error 2: "Invalid score format"

```
⚠️  Invalid score format: 'The document is relevant', using 0.0
```

**Cause**: GPT returned text instead of number

**Solution**: Already handled with try-except, defaults to 0.0

### Error 3: Rate Limit Exceeded

```
❌ OpenAI API error: Rate limit exceeded
```

**Solution**:
- Reduce query volume
- Upgrade OpenAI tier
- Switch to BGE reranker

### Error 4: Network Timeout

```
❌ OpenAI API error: Request timeout
```

**Solution**:
- Check internet connection
- Increase timeout in OpenAI client
- Use BGE for offline scenarios

---

## 🔄 Migration from BGE to OpenAI

### Step 1: Identify Current Usage

```bash
grep -r "get_singleton_reranker" src/
grep -r "BGEReranker" src/
```

### Step 2: Update API Calls

**Before**:
```python
retriever = create_retriever(mode="balanced", enable_reranking=True)
# Uses BGE by default
```

**After**:
```python
retriever = create_retriever(
    mode="balanced",
    enable_reranking=True,
    reranker_type="openai"  # 🆕 Switch to OpenAI
)
```

### Step 3: Test Backward Compatibility

```python
# Default behavior unchanged (still uses BGE)
retriever = create_retriever(mode="balanced")  # ✅ Still uses BGE

# Explicit BGE
retriever = create_retriever(mode="balanced", reranker_type="bge")

# New OpenAI option
retriever = create_retriever(mode="balanced", reranker_type="openai")
```

---

## 📋 Summary

✅ **Implemented**:
- OpenAI reranker class (`openai_reranker.py`)
- API endpoint toggle (`reranker` parameter)
- Integration with retriever factory
- Comprehensive test suite
- Cost-effective defaults (gpt-4o-mini)

🎯 **Usage**:
- Simple: Add `"reranker": "openai"` to API calls
- Default: Still uses BGE (backward compatible)
- Setup: Just need `OPENAI_API_KEY` env var

💡 **Recommendation**:
- **Production**: Use BGE (faster, free, offline)
- **Testing**: Use OpenAI (easier setup, no GPU)
- **Hybrid**: BGE for high-volume, OpenAI for complex queries

---

**Next Steps**:
1. Set `OPENAI_API_KEY` environment variable
2. Restart server: `./start_server.sh`
3. Test with: `curl -X POST http://localhost:8000/ask -d '{"question":"...", "reranker":"openai"}'`
4. Monitor costs at https://platform.openai.com/usage

**Documentation**: See also
- `documents/technical/reranking-analysis/TOM_TAT_TIENG_VIET.md` - BGE reranker guide
- `documents/technical/reranking-analysis/RERANKING_STRATEGIES.md` - Strategy comparison
