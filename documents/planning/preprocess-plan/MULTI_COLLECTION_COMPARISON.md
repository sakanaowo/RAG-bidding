# 🔍 COMPARISON: Multi-Collection Architecture vs Current System

**Date:** December 2024  
**Purpose:** Compare recommended multi-collection architecture with current RAG implementation

---

## 📊 TL;DR - QUICK COMPARISON

| Aspect | Recommended (Multi-Collection) | Current System | Gap Analysis |
|--------|-------------------------------|----------------|--------------|
| **Collections** | 3 separate (legal, reports, templates) | 1 unified ("docs") | ❌ No separation |
| **Indexing** | BM25 + Dense hybrid | Dense only (pgvector) | ❌ No BM25 |
| **Weighting** | Collection-specific boost (3.0, 1.5, 1.0) | Equal weight | ❌ No prioritization |
| **Query Classification** | Intent-based (specific vs conceptual) | No classification | ❌ No intent detection |
| **Parallel Retrieval** | Yes (from all collections) | N/A (single collection) | ❌ No parallelization |
| **Weighted Merging** | Adaptive [0.7,0.2,0.1] or [0.5,0.3,0.2] | N/A | ❌ No weighted fusion |
| **Hierarchy Context** | Store & display full path | ✅ Store (metadata) | ⚠️ Partial (store yes, display?) |
| **Status Filtering** | Always filter active | ✅ filter_status="active" | ✅ IMPLEMENTED |
| **Reranking** | Authority + recency weighted | ✅ BGE cross-encoder | ✅ IMPLEMENTED |

**Overall Assessment:** 
- ✅ Current system: Strong on reranking, filtering
- ❌ Missing: Multi-collection, BM25, intent classification, weighted merging

---

## 🏗️ ARCHITECTURE COMPARISON

### Recommended Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Query Processing                        │
├─────────────────────────────────────────────────────────────┤
│  1. Intent Classification                                   │
│     ├─ Specific query → [0.7, 0.2, 0.1] weights            │
│     └─ Conceptual query → [0.5, 0.3, 0.2] weights          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              Parallel Retrieval (3 Collections)             │
├───────────────────┬──────────────────────┬──────────────────┤
│ van_ban_phap_luat │ bao_cao_nghien_cuu   │ mau_van_ban     │
│ (Legal Docs)      │ (Reports)            │ (Templates)      │
├───────────────────┼──────────────────────┼──────────────────┤
│ Tier: 1           │ Tier: 2              │ Tier: 3          │
│ Boost: 3.0        │ Boost: 1.5           │ Boost: 1.0       │
│ Index: BM25+Dense │ Index: Dense only    │ Index: BM25+Dense│
│ Filter: active    │ Filter: active       │ Filter: active   │
└───────────────────┴──────────────────────┴──────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Weighted Merging                         │
│  - Apply collection weights [0.7, 0.2, 0.1]                │
│  - Combine scores: score' = score × boost × weight         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                 Reranking + Filtering                       │
│  - Authority scoring (legal > reports > templates)         │
│  - Recency scoring (newer = higher)                        │
│  - Final ranking                                            │
└─────────────────────────────────────────────────────────────┘
```

### Current System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Query Processing                        │
│  - Query Enhancement (Multi-Query, HyDE, Step-Back, etc.)  │
│  - No intent classification                                 │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              Single Collection Retrieval                    │
│                    "docs" (unified)                         │
├─────────────────────────────────────────────────────────────┤
│ - Dense vector search only (pgvector)                      │
│ - Metadata filter: status="active"                         │
│ - No collection-based prioritization                       │
│ - Retrieve k=5-10 documents                                │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  Reranking (Optional)                       │
│  - BGE cross-encoder (bge-reranker-v2-m3)                  │
│  - GPU/CPU auto-detection                                  │
│  - Rerank top-k documents                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔍 DETAILED FEATURE COMPARISON

### 1. Collection Strategy

#### Recommended: Multi-Collection
```python
# 3 separate collections with different characteristics
collections = {
    "van_ban_phap_luat": {
        "tier": 1,
        "boost": 3.0,
        "index": ["BM25", "dense"],
        "types": ["law", "decree", "circular", "decision"],
        "priority": "highest",  # Most authoritative
    },
    "bao_cao_nghien_cuu": {
        "tier": 2,
        "boost": 1.5,
        "index": ["dense"],  # Conceptual, dense-only better
        "types": ["report", "research"],
        "priority": "medium",
    },
    "mau_van_ban": {
        "tier": 3,
        "boost": 1.0,
        "index": ["BM25", "dense"],
        "types": ["template", "form", "exam"],
        "priority": "low",
    },
}

