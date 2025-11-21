"""
Document Reranking Module

Cung cấp các reranker implementations để cải thiện
ranking quality của retrieved documents.
"""

from .base_reranker import BaseReranker
from .bge_reranker import BGEReranker, get_singleton_reranker, reset_singleton_reranker
from .openai_reranker import OpenAIReranker

# Import các rerankers khác nếu đã implement
try:
    from .cross_encoder_reranker import CrossEncoderReranker
except ImportError:
    CrossEncoderReranker = None

try:
    from .llm_reranker import LLMReranker
except ImportError:
    LLMReranker = None

try:
    from .cohere_reranker import CohereReranker
except ImportError:
    CohereReranker = None

try:
    from .legal_score_reranker import LegalScoreReranker
except ImportError:
    LegalScoreReranker = None


__all__ = [
    "BaseReranker",
    "BGEReranker",
    "get_singleton_reranker",  # ⭐ Singleton factory (production use)
    "reset_singleton_reranker",  # ⚠️ Testing only
    "OpenAIReranker",  # 🆕 OpenAI-based reranker
]

# Thêm vào __all__ nếu available
if CrossEncoderReranker:
    __all__.append("CrossEncoderReranker")
if LLMReranker:
    __all__.append("LLMReranker")
if CohereReranker:
    __all__.append("CohereReranker")
if LegalScoreReranker:
    __all__.append("LegalScoreReranker")
