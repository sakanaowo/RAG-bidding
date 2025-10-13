# src/retrieval/retrievers/enhanced_retriever.py

from typing import List, Optional
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun

from src.retrieval.query_processing import (
    QueryEnhancer,
    QueryEnhancerConfig,
    EnhancementStrategy,
)
from .base_vector_retriever import BaseVectorRetriever


class EnhancedRetriever(BaseRetriever):
    """
    Retriever với query enhancement.

    Workflow:
    1. Enhance query → multiple queries
    2. Retrieve docs for each query
    3. Deduplicate & rerank
    4. Return top-k
    """

    base_retriever: BaseVectorRetriever
    enhancement_strategies: Optional[List[EnhancementStrategy]] = None
    k: int = 5
    deduplication: bool = True

    # Query enhancer instance (initialized after __init__)
    query_enhancer: Optional[QueryEnhancer] = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(
        self,
        base_retriever: BaseVectorRetriever,
        enhancement_strategies: List[EnhancementStrategy] | None = None,
        k: int = 5,
        deduplication: bool = True,
        **kwargs,
    ):
        """
        Args:
            base_retriever: Vector retriever instance
            enhancement_strategies: List of enhancement strategies (None = no enhancement)
            k: Number of final documents to return
            deduplication: Whether to deduplicate documents
        """
        super().__init__(
            base_retriever=base_retriever,
            enhancement_strategies=enhancement_strategies,
            k=k,
            deduplication=deduplication,
            **kwargs,
        )

        # Initialize query enhancer if strategies provided
        if self.enhancement_strategies:
            config = QueryEnhancerConfig(
                strategies=self.enhancement_strategies, max_queries=3
            )
            self.query_enhancer = QueryEnhancer(config)

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun | None = None,
    ) -> List[Document]:
        """Retrieve with query enhancement."""

        # Step 1: Enhance query
        if self.query_enhancer:
            queries = self.query_enhancer.enhance(query)
        else:
            queries = [query]

        # Step 2: Retrieve for each query
        all_docs = []
        for q in queries:
            docs = self.base_retriever.invoke(q)
            all_docs.extend(docs)

        # Step 3: Deduplicate
        if self.deduplication:
            all_docs = self._deduplicate_docs(all_docs)

        # Step 4: Return top-k
        return all_docs[: self.k]

    def _deduplicate_docs(self, docs: List[Document]) -> List[Document]:
        """Remove duplicate documents based on content hash."""
        seen = set()
        unique_docs = []

        for doc in docs:
            content_hash = hash(doc.page_content)
            if content_hash not in seen:
                seen.add(content_hash)
                unique_docs.append(doc)

        return unique_docs
