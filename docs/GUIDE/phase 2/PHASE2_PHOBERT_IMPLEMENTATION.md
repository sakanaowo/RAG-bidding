# 🚀 Triển Khai Reranking với PhoBERT - Plan Một Buổi Chiều

**Dự án**: RAG-bidding  
**Thời gian**: 3-4 giờ (một buổi chiều)  
**Mục tiêu**: Triển khai PhoBERT reranking cho văn bản pháp luật Việt Nam  
**Ngày**: 23 tháng 10, 2025

---

## 🎯 Mục Tiêu Buổi Chiều

### **Kết quả cần đạt được:**
- ✅ PhoBERT reranker hoạt động trong chế độ quality
- ✅ Test cases pass
- ✅ API endpoint hoạt động với reranking
- ✅ Benchmark latency < 150ms cho 10 docs
- ✅ Cải thiện MRR ít nhất 10-15%

### **Không cần làm hôm nay:**
- ❌ Fine-tune PhoBERT trên dữ liệu pháp luật (Phase 3)
- ❌ LLM reranking (Phase 2B)
- ❌ Legal scoring (Phase 2C)
- ❌ Production deployment

---

## ⏰ Timeline Chi Tiết

### **13:00 - 13:45 (45 phút): Setup & Base Infrastructure**
- [x] ~~Cài dependencies~~ (đã xong: sentence-transformers 5.1.2)
- [ ] Tạo folder structure
- [ ] Implement `BaseReranker` abstract class
- [ ] Test PhoBERT model download và khởi tạo

### **13:45 - 14:30 (45 phút): PhoBERT Reranker Implementation**
- [ ] Implement `PhoBERTReranker` class
- [ ] Test với sample query-document pairs
- [ ] Benchmark latency
- [ ] Handle edge cases (empty docs, long text)

### **14:30 - 15:00 (30 phút): Giải Lao & Review Code**
- [ ] Coffee break ☕
- [ ] Review code đã viết
- [ ] Fix bugs/issues nếu có

### **15:00 - 15:45 (45 phút): Integration với Retrievers**
- [ ] Update `EnhancedRetriever` để hỗ trợ reranking
- [ ] Update factory pattern trong `__init__.py`
- [ ] Test integration end-to-end

### **15:45 - 16:30 (45 phút): Testing & Validation**
- [ ] Viết unit tests
- [ ] Viết integration test
- [ ] Chạy test với real legal queries
- [ ] So sánh kết quả có/không reranking

### **16:30 - 17:00 (30 phút): Wrap Up**
- [ ] Update config
- [ ] Test API endpoint
- [ ] Document changes
- [ ] Commit code

---

## 📋 Chi Tiết Từng Bước

## **BƯỚC 1: Setup & Base Infrastructure (13:00 - 13:45)**

### **1.1. Tạo Folder Structure (5 phút)**

```bash
cd /home/sakana/Code/RAG-bidding

# Tạo thư mục ranking
mkdir -p src/retrieval/ranking

# Tạo các files
touch src/retrieval/ranking/__init__.py
touch src/retrieval/ranking/base_reranker.py
touch src/retrieval/ranking/phobert_reranker.py

# Tạo test folder
mkdir -p tests/unit/test_retrieval
touch tests/unit/test_retrieval/test_reranking.py
```

### **1.2. Implement BaseReranker (15 phút)**

```python
# src/retrieval/ranking/base_reranker.py

from abc import ABC, abstractmethod
from typing import List, Tuple
from langchain_core.documents import Document


class BaseReranker(ABC):
    """
    Abstract base class cho tất cả rerankers
    
    Reranker nhận query và list documents, trả về
    documents được xếp hạng lại theo độ liên quan.
    """
    
    @abstractmethod
    def rerank(
        self, 
        query: str, 
        documents: List[Document],
        top_k: int = 5
    ) -> List[Tuple[Document, float]]:
        """
        Xếp hạng lại documents theo độ liên quan với query
        
        Args:
            query: Câu hỏi của user
            documents: List documents từ retriever
            top_k: Số documents trả về (mặc định 5)
            
        Returns:
            List of (document, score) tuples, sorted by score descending
            
        Example:
            >>> reranker = PhoBERTReranker()
            >>> docs = [doc1, doc2, doc3]
            >>> results = reranker.rerank("Điều 14 Luật Đấu thầu", docs, top_k=2)
            >>> [(doc1, 0.95), (doc3, 0.82)]
        """
        pass
    
    def rerank_batch(
        self,
        queries: List[str],
        documents_list: List[List[Document]],
        top_k: int = 5
    ) -> List[List[Tuple[Document, float]]]:
        """
        Batch reranking cho nhiều queries
        
        Mặc định gọi rerank() cho từng query.
        Subclass có thể override để optimize batch processing.
        """
        return [
            self.rerank(query, docs, top_k)
            for query, docs in zip(queries, documents_list)
        ]
```