# Retrieval
results = []
for collection, config in collections.items():
    docs = retrieve_from_collection(
        query=query,
        collection=collection,
        k=config["boost"] * base_k,  # More from higher tier
    )
    # Apply boost to scores
    for doc in docs:
        doc.score *= config["boost"]
    results.extend(docs)

# Weighted merging
final_docs = weighted_merge(results, weights=[0.7, 0.2, 0.1])
```

**Pros:**
- ✅ Explicit prioritization (legal > reports > templates)
- ✅ Different indexing strategies per collection type
- ✅ Fine-grained control over retrieval
- ✅ Easy to adjust weights per use case

**Cons:**
- ❌ More complex infrastructure (3 collections to maintain)
- ❌ Need parallel retrieval (more API calls)
- ❌ Harder to debug (which collection failed?)

#### Current: Single Unified Collection
```python
# Single collection "docs" with all document types
collection = "docs"

# Retrieval with metadata filtering
vector_store = PGVector(
    collection_name="docs",
    connection=database_url,
)

# Retrieve
filter_dict = {"status": "active"}  # Filter expired docs
docs = vector_store.similarity_search(
    query=query,
    k=5,
    filter=filter_dict,
)
```

**Pros:**
- ✅ Simple architecture (1 collection)
- ✅ Unified schema (same metadata structure)
- ✅ Single retrieval call (faster)
- ✅ Easy to debug

**Cons:**
- ❌ No inherent prioritization (legal = templates)
- ❌ Can't apply different indexing strategies
- ❌ Harder to boost specific document types

---

### 2. Indexing Strategy

#### Recommended: Hybrid BM25 + Dense

```python
# Collection-specific indexing
if collection == "van_ban_phap_luat":
    # Legal: BM25 for exact term matching (Điều X, Article Y)
    # + Dense for semantic similarity
    bm25_results = bm25_search(query, k=10)
    dense_results = vector_search(query, k=10)
    
    # Hybrid fusion (0.6 BM25 + 0.4 Dense for legal)
    results = merge([bm25_results, dense_results], weights=[0.6, 0.4])

elif collection == "bao_cao_nghien_cuu":
    # Reports: Dense only (more conceptual)
    results = vector_search(query, k=10)

elif collection == "mau_van_ban":
    # Templates: BM25 for form numbers (Mẫu số X)
    # + Dense for content
    bm25_results = bm25_search(query, k=10)
    dense_results = vector_search(query, k=10)
    results = merge([bm25_results, dense_results], weights=[0.5, 0.5])
```

**Why BM25 for Legal Docs:**
- Query: "Điều 15 Luật Đấu thầu 2013" → BM25 exact match wins
- Query: "quy định về năng lực tài chính" → Dense semantic wins
- Hybrid = best of both worlds

#### Current: Dense-Only (pgvector)

```python
# Only dense vector search
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vector_store = PGVector(
    embeddings=embeddings,
    collection_name="docs",
)

