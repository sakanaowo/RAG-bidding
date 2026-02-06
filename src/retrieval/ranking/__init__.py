"""
Document Reranking Module

Provides reranker implementations to improve ranking quality of retrieved documents.

Available Rerankers:
- VertexAIReranker: Production reranker using Google Discovery Engine Ranking API (default)
- BGEReranker: Local reranker using BAAI/bge-reranker-v2-m3 (requires sentence_transformers)
- OpenAIReranker: Alternative reranker using GPT models (API-based)

Note: BGEReranker is lazy-loaded to avoid importing sentence_transformers when not needed.
"""

from .base_reranker import BaseReranker
from .vertex_reranker import VertexAIReranker

# Lazy loading for BGE to avoid sentence_transformers import at startup
# BGE is not used in production - we use VertexAIReranker instead
_bge_module = None


def _load_bge_module():
    """Lazy load BGE reranker module only when explicitly needed."""
    global _bge_module
    if _bge_module is None:
        from . import bge_reranker as _bge_module
    return _bge_module


def get_singleton_reranker(*args, **kwargs):
    """Get singleton BGE reranker instance (lazy loaded)."""
    return _load_bge_module().get_singleton_reranker(*args, **kwargs)


def reset_singleton_reranker():
    """Reset singleton BGE reranker instance (testing only)."""
    return _load_bge_module().reset_singleton_reranker()


def __getattr__(name):
    """Lazy load attributes to avoid importing sentence_transformers at module level."""
    if name == "BGEReranker":
        return _load_bge_module().BGEReranker
    if name == "OpenAIReranker":
        from .openai_reranker import OpenAIReranker

        return OpenAIReranker
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BaseReranker",
    "VertexAIReranker",  # ⭐ Production reranker (Google Cloud)
    "BGEReranker",  # Local reranker (lazy-loaded)
    "get_singleton_reranker",  # Singleton factory (lazy-loaded)
    "reset_singleton_reranker",  # Testing only (lazy-loaded)
    "OpenAIReranker",  # Alternative reranker (API-based)
]