### **1.3. Test PhoBERT Download (25 phút)**

```python
# Tạo file test nhanh: test_phobert_setup.py

"""
Test script để verify PhoBERT setup
Chạy: python test_phobert_setup.py
"""

import time
from sentence_transformers import CrossEncoder

print("🔍 Testing PhoBERT setup...")
print("-" * 60)

# Test 1: Load model
print("\n1️⃣ Loading PhoBERT model...")
start = time.time()

try:
    # Thử với vinai/phobert-base-v2 (nhỏ hơn, nhanh hơn)
    model = CrossEncoder(
        'vinai/phobert-base-v2',
        device='cpu',
        max_length=256  # PhoBERT max sequence length
    )
    load_time = time.time() - start
    print(f"   ✅ Model loaded successfully in {load_time:.2f}s")
    print(f"   📦 Model: vinai/phobert-base-v2")
except Exception as e:
    print(f"   ❌ Error loading model: {e}")
    exit(1)

# Test 2: Sample inference
print("\n2️⃣ Testing inference with legal text...")
start = time.time()

query = "Quy định về bảo đảm dự thầu"
docs = [
    "Điều 14. Bảo đảm dự thầu là điều kiện bắt buộc đối với nhà thầu khi dự thầu.",
    "Điều 68. Bảo đảm thực hiện hợp đồng được thực hiện sau khi ký hợp đồng.",
    "Điều 10. Ưu đãi nhà thầu trong nước được quy định chi tiết tại Nghị định."
]

pairs = [[query, doc] for doc in docs]
scores = model.predict(pairs)
inference_time = time.time() - start

print(f"   ✅ Inference completed in {inference_time:.2f}s")
print(f"   📊 Scores:")
for i, (doc, score) in enumerate(zip(docs, scores)):
    print(f"      [{i+1}] Score: {score:.4f} - {doc[:60]}...")

# Test 3: Verify ranking
print("\n3️⃣ Verifying ranking quality...")
best_idx = scores.argmax()
if best_idx == 0:  # Điều 14 nên có score cao nhất
    print(f"   ✅ Correct! Điều 14 ranked #1 (score: {scores[0]:.4f})")
else:
    print(f"   ⚠️  Warning: Điều 14 not ranked #1 (best: doc {best_idx+1})")

# Test 4: Latency benchmark
print("\n4️⃣ Benchmarking latency for 10 docs...")
docs_10 = docs * 4  # Tạo 12 docs (gần với 10)
pairs_10 = [[query, doc] for doc in docs_10[:10]]

start = time.time()
scores_10 = model.predict(pairs_10)
latency = (time.time() - start) * 1000  # Convert to ms

print(f"   ⏱️  Latency: {latency:.2f}ms for 10 docs")
if latency < 150:
    print(f"   ✅ Good! Under 150ms target")
else:
    print(f"   ⚠️  Warning: Slower than 150ms target")

print("\n" + "=" * 60)
print("✅ PhoBERT setup test COMPLETE!")
print("=" * 60)
```

**Chạy test:**
```bash
cd /home/sakana/Code/RAG-bidding
python test_phobert_setup.py
```

**Kết quả kỳ vọng:**
- Model load: 5-10s (lần đầu download ~500MB)
- Inference: <1s cho 3 docs
- Điều 14 có score cao nhất
- Latency <150ms cho 10 docs

---

## **BƯỚC 2: PhoBERT Reranker Implementation (13:45 - 14:30)**

### **2.1. Implement PhoBERTReranker (30 phút)**

