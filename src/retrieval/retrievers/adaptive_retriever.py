"""
Adaptive Retriever - Dynamic k dựa trên độ phức tạp câu hỏi
"""

import re
from typing import List, Dict, Optional
from langchain_core.documents import Document
from src.embedding.store.pgvector_store import vector_store
from config.models import settings


class AdaptiveRetriever:
    """
    Retriever thông minh tự động điều chỉnh số lượng documents
    dựa trên độ phức tạp và loại câu hỏi
    """

    def __init__(self):
        self.base_retriever = vector_store.as_retriever()

        # Question complexity indicators
        self.complex_keywords = [
            "so sánh",
            "phân tích",
            "đánh giá",
            "ưu nhược điểm",
            "tại sao",
            "như thế nào",
            "giải thích",
            "chi tiết",
            "khác biệt",
            "tương đồng",
            "mối quan hệ",
            "nguyên nhân",
            "hậu quả",
            "ảnh hưởng",
            "tác động",
            "ý nghĩa",
        ]

        self.simple_keywords = [
            "là gì",
            "định nghĩa",
            "khái niệm",
            "ai",
            "khi nào",
            "ở đâu",
            "bao nhiều",
            "có phải",
            "danh sách",
        ]

        self.factual_patterns = [
            r"^\s*ai\s+",
            r"^\s*gì\s+",
            r"^\s*khi\s+nào\s+",
            r"^\s*ở\s+đâu\s+",
            r"^\s*bao\s+nhiêu\s+",
        ]

    # TODO: replace analyze_question_complexity with class QuestionAnalyzer
    def analyze_question_complexity(self, question: str) -> Dict:
        """Phân tích độ phức tạp của câu hỏi"""
        question_lower = question.lower().strip()

        # Check factual patterns
        is_factual = any(
            re.match(pattern, question_lower) for pattern in self.factual_patterns
        )

        # Count complex vs simple indicators
        complex_score = sum(
            1 for keyword in self.complex_keywords if keyword in question_lower
        )
        simple_score = sum(
            1 for keyword in self.simple_keywords if keyword in question_lower
        )

        # Question length and structure
        word_count = len(question.split())
        has_multiple_clauses = (
            "," in question or "và" in question_lower or "hoặc" in question_lower
        )

        # Determine complexity level
        if is_factual and simple_score > 0:
            complexity = "simple"
            suggested_k = 2
        elif complex_score > simple_score and (word_count > 10 or has_multiple_clauses):
            complexity = "complex"
            suggested_k = 8
        elif word_count > 15 or complex_score > 0:
            complexity = "moderate"
            suggested_k = 5
        else:
            complexity = "simple"
            suggested_k = 3

        return {
            "complexity": complexity,
            "suggested_k": suggested_k,
            "word_count": word_count,
            "complex_score": complex_score,
            "simple_score": simple_score,
            "is_factual": is_factual,
            "has_multiple_clauses": has_multiple_clauses,
        }

    def get_documents(self, question: str, custom_k: int = None) -> List[Document]:
        """
        Retrieve documents với adaptive k
        """
        analysis = self.analyze_question_complexity(question)

        # Use custom k nếu provided, otherwise use suggested k
        k = custom_k if custom_k is not None else analysis["suggested_k"]

        # Ensure k is within reasonable bounds
        k = max(1, min(k, 15))

        # Configure retriever với dynamic k
        retriever = vector_store.as_retriever(
            search_kwargs={
                "k": k,
                "score_threshold": getattr(settings, "min_relevance_score", 0.7),
            }
        )

        documents = retriever.invoke(question)

        # Log analysis for debugging
        print(
            f"Question complexity: {analysis['complexity']}, Using k={k}, Retrieved: {len(documents)} docs"
        )

        return documents

    def get_documents_with_metadata(self, question: str) -> Dict:
        """
        Retrieve documents kèm metadata về analysis
        """
        analysis = self.analyze_question_complexity(question)
        documents = self.get_documents(question)

        return {
            "documents": documents,
            "analysis": analysis,
            "retrieval_strategy": f"Adaptive retrieval (k={analysis['suggested_k']})",
        }


# Global adaptive retriever instance
adaptive_retriever = AdaptiveRetriever()


def get_contextual_documents(
    question: str, context_history: List[str] = None
) -> List[Document]:
    """
    Enhanced retrieval với conversation context
    """
    if context_history and len(context_history) > 0:
        # Combine recent questions for better context understanding
        combined_query = f"Ngữ cảnh trước: {' '.join(context_history[-2:])}. Câu hỏi hiện tại: {question}"
        return adaptive_retriever.get_documents(combined_query)
    else:
        return adaptive_retriever.get_documents(question)


# Utility functions
def explain_retrieval_strategy(question: str, analysis: Optional[Dict] = None) -> str:
    """Giải thích chiến lược retrieval cho câu hỏi"""
    if analysis is None:
        analysis = adaptive_retriever.analyze_question_complexity(question)

    explanation = f"""
    Phân tích câu hỏi: "{question}"
    
    - Độ phức tạp: {analysis['complexity']}
    - Số từ: {analysis['word_count']}
    - Điểm phức tạp: {analysis['complex_score']}
    - Câu hỏi thực tế đơn giản: {analysis['is_factual']}
    - Có mệnh đề phụ: {analysis['has_multiple_clauses']}
    
    → Đề xuất retrieve {analysis['suggested_k']} documents
    """

    return explanation.strip()


def benchmark_adaptive_vs_fixed(questions: List[str], fixed_k: int = 5) -> Dict:
    """
    So sánh hiệu quả giữa adaptive và fixed k
    """
    results = {"adaptive": [], "fixed": [], "questions": questions}

    for question in questions:
        # Adaptive
        adaptive_docs = adaptive_retriever.get_documents_with_metadata(question)
        results["adaptive"].append(
            {
                "question": question,
                "k_used": adaptive_docs["analysis"]["suggested_k"],
                "doc_count": len(adaptive_docs["documents"]),
                "complexity": adaptive_docs["analysis"]["complexity"],
            }
        )

        # Fixed
        fixed_docs = adaptive_retriever.get_documents(question, custom_k=fixed_k)
        results["fixed"].append(
            {
                "question": question,
                "k_used": fixed_k,
                "doc_count": len(fixed_docs),
                "complexity": "n/a",
            }
        )

    return results
