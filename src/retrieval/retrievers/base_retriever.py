from src.embedding.store.pgvector_store import vector_store
from src.retrieval.retrievers.adaptive_retriever import adaptive_retriever

# Legacy retriever (kept for compatibility)
basic_retriever = vector_store.as_retriever(search_kwargs={"k": 5})


# New adaptive retriever (Phase 1 enhancement)
def smart_retrieve(question: str):
    """Smart retrieval với adaptive k"""
    return adaptive_retriever.get_documents(question)


# Default retriever - switch to adaptive (Phase 1 Quick Win)
retriever = smart_retrieve
