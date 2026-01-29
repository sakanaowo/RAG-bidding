"""
LLM Provider Factory Pattern

Provides abstraction layer for switching between LLM providers:
- OpenAI (ChatOpenAI) - Default
- Vertex AI (ChatVertexAI) - Google Cloud enterprise
- Gemini API (ChatGoogleGenerativeAI) - Google API key based

Usage:
    from src.config.llm_provider import get_llm_client, get_default_llm
    
    # Get default LLM (based on LLM_PROVIDER env var)
    llm = get_default_llm()
    
    # Get specific provider
    llm = get_llm_client(provider="vertex")
"""

import os
import logging
from enum import Enum
from typing import Optional

from langchain_core.language_models import BaseChatModel

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    VERTEX_AI = "vertex"
    GEMINI = "gemini"


def get_llm_client(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.0,
    max_tokens: Optional[int] = None,
    **kwargs
) -> BaseChatModel:
    """
    Factory function to create LLM client based on provider.
    
    Args:
        provider: LLM provider (openai, vertex, gemini). 
                  Defaults to LLM_PROVIDER env var.
        model: Model name override
        temperature: Sampling temperature (0.0 = deterministic)
        max_tokens: Maximum tokens in response
        **kwargs: Additional provider-specific arguments
    
    Returns:
        LangChain BaseChatModel instance
    
    Raises:
        ValueError: If provider is not recognized
        ImportError: If required provider package is not installed
    """
    # Import settings here to avoid circular imports
    from src.config.models import settings
    
    provider = provider or settings.llm_provider
    
    if provider == LLMProvider.OPENAI or provider == "openai":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError(
                "langchain-openai package not installed. "
                "Run: pip install langchain-openai"
            )
        
        client = ChatOpenAI(
            model=model or settings.llm_model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        logger.debug(f"Created OpenAI LLM client: model={model or settings.llm_model}")
        return client
    
    elif provider == LLMProvider.VERTEX_AI or provider == "vertex":
        try:
            from langchain_google_vertexai import ChatVertexAI
        except ImportError:
            raise ImportError(
                "langchain-google-vertexai package not installed. "
                "Run: pip install langchain-google-vertexai"
            )
        
        client = ChatVertexAI(
            model=model or settings.vertex_llm_model,
            project=settings.google_cloud_project or None,
            location=settings.google_cloud_location,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        logger.debug(
            f"Created Vertex AI LLM client: model={model or settings.vertex_llm_model}, "
            f"project={settings.google_cloud_project}"
        )
        return client
    
    elif provider == LLMProvider.GEMINI or provider == "gemini":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            raise ImportError(
                "langchain-google-genai package not installed. "
                "Run: pip install langchain-google-genai"
            )
        
        client = ChatGoogleGenerativeAI(
            model=model or settings.gemini_model,
            temperature=temperature,
            max_tokens=max_tokens,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            **kwargs
        )
        logger.debug(f"Created Gemini LLM client: model={model or settings.gemini_model}")
        return client
    
    else:
        raise ValueError(
            f"Unknown LLM provider: {provider}. "
            f"Available: {', '.join([p.value for p in LLMProvider])}"
        )


# ===== Singleton Pattern for Default Client =====
_default_client: Optional[BaseChatModel] = None
_default_client_lock = None  # Will be initialized on first use


def get_default_llm() -> BaseChatModel:
    """
    Get or create default LLM client (singleton pattern).
    
    Thread-safe singleton that creates LLM client based on 
    LLM_PROVIDER environment variable.
    
    Returns:
        BaseChatModel: The default LLM client
    """
    global _default_client, _default_client_lock
    
    if _default_client is None:
        import threading
        if _default_client_lock is None:
            _default_client_lock = threading.Lock()
        
        with _default_client_lock:
            # Double-check locking pattern
            if _default_client is None:
                from src.config.models import settings
                _default_client = get_llm_client()
                logger.info(
                    f"✅ Initialized default LLM client: "
                    f"provider={settings.llm_provider}, "
                    f"model={settings.llm_model if settings.llm_provider == 'openai' else settings.vertex_llm_model}"
                )
    
    return _default_client


def reset_default_llm() -> None:
    """
    Reset the singleton default LLM client.
    
    ⚠️ Use only for testing or when provider config changes.
    """
    global _default_client
    _default_client = None
    logger.info("🔄 Reset default LLM client singleton")
