"""
Reranker Provider Factory Pattern

Provides abstraction layer for switching between reranker providers:
- BGE (sentence-transformers CrossEncoder) - Default, local GPU/CPU
- OpenAI (GPT-based scoring) - API-based fallback
- Vertex AI (future) - Google Cloud Ranking API

Usage:
    from src.config.reranker_provider import get_reranker, get_default_reranker
    
    # Get default reranker (based on RERANKER_PROVIDER env var)
    reranker = get_default_reranker()
    
    # Get specific provider
    reranker = get_reranker(provider="openai")
"""

import logging
from enum import Enum
from typing import Optional, Protocol, List, Tuple

from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class RerankerProvider(str, Enum):
    """Supported reranker providers."""
    BGE = "bge"
    OPENAI = "openai"
    VERTEX_AI = "vertex"  # Future: Vertex AI Ranking API


class BaseRerankerProtocol(Protocol):
    """Protocol defining the interface for rerankers."""
    
    def rerank(
        self, 
        query: str, 
        documents: List[Document], 
        top_k: int = 5
    ) -> List[Tuple[Document, float]]:
        """Rerank documents based on query relevance."""
        ...


def get_reranker(
    provider: Optional[str] = None,
    **kwargs
) -> BaseRerankerProtocol:
    """
    Factory function to create reranker based on provider.
    
    Args:
        provider: Reranker provider (bge, openai, vertex).
                  Defaults to RERANKER_PROVIDER env var.
        **kwargs: Additional provider-specific arguments
    
    Returns:
        Reranker instance implementing BaseRerankerProtocol
    
    Raises:
        ValueError: If provider is not recognized
        ImportError: If required provider package is not installed
    """
    # Import settings here to avoid circular imports
    from src.config.models import settings
    
    provider = provider or settings.reranker_provider
    
    if provider == RerankerProvider.BGE or provider == "bge":
        try:
            from src.retrieval.ranking.bge_reranker import get_singleton_reranker
        except ImportError as e:
            raise ImportError(
                f"BGE reranker import failed: {e}. "
                "Make sure sentence-transformers is installed."
            )
        
        reranker = get_singleton_reranker(**kwargs)
        logger.debug(f"Created BGE reranker: model={settings.reranker_model}")
        return reranker
    
    elif provider == RerankerProvider.OPENAI or provider == "openai":
        try:
            from src.retrieval.ranking.openai_reranker import OpenAIReranker
        except ImportError as e:
            raise ImportError(
                f"OpenAI reranker import failed: {e}. "
                "Make sure langchain-openai is installed."
            )
        
        reranker = OpenAIReranker(**kwargs)
        logger.debug("Created OpenAI reranker: using GPT for scoring")
        return reranker
    
    elif provider == RerankerProvider.VERTEX_AI or provider == "vertex":
        try:
            from src.retrieval.ranking.vertex_reranker import get_vertex_reranker
        except ImportError as e:
            raise ImportError(
                f"Vertex AI reranker import failed: {e}. "
                "Make sure google-cloud-discoveryengine is installed."
            )
        
        reranker = get_vertex_reranker(**kwargs)
        logger.debug(f"Created Vertex AI reranker: model={reranker.model}")
        return reranker
    
    else:
        raise ValueError(
            f"Unknown reranker provider: {provider}. "
            f"Available: {', '.join([p.value for p in RerankerProvider])}"
        )


# ===== Singleton Pattern for Default Reranker =====
_default_reranker: Optional[BaseRerankerProtocol] = None
_default_reranker_lock = None


def get_default_reranker() -> BaseRerankerProtocol:
    """
    Get or create default reranker (singleton pattern).
    
    Thread-safe singleton that creates reranker based on 
    RERANKER_PROVIDER environment variable.
    
    Returns:
        BaseRerankerProtocol: The default reranker
    """
    global _default_reranker, _default_reranker_lock
    
    if _default_reranker is None:
        import threading
        if _default_reranker_lock is None:
            _default_reranker_lock = threading.Lock()
        
        with _default_reranker_lock:
            # Double-check locking pattern
            if _default_reranker is None:
                from src.config.models import settings
                _default_reranker = get_reranker()
                logger.info(
                    f"✅ Initialized default reranker: "
                    f"provider={settings.reranker_provider}"
                )
    
    return _default_reranker


def reset_default_reranker() -> None:
    """
    Reset the singleton default reranker.
    
    ⚠️ Use only for testing or when provider config changes.
    """
    global _default_reranker
    _default_reranker = None
    logger.info("🔄 Reset default reranker singleton")
