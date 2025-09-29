import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Literal
from app.core.logging import setup_logging
from app.core.config import settings
from app.core.vectorstore import bootstrap
from app.rag.chain import answer


setup_logging()
app = FastAPI(title="RAG API (LangChain)")


@app.on_event("startup")
def init_vector_store() -> None:
    bootstrap()


class AskIn(BaseModel):
    question: str
    mode: Literal["fast", "balanced", "quality"] = "balanced"


class AskResponse(BaseModel):
    answer: str
    sources: list[str]
    phase1_mode: str
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
        result = answer(body.question, mode=body.mode)
        processing_time = int((time.time() - start_time) * 1000)
        result["processing_time_ms"] = processing_time
        return result
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.get("/modes")
def get_available_modes():
    """Get available RAG modes and their descriptions."""
    return {
        "modes": {
            "fast": {
                "description": "Nhanh nhất, sử dụng ít tính năng nâng cao",
                "features": ["Adaptive Retrieval (k=3)", "Basic prompts"],
                "use_case": "Câu hỏi đơn giản, cần phản hồi nhanh",
            },
            "balanced": {
                "description": "Cân bằng tốc độ và chất lượng",
                "features": [
                    "Adaptive Retrieval (k=4-8)",
                    "Query Enhancement",
                    "Document Reranking",
                ],
                "use_case": "Đa số câu hỏi thông thường",
            },
            "quality": {
                "description": "Chất lượng tốt nhất, xử lý đầy đủ",
                "features": [
                    "Full Retrieval (k=5-10)",
                    "Query Enhancement",
                    "Document Reranking",
                    "Answer Validation",
                ],
                "use_case": "Câu hỏi phức tạp, cần độ chính xác cao",
            },
        },
        "default": "balanced",
    }


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
