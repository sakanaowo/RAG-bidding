# 📋 Giai đoạn 2: Xếp Hạng Lại Tài Liệu - Kế Hoạch Triển Khai

**Dự án**: RAG-bidding (Hệ thống RAG cho Văn bản Pháp luật Việt Nam)  
**Ngày**: 16 tháng 10, 2025  
**Nhánh**: `enhancement/2-phase2-reranking` (sẽ được tạo)  
**Điều kiện tiên quyết**: Giai đoạn 1 Cải thiện Truy vấn ✅ Hoàn thành

---

## 🎯 Phân Tích Bối Cảnh Dự Án

### **Đặc điểm Lĩnh vực:**

1. **Văn bản Pháp luật Việt Nam**
   - Luật Đấu thầu 2023, Nghị định, Thông tư
   - Cấu trúc cao: Điều, Khoản, Chương
   - Thuật ngữ pháp lý phức tạp
   - Nội dung dài (chunks ~1000 tokens)

2. **Kiến trúc Hiện tại:**
   - ✅ Cải thiện Truy vấn: 4 chiến lược (Multi-Query, HyDE, Step-Back, Decomposition)
   - ✅ Vector Store: pgvector + `text-embedding-3-large` (3072 dim)
   - ✅ Retrievers Mô-đun: Base, Enhanced, Fusion, Adaptive
   - ⏳ Reranking: Đã cấu hình nhưng CHƯA triển khai

3. **Yêu cầu Hiệu suất:**
   - Chế độ nhanh: <300ms
   - Chế độ cân bằng: <800ms  
   - Chế độ chất lượng: <1500ms (có thể sử dụng reranking ở đây)
   - Chế độ thích ứng: Động (dùng reranking cho câu hỏi phức tạp)

4. **Nhu cầu Người dùng:**
   - Câu hỏi pháp lý phức tạp yêu cầu xếp hạng chính xác
   - Câu hỏi đa khía cạnh (ví dụ: "So sánh quy định cũ và mới")
   - Cần độ liên quan cao (sai sót pháp lý có chi phí cao)

---

## 🏗️ Thiết Kế Kiến Trúc

### **Chiến lược Reranking: Tiếp cận Đa cấp**

```
Query → [Giai đoạn 1: Retrieval] → [Giai đoạn 2: Reranking] → Kết quả Top
         ↓                          ↓
    Vector Search (K=10)        Rerank xuống K=5
    + Cải thiện Query           + Cross-Encoder
                                + Chấm điểm Pháp luật VN
```

### **Cấu trúc Module:**

```
src/retrieval/ranking/
├── __init__.py
├── base_reranker.py              # Lớp cơ sở trừu tượng
├── cross_encoder_reranker.py     # Phương pháp chính (độ chính xác)
├── cohere_reranker.py            # Dựa trên API tùy chọn (nếu cần)
├── llm_reranker.py               # Dựa trên GPT (cho trường hợp phức tạp)
└── legal_score_reranker.py       # Đặc thù lĩnh vực (Pháp luật VN)
```

---

## 📊 So Sánh Các Phương Pháp Reranking

### **1. Cross-Encoder Reranking** ⭐ **ĐƯỢC ĐỀ XUẤT LÀM CHÍNH**

**Các tùy chọn Model:**
- `bkai-foundation-models/vietnamese-bi-encoder` (Tối ưu cho tiếng Việt)
- `BAAI/bge-reranker-v2-m3` (Đa ngôn ngữ, hỗ trợ tiếng Việt)
- `ms-marco-MiniLM-L-12-v2` (Nhanh, chủ yếu tiếng Anh nhưng hoạt động)

**Ưu điểm:**
- ✅ Độ chính xác cao (tốt hơn bi-encoder)
- ✅ Triển khai cục bộ (không tốn phí API)
- ✅ Suy luận nhanh (~50-100ms cho 10 docs)
- ✅ Có thể fine-tune trên lĩnh vực pháp luật

**Nhược điểm:**
- ❌ Chậm hơn so với chỉ vector search
- ❌ Cần tải model (~400MB)

**Trường hợp sử dụng:**
- Chế độ chất lượng (luôn dùng)
- Chế độ cân bằng (dùng cho độ phức tạp trung bình+)
- Chế độ thích ứng (dùng cho câu hỏi phức tạp)

---

### **2. LLM-Based Reranking** (GPT-4o-mini)

