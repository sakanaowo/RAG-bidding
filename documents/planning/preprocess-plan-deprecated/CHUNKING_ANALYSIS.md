# 📊 CHUNKING STRATEGY ANALYSIS & PROPOSAL

**Date:** December 2024  
**Phase:** Phase 2 Week 4 - Chunking Strategies

---

## 🎯 EXECUTIVE SUMMARY

**Recommendation:** Sử dụng **2 chunking strategies** khác biệt:

1. **HierarchicalChunker** - Cho văn bản có cấu trúc pháp lý rõ ràng
   - Áp dụng: Luật, Nghị định, Thông tư, Quyết định
   - Reuse: ✅ CÓ THỂ tái sử dụng `chunk_strategy.py` (có cải tiến)

2. **SemanticChunker** - Cho văn bản phi cấu trúc/bán cấu trúc
   - Áp dụng: Hồ sơ mời thầu, Mẫu báo cáo, Câu hỏi thi
   - Reuse: ❌ CẦN strategy mới (khác biệt về bản chất)

---

## 📋 DOCUMENT TYPE ANALYSIS

### Group 1: Legal Documents (Structured) 🏛️

**Document Types:** Luật, Nghị định, Thông tư, Quyết định

**Characteristics:**
```
✅ Cấu trúc phân cấp rõ ràng:
   Phần > Chương > Mục > Điều > Khoản > Điểm

✅ Numbering nhất quán:
   - Chương I, II, III... (Roman numerals)
   - Điều 1, 2, 3... (Arabic numbers)
   - Khoản 1, 2, 3... (numbered items)
   - Điểm a), b), c)... (lettered items)

✅ Semantic boundaries tự nhiên:
   - Mỗi Điều = 1 khái niệm pháp lý độc lập
   - Hierarchy cho context (Chương → Điều)

✅ Predictable structure:
   - Pattern matching với regex
   - Hierarchy traversal với tree structure
```

**Example:**
```
CHƯƠNG I
QUY ĐỊNH CHUNG

Điều 1. Phạm vi điều chỉnh
1. Luật này quy định về...
2. Luật này áp dụng đối với...
   a) Các tổ chức...
   b) Các cá nhân...

Điều 2. Đối tượng áp dụng
1. Đơn vị sự nghiệp công lập...
2. Doanh nghiệp...
```

**Chunking Strategy:** `HierarchicalChunker` ✅

**Optimal Chunk Unit:** **Điều** (Article)
- Average size: 500-1,500 chars
- Self-contained legal concept
- Natural semantic boundary
- Easy to reference (Điều X)

**Rationale:**
1. ✅ Mỗi Điều là đơn vị pháp lý độc lập
2. ✅ Kích thước phù hợp (không quá dài/ngắn)
3. ✅ Dễ trích dẫn và tham chiếu
4. ✅ Hierarchy context có sẵn (Chương/Mục)

---

### Group 2: Bidding Documents (Semi-Structured) 📋

**Document Types:** Hồ sơ mời thầu (11 types)

**Characteristics:**
```
⚠️ Cấu trúc không nhất quán:
   - Có PHẦN, CHƯƠNG nhưng không strict
   - Nhiều "Mẫu số X" (form templates)
   - Biểu mẫu (forms/tables)
   - Danh mục hàng hóa, yêu cầu kỹ thuật

⚠️ Mixed content types:
   - Narrative text (hướng dẫn)
   - Tables (specifications)
   - Forms (templates to fill)
   - Lists (requirements)

⚠️ Varying length:
   - Short forms: ~200 chars
   - Long sections: 2,000+ chars

❌ KHÔNG phù hợp với Điều/Khoản pattern:
   - Không có "Điều X" numbering
   - Sections không đồng nhất
```

**Example Structure:**
```
MẪU SỐ 5B
HỒ SƠ MỜI THẦU DỊCH VỤ PHI TƯ VẤN

BIỂU MẪU
├── Mẫu số 01 - Danh mục hàng hóa
├── Mẫu số 02 - Yêu cầu kỹ thuật
├── Mẫu số 03 - Tiêu chí đánh giá
└── Mẫu số 04 - Điều kiện thanh toán

PHẦN I - THÔNG TIN CHUNG
[Narrative text about project, owner, package...]

PHẦN II - YÊU CẦU KỸ THUẬT
[Tables with specifications, requirements...]

PHẦN III - ĐIỀU KHOẢN HỢP ĐỒNG
[Contract terms, legal clauses...]
```

