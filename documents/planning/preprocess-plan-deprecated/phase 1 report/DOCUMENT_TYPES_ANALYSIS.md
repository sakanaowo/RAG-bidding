 # 📚 PHÂN TÍCH 6 LOẠI VĂN BẢN
## Comprehensive Analysis of All Document Types

**Ngày tạo**: 31/10/2025  
**Mục đích**: Phân tích chi tiết cả 6 loại văn bản trong hệ thống RAG-Bidding

---

## 📊 TỔNG QUAN

### Thực trạng Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                  6 LOẠI VĂN BẢN TRONG HỆ THỐNG                  │
└─────────────────────────────────────────────────────────────────┘

✅ ĐÃ CÓ PIPELINE (4 loại)          ❌ CHƯA CÓ PIPELINE (2 loại)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Luật chính (Laws)                5. Mẫu báo cáo (Report Templates)
   📁 data/raw/Luat chinh/             📁 data/raw/Mau bao cao/
   
2. Nghị định (Decrees)              6. Câu hỏi thi (Exam Questions)  
   📁 data/raw/Nghi dinh/              📁 data/raw/Cau hoi thi/
   
3. Thông tư (Circulars)
   📁 data/raw/Thong tu/
   
4. Hồ sơ mời thầu (Bidding)
   📁 data/raw/Ho so moi thau/
```

---

## 📋 PHÂN TÍCH CHI TIẾT TỪNG LOẠI

### 1. ✅ LUẬT CHÍNH (Laws)

**Vị trí**: `data/raw/Luat chinh/`  
**Pipeline**: ✅ Đã có (Law Pipeline)  
**Pháp lý**: Cấp cao nhất trong hệ thống pháp luật VN

#### Đặc điểm
- **Cấu trúc**: Phần → Chương → Mục → Điều → Khoản → Điểm
- **Tính pháp lý**: Legal Level 1 (cao nhất)
- **Ban hành**: Quốc hội
- **Ví dụ**: Luật Đấu thầu 43/2013/QH13

#### Metadata Schema (31 fields)
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
  "legal_force": "legislative",
  "amendment_history": ["Law 38/2009/QH12"]
}
```

#### Challenges
- Cấu trúc phức tạp với 6 cấp độ
- Amendment history cần tracking
- Relationship với các văn bản hướng dẫn

---

### 2. ✅ NGHỊ ĐỊNH (Decrees)

**Vị trí**: `data/raw/Nghi dinh/`  
**Pipeline**: ✅ Đã có (Decree Pipeline)  
**Pháp lý**: Văn bản hướng dẫn thi hành Luật

#### Đặc điểm
- **Cấu trúc**: Tương tự Luật nhưng ít phức tạp hơn
- **Tính pháp lý**: Legal Level 2
- **Ban hành**: Chính phủ
- **Ví dụ**: Nghị định 63/2014/NĐ-CP

#### Metadata Schema (28 fields)
```json
{
  "doc_type": "decree",
  "decree_number": "63/2014/NĐ-CP",
  "issuing_authority": "Chính phủ",
  "signer": "Thủ tướng Chính phủ",
  "implements_law": "43/2013/QH13",
  "effective_date": "2014-07-01",
  "scope_of_application": "nationwide",
  "target_entities": ["public_agencies", "enterprises", "contractors"],
  "regulatory_level": "implementing",
  "related_decrees": ["Decree 30/2015/NĐ-CP"]
}
```

#### Files Hiện tại
- `ND 214 - 4.8.2025 - Thay thế NĐ24-original.docx`

#### Challenges
- Link với Luật gốc
- Supersession relationship
- Target entities phức tạp

---

### 3. ✅ THÔNG TƯ (Circulars)

**Vị trí**: `data/raw/Thong tu/`  
**Pipeline**: ✅ Đã có (Circular Pipeline)  
**Pháp lý**: Văn bản hướng dẫn chi tiết

#### Đặc điểm
- **Cấu trúc**: Điều → Khoản (đơn giản hơn Luật)
- **Tính pháp lý**: Legal Level 3
- **Ban hành**: Bộ, ngành
- **Ví dụ**: Thông tư 05/2025/TT-BKHĐT

