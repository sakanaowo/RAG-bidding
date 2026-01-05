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
    get_cached_enhancer,  # 🆕 Use cached enhancer
)
from src.retrieval.ranking import BaseReranker
from .base_vector_retriever import BaseVectorRetriever


class FusionRetriever(BaseRetriever):
    """
    RAG-Fusion retriever với Reciprocal Rank Fusion (RRF) và optional reranking.

    Paper: https://arxiv.org/abs/2402.03367

    Workflow:
    1. Generate multiple queries
    2. Retrieve docs for each query (retrieve more if reranking)
    3. Rank fusion using RRF algorithm
    4. [Optional] Rerank with cross-encoder
    5. Return top-k fused results
    """

    base_retriever: BaseVectorRetriever
    enhancement_strategies: List[EnhancementStrategy]
    reranker: Optional[BaseReranker] = None  # 🆕 Reranker support
    k: int = 5
    retrieval_k: int = 10  # 🆕 Retrieve more if reranking
    rrf_k: int = 60  # RRF constant (tunable)

    # Query enhancer instance (initialized after __init__)
    query_enhancer: Optional[QueryEnhancer] = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(
        self,
        base_retriever: BaseVectorRetriever,
        enhancement_strategies: List[EnhancementStrategy],
        reranker: Optional[BaseReranker] = None,  # 🆕
        k: int = 5,
        retrieval_k: Optional[int] = None,  # 🆕 Auto-set based on reranker
        rrf_k: int = 60,
        **kwargs,
    ):
        # Auto-set retrieval_k if not provided
        if retrieval_k is None:
            retrieval_k = k * 2 if reranker else k

        super().__init__(
            base_retriever=base_retriever,
            enhancement_strategies=enhancement_strategies,
            reranker=reranker,
            k=k,
            retrieval_k=retrieval_k,
            rrf_k=rrf_k,
            **kwargs,
        )

        # 🆕 Use cached enhancer instead of creating new instance
        self.query_enhancer = get_cached_enhancer(
            strategies=self.enhancement_strategies, max_queries=5
        )

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun | None = None,
    ) -> List[Document]:
        """Retrieve with RAG-Fusion and optional reranking."""

        # Step 1: Generate multiple queries
        queries = self.query_enhancer.enhance(query)

        # Step 2: Retrieve docs for each query (use retrieval_k per query)
        query_results = []
        for q in queries:
            # Temporarily override k for initial retrieval
            original_k = self.base_retriever.k
            self.base_retriever.k = self.retrieval_k
            docs = self.base_retriever.invoke(q)
            self.base_retriever.k = original_k
            query_results.append(docs)

        # Step 3: Apply RRF algorithm
        fused_docs = self._reciprocal_rank_fusion(query_results)

        # Step 4: Rerank if reranker provided
        if self.reranker and fused_docs:
            try:
                # Rerank and get top-k with scores
                doc_scores = self.reranker.rerank(query, fused_docs, top_k=self.k)
                # Extract documents only (discard scores)
                return [doc for doc, score in doc_scores]
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                error_msg = str(e).lower()
                # 🆕 Handle CUDA OOM with OpenAI fallback
                if "cuda out of memory" in error_msg or "out of memory" in error_msg:
                    logger.warning(f"⚠️ Reranker OOM, attempting OpenAI fallback: {e}")
                    try:
                        from src.retrieval.ranking import OpenAIReranker

                        fallback_reranker = OpenAIReranker()
                        doc_scores = fallback_reranker.rerank(
                            query, fused_docs, top_k=self.k
                        )
                        return [doc for doc, score in doc_scores]
                    except Exception as fallback_err:
                        logger.error(f"❌ OpenAI fallback failed: {fallback_err}")
                else:
                    logger.error(f"❌ Reranking error: {e}")
                # Final fallback: return fused docs without reranking
                logger.warning("⚠️ Returning docs without reranking")
                return fused_docs[: self.k]

        # Step 5: Return top-k (no reranking)
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
