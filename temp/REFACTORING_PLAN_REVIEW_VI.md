# Đánh Giá Chi Tiết - Plan Refactoring Kiến Trúc

**Ngày đánh giá:** 12 tháng 12, 2025  
**Plan version:** 1.0  
**Người đánh giá:** AI Analysis  
**Kết luận:** ✅ Plan khả thi nhưng cần bổ sung một số điểm quan trọng

---

## 📊 Tổng Quan Đánh Giá

### Điểm Mạnh (Strengths) ✅

| Khía cạnh | Đánh giá | Lý do |
|-----------|----------|-------|
| **Chiến lược phân pha** | ⭐⭐⭐⭐⭐ | Migration từng bước, giảm risk, có thể rollback |
| **Tách biệt concerns** | ⭐⭐⭐⭐⭐ | Repository → Service → Router rõ ràng |
| **Backward compatibility** | ⭐⭐⭐⭐⭐ | Giữ API contract, zero downtime |
| **Testing strategy** | ⭐⭐⭐⭐ | Unit → Integration → E2E |
| **Timeline estimate** | ⭐⭐⭐⭐ | 22h hợp lý, có breakdown chi tiết |

### Vấn Đề Quan Trọng (Critical Issues) ⚠️

1. **Sync vs Async mismatch** 🔴 - Repository hiện tại dùng sync, plan dùng async
2. **Transaction management unclear** 🟡 - Chưa rõ cách handle transactions
3. **Error handling missing** 🟡 - Thiếu standardized error handling
4. **Cache invalidation TODO** 🔴 - Chưa implement, chỉ có placeholder
5. **Existing code ignored** 🟡 - Bỏ qua 122 lines code repository đã có
6. **Raw SQL policy quá strict** 🟡 - Một số queries nên giữ raw SQL

---

## 🔴 Vấn Đề 1: Sync vs Async Mismatch - NGHIÊM TRỌNG

### Hiện Trạng

**Repository hiện tại** (`src/models/repositories.py`):
```python
class DocumentRepository:
    @staticmethod
    def get_all(db: Session, ...) -> List[Document]:  # ❌ SYNC
        query = db.query(Document)  # sync SQLAlchemy
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def get_stats(db: Session) -> Dict[str, Any]:  # ❌ SYNC
        total = db.query(func.count(Document.id)).scalar()
        return {"total_documents": total}
```

**Plan đề xuất** (base.py):
```python
class BaseRepository(Generic[ModelType]):
    async def get_all(self, db: AsyncSession, ...) -> List[ModelType]:  # ✅ ASYNC
        query = select(self.model)
        result = await self.db.execute(query)  # async SQLAlchemy 2.0
        return result.scalars().all()
```

### Vấn Đề

1. **Toàn bộ FastAPI routers đang dùng `async def` và `AsyncSession`**
2. **Repository hiện tại dùng sync `Session`** → Không tương thích
3. **Plan không đề cập migration path** từ sync → async

### Tác Động

- ❌ Không thể dùng existing repository code
- ❌ Phải rewrite toàn bộ 122 lines
- ❌ Risk cao khi test lại tất cả queries

### Giải Pháp Đề Xuất

**Thêm Phase 0.5: Migration Prep (2 giờ)**

```python
# BEFORE (sync - current):
@staticmethod
def get_by_id(db: Session, document_id: str) -> Optional[Document]:
    return db.query(Document).filter(Document.document_id == document_id).first()

# AFTER (async - migrated):
async def get_by_id(self, document_id: str) -> Optional[Document]:
    result = await self.db.execute(
        select(Document).where(Document.document_id == document_id)
    )
    return result.scalar_one_or_none()
```

**Checklist Phase 0.5:**
- [ ] Convert all `@staticmethod` → instance methods
- [ ] Add `async` keyword to all methods
- [ ] Change `db.query()` → `await db.execute(select())`
- [ ] Change `.first()` → `scalar_one_or_none()`
- [ ] Change `.all()` → `scalars().all()`
- [ ] Update `Session` → `AsyncSession` in type hints
- [ ] Test mỗi method riêng lẻ

**Estimate:** +2 giờ  
**Risk mitigation:** Test từng method trước khi continue

