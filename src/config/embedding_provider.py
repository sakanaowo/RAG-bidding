"""
Embedding Provider Factory Pattern

Provides abstraction layer for switching between embedding providers:
- OpenAI (OpenAIEmbeddings) - Default, 1536 dimensions
- Vertex AI (VertexAIEmbeddings) - Google Cloud, 768 dimensions

Usage:
    from src.config.embedding_provider import get_embeddings, get_default_embeddings
    
    # Get default embeddings (based on EMBED_PROVIDER env var)
    embeddings = get_default_embeddings()
    
    # Get specific provider
    embeddings = get_embeddings(provider="vertex")

⚠️ Important: OpenAI and Vertex AI embeddings have different dimensions:
- OpenAI text-embedding-3-small: 1536 dimensions
- Vertex AI text-embedding-004: 768 dimensions

Switching providers requires re-embedding all documents in PGVector!
"""

import os
import logging
from enum import Enum
from typing import Optional

from langchain_core.embeddings import Embeddings

logger = logging.getLogger(__name__)


class EmbeddingProvider(str, Enum):
    """Supported embedding providers."""
    OPENAI = "openai"
    VERTEX_AI = "vertex"


class _TruncatedEmbeddings(Embeddings):
    """
    Wrapper that truncates embeddings to target dimension.
    
    This is designed for MRL (Matryoshka Representation Learning) models like
    gemini-embedding-001, which are trained to preserve quality when truncated.
    
    MRL ensures that the first N dimensions of an embedding still capture
    meaningful representations, allowing dimension reduction without re-training.
    """
    
    def __init__(self, base_embeddings: Embeddings, target_dim: int):
        """
        Args:
            base_embeddings: Underlying embeddings provider
            target_dim: Target dimension to truncate to (e.g., 1536)
        """
        self._base = base_embeddings
        self._target_dim = target_dim
    
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed documents and truncate to target dimension."""
        full_embeddings = self._base.embed_documents(texts)
        return [emb[:self._target_dim] for emb in full_embeddings]
    
    def embed_query(self, text: str) -> list[float]:
        """Embed query and truncate to target dimension."""
        full_embedding = self._base.embed_query(text)
        return full_embedding[:self._target_dim]


# Dimension mapping for different models
# Note: gemini-embedding-001 supports 768/1536/3072 via output_dimensionality
EMBEDDING_DIMENSIONS = {
    # OpenAI models
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
    # Vertex AI / Gemini models
    "text-embedding-004": 768,
    "text-embedding-005": 768,
    "text-multilingual-embedding-002": 768,
    "textembedding-gecko@003": 768,
    # Gemini embedding models (configurable dims via MRL)
    "gemini-embedding-001": 1536,  # Default to 1536 to match OpenAI
}


def get_embedding_dimension(model: str) -> int:
    """
    Get the embedding dimension for a model.
    
    Args:
        model: Model name
        
    Returns:
        Dimension count (defaults to 768 if unknown)
    """
    return EMBEDDING_DIMENSIONS.get(model, 768)


def get_embeddings(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs
) -> Embeddings:
    """
    Factory function to create embedding client based on provider.
    
    Args:
        provider: Embedding provider (openai, vertex).
                  Defaults to EMBED_PROVIDER env var.
        model: Model name override
        **kwargs: Additional provider-specific arguments
    
    Returns:
        LangChain Embeddings instance
    
    Raises:
        ValueError: If provider is not recognized
        ImportError: If required provider package is not installed
    """
    # Import settings here to avoid circular imports
    from src.config.models import settings
    
    provider = provider or settings.embed_provider
    
    if provider == EmbeddingProvider.OPENAI or provider == "openai":
        try:
            from langchain_openai import OpenAIEmbeddings
        except ImportError:
            raise ImportError(
                "langchain-openai package not installed. "
                "Run: pip install langchain-openai"
            )
        
        model_name = model or settings.embed_model
        embeddings = OpenAIEmbeddings(model=model_name, **kwargs)
        logger.debug(
            f"Created OpenAI Embeddings: model={model_name}, "
            f"dimensions={get_embedding_dimension(model_name)}"
        )
        return embeddings
    
    elif provider == EmbeddingProvider.VERTEX_AI or provider == "vertex":
        # Use GoogleGenerativeAIEmbeddings (newer, not deprecated)
        # instead of VertexAIEmbeddings which is deprecated in LangChain 3.2.0
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
        except ImportError:
            raise ImportError(
                "langchain-google-genai package not installed. "
                "Run: pip install langchain-google-genai"
            )
        
        model_name = model or settings.vertex_embed_model
        
        # Get target dimension from settings (default 1536 for database compatibility)
        target_dim = getattr(settings, 'embed_dimensions', 1536)
        
        embed_kwargs = {
            "model": f"models/{model_name}",  # Google GenAI expects "models/" prefix
            **kwargs
        }
        
        # Set task_type for retrieval-optimized embeddings
        if "gemini" in model_name.lower():
            embed_kwargs["task_type"] = "retrieval_document"
        
        base_embeddings = GoogleGenerativeAIEmbeddings(**embed_kwargs)
        
        # Wrap with truncation support for MRL models (gemini-embedding-001)
        # MRL (Matryoshka Representation Learning) models are designed to be
        # truncated without significant quality loss
        if "gemini" in model_name.lower() and target_dim < 3072:
            embeddings = _TruncatedEmbeddings(base_embeddings, target_dim)
            logger.info(
                f"Created Google GenAI Embeddings with truncation: model={model_name}, "
                f"base_dim=3072 -> target_dim={target_dim} (MRL compatible)"
            )
        else:
            embeddings = base_embeddings
            logger.info(
                f"Created Google GenAI Embeddings: model={model_name}, "
                f"dimensions={get_embedding_dimension(model_name)}"
            )
        
        return embeddings
    
    else:
        raise ValueError(
            f"Unknown embedding provider: {provider}. "
            f"Available: {', '.join([p.value for p in EmbeddingProvider])}"
        )


# ===== Singleton Pattern for Default Embeddings =====
_default_embeddings: Optional[Embeddings] = None
_default_embeddings_lock = None


def get_default_embeddings() -> Embeddings:
    """
    Get or create default embeddings client (singleton pattern).
    
    Thread-safe singleton that creates embeddings client based on 
    EMBED_PROVIDER environment variable.
    
    Returns:
        Embeddings: The default embedding client
    """
    global _default_embeddings, _default_embeddings_lock
    
    if _default_embeddings is None:
        import threading
        if _default_embeddings_lock is None:
            _default_embeddings_lock = threading.Lock()
        
        with _default_embeddings_lock:
            # Double-check locking pattern
            if _default_embeddings is None:
                from src.config.models import settings
                _default_embeddings = get_embeddings()
                model = (
                    settings.embed_model 
                    if settings.embed_provider == "openai" 
                    else settings.vertex_embed_model
                )
                logger.info(
                    f"✅ Initialized default embeddings: "
                    f"provider={settings.embed_provider}, "
                    f"model={model}, "
                    f"dimensions={get_embedding_dimension(model)}"
                )
    
    return _default_embeddings


def reset_default_embeddings() -> None:
    """
    Reset the singleton default embeddings client.
    
    ⚠️ Use only for testing or when provider config changes.
    """
    global _default_embeddings
    _default_embeddings = None
    logger.info("🔄 Reset default embeddings singleton")