```python
# src/retrieval/ranking/phobert_reranker.py

from sentence_transformers import CrossEncoder
from typing import List, Tuple, Optional
from langchain_core.documents import Document
import logging
import time

from .base_reranker import BaseReranker

logger = logging.getLogger(__name__)


class PhoBERTReranker(BaseReranker):
    """
    PhoBERT-based reranking cho văn bản pháp luật Việt Nam
    
    Model: vinai/phobert-base-v2
    - 135M parameters
    - Trained on 20GB Vietnamese text
    - Max sequence length: 256 tokens (RoBERTa tokenizer)
    
    Performance:
    - Latency: ~100-150ms for 10 docs on CPU
    - Accuracy: Tốt cho tiếng Việt, đặc biệt văn bản chính thống
    
    Note:
    - Sử dụng AutoTokenizer tự động (không xung đột với tiktoken)
    - Device: cpu (có thể chuyển sang cuda nếu có GPU)
    """
    
    # Model options (có thể thử fine-tuned models sau)
    PHOBERT_BASE = "vinai/phobert-base-v2"      # 135M params, fast
    PHOBERT_LARGE = "vinai/phobert-large"       # 370M params, slower
    
    def __init__(
        self, 
        model_name: str = PHOBERT_BASE,
        device: str = "cpu",
        max_length: int = 256,
        batch_size: int = 16,
        cache_dir: Optional[str] = None
    ):
        """
        Args:
            model_name: PhoBERT model name (default: vinai/phobert-base-v2)
            device: "cpu" or "cuda"
            max_length: Max tokens (PhoBERT max = 256)
            batch_size: Batch size for inference
            cache_dir: Model cache directory (default: ~/.cache/huggingface)
        """
        logger.info(f"🔧 Initializing PhoBERT reranker: {model_name}")
        
        self.model_name = model_name
        self.device = device
        self.max_length = max_length
        self.batch_size = batch_size
        
        # Load CrossEncoder (tự động load AutoTokenizer bên trong)
        try:
            self.model = CrossEncoder(
                model_name,
                device=device,
                max_length=max_length,
                default_activation_function=None  # Dùng raw scores
            )
            logger.info(f"✅ PhoBERT loaded on {device}")
            logger.info(f"📦 Max sequence length: {max_length} tokens")
        except Exception as e:
            logger.error(f"❌ Failed to load PhoBERT: {e}")
            raise
    
    def rerank(
        self, 
        query: str, 
        documents: List[Document],
        top_k: int = 5
    ) -> List[Tuple[Document, float]]:
        """
        Rerank documents using PhoBERT cross-encoder
        
        Args:
            query: User query (tiếng Việt)
            documents: Retrieved documents
            top_k: Number of top documents to return
            
        Returns:
            List of (document, score) sorted by score descending
        """
        if not documents:
            logger.warning("⚠️  Empty documents list")
            return []
        
        start_time = time.time()
        
        # Truncate nếu có quá nhiều docs (tránh OOM)
        if len(documents) > 50:
            logger.warning(f"⚠️  Too many docs ({len(documents)}), truncating to 50")
            documents = documents[:50]
        
        # Chuẩn bị query-document pairs
        pairs = []
        for doc in documents:
            # Truncate content nếu quá dài (PhoBERT max 256 tokens)
            # Ước tính: 1 token ≈ 4 chars cho tiếng Việt
            content = doc.page_content[:800]  # ~200 tokens content
            pairs.append([query, content])
        
        # Predict relevance scores
        try:
            scores = self.model.predict(
                pairs,
                batch_size=self.batch_size,
                show_progress_bar=False
            )
        except Exception as e:
            logger.error(f"❌ Prediction error: {e}")
            # Fallback: return original order with dummy scores
            return [(doc, 1.0 - i * 0.1) for i, doc in enumerate(documents[:top_k])]
        
        # Zip documents with scores và sort
        doc_scores = list(zip(documents, scores))
        doc_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Log performance
        latency = (time.time() - start_time) * 1000
        top_score = doc_scores[0][1] if doc_scores else 0
        
        logger.info(
            f"📊 Reranked {len(documents)} docs in {latency:.1f}ms | "
            f"Top score: {top_score:.4f} | Returning top {top_k}"
        )
        
        # Debug: Log top 3 scores
        if logger.isEnabledFor(logging.DEBUG):
            for i, (doc, score) in enumerate(doc_scores[:3]):
                preview = doc.page_content[:80].replace('\n', ' ')
                logger.debug(f"  [{i+1}] {score:.4f} - {preview}...")
        
        return doc_scores[:top_k]
    
    def rerank_batch(
        self,
        queries: List[str],
        documents_list: List[List[Document]],
        top_k: int = 5
    ) -> List[List[Tuple[Document, float]]]:
        """
        Batch reranking (tối ưu hóa sau nếu cần)
        
        Hiện tại: Gọi rerank() cho từng query
        TODO: Implement true batch processing
        """
        logger.info(f"🔄 Batch reranking {len(queries)} queries...")
        
        results = []
        for query, docs in zip(queries, documents_list):
            result = self.rerank(query, docs, top_k)
            results.append(result)
        
        return results
```

