# 🔍 IMPACT ANALYSIS: Multiple Chunking Strategies on Embedding

**Date:** December 2024  
**Question:** Sử dụng nhiều chunking strategies khác nhau có ảnh hưởng đến embedding không?

---

## 🎯 TL;DR - QUICK ANSWER

**✅ KHÔNG ảnh hưởng tiêu cực** - nếu thiết kế đúng

**Lý do:**
1. ✅ Embedding model KHÔNG quan tâm cách chunk được tạo ra
2. ✅ Embedding chỉ quan tâm **text content** và **semantic meaning**
3. ✅ Miễn là chunk có **semantic coherence** (nghĩa rõ ràng, trọn vẹn)

**Nhưng CẦN:**
- ⚠️ Chunk size consistency (đều ~500-1,500 chars)
- ⚠️ Semantic boundary preservation (không cắt ngang câu/ý nghĩa)
- ⚠️ Metadata standardization (cùng schema)

---

## 📊 DETAILED ANALYSIS

### 1. Embedding Process Overview

```
Chunking Strategy → Text Chunks → Embedding Model → Vector Embeddings
     ↑                  ↓                ↓                  ↓
   (KHÁC NHAU)    (Input to model)  (Transforms)    (Dense vectors)
                       ↑
                 Model ONLY sees this
                 Model DOESN'T care HOW it was created
```

**Key Insight:** 
Embedding model (BGE-M3, PhoBERT, etc.) chỉ nhận **raw text** làm input.
Model KHÔNG biết (và KHÔNG quan tâm):
- ❌ Text này từ Điều hay từ Mẫu số
- ❌ Chunk này từ legal doc hay bidding doc
- ❌ Strategy nào đã tạo ra chunk này

**Model CHỈ quan tâm:**
- ✅ Text có semantic meaning không
- ✅ Text length (token count)
- ✅ Text quality (grammar, coherence)

---

### 2. Potential Issues (và cách TRÁNH)

#### ❌ Issue 1: Inconsistent Chunk Sizes

**Problem:**
```
Legal doc chunks:  500-1,500 chars (Điều-based)
Bidding chunks:    200-3,000 chars (Form-based - KHÔNG đều)
Report chunks:     100-2,500 chars (Subsection - KHÔNG đều)
Exam chunks:       150-400 chars  (Question - RẤT ngắn)
```

**Impact on Embedding:**
- ⚠️ Short chunks (< 300 chars): Thiếu context, embedding kém chất lượng
- ⚠️ Long chunks (> 2,000 chars): Quá nhiều concepts, embedding mất focus
- ⚠️ Inconsistent sizes: Retrieval bias (prefer longer/shorter chunks)

**Solution:**
```python
class BaseLegalChunker:
    def __init__(
        self,
        min_chunk_size: int = 300,   # Minimum for good embedding
        max_chunk_size: int = 1500,  # Maximum to keep focus
        target_chunk_size: int = 800, # Target sweet spot
    ):
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.target_chunk_size = target_chunk_size
    
    def _validate_chunk_size(self, chunk: UniversalChunk) -> bool:
        """Ensure chunk is not too short or too long"""
        if chunk.char_count < self.min_chunk_size:
            # Merge with adjacent chunks
            return self._merge_small_chunk(chunk)
        elif chunk.char_count > self.max_chunk_size:
            # Split into smaller chunks
            return self._split_large_chunk(chunk)
        return True
```

**Best Practice:**
✅ Enforce size constraints ACROSS ALL strategies
✅ Target range: 500-1,500 chars (~100-300 tokens for Vietnamese)

---

#### ❌ Issue 2: Semantic Boundary Violations

**Problem:**
```
BAD chunk (cắt ngang ý nghĩa):
"...yêu cầu về năng lực tài chính của nhà thầu bao gồm: vốn chủ sở hữu tối thiểu"
[CHUNK ENDS HERE - next chunk starts]
"100 tỷ đồng, doanh thu trung bình 3 năm gần nhất..."

→ Embedding của chunk 1: THIẾU thông tin quan trọng
→ Retrieval sẽ KÉM vì chunk không đầy đủ
```

