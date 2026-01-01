"""
Citation Model - Schema v3
Represents citations linking messages to document chunks
"""

from sqlalchemy import Column, Integer, Text, TIMESTAMP, ForeignKey, Index, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import TYPE_CHECKING
import uuid

from .base import Base

if TYPE_CHECKING:
    from .messages import Message
    from .documents import Document
    from .document_chunks import DocumentChunk


class Citation(Base):
    """
    Citation model for tracking document references in messages
    
    Links AI responses to the source documents/chunks used,
    enabling source verification and citation tracking.
    """

    __tablename__ = "citations"

    # Primary Key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        comment="Primary key"
    )

    # Foreign keys
    message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Message containing this citation"
    )

    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Referenced document"
    )

    chunk_id = Column(
        UUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Referenced chunk"
    )

    # Citation details
    citation_number = Column(
        Integer,
        nullable=False,
        comment="Citation number in message (1, 2, 3...)"
    )

    citation_text = Column(
        Text,
        nullable=True,
        comment="Quoted text from source"
    )

    relevance_score = Column(
        Numeric(5, 4),
        nullable=True,
        comment="Relevance score from retrieval (0.0000 - 1.0000)"
    )

    # Timestamp
    created_at = Column(
        TIMESTAMP(timezone=False),
        server_default=func.current_timestamp(),
        nullable=True,
        comment="Citation creation timestamp"
    )

    # Relationships
    message = relationship(
        "Message",
        back_populates="citations"
    )
    
    document = relationship(
        "Document"
    )
    
    chunk = relationship(
        "DocumentChunk",
        back_populates="citations"
    )

    # Indexes
    __table_args__ = (
        Index("idx_citations_message", "message_id"),
        Index("idx_citations_document", "document_id"),
        Index("idx_citations_chunk", "chunk_id"),
        {"comment": "Source citations in AI responses (v3)"},
    )

    def __repr__(self):
        return f"<Citation(id={self.id}, message_id={self.message_id}, citation_number={self.citation_number})>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "id": str(self.id),
            "message_id": str(self.message_id),
            "document_id": str(self.document_id),
            "chunk_id": str(self.chunk_id),
            "citation_number": self.citation_number,
            "citation_text": self.citation_text,
            "relevance_score": float(self.relevance_score) if self.relevance_score else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