**Chunking Strategy:** `SemanticChunker` ⚠️

**Optimal Approach:**
1. **Form-based chunking** - Mỗi "Mẫu số X" = 1 chunk
2. **Section-based chunking** - PHẦN I, II, III... 
3. **Semantic sliding window** - For long narrative sections
4. **Table preservation** - Keep tables intact as single chunks

**Why NOT HierarchicalChunker:**
- ❌ No strict Điều/Khoản structure
- ❌ Forms/tables break hierarchy assumptions
- ❌ Mixed content needs different handling

---

### Group 3: Report Templates (Semi-Structured) 📊

**Document Types:** Mẫu báo cáo (5 types)

**Characteristics:**
```
⚠️ Template structure:
   - PHẦN I, II, III... (sections)
   - Numbered items (I.1, I.2, II.1...)
   - Tables for data entry
   - Fill-in-the-blank fields

⚠️ Mixed purposes:
   - Evaluation reports (BCĐG)
   - Appraisal reports (BCTĐ)
   - Technical/financial reports

⚠️ Heavy table usage:
   - 20-25 tables per document
   - Tables = main content carriers
   - Narrative text = context/instructions
```

**Example Structure:**
```
PHẦN I - BÁO CÁO ĐÁNH GIÁ

I. THÔNG TIN CƠ BẢN
1. Giới thiệu chung về dự án
   a) Khái quát về dự án
   - Người có thẩm quyền: ___
   - Chủ đầu tư: ___
   
2. Thông tin về gói thầu
   [Table: Package details]

II. ĐÁNH GIÁ HỒ SƠ DỰ THẦU
1. Đánh giá về mặt hành chính
   [Table: Administrative evaluation]
   
2. Đánh giá kỹ thuật
   [Table: Technical evaluation]
```

**Chunking Strategy:** `SemanticChunker` ⚠️

**Optimal Approach:**
1. **Section-based** - PHẦN I, II, III as boundaries
2. **Subsection chunking** - I.1, I.2, II.1, II.2...
3. **Table-aware** - Preserve tables with context
4. **Semantic grouping** - Related items together

**Why NOT HierarchicalChunker:**
- ❌ Not Điều-based structure
- ❌ Tables need special handling
- ❌ Fill-in fields not legal clauses

---

### Group 4: Exam Questions (Unstructured) ❓

**Document Types:** Câu hỏi thi (PDF format)

**Characteristics:**
```
✅ Question-based structure:
   Câu 1: [question text]
   A. [option A]
   B. [option B]
   C. [option C]
   D. [option D]
   Đáp án: [correct answer]

✅ Clear boundaries:
   - Each question = discrete unit
   - Self-contained
   - Easy to identify (Câu X:)

⚠️ PDF extraction challenges:
   - Text may be fragmented
   - Layout-dependent parsing
   - OCR needed for scanned PDFs
```

**Chunking Strategy:** `SemanticChunker` with question detection

**Optimal Approach:**
1. **Question-based chunking** - 1 question = 1 chunk
2. **Pattern matching** - Detect "Câu X:" boundaries
3. **Option extraction** - Keep A/B/C/D together
4. **Answer preservation** - Include correct answer if present

**Why NOT HierarchicalChunker:**
- ❌ No Điều/Khoản structure
- ❌ Questions are flat list, not hierarchy
- ✅ Simple sequential chunking works best

---

## 🔄 REUSABILITY ANALYSIS: `chunk_strategy.py`

### ✅ PROS - What Can Be Reused

**Core Algorithms:**
```python
✅ _parse_structure() - Pattern matching logic
   - Can adapt patterns for bidding/report sections
   - Regex approach is flexible

✅ _split_with_overlap() - Sliding window with overlap
   - Universal technique for long text
   - Reusable for ANY document type

✅ _build_chunk_with_context() - Context preservation
   - Adding parent section context
   - Works for any hierarchy

✅ Chunk size management:
   - max_chunk_size parameter
   - overlap_size parameter
   - Splitting large chunks
```