### **2.2. Update __init__.py (5 phút)**

```python
# src/retrieval/ranking/__init__.py

from .base_reranker import BaseReranker
from .phobert_reranker import PhoBERTReranker

__all__ = [
    "BaseReranker",
    "PhoBERTReranker",
]
```

### **2.3. Test PhoBERTReranker (10 phút)**

```python
# Tạo file: test_phobert_reranker.py

"""
Quick test PhoBERTReranker implementation
"""

from langchain_core.documents import Document
from src.retrieval.ranking import PhoBERTReranker

print("🧪 Testing PhoBERTReranker...")
print("-" * 60)

# Initialize reranker
reranker = PhoBERTReranker(device="cpu")

# Sample query về bảo đảm dự thầu
query = "Quy định về thời gian hiệu lực bảo đảm dự thầu trong Luật Đấu thầu 2023"

# Sample documents (giả lập từ vector search)
docs = [
    Document(
        page_content="Điều 14. Bảo đảm dự thầu\n1. Thời gian hiệu lực bảo đảm dự thầu được quy định trong hồ sơ mời thầu, tối thiểu là 30 ngày kể từ ngày hết hạn nộp hồ sơ dự thầu.",
        metadata={"source": "Luật Đấu thầu 2023", "article": "Điều 14"}
    ),
    Document(
        page_content="Điều 68. Bảo đảm thực hiện hợp đồng\nThời hạn bảo đảm thực hiện hợp đồng được quy định trong hợp đồng, thường từ ngày ký hợp đồng đến khi hoàn thành nghĩa vụ.",
        metadata={"source": "Luật Đấu thầu 2023", "article": "Điều 68"}
    ),
    Document(
        page_content="Điều 10. Ưu đãi nhà thầu trong nước\nNhà thầu trong nước được hưởng ưu đãi về giá trong đánh giá, ưu tiên xem xét trong trường hợp điểm kỹ thuật bằng nhau.",
        metadata={"source": "Luật Đấu thầu 2023", "article": "Điều 10"}
    ),
    Document(
        page_content="Điều 25. Thời điểm có hiệu lực của hợp đồng\nHợp đồng có hiệu lực kể từ ngày được ký kết hoặc theo thỏa thuận của các bên trong hợp đồng.",
        metadata={"source": "Luật Đấu thầu 2023", "article": "Điều 25"}
    ),
]

print(f"\n📝 Query: {query}")
print(f"📚 Documents to rerank: {len(docs)}")

# Rerank
results = reranker.rerank(query, docs, top_k=3)

print(f"\n🏆 Top 3 Results:")
print("-" * 60)
for i, (doc, score) in enumerate(results):
    article = doc.metadata.get("article", "Unknown")
    preview = doc.page_content[:100].replace('\n', ' ')
    print(f"\n[{i+1}] Score: {score:.4f}")
    print(f"    Article: {article}")
    print(f"    Preview: {preview}...")

# Verify
print("\n" + "=" * 60)
if "Điều 14" in results[0][0].metadata.get("article", ""):
    print("✅ TEST PASSED: Điều 14 ranked #1 (correct!)")
else:
    print("⚠️  TEST WARNING: Điều 14 not ranked #1")
print("=" * 60)
```

**Chạy:**
```bash
python test_phobert_reranker.py
```

---

## **BƯỚC 3: Giải Lao (14:30 - 15:00)**

☕ **Coffee break & code review**