---

## 🟡 Vấn Đề 2: Raw SQL Policy Quá Strict

### Plan Hiện Tại

**Success Metrics:**
- ✅ 0 raw SQL queries in routers
- ✅ **100% ORM usage for documents table** ← Quá strict!

### Vấn Đề

Một số queries **NÊN GIỮ** raw SQL vì:

#### A. JSONB Aggregation Queries (Vector Catalog)

```python
# Plan đúng khi giữ raw SQL ở VectorRepository:
async def get_catalog_summary(self, ...):
    query = text("""
        WITH document_groups AS (
            SELECT 
                cmetadata->>'document_id' as document_id,
                COUNT(*) as chunk_count,
                array_agg(id ORDER BY ...) as chunk_ids
            FROM langchain_pg_embedding
            GROUP BY cmetadata->>'document_id'  -- ❌ Khó convert sang ORM
        )
        SELECT * FROM document_groups
    """)
```

**Lý do giữ raw SQL:**
- JSONB operations (`->`, `->>`) phức tạp trong ORM
- GROUP BY trên JSONB field
- Array aggregation (`array_agg`)
- Performance-critical endpoint
- Không có ORM model cho `langchain_pg_embedding` (do LangChain manage)

#### B. Full-Text Search (Tương lai)

```sql
-- PostgreSQL full-text search với Vietnamese:
SELECT * FROM documents 
WHERE to_tsvector('vietnamese', document_name) 
      @@ to_tsquery('vietnamese', :search_query)
ORDER BY ts_rank(to_tsvector(...), to_tsquery(...)) DESC
```

**Lý do giữ raw SQL:**
- PostgreSQL full-text search functions
- Custom text search configuration
- ORM không support native FTS operators

#### C. Complex Analytics Queries

```sql
-- Document statistics với window functions:
SELECT 
    document_type,
    COUNT(*) as total,
    AVG(file_size) OVER (PARTITION BY category) as avg_size_by_category,
    RANK() OVER (ORDER BY created_at DESC) as recency_rank
FROM documents
```

### Khuyến Nghị

**Cập nhật Success Metrics:**

❌ **Cũ (quá strict):**
- 100% ORM usage for documents table

✅ **Mới (realistic):**
- 100% ORM cho CRUD operations trên `documents` table
- Raw SQL được phép **CHỈ TRONG REPOSITORIES** cho:
  - JSONB operations (vector_repository)
  - Complex aggregations với window functions
  - Full-text search
  - Performance-critical queries đã được benchmark
- 0% raw SQL trong routers và services
- Mọi raw SQL phải có comment giải thích lý do

**Quy tắc vàng:**
```python
# ✅ OK - Raw SQL trong repository với comment:
class VectorRepository:
    async def get_catalog(self):
        # Raw SQL required: JSONB aggregation không support tốt trong ORM
        query = text("SELECT cmetadata->>'document_id' FROM ...")
        
# ❌ NOT OK - Raw SQL trong service:
class DocumentService:
    async def list_docs(self):
        query = text("SELECT * FROM documents")  # Dùng ORM!

# ❌ NOT OK - Raw SQL trong router:
@router.get("/documents")
async def list_docs(db: AsyncSession):
    result = await db.execute(text("SELECT ..."))  # Dùng service!
```

---

## 🟡 Vấn Đề 3: Error Handling Thiếu Chuẩn Hóa

### Plan Hiện Tại

**Service layer:**
```python
async def update_document_status(self, document_id, new_status):
    if new_status not in ["active", "archived", "deleted"]:
        raise ValueError("Invalid status")  # ❌ Generic exception
```

**Router layer:**
```python
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))  # ❌ Exposes internals
```

### Vấn Đề

1. **Inconsistent exceptions** - Dùng `ValueError`, `Exception` generic
2. **Không distinguish** giữa client errors (400) vs server errors (500)
3. **Expose internal details** - `str(e)` có thể leak database errors
4. **Không có error codes** - Frontend không biết handle cụ thể

### Giải Pháp

**Thêm vào Phase 2: Custom Exception Hierarchy**

**File:** `src/services/exceptions.py` (NEW)

