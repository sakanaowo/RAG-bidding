"""
Message Model - Schema v3
Represents individual chat messages within conversations
"""

from sqlalchemy import Column, String, Integer, Text, TIMESTAMP, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import TYPE_CHECKING
import uuid

from .base import Base

if TYPE_CHECKING:
    from .users import User
    from .conversations import Conversation
    from .citations import Citation
    from .feedback import Feedback


class Message(Base):
    """
    Message model for chat messages
    
    Represents individual messages in a conversation,
    including user queries and AI responses with sources.
    """

    __tablename__ = "messages"

    # Primary Key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        comment="Primary key"
    )

    # Foreign keys
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent conversation"
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Message author"
    )

    # Message content
    role = Column(
        String(20),
        nullable=False,
        comment="Role: user, assistant, system"
    )

    content = Column(
        Text,
        nullable=False,
        comment="Message content"
    )

    # Sources for AI responses (retrieved documents/chunks)
    sources = Column(
        JSONB,
        nullable=True,
        comment="Retrieved sources for AI response"
    )

    # Performance metrics
    processing_time_ms = Column(
        Integer,
        nullable=True,
        comment="Total processing time in milliseconds"
    )

    tokens_total = Column(
        Integer,
        nullable=True,
        comment="Total tokens (prompt + completion)"
    )

    # User feedback on this message
    feedback_rating = Column(
        Integer,
        nullable=True,
        comment="Quick feedback: 1-5 stars or thumbs up/down"
    )

    # Timestamp
    created_at = Column(
        TIMESTAMP(timezone=False),
        server_default=func.current_timestamp(),
        nullable=True,
        comment="Message timestamp"
    )

    # Relationships
    conversation = relationship(
        "Conversation",
        back_populates="messages"
    )
    
    user = relationship(
        "User",
        back_populates="messages"
    )
    
    citations = relationship(
        "Citation",
        back_populates="message",
        cascade="all, delete-orphan"
    )
    
    feedbacks = relationship(
        "Feedback",
        back_populates="message",
        cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_messages_conversation_created", "conversation_id", "created_at"),
        Index("idx_messages_user_created", "user_id", "created_at"),
        {"comment": "Chat messages within conversations (v3)"},
    )

    def __repr__(self):
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<Message(id={self.id}, role={self.role}, content={preview})>"

    def to_dict(self, include_sources: bool = True):
        """Convert to dictionary for JSON serialization"""
        data = {
            "id": str(self.id),
            "conversation_id": str(self.conversation_id),
            "user_id": str(self.user_id),
            "role": self.role,
            "content": self.content,
            "processing_time_ms": self.processing_time_ms,
            "tokens_total": self.tokens_total,
            "feedback_rating": self.feedback_rating,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_sources:
            data["sources"] = self.sources
            
        return data
