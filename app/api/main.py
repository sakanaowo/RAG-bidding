import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.core.logging import setup_logging
from app.core.config import settings
from app.rag.chain import answer


setup_logging()
app = FastAPI(title="RAG API (LangChain)")


class AskIn(BaseModel):
    question: str
    k: int | None = None


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


@app.post("/ask")
def ask(body: AskIn):
    if not body.question or not body.question.strip():
        raise HTTPException(400, detail="question is required")
    try:
        return answer(body.question)
    except Exception as e:
        raise HTTPException(500, detail=str(e))
