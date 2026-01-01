#!/usr/bin/env python3
"""
Import processed chunks (UniversalChunk format) to PGVector database.
Converts UniversalChunk to LangChain Document and stores with embeddings.
"""
import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any
from tqdm import tqdm

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from src.config.models import settings


def load_universal_chunk(file_path: Path) -> List[Dict[str, Any]]:
    """Load UniversalChunk objects from JSONL file."""
    chunks = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    chunk = json.loads(line)
                    chunks.append(chunk)
                except json.JSONDecodeError as e:
                    print(f"⚠️  Error parsing line in {file_path}: {e}")
    return chunks


def universal_chunk_to_document(chunk: Dict[str, Any]) -> Document:
    """
    Convert UniversalChunk to LangChain Document.

    Preserves all metadata including hierarchy as JSON.
    """
    content = chunk.get("content", "")

    # Build metadata - preserve all fields
    metadata = {
        "chunk_id": chunk.get("chunk_id"),
        "document_id": chunk.get("document_id"),
        "document_type": chunk.get("document_type"),
        "hierarchy": json.dumps(
            chunk.get("hierarchy", []), ensure_ascii=False
        ),  # Store as JSON string
        "level": chunk.get("level"),
        "section_title": chunk.get("section_title", ""),
        "char_count": chunk.get("char_count", len(content)),
        "chunk_index": chunk.get("chunk_index", 0),
        "total_chunks": chunk.get("total_chunks", 1),
        "is_complete_unit": chunk.get("is_complete_unit", True),
        "has_table": chunk.get("has_table", False),
        "has_list": chunk.get("has_list", False),
        "extra_metadata": json.dumps(
            chunk.get("extra_metadata", {}), ensure_ascii=False
        ),
    }

    return Document(page_content=content, metadata=metadata)


def import_chunks_batch(
    chunks: List[Dict[str, Any]], vector_store: PGVector, batch_size: int = 50
) -> int:
    """
    Import chunks in batches with progress bar.

    Returns:
        Number of chunks successfully imported
    """
    total_imported = 0
    num_batches = (len(chunks) + batch_size - 1) // batch_size

    with tqdm(total=len(chunks), desc="Importing", unit="chunks") as pbar:
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]

            # Convert to Documents
            documents = [universal_chunk_to_document(chunk) for chunk in batch]

            # Add to vector store (automatically embeds)
            try:
                vector_store.add_documents(documents)
                total_imported += len(documents)
                pbar.update(len(documents))
            except Exception as e:
                print(f"\n❌ Error importing batch {i//batch_size + 1}: {e}")
                pbar.update(len(documents))

    return total_imported


def main():
    """Main import pipeline."""
    parser = argparse.ArgumentParser(description="Import processed chunks to PGVector")
    parser.add_argument(
        "--chunks-dir",
        type=Path,
        default=Path("data/processed/chunks"),
        help="Directory containing chunk JSONL files",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of chunks to import per batch",
    )
    parser.add_argument(
        "--file-pattern",
        type=str,
        default="*.jsonl",
        help="File pattern to match (e.g., 'Luat*.jsonl')",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Load files but don't import to database"
    )

    args = parser.parse_args()

    # Resolve chunks directory
    chunks_dir = args.chunks_dir
    if not chunks_dir.is_absolute():
        chunks_dir = Path(__file__).parent.parent / chunks_dir

    if not chunks_dir.exists():
        print(f"❌ Directory not found: {chunks_dir}")
        sys.exit(1)

    print("=" * 80)
    print("IMPORT PROCESSED CHUNKS TO PGVECTOR")
    print("=" * 80)
    print(f"Database: {settings.database_url.split('@')[-1]}")
    print(f"Collection: {settings.collection}")
    print(f"Embedding Model: {settings.embed_model}")
    print(f"Embedding Dimensions: 3072 (native)")
    print(f"Dry run: {args.dry_run}")
    print()

    # Find chunk files
    chunk_files = sorted(chunks_dir.glob(args.file_pattern))
    print(f"📁 Found {len(chunk_files)} chunk files matching '{args.file_pattern}'")

    if not chunk_files:
        print("❌ No files found!")
        sys.exit(1)

    # Load all chunks
    all_chunks = []
    for file_path in chunk_files:
        chunks = load_universal_chunk(file_path)
        all_chunks.extend(chunks)
        print(f"  ✓ {file_path.name}: {len(chunks)} chunks")

    print(f"\n📊 Total chunks loaded: {len(all_chunks)}")

    if args.dry_run:
        print("\n🔍 DRY RUN - Showing sample metadata:")
        if all_chunks:
            sample = all_chunks[0]
            print(f"\nSample chunk:")
            print(f"  chunk_id: {sample.get('chunk_id')}")
            print(f"  document_type: {sample.get('document_type')}")
            print(f"  level: {sample.get('level')}")
            print(f"  hierarchy: {sample.get('hierarchy')}")
            print(f"  section_title: {sample.get('section_title', '')[:60]}")
            print(f"  char_count: {sample.get('char_count')}")
            print(f"  content length: {len(sample.get('content', ''))}")
        print("\n✅ Dry run complete. Use without --dry-run to import.")
        return

    # Initialize vector store
    print("\n🔌 Connecting to database...")

    # Use native 3072 dimensions for text-embedding-3-large
    embeddings = OpenAIEmbeddings(
        model=settings.embed_model,
        # No dimensions parameter = native 3072 dims
    )

    print(f"   Using {settings.embed_model} with native 3072 dimensions")

    vector_store = PGVector(
        embeddings=embeddings,
        collection_name=settings.collection,
        connection=settings.database_url,
        use_jsonb=True,
    )

    # Import chunks
    print(f"\n📥 Importing {len(all_chunks)} chunks (batch size: {args.batch_size})...")
    imported_count = import_chunks_batch(all_chunks, vector_store, args.batch_size)

    # Summary
    print("\n" + "=" * 80)
    print("IMPORT SUMMARY")
    print("=" * 80)
    print(f"Files processed:   {len(chunk_files)}")
    print(f"Chunks loaded:     {len(all_chunks):,}")
    print(f"Chunks imported:   {imported_count:,}")

    if imported_count == len(all_chunks):
        print("\n✅ ALL CHUNKS IMPORTED SUCCESSFULLY!")
    else:
        print(
            f"\n⚠️  Some chunks failed to import ({len(all_chunks) - imported_count} failed)"
        )

    print("=" * 80)


if __name__ == "__main__":
    main()
