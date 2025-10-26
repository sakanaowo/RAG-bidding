"""
Tạo một document giả định trả lời câu hỏi, dùng document này để search
"""

from src.retrieval.query_processing.strategies.base_strategy import (
    BaseEnhancementStrategy,
)

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class HyDEStrategy(BaseEnhancementStrategy):
    """
    Hypothetical Document Embeddings

    Tạo một đoạn văn giả định trả lời câu hỏi,
    sau đó dùng đoạn văn này để search thay vì query gốc

    Reference: https://arxiv.org/abs/2212.10496

    Use case:
    - Cải thiện khả năng tìm kiếm trong các hệ thống retrieval
    - Hữu ích khi câu hỏi có thể không khớp trực tiếp với nội dung tài liệu
    - Tăng khả năng hiểu ngữ cảnh và ý định của người dùng
    """

    def __init__(self, llm_model, temperature=0.3):
        super().__init__(llm_model, temperature)
        logger.info("Initialized HyDEStrategy")

    def enhance(self, query: str) -> str:
        """
        Tạo một document giả định trả lời câu hỏi

        Args:
            query: Câu hỏi gốc

        Returns:
            str: Document giả định trả lời câu hỏi
        """
        try:
            system_prompt, user_prompt = self._build_hyde_prompt(query)
            hypothetical_doc = self._call_llm(system_prompt, user_prompt)
            result = [query, hypothetical_doc]

            logger.debug(
                f"HyDEStrategy generated hypothetical document: {hypothetical_doc}"
            )
            return result

        except Exception as e:
            logger.error(f"Error in HyDEStrategy enhance: {e}")
            return [query]

    def _build_hyde_prompt(self, query: str) -> str:
        """
        Build system and user prompts

        Returns:
            (system_prompt, user_prompt)
        """
        system_prompt = """
        Bạn là chuyên gia pháp lý về đấu thầu công Việt Nam.

        NHIỆM VỤ: Viết một đoạn văn chi tiết, chuyên nghiệp trả lời câu hỏi của người dùng.

        YÊU CẦU:
        - Viết như một đoạn trong văn bản pháp luật/tài liệu hướng dẫn
        - Bao gồm các điều khoản, số liệu, quy định cụ thể nếu có
        - Độ dài: 100-200 từ
        - Tập trung vào thông tin FACTUAL, chính xác
        - Sử dụng thuật ngữ pháp lý chuẩn xác
        - Trích dẫn văn bản pháp luật nếu phù hợp (Luật, Nghị định, Thông tư)

        VÍ DỤ FORMAT:
        "Theo [Văn bản pháp luật], [quy định chính]...
        Cụ thể: [chi tiết 1], [chi tiết 2]...
        [Lưu ý/Điều kiện đặc biệt nếu có]...
        """
        user_prompt = f"""
        Câu hỏi gốc: {query}
        Tạo một đoạn văn giả định trả lời câu hỏi này (100-200 từ):
        """
        return system_prompt, user_prompt
