"""
Example usage of SQLAlchemy models
Demo các pattern thường dùng trong production
"""

import sys
from pathlib import Path

# Add project root to path (parent.parent vì file này ở scripts/examples/)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.models.base import SessionLocal, get_db
from src.models.documents import Document
from src.models.repositories import DocumentRepository
from src.models.embeddings import LangchainPGEmbedding


def example_1_basic_crud():
    """Example 1: Basic CRUD operations"""
    print("\n=== Example 1: Basic CRUD ===\n")

    db = SessionLocal()

    try:
        # CREATE - Add new document
        print("Creating new document...")
        new_doc = Document(
            document_id="example_doc_001",
            document_name="Ví dụ Nghị định ABC",
            category="legal",
            document_type="decree",
            source_file="/data/processed/example.json",
            filename="example.pdf",
            total_chunks=0,
            status="processing",
        )
        db.add(new_doc)
        db.commit()
        db.refresh(new_doc)
        print(f"✅ Created document: {new_doc.document_id}")

        # READ - Get document
        print("\nReading document...")
        doc = (
            db.query(Document).filter(Document.document_id == "example_doc_001").first()
        )
        print(f"✅ Found: {doc.document_name} (status: {doc.status})")

        # UPDATE - Change status
        print("\nUpdating document...")
        doc.status = "active"
        doc.total_chunks = 25
        db.commit()
        print(f"✅ Updated status to: {doc.status}")

        # DELETE (soft) - Mark as deleted
        print("\nSoft deleting document...")
        doc.status = "deleted"
        db.commit()
        print(f"✅ Soft deleted (status: {doc.status})")

        # DELETE (hard) - Actually remove
        print("\nHard deleting document...")
        db.delete(doc)
        db.commit()
        print("✅ Hard deleted from database")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


def example_2_using_repository():
    """Example 2: Using Repository pattern"""
    print("\n=== Example 2: Repository Pattern ===\n")

    db = SessionLocal()

    try:
        # Create using repository
        print("Creating document via repository...")
        doc = DocumentRepository.create(
            db,
            document_id="repo_example_001",
            document_name="Repository Pattern Example",
            category="legal",
            document_type="law",
            source_file="/data/processed/repo_example.json",
            filename="repo_example.pdf",
            total_chunks=50,
        )
        print(f"✅ Created: {doc.document_id}")

        # Get with filters
        print("\nGetting all active laws...")
        laws = DocumentRepository.get_all(
            db, document_type="law", status="active", limit=5
        )
        print(f"✅ Found {len(laws)} active laws")
        for law in laws:
            print(f"   - {law.document_name}")

        # Search
        print("\nSearching documents...")
        results = DocumentRepository.search(db, "luật")
        print(f"✅ Search found {len(results)} results")

        # Get stats
        print("\nGetting statistics...")
        stats = DocumentRepository.get_stats(db)
        print(f"✅ Total documents: {stats['total_documents']}")
        print(f"   By type: {stats['by_type']}")

        # Cleanup
        DocumentRepository.delete(db, "repo_example_001", soft=False)

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


def example_3_query_embeddings():
    """Example 3: Querying vector embeddings"""
    print("\n=== Example 3: Query Embeddings ===\n")

    db = SessionLocal()

    try:
        # Get total embedding count
        print("Counting embeddings...")
        total = db.query(LangchainPGEmbedding).count()
        print(f"✅ Total embeddings: {total}")

        # Get chunks for specific document
        print("\nGetting chunks for first document...")
        first_doc = db.query(Document).filter(Document.status == "active").first()

        if first_doc:
            chunks = (
                db.query(LangchainPGEmbedding)
                .filter(
                    LangchainPGEmbedding.cmetadata["document_id"].astext
                    == first_doc.document_id
                )
                .all()
            )

            print(f"✅ Document '{first_doc.document_name}' has {len(chunks)} chunks")

            if chunks:
                # Show first chunk
                first_chunk = chunks[0]
                print(f"\nFirst chunk preview:")
                print(f"  ID: {first_chunk.id}")
                print(f"  Content: {first_chunk.document[:150]}...")
                print(f"  Metadata: {first_chunk.cmetadata}")

        # Filter by document type
        print("\nCounting law chunks...")
        law_count = (
            db.query(LangchainPGEmbedding)
            .filter(LangchainPGEmbedding.cmetadata["document_type"].astext == "law")
            .count()
        )
        print(f"✅ Law chunks: {law_count}")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()


