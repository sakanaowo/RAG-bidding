# 🔄 Chunking Refactoring & Status Field Implementation

**Date**: November 9, 2025  
**Author**: System Refactoring  
**Status**: ✅ Completed

---

## 📋 Refactoring Summary

### **Problem Identified**
- Có 2 module chunking trùng lặp:
  - `src/chunking/` - **Production code** (modern, đầy đủ features)
  - `src/preprocessing/chunking/` - **Legacy code** (cũ, đơn giản hơn)
- Gây confusion và maintenance overhead
- Trường `status` cho tài liệu pháp lý chưa được thiết kế đầy đủ

---

## ✅ Refactoring Actions

### 1️⃣ **Consolidate Chunking Module**

**Before:**
```
src/
├── chunking/                          # Modern production code
│   ├── base_chunker.py
│   ├── hierarchical_chunker.py
│   ├── semantic_chunker.py
│   ├── bidding_hybrid_chunker.py
│   ├── report_hybrid_chunker.py
│   ├── chunk_factory.py
│   └── strategies/
│       └── chunk_strategy.py
│
└── preprocessing/
    └── chunking/                      # Legacy duplicate
        ├── hierarchical_chunker.py    ❌ OLD
        ├── semantic_chunker.py        ❌ OLD
        └── __init__.py
```

**After:**
```
src/
└── preprocessing/
    └── chunking/                      # All chunking consolidated here
        ├── base_chunker.py           ✅ Moved from src/chunking
        ├── hierarchical_chunker.py   ✅ Moved (modern version)
        ├── semantic_chunker.py       ✅ Moved (modern version)
        ├── bidding_hybrid_chunker.py ✅ Moved
        ├── report_hybrid_chunker.py  ✅ Moved
        ├── chunk_factory.py          ✅ Moved
        └── strategies/
            └── chunk_strategy.py     ✅ Moved
```

**Rationale:**
- Chunking là part của preprocessing pipeline
- Logical structure: `preprocessing/` chứa tất cả các bước xử lý từ raw → chunks
- Dễ maintain hơn khi tất cả ở một nơi

---

## 🆕 Status Field Implementation

### **Requirement**
Cần thêm trường `status` để track trạng thái xử lý của documents qua các giai đoạn pipeline.

### **Analysis**

#### **Option 1: Thêm vào `LegalMetadata.legal_status`** ❌ KHÔNG PHÙ HỢP
```python
class LegalMetadata(BaseModel):
    legal_status: LegalStatus = Field(...)  # ĐÃ TỒN TẠI
    # legal_status = "con_hieu_luc" | "het_hieu_luc" | "bi_thay_the" | ...
```

**Problems:**
- `legal_status` là **legal validity** (hiệu lực pháp lý) - khác với processing status
- Chỉ apply cho Law/Decree/Circular/Decision
- Không apply cho Bidding/Report/Exam documents
- Semantic confusion: "còn hiệu lực" ≠ "đang xử lý"

#### **Option 2: Thêm vào `ProcessingMetadata`** ✅ **RECOMMENDED**
```python
class ProcessingMetadata(BaseModel):
    processing_id: str
    pipeline_version: str
    processed_at: datetime
    processing_stage: ProcessingStage  # ENUM ALREADY EXISTS
    processing_status: ProcessingStatus  # 🆕 NEW FIELD
    # ... other fields
```

**Why this is better:**
- `ProcessingMetadata` đã có `processing_stage` (ingestion, extraction, chunking, etc.)
- Logical separation:
  - `processing_stage` = WHICH step (where in pipeline)
  - `processing_status` = HOW it went (success/failed/pending)
- Applies to ALL document types
- Clear semantics: processing status ≠ legal status

#### **Option 3: Thêm vào `DocumentInfo`** ⚠️ NOT IDEAL
```python
class LegalDocumentInfo(BaseModel):
    doc_id: str
    doc_type: DocType
    processing_status: ProcessingStatus  # 🆕 Less ideal here
```

**Problems:**
- `DocumentInfo` là về metadata của document **content** (title, date, authority)
- Processing status là runtime/pipeline concern
- Mixing content metadata với processing metadata

---

### **✅ RECOMMENDED SOLUTION**

#### **1. Add new enum: `ProcessingStatus`**

**File:** `src/preprocessing/schema/enums.py`

```python
class ProcessingStatus(str, Enum):
    """Status of document processing through pipeline"""
    
    PENDING = "pending"              # Chưa xử lý
    IN_PROGRESS = "in_progress"      # Đang xử lý
    COMPLETED = "completed"          # Hoàn thành
    FAILED = "failed"                # Thất bại
    PARTIAL = "partial"              # Một phần thành công
    SKIPPED = "skipped"              # Bỏ qua (duplicate, blacklist, etc.)
    RETRY = "retry"                  # Cần retry
```

