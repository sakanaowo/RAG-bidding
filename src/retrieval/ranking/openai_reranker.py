"""
OpenAI-based Reranker using GPT models for semantic reranking.

Uses OpenAI API to rerank documents based on query relevance.
More expensive but potentially more accurate than BGE reranker.

NEW: Parallel API calls với asyncio để tăng tốc 10-20x!
"""

import asyncio
import logging
import time
from typing import List, Tuple, Optional
import os

from langchain_core.documents import Document
from openai import OpenAI, AsyncOpenAI

from .base_reranker import BaseReranker

logger = logging.getLogger(__name__)


class OpenAIReranker(BaseReranker):
    """
    OpenAI-based reranker using GPT models.

    Uses GPT-4 or GPT-3.5 to score document relevance to query.

    Pros:
    - High accuracy (GPT-4 understanding)
    - Good for Vietnamese text
    - No model loading (API-based)
    - No GPU required

    Cons:
    - API costs ($$$)
    - Network latency
    - Rate limits
    - Requires API key

    Performance:
    - Latency: ~200-500ms per batch (with parallel processing)
    - Sequential: ~300ms × N docs (SLOW!)
    - Parallel: ~500ms for N docs (FAST!) ⚡
    - Cost: ~$0.01-0.05 per 1000 tokens
    - Quality: Excellent for complex queries

    Usage:
        reranker = OpenAIReranker(model="gpt-4o-mini")
        results = reranker.rerank(query, documents, top_k=5)
    """

    # Model options
    GPT4_TURBO = "gpt-4-turbo-preview"
    GPT4_MINI = "gpt-4o-mini"  # Cheaper, faster
    GPT35_TURBO = "gpt-3.5-turbo"  # Cheapest

    def __init__(
        self,
        model_name: str = GPT4_MINI,  # Default to gpt-4o-mini (balance cost/quality)
        api_key: Optional[str] = None,
        temperature: float = 0.0,  # Deterministic for ranking
        max_tokens: int = 10,  # Only need a score
        use_parallel: bool = True,  # 🆕 Enable parallel API calls
    ):
        """
        Initialize OpenAI reranker.

        Args:
            model_name: OpenAI model to use (gpt-4o-mini recommended)
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            temperature: Sampling temperature (0 = deterministic)
            max_tokens: Max tokens for response (10 is enough for score)
            use_parallel: Use async parallel API calls (10-20x faster!)
        """
        super().__init__()

        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.use_parallel = use_parallel

        # Get API key from param or environment
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API key required! "
                "Set OPENAI_API_KEY environment variable or pass api_key parameter."
            )

        # Initialize OpenAI clients (sync + async)
        self.client = OpenAI(api_key=api_key)
        self.async_client = AsyncOpenAI(api_key=api_key)  # 🆕 Async client

        logger.info(f"✅ OpenAI reranker initialized: {model_name}")
        logger.info(f"⚙️  Temperature: {temperature}, Max tokens: {max_tokens}")
        logger.info(f"⚡ Parallel mode: {'ENABLED' if use_parallel else 'DISABLED'}")

    def _score_document(self, query: str, document_text: str) -> float:
        """
        Score a single document's relevance to query using OpenAI.

        Prompts GPT to rate relevance on scale 0-10.

        Args:
            query: User query
            document_text: Document content to score

        Returns:
            Relevance score (0.0 to 1.0)
        """
        # Truncate document to avoid token limits
        max_doc_chars = 2000  # ~500 tokens
        if len(document_text) > max_doc_chars:
            document_text = document_text[:max_doc_chars] + "..."

        # Prompt GPT to score relevance
        prompt = f"""Bạn là một chuyên gia đánh giá độ liên quan của văn bản pháp luật Việt Nam.

Cho câu hỏi và đoạn văn bản dưới đây, hãy đánh giá độ liên quan từ 0-10:
- 0: Hoàn toàn không liên quan
- 5: Có liên quan một phần
- 10: Rất liên quan, trả lời trực tiếp câu hỏi

Chỉ trả về một số từ 0-10, không giải thích.

Câu hỏi: {query}

Văn bản:
{document_text}

Điểm số (0-10):"""

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "Bạn là chuyên gia đánh giá văn bản pháp luật.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            # Parse score from response
            score_text = response.choices[0].message.content.strip()
            try:
                score = float(score_text)
                # Normalize to 0-1
                normalized_score = score / 10.0
                return max(0.0, min(1.0, normalized_score))
            except ValueError:
                logger.warning(f"⚠️  Invalid score format: '{score_text}', using 0.0")
                return 0.0

        except Exception as e:
            logger.error(f"❌ OpenAI API error: {e}")
            return 0.0

    async def _score_document_async(self, query: str, document_text: str) -> float:
        """
        🆕 Async version: Score document using async OpenAI client.

        Allows parallel API calls for 10-20x speedup!

        Args:
            query: User query
            document_text: Document content to score

        Returns:
            Relevance score (0.0 to 1.0)
        """
        # Truncate document to avoid token limits
        max_doc_chars = 2000  # ~500 tokens
        if len(document_text) > max_doc_chars:
            document_text = document_text[:max_doc_chars] + "..."

        # Prompt GPT to score relevance
        prompt = f"""Bạn là một chuyên gia đánh giá độ liên quan của văn bản pháp luật Việt Nam.

                Cho câu hỏi và đoạn văn bản dưới đây, hãy đánh giá độ liên quan từ 0-10:
                - 0: Hoàn toàn không liên quan
                - 5: Có liên quan một phần
                - 10: Rất liên quan, trả lời trực tiếp câu hỏi

                Chỉ trả về một số từ 0-10, không giải thích.

                Câu hỏi: {query}

                Văn bản:
                {document_text}

                Điểm số (0-10):"""

        try:
            # 🆕 Use async client
            response = await self.async_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "Bạn là chuyên gia đánh giá văn bản pháp luật.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            # Parse score from response
            score_text = response.choices[0].message.content.strip()
            try:
                score = float(score_text)
                # Normalize to 0-1
                normalized_score = score / 10.0
                return max(0.0, min(1.0, normalized_score))
            except ValueError:
                logger.warning(f"⚠️  Invalid score format: '{score_text}', using 0.0")
                return 0.0

        except Exception as e:
            logger.error(f"❌ OpenAI API error: {e}")
            return 0.0

    async def _rerank_parallel(
        self, query: str, documents: List[Document]
    ) -> List[Tuple[Document, float]]:
        """
        🆕 Parallel reranking using asyncio.gather().

        Sends all API requests concurrently instead of sequentially.
        Speedup: 300ms × N docs → ~500ms total (10-20x faster!)

        Args:
            query: User query
            documents: Documents to rerank

        Returns:
            List of (document, score) tuples
        """
        # Create async tasks for all documents
        tasks = [
            self._score_document_async(query, doc.page_content) for doc in documents
        ]

        # Execute all tasks in parallel
        scores = await asyncio.gather(*tasks)

        # Combine docs with scores
        doc_scores = list(zip(documents, scores))

        return doc_scores

    def rerank(
        self, query: str, documents: List[Document], top_k: int = 5
    ) -> List[Tuple[Document, float]]:
        """
        Rerank documents using OpenAI API.

        🆕 Now supports parallel processing for 10-20x speedup!

        Args:
            query: User query (Vietnamese)
            documents: Retrieved documents to rerank
            top_k: Number of top documents to return

        Returns:
            List of (document, score) sorted by relevance
        """
        if not documents:
            logger.warning("⚠️  Empty documents list")
            return []

        start_time = time.time()

        # Limit documents to avoid excessive API costs
        max_docs = 20  # Don't send too many to API
        if len(documents) > max_docs:
            logger.warning(
                f"⚠️  Too many docs ({len(documents)}), limiting to {max_docs}"
            )
            documents = documents[:max_docs]

        # 🆕 Use parallel or sequential processing
        if self.use_parallel:
            # Parallel: Run async code in sync context
            doc_scores = asyncio.run(self._rerank_parallel(query, documents))
            processing_mode = "PARALLEL"
        else:
            # Sequential: Original implementation
            doc_scores = []
            for i, doc in enumerate(documents):
                score = self._score_document(query, doc.page_content)
                doc_scores.append((doc, score))

                # Log progress
                if (i + 1) % 5 == 0:
                    logger.debug(f"📊 Scored {i+1}/{len(documents)} documents")
            processing_mode = "SEQUENTIAL"

        # Sort by score descending
        doc_scores.sort(key=lambda x: x[1], reverse=True)

        # Calculate metrics
        latency = (time.time() - start_time) * 1000
        top_score = doc_scores[0][1] if doc_scores else 0

        logger.info(
            f"📊 Reranked {len(documents)} docs in {latency:.1f}ms ({processing_mode}) | "
            f"Top score: {top_score:.4f} | Returning top {top_k}"
        )

        # Log top 3 scores for debugging
        if logger.isEnabledFor(logging.DEBUG):
            for i, (doc, score) in enumerate(doc_scores[:3]):
                preview = doc.page_content[:80].replace("\n", " ")
                logger.debug(f"  [{i+1}] {score:.4f} - {preview}...")

        return doc_scores[:top_k]

    def rerank_batch(
        self, queries: List[str], documents_list: List[List[Document]], top_k: int = 5
    ) -> List[List[Tuple[Document, float]]]:
        """
        Batch reranking for multiple queries.

        Note: OpenAI API doesn't have native batch support,
        so this just calls rerank() for each query sequentially.

        Could be optimized with async/concurrent requests in future.
        """
        results = []
        for query, docs in zip(queries, documents_list):
            result = self.rerank(query, docs, top_k)
            results.append(result)
        return results
