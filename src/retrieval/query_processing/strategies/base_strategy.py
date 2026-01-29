from abc import ABC, abstractmethod
from typing import List, Optional
from src.config.llm_provider import get_llm_client
from langchain.schema import SystemMessage, HumanMessage
import os
import re
import logging
import time

logger = logging.getLogger(__name__)


class BaseEnhancementStrategy(ABC):
    """
    Abstract base class cho tất cả enhancement strategies

    Provides:
    - LLM client (from provider factory - supports OpenAI, Vertex AI, Gemini)
    - Common LLM calling method
    - Response parsing utilities
    - Error handling & retries
    """

    def __init__(self, llm_model: str, temperature: float = 0.7):
        """
        Initialize strategy

        Args:
            llm_model: Model name (uses provider from settings)
            temperature: Sampling temperature (0.0-1.0)
        """
        self.llm_model = llm_model
        self.temperature = temperature

        # Use LLM provider factory (supports OpenAI, Vertex AI, Gemini)
        self.client = get_llm_client(
            temperature=temperature,
            max_tokens=500,
        )

        logger.info(
            f"Initialized {self.__class__.__name__} "
            f"with model={llm_model}, temp={temperature}"
        )

    @abstractmethod
    def enhance(self, query: str) -> List[str]:
        """
        Main enhancement method - must implement in subclass

        Args:
            query: Original user query

        Returns:
            List of enhanced queries
        """
        pass

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """
        Call LLM with retry logic

        Args:
            system_prompt: System instructions
            user_prompt: User query/request

        Returns:
            LLM response text

        Raises:
            Exception: After max retries failed
        """
        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]

                response = self.client.invoke(messages)
                return response.content.strip()

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")

                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logger.error(f"All retries exhausted")
                    raise Exception(f"LLM call failed: {str(e)}")

    def _parse_list_response(self, response: str) -> List[str]:
        """
        Parse LLM response into list of strings

        Handles:
        - Numbered lists (1. 2. 3.)
        - Bulleted lists (- * •)
        - Plain newline-separated

        Args:
            response: Raw LLM response

        Returns:
            List of cleaned strings
        """
        if not response or not response.strip():
            return []

        lines = response.strip().split("\n")
        parsed = []

        for line in lines:
            if not line.strip():
                continue

            # Remove prefixes
            cleaned = re.sub(r"^\s*[\d]+[\.\)]\s*", "", line)
            cleaned = re.sub(r"^\s*[-*•]\s*", "", cleaned)
            cleaned = cleaned.strip()

            if cleaned:
                parsed.append(cleaned)

        return parsed
