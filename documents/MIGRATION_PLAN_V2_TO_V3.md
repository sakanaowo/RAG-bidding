# 🔄 Migration Plan: Schema v2 → v3

> **Created**: 2025-12-30  
> **Completed**: 2025-12-30  
> **Status**: ✅ COMPLETED  
> **Database**: `rag_bidding_v2` → `rag_bidding_v3`

---

## 📋 Executive Summary

Chuyển đổi RAG Bidding System từ schema v2 sang v3 với các thay đổi chính:

| Aspect | v2 | v3 |
|--------|----|----|
| Embedding Model | `text-embedding-3-large` | `text-embedding-3-small` |
| Embedding Dimension | 3072 | 1536 |
| User Management | ❌ None | ✅ Full (Local + OAuth ready) |
| Chat History | ❌ None | ✅ Conversations + Messages |
| Chunk Tracking | `cmetadata` JSONB | `document_chunks` table |
| Analytics | ❌ None | ✅ Queries + Feedback + Metrics |

---

## 🎯 Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Embedding Model | `text-embedding-3-small` (1536) | Cost-effective, sufficient quality |
| Auth Strategy | Local first, OAuth-ready | Simple start, extensible |
| Data Migration | Fresh re-embed | Clean slate, no legacy data issues |
| Database | `rag_bidding_v3` (already exists) | Schema already applied |

---

## 📊 Current State Analysis

### ✅ All Phases Completed
- [x] SQLAlchemy models cho tất cả 11 tables
- [x] Database `rag_bidding_v3` với schema đã apply
- [x] `.env` đã trỏ sang v3 với `text-embedding-3-small`
- [x] `alembic.ini` và `env.py` đã update
- [x] Update embedding pipeline (3072 → 1536) ✅
- [x] Fix field name `file_name` → `filename` ✅
- [x] Create auth system (Local + OAuth skeleton) ✅
- [x] Create conversation/chat endpoints ✅
- [x] Update repositories layer (9 repositories) ✅
- [x] Re-index all documents (4,512 chunks, 65 documents) ✅
- [x] Testing completed ✅

---

## 🚀 Implementation Phases

### Phase 1: Configuration & Pipeline Updates
**Timeline**: Day 1  
**Priority**: 🔴 Critical

#### 1.1 Environment Configuration
```bash
# File: .env
EMBED_MODEL=text-embedding-3-small  # Changed from text-embedding-3-large
# DATABASE_URL already points to rag_bidding_v3 ✅
```

#### 1.2 Files to Update

| File | Change | Status |
|------|--------|--------|
| `.env` | `EMBED_MODEL=text-embedding-3-small` | ⬜ TODO |
| `src/config/models.py` | Verify default is `text-embedding-3-small` | ✅ Done |
| `src/preprocessing/parsers/utils.py` | Verify TokenChecker default | ⬜ TODO |
| `README.md` | Update embedding docs (3072 → 1536) | ⬜ TODO |

#### 1.3 Embedding Pipeline Verification
```python
# Verify embedding dimension in:
# - src/embedding/embedders/openai_embedder.py
# - src/embedding/store/pgvector_store.py
# - src/models/embeddings.py (already 1536) ✅
```

---

### Phase 2: Field Name & Schema Alignment
**Timeline**: Day 1-2  
**Priority**: 🔴 Critical

#### 2.1 Document Model Field Changes

| Old Field | New Field | Files Affected |
|-----------|-----------|----------------|
| `file_name` | `filename` | 8 files |
| N/A | `filepath` | New field |
| N/A | `uploaded_by` | New field (FK → users) |
| N/A | `file_hash` | New field |
| N/A | `file_size_bytes` | New field |
| N/A | `metadata` → `extra_metadata` | SQLAlchemy reserved |

#### 2.2 Files Requiring Field Name Updates