**Solution:**
```python
def _split_with_semantic_boundaries(self, text: str, max_size: int) -> List[str]:
    """
    Split text respecting semantic boundaries:
    - Prefer splitting at paragraph breaks
    - Then sentence breaks (. ! ?)
    - Avoid splitting mid-sentence
    """
    chunks = []
    
    # 1. Try paragraph-based splitting
    paragraphs = text.split('\n\n')
    current_chunk = []
    current_size = 0
    
    for para in paragraphs:
        para_size = len(para)
        
        if current_size + para_size <= max_size:
            current_chunk.append(para)
            current_size += para_size
        else:
            # Save current chunk
            if current_chunk:
                chunks.append('\n\n'.join(current_chunk))
            
            # Start new chunk
            if para_size <= max_size:
                current_chunk = [para]
                current_size = para_size
            else:
                # Paragraph too long: split by sentences
                sentences = self._split_by_sentences(para)
                for sent in sentences:
                    if len(sent) <= max_size:
                        chunks.append(sent)
                    else:
                        # Sentence too long: sliding window
                        chunks.extend(self._split_with_overlap(sent, max_size))
    
    return chunks
```

**Best Practice:**
✅ Split at paragraph boundaries (best)
✅ Split at sentence boundaries (good)
✅ Use sliding window with overlap (last resort)
❌ NEVER split mid-sentence

---

#### ❌ Issue 3: Missing Context

**Problem:**
```
Legal doc chunk (HAS context):
"[Context: CHƯƠNG II - Quy định về năng lực nhà thầu]
Điều 15. Yêu cầu về năng lực tài chính
1. Nhà thầu phải có vốn chủ sở hữu..."

Bidding doc chunk (NO context):
"Yêu cầu về năng lực tài chính:
- Vốn chủ sở hữu tối thiểu 100 tỷ đồng
- Doanh thu trung bình..."

→ Embedding của legal chunk: BETTER (có context "Chương II")
→ Embedding của bidding chunk: WORSE (thiếu context)
```

**Impact:**
- Retrieval có thể BIAS toward legal docs (vì có thêm context)
- Bidding/report chunks có thể RANK thấp hơn dù relevant

**Solution:**
```python
class SemanticChunker(BaseLegalChunker):
    def _create_chunk(self, section: Dict, parent: str = None) -> UniversalChunk:
        """Always add parent context for consistency"""
        
        text = section["text"]
        
        # Add parent context (like HierarchicalChunker does)
        if parent and self.keep_parent_context:
            text = f"[Context: {parent}]\n\n{text}"
        
        # Add document type context
        if self.document_type:
            doc_type_label = self._get_doc_type_label()
            text = f"[Loại: {doc_type_label}]\n{text}"
        
        return UniversalChunk(
            chunk_id=self._generate_id(section),
            text=text,  # Now has consistent context
            metadata={...},
            ...
        )
```

**Best Practice:**
✅ Add parent context CONSISTENTLY across all strategies
✅ Include document type label if needed
✅ Ensure ALL chunks have similar context depth

---

#### ⚠️ Issue 4: Metadata Schema Inconsistency

**Problem:**
```python
# Legal chunk metadata
{
    "dieu": "15",
    "chuong": "CHƯƠNG II",
    "hierarchy": ["CHƯƠNG II", "Điều 15"],
    "document_type": "decree",
}

# Bidding chunk metadata
{
    "form": "Mẫu số 5",
    "section": "PHẦN I",
    # Missing: hierarchy? → INCONSISTENT!
}
```

**Impact on RAG:**
- ⚠️ Filtering by metadata: Inconsistent fields make filtering harder
- ⚠️ Reranking: Can't compare apples-to-apples
- ⚠️ Source citation: Different metadata formats

**Solution:**
```python
@dataclass
class UniversalChunk:
    """Standardized chunk schema for ALL document types"""
    
    chunk_id: str
    text: str
    metadata: Dict  # MUST follow standard schema
    chunk_type: str  # 'dieu', 'section', 'form', 'question'
    hierarchy: List[str]  # ALWAYS present (even if flat)
    char_count: int
    parent_id: str = None
    
    # Standard metadata fields (REQUIRED for all types)
    document_type: str  # 'law', 'decree', 'bidding', 'report', 'exam'
    document_id: str
    source_file: str
    
    # Type-specific fields (OPTIONAL but standardized)
    legal_metadata: Optional[LegalMetadata] = None  # For legal docs
    bidding_metadata: Optional[BiddingMetadata] = None  # For bidding
    ...
```

**Best Practice:**
✅ Define STANDARD metadata schema for all chunk types
✅ Ensure ALL chunks have required fields
✅ Type-specific fields go in separate nested objects