```python
"""
Service Layer Exceptions
Domain-specific errors cho business logic
"""

class ServiceError(Exception):
    """Base exception cho tất cả service errors."""
    def __init__(self, message: str, code: str = None):
        self.message = message
        self.code = code
        super().__init__(message)


# ===== 4XX Client Errors =====

class NotFoundError(ServiceError):
    """Resource không tồn tại (404)."""
    def __init__(self, resource: str, id: str):
        super().__init__(
            message=f"{resource} with id '{id}' not found",
            code="NOT_FOUND"
        )


class ValidationError(ServiceError):
    """Input validation failed (400)."""
    def __init__(self, field: str, message: str):
        super().__init__(
            message=f"Validation failed for '{field}': {message}",
            code="VALIDATION_ERROR"
        )


class InvalidStatusError(ValidationError):
    """Document status không hợp lệ."""
    def __init__(self, status: str, valid_statuses: list):
        super().__init__(
            field="status",
            message=f"Invalid status '{status}'. Must be one of: {valid_statuses}"
        )


class DuplicateError(ServiceError):
    """Resource đã tồn tại (409)."""
    def __init__(self, resource: str, field: str, value: str):
        super().__init__(
            message=f"{resource} with {field}='{value}' already exists",
            code="DUPLICATE"
        )


# ===== 5XX Server Errors =====

class DatabaseError(ServiceError):
    """Database operation failed (500)."""
    def __init__(self, operation: str, details: str = None):
        message = f"Database {operation} failed"
        if details:
            message += f": {details}"
        super().__init__(message, code="DATABASE_ERROR")


class CacheError(ServiceError):
    """Cache operation failed (500)."""
    pass
```

**Sử dụng trong Service:**

```python
from src.services.exceptions import (
    NotFoundError, 
    InvalidStatusError,
    DatabaseError
)

class DocumentService:
    async def update_document_status(self, document_id: str, new_status: str):
        # Validate status
        valid_statuses = ["active", "archived", "deleted"]
        if new_status not in valid_statuses:
            raise InvalidStatusError(new_status, valid_statuses)  # ✅ Specific
        
        # Get document
        doc = await self.doc_repo.get_by_document_id(document_id)
        if not doc:
            raise NotFoundError("Document", document_id)  # ✅ Clear
        
        try:
            return await self.doc_repo.update_status(document_id, new_status)
        except Exception as e:
            raise DatabaseError("update", str(e))  # ✅ Wrapped
```

**Error Handling trong Router:**

```python
from fastapi import HTTPException
from src.services.exceptions import (
    NotFoundError, 
    ValidationError, 
    ServiceError
)

@router.patch("/{document_id}/status")
async def update_status(
    document_id: str,
    request: UpdateStatusRequest,
    service: DocumentService = Depends(get_document_service)
):
    try:
        return await service.update_document_status(
            document_id, 
            request.status
        )
    
    # ===== Client Errors (4XX) =====
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail={
            "code": e.code,
            "message": e.message
        })
    
    except ValidationError as e:
        raise HTTPException(status_code=400, detail={
            "code": e.code,
            "message": e.message
        })
    
    # ===== Server Errors (5XX) =====
    except ServiceError as e:
        logger.error(f"Service error: {e.message}", exc_info=True)
        raise HTTPException(status_code=500, detail={
            "code": e.code,
            "message": "Internal server error"  # ✅ Don't leak details
        })
    
    # ===== Unexpected Errors =====
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred"
        })
```

**Lợi ích:**
- ✅ Consistent error structure
- ✅ Proper HTTP status codes
- ✅ Error codes cho frontend
- ✅ Không leak database errors
- ✅ Structured error responses

---

## 🔴 Vấn Đề 4: Transaction Management Không Rõ Ràng

### Plan Hiện Tại

**Service layer mention:**
> "Transaction management" - nhưng không có implementation

**Example trong plan:**
```python
async def update_document_status(self, ...):
    # Update documents table
    doc = await self.doc_repo.update_status(document_id, status)
    
    # Invalidate cache
    await self._invalidate_cache(document_id)
    
    # ❌ Nếu cache fails thì sao?
    # ❌ Document đã update nhưng cache chưa clear
    # ❌ Inconsistent state!
```

