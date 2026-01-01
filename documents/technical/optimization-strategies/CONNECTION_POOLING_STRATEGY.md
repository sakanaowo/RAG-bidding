# 🏊‍♂️ CONNECTION POOLING STRATEGY

**Phương án tối ưu hóa database connection để tăng performance và scalability**

---

## 📊 HIỆN TRẠNG VÀ VẤN ĐỀ

### **Current Database Usage Pattern:**
- **PostgreSQL 18** + pgvector 0.8.1
- **Async operations** với FastAPI 2.0
- **Multiple concurrent operations:**
  - Upload processing (embedding generation + vector storage)
  - Query retrieval (vector search + metadata filtering)  
  - Real-time status tracking
  - Health checks

### **Identified Performance Bottlenecks:**
1. **Connection overhead**: Tạo/đóng connection cho mỗi query
2. **Concurrent load issues**: Multiple users → connection exhaustion
3. **Resource waste**: Idle connections không được reuse
4. **Scalability limits**: Limited by max_connections setting

---

## 🎯 PROPOSED SOLUTION: MULTI-LAYER CONNECTION POOLING

### **Architecture Overview:**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI App   │───▶│  Connection Pool │───▶│  PostgreSQL DB  │
│                 │    │     Manager      │    │                 │
│ - Upload API    │    │                  │    │ - Vector Store  │
│ - Query API     │    │ - Session Pool   │    │ - Metadata      │
│ - Status API    │    │ - Connection     │    │ - Indexes       │
│                 │    │   Validation     │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

---

## 🔧 IMPLEMENTATION STRATEGY

### **1. SQLAlchemy Async Engine với Connection Pooling**

**File: `src/config/database.py`**

```python
"""
Optimized Database Configuration với Connection Pooling
"""

import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine.events import event
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

class DatabaseConfig:
    """Centralized database configuration với connection pooling"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        
        # Connection Pool Configuration
        self.engine = create_async_engine(
            database_url,
            
            # Connection Pool Settings
            poolclass=QueuePool,
            pool_size=20,          # Core connections kept alive
            max_overflow=30,       # Additional connections when needed
            pool_recycle=3600,     # Recycle connections after 1 hour
            pool_pre_ping=True,    # Validate connections before use
            pool_reset_on_return='commit',  # Reset state on return
            
            # Performance Settings
            echo=False,            # Set True for SQL debugging
            echo_pool=False,       # Set True for pool debugging
            
            # Connection Settings
            connect_args={
                "server_settings": {
                    "application_name": "rag_bidding_app",
                    "jit": "off",  # Disable JIT for faster connection
                }
            }
        )
        
        # Session Factory
        self.SessionLocal = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=True,
            autocommit=False
        )
        
        # Setup connection pool monitoring
        self._setup_pool_monitoring()
    
    def _setup_pool_monitoring(self):
        """Setup connection pool monitoring và logging"""
        
        @event.listens_for(self.engine.sync_engine, "connect")
        def receive_connect(dbapi_connection, connection_record):
            logger.debug("New database connection established")
        
        @event.listens_for(self.engine.sync_engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            logger.debug("Connection checked out from pool")
        
        @event.listens_for(self.engine.sync_engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            logger.debug("Connection returned to pool")
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session from pool"""
        async with self.SessionLocal() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def test_connection(self) -> bool:
        """Test database connectivity"""
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    async def get_pool_status(self) -> dict:
        """Get connection pool status for monitoring"""
        pool = self.engine.pool
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid(),
        }
    
    async def close(self):
        """Close all connections and cleanup"""
        await self.engine.dispose()

# Global database instance
db_config: DatabaseConfig = None

def init_database(database_url: str):
    """Initialize database connection pool"""
    global db_config
    db_config = DatabaseConfig(database_url)
    logger.info("Database connection pool initialized")

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions"""
    if not db_config:
        raise RuntimeError("Database not initialized")
    
    async for session in db_config.get_session():
        yield session
```