**Triển khai:**
- Sử dụng LLM có sẵn (gpt-4o-mini)
- Prompt: "Xếp hạng các tài liệu này theo độ liên quan với câu hỏi..."
- Temperature: 0 (xác định)

**Ưu điểm:**
- ✅ Không cần thêm dependencies
- ✅ Hiểu xuất sắc văn bản pháp luật tiếng Việt
- ✅ Có thể cung cấp lý do cho xếp hạng

**Nhược điểm:**
- ❌ Chậm hơn (~500-800ms cho 10 docs)
- ❌ Chi phí API ($0.150/1M tokens)
- ❌ Ít đáng tin cậy hơn cross-encoder cho xếp hạng thuần túy

**Trường hợp sử dụng:**
- Chế độ chất lượng (như xác thực phụ)
- Câu hỏi đa khía cạnh rất phức tạp
- Khi cần giải thích xếp hạng

---

### **3. Cohere Rerank API** (Tùy chọn)

**Model:** `rerank-multilingual-v3.0`

**Ưu điểm:**
- ✅ Độ chính xác tiên tiến
- ✅ Hỗ trợ tiếng Việt
- ✅ Không cần cơ sở hạ tầng cục bộ

**Nhược điểm:**
- ❌ Phụ thuộc API
- ❌ Chi phí: $1.00 cho 1000 tìm kiếm
- ❌ Độ trễ: ~200-400ms

**Trường hợp sử dụng:**
- Nếu cross-encoder tự host không đủ chính xác
- Triển khai doanh nghiệp có ngân sách

---

### **4. Legal Domain Scoring** (Tùy chỉnh)

**Tính năng:**
- Tăng cường khớp chính xác (Điều X, Khoản Y)
- Khớp cấu trúc (query đề cập "Chương" → ưu tiên chunks có Chương)
- Mật độ từ khóa (thuật ngữ pháp lý)
- Chấm điểm gần đây (Luật 2023 > phiên bản cũ)

**Ưu điểm:**
- ✅ Đặc thù lĩnh vực
- ✅ Rất nhanh (~5ms)
- ✅ Không phụ thuộc bên ngoài
- ✅ Chấm điểm minh bạch

**Nhược điểm:**
- ❌ Dựa trên quy tắc (không học)
- ❌ Độ chính xác thấp hơn các model ML

**Trường hợp sử dụng:**
- Chế độ nhanh (chỉ dùng cái này)
- Như một booster cho điểm cross-encoder
- Phá vỡ tie

---

## 🎯 Kế Hoạch Triển Khai Được Đề Xuất

### **Giai đoạn 2A: Reranking Cốt lõi (Tuần 1)** ⭐ **BẮT ĐẦU TẠI ĐÂY**

**Mục tiêu:** Triển khai cross-encoder reranking cho chế độ chất lượng

#### **Bước 1: Cơ sở Hạ tầng Cơ bản** (Ngày 1-2)
```python
# src/retrieval/ranking/base_reranker.py
from abc import ABC, abstractmethod
from typing import List, Tuple
from langchain_core.documents import Document

class BaseReranker(ABC):
    """Lớp cơ sở trừu tượng cho tất cả rerankers"""
    
    @abstractmethod
    def rerank(
        self, 
        query: str, 
        documents: List[Document],
        top_k: int = 5
    ) -> List[Tuple[Document, float]]:
        """
        Xếp hạng lại tài liệu theo độ liên quan với query
        
        Returns:
            List các tuple (document, score), sắp xếp theo score giảm dần
        """
        pass
```

