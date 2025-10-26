"""
Mục đích: Tạo câu hỏi tổng quát hơn để lấy broader context

Use case:
    Query quá cụ thể (có địa điểm, số liệu, tên riêng)
    Cần understand big picture trước khi answer specific question
Ví dụ:
Specific: "Mức phạt vi phạm hợp đồng xây dựng trường học công lập ở Hà Nội?"
↓
Step-Back: "Quy định xử phạt vi phạm hợp đồng trong xây dựng công trình công?"

Benefits:
- Query 1 → specific docs về trường học Hà Nội
- Query 2 → general docs về xử phạt vi phạm hợp đồng
- Combine both → comprehensive answer
"""

from typing import List
from src.retrieval.query_processing.strategies.base_strategy import (
    BaseEnhancementStrategy,
)
import logging

logger = logging.getLogger(__name__)


class StepBackStrategy(BaseEnhancementStrategy):
    """Step-Back Prompting - tạo câu hỏi tổng quát hơn
    Reference: https://arxiv.org/abs/2310.06117
    """

    def __init__(self, llm_model, temperature=0.5):
        super().__init__(llm_model, temperature)

    def enhance(self, query) -> List[str]:
        try:
            if self._is_already_general(query):
                logger.info("Query is already general, no step-back needed")
                return [query]
            system_prompt, user_prompt = self._build_stepback_prompt(query)

            response = self._call_llm(system_prompt, user_prompt)
            step_back_query = response.strip()

            return [query, step_back_query]
        except Exception as e:
            logger.error(f"Error in StepBackStrategy _is_already_general: {e}")
            return [query]

    def _build_stepback_prompt(self, query: str) -> tuple[str, str]:
        system_prompt = """
        Bạn là trợ lý chuyên tạo câu hỏi tổng quát.

        NHIỆM VỤ: Với câu hỏi cụ thể, tạo câu hỏi TỔNG QUÁT HƠN về cùng chủ đề.

        CÁCH LÀM:
        1. Xác định yếu tố cụ thể: địa điểm, số liệu, tên riêng, chi tiết đặc thù
        2. Loại bỏ/tổng quát hóa các yếu tố đó
        3. Giữ lại concept/chủ đề chính

        VÍ DỤ:
        Cụ thể: "Mức phạt vi phạm hợp đồng xây dựng trường học ở Hà Nội?"
        Tổng quát: "Quy định xử phạt vi phạm hợp đồng xây dựng công trình công?"

        Cụ thể: "Điều kiện đấu thầu gói thầu 10 tỷ mua thiết bị y tế?"
        Tổng quát: "Điều kiện tham gia đấu thầu mua sắm trang thiết bị?"

        YÊU CẦU:
        - Chỉ trả về 1 câu hỏi tổng quát
        - Không giải thích
        - Giữ nguyên ngữ cảnh pháp lý đấu thầu"""
        user_prompt = f"""
        Câu hỏi cụ thể: "{query}"
        Câu hỏi tổng quát hơn:
        """

        return system_prompt, user_prompt

    def _is_already_general(self, query: str) -> bool:
        """
        Check if query is already general (no specifics)

        Indicators of specific query:
        - Contains numbers (10 tỷ, 30 ngày, 2024)
        - Contains locations (Hà Nội, TP.HCM)
        - Contains proper nouns (trường X, công ty Y)
        """
        import re

        # Check for numbers
        if re.search(r"\d+", query):
            return False

        # Check for common locations
        # TODO: Expand list of locations as needed
        locations = ["hà nội", "hcm", "tp.hcm", "đà nẵng", "hải phòng"]
        if any(loc in query.lower() for loc in locations):
            return False

        # Likely general
        return True
