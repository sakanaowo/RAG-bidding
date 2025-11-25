# System Design Documentation - RAG Bidding System

**Ngày tạo:** 24/11/2025  
**Phiên bản:** 2.0

---

## 📑 Mục Lục Tài Liệu

Bộ tài liệu thiết kế hệ thống RAG Bidding bao gồm 5 tài liệu chính:

### 1. [Đặc Tả Hệ Thống](./01_System_Specification.md)

**Mô tả:** Tổng quan về hệ thống, mục tiêu, yêu cầu phi chức năng  
**Nội dung chính:**

- Giới thiệu hệ thống RAG Bidding
- Tech stack (FastAPI, PostgreSQL, Redis, OpenAI)
- Kiến trúc tổng quan
- Yêu cầu phi chức năng (Performance, Scalability, Security)
- RAG Pipeline Modes (fast/balanced/quality/adaptive)
- Caching Strategy (3-tier: L1/L2/L3)
- Deployment & Future Enhancements

**Đọc trước tiên:** ✅ Bắt đầu từ tài liệu này

---

### 2. [Use Cases](./02_Use_Cases.md)

**Mô tả:** Chi tiết các use case và kịch bản sử dụng  
**Nội dung chính:**

- Actors (End User, Document Manager, Admin)
- Use Case Diagram
- Question Answering Use Cases (UC-1 đến UC-3)
- Document Management Use Cases (UC-7 đến UC-13)
- Chat Session Use Cases (UC-4 đến UC-6)
- System Administration Use Cases (UC-14 đến UC-18)
- Exception Scenarios
- Use Case Metrics
- Future Use Cases (planned)

**Đọc sau:** Tài liệu 1

---

### 3. [Database Schema Design](./03_Database_Schema.md)

**Mô tả:** Thiết kế database schema chi tiết  
**Nội dung chính:**

- Current Tables:
  - `documents` ⭐ PRIMARY TABLE
  - `langchain_pg_embedding` (vector storage)
  - `langchain_pg_collection` ⚠️ INTERNAL
- Proposed New Tables:
  - `users` (authentication)
  - `chat_sessions` & `chat_messages`
  - `query_logs` (analytics)
  - `document_upload_jobs`
  - `api_keys`, `feedback`, `document_versions`
- Complete Schema Diagram
- Indexes & Constraints
- Migration Plan (4 phases)
- Performance Optimization

**Đọc sau:** Tài liệu 1 hoặc 2

---

### 4. [System Architecture](./04_System_Architecture.md)

**Mô tả:** Kiến trúc chi tiết của hệ thống  
**Nội dung chính:**

- High-Level Architecture (6 layers)
- Component Details:
  - API Layer (FastAPI modules)
  - RAG Pipeline Layer (4 modes)
  - Embedding Layer (OpenAI)
  - Storage Layer (PostgreSQL + pgvector)
- Data Flow:
  - Query Processing Flow (14 steps, ~2.3s)
  - Document Upload Flow (14 steps, ~35s)
- RAG Pipeline Architecture
- Caching Architecture (3-tier)
- Deployment Architecture (dev + prod)
- Security Architecture (7 layers)
- Performance & Scalability

**Đọc sau:** Tài liệu 1

---

### 5. [API Specification](./05_API_Specification.md)

**Mô tả:** Đặc tả API endpoints chi tiết  
**Nội dung chính:**

- API Overview (base URL, versioning, headers)
- Authentication (planned JWT/API Key)
- Question Answering APIs:
  - `POST /ask` (simple & advanced)
- Document Management APIs:
  - `POST /api/upload/files`
  - `GET /api/upload/status/{id}`
  - `GET /api/documents`
  - `PATCH /api/documents/{id}`
  - `DELETE /api/documents/{id}`
- Chat Session APIs:
  - `POST /api/chat/sessions`
  - `POST /api/chat/sessions/{id}/messages`
  - `GET /api/chat/sessions/{id}`
- System APIs:
  - `GET /health`, `GET /stats`, `POST /clear_cache`
- Error Handling (error codes, examples)
- Rate Limiting (100 req/min)
- Webhooks (planned)

**Đọc cuối:** Sau khi hiểu system architecture

---

## 📊 Thống Kê Hệ Thống

### Current State (v2.0)

- **Database:** PostgreSQL 18 + pgvector 0.8.1
- **Total Documents:** 64
- **Total Chunks:** 7,892
- **Database Size:** 149 MB
- **Embedding Model:** OpenAI text-embedding-3-large (3,072-dim)
- **Reranker Model:** BAAI/bge-reranker-v2-m3
- **LLM:** GPT-4o-mini
- **Cache:** 3-tier (In-Memory LRU + Redis + PostgreSQL)

### Performance Metrics

| Metric                   | Current     | Target | Status          |
| ------------------------ | ----------- | ------ | --------------- |
| Query Latency (balanced) | ~2.3s       | <3s    | ✅              |
| Cache Hit Rate (L1)      | 40-60%      | >40%   | ✅              |
| Concurrent Users         | ~10         | 100+   | ⏳ Need pooling |
| Document Processing      | ~0.35s/page | <1s    | ✅              |

---

## 🗂️ Cấu Trúc Folder

```
documents/
└── System Design/
    ├── README.md                      # Tài liệu này
    ├── 01_System_Specification.md     # Đặc tả hệ thống
    ├── 02_Use_Cases.md                # Use cases
    ├── 03_Database_Schema.md          # Database schema
    ├── 04_System_Architecture.md      # Kiến trúc hệ thống
    └── 05_API_Specification.md        # API specification
```

---

## 🎯 Hướng Dẫn Đọc

### Cho Developer mới

1. Đọc `01_System_Specification.md` - Hiểu tổng quan
2. Đọc `02_Use_Cases.md` - Hiểu nghiệp vụ
3. Đọc `04_System_Architecture.md` - Hiểu kiến trúc
4. Đọc `05_API_Specification.md` - Implement features

### Cho Database Developer

1. Đọc `03_Database_Schema.md` - Schema design
2. Đọc `01_System_Specification.md` - Context
3. Đọc migration scripts trong `/scripts/migration/`

### Cho Product Manager

1. Đọc `01_System_Specification.md` - Features overview
2. Đọc `02_Use_Cases.md` - User scenarios
3. Đọc phần "Future Enhancements"

### Cho DevOps/SRE

1. Đọc `04_System_Architecture.md` - Deployment
2. Đọc `01_System_Specification.md` - Performance requirements
3. Đọc phần "Production Deployment Checklist"

---

## 🔄 Lịch Sử Cập Nhật

| Ngày       | Phiên bản | Thay đổi                          |
| ---------- | --------- | --------------------------------- |
| 2025-11-24 | 2.0       | Tạo mới bộ tài liệu System Design |

---

## 📞 Liên Hệ

**Project:** RAG Bidding System  
**Repository:** [RAG-bidding](https://github.com/sakanaowo/RAG-bidding)  
**Documentation:** `/documents/System Design/`

---

## 📚 Tài Liệu Tham Khảo Khác

- `/temp/database_schema_explained.txt` - Current database reference
- `/temp/system_architecture.txt` - Architecture reference
- `/temp/README.md` - Quick reference
- `/documents/technical/` - Technical documentation
- `/.github/copilot-instructions.md` - Development guide
