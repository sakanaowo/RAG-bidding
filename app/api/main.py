from fastapi import FastAPI
from pydantic import BaseModel
from app.rag.chain import build_chain

app = FastAPI(title="RAG Bidding Assistant", version="0.1.0")

chain = build_chain(k=5)


class AskRequest(BaseModel):
    question: str


@app.post("/ask")
def ask(request: AskRequest):
    out = chain.invoke(request.question)
    # normalize sources
    cites = []

    for d in out["sources"]:
        md = d.metadata or {}
        cites.append(
            {
                "title": md.get("title"),
                "code": md.get("code"),
                "doc_type": md.get("doc_type"),
                "url": md.get("source_url"),
                "heading_path": md.get("heading_path"),
            }
        )
    return {"answer": out["answer"], "sources": cites}
