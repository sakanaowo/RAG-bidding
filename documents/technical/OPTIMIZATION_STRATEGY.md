# RAG System Optimization Strategy

## Current Performance Baseline
- **Retrieval**: 678ms average (target: <200ms)
- **E2E (with LLM)**: 5.4s average (target: <2s)
- **Bottleneck**: LLM generation (83% of total time)

## Industry Best Practices for RAG Optimization

### 1. **Vector Search Optimization** (Target: 678ms → <100ms)

#### A. Use Specialized Vector Databases
**Current**: PostgreSQL + pgvector
**Industry Standard**:
- **Pinecone** - Managed, ultra-fast (~20-50ms latency)
- **Weaviate** - Open-source, HNSW index (~30-80ms)
- **Qdrant** - Rust-based, high performance (~25-60ms)
- **Milvus** - Distributed, scalable (~40-100ms)

**Recommendation**: Keep PostgreSQL for now, but consider migration if scaling needed.

#### B. Optimize pgvector Configuration
```sql
-- Current index: IVFFlat (approximate search)
CREATE INDEX ON langchain_pg_embedding 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Optimization strategies:
-- 1. Tune lists parameter (sqrt(total_rows) to 4*sqrt(total_rows))
-- For 4,640 embeddings: lists = 68 to 272
-- Current 100 is good, but test 150-200

-- 2. Use HNSW index (more accurate, faster for reads)
CREATE INDEX ON langchain_pg_embedding 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 3. Enable parallel workers
SET max_parallel_workers_per_gather = 4;
```

#### C. Pre-filtering vs Post-filtering
```python
# Current: Post-filtering (search all, then filter)
# Better: Pre-filtering with partial indexes

# Create specialized indexes per document type
CREATE INDEX idx_law_embeddings ON langchain_pg_embedding 
USING ivfflat (embedding vector_cosine_ops)
WHERE cmetadata->>'document_type' = 'law';

CREATE INDEX idx_decree_embeddings ON langchain_pg_embedding 
USING ivfflat (embedding vector_cosine_ops)
WHERE cmetadata->>'document_type' = 'decree';
```

**Expected Improvement**: 678ms → 200-300ms

---

### 2. **Caching Strategy** (Critical for Production)

#### A. Query Result Cache
**Tools**: Redis, Memcached
**Implementation**:
```python
import redis
import hashlib

class CachedRetrieval:
    def __init__(self, vector_store, redis_client, ttl=3600):
        self.vector_store = vector_store
        self.redis = redis_client
        self.ttl = ttl
    
    def retrieve(self, query: str, k: int = 5, filters=None):
        # Generate cache key
        cache_key = self._generate_key(query, k, filters)
        
        # Try cache first
        cached = self.redis.get(cache_key)
        if cached:
            return pickle.loads(cached)
        
        # Miss: Query vector store
        docs = self.vector_store.similarity_search(query, k=k, filter=filters)
        
        # Cache result
        self.redis.setex(cache_key, self.ttl, pickle.dumps(docs))
        return docs
```

**Real-world Examples**:
- **Perplexity.ai**: Redis cache for embeddings + results (95% cache hit rate)
- **ChatGPT Plugins**: CDN + Redis for common queries
- **You.com**: Multi-layer cache (L1: memory, L2: Redis, L3: vector DB)

**Expected Improvement**: 200-300ms → <50ms for cached queries

#### B. Embedding Cache
```python
# Cache query embeddings to avoid re-embedding same queries
class EmbeddingCache:
    def __init__(self, embeddings_model, redis_client):
        self.model = embeddings_model
        self.redis = redis_client
    
    def embed_query(self, text: str):
        key = f"emb:{hashlib.md5(text.encode()).hexdigest()}"
        cached = self.redis.get(key)
        if cached:
            return pickle.loads(cached)
        
        embedding = self.model.embed_query(text)
        self.redis.setex(key, 86400, pickle.dumps(embedding))
        return embedding
```

---

### 3. **LLM Optimization** (Target: 4.5s → <1s)

