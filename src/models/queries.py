"""
Query Model - Schema v3
Represents query analytics for tracking and optimization
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
    from .conversations import Conversation
    from .messages import Message


class Query(Base):
    """
    Query model for analytics and optimization
    
    Tracks:
    - Query text and hash (for caching)
    - RAG mode and categories searched
    - Performance metrics (latency, tokens, cost)
    """

    __tablename__ = "queries"

    # Primary Key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        comment="Primary key"
    )

    # Foreign keys (all optional for anonymous queries)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who made the query"
    )

    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Parent conversation"
    )

    message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Associated message"
    )

    # Query details
    query_text = Column(
        Text,
        nullable=False,
        comment="Original query text"
    )

    query_hash = Column(
        String(64),
        nullable=True,
        index=True,
        comment="SHA-256 hash for cache lookup"
    )

    # RAG configuration
    rag_mode = Column(
        String(50),
        nullable=True,
        comment="RAG mode used: fast, balanced, quality, adaptive"
    )

    categories_searched = Column(
        ARRAY(Text),
        nullable=True,
        comment="Categories searched"
    )

    # Performance metrics
    retrieval_count = Column(
        Integer,
        nullable=True,
        comment="Number of documents retrieved"
    )

    total_latency_ms = Column(
        Integer,
        nullable=True,
        comment="Total query latency in milliseconds"
    )

    tokens_total = Column(
        Integer,
        nullable=True,
        comment="Total tokens used"
    )

    estimated_cost_usd = Column(
        Numeric(10, 6),
        nullable=True,
        comment="Estimated cost in USD"
    )

    # Timestamp
    created_at = Column(
        TIMESTAMP(timezone=False),
        server_default=func.current_timestamp(),
        nullable=True,
        comment="Query timestamp"
    )

    # Relationships
    user = relationship(
        "User",
        back_populates="queries"
    )
    
    conversation = relationship(
        "Conversation",
        back_populates="queries"
    )

    # Indexes
    __table_args__ = (
        Index("idx_queries_user_created", "user_id", "created_at"),
        Index("idx_queries_hash", "query_hash"),
        Index("idx_queries_mode", "rag_mode"),
        {"comment": "Query analytics and caching (v3)"},
    )

    def __repr__(self):
        preview = self.query_text[:30] + "..." if len(self.query_text) > 30 else self.query_text
        return f"<Query(id={self.id}, query={preview})>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "conversation_id": str(self.conversation_id) if self.conversation_id else None,
            "message_id": str(self.message_id) if self.message_id else None,
            "query_text": self.query_text,
            "query_hash": self.query_hash,
            "rag_mode": self.rag_mode,
            "categories_searched": self.categories_searched,
            "retrieval_count": self.retrieval_count,
            "total_latency_ms": self.total_latency_ms,
            "tokens_total": self.tokens_total,
            "estimated_cost_usd": float(self.estimated_cost_usd) if self.estimated_cost_usd else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
