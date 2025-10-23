# 📋 Phase 2: Document Reranking - Implementation Plan

**Project**: RAG-bidding (Vietnamese Legal Document RAG System)  
**Date**: October 16, 2025  
**Branch**: `enhancement/2-phase2-reranking` (to be created)  
**Prerequisites**: Phase 1 Query Enhancement ✅ Complete

---

## 🎯 Project Context Analysis

### **Domain Characteristics:**

1. **Vietnamese Legal Documents**
   - Luật Đấu thầu 2023, Nghị định, Thông tư
   - Highly structured: Điều, Khoản, Chương
   - Complex legal terminology
   - Long-form content (chunks ~1000 tokens)

2. **Current Architecture:**
   - ✅ Query Enhancement: 4 strategies (Multi-Query, HyDE, Step-Back, Decomposition)
   - ✅ Vector Store: pgvector + `text-embedding-3-large` (3072 dim)
   - ✅ Modular Retrievers: Base, Enhanced, Fusion, Adaptive
   - ⏳ Reranking: Configured but NOT implemented

3. **Performance Requirements:**
   - Fast mode: <300ms
   - Balanced mode: <800ms  
   - Quality mode: <1500ms (can afford reranking here)
   - Adaptive mode: Dynamic (use reranking for complex queries)

4. **User Needs:**
   - Complex legal queries requiring precise ranking
   - Multi-aspect questions (e.g., "So sánh quy định cũ và mới")
   - Need high relevance (legal mistakes costly)

---

## 🏗️ Architecture Design

### **Reranking Strategy: Multi-Level Approach**

```
Query → [Phase 1: Retrieval] → [Phase 2: Reranking] → Top Results
         ↓                      ↓
    Vector Search (K=10)    Rerank to K=5
    + Query Enhancement     + Cross-Encoder
                            + Vietnamese Legal Scoring
```

### **Module Structure:**

```
src/retrieval/ranking/
├── __init__.py
├── base_reranker.py              # Abstract base class
├── cross_encoder_reranker.py     # Primary method (accuracy)
├── cohere_reranker.py            # Optional API-based (if needed)
├── llm_reranker.py               # GPT-based (for complex cases)
└── legal_score_reranker.py       # Domain-specific (Vietnamese legal)
```

---

## 📊 Reranking Methods Comparison

### **1. Cross-Encoder Reranking** ⭐ **RECOMMENDED PRIMARY**

**Model Options:**
- `bkai-foundation-models/vietnamese-bi-encoder` (Vietnamese-optimized)
- `BAAI/bge-reranker-v2-m3` (Multilingual, supports Vietnamese)
- `ms-marco-MiniLM-L-12-v2` (Fast, English-dominant but works)

**Pros:**
- ✅ High accuracy (better than bi-encoder)
- ✅ Local deployment (no API cost)
- ✅ Fast inference (~50-100ms for 10 docs)
- ✅ Can fine-tune on legal domain

**Cons:**
- ❌ Slower than vector search alone
- ❌ Need to download model (~400MB)

**Use Cases:**
- Quality mode (always use)
- Balanced mode (use for medium+ complexity)
- Adaptive mode (use for complex queries)

---

### **2. LLM-Based Reranking** (GPT-4o-mini)

**Implementation:**
- Use existing LLM (gpt-4o-mini)
- Prompt: "Rank these documents by relevance to query..."
- Temperature: 0 (deterministic)

**Pros:**
- ✅ No new dependencies
- ✅ Excellent understanding of Vietnamese legal text
- ✅ Can provide reasoning for rankings

**Cons:**
- ❌ Slower (~500-800ms for 10 docs)
- ❌ API cost ($0.150/1M tokens)
- ❌ Less reliable than cross-encoder for pure ranking

**Use Cases:**
- Quality mode (as secondary validation)
- Very complex multi-aspect queries
- When need to explain ranking

---

### **3. Cohere Rerank API** (Optional)

