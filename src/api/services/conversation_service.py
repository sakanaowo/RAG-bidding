"""
Conversation Service - Schema v3
Business logic for conversations, messages, and RAG integration
"""

import time
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.conversations import Conversation
from src.models.messages import Message
from src.models.documents import Document
from src.models.document_chunks import DocumentChunk
from src.models.citations import Citation
from src.models.repositories import (
    ConversationRepository,
    MessageRepository,
    CitationRepository,
    DocumentChunkRepository,
    QueryRepository,
    UserUsageMetricRepository,
)
from src.generation.chains.qa_chain import answer as rag_answer
from src.generation.intent_detector import (
    IntentDetector,
    QueryIntent,
    get_intent_detector,
)
from src.api.schemas.conversation_schemas import SourceInfo
from src.utils.token_counter import count_message_tokens, estimate_cost_usd
from src.api.services.summary_service import SummaryService
from src.api.services.rate_limit_service import RateLimitService, RateLimitExceededError

logger = logging.getLogger(__name__)


class ConversationService:
    """
    Conversation service with PostgreSQL persistence and RAG integration.

    Replaces the old Redis/in-memory session management with proper
    database-backed conversations following schema v3.
    """

    # ==========================================================================
    # CONVERSATION CRUD
    # ==========================================================================

    @staticmethod
    def create_conversation(
        db: Session,
        user_id: UUID,
        title: Optional[str] = None,
        rag_mode: str = "balanced",
        category_filter: Optional[List[str]] = None,
    ) -> Conversation:
        """
        Create a new conversation

        Args:
            db: Database session
            user_id: Owner user ID
            title: Optional title (auto-generated from first message if not provided)
            rag_mode: RAG processing mode
            category_filter: Optional document category filter

        Returns:
            Created conversation
        """
        conversation = ConversationRepository.create(
            db=db,
            user_id=user_id,
            title=title,
            rag_mode=rag_mode,
            category_filter=category_filter,
        )

        logger.info(f"Created conversation {conversation.id} for user {user_id}")
        return conversation

    @staticmethod
    def get_conversation(
        db: Session, conversation_id: UUID, user_id: UUID
    ) -> Optional[Conversation]:
        """
        Get conversation by ID (with ownership check)

        Args:
            db: Database session
            conversation_id: Conversation UUID
            user_id: Current user ID for ownership verification

        Returns:
            Conversation if found and owned by user, None otherwise
        """
        conversation = ConversationRepository.get_by_id(db, conversation_id)

        if not conversation:
            return None

        # Verify ownership
        if conversation.user_id != user_id:
            logger.warning(
                f"User {user_id} tried to access conversation {conversation_id} owned by {conversation.user_id}"
            )
            return None

        # Check if deleted
        if conversation.deleted_at is not None:
            return None

        return conversation

    @staticmethod
    def list_conversations(
        db: Session, user_id: UUID, skip: int = 0, limit: int = 50
    ) -> Tuple[List[Conversation], int]:
        """
        List user's conversations with pagination

        Args:
            db: Database session
            user_id: User ID
            skip: Offset
            limit: Max results

        Returns:
            Tuple of (conversations, total_count)
        """
        conversations = ConversationRepository.get_user_conversations(
            db=db, user_id=user_id, skip=skip, limit=limit, include_deleted=False
        )

        # Get total count
        from sqlalchemy import func

        total = (
            db.query(func.count(Conversation.id))
            .filter(Conversation.user_id == user_id, Conversation.deleted_at.is_(None))
            .scalar()
        )

        return conversations, total

    @staticmethod
    def update_conversation(
        db: Session,
        conversation_id: UUID,
        user_id: UUID,
        title: Optional[str] = None,
        rag_mode: Optional[str] = None,
        category_filter: Optional[List[str]] = None,
    ) -> Optional[Conversation]:
        """
        Update conversation settings

        Args:
            db: Database session
            conversation_id: Conversation UUID
            user_id: Current user ID
            title: New title
            rag_mode: New RAG mode
            category_filter: New category filter

        Returns:
            Updated conversation or None if not found/unauthorized
        """
        conversation = ConversationService.get_conversation(
            db, conversation_id, user_id
        )
        if not conversation:
            return None

        if title is not None:
            conversation.title = title
        if rag_mode is not None:
            conversation.rag_mode = rag_mode
        if category_filter is not None:
            conversation.category_filter = category_filter

        db.commit()
        db.refresh(conversation)

        return conversation

    @staticmethod
    def delete_conversation(db: Session, conversation_id: UUID, user_id: UUID) -> bool:
        """
        Soft delete a conversation

        Args:
            db: Database session
            conversation_id: Conversation UUID
            user_id: Current user ID

        Returns:
            True if deleted, False if not found/unauthorized
        """
        conversation = ConversationService.get_conversation(
            db, conversation_id, user_id
        )
        if not conversation:
            return False

        conversation.deleted_at = datetime.utcnow()
        db.commit()

        logger.info(f"Soft deleted conversation {conversation_id}")
        return True

    # ==========================================================================
    # MESSAGE OPERATIONS WITH RAG
    # ==========================================================================

    @staticmethod
    def get_messages(
        db: Session,
        conversation_id: UUID,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Message], int, bool]:
        """
        Get messages in a conversation

        Args:
            db: Database session
            conversation_id: Conversation UUID
            user_id: Current user ID
            skip: Offset
            limit: Max results

        Returns:
            Tuple of (messages, total_count, has_more)
        """
        # Verify conversation ownership
        conversation = ConversationService.get_conversation(
            db, conversation_id, user_id
        )
        if not conversation:
            return [], 0, False

        messages = MessageRepository.get_conversation_messages(
            db=db, conversation_id=conversation_id, skip=skip, limit=limit
        )

        total = conversation.message_count or 0
        has_more = (skip + len(messages)) < total

        return messages, total, has_more

    @staticmethod
    def send_message(
        db: Session,
        conversation_id: UUID,
        user_id: UUID,
        content: str,
        rag_mode: Optional[str] = None,
        include_sources: bool = True,
    ) -> Tuple[Optional[Message], Optional[Message], List[SourceInfo], int]:
        """
        Send a user message and get AI response via RAG

        Args:
            db: Database session
            conversation_id: Conversation UUID
            user_id: Current user ID
            content: Message content
            rag_mode: Override RAG mode (uses conversation default if None)
            include_sources: Whether to include source citations

        Returns:
            Tuple of (user_message, assistant_message, sources, processing_time_ms)
        """
        start_time = time.time()

        # Check rate limit before processing
        rate_limit_result = RateLimitService.check_and_increment(user_id)
        if not rate_limit_result.allowed:
            raise RateLimitExceededError(
                f"Daily query limit reached ({rate_limit_result.limit} queries/day). "
                f"Remaining: {rate_limit_result.remaining}. Resets at: {rate_limit_result.reset_at}",
                rate_limit_result
            )

        # Verify conversation ownership
        conversation = ConversationService.get_conversation(
            db, conversation_id, user_id
        )
        if not conversation:
            return None, None, [], 0

        # Use conversation's rag_mode if not overridden
        effective_rag_mode = rag_mode or conversation.rag_mode or "balanced"

        # Check if this is the first message BEFORE creating user message
        # (message_count is 0 or None at this point for new conversations)
        is_first_message = (
            not conversation.title and (conversation.message_count or 0) == 0
        )

        # Create user message with rag_mode for tracking
        user_message = MessageRepository.add_message(
            db=db,
            conversation_id=conversation_id,
            user_id=user_id,
            role="user",
            content=content,
            rag_mode=effective_rag_mode,
        )

        # Auto-generate title from first message if not set
        if is_first_message:
            # Refresh conversation to get the latest state after message creation
            db.refresh(conversation)
            auto_title = content[:100] + "..." if len(content) > 100 else content
            conversation.title = auto_title
            db.commit()
            db.refresh(conversation)

        # 🆕 INTENT DETECTION: Check query intent BEFORE attaching context
        # This prevents gibberish/off-topic queries from polluting RAG with irrelevant context
        intent_detector = get_intent_detector()
        intent_result = intent_detector.detect(content)
        
        logger.info(
            f"🎯 Intent detected: {intent_result.intent.value} "
            f"(confidence: {intent_result.confidence:.2f}, reason: {intent_result.reason})"
        )

        # Handle GIBBERISH: Skip RAG entirely, return polite error
        if intent_result.intent == QueryIntent.GIBBERISH:
            processing_time = int((time.time() - start_time) * 1000)
            logger.info(f"🚫 Gibberish query rejected in {processing_time}ms: '{content[:30]}...'")
            
            assistant_message = MessageRepository.add_message(
                db=db,
                conversation_id=conversation_id,
                user_id=user_id,
                role="assistant",
                content=intent_result.suggested_response or "Xin lỗi, tôi không hiểu câu hỏi của bạn.",
                sources=None,
                processing_time_ms=processing_time,
                rag_mode="gibberish",
                tokens_total=0,
            )
            ConversationRepository.update_last_message(db, conversation_id)
            return user_message, assistant_message, [], processing_time

        # Handle OFF_TOPIC: Skip RAG, redirect to domain
        if intent_result.intent == QueryIntent.OFF_TOPIC:
            processing_time = int((time.time() - start_time) * 1000)
            logger.info(f"🔄 Off-topic query redirected in {processing_time}ms: '{content[:30]}...'")
            
            assistant_message = MessageRepository.add_message(
                db=db,
                conversation_id=conversation_id,
                user_id=user_id,
                role="assistant",
                content=intent_result.suggested_response or "Tôi chỉ hỗ trợ về pháp luật đấu thầu.",
                sources=None,
                processing_time_ms=processing_time,
                rag_mode="off_topic",
                tokens_total=0,
            )
            ConversationRepository.update_last_message(db, conversation_id)
            return user_message, assistant_message, [], processing_time

        # Handle CASUAL: Skip RAG, return direct response
        if intent_result.intent == QueryIntent.CASUAL:
            processing_time = int((time.time() - start_time) * 1000)
            logger.info(f"💬 Casual query early exit in {processing_time}ms: '{content[:30]}...'")

            assistant_message = MessageRepository.add_message(
                db=db,
                conversation_id=conversation_id,
                user_id=user_id,
                role="assistant",
                content=intent_result.suggested_response or "Xin chào! Tôi có thể giúp gì cho bạn?",
                sources=None,
                processing_time_ms=processing_time,
                rag_mode="casual",
                tokens_total=0,
            )
            ConversationRepository.update_last_message(db, conversation_id)
            return user_message, assistant_message, [], processing_time

        # 🆕 SMART CONTEXT: Only attach context for ON_TOPIC or CONTEXT_FOLLOW_UP
        enhanced_question = content
        conversation_context = None
        
        if intent_result.intent in [QueryIntent.ON_TOPIC, QueryIntent.CONTEXT_FOLLOW_UP]:
            # Build conversation context for RAG (summary + recent messages)
            conversation_context, _ = SummaryService.build_context_for_rag(
                db, conversation_id, content
            )
            
            # Only attach context if query is a context follow-up
            # For ON_TOPIC with context, we still pass context but let RAG prioritize docs
            if conversation_context and intent_result.intent == QueryIntent.CONTEXT_FOLLOW_UP:
                enhanced_question = f"""[CONTEXT HỘI THOẠI]
{conversation_context}

[CÂU HỎI HIỆN TẠI]
{content}"""
                logger.info("📎 Context attached for follow-up query")

        # Call RAG pipeline with enhanced question
        try:
            rag_result = rag_answer(
                question=enhanced_question,
                mode=effective_rag_mode,
                reranker_type="bge",
                original_query=content,  # 🆕 Pass original query for cache key
            )

            assistant_content = rag_result.get(
                "answer", "Xin lỗi, tôi không thể trả lời câu hỏi này."
            )
            # Use source_documents_raw for proper metadata extraction
            raw_sources = rag_result.get("source_documents_raw", [])
            rag_time = rag_result.get("processing_time_ms", 0)

        except Exception as e:
            logger.error(f"RAG pipeline error: {e}")
            assistant_content = "Xin lỗi, đã xảy ra lỗi khi xử lý câu hỏi của bạn."
            raw_sources = []
            rag_time = 0

        processing_time = int((time.time() - start_time) * 1000)

        # Build sources info from raw source documents
        sources_info = ConversationService._build_sources_info_from_raw(raw_sources)

        # Count tokens for the interaction
        context_contents = (
            [doc.get("content", "") for doc in raw_sources] if raw_sources else None
        )
        token_counts = count_message_tokens(
            user_message=content,
            assistant_response=assistant_content,
            context_docs=context_contents,
        )
        total_tokens = token_counts["total_tokens"]

        # Estimate cost
        estimated_cost = estimate_cost_usd(
            input_tokens=token_counts["input_tokens"],
            output_tokens=token_counts["output_tokens"],
        )

        # Create assistant message with rag_mode and tokens
        assistant_message = MessageRepository.add_message(
            db=db,
            conversation_id=conversation_id,
            user_id=user_id,
            role="assistant",
            content=assistant_content,
            sources=(
                {"sources": [s.model_dump() for s in sources_info]}
                if include_sources
                else None
            ),
            processing_time_ms=processing_time,
            rag_mode=effective_rag_mode,
            tokens_total=total_tokens,
        )

        # Update conversation usage stats
        ConversationRepository.update_last_message(db, conversation_id)

        # Extract actual categories from retrieved documents for analytics
        # This provides better insights than just using the user's category filter
        actual_categories = list(set(
            doc.get("category") for doc in raw_sources 
            if doc.get("category")
        )) or conversation.category_filter  # Fallback to filter if no categories in docs

        # Log query for analytics with token info
        try:
            QueryRepository.log_query(
                db=db,
                query_text=content,
                user_id=user_id,
                conversation_id=conversation_id,
                message_id=assistant_message.id,
                rag_mode=effective_rag_mode,
                categories_searched=actual_categories,
                retrieval_count=len(raw_sources),
                total_latency_ms=processing_time,
                tokens_total=total_tokens,
                estimated_cost_usd=estimated_cost,
            )
        except Exception as e:
            logger.warning(f"Failed to log query: {e}")

        # Extract and save citations
        try:
            ConversationService._save_citations(
                db=db, message_id=assistant_message.id, raw_sources=raw_sources
            )
        except Exception as e:
            logger.warning(f"Failed to save citations: {e}")

        # Update user usage metrics
        try:
            UserUsageMetricRepository.increment_usage(
                db=db,
                user_id=user_id,
                queries=1,
                messages=2,  # user message + assistant message
                tokens=total_tokens,
                cost_usd=estimated_cost,
            )
        except Exception as e:
            logger.warning(f"Failed to update usage metrics: {e}")

        # Generate/update conversation summary if needed (async-like, non-blocking)
        try:
            # Refresh conversation to get updated message_count
            db.refresh(conversation)
            if SummaryService.should_update_summary(conversation):
                SummaryService.generate_summary(db, conversation_id)
        except Exception as e:
            logger.warning(f"Failed to update summary: {e}")

        logger.info(
            f"Processed message in conversation {conversation_id}: {processing_time}ms"
        )

        return user_message, assistant_message, sources_info, processing_time

    @staticmethod
    def _save_citations(
        db: Session, message_id: UUID, raw_sources: List[Dict]
    ) -> List[Citation]:
        """
        Save citations for a message based on raw source documents.

        Maps string document_id/chunk_id to UUID references.

        Args:
            db: Database session
            message_id: UUID of the assistant message
            raw_sources: List of source document dicts from qa_chain

        Returns:
            List of created Citation objects
        """
        from src.models.repositories import DocumentRepository, DocumentChunkRepository

        if not raw_sources:
            return []

        citations_data = []
        for i, src in enumerate(raw_sources):
            doc_id_str = src.get("document_id")
            chunk_id_str = src.get("chunk_id")

            if not doc_id_str or not chunk_id_str:
                logger.debug(
                    f"Skipping citation {i+1}: missing document_id or chunk_id"
                )
                continue

            # Lookup UUIDs from string IDs
            document = DocumentRepository.get_by_id(db, doc_id_str)
            chunk = DocumentChunkRepository.get_by_chunk_id(db, chunk_id_str)

            if not document or not chunk:
                logger.debug(
                    f"Skipping citation {i+1}: document/chunk not found "
                    f"(doc={doc_id_str}, chunk={chunk_id_str})"
                )
                continue

            citations_data.append(
                {
                    "document_id": document.id,
                    "chunk_id": chunk.id,
                    "citation_number": i + 1,
                    "citation_text": src.get("content", "")[
                        :500
                    ],  # Limit citation text
                    "relevance_score": src.get("score"),
                }
            )

        if citations_data:
            return CitationRepository.create_batch(db, message_id, citations_data)
        return []

    @staticmethod
    def _build_sources_info_from_raw(raw_sources: List[Dict]) -> List[SourceInfo]:
        """
        Build source info from raw source documents with full metadata

        Args:
            raw_sources: List of dicts with document metadata from qa_chain

        Returns:
            List of SourceInfo objects with proper document_id, chunk_id, etc.
        """
        sources_info = []

        for src in raw_sources:
            try:
                # Build section string from hierarchy
                hierarchy = src.get("hierarchy", [])
                section_parts = []

                if src.get("dieu"):
                    section_parts.append(f"Điều {src['dieu']}")
                if src.get("khoan"):
                    section_parts.append(f"Khoản {src['khoan']}")
                if src.get("diem"):
                    section_parts.append(f"Điểm {src['diem']}")

                section = (
                    " → ".join(section_parts)
                    if section_parts
                    else (
                        " → ".join(hierarchy)
                        if hierarchy
                        else src.get("section_title", "")
                    )
                )

                source_info = SourceInfo(
                    document_id=src.get("document_id", ""),
                    document_name=src.get("document_name", "Tài liệu"),
                    chunk_id=src.get("chunk_id"),
                    citation_text=src.get("content", "")[:300],  # First 300 chars
                    relevance_score=None,  # TODO: Add relevance score from reranker
                    page_number=None,  # Not available in current metadata
                    section=section,
                )
                sources_info.append(source_info)
            except Exception as e:
                logger.warning(f"Failed to parse source: {e}")

        return sources_info

    @staticmethod
    def _build_sources_info(db: Session, rag_sources: List[str]) -> List[SourceInfo]:
        """
        DEPRECATED: Build source info from RAG source strings
        Use _build_sources_info_from_raw instead.

        Args:
            db: Database session
            rag_sources: List of source strings from RAG pipeline

        Returns:
            List of SourceInfo objects
        """
        sources_info = []

        for source in rag_sources:
            # Parse source string - format varies by RAG implementation
            # Try to extract document info
            try:
                # Simple parsing - adapt based on actual source format
                source_info = SourceInfo(
                    document_id=str(hash(source)),  # Placeholder
                    document_name=source,
                    citation_text=source[:200] if len(source) > 200 else source,
                )
                sources_info.append(source_info)
            except Exception as e:
                logger.warning(f"Failed to parse source: {e}")

        return sources_info

    @staticmethod
    def add_message_feedback(
        db: Session,
        message_id: UUID,
        user_id: UUID,
        rating: int,
        feedback_type: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> bool:
        """
        Add feedback to a message

        Args:
            db: Database session
            message_id: Message UUID
            user_id: User ID
            rating: Rating (1-5)
            feedback_type: Type of feedback
            comment: Optional comment

        Returns:
            True if feedback added successfully
        """
        from src.models.repositories import FeedbackRepository

        # Verify message exists and user has access
        message = MessageRepository.get_by_id(db, message_id)
        if not message:
            return False

        # Verify user owns the conversation
        conversation = ConversationRepository.get_by_id(db, message.conversation_id)
        if not conversation or conversation.user_id != user_id:
            return False

        # Update quick rating on message
        MessageRepository.update_feedback_rating(db, message_id, rating)

        # Create detailed feedback record
        FeedbackRepository.create(
            db=db,
            user_id=user_id,
            message_id=message_id,
            rating=rating,
            feedback_type=feedback_type,
            comment=comment,
        )

        logger.info(f"Added feedback (rating={rating}) to message {message_id}")
        return True


# Global service instance
conversation_service = ConversationService()
