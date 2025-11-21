import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
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
from .routers import documents_chat
from .routers import documents_management


setup_logging()
app = FastAPI(
    title="RAG Bidding API",
    description="Vietnamese Legal & Bidding Document RAG System",
    version="2.0.0",
)

# Include routers
# ⚠️ ORDER MATTERS: Specific paths MUST come before dynamic paths
app.include_router(upload.router, prefix="/api")
app.include_router(
    documents_management.router, prefix="/api"
)  # Document Management - /documents endpoints
app.include_router(
    documents_chat.router, prefix="/api"
)  # Chat endpoints - /chat/sessions


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
    question: str
    mode: Literal["fast", "balanced", "quality", "adaptive"] = "balanced"
    reranker: Literal["bge", "openai"] = "bge"  # Default: BGE (singleton, faster)


class AskResponse(BaseModel):
    answer: str
    sources: list[str]
    adaptive_retrieval: dict
    enhanced_features: list[str]
    processing_time_ms: int = None


@app.get("/health")
def health():
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


@app.post("/ask", response_model=AskResponse)
def ask(body: AskIn):

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


@app.get("/stats")
def get_system_stats():
    """Get system statistics and configuration."""
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


@app.get("/features")
def get_feature_flags():
    """
    Get current feature flags and production readiness status.

    Shows:
    - Database pooling status (pgBouncer vs NullPool)
    - Cache configuration (L1/L2/L3 layers)
    - Session storage (Redis vs In-Memory)
    - Reranking settings (BGE singleton, OpenAI parallel)

    See: src/config/feature_flags.py for configuration
    See: documents/technical/POOLING_CACHE_PLAN.md for implementation plan
    """
    from src.config.feature_flags import get_feature_status

    return {
        "status": "ok",
        "features": get_feature_status(),
        "deployment_guide": "/documents/technical/POOLING_CACHE_PLAN.md",
    }


@app.get("/")
def root():
    """API root with helpful links."""
    return {
        "api": "RAG Bidding System",
        "version": "2.0.0",
        "endpoints": {
            "health": "/health - Database connectivity check",
            "stats": "/stats - System configuration",
            "features": "/features - Feature flags & production readiness",
            "ask": "POST /ask - Question answering",
            "documents": "/api/documents - Document management",
            "chat": "/api/chat/sessions - Chat session management",
        },
        "docs": "/docs - Swagger UI",
    }
