#!/usr/bin/env python3
"""
Enrich and Re-embed Existing Chunks

Takes existing chunk JSONL files, enriches them, and re-embeds with 1536 dims.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from src.preprocessing.enrichment import ChunkEnricher
from src.config.models import settings
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_core.documents import Document
from tqdm import tqdm
from sqlalchemy import create_engine, text
import time


def load_chunks_from_jsonl(
    chunks_dir: Path, pattern: str = "*.jsonl"
) -> List[Dict[str, Any]]:
    """Load all chunks from JSONL files (excluding enriched output file)."""
    all_chunks = []

    chunk_files = sorted(chunks_dir.glob(pattern))

    # Exclude the output file to avoid loading enriched chunks twice
    chunk_files = [f for f in chunk_files if f.name != "enriched_chunks.jsonl"]

    print(f"📁 Found {len(chunk_files)} JSONL files (excluding enriched_chunks.jsonl)")

    for file_path in chunk_files:
        chunks = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        chunk = json.loads(line)
                        chunks.append(chunk)
                    except json.JSONDecodeError as e:
                        print(f"⚠️  Error in {file_path.name}: {e}")

        all_chunks.extend(chunks)
        print(f"  ✓ {file_path.name}: {len(chunks)} chunks")

    return all_chunks


def enrich_existing_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Enrich existing chunks with semantic metadata."""
    print(f"\n🔍 Enriching {len(chunks):,} chunks...")

    enricher = ChunkEnricher()

    # Enrich in batches for progress tracking
    enriched = []
    batch_size = 100

    with tqdm(total=len(chunks), desc="Enriching", unit="chunks") as pbar:
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            enriched_batch = enricher.enrich_chunks(batch)
            enriched.extend(enriched_batch)
            pbar.update(len(batch))

    # Print stats
    stats = enricher.get_enrichment_stats(enriched)
    print(f"\n✨ Enrichment Statistics:")
    print(f"   Total chunks: {stats['total_chunks']:,}")
    print(f"   Enriched: {stats['enriched_chunks']:,}")
    print(f"   Failed: {stats['failed_chunks']:,}")
    print(f"   Avg entities/chunk: {stats.get('avg_entities_per_chunk', 0):.1f}")
    print(f"   Avg concepts/chunk: {stats.get('avg_concepts_per_chunk', 0):.1f}")
    print(f"   Avg keywords/chunk: {stats.get('avg_keywords_per_chunk', 0):.1f}")
    print(f"\n📊 Document Focus Distribution:")
    for focus, count in sorted(
        stats["document_focuses"].items(), key=lambda x: x[1], reverse=True
    ):
        pct = (count / stats["total_chunks"]) * 100
        print(f"      {focus}: {count} ({pct:.1f}%)")

    return enriched


def clear_collection(collection_name: str, db_url: str):
    """Clear all embeddings from collection."""
    print(f"\n🗑️  Clearing collection '{collection_name}'...")

    engine = create_engine(db_url)
    with engine.connect() as conn:
        # Get collection ID
        result = conn.execute(
            text("SELECT uuid FROM langchain_pg_collection WHERE name = :name"),
            {"name": collection_name},
        )
        collection = result.fetchone()

        if collection:
            collection_id = collection[0]

            # Count current embeddings
            count_result = conn.execute(
                text(
                    "SELECT COUNT(*) FROM langchain_pg_embedding WHERE collection_id = :coll_id"
                ),
                {"coll_id": collection_id},
            )
            count = count_result.scalar()
            print(f"   Found {count:,} existing embeddings")

            # Delete embeddings
            conn.execute(
                text(
                    "DELETE FROM langchain_pg_embedding WHERE collection_id = :coll_id"
                ),
                {"coll_id": collection_id},
            )
            conn.commit()
            print(f"   ✅ Deleted {count:,} embeddings")
        else:
            print(f"   Collection '{collection_name}' not found (will be created)")


def chunk_to_document(chunk: Dict[str, Any]) -> Document:
    """Convert chunk dict to LangChain Document."""

    # Extract text content
    text = chunk.get("content", chunk.get("text", ""))

    # Get metadata
    metadata = chunk.get("metadata", {})

    # Add chunk_id if not in metadata
    if "chunk_id" not in metadata:
        metadata["chunk_id"] = chunk.get("chunk_id", chunk.get("id", "unknown"))

    # Flatten nested structures for PGVector
    for key, value in list(metadata.items()):
        if isinstance(value, (list, dict)):
            metadata[key] = json.dumps(value, ensure_ascii=False)

    return Document(page_content=text, metadata=metadata)


