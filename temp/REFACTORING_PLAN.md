# RAG Bidding System - Architecture Refactoring Plan

**Version:** 1.0  
**Date:** December 12, 2025  
**Estimated Duration:** 3-5 days (incremental)  
**Risk Level:** Medium (with migration strategy)

---

## 🎯 Goals

### Primary Objectives
1. **Separate Concerns** - Router → Service → Repository → Model
2. **Eliminate Raw SQL** - Use SQLAlchemy ORM throughout
3. **Improve Testability** - Each layer independently testable
4. **Maintain Compatibility** - Zero downtime, backward compatible API

### Success Metrics
- ✅ 0 raw SQL queries in routers
- ✅ 100% ORM usage for documents table
- ✅ Service layer coverage for all business logic
- ✅ Repository pattern usage >90%
- ✅ All existing tests pass
- ✅ API contract unchanged (same request/response)

---

## 📋 Current vs Target Architecture

### Current State (Messy)
```
API Routers (814 lines)
├─ Route definitions
├─ Request validation
├─ Business logic (status checks, validation)
├─ Raw SQL queries (❌)
├─ Response formatting
└─ Error handling

Direct DB access everywhere
```

### Target State (Clean)
```
┌─────────────────────────────────────────┐
│ Router (API Layer)                      │  50-100 lines per file
│ - Route definitions                     │
│ - Request/response validation (Pydantic)│
│ - Dependency injection                  │
└──────────────┬──────────────────────────┘
               │ calls
┌──────────────▼──────────────────────────┐
│ Service (Business Logic Layer)          │  100-200 lines per file
│ - Validation rules                      │
│ - Business workflows                    │
│ - Transaction management                │
│ - Cache invalidation                    │
└──────────────┬──────────────────────────┘
               │ calls
┌──────────────▼──────────────────────────┐
│ Repository (Data Access Layer)          │  150-300 lines per file
│ - CRUD operations                       │
│ - Query building (ORM)                  │
│ - Data transformation                   │
└──────────────┬──────────────────────────┘
               │ uses
┌──────────────▼──────────────────────────┐
│ Model (ORM)                             │  Existing
│ - Document class                        │
│ - Relationships                         │
└─────────────────────────────────────────┘
```

---

## 🗂️ New File Structure

### Phase 1: Create Repository Layer
```
src/
├── repositories/
│   ├── __init__.py                    # NEW - Export all repositories
│   ├── base.py                        # NEW - Base repository class
│   ├── document_repository.py         # EXPAND - Async methods for Document
│   ├── chat_repository.py             # NEW - Chat session & messages
│   └── vector_repository.py           # NEW - Wrapper for langchain_pg_embedding
```

### Phase 2: Create Service Layer
```
src/
├── services/
│   ├── __init__.py                    # NEW - Export all services
│   ├── document_service.py            # NEW - Document business logic
│   ├── chat_service.py                # NEW - Chat session management
│   ├── upload_service.py              # REFACTOR - Use repository
│   └── cache_service.py               # NEW - Cache invalidation logic
```

### Phase 3: Slim Down Routers
```
src/api/
├── routers/
│   ├── documents.py                   # RENAME from documents_management.py
│   │                                  # 814 lines → 150 lines
│   ├── chat.py                        # RENAME from documents_chat.py
│   │                                  # 395 lines → 120 lines
│   └── upload.py                      # REFACTOR - Already good pattern
│
└── dependencies.py                    # NEW - Dependency injection
```

---

## 📅 Implementation Phases

---

## **PHASE 1: Foundation - Repository Layer** (Day 1, ~4 hours)

### 1.1 Create Base Repository

**File:** `src/repositories/base.py`

