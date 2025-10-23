"""
Base Vector Retriever

Simple wrapper cho vector store, tuân thủ LangChain BaseRetriever interface.
"""

from typing import List
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun

from src.embedding.store.pgvector_store import vector_store


class BaseVectorRetriever(BaseRetriever):
    """
    Simple vector store retriever wrapper.

    Tuân thủ LangChain BaseRetriever interface để có thể sử dụng trong chains.
    """

    k: int = 5

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun | None = None,
    ) -> List[Document]:
        """
        Core retrieval logic - synchronous.

        Args:
            query: User's question
            run_manager: Callback manager for tracing (LangChain)

        Returns:
            List of relevant documents
        """
        return vector_store.similarity_search(query, k=self.k)

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun | None = None,
    ) -> List[Document]:
        """
        Async version of retrieval.

        Args:
            query: User's question
            run_manager: Callback manager for tracing

        Returns:
            List of relevant documents
        """
        # PGVector hỗ trợ async search
        return await vector_store.asimilarity_search(query, k=self.k)