### Vấn Đề

1. **Không có transaction boundaries** - Unclear khi nào commit/rollback
2. **Multiple operations** không atomic - Document update + cache invalidation
3. **Repository instances riêng** - Không share same database session
4. **Error recovery unclear** - Nếu step 2 fails, step 1 đã commit chưa?

### Giải Pháp

#### A. Update Dependency Injection - Share Session

**File:** `src/api/dependencies.py`

```python
def get_document_service(
    db: AsyncSession = Depends(get_db)  # ← Inject session directly
) -> DocumentService:
    """
    Get DocumentService với shared database session.
    
    Transaction scope được manage bởi FastAPI dependency:
    - Session start: Khi request bắt đầu
    - Session commit: Khi response success
    - Session rollback: Khi exception raised
    """
    # All repositories share SAME session
    doc_repo = DocumentRepository(db)
    vector_repo = VectorRepository(db)
    
    # Pass db session to service for transaction control
    return DocumentService(
        doc_repo=doc_repo,
        vector_repo=vector_repo,
        db=db  # ← Service có thể manage transactions
    )
```

#### B. Transaction Patterns trong Service

**Pattern 1: Implicit Transaction (FastAPI Managed)**

```python
class DocumentService:
    def __init__(self, doc_repo, vector_repo, db: AsyncSession):
        self.doc_repo = doc_repo
        self.vector_repo = vector_repo
        self.db = db
    
    async def update_document_status(self, document_id: str, status: str):
        """
        Transaction được manage tự động bởi FastAPI.
        
        Nếu method này raise exception → FastAPI rollback toàn bộ.
        Nếu method return success → FastAPI commit.
        """
        # Step 1: Update document
        doc = await self.doc_repo.update_status(document_id, status)
        if not doc:
            raise NotFoundError("Document", document_id)
        
        # Step 2: Update related chunks (same transaction)
        await self.vector_repo.update_chunk_metadata(
            document_id, 
            {"status": status}
        )
        
        # ✅ Both operations commit together
        # ❌ If step 2 fails → both rollback
        
        return doc
```

**Pattern 2: Explicit Transaction (Manual Control)**

```python
async def complex_multi_step_operation(self, ...):
    """
    Explicit transaction khi cần control commit points.
    """
    async with self.db.begin():  # ← Explicit transaction
        # Step 1: Create document
        doc = await self.doc_repo.create(...)
        
        # Step 2: Create chunks
        for chunk in chunks:
            await self.vector_repo.insert_chunk(doc.document_id, chunk)
        
        # Step 3: Update statistics
        await self.doc_repo.update_stats(doc.document_id, len(chunks))
        
        # ✅ All 3 steps commit together
        # ❌ If any fails → all rollback
    
    # Step 4: Cache operations AFTER commit
    # (Cache failures không rollback database)
    try:
        await self._invalidate_cache(doc.document_id)
    except CacheError:
        logger.warning("Cache invalidation failed, but DB committed")
```

**Pattern 3: Nested Transactions (Savepoints)**

```python
async def bulk_operation_with_partial_rollback(self, items: List[Dict]):
    """
    Nested transactions cho bulk operations.
    Một số items có thể fail mà không affect others.
    """
    results = {"success": [], "failed": []}
    
    async with self.db.begin():  # Outer transaction
        for item in items:
            try:
                async with self.db.begin_nested():  # Savepoint
                    doc = await self.doc_repo.create(**item)
                    results["success"].append(doc.document_id)
            except Exception as e:
                # Rollback to savepoint, outer transaction continues
                results["failed"].append({"item": item, "error": str(e)})
        
        # Commit all successful items
    
    return results
```

#### C. Cache Operations - Outside Transaction

```python
async def update_document_status(self, ...):
    # ===== DATABASE OPERATIONS (Transactional) =====
    async with self.db.begin():
        doc = await self.doc_repo.update_status(document_id, status)
        await self.vector_repo.update_chunk_status(document_id, status)
        # ✅ Commit together
    
    # ===== CACHE OPERATIONS (Non-transactional) =====
    # Chạy AFTER commit để tránh:
    # - Cache cleared nhưng DB rollback
    # - Inconsistent state
    try:
        await self._invalidate_cache(document_id)
    except CacheError as e:
        # Cache failure không critical
        logger.warning(f"Cache invalidation failed: {e}")
        # Document vẫn updated thành công
```

