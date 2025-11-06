import os
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from src.config.models import settings

embeddings = OpenAIEmbeddings(model=settings.embed_model)

vector_store = PGVector(
    embeddings=embeddings,
    collection_name=settings.collection,
    connection=settings.database_url,
    use_jsonb=True,
    create_extension=True,
)


def bootstrap():
    vector_store.create_vector_extension()
    vector_store.create_tables_if_not_exists()
    vector_store.create_collection()


class PGVectorStore:
    """
    Wrapper class for PGVector store for upload service compatibility
    """

    def __init__(self):
        self.store = vector_store

    def add_texts(self, texts: list[str], metadatas: list[dict] = None):
        """Add texts with metadata to vector store"""
        return self.store.add_texts(texts, metadatas=metadatas)

    def add_documents(self, documents):
        """Add documents to vector store"""
        return self.store.add_documents(documents)

    def similarity_search(self, query: str, k: int = 5):
        """Search for similar documents"""
        return self.store.similarity_search(query, k=k)