# Similarity search (cosine similarity on dense vectors)
docs = vector_store.similarity_search(query, k=5)
```

**Pros:**
- ✅ Good for semantic/conceptual queries
- ✅ Simple implementation
- ✅ Works with pgvector extension

**Cons:**
- ❌ Misses exact term matches (e.g., "Điều 15" vs "Điều 16")
- ❌ Can't leverage keyword matching
- ❌ Less effective for specific legal references

---

### 3. Query Intent Classification

#### Recommended: Intent-Based Weighting

```python
def classify_intent(query: str) -> str:
    """
    Classify query intent:
    - specific: Asking about specific Điều, Article, Law
    - conceptual: General concept, procedure, requirement
    """
    
    # Specific patterns
    specific_patterns = [
        r"Điều\s+\d+",          # Điều 15
        r"Luật\s+\S+\s+\d+",    # Luật Đấu thầu 2013
        r"Nghị định\s+\d+",     # Nghị định 63/2014
        r"Mẫu số\s+\d+",        # Mẫu số 5
    ]
    
    for pattern in specific_patterns:
        if re.search(pattern, query):
            return "specific"
    
    return "conceptual"

# Apply different weights based on intent
intent = classify_intent(query)

if intent == "specific":
    # Specific: Prioritize legal docs heavily
    collection_weights = [0.7, 0.2, 0.1]  # Legal 70%
elif intent == "conceptual":
    # Conceptual: More balanced
    collection_weights = [0.5, 0.3, 0.2]  # Legal 50%
```

**Example:**
```python
# Specific query
query1 = "Điều 15 Luật Đấu thầu quy định gì?"
→ Intent: specific
→ Weights: [0.7, 0.2, 0.1] (prioritize legal docs)

# Conceptual query
query2 = "Quy trình đánh giá hồ sơ dự thầu như thế nào?"
→ Intent: conceptual  
→ Weights: [0.5, 0.3, 0.2] (more balanced, reports help)
```

#### Current: No Intent Classification

```python
# All queries treated the same
retriever = create_retriever(mode="balanced")
docs = retriever.invoke(query)  # Same strategy for all queries
```

**Impact:**
- ❌ Specific queries may retrieve too many non-legal docs
- ❌ Conceptual queries may over-prioritize legal text
- ✅ But simpler to implement and maintain

---

### 4. Weighted Merging

#### Recommended: Adaptive Weighted Fusion

```python
def weighted_merge(
    results: Dict[str, List[Document]],
    weights: List[float],
    boost_factors: Dict[str, float],
) -> List[Document]:
    """
    Merge results from multiple collections with weights.
    
    Final score = (retrieval_score × collection_boost) × collection_weight
    """
    scored_docs = []
    
    collections = ["van_ban_phap_luat", "bao_cao_nghien_cuu", "mau_van_ban"]
    
    for i, collection in enumerate(collections):
        docs = results[collection]
        weight = weights[i]
        boost = boost_factors[collection]
        
        for doc in docs:
            # Combine scores
            final_score = doc.score * boost * weight
            
            scored_docs.append({
                "doc": doc,
                "score": final_score,
                "collection": collection,
            })
    
    # Sort by final score
    scored_docs.sort(key=lambda x: x["score"], reverse=True)
    
    return [item["doc"] for item in scored_docs[:k]]
```

**Example:**
```python
# Specific query: "Điều 15 Luật Đấu thầu"
results = {
    "van_ban_phap_luat": [  # Legal docs
        Document(score=0.95, content="Điều 15. Năng lực..."),
        Document(score=0.88, content="Điều 15 quy định..."),
    ],
    "bao_cao_nghien_cuu": [  # Reports
        Document(score=0.75, content="Phân tích Điều 15..."),
    ],
    "mau_van_ban": [  # Templates
        Document(score=0.60, content="Mẫu chứng minh năng lực..."),
    ],
}

weights = [0.7, 0.2, 0.1]  # Specific query
boosts = {"van_ban_phap_luat": 3.0, "bao_cao_nghien_cuu": 1.5, "mau_van_ban": 1.0}

# Calculate final scores
legal_doc1 = 0.95 × 3.0 × 0.7 = 1.995  ← Highest
legal_doc2 = 0.88 × 3.0 × 0.7 = 1.848
report_doc = 0.75 × 1.5 × 0.2 = 0.225
template_doc = 0.60 × 1.0 × 0.1 = 0.06  ← Lowest

# Result: Legal docs dominate (as expected for specific query)
```

#### Current: No Weighted Merging

```python
# All documents treated equally (no collection-based weighting)
docs = retriever.invoke(query)  # Returns top-k by similarity score only

