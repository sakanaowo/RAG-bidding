from typing import List, Tuple
from src.retrieval.query_processing.strategies.base_strategy import (
    BaseEnhancementStrategy,
)

import logging

logger = logging.getLogger(__name__)


class DecompositionStrategy(BaseEnhancementStrategy):
    """
    Query Decomposition Strategy

    ref: https://arxiv.org/abs/2205.10625
    """

    def __init__(self, llm_model, temperature=0.7, max_subqueries=5):
        super().__init__(llm_model, temperature)
        self.max_subqueries = max_subqueries

    def enhance(self, query: str) -> List[str]:
        """
        Decompose complex query into sub-questions

        Returns:
            [original_query] + sub_queries (if decomposable)
            [original_query] (if not decomposable)
        """

        try:
            if not self._should_decompose(query):
                logger.info("Query not complex enough to decompose")
                return [query]

            system_prompt, user_prompt = self._build_decomposition_prompt(query)
            response = self._call_llm(system_prompt, user_prompt)

            sub_questions = self._parse_list_response(response)
            sub_questions = sub_questions[: self.max_subqueries]

            results = [query] + sub_questions
            logger.info(f"Decomposed query into {len(sub_questions)} sub-questions")
            results = results

            return results
        except Exception as e:
            logger.error(f"Error in query decomposition: {e}")
            return [query]

    def _build_decomposition_prompt(self, query: str) -> Tuple[str, str]:
        system_prompt = f"""
        Bạn là trợ lý chuyên phân tách câu hỏi phức tạp.

        NHIỆM VỤ: Chia câu hỏi phức tạp thành các câu hỏi con ĐƠN GIẢN hơn.

        QUY TẮC:
        - Mỗi sub-question tập trung vào 1 khía cạnh cụ thể
        - Trả lời TẤT CẢ sub-questions sẽ trả lời được câu hỏi gốc
        - Tối đa {self.max_subqueries} câu hỏi con
        - Mỗi câu hỏi trên 1 dòng
        - KHÔNG đánh số, KHÔNG dùng dấu gạch đầu dòng

        VÍ DỤ:
        Câu phức tạp: "So sánh ưu nhược điểm đấu thầu rộng rãi và chỉ định thầu?"

        Sub-questions:
        Ưu điểm của đấu thầu rộng rãi?
        Nhược điểm của đấu thầu rộng rãi?
        Ưu điểm của chỉ định thầu?
        Nhược điểm của chỉ định thầu?
        """
        user_prompt = f"""Câu hỏi phức tạp: {query}
        Phân tách thành các câu hỏi con:"""

        return system_prompt, user_prompt

    def _should_decompose(self, query: str) -> bool:
        """
        Heuristic to decide if query should be decomposed

        Simple check: if query contains "và" (and), "hoặc" (or), "nếu" (if)
        """
        query_lower = query.lower()

        # Indicator 1: Conjunctions
        conjunctions = ["và", "hoặc", "cùng với", "kèm theo"]
        has_conjunction = any(conj in query_lower for conj in conjunctions)

        # Indicator 2: Comparison keywords
        comparison_keywords = ["so sánh", "khác biệt", "giống nhau", "ưu nhược điểm"]
        has_comparison = any(kw in query_lower for kw in comparison_keywords)

        # Indicator 3: Multiple clauses (dấu phẩy)
        clause_count = query.count(",") + query.count(";")

        # Indicator 4: Length
        word_count = len(query.split())

        # Decision logic
        if has_comparison:
            return True
        if has_conjunction and word_count > 10:
            return True
        if clause_count >= 2:
            return True
        if word_count > 20:
            return True

        return False