### Quy Tắc Transaction Management

| Operation Type | Transaction Scope | Rollback Behavior |
|----------------|-------------------|-------------------|
| **Database writes** | Inside transaction | Rollback on error |
| **Database reads** | No transaction needed | N/A |
| **Multiple DB writes** | Same transaction | All-or-nothing |
| **Cache operations** | Outside transaction | Don't rollback DB |
| **External API calls** | Outside transaction | Don't rollback DB |
| **File operations** | Outside transaction | Manual cleanup |

---

## 🔴 Vấn Đề 5: Cache Invalidation Chưa Implement

### Plan Hiện Tại

```python
async def _invalidate_document_cache(self, document_id: str):
    # TODO: Implement cache invalidation
    logger.info(f"🗑️ Cache invalidated for: {document_id}")
```

**Vấn đề:** Chỉ là placeholder, không có implementation thật!

### Tác Động

- Document status updated nhưng cached data vẫn cũ
- Retriever trả về stale results
- User thấy data inconsistent

### Giải Pháp

**Thêm Phase 2: Cache Service Implementation**

**File:** `src/services/cache_service.py` (NEW)

```python
"""
Cache Service
Centralized cache invalidation logic
"""
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class CacheService:
    """
    Service để manage cache invalidation.
    
    Supports:
    - LangChain retriever cache
    - Redis cache (nếu có)
    - In-memory caches
    """
    
    @staticmethod
    async def invalidate_document(document_id: str) -> bool:
        """
        Invalidate tất cả cache liên quan tới document.
        
        Returns: True nếu success, False nếu có lỗi
        """
        try:
            success = True
            
            # 1. Clear LangChain retriever cache
            success &= await CacheService._clear_retriever_cache(document_id)
            
            # 2. Clear Redis cache (nếu enabled)
            success &= await CacheService._clear_redis_cache(document_id)
            
            # 3. Clear in-memory caches
            success &= await CacheService._clear_memory_cache(document_id)
            
            if success:
                logger.info(f"✅ Cache invalidated for document: {document_id}")
            else:
                logger.warning(f"⚠️ Partial cache invalidation for: {document_id}")
            
            return success
        
        except Exception as e:
            logger.error(f"❌ Cache invalidation failed: {e}")
            return False
    
    @staticmethod
    async def _clear_retriever_cache(document_id: str) -> bool:
        """Clear LangChain retriever cache."""
        try:
            from src.retrieval.cached_retrieval import cached_retriever
            
            if hasattr(cached_retriever, '_cache'):
                # Find all cache keys containing document_id
                keys_to_delete = [
                    key for key in cached_retriever._cache.keys()
                    if document_id in str(key)
                ]
                
                for key in keys_to_delete:
                    del cached_retriever._cache[key]
                
                logger.debug(f"Cleared {len(keys_to_delete)} retriever cache entries")
            
            return True
        
        except Exception as e:
            logger.error(f"Retriever cache clear failed: {e}")
            return False
    
    @staticmethod
    async def _clear_redis_cache(document_id: str) -> bool:
        """Clear Redis cache entries."""
        try:
            from src.config.feature_flags import ENABLE_REDIS_SESSIONS
            
            if not ENABLE_REDIS_SESSIONS:
                return True  # No Redis, skip
            
            import redis
            r = redis.Redis(host='localhost', port=6379, db=0)
            
            # Find keys matching pattern
            pattern = f"*{document_id}*"
            keys = r.keys(pattern)
            
            if keys:
                r.delete(*keys)
                logger.debug(f"Cleared {len(keys)} Redis cache entries")
            
            return True
        
        except Exception as e:
            logger.error(f"Redis cache clear failed: {e}")
            return False
    
    @staticmethod
    async def _clear_memory_cache(document_id: str) -> bool:
        """Clear in-memory caches."""
        try:
            # Clear any module-level caches
            # Example: Document name mapping cache
            from src.api.routers.documents_management import DOCUMENT_NAME_MAPPING
            
            if document_id in DOCUMENT_NAME_MAPPING:
                del DOCUMENT_NAME_MAPPING[document_id]
            
            return True
        
        except Exception as e:
            logger.error(f"Memory cache clear failed: {e}")
            return False
    
    @staticmethod
    async def invalidate_all() -> bool:
        """Clear ALL caches (use with caution!)."""
        logger.warning("🗑️ CLEARING ALL CACHES")
        
        try:
            # Clear retriever
            from src.retrieval.cached_retrieval import cached_retriever
            if hasattr(cached_retriever, '_cache'):
                cached_retriever._cache.clear()
            
            # Clear Redis
            import redis
            r = redis.Redis(host='localhost', port=6379, db=0)
            r.flushdb()
            
            logger.info("✅ All caches cleared")
            return True
        
        except Exception as e:
            logger.error(f"❌ Clear all caches failed: {e}")
            return False
```