#### Metadata Schema (25 fields)
```json
{
  "doc_type": "circular",
  "circular_number": "05/2025/TT-BKHĐT",
  "issuing_agency": "Bộ Kế hoạch và Đầu tư",
  "effective_date": "2025-04-01",
  "status": "active",
  "supersedes": ["Circular 03/2023/TT-BKHĐT"],
  "subject_area": ["bidding", "procurement", "evaluation"],
  "article_number": "15",
  "clause_number": "2",
  "regulation_type": "mandatory"
}
```

#### Files Hiện tại
- `00. Quyết định Thông tư.docx`

#### Challenges
- Supersession relationships
- Multiple subject areas
- Regulation types (mandatory vs guidance)

---

### 4. ✅ HỒ SƠ MỜI THẦU (Bidding Templates)

**Vị trí**: `data/raw/Ho so moi thau/`  
**Pipeline**: ✅ Đã có (Bidding Pipeline)  
**Pháp lý**: Mẫu áp dụng thực tế

#### Đặc điểm
- **Cấu trúc**: Phần → Section (không có Điều, Khoản)
- **Tính pháp lý**: Legal Level 4 (applied documents)
- **Ban hành**: Bộ Kế hoạch & Đầu tư
- **Loại**: Tư vấn, Xây lắp, Hàng hóa, PC, EC

#### Metadata Schema (37 fields)
```json
{
  "doc_type": "bidding_template",
  "template_type": "consultant|construction|goods|mixed",
  "section_type": "general_requirements|specific_requirements|evaluation",
  "requirements_level": "mandatory|optional|preferred",
  "evaluation_criteria": ["technical", "financial", "experience"],
  "contractor_type": "individual|enterprise|joint_venture",
  "contract_value_range": "under_5b|5b_to_50b|over_50b",
  "procurement_method": "open|limited|direct",
  "technical_complexity": "simple|moderate|complex"
}
```

#### Files Hiện tại (69 files)
**Kế hoạch LCNT**:
- `1. Mẫu 01A-02C_Kế hoạch tổng thể LCNT.docx`

**Hàng hóa**:
- `4. Mẫu số 4A E-HSMT hàng hóa 1 túi.docx`
- `4. Mẫu số 4B E-HSMT hàng hóa 2 túi.docx`
- `4. Mẫu số 4C_E-HSMST hàng hóa sơ tuyển.docx`

**EC (Tư vấn + Xây lắp)**:
- `8. Mẫu số 8A. E-HSMT_ EC 01 túi.docx`
- `8. Mẫu số 8B. E-HSMT_EC 02 túi.docx`
- `8. Mẫu số 8C. E-HSMST_EC sơ tuyển.docx`

**PC (Hàng hóa + Xây lắp)**:
- `9.Mẫu số 9A_E-HSMT_PC 1 túi.docx`
- `9. Mẫu số 9B_ E-HSMT_PC 2 túi.docx`
- `9. Mẫu số 9C_E-HSMST_PC sơ tuyển.docx`

**Mua sắm trực tuyến**:
- `13. Mẫu số 13_ Mua sắm trực tuyến.docx`

**Phụ lục**:
- `15. Phu luc.docx`

#### Challenges
- Nhiều template types khác nhau
- Procurement methods đa dạng
- Evaluation criteria phức tạp
- Large number of files (69 files)

---

### 5. ❌ MẪU BÁO CÁO (Report Templates) - CHƯA CÓ PIPELINE

**Vị trí**: `data/raw/Mau bao cao/`  
**Pipeline**: ❌ Chưa có  
**Pháp lý**: Templates for compliance reporting

#### Đề xuất Schema

