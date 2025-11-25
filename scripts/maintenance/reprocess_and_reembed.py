#!/usr/bin/env python3
"""
Batch Reprocess and Re-embed with Enrichment

This script:
1. Reprocesses all MD files with enrichment enabled
2. Re-embeds with native 3072 dimensions
3. Clears old database and imports new enriched chunks
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

from src.preprocessing.parsers import MarkdownDocumentProcessor
from src.config.models import settings
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_core.documents import Document
from tqdm import tqdm
from sqlalchemy import create_engine, text
import time


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


def reprocess_all_documents(
    input_dir: Path, output_dir: Path, enable_enrichment: bool = True
) -> List[Dict[str, Any]]:
    """
    Reprocess all MD files with enrichment.

    Returns:
        List of all processed chunks
    """
    print(f"\n📂 Reprocessing documents from: {input_dir}")
    print(f"   Enrichment: {'✅ Enabled' if enable_enrichment else '❌ Disabled'}")

    # Initialize processor with enrichment
    processor = MarkdownDocumentProcessor(
        max_chunk_size=2000,
        min_chunk_size=300,
        token_limit=6500,
        enable_enrichment=enable_enrichment,
    )

    # Find all MD files
    md_files = sorted(input_dir.glob("*.md"))
    print(f"   Found {len(md_files)} MD files")

    all_chunks = []
    stats = {
        "processed": 0,
        "failed": 0,
        "total_chunks": 0,
    }

    for md_file in md_files:
        try:
            print(f"\n📄 {md_file.name}")

            # Parse
            document = processor.parse_md_file(str(md_file))

            # Validate
            if not processor.validate_document(document):
                print(f"   ❌ Validation failed")
                stats["failed"] += 1
                continue

            # Chunk
            chunks = processor.process_to_chunks(document)
            print(f"   📊 {len(chunks)} chunks created")

            # Validate & Enrich (enrichment happens inside validate_chunks)
            validated_chunks = processor.validate_chunks(chunks)

            all_chunks.extend(validated_chunks)
            stats["processed"] += 1
            stats["total_chunks"] += len(validated_chunks)

        except Exception as e:
            print(f"   ❌ Error: {e}")
            stats["failed"] += 1

    # Export to JSONL
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "enriched_chunks.jsonl"

    print(f"\n💾 Exporting to {output_file}")
    with open(output_file, "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print(f"\n📊 Reprocessing Summary:")
    print(f"   Files processed: {stats['processed']}")
    print(f"   Files failed: {stats['failed']}")
    print(f"   Total chunks: {stats['total_chunks']:,}")
    print(f"   Output: {output_file}")

    return all_chunks


def chunk_to_document(chunk: Dict[str, Any]) -> Document:
    """Convert chunk dict to LangChain Document."""
    text = chunk.get("text", "")
    metadata = chunk.get("metadata", {})

    # Flatten nested lists to strings for PGVector
    for key, value in metadata.items():
        if isinstance(value, (list, dict)):
            metadata[key] = json.dumps(value, ensure_ascii=False)

    return Document(page_content=text, metadata=metadata)


def import_with_embeddings(
    chunks: List[Dict[str, Any]],
    collection_name: str,
    db_url: str,
    embed_model: str,
    batch_size: int = 50,
) -> int:
    """
    Import chunks with native 3072-dimensional embeddings.

    Returns:
        Number of chunks imported
    """
    print(f"\n📥 Importing {len(chunks):,} chunks with new embeddings...")
    print(f"   Model: {embed_model}")
    print(f"   Dimensions: 3072 (native)")
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
        description="Batch reprocess and re-embed all documents with enrichment"
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/processed"),
        help="Directory containing MD files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed/chunks"),
        help="Output directory for enriched chunks",
    )
    parser.add_argument(
        "--no-enrichment",
        action="store_true",
        help="Disable enrichment (just re-embed)",
    )
    parser.add_argument(
        "--no-clear", action="store_true", help="Don't clear existing embeddings"
    )
    parser.add_argument("--batch-size", type=int, default=50, help="Import batch size")
    parser.add_argument(
        "--dry-run", action="store_true", help="Process but don't import to database"
    )

    args = parser.parse_args()

    # Resolve paths
    input_dir = args.input_dir
    if not input_dir.is_absolute():
        input_dir = Path(__file__).parent.parent / input_dir

    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = Path(__file__).parent.parent / output_dir

    if not input_dir.exists():
        print(f"❌ Input directory not found: {input_dir}")
        sys.exit(1)

    print("=" * 80)
    print("BATCH REPROCESS & RE-EMBED WITH ENRICHMENT")
    print("=" * 80)
    print(f"Input: {input_dir}")
    print(f"Output: {output_dir}")
    print(f"Enrichment: {'❌ Disabled' if args.no_enrichment else '✅ Enabled'}")
    print(f"Collection: {settings.collection}")
    print(f"Model: {settings.embed_model} @ 3072 dims (native)")
    print(f"Dry run: {args.dry_run}")

    start_time = time.time()

    # Step 1: Clear existing embeddings (if not skipped)
    if not args.dry_run and not args.no_clear:
        clear_collection(settings.collection, settings.database_url)

    # Step 2: Reprocess all documents with enrichment
    chunks = reprocess_all_documents(
        input_dir, output_dir, enable_enrichment=not args.no_enrichment
    )

    if args.dry_run:
        print("\n🔍 DRY RUN - Skipping database import")
        if chunks:
            print("\nSample enriched chunk metadata:")
            sample = chunks[0]
            metadata = sample.get("metadata", {})
            print(f"  Enriched: {metadata.get('enriched', False)}")
            print(f"  Keywords: {metadata.get('keywords', [])[:5]}")
            print(f"  Concepts: {metadata.get('primary_concepts', [])[:3]}")
            print(
                f"  Entities: Laws={len(metadata.get('referenced_laws', []))}, "
                f"Decrees={len(metadata.get('referenced_decrees', []))}"
            )
        return

    # Step 3: Import with new embeddings
    imported = import_with_embeddings(
        chunks,
        settings.collection,
        settings.database_url,
        settings.embed_model,
        args.batch_size,
    )

    elapsed = time.time() - start_time

    # Summary
    print("\n" + "=" * 80)
    print("REPROCESSING & RE-EMBEDDING COMPLETE")
    print("=" * 80)
    print(f"Total chunks: {len(chunks):,}")
    print(f"Imported: {imported:,}")
    print(f"Time: {elapsed/60:.1f} minutes")
    print(f"Enrichment: {'✅ Applied' if not args.no_enrichment else '❌ Skipped'}")
    print(f"Embedding dimensions: 3072 (native)")
    print("\n✅ Complete!")


if __name__ == "__main__":
    main()
