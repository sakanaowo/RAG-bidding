#!/usr/bin/env python3
"""
Test context formatter with real retrieval results.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from src.config.models import settings
from src.generation.formatters.context_formatter import (
    ContextFormatter,
    format_context_with_hierarchy
)


def test_formatter_with_retrieval():
    """Test formatter with real retrieved documents."""
    print("=" * 80)
    print("TESTING CONTEXT FORMATTER WITH RETRIEVAL")
    print("=" * 80)
    
    # Initialize vector store
    print("\n🔌 Connecting to database...")
    embeddings = OpenAIEmbeddings(model=settings.embed_model)
    vector_store = PGVector(
        embeddings=embeddings,
        collection_name=settings.collection,
        connection=settings.database_url,
        use_jsonb=True,
    )
    
    # Test queries with different document types
    test_cases = [
        {
            "query": "điều kiện tham gia đấu thầu",
            "filter": {"document_type": "law"},
            "description": "Law documents only"
        },
        {
            "query": "hồ sơ mời thầu gồm những gì",
            "filter": {"document_type": "decree"},
            "description": "Decree documents only"
        },
        {
            "query": "mẫu hợp đồng xây dựng",
            "filter": {"document_type": "bidding"},
            "description": "Bidding templates only"
        },
    ]
    
    formatter = ContextFormatter(
        include_hierarchy=True,
        include_metadata=True,
        max_chars_per_chunk=200  # Truncate for display
    )
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"TEST CASE {i}: {test['description']}")
        print(f"Query: {test['query']}")
        print(f"Filter: {test['filter']}")
        print("=" * 80)
        
        # Retrieve documents
        docs = vector_store.similarity_search(
            test['query'],
            k=3,
            filter=test['filter']
        )
        
        print(f"\n✓ Retrieved {len(docs)} documents\n")
        
        # Format each document
        print("INDIVIDUAL DOCUMENTS:")
        print("-" * 80)
        for j, doc in enumerate(docs, 1):
            formatted = formatter.format_document(doc)
            print(f"\n{j}. {formatted}")
            print()
        
        # Format as full context
        print("\n" + "-" * 80)
        print("FULL CONTEXT (for LLM):")
        print("-" * 80)
        context = format_context_with_hierarchy(
            docs,
            query=test['query'],
            include_instructions=True
        )
        print(context)
    
    print("\n" + "=" * 80)
    print("✅ CONTEXT FORMATTER TEST COMPLETE!")
    print("=" * 80)


if __name__ == "__main__":
    test_formatter_with_retrieval()