# Optionally: Reranking (but not collection-aware)
if reranker:
    docs = reranker.rerank(query, docs)
```

**Impact:**
- ❌ Legal docs and templates have equal chance
- ❌ Can't enforce "legal docs should always rank higher"
- ✅ But simpler scoring (less to tune)

---

### 5. Hierarchy Preservation

#### Recommended: Store + Display Full Context

```python
# Chunk metadata includes FULL hierarchy
chunk = {
    "content": "1. Nhà thầu phải có vốn chủ sở hữu...",
    "metadata": {
        # Full hierarchy path
        "hierarchy": [
            "Luật Đấu thầu 43/2013/QH13",
            "CHƯƠNG II - Quy định về nhà thầu",
            "Mục 2 - Năng lực nhà thầu",
            "Điều 15 - Năng lực tài chính",
            "Khoản 1",
        ],
        # Individual levels (for filtering)
        "law_id": "43/2013/QH13",
        "chuong": "CHƯƠNG II",
        "muc": "Mục 2",
        "dieu": "15",
        "khoan": "1",
    },
}

# Display to user
def format_result(doc):
    hierarchy = doc.metadata["hierarchy"]
    return f"""
    📜 {hierarchy[0]}  # Law name
    📂 {hierarchy[1]}  # Chapter
    📂 {hierarchy[2]}  # Section  
    📍 {hierarchy[3]}  # Article
    
    {doc.content}
    """
```

**Output:**
```
📜 Luật Đấu thầu 43/2013/QH13
📂 CHƯƠNG II - Quy định về nhà thầu
📂 Mục 2 - Năng lực nhà thầu
📍 Điều 15 - Năng lực tài chính

1. Nhà thầu phải có vốn chủ sở hữu tối thiểu 100 tỷ đồng...
```

#### Current: Store Hierarchy (Partial Display?)

```python
# Current schema stores hierarchy
# (from Phase 1 V2 schema - UnifiedLegalChunk)

chunk_metadata = {
    "document_type": "decree",
    "legal_metadata": {
        "legal_id": "43/2013/QH13",
        "issued_by": "Quốc hội",
    },
    "content_structure": {
        "hierarchy": HierarchyPath(
            phan=None,
            chuong="CHƯƠNG II",
            muc="Mục 2",
            dieu="15",
            khoan="1",
        ),
    },
}
```

**Assessment:**
- ✅ Hierarchy IS stored in metadata
- ⚠️ Need to verify: Is hierarchy DISPLAYED to user in API response?
- ⚠️ Need to check: Does frontend show full context path?

---

### 6. Metadata Filtering

#### Recommended: Always Filter Active

```python
# Always filter by status
def retrieve(query, collection):
    filter_dict = {
        "status": "hiệu_lực",  # Active/valid documents only
        # Optional additional filters:
        # "jurisdiction": "trung_ương",
        # "doc_type": "luật",
    }
    
    return collection.search(query, filter=filter_dict)
```

#### Current: ✅ IMPLEMENTED

```python
# Already implemented in current system!
def create_retriever(
    mode: str = "balanced",
    filter_status: Optional[str] = "active",  # ✅ Default filter
):
    base = BaseVectorRetriever(
        k=5,
        filter_status=filter_status,  # ✅ Applied
    )
    ...

# BaseVectorRetriever._build_filter()
def _build_filter(self) -> Optional[Dict[str, Any]]:
    if self.filter_status == "active":
        return {"status": {"$eq": "active"}}
    elif self.filter_status == "expired":
        return {"status": {"$eq": "expired"}}
    return None
