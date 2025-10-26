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
from src.retrieval.ranking import BaseReranker
from .base_vector_retriever import BaseVectorRetriever


class EnhancedRetriever(BaseRetriever):
    """
    Retriever với query enhancement và optional reranking.

    Workflow:
    1. Enhance query → multiple queries
    2. Retrieve docs for each query (retrieve more if reranking)
    3. Deduplicate & merge
    4. [Optional] Rerank with cross-encoder
    5. Return top-k
    """

    base_retriever: BaseVectorRetriever
    enhancement_strategies: Optional[List[EnhancementStrategy]] = None
    reranker: Optional[BaseReranker] = None  # 🆕 Reranker support
    k: int = 5
    retrieval_k: int = 10  # 🆕 Retrieve more if reranking
    deduplication: bool = True

    # Query enhancer instance (initialized after __init__)
    query_enhancer: Optional[QueryEnhancer] = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(
        self,
        base_retriever: BaseVectorRetriever,
        enhancement_strategies: List[EnhancementStrategy] | None = None,
        reranker: Optional[BaseReranker] = None,  # 🆕
        k: int = 5,
        retrieval_k: Optional[int] = None,  # 🆕 Auto-set based on reranker
        deduplication: bool = True,
        **kwargs,
    ):
        """
        Args:
            base_retriever: Vector retriever instance
            enhancement_strategies: List of enhancement strategies (None = no enhancement)
            reranker: Reranker instance (None = no reranking)
            k: Number of final documents to return
            retrieval_k: Number of docs to retrieve before reranking (default: k*2 if reranker else k)
            deduplication: Whether to deduplicate documents
        """
        # Auto-set retrieval_k if not provided
        if retrieval_k is None:
            retrieval_k = k * 2 if reranker else k

        super().__init__(
            base_retriever=base_retriever,
            enhancement_strategies=enhancement_strategies,
            reranker=reranker,
            k=k,
            retrieval_k=retrieval_k,
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
        """Retrieve with query enhancement and optional reranking."""

        # Step 1: Enhance query
        if self.query_enhancer:
            queries = self.query_enhancer.enhance(query)
        else:
            queries = [query]

        # Step 2: Retrieve for each query (use retrieval_k per query)
        all_docs = []
        for q in queries:
            # Temporarily override k for initial retrieval
            original_k = self.base_retriever.k
            self.base_retriever.k = self.retrieval_k
            docs = self.base_retriever.invoke(q)
            self.base_retriever.k = original_k
            all_docs.extend(docs)

        # Step 3: Deduplicate
        if self.deduplication:
            all_docs = self._deduplicate_docs(all_docs)

        # Step 4: Rerank if reranker provided
        if self.reranker and all_docs:
            # Rerank and get top-k with scores
            doc_scores = self.reranker.rerank(query, all_docs, top_k=self.k)
            # Extract documents only (discard scores)
            return [doc for doc, score in doc_scores]

        # Step 5: Return top-k (no reranking)
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