```python
"""
Base Repository Pattern
Reusable CRUD operations for all models
"""
from typing import TypeVar, Generic, Type, List, Optional, Dict, Any
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    """Generic repository for common CRUD operations."""
    
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db
    
    async def get_by_id(self, id: Any) -> Optional[ModelType]:
        """Get single record by primary key."""
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(
        self, 
        skip: int = 0, 
        limit: int = 100,
        filters: Dict[str, Any] = None
    ) -> List[ModelType]:
        """Get all records with pagination and filters."""
        query = select(self.model)
        
        # Apply filters
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
        
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def create(self, **kwargs) -> ModelType:
        """Create new record."""
        instance = self.model(**kwargs)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance
    
    async def update(self, id: Any, **kwargs) -> Optional[ModelType]:
        """Update existing record."""
        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(**kwargs)
            .returning(self.model)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.scalar_one_or_none()
    
    async def delete(self, id: Any) -> bool:
        """Delete record (returns True if deleted)."""
        stmt = delete(self.model).where(self.model.id == id)
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount > 0
    
    async def count(self, filters: Dict[str, Any] = None) -> int:
        """Count records with optional filters."""
        query = select(func.count()).select_from(self.model)
        
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
        
        result = await self.db.execute(query)
        return result.scalar()
```

**Testing:** `scripts/tests/test_base_repository.py`

---

### 1.2 Expand Document Repository

**File:** `src/repositories/document_repository.py` (REFACTOR existing)

```python
"""
Document Repository
All database operations for Document model
"""
from typing import List, Optional, Dict, Any
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from src.models.documents import Document
from .base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """Repository for Document CRUD operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Document, db)
    
    # ===== CUSTOM QUERIES =====
    
    async def get_by_document_id(self, document_id: str) -> Optional[Document]:
        """Get document by document_id (not primary key)."""
        result = await self.db.execute(
            select(Document).where(Document.document_id == document_id)
        )
        return result.scalar_one_or_none()
    
    async def list_documents(
        self,
        status: Optional[str] = None,
        document_type: Optional[str] = None,
        category: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Document]:
        """
        List documents with filters.
        
        Replaces raw SQL:
        SELECT * FROM documents WHERE status = :status
        ORDER BY created_at DESC LIMIT :limit
        """
        query = select(Document)
        
        # Build filters
        if status:
            query = query.where(Document.status == status)
        if document_type:
            query = query.where(Document.document_type == document_type)
        if category:
            query = query.where(Document.category == category)
        
        # Order and paginate
        query = (
            query
            .order_by(Document.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def update_status(
        self, 
        document_id: str, 
        new_status: str
    ) -> Optional[Document]:
        """
        Update document status.
        
        Replaces raw SQL:
        UPDATE documents SET status = :status, updated_at = NOW()
        WHERE document_id = :document_id
        """
        doc = await self.get_by_document_id(document_id)
        if not doc:
            return None
        
        doc.status = new_status
        doc.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(doc)
        return doc
    
    async def get_statistics(self, document_id: str) -> Dict[str, Any]:
        """
        Get document statistics.
        
        Replaces raw SQL with aggregation queries
        """
        doc = await self.get_by_document_id(document_id)
        if not doc:
            return None
        
        # Note: Chunk stats would come from vector_repository
        return {
            "document_id": doc.document_id,
            "filename": doc.filename,
            "status": doc.status,
            "total_chunks": doc.total_chunks,
            "file_size": doc.file_size,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
        }
    
    async def search_by_filename(self, filename_pattern: str) -> List[Document]:
        """Search documents by filename pattern."""
        result = await self.db.execute(
            select(Document)
            .where(Document.filename.ilike(f"%{filename_pattern}%"))
            .order_by(Document.created_at.desc())
        )
        return result.scalars().all()
```

**Tasks:**
- [x] Implement async methods
- [ ] Add complex query methods
- [ ] Add bulk operations
- [ ] Add transaction support

---

### 1.3 Create Vector Repository

**File:** `src/repositories/vector_repository.py` (NEW)

