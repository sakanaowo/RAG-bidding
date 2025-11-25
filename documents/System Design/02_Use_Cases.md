# Use Cases - RAG Bidding System

**Ngày tạo:** 24/11/2025  
**Phiên bản:** 2.0  
**Tác giả:** System Architecture Team

---

## Mục Lục

1. [Actors](#1-actors)
2. [Use Case Diagram](#2-use-case-diagram)
3. [Use Cases - Question Answering](#3-use-cases---question-answering)
4. [Use Cases - Document Management](#4-use-cases---document-management)
5. [Use Cases - Chat Sessions](#5-use-cases---chat-sessions)
6. [Use Cases - System Administration](#6-use-cases---system-administration)
7. [Exception Scenarios](#7-exception-scenarios)

---

## 1. Actors

### 1.1. Primary Actors

- **End User:** Người dùng hỏi đáp về luật và đấu thầu
- **Document Manager:** Người quản lý upload và xử lý tài liệu
- **System Administrator:** Người quản trị hệ thống

### 1.2. Secondary Actors

- **OpenAI API:** Cung cấp embeddings và LLM
- **PostgreSQL Database:** Lưu trữ documents và vectors
- **Redis Cache:** Caching layer
- **Background Worker:** Xử lý tài liệu bất đồng bộ

---

## 2. Use Case Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    RAG BIDDING SYSTEM                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [End User]                                                      │
│      │                                                           │
│      ├──→ UC-1: Ask Question (Simple)                          │
│      ├──→ UC-2: Ask Question (Advanced with Filters)           │
│      ├──→ UC-3: View Source Documents                          │
│      ├──→ UC-4: Create Chat Session                            │
│      ├──→ UC-5: Continue Chat Conversation                     │
│      └──→ UC-6: View Chat History                              │
│                                                                  │
│  [Document Manager]                                              │
│      │                                                           │
│      ├──→ UC-7: Upload Single Document                         │
│      ├──→ UC-8: Upload Batch Documents                         │
│      ├──→ UC-9: Check Processing Status                        │
│      ├──→ UC-10: Update Document Metadata                      │
│      ├──→ UC-11: Delete Document                               │
│      ├──→ UC-12: Search Documents by Metadata                  │
│      └──→ UC-13: Export Document Statistics                    │
│                                                                  │
│  [System Administrator]                                          │
│      │                                                           │
│      ├──→ UC-14: Monitor System Health                         │
│      ├──→ UC-15: Clear Cache                                   │
│      ├──→ UC-16: View System Statistics                        │
│      ├──→ UC-17: Configure RAG Pipeline Mode                   │
│      └──→ UC-18: Manage Database Indexes                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Use Cases - Question Answering

### UC-1: Ask Question (Simple)

**Actor:** End User  
**Priority:** High  
**Frequency:** Very High (~1000 queries/day)

**Preconditions:**

- Hệ thống đang hoạt động
- Database có ít nhất 1 document active

**Main Flow:**

1. User gửi câu hỏi qua POST `/ask`
   ```json
   {
     "question": "Quy định về thầu rộng rãi trong luật đấu thầu là gì?"
   }
   ```
2. System validates input
3. System checks L1 cache (LRU)
4. If cache miss:
   - Generate embeddings cho query
   - Vector search trong PostgreSQL (cosine similarity)
   - Retrieve top-K chunks (K=10)
   - Rerank với BGE (top-5)
5. System generates answer với GPT-4o-mini
6. System caches result (L1 + L2)
7. System returns response
   ```json
   {
     "answer": "Thầu rộng rãi là...",
     "sources": [...],
     "latency_ms": 2345,
     "cache_hit": false,
     "mode": "balanced"
   }
   ```

**Alternative Flows:**

- **A1:** Cache hit → Return cached result (latency <1ms)
- **A2:** No relevant docs found → Return "Không tìm thấy thông tin"

**Postconditions:**

- User nhận được câu trả lời
- Query được cache
- Metrics được log

---

### UC-2: Ask Question (Advanced with Filters)

**Actor:** End User  
**Priority:** Medium  
**Frequency:** Medium (~300 queries/day)

**Preconditions:**

- Same as UC-1

**Main Flow:**

1. User gửi câu hỏi với filters
   ```json
   {
     "question": "Quy định về bảo đảm dự thầu",
     "filters": {
       "document_types": ["law", "decree"],
       "categories": ["legal"],
       "date_range": {
         "from": "2020-01-01",
         "to": "2025-12-31"
       }
     },
     "mode": "quality",
     "top_k": 5
   }
   ```
2. System applies metadata filters trong vector search
3. Rest same as UC-1

**Postconditions:**

- Results filtered theo metadata
- Higher precision due to filters

---

### UC-3: View Source Documents

**Actor:** End User  
**Priority:** Medium  
**Frequency:** Medium

**Preconditions:**

- User đã nhận answer từ UC-1 hoặc UC-2

**Main Flow:**

1. User clicks vào source document ID
2. System retrieves full document metadata
   ```json
   {
     "document_id": "doc_001",
     "document_name": "Luật Đấu Thầu 2023",
     "document_type": "law",
     "category": "legal",
     "total_chunks": 125,
     "created_at": "2024-01-15",
     "source_file": "data/processed/laws/luat_dau_thau_2023.jsonl"
   }
   ```
3. User có thể view full chunks của document
4. User có thể download original file

**Postconditions:**

- User hiểu context của answer
- Transparency về sources

---

## 4. Use Cases - Document Management

### UC-7: Upload Single Document

**Actor:** Document Manager  
**Priority:** High  
**Frequency:** Medium (~50 uploads/week)

**Preconditions:**

- User có quyền upload
- File hợp lệ (DOCX/PDF, <50MB)

**Main Flow:**

1. User uploads file qua POST `/api/upload/files`

   ```
   POST /api/upload/files
   Content-Type: multipart/form-data

   file: luat_dau_thau_2024.docx
   category: legal
   document_type: law (optional, auto-detect)
   ```

2. System validates file (type, size, virus scan)
3. System generates unique `document_id`
4. System creates record trong `documents` table (status=processing)
5. System queues background processing job
6. System returns upload confirmation
   ```json
   {
     "document_id": "doc_12345",
     "status": "processing",
     "estimated_time": "30-60 seconds"
   }
   ```
7. **Background Processing:**
   - Parse structure (hierarchical)
   - Extract metadata (NER, keywords)
   - Chunking (1000 chars, 200 overlap)
   - Generate embeddings (OpenAI)
   - Store chunks trong `langchain_pg_embedding`
   - Update `documents.status = 'active'`
   - Update `documents.total_chunks`

**Alternative Flows:**

- **A1:** Invalid file format → Return 400 error
- **A2:** File too large → Return 413 error
- **A3:** Processing failed → Set status='error'

**Postconditions:**

- Document available for search
- Embeddings stored trong database
- Metadata indexed

---

### UC-8: Upload Batch Documents

**Actor:** Document Manager  
**Priority:** Medium  
**Frequency:** Low (~5 batches/month)

**Main Flow:**

1. User uploads multiple files (max 20 files)
2. System processes each file sequentially
3. System returns batch status
   ```json
   {
     "total": 20,
     "queued": 20,
     "batch_id": "batch_001"
   }
   ```
4. User polls GET `/api/upload/status/batch_001`

**Postconditions:**

- Multiple documents processed
- Batch report available

---

### UC-9: Check Processing Status

**Actor:** Document Manager  
**Priority:** Medium  
**Frequency:** High

**Main Flow:**

1. User calls GET `/api/upload/status?document_id=doc_12345`
2. System returns status
   ```json
   {
     "document_id": "doc_12345",
     "status": "active",
     "progress": 100,
     "total_chunks": 125,
     "processing_time": "45 seconds",
     "errors": null
   }
   ```

**Status Values:**

- `processing` - Đang xử lý
- `active` - Đã hoàn thành, available
- `error` - Xử lý thất bại
- `expired` - Document bị vô hiệu hóa

---

### UC-10: Update Document Metadata

**Actor:** Document Manager  
**Priority:** Low  
**Frequency:** Low

**Main Flow:**

1. User updates metadata via PATCH `/api/documents/{document_id}`
   ```json
   {
     "category": "legal-updated",
     "status": "expired"
   }
   ```
2. System updates `documents` table
3. System triggers cache invalidation
4. If status changed to 'expired':
   - Document excluded from search
   - Chunks still in DB (soft delete)

**Postconditions:**

- Metadata updated
- Cache cleared
- Search results reflect changes

---

### UC-11: Delete Document

**Actor:** Document Manager  
**Priority:** Low  
**Frequency:** Low

**Main Flow:**

1. User calls DELETE `/api/documents/{document_id}`
2. System soft-deletes:
   - Set `documents.status = 'deleted'`
   - Do NOT delete chunks (audit trail)
3. System clears related cache entries
4. Document excluded from search

**Alternative Flow:**

- **A1:** Hard delete (admin only):
  - Delete from `documents`
  - Cascade delete chunks from `langchain_pg_embedding`

**Postconditions:**

- Document not searchable
- Audit trail preserved

---

### UC-12: Search Documents by Metadata

**Actor:** Document Manager  
**Priority:** Medium  
**Frequency:** Medium

**Main Flow:**

1. User searches via GET `/api/documents/search`
   ```
   GET /api/documents/search?
     document_type=law&
     category=legal&
     status=active&
     created_after=2024-01-01
   ```
2. System queries `documents` table với filters
3. System returns paginated results
   ```json
   {
     "total": 45,
     "page": 1,
     "page_size": 20,
     "results": [...]
   }
   ```

**Postconditions:**

- User finds relevant documents
- Can drill down to specific docs

---

## 5. Use Cases - Chat Sessions

### UC-4: Create Chat Session

**Actor:** End User  
**Priority:** High  
**Frequency:** High

**Preconditions:**

- User authenticated (planned)

**Main Flow:**

1. User creates session via POST `/api/chat/sessions`
   ```json
   {
     "user_id": "user_123",
     "title": "Hỏi về luật đấu thầu"
   }
   ```
2. System creates session
   ```json
   {
     "session_id": "session_789",
     "user_id": "user_123",
     "title": "Hỏi về luật đấu thầu",
     "created_at": "2025-11-24T10:00:00Z",
     "messages": []
   }
   ```
3. System stores session trong Redis (DB 1) - **TO BE DEPRECATED**
4. Future: Migrate to PostgreSQL table `chat_sessions`

**Postconditions:**

- Session created
- Ready for messages

---

### UC-5: Continue Chat Conversation

**Actor:** End User  
**Priority:** High  
**Frequency:** Very High

**Main Flow:**

1. User sends message via POST `/api/chat/sessions/{session_id}/messages`
   ```json
   {
     "message": "Thầu rộng rãi khác gì thầu hạn chế?"
   }
   ```
2. System retrieves session context (last N messages)
3. System generates context-aware query
4. System performs RAG (same as UC-1)
5. System appends message + answer to session
6. System returns response

**Postconditions:**

- Conversation history preserved
- Context-aware answers

---

### UC-6: View Chat History

**Actor:** End User  
**Priority:** Medium  
**Frequency:** Medium

**Main Flow:**

1. User calls GET `/api/chat/sessions/{session_id}`
2. System returns full conversation
   ```json
   {
     "session_id": "session_789",
     "messages": [
       {
         "role": "user",
         "content": "...",
         "timestamp": "..."
       },
       {
         "role": "assistant",
         "content": "...",
         "sources": [...],
         "timestamp": "..."
       }
     ]
   }
   ```

**Postconditions:**

- User reviews past conversations
- Can continue from any point

---

## 6. Use Cases - System Administration

### UC-14: Monitor System Health

**Actor:** System Administrator  
**Priority:** High  
**Frequency:** Continuous

**Main Flow:**

1. Admin calls GET `/health`
   ```json
   {
     "status": "healthy",
     "database": "connected",
     "redis": "connected",
     "embedding_model": "loaded",
     "reranker_model": "loaded",
     "uptime": "5 days 3 hours"
   }
   ```
2. Admin monitors metrics endpoint GET `/metrics`
   ```json
   {
     "queries_total": 125000,
     "queries_per_minute": 25,
     "average_latency_ms": 2340,
     "cache_hit_rate": 0.55,
     "database_connections": {
       "active": 5,
       "idle": 15,
       "max": 20
     },
     "redis_memory_usage_mb": 128
   }
   ```

**Postconditions:**

- System health visible
- Alerts triggered if unhealthy

---

### UC-15: Clear Cache

**Actor:** System Administrator  
**Priority:** Medium  
**Frequency:** Low

**Main Flow:**

1. Admin calls POST `/clear_cache`
   ```json
   {
     "cache_type": "all" // or "L1", "L2"
   }
   ```
2. System clears specified cache
3. System returns confirmation
   ```json
   {
     "cleared": true,
     "cache_type": "all",
     "entries_cleared": 1250
   }
   ```

**Postconditions:**

- Cache cleared
- Next queries will be cache misses

---

### UC-16: View System Statistics

**Actor:** System Administrator  
**Priority:** Medium  
**Frequency:** Daily

**Main Flow:**

1. Admin calls GET `/stats`
   ```json
   {
     "database": {
       "total_documents": 64,
       "total_chunks": 7892,
       "database_size_mb": 149,
       "documents_by_type": {
         "law": 6,
         "decree": 2,
         "circular": 2,
         "bidding_form": 37
       }
     },
     "queries": {
       "total_today": 1250,
       "average_latency_ms": 2340,
       "mode_distribution": {
         "fast": 450,
         "balanced": 700,
         "quality": 100
       }
     },
     "cache": {
       "l1_hit_rate": 0.55,
       "l2_hit_rate": 0.25,
       "total_hit_rate": 0.8
     }
   }
   ```

**Postconditions:**

- Admin understands system usage
- Can plan capacity

---

### UC-17: Configure RAG Pipeline Mode

**Actor:** System Administrator  
**Priority:** Medium  
**Frequency:** Low

**Main Flow:**

1. Admin updates config via POST `/api/config/rag_mode`
   ```json
   {
     "default_mode": "balanced",
     "allow_user_override": true
   }
   ```
2. System updates `src/config/models.py` dynamically
3. System reloads configuration

**Postconditions:**

- New default mode active
- Affects all new queries

---

## 7. Exception Scenarios

### E-1: OpenAI API Rate Limit

**Trigger:** Too many embedding/LLM requests  
**Handling:**

- Retry with exponential backoff
- Queue requests
- Return 503 Service Unavailable

### E-2: PostgreSQL Connection Pool Exhausted

**Trigger:** Too many concurrent queries  
**Handling:**

- Queue requests
- Return 503 with retry-after header
- Alert admin

### E-3: Redis Cache Unavailable

**Trigger:** Redis server down  
**Handling:**

- Fallback to L1 cache only
- Log warning
- Continue operation (degraded)

### E-4: Document Processing Failed

**Trigger:** Corrupted file, parsing error  
**Handling:**

- Set document status='error'
- Store error details
- Notify uploader
- Retry logic (3 attempts)

### E-5: No Relevant Documents Found

**Trigger:** Query too specific or no matching docs  
**Handling:**

- Return polite message
- Suggest broader query
- Log for analysis

### E-6: Vector Search Timeout

**Trigger:** Large database, slow query  
**Handling:**

- Kill query after 10s
- Return cached similar query
- Alert admin to optimize index

---

## 8. Use Case Metrics

| Use Case                      | Daily Volume | Avg Latency | Success Rate |
| ----------------------------- | ------------ | ----------- | ------------ |
| UC-1: Ask Question (Simple)   | 1000         | 2.3s        | 98.5%        |
| UC-2: Ask Question (Advanced) | 300          | 3.1s        | 97.2%        |
| UC-7: Upload Document         | 7            | 45s         | 99.1%        |
| UC-9: Check Status            | 50           | 15ms        | 99.9%        |
| UC-4: Create Session          | 200          | 50ms        | 99.8%        |
| UC-14: Health Check           | 1440         | 5ms         | 100%         |

---

## 9. Future Use Cases (Planned)

### UC-19: User Authentication & Authorization

- Login/Register
- Role-based access control
- API key management

### UC-20: Advanced Analytics

- Query trend analysis
- Popular documents
- User behavior insights

### UC-21: Document Versioning

- Track document changes
- Compare versions
- Rollback support

### UC-22: Export & Reporting

- Export query results (PDF/Excel)
- Generate usage reports
- Compliance reports

### UC-23: Feedback Loop

- User ratings on answers
- Report incorrect answers
- Model improvement pipeline

---

## Tài Liệu Liên Quan

- `01_System_Specification.md` - Đặc tả hệ thống
- `03_Database_Schema.md` - Database design
- `05_API_Specification.md` - API endpoints detail
