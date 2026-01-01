"""
Conversation Model - Schema v3
Represents chat conversations/sessions
"""

from sqlalchemy import Column, String, Integer, Text, TIMESTAMP, ForeignKey, Index, Numeric
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import TYPE_CHECKING
import uuid

from .base import Base

if TYPE_CHECKING:
    from .users import User
    from .messages import Message
    from .queries import Query


class Conversation(Base):
    """
    Conversation model for chat session management
    
    Represents a chat session between a user and the RAG system,
    containing multiple messages and tracking usage metrics.
    """

    __tablename__ = "conversations"

    # Primary Key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        comment="Primary key"
    )

    # Foreign key to users
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Owner of the conversation"
    )

    # Conversation metadata
    title = Column(
        String(500),
        nullable=True,
        comment="Conversation title (auto-generated or user-defined)"
    )

    summary = Column(
        Text,
        nullable=True,
        comment="AI-generated summary of conversation"
    )

    # RAG configuration for this conversation
    rag_mode = Column(
        String(50),
        default="balanced",
        nullable=True,
        comment="RAG mode: fast, balanced, quality, adaptive"
    )

    category_filter = Column(
        ARRAY(Text),
        nullable=True,
        comment="Categories to search within: ['Luat chinh', 'Nghi dinh']"
    )

    # Usage metrics
    message_count = Column(
        Integer,
        default=0,
        nullable=True,
        comment="Number of messages in conversation"
    )

    total_tokens = Column(
        Integer,
        default=0,
        nullable=True,
        comment="Total tokens used in this conversation"
    )

    total_cost_usd = Column(
        Numeric(10, 4),
        default=0,
        nullable=True,
        comment="Estimated cost in USD"
    )

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=False),
        server_default=func.current_timestamp(),
        nullable=True,
        comment="Conversation start timestamp"
    )

    last_message_at = Column(
        TIMESTAMP(timezone=False),
        nullable=True,
        comment="Last message timestamp"
    )

    deleted_at = Column(
        TIMESTAMP(timezone=False),
        nullable=True,
        comment="Soft delete timestamp"
    )

    # Relationships
    user = relationship(
        "User",
        back_populates="conversations"
    )
    
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at"
    )
    
    queries = relationship(
        "Query",
        back_populates="conversation"
    )

    # Indexes
    __table_args__ = (
        Index("idx_conversations_user_created", "user_id", "created_at"),
        Index("idx_conversations_user_last_message", "user_id", "last_message_at"),
        {"comment": "Chat conversation sessions (v3)"},
    )

    def __repr__(self):
        return f"<Conversation(id={self.id}, user_id={self.user_id}, messages={self.message_count})>"

    def to_dict(self, include_messages: bool = False):
        """Convert to dictionary for JSON serialization"""
        data = {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "title": self.title,
            "summary": self.summary,
            "rag_mode": self.rag_mode,
            "category_filter": self.category_filter,
            "message_count": self.message_count,
            "total_tokens": self.total_tokens,
            "total_cost_usd": float(self.total_cost_usd) if self.total_cost_usd else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
        }
        
        if include_messages and self.messages:
            data["messages"] = [msg.to_dict() for msg in self.messages]
            
        return data
