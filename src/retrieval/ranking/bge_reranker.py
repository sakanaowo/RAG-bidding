"""
BGE Reranker for Vietnamese Legal Documents

Sử dụng BAAI/bge-reranker-v2-m3 - multilingual cross-encoder
đã được fine-tuned cho reranking task.
"""

from sentence_transformers import CrossEncoder
from typing import List, Tuple, Optional
from langchain_core.documents import Document
import logging
import time
import torch

from .base_reranker import BaseReranker

logger = logging.getLogger(__name__)


class BGEReranker(BaseReranker):
    """
    BGE Multilingual Reranker cho văn bản pháp luật Việt Nam

    Default Model: BAAI/bge-reranker-v2-m3 ⭐
    - ĐÃ FINE-TUNED cho reranking task
    - Multilingual (hỗ trợ 180+ ngôn ngữ, bao gồm tiếng Việt)
    - KHÔNG CÓ WARNING về uninitialized weights
    - Max sequence length: 512 tokens
    - State-of-the-art performance

    Alternative Models (nếu cần):
    - vinai/phobert-base-v2: Vietnamese-specific (chưa fine-tuned cho reranking)
    - vinai/phobert-large: Larger Vietnamese model (chưa fine-tuned)

    Performance:
    - Latency: ~100-150ms for 10 docs on CPU
    - Accuracy: Excellent cho tiếng Việt và multilingual
    - Score separation: Clear distinction between relevant/irrelevant docs

    Note:
    - Sử dụng AutoTokenizer tự động (không xung đột với tiktoken cho chunking)
    - Device: cpu (có thể chuyển sang cuda nếu có GPU để tăng tốc)
    - Batch processing: Hỗ trợ batch inference để tối ưu throughput
    """

    # Model options for RERANKING
    BGE_RERANKER_M3 = "BAAI/bge-reranker-v2-m3"  # ⭐ DEFAULT (fine-tuned, multilingual)
    BGE_RERANKER_BASE = "BAAI/bge-reranker-base"  # Alternative BGE model
    PHOBERT_BASE = "vinai/phobert-base-v2"  # Vietnamese (not fine-tuned for reranking)

    # Note: huynguyen251/phobert-legal-qa-v2 is for QA task, NOT reranking
    # Use it separately in generation pipeline for answer extraction

    def __init__(
        self,
        model_name: str = BGE_RERANKER_M3,  # ⭐ Changed to fine-tuned model
        device: Optional[str] = None,  # ⭐ Auto-detect GPU
        max_length: int = 512,  # ⭐ BGE supports 512 tokens
        batch_size: int = 32,  # ⭐ Increased for GPU
        cache_dir: Optional[str] = None,
    ):
        """
        Args:
            model_name: Reranker model name
                Default: BAAI/bge-reranker-v2-m3 (fine-tuned, multilingual)
                Alternative: vinai/phobert-base-v2 (Vietnamese, not fine-tuned)
            device: "cpu", "cuda", or None (auto-detect GPU)
            max_length: Max tokens (BGE max = 512, PhoBERT max = 256)
            batch_size: Batch size for inference (32 for GPU, 16 for CPU)
            cache_dir: Model cache directory (default: ~/.cache/huggingface)
        """
        logger.info(f"🔧 Initializing reranker: {model_name}")

        # Auto-detect device if not specified
        if device is None:
            try:
                if torch.cuda.is_available():
                    device = "cuda"
                    logger.info("🎮 GPU detected! Using CUDA for acceleration")
                else:
                    device = "cpu"
                    logger.info("💻 No GPU detected, using CPU")
            except Exception as e:
                # Handle CUDA initialization errors gracefully
                logger.warning(f"⚠️  CUDA check failed ({str(e)}), falling back to CPU")
                device = "cpu"

        self.model_name = model_name
        self.device = device
        self.max_length = max_length

        # Auto-adjust batch size for CPU
        if device == "cpu" and batch_size > 16:
            logger.info(f"⚙️  CPU detected, reducing batch_size from {batch_size} to 16")
            batch_size = 16

        self.batch_size = batch_size

        # Auto-adjust max_length based on model
        if "phobert" in model_name.lower() and max_length > 256:
            logger.warning(f"⚠️  PhoBERT max length is 256, adjusting from {max_length}")
            self.max_length = 256

        # Load CrossEncoder (tự động load AutoTokenizer bên trong)
        try:
            self.model = CrossEncoder(
                model_name,
                device=device,
                max_length=self.max_length,
                model_kwargs={"cache_dir": cache_dir} if cache_dir else None,
            )
            logger.info(f"✅ Model loaded on {device}")
            logger.info(f"📦 Max sequence length: {self.max_length} tokens")
        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            raise

    def rerank(
        self, query: str, documents: List[Document], top_k: int = 5
    ) -> List[Tuple[Document, float]]:
        """
        Rerank documents using BGE cross-encoder

        Args:
            query: User query (tiếng Việt)
            documents: Retrieved documents
            top_k: Number of top documents to return

        Returns:
            List of (document, score) sorted by score descending
        """
        if not documents:
            logger.warning("⚠️  Empty documents list")
            return []

        start_time = time.time()

        # Truncate nếu có quá nhiều docs (tránh OOM)
        if len(documents) > 50:
            logger.warning(f"⚠️  Too many docs ({len(documents)}), truncating to 50")
            documents = documents[:50]

        # Chuẩn bị query-document pairs
        pairs = []
        for doc in documents:
            # Truncate content nếu quá dài
            # BGE max 512 tokens, PhoBERT max 256 tokens
            # Ước tính: 1 token ≈ 4 chars cho tiếng Việt
            max_chars = (self.max_length - 50) * 4  # Reserve 50 tokens for query
            content = doc.page_content[:max_chars]
            pairs.append([query, content])

        # Predict relevance scores
        try:
            scores = self.model.predict(
                pairs, batch_size=self.batch_size, show_progress_bar=False
            )
        except Exception as e:
            logger.error(f"❌ Prediction error: {e}")
            # Fallback: return original order with dummy scores
            return [(doc, 1.0 - i * 0.1) for i, doc in enumerate(documents[:top_k])]

        # Zip documents with scores và sort
        doc_scores = list(zip(documents, scores))
        doc_scores.sort(key=lambda x: x[1], reverse=True)

        # Log performance
        latency = (time.time() - start_time) * 1000
        top_score = doc_scores[0][1] if doc_scores else 0

        logger.info(
            f"📊 Reranked {len(documents)} docs in {latency:.1f}ms | "
            f"Top score: {top_score:.4f} | Returning top {top_k}"
        )

        # Debug: Log top 3 scores
        if logger.isEnabledFor(logging.DEBUG):
            for i, (doc, score) in enumerate(doc_scores[:3]):
                preview = doc.page_content[:80].replace("\n", " ")
                logger.debug(f"  [{i+1}] {score:.4f} - {preview}...")

        return doc_scores[:top_k]

    def rerank_batch(
        self, queries: List[str], documents_list: List[List[Document]], top_k: int = 5
    ) -> List[List[Tuple[Document, float]]]:
        """
        Batch reranking (tối ưu hóa sau nếu cần)

        Hiện tại: Gọi rerank() cho từng query
        TODO: Implement true batch processing
        Hiện tại API chỉ xử lý 1 query/request → không cần batch
        """
        logger.info(f"🔄 Batch reranking {len(queries)} queries...")

        results = []
        for query, docs in zip(queries, documents_list):
            result = self.rerank(query, docs, top_k)
            results.append(result)

        return results