```python
"""
Vector Repository
Operations on langchain_pg_embedding table (chunks)
"""
from typing import List, Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)


class VectorRepository:
    """
    Repository for vector/chunk operations.
    
    Note: langchain_pg_embedding doesn't have ORM model,
    so we use raw SQL here (acceptable for complex JSONB queries).
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_document_chunks(
        self, 
        document_id: str,
        order_by_index: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all chunks for a document.
        
        Returns: List of {chunk_id, chunk_index, content, metadata}
        """
        order_clause = (
            "ORDER BY (cmetadata->>'chunk_index')::int" 
            if order_by_index 
            else ""
        )
        
        query = text(f"""
            SELECT 
                id as chunk_id,
                document as content,
                cmetadata as metadata,
                (cmetadata->>'chunk_index')::int as chunk_index
            FROM langchain_pg_embedding
            WHERE cmetadata->>'document_id' = :document_id
            {order_clause}
        """)
        
        result = await self.db.execute(query, {"document_id": document_id})
        rows = result.fetchall()
        
        return [
            {
                "chunk_id": row.chunk_id,
                "chunk_index": row.chunk_index,
                "content": row.content,
                "metadata": row.metadata,
            }
            for row in rows
        ]
    
    async def get_catalog_summary(
        self,
        document_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get document catalog (grouped by document_id).
        
        Complex JSONB aggregation - raw SQL acceptable here.
        """
        where_clauses = []
        if document_type:
            where_clauses.append(f"cmetadata->>'document_type' = :document_type")
        
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        query = text(f"""
            WITH document_groups AS (
                SELECT 
                    cmetadata->>'document_id' as document_id,
                    cmetadata->>'document_type' as document_type,
                    COUNT(*) as chunk_count,
                    MIN((cmetadata->>'chunk_index')::int) as first_chunk_idx,
                    MAX(CAST(cmetadata->>'created_at' AS TIMESTAMP)) as created_at,
                    array_agg(id ORDER BY (cmetadata->>'chunk_index')::int) as chunk_ids,
                    (array_agg(cmetadata ORDER BY (cmetadata->>'chunk_index')::int))[1] as first_chunk_metadata
                FROM langchain_pg_embedding
                {where_sql}
                GROUP BY cmetadata->>'document_id', cmetadata->>'document_type'
            )
            SELECT *
            FROM document_groups
            ORDER BY created_at DESC NULLS LAST, document_id
            LIMIT :limit OFFSET :offset
        """)
        
        params = {"limit": limit, "offset": offset}
        if document_type:
            params["document_type"] = document_type
        
        result = await self.db.execute(query, params)
        return [dict(row._mapping) for row in result.fetchall()]
    
    async def count_chunks_by_document(self, document_id: str) -> int:
        """Count total chunks for a document."""
        query = text("""
            SELECT COUNT(*)
            FROM langchain_pg_embedding
            WHERE cmetadata->>'document_id' = :document_id
        """)
        result = await self.db.execute(query, {"document_id": document_id})
        return result.scalar()
```

**Note:** Raw SQL acceptable for langchain_pg_embedding vì:
- Không có ORM model (managed by LangChain)
- Complex JSONB queries (GROUP BY on JSONB fields)
- Performance-critical aggregations

---

### 1.4 Create Chat Repository

**File:** `src/repositories/chat_repository.py` (NEW)

```python
"""
Chat Session Repository
Operations for chat sessions and messages (future PostgreSQL migration)
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

# TODO: Create ChatSession and ChatMessage ORM models first
# For now, this is a placeholder


class ChatRepository:
    """
    Repository for chat sessions and messages.
    
    TODO [CHAT-MIGRATION]: 
    - Create ORM models (ChatSession, ChatMessage)
    - Implement async CRUD operations
    - Replace Redis storage
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_session(self, user_id: Optional[str] = None) -> str:
        """Create new chat session."""
        raise NotImplementedError("Chat migration pending")
    
    async def get_session_messages(
        self, 
        session_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get messages for a session."""
        raise NotImplementedError("Chat migration pending")
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Add message to session."""
        raise NotImplementedError("Chat migration pending")
```

