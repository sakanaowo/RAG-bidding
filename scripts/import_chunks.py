#!/usr/bin/env python3
"""
Import processed chunks from JSONL into vectorstore
"""
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add app directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.embedding.store.pgvector_store import vector_store, bootstrap
from src.config.models import settings
from langchain.schema import Document


def load_chunks_from_jsonl(file_path: str) -> List[Dict[str, Any]]:
    """Load chunks from JSONL file."""
    chunks = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    chunk = json.loads(line.strip())
                    chunks.append(chunk)
        print(f"✅ Loaded {len(chunks)} chunks from {file_path}")
        return chunks
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
        return []
    except Exception as e:
        print(f"❌ Error loading chunks: {e}")
        return []


def convert_chunks_to_documents(chunks: List[Dict[str, Any]]) -> List[Document]:
    """Convert chunk dicts to LangChain Documents."""
    documents = []

    for i, chunk in enumerate(chunks):
        try:
            # Extract content
            content = chunk.get("content", chunk.get("text", ""))
            if not content:
                print(f"⚠️ Warning: Empty content in chunk {i}")
                continue

            # Extract metadata
            metadata = chunk.get("metadata", {})

            # Ensure required metadata fields
            if "source_file" not in metadata and "source" in chunk:
                metadata["source_file"] = chunk["source"]

            if "chunk_id" not in metadata:
                metadata["chunk_id"] = chunk.get("chunk_id", f"chunk_{i}")

            # Add document info if available
            if "document_title" in chunk:
                metadata["document_title"] = chunk["document_title"]
            if "document_type" in chunk:
                metadata["document_type"] = chunk["document_type"]

            # Create Document
            doc = Document(page_content=content, metadata=metadata)
            documents.append(doc)

        except Exception as e:
            print(f"⚠️ Error converting chunk {i}: {e}")
            continue

    print(f"✅ Converted {len(documents)} chunks to Documents")
    return documents


def import_chunks_to_vectorstore(chunks_file: str) -> bool:
    """Import chunks from JSONL file to vectorstore."""
    print("🚀 Starting chunks import to vectorstore...")
    print(f"📁 Source file: {chunks_file}")
    print(f"🗄️ Collection: {settings.collection}")
    print(f"🤖 Embedding model: {settings.embed_model}")

    try:
        # Load chunks
        chunks = load_chunks_from_jsonl(chunks_file)
        if not chunks:
            print("❌ No chunks to import")
            return False

        # Convert to Documents
        documents = convert_chunks_to_documents(chunks)
        if not documents:
            print("❌ No valid documents to import")
            return False

        # Bootstrap database first
        print("🔧 Bootstrapping database...")
        bootstrap()

        # Import documents in batches
        batch_size = 50
        total_docs = len(documents)

        print(f"📥 Importing {total_docs} documents in batches of {batch_size}...")

        for i in range(0, total_docs, batch_size):
            batch = documents[i : i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_docs + batch_size - 1) // batch_size

            print(f"   Batch {batch_num}/{total_batches}: {len(batch)} documents")

            try:
                vector_store.add_documents(batch)
                print(f"   ✅ Batch {batch_num} imported successfully")
            except Exception as e:
                print(f"   ❌ Error importing batch {batch_num}: {e}")
                return False

        print(f"🎉 Successfully imported {total_docs} documents to vectorstore!")
        return True

    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def test_vectorstore_search(query: str = "Điều kiện tham gia đấu thầu") -> None:
    """Test vectorstore with a sample search."""
    print(f"\n🔍 Testing vectorstore search: '{query}'")

    try:
        # Search similar documents
        docs = vector_store.similarity_search(query, k=3)

        print(f"📊 Found {len(docs)} similar documents:")
        for i, doc in enumerate(docs, 1):
            print(f"\n{i}. Document:")
            print(f"   📄 Content: {doc.page_content[:200]}...")
            print(f"   📋 Metadata: {doc.metadata}")

        return True

    except Exception as e:
        print(f"❌ Search test failed: {e}")
        return False


def main():
    """Main function."""
    # Default path to processed chunks
    chunks_file = (
        "/home/sakana/Code/RAG-bidding/app/data/outputs/processed_chunks.jsonl"
    )

    # Check if file exists
    if not Path(chunks_file).exists():
        print(f"❌ Chunks file not found: {chunks_file}")
        print("Please run the md-preprocess integration script first.")
        sys.exit(1)

    # Import chunks
    success = import_chunks_to_vectorstore(chunks_file)

    if success:
        # Test the vectorstore
        print("\n" + "=" * 60)
        test_vectorstore_search()
        print("\n🎯 Vectorstore setup complete! Ready for RAG queries.")
    else:
        print("❌ Import failed. Please check the logs above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
