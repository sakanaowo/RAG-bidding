"""
Base Reranker Abstract Class

Cung cấp interface chung cho tất cả reranking implementations.
"""

from abc import ABC, abstractmethod
from typing import List, Tuple
from langchain_core.documents import Document


class BaseReranker(ABC):
    """
    Abstract base class cho tất cả rerankers

    Reranker nhận query và list documents, trả về
    documents được xếp hạng lại theo độ liên quan.
    """

    @abstractmethod
    def rerank(
        self, query: str, documents: List[Document], top_k: int = 5
    ) -> List[Tuple[Document, float]]:
        """
        Xếp hạng lại documents theo độ liên quan với query

        Args:
            query: Câu hỏi của user
            documents: List documents từ retriever
            top_k: Số documents trả về (mặc định 5)

        Returns:
            List of (document, score) tuples, sorted by score descending

        Example:
            >>> reranker = PhoBERTReranker()
            >>> docs = [doc1, doc2, doc3]
            >>> results = reranker.rerank("Điều 14 Luật Đấu thầu", docs, top_k=2)
            >>> [(doc1, 0.95), (doc3, 0.82)]
        """
        pass

    def rerank_batch(
        self, queries: List[str], documents_list: List[List[Document]], top_k: int = 5
    ) -> List[List[Tuple[Document, float]]]:
        """
        Batch reranking cho nhiều queries

        Mặc định gọi rerank() cho từng query.
        Subclass có thể override để optimize batch processing.

        Args:
            queries: List các câu hỏi
            documents_list: List các list documents (tương ứng với mỗi query)
            top_k: Số documents trả về cho mỗi query

        Returns:
            List of lists of (document, score) tuples
        """
        return [
            self.rerank(query, docs, top_k)
            for query, docs in zip(queries, documents_list)
        ]
