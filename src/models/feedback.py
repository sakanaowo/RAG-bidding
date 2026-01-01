"""
Feedback Model - Schema v3
Represents user feedback on AI responses
"""

from sqlalchemy import Column, String, Integer, Text, TIMESTAMP, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import TYPE_CHECKING
import uuid

from .base import Base

if TYPE_CHECKING:
    from .users import User
    from .messages import Message


class Feedback(Base):
    """
    Feedback model for collecting user feedback on AI responses
    
    Supports:
    - Rating (1-5 stars or thumbs up/down)
    - Detailed comments
    - Feedback types (accuracy, helpfulness, etc.)
    """

    __tablename__ = "feedback"

    # Primary Key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        comment="Primary key"
    )

    # Foreign keys
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User providing feedback"
    )

    message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Message being rated"
    )

    # Feedback details
    feedback_type = Column(
        String(50),
        nullable=True,
        comment="Type: accuracy, helpfulness, relevance, formatting"
    )

    rating = Column(
        Integer,
        nullable=True,
        comment="Rating: 1-5 stars or -1/1 for thumbs"
    )

    comment = Column(
        Text,
        nullable=True,
        comment="Detailed feedback comment"
    )

    # Timestamp
    created_at = Column(
        TIMESTAMP(timezone=False),
        server_default=func.current_timestamp(),
        nullable=True,
        comment="Feedback timestamp"
    )

    # Relationships
    user = relationship(
        "User",
        back_populates="feedbacks"
    )
    
    message = relationship(
        "Message",
        back_populates="feedbacks"
    )

    # Indexes
    __table_args__ = (
        Index("idx_feedback_user", "user_id"),
        Index("idx_feedback_message", "message_id"),
        Index("idx_feedback_type_rating", "feedback_type", "rating"),
        {"comment": "User feedback on AI responses (v3)"},
    )

    def __repr__(self):
        return f"<Feedback(id={self.id}, rating={self.rating}, type={self.feedback_type})>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "message_id": str(self.message_id),
            "feedback_type": self.feedback_type,
            "rating": self.rating,
            "comment": self.comment,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