**Model:** `rerank-multilingual-v3.0`

**Pros:**
- ✅ State-of-the-art accuracy
- ✅ Supports Vietnamese
- ✅ No local infrastructure

**Cons:**
- ❌ API dependency
- ❌ Cost: $1.00 per 1000 searches
- ❌ Latency: ~200-400ms

**Use Cases:**
- If self-hosted cross-encoder not accurate enough
- Enterprise deployment with budget

---

### **4. Legal Domain Scoring** (Custom)

**Features:**
- Exact match boost (Điều X, Khoản Y)
- Structure matching (query mentions "Chương" → prefer chunks with Chương)
- Keyword density (legal terms)
- Recency scoring (Luật 2023 > older versions)

**Pros:**
- ✅ Domain-specific
- ✅ Very fast (~5ms)
- ✅ No external dependencies
- ✅ Transparent scoring

**Cons:**
- ❌ Rule-based (not learned)
- ❌ Lower accuracy than ML models

**Use Cases:**
- Fast mode (only use this)
- As a booster to cross-encoder scores
- Tie-breaking

---

## 🎯 Recommended Implementation Plan

### **Phase 2A: Core Reranking (Week 1)** ⭐ **START HERE**

**Goal:** Implement cross-encoder reranking for quality mode

#### **Step 1: Base Infrastructure** (Day 1-2)
```python
# src/retrieval/ranking/base_reranker.py
from abc import ABC, abstractmethod
from typing import List, Tuple
from langchain_core.documents import Document

class BaseReranker(ABC):
    """Abstract base class for all rerankers"""
    
    @abstractmethod
    def rerank(
        self, 
        query: str, 
        documents: List[Document],
        top_k: int = 5
    ) -> List[Tuple[Document, float]]:
        """
        Rerank documents by relevance to query
        
        Returns:
            List of (document, score) tuples, sorted by score descending
        """
        pass
```

#### **Step 2: Cross-Encoder Implementation** (Day 2-3)
```python
# src/retrieval/ranking/cross_encoder_reranker.py
from sentence_transformers import CrossEncoder
from typing import List, Tuple
from langchain_core.documents import Document
import logging

logger = logging.getLogger(__name__)

class CrossEncoderReranker(BaseReranker):
    """
    Cross-Encoder reranking for Vietnamese legal documents
    """
    
    def __init__(
        self, 
        model_name: str = "BAAI/bge-reranker-v2-m3",
        device: str = "cpu",  # or "cuda" if GPU available
        cache_dir: str = ".cache/rerankers"
    ):
        """
        Args:
            model_name: HuggingFace model name
                Options:
                - "BAAI/bge-reranker-v2-m3" (multilingual, good for Vietnamese)
                - "bkai-foundation-models/vietnamese-bi-encoder" (Vietnamese-specific)
            device: "cpu" or "cuda"
            cache_dir: Model cache directory
        """
        logger.info(f"Loading cross-encoder model: {model_name}")
        self.model = CrossEncoder(model_name, device=device)
        logger.info(f"Cross-encoder loaded on {device}")
    
    def rerank(
        self, 
        query: str, 
        documents: List[Document],
        top_k: int = 5
    ) -> List[Tuple[Document, float]]:
        """Rerank documents using cross-encoder"""
        
        if not documents:
            return []
        
        # Prepare query-document pairs
        pairs = [[query, doc.page_content] for doc in documents]
        
        # Get relevance scores
        scores = self.model.predict(pairs)
        
        # Sort by score descending
        doc_scores = list(zip(documents, scores))
        doc_scores.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f"Reranked {len(documents)} docs, top score: {doc_scores[0][1]:.4f}")
        
        return doc_scores[:top_k]
```

