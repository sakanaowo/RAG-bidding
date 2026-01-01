"""
OpenAI Embedder
Wrapper for OpenAI embeddings using LangChain
"""

from langchain_openai import OpenAIEmbeddings
from src.config.models import settings


class OpenAIEmbedder:
    """
    OpenAI embeddings wrapper for consistency with upload service
    """

    def __init__(self, model: str = None):
        self.model = model or settings.embed_model
        self.embeddings = OpenAIEmbeddings(model=self.model)

    def embed_text(self, text: str) -> list[float]:
        """Embed a single text"""
        return self.embeddings.embed_query(text)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts"""
        return self.embeddings.embed_documents(texts)

    def embed_query(self, query: str) -> list[float]:
        """Embed a query (alias for embed_text)"""
        return self.embed_text(query)
