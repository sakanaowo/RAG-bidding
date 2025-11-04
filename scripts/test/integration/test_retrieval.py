#!/usr/bin/env python3
"""Test vector store retrieval."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from src.config.models import settings

print("=" * 80)
print("TESTING VECTOR STORE RETRIEVAL")
print("=" * 80)
print(f"Database: {settings.database_url.split('@')[-1]}")
print(f"Collection: {settings.collection}")
print()

# Initialize vector store
embeddings = OpenAIEmbeddings(model=settings.embed_model)
vector_store = PGVector(
    embeddings=embeddings,
    collection_name=settings.collection,
    connection=settings.database_url,
    use_jsonb=True,
)

# Test queries
queries = [
    "điều kiện tham gia đấu thầu",
    "quy định về hợp đồng xây dựng",
    "hồ sơ mời thầu gồm những gì",
]

for i, query in enumerate(queries, 1):
    print(f"\n{'='*80}")
    print(f"Query {i}: {query}")
    print("=" * 80)

    # Search
    docs = vector_store.similarity_search(query, k=3)

    for j, doc in enumerate(docs, 1):
        print(f"\n{j}. Chunk ID: {doc.metadata.get('chunk_id', 'N/A')}")
        print(f"   Type: {doc.metadata.get('document_type', 'N/A')}")
        print(f"   Level: {doc.metadata.get('level', 'N/A')}")
        print(f"   Section: {doc.metadata.get('section_title', 'N/A')[:60]}")
        print(f"   Content: {doc.page_content[:200]}...")

print("\n" + "=" * 80)
print("✅ RETRIEVAL TEST COMPLETE!")
print("=" * 80)