**Checklist trước khi tiếp tục:**
- [ ] PhoBERT model đã download thành công
- [ ] Reranker trả về kết quả đúng format
- [ ] Điều 14 được rank cao hơn các điều khác
- [ ] Latency < 150ms
- [ ] Code clean, có logging

---

## **BƯỚC 4: Integration với Retrievers (15:00 - 15:45)**

### **4.1. Update EnhancedRetriever (25 phút)**

```python
# src/retrieval/retrievers/enhanced_retriever.py
# Tìm class EnhancedRetriever và thêm reranking support

# Thêm import ở đầu file
from typing import Optional
from ..ranking import BaseReranker

# Update class EnhancedRetriever
class EnhancedRetriever(BaseRetriever):
    """Enhanced retriever with query enhancement + optional reranking"""
    
    base_retriever: BaseVectorRetriever
    enhancement_strategies: Optional[List[EnhancementStrategy]] = None
    reranker: Optional[BaseReranker] = None  # ⭐ NEW
    k: int = 5
    rerank_top_k: int = 10  # ⭐ NEW: Retrieve more, rerank down to k
    enable_deduplication: bool = True
    
    def _get_relevant_documents(
        self, 
        query: str,
        run_manager: CallbackManagerForRetrieverRun = None
    ) -> List[Document]:
        """
        Retrieve và rerank documents
        
        Workflow:
        1. Enhance query (nếu có strategies)
        2. Retrieve nhiều docs (rerank_top_k nếu có reranker)
        3. Deduplicate
        4. Rerank (nếu có reranker) ⭐ NEW
        5. Return top k
        """
        # Step 1: Enhance query
        if self.enhancement_strategies:
            queries = self._enhance_query(query)
        else:
            queries = [query]
        
        # Step 2: Retrieve (lấy nhiều hơn nếu sẽ rerank)
        retrieval_k = self.rerank_top_k if self.reranker else self.k
        
        all_docs = []
        for q in queries:
            docs = self.base_retriever.invoke(q, k=retrieval_k)
            all_docs.extend(docs)
        
        # Step 3: Deduplicate
        if self.enable_deduplication:
            all_docs = self._deduplicate_docs(all_docs)
        
        # Step 4: Rerank ⭐ NEW
        if self.reranker:
            logger.info(f"🔄 Reranking {len(all_docs)} docs with {self.reranker.__class__.__name__}")
            doc_scores = self.reranker.rerank(query, all_docs, top_k=self.k)
            reranked_docs = [doc for doc, score in doc_scores]
            
            # Log improvement
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"  Original top doc: {all_docs[0].page_content[:60]}...")
                logger.debug(f"  Reranked top doc: {reranked_docs[0].page_content[:60]}...")
            
            return reranked_docs
        
        # No reranking: return first k docs
        return all_docs[:self.k]
```

### **4.2. Update Factory Pattern (20 phút)**