#### A. Use Faster Models
**Current**: gpt-4o-mini (~4.5s per response)
**Alternatives**:

| Model | Latency | Quality | Cost |
|-------|---------|---------|------|
| **gpt-4o-mini** | 4.5s | High | $0.15/1M |
| **gpt-3.5-turbo** | 2-3s | Medium-High | $0.50/1M |
| **Claude 3 Haiku** | 1-2s | High | $0.25/1M |
| **Llama 3.1 8B** (local) | 0.5-1s | Medium | Free |
| **Mistral 7B** (local) | 0.3-0.8s | Medium | Free |

**Recommendation**: Test Claude 3 Haiku (best balance: fast + quality)

#### B. Streaming Responses
```python
# Instead of waiting for full response, stream tokens
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    streaming=True,
    callbacks=[StreamingStdOutCallbackHandler()]
)

# User sees first tokens in ~500ms instead of 4.5s
```

**Real-world**: All major RAG systems (ChatGPT, Claude, Perplexity) use streaming

#### C. Prompt Optimization
```python
# Current prompt: Detailed instructions + full context
# Optimized: Shorter prompt, structured format

OPTIMIZED_PROMPT = """Dựa trên văn bản sau, trả lời ngắn gọn:

{context}

Câu hỏi: {question}
Trả lời:"""

# Reduces input tokens by 30-50% → faster + cheaper
```

#### D. Response Length Limiting
```python
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    max_tokens=150,  # Limit response length
)
# Shorter response = faster generation
```

---

### 4. **Hybrid Search** (Improve Accuracy + Speed)

**Combine dense (vector) + sparse (keyword) retrieval**

#### Implementation:
```python
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever

# BM25 for keyword matching (very fast: ~10-20ms)
bm25_retriever = BM25Retriever.from_documents(documents)
bm25_retriever.k = 5

# Vector retriever (current: ~678ms)
vector_retriever = vector_store.as_retriever(search_kwargs={"k": 5})

# Ensemble: Combine both
ensemble_retriever = EnsembleRetriever(
    retrievers=[bm25_retriever, vector_retriever],
    weights=[0.3, 0.7]  # 30% BM25, 70% vector
)
```

**Real-world Examples**:
- **Pinecone**: Hybrid search built-in
- **Weaviate**: BM25 + vector combined
- **Elastic**: Vector + keyword search fusion

**Expected Improvement**: Better relevance + potential speed gain

---

### 5. **Reranking** (Improve Quality, Small Latency Cost)

**Use lightweight reranker to improve top-k results**

```python
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder

# Retrieve more documents (k=20)
base_retriever = vector_store.as_retriever(search_kwargs={"k": 20})

# Rerank to get best 5
model = HuggingFaceCrossEncoder(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
compressor = CrossEncoderReranker(model=model, top_n=5)

reranker = ContextualCompressionRetriever(
    base_compressor=compressor,
    base_retriever=base_retriever
)

# Cost: ~100-200ms reranking, but much better results
```

**Real-world**:
- **Perplexity.ai**: Uses Cohere rerank API
- **You.com**: Custom reranker
- **ChatGPT**: Proprietary reranking

**Vietnamese Reranker Options**:
- `vinai/phobert-base` fine-tuned for ranking
- `bge-reranker-v2-m3` (multilingual, works well for Vietnamese)

---

### 6. **Infrastructure Optimization**

#### A. Connection Pooling
```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

# Current: New connection per query
# Better: Reuse connections
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)
```

#### B. Batch Processing
```python
# Process multiple queries in parallel
import asyncio

async def batch_retrieve(queries: List[str], k: int = 5):
    tasks = [
        asyncio.to_thread(vector_store.similarity_search, q, k)
        for q in queries
    ]
    return await asyncio.gather(*tasks)

# Throughput: 1 query/s → 10+ queries/s
```

#### C. GPU Acceleration (for local LLMs)
```python
# Use vLLM for 10-100x faster inference
from vllm import LLM

llm = LLM(
    model="meta-llama/Llama-3.1-8B-Instruct",
    gpu_memory_utilization=0.9,
    max_model_len=4096
)

# Latency: 4.5s → 0.3-0.8s (on GPU)
```

