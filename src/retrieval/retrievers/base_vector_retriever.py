"""
Base Vector Retriever

Simple wrapper cho vector store, tuân thủ LangChain BaseRetriever interface.
"""

from typing import List, Optional, Dict, Any
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun

from src.embedding.store.pgvector_store import vector_store


class BaseVectorRetriever(BaseRetriever):
    """
    Simple vector store retriever wrapper.

    Tuân thủ LangChain BaseRetriever interface để có thể sử dụng trong chains.

    Supports metadata filtering:
    - filter_status: Filter by document status ("active", "expired", None)
    - filter_dict: Custom PGVector filter (e.g. {"status": "active", "dieu": "14"})
    """

    k: int = 5
    filter_status: Optional[str] = None  # "active", "expired", or None
    filter_dict: Optional[Dict[str, Any]] = None  # Custom PGVector filter

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
            List of relevant documents (filtered if filter_status or filter_dict set)
        """
        # Build filter
        pgvector_filter = self._build_filter()

        # Retrieve with filter
        if pgvector_filter:
            # Retrieve more docs if filtering (to get k after filter)
            retrieve_k = self.k * 2
            return vector_store.similarity_search(
                query, k=retrieve_k, filter=pgvector_filter
            )[: self.k]
        else:
            return vector_store.similarity_search(query, k=self.k)

    def _build_filter(self) -> Optional[Dict[str, Any]]:
        """Build PGVector filter from filter_status and filter_dict."""
        if self.filter_dict:
            return self.filter_dict

        if self.filter_status:
            return {"status": self.filter_status}

        return None

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