#### **Step 3: Integration with Retrievers** (Day 3-4)
```python
# Update: src/retrieval/retrievers/enhanced_retriever.py

class EnhancedRetriever(BaseRetriever):
    """Retriever with query enhancement + optional reranking"""
    
    base_retriever: BaseVectorRetriever
    enhancement_strategies: Optional[List[EnhancementStrategy]] = None
    reranker: Optional[BaseReranker] = None  # ⭐ NEW
    k: int = 5
    rerank_top_k: int = 10  # ⭐ NEW: Retrieve more, rerank to k
    
    def _get_relevant_documents(self, query: str, ...) -> List[Document]:
        # Step 1: Enhance query
        if self.query_enhancer:
            queries = self.query_enhancer.enhance(query)
        else:
            queries = [query]
        
        # Step 2: Retrieve (get more docs if reranking)
        retrieval_k = self.rerank_top_k if self.reranker else self.k
        all_docs = []
        for q in queries:
            docs = self.base_retriever.invoke(q, k=retrieval_k)
            all_docs.extend(docs)
        
        # Step 3: Deduplicate
        if self.deduplication:
            all_docs = self._deduplicate_docs(all_docs)
        
        # Step 4: Rerank ⭐ NEW
        if self.reranker:
            doc_scores = self.reranker.rerank(query, all_docs, top_k=self.k)
            return [doc for doc, score in doc_scores]
        
        return all_docs[:self.k]
```

#### **Step 4: Factory Pattern Update** (Day 4)
```python
# Update: src/retrieval/retrievers/__init__.py

def create_retriever(
    mode: str = "balanced",
    vector_store=None,
    enable_reranking: bool = True  # ⭐ NEW parameter
) -> BaseRetriever:
    """Create retriever based on mode"""
    
    base_retriever = BaseVectorRetriever(vector_store=vector_store)
    
    # Initialize reranker if enabled
    reranker = None
    if enable_reranking and mode in ["balanced", "quality", "adaptive"]:
        reranker = CrossEncoderReranker(
            model_name="BAAI/bge-reranker-v2-m3",
            device="cpu"
        )
    
    if mode == "fast":
        return base_retriever
    
    elif mode == "balanced":
        return EnhancedRetriever(
            base_retriever=base_retriever,
            enhancement_strategies=[
                EnhancementStrategy.MULTI_QUERY,
                EnhancementStrategy.STEP_BACK
            ],
            reranker=reranker,  # ⭐ NEW
            rerank_top_k=8,
            k=4
        )
    
    elif mode == "quality":
        return FusionRetriever(
            base_retriever=base_retriever,
            reranker=reranker,  # ⭐ NEW
            rerank_top_k=10,
            k=5
        )
    
    # ... adaptive mode similar
```

#### **Step 5: Testing** (Day 5)
```python
# tests/unit/test_retrieval/test_reranking.py

def test_cross_encoder_reranker():
    """Test cross-encoder reranking"""
    reranker = CrossEncoderReranker()
    
    query = "Quy định về bảo đảm dự thầu trong Luật Đấu thầu 2023"
    documents = [
        Document(page_content="Điều 14. Bảo đảm dự thầu..."),
        Document(page_content="Điều 68. Bảo đảm thực hiện hợp đồng..."),
        Document(page_content="Điều 10. Ưu đãi nhà thầu trong nước...")
    ]
    
    results = reranker.rerank(query, documents, top_k=2)
    
    assert len(results) == 2
    assert results[0][1] > results[1][1]  # Scores descending
    assert "Điều 14" in results[0][0].page_content  # Most relevant first

def test_retriever_with_reranking():
    """Test enhanced retriever with reranking"""
    retriever = create_retriever(mode="quality", enable_reranking=True)
    
    docs = retriever.invoke("Thời gian hiệu lực bảo đảm dự thầu")
    
    assert len(docs) == 5
    # Verify reranking improved relevance (manual inspection needed)
```

---

### **Phase 2B: LLM Reranking (Week 2)** (Optional)

**Goal:** Add LLM-based reranking for very complex queries