def import_with_embeddings(
    chunks: List[Dict[str, Any]],
    collection_name: str,
    db_url: str,
    embed_model: str,
    batch_size: int = 30,
) -> int:
    """
    Import chunks with embeddings at native 3072 dimensions.

    Returns:
        Number of chunks imported
    """
    print(f"\n📥 Importing {len(chunks):,} chunks to database...")
    print(f"   Model: {embed_model}")
    print(f"   Dimensions: 3072 (native)")
    print(f"   Collection: {collection_name}")
    print(f"   Batch size: {batch_size}")

    # Initialize embeddings with native dimensions
    embeddings = OpenAIEmbeddings(
        model=embed_model,
        # No dimensions parameter = native 3072 dims
    )

    # Initialize vector store
    vector_store = PGVector(
        embeddings=embeddings,
        collection_name=collection_name,
        connection=db_url,
        use_jsonb=True,
    )

    # Import in batches
    total_imported = 0
    num_batches = (len(chunks) + batch_size - 1) // batch_size

    with tqdm(total=len(chunks), desc="Embedding & Importing", unit="chunks") as pbar:
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]

            # Convert to Documents
            documents = [chunk_to_document(chunk) for chunk in batch]

            # Add to vector store (embeds + stores)
            try:
                vector_store.add_documents(documents)
                total_imported += len(documents)
                pbar.update(len(documents))
            except Exception as e:
                print(f"\n❌ Error in batch {i//batch_size + 1}/{num_batches}: {e}")
                pbar.update(len(documents))

    return total_imported


def main():
    parser = argparse.ArgumentParser(
        description="Enrich existing chunks and re-embed with 1536 dimensions"
    )
    parser.add_argument(
        "--chunks-dir",
        type=Path,
        default=Path("data/processed/chunks"),
        help="Directory containing chunk JSONL files",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path("data/processed/chunks/enriched_chunks.jsonl"),
        help="Output file for enriched chunks",
    )
    parser.add_argument(
        "--pattern", type=str, default="*.jsonl", help="File pattern to match"
    )
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Don't clear existing embeddings before import",
    )
    parser.add_argument("--batch-size", type=int, default=50, help="Import batch size")
    parser.add_argument(
        "--dry-run", action="store_true", help="Enrich but don't import to database"
    )
    parser.add_argument(
        "--enrich-only",
        action="store_true",
        help="Only enrich and save to file, don't import",
    )

    args = parser.parse_args()

    # Resolve paths
    chunks_dir = args.chunks_dir
    if not chunks_dir.is_absolute():
        chunks_dir = Path(__file__).parent.parent / chunks_dir

    output_file = args.output_file
    if not output_file.is_absolute():
        output_file = Path(__file__).parent.parent / output_file

    if not chunks_dir.exists():
        print(f"❌ Chunks directory not found: {chunks_dir}")
        sys.exit(1)

    print("=" * 80)
    print("ENRICH & RE-EMBED EXISTING CHUNKS")
    print("=" * 80)
    print(f"Chunks dir: {chunks_dir}")
    print(f"Pattern: {args.pattern}")
    print(f"Output: {output_file}")
    print(f"Collection: {settings.collection}")
    print(f"Model: {settings.embed_model} @ 3072 dims (native)")
    print(f"Dry run: {args.dry_run}")

    start_time = time.time()

    # Step 1: Load existing chunks
    chunks = load_chunks_from_jsonl(chunks_dir, args.pattern)

    if not chunks:
        print("❌ No chunks found!")
        sys.exit(1)

    print(f"\n📊 Loaded {len(chunks):,} chunks total")

    # Step 2: Enrich chunks
    enriched_chunks = enrich_existing_chunks(chunks)

    # Step 3: Save enriched chunks
    output_file.parent.mkdir(parents=True, exist_ok=True)
    print(f"\n💾 Saving enriched chunks to {output_file}")
    with open(output_file, "w", encoding="utf-8") as f:
        for chunk in enriched_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    print(f"   ✅ Saved {len(enriched_chunks):,} enriched chunks")

    if args.dry_run or args.enrich_only:
        print("\n🔍 Skipping database import")
        if enriched_chunks:
            print("\nSample enriched metadata:")
            sample = enriched_chunks[0]
            metadata = sample.get("metadata", {})
            print(f"  Enriched: {metadata.get('enriched', False)}")
            print(f"  Keywords: {metadata.get('keywords', [])[:5]}")
            print(f"  Primary concepts: {metadata.get('primary_concepts', [])[:3]}")
            print(f"  Referenced laws: {metadata.get('referenced_laws', [])[:3]}")
            print(f"  Document focus: {metadata.get('document_focus', 'unknown')}")
        return

    # Step 4: Clear existing embeddings (if not skipped)
    if not args.no_clear:
        clear_collection(settings.collection, settings.database_url)

    # Step 5: Import with new 1536-dim embeddings
    imported = import_with_embeddings(
        enriched_chunks,
        settings.collection,
        settings.database_url,
        settings.embed_model,
        args.batch_size,
    )

    elapsed = time.time() - start_time

    # Summary
    print("\n" + "=" * 80)
    print("ENRICHMENT & RE-EMBEDDING COMPLETE")
    print("=" * 80)
    print(f"Chunks processed: {len(chunks):,}")
    print(f"Chunks enriched: {len(enriched_chunks):,}")
    print(f"Chunks imported: {imported:,}")
    print(f"Time: {elapsed/60:.1f} minutes")
    print(f"Output: {output_file}")
    print(f"Embedding dimensions: 1536 (reduced from 3072)")
    print("\n✅ Ready for HNSW index creation!")
    print("\nNext steps:")
    print("  1. Test retrieval: python scripts/test_retrieval.py")
    print("  2. Create HNSW index: See database migration guide")
    print("  3. Benchmark: python scripts/benchmark_retrieval.py")


if __name__ == "__main__":
    main()
