"""
Database initialization and migration utilities
"""

from sqlalchemy import text, inspect
from .base import engine, Base, SessionLocal
from .documents import Document
from .embeddings import LangchainPGEmbedding, LangchainPGCollection


def check_database_exists() -> bool:
    """Check if database tables exist"""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    return len(tables) > 0


def create_all_tables():
    """
    Create all tables defined in models
    ⚠️ Only use in development! Use Alembic for production.
    """
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully")


def create_vector_index():
    """
    Create HNSW vector index for embeddings
    This should be run after table creation
    """
    with SessionLocal() as db:
        try:
            # Check if index already exists
            result = db.execute(
                text(
                    """
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'langchain_pg_embedding' 
                AND indexname = 'idx_embedding_hnsw'
            """
                )
            )

            if result.fetchone():
                print("✅ Vector index already exists")
                return

            print("Creating HNSW vector index...")
            db.execute(
                text(
                    """
                CREATE INDEX IF NOT EXISTS idx_embedding_hnsw
                ON langchain_pg_embedding
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64)
            """
                )
            )
            db.commit()
            print("✅ HNSW index created successfully")

        except Exception as e:
            print(f"❌ Error creating vector index: {e}")
            db.rollback()


def verify_schema():
    """Verify database schema matches models"""
    inspector = inspect(engine)

    expected_tables = {"documents", "langchain_pg_embedding", "langchain_pg_collection"}

    actual_tables = set(inspector.get_table_names())

    print("\n=== Database Schema Verification ===")
    print(f"Expected tables: {expected_tables}")
    print(f"Actual tables: {actual_tables}")

    missing = expected_tables - actual_tables
    if missing:
        print(f"⚠️ Missing tables: {missing}")
        return False

    extra = actual_tables - expected_tables
    if extra:
        print(f"ℹ️ Extra tables: {extra}")

    print("✅ Schema verification passed")
    return True


def get_database_stats():
    """Get current database statistics"""
    with SessionLocal() as db:
        stats = {}

        # Document count
        doc_count = db.execute(text("SELECT COUNT(*) FROM documents")).scalar()
        stats["total_documents"] = doc_count

        # Embedding count
        emb_count = db.execute(
            text("SELECT COUNT(*) FROM langchain_pg_embedding")
        ).scalar()
        stats["total_embeddings"] = emb_count

        # Database size
        size = db.execute(
            text(
                """
            SELECT pg_size_pretty(pg_database_size(current_database()))
        """
            )
        ).scalar()
        stats["database_size"] = size

        # Document types
        types = db.execute(
            text(
                """
            SELECT document_type, COUNT(*) as count
            FROM documents
            GROUP BY document_type
            ORDER BY count DESC
        """
            )
        ).fetchall()
        stats["document_types"] = [{"type": t[0], "count": t[1]} for t in types]

        return stats


if __name__ == "__main__":
    """Run database initialization"""
    print("=== RAG Bidding Database Setup ===\n")

    # Check if tables exist
    if not check_database_exists():
        print("No tables found. Creating schema...")
        create_all_tables()
        create_vector_index()
    else:
        print("Tables already exist. Verifying schema...")
        verify_schema()

    # Show stats
    print("\n=== Database Statistics ===")
    stats = get_database_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")
