"""
Conversations Router - Schema v3
PostgreSQL-backed conversation management with RAG integration

Replaces the old Redis/in-memory chat session system.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.models.base import get_db
from src.models.users import User
from src.auth.dependencies import get_current_active_user, get_optional_user
from src.api.schemas.conversation_schemas import (
    CreateConversationRequest,
    SendMessageRequest,
    UpdateConversationRequest,
    FeedbackRequest,
    ConversationCreatedResponse,
    ConversationDetail,
    ConversationListResponse,
    ConversationSummary,
    MessageSentResponse,
    MessageListResponse,
    MessageResponse,
    DeleteResponse,
    SourceInfo,
)
from src.api.services.conversation_service import conversation_service

import logging
logger = logging.getLogger(__name__)


router = APIRouter(prefix="/conversations", tags=["Conversations"])


# =============================================================================
# CONVERSATION CRUD ENDPOINTS
# =============================================================================

@router.post("", response_model=ConversationCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    request: CreateConversationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new conversation
    
    - **title**: Optional title (auto-generated from first message if not provided)
    - **rag_mode**: RAG processing mode (fast, balanced, quality, adaptive)
    - **category_filter**: Optional document category filter
    """
    conversation = conversation_service.create_conversation(
        db=db,
        user_id=current_user.id,
        title=request.title,
        rag_mode=request.rag_mode.value,
        category_filter=request.category_filter
    )
    
    return ConversationCreatedResponse(
        id=conversation.id,
        title=conversation.title,
        rag_mode=conversation.rag_mode,
        created_at=conversation.created_at
    )


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    skip: int = Query(0, ge=0, description="Number of conversations to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max conversations to return"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List user's conversations with pagination
    
    Returns conversations sorted by last message time (most recent first)
    """
    conversations, total = conversation_service.list_conversations(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )
    
    return ConversationListResponse(
        conversations=[
            ConversationSummary(
                id=c.id,
                title=c.title,
                rag_mode=c.rag_mode or "balanced",
                message_count=c.message_count or 0,
                total_tokens=c.total_tokens,
                last_message_at=c.last_message_at,
                created_at=c.created_at
            )
            for c in conversations
        ],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: UUID,
    include_messages: bool = Query(True, description="Include messages in response"),
    message_limit: int = Query(50, ge=1, le=200, description="Max messages to include"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get conversation details with optional messages
    """
    conversation = conversation_service.get_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id
    )
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    messages = []
    if include_messages:
        msgs, _, _ = conversation_service.get_messages(
            db=db,
            conversation_id=conversation_id,
            user_id=current_user.id,
            limit=message_limit
        )
        messages = [
            MessageResponse(
                id=m.id,
                role=m.role,
                content=m.content,
                sources=_parse_sources(m.sources) if m.sources else None,
                processing_time_ms=m.processing_time_ms,
                tokens_total=m.tokens_total,
                feedback_rating=m.feedback_rating,
                created_at=m.created_at
            )
            for m in msgs
        ]
    
    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        rag_mode=conversation.rag_mode or "balanced",
        category_filter=conversation.category_filter,
        message_count=conversation.message_count or 0,
        total_tokens=conversation.total_tokens,
        total_cost_usd=float(conversation.total_cost_usd) if conversation.total_cost_usd else None,
        messages=messages,
        created_at=conversation.created_at,
        last_message_at=conversation.last_message_at
    )