### **2. Vector Store Connection Optimization**

**File: `src/embedding/store/pooled_pgvector_store.py`**

```python
"""
Optimized PGVector Store với connection pooling
"""

import asyncio
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_postgres import PGVector
from sqlalchemy.ext.asyncio import AsyncSession
from ..config.database import get_db
import logging

logger = logging.getLogger(__name__)

class PooledPGVectorStore:
    """PGVector store optimized với connection pooling"""
    
    def __init__(self, embeddings, collection_name: str = "docs"):
        self.embeddings = embeddings
        self.collection_name = collection_name
        self._connection_string = None
        
    def _get_sync_connection_string(self) -> str:
        """Get synchronous connection string for LangChain PGVector"""
        if not self._connection_string:
            from src.config.models import settings
            # Convert async URL to sync for LangChain compatibility
            self._connection_string = settings.database_url.replace(
                "postgresql+asyncpg://", "postgresql://"
            ).replace(
                "postgresql+psycopg://", "postgresql://"
            )
        return self._connection_string
    
    def get_vector_store(self) -> PGVector:
        """Get LangChain PGVector instance với optimized connection"""
        return PGVector(
            embeddings=self.embeddings,
            collection_name=self.collection_name,
            connection_string=self._get_sync_connection_string(),
            use_jsonb=True,
        )
    
    async def add_documents_batch(self, documents: List[Document], 
                                batch_size: int = 100) -> List[str]:
        """Add documents in batches để tối ưu performance"""
        vector_store = self.get_vector_store()
        
        # Process in batches to avoid overwhelming the connection pool
        document_ids = []
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}: {len(batch)} documents")
            
            batch_ids = vector_store.add_documents(batch)
            document_ids.extend(batch_ids)
            
            # Small delay between batches to prevent connection exhaustion
            if i + batch_size < len(documents):
                await asyncio.sleep(0.1)
        
        logger.info(f"Successfully added {len(document_ids)} documents")
        return document_ids
    
    async def similarity_search_with_score(self, query: str, k: int = 5, 
                                         filter: Optional[Dict] = None) -> List[tuple]:
        """Async similarity search với connection pooling"""
        vector_store = self.get_vector_store()
        
        # Use connection pool efficiently
        return vector_store.similarity_search_with_score(
            query=query, 
            k=k, 
            filter=filter
        )
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics using pooled connection"""
        async for session in get_db():
            try:
                # Use raw SQL for efficient stats gathering
                result = await session.execute(text("""
                    SELECT 
                        COUNT(*) as total_documents,
                        COUNT(DISTINCT metadata->>'document') as unique_documents,
                        AVG(array_length(embedding, 1)) as avg_embedding_dim
                    FROM langchain_pg_embedding 
                    WHERE collection_id = (
                        SELECT uuid FROM langchain_pg_collection 
                        WHERE name = :collection_name
                    )
                """), {"collection_name": self.collection_name})
                
                row = result.fetchone()
                return {
                    "total_documents": row[0] if row else 0,
                    "unique_documents": row[1] if row else 0,
                    "avg_embedding_dim": int(row[2]) if row and row[2] else 0
                }
            except Exception as e:
                logger.error(f"Failed to get collection stats: {e}")
                return {}
```

### **3. FastAPI Integration với Dependency Injection**

**File: `src/api/dependencies.py`**

