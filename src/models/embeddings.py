"""
Embedding Models
Represents LangChain PGVector tables for vector storage
"""

from sqlalchemy import Column, String, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector

from .base import Base


class LangchainPGCollection(Base):
    """
    LangChain collection table - INTERNAL USE ONLY
    Managed by LangChain library, not directly by application
    """

    __tablename__ = "langchain_pg_collection"

    uuid = Column(UUID(as_uuid=True), primary_key=True, comment="Collection UUID")

    name = Column(String, comment="Collection name (e.g., 'docs')")

    cmetadata = Column(JSONB, comment="Collection metadata")

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
    Vector embedding storage table
    Stores document chunks with their embeddings and metadata
    """

    __tablename__ = "langchain_pg_embedding"

    # Primary key (chunk ID)
    id = Column(String, primary_key=True, comment="Chunk ID (UUID format)")

    # Foreign key to collection
    collection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("langchain_pg_collection.uuid", ondelete="CASCADE"),
        comment="Reference to collection",
    )

    # Vector embedding (3072 dimensions for text-embedding-3-large)
    embedding = Column(
        Vector(3072), comment="OpenAI text-embedding-3-large vector (3072-dim)"
    )

    # Chunk content
    document = Column(Text, comment="Chunk text content")

    # Rich metadata in JSONB
    cmetadata = Column(
        JSONB, comment="Chunk metadata: document_id, chunk_index, hierarchy, etc."
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
        {"comment": "Vector embeddings storage with metadata"},
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
            "embedding_dims": len(self.embedding) if self.embedding else None,
        }
