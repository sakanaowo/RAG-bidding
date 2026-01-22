# src/retrieval/retrievers/__init__.py

from typing import Optional, Literal
from .base_vector_retriever import BaseVectorRetriever
from .enhanced_retriever import EnhancedRetriever
from .fusion_retriever import FusionRetriever
# NOTE: AdaptiveKRetriever removed - use balanced mode instead

from src.embedding.store.pgvector_store import vector_store
from src.retrieval.query_processing import EnhancementStrategy
from src.retrieval.ranking import (
    BaseReranker,
    get_singleton_reranker,
    OpenAIReranker,
)


def create_retriever(
    mode: str = "balanced",
    enable_reranking: bool = True,
    reranker: Optional[BaseReranker] = None,
    reranker_type: Literal["bge", "openai"] = "bge",
    filter_status: Optional[str] = None,  # ⚠️ Deprecated
):
    """
    Factory function to create retriever based on mode.

    Args:
        mode: Retrieval mode (fast, balanced, quality)
        enable_reranking: Whether to enable reranking (default: True)
        reranker: Custom reranker instance (if None, creates based on reranker_type)
        reranker_type: Type of reranker to use ("bge" or "openai")
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
    """

    # ✅ Reranking với BGE hoặc OpenAI nếu enable
    if enable_reranking and reranker is None:
        if reranker_type == "bge":
            reranker = get_singleton_reranker()
        elif reranker_type == "openai":
            reranker = OpenAIReranker()
        else:
            raise ValueError(f"Unknown reranker_type: {reranker_type}")

    # Base retriever
    base = BaseVectorRetriever(k=5, filter_status=None)

    if mode == "fast":
        # Fast mode: no enhancement, no reranking
        return base

    elif mode == "balanced":
        # Balanced mode (recommended default)
        return EnhancedRetriever(
            base_retriever=base,
            enhancement_strategies=[
                EnhancementStrategy.MULTI_QUERY,
                EnhancementStrategy.STEP_BACK,
            ],
            reranker=reranker,
            k=5,
            retrieval_k=5,
        )

    elif mode == "quality":
        # Quality mode: full pipeline with RRF
        return FusionRetriever(
            base_retriever=base,
            enhancement_strategies=[
                EnhancementStrategy.MULTI_QUERY,
                EnhancementStrategy.HYDE,
                EnhancementStrategy.STEP_BACK,
                EnhancementStrategy.DECOMPOSITION,
            ],
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