**Sử dụng trong DocumentService:**

```python
from src.services.cache_service import CacheService

class DocumentService:
    async def update_document_status(self, ...):
        # Database update
        doc = await self.doc_repo.update_status(document_id, status)
        
        # Cache invalidation (after DB commit)
        cache_cleared = await CacheService.invalidate_document(document_id)
        
        if not cache_cleared:
            logger.warning(f"Cache invalidation failed for {document_id}")
            # Không raise exception - cache failure không critical
        
        return doc
```

---

## 🟡 Vấn Đề 6: Bỏ Qua Code Repository Hiện Có

### Hiện Trạng

**File:** `src/models/repositories.py` - 122 lines code đang hoạt động:

```python
class DocumentRepository:
    @staticmethod
    def get_by_id(db: Session, document_id: str): ...      # ✅ Working
    
    @staticmethod
    def get_all(db: Session, ...): ...                     # ✅ Working
    
    @staticmethod
    def create(db: Session, **kwargs): ...                 # ✅ Working
    
    @staticmethod
    def update(db: Session, document_id: str, ...): ...    # ✅ Working
    
    @staticmethod
    def delete(db: Session, document_id: str, ...): ...    # ✅ Working
    
    @staticmethod
    def get_stats(db: Session): ...                        # ✅ Working
    
    @staticmethod
    def search(db: Session, search_term: str): ...         # ✅ Working
```

### Plan Hiện Tại

> "Create base.py" + "Expand document_repository.py"

**Vấn đề:**
- Plan không đề cập migrate existing code
- Risk: Duplicate implementations
- Waste: Viết lại code đã có

### Khuyến Nghị

**Phase 1 nên là MIGRATE, không phải CREATE:**

**Step 1: Convert Sync → Async**
```python
# BEFORE (sync):
@staticmethod
def get_by_id(db: Session, document_id: str) -> Optional[Document]:
    return db.query(Document).filter(...).first()

# AFTER (async):
async def get_by_id(self, document_id: str) -> Optional[Document]:
    result = await self.db.execute(select(Document).where(...))
    return result.scalar_one_or_none()
```

**Step 2: Convert Static → Instance Methods**
```python
# BEFORE:
class DocumentRepository:
    @staticmethod
    def get_all(db: Session, ...): ...

# AFTER:
class DocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_all(self, ...): ...
```

**Step 3: Refactor to Use BaseRepository (Optional)**
```python
from .base import BaseRepository

class DocumentRepository(BaseRepository[Document]):
    def __init__(self, db: AsyncSession):
        super().__init__(Document, db)
    
    # Inherit: get_by_id, get_all, create, update, delete
    
    # Custom methods:
    async def get_by_document_id(self, document_id: str): ...
    async def search(self, term: str): ...
```

---

## 🟡 Vấn Đề 7: Upload Service Refactor Thiếu Chi Tiết

### Plan Hiện Tại

> "upload_service.py - REFACTOR - Use repository"

**Không đề cập:**
- Cách migrate từ raw SQL INSERT?
- Impact lên upload pipeline?
- Testing strategy?

### Upload Service Hiện Tại

**File:** `src/api/services/upload_service.py` - 525 lines

