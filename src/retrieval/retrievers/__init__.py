# src/retrieval/retrievers/__init__.py

from .base_vector_retriever import BaseVectorRetriever
from .enhanced_retriever import EnhancedRetriever
from .fusion_retriever import FusionRetriever
from .adaptive_k_retriever import AdaptiveKRetriever

from src.embedding.store.pgvector_store import vector_store
from src.retrieval.query_processing import EnhancementStrategy


def create_retriever(mode: str = "balanced"):
    """
    Factory function to create retriever based on mode.

    Modes:
    - fast: BaseVectorRetriever (no enhancement)
    - balanced: EnhancedRetriever (Multi-Query + Step-Back)
    - quality: FusionRetriever (All 4 strategies + RRF)
    - adaptive: AdaptiveKRetriever (Multi-Query + Step-Back + Dynamic K)

    Enhancement Strategies:
    - Multi-Query: Generate 3-5 query variations
    - HyDE: Hypothetical document embeddings
    - Step-Back: Query generalization for broader context
    - Decomposition: Break complex queries into sub-questions
    """

    # Base retriever (always needed)
    base = BaseVectorRetriever(k=5)

    if mode == "fast":
        return base

    elif mode == "balanced":
        return EnhancedRetriever(
            base_retriever=base,
            enhancement_strategies=[
                EnhancementStrategy.MULTI_QUERY,
                EnhancementStrategy.STEP_BACK,
            ],
            k=5,
        )

    elif mode == "quality":
        return FusionRetriever(
            base_retriever=base,
            enhancement_strategies=[
                EnhancementStrategy.MULTI_QUERY,
                EnhancementStrategy.HYDE,
                EnhancementStrategy.STEP_BACK,
                EnhancementStrategy.DECOMPOSITION,
            ],
            k=5,
            rrf_k=60,
        )

    elif mode == "adaptive":
        enhanced = EnhancedRetriever(
            base_retriever=base,
            enhancement_strategies=[
                EnhancementStrategy.MULTI_QUERY,
                EnhancementStrategy.STEP_BACK,
            ],
            k=5,
        )
        return AdaptiveKRetriever(enhanced_retriever=enhanced, k_min=3, k_max=10)

    else:
        raise ValueError(f"Unknown mode: {mode}")


# Export for backward compatibility
__all__ = [
    "BaseVectorRetriever",
    "EnhancedRetriever",
    "FusionRetriever",
    "AdaptiveKRetriever",
    "create_retriever",
]
