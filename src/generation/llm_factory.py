"""
LLM Factory - Create LLM instances based on provider configuration.

Supports:
- OpenAI: gpt-4o-mini, gpt-4o, gpt-4-turbo
- Gemini: gemini-1.5-flash, gemini-1.5-pro, gemini-2.0-flash-exp, gemini-2.5-flash

Usage:
    from src.generation.llm_factory import get_llm

    # Use default provider from settings
    llm = get_llm(temperature=0)

    # Force specific provider
    llm = get_llm(provider="gemini", temperature=0)
"""

import os
import logging
from typing import Literal, Optional

from langchain_core.language_models.chat_models import BaseChatModel

from src.config.models import settings

logger = logging.getLogger(__name__)

LLMProvider = Literal["openai", "gemini"]


def get_llm(
    provider: Optional[LLMProvider] = None,
    model: Optional[str] = None,
    temperature: float = 0,
    **kwargs,
) -> BaseChatModel:
    """
    Get LLM instance based on provider.

    Args:
        provider: LLM provider ("openai" or "gemini"). Defaults to settings.llm_provider
        model: Model name. Defaults to provider's default model from settings
        temperature: Sampling temperature (0.0-1.0)
        **kwargs: Additional arguments passed to LLM constructor

    Returns:
        LangChain BaseChatModel instance

    Raises:
        ValueError: If provider is unknown or API key is missing
    """
    # Default to settings if not specified
    provider = provider or getattr(settings, "llm_provider", "openai")

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        model = model or settings.llm_model
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        logger.debug(f"Creating OpenAI LLM: model={model}, temp={temperature}")
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            openai_api_key=api_key,
            **kwargs,
        )

    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        model = model or getattr(settings, "gemini_model", "gemini-1.5-flash")
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")

        logger.debug(f"Creating Gemini LLM: model={model}, temp={temperature}")
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            google_api_key=api_key,
            convert_system_message_to_human=True,  # Gemini requirement
            **kwargs,
        )

    else:
        raise ValueError(f"Unknown LLM provider: {provider}. Supported: 'openai', 'gemini'")


def get_fast_llm(**kwargs) -> BaseChatModel:
    """
    Get fast LLM for typical queries.

    - OpenAI: gpt-4o-mini
    - Gemini: gemini-1.5-flash (or configured model)
    """
    return get_llm(**kwargs)


def get_quality_llm(**kwargs) -> BaseChatModel:
    """
    Get high-quality LLM for complex reasoning tasks.

    - OpenAI: gpt-4o
    - Gemini: gemini-1.5-pro
    """
    provider = kwargs.pop("provider", getattr(settings, "llm_provider", "openai"))
    if provider == "openai":
        return get_llm(provider=provider, model="gpt-4o", **kwargs)
    else:
        return get_llm(provider=provider, model="gemini-1.5-pro", **kwargs)


def get_current_provider() -> str:
    """Get the currently configured LLM provider."""
    return getattr(settings, "llm_provider", "openai")


def get_current_model() -> str:
    """Get the currently configured model name."""
    provider = get_current_provider()
    if provider == "gemini":
        return getattr(settings, "gemini_model", "gemini-1.5-flash")
    return settings.llm_model


# TODO: Add Gemini Embeddings support in future
# def get_embeddings(provider: Optional[str] = None) -> Embeddings:
#     """Get embedding instance based on provider."""
#     provider = provider or getattr(settings, "embed_provider", "openai")
#     if provider == "openai":
#         from langchain_openai import OpenAIEmbeddings
#         return OpenAIEmbeddings(model=settings.embed_model)
#     elif provider == "gemini":
#         from langchain_google_genai import GoogleGenerativeAIEmbeddings
#         model = getattr(settings, "gemini_embed_model", "text-embedding-004")
#         return GoogleGenerativeAIEmbeddings(model=f"models/{model}")
#     else:
#         raise ValueError(f"Unknown embedding provider: {provider}")
