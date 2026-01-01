"""
Document Model - Schema v3
Represents the documents table - PRIMARY table for document management
"""

from sqlalchemy import Column, String, Integer, Text, TIMESTAMP, Index, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import Optional, TYPE_CHECKING
import uuid

from .base import Base

if TYPE_CHECKING:
    from .users import User
    from .document_chunks import DocumentChunk


class Document(Base):
    """
    Document model - Application-level document management (Schema v3)

    Represents legal documents, bidding forms, reports, etc.
    Changes from v2:
    - document_id: now nullable
    - Added: filepath, uploaded_by, file_hash, file_size_bytes, metadata
    - Removed: file_name (renamed to filename)
    """

    __tablename__ = "documents"

    # Primary Key
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4, 
        server_default=func.gen_random_uuid(),
        comment="Primary key"
    )

    # Unique identifier - NOW NULLABLE in v3
    document_id = Column(
        String(255),
        unique=True,
        nullable=True,  # Changed from v2: was NOT NULL
        index=True,
        comment="Unique document identifier (Vietnamese legal citation format)",
    )

    # Document metadata
    document_name = Column(
        String(500),  # Changed from Text to varchar(500) in v3
        nullable=True,
        comment="Document title/name"
    )

    filename = Column(
        String(255),  # Changed from Text in v2
        nullable=True,
        comment="Original filename"
    )

    filepath = Column(
        String(500),
        nullable=True,
        comment="Full path to file"
    )  # NEW in v3

    source_file = Column(
        Text, 
        nullable=True,  # Changed: was NOT NULL in v2
        index=True, 
        comment="Path to source file"
    )

    category = Column(
        String(100),
        nullable=False,
        default="Khác",
        index=True,
        comment="Category: Luat chinh, Nghi dinh, Thong tu, etc.",
    )

    document_type = Column(
        String(50),
        nullable=True,  # Changed: was NOT NULL in v2
        index=True,
        comment="Type: law, decree, circular, bidding_form, etc.",
    )

    # NEW in v3: Foreign key to users
    uploaded_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who uploaded the document"
    )

    # NEW in v3: File integrity
    file_hash = Column(
        String(64),
        nullable=True,
        comment="SHA-256 hash for deduplication"
    )

    file_size_bytes = Column(
        BigInteger,
        nullable=True,
        comment="File size in bytes"
    )

    total_chunks = Column(
        Integer, 
        default=0, 
        comment="Number of chunks/embeddings"
    )

    # NEW in v3: Flexible metadata storage
    # Note: Using 'extra_metadata' because 'metadata' is reserved in SQLAlchemy
    extra_metadata = Column(
        "metadata",  # Actual column name in DB is 'metadata'
        JSONB,
        nullable=True,
        comment="Additional metadata as JSON"
    )

    status = Column(
        String(50),
        default="active",
        index=True,
        comment="Status: active, processing, expired, deleted",
    )

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=False),
        server_default=func.current_timestamp(),
        nullable=True,
        comment="Creation timestamp",
    )

    updated_at = Column(
        TIMESTAMP(timezone=False),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=True,
        comment="Last update timestamp",
    )

    # Relationships
    uploader = relationship(
        "User",
        back_populates="documents",
        foreign_keys=[uploaded_by]
    )
    
    chunks = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan"
    )

    # Composite indexes for query optimization
    __table_args__ = (
        Index("idx_documents_status_type", "status", "document_type"),
        Index("idx_documents_category_status", "category", "status"),
        {"comment": "Application-level document management table (v3)"},
    )

    def __repr__(self):
        return f"<Document(id={self.document_id}, name={self.document_name}, type={self.document_type})>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "id": str(self.id),
            "document_id": self.document_id,
            "document_name": self.document_name,
            "filename": self.filename,
            "filepath": self.filepath,
            "category": self.category,
            "document_type": self.document_type,
            "source_file": self.source_file,
            "uploaded_by": str(self.uploaded_by) if self.uploaded_by else None,
            "file_hash": self.file_hash,
            "file_size_bytes": self.file_size_bytes,
            "total_chunks": self.total_chunks,
            "metadata": self.extra_metadata,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
