import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Literal
from src.config.logging_config import setup_logging
from src.config.models import settings
from src.embedding.store.pgvector_store import bootstrap
from src.generation.chains.qa_chain import answer
from src.retrieval.query_processing.query_enhancer import (
    EnhancementStrategy,
    QueryEnhancer,
    QueryEnhancerConfig,
)


setup_logging()
app = FastAPI(title="RAG API (LangChain)")


@app.on_event("startup")
def init_vector_store() -> None:
    bootstrap()


class AskIn(BaseModel):
    question: str
    mode: Literal["fast", "balanced", "quality", "adaptive"] = "balanced"


class AskResponse(BaseModel):
    answer: str
    sources: list[str]
    # phase1_mode: str
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
    from src.retrieval.retrievers import create_retriever

    # 🆕 Enable reranking based on config (default: True for balanced/quality/adaptive)
    enable_reranking = settings.enable_reranking and body.mode != "fast"
    retriever = create_retriever(mode=body.mode, enable_reranking=enable_reranking)

    if not body.question or not body.question.strip():
        raise HTTPException(400, detail="question is required")
    try:
        import time

        start_time = time.time()
        result = answer(body.question, mode=body.mode, use_enhancement=True)
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
        "current_mode": settings.rag_mode,
        "chunk_stats": {
            "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap,
        },
    }


# TODO: remove non-relative data

# TODO: endpoint to toggle status

# TODO: endpoint to upsert data
