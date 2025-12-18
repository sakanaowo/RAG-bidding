"""
Test Upload Script - Upload a sample document to rag_bidding_v3 database
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.models import settings
from src.embedding.store.pgvector_store import bootstrap, PGVectorStore
from langchain_core.documents import Document


def test_connection():
    """Test database connection"""
    print("=" * 60)
    print("🔍 Testing Database Connection")
    print("=" * 60)
    print(f"Database: {settings.database_url}")
    print(f"Embedding Model: {settings.embed_model}")
    print()

    try:
        import psycopg

        dsn = settings.database_url.replace("postgresql+psycopg", "postgresql")
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                # Check database name
                cur.execute("SELECT current_database()")
                db_name = cur.fetchone()[0]
                print(f"✅ Connected to database: {db_name}")

                # Check tables
                cur.execute(
                    """
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    ORDER BY table_name
                """
                )
                tables = [row[0] for row in cur.fetchall()]
                print(f"✅ Found {len(tables)} tables: {', '.join(tables)}")

                # Check vector dimensions
                cur.execute(
                    """
                    SELECT column_name, data_type, udt_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'langchain_pg_embedding' 
                    AND column_name = 'embedding'
                """
                )
                result = cur.fetchone()
                if result:
                    print(f"✅ Vector column: {result[0]} ({result[2]})")
                else:
                    print("⚠️ No vector column found - need to bootstrap")

                # Check vector index
                cur.execute(
                    """
                    SELECT indexname, indexdef 
                    FROM pg_indexes 
                    WHERE tablename = 'langchain_pg_embedding'
                    AND indexdef LIKE '%hnsw%'
                """
                )
                indexes = cur.fetchall()
                if indexes:
                    for idx_name, idx_def in indexes:
                        print(f"✅ HNSW Index: {idx_name}")
                else:
                    print("⚠️ No HNSW index found")

        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


def test_embedding_dimensions():
    """Test embedding dimensions"""
    print("\n" + "=" * 60)
    print("🧪 Testing Embedding Dimensions")
    print("=" * 60)

    from langchain_openai import OpenAIEmbeddings

    try:
        embeddings = OpenAIEmbeddings(model=settings.embed_model)

        # Test single embedding
        test_text = "Đây là một câu test để kiểm tra embedding."
        vector = embeddings.embed_query(test_text)

        print(f"Model: {settings.embed_model}")
        print(f"✅ Embedding dimension: {len(vector)}")
        print(f"Sample vector (first 5): {vector[:5]}")

        # Verify expected dimensions
        expected_dims = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
        }
        expected = expected_dims.get(settings.embed_model)
        if expected and len(vector) == expected:
            print(f"✅ Dimension matches expected: {expected}")
        else:
            print(f"⚠️ Dimension mismatch: got {len(vector)}, expected {expected}")

        return True
    except Exception as e:
        print(f"❌ Embedding test failed: {e}")
        return False


def test_bootstrap():
    """Test vector store bootstrap"""
    print("\n" + "=" * 60)
    print("🔧 Bootstrapping Vector Store")
    print("=" * 60)

    try:
        bootstrap()
        print("✅ Vector store bootstrap completed")
        return True
    except Exception as e:
        print(f"❌ Bootstrap failed: {e}")
        return False


def test_simple_upload():
    """Test simple document upload"""
    print("\n" + "=" * 60)
    print("📤 Testing Simple Document Upload")
    print("=" * 60)

    try:
        vector_store = PGVectorStore()

        # Create test documents
        test_docs = [
            Document(
                page_content="Luật Đấu thầu số 43/2013/QH13 quy định về đấu thầu trong hoạt động đầu tư sử dụng vốn nhà nước.",
                metadata={
                    "document_id": "TEST-LAW-001",
                    "chunk_id": "TEST-LAW-001-chunk-0",
                    "chunk_index": 0,
                    "document_type": "law",
                    "category": "Luật chính",
                    "section_title": "Chương 1: Quy định chung",
                },
            ),
            Document(
                page_content="Nghị định 63/2014/NĐ-CP hướng dẫn chi tiết một số điều của Luật Đấu thầu về lựa chọn nhà thầu.",
                metadata={
                    "document_id": "TEST-DECREE-001",
                    "chunk_id": "TEST-DECREE-001-chunk-0",
                    "chunk_index": 0,
                    "document_type": "decree",
                    "category": "Quy định khác",
                    "section_title": "Điều 1: Phạm vi điều chỉnh",
                },
            ),
        ]

        print(f"Uploading {len(test_docs)} test documents...")
        ids = vector_store.add_documents(test_docs)

        print(f"✅ Uploaded {len(ids)} documents")
        print(f"Document IDs: {ids}")

        # Test similarity search
        print("\nTesting similarity search...")
        query = "quy định về đấu thầu"
        results = vector_store.similarity_search(query, k=2)

        print(f"✅ Found {len(results)} similar documents:")
        for i, doc in enumerate(results, 1):
            print(f"\n{i}. {doc.metadata.get('section_title', 'No title')}")
            print(f"   Content: {doc.page_content[:100]}...")
            print(f"   Category: {doc.metadata.get('category', 'N/A')}")

        return True

    except Exception as e:
        print(f"❌ Upload test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "🚀 " * 20)
    print("RAG BIDDING V3 - DATABASE & EMBEDDING TEST")
    print("🚀 " * 20 + "\n")

    results = []

    # Test 1: Connection
    results.append(("Database Connection", test_connection()))

    # Test 2: Embedding dimensions
    results.append(("Embedding Dimensions", test_embedding_dimensions()))

    # Test 3: Bootstrap (if needed)
    results.append(("Vector Store Bootstrap", test_bootstrap()))

    # Test 4: Simple upload
    results.append(("Document Upload", test_simple_upload()))

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:<30} {status}")

    all_passed = all(result[1] for result in results)

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Database ready for production upload")
    else:
        print("⚠️ SOME TESTS FAILED - Check errors above")
    print("=" * 60 + "\n")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