```json
{
  "doc_type": "report_template",
  "template_id": "report_{type}_{version}",
  
  // Classification
  "report_type": "progress|completion|financial|technical|evaluation|monitoring",
  "template_category": "bidding|project_management|monitoring|compliance",
  "template_version": "1.0",
  
  // Structure
  "required_sections": [
    "executive_summary",
    "detailed_content", 
    "financial_data",
    "technical_specs",
    "appendices"
  ],
  
  // Context
  "target_audience": "owner|consultant|contractor|regulator|auditor",
  "submission_phase": "pre_bidding|during_bidding|contract_execution|closeout",
  "frequency": "daily|weekly|monthly|quarterly|annual|milestone|ad_hoc",
  
  // Requirements
  "data_requirements": [
    "project_info",
    "financial_data",
    "technical_specs",
    "progress_metrics",
    "risk_assessment"
  ],
  
  // Compliance
  "compliance_standards": ["Decree 63", "Circular 05", "Contract Terms"],
  "legal_references": ["43/2013/QH13", "63/2014/NĐ-CP"],
  
  // Workflow
  "approval_workflow": {
    "preparer": "project_manager",
    "reviewers": ["technical_lead", "financial_controller"],
    "approver": "project_director",
    "final_authority": "owner_representative"
  },
  
  // Metadata
  "issued_by": "Bộ Kế hoạch và Đầu tư",
  "effective_date": "2025-01-01",
  "status": "active",
  "supersedes": null
}
```

#### Trường đề xuất (Estimated 25-30 fields)

**Core Fields** (from unified schema):
- document_info (6 fields)
- legal_metadata (7 fields)
- content_structure (5 fields - simplified)
- processing_metadata (5 fields)
- quality_metrics (5 fields)

**Extended Fields** (report-specific):
```json
{
  "extended_metadata": {
    "report": {
      "report_type": "string",
      "template_category": "string",
      "target_audience": "string",
      "submission_phase": "string",
      "frequency": "string",
      "data_requirements": ["array"],
      "compliance_standards": ["array"],
      "approval_workflow": {
        "preparer": "string",
        "reviewers": ["array"],
        "approver": "string"
      },
      "template_version": "string"
    }
  }
}
```

#### Use Cases
1. **Progress Reports**: Monthly project progress
2. **Financial Reports**: Budget vs actual spending
3. **Technical Reports**: Quality assurance, testing
4. **Evaluation Reports**: Bid evaluation, contractor performance
5. **Compliance Reports**: Regulatory compliance verification
6. **Monitoring Reports**: Project monitoring, risk tracking

#### Implementation Priority
**Priority**: MEDIUM-HIGH  
**Rationale**:
- Critical for project management
- Compliance requirements
- Links to bidding process
- Standardization benefits

**Suggested Timeline**:
- Phase 2: Schema design (Week 4-5)
- Phase 3: Pipeline development (Week 6-7)
- Phase 4: Data migration (Week 8-9)

---

### 6. ❌ CÂU HỎI THI (Exam Questions) - CHƯA CÓ PIPELINE

**Vị trí**: `data/raw/Cau hoi thi/`  
**Pipeline**: ❌ Chưa có  
**Pháp lý**: Educational and assessment materials

#### Files Hiện tại (6 files)
- `Ngân hàng câu hỏi thi CCDT đợt 1.pdf`
- `Ngân hàng câu hỏi CCDT đợt 2.pdf`
- `Ngân hàng câu hỏi CCDT đợt 2.pdf` (duplicate?)
- `NHCH_26.9.2025_dot 2- bổ sung.pdf`
- `NHCH_30.9.25_bo_sung_theo_TB1952_qldt.pdf`
- `Tình huống - câu hỏi đấu thầu.xlsx`

**CCDT**: Chứng chỉ Chuyên gia Đấu thầu (Bidding Expert Certificate)

#### Đề xuất Schema

```json
{
  "doc_type": "exam_question",
  "question_id": "exam_{bank}_{category}_{id}",
  
  // Classification
  "question_type": "multiple_choice|true_false|scenario|essay|calculation",
  "difficulty_level": "basic|intermediate|advanced|expert",
  "question_bank": "CCDT_round_1|CCDT_round_2|CCDT_supplementary",
  
  // Content
  "topic_area": [
    "bidding_law",
    "procurement_procedures",
    "bid_evaluation",
    "contract_management",
    "dispute_resolution",
    "ethical_practices"
  ],
  
  // Legal Links
  "legal_references": [
    {
      "doc_id": "law_43_2013_qh13",
      "article": "Điều 5",
      "paragraph": "Khoản 2"
    }
  ],
  
  // Assessment
  "competency_tested": "knowledge|application|analysis|evaluation|synthesis",
  "bloom_taxonomy_level": 1-6,
  "learning_objective": "string",
  
  // Question Details
  "question_text": "string",
  "scenario_description": "string|null",
  "answer_options": [
    {"id": "A", "text": "..."},
    {"id": "B", "text": "..."},
    {"id": "C", "text": "..."},
    {"id": "D", "text": "..."}
  ],
  "correct_answer": "A|B|C|D|multiple",
  "answer_explanation": "string",
  
  // Metadata
  "points_value": 1.0,
  "time_allocation_minutes": 2,
  "multi_part": false,
  "scenario_based": true,
  
  // Version Control
  "created_date": "2025-09-26",
  "last_modified": "2025-09-30",
  "version": "2.0",
  "status": "active|retired|under_review",
  
  // Usage Tracking
  "usage_stats": {
    "times_used": 0,
    "avg_score": 0.0,
    "difficulty_index": 0.0
  }
}
```