**Data Structure:**
```python
✅ LawChunk dataclass concept:
   - chunk_id
   - text
   - metadata
   - hierarchy
   - char_count
   
   → Can generalize to UniversalChunk
```

### ❌ CONS - What Needs Change

**Hard-coded Assumptions:**
```python
❌ Điều/Khoản/Điểm patterns:
   self.patterns = {
       "chuong": r"^(CHƯƠNG|Chương)...",
       "dieu": r"^Điều\s+(\d+)...",
       "khoan": r"^(\d+)\.\s+...",
   }
   
   → Bidding docs don't have Điều!
   → Reports use different numbering (I.1, I.2)
   → Exams use "Câu X:" pattern

❌ Hierarchy assumptions:
   - Assumes Chương → Điều → Khoản tree
   - Bidding: Mẫu → Sections → Items (different!)
   - Reports: PHẦN → Subsections (flatter)

❌ Strategy names misleading:
   - "by_dieu" doesn't apply to non-legal docs
   - "hierarchical" assumes legal hierarchy
```

**Missing Features for Non-Legal Docs:**
```python
❌ Table handling:
   - Bidding/reports have 10-25 tables
   - Need table-aware chunking
   - Preserve table context

❌ Form detection:
   - "Mẫu số X" in bidding docs
   - Should chunk by form boundaries

❌ Question detection:
   - "Câu X:" pattern for exams
   - Option extraction (A/B/C/D)

❌ Semantic boundary detection:
   - Topic changes in narrative text
   - Subsection numbering (I.1, I.2)
```

---

## 💡 PROPOSED SOLUTION

### Architecture: 2 Specialized Chunkers

```
src/preprocessing/chunking/
├── __init__.py
├── base_chunker.py          # Base class (NEW)
├── hierarchical_chunker.py  # For legal docs (REFACTOR from chunk_strategy.py)
└── semantic_chunker.py      # For bidding/report/exam (NEW)
```

### 1. BaseLegalChunker (Abstract Base Class)

**Purpose:** Common interface and utilities

```python
from abc import ABC, abstractmethod
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class UniversalChunk:
    """Universal chunk structure for all document types"""
    chunk_id: str
    text: str
    metadata: Dict
    chunk_type: str  # 'dieu', 'section', 'form', 'question'
    hierarchy: List[str]
    char_count: int
    parent_id: str = None

class BaseLegalChunker(ABC):
    """Base class for all chunking strategies"""
    
    def __init__(
        self,
        max_chunk_size: int = 1500,
        overlap_size: int = 200,
        keep_parent_context: bool = True,
    ):
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size
        self.keep_parent_context = keep_parent_context
    
    @abstractmethod
    def chunk_document(self, document: Dict) -> List[UniversalChunk]:
        """Main chunking method - must implement"""
        pass
    
    def _split_with_overlap(self, text: str, max_size: int) -> List[str]:
        """Reusable overlap splitting - common utility"""
        chunks = []
        start = 0
        while start < len(text):
            end = start + max_size
            chunks.append(text[start:end])
            start = end - self.overlap_size
        return chunks
    
    def _add_parent_context(self, text: str, parent: str) -> str:
        """Add parent context to chunk - common utility"""
        if self.keep_parent_context and parent:
            return f"[Context: {parent}]\n\n{text}"
        return text
```

### 2. HierarchicalChunker (Legal Documents)

**Source:** Refactor from `chunk_strategy.py`

**Changes:**
- ✅ Keep: Điều/Khoản/Điểm parsing
- ✅ Keep: Hierarchy tree building
- ✅ Keep: Context preservation
- ✅ Update: Use UniversalChunk instead of LawChunk
- ✅ Update: Integrate with V2 schema (UnifiedLegalChunk)