```python
"""
FastAPI Dependencies với optimized database access
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.config.database import get_db, db_config
from src.embedding.store.pooled_pgvector_store import PooledPGVectorStore
from src.embedding.embedders.openai_embedder import OpenAIEmbedder
import logging

logger = logging.getLogger(__name__)

# Singleton instances
_vector_store: PooledPGVectorStore = None
_embedder: OpenAIEmbedder = None

async def get_database_session() -> AsyncSession:
    """Get database session dependency"""
    async for session in get_db():
        yield session

async def get_vector_store() -> PooledPGVectorStore:
    """Get vector store dependency với connection pooling"""
    global _vector_store, _embedder
    
    if _vector_store is None:
        if _embedder is None:
            _embedder = OpenAIEmbedder()
        _vector_store = PooledPGVectorStore(_embedder)
        logger.info("Vector store initialized with connection pooling")
    
    return _vector_store

async def get_pool_health() -> dict:
    """Get connection pool health status"""
    if db_config:
        pool_status = await db_config.get_pool_status()
        connection_test = await db_config.test_connection()
        
        return {
            "pool_status": pool_status,
            "connection_healthy": connection_test,
            "pool_utilization": {
                "usage_percent": (pool_status["checked_out"] / 
                                (pool_status["pool_size"] + pool_status["overflow"])) * 100,
                "available_connections": pool_status["pool_size"] - pool_status["checked_out"]
            }
        }
    return {"error": "Database not initialized"}
```

---

## 📈 PERFORMANCE OPTIMIZATIONS

### **4. Query Optimization với Prepared Statements**

```python
"""
Optimized query patterns với connection reuse
"""

class OptimizedQueries:
    """Pre-compiled queries cho better performance"""
    
    # Vector similarity search với index hints
    SIMILARITY_SEARCH = text("""
        SELECT 
            document, metadata, embedding <-> :query_embedding as distance
        FROM langchain_pg_embedding 
        WHERE collection_id = :collection_id
            AND (:filter_clause IS NULL OR metadata @> :filter_clause)
        ORDER BY embedding <-> :query_embedding
        LIMIT :k
    """)
    
    # Batch document insertion
    BATCH_INSERT = text("""
        INSERT INTO langchain_pg_embedding 
            (collection_id, document, metadata, embedding, uuid)
        VALUES 
            (:collection_id, :document, :metadata, :embedding, :uuid)
    """)
    
    # Collection statistics
    COLLECTION_STATS = text("""
        SELECT 
            COUNT(*) as total_docs,
            COUNT(DISTINCT metadata->>'source') as unique_sources,
            AVG(LENGTH(document)) as avg_doc_length
        FROM langchain_pg_embedding 
        WHERE collection_id = :collection_id
    """)
```

### **5. Monitoring và Health Checks**

**File: `src/api/routers/monitoring.py`**

```python
"""
Database monitoring endpoints
"""

from fastapi import APIRouter, Depends
from src.api.dependencies import get_pool_health, get_vector_store

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])

@router.get("/pool-status")
async def get_connection_pool_status():
    """Get detailed connection pool status"""
    return await get_pool_health()

@router.get("/database-stats")
async def get_database_stats(vector_store = Depends(get_vector_store)):
    """Get database và collection statistics"""
    stats = await vector_store.get_collection_stats()
    pool_health = await get_pool_health()
    
    return {
        "collection_stats": stats,
        "connection_pool": pool_health,
        "recommendations": generate_performance_recommendations(stats, pool_health)
    }

def generate_performance_recommendations(stats: dict, pool_health: dict) -> list:
    """Generate performance recommendations"""
    recommendations = []
    
    pool_status = pool_health.get("pool_status", {})
    utilization = pool_health.get("pool_utilization", {})
    
    if utilization.get("usage_percent", 0) > 80:
        recommendations.append("High connection pool utilization. Consider increasing pool_size.")
    
    if pool_status.get("overflow", 0) > 10:
        recommendations.append("Frequent connection overflow. Increase max_overflow setting.")
    
    if stats.get("total_documents", 0) > 100000:
        recommendations.append("Large collection detected. Consider partitioning or indexing optimization.")
    
    return recommendations
```

---

## 🚀 DEPLOYMENT CONFIGURATION

### **6. Environment Variables cho Production**

