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
        try:
            from langchain_google_vertexai import VertexAIEmbeddings
        except ImportError:
            raise ImportError(
                "langchain-google-vertexai package not installed. "
                "Run: pip install langchain-google-vertexai"
            )
        
        model_name = model or settings.vertex_embed_model
        
        # Get configured dimension (for gemini-embedding-001 MRL support)
        embed_dim = getattr(settings, 'embed_dimensions', None)
        
        embed_kwargs = {
            "model_name": model_name,
            "project": settings.google_cloud_project or None,
            "location": settings.google_cloud_location,
            **kwargs
        }
        
        # Add output_dimensionality for models that support MRL (like gemini-embedding-001)
        if embed_dim and "gemini" in model_name.lower():
            embed_kwargs["output_dimensionality"] = embed_dim
        
        embeddings = VertexAIEmbeddings(**embed_kwargs)
        
        actual_dim = embed_dim if embed_dim else get_embedding_dimension(model_name)
        logger.debug(
            f"Created Vertex AI Embeddings: model={model_name}, "
            f"dimensions={actual_dim}, "
            f"project={settings.google_cloud_project}"
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
