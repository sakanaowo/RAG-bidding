#!/usr/bin/env python3
"""
Test retrieval with metadata filters.
Tests filtering by document_type and level.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from src.config.models import settings


def test_retrieval_with_filter(
    vector_store, query: str, filter_dict: dict, description: str
):
    """Test retrieval with specific filter."""
    print(f"\n{'='*80}")
    print(f"TEST: {description}")
    print(f"Query: {query}")
    print(f"Filter: {filter_dict}")
    print("=" * 80)

    try:
        docs = vector_store.similarity_search(query, k=5, filter=filter_dict)

        print(f"\n✓ Found {len(docs)} results")

        for i, doc in enumerate(docs[:3], 1):  # Show top 3
            print(f"\n{i}. Chunk: {doc.metadata.get('chunk_id', 'N/A')[:50]}")
            print(f"   Type: {doc.metadata.get('document_type', 'N/A')}")
            print(f"   Level: {doc.metadata.get('level', 'N/A')}")
            print(f"   Section: {doc.metadata.get('section_title', 'N/A')[:60]}")

            # Verify filter worked
            if "document_type" in filter_dict:
                assert (
                    doc.metadata.get("document_type") == filter_dict["document_type"]
                ), f"Filter failed! Expected type '{filter_dict['document_type']}', got '{doc.metadata.get('document_type')}'"

            if "level" in filter_dict:
                assert (
                    doc.metadata.get("level") == filter_dict["level"]
                ), f"Filter failed! Expected level '{filter_dict['level']}', got '{doc.metadata.get('level')}'"

        print("\n✅ Filter validation passed!")
        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def main():
    """Run filter tests."""
    print("=" * 80)
    print("TESTING RETRIEVAL WITH METADATA FILTERS")
    print("=" * 80)
    print(f"Database: {settings.database_url.split('@')[-1]}")
    print(f"Collection: {settings.collection}")

    # Initialize vector store
    print("\n🔌 Connecting to database...")
    embeddings = OpenAIEmbeddings(model=settings.embed_model)
    vector_store = PGVector(
        embeddings=embeddings,
        collection_name=settings.collection,
        connection=settings.database_url,
        use_jsonb=True,
    )

    # Test cases
    test_cases = [
        {
            "query": "điều kiện tham gia đấu thầu",
            "filter": {"document_type": "law"},
            "description": "Filter by document_type = 'law'",
        },
        {
            "query": "hồ sơ mời thầu gồm những gì",
            "filter": {"document_type": "decree"},
            "description": "Filter by document_type = 'decree'",
        },
        {
            "query": "mẫu hợp đồng xây dựng",
            "filter": {"document_type": "bidding"},
            "description": "Filter by document_type = 'bidding'",
        },
        {
            "query": "quy định về đấu thầu",
            "filter": {"level": "dieu"},
            "description": "Filter by level = 'dieu'",
        },
        {
            "query": "điều kiện hợp lệ",
            "filter": {"level": "khoan"},
            "description": "Filter by level = 'khoan'",
        },
        {
            "query": "mẫu biểu",
            "filter": {"level": "form"},
            "description": "Filter by level = 'form'",
        },
    ]

    # Run tests
    results = []
    for test_case in test_cases:
        success = test_retrieval_with_filter(
            vector_store,
            test_case["query"],
            test_case["filter"],
            test_case["description"],
        )
        results.append(success)

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total tests: {len(results)}")
    print(f"Passed: {sum(results)}")
    print(f"Failed: {len(results) - sum(results)}")

    if all(results):
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print("\n⚠️  Some tests failed")

    print("=" * 80)


if __name__ == "__main__":
    main()