```python
# src/retrieval/ranking/llm_reranker.py

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from typing import List, Tuple
from langchain_core.documents import Document

RERANK_PROMPT = """Bạn là chuyên gia pháp lý Việt Nam. Nhiệm vụ: xếp hạng các đoạn văn bản pháp luật theo mức độ liên quan đến câu hỏi.

Câu hỏi: {query}

Các đoạn văn bản:
{documents}

Hãy trả về danh sách số thứ tự (từ 1 đến {n}) được xếp hạng từ LIÊN QUAN NHẤT đến ÍT LIÊN QUAN NHẤT.
Chỉ trả về các số, cách nhau bằng dấu phẩy. Ví dụ: 3,1,5,2,4

Xếp hạng:"""

class LLMReranker(BaseReranker):
    """LLM-based reranking using GPT-4o-mini"""
    
    def __init__(self, model_name: str = "gpt-4o-mini", temperature: float = 0):
        self.llm = ChatOpenAI(model=model_name, temperature=temperature)
        self.prompt = ChatPromptTemplate.from_template(RERANK_PROMPT)
    
    def rerank(self, query: str, documents: List[Document], top_k: int = 5) -> List[Tuple[Document, float]]:
        # Format documents
        docs_text = "\n\n".join([
            f"[{i+1}] {doc.page_content[:500]}..." 
            for i, doc in enumerate(documents)
        ])
        
        # Get ranking from LLM
        chain = self.prompt | self.llm
        response = chain.invoke({
            "query": query,
            "documents": docs_text,
            "n": len(documents)
        })
        
        # Parse response (e.g., "3,1,5,2,4")
        ranking = [int(x.strip()) - 1 for x in response.content.split(",")]
        
        # Reorder documents
        reranked = [documents[i] for i in ranking]
        
        # Assign scores (highest to lowest)
        scores = [1.0 - (i / len(reranked)) for i in range(len(reranked))]
        
        return list(zip(reranked, scores))[:top_k]
```

**Use Case:** Quality mode + very complex queries (complexity analyzer score > 0.8)

---

### **Phase 2C: Legal Domain Scoring (Week 2)** (Booster)

**Goal:** Add Vietnamese legal-specific scoring as a booster

```python
# src/retrieval/ranking/legal_score_reranker.py

import re
from typing import List, Tuple
from langchain_core.documents import Document

class LegalScoreReranker(BaseReranker):
    """Vietnamese legal document scoring"""
    
    LEGAL_KEYWORDS = [
        "luật", "nghị định", "thông tư", "quyết định",
        "điều", "khoản", "chương", "phần", "mục"
    ]
    
    def rerank(self, query: str, documents: List[Document], top_k: int = 5) -> List[Tuple[Document, float]]:
        doc_scores = []
        
        for doc in documents:
            score = self._calculate_legal_score(query, doc)
            doc_scores.append((doc, score))
        
        doc_scores.sort(key=lambda x: x[1], reverse=True)
        return doc_scores[:top_k]
    
    def _calculate_legal_score(self, query: str, doc: Document) -> float:
        """Calculate legal relevance score"""
        score = 0.0
        content = doc.page_content.lower()
        query_lower = query.lower()
        
        # 1. Exact structure match (e.g., "Điều 14")
        dieu_matches = re.findall(r"điều\s+\d+", query_lower)
        for match in dieu_matches:
            if match in content:
                score += 0.5  # High boost for exact match
        
        # 2. Keyword density
        keyword_count = sum(1 for kw in self.LEGAL_KEYWORDS if kw in content)
        score += keyword_count * 0.05
        
        # 3. Recency (prefer newer laws)
        if "2023" in content or "2024" in content:
            score += 0.1
        
        # 4. Metadata boosts
        metadata = doc.metadata
        if metadata.get("source") == "official_gazette":
            score += 0.15
        
        return score
```

**Use Case:** Fast mode (only this), or as a booster to cross-encoder

---

## 📝 Configuration Updates

### **Update `config/models.py`:**

