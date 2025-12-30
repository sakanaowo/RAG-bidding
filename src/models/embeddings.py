"""
Embedding Models - Schema v3
Represents LangChain PGVector tables for vector storage

Changes from v2:
- embedding: vector(3072) -> vector(1536) for text-embedding-3-small
- Added: chunk_id FK to document_chunks
- Added: created_at timestamp
"""

from sqlalchemy import Column, String, Text, ForeignKey, Index, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from typing import TYPE_CHECKING

from .base import Base

if TYPE_CHECKING:
    from .document_chunks import DocumentChunk


class LangchainPGCollection(Base):
    """
    LangChain collection table - INTERNAL USE ONLY
    Managed by LangChain library, not directly by application
    """

    __tablename__ = "langchain_pg_collection"

    uuid = Column(UUID(as_uuid=True), primary_key=True, comment="Collection UUID")

    name = Column(
        String, 
        nullable=False,  # Required in v3
        comment="Collection name (e.g., 'docs')"
    )

    cmetadata = Column(
        JSONB,  # Changed from JSON to JSONB for better performance
        comment="Collection metadata"
    )

    __table_args__ = (
        Index("langchain_pg_collection_name_key", "name", unique=True),
        {
            "comment": "LangChain internal collection management - DO NOT modify directly"
        },
    )

    def __repr__(self):
        return f"<LangchainPGCollection(name={self.name})>"


class LangchainPGEmbedding(Base):
    """
    Vector embedding storage table - Schema v3
    Stores document chunks with their embeddings and metadata
    
    Changes from v2:
    - embedding dimension: 3072 -> 1536 (text-embedding-3-small)
    - Added chunk_id FK to link with document_chunks table
    - Added created_at timestamp
    """

    __tablename__ = "langchain_pg_embedding"

    # Primary key (chunk ID as string)
    id = Column(
        String, 
        primary_key=True, 
        server_default=func.gen_random_uuid().cast(String),
        comment="Chunk ID (UUID format as string)"
    )

    # Foreign key to collection
    collection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("langchain_pg_collection.uuid", ondelete="CASCADE"),
        nullable=True,
        comment="Reference to collection",
    )

    # Vector embedding - CHANGED: 3072 -> 1536 for text-embedding-3-small
    embedding = Column(
        Vector(1536),  # Changed from 3072
        comment="OpenAI text-embedding-3-small vector (1536-dim)"
    )

    # Chunk content
    document = Column(
        Text,  # Changed from VARCHAR in v2
        comment="Chunk text content"
    )

    # Rich metadata in JSONB
    cmetadata = Column(
        JSONB, 
        comment="Chunk metadata: document_id, chunk_index, hierarchy, etc."
    )

    # NEW in v3: Link to document_chunks table
    chunk_id = Column(
        UUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
        comment="Reference to document_chunks table"
    )

    # NEW in v3: Creation timestamp
    created_at = Column(
        TIMESTAMP(timezone=False),
        server_default=func.current_timestamp(),
        nullable=True,
        comment="Embedding creation timestamp"
    )

    # Relationships
    chunk = relationship(
        "DocumentChunk",
        back_populates="embeddings",
        foreign_keys=[chunk_id]
    )

    # Indexes for performance
    __table_args__ = (
        # GIN index for JSONB metadata queries
        Index(
            "ix_cmetadata_gin",
            "cmetadata",
            postgresql_using="gin",
            postgresql_ops={"cmetadata": "jsonb_path_ops"},
        ),
        # B-tree indexes for frequently queried metadata fields
        Index("idx_embedding_document_id", cmetadata["document_id"].astext),
        Index("idx_embedding_document_type", cmetadata["document_type"].astext),
        # Vector index will be created separately (HNSW or IVFFlat)
        # CREATE INDEX ON langchain_pg_embedding USING hnsw (embedding vector_cosine_ops);
        {"comment": "Vector embeddings storage with metadata (v3 - 1536 dim)"},
    )

    def __repr__(self):
        doc_id = self.cmetadata.get("document_id") if self.cmetadata else None
        return f"<LangchainPGEmbedding(id={self.id}, document_id={doc_id})>"

    def to_dict(self):
        """Convert to dictionary (without embedding vector for readability)"""
        return {
            "id": self.id,
            "collection_id": str(self.collection_id) if self.collection_id else None,
            "document": (
                self.document[:100] + "..."
                if self.document and len(self.document) > 100
                else self.document
            ),
            "metadata": self.cmetadata,
            "chunk_id": str(self.chunk_id) if self.chunk_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "embedding_dims": len(self.embedding) if self.embedding else None,
        }