```python
class HierarchicalChunker(BaseLegalChunker):
    """
    Chunking for structured legal documents.
    
    Applies to: Luật, Nghị định, Thông tư, Quyết định
    
    Strategy: Điều-based chunking with hierarchy preservation
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Legal document patterns
        self.patterns = {
            "phan": r"^(PHẦN|Phần)\s+([IVXLCDM]+)",
            "chuong": r"^(CHƯƠNG|Chương)\s+([IVXLCDM]+)",
            "muc": r"^(MỤC|Mục)\s+([IVXLCDM]+|\d+)",
            "dieu": r"^Điều\s+(\d+[a-z]?)\.\s*(.+?)$",
            "khoan": r"^(\d+)\.\s+(.+)",
            "diem": r"^([a-zđ])\)\s+(.+)",
        }
    
    def chunk_document(self, document: Dict) -> List[UniversalChunk]:
        """Chunk by Điều with hierarchy"""
        # 1. Parse structure tree (Phần > Chương > Mục > Điều)
        structure = self._parse_legal_structure(document["text"])
        
        # 2. Chunk by Điều (optimal level)
        chunks = []
        for dieu in structure:
            if dieu["type"] == "dieu":
                chunk = self._create_dieu_chunk(dieu, document)
                
                # Split large Điều by Khoản
                if len(chunk.text) > self.max_chunk_size:
                    sub_chunks = self._split_by_khoan(dieu, document)
                    chunks.extend(sub_chunks)
                else:
                    chunks.append(chunk)
        
        return chunks
    
    def _parse_legal_structure(self, text: str) -> List[Dict]:
        """Parse Phần > Chương > Mục > Điều > Khoản > Điểm"""
        # DFS tree traversal
        # ... (reuse from chunk_strategy.py)
```

### 3. SemanticChunker (Non-Legal Documents)

**Purpose:** Handle bidding, reports, exams

**New Implementation:**