**Raw SQL ở line 471:**
```python
# Insert document metadata to documents table
query = text("""
    INSERT INTO documents (
        document_id, filename, document_name, document_type,
        category, file_size, total_chunks, status, created_at
    ) VALUES (
        :document_id, :filename, :document_name, :document_type,
        :category, :file_size, :total_chunks, :status, NOW()
    )
    ON CONFLICT (document_id) DO UPDATE SET
        updated_at = NOW()
""")

conn = get_db_sync()
conn.execute(query, {...})
conn.commit()
```

### Refactor Plan Chi Tiết

**Thêm Phase 2.5: Upload Service Migration (2 giờ)**

#### Step 1: Inject Repository

```python
class UploadProcessingService:
    def __init__(self, doc_repo: DocumentRepository = None):
        self.classifier = DocumentClassifier()
        self.embedder = OpenAIEmbedder()
        self.vector_store = PGVectorStore()
        
        # ✅ Repository injection
        self.doc_repo = doc_repo  # Will be set via dependency injection
```

#### Step 2: Replace Raw SQL

```python
# BEFORE (raw SQL):
query = text("""INSERT INTO documents (...) VALUES (...)""")
conn.execute(query, params)

# AFTER (repository):
doc = await self.doc_repo.create(
    document_id=document_id,
    filename=filename,
    document_name=document_name,
    document_type=doc_type,
    category=category,
    file_size=file_size,
    total_chunks=len(chunks),
    status="active"
)
```

#### Step 3: Handle ON CONFLICT

```python
# Option 1: Try create, catch duplicate
try:
    doc = await self.doc_repo.create(...)
except DuplicateError:
    doc = await self.doc_repo.update(document_id, updated_at=datetime.now())

# Option 2: Upsert method trong repository
doc = await self.doc_repo.upsert(
    document_id=document_id,
    defaults={...},
    update_on_conflict={
        "updated_at": datetime.now()
    }
)
```

#### Step 4: Update Dependencies

```python
# src/api/dependencies.py
def get_upload_service(
    doc_repo: DocumentRepository = Depends(get_document_repository)
) -> UploadProcessingService:
    service = UploadProcessingService()
    service.doc_repo = doc_repo  # Inject repository
    return service

# src/api/routers/upload.py
@router.post("/upload")
async def upload_files(
    files: List[UploadFile],
    service: UploadProcessingService = Depends(get_upload_service)
):
    return await service.upload_files(files)
```

---

## 📊 Plan Cập Nhật - Summary of Changes

### Thêm Phases Mới

| Phase | Original | Updated | Change |
|-------|----------|---------|--------|
| **0.5** | - | Migration Prep (2h) | **NEW** - Sync→Async |
| **1** | Repositories (4h) | Repositories (4h) | Same |
| **2** | Services (6h) | Services + Exceptions + Cache (8h) | **+2h** |
| **2.5** | - | Upload Service (2h) | **NEW** |
| **3** | Routers (5h) | Routers (5h) | Same |
| **4** | Testing (4h) | Testing (4h) | Same |
| **5** | Migration (3h) | Migration (3h) | Same |
| **Total** | **22h** | **28h** | **+6h** |

### Updated Success Metrics

| Metric | Original | Updated |
|--------|----------|---------|
| **Raw SQL in routers** | 0% | 0% ✅ |
| **ORM usage** | 100% | 100% for CRUD, raw SQL allowed in repos for JSONB ✅ |
| **Service coverage** | >90% | >90% ✅ |
| **Error handling** | - | Standardized with custom exceptions ✅ |
| **Transaction management** | Mentioned | Fully documented with patterns ✅ |
| **Cache invalidation** | TODO | Implemented CacheService ✅ |
| **Tests pass** | 100% | 100% ✅ |

### New Deliverables

**Phase 0.5:**
- [ ] Migrated repositories.py (sync → async)
- [ ] Updated all method signatures
- [ ] Unit tests for each method

**Phase 2 (expanded):**
- [ ] DocumentService (original)
- [ ] `src/services/exceptions.py` (NEW)
- [ ] `src/services/cache_service.py` (NEW)
- [ ] Error handling tests