#### Trường đề xuất (Estimated 30-35 fields)

**Core Fields** (from unified schema - adapted):
- document_info (6 fields)
- legal_metadata (5 fields - simplified for educational content)
- relationships (3 fields - link to legal docs)
- processing_metadata (5 fields)
- quality_metrics (5 fields)

**Extended Fields** (exam-specific):
```json
{
  "extended_metadata": {
    "exam": {
      "question_type": "string",
      "difficulty_level": "string",
      "question_bank": "string",
      "topic_area": ["array"],
      "competency_tested": "string",
      "bloom_taxonomy_level": "integer",
      "question_text": "string",
      "scenario_description": "string",
      "answer_options": ["array"],
      "correct_answer": "string",
      "answer_explanation": "string",
      "points_value": "float",
      "time_allocation_minutes": "integer",
      "multi_part": "boolean",
      "scenario_based": "boolean",
      "usage_stats": {
        "times_used": "integer",
        "avg_score": "float",
        "difficulty_index": "float"
      }
    }
  }
}
```

#### Use Cases
1. **Certification Exams**: CCDT certification testing
2. **Training Materials**: Educational content for bidding professionals
3. **Knowledge Base**: Repository of bidding scenarios and solutions
4. **Practice Tests**: Self-assessment for learners
5. **Quality Assurance**: Validate understanding of regulations

#### Special Considerations
- **Answer keys**: Need secure storage (encrypted or separate)
- **Scenario-based**: Complex multi-part questions
- **Legal accuracy**: Must align with current laws
- **Version control**: Questions need updates when laws change
- **Usage analytics**: Track question difficulty and effectiveness

#### Implementation Priority
**Priority**: MEDIUM  
**Rationale**:
- Educational support function
- Not critical for core bidding operations
- Can leverage existing legal document links

**Suggested Timeline**:
- Phase 3: Schema design (Week 8-9)
- Phase 4: Pipeline development (Week 10-11)
- Phase 5: Data migration (Week 12-13)

---

## 📊 COMPARATIVE ANALYSIS

### Schema Complexity Comparison

| Document Type | Fields | Complexity | Legal Level | Priority |
|---------------|--------|------------|-------------|----------|
| **Law** | 31 | ⭐⭐⭐⭐⭐ Very High | 1 | Critical |
| **Decree** | 28 | ⭐⭐⭐⭐ High | 2 | Critical |
| **Circular** | 25 | ⭐⭐⭐ Medium | 3 | Critical |
| **Bidding** | 37 | ⭐⭐⭐⭐ High | 4 | Critical |
| **Report** (TBD) | ~30 | ⭐⭐⭐ Medium | 4 | Medium-High |
| **Exam** (TBD) | ~35 | ⭐⭐⭐⭐ High | 5 | Medium |

### Unified Schema Coverage

```
Current State (4 pipelines):
━━━━━━━━━━━━━━━━━━━━━━━━━━
Law:       [████████░░] 80% coverage by unified schema
Decree:    [█████████░] 85% coverage
Circular:  [██████████] 90% coverage  
Bidding:   [███████░░░] 70% coverage

Future State (6 pipelines):
━━━━━━━━━━━━━━━━━━━━━━━━━━
Law:       [██████████] 95% coverage (improved)
Decree:    [██████████] 95% coverage
Circular:  [██████████] 95% coverage
Bidding:   [█████████░] 85% coverage
Report:    [████████░░] 80% coverage (estimated)
Exam:      [███████░░░] 75% coverage (estimated)
```

### Hierarchical Structure Comparison