#### **Bước 2: Triển khai Cross-Encoder** (Ngày 2-3)
```python
# src/retrieval/ranking/cross_encoder_reranker.py
from sentence_transformers import CrossEncoder
from typing import List, Tuple
from langchain_core.documents import Document
import logging

logger = logging.getLogger(__name__)

class CrossEncoderReranker(BaseReranker):
    """
    Cross-Encoder reranking cho tài liệu pháp luật Việt Nam
    """
    
    def __init__(
        self, 
        model_name: str = "BAAI/bge-reranker-v2-m3",
        device: str = "cpu",  # hoặc "cuda" nếu có GPU
        cache_dir: str = ".cache/rerankers"
    ):
        """
        Args:
            model_name: Tên model HuggingFace
                Các tùy chọn:
                - "BAAI/bge-reranker-v2-m3" (đa ngôn ngữ, tốt cho tiếng Việt)
                - "bkai-foundation-models/vietnamese-bi-encoder" (đặc thù VN)
            device: "cpu" hoặc "cuda"
            cache_dir: Thư mục cache model
        """
        logger.info(f"Đang tải cross-encoder model: {model_name}")
        self.model = CrossEncoder(model_name, device=device)
        logger.info(f"Cross-encoder đã tải trên {device}")
    
    def rerank(
        self, 
        query: str, 
        documents: List[Document],
        top_k: int = 5
    ) -> List[Tuple[Document, float]]:
        """Xếp hạng lại tài liệu sử dụng cross-encoder"""
        
        if not documents:
            return []
        
        # Chuẩn bị các cặp query-document
        pairs = [[query, doc.page_content] for doc in documents]
        
        # Lấy điểm liên quan
        scores = self.model.predict(pairs)
        
        # Sắp xếp theo điểm giảm dần
        doc_scores = list(zip(documents, scores))
        doc_scores.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f"Đã rerank {len(documents)} docs, điểm top: {doc_scores[0][1]:.4f}")
        
        return doc_scores[:top_k]
```

#### **Bước 3: Tích hợp với Retrievers** (Ngày 3-4)
```python
# Cập nhật: src/retrieval/retrievers/enhanced_retriever.py

class EnhancedRetriever(BaseRetriever):
    """Retriever với cải thiện query + reranking tùy chọn"""
    
    base_retriever: BaseVectorRetriever
    enhancement_strategies: Optional[List[EnhancementStrategy]] = None
    reranker: Optional[BaseReranker] = None  # ⭐ MỚI
    k: int = 5
    rerank_top_k: int = 10  # ⭐ MỚI: Lấy nhiều hơn, rerank xuống k
    
    def _get_relevant_documents(self, query: str, ...) -> List[Document]:
        # Bước 1: Cải thiện query
        if self.query_enhancer:
            queries = self.query_enhancer.enhance(query)
        else:
            queries = [query]
        
        # Bước 2: Retrieve (lấy nhiều docs nếu reranking)
        retrieval_k = self.rerank_top_k if self.reranker else self.k
        all_docs = []
        for q in queries:
            docs = self.base_retriever.invoke(q, k=retrieval_k)
            all_docs.extend(docs)
        
        # Bước 3: Loại bỏ trùng lặp
        if self.deduplication:
            all_docs = self._deduplicate_docs(all_docs)
        
        # Bước 4: Rerank ⭐ MỚI
        if self.reranker:
            doc_scores = self.reranker.rerank(query, all_docs, top_k=self.k)
            return [doc for doc, score in doc_scores]
        
        return all_docs[:self.k]
```

#### **Bước 4: Cập nhật Factory Pattern** (Ngày 4)
```python
# Cập nhật: src/retrieval/retrievers/__init__.py

def create_retriever(
    mode: str = "balanced",
    vector_store=None,
    enable_reranking: bool = True  # ⭐ Tham số MỚI
) -> BaseRetriever:
    """Tạo retriever dựa trên mode"""
    
    base_retriever = BaseVectorRetriever(vector_store=vector_store)
    
    # Khởi tạo reranker nếu được bật
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
            reranker=reranker,  # ⭐ MỚI
            rerank_top_k=8,
            k=4
        )
    
    elif mode == "quality":
        return FusionRetriever(
            base_retriever=base_retriever,
            reranker=reranker,  # ⭐ MỚI
            rerank_top_k=10,
            k=5
        )
    
    # ... chế độ adaptive tương tự
```

#### **Bước 5: Kiểm thử** (Ngày 5)
```python
# tests/unit/test_retrieval/test_reranking.py

def test_cross_encoder_reranker():
    """Kiểm thử cross-encoder reranking"""
    reranker = CrossEncoderReranker()
    
    query = "Quy định về bảo đảm dự thầu trong Luật Đấu thầu 2023"
    documents = [
        Document(page_content="Điều 14. Bảo đảm dự thầu..."),
        Document(page_content="Điều 68. Bảo đảm thực hiện hợp đồng..."),
        Document(page_content="Điều 10. Ưu đãi nhà thầu trong nước...")
    ]
    
    results = reranker.rerank(query, documents, top_k=2)
    
    assert len(results) == 2
    assert results[0][1] > results[1][1]  # Điểm giảm dần
    assert "Điều 14" in results[0][0].page_content  # Liên quan nhất trước

def test_retriever_with_reranking():
    """Kiểm thử enhanced retriever với reranking"""
    retriever = create_retriever(mode="quality", enable_reranking=True)
    
    docs = retriever.invoke("Thời gian hiệu lực bảo đảm dự thầu")
    
    assert len(docs) == 5
    # Xác minh reranking cải thiện độ liên quan (cần kiểm tra thủ công)
```

