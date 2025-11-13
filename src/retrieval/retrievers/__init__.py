# src/retrieval/retrievers/__init__.py

from typing import Optional
from .base_vector_retriever import BaseVectorRetriever
from .enhanced_retriever import EnhancedRetriever
from .fusion_retriever import FusionRetriever
from .adaptive_k_retriever import AdaptiveKRetriever

from src.embedding.store.pgvector_store import vector_store
from src.retrieval.query_processing import EnhancementStrategy
from src.retrieval.ranking import (
    BaseReranker,
    get_singleton_reranker,
)  # ⭐ Import singleton factory


def create_retriever(
    mode: str = "balanced",
    enable_reranking: bool = True,
    reranker: Optional[BaseReranker] = None,
    filter_status: Optional[str] = None,  # 🆕 Default to None (no filtering)
):
    """
    Factory function to create retriever based on mode.

    Args:
        mode: Retrieval mode
        enable_reranking: Whether to enable reranking (default: True)
        reranker: Custom reranker instance (if None, uses BGEReranker)
        filter_status: Filter documents by status ("active", "expired", None for all)
                      Default: "active" (only retrieve active/current documents)

    Modes:
    - fast: BaseVectorRetriever (no enhancement, no reranking)
    - balanced: EnhancedRetriever (Multi-Query + Step-Back + optional reranking)
    - quality: FusionRetriever (All 4 strategies + RRF + optional reranking)
    - adaptive: AdaptiveKRetriever (Multi-Query + Step-Back + Dynamic K + optional reranking)

    Enhancement Strategies:
    - Multi-Query: Generate 3-5 query variations
    - HyDE: Hypothetical document embeddings
    - Step-Back: Query generalization for broader context
    - Decomposition: Break complex queries into sub-questions

    Reranking:
    - Uses BGE (BAAI/bge-reranker-v2-m3) by default
    - Auto-detects GPU for acceleration
    - Improves ranking quality by ~10-20% MRR

    Filtering:
    - Default: filter_status="active" (only current/valid documents)
    - Set filter_status=None to retrieve all documents (including expired)
    - Legal docs (Luật: 5yr, Nghị định/Thông tư: 2yr validity)
    - Educational materials: 5yr validity
    """

    # ✅ Reranking bằng BGE cross-encoder nếu enable
    if enable_reranking and reranker is None:
        # ⭐ FIXED: Dùng singleton thay vì tạo instance mới
        # Giảm memory: 60 instances (20GB) → 1 instance (1.2GB)
        reranker = get_singleton_reranker()

    # Base retriever with status filtering
    base = BaseVectorRetriever(k=5, filter_status=filter_status)

    if mode == "fast":
        # Fast mode: no enhancement, no reranking
        return base

    elif mode == "balanced":
        return EnhancedRetriever(
            base_retriever=base,
            enhancement_strategies=[
                EnhancementStrategy.MULTI_QUERY,
                EnhancementStrategy.STEP_BACK,
            ],
            reranker=reranker,  # 🆕
            k=5,
            retrieval_k=10 if reranker else 5,  # Retrieve more if reranking
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
            reranker=reranker,  # 🆕
            k=5,
            retrieval_k=10 if reranker else 5,  # Retrieve more if reranking
            rrf_k=60,
        )

    elif mode == "adaptive":
        enhanced = EnhancedRetriever(
            base_retriever=base,
            enhancement_strategies=[
                EnhancementStrategy.MULTI_QUERY,
                EnhancementStrategy.STEP_BACK,
            ],
            reranker=reranker,  # 🆕
            k=5,
            retrieval_k=10 if reranker else 5,  # Retrieve more if reranking
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