```
Law/Decree/Circular:
Phần → Chương → Mục → Điều → Khoản → Điểm
(6 levels)

Bidding Templates:
Phần → Section
(2 levels - simpler)

Report Templates:
Section → Subsection → Item
(3 levels - proposed)

Exam Questions:
Topic → Subtopic → Question
(3 levels - proposed)
```

---

## 🎯 UNIFIED SCHEMA ADAPTATION

### Core Schema Extensions

```json
{
  "schema_version": "1.0.0",
  
  // Same for all 6 types
  "document_info": { ... },
  "legal_metadata": { ... },
  "content_structure": { ... },
  "relationships": { ... },
  "processing_metadata": { ... },
  "quality_metrics": { ... },
  
  // Type-specific extensions
  "extended_metadata": {
    "bidding": { ... },      // Type 4
    "circular": { ... },     // Type 3 (minimal)
    "law": { ... },          // Type 1 (minimal)
    "decree": { ... },       // Type 2
    "report": { ... },       // Type 5 - NEW
    "exam": { ... }          // Type 6 - NEW
  }
}
```

### Field Reusability Matrix

| Field Category | Law | Decree | Circular | Bidding | Report | Exam |
|----------------|-----|--------|----------|---------|--------|------|
| document_info | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| legal_metadata | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ⚠️ |
| content_structure | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ⚠️ |
| relationships | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| processing_metadata | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| quality_metrics | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Reusability** | 100% | 100% | 100% | 83% | 83% | 83% |

Legend: ✅ Full reuse | ⚠️ Partial reuse (adapted) | ❌ Not applicable

---

## 📅 IMPLEMENTATION ROADMAP

### Phase Distribution

```
PHASE 1 (Week 1-3): Schema Design
├─ Law, Decree, Circular, Bidding: ✅ Done
├─ Report Templates: Design schema
└─ Exam Questions: Design schema

PHASE 2 (Week 4-6): Pipeline Development
├─ Law, Decree, Circular, Bidding: Update to unified
├─ Report Templates: Develop new pipeline
└─ Exam Questions: Plan pipeline

PHASE 3 (Week 7-9): Data Migration
├─ Law, Decree, Circular, Bidding: Migrate
├─ Report Templates: Initial data processing
└─ Exam Questions: Data analysis

PHASE 4 (Week 10-12): Integration
├─ All 4 existing: Full integration
├─ Report Templates: Pipeline integration
└─ Exam Questions: Develop pipeline

PHASE 5 (Week 13-14): Launch
├─ All 6 types: Production ready
└─ Monitoring: All pipelines
```

### Priority Ordering

**P0 (Critical - Week 1-9)**:
1. Law
2. Decree  
3. Circular
4. Bidding

**P1 (High - Week 8-12)**:
5. Report Templates

**P2 (Medium - Week 10-14)**:
6. Exam Questions

---

## 💡 RECOMMENDATIONS

### Immediate Actions (Week 1-2)
1. ✅ **Finalize schema** for existing 4 types
2. 📋 **Draft schema** for Report Templates
3. 📋 **Draft schema** for Exam Questions
4. 📋 **Validate** with domain experts

### Short-term (Week 3-6)
1. **Implement** unified schema for existing 4 types
2. **Develop** Report Templates pipeline
3. **Prototype** Exam Questions pipeline
4. **Test** with sample data from all 6 types

### Long-term (Week 7-14)
1. **Migrate** all existing data
2. **Launch** Report Templates pipeline
3. **Launch** Exam Questions pipeline
4. **Monitor** all 6 pipelines
5. **Optimize** based on usage patterns

---

## 📈 SUCCESS METRICS

### Coverage Metrics
- [ ] All 6 document types have defined schemas
- [ ] 95%+ field coverage by unified schema
- [ ] 100% of existing data migrated successfully

### Quality Metrics
- [ ] <5% data loss during migration
- [ ] >98% validation success rate
- [ ] <100ms processing time per document

### Business Metrics
- [ ] Support all bidding lifecycle phases
- [ ] Enable comprehensive legal search
- [ ] Support educational/training needs

---

**Document Status**: 📊 Analysis Complete  
**Next Steps**: Schema finalization and stakeholder review  
**Dependencies**: DEEP_ANALYSIS_REPORT.md, SCHEMA_IMPLEMENTATION_GUIDE.md