---

### Phase 1 Deliverables

**Files Created:**
- `src/repositories/base.py` - 150 lines
- `src/repositories/document_repository.py` - 200 lines (expanded)
- `src/repositories/vector_repository.py` - 150 lines
- `src/repositories/chat_repository.py` - 50 lines (placeholder)
- `src/repositories/__init__.py` - Export all

**Tests Created:**
- `scripts/tests/test_repositories/test_base_repository.py`
- `scripts/tests/test_repositories/test_document_repository.py`
- `scripts/tests/test_repositories/test_vector_repository.py`

**Migration:** No breaking changes (repositories not used yet)

---

## **PHASE 2: Business Logic - Service Layer** (Day 2, ~6 hours)

### 2.1 Create Document Service

**File:** `src/services/document_service.py` (NEW)

```python
"""
Document Service
Business logic for document management
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.document_repository import DocumentRepository
from src.repositories.vector_repository import VectorRepository
from src.models.documents import Document

logger = logging.getLogger(__name__)


class DocumentService:
    """
    Service layer for document business logic.
    
    Responsibilities:
    - Validate business rules
    - Coordinate multiple repositories
    - Handle cache invalidation
    - Transaction management
    """
    
    def __init__(
        self, 
        doc_repo: DocumentRepository,
        vector_repo: VectorRepository
    ):
        self.doc_repo = doc_repo
        self.vector_repo = vector_repo
    
    # ===== DOCUMENT CRUD =====
    
    async def list_documents(
        self,
        status: Optional[str] = None,
        document_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Document]:
        """
        List documents with business logic.
        
        Replaces: documents_management.py list_documents() endpoint logic
        """
        # Validate status
        if status and status not in ["active", "archived", "deleted"]:
            raise ValueError(f"Invalid status: {status}")
        
        # Validate limit
        if limit > 200:
            logger.warning(f"Limit {limit} exceeds max 200, capping")
            limit = 200
        
        # Delegate to repository
        return await self.doc_repo.list_documents(
            status=status,
            document_type=document_type,
            skip=skip,
            limit=limit
        )
    
    async def get_document(self, document_id: str) -> Optional[Document]:
        """Get single document by document_id."""
        doc = await self.doc_repo.get_by_document_id(document_id)
        if not doc:
            logger.info(f"Document not found: {document_id}")
        return doc
    
    async def update_document_status(
        self,
        document_id: str,
        new_status: str,
        invalidate_cache: bool = True
    ) -> Optional[Document]:
        """
        Update document status with validation.
        
        Replaces: documents_management.py update_document_status()
        """
        # Validate status
        valid_statuses = ["active", "archived", "deleted"]
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        
        # Get current document
        doc = await self.doc_repo.get_by_document_id(document_id)
        if not doc:
            logger.error(f"Document not found: {document_id}")
            return None
        
        # Check if status actually changed
        if doc.status == new_status:
            logger.info(f"Status unchanged: {document_id} already {new_status}")
            return doc
        
        # Update status
        updated_doc = await self.doc_repo.update_status(document_id, new_status)
        
        # Cache invalidation
        if invalidate_cache:
            await self._invalidate_document_cache(document_id)
        
        logger.info(
            f"✅ Document status updated: {document_id} "
            f"{doc.status} → {new_status}"
        )
        
        return updated_doc
    
    # ===== CATALOG OPERATIONS =====
    
    async def get_catalog(
        self,
        document_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get document catalog with chunk aggregation.
        
        Replaces: documents_management.py list_document_catalog()
        
        Returns: List of DocumentSummary (grouped by document_id)
        """
        # Get grouped documents from vector store
        catalog = await self.vector_repo.get_catalog_summary(
            document_type=document_type,
            limit=limit,
            offset=offset
        )
        
        # Enrich with document table status
        enriched = []
        for item in catalog:
            doc_id = item["document_id"]
            
            # Get status from documents table
            doc = await self.doc_repo.get_by_document_id(doc_id)
            current_status = doc.status if doc else "active"
            
            # Filter by status if requested
            if status and current_status != status:
                continue
            
            # Extract title from metadata
            metadata = item["first_chunk_metadata"]
            title = self._extract_title(metadata)
            
            enriched.append({
                "document_id": doc_id,
                "title": title,
                "document_type": item["document_type"],
                "total_chunks": item["chunk_count"],
                "status": current_status,
                "chunk_ids": item["chunk_ids"],
                "created_at": item["created_at"],
            })
        
        return enriched
    
    async def get_document_detail(
        self, 
        document_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get complete document with all chunks.
        
        Replaces: documents_management.py get_document_detail()
        """
        # Get document metadata
        doc = await self.doc_repo.get_by_document_id(document_id)
        if not doc:
            return None
        
        # Get all chunks
        chunks = await self.vector_repo.get_document_chunks(document_id)
        
        if not chunks:
            logger.warning(f"Document {document_id} has no chunks")
            return None
        
        # Extract metadata from first chunk
        first_metadata = chunks[0]["metadata"]
        title = self._extract_title(first_metadata)
        
        return {
            "document_id": document_id,
            "title": title,
            "document_type": doc.document_type,
            "total_chunks": len(chunks),
            "status": doc.status,
            "metadata": first_metadata,
            "chunks": chunks,
        }
    
    # ===== STATISTICS =====
    
    async def get_document_stats(
        self, 
        document_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get document statistics."""
        doc = await self.doc_repo.get_by_document_id(document_id)
        if not doc:
            return None
        
        chunk_count = await self.vector_repo.count_chunks_by_document(document_id)
        
        return {
            "document_id": document_id,
            "filename": doc.filename,
            "status": doc.status,
            "total_chunks": chunk_count,
            "file_size": doc.file_size,
            "created_at": doc.created_at,
            "updated_at": doc.updated_at,
        }
    
    # ===== PRIVATE HELPERS =====
    
    def _extract_title(self, metadata: Dict[str, Any]) -> str:
        """Extract title from metadata (business logic)."""
        # Try different title fields
        for key in ["title", "document_name", "file_name"]:
            if key in metadata and metadata[key]:
                return metadata[key]
        
        # Fallback to document_id
        return metadata.get("document_id", "Untitled")
    
    async def _invalidate_document_cache(self, document_id: str):
        """Invalidate cached data for document."""
        # TODO: Implement cache invalidation
        # - Clear Redis cache keys
        # - Clear LangChain retriever cache
        logger.info(f"🗑️ Cache invalidated for: {document_id}")
```

