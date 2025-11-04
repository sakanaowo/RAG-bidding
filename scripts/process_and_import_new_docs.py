#!/usr/bin/env python3
"""
Unified Pipeline: Process MD files → Enrich → Import to Database

Use this script to add new documents to the system.
It will automatically:
1. Find new MD files
2. Process with optimal chunking
3. Enrich with semantic metadata
4. Embed with 1536 dimensions
5. Import to PGVector database
"""

import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any
import json
import time

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


def process_new_md_files(
    input_dir: Path, output_dir: Path, enable_enrichment: bool = True
) -> List[Dict[str, Any]]:
    """
    Process all MD files with enrichment.

    Returns:
        List of processed and enriched chunks
    """
    print(f"\n📂 Processing MD files from: {input_dir}")

    # Initialize processor with enrichment
    processor = MarkdownDocumentProcessor(
        max_chunk_size=2000,
        min_chunk_size=300,
        token_limit=6500,
        enable_enrichment=enable_enrichment,  # Enable enrichment!
    )

    # Find MD files
    md_files = sorted(input_dir.glob("*.md"))

    if not md_files:
        print(f"   ❌ No MD files found in {input_dir}")
        return []

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

            # Parse MD file
            document = processor.parse_md_file(str(md_file))

            # Validate
            if not processor.validate_document(document):
                print(f"   ❌ Validation failed")
                stats["failed"] += 1
                continue

            # Chunk with optimal strategy
            chunks = processor.process_to_chunks(document)
            print(f"   📊 {len(chunks)} chunks created")

            # Validate & Enrich (enrichment happens inside validate_chunks if enabled)
            validated_chunks = processor.validate_chunks(chunks)

            all_chunks.extend(validated_chunks)
            stats["processed"] += 1
            stats["total_chunks"] += len(validated_chunks)

        except Exception as e:
            print(f"   ❌ Error: {e}")
            stats["failed"] += 1

    # Export to JSONL
    if all_chunks:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "processed_chunks.jsonl"

        print(f"\n💾 Exporting {len(all_chunks)} chunks to {output_file}")
        with open(output_file, "w", encoding="utf-8") as f:
            for chunk in all_chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print(f"\n📊 Processing Summary:")
    print(f"   Files processed: {stats['processed']}")
    print(f"   Files failed: {stats['failed']}")
    print(f"   Total chunks: {stats['total_chunks']:,}")

    return all_chunks


def chunk_to_document(chunk: Dict[str, Any]) -> Document:
    """Convert chunk dict to LangChain Document."""

    # Extract text content
    text = chunk.get("text", chunk.get("content", ""))

    # Get metadata
    metadata = chunk.get("metadata", {})

    # Flatten nested structures for PGVector
    for key, value in list(metadata.items()):
        if isinstance(value, (list, dict)):
            metadata[key] = json.dumps(value, ensure_ascii=False)

    return Document(page_content=text, metadata=metadata)


def import_to_database(
    chunks: List[Dict[str, Any]],
    collection_name: str,
    db_url: str,
    embed_model: str,
    batch_size: int = 30,
) -> int:
    """
    Import chunks to PGVector with native 3072-dimensional embeddings.

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
                print(f"\n❌ Error in batch {i//batch_size + 1}: {e}")
                # Continue with next batch
                pbar.update(len(documents))

    return total_imported


def main():
    parser = argparse.ArgumentParser(
        description="Process new MD files and import to database with enrichment"
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing new MD files to process",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed/chunks"),
        help="Output directory for processed chunks",
    )
    parser.add_argument(
        "--no-enrichment", action="store_true", help="Disable enrichment"
    )
    parser.add_argument(
        "--no-import",
        action="store_true",
        help="Process only, don't import to database",
    )
    parser.add_argument("--batch-size", type=int, default=30, help="Import batch size")

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
    print("PROCESS & IMPORT NEW DOCUMENTS PIPELINE")
    print("=" * 80)
    print(f"Input: {input_dir}")
    print(f"Output: {output_dir}")
    print(f"Enrichment: {'❌ Disabled' if args.no_enrichment else '✅ Enabled'}")
    print(f"Import: {'❌ Skipped' if args.no_import else '✅ Enabled'}")
    print(f"Collection: {settings.collection}")
    print(f"Model: {settings.embed_model} @ 3072 dims (native)")

    start_time = time.time()

    # Step 1: Process MD files with enrichment
    chunks = process_new_md_files(
        input_dir, output_dir, enable_enrichment=not args.no_enrichment
    )

    if not chunks:
        print("\n⚠️  No chunks to import!")
        sys.exit(0)

    # Step 2: Import to database
    if args.no_import:
        print("\n🔍 Skipping database import (--no-import flag)")
        imported = 0
    else:
        imported = import_to_database(
            chunks,
            settings.collection,
            settings.database_url,
            settings.embed_model,
            args.batch_size,
        )

    elapsed = time.time() - start_time

    # Summary
    print("\n" + "=" * 80)
    print("PIPELINE COMPLETE")
    print("=" * 80)
    print(f"Chunks processed: {len(chunks):,}")
    print(f"Chunks imported: {imported:,}")
    print(f"Time: {elapsed/60:.1f} minutes")
    print(f"Enrichment: {'✅ Applied' if not args.no_enrichment else '❌ Skipped'}")
    print(f"Output: {output_dir}")

    if imported > 0:
        print("\n✅ New documents successfully added to database!")
        print("\nNext steps:")
        print("  1. Test retrieval: python scripts/test_retrieval.py")
        print("  2. Benchmark: python scripts/benchmark_retrieval.py")


if __name__ == "__main__":
    main()
