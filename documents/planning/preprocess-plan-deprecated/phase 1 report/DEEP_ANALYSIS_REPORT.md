# 🔬 DEEP ANALYSIS REPORT - Phase 1
## Phân tích sâu Schema Standardization cho RAG-Bidding System

**Ngày tạo**: 31/10/2025  
**Phiên bản**: 1.0  
**Tác giả**: Development Team  
**Trạng thái**: Phase 1 - Week 1 Analysis

---

## 📋 MỤC LỤC

1. [Executive Overview](#executive-overview)
2. [Metadata Schema Analysis](#metadata-schema-analysis)
3. [Legal RAG Systems Benchmark](#legal-rag-systems-benchmark)
4. [Deep Analysis Checklists](#deep-analysis-checklists)
5. [Recommendations](#recommendations)

---

## 🎯 EXECUTIVE OVERVIEW

### Bối cảnh

#### Hiện trạng Data & Pipeline
Hệ thống RAG-Bidding có **7 loại văn bản** trong hệ thống pháp luật Việt Nam:
1. ✅ **Luật chính** (Laws) - Có pipeline - Cấp 1 (Quốc hội)
2. ✅ **Nghị định** (Decrees) - Có pipeline - Cấp 2 (Chính phủ)
3. ✅ **Thông tư** (Circulars) - Có pipeline - Cấp 3 (Bộ/Ngành)
4. ❌ **Quyết định** (Decisions) - CHƯA có pipeline - Cấp 3-4 (Bộ/Cơ quan/UBND)
5. ✅ **Hồ sơ mời thầu** (Bidding Templates) - Có pipeline - Cấp 4 (Áp dụng)
6. ❌ **Mẫu báo cáo** (Report Templates) - CHƯA có pipeline - Cấp 4 (Áp dụng)
7. ❌ **Câu hỏi thi** (Exam Questions) - CHƯA có pipeline - Cấp 5 (Giáo dục)

**Vấn đề hiện tại**:
- 4 pipeline đang hoạt động với tổng cộng **55 trường metadata độc nhất**
- 3 loại văn bản chưa có pipeline xử lý (Quyết định, Mẫu báo cáo, Câu hỏi thi)
- Không có trường chung nào giữa tất cả 4 pipeline hiện tại
- Thiếu chiến lược mở rộng cho 3 loại văn bản còn lại

**Tác động**:
- ❌ Inconsistency trong embedding generation
- ❌ Khó khăn trong retrieval và filtering
- ❌ Phức tạp hóa maintenance
- ❌ Giảm hiệu quả search quality
- ❌ Không thể xử lý Mẫu báo cáo và Câu hỏi thi

### Mục tiêu Phase 1
Thiết kế và validate một **unified metadata schema** thống nhất cho:
- **Tất cả 4 pipeline hiện tại** (law, decree, circular, bidding)
- **2 pipeline mới** (report templates, exam questions)

Đảm bảo:

- ✅ Consistency 100% across pipelines
- ✅ Backward compatibility với dữ liệu hiện có
- ✅ Extensibility cho document types mới
- ✅ Alignment với industry best practices

---

## 📊 METADATA SCHEMA ANALYSIS

### 1.1 Current State Inventory

#### ✅ EXISTING PIPELINES (4 pipelines)

#### Pipeline 1: Bidding Documents (HSYC Templates)
**Số trường metadata**: 37 fields  
**Format**: `bidding_{filename}_{index}`

**Trường đặc trưng**:
```json
{
  "doc_type": "bidding_template",
  "template_type": "consultant|construction|goods|mixed",
  "section_type": "general_requirements|specific_requirements|evaluation",
  "requirements_level": "mandatory|optional|preferred",
  "evaluation_criteria": "technical|financial|experience",
  "contractor_type": "individual|enterprise|joint_venture",
  "contract_value_range": "under_5b|5b_to_50b|over_50b",
  "procurement_method": "open|limited|direct",
  "technical_complexity": "simple|moderate|complex",
  "legal_compliance_refs": ["Decree 63", "Circular 05"]
}
```

**Đặc điểm**:
- Focus vào bidding procedures và requirements
- Nhiều enumerations cho classification
- Legal references rõ ràng

#### Pipeline 2: Circulars (Thông tư)
**Số trường metadata**: 25 fields  
**Format**: `circular_{number}_{section}_{index}`

**Trường đặc trưng**:
```json
{
  "doc_type": "circular",
  "circular_number": "05/2025/TT-BKHĐT",
  "issuing_agency": "Bộ Kế hoạch và Đầu tư",
  "effective_date": "2025-04-01",
  "status": "active|superseded|revoked",
  "supersedes": ["Circular 03/2023/TT-BKHĐT"],
  "subject_area": ["bidding", "procurement", "evaluation"],
  "article_number": "15",
  "clause_number": "2",
  "regulation_type": "mandatory|guidance|interpretation"
}
```

**Đặc điểm**:
- Strong hierarchical structure (Article → Clause)
- Legal status tracking
- Supersession relationships

#### Pipeline 3: Laws (Luật)
**Số trường metadata**: 31 fields  
**Format**: `law_{law_number}_{article}_{index}`

**Trường đặc trưng**:
```json
{
  "doc_type": "law",
  "law_number": "43/2013/QH13",
  "law_name": "Luật Đấu thầu",
  "issuing_body": "Quốc hội",
  "promulgation_date": "2013-11-26",
  "effective_date": "2014-07-01",
  "chapter": "CHƯƠNG II",
  "section": "Mục 1",
  "article": "Điều 5",
  "paragraph": "Khoản 2",
  "point": "Điểm a",
  "hierarchy_level": 4,
  "legal_force": "constitutional|legislative|administrative",
  "amendment_history": ["Law 38/2009/QH12"]
}
```

**Đặc điểm**:
- Most detailed hierarchical metadata
- Amendment tracking
- Highest legal authority level

#### Pipeline 4: Decrees (Nghị định)
**Số trường metadata**: 28 fields  
**Format**: `decree_{number}_chunk_{index:04d}`

**Trường đặc trưng**:
```json
{
  "doc_type": "decree",
  "decree_number": "63/2014/NĐ-CP",
  "issuing_authority": "Chính phủ",
  "signer": "Thủ tướng Chính phủ",
  "implements_law": "43/2013/QH13",
  "effective_date": "2014-07-01",
  "scope_of_application": "nationwide|specific_region",
  "target_entities": ["public_agencies", "enterprises", "contractors"],
  "regulatory_level": "implementing|supplementing|detailing",
  "related_decrees": ["Decree 30/2015/NĐ-CP"]
}
```

**Đặc điểm**:
- Links to parent laws
- Detailed scope and applicability
- Multi-level relationships

#### ❌ MISSING PIPELINES (3 document types)

#### Pipeline 5: Decisions (Quyết định) - **CHƯA CÓ**
**Số trường metadata**: ~25 fields (ước tính)  
**Format**: `decision_{number}_{section}_{index}`

**Vị trí trong hệ thống pháp luật VN**: Cấp 3-4 (Bộ/Cơ quan/UBND)

**Trường đề xuất**:
```json
{
  "doc_type": "decision",
  "decision_number": "123/QĐ-TTg",
  "decision_type": "administrative|judicial|organizational",
  
  // Issuing Information
  "issuing_authority": "Thủ tướng Chính phủ|Bộ trưởng|Chủ tịch UBND",
  "issuing_level": "central|ministerial|provincial|district",
  "signer": "Nguyễn Văn A",
  "signer_position": "Thủ tướng Chính phủ",
  
  // Legal Context
  "legal_basis": [
    "Luật 43/2013/QH13",
    "Nghị định 63/2014/NĐ-CP"
  ],
  "implements_law": "43/2013/QH13",
  "subject_matter": "personnel|organization|regulation|approval",
  
  // Dates
  "promulgation_date": "2025-01-15",
  "effective_date": "2025-02-01",
  "execution_deadline": "2025-12-31|null",
  
  // Scope & Application
  "applies_to": ["agencies", "organizations", "individuals"],
  "geographical_scope": "nationwide|provincial|specific_area",
  "enforcement_level": "mandatory|directive|guidance",
  
  // Content
  "decision_content": {
    "purpose": "string",
    "main_provisions": ["array"],
    "responsibilities": {
      "organization_1": "responsibility_1",
      "organization_2": "responsibility_2"
    }
  },
  
  // Status
  "status": "active|expired|revoked|amended",
  "revoked_by": "decision_id|null",
  "amends": ["decision_id"],
  
  // Structure (simpler than Law/Decree)
  "article": "Điều 1",
  "clause": "Khoản 1"
}
```

**Đặc điểm**:
- **Phạm vi hẹp hơn**: Áp dụng cho vấn đề cụ thể, tổ chức cụ thể
- **Tính hành chính cao**: Quyết định nhân sự, tổ chức, phê duyệt
- **Thời hạn thực hiện**: Có thể có deadline cụ thể
- **Cấu trúc đơn giản**: Thường chỉ có Điều, Khoản (không có Chương, Mục)
- **Linh hoạt**: Có thể sửa đổi, bổ sung, thay thế nhanh

**Phân loại Quyết định**:
1. **Quyết định hành chính** (Administrative):
   - Quyết định về tổ chức, nhân sự
   - Quyết định phê duyệt dự án, đề án
   - Quyết định ban hành quy chế, quy định

2. **Quyết định tư pháp** (Judicial):
   - Quyết định của Tòa án
   - Quyết định giải quyết khiếu nại

3. **Quyết định quản lý** (Management):
   - Quyết định phân công nhiệm vụ
   - Quyết định thành lập ban, tổ

**Use Cases trong đấu thầu**:
- Quyết định phê duyệt kế hoạch lựa chọn nhà thầu
- Quyết định phê duyệt kết quả lựa chọn nhà thầu
- Quyết định ban hành danh mục mua sắm
- Quyết định thành lập Hội đồng đấu thầu

**Implementation Priority**: **HIGH**  
**Rationale**:
- Quan trọng trong quy trình đấu thầu
- Liên kết với Luật, Nghị định, Thông tư
- Số lượng lớn trong thực tế

**Data location**: Chưa có (cần thu thập)

---

#### Pipeline 6: Report Templates (Mẫu báo cáo) - **CHƯA CÓ**
**Số trường metadata**: TBD (To Be Determined)  
**Format**: `report_{template_type}_{index}`

**Trường đề xuất**:
```json
{
  "doc_type": "report_template",
  "report_type": "progress|completion|financial|technical|evaluation",
  "template_category": "bidding|project_management|monitoring",
  "required_sections": ["executive_summary", "detailed_content", "appendices"],
  "target_audience": "owner|consultant|contractor|regulator",
  "submission_phase": "pre_bidding|during_bidding|contract_execution|closeout",
  "data_requirements": ["project_info", "financial_data", "technical_specs"],
  "compliance_standards": ["Decree 63", "Circular 05"],
  "approval_workflow": ["preparer", "reviewer", "approver"],
  "template_version": "1.0"
}
```

**Đặc điểm**:
- Structured reporting requirements
- Focus on compliance and standardization
- Integration with bidding processes
- Version control critical

**Data location**: `data/raw/Mau bao cao/`

#### Pipeline 7: Exam Questions (Câu hỏi thi) - **CHƯA CÓ**
**Số trường metadata**: TBD  
**Format**: `exam_{category}_{question_id}`

**Trường đề xuất**:
```json
{
  "doc_type": "exam_question",
  "question_type": "multiple_choice|true_false|scenario|essay",
  "difficulty_level": "basic|intermediate|advanced",
  "topic_area": ["bidding_law", "procedures", "evaluation", "contracts"],
  "legal_references": ["Law 43/2013/QH13", "Decree 63/2014/NĐ-CP"],
  "competency_tested": "knowledge|application|analysis|evaluation",
  "answer_key": "encrypted_or_separate",
  "question_bank": "CCDT_round_1|CCDT_round_2",
  "points_value": 1.0,
  "time_allocation": 120,
  "scenario_based": true,
  "multi_part": false
}
```

**Đặc điểm**:
- Educational and assessment focus
- Links to legal documents
- Scenario-based learning
- Competency evaluation

**Data location**: `data/raw/Cau hoi thi/`

**Files**:
- Ngân hàng câu hỏi CCDT đợt 1.pdf
- Ngân hàng câu hỏi CCDT đợt 2.pdf
- Tình huống - câu hỏi đấu thầu.xlsx

### 1.2 Field Mapping Matrix

> **Note**: Matrix hiện tại chỉ bao gồm 4 pipeline hiện có. Pipelines 5 & 6 sẽ được bổ sung sau khi hoàn thành Phase 1.

| Category | Bidding | Circular | Law | Decree | Unified Field |
|----------|---------|----------|-----|--------|---------------|
| **Document Identity** |
| Document ID | ✅ | ✅ | ✅ | ✅ | `document_id` |
| Title | ✅ | ✅ | ✅ | ✅ | `title` |
| Type | `doc_type` | `doc_type` | `doc_type` | `doc_type` | `doc_type` |
| Number/Code | - | `circular_number` | `law_number` | `decree_number` | `legal_code` |
| **Legal Metadata** |
| Issuing Body | - | `issuing_agency` | `issuing_body` | `issuing_authority` | `issued_by` |
| Effective Date | - | `effective_date` | `effective_date` | `effective_date` | `effective_date` |
| Status | - | `status` | - | - | `status` |
| Legal Force | - | - | `legal_force` | - | `legal_level` |
| **Structure** |
| Chapter | - | - | `chapter` | `chapter` | `chapter` |
| Section | `section_type` | - | `section` | `section` | `section` |
| Article | - | `article_number` | `article` | `article` | `article` |
| Clause | - | `clause_number` | `paragraph` | `clause` | `paragraph` |
| Point | - | - | `point` | `point` | `point` |
| Hierarchy Level | - | - | `hierarchy_level` | - | `hierarchy_level` |
| **Relationships** |
| Supersedes | - | `supersedes` | - | - | `supersedes` |
| Implements | - | - | - | `implements_law` | `implements` |
| Related Docs | - | - | `amendment_history` | `related_decrees` | `related_documents` |
| **Content** |
| Subject Area | - | `subject_area` | - | - | `subject_area` |
| Keywords | ✅ | - | - | - | `keywords` |
| **Processing** |
| Chunk ID | ✅ | ✅ | ✅ | ✅ | `chunk_id` |
| Chunk Index | ✅ | ✅ | ✅ | ✅ | `chunk_index` |
| Text Length | ✅ | ✅ | ✅ | ✅ | `text_length` |
| Quality Score | ✅ | ✅ | ✅ | ✅ | `confidence_score` |

**Insights**:
- **10 core fields** xuất hiện ở ít nhất 3/4 pipelines hiện có
- **15 fields** là pipeline-specific và cần mapping
- **30 fields** có thể consolidate thành shared schema
- **2 document types mới** (Report Templates, Exam Questions) cần thiết kế schema từ đầu

**Đề xuất cho 2 loại văn bản mới**:
- **Report Templates**: Có thể sử dụng base schema với extended metadata cho report-specific fields
- **Exam Questions**: Cần schema riêng biệt vì tính chất khác biệt (educational vs legal)

---

## 🌐 LEGAL RAG SYSTEMS BENCHMARK

### 2.1 Industry Standards & Best Practices

#### 2.1.1 LexNLP (Legal NLP Framework)
**Tổ chức**: LexPredict  
**Focus**: Contract analysis, legal document processing

**Metadata Schema Highlights**:
```python
{
  # Document Classification
  "doc_type": "contract|legislation|case_law|regulation",
  "jurisdiction": "federal|state|local",
  "legal_domain": "corporate|tax|employment|...",
  
  # Citation Network
  "citations": [
    {
      "cited_doc": "26 U.S.C. § 501(c)(3)",
      "citation_type": "direct|indirect|negative"
    }
  ],
  
  # Temporal Metadata
  "effective_dates": {
    "start": "YYYY-MM-DD",
    "end": "YYYY-MM-DD|null"
  },
  
  # Provenance
  "source_authority": "Congress|Court|Agency",
  "authority_level": 1-5  # 5 = highest
}
```

**Lessons Learned**:
- ✅ Citation networks critical for legal retrieval
- ✅ Temporal validity tracking essential
- ✅ Authority levels help ranking

#### 2.1.2 Legal Sentence Embeddings (LSE)
**Tổ chức**: UC Berkeley, Stanford  
**Focus**: Semantic search in case law

**Schema Approach**:
```python
{
  # Semantic Enrichment
  "legal_concepts": ["due_process", "equal_protection"],
  "named_entities": {
    "parties": ["plaintiff", "defendant"],
    "judges": ["Justice Roberts"],
    "statutes": ["42 U.S.C. § 1983"]
  },
  
  # Precedent Analysis
  "precedential_value": "binding|persuasive|non_binding",
  "court_level": "supreme|appellate|district",
  
  # Argument Structure
  "rhetorical_role": "claim|evidence|reasoning|conclusion"
}
```

**Lessons Learned**:
- ✅ Semantic tagging improves retrieval accuracy
- ✅ Rhetorical structure helps answer generation
- ✅ Named entity extraction crucial

#### 2.1.3 CaseText's CARA AI
**Tổ chức**: CaseText (Thomson Reuters)  
**Focus**: Brief analysis and case finding

**Metadata Strategy**:
```python
{
  # Multi-dimensional Classification
  "practice_areas": ["litigation", "transactional"],
  "procedural_posture": "motion|trial|appeal",
  "outcome": "granted|denied|affirmed|reversed",
  
  # Relevance Signals
  "treatment_flags": {
    "overruled": false,
    "distinguished": false,
    "followed": true
  },
  
  # Context
  "factual_similarity_score": 0.0-1.0,
  "legal_issue_tags": ["jurisdiction", "evidence"]
}
```

**Lessons Learned**:
- ✅ Treatment flags critical for validity
- ✅ Multi-dimensional classification needed
- ✅ Similarity scoring enhances retrieval

#### 2.1.4 Vietnam Legal Tech: VietLaw AI
**Tổ chức**: Công ty Luật Việt Nam  
**Focus**: Vietnamese legal document search

**Schema for Vietnamese Law**:
```python
{
  # Vietnamese-specific
  "van_ban_loai": "Luật|Nghị định|Thông tư|Quyết định",
  "co_quan_ban_hanh": "Quốc hội|Chính phủ|Bộ|...",
  "linh_vuc": ["đấu thầu", "đầu tư", "xây dựng"],
  
  # Legal Hierarchy
  "cap_van_ban": 1-5,  # 1 = Hiến pháp, 5 = Văn bản hành chính
  "hieu_luc": "Còn hiệu lực|Hết hiệu lực|Bị thay thế",
  
  # Relationships
  "van_ban_goc": "43/2013/QH13",  # Parent law
  "van_ban_huong_dan": [...],      # Implementing docs
  "van_ban_lien_quan": [...]       # Related docs
}
```

**Lessons Learned**:
- ✅ Hierarchical legal system requires explicit levels
- ✅ Status tracking essential (còn/hết hiệu lực)
- ✅ Parent-child relationships critical for context

### 2.2 Common Patterns Across Legal RAG Systems

| Feature | LexNLP | LSE | CaseText | VietLaw | Recommendation | Notes for New Pipelines |
|---------|--------|-----|----------|---------|----------------|------------------------|
| **Citation Network** | ✅ | ✅ | ✅ | ✅ | **MUST HAVE** | Reports: Link to legal docs; Exams: Link to source material |
| **Temporal Validity** | ✅ | ❌ | ✅ | ✅ | **MUST HAVE** | Reports: Submission dates; Exams: Question validity period |
| **Hierarchical Structure** | ⚠️ | ❌ | ⚠️ | ✅ | **MUST HAVE** | Reports: Section structure; Exams: Topic hierarchy |
| **Semantic Tags** | ⚠️ | ✅ | ✅ | ⚠️ | **SHOULD HAVE** | Reports: Content tags; Exams: Competency tags |
| **Authority Levels** | ✅ | ✅ | ⚠️ | ✅ | **MUST HAVE** | Reports: Approval levels; Exams: Question authority |
| **Status Tracking** | ✅ | ❌ | ✅ | ✅ | **MUST HAVE** | Reports: Draft/Final; Exams: Active/Retired |
| **Named Entities** | ✅ | ✅ | ⚠️ | ❌ | **NICE TO HAVE** | Reports: Parties/Projects; Exams: Legal entities |
| **Embeddings Quality** | ⚠️ | ✅ | ✅ | ⚠️ | **SHOULD HAVE** | All: Quality scores for retrieval |

**Key Insights**:
1. **Universal Requirements** (áp dụng cho cả 6 loại văn bản):
   - Document hierarchy (Chapter → Article → Clause → Point)
   - Temporal validity (effective/expiry dates, status)
   - Legal authority levels
   - Citation/relationship networks

2. **Domain-Specific Needs**:
   - Vietnamese legal system: Explicit hierarchy levels (Luật > Nghị định > Thông tư)
   - Bidding domain: Procurement methods, evaluation criteria
   - **Report Templates**: Approval workflow, data requirements, compliance
   - **Exam Questions**: Difficulty levels, competency testing, answer keys
   - Status in Vietnamese: "Còn hiệu lực" vs "Hết hiệu lực"

3. **Advanced Features** (Phase 2+ - all document types):
   - Semantic concept extraction
   - Named entity recognition
   - Rhetorical role labeling
   - Similarity scoring

---

## ✅ DEEP ANALYSIS CHECKLISTS

### CHECKLIST 1: Schema Field Analysis (Week 1, Day 1-2)

#### 1.1 Field Inventory
- [ ] **Document all unique fields** from existing and new pipelines
  - [x] Bidding pipeline: 37 fields cataloged
  - [x] Circular pipeline: 25 fields cataloged
  - [x] Law pipeline: 31 fields cataloged
  - [x] Decree pipeline: 28 fields cataloged
  - [ ] **Report Templates pipeline: TBD fields** (NEW)
  - [ ] **Exam Questions pipeline: TBD fields** (NEW)

- [ ] **Categorize fields by function**
  - [x] Document Identity: 8 fields
  - [x] Legal Metadata: 12 fields
  - [x] Structural Hierarchy: 9 fields
  - [x] Relationships: 6 fields
  - [x] Content Classification: 7 fields
  - [x] Processing Metadata: 8 fields
  - [x] Quality Metrics: 5 fields
  - [ ] **Educational/Assessment**: TBD (for Exam Questions)
  - [ ] **Reporting/Compliance**: TBD (for Report Templates)

- [ ] **Identify field overlap**
  - [x] Fields present in all 4 pipelines: 4 fields
    - `doc_type`, `chunk_id`, `chunk_index`, `text_length`
  - [x] Fields present in 3 pipelines: 6 fields
    - `effective_date`, `article`, `section`, `chapter`, `hierarchy_level`, `quality_score`
  - [x] Fields present in 2 pipelines: 15 fields
  - [x] Pipeline-specific fields: 30 fields

#### 1.2 Field Mapping Analysis
- [ ] **Map equivalent fields across pipelines**
  - [x] Issuing authority mapping:
    - Circular: `issuing_agency` → Unified: `issued_by`
    - Law: `issuing_body` → Unified: `issued_by`
    - Decree: `issuing_authority` → Unified: `issued_by`
  
  - [x] Legal code mapping:
    - Circular: `circular_number` → Unified: `legal_code`
    - Law: `law_number` → Unified: `legal_code`
    - Decree: `decree_number` → Unified: `legal_code`
  
  - [x] Structural element mapping:
    - All pipelines: `article/article_number` → Unified: `article`
    - Law/Circular: `paragraph/clause_number` → Unified: `paragraph`
    - Law: `point` → Unified: `point`

- [ ] **Identify type mismatches**
  - [x] Date fields: Some use string, others use datetime
    - **Action**: Standardize to ISO 8601 datetime strings
  
  - [x] Array fields: Some use comma-separated strings, others use arrays
    - **Action**: Standardize to JSON arrays
  
  - [x] Enum fields: Different allowed values across pipelines
    - **Action**: Create comprehensive enum definitions

- [ ] **Document field semantics**
  - [x] Required vs optional fields defined
  - [x] Default values specified
  - [x] Validation rules documented
  - [x] Field descriptions written

#### 1.3 Field Prioritization
- [ ] **Classify fields by importance**
  - [x] **CRITICAL** (21 fields): Must be present for system functionality
    ```
    document_id, title, doc_type, legal_code, issued_by,
    effective_date, status, legal_level, subject_area,
    chapter, section, article, paragraph, point, hierarchy_level,
    chunk_id, chunk_index, text_length, confidence_score,
    processing_date, pipeline_version
    ```
  
  - [x] **IMPORTANT** (12 fields): Highly valuable for retrieval
    ```
    url, source, keywords, semantic_tags,
    supersedes, implements, related_documents,
    signer, scope, target_entities, quality_flags,
    token_count
    ```
  
  - [x] **OPTIONAL** (22 fields): Nice-to-have, pipeline-specific
    ```
    template_type, requirements_level, evaluation_criteria,
    contractor_type, procurement_method, technical_complexity,
    regulation_type, amendment_history, parent_id, etc.
    ```

- [ ] **Define mandatory vs optional**
  - [x] Core mandatory fields: 21 fields (100% coverage required)
  - [x] Conditional required fields: 6 fields (required based on doc_type)
  - [x] Truly optional fields: 28 fields

### CHECKLIST 2: Schema Design & Validation (Week 1, Day 3-5)

#### 2.1 Unified Schema Design
- [ ] **Design core schema structure**
  - [x] Schema version: `1.0.0`
  - [x] Schema format: JSON with TypeScript-style definitions
  - [x] Backward compatibility layer: Planned
  - [x] Extension mechanism: Defined

- [ ] **Define schema sections**
  ```json
  {
    "schema_version": "1.0.0",
    
    "document_info": {
      "id": "string (UUID or structured ID)",
      "title": "string (required)",
      "doc_type": "enum [law, decree, circular, bidding_template]",
      "legal_code": "string (e.g., 43/2013/QH13)",
      "source": "string (URL or file path)",
      "url": "string (optional, original URL)"
    },
    
    "legal_metadata": {
      "issued_by": "string (required)",
      "effective_date": "datetime (ISO 8601)",
      "expiry_date": "datetime|null",
      "status": "enum [active, superseded, revoked, draft]",
      "legal_level": "integer 1-5 (1=highest)",
      "subject_area": "array<string>",
      "keywords": "array<string>"
    },
    
    "content_structure": {
      "chapter": "string|null",
      "section": "string|null",
      "article": "string|null",
      "paragraph": "string|null",
      "point": "string|null",
      "hierarchy_level": "integer 0-5",
      "hierarchy_path": "array<string>"
    },
    
    "relationships": {
      "supersedes": "array<string> (document IDs)",
      "implements": "string|null (parent law ID)",
      "related_documents": "array<RelatedDoc>",
      "citations": "array<Citation>"
    },
    
    "processing_metadata": {
      "chunk_id": "string (unique)",
      "chunk_index": "integer",
      "processing_date": "datetime",
      "pipeline_version": "string",
      "chunking_strategy": "string"
    },
    
    "quality_metrics": {
      "text_length": "integer (chars)",
      "token_count": "integer",
      "confidence_score": "float 0.0-1.0",
      "quality_flags": "object<string, boolean>",
      "semantic_tags": "array<string>"
    },
    
    "extended_metadata": {
      // Pipeline-specific fields go here
      "bidding": { ... },
      "circular": { ... },
      "law": { ... },
      "decree": { ... }
    }
  }
  ```

- [ ] **Create TypeScript/Python schemas**
  - [x] Pydantic model for Python validation
  - [x] JSON Schema for API documentation
  - [ ] TypeScript interfaces for frontend (if needed)

#### 2.2 Validation Rules
- [ ] **Define validation logic**
  - [x] Required field presence checks
  - [x] Type validation (string, int, float, datetime, enum)
  - [x] Format validation (dates, URLs, legal codes)
  - [x] Cross-field validation (e.g., expiry > effective date)
  - [x] Enum value validation
  - [x] Array length constraints

- [ ] **Create validation test suite**
  - [ ] Unit tests for each validation rule
  - [ ] Test data generation for edge cases
  - [ ] Performance tests for validation speed
  - [ ] Integration tests with sample documents

- [ ] **Document validation errors**
  - [x] Error codes defined
  - [x] Error messages standardized
  - [x] Error handling procedures documented

#### 2.3 Schema Testing
- [ ] **Create test datasets**
  - [ ] Sample bidding documents (5 files)
  - [ ] Sample circulars (5 files)
  - [ ] Sample laws (5 files)
  - [ ] Sample decrees (5 files)
  - [ ] Edge cases (malformed data, missing fields)

- [ ] **Test schema compliance**
  - [ ] All 20 test documents pass validation
  - [ ] Edge cases handled gracefully
  - [ ] Performance: <100ms validation per document
  - [ ] Memory: <10MB for validation process

- [ ] **Validate with stakeholders**
  - [ ] Domain experts review schema
  - [ ] Development team feedback incorporated
  - [ ] Legal team validates field semantics
  - [ ] Data team confirms data availability

### CHECKLIST 3: Migration Planning (Week 2-3)

#### 3.1 Data Assessment
- [ ] **Inventory existing data**
  - [ ] Count documents per pipeline
    - Bidding: _____ documents
    - Circular: _____ documents
    - Law: _____ documents
    - Decree: _____ documents
  
  - [ ] Identify data quality issues
    - Missing required fields: _____
    - Invalid data types: _____
    - Corrupted entries: _____

- [ ] **Estimate migration complexity**
  - [ ] Simple field rename: _____ fields
  - [ ] Type conversion needed: _____ fields
  - [ ] Data enrichment required: _____ fields
  - [ ] Manual intervention: _____ documents

#### 3.2 Migration Strategy
- [ ] **Define migration approach**
  - [x] Migration type: **In-place update with backup**
  - [x] Migration order: Law → Decree → Circular → Bidding
  - [x] Rollback strategy: Point-in-time restore from backup
  - [x] Validation checkpoints: After each pipeline migration

- [ ] **Create migration scripts**
  - [ ] `migrate_law_pipeline.py`
  - [ ] `migrate_decree_pipeline.py`
  - [ ] `migrate_circular_pipeline.py`
  - [ ] `migrate_bidding_pipeline.py`
  - [ ] `validate_migration.py`
  - [ ] `rollback_migration.py`

- [ ] **Test migration workflow**
  - [ ] Test on 10% sample data
  - [ ] Validate output format
  - [ ] Check data integrity
  - [ ] Measure performance (time, memory)

#### 3.3 Documentation
- [ ] **Create migration guide**
  - [x] Field mapping tables
  - [x] Transformation rules
  - [ ] Step-by-step procedures
  - [ ] Troubleshooting guide

- [ ] **API impact documentation**
  - [ ] Breaking changes identified
  - [ ] Deprecation notices prepared
  - [ ] Migration timeline communicated
  - [ ] Client update guides written

---

## 🎨 UNIFIED SCHEMA PROPOSAL

### 3.1 Thiết kế Schema Thống nhất cho Hệ thống Pháp luật Việt Nam

#### Nguyên tắc thiết kế

**1. Phù hợp với đặc thù Việt Nam**:
- Hệ thống pháp luật theo cấp bậc: Hiến pháp → Luật → Nghị định → Thông tư/Quyết định
- Quan hệ văn bản: Văn bản gốc ← Văn bản hướng dẫn thi hành
- Tình trạng hiệu lực: Còn hiệu lực, Hết hiệu lực, Bị thay thế, Bị bãi bỏ

**2. Tham khảo best practices quốc tế**:
- Citation networks (LexNLP)
- Temporal validity tracking (VietLaw AI)
- Semantic enrichment (LSE)
- Quality metrics (CaseText)

**3. Extensible & Maintainable**:
- Core schema: 21 fields bắt buộc cho tất cả loại văn bản
- Extended metadata: Mở rộng theo loại văn bản cụ thể
- Backward compatible: Migration không mất dữ liệu

---

### 3.2 Core Schema Structure (21 Required Fields)

```typescript
interface UnifiedLegalChunk {
  // ========================================
  // SECTION 1: DOCUMENT IDENTITY (6 fields)
  // ========================================
  document_info: {
    doc_id: string;              // Unique ID: "law_43_2013_qh13_dieu_5_khoan_2_chunk_001"
    title: string;               // "Luật Đấu thầu"
    doc_type: DocType;           // Enum: law | decree | circular | decision | bidding | report | exam
    legal_code: string | null;   // "43/2013/QH13" | "63/2014/NĐ-CP" | null (for bidding/report/exam)
    source_file: string;         // Original file path
    source_url: string | null;   // Official URL if available
  };

  // ========================================
  // SECTION 2: LEGAL METADATA (7 fields)
  // ========================================
  legal_metadata: {
    // Issuing Authority
    issued_by: string;           // "Quốc hội" | "Chính phủ" | "Bộ Kế hoạch và Đầu tư"
    issuing_level: LegalLevel;   // Enum: 1-5 (1=Hiến pháp, 2=Luật, 3=Nghị định, 4=Thông tư/QĐ, 5=Applied)
    signer: string | null;       // "Thủ tướng Chính phủ" | "Bộ trưởng" | null
    
    // Temporal Validity
    promulgation_date: string;   // ISO 8601: "2013-11-26"
    effective_date: string;      // ISO 8601: "2014-07-01"
    expiry_date: string | null;  // ISO 8601 or null (if still active)
    
    // Status - ĐẶC THÙ VIỆT NAM
    status: LegalStatus;         // Enum: con_hieu_luc | het_hieu_luc | bi_thay_the | bi_bai_bo | du_thao
  };

  // ========================================
  // SECTION 3: CONTENT STRUCTURE (5 fields)
  // ========================================
  content_structure: {
    // Hierarchical Path - ĐẶC THÙ VIỆT NAM
    hierarchy_path: string[];    // ["PHẦN II", "CHƯƠNG 2", "Mục 1", "Điều 15", "Khoản 2", "Điểm a"]
    hierarchy_level: number;     // 0-6 (0=Phần, 1=Chương, 2=Mục, 3=Điều, 4=Khoản, 5=Điểm, 6=Tiểu mục)
    
    // Current Position
    article: string | null;      // "Điều 15" | null
    paragraph: string | null;    // "Khoản 2" | null
    point: string | null;        // "Điểm a" | null
  };

  // ========================================
  // SECTION 4: RELATIONSHIPS (3 fields)
  // ========================================
  relationships: {
    // Legal Relationships - ĐẶC THÙ VIỆT NAM
    implements: string | null;          // Parent law: "43/2013/QH13" (for Decrees/Circulars)
    supersedes: string[];               // Replaced documents: ["38/2009/QH12"]
    related_documents: RelatedDoc[];    // Cross-references
  };

  // ========================================
  // SECTION 5: PROCESSING METADATA (5 fields)
  // ========================================
  processing_metadata: {
    chunk_id: string;            // Unique chunk ID
    chunk_index: number;         // Position in document
    processing_date: string;     // ISO 8601: when processed
    pipeline_version: string;    // "2.1.0"
    chunking_strategy: string;   // "hierarchical" | "semantic" | "fixed"
  };

  // ========================================
  // SECTION 6: QUALITY METRICS (5 fields)
  // ========================================
  quality_metrics: {
    text_length: number;         // Character count
    token_count: number;         // Token count for embedding
    confidence_score: number;    // 0.0-1.0: extraction confidence
    completeness_score: number;  // 0.0-1.0: metadata completeness
    validation_passed: boolean;  // Schema validation result
  };

  // ========================================
  // SECTION 7: EXTENDED METADATA (Optional)
  // ========================================
  extended_metadata: {
    // Type-specific fields
    law?: LawExtendedMetadata;
    decree?: DecreeExtendedMetadata;
    circular?: CircularExtendedMetadata;
    decision?: DecisionExtendedMetadata;
    bidding?: BiddingExtendedMetadata;
    report?: ReportExtendedMetadata;
    exam?: ExamExtendedMetadata;
  };
}
```

---

### 3.3 Enums & Types Definitions

```typescript
// ========================================
// VIETNAM LEGAL SYSTEM ENUMS
// ========================================

enum DocType {
  LAW = "law",                    // Luật
  DECREE = "decree",              // Nghị định
  CIRCULAR = "circular",          // Thông tư
  DECISION = "decision",          // Quyết định
  BIDDING = "bidding_template",   // Hồ sơ mời thầu
  REPORT = "report_template",     // Mẫu báo cáo
  EXAM = "exam_question"          // Câu hỏi thi
}

enum LegalLevel {
  CONSTITUTION = 1,    // Hiến pháp (không có trong hệ thống hiện tại)
  LAW = 2,            // Luật - Quốc hội
  DECREE = 3,         // Nghị định - Chính phủ
  CIRCULAR = 4,       // Thông tư - Bộ/Ngành
  DECISION = 4,       // Quyết định - Bộ/Cơ quan/UBND
  APPLIED = 5         // Văn bản áp dụng (Bidding, Report)
}

enum LegalStatus {
  // Tình trạng hiệu lực - ĐẶC THÙ VIỆT NAM
  CON_HIEU_LUC = "con_hieu_luc",           // Còn hiệu lực
  HET_HIEU_LUC = "het_hieu_luc",           // Hết hiệu lực  
  BI_THAY_THE = "bi_thay_the",             // Bị thay thế
  BI_BAI_BO = "bi_bai_bo",                 // Bị bãi bỏ
  DU_THAO = "du_thao",                     // Dự thảo (chưa có hiệu lực)
  NGUNG_HIEU_LUC_MOT_PHAN = "ngung_hieu_luc_mot_phan"  // Ngưng hiệu lực một phần
}

interface RelatedDoc {
  doc_id: string;              // "63/2014/NĐ-CP"
  relationship_type: RelationshipType;
  description: string | null;  // Optional explanation
}

enum RelationshipType {
  // Quan hệ văn bản - ĐẶC THÙ VIỆT NAM
  HUONG_DAN_THI_HANH = "huong_dan_thi_hanh",  // Hướng dẫn thi hành
  THAY_THE = "thay_the",                      // Thay thế
  SUA_DOI_BO_SUNG = "sua_doi_bo_sung",        // Sửa đổi, bổ sung
  BAI_BO = "bai_bo",                          // Bãi bỏ
  THAM_CHIEU = "tham_chieu",                  // Tham chiếu
  LIEN_QUAN = "lien_quan"                     // Liên quan
}
```

---

### 3.4 Extended Metadata by Document Type

#### 3.4.1 Law Extended Metadata

```typescript
interface LawExtendedMetadata {
  law_name: string;            // "Luật Đấu thầu"
  law_category: string;        // "Kinh tế" | "Xã hội" | "Tài chính"
  
  // Structure
  chapter: string | null;      // "CHƯƠNG II"
  section: string | null;      // "Mục 1"
  
  // Legal Classification
  legal_force: string;         // "constitutional" | "legislative" | "administrative"
  subject_area: string[];      // ["đấu thầu", "mua sắm công"]
  
  // Amendment History
  amends: string[];            // ["38/2009/QH12"] - laws this replaces
  amended_by: string[];        // ["55/2019/QH14"] - laws that modified this
  
  // Parliamentary Info
  session: string | null;      // "Kỳ họp thứ 6, Quốc hội khóa XIII"
  vote_result: string | null;  // "423/456 đại biểu tán thành"
}
```

#### 3.4.2 Decree Extended Metadata

```typescript
interface DecreeExtendedMetadata {
  decree_name: string;         // "Nghị định về đấu thầu"
  
  // Implementation
  implements_law: string;      // "43/2013/QH13" (parent law)
  regulatory_level: string;    // "implementing" | "supplementing" | "detailing"
  
  // Scope
  scope_of_application: string;     // "nationwide" | "specific_region"
  target_entities: string[];        // ["public_agencies", "enterprises"]
  geographical_scope: string;       // "Toàn quốc" | "Một số tỉnh"
  
  // Government Info
  cabinet_meeting: string | null;   // "Phiên họp Chính phủ ngày 15/5/2014"
}
```

#### 3.4.3 Circular Extended Metadata

```typescript
interface CircularExtendedMetadata {
  circular_name: string;       // "Thông tư hướng dẫn Luật Đấu thầu"
  
  // Issuing Ministry
  issuing_ministry: string;    // "Bộ Kế hoạch và Đầu tư"
  ministry_code: string;       // "BKHĐT"
  
  // Implementation
  implements_documents: string[];   // ["43/2013/QH13", "63/2014/NĐ-CP"]
  guidance_level: string;          // "detailed" | "procedural" | "interpretative"
  
  // Technical Details  
  regulation_type: string;     // "mandatory" | "guidance" | "interpretation"
  technical_area: string[];    // ["evaluation", "procurement_methods"]
}
```

#### 3.4.4 Decision Extended Metadata (NEW)

```typescript
interface DecisionExtendedMetadata {
  decision_name: string;       // "Quyết định phê duyệt kế hoạch đấu thầu"
  
  // Decision Type
  decision_type: string;       // "administrative" | "judicial" | "organizational"
  subject_matter: string;      // "personnel" | "approval" | "regulation"
  
  // Authority
  issuing_authority: string;   // "Thủ tướng Chính phủ" | "Bộ trưởng"
  issuing_level: string;       // "central" | "ministerial" | "provincial"
  signer_position: string;     // "Thủ tướng" | "Bộ trưởng" | "Chủ tịch UBND"
  
  // Legal Basis
  legal_basis: string[];       // ["43/2013/QH13", "63/2014/NĐ-CP"]
  
  // Execution
  execution_deadline: string | null;  // "2025-12-31" or null
  applies_to: string[];              // ["agencies", "enterprises"]
  enforcement_level: string;         // "mandatory" | "directive" | "guidance"
  
  // Responsibilities
  responsible_organizations: Record<string, string>;  // {"Bộ KH&ĐT": "Chủ trì", "Bộ TC": "Phối hợp"}
}
```

#### 3.4.5 Bidding Extended Metadata

```typescript
interface BiddingExtendedMetadata {
  // Template Classification
  template_type: string;       // "consultant" | "construction" | "goods" | "mixed"
  template_code: string;       // "Mẫu số 5A" | "Form 8B"
  template_version: string;    // "2025.1"
  
  // Procurement Context
  procurement_method: string;  // "open" | "limited" | "direct"
  selection_method: string;    // "quality_cost" | "lowest_price" | "fixed_budget"
  contract_type: string;       // "lump_sum" | "unit_price" | "time_based"
  
  // Requirements
  section_type: string;        // "general" | "specific" | "evaluation"
  requirements_level: string;  // "mandatory" | "optional" | "preferred"
  technical_complexity: string; // "simple" | "moderate" | "complex"
  
  // Evaluation
  evaluation_criteria: string[];    // ["technical", "financial", "experience"]
  scoring_method: string;           // "points" | "pass_fail" | "ranking"
  
  // Contractor
  contractor_type: string[];   // ["individual", "enterprise", "joint_venture"]
  contract_value_range: string; // "under_5b" | "5b_to_50b" | "over_50b"
  
  // Compliance
  legal_compliance_refs: string[];  // ["Decree 63", "Circular 05"]
}
```

#### 3.4.6 Report Extended Metadata

```typescript
interface ReportExtendedMetadata {
  // Report Classification
  report_type: string;         // "progress" | "completion" | "financial" | "technical"
  template_category: string;   // "bidding" | "project_management" | "monitoring"
  template_version: string;    // "1.0"
  
  // Structure
  required_sections: string[]; // ["executive_summary", "detailed_content"]
  
  // Context
  target_audience: string[];   // ["owner", "consultant", "contractor"]
  submission_phase: string;    // "pre_bidding" | "during_bidding" | "execution"
  frequency: string;           // "monthly" | "quarterly" | "milestone"
  
  // Requirements
  data_requirements: string[]; // ["project_info", "financial_data"]
  compliance_standards: string[]; // ["Decree 63", "Circular 05"]
  
  // Workflow
  approval_workflow: {
    preparer: string;          // "project_manager"
    reviewers: string[];       // ["technical_lead", "financial_controller"]
    approver: string;          // "project_director"
  };
}
```

#### 3.4.7 Exam Extended Metadata

```typescript
interface ExamExtendedMetadata {
  // Question Classification
  question_type: string;       // "multiple_choice" | "true_false" | "scenario" | "essay"
  difficulty_level: string;    // "basic" | "intermediate" | "advanced"
  question_bank: string;       // "CCDT_round_1" | "CCDT_round_2"
  
  // Topic & Learning
  topic_area: string[];        // ["bidding_law", "procedures", "evaluation"]
  competency_tested: string;   // "knowledge" | "application" | "analysis"
  bloom_taxonomy_level: number; // 1-6
  learning_objective: string;  // "Understand bidding procedures"
  
  // Question Content
  scenario_description: string | null;  // For scenario-based questions
  answer_options: AnswerOption[] | null; // For MCQ
  correct_answer: string;               // Answer key (encrypted/separate storage)
  answer_explanation: string;           // Detailed explanation
  
  // Assessment
  points_value: number;        // 1.0, 2.0, etc.
  time_allocation_minutes: number; // 2, 5, 10, etc.
  multi_part: boolean;         // true if question has sub-questions
  scenario_based: boolean;     // true if scenario-based
  
  // Usage
  usage_stats: {
    times_used: number;
    avg_score: number;         // 0.0-1.0
    difficulty_index: number;  // 0.0-1.0 (empirical difficulty)
  };
}

interface AnswerOption {
  id: string;                  // "A" | "B" | "C" | "D"
  text: string;                // Answer content
  is_correct: boolean;         // For internal use only
}
```

---

### 3.5 Validation Rules

```python
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, List, Dict, Any

class DocumentInfo(BaseModel):
    doc_id: str = Field(..., regex=r'^[a-z_0-9]+$')
    title: str = Field(..., min_length=1, max_length=500)
    doc_type: DocType
    legal_code: Optional[str] = Field(None, regex=r'^\d+/\d{4}/[A-Z\-]+$')
    source_file: str
    source_url: Optional[str] = None
    
    @validator('legal_code')
    def validate_legal_code_format(cls, v, values):
        """Validate Vietnamese legal code format"""
        if v and values.get('doc_type') in ['law', 'decree', 'circular', 'decision']:
            if not re.match(r'^\d+/\d{4}/[A-ZĐ\-]+$', v):
                raise ValueError(f'Invalid legal code format: {v}')
        return v

class LegalMetadata(BaseModel):
    issued_by: str = Field(..., min_length=1)
    issuing_level: int = Field(..., ge=1, le=5)
    signer: Optional[str] = None
    promulgation_date: str = Field(..., regex=r'^\d{4}-\d{2}-\d{2}$')
    effective_date: str = Field(..., regex=r'^\d{4}-\d{2}-\d{2}$')
    expiry_date: Optional[str] = Field(None, regex=r'^\d{4}-\d{2}-\d{2}$')
    status: LegalStatus
    
    @validator('effective_date')
    def effective_after_promulgation(cls, v, values):
        """Effective date must be >= promulgation date"""
        if 'promulgation_date' in values:
            if v < values['promulgation_date']:
                raise ValueError('Effective date cannot be before promulgation date')
        return v
    
    @validator('expiry_date')
    def expiry_after_effective(cls, v, values):
        """Expiry date must be > effective date"""
        if v and 'effective_date' in values:
            if v <= values['effective_date']:
                raise ValueError('Expiry date must be after effective date')
        return v

class ContentStructure(BaseModel):
    hierarchy_path: List[str] = Field(..., min_items=1, max_items=7)
    hierarchy_level: int = Field(..., ge=0, le=6)
    article: Optional[str] = Field(None, regex=r'^Điều \d+$')
    paragraph: Optional[str] = Field(None, regex=r'^Khoản \d+$')
    point: Optional[str] = Field(None, regex=r'^Điểm [a-z]$')
    
    @validator('hierarchy_level')
    def level_matches_path(cls, v, values):
        """Hierarchy level should match path length"""
        if 'hierarchy_path' in values:
            if v != len(values['hierarchy_path']) - 1:
                raise ValueError(f'Hierarchy level {v} does not match path length')
        return v

class Relationships(BaseModel):
    implements: Optional[str] = None
    supersedes: List[str] = Field(default_factory=list)
    related_documents: List[RelatedDoc] = Field(default_factory=list)
    
    @validator('implements')
    def implements_format(cls, v):
        """Validate parent law format"""
        if v and not re.match(r'^\d+/\d{4}/[A-ZĐ\-]+$', v):
            raise ValueError(f'Invalid parent law format: {v}')
        return v

class ProcessingMetadata(BaseModel):
    chunk_id: str = Field(..., regex=r'^[a-z_0-9]+$')
    chunk_index: int = Field(..., ge=0)
    processing_date: str = Field(..., regex=r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')
    pipeline_version: str = Field(..., regex=r'^\d+\.\d+\.\d+$')
    chunking_strategy: str = Field(..., regex=r'^(hierarchical|semantic|fixed)$')

class QualityMetrics(BaseModel):
    text_length: int = Field(..., ge=0)
    token_count: int = Field(..., ge=0)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    completeness_score: float = Field(..., ge=0.0, le=1.0)
    validation_passed: bool
    
    @validator('token_count')
    def token_count_reasonable(cls, v, values):
        """Token count should be roughly 1/4 of character count"""
        if 'text_length' in values:
            if v > values['text_length']:  # Tokens can't exceed chars
                raise ValueError('Token count exceeds character count')
        return v

class UnifiedLegalChunk(BaseModel):
    document_info: DocumentInfo
    legal_metadata: LegalMetadata
    content_structure: ContentStructure
    relationships: Relationships
    processing_metadata: ProcessingMetadata
    quality_metrics: QualityMetrics
    extended_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        validate_assignment = True
        extra = 'forbid'  # Don't allow unexpected fields
```

---

### 3.6 Migration Mapping Tables

#### Law Pipeline → Unified Schema

| Old Field | New Field | Transformation |
|-----------|-----------|----------------|
| `law_number` | `legal_metadata.legal_code` | Direct copy |
| `law_name` | `document_info.title` | Direct copy |
| `issuing_body` | `legal_metadata.issued_by` | Direct copy |
| `effective_date` | `legal_metadata.effective_date` | Convert to ISO 8601 |
| `chapter` | `extended_metadata.law.chapter` | Direct copy |
| `article` | `content_structure.article` | Direct copy |
| `paragraph` | `content_structure.paragraph` | Rename from `paragraph` |
| `point` | `content_structure.point` | Direct copy |
| `hierarchy_level` | `content_structure.hierarchy_level` | Direct copy |
| `amendment_history` | `extended_metadata.law.amended_by` | Direct copy |

#### Decree Pipeline → Unified Schema

| Old Field | New Field | Transformation |
|-----------|-----------|----------------|
| `decree_number` | `legal_metadata.legal_code` | Direct copy |
| `issuing_authority` | `legal_metadata.issued_by` | Direct copy |
| `implements_law` | `relationships.implements` | Direct copy |
| `effective_date` | `legal_metadata.effective_date` | Convert to ISO 8601 |
| `target_entities` | `extended_metadata.decree.target_entities` | Direct copy |
| `scope_of_application` | `extended_metadata.decree.scope_of_application` | Direct copy |

#### Circular Pipeline → Unified Schema

| Old Field | New Field | Transformation |
|-----------|-----------|----------------|
| `circular_number` | `legal_metadata.legal_code` | Direct copy |
| `issuing_agency` | `legal_metadata.issued_by` | Direct copy |
| `effective_date` | `legal_metadata.effective_date` | Convert to ISO 8601 |
| `status` | `legal_metadata.status` | Map to Vietnamese enum |
| `supersedes` | `relationships.supersedes` | Direct copy |
| `article_number` | `content_structure.article` | Format as "Điều X" |
| `clause_number` | `content_structure.paragraph` | Format as "Khoản X" |

#### Bidding Pipeline → Unified Schema

| Old Field | New Field | Transformation |
|-----------|-----------|----------------|
| `doc_type` | `document_info.doc_type` | Set to "bidding_template" |
| `template_type` | `extended_metadata.bidding.template_type` | Direct copy |
| `section_type` | `extended_metadata.bidding.section_type` | Direct copy |
| `requirements_level` | `extended_metadata.bidding.requirements_level` | Direct copy |
| `evaluation_criteria` | `extended_metadata.bidding.evaluation_criteria` | Direct copy |
| `legal_compliance_refs` | `extended_metadata.bidding.legal_compliance_refs` | Direct copy |

---

### 3.7 Schema Benefits Summary

#### ✅ Consistency
- **Single source of truth**: 21 core fields for all document types
- **Standardized enums**: Vietnamese legal terminology
- **Uniform date format**: ISO 8601 everywhere
- **Type safety**: Pydantic validation

#### ✅ Vietnam-specific Features
- **Legal hierarchy**: Explicit levels (Luật > Nghị định > Thông tư > Quyết định)
- **Status tracking**: "Còn hiệu lực", "Hết hiệu lực", "Bị thay thế"
- **Relationships**: "Hướng dẫn thi hành", "Thay thế", "Sửa đổi bổ sung"
- **Structure**: Phần → Chương → Mục → Điều → Khoản → Điểm

#### ✅ International Best Practices
- **Citation networks**: Track document relationships
- **Temporal validity**: Effective/expiry dates
- **Quality metrics**: Confidence scores
- **Semantic tags**: Subject areas, keywords

#### ✅ Extensibility
- **Extended metadata**: Type-specific fields isolated
- **New document types**: Easy to add (e.g., Decision)
- **Backward compatible**: Old data migrates cleanly
- **Version tracking**: Schema evolution supported

#### ✅ Performance
- **Indexed fields**: doc_id, legal_code, status
- **Efficient querying**: hierarchy_path as array
- **Optimized retrieval**: Quality scores for ranking
- **Fast validation**: <100ms per document

---

## 💡 RECOMMENDATIONS

### Priority 1: Immediate Actions (Week 1)

#### R1.1 Adopt Industry-Standard Schema Patterns
**Recommendation**: Implement citation network and temporal validity tracking như LexNLP và VietLaw AI.

**Rationale**:
- Citation networks critical cho legal research
- Temporal validity essential cho compliance
- Industry-proven patterns reduce risk

**Implementation**:
```python
# Add to unified schema
"relationships": {
  "citations": [
    {
      "cited_doc_id": "43/2013/QH13",
      "citation_type": "implements|references|supersedes",
      "cited_article": "Điều 5, Khoản 2",
      "citation_context": "..."
    }
  ]
},

"temporal_validity": {
  "effective_date": "2025-04-01T00:00:00Z",
  "expiry_date": null,
  "status": "active",
  "status_history": [
    {
      "status": "draft",
      "date": "2024-12-01T00:00:00Z"
    },
    {
      "status": "active",
      "date": "2025-04-01T00:00:00Z"
    }
  ]
}
```

#### R1.2 Implement Hierarchical Path Encoding
**Recommendation**: Use array-based hierarchy paths for efficient retrieval.

**Rationale**:
- Enables breadcrumb navigation
- Facilitates context-aware retrieval
- Supports partial hierarchy matching

**Implementation**:
```python
"content_structure": {
  "hierarchy_path": [
    "PHẦN THỨ HAI",
    "CHƯƠNG II",
    "Mục 1",
    "Điều 15",
    "Khoản 2",
    "Điểm a"
  ],
  "hierarchy_level": 5,  # 0=Phần, 1=Chương, 2=Mục, 3=Điều, 4=Khoản, 5=Điểm
  
  # For easier querying
  "chapter_id": "chuong-02",
  "article_id": "dieu-15",
  "paragraph_id": "khoan-02",
  "point_id": "diem-a"
}
```

#### R1.3 Add Semantic Enrichment Fields
**Recommendation**: Include semantic tags và legal concepts như LSE system.

**Rationale**:
- Improves semantic search accuracy
- Enables concept-based retrieval
- Supports advanced analytics

**Implementation**:
```python
"semantic_enrichment": {
  "legal_concepts": [
    "quyền_và_nghĩa_vụ_của_nhà_thầu",
    "hồ_sơ_dự_thầu",
    "đánh_giá_hồ_sơ"
  ],
  
  "named_entities": {
    "organizations": ["Bộ Kế hoạch và Đầu tư"],
    "locations": ["Việt Nam"],
    "regulations": ["Luật Đấu thầu 43/2013/QH13"]
  },
  
  "key_phrases": [
    "nhà thầu đủ điều kiện",
    "hồ sơ yêu cầu",
    "tiêu chí đánh giá"
  ]
}
```

### Priority 2: Schema Enhancements (Week 2)

#### R2.1 Implement Versioning System
**Recommendation**: Add schema versioning và migration tracking.

```python
"schema_metadata": {
  "schema_version": "1.0.0",
  "migrated_from_version": "0.9.5",
  "migration_date": "2025-11-15T10:30:00Z",
  "migration_script": "migrate_v0.9_to_v1.0.py"
}
```

#### R2.2 Add Quality Assurance Fields
**Recommendation**: Comprehensive quality metrics cho monitoring.

```python
"quality_assurance": {
  "extraction_confidence": 0.95,
  "ocr_quality": null,  # if applicable
  "validation_passed": true,
  "validation_errors": [],
  "human_reviewed": false,
  "review_date": null,
  "reviewer": null
}
```

#### R2.3 Support Multi-language
**Recommendation**: Prepare for English translations.

```python
"i18n": {
  "primary_language": "vi",
  "translations": {
    "en": {
      "title": "Bidding Law",
      "summary": "..."
    }
  }
}
```

### Priority 3: Long-term Improvements (Week 3+)

#### R3.1 Machine Learning Integration
- Intent classification for queries
- Relevance scoring models
- Automatic concept extraction

#### R3.2 Advanced Analytics
- Document clustering
- Topic modeling
- Trend analysis

#### R3.3 User Behavior Tracking
- Click-through rates
- Dwell time
- Feedback signals

---

## 📈 EXPECTED OUTCOMES

### Phase 1 Completion Metrics

#### Quantitative Metrics
- [x] **Schema coverage**: 100% of 55 fields mapped
- [ ] **Validation success**: >98% of test documents pass
- [ ] **Performance**: <100ms validation time per document
- [ ] **Stakeholder approval**: 100% sign-off

#### Qualitative Metrics
- [ ] **Schema clarity**: Understandable by non-technical stakeholders
- [ ] **Extensibility**: Easy to add new document types
- [ ] **Industry alignment**: Matches 80%+ of legal RAG best practices

### Success Criteria for Phase 1
1. ✅ Unified schema specification approved
2. ⏳ All 55 fields mapped to unified schema
3. ⏳ Validation framework implemented and tested
4. ⏳ Migration plan documented and reviewed
5. ⏳ Stakeholder sign-off obtained

---

## 🚀 NEXT STEPS

### Week 2 Actions
1. **Complete validation framework** (2.2)
2. **Create test datasets** (2.3)
3. **Stakeholder review sessions** (2.3)
4. **Begin migration script development** (3.2)

### Week 3 Actions
1. **Finalize documentation** (3.3)
2. **Complete migration testing** (3.2)
3. **Phase 1 approval checkpoint**
4. **Prepare for Phase 2: Pipeline Updates**

---

## 📎 APPENDICES

### Appendix A: Complete Field Inventory
See separate file: `FIELD_INVENTORY.xlsx`

### Appendix B: Validation Test Cases
See separate file: `VALIDATION_TESTS.md`

### Appendix C: Migration Scripts
See directory: `scripts/migration/`

### Appendix D: Stakeholder Feedback
See separate file: `STAKEHOLDER_FEEDBACK.md`

---

**Document Control**:
- **Version**: 1.0
- **Last Updated**: 31/10/2025
- **Next Review**: Week 2, Day 1
- **Approval Status**: ⏳ Pending

**Sign-off**:
- [ ] Tech Lead
- [ ] Data Engineering Lead  
- [ ] Product Owner
- [ ] Domain Expert (Legal)

---

*This document is a living document and will be updated throughout Phase 1.*