#### **2. Update `ProcessingMetadata`**

**File:** `src/preprocessing/schema/models/processing_metadata.py`

```python
from ..enums import ProcessingStage, ProcessingStatus  # Add import

class ProcessingMetadata(BaseModel):
    """Processing pipeline metadata"""
    
    processing_id: str
    pipeline_version: str
    processed_at: datetime
    
    # Processing progress tracking
    processing_stage: ProcessingStage          # EXISTING
    processing_status: ProcessingStatus = Field(  # 🆕 NEW
        default=ProcessingStatus.PENDING,
        description="Current processing status"
    )
    
    # Error handling
    error_message: Optional[str] = Field(
        None,
        description="Error message if status=failed"
    )
    
    retry_count: int = Field(
        default=0,
        description="Number of retry attempts"
    )
    
    # ... other existing fields
```

#### **3. Usage Example**

```python
# When starting processing
chunk.processing_metadata.processing_status = ProcessingStatus.IN_PROGRESS
chunk.processing_metadata.processing_stage = ProcessingStage.CHUNKING

# On success
chunk.processing_metadata.processing_status = ProcessingStatus.COMPLETED

# On failure
chunk.processing_metadata.processing_status = ProcessingStatus.FAILED
chunk.processing_metadata.error_message = "Chunking failed: Invalid structure"
chunk.processing_metadata.retry_count += 1

# Query documents by status
failed_docs = db.query(UnifiedLegalChunk).filter(
    ProcessingMetadata.processing_status == ProcessingStatus.FAILED
)
```

---

### **Benefits of This Approach**

✅ **Clear Separation of Concerns:**
- `legal_status` = legal validity (content)
- `processing_status` = pipeline execution (runtime)

✅ **Universal Application:**
- Works for ALL document types (Law, Bidding, Report, Exam)

✅ **Pipeline Tracking:**
- Can track documents through entire pipeline
- Easy to find failed/stuck documents
- Supports retry logic

✅ **Schema Consistency:**
- Fits naturally into existing `ProcessingMetadata`
- Already have `processing_stage` for tracking WHERE
- Now have `processing_status` for tracking HOW

✅ **Database Queries:**
```sql
-- Find all failed documents
SELECT * FROM chunks 
WHERE processing_metadata->>'processing_status' = 'failed';

-- Find documents stuck in chunking
SELECT * FROM chunks 
WHERE processing_metadata->>'processing_stage' = 'chunking'
  AND processing_metadata->>'processing_status' = 'in_progress';
```

---

## 📊 Status vs Stage Comparison

| Field | Purpose | Values | Applies To |
|-------|---------|--------|-----------|
| `legal_status` | Legal validity | con_hieu_luc, het_hieu_luc, bi_thay_the | Legal docs only |
| `processing_stage` | Where in pipeline | ingestion, chunking, enrichment, output | All docs |
| `processing_status` | How processing went | pending, in_progress, completed, failed | All docs |

---

## 🔄 Migration Path

### **Phase 1: Add New Fields** (Non-breaking)
1. Add `ProcessingStatus` enum
2. Add `processing_status` to `ProcessingMetadata` with default
3. Add `error_message` and `retry_count` fields
4. Deploy - backward compatible

### **Phase 2: Update Pipeline**
1. Update chunking pipeline to set status
2. Update embedding pipeline to check status
3. Add retry logic for failed documents

### **Phase 3: Monitoring**
1. Dashboard to show processing status breakdown
2. Alerts for stuck/failed documents
3. Metrics on retry rates

---

## 📝 Implementation Files

### Files Modified:
1. `src/preprocessing/schema/enums.py` - Add `ProcessingStatus`
2. `src/preprocessing/schema/models/processing_metadata.py` - Add status field
3. `src/preprocessing/chunking/*.py` - Update to set processing_status
4. `src/api/services/upload_service.py` - Update status tracking

### Files Created:
- This documentation file

---

## ✅ Verification Checklist

- [x] Legacy chunking code removed
- [x] Modern chunking moved to `src/preprocessing/chunking/`
- [x] All imports updated
- [x] Status field design documented
- [ ] `ProcessingStatus` enum implemented
- [ ] `processing_status` field added to `ProcessingMetadata`
- [ ] Pipeline updated to use new status field
- [ ] Tests updated
- [ ] Documentation updated

---

## 🎯 Next Steps

1. **Implement status enum and fields** (this document provides spec)
2. **Update chunking pipeline** to set status at each stage
3. **Add monitoring dashboard** to track processing status
4. **Implement retry logic** for failed documents
5. **Add tests** for status transitions

---

**End of Document**