```bash
# Database Connection Pool Settings
DB_POOL_SIZE=20                    # Core connections
DB_MAX_OVERFLOW=30                 # Additional connections  
DB_POOL_RECYCLE=3600              # Connection lifetime (seconds)
DB_POOL_TIMEOUT=30                # Connection timeout
DB_POOL_PRE_PING=true             # Validate connections

# PostgreSQL Settings (postgresql.conf)
max_connections=200               # Increase from default 100
shared_buffers=256MB             # 25% of RAM
effective_cache_size=1GB         # 75% of RAM
work_mem=4MB                     # Per-connection memory
maintenance_work_mem=64MB        # Maintenance operations
wal_buffers=16MB                 # WAL buffer size

# pgvector Specific
shared_preload_libraries='vector'
max_locks_per_transaction=1024   # For vector operations
```

### **7. Docker Compose với Optimized PostgreSQL**

```yaml
# docker-compose.yml
version: '3.8'
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: rag_bidding_v2
      POSTGRES_USER: sakana
      POSTGRES_PASSWORD: sakana123
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./postgresql.conf:/etc/postgresql/postgresql.conf
    command: postgres -c config_file=/etc/postgresql/postgresql.conf
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru

volumes:
  postgres_data:
  redis_data:
```

---

## 📊 EXPECTED PERFORMANCE IMPROVEMENTS

### **Before vs After Comparison:**

| Metric | Before (No Pooling) | After (With Pooling) | Improvement |
|--------|-------------------|---------------------|-------------|
| **Connection Time** | ~50-100ms per query | ~1-5ms (reused) | **90-95% faster** |
| **Concurrent Users** | 5-10 users max | 50+ users | **5-10x more** |
| **Query Throughput** | 2-5 queries/sec | 20-50 queries/sec | **10x faster** |
| **Resource Usage** | High CPU/Memory | Optimized | **60% reduction** |
| **Error Rate** | 5-10% under load | <1% under load | **90% reduction** |

### **Scalability Targets:**

- ✅ **50+ concurrent users** 
- ✅ **100+ queries per second**
- ✅ **<100ms average response time**
- ✅ **99.9% uptime under load**
- ✅ **Efficient resource utilization**

---

## 🔨 IMPLEMENTATION TIMELINE

### **Phase 1: Core Infrastructure (Week 1)**
- [ ] Implement `DatabaseConfig` with connection pooling
- [ ] Create `PooledPGVectorStore` 
- [ ] Setup FastAPI dependencies
- [ ] Basic monitoring endpoints

### **Phase 2: Optimization (Week 2)** 
- [ ] Query optimization với prepared statements
- [ ] Batch processing improvements
- [ ] Connection pool tuning
- [ ] Performance testing

### **Phase 3: Production Deployment (Week 3)**
- [ ] Docker configuration
- [ ] Environment setup
- [ ] Load testing validation  
- [ ] Monitoring dashboard

### **Phase 4: Fine-tuning (Week 4)**
- [ ] Performance analysis
- [ ] Configuration optimization
- [ ] Documentation completion
- [ ] Team training

---

## 💡 ADDITIONAL RECOMMENDATIONS

### **1. Redis Integration**
- **Session caching** for frequent queries
- **Connection metadata caching**
- **Query result caching** with TTL

### **2. Database Indexing**
- **HNSW indexes** for vector similarity
- **GIN indexes** for metadata filtering
- **Composite indexes** for common query patterns

### **3. Application-Level Optimization**
- **Request deduplication** for identical queries
- **Background task queuing** for heavy operations
- **Graceful degradation** under high load

### **4. Monitoring và Alerting**
- **Connection pool metrics** dashboard
- **Query performance monitoring**
- **Automated scaling triggers**
- **Error rate alerting**

---

**Implementation Priority: HIGH** 🔥  
**Expected ROI: 10x performance improvement**  
**Timeline: 4 weeks**  
**Risk Level: LOW** (well-tested patterns)