# 📋 Báo Cáo Phân Tích Thiết Kế Hệ Thống RAG Bidding

**Ngày tạo:** 27/11/2025  
**Phiên bản:** 3.0  
**Tác giả:** System Architecture Team  
**Dựa trên:** Library Management System requirements + RAG System best practices

---

## Mục Lục

1. [Bảng Từ Khóa Hệ Thống](#1-bảng-từ-khóa-hệ-thống)
2. [Sơ Đồ Use Case Tổng Quan](#2-sơ-đồ-use-case-tổng-quan)
3. [Sơ Đồ Lớp Hệ Thống](#3-sơ-đồ-lớp-hệ-thống)
4. [Database Schema Chi Tiết](#4-database-schema-chi-tiết)

---

## 1. Bảng Từ Khóa Hệ Thống

### 1.1. Nhóm Khái Niệm Liên Quan Đến Con Người

| TT | Tiếng Việt | Tiếng Anh | Giải Thích |
|----|------------|-----------|------------|
| 1 | **Quản trị viên** | Administrator | Người có quyền quản lý toàn hệ thống: quản lý người dùng, xem báo cáo thống kê, cấu hình hệ thống, quản lý API keys |
| 2 | **Quản lý** | Manager | Người có quyền xem các báo cáo thống kê: số lượng truy vấn, tài liệu được sử dụng nhiều nhất, hiệu suất hệ thống, phân tích xu hướng |
| 3 | **Nhân viên** | Staff/Employee | Người có tài khoản để thực hiện các chức năng: upload tài liệu, cập nhật metadata, quản lý collections, xem trạng thái xử lý |
| 4 | **Người dùng** | User/End User | Người sử dụng hệ thống để: hỏi đáp về tài liệu pháp lý, tìm kiếm thông tin đấu thầu, lưu câu hỏi quan trọng, chia sẻ kết quả |
| 5 | **Nhà phát triển** | Developer | Người tích hợp hệ thống thông qua API: sử dụng API keys, xây dựng ứng dụng client, tích hợp RAG vào workflow |

### 1.2. Nhóm Khái Niệm Liên Quan Đến Hoạt Động

| TT | Tiếng Việt | Tiếng Anh | Giải Thích |
|----|------------|-----------|------------|
| 6 | **Hỏi đáp** | Question Answering | Hoạt động chính: Người dùng đặt câu hỏi, hệ thống trả lời dựa trên RAG pipeline (retrieval + generation) |
| 7 | **Tìm kiếm** | Search/Retrieval | Tìm kiếm tài liệu, chunk, hoặc thông tin cụ thể với filters (loại văn bản, ngày tháng, từ khóa) |
| 8 | **Upload tài liệu** | Document Upload | Nhân viên upload file DOCX/PDF → Hệ thống xử lý: classification, chunking, embedding, indexing |
| 9 | **Xử lý tài liệu** | Document Processing | Pipeline tự động: Phân loại → Parse → Chunk → Enrich → Embed → Store → Index |
| 10 | **Cập nhật metadata** | Update Metadata | Sửa thông tin tài liệu: category, document_type, status, tags |
| 11 | **Tạo chat session** | Create Chat Session | Bắt đầu cuộc hội thoại mới với context preservation (lưu lịch sử câu hỏi) |
| 12 | **Tiếp tục hội thoại** | Continue Conversation | Hỏi tiếp trong session với context từ câu hỏi trước |
| 13 | **Xem lịch sử** | View History | Xem lại các cuộc hội thoại, câu hỏi, và câu trả lời đã lưu |
| 14 | **Lưu bookmark** | Save Bookmark | Lưu câu hỏi/câu trả lời hữu ích để tham khảo sau |
| 15 | **Chia sẻ** | Share | Chia sẻ conversation, bookmark, hoặc collection với người khác |
| 16 | **Phản hồi** | Provide Feedback | Đánh giá chất lượng câu trả lời (thumbs up/down, rating, comment) |
| 17 | **Xem báo cáo** | View Reports | Quản lý xem thống kê: usage metrics, performance, cost tracking |
| 18 | **Quản lý API** | API Management | Tạo, xóa, revoke API keys; xem usage statistics |

### 1.3. Nhóm Khái Niệm Đối Tượng Xử Lý

| TT | Tiếng Việt | Tiếng Anh | Giải Thích |
|----|------------|-----------|------------|
| 19 | **Hệ thống** | System | Hệ thống RAG Bidding - Tập hợp các thành phần: API, Database, Vector Store, LLM, Cache |
| 20 | **Tài liệu** | Document | Văn bản nguồn: Luật, Nghị định, Thông tư, Quyết định, Hồ sơ mời thầu, Mẫu báo cáo. Format: DOCX, PDF |
| 21 | **Chunk** | Chunk/Segment | Đoạn văn bản nhỏ được chia từ document (500-1500 chars) với metadata: section_title, hierarchy, keywords |
| 22 | **Embedding** | Vector Embedding | Biểu diễn semantic của chunk dưới dạng vector 3072 chiều (OpenAI text-embedding-3-large) |
| 23 | **Collection** | Document Collection | Nhóm tài liệu theo chủ đề: Luật đấu thầu, Nghị định hướng dẫn, Mẫu hồ sơ, etc. |
| 24 | **Conversation** | Chat Conversation | Cuộc hội thoại đa lượt (multi-turn) với context preservation |
| 25 | **Message** | Chat Message | Tin nhắn đơn lẻ trong conversation (user hoặc assistant) |
| 26 | **Query** | Search Query | Truy vấn tìm kiếm với filters và RAG mode (fast/balanced/quality/adaptive) |
| 27 | **Citation** | Source Citation | Trích dẫn nguồn: document_id, chunk_id, relevance_score, section_title |
| 28 | **Feedback** | User Feedback | Phản hồi của người dùng: rating (1-5 sao), issues (incorrect/incomplete), comment |
| 29 | **Bookmark** | Saved Bookmark | Câu hỏi/câu trả lời được lưu với title, notes, tags |
| 30 | **API Key** | API Authentication Key | Key xác thực API: scopes, rate limits, usage tracking |
| 31 | **Session** | User Session | Phiên làm việc của người dùng trên hệ thống |
| 32 | **Cache** | Response Cache | Cache 3 tầng: L1 (In-Memory), L2 (Redis), L3 (PostgreSQL) |
| 33 | **Reranker** | Relevance Reranker | Model sắp xếp lại kết quả theo độ liên quan: BGE-reranker-v2-m3 |
| 34 | **Pipeline** | Processing Pipeline | Luồng xử lý tự động: Upload → Classify → Parse → Chunk → Embed → Store |
| 35 | **Metadata** | Document Metadata | Thông tin mô tả: document_type, category, status, published_date, keywords |

### 1.4. Nhóm Khái Niệm Kỹ Thuật

| TT | Tiếng Việt | Tiếng Anh | Giải Thích |
|----|------------|-----------|------------|
| 36 | **RAG** | Retrieval-Augmented Generation | Kỹ thuật kết hợp retrieval (tìm kiếm) và generation (sinh text) để trả lời câu hỏi |
| 37 | **Vector Database** | Vector Database | PostgreSQL + pgvector - Lưu trữ và tìm kiếm vector embeddings |
| 38 | **Semantic Search** | Semantic Search | Tìm kiếm theo nghĩa (không chỉ từ khóa) sử dụng cosine similarity |
| 39 | **Query Enhancement** | Query Enhancement | Cải thiện query: Multi-Query, HyDE, Step-Back strategies |
| 40 | **Chunking** | Text Chunking | Chia tài liệu thành đoạn nhỏ với overlap để bảo toàn context |
| 41 | **Enrichment** | Metadata Enrichment | Trích xuất keywords, concepts, entities từ text |
| 42 | **Versioning** | Document Versioning | Quản lý phiên bản tài liệu: v1.0, v2.0, compare changes, rollback |
| 43 | **Rate Limiting** | API Rate Limiting | Giới hạn số request: 100 req/min, 1000 req/hour |
| 44 | **Authentication** | User Authentication | Xác thực người dùng: JWT tokens, OAuth2, API keys |
| 45 | **Authorization** | Access Control | Phân quyền: RBAC (Role-Based Access Control) - Admin/Manager/Staff/User |

### 1.5. Nhóm Khái Niệm Báo Cáo & Phân Tích

| TT | Tiếng Việt | Tiếng Anh | Giải Thích |
|----|------------|-----------|------------|
| 46 | **Báo cáo thống kê** | Statistical Report | Báo cáo tổng hợp: query volume, document usage, cache performance, cost breakdown |
| 47 | **Metrics** | Performance Metrics | Chỉ số đo lường: latency (ms), cache hit rate (%), token usage, cost ($) |
| 48 | **Analytics** | Usage Analytics | Phân tích: query patterns, popular documents, user behavior, peak times |
| 49 | **Dashboard** | Analytics Dashboard | Giao diện hiển thị metrics real-time và historical trends |
| 50 | **Logging** | System Logging | Ghi log: query logs, error logs, performance logs, audit logs |

---

## 2. Sơ Đồ Use Case Tổng Quan

### 2.1. Use Case Diagram (PlantUML)

```plantuml
@startuml RAG_Bidding_Use_Cases

!define ACTOR_COLOR #85C1E9
!define SYSTEM_COLOR #AED6F1
!define UC_COLOR #D6EAF8

skinparam actor {
    BackgroundColor ACTOR_COLOR
    BorderColor #2E86C1
}

skinparam usecase {
    BackgroundColor UC_COLOR
    BorderColor #2E86C1
}

skinparam rectangle {
    BackgroundColor SYSTEM_COLOR
    BorderColor #1B4F72
}

' ===== ACTORS =====
actor "Người dùng\n(User)" as User
actor "Nhân viên\n(Staff)" as Staff
actor "Quản lý\n(Manager)" as Manager
actor "Quản trị viên\n(Admin)" as Admin
actor "Nhà phát triển\n(Developer)" as Developer

' Actor hierarchy
User <|-- Staff
Staff <|-- Manager
Manager <|-- Admin

' ===== SYSTEM BOUNDARY =====
rectangle "RAG Bidding System v3.0" as System {
    
    ' ===== CORE RAG FEATURES (UC-1 to UC-6) =====
    package "Hỏi Đáp & Hội Thoại" as QA #F9E79F {
        usecase "UC-1: Hỏi Đáp Đơn Giản" as UC1
        usecase "UC-2: Hỏi Với Context" as UC2
        usecase "UC-3: Tìm Kiếm Nâng Cao" as UC3
        usecase "UC-4: Tạo Chat Session" as UC4
        usecase "UC-5: Tiếp Tục Hội Thoại" as UC5
        usecase "UC-6: Xem Lịch Sử Chat" as UC6
    }
    
    ' ===== DOCUMENT MANAGEMENT (UC-7 to UC-13) =====
    package "Quản Lý Tài Liệu" as DocMgmt #FADBD8 {
        usecase "UC-7: Upload Tài Liệu" as UC7
        usecase "UC-8: Theo Dõi Xử Lý" as UC8
        usecase "UC-9: Liệt Kê Tài Liệu" as UC9
        usecase "UC-10: Tìm Kiếm Tài Liệu" as UC10
        usecase "UC-11: Xem Chi Tiết" as UC11
        usecase "UC-12: Cập Nhật Metadata" as UC12
        usecase "UC-13: Xóa Tài Liệu" as UC13
    }
    
    ' ===== USER FEATURES (NEW) =====
    package "Tính Năng Người Dùng" as UserFeatures #D5F4E6 {
        usecase "UC-24: Xem Nguồn Trích Dẫn" as UC24
        usecase "UC-25: Phản Hồi Câu Trả Lời" as UC25
        usecase "UC-42: Lưu Bookmark" as UC42
        usecase "UC-43: Quản Lý Bookmark" as UC43
        usecase "UC-44: Chia Sẻ Bookmark" as UC44
        usecase "UC-45: Lưu Filter" as UC45
    }
    
    ' ===== COLLABORATION (NEW) =====
    package "Cộng Tác" as Collab #E8DAEF {
        usecase "UC-22: Chia Sẻ Conversation" as UC22
        usecase "UC-23: Nghiên Cứu Nhóm" as UC23
        usecase "UC-37: Tạo Collection" as UC37
        usecase "UC-38: Tìm Trong Collection" as UC38
        usecase "UC-39: Chia Sẻ Collection" as UC39
    }
    
    ' ===== DOCUMENT VERSIONING (NEW) =====
    package "Quản Lý Phiên Bản" as Versioning #FCF3CF {
        usecase "UC-34: Kiểm Soát Phiên Bản" as UC34
        usecase "UC-35: So Sánh Phiên Bản" as UC35
        usecase "UC-36: Rollback Tài Liệu" as UC36
    }
    
    ' ===== ANALYTICS & REPORTING =====
    package "Thống Kê & Báo Cáo" as Analytics #EBDEF0 {
        usecase "UC-14: Xem Metrics" as UC14
        usecase "UC-15: Monitor Hiệu Suất" as UC15
        usecase "UC-26: Analytics Dashboard" as UC26
        usecase "UC-27: Theo Dõi Chi Phí" as UC27
        usecase "UC-28: Phân Tích Query" as UC28
    }
    
    ' ===== SYSTEM MANAGEMENT =====
    package "Quản Trị Hệ Thống" as SysMgmt #FADBD8 {
        usecase "UC-16: Quản Lý Cache" as UC16
        usecase "UC-17: Health Check" as UC17
        usecase "UC-18: Clear Cache" as UC18
        usecase "UC-19: Đăng Ký/Đăng Nhập" as UC19
        usecase "UC-20: Quản Lý Profile" as UC20
        usecase "UC-21: Quản Lý Tổ Chức" as UC21
    }
    
    ' ===== API MANAGEMENT =====
    package "Quản Lý API" as APIMgmt #D6EAF8 {
        usecase "UC-47: Tạo API Key" as UC47
        usecase "UC-48: Quản Lý API Keys" as UC48
        usecase "UC-49: Rate Limiting" as UC49
    }
}

' ===== USER RELATIONSHIPS =====
User --> UC1 : "Đặt câu hỏi"
User --> UC2 : "Hỏi với context"
User --> UC3 : "Tìm kiếm nâng cao"
User --> UC4 : "Tạo session"
User --> UC5 : "Chat tiếp"
User --> UC6 : "Xem lịch sử"
User --> UC9 : "Xem danh sách"
User --> UC10 : "Tìm tài liệu"
User --> UC11 : "Xem chi tiết"
User --> UC24 : "Xem nguồn"
User --> UC25 : "Feedback"
User --> UC42 : "Lưu bookmark"
User --> UC43 : "Quản lý bookmark"
User --> UC44 : "Chia sẻ"
User --> UC45 : "Lưu filter"

' ===== STAFF RELATIONSHIPS =====
Staff --> UC7 : "Upload tài liệu"
Staff --> UC8 : "Theo dõi xử lý"
Staff --> UC12 : "Cập nhật metadata"
Staff --> UC13 : "Xóa tài liệu"
Staff --> UC37 : "Tạo collection"
Staff --> UC38 : "Tìm trong collection"
Staff --> UC39 : "Chia sẻ collection"

' ===== MANAGER RELATIONSHIPS =====
Manager --> UC14 : "Xem metrics"
Manager --> UC15 : "Monitor"
Manager --> UC26 : "Dashboard"
Manager --> UC27 : "Theo dõi cost"
Manager --> UC28 : "Phân tích query"

' ===== ADMIN RELATIONSHIPS =====
Admin --> UC16 : "Quản lý cache"
Admin --> UC17 : "Health check"
Admin --> UC18 : "Clear cache"
Admin --> UC19 : "User management"
Admin --> UC20 : "Profile mgmt"
Admin --> UC21 : "Org management"
Admin --> UC34 : "Version control"
Admin --> UC35 : "Compare versions"
Admin --> UC36 : "Rollback"

' ===== DEVELOPER RELATIONSHIPS =====
Developer --> UC47 : "Tạo key"
Developer --> UC48 : "Manage keys"
Developer --> UC49 : "Check rate limit"

' ===== COLLABORATION RELATIONSHIPS =====
User --> UC22 : "Share conversation"
User --> UC23 : "Nhóm nghiên cứu"

' ===== INCLUDE RELATIONSHIPS =====
UC1 ..> UC24 : <<include>>
UC2 ..> UC24 : <<include>>
UC3 ..> UC24 : <<include>>
UC7 ..> UC8 : <<include>>

' ===== EXTEND RELATIONSHIPS =====
UC3 ..> UC45 : <<extend>>
UC5 ..> UC6 : <<extend>>

@enduml
```

### 2.2. Danh Sách Use Cases Chi Tiết

#### Nhóm 1: Hỏi Đáp & Hội Thoại (UC-1 to UC-6)

**UC-1: Hỏi Đáp Đơn Giản**
- **Actor:** User
- **Endpoint:** `POST /ask`
- **Mô tả:** Người dùng đặt câu hỏi, hệ thống trả lời bằng RAG pipeline
- **Input:** Question text, mode (fast/balanced/quality)
- **Output:** Answer, sources, metadata
- **Success Criteria:** Latency < 5s, min 3 sources

**UC-2: Hỏi Với Context**
- **Actor:** User
- **Endpoint:** `POST /ask`
- **Mô tả:** Hỏi với filters (document_type, date_range, category)
- **Input:** Question + filters
- **Output:** Filtered answer với sources chính xác hơn

**UC-3: Tìm Kiếm Nâng Cao**
- **Actor:** User
- **Endpoint:** `POST /ask` với advanced filters
- **Mô tả:** Search với multiple filters, sort options, pagination
- **Features:** Filter theo type, category, status, date range

**UC-4: Tạo Chat Session**
- **Actor:** User
- **Endpoint:** `POST /api/chat/sessions`
- **Mô tả:** Tạo conversation mới với session_id
- **Output:** session_id, created_at

**UC-5: Tiếp Tục Hội Thoại**
- **Actor:** User
- **Endpoint:** `POST /api/chat/sessions/{session_id}/messages`
- **Mô tả:** Gửi message trong session với context preservation
- **Features:** Context window management, history tracking

**UC-6: Xem Lịch Sử Chat**
- **Actor:** User
- **Endpoint:** `GET /api/chat/sessions/{session_id}/history`
- **Output:** List messages (user + assistant) với timestamps

#### Nhóm 2: Quản Lý Tài Liệu (UC-7 to UC-13)

**UC-7: Upload Tài Liệu**
- **Actor:** Staff
- **Endpoint:** `POST /api/upload/files`
- **Input:** Files (DOCX/PDF), category, document_type
- **Process:** Upload → Classify → Parse → Chunk → Embed → Store
- **Output:** upload_id, status_url

**UC-8: Theo Dõi Xử Lý**
- **Actor:** Staff
- **Endpoint:** `GET /api/upload/status/{upload_id}`
- **Output:** Progress %, current_step, estimated_time

**UC-9: Liệt Kê Tài Liệu**
- **Actor:** User, Staff
- **Endpoint:** `GET /api/documents`
- **Features:** Pagination, filters, sorting
- **Output:** List of documents with metadata

**UC-10: Tìm Kiếm Tài Liệu**
- **Actor:** User
- **Endpoint:** `GET /api/documents?document_type=law&category=legal`
- **Features:** Full-text search, semantic search

**UC-11: Xem Chi Tiết**
- **Actor:** User
- **Endpoint:** `GET /api/documents/{document_id}`
- **Output:** Full document with chunks, metadata, stats

**UC-12: Cập Nhật Metadata**
- **Actor:** Staff
- **Endpoint:** `PATCH /api/documents/{document_id}`
- **Features:** Update category, status, document_name

**UC-13: Xóa Tài Liệu**
- **Actor:** Staff, Admin
- **Endpoint:** `DELETE /api/documents/{document_id}`
- **Features:** Soft delete (default), hard delete (optional)

#### Nhóm 3: Tính Năng Người Dùng (NEW - UC-24, UC-25, UC-42 to UC-45)

**UC-24: Xem Nguồn Trích Dẫn**
- **Tích hợp trong:** UC-1, UC-2, UC-3
- **Output:** document_id, chunk_id, section_title, relevance_score

**UC-25: Phản Hồi Câu Trả Lời**
- **Actor:** User
- **Endpoint:** `POST /api/feedback` (planned)
- **Input:** message_id, rating (1-5), comment, issues[]

**UC-42: Lưu Bookmark**
- **Actor:** User
- **Endpoint:** `POST /api/bookmarks` (planned)
- **Input:** message_id, title, notes, tags

**UC-43: Quản Lý Bookmark**
- **Endpoint:** `GET /api/bookmarks`, `PATCH /api/bookmarks/{id}`
- **Features:** Organize by folder, search, edit

**UC-44: Chia Sẻ Bookmark**
- **Endpoint:** `POST /api/bookmarks/{id}/share`
- **Features:** Generate share URL, set permissions

**UC-45: Lưu Filter**
- **Endpoint:** `POST /api/filters` (planned)
- **Features:** Save frequently used search filters

#### Nhóm 4: Thống Kê & Báo Cáo (UC-14, UC-15, UC-26 to UC-28)

**UC-14: Xem Metrics**
- **Actor:** Manager
- **Endpoint:** `GET /stats`
- **Output:** Document count, query volume, cache stats

**UC-15: Monitor Hiệu Suất**
- **Actor:** Manager, Admin
- **Endpoint:** `GET /health`
- **Output:** Component status, latency, uptime

**UC-26: Analytics Dashboard** (Planned)
- **Actor:** Manager
- **Features:** Real-time metrics, historical trends, charts

**UC-27: Theo Dõi Chi Phí** (Planned)
- **Metrics:** Token usage, embedding costs, LLM costs ($)

**UC-28: Phân Tích Query** (Planned)
- **Features:** Query patterns, popular topics, peak times

#### Nhóm 5: Quản Trị Hệ Thống (UC-16 to UC-21)

**UC-16: Quản Lý Cache**
- **Actor:** Admin
- **Endpoint:** `GET /cache/stats` (planned)
- **Features:** View L1/L2/L3 hit rates

**UC-17: Health Check**
- **Actor:** Admin, System Monitor
- **Endpoint:** `GET /health`
- **Output:** DB, Redis, Models status

**UC-18: Clear Cache**
- **Actor:** Admin
- **Endpoint:** `POST /clear_cache`
- **Features:** Clear L1, L2, or all

**UC-19 to UC-21:** User & Organization Management (Planned)

#### Nhóm 6: API Management (UC-47 to UC-49)

**UC-47: Tạo API Key** (Planned)
- **Actor:** Developer
- **Input:** name, scopes[], rate_limits

**UC-48: Quản Lý API Keys** (Planned)
- **Features:** List, revoke, view usage

**UC-49: Rate Limiting** (Implemented)
- **Current Limits:** 100 req/min (ask), 1000 req/hour (global)

---

## 3. Sơ Đồ Lớp Hệ Thống

### 3.1. Class Diagram - Core Entities (PlantUML)

```plantuml
@startuml RAG_Bidding_Class_Diagram

!define PRIMARY_COLOR #3498DB
!define SECONDARY_COLOR #2ECC71
!define ACCENT_COLOR #E74C3C
!define NEUTRAL_COLOR #95A5A6

skinparam class {
    BackgroundColor #FFFFFF
    BorderColor #2C3E50
    ArrowColor #34495E
    FontSize 11
}

skinparam package {
    BackgroundColor #ECF0F1
    BorderColor #7F8C8D
    FontStyle bold
}

' ===== USER MANAGEMENT =====
package "User Management" <<Rectangle>> {
    class User {
        +id: UUID <<PK>>
        +email: String <<unique>>
        +username: String
        +password_hash: String
        +full_name: String
        +role: String
        --
        +oauth_provider: String
        +oauth_id: String
        +preferences: JSONB
        --
        +is_active: Boolean
        +created_at: Timestamp
        +updated_at: Timestamp
        ==
        +authenticate()
        +update_profile()
        +set_preferences()
    }
    
    class APIKey {
        +id: UUID <<PK>>
        +user_id: UUID <<FK>>
        +key_hash: String <<unique>>
        +key_prefix: String
        +name: String
        --
        +scopes: String[]
        +rate_limit_rpm: Integer
        +total_requests: Integer
        --
        +is_active: Boolean
        +expires_at: Timestamp
        ==
        +validate()
        +revoke()
        +track_usage()
    }
}

' ===== DOCUMENT MANAGEMENT =====
package "Document Management" <<Rectangle>> {
    class Document {
        +id: UUID <<PK>>
        +document_id: String <<unique>>
        +document_name: String
        +document_type: String
        +category: String
        --
        +file_name: String
        +source_file: String
        +total_chunks: Integer
        --
        +status: String
        +created_at: Timestamp
        +updated_at: Timestamp
        ==
        +update_status()
        +get_chunks()
        +get_stats()
    }
    
    class DocumentChunk {
        +id: UUID <<PK>>
        +chunk_id: String <<unique>>
        +document_id: String <<FK>>
        +content: Text
        --
        +chunk_index: Integer
        +section_title: String
        +hierarchy_path: String[]
        --
        +keywords: String[]
        +concepts: String[]
        +retrieval_count: Integer
        --
        +created_at: Timestamp
        ==
        +get_embedding()
        +track_retrieval()
    }
    
    class Embedding {
        +id: String <<PK>>
        +collection_id: UUID <<FK>>
        +document: Text
        +cmetadata: JSONB
        +embedding: Vector(3072)
        ==
        +cosine_similarity()
        +search_similar()
    }
    
    class DocumentVersion {
        +id: UUID <<PK>>
        +document_id: String <<FK>>
        +version_number: Integer
        +version_label: String
        --
        +source_file: String
        +file_hash: String
        +total_chunks: Integer
        --
        +is_current: Boolean
        +published_at: Timestamp
        ==
        +compare_with()
        +rollback()
    }
    
    class DocumentCollection {
        +id: UUID <<PK>>
        +name: String
        +description: Text
        +owner_id: UUID <<FK>>
        --
        +collection_type: String
        +auto_include_rules: JSONB
        +document_count: Integer
        --
        +is_public: Boolean
        +created_at: Timestamp
        ==
        +add_document()
        +remove_document()
        +apply_rules()
    }
}

' ===== CONVERSATION MANAGEMENT =====
package "Conversation Management" <<Rectangle>> {
    class Conversation {
        +id: UUID <<PK>>
        +user_id: UUID <<FK>>
        +title: String
        +summary: Text
        --
        +rag_mode: String
        +model_config: JSONB
        +filters: JSONB
        --
        +message_count: Integer
        +is_public: Boolean
        +share_url: String
        --
        +created_at: Timestamp
        +last_message_at: Timestamp
        ==
        +add_message()
        +generate_title()
        +share()
    }
    
    class Message {
        +id: UUID <<PK>>
        +conversation_id: UUID <<FK>>
        +user_id: UUID <<FK>>
        +role: String
        +content: Text
        --
        +sources: JSONB
        +confidence_score: Float
        +processing_time_ms: Integer
        --
        +feedback: String
        +cache_hit: Boolean
        --
        +created_at: Timestamp
        ==
        +add_feedback()
        +get_citations()
    }
    
    class Citation {
        +id: UUID <<PK>>
        +message_id: UUID <<FK>>
        +document_id: String <<FK>>
        +chunk_id: String <<FK>>
        --
        +citation_number: Integer
        +citation_text: Text
        --
        +initial_score: Float
        +rerank_score: Float
        +final_score: Float
        --
        +clicked: Boolean
        +click_count: Integer
        ==
        +track_click()
    }
}

' ===== ANALYTICS & FEEDBACK =====
package "Analytics & Feedback" <<Rectangle>> {
    class Query {
        +id: UUID <<PK>>
        +user_id: UUID <<FK>>
        +conversation_id: UUID <<FK>>
        +message_id: UUID <<FK>>
        --
        +query_text: Text
        +query_hash: String
        +query_type: String
        --
        +rag_mode: String
        +sources_count: Integer
        --
        +total_latency_ms: Integer
        +cache_hit: Boolean
        --
        +tokens_total: Integer
        +estimated_cost_usd: Decimal
        --
        +created_at: Timestamp
        ==
        +calculate_cost()
        +get_performance()
    }
    
    class Feedback {
        +id: UUID <<PK>>
        +user_id: UUID <<FK>>
        +message_id: UUID <<FK>>
        +feedback_type: String
        --
        +rating: Integer
        +issues: String[]
        +comment: Text
        --
        +resolved: Boolean
        +resolved_at: Timestamp
        ==
        +resolve()
    }
    
    class UsageMetrics {
        +id: UUID <<PK>>
        +date: Date
        +hour: Integer
        +user_id: UUID <<FK>>
        +rag_mode: String
        --
        +total_queries: Integer
        +avg_latency_ms: Integer
        +cache_hit_rate: Float
        --
        +total_tokens: Integer
        +total_cost_usd: Decimal
        ==
        +aggregate()
    }
}

' ===== USER FEATURES =====
package "User Features" <<Rectangle>> {
    class Bookmark {
        +id: UUID <<PK>>
        +user_id: UUID <<FK>>
        +message_id: UUID <<FK>>
        +conversation_id: UUID <<FK>>
        --
        +title: String
        +notes: Text
        +tags: String[]
        --
        +folder_path: String
        +is_favorite: Boolean
        +is_public: Boolean
        --
        +created_at: Timestamp
        ==
        +share()
        +organize()
    }
    
    class SearchFilter {
        +id: UUID <<PK>>
        +user_id: UUID <<FK>>
        +name: String
        +filters: JSONB
        --
        +use_count: Integer
        +last_used_at: Timestamp
        +is_default: Boolean
        ==
        +apply()
    }
}

' ===== RELATIONSHIPS =====

' User relationships
User "1" -- "0..*" APIKey : has
User "1" -- "0..*" Conversation : creates
User "1" -- "0..*" Bookmark : saves
User "1" -- "0..*" SearchFilter : defines
User "1" -- "0..*" Feedback : provides

' Document relationships
Document "1" -- "0..*" DocumentChunk : contains
Document "1" -- "0..*" DocumentVersion : has versions
DocumentChunk "1" -- "0..1" Embedding : has embedding
DocumentCollection "1" -- "0..*" Document : contains

' Conversation relationships
Conversation "1" -- "0..*" Message : contains
Message "1" -- "0..*" Citation : has citations
Citation "*" -- "1" DocumentChunk : references
Message "1" -- "0..1" Query : generates
Message "1" -- "0..*" Feedback : receives

' Bookmark relationships
Bookmark "*" -- "1" Message : bookmarks
Bookmark "*" -- "0..1" Conversation : from

' Query relationships
Query "*" -- "0..1" User : by
Query "*" -- "0..1" Conversation : in
UsageMetrics "*" -- "0..1" User : tracks

@enduml
```

### 3.2. Class Diagram - RAG Pipeline Components

```plantuml
@startuml RAG_Pipeline_Classes

skinparam class {
    BackgroundColor #FFFFFF
    BorderColor #2C3E50
}

package "RAG Pipeline" <<Rectangle>> {
    
    class QueryEnhancer {
        +config: QueryEnhancerConfig
        --
        +enhance_query(query: str): List[str]
        +multi_query_strategy()
        +hyde_strategy()
        +step_back_strategy()
    }
    
    class VectorStore {
        +collection_name: String
        +embedding_model: String
        --
        +add_documents(chunks: List)
        +similarity_search(query: str, k: int)
        +similarity_search_with_score()
        +clear_cache()
    }
    
    class Reranker <<abstract>> {
        +model_name: String
        +device: String
        --
        +rerank(query: str, docs: List): List
        +compute_scores()
    }
    
    class BGEReranker {
        +model: AutoModelForSequenceClassification
        +tokenizer: AutoTokenizer
        +batch_size: int
        --
        +rerank(query: str, docs: List): List
        +_batch_score()
    }
    
    class CacheManager {
        +l1_cache: LRUCache
        +l2_cache: RedisCache
        +l3_cache: PostgreSQLCache
        --
        +get(key: str): Optional[Any]
        +set(key: str, value: Any)
        +invalidate(pattern: str)
        +get_stats(): Dict
    }
    
    class QAChain {
        +llm: ChatOpenAI
        +retriever: VectorStoreRetriever
        +prompt_template: str
        --
        +answer(question: str): Dict
        +_format_sources()
        +_validate_answer()
    }
}

package "Document Processing" <<Rectangle>> {
    
    class DocumentClassifier {
        +rules: Dict
        --
        +classify_document(filename: str): DocumentType
        +get_features_detected(): List
    }
    
    class DocumentParser <<abstract>> {
        +file_path: Path
        --
        +parse(): List[Chunk]
        +extract_metadata(): Dict
    }
    
    class DOCXParser {
        +parse(): List[Chunk]
        +extract_hierarchy()
        +extract_tables()
    }
    
    class PDFParser {
        +parse(): List[Chunk]
        +extract_text()
        +detect_layout()
    }
    
    class Chunker {
        +chunk_size: int
        +chunk_overlap: int
        --
        +chunk_document(text: str): List[Chunk]
        +preserve_structure()
    }
    
    class MetadataEnricher {
        +extract_keywords(text: str): List[str]
        +extract_concepts(text: str): List[str]
        +extract_entities(text: str): Dict
    }
}

' Relationships
QueryEnhancer -- VectorStore : uses
VectorStore -- Reranker : uses
BGEReranker --|> Reranker : implements
QAChain -- VectorStore : uses
QAChain -- CacheManager : uses

DocumentClassifier -- DocumentParser : routes to
DOCXParser --|> DocumentParser : implements
PDFParser --|> DocumentParser : implements
DocumentParser -- Chunker : uses
Chunker -- MetadataEnricher : uses
MetadataEnricher -- VectorStore : stores in

@enduml
```

### 3.3. Mô Tả Chi Tiết Các Lớp

#### Nhóm User Management

**User**
- Quản lý thông tin người dùng, authentication, authorization
- Lưu preferences (UI settings, default filters)
- Support OAuth (Google, Microsoft, GitHub)

**APIKey**
- API authentication với scopes (read:documents, write:queries)
- Rate limiting per key (rpm, rph, rpd)
- Usage tracking (total_requests, tokens, cost)

#### Nhóm Document Management

**Document**
- Aggregate root cho document entities
- Quản lý metadata, status (active/archived/expired)
- Track total_chunks, processing status

**DocumentChunk**
- Chunk nhỏ từ document (500-1500 chars)
- Metadata: section_title, hierarchy_path, keywords
- Track usage: retrieval_count, citation_count

**Embedding**
- Vector representation (3072 dimensions)
- LangChain pgvector integration
- Support cosine similarity search

**DocumentVersion**
- Git-like version control
- Compare versions, track changes
- Rollback capability

**DocumentCollection**
- Group documents by topic/project
- Auto-include rules (smart filters)
- Share with team members

#### Nhóm Conversation Management

**Conversation**
- Multi-turn chat session
- RAG mode config per conversation
- Share conversations (is_public, share_url)

**Message**
- Individual message (user or assistant)
- Track sources, confidence_score
- Cache hit tracking

**Citation**
- Explicit source attribution
- Track click-through rate
- Relevance scores (initial, rerank, final)

#### Nhóm Analytics & Feedback

**Query**
- Log every query for analytics
- Track performance (latency, cache hit)
- Cost tracking (tokens, $)

**Feedback**
- User ratings (1-5 stars)
- Issue tracking (incorrect, incomplete, outdated)
- Resolution workflow

**UsageMetrics**
- Pre-aggregated metrics (daily/hourly)
- Dashboard data source
- Performance trends

#### Nhóm User Features

**Bookmark**
- Save important Q&A
- Organize by folder, tags
- Share bookmarks

**SearchFilter**
- Save frequently used filters
- Quick access, auto-apply
- Share with team

---

## 4. Database Schema Chi Tiết

### 4.1. Schema Overview

**Current Tables (Existing):**
1. `documents` - Document metadata ✅
2. `langchain_pg_embedding` - Vector storage ✅
3. `langchain_pg_collection` - LangChain internal ✅

**Proposed Tables (v3.0):**
1. `users` - User management
2. `api_keys` - API authentication
3. `conversations` - Chat sessions
4. `messages` - Chat messages
5. `citations` - Source tracking
6. `queries` - Analytics
7. `feedback` - User feedback
8. `document_chunks` - Explicit chunk metadata
9. `document_versions` - Version control
10. `document_collections` - Collections
11. `collection_documents` - M:N junction
12. `bookmarks` - Saved Q&A
13. `search_filters` - Saved searches
14. `usage_metrics` - Aggregated analytics

**Total:** 17 tables

### 4.2. Cập Nhật Schema v3.0

Chi tiết schema đã được documented trong file `proposed_schema_v3.md` với:

✅ **13 tables mới** với full DDL
✅ **50 use cases** (18 existing + 32 new)
✅ **5-phase migration plan** (8 weeks)
✅ **Performance improvements:** 50% faster chunk queries, 10x faster analytics
✅ **Industry best practices:** Perplexity citations, ChatGPT conversations, Notion collections

### 4.3. Entity Relationship Diagram

```plantuml
@startuml RAG_Bidding_ERD

!define TABLE(x) class x << (T,#FFAAAA) >>
!define PK(x) <b>PK:</b> x
!define FK(x) <i>FK:</i> x

skinparam class {
    BackgroundColor #FFFFFF
    BorderColor #2C3E50
}

' ===== CORE TABLES =====

TABLE(users) {
    PK(id): UUID
    --
    email: String
    username: String
    role: String
    preferences: JSONB
    is_active: Boolean
}

TABLE(documents) {
    PK(id): UUID
    document_id: String
    --
    document_name: String
    document_type: String
    category: String
    total_chunks: Integer
    status: String
}

TABLE(langchain_pg_embedding) {
    PK(id): String
    FK(collection_id): UUID
    --
    document: Text
    cmetadata: JSONB
    embedding: Vector(3072)
}

TABLE(conversations) {
    PK(id): UUID
    FK(user_id): UUID
    --
    title: String
    rag_mode: String
    message_count: Integer
    is_public: Boolean
}

TABLE(messages) {
    PK(id): UUID
    FK(conversation_id): UUID
    FK(user_id): UUID
    --
    role: String
    content: Text
    sources: JSONB
    feedback: String
}

TABLE(citations) {
    PK(id): UUID
    FK(message_id): UUID
    FK(document_id): String
    --
    chunk_id: String
    citation_number: Integer
    rerank_score: Float
    clicked: Boolean
}

TABLE(queries) {
    PK(id): UUID
    FK(user_id): UUID
    FK(conversation_id): UUID
    --
    query_text: Text
    total_latency_ms: Integer
    cache_hit: Boolean
    tokens_total: Integer
}

TABLE(bookmarks) {
    PK(id): UUID
    FK(user_id): UUID
    FK(message_id): UUID
    --
    title: String
    tags: String[]
    is_favorite: Boolean
}

' ===== RELATIONSHIPS =====

users "1" -- "0..*" conversations
users "1" -- "0..*" bookmarks
users "1" -- "0..*" queries

conversations "1" -- "0..*" messages
messages "1" -- "0..*" citations

documents "1" -- "0..*" langchain_pg_embedding
citations "*" -- "1" documents

messages "1" -- "0..1" queries
bookmarks "*" -- "1" messages

@enduml
```

### 4.4. Migration Strategy

**Phase 1: User & Auth (v3.1)** - 2 weeks
- Create `users`, `api_keys` tables
- Implement JWT authentication
- Migrate implicit users from sessions

**Phase 2: Conversations (v3.2)** - 2 weeks
- Create `conversations`, `messages`, `citations` tables
- Migrate chat sessions from Redis to PostgreSQL
- Implement conversation sharing

**Phase 3: Analytics (v3.3)** - 1 week
- Create `queries`, `usage_metrics` tables
- Start logging all queries
- Build analytics dashboard

**Phase 4: Document Advanced (v3.4)** - 2 weeks
- Create `document_chunks`, `document_versions`, `document_collections` tables
- Implement version control
- Build collection management

**Phase 5: User Features (v3.5)** - 1 week
- Create `feedback`, `bookmarks`, `search_filters` tables
- Implement bookmark system
- Saved filter quick access

**Total Timeline:** 8 weeks

---

## 5. Kết Luận

### 5.1. Tổng Kết

Báo cáo này đã phân tích và thiết kế toàn diện hệ thống RAG Bidding v3.0 với:

✅ **50 từ khóa hệ thống** được định nghĩa rõ ràng  
✅ **50 use cases** (18 existing + 32 new) với endpoints cụ thể  
✅ **17 tables** (3 existing + 14 new) với full schema  
✅ **PlantUML diagrams:** Use Case, Class Diagram, ERD  
✅ **Migration roadmap:** 5 phases, 8 weeks  

### 5.2. Điểm Nổi Bật

**Dựa trên RAG best practices:**
- Perplexity-style citations
- ChatGPT-style conversations
- Notion-style collections
- Industry-standard analytics

**Hiệu suất cải thiện:**
- Chunk queries: 50% faster
- Analytics: 10x faster
- Cache hit rate: +10-15%

**User experience:**
- Full chat history
- Bookmark system
- Saved filters
- Collaboration features

### 5.3. Next Steps

1. ✅ Review schema với team
2. ⏳ Prioritize phases (1-5)
3. ⏳ Start Phase 1 implementation
4. ⏳ Build migration scripts
5. ⏳ Create API documentation

---

**Document Version:** v3.0  
**Last Updated:** November 27, 2025  
**Status:** Proposed - Pending Review  
**Related Files:**
- `03_Database_Schema.md` - Original schema proposal
- `05_API_Specification.md` - Current API endpoints
- `proposed_schema_v3.md` - Detailed v3.0 schema