**Phase 2.5:**
- [ ] Refactored upload_service.py
- [ ] Upsert method in repository
- [ ] Upload integration tests

---

## 🎯 Go/No-Go Decision Matrix

### ✅ GO Conditions (Recommended)

Accept plan **NẾU:**
- [ ] Chấp nhận timeline tăng 22h → 28h (+27%)
- [ ] Commit implement error handling đầy đủ
- [ ] Commit implement cache service (không để TODO)
- [ ] Có resources để test kỹ sync→async migration
- [ ] Team hiểu transaction patterns

### ❌ NO-GO Conditions

**KHÔNG** proceed nếu:
- [ ] Deadline hard < 4 ngày
- [ ] Không có time để implement cache service
- [ ] Team chưa familiar với async SQLAlchemy
- [ ] Không có comprehensive test suite
- [ ] Production traffic cao (risk downtime)

---

## 🚀 Recommended Next Actions

### Option A: Accept Updated Plan ⭐ (RECOMMENDED)

**Pros:**
- ✅ Complete implementation (không có TODOs)
- ✅ Proper error handling
- ✅ Transaction management clear
- ✅ Cache invalidation working
- ✅ Build on existing code

**Cons:**
- ❌ Timeline dài hơn (+6 hours)
- ❌ Phức tạp hơn (more files)

**Timeline:** 28 hours (~4-5 days)

### Option B: Minimal Plan (Fast Track)

**Scope:**
- Phase 1: Repositories only (async migration)
- Phase 3: Slim routers (use repositories directly, skip service layer)
- Skip: Error handling, cache service, transaction docs

**Timeline:** 12 hours (1.5-2 days)

**Risks:**
- ⚠️ Thiếu business logic layer
- ⚠️ Error handling inconsistent
- ⚠️ Cache invalidation broken

### Option C: Hybrid Approach

**Scope:**
- Phase 0.5 + 1: Repositories (6h)
- Phase 2: Basic DocumentService only (4h)
- Phase 3: Routers (5h)
- Leave: Error handling, cache as "Phase 2" later

**Timeline:** 15 hours (2-3 days)

**Pros:**
- ✅ Faster than full plan
- ✅ Core architecture in place
- ✅ Can add error handling later

---

## 📋 Final Checklist Before Starting

### Pre-Implementation

- [ ] Đọc kỹ toàn bộ plan review
- [ ] Chọn option (A/B/C)
- [ ] Confirm timeline với stakeholders
- [ ] Backup database (migration risk)
- [ ] Create feature branch: `refactor/layered-architecture`
- [ ] Setup staging environment cho testing

### During Implementation

- [ ] Commit sau mỗi phase
- [ ] Run tests sau mỗi change
- [ ] Document breaking changes
- [ ] Update API docs (Swagger)
- [ ] Monitor performance metrics

### Post-Implementation

- [ ] Full regression testing
- [ ] Performance benchmarks
- [ ] Code review
- [ ] Deploy to staging
- [ ] Monitor for 24h
- [ ] Deploy to production
- [ ] Delete deprecated code after 1 week

---

## 📚 Tài Liệu Tham Khảo

### Architecture Patterns
- [Clean Architecture - Uncle Bob](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Repository Pattern - Martin Fowler](https://martinfowler.com/eaaCatalog/repository.html)
- [Service Layer Pattern](https://martinfowler.com/eaaCatalog/serviceLayer.html)

### SQLAlchemy Async
- [SQLAlchemy 2.0 Async Tutorial](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [AsyncSession Best Practices](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html)

### FastAPI Best Practices
- [FastAPI Best Practices Guide](https://github.com/zhanymkanov/fastapi-best-practices)
- [FastAPI Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/)

### Error Handling
- [Python Custom Exceptions](https://docs.python.org/3/tutorial/errors.html#user-defined-exceptions)
- [FastAPI Error Handling](https://fastapi.tiangolo.com/tutorial/handling-errors/)

---

**Kết Luận:** Plan có nền tảng tốt, cần bổ sung 6 giờ để hoàn thiện các vấn đề critical. Recommend chọn **Option A (Updated Plan)** để đảm bảo chất lượng lâu dài.