**Testing:** `scripts/tests/test_services/test_document_service.py`

---

### 2.2 Create Dependency Injection

**File:** `src/api/dependencies.py` (NEW)

```python
"""
Dependency Injection
Provides services and repositories to routers
"""
from typing import Generator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.repositories.document_repository import DocumentRepository
from src.repositories.vector_repository import VectorRepository
from src.services.document_service import DocumentService


# ===== REPOSITORY DEPENDENCIES =====

def get_document_repository(
    db: AsyncSession = Depends(get_db)
) -> DocumentRepository:
    """Get DocumentRepository instance."""
    return DocumentRepository(db)


def get_vector_repository(
    db: AsyncSession = Depends(get_db)
) -> VectorRepository:
    """Get VectorRepository instance."""
    return VectorRepository(db)


# ===== SERVICE DEPENDENCIES =====

def get_document_service(
    doc_repo: DocumentRepository = Depends(get_document_repository),
    vector_repo: VectorRepository = Depends(get_vector_repository)
) -> DocumentService:
    """Get DocumentService instance."""
    return DocumentService(doc_repo, vector_repo)
```

---

### Phase 2 Deliverables

**Files Created:**
- `src/services/document_service.py` - 300 lines
- `src/api/dependencies.py` - 50 lines
- `src/services/__init__.py` - Export all

