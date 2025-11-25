"""
Document Model
Represents the documents table - PRIMARY table for document management
"""

from sqlalchemy import Column, String, Integer, Text, TIMESTAMP, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional
import uuid

from .base import Base


class Document(Base):
    """
    Document model - Application-level document management

    Represents legal documents, bidding forms, reports, etc.
    """

    __tablename__ = "documents"

    # Primary Key
    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="Primary key"
    )

    # Unique identifier used in application
    document_id = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique document identifier",
    )

    # Document metadata
    document_name = Column(Text, nullable=False, comment="Document title/name")

    category = Column(
        String(100),
        nullable=False,
        index=True,
        comment="Category: legal, bidding, etc.",
    )

    document_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Type: law, decree, circular, bidding_form, etc.",
    )

    source_file = Column(
        Text, nullable=False, index=True, comment="Path to source file"
    )

    file_name = Column(Text, nullable=False, comment="Original filename")

    total_chunks = Column(Integer, default=0, comment="Number of chunks/embeddings")

    status = Column(
        String(50),
        default="active",
        index=True,
        comment="Status: active, processing, expired, deleted",
    )

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=False),
        server_default=func.now(),
        nullable=False,
        comment="Creation timestamp",
    )

    updated_at = Column(
        TIMESTAMP(timezone=False),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Last update timestamp",
    )

    # Composite indexes for query optimization
    __table_args__ = (
        Index("idx_documents_status_type", "status", "document_type"),
        Index("idx_documents_category_status", "category", "status"),
        {"comment": "Application-level document management table"},
    )

    def __repr__(self):
        return f"<Document(id={self.document_id}, name={self.document_name}, type={self.document_type})>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "id": str(self.id),
            "document_id": self.document_id,
            "document_name": self.document_name,
            "category": self.category,
            "document_type": self.document_type,
            "source_file": self.source_file,
            "file_name": self.file_name,
            "total_chunks": self.total_chunks,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