@router.patch("/{conversation_id}", response_model=ConversationSummary)
async def update_conversation(
    conversation_id: UUID,
    request: UpdateConversationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update conversation settings (title, rag_mode, category_filter)
    """
    conversation = conversation_service.update_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
        title=request.title,
        rag_mode=request.rag_mode.value if request.rag_mode else None,
        category_filter=request.category_filter
    )
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    return ConversationSummary(
        id=conversation.id,
        title=conversation.title,
        rag_mode=conversation.rag_mode or "balanced",
        message_count=conversation.message_count or 0,
        total_tokens=conversation.total_tokens,
        last_message_at=conversation.last_message_at,
        created_at=conversation.created_at
    )


@router.delete("/{conversation_id}", response_model=DeleteResponse)
async def delete_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Soft delete a conversation
    
    The conversation is marked as deleted but not permanently removed.
    """
    success = conversation_service.delete_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    return DeleteResponse(
        success=True,
        message="Conversation deleted successfully"
    )


# =============================================================================
# SUMMARY ENDPOINT
# =============================================================================

@router.get("/{conversation_id}/summary")
async def get_conversation_summary(
    conversation_id: UUID,
    regenerate: bool = Query(False, description="Force regenerate summary"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get or generate conversation summary
    
    Summary helps preserve context in long conversations.
    Use `regenerate=true` to force a new summary.
    """
    from src.api.services.summary_service import SummaryService
    
    conversation = conversation_service.get_conversation(db, conversation_id, current_user.id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    summary = None
    if regenerate or not conversation.summary:
        summary = SummaryService.generate_summary(db, conversation_id, force=regenerate)
    else:
        summary = conversation.summary
    
    return {
        "conversation_id": str(conversation_id),
        "summary": summary,
        "message_count": conversation.message_count,
        "has_summary": bool(summary)
    }


# =============================================================================
# MESSAGE ENDPOINTS
# =============================================================================

@router.get("/{conversation_id}/messages", response_model=MessageListResponse)
async def get_messages(
    conversation_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get messages in a conversation with pagination
    """
    messages, total, has_more = conversation_service.get_messages(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )
    
    if not messages and total == 0:
        # Check if conversation exists
        conversation = conversation_service.get_conversation(db, conversation_id, current_user.id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
    
    return MessageListResponse(
        conversation_id=conversation_id,
        messages=[
            MessageResponse(
                id=m.id,
                role=m.role,
                content=m.content,
                sources=_parse_sources(m.sources) if m.sources else None,
                processing_time_ms=m.processing_time_ms,
                tokens_total=m.tokens_total,
                feedback_rating=m.feedback_rating,
                created_at=m.created_at
            )
            for m in messages
        ],
        total=total,
        has_more=has_more
    )


@router.post("/{conversation_id}/messages", response_model=MessageSentResponse)
async def send_message(
    conversation_id: UUID,
    request: SendMessageRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Send a message and get AI response via RAG pipeline
    
    - **content**: Your question or message
    - **rag_mode**: Override conversation's default RAG mode for this message
    - **include_sources**: Whether to include source citations (default: true)
    """
    user_msg, assistant_msg, sources, processing_time = conversation_service.send_message(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
        content=request.content,
        rag_mode=request.rag_mode.value if request.rag_mode else None,
        include_sources=request.include_sources
    )
    
    if not user_msg or not assistant_msg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    return MessageSentResponse(
        conversation_id=conversation_id,
        user_message=MessageResponse(
            id=user_msg.id,
            role=user_msg.role,
            content=user_msg.content,
            sources=None,
            processing_time_ms=None,
            tokens_total=None,
            feedback_rating=None,
            created_at=user_msg.created_at
        ),
        assistant_message=MessageResponse(
            id=assistant_msg.id,
            role=assistant_msg.role,
            content=assistant_msg.content,
            sources=sources,
            processing_time_ms=assistant_msg.processing_time_ms,
            tokens_total=assistant_msg.tokens_total,
            feedback_rating=None,
            created_at=assistant_msg.created_at
        ),
        sources=sources,
        processing_time_ms=processing_time
    )


# =============================================================================
# FEEDBACK ENDPOINT
# =============================================================================

@router.post("/{conversation_id}/messages/{message_id}/feedback", status_code=status.HTTP_201_CREATED)
async def add_feedback(
    conversation_id: UUID,
    message_id: UUID,
    request: FeedbackRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Add feedback to a message
    
    - **rating**: 1-5 rating
    - **feedback_type**: Type (helpful, incorrect, incomplete, etc.)
    - **comment**: Optional detailed feedback
    """
    success = conversation_service.add_message_feedback(
        db=db,
        message_id=message_id,
        user_id=current_user.id,
        rating=request.rating,
        feedback_type=request.feedback_type,
        comment=request.comment
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found or access denied"
        )
    
    return {"success": True, "message": "Feedback submitted successfully"}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _parse_sources(sources_data: dict) -> list[SourceInfo]:
    """Parse sources from message JSONB field"""
    if not sources_data:
        return []
    
    sources_list = sources_data.get("sources", [])
    result = []
    
    for s in sources_list:
        try:
            result.append(SourceInfo(
                document_id=s.get("document_id", ""),
                document_name=s.get("document_name", ""),
                chunk_id=s.get("chunk_id"),
                citation_text=s.get("citation_text"),
                relevance_score=s.get("relevance_score"),
                page_number=s.get("page_number"),
                section=s.get("section")
            ))
        except Exception:
            pass
    
    return result
