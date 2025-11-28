# System Design Documentation - RAG Bidding System

**Ngày cập nhật:** 27/11/2025  
**Phiên bản:** 3.0  
**Status:** ✅ v2.0 Production | 📋 v3.0 Proposed

---

## 📑 Mục Lục Tài Liệu

### ✅ Core System Design (v2.0 - Production)

1. **[Đặc Tả Hệ Thống](./01_System_Specification.md)** - Tech stack, requirements, RAG modes
2. **[Use Cases](./02_Use_Cases.md)** - 18 use cases (UC-1 to UC-18)
3. **[Database Schema](./03_Database_Schema.md)** - Current schema (3 tables)
4. **[System Architecture](./04_System_Architecture.md)** - 6-layer architecture
5. **[API Specification](./05_API_Specification.md)** - REST endpoints

### ✅ SQLAlchemy Implementation (v2.1 - Production)

6. **[SQLAlchemy Implementation](./06_SQLAlchemy_Implementation.md)** - ORM usage guide
7. **[SQLAlchemy Roadmap](./07_SQLAlchemy_Roadmap.md)** - 8-phase plan (Phase 1 DONE)
8. **[Quick Start ORM](./08_Quick_Start_ORM.md)** - Quick reference
9. **[SQLAlchemy Rules](./09_SQLAlchemy_Rules.md)** - Critical rules ⚠️

### 📋 Schema v3.0 Proposal (NEW - Nov 27, 2025) ⭐

10. **[Analysis & Design Report](./10_Analysis_Design_Report.md)** 🆕 **START HERE**
    - 📖 **Bảng từ khóa:** 50 terms (Vietnamese + English)
    - 📊 **Use Case Diagram:** PlantUML with 50 use cases
    - 🏗️ **Class Diagrams:** Full entity relationships
    - 📝 **Complete analysis:** Terminology, actors, flows

11. **[Database Schema v3.0](./03_Database_Schema_v3.md)** 🆕
    - 🗄️ **17 tables:** 3 existing + 14 new
    - ⏱️ **Migration:** 5 phases, 8 weeks roadmap
    - ⚡ **Performance:** 50% faster chunk queries, 10x faster analytics
    - 🎯 **Best practices:** Perplexity citations, ChatGPT conversations, Notion collections

---

## 🎯 Hướng Dẫn Đọc Theo Vai Trò

### 🆕 Cho Contributors Mới (Bắt Đầu Đây)

1. 📋 **`10_Analysis_Design_Report.md`** - Tổng quan hệ thống
   - Terminology (50 từ khóa)
   - Use cases (50 kịch bản)
   - Class diagrams
2. 🗄️ **`03_Database_Schema_v3.md`** - Schema v3.0
3. 📖 **`01_System_Specification.md`** - Tech stack & yêu cầu

### 💻 Cho Developers (ORM Implementation)

1. **`08_Quick_Start_ORM.md`** - Quick reference (5 phút)
2. **`06_SQLAlchemy_Implementation.md`** - Detailed guide
3. **`09_SQLAlchemy_Rules.md`** - Critical rules ⚠️ **KEEP OPEN**
4. **`07_SQLAlchemy_Roadmap.md`** - Implementation phases

### 🏗️ Cho Architects (System Design)

1. **`10_Analysis_Design_Report.md`** - Full analysis
2. **`04_System_Architecture.md`** - 6-layer architecture
3. **`03_Database_Schema_v3.md`** - Schema evolution
4. **`07_SQLAlchemy_Roadmap.md`** - Migration strategy

### 🔌 Cho API Users

1. **`05_API_Specification.md`** - All endpoints
2. **`10_Analysis_Design_Report.md` Section 2** - Use cases

### 🗄️ Cho Database Administrators

1. **`03_Database_Schema_v3.md`** - Schema v3.0 proposal
2. **`temp/proposed_schema_v3.md`** - Detailed DDL
3. **`10_Analysis_Design_Report.md` Section 4** - Migration plan

---

## 📊 Thống Kê Hệ Thống

### Current State (v2.0 - Production)

**Database:**
- PostgreSQL 18.1 + pgvector 0.8.1
- ORM: SQLAlchemy 2.0.44 + Alembic 1.17.2 ✅
- Documents: 64 (8 types)
- Chunks: 7,892
- Size: 149 MB
- Baseline: 0dd6951d6844 (Nov 27, 2025)

**Models:**
- Embedding: OpenAI text-embedding-3-large (3,072-dim)
- Reranker: BAAI/bge-reranker-v2-m3
- LLM: GPT-4o-mini
- Cache: 3-tier (L1 In-Memory + L2 Redis + L3 PostgreSQL)

