#!/usr/bin/env python3
"""
Build document_id -> document_name mapping từ metadata files và database.

Vì database đã được migrate với document_id mới (có hash), nhưng metadata
files vẫn dùng tên cũ, script này sẽ:
1. Scan tất cả chunks trong database để lấy REAL document_ids
2. Map chunks về source files dựa trên chunk_id pattern
3. Tạo mapping từ real document_id -> document_name

Usage:
    python scripts/build_document_name_mapping.py
"""

import json
import glob
import asyncio
from pathlib import Path
from sqlalchemy import text
import sys
import os

# Add parent directory to path để import được src modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.database import get_db, init_database


async def build_mapping():
    """Build document_id -> document_name mapping từ database"""
    mapping = {}
    processed_count = 0
    skipped_count = 0

    print("🔍 Connecting to database...")

    # Initialize database connection (sync function)
    init_database()

    # Build metadata lookup: chunk_id_pattern -> metadata
    print("📁 Loading metadata files...")
    metadata_lookup = {}
    for meta_file in sorted(glob.glob("data/processed/metadata/*.json")):
        try:
            with open(meta_file, encoding="utf-8") as f:
                meta = json.load(f)

            source_file = meta.get("source_file", "")
            if not source_file:
                continue

            # Extract document name
            doc_name = Path(source_file).stem
            meta_basename = Path(meta_file).stem

            # Store by metadata basename for lookup
            metadata_lookup[meta_basename] = {
                "name": doc_name,
                "category": meta.get("category", ""),
                "source_file": source_file,
                "document_type": meta.get("document_type", ""),
            }
        except Exception as e:
            print(f"⚠️  Error reading {meta_file}: {e}")

    print(f"✅ Loaded {len(metadata_lookup)} metadata files")
    print("\n🔍 Querying database for document IDs...")

    # Query database for all unique document_ids with sample chunk_id
    async for db in get_db():
        try:
            result = await db.execute(
                text(
                    """
                    SELECT DISTINCT ON (cmetadata->>'document_id')
                        cmetadata->>'document_id' as doc_id,
                        cmetadata->>'chunk_id' as chunk_id,
                        cmetadata->>'document_type' as doc_type,
                        (cmetadata->'total_chunks')::int as total_chunks
                    FROM langchain_pg_embedding
                    WHERE cmetadata->>'document_id' IS NOT NULL
                    ORDER BY cmetadata->>'document_id', id
                """
                )
            )

            documents = result.fetchall()
            print(f"📊 Found {len(documents)} unique documents in database\n")

            # Match each document with metadata
            for row in documents:
                doc_id, chunk_id, doc_type, total_chunks = row

                # Extract pattern from chunk_id to match metadata
                # chunk_id format: "{type}_{doc_pattern}_{section}_{index}"
                # Example: "bidding_untitled_form_0102"

                # Try to find matching metadata by searching chunk files
                matched_meta = None

                # Search all chunk files for this document_id
                for chunk_file in glob.glob("data/processed/chunks/*.jsonl"):
                    try:
                        with open(chunk_file, encoding="utf-8") as cf:
                            first_line = cf.readline().strip()
                            if first_line:
                                first_chunk = json.loads(first_line)
                                if first_chunk.get("document_id") == doc_id:
                                    # Found matching chunk file!
                                    meta_basename = Path(chunk_file).stem
                                    if meta_basename in metadata_lookup:
                                        matched_meta = metadata_lookup[meta_basename]
                                        break
                    except:
                        continue

                if matched_meta:
                    mapping[doc_id] = {
                        "name": matched_meta["name"],
                        "category": matched_meta["category"],
                        "source_file": matched_meta["source_file"],
                        "document_type": doc_type or matched_meta["document_type"],
                        "total_chunks": total_chunks or 0,
                    }
                    processed_count += 1
                    print(f"✅ {doc_id[:30]:30} → {matched_meta['name'][:60]}")
                else:
                    # Fallback: use chunk_id as name
                    mapping[doc_id] = {
                        "name": chunk_id.replace("_", " ").title(),
                        "category": "Unknown",
                        "source_file": "",
                        "document_type": doc_type or "unknown",
                        "total_chunks": total_chunks or 0,
                    }
                    skipped_count += 1
                    print(f"⚠️  {doc_id[:30]:30} → No metadata (using chunk_id)")

            break  # Only need one session

        except Exception as e:
            print(f"❌ Database error: {e}")
            raise

    # Save mapping
    output_file = Path("src/config/document_name_mapping.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print(f"🎉 Mapping created successfully!")
    print(f"📊 Stats:")
    print(f"   - Processed: {processed_count} documents")
    print(f"   - Fallback:  {skipped_count} documents")
    print(f"   - Total:     {len(mapping)} documents")
    print(f"   - Output:    {output_file}")
    print("=" * 80)

    return mapping


if __name__ == "__main__":
    asyncio.run(build_mapping())