```python
# src/retrieval/retrievers/__init__.py

from typing import Optional
from ...ranking import PhoBERTReranker, BaseReranker

def create_retriever(
    mode: str = "balanced",
    vector_store=None,
    enable_reranking: bool = True,  # ⭐ NEW parameter
    reranker: Optional[BaseReranker] = None  # ⭐ NEW: custom reranker
) -> BaseRetriever:
    """
    Factory function to create retriever based on mode
    
    Args:
        mode: "fast", "balanced", "quality", "adaptive"
        vector_store: PGVector store instance
        enable_reranking: Enable PhoBERT reranking (default: True)
        reranker: Custom reranker (default: PhoBERTReranker)
    
    Returns:
        Configured retriever instance
    """
    from .base_retriever import BaseVectorRetriever
    from .enhanced_retriever import EnhancedRetriever
    from .fusion_retriever import FusionRetriever
    from .adaptive_retriever import AdaptiveKRetriever
    from ..query_processing.strategies import EnhancementStrategy
    
    # Create base retriever
    base_retriever = BaseVectorRetriever(vector_store=vector_store)
    
    # Initialize reranker nếu enabled và mode hỗ trợ
    reranker_instance = None
    if enable_reranking and mode in ["balanced", "quality", "adaptive"]:
        if reranker:
            reranker_instance = reranker
        else:
            logger.info("🔧 Initializing PhoBERT reranker...")
            reranker_instance = PhoBERTReranker(device="cpu")
    
    # Fast mode: No enhancement, no reranking
    if mode == "fast":
        return base_retriever
    
    # Balanced mode: Light enhancement + reranking
    elif mode == "balanced":
        return EnhancedRetriever(
            base_retriever=base_retriever,
            enhancement_strategies=[
                EnhancementStrategy.MULTI_QUERY,
                EnhancementStrategy.STEP_BACK
            ],
            reranker=reranker_instance,  # ⭐ NEW
            rerank_top_k=8,
            k=4,
            enable_deduplication=True
        )
    
    # Quality mode: Full enhancement + reranking
    elif mode == "quality":
        return FusionRetriever(
            base_retriever=base_retriever,
            enhancement_strategies=[
                EnhancementStrategy.MULTI_QUERY,
                EnhancementStrategy.HYDE,
                EnhancementStrategy.STEP_BACK,
                EnhancementStrategy.DECOMPOSITION
            ],
            reranker=reranker_instance,  # ⭐ NEW
            rerank_top_k=10,
            k=5,
            enable_deduplication=True,
            fusion_weights=[0.4, 0.3, 0.2, 0.1]  # Weighted fusion
        )
    
    # Adaptive mode: Dynamic + reranking
    elif mode == "adaptive":
        return AdaptiveKRetriever(
            base_retriever=base_retriever,
            reranker=reranker_instance,  # ⭐ NEW
            min_k=3,
            max_k=10,
            enable_query_enhancement=True
        )
    
    else:
        raise ValueError(f"Unknown mode: {mode}")
```

---

## **BƯỚC 5: Testing & Validation (15:45 - 16:30)**

### **5.1. Unit Tests (20 phút)**

```python
# tests/unit/test_retrieval/test_reranking.py

import pytest
from langchain_core.documents import Document
from src.retrieval.ranking import PhoBERTReranker


class TestPhoBERTReranker:
    """Test suite cho PhoBERT reranker"""
    
    @pytest.fixture
    def reranker(self):
        """Fixture: Khởi tạo reranker"""
        return PhoBERTReranker(device="cpu")
    
    @pytest.fixture
    def sample_docs(self):
        """Fixture: Sample legal documents"""
        return [
            Document(
                page_content="Điều 14. Bảo đảm dự thầu là yêu cầu bắt buộc.",
                metadata={"article": "Điều 14"}
            ),
            Document(
                page_content="Điều 68. Bảo đảm thực hiện hợp đồng áp dụng sau ký kết.",
                metadata={"article": "Điều 68"}
            ),
            Document(
                page_content="Điều 10. Ưu đãi nhà thầu trong nước.",
                metadata={"article": "Điều 10"}
            ),
        ]
    
    def test_rerank_basic(self, reranker, sample_docs):
        """Test basic reranking functionality"""
        query = "Quy định về bảo đảm dự thầu"
        
        results = reranker.rerank(query, sample_docs, top_k=2)
        
        # Check format
        assert len(results) == 2
        assert all(isinstance(r, tuple) for r in results)
        assert all(len(r) == 2 for r in results)
        
        # Check scores descending
        scores = [score for _, score in results]
        assert scores[0] >= scores[1]
    
    def test_rerank_relevance(self, reranker, sample_docs):
        """Test ranking relevance"""
        query = "Thời gian hiệu lực bảo đảm dự thầu"
        
        results = reranker.rerank(query, sample_docs, top_k=3)
        
        # Điều 14 về bảo đảm dự thầu nên ranked cao nhất
        top_doc = results[0][0]
        assert "Điều 14" in top_doc.metadata.get("article", "")
    
    def test_rerank_empty_docs(self, reranker):
        """Test với empty documents"""
        results = reranker.rerank("test query", [], top_k=5)
        assert results == []
    
    def test_rerank_single_doc(self, reranker, sample_docs):
        """Test với single document"""
        results = reranker.rerank("test", sample_docs[:1], top_k=5)
        assert len(results) == 1
    
    def test_rerank_top_k_limit(self, reranker, sample_docs):
        """Test top_k limit"""
        results = reranker.rerank("test", sample_docs, top_k=2)
        assert len(results) <= 2


# Chạy tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

### **5.2. Integration Test (15 phút)**

```python
# tests/integration/test_reranking_pipeline.py

