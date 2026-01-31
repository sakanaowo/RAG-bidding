# src/retrieval/retrievers/__init__.py

import logging
from typing import Optional, Literal
from .base_vector_retriever import BaseVectorRetriever
from .enhanced_retriever import EnhancedRetriever
from .fusion_retriever import FusionRetriever

# NOTE: AdaptiveKRetriever removed - use balanced mode instead

logger = logging.getLogger(__name__)

from src.embedding.store.pgvector_store import vector_store
from src.retrieval.query_processing import EnhancementStrategy
from src.retrieval.ranking import BaseReranker
from src.config.feature_flags import DEFAULT_RERANKER_TYPE


def create_retriever(
    mode: str = "balanced",
    enable_reranking: bool = True,
    reranker: Optional[BaseReranker] = None,
    reranker_type: Literal["bge", "openai", "vertex"] = DEFAULT_RERANKER_TYPE,
    filter_status: Optional[str] = None,  # ⚠️ Deprecated
):
    """
    Factory function to create retriever based on mode.

    Args:
        mode: Retrieval mode (fast, balanced, quality)
        enable_reranking: Whether to enable reranking (default: True)
        reranker: Custom reranker instance (if None, creates based on reranker_type)
        reranker_type: Type of reranker to use ("bge", "openai", or "vertex")
        filter_status: ⚠️ DEPRECATED - status not in embedding metadata

    Modes:
    - fast: BaseVectorRetriever (no enhancement, no reranking) ~1s
    - balanced: EnhancedRetriever (Multi-Query + Step-Back + reranking) ~2-3s [DEFAULT]
    - quality: FusionRetriever (All 4 strategies + RRF + reranking) ~3-5s

    Enhancement Strategies:
    - Multi-Query: Generate 3-5 query variations
    - HyDE: Hypothetical document embeddings (quality only)
    - Step-Back: Query generalization for broader context
    - Decomposition: Break complex queries into sub-questions (quality only)

    Reranking:
    - BGE (default): BAAI/bge-reranker-v2-m3, singleton pattern, GPU accelerated
    - OpenAI: GPT-4o-mini API-based reranking
    - Vertex: Google Cloud Discovery Engine Ranking API
    """

    # ✅ Reranking với BGE, OpenAI, hoặc Vertex nếu enable
    if enable_reranking and reranker is None:
        from src.config.reranker_provider import get_reranker
        reranker = get_reranker(provider=reranker_type)

    # Base retriever
    base = BaseVectorRetriever(k=5, filter_status=None)

    if mode == "fast":
        # Fast mode: no enhancement, no reranking
        logger.info(
            f"🚀 Created BaseVectorRetriever | mode=fast | "
            f"strategies=None | reranker=None"
        )
        return base

    elif mode == "balanced":
        # Balanced mode (recommended default)
        strategies = [EnhancementStrategy.MULTI_QUERY, EnhancementStrategy.STEP_BACK]
        logger.info(
            f"⚖️ Created EnhancedRetriever | mode=balanced | "
            f"strategies={[s.value for s in strategies]} | "
            f"reranker={type(reranker).__name__ if reranker else 'None'}"
        )
        return EnhancedRetriever(
            base_retriever=base,
            enhancement_strategies=strategies,
            reranker=reranker,
            k=5,
            retrieval_k=5,
        )

    elif mode == "quality":
        # Quality mode: full pipeline with RRF
        strategies = [
            EnhancementStrategy.MULTI_QUERY,
            EnhancementStrategy.HYDE,
            EnhancementStrategy.STEP_BACK,
            EnhancementStrategy.DECOMPOSITION,
        ]
        logger.info(
            f"💎 Created FusionRetriever | mode=quality | "
            f"strategies={[s.value for s in strategies]} | "
            f"reranker={type(reranker).__name__ if reranker else 'None'} | rrf_k=60"
        )
        return FusionRetriever(
            base_retriever=base,
            enhancement_strategies=strategies,
            reranker=reranker,
            k=5,
            retrieval_k=5,
            rrf_k=60,
        )

    else:
        raise ValueError(f"Unknown mode: {mode}. Available: fast, balanced, quality")


# Export for backward compatibility
__all__ = [
    "BaseVectorRetriever",
    "EnhancedRetriever",
    "FusionRetriever",
    "create_retriever",
]
