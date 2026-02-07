import os
import logging
import asyncio
import multiprocessing
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from src.config.logging_config import setup_logging
from src.config.models import settings
from src.config.database import init_database, startup_database, shutdown_database
from src.embedding.store.pgvector_store import bootstrap
from src.generation.chains.qa_chain import answer
from src.retrieval.query_processing.query_enhancer import (
    EnhancementStrategy,
    QueryEnhancer,
    QueryEnhancerConfig,
)
from .routers import upload
from .routers import user_upload  # User document contribution
from .routers import documents_management
from .routers import auth
from .routers import conversations
from .routers import cache
from .routers import analytics
from .middleware import (
    AuthMiddleware,
    RequestLoggingMiddleware,
    RateLimitMiddleware,
    CORSAuthMiddleware,
)

logger = logging.getLogger(__name__)

# ============================================================================
# WORKER COORDINATION (for synchronized logging with multiple workers)
# ============================================================================
# Shared state between workers for startup coordination
worker_manager = multiprocessing.Manager()
worker_states = (
    worker_manager.dict()
)  # {worker_pid: {"status": "...", "config": {...}}}
worker_lock = worker_manager.Lock()  # Synchronize log output
expected_workers = int(os.getenv("GUNICORN_WORKERS", "4"))  # Expected number of workers

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

setup_logging()


