# src/retrieval/retrievers/base_vector_retriever.py

from typing import List
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from src.embedding.store.pgvector_store import vector_store


class BaseVectorRetriever(BaseRetriever):
    """
    Simple vector store retriever wrapper.
    Tuân thủ LangChain BaseRetriever interface.
    """

    k: int = 5

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun | None = None,
    ) -> List[Document]:
        """Core retrieval logic."""
        return vector_store.similarity_search(query, k=self.k)

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun | None = None,
    ) -> List[Document]:
        """Async version."""
        return await vector_store.asimilarity_search(query, k=self.k)
