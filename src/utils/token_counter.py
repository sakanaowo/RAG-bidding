"""Token counting utilities for RAG system.

Uses tiktoken for accurate token counting with LLM models.
Supports both OpenAI and Google Gemini models.
"""

import tiktoken
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Cache encoder for performance
_encoder_cache: dict = {}


def get_encoder(model: str = "gemini-2.5-flash") -> tiktoken.Encoding:
    """Get cached tiktoken encoder for a model.

    Args:
        model: Model name (default: gemini-2.5-flash)

    Returns:
        tiktoken.Encoding instance

    Note:
        For Gemini models, uses cl100k_base encoding as approximation.
        Gemini tokenization is similar but not identical.
    """
    if model not in _encoder_cache:
        try:
            # For Gemini models, use cl100k_base as approximation
            if model.startswith("gemini"):
                _encoder_cache[model] = tiktoken.get_encoding("cl100k_base")
            else:
                _encoder_cache[model] = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fallback to cl100k_base for unknown models
            logger.warning(f"Unknown model {model}, using cl100k_base encoding")
            _encoder_cache[model] = tiktoken.get_encoding("cl100k_base")
    return _encoder_cache[model]


def count_tokens(text: str, model: str = "gemini-2.5-flash") -> int:
    """Count tokens in a text string.

    Args:
        text: Text to count tokens for
        model: Model name for tokenizer (default: gemini-2.5-flash)

    Returns:
        Number of tokens
    """
    if not text:
        return 0
    encoder = get_encoder(model)
    return len(encoder.encode(text))


def count_message_tokens(
    user_message: str,
    assistant_response: str,
    system_prompt: Optional[str] = None,
    context_docs: Optional[list] = None,
    model: str = "gemini-2.5-flash",
) -> dict:
    """Count tokens for a complete chat interaction.

    Args:
        user_message: User's input message
        assistant_response: AI's response
        system_prompt: Optional system prompt
        context_docs: Optional list of context documents
        model: Model name for tokenizer

    Returns:
        Dict with token counts:
            - input_tokens: Tokens in user message + system + context
            - output_tokens: Tokens in assistant response
            - total_tokens: Sum of input and output
    """
    encoder = get_encoder(model)

    # Count input tokens
    input_tokens = len(encoder.encode(user_message)) if user_message else 0

    # Add system prompt tokens
    if system_prompt:
        input_tokens += len(encoder.encode(system_prompt))
        # Add overhead for system message formatting (~4 tokens)
        input_tokens += 4

    # Add context document tokens
    if context_docs:
        for doc in context_docs:
            if isinstance(doc, str):
                input_tokens += len(encoder.encode(doc))
            elif hasattr(doc, "page_content"):
                input_tokens += len(encoder.encode(doc.page_content))
            elif isinstance(doc, dict) and "content" in doc:
                input_tokens += len(encoder.encode(doc["content"]))

    # Add overhead for message formatting (~4 tokens per message)
    input_tokens += 8  # user + assistant message overhead

    # Count output tokens
    output_tokens = len(encoder.encode(assistant_response)) if assistant_response else 0

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }


def estimate_cost_usd(
    input_tokens: int, output_tokens: int, model: str = "gemini-2.5-flash"
) -> float:
    """Estimate cost in USD for token usage.

    Pricing as of Feb 2026 (Google Cloud / Vertex AI):
    - gemini-2.5-flash: $0.30/1M input, $2.50/1M output
    - gemini-2.5-pro: $1.25/1M input, $10.00/1M output
    - gemini-2.0-flash: $0.10/1M input, $0.40/1M output
    - gemini-embedding-001: $0.15/1M tokens (input only)

    Legacy OpenAI pricing (for reference):
    - gpt-4o-mini: $0.15/1M input, $0.60/1M output
    - text-embedding-3-large: $0.13/1M tokens

    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        model: Model name

    Returns:
        Estimated cost in USD
    """
    # Pricing per 1M tokens (Google Cloud / Vertex AI - Feb 2026)
    pricing = {
        # Google Gemini models (primary)
        "gemini-2.5-flash": {"input": 0.30, "output": 2.50},
        "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
        "gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40},
        "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
        "gemini-2.0-flash-lite": {"input": 0.075, "output": 0.30},
        "gemini-embedding-001": {"input": 0.15, "output": 0.00},
        # Vertex AI text embeddings
        "text-embedding-004": {"input": 0.025, "output": 0.00},
        # Legacy OpenAI models (for backward compatibility)
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4-turbo": {"input": 10.00, "output": 30.00},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
        "text-embedding-3-small": {"input": 0.02, "output": 0.02},
        "text-embedding-3-large": {"input": 0.13, "output": 0.13},
    }

    model_pricing = pricing.get(model, pricing["gemini-2.5-flash"])

    input_cost = (input_tokens / 1_000_000) * model_pricing["input"]
    output_cost = (output_tokens / 1_000_000) * model_pricing["output"]

    return round(input_cost + output_cost, 8)