```

**Status:** ✅ **ALREADY IMPLEMENTED** - No gap here!

---

### 7. Reranking

#### Recommended: Authority + Recency Weighted

```python
def rerank_with_metadata(docs, query):
    """Rerank with authority and recency scores"""
    
    for doc in docs:
        # Base semantic score (from cross-encoder)
        semantic_score = cross_encoder.score(query, doc.content)
        
        # Authority score (collection tier)
        if doc.metadata["collection"] == "van_ban_phap_luat":
            authority_score = 1.0  # Highest authority
        elif doc.metadata["collection"] == "bao_cao_nghien_cuu":
            authority_score = 0.7
        else:
            authority_score = 0.5
        
        # Recency score (newer = better)
        days_old = (today - doc.metadata["issued_date"]).days
        recency_score = 1.0 / (1 + days_old / 365)  # Decay over years
        
        # Combined score
        doc.final_score = (
            0.6 * semantic_score +
            0.3 * authority_score +
            0.1 * recency_score
        )
    
    return sorted(docs, key=lambda x: x.final_score, reverse=True)
```

#### Current: ✅ Semantic Reranking (BGE)

```python
# BGE cross-encoder reranking
from src.retrieval.ranking import BGEReranker

reranker = BGEReranker(
    model_name="BAAI/bge-reranker-v2-m3",
    device="cuda",  # Auto-detect GPU
)

