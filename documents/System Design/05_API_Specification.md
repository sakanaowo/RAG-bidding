# API Specification - RAG Bidding System

**Ngày tạo:** 24/11/2025  
**Phiên bản:** 2.0  
**Tác giả:** System Architecture Team

---

## Mục Lục

1. [API Overview](#1-api-overview)
2. [Authentication](#2-authentication)
3. [Question Answering APIs](#3-question-answering-apis)
4. [Document Management APIs](#4-document-management-apis)
5. [Chat Session APIs](#5-chat-session-apis)
6. [System APIs](#6-system-apis)
7. [Error Handling](#7-error-handling)
8. [Rate Limiting](#8-rate-limiting)

---

## 1. API Overview

### 1.1. Base URL

```
Development: http://localhost:8000
Production:  https://api.rag-bidding.example.com
```

### 1.2. Content Type

```
Content-Type: application/json
Accept: application/json
```

### 1.3. API Versioning

- Current version: v2.0
- Future: `/v2/ask`, `/v2/upload`

### 1.4. Common Headers

```http
Content-Type: application/json
Authorization: Bearer {token}  # Future
X-API-Key: {api_key}           # Future
X-Request-ID: {uuid}           # For tracing
```

---

## 2. Authentication

### 2.1. Current Status

⚠️ **No authentication required** (v2.0)

### 2.2. Planned Authentication (v2.1+)

**JWT Authentication:**

```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "secure_password"
}

Response:
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "refresh_token_here"
}
```

**Using Token:**

```http
GET /api/protected-endpoint
Authorization: Bearer eyJhbGciOiJSUzI1NiIs...
```

**API Key Authentication:**

```http
GET /ask
X-API-Key: sk_live_1234567890abcdef
```

---

## 3. Question Answering APIs

### 3.1. Ask Question (Simple)

**Endpoint:** `POST /ask`

**Description:** Hỏi đáp đơn giản với RAG pipeline

**Request:**

```http
POST /ask
Content-Type: application/json

{
  "question": "Quy định về thầu rộng rãi trong luật đấu thầu là gì?"
}
```

**Request Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| question | string | ✅ | - | Câu hỏi của người dùng |
| mode | string | ❌ | "balanced" | RAG mode: fast/balanced/quality/adaptive |
| top_k | integer | ❌ | 5 | Số lượng chunks trả về |

**Response (200 OK):**

```json
{
  "answer": "Thầu rộng rãi là hình thức đấu thầu mà mọi nhà thầu đáp ứng đủ điều kiện, năng lực theo quy định đều có quyền tham dự thầu. Theo Luật Đấu Thầu 2023, thầu rộng rãi được áp dụng cho các gói thầu có giá trị lớn và không yêu cầu năng lực đặc biệt.",
  "sources": [
    {
      "document_id": "doc_001",
      "document_name": "Luật Đấu Thầu 2023",
      "document_type": "law",
      "chunk_id": "doc_001_chunk_015",
      "section_title": "Điều 5: Các hình thức đấu thầu",
      "content": "Thầu rộng rãi là hình thức đấu thầu...",
      "score": 0.89,
      "hierarchy": ["Chapter 1", "Article 5"]
    },
    {
      "document_id": "doc_001",
      "document_name": "Luật Đấu Thầu 2023",
      "document_type": "law",
      "chunk_id": "doc_001_chunk_016",
      "section_title": "Điều 6: Điều kiện áp dụng thầu rộng rãi",
      "content": "Thầu rộng rãi được áp dụng khi...",
      "score": 0.85,
      "hierarchy": ["Chapter 1", "Article 6"]
    }
  ],
  "metadata": {
    "mode": "balanced",
    "latency_ms": 2345,
    "cache_hit": false,
    "cache_layer": null,
    "sources_count": 2,
    "query_enhancements": ["multi_query", "step_back"],
    "reranked": true,
    "timestamp": "2025-11-24T10:00:00Z"
  }
}
```

**Response (400 Bad Request):**

```json
{
  "error": "validation_error",
  "message": "Question is required",
  "details": {
    "field": "question",
    "issue": "missing_field"
  }
}
```

**Response (503 Service Unavailable):**

```json
{
  "error": "service_unavailable",
  "message": "OpenAI API rate limit exceeded. Please try again later.",
  "retry_after": 60
}
```

**cURL Example:**

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quy định về thầu rộng rãi trong luật đấu thầu là gì?"
  }'
```

---

### 3.2. Ask Question (Advanced)

**Endpoint:** `POST /ask`

**Description:** Hỏi đáp với filters và configuration nâng cao

**Request:**

```http
POST /ask
Content-Type: application/json

{
  "question": "Quy định về bảo đảm dự thầu",
  "mode": "quality",
  "top_k": 10,
  "filters": {
    "document_types": ["law", "decree"],
    "categories": ["legal"],
    "date_range": {
      "from": "2020-01-01",
      "to": "2025-12-31"
    },
    "status": "active"
  },
  "include_metadata": true
}
```

**Request Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| question | string | ✅ | - | Câu hỏi |
| mode | string | ❌ | "balanced" | fast/balanced/quality/adaptive |
| top_k | integer | ❌ | 5 | Số chunks (1-20) |
| filters | object | ❌ | {} | Metadata filters |
| filters.document_types | array | ❌ | [] | Filter theo loại văn bản |
| filters.categories | array | ❌ | [] | Filter theo category |
| filters.date_range | object | ❌ | null | Filter theo ngày tạo |
| filters.status | string | ❌ | "active" | active/expired/all |
| include_metadata | boolean | ❌ | true | Include metadata trong response |

**Response:** Same as 3.1

---

## 4. Document Management APIs

### 4.1. Upload Document

**Endpoint:** `POST /api/upload/files`

**Description:** Upload văn bản DOCX/PDF

**Request:**

```http
POST /api/upload/files
Content-Type: multipart/form-data

file: @luat_dau_thau_2024.docx
category: legal
document_type: law
```

**Form Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| file | file | ✅ | DOCX/PDF file (<50MB) |
| category | string | ❌ | Category (auto-detect if omitted) |
| document_type | string | ❌ | Type (auto-detect if omitted) |

**Response (202 Accepted):**

```json
{
  "document_id": "doc_12345",
  "job_id": "job_67890",
  "status": "processing",
  "file_name": "luat_dau_thau_2024.docx",
  "file_size_bytes": 524288,
  "estimated_time_seconds": 45,
  "status_url": "/api/upload/status/doc_12345"
}
```

**Response (400 Bad Request):**

```json
{
  "error": "invalid_file_type",
  "message": "Only DOCX and PDF files are supported",
  "supported_types": [
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/pdf"
  ]
}
```

**Response (413 Payload Too Large):**

```json
{
  "error": "file_too_large",
  "message": "File size exceeds 50MB limit",
  "max_size_bytes": 52428800,
  "actual_size_bytes": 104857600
}
```

**cURL Example:**

```bash
curl -X POST http://localhost:8000/api/upload/files \
  -F "file=@luat_dau_thau_2024.docx" \
  -F "category=legal" \
  -F "document_type=law"
```

---

### 4.2. Check Upload Status

**Endpoint:** `GET /api/upload/status/{document_id}`

**Description:** Kiểm tra trạng thái xử lý document

**Request:**

```http
GET /api/upload/status/doc_12345
```

**Response (200 OK) - Processing:**

```json
{
  "document_id": "doc_12345",
  "job_id": "job_67890",
  "status": "processing",
  "progress": 65,
  "file_name": "luat_dau_thau_2024.docx",
  "total_chunks": 0,
  "current_step": "embedding_generation",
  "started_at": "2025-11-24T10:00:00Z",
  "estimated_completion": "2025-11-24T10:00:45Z"
}
```

**Response (200 OK) - Completed:**

```json
{
  "document_id": "doc_12345",
  "job_id": "job_67890",
  "status": "active",
  "progress": 100,
  "file_name": "luat_dau_thau_2024.docx",
  "total_chunks": 125,
  "processing_time_seconds": 42,
  "started_at": "2025-11-24T10:00:00Z",
  "completed_at": "2025-11-24T10:00:42Z"
}
```

**Response (200 OK) - Failed:**

```json
{
  "document_id": "doc_12345",
  "job_id": "job_67890",
  "status": "error",
  "progress": 45,
  "error_message": "Failed to parse document structure",
  "error_details": {
    "step": "document_parsing",
    "error_type": "ParsingError",
    "traceback": "..."
  },
  "retry_available": true
}
```

**Response (404 Not Found):**

```json
{
  "error": "document_not_found",
  "message": "Document with ID 'doc_12345' not found"
}
```

---

### 4.3. List Documents

**Endpoint:** `GET /api/documents`

**Description:** Lấy danh sách documents với filters

**Request:**

```http
GET /api/documents?
  document_type=law&
  category=legal&
  status=active&
  page=1&
  page_size=20&
  sort_by=created_at&
  sort_order=desc
```

**Query Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| document_type | string | ❌ | all | Filter theo type |
| category | string | ❌ | all | Filter theo category |
| status | string | ❌ | active | active/expired/all |
| created_after | string | ❌ | null | ISO date (YYYY-MM-DD) |
| created_before | string | ❌ | null | ISO date |
| page | integer | ❌ | 1 | Page number |
| page_size | integer | ❌ | 20 | Items per page (max 100) |
| sort_by | string | ❌ | created_at | Field to sort |
| sort_order | string | ❌ | desc | asc/desc |

**Response (200 OK):**

```json
{
  "total": 64,
  "page": 1,
  "page_size": 20,
  "total_pages": 4,
  "documents": [
    {
      "id": "uuid-1",
      "document_id": "doc_001",
      "document_name": "Luật Đấu Thầu 2023",
      "category": "legal",
      "document_type": "law",
      "source_file": "data/processed/laws/luat_dau_thau_2023.jsonl",
      "file_name": "luat_dau_thau_2023.docx",
      "total_chunks": 125,
      "status": "active",
      "created_at": "2024-01-15T08:30:00Z",
      "updated_at": "2024-01-15T08:30:45Z"
    }
    // ... 19 more documents
  ]
}
```

---

### 4.4. Get Document Details

**Endpoint:** `GET /api/documents/{document_id}`

**Description:** Lấy chi tiết 1 document

**Request:**

```http
GET /api/documents/doc_001
```

**Response (200 OK):**

```json
{
  "id": "uuid-1",
  "document_id": "doc_001",
  "document_name": "Luật Đấu Thầu 2023",
  "category": "legal",
  "document_type": "law",
  "source_file": "data/processed/laws/luat_dau_thau_2023.jsonl",
  "file_name": "luat_dau_thau_2023.docx",
  "total_chunks": 125,
  "status": "active",
  "created_at": "2024-01-15T08:30:00Z",
  "updated_at": "2024-01-15T08:30:45Z",
  "chunks": [
    {
      "chunk_id": "doc_001_chunk_001",
      "chunk_index": 1,
      "section_title": "Chapter 1: General Provisions",
      "content": "...",
      "char_count": 850,
      "hierarchy": ["Chapter 1"]
    }
    // ... more chunks
  ]
}
```

---

### 4.5. Update Document Metadata

**Endpoint:** `PATCH /api/documents/{document_id}`

**Description:** Cập nhật metadata của document

**Request:**

```http
PATCH /api/documents/doc_001
Content-Type: application/json

{
  "category": "legal-updated",
  "status": "expired"
}
```

**Allowed Fields:**
| Field | Type | Description |
|-------|------|-------------|
| category | string | Update category |
| status | string | active/expired/deleted |
| document_name | string | Update name |

**Response (200 OK):**

```json
{
  "document_id": "doc_001",
  "updated_fields": ["category", "status"],
  "cache_cleared": true,
  "updated_at": "2025-11-24T10:00:00Z"
}
```

---

### 4.6. Delete Document

**Endpoint:** `DELETE /api/documents/{document_id}`

**Description:** Xóa document (soft delete)

**Request:**

```http
DELETE /api/documents/doc_001?hard_delete=false
```

**Query Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| hard_delete | boolean | ❌ | false | true = permanent delete |

**Response (200 OK):**

```json
{
  "document_id": "doc_001",
  "delete_type": "soft",
  "status": "deleted",
  "chunks_affected": 125,
  "cache_cleared": true
}
```

---

## 5. Chat Session APIs

### 5.1. Create Chat Session

**Endpoint:** `POST /api/chat/sessions`

**Description:** Tạo chat session mới

**Request:**

```http
POST /api/chat/sessions
Content-Type: application/json

{
  "user_id": "user_123",
  "title": "Hỏi về luật đấu thầu"
}
```

**Response (201 Created):**

```json
{
  "session_id": "session_789",
  "user_id": "user_123",
  "title": "Hỏi về luật đấu thầu",
  "status": "active",
  "created_at": "2025-11-24T10:00:00Z",
  "message_count": 0
}
```

---

### 5.2. Send Message to Session

**Endpoint:** `POST /api/chat/sessions/{session_id}/messages`

**Description:** Gửi message trong session

**Request:**

```http
POST /api/chat/sessions/session_789/messages
Content-Type: application/json

{
  "message": "Thầu rộng rãi khác gì thầu hạn chế?"
}
```

**Response (200 OK):**

```json
{
  "session_id": "session_789",
  "message_id": "msg_456",
  "user_message": {
    "role": "user",
    "content": "Thầu rộng rãi khác gì thầu hạn chế?",
    "timestamp": "2025-11-24T10:01:00Z"
  },
  "assistant_message": {
    "role": "assistant",
    "content": "Thầu rộng rãi và thầu hạn chế khác nhau...",
    "sources": [...],
    "metadata": {
      "mode": "balanced",
      "latency_ms": 2456
    },
    "timestamp": "2025-11-24T10:01:02Z"
  }
}
```

---

### 5.3. Get Session History

**Endpoint:** `GET /api/chat/sessions/{session_id}`

**Description:** Lấy toàn bộ conversation history

**Request:**

```http
GET /api/chat/sessions/session_789
```

**Response (200 OK):**

```json
{
  "session_id": "session_789",
  "user_id": "user_123",
  "title": "Hỏi về luật đấu thầu",
  "status": "active",
  "created_at": "2025-11-24T10:00:00Z",
  "last_message_at": "2025-11-24T10:05:00Z",
  "message_count": 6,
  "messages": [
    {
      "message_id": "msg_001",
      "role": "user",
      "content": "...",
      "timestamp": "..."
    },
    {
      "message_id": "msg_002",
      "role": "assistant",
      "content": "...",
      "sources": [...],
      "timestamp": "..."
    }
    // ... more messages
  ]
}
```

---

### 5.4. List User Sessions

**Endpoint:** `GET /api/chat/sessions`

**Description:** Lấy danh sách sessions của user

**Request:**

```http
GET /api/chat/sessions?user_id=user_123&status=active&page=1
```

**Response (200 OK):**

```json
{
  "total": 15,
  "page": 1,
  "page_size": 20,
  "sessions": [
    {
      "session_id": "session_789",
      "title": "Hỏi về luật đấu thầu",
      "status": "active",
      "message_count": 6,
      "created_at": "2025-11-24T10:00:00Z",
      "last_message_at": "2025-11-24T10:05:00Z"
    }
    // ... more sessions
  ]
}
```

---

### 5.5. Delete Session

**Endpoint:** `DELETE /api/chat/sessions/{session_id}`

**Description:** Xóa chat session

**Request:**

```http
DELETE /api/chat/sessions/session_789
```

**Response (200 OK):**

```json
{
  "session_id": "session_789",
  "deleted": true,
  "messages_deleted": 6
}
```

---

## 6. System APIs

### 6.1. Health Check

**Endpoint:** `GET /health`

**Description:** Kiểm tra system health

**Request:**

```http
GET /health
```

**Response (200 OK):**

```json
{
  "status": "healthy",
  "timestamp": "2025-11-24T10:00:00Z",
  "uptime_seconds": 432000,
  "components": {
    "database": {
      "status": "connected",
      "latency_ms": 5
    },
    "redis": {
      "status": "connected",
      "latency_ms": 2
    },
    "embedding_model": {
      "status": "loaded",
      "model": "text-embedding-3-large"
    },
    "reranker_model": {
      "status": "loaded",
      "model": "BAAI/bge-reranker-v2-m3",
      "device": "cuda"
    }
  }
}
```

**Response (503 Service Unavailable):**

```json
{
  "status": "unhealthy",
  "timestamp": "2025-11-24T10:00:00Z",
  "components": {
    "database": {
      "status": "disconnected",
      "error": "Connection timeout"
    }
  }
}
```

---

### 6.2. System Statistics

**Endpoint:** `GET /stats`

**Description:** Lấy thống kê hệ thống

**Request:**

```http
GET /stats
```

**Response (200 OK):**

```json
{
  "database": {
    "total_documents": 64,
    "total_chunks": 7892,
    "database_size_mb": 149,
    "documents_by_type": {
      "law": 6,
      "decree": 2,
      "bidding_form": 37
    }
  },
  "queries": {
    "total_today": 1250,
    "total_this_week": 8500,
    "average_latency_ms": 2340,
    "mode_distribution": {
      "fast": 450,
      "balanced": 700,
      "quality": 100
    }
  },
  "cache": {
    "l1_size": 485,
    "l1_hit_rate": 0.55,
    "l2_hit_rate": 0.25,
    "total_hit_rate": 0.8
  },
  "performance": {
    "average_query_latency_ms": 2340,
    "p50_latency_ms": 2100,
    "p95_latency_ms": 4200,
    "p99_latency_ms": 5800
  }
}
```

---

### 6.3. Clear Cache

**Endpoint:** `POST /clear_cache`

**Description:** Xóa cache

**Request:**

```http
POST /clear_cache
Content-Type: application/json

{
  "cache_type": "all"
}
```

**Request Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| cache_type | string | ❌ | "all" | all/L1/L2 |

**Response (200 OK):**

```json
{
  "cleared": true,
  "cache_type": "all",
  "entries_cleared": {
    "L1": 485,
    "L2": 1250
  }
}
```

---

### 6.4. Get Features

**Endpoint:** `GET /features`

**Description:** Lấy danh sách features được enable

**Request:**

```http
GET /features
```

**Response (200 OK):**

```json
{
  "features": {
    "rag_modes": ["fast", "balanced", "quality", "adaptive"],
    "query_enhancements": ["multi_query", "hyde", "step_back"],
    "reranking": true,
    "reranker_model": "BAAI/bge-reranker-v2-m3",
    "caching": {
      "L1": true,
      "L2": true,
      "L3": true
    },
    "authentication": false,
    "rate_limiting": true,
    "max_file_size_mb": 50,
    "supported_file_types": ["docx", "pdf"]
  }
}
```

---

## 7. Error Handling

### 7.1. Error Response Format

**Standard Error Response:**

```json
{
  "error": "error_code",
  "message": "Human-readable error message",
  "details": {
    "field": "problematic_field",
    "value": "invalid_value",
    "constraint": "validation_rule"
  },
  "timestamp": "2025-11-24T10:00:00Z",
  "request_id": "req_12345"
}
```

### 7.2. Common Error Codes

| HTTP Status | Error Code          | Description                       |
| ----------- | ------------------- | --------------------------------- |
| 400         | validation_error    | Invalid request parameters        |
| 400         | invalid_file_type   | Unsupported file type             |
| 401         | unauthorized        | Missing or invalid authentication |
| 403         | forbidden           | Insufficient permissions          |
| 404         | not_found           | Resource not found                |
| 404         | document_not_found  | Document ID not found             |
| 404         | session_not_found   | Session ID not found              |
| 413         | file_too_large      | File exceeds size limit           |
| 429         | rate_limit_exceeded | Too many requests                 |
| 500         | internal_error      | Server error                      |
| 503         | service_unavailable | External service down             |
| 503         | openai_rate_limit   | OpenAI API rate limit             |

### 7.3. Error Examples

**Validation Error:**

```json
{
  "error": "validation_error",
  "message": "Question must be at least 5 characters",
  "details": {
    "field": "question",
    "value": "Hi",
    "min_length": 5
  }
}
```

**Rate Limit Error:**

```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit of 100 requests per minute exceeded",
  "retry_after": 30,
  "limit": 100,
  "window": "1 minute"
}
```

---

## 8. Rate Limiting

### 8.1. Current Limits (v2.0)

| Endpoint               | Limit    | Window   |
| ---------------------- | -------- | -------- |
| POST /ask              | 100 req  | 1 minute |
| POST /api/upload/files | 20 req   | 1 hour   |
| GET /api/documents     | 200 req  | 1 minute |
| All endpoints          | 1000 req | 1 hour   |

### 8.2. Rate Limit Headers

**Response Headers:**

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1732449600
```

### 8.3. Rate Limit Response

**Status:** 429 Too Many Requests

```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Please try again later.",
  "retry_after": 30,
  "limit": 100,
  "window": "1 minute",
  "reset_at": "2025-11-24T10:01:00Z"
}
```

---

## 9. Webhooks (Planned)

### 9.1. Document Processing Webhook

**Trigger:** Document processing completed

**Payload:**

```json
{
  "event": "document.processing.completed",
  "document_id": "doc_12345",
  "status": "active",
  "total_chunks": 125,
  "processing_time_seconds": 42,
  "timestamp": "2025-11-24T10:00:42Z"
}
```

---

## Tài Liệu Liên Quan

- `01_System_Specification.md` - System overview
- `02_Use_Cases.md` - Use case scenarios
- `03_Database_Schema.md` - Database design
- `04_System_Architecture.md` - Architecture details