---

### 3. Embedding Quality Comparison

#### Experiment: Same Content, Different Chunking

**Scenario:** Một đoạn text về "yêu cầu năng lực tài chính" xuất hiện trong:
- Legal doc (Điều 15 of Decree)
- Bidding doc (PHẦN II - Yêu cầu năng lực)

**Test:**
```python
# Legal chunk (HierarchicalChunker)
legal_chunk = """
[Context: CHƯƠNG II - Quy định về năng lực nhà thầu]

Điều 15. Yêu cầu về năng lực tài chính

1. Nhà thầu phải có vốn chủ sở hữu tối thiểu 100 tỷ đồng.
2. Doanh thu trung bình 3 năm gần nhất tối thiểu 200 tỷ đồng/năm.
3. Tỷ lệ nợ trên vốn chủ sở hữu không quá 3 lần.
"""

# Bidding chunk (SemanticChunker)
bidding_chunk = """
[Context: PHẦN II - Yêu cầu về năng lực nhà thầu]

YÊU CẦU VỀ NĂNG LỰC TÀI CHÍNH

Nhà thầu tham gia dự thầu phải đáp ứng các yêu cầu sau:
1. Vốn chủ sở hữu tối thiểu: 100 tỷ đồng
2. Doanh thu trung bình 3 năm gần nhất: 200 tỷ đồng/năm
3. Tỷ lệ nợ/vốn chủ sở hữu: ≤ 3 lần
"""

# Embed both
legal_embedding = embed_model.encode(legal_chunk)
bidding_embedding = embed_model.encode(bidding_chunk)

# Check similarity
similarity = cosine_similarity(legal_embedding, bidding_embedding)
print(f"Similarity: {similarity:.3f}")
# Expected: 0.85-0.95 (VERY HIGH - same semantic content)
```

**Result:**
✅ Embeddings sẽ RẤT GIỐNG NHAU vì:
- Content giống nhau (cùng nội dung về năng lực tài chính)
- Structure tương tự (đều có list 3 items)
- Context có thể khác nhau nhưng KHÔNG ảnh hưởng nhiều

**Conclusion:**
💡 Chunking strategy KHÔNG làm embedding khác biệt đáng kể **NÊU:**
- ✅ Chunk sizes tương đương
- ✅ Semantic boundaries được giữ nguyên
- ✅ Context được thêm nhất quán

---

### 4. Retrieval Impact Analysis

#### Scenario: User Query

**Query:** "Yêu cầu năng lực tài chính của nhà thầu là gì?"

**Vector Search Results:**

```python
# Top 5 retrieved chunks (with different chunking strategies)

1. Score: 0.92 - Legal Chunk (Điều 15 - HierarchicalChunker)
   "Điều 15. Yêu cầu về năng lực tài chính..."
   
2. Score: 0.91 - Bidding Chunk (PHẦN II - SemanticChunker)
   "Yêu cầu về năng lực tài chính: Nhà thầu phải..."
   
3. Score: 0.88 - Report Chunk (Subsection - SemanticChunker)
   "I.2. Đánh giá năng lực tài chính..."
   
4. Score: 0.85 - Legal Chunk (Điều 20 - HierarchicalChunker)
   "Điều 20. Chứng minh năng lực tài chính..."
   
5. Score: 0.83 - Bidding Chunk (Form - SemanticChunker)
   "Mẫu số 3: Bảng chứng minh năng lực tài chính..."
```

**Analysis:**
✅ Scores rất gần nhau (0.83-0.92): Strategy KHÔNG tạo bias lớn
✅ Cả legal và bidding chunks đều rank cao: CÔNG BẰNG
✅ Diversity: User gets information from MULTIPLE document types

**Potential Issues:**
⚠️ Nếu legal chunks LUÔN rank cao hơn bidding:
   - Có thể do legal chunks có thêm context/structure
   - Fix: Ensure SemanticChunker adds equivalent context
   
⚠️ Nếu exam chunks (ngắn) KHÔNG BAO GIỜ rank cao:
   - Có thể do chunk quá ngắn, embedding kém
   - Fix: Merge small questions into groups

---

### 5. Best Practices for Multi-Strategy Embedding

#### ✅ DO: Standardize Chunk Characteristics