```
src/api/routers/documents_management.py
├── Line 58: Pydantic schema file_name → filename
├── Line 269: row.filename (verify)
└── Line 529: row.filename (verify)

src/api/services/upload_service.py
├── Line 351: file_name=file_name → filename=file_name
├── Line 439: parameter name
└── Line 491: "filename": file_name

scripts/examples/sqlalchemy_usage.py
├── Line 33: file_name= → filename=
├── Line 91: file_name= → filename=
├── Line 231: file_name= → filename=
└── Line 252: file_name= → filename=

scripts/migration/003_populate_documents_table.py
└── SQL column: file_name → filename
```

---

### Phase 3: Repository Layer Enhancement
**Timeline**: Day 2-3  
**Priority**: 🟡 Medium

#### 3.1 New Repositories to Add

```python
# File: src/models/repositories.py

class UserRepository:
    """User CRUD operations"""
    @staticmethod
    def get_by_id(db, user_id: UUID) -> Optional[User]
    @staticmethod
    def get_by_email(db, email: str) -> Optional[User]
    @staticmethod
    def create(db, email: str, password_hash: str, **kwargs) -> User
    @staticmethod
    def update(db, user_id: UUID, **kwargs) -> Optional[User]
    @staticmethod
    def soft_delete(db, user_id: UUID) -> bool

class ConversationRepository:
    """Conversation CRUD operations"""
    @staticmethod
    def get_user_conversations(db, user_id: UUID, limit: int = 50) -> List[Conversation]
    @staticmethod
    def get_by_id(db, conversation_id: UUID) -> Optional[Conversation]
    @staticmethod
    def create(db, user_id: UUID, title: str = None, **kwargs) -> Conversation
    @staticmethod
    def update_last_message(db, conversation_id: UUID) -> None
    @staticmethod
    def soft_delete(db, conversation_id: UUID) -> bool

class MessageRepository:
    """Message CRUD operations"""
    @staticmethod
    def get_conversation_messages(db, conversation_id: UUID) -> List[Message]
    @staticmethod
    def add_message(db, conversation_id: UUID, user_id: UUID, role: str, content: str, **kwargs) -> Message
    @staticmethod
    def add_sources(db, message_id: UUID, sources: dict) -> None

class DocumentChunkRepository:
    """Document chunk operations"""
    @staticmethod
    def get_by_document(db, document_id: UUID) -> List[DocumentChunk]
    @staticmethod
    def create_batch(db, document_id: UUID, chunks: List[dict]) -> List[DocumentChunk]
    @staticmethod
    def increment_retrieval_count(db, chunk_ids: List[UUID]) -> None

class FeedbackRepository:
    """Feedback operations"""
    @staticmethod
    def create(db, user_id: UUID, message_id: UUID, rating: int, **kwargs) -> Feedback
    @staticmethod
    def get_message_feedback(db, message_id: UUID) -> List[Feedback]

class QueryRepository:
    """Query analytics operations"""
    @staticmethod
    def log_query(db, query_text: str, user_id: UUID = None, **kwargs) -> Query
    @staticmethod
    def get_by_hash(db, query_hash: str) -> Optional[Query]
```

---

### Phase 4: Authentication System
**Timeline**: Day 3-5  
**Priority**: 🟡 Medium

#### 4.1 Auth Architecture

```
src/api/
├── routers/
│   └── auth.py              # Auth endpoints
├── services/
│   └── auth_service.py      # Auth business logic
├── middleware/
│   └── auth_middleware.py   # JWT validation
└── schemas/
    └── auth_schemas.py      # Pydantic models
```

#### 4.2 Auth Endpoints (Local)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Create new user |
| POST | `/auth/login` | Login, get JWT |
| POST | `/auth/logout` | Invalidate token |
| GET | `/auth/me` | Get current user |
| POST | `/auth/refresh` | Refresh JWT |
| POST | `/auth/change-password` | Update password |

#### 4.3 OAuth Skeleton (Future-Ready)