def example_4_fastapi_style():
    """Example 4: FastAPI-style dependency injection"""
    print("\n=== Example 4: FastAPI Style ===\n")

    # Simulate FastAPI endpoint
    def get_documents_endpoint(
        skip: int = 0,
        limit: int = 10,
        document_type: str = None,
        db=None,  # Would be: Depends(get_db) in FastAPI
    ):
        """Simulated FastAPI endpoint"""
        docs = DocumentRepository.get_all(
            db, skip=skip, limit=limit, document_type=document_type
        )
        return [doc.to_dict() for doc in docs]

    # Get DB session using generator
    db_gen = get_db()
    db = next(db_gen)

    try:
        print("Calling endpoint with pagination...")
        result = get_documents_endpoint(skip=0, limit=5, document_type="law", db=db)

        print(f"✅ Returned {len(result)} documents")
        for doc in result:
            print(f"   - {doc['document_name']} ({doc['document_type']})")

    finally:
        # Close session (FastAPI does this automatically)
        try:
            next(db_gen)
        except StopIteration:
            pass


def example_5_transactions():
    """Example 5: Transaction handling"""
    print("\n=== Example 5: Transactions ===\n")

    db = SessionLocal()

    try:
        # Start transaction
        print("Creating multiple documents in transaction...")

        docs = [
            Document(
                document_id=f"trans_doc_{i:03d}",
                document_name=f"Transaction Test {i}",
                category="test",
                document_type="example",
                source_file=f"/test/doc_{i}.json",
                filename=f"doc_{i}.pdf",
            )
            for i in range(1, 4)
        ]

        for doc in docs:
            db.add(doc)

        # Commit all at once
        db.commit()
        print(f"✅ Created {len(docs)} documents in single transaction")

        # Rollback example
        print("\nTesting rollback...")
        try:
            bad_doc = Document(
                document_id="bad_doc",
                document_name="This will fail",
                category=None,  # This violates NOT NULL constraint
                document_type="test",
                source_file="/test.json",
                file_name="test.pdf",
            )
            db.add(bad_doc)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"✅ Rollback successful: {str(e)[:50]}...")

        # Cleanup
        print("\nCleaning up test documents...")
        db.query(Document).filter(Document.document_id.like("trans_doc_%")).delete()
        db.commit()
        print("✅ Cleanup complete")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


def example_6_advanced_queries():
    """Example 6: Advanced queries"""
    print("\n=== Example 6: Advanced Queries ===\n")

    from sqlalchemy import func, and_, or_

    db = SessionLocal()

    try:
        # Count by type
        print("Documents by type:")
        type_counts = (
            db.query(Document.document_type, func.count(Document.id).label("count"))
            .group_by(Document.document_type)
            .all()
        )

        for doc_type, count in type_counts:
            print(f"  {doc_type}: {count}")

        # Multiple filters with AND
        print("\nActive legal documents:")
        active_legal = (
            db.query(Document)
            .filter(and_(Document.status == "active", Document.category == "legal"))
            .count()
        )
        print(f"✅ Found {active_legal} active legal documents")

        # OR condition
        print("\nLaws or decrees:")
        laws_or_decrees = (
            db.query(Document)
            .filter(
                or_(Document.document_type == "law", Document.document_type == "decree")
            )
            .count()
        )
        print(f"✅ Found {laws_or_decrees} laws or decrees")

        # LIKE search
        print("\nSearch with LIKE:")
        search_results = (
            db.query(Document)
            .filter(Document.document_name.ilike("%luật%"))
            .limit(3)
            .all()
        )
        print(f"✅ Found {len(search_results)} results:")
        for doc in search_results:
            print(f"   - {doc.document_name}")

        # Order by
        print("\nNewest documents:")
        newest = db.query(Document).order_by(Document.created_at.desc()).limit(3).all()
        print(f"✅ {len(newest)} newest documents:")
        for doc in newest:
            print(f"   - {doc.document_name} ({doc.created_at})")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    """Run all examples"""
    print("=" * 60)
    print("SQLAlchemy Usage Examples - RAG Bidding System")
    print("=" * 60)

    # Run examples
    example_1_basic_crud()
    example_2_using_repository()
    example_3_query_embeddings()
    example_4_fastapi_style()
    example_5_transactions()
    example_6_advanced_queries()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)