```python
class SemanticChunker(BaseLegalChunker):
    """
    Chunking for semi-structured and unstructured documents.
    
    Applies to: Hồ sơ mời thầu, Mẫu báo cáo, Câu hỏi thi
    
    Strategy: Semantic boundary detection + sliding window
    """
    
    def __init__(self, document_type: str, **kwargs):
        super().__init__(**kwargs)
        self.document_type = document_type
        
        # Patterns by document type
        self.patterns = self._get_patterns_for_type(document_type)
    
    def _get_patterns_for_type(self, doc_type: str) -> Dict:
        """Get chunking patterns based on document type"""
        
        if doc_type == "bidding":
            return {
                "form": r"^Mẫu\s+số\s+(\d+[A-Z]?)",
                "section": r"^(PHẦN|CHƯƠNG)\s+([IVXLCDM]+|\d+)",
                "table_title": r"^(Bảng|BẢNG|Biểu)\s+(\d+)",
            }
        
        elif doc_type == "report":
            return {
                "section": r"^(PHẦN)\s+([IVXLCDM]+)",
                "subsection": r"^([IVX]+)\.\s+(.+)",
                "item": r"^(\d+)\.\s+(.+)",
                "subitem": r"^([a-z])\)\s+(.+)",
            }
        
        elif doc_type == "exam":
            return {
                "question": r"^(Câu|CÂU)\s+(\d+)[:\.]",
                "option": r"^([A-D])[:\.\)]\s+(.+)",
                "answer": r"(?i)(đáp\s*án|correct)[:\s]+([A-D])",
            }
        
        return {}
    
    def chunk_document(self, document: Dict) -> List[UniversalChunk]:
        """Main chunking dispatcher"""
        
        if self.document_type == "bidding":
            return self._chunk_bidding(document)
        elif self.document_type == "report":
            return self._chunk_report(document)
        elif self.document_type == "exam":
            return self._chunk_exam(document)
        else:
            return self._chunk_generic(document)
    
    def _chunk_bidding(self, document: Dict) -> List[UniversalChunk]:
        """
        Bidding document chunking:
        1. Chunk by Mẫu số X (forms)
        2. Chunk by PHẦN/CHƯƠNG (sections)
        3. Preserve tables as separate chunks
        """
        chunks = []
        text = document["text"]
        
        # 1. Detect form boundaries (Mẫu số X)
        form_sections = self._split_by_pattern(
            text, 
            self.patterns["form"]
        )
        
        # 2. For each form, split by sections
        for form in form_sections:
            if len(form["text"]) <= self.max_chunk_size:
                # Small form: keep intact
                chunks.append(self._create_chunk(
                    form, 
                    chunk_type="form",
                    document=document
                ))
            else:
                # Large form: split by sections
                sections = self._split_by_pattern(
                    form["text"],
                    self.patterns["section"]
                )
                for section in sections:
                    chunks.append(self._create_chunk(
                        section,
                        chunk_type="section",
                        parent=form["title"],
                        document=document
                    ))
        
        return chunks
    
    def _chunk_report(self, document: Dict) -> List[UniversalChunk]:
        """
        Report chunking:
        1. Chunk by PHẦN (major sections)
        2. Chunk by subsections (I.1, I.2, II.1...)
        3. Keep tables with their context
        """
        chunks = []
        text = document["text"]
        
        # Split by PHẦN I, II, III...
        sections = self._split_by_pattern(text, self.patterns["section"])
        
        for section in sections:
            # Split by subsections (I.1, I.2...)
            subsections = self._split_by_pattern(
                section["text"],
                self.patterns["subsection"]
            )
            
            for subsection in subsections:
                if len(subsection["text"]) <= self.max_chunk_size:
                    chunks.append(self._create_chunk(
                        subsection,
                        chunk_type="subsection",
                        parent=section["title"],
                        document=document
                    ))
                else:
                    # Long subsection: sliding window
                    overlapped = self._split_with_overlap(
                        subsection["text"],
                        self.max_chunk_size
                    )
                    for i, chunk_text in enumerate(overlapped):
                        chunks.append(self._create_chunk(
                            {"text": chunk_text, "title": f"{subsection['title']} (part {i+1})"},
                            chunk_type="subsection_part",
                            parent=section["title"],
                            document=document
                        ))
        
        return chunks
    
    def _chunk_exam(self, document: Dict) -> List[UniversalChunk]:
        """
        Exam chunking:
        1. Detect question boundaries (Câu X:)
        2. Extract options (A, B, C, D)
        3. Include answer if present
        4. One question = one chunk
        """
        chunks = []
        text = document["text"]
        
        # Split by questions
        questions = self._extract_questions(text)
        
        for q in questions:
            chunk = UniversalChunk(
                chunk_id=f"{document['id']}_q_{q['number']}",
                text=q["full_text"],
                metadata={
                    **document.get("metadata", {}),
                    "question_number": q["number"],
                    "options": q.get("options", []),
                    "answer": q.get("answer"),
                },
                chunk_type="question",
                hierarchy=[f"Question {q['number']}"],
                char_count=len(q["full_text"]),
            )
            chunks.append(chunk)
        
        return chunks
    
    def _extract_questions(self, text: str) -> List[Dict]:
        """Extract individual questions with options and answers"""
        questions = []
        
        # Find all "Câu X:" boundaries
        question_pattern = self.patterns["question"]
        matches = list(re.finditer(question_pattern, text, re.MULTILINE))
        
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i+1].start() if i+1 < len(matches) else len(text)
            
            question_block = text[start:end]
            
            # Extract components
            q_number = match.group(2)
            options = self._extract_options(question_block)
            answer = self._extract_answer(question_block)
            
            questions.append({
                "number": q_number,
                "full_text": question_block.strip(),
                "options": options,
                "answer": answer,
            })
        
        return questions
    
    def _split_by_pattern(self, text: str, pattern: str) -> List[Dict]:
        """Split text by regex pattern (section markers)"""
        parts = []
        matches = list(re.finditer(pattern, text, re.MULTILINE))
        
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i+1].start() if i+1 < len(matches) else len(text)
            
            parts.append({
                "title": match.group(0),
                "text": text[start:end],
                "number": match.group(2) if len(match.groups()) >= 2 else str(i),
            })
        
        return parts
```

---

## 📊 COMPARISON TABLE

| Feature | HierarchicalChunker | SemanticChunker |
|---------|---------------------|-----------------|
| **Document Types** | Luật, Nghị định, Thông tư, Quyết định | Hồ sơ mời thầu, Mẫu báo cáo, Câu hỏi thi |
| **Structure** | Strict hierarchy (Phần→Chương→Điều) | Semi/unstructured |
| **Chunk Unit** | Điều (Article) | Form, Section, Question |
| **Pattern Matching** | Điều/Khoản/Điểm regex | Flexible patterns per doc type |
| **Hierarchy** | Deep tree (5-6 levels) | Flat/shallow (2-3 levels) |
| **Avg Chunk Size** | 500-1,500 chars (Điều) | Variable (200-2,000 chars) |
| **Table Handling** | Rare, within Điều | Common, preserve separately |
| **Context Strategy** | Parent Chương/Mục | Parent Section/Form |
| **Splitting Strategy** | By Khoản for large Điều | Sliding window with overlap |
| **Reuse from V1** | ✅ 80% (refactor chunk_strategy.py) | ❌ 20% (mostly new logic) |

