# src/retrieval/retrievers/fusion_retriever.py

from typing import List, Optional
from collections import defaultdict
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun

from src.retrieval.query_processing import (
    QueryEnhancer,
    QueryEnhancerConfig,
    EnhancementStrategy,
)
from .base_vector_retriever import BaseVectorRetriever


class FusionRetriever(BaseRetriever):
    """
    RAG-Fusion retriever với Reciprocal Rank Fusion (RRF).

    Paper: https://arxiv.org/abs/2402.03367

    Workflow:
    1. Generate multiple queries
    2. Retrieve docs for each query
    3. Rank fusion using RRF algorithm
    4. Return top-k fused results
    """

    base_retriever: BaseVectorRetriever
    enhancement_strategies: List[EnhancementStrategy]
    k: int = 5
    rrf_k: int = 60  # RRF constant (tunable)

    # Query enhancer instance (initialized after __init__)
    query_enhancer: Optional[QueryEnhancer] = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(
        self,
        base_retriever: BaseVectorRetriever,
        enhancement_strategies: List[EnhancementStrategy],
        k: int = 5,
        rrf_k: int = 60,
        **kwargs,
    ):
        super().__init__(
            base_retriever=base_retriever,
            enhancement_strategies=enhancement_strategies,
            k=k,
            rrf_k=rrf_k,
            **kwargs,
        )

        config = QueryEnhancerConfig(
            strategies=self.enhancement_strategies, max_queries=5
        )
        self.query_enhancer = QueryEnhancer(config)

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun | None = None,
    ) -> List[Document]:
        """Retrieve with RAG-Fusion."""

        # Step 1: Generate multiple queries
        queries = self.query_enhancer.enhance(query)

        # Step 2: Retrieve docs for each query (keep order)
        query_results = []
        for q in queries:
            docs = self.base_retriever.invoke(q)
            query_results.append(docs)

        # Step 3: Apply RRF algorithm
        fused_docs = self._reciprocal_rank_fusion(query_results)

        # Step 4: Return top-k
        return fused_docs[: self.k]

    def _reciprocal_rank_fusion(
        self, doc_lists: List[List[Document]]
    ) -> List[Document]:
        """
        Reciprocal Rank Fusion algorithm.

        RRF Score = Σ 1 / (k + rank_i)
        where rank_i is the rank in query i
        """
        # Build document → RRF score mapping
        doc_scores = defaultdict(float)
        doc_map = {}  # Keep document objects

        for doc_list in doc_lists:
            for rank, doc in enumerate(doc_list, start=1):
                doc_key = hash(doc.page_content)
                doc_scores[doc_key] += 1 / (self.rrf_k + rank)
                doc_map[doc_key] = doc

        # Sort by RRF score (descending)
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)

        # Return documents in fused order
        return [doc_map[doc_key] for doc_key, _ in sorted_docs]