```python
# Global configuration for ALL chunkers
CHUNK_CONFIG = {
    "min_chunk_size": 300,      # Min for good embedding
    "max_chunk_size": 1500,     # Max to keep focus
    "target_chunk_size": 800,   # Sweet spot
    "overlap_size": 150,        # For sliding window
    "keep_parent_context": True, # Always add context
}

# Apply to ALL chunkers
hierarchical_chunker = HierarchicalChunker(**CHUNK_CONFIG)
semantic_chunker = SemanticChunker(**CHUNK_CONFIG)
```

#### ✅ DO: Preserve Semantic Boundaries

```python
def chunk_document(self, document: Dict) -> List[UniversalChunk]:
    """Always split at natural boundaries"""
    
    # Priority order:
    # 1. Structural boundaries (Điều, Section, Form)
    # 2. Paragraph boundaries (\n\n)
    # 3. Sentence boundaries (. ! ?)
    # 4. Sliding window with overlap (last resort)
    
    chunks = []
    for section in self._parse_structure(document):
        if len(section.text) <= self.max_chunk_size:
            # Perfect size: keep intact
            chunks.append(self._create_chunk(section))
        else:
            # Too large: split at paragraphs/sentences
            sub_chunks = self._split_semantically(section)
            chunks.extend(sub_chunks)
    
    return chunks
```

#### ✅ DO: Add Consistent Context

```python
def _add_context(self, chunk_text: str, metadata: Dict) -> str:
    """Add consistent context to ALL chunks"""
    
    context_parts = []
    
    # Document type
    doc_type = metadata.get("document_type")
    if doc_type:
        context_parts.append(f"[Loại: {doc_type}]")
    
    # Parent hierarchy
    hierarchy = metadata.get("hierarchy", [])
    if hierarchy and len(hierarchy) > 1:
        parent = hierarchy[-2]  # Second to last
        context_parts.append(f"[Context: {parent}]")
    
    # Combine
    if context_parts:
        context = " ".join(context_parts)
        return f"{context}\n\n{chunk_text}"
    
    return chunk_text
```

#### ✅ DO: Validate Before Embedding

```python
def validate_chunks_for_embedding(chunks: List[UniversalChunk]) -> bool:
    """Ensure chunks are embedding-ready"""
    
    for chunk in chunks:
        # Size check
        if not (300 <= chunk.char_count <= 1500):
            raise ValueError(f"Chunk {chunk.chunk_id} has invalid size: {chunk.char_count}")
        
        # Semantic check
        if chunk.text.strip().endswith(',') or chunk.text.strip().endswith('và'):
            raise ValueError(f"Chunk {chunk.chunk_id} ends mid-sentence")
        
        # Metadata check
        required_fields = ["document_type", "hierarchy", "source_file"]
        for field in required_fields:
            if field not in chunk.metadata:
                raise ValueError(f"Chunk {chunk.chunk_id} missing metadata: {field}")
    
    return True
```

#### ❌ DON'T: Create Tiny Chunks

```python
# BAD: Exam questions too short
chunk = UniversalChunk(
    text="Câu 15: Vốn chủ sở hữu tối thiểu là bao nhiêu?",  # Only 51 chars!
    char_count=51,  # TOO SHORT for good embedding
)

# GOOD: Merge with context
chunk = UniversalChunk(
    text="""
    [Context: Ngân hàng câu hỏi về năng lực nhà thầu]
    
    Câu 15: Vốn chủ sở hữu tối thiểu của nhà thầu tham gia gói thầu xây lắp là bao nhiêu?
    A. 50 tỷ đồng
    B. 100 tỷ đồng
    C. 150 tỷ đồng
    D. 200 tỷ đồng
    
    Đáp án: B (100 tỷ đồng theo Nghị định 63/2014)
    """,
    char_count=320,  # Good size with context
)
```

#### ❌ DON'T: Create Mega Chunks

```python
# BAD: Entire bidding form in one chunk
chunk = UniversalChunk(
    text="Mẫu số 5 - Hồ sơ mời thầu...[5000 chars of forms/tables]...",
    char_count=5000,  # TOO LONG - loses focus
)

# GOOD: Split into logical sections
chunks = [
    UniversalChunk(text="Mẫu số 5A - Thông tin chung...", char_count=800),
    UniversalChunk(text="Mẫu số 5B - Yêu cầu kỹ thuật...", char_count=1200),
    UniversalChunk(text="Mẫu số 5C - Tiêu chí đánh giá...", char_count=900),
]
```

---

## 📊 MEASUREMENT & MONITORING