---

### **Giai đoạn 2B: LLM Reranking (Tuần 2)** (Tùy chọn)

**Mục tiêu:** Thêm LLM-based reranking cho câu hỏi rất phức tạp

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
    """LLM-based reranking sử dụng GPT-4o-mini"""
    
    def __init__(self, model_name: str = "gpt-4o-mini", temperature: float = 0):
        self.llm = ChatOpenAI(model=model_name, temperature=temperature)
        self.prompt = ChatPromptTemplate.from_template(RERANK_PROMPT)
    
    def rerank(self, query: str, documents: List[Document], top_k: int = 5) -> List[Tuple[Document, float]]:
        # Định dạng tài liệu
        docs_text = "\n\n".join([
            f"[{i+1}] {doc.page_content[:500]}..." 
            for i, doc in enumerate(documents)
        ])
        
        # Lấy xếp hạng từ LLM
        chain = self.prompt | self.llm
        response = chain.invoke({
            "query": query,
            "documents": docs_text,
            "n": len(documents)
        })
        
        # Phân tích response (ví dụ: "3,1,5,2,4")
        ranking = [int(x.strip()) - 1 for x in response.content.split(",")]
        
        # Sắp xếp lại tài liệu
        reranked = [documents[i] for i in ranking]
        
        # Gán điểm (cao nhất đến thấp nhất)
        scores = [1.0 - (i / len(reranked)) for i in range(len(reranked))]
        
        return list(zip(reranked, scores))[:top_k]
```

**Trường hợp sử dụng:** Chế độ chất lượng + câu hỏi rất phức tạp (điểm phân tích độ phức tạp > 0.8)

---

### **Giai đoạn 2C: Legal Domain Scoring (Tuần 2)** (Booster)

**Mục tiêu:** Thêm chấm điểm đặc thù pháp luật Việt Nam như một booster

```python
# src/retrieval/ranking/legal_score_reranker.py

import re
from typing import List, Tuple
from langchain_core.documents import Document

class LegalScoreReranker(BaseReranker):
    """Chấm điểm tài liệu pháp luật Việt Nam"""
    
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
        """Tính điểm liên quan pháp lý"""
        score = 0.0
        content = doc.page_content.lower()
        query_lower = query.lower()
        
        # 1. Khớp cấu trúc chính xác (ví dụ: "Điều 14")
        dieu_matches = re.findall(r"điều\s+\d+", query_lower)
        for match in dieu_matches:
            if match in content:
                score += 0.5  # Tăng cao cho khớp chính xác
        
        # 2. Mật độ từ khóa
        keyword_count = sum(1 for kw in self.LEGAL_KEYWORDS if kw in content)
        score += keyword_count * 0.05
        
        # 3. Gần đây (ưu tiên luật mới hơn)
        if "2023" in content or "2024" in content:
            score += 0.1
        
        # 4. Tăng cường metadata
        metadata = doc.metadata
        if metadata.get("source") == "official_gazette":
            score += 0.15
        
        return score
```

**Trường hợp sử dụng:** Chế độ nhanh (chỉ cái này), hoặc như một booster cho cross-encoder

---

## 📝 Cập Nhật Cấu Hình

### **Cập nhật `config/models.py`:**

```python
@dataclass
class Settings:
    # ... cài đặt hiện có ...
    
    # Reranking tài liệu (Giai đoạn 2)
    enable_reranking: bool = _env_bool("ENABLE_RERANKING", False)  # ⭐ Đặt FALSE ban đầu
    rerank_method: str = os.getenv("RERANK_METHOD", "cross_encoder")  # cross_encoder, llm, legal_score
    rerank_model: str = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
    rerank_top_k: int = int(os.getenv("RERANK_TOP_K", "10"))
    final_docs_k: int = int(os.getenv("FINAL_DOCS_K", "5"))
    rerank_device: str = os.getenv("RERANK_DEVICE", "cpu")  # cpu hoặc cuda