**Tests:**
- `scripts/tests/test_services/test_document_service.py`
- Unit tests với mock repositories

**Migration:** No breaking changes (services not used yet)

---

## **PHASE 3: Slim Down Routers** (Day 3, ~5 hours)

### 3.1 Refactor documents_management.py

**Before: 814 lines** (Raw SQL + Business Logic + API)  
**After: ~150 lines** (Pure API layer)

**File:** `src/api/routers/documents.py` (RENAME)

```python
"""
Document Management API
Thin controller layer - delegates to DocumentService
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional

from src.api.schemas.document_schemas import (
    DocumentMetadata,
    DocumentSummary,
    DocumentDetail,
    DocumentStats,
    UpdateDocumentStatusRequest,
    UpdateDocumentStatusResponse,
)
from src.api.dependencies import get_document_service
from src.services.document_service import DocumentService

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


# ===== DOCUMENT LIST =====

@router.get("", response_model=List[DocumentMetadata])
async def list_documents(
    status: Optional[str] = Query(None, description="Filter by status"),
    document_type: Optional[str] = Query(None, description="Filter by type"),
    limit: int = Query(default=100, le=200),
    offset: int = Query(default=0, ge=0),
    service: DocumentService = Depends(get_document_service),
):
    """
    List documents from documents table.
    
    Thin wrapper - delegates to DocumentService.
    """
    try:
        documents = await service.list_documents(
            status=status,
            document_type=document_type,
            skip=offset,
            limit=limit
        )
        
        # Convert ORM to response schema
        return [doc.to_dict() for doc in documents]
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ List documents failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== CATALOG ENDPOINTS =====

@router.get("/catalog", response_model=List[DocumentSummary])
async def get_catalog(
    document_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    service: DocumentService = Depends(get_document_service),
):
    """Get document catalog (grouped by document_id)."""
    try:
        return await service.get_catalog(
            document_type=document_type,
            status=status,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        logger.error(f"❌ Get catalog failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/catalog/{document_id}", response_model=DocumentDetail)
async def get_document_detail(
    document_id: str,
    service: DocumentService = Depends(get_document_service),
):
    """Get complete document with all chunks."""
    detail = await service.get_document_detail(document_id)
    
    if not detail:
        raise HTTPException(
            status_code=404, 
            detail=f"Document {document_id} not found"
        )
    
    return detail


# ===== DOCUMENT METADATA =====

@router.get("/{document_id}", response_model=DocumentMetadata)
async def get_document(
    document_id: str,
    service: DocumentService = Depends(get_document_service),
):
    """Get document metadata from documents table."""
    doc = await service.get_document(document_id)
    
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"Document {document_id} not found"
        )
    
    return doc.to_dict()


# ===== UPDATE STATUS =====

@router.patch(
    "/{document_id}/status",
    response_model=UpdateDocumentStatusResponse
)
async def update_document_status(
    document_id: str,
    request: UpdateDocumentStatusRequest,
    service: DocumentService = Depends(get_document_service),
):
    """Update document status."""
    try:
        updated = await service.update_document_status(
            document_id=document_id,
            new_status=request.status,
            invalidate_cache=True
        )
        
        if not updated:
            raise HTTPException(
                status_code=404,
                detail=f"Document {document_id} not found"
            )
        
        return {
            "document_id": updated.document_id,
            "old_status": "N/A",  # Could track in service
            "new_status": updated.status,
            "updated_at": updated.updated_at.isoformat(),
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Update status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== STATISTICS =====

@router.get("/{document_id}/stats", response_model=DocumentStats)
async def get_document_stats(
    document_id: str,
    service: DocumentService = Depends(get_document_service),
):
    """Get document statistics."""
    stats = await service.get_document_stats(document_id)
    
    if not stats:
        raise HTTPException(
            status_code=404,
            detail=f"Document {document_id} not found"
        )
    
    return stats
```