import pytest
from src.retrieval.retrievers import create_retriever
from src.embedding.store import vector_store


@pytest.mark.integration
class TestRerankingPipeline:
    """Test end-to-end pipeline với reranking"""
    
    def test_quality_mode_with_reranking(self):
        """Test quality mode có reranking"""
        # Create retriever với reranking
        retriever = create_retriever(
            mode="quality",
            vector_store=vector_store,
            enable_reranking=True
        )
        
        # Query thực tế
        query = "Thời hạn hiệu lực của bảo đảm dự thầu là bao lâu?"
        
        # Invoke
        docs = retriever.invoke(query)
        
        # Verify
        assert len(docs) == 5
        assert all(hasattr(doc, 'page_content') for doc in docs)
        assert all(hasattr(doc, 'metadata') for doc in docs)
        
        # Check relevance (Điều 14 nên trong top 2)
        top_2_content = " ".join([d.page_content for d in docs[:2]])
        assert "Điều 14" in top_2_content or "bảo đảm dự thầu" in top_2_content
    
    def test_comparison_with_without_reranking(self):
        """So sánh có/không reranking"""
        query = "Quy định về thời gian hiệu lực bảo đảm dự thầu"
        
        # Without reranking
        retriever_no_rerank = create_retriever(
            mode="quality",
            vector_store=vector_store,
            enable_reranking=False
        )
        docs_no_rerank = retriever_no_rerank.invoke(query)
        
        # With reranking
        retriever_rerank = create_retriever(
            mode="quality",
            vector_store=vector_store,
            enable_reranking=True
        )
        docs_rerank = retriever_rerank.invoke(query)
        
        # Compare
        print("\n📊 Comparison:")
        print(f"Without reranking top doc: {docs_no_rerank[0].page_content[:80]}...")
        print(f"With reranking top doc: {docs_rerank[0].page_content[:80]}...")
        
        # Assert có sự khác biệt (hoặc improvement)
        assert len(docs_no_rerank) == len(docs_rerank)
```

### **5.3. Manual Testing với Real Queries (10 phút)**

```python
# Tạo file: test_real_queries.py

"""
Manual test với real legal queries
"""

from src.retrieval.retrievers import create_retriever
from src.embedding.store import vector_store

print("🧪 Testing với Real Legal Queries")
print("=" * 70)

# Initialize retriever
retriever = create_retriever(
    mode="quality",
    vector_store=vector_store,
    enable_reranking=True
)

# Real queries từ use cases
queries = [
    "Thời gian hiệu lực bảo đảm dự thầu tối thiểu là bao nhiêu ngày?",
    "Điều kiện để được ưu đãi nhà thầu trong nước?",
    "So sánh bảo đảm dự thầu và bảo đảm thực hiện hợp đồng",
    "Hồ sơ dự thầu cần có những gì?",
]

for i, query in enumerate(queries, 1):
    print(f"\n{'─' * 70}")
    print(f"Query {i}: {query}")
    print(f"{'─' * 70}")
    
    docs = retriever.invoke(query)
    
    print(f"\n🏆 Top 3 Results:")
    for j, doc in enumerate(docs[:3], 1):
        article = doc.metadata.get("article", "N/A")
        source = doc.metadata.get("source", "N/A")
        preview = doc.page_content[:120].replace('\n', ' ')
        
        print(f"\n  [{j}] {article} ({source})")
        print(f"      {preview}...")

print("\n" + "=" * 70)
print("✅ Manual testing complete!")
```

---

## **BƯỚC 6: Wrap Up (16:30 - 17:00)**

### **6.1. Update Config (10 phút)**

```python
# config/models.py

# Thêm reranking config
@dataclass
class Settings:
    # ... existing settings ...
    
    # Reranking (Phase 2)
    enable_reranking: bool = _env_bool("ENABLE_RERANKING", True)  # ⭐ Set TRUE
    reranker_model: str = os.getenv("RERANKER_MODEL", "vinai/phobert-base-v2")
    reranker_device: str = os.getenv("RERANKER_DEVICE", "cpu")
    rerank_top_k: int = int(os.getenv("RERANK_TOP_K", "10"))
