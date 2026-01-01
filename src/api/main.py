import os
from fastapi import FastAPI, HTTPException
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field
from typing import List, Literal
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
from .routers import documents_management
from .routers import auth
from .routers import conversations
from .middleware import (
    AuthMiddleware,
    RequestLoggingMiddleware,
    RateLimitMiddleware,
)


setup_logging()

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
- **adaptive**: Dynamic K selection dựa trên query complexity
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
    {"name": "System", "description": "Health checks and system information"},
]

app = FastAPI(
    title="RAG Bidding API",
    description=SWAGGER_DESCRIPTION,
    version="3.0.0",
    openapi_tags=SWAGGER_TAGS,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ============================================================================
# MIDDLEWARE (order matters - first added = outermost = runs first)
# ============================================================================
# Request logging (outermost - logs all requests including errors)
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
app.include_router(
    documents_management.router, prefix="/api"
)  # Document Management - /documents endpoints


@app.on_event("startup")
async def init_services() -> None:
    """Initialize all services on startup."""
    # Initialize database connection pool first
    init_database()
    await startup_database()


@app.on_event("shutdown")
async def cleanup_services() -> None:
    """Cleanup on shutdown."""
    await shutdown_database()


# Initialize vector store at module level (sync)
bootstrap()


class AskIn(BaseModel):
    """Request body for quick Q&A endpoint"""

    question: str = Field(
        ...,
        description="Câu hỏi về pháp luật đấu thầu Việt Nam",
        json_schema_extra={
            "example": "Điều kiện để nhà thầu được tham gia đấu thầu là gì?"
        },
    )
    mode: Literal["fast", "balanced", "quality", "adaptive"] = Field(
        default="balanced",
        description="RAG mode: fast (1s), balanced (2-3s), quality (3-5s), adaptive",
    )
    reranker: Literal["bge", "openai"] = Field(
        default="bge", description="Reranker: bge (local, free) hoặc openai (API, paid)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "question": "Điều kiện để nhà thầu được tham gia đấu thầu là gì?",
                    "mode": "balanced",
                    "reranker": "bge",
                },
                {
                    "question": "Quy trình lựa chọn nhà thầu qua mạng như thế nào?",
                    "mode": "quality",
                    "reranker": "bge",
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
    processing_time_ms: int = Field(None, description="Thời gian xử lý (ms)")


@app.get("/health", tags=["System"])
def health():
    """
    Health check endpoint

    Kiểm tra kết nối database PostgreSQL.
    Returns: `{"db": true}` nếu OK
    """
    try:
        import psycopg

        dsn = settings.database_url.replace("postgresql+psycopg", "postgresql")
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
    - `balanced`: Multi-Query + BGE reranking (~2-3s) ⭐ Recommended
    - `quality`: Full enhancement + RRF fusion (~3-5s)
    - `adaptive`: Dynamic K selection
    """
    if not body.question or not body.question.strip():
        raise HTTPException(400, detail="question is required")
    try:
        import time

        start_time = time.time()
        # ✅ answer() sẽ tạo retriever với singleton pattern + reranker selection
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


@app.get("/stats", tags=["System"])
def get_system_stats():
    """
    Get system statistics and configuration

    Hiển thị cấu hình vector store, LLM, và các feature flags.
    """
    return {
        "vector_store": {
            "collection": settings.collection,
            "embedding_model": settings.embed_model,
        },
        "llm": {"model": settings.llm_model},
        "phase1_features": {
            "adaptive_retrieval": settings.enable_adaptive_retrieval,
            "enhanced_prompts": settings.enable_enhanced_prompts,
            "query_enhancement": settings.enable_query_enhancement,
            "reranking": settings.enable_reranking,
            "answer_validation": settings.enable_answer_validation,
        },
    }


@app.get("/features", tags=["System"])
def get_feature_flags():
    """
    Get current feature flags and production readiness status

    Shows:
    - Database pooling status (pgBouncer vs NullPool)
    - Cache configuration (L1/L2/L3 layers)
    - Session storage (Redis vs In-Memory)
    - Reranking settings (BGE singleton, OpenAI parallel)
    """
    from src.config.feature_flags import get_feature_status

    return {
        "status": "ok",
        "features": get_feature_status(),
        "deployment_guide": "/documents/technical/POOLING_CACHE_PLAN.md",
    }


@app.get("/", tags=["System"])
def root():
    """
    API root with helpful links

    Trang chủ API với danh sách các endpoints chính.
    """
    return {
        "api": "RAG Bidding System",
        "version": "3.0.0",
        "endpoints": {
            "health": "GET /health - Database connectivity check",
            "stats": "GET /stats - System configuration",
            "features": "GET /features - Feature flags",
            "ask": "POST /ask - Quick Q&A (no auth)",
            "auth": {
                "register": "POST /api/auth/register",
                "login": "POST /api/auth/login",
                "me": "GET /api/auth/me",
            },
            "conversations": {
                "create": "POST /api/conversations",
                "list": "GET /api/conversations",
                "send_message": "POST /api/conversations/{id}/messages",
            },
            "documents": "GET /api/documents",
        },
        "docs": {"swagger": "/docs", "redoc": "/redoc"},
    }