**Reduction:** 814 → 150 lines (~81% reduction!)

**Changes:**
- ❌ Raw SQL queries removed
- ✅ Service layer injection via `Depends()`
- ✅ Thin controllers (routing only)
- ✅ Business logic in service
- ✅ Data access in repository

---

### 3.2 Create Response Schemas

**File:** `src/api/schemas/document_schemas.py` (MOVE from router)

```python
"""
Document API Schemas
Pydantic models for request/response validation
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class DocumentMetadata(BaseModel):
    """Document metadata from documents table."""
    document_id: str
    document_name: str
    document_type: str
    category: str
    file_name: str
    total_chunks: int
    status: str
    created_at: str
    updated_at: str


class DocumentSummary(BaseModel):
    """Document catalog summary (aggregated)."""
    document_id: str
    title: str
    document_type: str
    total_chunks: int
    status: Optional[str] = None
    published_date: Optional[str] = None
    effective_date: Optional[str] = None
    chunk_ids: List[str]
    created_at: Optional[str] = None


class DocumentDetail(BaseModel):
    """Complete document with chunks."""
    document_id: str
    title: str
    document_type: str
    total_chunks: int
    status: Optional[str] = None
    metadata: Dict[str, Any]
    chunks: List[Dict[str, Any]]


class DocumentStats(BaseModel):
    """Document statistics."""
    document_id: str
    filename: str
    status: str
    total_chunks: int
    file_size: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UpdateDocumentStatusRequest(BaseModel):
    """Update status request."""
    status: str = Field(..., description="New status: active, archived, deleted")


class UpdateDocumentStatusResponse(BaseModel):
    """Update status response."""
    document_id: str
    old_status: str
    new_status: str
    updated_at: str
```

---

### Phase 3 Deliverables

**Files Refactored:**
- `src/api/routers/documents.py` - 814 → 150 lines
- `src/api/schemas/document_schemas.py` - NEW (moved from router)

**Deleted:**
- `src/api/routers/documents_management.py` (replaced)

**Tests:**
- Update existing endpoint tests to use new paths
- All API tests should still pass (same contracts)

**Migration Path:**
1. Keep old file for 1 sprint (mark deprecated)
2. Update all imports to new path
3. Run full test suite
4. Delete old file

---

## **PHASE 4: Testing & Validation** (Day 4, ~4 hours)

### 4.1 Unit Tests

**Repository Tests:**
```
scripts/tests/test_repositories/
├── test_base_repository.py          # Base CRUD operations
├── test_document_repository.py      # Document-specific queries
└── test_vector_repository.py        # Chunk aggregations
```

**Service Tests:**
```
scripts/tests/test_services/
├── test_document_service.py         # Business logic validation
└── test_mocks.py                    # Mock repositories
```

**Integration Tests:**
```
scripts/tests/integration/
└── test_document_api_refactored.py  # End-to-end API tests
```

### 4.2 Performance Benchmarks

**Before/After Comparison:**
```python
# scripts/tests/performance/benchmark_refactoring.py

import asyncio
import time
from src.config.database import get_db_async

async def benchmark_old_sql():
    """Benchmark old raw SQL approach."""
    # ... measure time

async def benchmark_new_orm():
    """Benchmark new ORM approach."""
    # ... measure time

# Compare:
# - Query execution time
# - Memory usage
# - Database connections
```

**Acceptance Criteria:**
- ORM performance within 10% of raw SQL
- Memory usage stable
- No N+1 query issues

### 4.3 API Contract Validation

**Ensure backward compatibility:**
```bash
# Test all endpoints return same structure
pytest scripts/tests/integration/test_api_contracts.py -v

# Expected: 100% pass rate
```

