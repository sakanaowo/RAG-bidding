"""
Tạo nhiều cách diễn đạt khác nhau cho cùng 1 câu hỏi
để truy xuất thông tin tốt hơn."""

from src.retrieval.query_processing.strategies.base_strategy import (
    BaseEnhancementStrategy,
)
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


class MultiQueryStrategy(BaseEnhancementStrategy):
    """
    Tạo nhiều biến thể của cùng một câu hỏi

    Use case:
    - Tăng recall trong retrieval
    - Cover nhiều cách diễn đạt khác nhau
    - Đặc biệt hiệu quả với tiếng Việt (nhiều cách nói)
    """

    def __init__(self, llm_model, temperature=0.7, max_queries=5):
        super().__init__(llm_model, temperature)
        self.max_queries = max_queries
        logger.info(f"MultiQueryStrategy initialized to generate {max_queries} queries")

    def enhance(self, query: str) -> List[str]:
        """
        Tạo nhiều cách diễn đạt khác nhau cho cùng 1 câu hỏi

        Args:
            query: Câu hỏi gốc

        Returns:
            List[str]: Danh sách các câu hỏi đã được biến thể
        """
        try:
            system_prompt, user_prompt = self._build_multi_query_prompt(query)
            response = self._call_llm(system_prompt, user_prompt)

            variations = self._parse_list_response(response)

            results = [query] + variations

            results = results[: self.max_queries + 1]

            logger.debug(f"Generated {len(results)} query variations")
            return results
        except Exception as e:
            logger.error(f"Error in MultiQueryStrategy: {e}")
            return [query]

    def _build_multi_query_prompt(self, query: str) -> Tuple[str, str]:
        """
        Build system and user prompts

        Returns:
            (system_prompt, user_prompt)
        """
        system_prompt = f"""
        Bạn là một trợ lý thông minh giúp tạo các câu hỏi tìm kiếm thay thế.
        Mục tiêu: Với câu hỏi của người dùng, hãy tạo {self.max_queries} cách diễn đạt khác nhau nhưng giữ nguyên ý nghĩa.
        Yêu cầu:
        - Mỗi câu hỏi trên một dòng riêng
        - KHÔNG đánh số, KHÔNG dùng dấu gạch đầu dòng
        - Giữ nguyên ngữ cảnh pháp lý đấu thầu Việt Nam
        - Sử dụng từ đồng nghĩa và cấu trúc câu khác nhau
        - Không thay đổi ý nghĩa gốc

        Ví dụ:
        Câu gốc: "Thời hạn nộp hồ sơ dự thầu?"
        Cách khác 1: Thời gian quy định để nộp HSDT?
        Cách khác 2: Deadline nộp hồ sơ tham gia đấu thầu?
        Cách khác 3: Hạn chót nộp hồ sơ dự thầu là khi nào?
        """

        user_prompt = f"""Câu hỏi gốc: {query} 
        Tạo {self.max_queries} cách hỏi khác:"""

        return system_prompt, user_prompt
