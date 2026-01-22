"""
Conversation Pydantic Schemas - Schema v3
Request/Response models for conversation and message endpoints
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field


# =============================================================================
# ENUMS
# =============================================================================

class MessageRole(str, Enum):
    """Message roles"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class RAGMode(str, Enum):
    """RAG processing modes"""
    FAST = "fast"
    BALANCED = "balanced"
    QUALITY = "quality"
    # NOTE: ADAPTIVE removed - use BALANCED as default


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================

class CreateConversationRequest(BaseModel):
    """Request body for creating a conversation"""
    title: Optional[str] = Field(None, max_length=255, description="Conversation title (auto-generated if not provided)")
    rag_mode: RAGMode = Field(RAGMode.BALANCED, description="RAG processing mode")
    category_filter: Optional[List[str]] = Field(None, description="Filter documents by categories")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "title": "Hỏi về quy trình đấu thầu",
                    "rag_mode": "balanced",
                    "category_filter": None
                },
                {
                    "title": "Câu hỏi về Luật Đấu thầu 2023",
                    "rag_mode": "quality",
                    "category_filter": ["Luat chinh", "Nghi dinh"]
                }
            ]
        }
    }


class SendMessageRequest(BaseModel):
    """Request body for sending a message"""
    content: str = Field(..., min_length=1, max_length=10000, description="Message content")
    rag_mode: Optional[RAGMode] = Field(None, description="Override conversation RAG mode for this message")
    include_sources: bool = Field(True, description="Include source citations in response")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "content": "Điều kiện để nhà thầu được tham gia đấu thầu là gì?",
                    "rag_mode": None,
                    "include_sources": True
                },
                {
                    "content": "Quy trình lựa chọn nhà thầu qua mạng như thế nào?",
                    "rag_mode": "quality",
                    "include_sources": True
                }
            ]
        }
    }


class UpdateConversationRequest(BaseModel):
    """Request body for updating a conversation"""
    title: Optional[str] = Field(None, max_length=255)
    rag_mode: Optional[RAGMode] = None
    category_filter: Optional[List[str]] = None


class FeedbackRequest(BaseModel):
    """Request body for message feedback"""
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5")
    feedback_type: Optional[str] = Field(None, max_length=50, description="Type: helpful, incorrect, incomplete, etc.")
    comment: Optional[str] = Field(None, max_length=1000, description="Optional feedback comment")


# =============================================================================
# RESPONSE SCHEMAS - NESTED COMPONENTS
# =============================================================================

class SourceInfo(BaseModel):
    """Source/citation information"""
    document_id: str
    document_name: str
    chunk_id: Optional[str] = None
    citation_text: Optional[str] = None
    relevance_score: Optional[float] = None
    page_number: Optional[int] = None
    section: Optional[str] = None


class MessageResponse(BaseModel):
    """Single message in conversation"""
    id: UUID
    role: str
    content: str
    rag_mode: Optional[str] = None
    sources: Optional[List[SourceInfo]] = None
    processing_time_ms: Optional[int] = None
    tokens_total: Optional[int] = None
    feedback_rating: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ConversationSummary(BaseModel):
    """Conversation summary for list view"""
    id: UUID
    title: Optional[str] = None
    rag_mode: str = "balanced"
    message_count: int = 0
    total_tokens: Optional[int] = None
    last_message_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ConversationDetail(BaseModel):
    """Full conversation with messages"""
    id: UUID
    title: Optional[str] = None
    rag_mode: str = "balanced"
    category_filter: Optional[List[str]] = None
    message_count: int = 0
    total_tokens: Optional[int] = None
    total_cost_usd: Optional[float] = None
    messages: List[MessageResponse] = []
    created_at: datetime
    last_message_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# =============================================================================
# RESPONSE SCHEMAS - API RESPONSES
# =============================================================================

class ConversationCreatedResponse(BaseModel):
    """Response for conversation creation"""
    id: UUID
    title: Optional[str] = None
    rag_mode: str
    created_at: datetime


class MessageSentResponse(BaseModel):
    """Response for sending a message (includes AI response)"""
    conversation_id: UUID
    user_message: MessageResponse
    assistant_message: MessageResponse
    sources: List[SourceInfo]
    processing_time_ms: int


class ConversationListResponse(BaseModel):
    """Response for listing conversations"""
    conversations: List[ConversationSummary]
    total: int
    skip: int
    limit: int


class MessageListResponse(BaseModel):
    """Response for listing messages in a conversation"""
    conversation_id: UUID
    messages: List[MessageResponse]
    total: int
    has_more: bool


class DeleteResponse(BaseModel):
    """Response for delete operations"""
    success: bool
    message: str