```python
# File: src/api/routers/auth.py

# OAuth endpoints - skeleton for future implementation
@router.get("/auth/oauth/{provider}")
async def oauth_redirect(provider: str):
    """Redirect to OAuth provider"""
    raise HTTPException(501, f"OAuth provider '{provider}' not yet implemented")

@router.get("/auth/oauth/{provider}/callback")
async def oauth_callback(provider: str, code: str):
    """Handle OAuth callback"""
    raise HTTPException(501, f"OAuth provider '{provider}' not yet implemented")

# Supported providers enum for future
class OAuthProvider(str, Enum):
    GOOGLE = "google"
    GITHUB = "github"
    MICROSOFT = "microsoft"
```

#### 4.4 JWT Configuration

```python
# File: src/config/auth.py (NEW)

from dataclasses import dataclass
import os

@dataclass
class AuthConfig:
    secret_key: str = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # OAuth - ready for future
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    github_client_id: str = os.getenv("GITHUB_CLIENT_ID", "")
    github_client_secret: str = os.getenv("GITHUB_CLIENT_SECRET", "")

auth_config = AuthConfig()
```

---

### Phase 5: Conversation System
**Timeline**: Day 5-7  
**Priority**: 🟡 Medium

#### 5.1 Conversation Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/conversations` | List user's conversations |
| POST | `/conversations` | Create new conversation |
| GET | `/conversations/{id}` | Get conversation with messages |
| DELETE | `/conversations/{id}` | Soft delete conversation |
| PATCH | `/conversations/{id}` | Update title/settings |
| POST | `/conversations/{id}/messages` | Add message (triggers RAG) |

#### 5.2 Integration with RAG Pipeline

```python
# File: src/api/services/conversation_service.py

class ConversationService:
    async def process_message(
        self,
        conversation_id: UUID,
        user_id: UUID,
        query: str,
        rag_mode: str = "balanced"
    ) -> Message:
        """
        Process user message through RAG pipeline:
        1. Save user message
        2. Run RAG retrieval
        3. Generate response
        4. Save assistant message with sources
        5. Log query analytics
        6. Update conversation metrics
        """
        pass
```

---

### Phase 6: Document Re-Indexing
**Timeline**: Day 7-9  
**Priority**: 🔴 Critical

#### 6.1 Re-Embedding Pipeline

```python
# File: scripts/reindex_documents_v3.py

"""
Re-index all documents with new embedding model (1536 dim)

Steps:
1. Read all documents from data/processed/
2. For each document:
   a. Load chunks
   b. Create Document record
   c. Create DocumentChunk records
   d. Generate embeddings (text-embedding-3-small)
   e. Store in langchain_pg_embedding with chunk_id FK
3. Verify counts match
"""

async def reindex_all():
    # Implementation
    pass
```

#### 6.2 Verification Checklist

```bash
# After re-indexing, verify:
psql -U sakana -d rag_bidding_v3 -c "
SELECT 
    (SELECT COUNT(*) FROM documents) as documents,
    (SELECT COUNT(*) FROM document_chunks) as chunks,
    (SELECT COUNT(*) FROM langchain_pg_embedding) as embeddings,
    (SELECT COUNT(*) FROM langchain_pg_collection) as collections;
"
```

---

### Phase 7: API Integration & Testing
**Timeline**: Day 9-10  
**Priority**: 🟢 Normal

#### 7.1 Update Main Router

```python
# File: src/api/main.py

from .routers import (
    documents_management,
    upload,
    query,
    auth,           # NEW
    conversations,  # NEW
    feedback,       # NEW
)

app.include_router(auth.router)
app.include_router(conversations.router)
app.include_router(feedback.router)
```

#### 7.2 Test Cases

```bash
# Auth tests
POST /auth/register → 201
POST /auth/login → 200 + JWT
GET /auth/me (with JWT) → 200 + user info

# Conversation tests
POST /conversations → 201 + conversation_id
POST /conversations/{id}/messages → 200 + AI response
GET /conversations → 200 + list

# Document tests (existing)
GET /documents/catalog → 200 + list
POST /upload → 202 + job_id
```

---

## 📁 New Files to Create