### Metrics to Track

```python
def analyze_chunking_quality(chunks: List[UniversalChunk]) -> Dict:
    """Measure chunk quality across all strategies"""
    
    stats = {
        "total_chunks": len(chunks),
        "by_strategy": defaultdict(int),
        "by_doc_type": defaultdict(int),
        
        # Size distribution
        "size_stats": {
            "min": min(c.char_count for c in chunks),
            "max": max(c.char_count for c in chunks),
            "mean": np.mean([c.char_count for c in chunks]),
            "median": np.median([c.char_count for c in chunks]),
            "std": np.std([c.char_count for c in chunks]),
        },
        
        # Quality checks
        "too_short": len([c for c in chunks if c.char_count < 300]),
        "too_long": len([c for c in chunks if c.char_count > 1500]),
        "has_context": len([c for c in chunks if "[Context:" in c.text]),
        
        # Semantic coherence (placeholder - would use NLP)
        "ends_mid_sentence": len([c for c in chunks if c.text.strip()[-1] in ',;và']),
    }
    
    return stats
```

**Target Metrics:**
- ✅ Mean chunk size: 700-900 chars
- ✅ Std deviation: < 400 chars (not too variable)
- ✅ Too short (< 300): < 5%
- ✅ Too long (> 1500): < 5%
- ✅ Has context: > 90%
- ✅ Ends mid-sentence: 0%

---

## 🎯 FINAL RECOMMENDATIONS

### ✅ Safe to Use Multiple Strategies IF:

1. **Chunk size consistency**
   - All strategies target 500-1,500 chars
   - Enforce min/max limits globally
   - Monitor size distribution

2. **Semantic boundary preservation**
   - Split at natural boundaries (Điều, Section, Paragraph)
   - Never split mid-sentence
   - Use overlap for edge cases

3. **Context standardization**
   - ALL chunks get parent context
   - Consistent context format: `[Context: ...]`
   - Similar context depth across strategies

4. **Metadata schema uniformity**
   - Standard fields for all chunks
   - Type-specific fields in nested objects
   - Consistent field naming

5. **Quality validation**
   - Validate before embedding
   - Monitor metrics
   - Adjust strategies as needed

### ⚠️ Watch Out For:

- ❌ Size variance > 500 chars between doc types
- ❌ Some strategies produce chunks < 300 chars
- ❌ Inconsistent context addition
- ❌ Metadata schema drift
- ❌ Semantic boundary violations

### 🎯 Implementation Checklist:

```python
# In BaseLegalChunker
class BaseLegalChunker(ABC):
    # Global constraints
    MIN_CHUNK_SIZE = 300
    MAX_CHUNK_SIZE = 1500
    TARGET_CHUNK_SIZE = 800
    
    def validate_chunk(self, chunk: UniversalChunk) -> bool:
        """All subclasses must validate chunks"""
        assert self.MIN_CHUNK_SIZE <= chunk.char_count <= self.MAX_CHUNK_SIZE
        assert chunk.metadata.get("document_type") is not None
        assert len(chunk.hierarchy) > 0
        return True
    
    def add_standard_context(self, text: str, metadata: Dict) -> str:
        """All subclasses use same context format"""
        # ... consistent context logic
```

---

## 💡 CONCLUSION

**Multiple chunking strategies ✅ KHÔNG ảnh hưởng xấu đến embedding** nếu:

1. Chunk sizes đồng nhất (500-1,500 chars)
2. Semantic boundaries được giữ nguyên
3. Context được thêm nhất quán
4. Metadata schema chuẩn hóa

**Lợi ích:**
- ✅ Mỗi document type được chunk tối ưu
- ✅ Semantic quality tốt hơn (không ép format sai)
- ✅ Retrieval đa dạng (từ nhiều nguồn)

**Rủi ro (nếu không kiểm soát):**
- ❌ Bias toward một loại document
- ❌ Embedding quality không đồng nhất
- ❌ Retrieval không công bằng

**Khuyến nghị:**
✅ Implement theo đề xuất 2 strategies (Hierarchical + Semantic)
✅ Enforce global constraints (size, context, metadata)
✅ Monitor metrics continuously
✅ A/B test retrieval quality

---

**Next Steps:**
1. Implement BaseLegalChunker with global constraints
2. Ensure both strategies follow same size/context rules
3. Add validation layer before embedding
4. Monitor chunk quality metrics
5. A/B test retrieval performance
