"""
Summary Service - Conversation Context Management
Generates and manages conversation summaries to preserve context for long conversations.
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy.orm import Session

from src.config.models import settings
from src.models.conversations import Conversation
from src.models.messages import Message
from src.models.repositories import ConversationRepository, MessageRepository

logger = logging.getLogger(__name__)

# Configuration
MAX_CONTEXT_MESSAGES = 10  # Max recent messages to include
SUMMARY_THRESHOLD = 8  # Generate summary after N messages (higher = less LLM calls)
TOKEN_LIMIT_ESTIMATE = 4000  # Approximate token budget for context

# Strategy options:
# - SUMMARY_THRESHOLD = 2: Aggressive summarization (high cost, always fresh)
# - SUMMARY_THRESHOLD = 6: Balanced (recommended)
# - SUMMARY_THRESHOLD = 10+: Lazy summarization (low cost, may lose context)

# LLM for summarization
summary_model = ChatOpenAI(model=settings.llm_model, temperature=0)


SUMMARY_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """Bạn là trợ lý tóm tắt hội thoại. Hãy tóm tắt ngắn gọn nội dung cuộc hội thoại dưới đây.

        Yêu cầu:
        - Tóm tắt các chủ đề chính đã thảo luận
        - Liệt kê các thông tin quan trọng đã được cung cấp
        - Nêu các câu hỏi/yêu cầu chính của người dùng
        - Tối đa 200 từ

        Output format:
        **Chủ đề chính:** [liệt kê ngắn gọn]
        **Thông tin đã cung cấp:** [bullet points]
        **Yêu cầu của người dùng:** [bullet points]""",
        ),
        ("user", "Hội thoại cần tóm tắt:\n\n{conversation}"),
    ]
)


class SummaryService:
    """
    Service for managing conversation context and summaries.

    Strategies to preserve context:
    1. Sliding window: Keep N most recent messages
    2. Summary: Generate summary of older messages
    3. Hybrid: Summary + recent messages
    """

    @staticmethod
    def build_context_for_rag(
        db: Session, conversation_id: UUID, current_question: str
    ) -> Tuple[str, List[Dict]]:
        """
        Build context string for RAG pipeline.

        Uses hybrid approach:
        - Include conversation summary (if exists)
        - Include last N messages
        - Format for LLM consumption

        Args:
            db: Database session
            conversation_id: Conversation UUID
            current_question: Current user question

        Returns:
            Tuple of (context_string, recent_messages_list)
        """
        conversation = ConversationRepository.get_by_id(db, conversation_id)
        if not conversation:
            return "", []

        # Get recent messages (default order is chronological)
        messages = MessageRepository.get_conversation_messages(
            db,
            conversation_id,
            skip=0,
            limit=MAX_CONTEXT_MESSAGES * 2,  # Get more, then slice
        )
        # Take last N messages
        messages = (
            messages[-MAX_CONTEXT_MESSAGES:]
            if len(messages) > MAX_CONTEXT_MESSAGES
            else messages
        )

        context_parts = []

        # Add summary if exists and we have many messages
        conv_summary = conversation.summary
        if conv_summary and len(messages) >= SUMMARY_THRESHOLD // 2:
            context_parts.append(f"[Tóm tắt hội thoại trước đó]\n{conv_summary}")

        # Add recent messages
        if messages:
            recent_context = []
            for msg in messages:
                role = "Người dùng" if msg.role == "user" else "Trợ lý"
                # Truncate long messages
                content = (
                    msg.content[:500] + "..." if len(msg.content) > 500 else msg.content
                )
                recent_context.append(f"{role}: {content}")

            context_parts.append("[Tin nhắn gần đây]\n" + "\n".join(recent_context))

        context_string = "\n\n".join(context_parts) if context_parts else ""

        # Return messages as dicts for flexibility
        messages_data = [
            {
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ]

        return context_string, messages_data

    @staticmethod
    def should_update_summary(conversation: Conversation) -> bool:
        """
        Check if conversation summary should be updated.

        Criteria:
        - More than SUMMARY_THRESHOLD messages
        - No existing summary OR many new messages since last summary
        """
        message_count = conversation.message_count or 0
        has_summary = bool(conversation.summary)

        # Always generate summary after threshold
        if message_count >= SUMMARY_THRESHOLD and not has_summary:
            return True

        # Update summary every N messages after initial
        if message_count >= SUMMARY_THRESHOLD * 2 and has_summary:
            # Simple heuristic: update every SUMMARY_THRESHOLD messages
            return message_count % SUMMARY_THRESHOLD == 0

        return False

    @staticmethod
    def generate_summary(
        db: Session, conversation_id: UUID, force: bool = False
    ) -> Optional[str]:
        """
        Generate or update conversation summary.

        Args:
            db: Database session
            conversation_id: Conversation UUID
            force: Force regeneration even if not needed

        Returns:
            Generated summary string or None
        """
        conversation = ConversationRepository.get_by_id(db, conversation_id)
        if not conversation:
            return None

        if not force and not SummaryService.should_update_summary(conversation):
            return str(conversation.summary) if conversation.summary else None

        # Get all messages for summarization
        messages = MessageRepository.get_conversation_messages(
            db, conversation_id, skip=0, limit=50  # Summarize up to 50 messages
        )

        if len(messages) < SUMMARY_THRESHOLD:
            return None

        # Format messages for summarization
        conversation_text = []
        for msg in messages:
            role = "Người dùng" if msg.role == "user" else "Trợ lý"
            # Truncate very long messages
            content = (
                msg.content[:800] + "..." if len(msg.content) > 800 else msg.content
            )
            conversation_text.append(f"{role}: {content}")

        try:
            # Generate summary using LLM
            chain = SUMMARY_PROMPT | summary_model
            result = chain.invoke({"conversation": "\n\n".join(conversation_text)})

            summary = str(result.content).strip()

            # Save summary to conversation
            conversation.summary = summary  # type: ignore
            db.commit()

            logger.info(
                f"Generated summary for conversation {conversation_id}: {len(summary)} chars"
            )
            return summary

        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return None

    @staticmethod
    def get_rag_system_context(db: Session, conversation_id: UUID) -> str:
        """
        Get formatted system context for RAG including conversation history.

        This can be prepended to the RAG system prompt to provide
        conversation context.
        """
        context, _ = SummaryService.build_context_for_rag(db, conversation_id, "")

        if not context:
            return ""

        return f"""
[CONTEXT TỪ HỘI THOẠI TRƯỚC]
{context}

[LƯU Ý]
- Sử dụng thông tin trên để hiểu context của câu hỏi
- Tham chiếu lại nếu người dùng hỏi "như đã nói", "ở trên", etc.
- Ưu tiên trả lời câu hỏi mới dựa trên tài liệu RAG
"""


# Singleton instance
summary_service = SummaryService()
