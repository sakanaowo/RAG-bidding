"""
DocumentChunk Model - Schema v3
Represents document chunks for granular tracking and retrieval
"""

from sqlalchemy import Column, String, Integer, Text, Boolean, TIMESTAMP, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import TYPE_CHECKING
import uuid

from .base import Base

if TYPE_CHECKING:
    from .documents import Document
    from .embeddings import LangchainPGEmbedding
    from .citations import Citation


class DocumentChunk(Base):
    """
    DocumentChunk model for tracking individual chunks
    
    Provides granular control over document chunks:
    - Track chunk metadata (hierarchy, keywords, entities)
    - Link to embeddings
    - Track retrieval statistics
    """

    __tablename__ = "document_chunks"

    # Primary Key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        comment="Primary key"
    )

    # Unique chunk identifier
    chunk_id = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique chunk identifier"
    )

    # Foreign key to documents
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent document"
    )

    # Chunk content
    content = Column(
        Text,
        nullable=False,
        comment="Chunk text content"
    )

    chunk_index = Column(
        Integer,
        nullable=False,
        comment="Position in document (0-indexed)"
    )

    # Structural metadata
    section_title = Column(
        String(500),
        nullable=True,
        comment="Section/article title"
    )

    hierarchy_path = Column(
        ARRAY(Text),
        nullable=True,
        comment="Hierarchy: ['Chương I', 'Điều 1', 'Khoản 2']"
    )

    # Semantic metadata
    keywords = Column(
        ARRAY(Text),
        nullable=True,
        comment="Extracted keywords"
    )

    concepts = Column(
        ARRAY(Text),
        nullable=True,
        comment="Legal concepts in chunk"
    )

    entities = Column(
        JSONB,
        nullable=True,
        comment="Named entities: {organizations: [], dates: [], amounts: []}"
    )

    # Chunk characteristics
    char_count = Column(
        Integer,
        nullable=True,
        comment="Character count"
    )

    has_table = Column(
        Boolean,
        default=False,
        nullable=True,
        comment="Contains table data"
    )

    has_list = Column(
        Boolean,
        default=False,
        nullable=True,
        comment="Contains list/bullet points"
    )

    is_complete_unit = Column(
        Boolean,
        default=True,
        nullable=True,
        comment="Is a complete semantic unit (not split mid-sentence)"
    )

    # Analytics
    retrieval_count = Column(
        Integer,
        default=0,
        nullable=True,
        comment="Number of times retrieved"
    )

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=False),
        server_default=func.current_timestamp(),
        nullable=True,
        comment="Chunk creation timestamp"
    )

    updated_at = Column(
        TIMESTAMP(timezone=False),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=True,
        comment="Last update timestamp"
    )

    # Relationships
    document = relationship(
        "Document",
        back_populates="chunks"
    )
    
    embeddings = relationship(
        "LangchainPGEmbedding",
        back_populates="chunk",
        foreign_keys="LangchainPGEmbedding.chunk_id"
    )
    
    citations = relationship(
        "Citation",
        back_populates="chunk"
    )

    # Indexes
    __table_args__ = (
        Index("idx_chunks_document_index", "document_id", "chunk_index"),
        Index("idx_chunks_section", "section_title"),
        {"comment": "Document chunks for granular retrieval (v3)"},
    )

    def __repr__(self):
        return f"<DocumentChunk(id={self.chunk_id}, document_id={self.document_id}, index={self.chunk_index})>"

    def to_dict(self, include_content: bool = True):
        """Convert to dictionary for JSON serialization"""
        data = {
            "id": str(self.id),
            "chunk_id": self.chunk_id,
            "document_id": str(self.document_id),
            "chunk_index": self.chunk_index,
            "section_title": self.section_title,
            "hierarchy_path": self.hierarchy_path,
            "keywords": self.keywords,
            "concepts": self.concepts,
            "entities": self.entities,
            "char_count": self.char_count,
            "has_table": self.has_table,
            "has_list": self.has_list,
            "is_complete_unit": self.is_complete_unit,
            "retrieval_count": self.retrieval_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_content:
            data["content"] = self.content
            
        return data
