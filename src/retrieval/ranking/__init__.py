"""
Document Reranking Module

Provides reranker implementations to improve ranking quality of retrieved documents.

Available Rerankers:
- BGEReranker: Production reranker using BAAI/bge-reranker-v2-m3 (default)
- OpenAIReranker: Alternative reranker using GPT models (API-based)
"""

from .base_reranker import BaseReranker
from .bge_reranker import BGEReranker, get_singleton_reranker, reset_singleton_reranker
from .openai_reranker import OpenAIReranker


__all__ = [
    "BaseReranker",
    "BGEReranker",
    "get_singleton_reranker",  # ⭐ Singleton factory (production use)
    "reset_singleton_reranker",  # ⚠️ Testing only
    "OpenAIReranker",  # Alternative reranker (API-based)
]