# Rerank based on semantic similarity only
reranked_docs = reranker.rerank(query, docs, top_k=5)
```

**Assessment:**
- ✅ Semantic reranking: IMPLEMENTED
- ❌ Authority-based boosting: NOT IMPLEMENTED
- ❌ Recency scoring: NOT IMPLEMENTED
- 💡 **Easy extension:** Add authority/recency to BGEReranker

---

## 📊 GAP ANALYSIS SUMMARY

### ✅ Already Implemented (Strong Points)

1. **Status Filtering** ✅
   - `filter_status="active"` by default
   - Can filter expired/active documents
   - Metadata-based filtering supported

2. **Reranking** ✅
   - BGE cross-encoder (SOTA model)
   - GPU auto-detection
   - Integrated with all retriever modes

3. **Hierarchy Storage** ✅
   - V2 schema stores full hierarchy
   - HierarchyPath model with all levels
   - Metadata includes legal_id, issuer, etc.

4. **Query Enhancement** ✅
   - Multi-Query, HyDE, Step-Back, Decomposition
   - RAG-Fusion with RRF
   - Adaptive K based on complexity

---

### ❌ Missing Features (Gaps)

#### Gap 1: Multi-Collection Architecture ❌

**Current:** Single "docs" collection  
**Needed:** 3 collections (legal, reports, templates)

**Impact:** 
- Can't prioritize legal docs over templates
- Can't apply different indexing strategies
- All document types treated equally

**Effort:** HIGH (requires DB restructure)

#### Gap 2: BM25 + Hybrid Search ❌

**Current:** Dense-only (pgvector)  
**Needed:** BM25 for exact term matching + Dense for semantic

**Impact:**
- Misses exact legal references (Điều 15, Mẫu số 5)
- Conceptual queries work well, specific queries suffer

**Effort:** MEDIUM (add BM25 index, fusion logic)

#### Gap 3: Intent Classification ❌

**Current:** All queries treated the same  
**Needed:** Classify specific vs conceptual queries

**Impact:**
- Specific queries get too many irrelevant docs
- Can't adapt retrieval strategy to query type

**Effort:** LOW (regex patterns + conditional weights)

#### Gap 4: Weighted Collection Merging ❌

**Current:** Equal weighting  
**Needed:** Boost legal docs 3x, reports 1.5x

**Impact:**
- Templates can rank higher than legal docs
- No explicit prioritization

**Effort:** MEDIUM (requires multi-collection first)

#### Gap 5: Authority + Recency Reranking ❌

**Current:** Semantic reranking only  
**Needed:** Authority (tier) + Recency (date) scores

**Impact:**
- Old documents rank same as new
- Non-authoritative sources equal to official laws

**Effort:** LOW (extend BGEReranker)

---

## 💡 RECOMMENDATIONS

### Phased Implementation Plan

#### **Phase 1: Low-Hanging Fruit (1-2 weeks)** 🍃

**Implement without major restructure:**

1. **Intent Classification** (2 days)
   ```python
   def classify_intent(query: str) -> str:
       if re.search(r"Điều\s+\d+|Luật\s+\S+\s+\d+", query):
           return "specific"
       return "conceptual"
   
   # Use in retrieval
   intent = classify_intent(query)
   if intent == "specific":
       k = 3  # Fewer, more precise results
   else:
       k = 7  # More diverse results
   ```

2. **Authority + Recency Reranking** (3 days)
   ```python
   class WeightedBGEReranker(BGEReranker):
       def rerank(self, query, docs, top_k):
           # 1. Semantic scoring (existing)
           docs = super().rerank(query, docs, top_k=top_k*2)
           
           # 2. Add authority score
           for doc in docs:
               doc_type = doc.metadata.get("document_type")
               if doc_type in ["law", "decree", "circular"]:
                   authority = 1.0
               elif doc_type == "report":
                   authority = 0.7
               else:
                   authority = 0.5
               
               # 3. Add recency score
               issued_date = doc.metadata.get("issued_date")
               if issued_date:
                   days = (today - issued_date).days
                   recency = 1.0 / (1 + days/365)
               else:
                   recency = 0.5
               
               # 4. Combine
               doc.score = 0.6*doc.score + 0.3*authority + 0.1*recency
           
           return sorted(docs, key=lambda x: x.score, reverse=True)[:top_k]
   ```

3. **Metadata-Based Boosting** (2 days)
   ```python
   # Add boost to retrieval without multi-collection
   def retrieve_with_boost(query, k):
       # Retrieve more docs initially
       docs = vector_store.similarity_search(query, k=k*3)
       
       # Apply boost based on document_type
       for doc in docs:
           doc_type = doc.metadata.get("document_type")
           if doc_type in ["law", "decree", "circular", "decision"]:
               doc.score *= 3.0  # Legal boost
           elif doc_type == "report":
               doc.score *= 1.5  # Report boost
           # Templates: no boost (1.0)
       
       # Re-sort and return top-k
       return sorted(docs, key=lambda x: x.score, reverse=True)[:k]
   ```

**Total Effort:** ~1 week  
**Impact:** Medium-High (better ranking without major changes)

---

#### **Phase 2: Hybrid Search (2-3 weeks)** 🔍

**Add BM25 without multi-collection:**

1. **Install BM25 Library** (1 day)
   ```bash
   pip install rank-bm25
   ```

2. **Create BM25 Index** (2 days)
   ```python
   from rank_bm25 import BM25Okapi
   from underthesea import word_tokenize  # Vietnamese tokenizer
   
   # Build BM25 index (one-time)
   corpus = [doc.page_content for doc in all_docs]
   tokenized_corpus = [word_tokenize(doc) for doc in corpus]
   bm25 = BM25Okapi(tokenized_corpus)
   
   # Save index
   import pickle
   with open("bm25_index.pkl", "wb") as f:
       pickle.dump(bm25, f)
   ```

3. **Hybrid Retrieval** (3 days)
   ```python
   class HybridRetriever(BaseRetriever):
       def __init__(self, vector_store, bm25_index):
           self.vector_store = vector_store
           self.bm25_index = bm25_index
       
       def retrieve(self, query, k=5):
           # 1. BM25 retrieval
           tokenized_query = word_tokenize(query)
           bm25_scores = self.bm25_index.get_scores(tokenized_query)
           bm25_top = np.argsort(bm25_scores)[-k*2:][::-1]
           
           # 2. Dense retrieval
           dense_docs = self.vector_store.similarity_search(query, k=k*2)
           
           # 3. Reciprocal Rank Fusion
           fused_docs = self._rrf_fusion(bm25_top, dense_docs)
           
           return fused_docs[:k]
   ```

4. **Query-Adaptive Weights** (2 days)
   ```python
   def adaptive_hybrid(query, intent):
       if intent == "specific":
           # Specific: Prefer BM25 (exact matches)
           weights = [0.7, 0.3]  # BM25, Dense
       else:
           # Conceptual: Prefer Dense (semantic)
           weights = [0.3, 0.7]
       
       return hybrid_search(query, weights)
   ```

**Total Effort:** ~2 weeks  
**Impact:** HIGH (better specific query handling)

---

#### **Phase 3: Multi-Collection (4-6 weeks)** 🏗️

**Full architectural change (optional, for long-term):**

1. **DB Schema Migration** (1 week)
   - Create 3 collections in Postgres
   - Migrate existing data
   - Update ingestion pipeline

2. **Parallel Retrieval** (1 week)
   - Implement async retrieval from all collections
   - Add collection-specific configurations

3. **Weighted Merging** (1 week)
   - Implement weighted fusion logic
   - Add intent-based weight adjustment

4. **Testing & Tuning** (1-2 weeks)
   - Benchmark retrieval quality
   - Tune weights and boosts
   - A/B testing

**Total Effort:** ~4-6 weeks  
**Impact:** VERY HIGH (full recommended architecture)

**Decision:** Defer to Phase 3 if Phase 1-2 results are satisfactory

---

## 🎯 FINAL RECOMMENDATION

### Immediate Actions (Next 2 Weeks)

**Implement Phase 1 + Start Phase 2:**

1. ✅ **Intent Classification** (2 days)
   - Regex-based specific vs conceptual
   - Adjust k and strategies accordingly

2. ✅ **Weighted Reranking** (3 days)
   - Extend BGEReranker with authority + recency
   - Test on real queries

3. ✅ **Metadata Boosting** (2 days)
   - Boost legal docs 3x in current single collection
   - Quick win without restructure

4. ✅ **Start BM25 Integration** (3 days)
   - Build BM25 index
   - Create hybrid retriever prototype

**Total:** ~10 days → **Achievable in 2 weeks**

### Long-Term Strategy

- **Phase 2 completion** (2-3 weeks): Full hybrid search
- **Evaluate Phase 2 results** (1 week): Measure improvement
- **Decide on Phase 3** (multi-collection): Only if Phase 2 insufficient

---

## 📝 COMPARISON TABLE: Feature Checklist

| Feature | Recommended | Current | Priority | Effort |
|---------|-------------|---------|----------|--------|
| Multi-collection | ✅ | ❌ | Medium | High |
| BM25 indexing | ✅ | ❌ | **HIGH** | Medium |
| Dense indexing | ✅ | ✅ | - | - |
| Intent classification | ✅ | ❌ | **HIGH** | Low |
| Parallel retrieval | ✅ | ❌ | Low | High |
| Weighted merging | ✅ | ❌ | Medium | Medium |
| Authority scoring | ✅ | ❌ | **HIGH** | Low |
| Recency scoring | ✅ | ❌ | Medium | Low |
| Status filtering | ✅ | ✅ | - | - |
| Hierarchy storage | ✅ | ✅ | - | - |
| Hierarchy display | ✅ | ⚠️ | Medium | Low |
| Cross-encoder reranking | ✅ | ✅ | - | - |

**Priority Legend:**
- **HIGH**: Significant impact, low-medium effort → Do first
- Medium: Good impact, but can defer
- Low: Nice-to-have, complex to implement

---

## 💬 CONCLUSION

**Should you adopt multi-collection architecture?**

**Short answer:** Not immediately. **Phase 1-2 first, Phase 3 later.**

**Rationale:**
1. ✅ Current system already strong: reranking, filtering, query enhancement
2. 🎯 **Quick wins available**: Intent classification, authority scoring, BM25 (Phase 1-2)
3. ⏱️ Multi-collection is complex: DB migration, parallel retrieval, testing
4. 📊 **80/20 rule**: Get 80% of benefits from Phase 1-2 (20% effort)

**Recommended Path:**
```
Week 1-2: Phase 1 (Intent + Authority + Boost)
Week 3-4: Phase 2 (BM25 + Hybrid)
Week 5: Evaluate & Measure
Week 6+: Decide on Phase 3 (Multi-collection) based on results
```

**Expected Improvements:**
- Phase 1: +15-20% MRR (better ranking)
- Phase 2: +20-30% MRR (BM25 for specific queries)
- Phase 3: +10-15% MRR (diminishing returns)

**Total:** +45-65% improvement without full multi-collection restructure 🎉