---

## 🎯 IMPLEMENTATION PLAN

### Step 1: Create Base Class (2 hours)
```python
src/preprocessing/chunking/base_chunker.py
- BaseLegalChunker abstract class
- UniversalChunk dataclass
- Common utilities (_split_with_overlap, _add_parent_context)
```

### Step 2: Refactor HierarchicalChunker (4 hours)
```python
src/preprocessing/chunking/hierarchical_chunker.py
- Refactor from chunk_strategy.py
- Update to use UniversalChunk
- Integrate with V2 UnifiedLegalChunk schema
- Add Phần/Mục support (currently only Chương/Điều)
```

### Step 3: Implement SemanticChunker (8 hours)
```python
src/preprocessing/chunking/semantic_chunker.py
- NEW implementation
- Bidding chunking (form + section based)
- Report chunking (PHẦN + subsection based)
- Exam chunking (question based)
- Table-aware splitting
```

### Step 4: Schema Integration (4 hours)
```python
- Create ChunkFactory helper
- Convert UniversalChunk → UnifiedLegalChunk
- Handle all nested Pydantic models
- Fix validation errors
```

### Step 5: Testing (4 hours)
```python
scripts/test/test_chunking_strategies.py
- Test HierarchicalChunker with legal docs
- Test SemanticChunker with bidding/report/exam
- Compare chunk sizes
- Validate schema integration
```

**Total Estimated:** 22 hours

---

## 🔑 KEY DECISIONS

### ✅ DO Reuse from `chunk_strategy.py`

**What to reuse:**
1. ✅ Overlap splitting logic (`_split_with_overlap`)
2. ✅ Context preservation approach
3. ✅ Hierarchy tree building (DFS traversal)
4. ✅ Điều/Khoản/Điểm regex patterns
5. ✅ Chunk size management

**Rationale:** These are universal chunking concepts, not specific to legal docs.

### ❌ DO NOT Force Hierarchy on Non-Legal Docs

**Why:**
1. ❌ Bidding docs don't have Điều structure
2. ❌ Forms/tables need different treatment
3. ❌ Questions are flat, not hierarchical
4. ❌ Forcing hierarchy creates bad chunks

**Alternative:** Semantic boundary detection + type-specific patterns

### ✅ DO Use Polymorphism

**Strategy:**
```python
# Factory pattern
def create_chunker(document_type: str) -> BaseLegalChunker:
    if document_type in ["law", "decree", "circular", "decision"]:
        return HierarchicalChunker()
    elif document_type == "bidding":
        return SemanticChunker(document_type="bidding")
    elif document_type == "report":
        return SemanticChunker(document_type="report")
    elif document_type == "exam":
        return SemanticChunker(document_type="exam")
```

**Benefits:**
- ✅ Clean interface
- ✅ Easy to extend (new doc types)
- ✅ Testable (mock chunkers)

---

## 📌 CONCLUSION

**Summary:**

1. **HierarchicalChunker** (refactor chunk_strategy.py)
   - Điều-based chunking
   - For: Luật, Nghị định, Thông tư, Quyết định
   - Reuse: 80% of existing code

2. **SemanticChunker** (new implementation)
   - Flexible pattern matching
   - For: Hồ sơ mời thầu, Mẫu báo cáo, Câu hỏi thi
   - Reuse: 20% (only utilities)

**Recommendation:** Proceed with 2-chunker architecture

**Next Actions:**
1. Create BaseLegalChunker abstract class
2. Refactor chunk_strategy.py → HierarchicalChunker
3. Implement SemanticChunker from scratch
4. Fix schema integration (ChunkFactory)
5. Write comprehensive tests

**Expected Outcome:**
- ✅ All 7 document types supported
- ✅ Optimal chunk sizes (500-1,500 chars)
- ✅ Semantic boundaries preserved
- ✅ Schema integration working
- ✅ 16+ tests passing