```python
@dataclass
class Settings:
    # ... existing settings ...
    
    # Document reranking (Phase 2)
    enable_reranking: bool = _env_bool("ENABLE_RERANKING", False)  # ⭐ Set FALSE initially
    rerank_method: str = os.getenv("RERANK_METHOD", "cross_encoder")  # cross_encoder, llm, legal_score
    rerank_model: str = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
    rerank_top_k: int = int(os.getenv("RERANK_TOP_K", "10"))
    final_docs_k: int = int(os.getenv("FINAL_DOCS_K", "5"))
    rerank_device: str = os.getenv("RERANK_DEVICE", "cpu")  # cpu or cuda

# Update presets
class RAGPresets:
    @staticmethod
    def get_quality_mode() -> Dict[str, object]:
        return {
            "enable_query_enhancement": True,
            "enable_reranking": True,  # ⭐ Enable after implementation
            "rerank_method": "cross_encoder",
            "enable_answer_validation": True,
            "rerank_top_k": 10,
            "final_docs_k": 5,
        }
    
    @staticmethod
    def get_balanced_mode() -> Dict[str, object]:
        return {
            "enable_query_enhancement": True,
            "enable_reranking": True,  # ⭐ Enable after implementation
            "rerank_method": "cross_encoder",
            "rerank_top_k": 8,
            "final_docs_k": 4,
        }
```

---

## 🧪 Testing Strategy

### **Unit Tests:**
```bash
tests/unit/test_retrieval/
├── test_reranker_base.py           # Base class tests
├── test_cross_encoder_reranker.py  # Cross-encoder tests
├── test_llm_reranker.py            # LLM reranker tests
└── test_legal_score_reranker.py    # Legal scoring tests
```

### **Integration Tests:**
```python
# tests/integration/test_reranking_pipeline.py

def test_end_to_end_with_reranking():
    """Test full pipeline: query → enhancement → retrieval → reranking → answer"""
    
    query = "Thời hạn hiệu lực của bảo đảm dự thầu là bao lâu?"
    
    # Create retriever with reranking
    retriever = create_retriever(mode="quality", enable_reranking=True)
    
    # Invoke
    docs = retriever.invoke(query)
    
    # Verify
    assert len(docs) == 5
    assert any("Điều 14" in doc.page_content for doc in docs[:2])  # Top 2 should be relevant
```

### **Benchmark Tests:**
```python
# tests/benchmarks/test_reranking_performance.py

def benchmark_reranking_latency():
    """Measure reranking overhead"""
    
    results = {
        "no_reranking": [],
        "cross_encoder": [],
        "llm": [],
        "legal_score": []
    }
    
    queries = load_test_queries()  # 100 sample queries
    
    for query in queries:
        # Test each method
        # ... measure time
    
    print(f"Cross-Encoder avg latency: {avg(results['cross_encoder'])}ms")
    # Expected: ~50-100ms for 10 docs
```

---

## 📊 Success Metrics

### **Accuracy Metrics:**
- **MRR (Mean Reciprocal Rank)**: Target > 0.85 (vs baseline 0.70)
- **NDCG@5**: Target > 0.90 (vs baseline 0.75)
- **Recall@5**: Target > 0.95 (vs baseline 0.85)

### **Performance Metrics:**
- **Fast mode**: <300ms (no reranking)
- **Balanced mode**: <800ms (cross-encoder)
- **Quality mode**: <1500ms (cross-encoder + LLM validation)

### **User Metrics:**
- **Relevance satisfaction**: User feedback > 4/5
- **Task completion rate**: > 90%

---

## 🚀 Deployment Plan

### **Phase 2A Deployment (Week 1 End):**
1. ✅ Implement cross-encoder reranker
2. ✅ Integrate with quality mode
3. ✅ Run benchmarks
4. ✅ Deploy to staging
5. ✅ A/B test quality mode (with/without reranking)
6. ✅ Monitor metrics for 3 days
7. ✅ Deploy to production if metrics improved