```
src/
├── api/
│   ├── routers/
│   │   ├── auth.py                 # NEW
│   │   ├── conversations.py        # NEW
│   │   └── feedback.py             # NEW
│   ├── services/
│   │   ├── auth_service.py         # NEW
│   │   └── conversation_service.py # NEW
│   ├── middleware/
│   │   └── auth_middleware.py      # NEW
│   └── schemas/
│       ├── auth_schemas.py         # NEW
│       └── conversation_schemas.py # NEW
├── config/
│   └── auth.py                     # NEW
scripts/
└── reindex_documents_v3.py         # NEW
```

---

## 📁 Files to Update

```
.env                                           # EMBED_MODEL
src/api/routers/documents_management.py        # file_name → filename
src/api/services/upload_service.py             # file_name → filename, add new fields
src/api/main.py                                # Include new routers
src/models/repositories.py                     # Add new repositories
scripts/examples/sqlalchemy_usage.py           # file_name → filename
scripts/migration/003_populate_documents_table.py  # SQL column name
README.md                                      # Update embedding docs
```

---

## 🔒 Environment Variables to Add

```bash
# File: .env (additions)

# JWT Authentication
JWT_SECRET_KEY=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# OAuth (for future)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=

# Password hashing
BCRYPT_ROUNDS=12
```

---

## 📦 Dependencies to Add

```yaml
# File: environment.yaml (additions)

dependencies:
  - python-jose[cryptography]  # JWT
  - passlib[bcrypt]            # Password hashing
  - python-multipart           # Form data (already have?)
  
pip:
  - bcrypt>=4.0.0
  - PyJWT>=2.8.0
```

---

## ✅ Checklist Summary

### Day 1: Configuration
- [ ] Update `.env` với `EMBED_MODEL=text-embedding-3-small`
- [ ] Verify embedding pipeline reads correct model
- [ ] Fix `file_name` → `filename` trong tất cả files

### Day 2-3: Repository Layer
- [ ] Add `UserRepository`
- [ ] Add `ConversationRepository`
- [ ] Add `MessageRepository`
- [ ] Add `DocumentChunkRepository`
- [ ] Add `FeedbackRepository`
- [ ] Add `QueryRepository`

### Day 3-5: Auth System
- [ ] Create `src/config/auth.py`
- [ ] Create `src/api/schemas/auth_schemas.py`
- [ ] Create `src/api/services/auth_service.py`
- [ ] Create `src/api/routers/auth.py`
- [ ] Create `src/api/middleware/auth_middleware.py`
- [ ] Add OAuth skeleton endpoints

### Day 5-7: Conversation System
- [ ] Create `src/api/schemas/conversation_schemas.py`
- [ ] Create `src/api/services/conversation_service.py`
- [ ] Create `src/api/routers/conversations.py`
- [ ] Create `src/api/routers/feedback.py`
- [ ] Integrate with RAG pipeline

### Day 7-9: Re-Indexing
- [ ] Create `scripts/reindex_documents_v3.py`
- [ ] Run re-indexing pipeline
- [ ] Verify document counts
- [ ] Test similarity search

### Day 9-10: Testing & Cleanup
- [ ] Update `src/api/main.py` with new routers
- [ ] Run all API tests
- [ ] Update documentation
- [ ] Remove deprecated alembic migration

---

## 🔄 Rollback Plan

Nếu cần rollback về v2:

```bash
# 1. Đổi .env
DATABASE_URL=postgresql+psycopg://sakana:sakana123@localhost:5432/rag_bidding_v2
DB_NAME=rag_bidding_v2
EMBED_MODEL=text-embedding-3-large

# 2. Revert code changes
git checkout HEAD~N -- src/models/

# 3. Restart server
./start_server.sh
```

---

## 📝 Notes

1. **Database v3 đã có schema** - Không cần chạy Alembic migrations
2. **Data v2 không migrate** - Re-embed tất cả với model mới
3. **Auth optional cho API** - Endpoints vẫn hoạt động không cần login (initially)
4. **OAuth skeleton** - Endpoints trả 501 cho đến khi implement

---

*Last updated: 2025-12-30*