# ============================================================================
# LIFESPAN CONTEXT MANAGER (for startup/shutdown events)
# ============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI startup and shutdown events.

    This replaces the deprecated @app.on_event("startup") and @app.on_event("shutdown").

    Startup:
    - Initialize database connection pool
    - Bootstrap vector store
    - Pre-load BGEReranker model (CUDA)
    - Pre-load QueryEnhancer (GPT-4o-mini)

    Shutdown:
    - Close database connections
    """
    # STARTUP
    worker_pid = os.getpid()
    worker_config = {}  # Track this worker's configuration

    with worker_lock:
        logger.info(f"🚀 [Worker {worker_pid}] Starting up...")

    # 1. Initialize database
    with worker_lock:
        logger.info(
            f"📦 [Worker {worker_pid}] Initializing database connection pool..."
        )
    init_database()
    await startup_database()

    # Store database config
    from src.config.database import get_db_config

    db_config = get_db_config()
    pool_status = await db_config.get_pool_status()
    pool_metrics = pool_status.get("pool_metrics", {})

    # Handle both NullPool and AsyncAdaptedQueuePool
    worker_config["database"] = {
        "pool_class": pool_metrics.get("pool_class", "Unknown"),
        "pool_size": pool_metrics.get("pool_size", "N/A"),
        "max_overflow": pool_metrics.get("max_overflow", "N/A"),
    }

    # 2. Bootstrap vector store (sync operation)
    with worker_lock:
        logger.info(f"📦 [Worker {worker_pid}] Bootstrapping vector store...")
    bootstrap()
    worker_config["vector_store"] = "bootstrapped"

    # 3. Pre-load Reranker based on config
    from src.config.feature_flags import DEFAULT_RERANKER_TYPE

    with worker_lock:
        logger.info(
            f"🔧 [Worker {worker_pid}] Pre-loading Reranker (type: {DEFAULT_RERANKER_TYPE})..."
        )
    try:
        from src.config.reranker_provider import get_default_reranker

        reranker = get_default_reranker()

        # Store reranker config
        if DEFAULT_RERANKER_TYPE == "bge":
            device = getattr(reranker, "device", "N/A")
            worker_config["reranker"] = {
                "type": DEFAULT_RERANKER_TYPE,
                "device": str(device),
            }
            with worker_lock:
                logger.info(
                    f"✅ [Worker {worker_pid}] BGEReranker loaded (device: {device})"
                )
        elif DEFAULT_RERANKER_TYPE == "vertex":
            model = getattr(reranker, "model", "N/A")
            worker_config["reranker"] = {"type": DEFAULT_RERANKER_TYPE, "model": model}
            with worker_lock:
                logger.info(
                    f"✅ [Worker {worker_pid}] Vertex AI Reranker configured (model: {model})"
                )
        else:
            worker_config["reranker"] = {"type": DEFAULT_RERANKER_TYPE}
            with worker_lock:
                logger.info(
                    f"✅ [Worker {worker_pid}] {DEFAULT_RERANKER_TYPE.upper()} Reranker configured"
                )
    except Exception as e:
        worker_config["reranker"] = {"type": DEFAULT_RERANKER_TYPE, "error": str(e)}
        with worker_lock:
            logger.error(
                f"❌ [Worker {worker_pid}] Failed to load Reranker ({DEFAULT_RERANKER_TYPE}): {e}"
            )

    # 4. Pre-load QueryEnhancer
    with worker_lock:
        logger.info(
            f"🔧 [Worker {worker_pid}] Pre-loading QueryEnhancer (multi_query + step_back)..."
        )
    try:
        enhancer = QueryEnhancer(
            config=QueryEnhancerConfig(
                strategies=[
                    EnhancementStrategy.MULTI_QUERY,
                    EnhancementStrategy.STEP_BACK,
                ],
                max_queries=3,
            )
        )
        worker_config["query_enhancer"] = {
            "strategies": ["multi_query", "step_back"],
            "max_queries": 3,
        }
        with worker_lock:
            logger.info(f"✅ [Worker {worker_pid}] QueryEnhancer loaded successfully")
    except Exception as e:
        worker_config["query_enhancer"] = {"error": str(e)}
        with worker_lock:
            logger.error(f"❌ [Worker {worker_pid}] Failed to load QueryEnhancer: {e}")

    # Register this worker as ready
    with worker_lock:
        worker_states[worker_pid] = {"status": "ready", "config": worker_config}
        logger.info(
            f"🎉 [Worker {worker_pid}] Startup complete! Ready to serve requests."
        )
        logger.info(
            f"📊 [Worker {worker_pid}] Workers ready: {len(worker_states)}/{expected_workers}"
        )

    # Wait a bit for other workers to startup
    await asyncio.sleep(0.5)

    # Verification: If this is the last worker, verify all workers have same config
    with worker_lock:
        if len(worker_states) == expected_workers:
            await _verify_workers_consistency()

    yield

    # SHUTDOWN
    with worker_lock:
        logger.info(f"👋 [Worker {worker_pid}] Shutting down...")
    await shutdown_database()

    # Unregister this worker
    with worker_lock:
        if worker_pid in worker_states:
            del worker_states[worker_pid]
        logger.info(f"✅ [Worker {worker_pid}] Shutdown complete")


async def _verify_workers_consistency():
    """
    Verify all workers have consistent configuration.
    This runs once when all workers are ready.
    """
    if len(worker_states) == 0:
        return

    logger.info("\n" + "=" * 70)
    logger.info(f"🔍 WORKER VERIFICATION: {len(worker_states)} workers ready")
    logger.info("=" * 70)

    # Get reference config from first worker
    first_pid = list(worker_states.keys())[0]
    reference_config = worker_states[first_pid]["config"]

    # Check consistency
    all_consistent = True
    inconsistencies = []

    for pid, state in worker_states.items():
        if state["status"] != "ready":
            all_consistent = False
            inconsistencies.append(
                f"Worker {pid}: Not ready (status={state['status']})"
            )
            continue

        worker_config = state["config"]

        # Check database config
        if worker_config.get("database") != reference_config.get("database"):
            all_consistent = False
            inconsistencies.append(
                f"Worker {pid}: Database config mismatch\n"
                f"  Expected: {reference_config.get('database')}\n"
                f"  Got: {worker_config.get('database')}"
            )

        # Check reranker config
        if worker_config.get("reranker") != reference_config.get("reranker"):
            all_consistent = False
            inconsistencies.append(
                f"Worker {pid}: Reranker config mismatch\n"
                f"  Expected: {reference_config.get('reranker')}\n"
                f"  Got: {worker_config.get('reranker')}"
            )

        # Check query enhancer config
        if worker_config.get("query_enhancer") != reference_config.get(
            "query_enhancer"
        ):
            all_consistent = False
            inconsistencies.append(
                f"Worker {pid}: QueryEnhancer config mismatch\n"
                f"  Expected: {reference_config.get('query_enhancer')}\n"
                f"  Got: {worker_config.get('query_enhancer')}"
            )

    # Log results
    if all_consistent:
        logger.info("✅ All workers configured identically")
        logger.info(f"\n📋 Shared Configuration:")
        logger.info(f"   Database: {reference_config.get('database')}")
        logger.info(f"   Reranker: {reference_config.get('reranker')}")
        logger.info(f"   Query Enhancer: {reference_config.get('query_enhancer')}")
        logger.info("\n✅ System ready to handle requests")
    else:
        logger.warning("⚠️  Worker configuration inconsistencies detected:")
        for inconsistency in inconsistencies:
            logger.warning(f"   {inconsistency}")
        logger.warning("\n⚠️  System may behave unpredictably!")

    logger.info("=" * 70 + "\n")


# ============================================================================
# SWAGGER / OPENAPI CONFIGURATION
# ============================================================================
SWAGGER_DESCRIPTION = """
# RAG Bidding API - Vietnamese Legal Document Q&A System