---

## **PHASE 5: Migration & Cleanup** (Day 5, ~3 hours)

### 5.1 Gradual Migration

**Step 1: Deploy alongside old code**
- Keep `documents_management.py` with `@deprecated` decorator
- New endpoints in `documents.py`
- Both work simultaneously

**Step 2: Update clients**
- Update frontend/API clients to new paths
- Monitor old endpoint usage (logging)

**Step 3: Remove old code**
- After 1 week, delete `documents_management.py`
- Clean up unused imports

### 5.2 Update Documentation

**Files to Update:**
- `README.md` - New architecture diagram
- `documents/System Design/` - Architecture docs
- API documentation (OpenAPI/Swagger)

### 5.3 Performance Monitoring

**Add metrics:**
```python
# In DocumentService
import time

async def list_documents(self, ...):
    start = time.time()
    result = await self.doc_repo.list_documents(...)
    duration = time.time() - start
    
    logger.info(f"📊 list_documents took {duration*1000:.2f}ms")
    return result
```

---

## 📊 Success Metrics

### Code Quality
- [ ] Lines of code in routers reduced by >70%
- [ ] Raw SQL in routers reduced to 0%
- [ ] Test coverage >80% for new code
- [ ] No circular dependencies

### Performance
- [ ] API response time within 10% of current
- [ ] Database query count unchanged or reduced
- [ ] Memory usage stable

### Maintainability
- [ ] New feature can be added in single layer (service or repository)
- [ ] Onboarding time for new devs reduced
- [ ] Bug fix time reduced (easier to locate logic)

---

## 🚨 Risks & Mitigation

### Risk 1: Performance Regression
**Impact:** High  
**Probability:** Medium  
**Mitigation:**
- Benchmark before/after each phase
- Optimize ORM queries (use `joinedload`, `selectinload`)
- Keep complex JSONB queries as raw SQL in repository

### Risk 2: Breaking Changes
**Impact:** High  
**Probability:** Low  
**Mitigation:**
- Maintain API contract compatibility
- Comprehensive integration tests
- Gradual migration with old code deprecation

### Risk 3: Testing Gaps
**Impact:** Medium  
**Probability:** Medium  
**Mitigation:**
- Write tests BEFORE refactoring
- Mock repositories in service tests
- End-to-end API tests

### Risk 4: Team Learning Curve
**Impact:** Medium  
**Probability:** Medium  
**Mitigation:**
- Document patterns in code comments
- Code review sessions
- Example implementations

---

## 📅 Timeline Summary

| Phase | Duration | Deliverable | Risk |
|-------|----------|-------------|------|
| Phase 1: Repositories | 4h | Base + 3 repositories | Low |
| Phase 2: Services | 6h | DocumentService + DI | Medium |
| Phase 3: Routers | 5h | Slim controllers | Medium |
| Phase 4: Testing | 4h | Full test suite | Low |
| Phase 5: Migration | 3h | Production deployment | High |
| **Total** | **22h** | **Clean architecture** | **Medium** |

---

## 🎯 Next Actions

### Immediate (Start Phase 1)
1. Create `src/repositories/base.py`
2. Expand `src/repositories/document_repository.py`
3. Create `src/repositories/vector_repository.py`
4. Write repository tests

### Week 1
- Complete Phases 1-3
- Run full test suite
- Deploy to staging

### Week 2
- Monitor performance
- Fix issues
- Deploy to production
- Delete deprecated code

---

## 📚 References

- **Industry Patterns:** Clean Architecture (Uncle Bob), DDD (Eric Evans)
- **FastAPI Best Practices:** https://github.com/zhanymkanov/fastapi-best-practices
- **SQLAlchemy Async:** https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- **Repository Pattern:** https://martinfowler.com/eaaCatalog/repository.html

---

**End of Refactoring Plan**