---

### 7. **Monitoring & Profiling** (Essential)

#### Tools:
- **LangSmith**: LangChain's official monitoring (traces, latency, costs)
- **Weights & Biases**: Experiment tracking
- **Prometheus + Grafana**: Metrics visualization
- **OpenTelemetry**: Distributed tracing

```python
from langsmith import Client
from langchain.callbacks import LangChainTracer

# Enable tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "your-api-key"

# Automatic latency tracking, cost analysis, error monitoring
```

---

## Recommended Implementation Roadmap

### Phase 1: Quick Wins (1-2 days, 50% improvement)
1. ✅ **Add Redis caching** for query results
   - Expected: 678ms → <50ms (cached), 300ms (uncached)
2. ✅ **Enable streaming** for LLM responses
   - Expected: 4.5s perceived → 0.5s first token
3. ✅ **Optimize pgvector index** (tune lists parameter)
   - Expected: 678ms → 400-500ms
4. ✅ **Add connection pooling**
   - Expected: 10-15% improvement

### Phase 2: Medium Effort (3-5 days, 70% improvement)
1. **Implement hybrid search** (BM25 + vector)
   - Expected: Better accuracy + potential speed gain
2. **Add reranking** with Vietnamese model
   - Expected: +100-200ms latency, +30% accuracy
3. **Optimize prompts** and limit response length
   - Expected: 4.5s → 2-3s
4. **Set up monitoring** with LangSmith
   - Expected: Visibility into bottlenecks

### Phase 3: Long-term (1-2 weeks, 90% improvement)
1. **Migrate to specialized vector DB** (Weaviate/Qdrant)
   - Expected: 678ms → 50-100ms
2. **Deploy local LLM** (Llama 3.1 8B with vLLM)
   - Expected: 4.5s → 0.5-1s (on GPU)
3. **Implement multi-layer caching** (L1: memory, L2: Redis)
   - Expected: 95%+ cache hit rate
4. **Auto-scaling infrastructure** (Kubernetes)
   - Expected: Handle 100+ concurrent users

---

## Target Metrics After Optimization

| Metric | Current | After Phase 1 | After Phase 2 | After Phase 3 |
|--------|---------|---------------|---------------|---------------|
| Retrieval (cold) | 678ms | 400ms | 300ms | 80ms |
| Retrieval (cached) | N/A | <50ms | <50ms | <10ms |
| E2E (first token) | 5.4s | 1.5s | 1s | 0.5s |
| E2E (full response) | 5.4s | 4s | 2.5s | 1.2s |
| Throughput | 1 qps | 5 qps | 20 qps | 100+ qps |
| Cost per query | $0.002 | $0.0015 | $0.001 | $0.0002 |

---

## Real-world Benchmarks (for reference)

### Production RAG Systems:
- **Perplexity.ai**: <1s first token, 2-3s full response
- **ChatGPT (with retrieval)**: 0.5-1s first token, 3-5s full
- **You.com**: <500ms first token, 1-2s full
- **Phind.com**: <300ms first token, 1-2s full

### Vector Search Benchmarks:
- **Pinecone**: p50=20ms, p95=50ms, p99=100ms
- **Weaviate**: p50=30ms, p95=80ms, p99=150ms
- **Qdrant**: p50=25ms, p95=60ms, p99=120ms
- **pgvector (optimized)**: p50=100ms, p95=300ms, p99=600ms

---

## Conclusion

**Priority order for optimization:**
1. **Caching (Redis)** - Biggest impact for production use
2. **Streaming** - Best UX improvement
3. **Index tuning** - Free performance gain
4. **Reranking** - Quality improvement
5. **Hybrid search** - Accuracy + speed
6. **Specialized vector DB** - Long-term scalability
7. **Local LLM** - Cost reduction + speed (if GPU available)

**Next steps**: Start with Phase 1 (caching + streaming)?