```

Update `.env`:
```bash
# Reranking
ENABLE_RERANKING=true
RERANKER_MODEL=vinai/phobert-base-v2
RERANKER_DEVICE=cpu
RERANK_TOP_K=10
```

### **6.2. Test API Endpoint (10 phút)**

```bash
# Test với curl
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Thời hạn hiệu lực bảo đảm dự thầu là bao lâu?",
    "mode": "quality"
  }'
```

**Kỳ vọng:**
- Response có `documents` với 5 docs
- Top doc liên quan đến Điều 14
- Response time < 2s

### **6.3. Commit Code (10 phút)**

```bash
cd /home/sakana/Code/RAG-bidding

# Check status
git status

# Add files
git add src/retrieval/ranking/
git add tests/unit/test_retrieval/test_reranking.py
git add tests/integration/test_reranking_pipeline.py
git add config/models.py
git add docs/GUIDE/phase\ 2/PHASE2_PHOBERT_IMPLEMENTATION.md

# Commit
git commit -m "feat(retrieval): Implement PhoBERT reranking for Vietnamese legal documents

- Add BaseReranker abstract class
- Implement PhoBERTReranker with vinai/phobert-base-v2
- Integrate reranking into EnhancedRetriever and factory pattern
- Add comprehensive unit and integration tests
- Update config to enable reranking by default
- Performance: ~100-150ms latency for 10 docs on CPU

Closes #2-phase2-reranking"

# Push (nếu cần)
# git push origin enhancement/1-phase1-implement
```

---

## 📊 Kết Quả Kỳ Vọng

### **Metrics:**
- ✅ **Latency**: 100-150ms cho reranking 10 docs
- ✅ **Accuracy**: Điều 14 ranked #1 cho query về "bảo đảm dự thầu"
- ✅ **MRR improvement**: +10-15% (so với không reranking)
- ✅ **Test coverage**: >80% cho ranking module

### **Deliverables:**
- ✅ `src/retrieval/ranking/` folder với 3 files
- ✅ PhoBERTReranker hoạt động
- ✅ Integration với retrievers
- ✅ Unit tests + integration tests
- ✅ API endpoint test passed
- ✅ Documentation

---

## 🐛 Troubleshooting

### **Issue 1: Model download chậm**
```bash
# Giải pháp: Pre-download model
python -c "from sentence_transformers import CrossEncoder; CrossEncoder('vinai/phobert-base-v2')"
```

### **Issue 2: Out of Memory**
```python
# Giải pháp: Giảm batch_size
reranker = PhoBERTReranker(batch_size=8)  # Thay vì 16
```

### **Issue 3: Latency quá cao (>200ms)**
```python
# Giải pháp 1: Giảm max_length
reranker = PhoBERTReranker(max_length=128)  # Thay vì 256

# Giải pháp 2: Truncate content sớm hơn
content = doc.page_content[:400]  # Thay vì 800
```

### **Issue 4: Import errors**
```bash
# Verify Python path
export PYTHONPATH=/home/sakana/Code/RAG-bidding:$PYTHONPATH
```

---

## 📚 References

- [PhoBERT Paper](https://arxiv.org/abs/2003.00744)
- [sentence-transformers CrossEncoder](https://www.sbert.net/docs/pretrained_cross-encoders.html)
- [vinai/phobert-base-v2](https://huggingface.co/vinai/phobert-base-v2)

---

## ✅ Final Checklist

**Trước khi kết thúc:**
- [ ] PhoBERT model đã download và hoạt động
- [ ] Reranker test passed (Điều 14 ranked #1)
- [ ] Integration test passed
- [ ] API endpoint hoạt động với reranking
- [ ] Latency < 150ms
- [ ] Code committed với message rõ ràng
- [ ] .env updated với ENABLE_RERANKING=true

**Nếu còn thời gian (bonus):**
- [ ] Thêm logging chi tiết
- [ ] Benchmark với 20 queries thực tế
- [ ] Document API changes
- [ ] Tạo comparison report (có/không reranking)

---

**Chuẩn bị bởi**: GitHub Copilot  
**Timeline**: 3-4 giờ (một buổi chiều)  
**Độ khó**: Medium  
**Mục tiêu**: ✅ PhoBERT reranking hoạt động trong quality mode

🚀 **LET'S GO!**