### **Phase 2B Deployment (Week 2):**
1. Implement LLM reranker
2. Use for very complex queries only
3. Monitor costs vs accuracy gains

### **Phase 2C Deployment (Week 2):**
1. Implement legal scoring
2. Use as booster in fast mode
3. Benchmark latency impact (<10ms target)

---

## 💰 Cost Analysis

### **Infrastructure:**
- **Cross-Encoder Model**: Free (self-hosted), ~400MB disk, ~1GB RAM
- **LLM Reranking**: $0.150/1M input tokens (~$0.0015 per query with 10 docs)
- **Legal Scoring**: Free (rule-based)

### **Estimated Costs (1000 queries/day):**
- Cross-Encoder only: **$0/month** (compute already exists)
- + LLM for 10% complex queries: **~$5/month**
- Cohere Rerank (alternative): **$30/month** (1000 searches)

**Recommendation:** Use cross-encoder as primary, LLM for top 10% complex queries

---

## 🔧 Dependencies to Add

```bash
# requirements.txt additions
sentence-transformers>=2.2.0  # For cross-encoder
torch>=2.0.0                  # PyTorch backend
transformers>=4.30.0          # HuggingFace models

# Optional:
# cohere>=4.0.0               # If using Cohere Rerank API
```

---

## 📚 Resources & References

### **Models:**
- [BAAI/bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3) - Multilingual reranker
- [bkai-foundation-models/vietnamese-bi-encoder](https://huggingface.co/bkai-foundation-models/vietnamese-bi-encoder) - Vietnamese-specific
- [Cohere Rerank API](https://docs.cohere.com/docs/reranking)

### **Papers:**
- [RankGPT: Is ChatGPT Good at Reranking?](https://arxiv.org/abs/2304.09542)
- [ColBERTv2: Effective and Efficient Retrieval](https://arxiv.org/abs/2112.01488)

### **Tutorials:**
- [Sentence-Transformers Cross-Encoders](https://www.sbert.net/examples/applications/cross-encoder/README.html)

---

## ✅ Checklist

### **Phase 2A: Core Reranking**
- [ ] Create `src/retrieval/ranking/` folder structure
- [ ] Implement `BaseReranker` abstract class
- [ ] Implement `CrossEncoderReranker`
- [ ] Update `EnhancedRetriever` to support reranking
- [ ] Update `FusionRetriever` to support reranking
- [ ] Update factory pattern in `__init__.py`
- [ ] Add unit tests (coverage > 90%)
- [ ] Add integration tests
- [ ] Benchmark latency
- [ ] Update config presets (enable reranking in quality/balanced modes)
- [ ] Update API documentation
- [ ] Deploy to staging
- [ ] A/B test for 3 days
- [ ] Deploy to production

### **Phase 2B: LLM Reranking** (Optional)
- [ ] Implement `LLMReranker`
- [ ] Add complexity-based routing (high complexity → LLM rerank)
- [ ] Monitor costs
- [ ] A/B test accuracy gains

### **Phase 2C: Legal Scoring** (Optional)
- [ ] Implement `LegalScoreReranker`
- [ ] Use in fast mode
- [ ] Use as booster to cross-encoder
- [ ] Benchmark latency

---

## 🎓 Learning Outcomes

After Phase 2, team will have:
- ✅ Understanding of reranking in RAG systems
- ✅ Experience with cross-encoder models
- ✅ LLM-as-judge pattern knowledge
- ✅ Domain-specific scoring techniques
- ✅ Performance optimization skills

---

**Next Phase Ideas (Phase 3):**
- Hybrid Search (BM25 + Vector)
- Fine-tuning cross-encoder on Vietnamese legal data
- Query understanding improvements
- Caching layer for popular queries

---

**Prepared by**: GitHub Copilot  
**Status**: Ready for Implementation  
**Estimated Timeline**: 2 weeks (Phase 2A: 1 week, Phase 2B+C: 1 week)