### Proposed v3.0 Enhancements

**Schema:**
- 17 tables (3 existing + 14 new)
- New features: Users, Conversations, Citations, Analytics
- Migration: 5 phases, 8 weeks

**Performance:**
- Chunk queries: 50% faster
- Analytics: 10x faster
- Cache hit rate: +10-15%

**Use Cases:**
- Current: 18 use cases
- Proposed: 50 use cases (32 new)

---

## 🔗 Quick Links

### ✅ Implementation Status

**Phase 1: SQLAlchemy Setup (DONE - Nov 27, 2025)**
- ✅ Alembic migration baseline: 0dd6951d6844
- ✅ All 6 example scripts passing
- ✅ Models: `documents.py`, `embeddings.py`, `repositories.py`
- ✅ Repository pattern implemented

### 📋 Schema v3.0 Proposal (NEW)

**Status:** ⏳ Pending team review

**Key Documents:**
- Full analysis: `10_Analysis_Design_Report.md`
- Schema proposal: `03_Database_Schema_v3.md`
- Detailed DDL: `temp/proposed_schema_v3.md`

**Highlights:**
- 50 use cases documented with PlantUML
- Complete class diagrams
- 50 terminology entries
- 5-phase migration roadmap

### ⏳ Next Steps

1. **Review Schema v3.0:**
   - Team review of `10_Analysis_Design_Report.md`
   - Prioritize migration phases
   - Approve schema changes

2. **Phase 2: FastAPI Integration** (See `07_SQLAlchemy_Roadmap.md`)
   - Update endpoints to use ORM
   - Remove raw SQL queries
   - Add dependency injection

3. **Schema v3.0 Implementation:**
   - Phase 1: User & Auth (2 weeks)
   - Phase 2: Conversations (2 weeks)
   - Phase 3: Analytics (1 week)
   - Phase 4: Document Advanced (2 weeks)
   - Phase 5: User Features (1 week)

---

## 📁 Cấu Trúc Folder

```
documents/System Design/
├── README.md                          # 📖 Tài liệu này
│
├── ✅ Core System (v2.0)
│   ├── 01_System_Specification.md
│   ├── 02_Use_Cases.md
│   ├── 03_Database_Schema.md
│   ├── 04_System_Architecture.md
│   └── 05_API_Specification.md
│
├── ✅ SQLAlchemy (v2.1)
│   ├── 06_SQLAlchemy_Implementation.md
│   ├── 07_SQLAlchemy_Roadmap.md
│   ├── 08_Quick_Start_ORM.md
│   └── 09_SQLAlchemy_Rules.md
│
└── 📋 Schema v3.0 Proposal (NEW)
    ├── 10_Analysis_Design_Report.md    # 🆕 Full analysis
    └── 03_Database_Schema_v3.md        # 🆕 Schema proposal
```

---

## 🔄 Lịch Sử Cập Nhật

| Ngày       | Version | Thay đổi                                                                         |
| ---------- | ------- | -------------------------------------------------------------------------------- |
| 2025-11-27 | 3.0     | 🆕 Thêm Analysis Report & Schema v3.0 (50 use cases, class diagrams, migration) |
| 2025-11-27 | 2.2     | ✅ Hoàn thành Phase 1 - SQLAlchemy Setup                                        |
| 2025-11-25 | 2.1     | Thêm SQLAlchemy Implementation (docs 6-9)                                        |
| 2025-11-24 | 2.0     | Tạo mới bộ tài liệu System Design                                                |

---

## 📁 Related Files

**Production Code:**
- Models: `/src/models/`
- Migrations: `/alembic/versions/`
- Examples: `/scripts/examples/`
- Tests: `/scripts/tests/`

**Schema v3.0 Proposal:**
- Analysis: `10_Analysis_Design_Report.md`
- Schema: `03_Database_Schema_v3.md`
- Detailed DDL: `temp/proposed_schema_v3.md`

**Progress Tracking:**
- Session context: `temp/CURRENT_SESSION_CONTEXT.md`
- Step 4 report: `temp/step4_completion_report.md`
- Detailed analysis: `temp/detailed_schema_analysis.md`

---

## 📞 Liên Hệ

**Project:** RAG Bidding System  
**Repository:** [RAG-bidding](https://github.com/sakanaowo/RAG-bidding)  
**Branch:** phase-design  
**Documentation:** `/documents/System Design/`

**Contributors:** System Architecture Team  
**Last Updated:** November 27, 2025