## 🎯 Overview
Hệ thống hỏi đáp tài liệu pháp luật Việt Nam sử dụng RAG (Retrieval-Augmented Generation).

## 🔐 Authentication
Sử dụng JWT Bearer token. Các bước:
1. **Register**: `POST /api/auth/register` - Tạo tài khoản mới
2. **Login**: `POST /api/auth/login` - Lấy access token
3. **Use token**: Thêm header `Authorization: Bearer <access_token>`

## 📝 Test Flow (Recommended Order)

### Step 1: Authentication
1. `POST /api/auth/register` - Đăng ký tài khoản test
2. `POST /api/auth/login` - Đăng nhập lấy token
3. Click **Authorize** button, paste token

### Step 2: Conversations
4. `POST /api/conversations` - Tạo conversation mới
5. `POST /api/conversations/{id}/messages` - Gửi câu hỏi
6. `GET /api/conversations/{id}` - Xem chi tiết conversation

### Step 3: Quick Q&A (No Auth Required)
- `POST /ask` - Hỏi đáp nhanh không cần đăng nhập

### Step 4: Documents Management
- `GET /api/documents` - Liệt kê documents
- `GET /api/documents/stats` - Thống kê documents

## 🔧 RAG Modes
- **fast**: Không enhancement, không reranking (~1s)
- **balanced**: Multi-Query + Step-Back + BGE reranking (~2-3s) ⭐ Default
- **quality**: All 4 strategies + RRF fusion (~3-5s)
"""

SWAGGER_TAGS = [
    {
        "name": "Authentication",
        "description": "User registration, login, and account management",
    },
    {
        "name": "Conversations",
        "description": "Chat conversations with RAG-powered responses",
    },
    {"name": "Documents", "description": "Document management and statistics"},
    {"name": "Upload", "description": "Document upload and processing"},
    {"name": "cache", "description": "Cache management and monitoring"},
    {
        "name": "Analytics",
        "description": "Dashboard analytics, cost metrics, usage statistics, and admin operations",
    },
    {"name": "System", "description": "Health checks and system information"},
]

app = FastAPI(
    title="RAG Bidding API",
    description=SWAGGER_DESCRIPTION,
    version="3.0.0",
    openapi_tags=SWAGGER_TAGS,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,  # Use lifespan context manager
)

# ============================================================================
# MIDDLEWARE (order matters - first added = outermost = runs first)
# ============================================================================
# CORS middleware (must be outermost to handle preflight requests)
# Get allowed origins from environment variable
cors_origins_str = os.environ.get("CORS_ORIGINS", "http://localhost:3000")
cors_origins = [
    origin.strip() for origin in cors_origins_str.split(",") if origin.strip()
]
app.add_middleware(
    CORSAuthMiddleware, allow_origins=cors_origins, allow_credentials=True, max_age=600
)

# Request logging (logs all requests including errors)
app.add_middleware(RequestLoggingMiddleware)

# Rate limiting (before auth to prevent brute force)
app.add_middleware(RateLimitMiddleware, requests_per_minute=120, burst_size=20)

# Auth middleware (extracts user from JWT, adds to request.state)
app.add_middleware(AuthMiddleware)

# ============================================================================
# ROUTERS
# ============================================================================
# Include routers
# ⚠️ ORDER MATTERS: Specific paths MUST come before dynamic paths
app.include_router(auth.router, prefix="/api")  # Auth endpoints - /auth/*
app.include_router(
    conversations.router, prefix="/api"
)  # Conversations - /conversations/*
app.include_router(upload.router, prefix="/api")
app.include_router(user_upload.router, prefix="/api")  # User document contribution
app.include_router(
    documents_management.router, prefix="/api"
)  # Document Management - /documents endpoints
app.include_router(cache.router, prefix="/api")  # Cache Management - /cache endpoints
app.include_router(analytics.router, prefix="/api")  # Analytics - /analytics endpoints


# ============================================================================
# QUICK Q&A ENDPOINT (No Authentication Required)
# ============================================================================
class AskIn(BaseModel):
    """Request body for quick Q&A endpoint"""

    question: str = Field(
        ...,
        description="Câu hỏi về pháp luật đấu thầu Việt Nam",
        json_schema_extra={
            "example": "Điều kiện để nhà thầu được tham gia đấu thầu là gì?"
        },
    )
    mode: Literal["fast", "balanced", "quality"] = Field(
        default="balanced",
        description="RAG mode: fast (1s), balanced (2-3s), quality (3-5s)",
    )
    reranker: Literal["bge", "openai"] | None = Field(
        default=None,
        description="Reranker: bge (local, free) hoặc openai (API, paid). None = use config default",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "question": "Điều kiện để nhà thầu được tham gia đấu thầu là gì?",
                    "mode": "balanced",
                },
                {
                    "question": "Quy trình lựa chọn nhà thầu qua mạng như thế nào?",
                    "mode": "quality",
                },
            ]
        }
    }


class SourceDocument(BaseModel):
    """Detailed source document info"""

    document_id: str = Field("", description="Document identifier")
    document_name: str = Field("", description="Document title/name")
    chunk_id: str = Field("", description="Chunk identifier")
    content: str = Field("", description="Citation text (first 500 chars)")
    hierarchy: list = Field(default=[], description="Document hierarchy")
    section_title: str = Field("", description="Section title")
    document_type: str = Field("", description="Document type")
    category: str = Field("", description="Category")
    status: str = Field("active", description="Document status")


class AskResponse(BaseModel):
    """Response from Q&A endpoint"""

    answer: str = Field(..., description="Câu trả lời từ LLM")
    sources: list[str] = Field(
        default=[], description="Danh sách nguồn (format đơn giản)"
    )
    source_documents_raw: list[SourceDocument] = Field(
        default=[], description="Chi tiết nguồn tài liệu"
    )
    adaptive_retrieval: dict = Field(
        default={}, description="Thông tin adaptive retrieval"
    )
    enhanced_features: list[str] = Field(
        default=[], description="Các features đã sử dụng"
    )
    processing_time_ms: Optional[int] = Field(None, description="Thời gian xử lý (ms)")


@app.get("/health", tags=["System"])
def health():
    """
    Health check endpoint

    Kiểm tra kết nối database PostgreSQL.
    Returns: `{"db": true}` nếu OK
    """
    try:
        import psycopg

        from src.config.database import get_effective_database_url

        dsn = get_effective_database_url().replace("postgresql+psycopg", "postgresql")
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return {"db": True}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.post("/ask", response_model=AskResponse, tags=["System"])
def ask(body: AskIn):
    """
    Quick Q&A endpoint (No authentication required)

    Gửi câu hỏi và nhận câu trả lời từ hệ thống RAG.
    Không cần đăng nhập - phù hợp cho testing nhanh.

    **RAG Modes:**
    - `fast`: Không enhancement, không reranking (~1s)
    - `balanced`: Multi-Query + BGE reranking (~2-3s) ⭐ Default
    """
    if not body.question or not body.question.strip():
        raise HTTPException(400, detail="question is required")
    try:
        import time

        start_time = time.time()
        result = answer(
            body.question,
            mode=body.mode,
            reranker_type=body.reranker,
        )
        processing_time = int((time.time() - start_time) * 1000)
        result["processing_time_ms"] = processing_time
        return result
    except Exception as e:
        raise HTTPException(500, detail=str(e))
