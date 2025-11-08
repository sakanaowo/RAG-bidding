#!/usr/bin/env python3
"""
Simple API server for testing - bypasses upload functionality that has missing modules
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Literal
import time

# Import only the working components
from src.config.logging_config import setup_logging
from src.config.models import settings
from src.embedding.store.pgvector_store import bootstrap
from src.generation.chains.qa_chain import answer

setup_logging()
app = FastAPI(
    title="RAG Bidding API - Test Version",
    description="Vietnamese Legal & Bidding Document RAG System (Testing)",
    version="2.0.0-test",
)

# Skip upload router to avoid module errors
# app.include_router(upload.router)

@app.on_event("startup")
def init_vector_store() -> None:
    bootstrap()

class AskIn(BaseModel):
    question: str
    mode: Literal["fast", "balanced", "quality", "adaptive"] = "balanced"

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
        return {"db": True, "status": "healthy", "version": "2.0.0-test"}
    except Exception as e:
        raise HTTPException(500, detail=str(e))

@app.post("/ask", response_model=AskResponse)
def ask(body: AskIn):
    if not body.question or not body.question.strip():
        raise HTTPException(400, detail="question is required")
    
    try:
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
        "version": "2.0.0-test",
        "upload_functionality": "disabled (testing mode)"
    }

@app.get("/test/retrieval")
def test_retrieval(query: str = "Luật đầu tư", mode: str = "fast"):
    """Test endpoint for retrieval functionality"""
    try:
        from src.retrieval.retrievers import create_retriever
        
        retriever = create_retriever(mode=mode, enable_reranking=False)
        docs = retriever.invoke(query)
        
        return {
            "query": query,
            "mode": mode,
            "documents_found": len(docs),
            "results": [
                {
                    "content_preview": doc.page_content[:200],
                    "metadata": doc.metadata
                }
                for doc in docs[:3]  # Return top 3 results
            ]
        }
    except Exception as e:
        raise HTTPException(500, detail=f"Retrieval test failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)