# Cập nhật presets
class RAGPresets:
    @staticmethod
    def get_quality_mode() -> Dict[str, object]:
        return {
            "enable_query_enhancement": True,
            "enable_reranking": True,  # ⭐ Bật sau khi triển khai
            "rerank_method": "cross_encoder",
            "enable_answer_validation": True,
            "rerank_top_k": 10,
            "final_docs_k": 5,
        }
    
    @staticmethod
    def get_balanced_mode() -> Dict[str, object]:
        return {
            "enable_query_enhancement": True,
            "enable_reranking": True,  # ⭐ Bật sau khi triển khai
            "rerank_method": "cross_encoder",
            "rerank_top_k": 8,
            "final_docs_k": 4,
        }
```

---

## 🧪 Chiến Lược Kiểm Thử

### **Unit Tests:**
```bash
tests/unit/test_retrieval/
├── test_reranker_base.py           # Kiểm thử lớp base
├── test_cross_encoder_reranker.py  # Kiểm thử cross-encoder
├── test_llm_reranker.py            # Kiểm thử LLM reranker
└── test_legal_score_reranker.py    # Kiểm thử chấm điểm pháp lý
```

### **Integration Tests:**
```python
# tests/integration/test_reranking_pipeline.py

def test_end_to_end_with_reranking():
    """Kiểm thử pipeline đầy đủ: query → enhancement → retrieval → reranking → answer"""
    
    query = "Thời hạn hiệu lực của bảo đảm dự thầu là bao lâu?"
    
    # Tạo retriever với reranking
    retriever = create_retriever(mode="quality", enable_reranking=True)
    
    # Invoke
    docs = retriever.invoke(query)
    
    # Xác minh
    assert len(docs) == 5
    assert any("Điều 14" in doc.page_content for doc in docs[:2])  # Top 2 nên liên quan
```

### **Benchmark Tests:**
```python
# tests/benchmarks/test_reranking_performance.py

def benchmark_reranking_latency():
    """Đo overhead reranking"""
    
    results = {
        "no_reranking": [],
        "cross_encoder": [],
        "llm": [],
        "legal_score": []
    }
    
    queries = load_test_queries()  # 100 câu hỏi mẫu
    
    for query in queries:
        # Kiểm thử từng phương pháp
        # ... đo thời gian
    
    print(f"Cross-Encoder avg latency: {avg(results['cross_encoder'])}ms")
    # Kỳ vọng: ~50-100ms cho 10 docs
```

---

## 📊 Chỉ Số Thành Công

### **Chỉ số Độ chính xác:**
- **MRR (Mean Reciprocal Rank)**: Mục tiêu > 0.85 (vs baseline 0.70)
- **NDCG@5**: Mục tiêu > 0.90 (vs baseline 0.75)
- **Recall@5**: Mục tiêu > 0.95 (vs baseline 0.85)

### **Chỉ số Hiệu suất:**
- **Chế độ nhanh**: <300ms (không reranking)
- **Chế độ cân bằng**: <800ms (cross-encoder)
- **Chế độ chất lượng**: <1500ms (cross-encoder + xác thực LLM)

### **Chỉ số Người dùng:**
- **Hài lòng về độ liên quan**: Phản hồi người dùng > 4/5
- **Tỷ lệ hoàn thành nhiệm vụ**: > 90%

---

## 🚀 Kế Hoạch Triển Khai

### **Triển khai Giai đoạn 2A (Cuối Tuần 1):**
1. ✅ Triển khai cross-encoder reranker
2. ✅ Tích hợp với chế độ chất lượng
3. ✅ Chạy benchmarks
4. ✅ Triển khai lên staging
5. ✅ A/B test chế độ chất lượng (có/không reranking)
6. ✅ Giám sát chỉ số trong 3 ngày
7. ✅ Triển khai lên production nếu chỉ số cải thiện

### **Triển khai Giai đoạn 2B (Tuần 2):**
1. Triển khai LLM reranker
2. Chỉ dùng cho câu hỏi rất phức tạp
3. Giám sát chi phí vs lợi ích độ chính xác

### **Triển khai Giai đoạn 2C (Tuần 2):**
1. Triển khai legal scoring
2. Dùng như booster trong chế độ nhanh
3. Benchmark tác động độ trễ (mục tiêu <10ms)

---

## 💰 Phân Tích Chi Phí

### **Cơ sở Hạ tầng:**
- **Cross-Encoder Model**: Miễn phí (tự host), ~400MB disk, ~1GB RAM
- **LLM Reranking**: $0.150/1M input tokens (~$0.0015 cho mỗi query với 10 docs)
- **Legal Scoring**: Miễn phí (dựa trên quy tắc)

### **Chi phí Ước tính (1000 queries/ngày):**
- Chỉ Cross-Encoder: **$0/tháng** (compute đã tồn tại)
- + LLM cho 10% câu hỏi phức tạp: **~$5/tháng**
- Cohere Rerank (thay thế): **$30/tháng** (1000 tìm kiếm)

**Đề xuất:** Dùng cross-encoder làm chính, LLM cho top 10% câu hỏi phức tạp

---

## 🔧 Dependencies Cần Thêm

```bash
# Thêm vào requirements.txt
sentence-transformers>=2.2.0  # Cho cross-encoder
torch>=2.0.0                  # PyTorch backend
transformers>=4.30.0          # HuggingFace models

# Tùy chọn:
# cohere>=4.0.0               # Nếu dùng Cohere Rerank API
```

---

## 📚 Tài Nguyên & Tham Khảo

### **Models:**
- [BAAI/bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3) - Reranker đa ngôn ngữ
- [bkai-foundation-models/vietnamese-bi-encoder](https://huggingface.co/bkai-foundation-models/vietnamese-bi-encoder) - Đặc thù VN
- [Cohere Rerank API](https://docs.cohere.com/docs/reranking)

### **Papers:**
- [RankGPT: Is ChatGPT Good at Reranking?](https://arxiv.org/abs/2304.09542)
- [ColBERTv2: Effective and Efficient Retrieval](https://arxiv.org/abs/2112.01488)

### **Tutorials:**
- [Sentence-Transformers Cross-Encoders](https://www.sbert.net/examples/applications/cross-encoder/README.html)

---

## ✅ Danh Sách Kiểm Tra

### **Giai đoạn 2A: Reranking Cốt lõi**
- [ ] Tạo cấu trúc thư mục `src/retrieval/ranking/`
- [ ] Triển khai lớp trừu tượng `BaseReranker`
- [ ] Triển khai `CrossEncoderReranker`
- [ ] Cập nhật `EnhancedRetriever` để hỗ trợ reranking
- [ ] Cập nhật `FusionRetriever` để hỗ trợ reranking
- [ ] Cập nhật factory pattern trong `__init__.py`
- [ ] Thêm unit tests (coverage > 90%)
- [ ] Thêm integration tests
- [ ] Benchmark độ trễ
- [ ] Cập nhật config presets (bật reranking trong chế độ quality/balanced)
- [ ] Cập nhật tài liệu API
- [ ] Triển khai lên staging
- [ ] A/B test trong 3 ngày
- [ ] Triển khai lên production

### **Giai đoạn 2B: LLM Reranking** (Tùy chọn)
- [ ] Triển khai `LLMReranker`
- [ ] Thêm định tuyến dựa trên độ phức tạp (độ phức tạp cao → LLM rerank)
- [ ] Giám sát chi phí
- [ ] A/B test lợi ích độ chính xác

### **Giai đoạn 2C: Legal Scoring** (Tùy chọn)
- [ ] Triển khai `LegalScoreReranker`
- [ ] Dùng trong chế độ nhanh
- [ ] Dùng như booster cho cross-encoder
- [ ] Benchmark độ trễ

---

## 🎓 Kết Quả Học Tập

Sau Giai đoạn 2, team sẽ có:
- ✅ Hiểu biết về reranking trong hệ thống RAG
- ✅ Kinh nghiệm với cross-encoder models
- ✅ Kiến thức mô hình LLM-as-judge
- ✅ Kỹ thuật chấm điểm đặc thù lĩnh vực
- ✅ Kỹ năng tối ưu hiệu suất

---

**Ý tưởng Giai đoạn Tiếp theo (Giai đoạn 3):**
- Hybrid Search (BM25 + Vector)
- Fine-tuning cross-encoder trên dữ liệu pháp luật Việt Nam
- Cải thiện hiểu câu hỏi
- Lớp caching cho câu hỏi phổ biến

---

**Chuẩn bị bởi**: GitHub Copilot  
**Trạng thái**: Sẵn sàng để Triển khai  
**Timeline Ước tính**: 2 tuần (Giai đoạn 2A: 1 tuần, Giai đoạn 2B+C: 1 tuần)
