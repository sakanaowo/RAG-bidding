"""
Script migration Document IDs - Option 4 (Hybrid System)

Chuyển đổi document_id hiện tại sang format mới:
{type_code}-{số_hiệu}/{năm}#{hash_short}

Ví dụ:
- bidding_untitled → FORM-Bidding/2024#7c4e1a
- circular_untitled → TT-Unknown/2024#3f8a9c
- decree_untitled → ND-Unknown/2024#5b2d7e
"""

import psycopg
import json
import hashlib
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.models import settings


def extract_metadata_from_old_id(old_id: str, metadata: dict) -> dict:
    """Extract hoặc infer metadata từ old_id và cmetadata"""

    # Lấy document_type từ metadata hoặc old_id
    doc_type = metadata.get("document_type")
    if not doc_type and old_id:
        if "bidding" in old_id.lower():
            doc_type = "bidding"
        elif "circular" in old_id.lower():
            doc_type = "circular"
        elif "decree" in old_id.lower():
            doc_type = "decree"
        elif "law" in old_id.lower():
            doc_type = "law"
        elif "exam" in old_id.lower():
            doc_type = "exam"
        elif "report" in old_id.lower():
            doc_type = "report"
        else:
            doc_type = "document"

    # Lấy year từ metadata hoặc timestamp
    year = metadata.get("year")
    if not year and metadata.get("processing_metadata"):
        processed_at = metadata["processing_metadata"].get("last_processed_at", "")
        if processed_at:
            year = processed_at[:4]
    if not year:
        year = "2024"

    # Lấy number từ document_id nếu có
    number = metadata.get("number")
    if not number:
        # Try extract từ old_id
        import re

        match = re.search(r"(\d+)", old_id)
        if match:
            number = match.group(1)
        else:
            # Dùng type name thay vì "Unknown"
            number = doc_type.title()

    return {"type": doc_type or "doc", "year": year, "number": number}


def generate_new_document_id(old_id: str, metadata: dict) -> str:
    """
    Generate new document_id theo Hybrid System

    Format: {type_code}-{number}/{year}#{hash_short}
    """

    extracted = extract_metadata_from_old_id(old_id, metadata)
    doc_type = extracted["type"]
    year = extracted["year"]
    number = extracted["number"]

    # Type code mapping
    type_code_map = {
        "law": "LAW",
        "decree": "ND",
        "circular": "TT",
        "decision": "QD",
        "bidding": "FORM",
        "report": "RPT",
        "exam": "EXAM",
        "document": "DOC",
    }

    type_code = type_code_map.get(doc_type, "DOC")

    # Generate hash từ old_id để đảm bảo uniqueness và idempotent
    hash_obj = hashlib.md5(old_id.encode())
    hash_short = hash_obj.hexdigest()[:6]

    new_id = f"{type_code}-{number}/{year}#{hash_short}"

    return new_id


def preview_migration():
    """
    Preview migration - Show what will be changed
    """
    print("=" * 80)
    print("📋 PREVIEW MIGRATION - Document ID Changes")
    print("=" * 80)
    print()

    db_url = settings.database_url.replace("postgresql+psycopg", "postgresql")

    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            # Lấy danh sách unique document_ids
            cur.execute(
                """
                SELECT DISTINCT cmetadata->>'document_id' as old_id
                FROM langchain_pg_embedding
                WHERE cmetadata->>'document_id' IS NOT NULL
                ORDER BY old_id
            """
            )

            unique_docs = [row[0] for row in cur.fetchall()]

            print(f"Found {len(unique_docs)} unique documents\n")

            migration_map = {}
            total_chunks = 0

            for idx, old_id in enumerate(unique_docs, 1):
                # Lấy metadata từ một chunk
                cur.execute(
                    """
                    SELECT cmetadata
                    FROM langchain_pg_embedding
                    WHERE cmetadata->>'document_id' = %s
                    LIMIT 1
                """,
                    (old_id,),
                )

                metadata = cur.fetchone()[0]
                new_id = generate_new_document_id(old_id, metadata)

                migration_map[old_id] = new_id

                # Count chunks
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM langchain_pg_embedding
                    WHERE cmetadata->>'document_id' = %s
                """,
                    (old_id,),
                )

                chunk_count = cur.fetchone()[0]
                total_chunks += chunk_count

                doc_type = metadata.get("document_type", "unknown")

                print(
                    f"{idx:3d}. [{doc_type:10s}] {old_id:40s} → {new_id:35s} ({chunk_count:5d} chunks)"
                )

            print()
            print("=" * 80)
            print(f"📊 Summary:")
            print(f"   - Total documents: {len(migration_map)}")
            print(f"   - Total chunks: {total_chunks}")
            print("=" * 80)

            return migration_map


def execute_migration(dry_run=True):
    """
    Execute migration

    Args:
        dry_run: If True, only preview, don't actually update
    """

    if dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made")
        print(
            "To execute migration, run: python scripts/migrate_document_ids.py --execute\n"
        )
        migration_map = preview_migration()
        return migration_map

    print()
    print("=" * 80)
    print("🚀 EXECUTING MIGRATION - This will update the database")
    print("=" * 80)
    print()

    # Show preview first
    migration_map = preview_migration()

    # Confirm
    print()
    response = input("⚠️  Proceed with migration? (yes/no): ")
    if response.lower() != "yes":
        print("❌ Migration cancelled")
        return {}

    print()
    print("🔄 Starting migration...")

    db_url = settings.database_url.replace("postgresql+psycopg", "postgresql")

    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            total_updated = 0

            for idx, (old_id, new_id) in enumerate(migration_map.items(), 1):
                # Update tất cả chunks của document này
                cur.execute(
                    """
                    UPDATE langchain_pg_embedding
                    SET cmetadata = jsonb_set(
                        cmetadata,
                        '{document_id}',
                        to_jsonb(%s::text)
                    )
                    WHERE cmetadata->>'document_id' = %s
                """,
                    (new_id, old_id),
                )

                updated_count = cur.rowcount
                total_updated += updated_count

                print(
                    f"   [{idx}/{len(migration_map)}] Updated {old_id} → {new_id} ({updated_count} chunks)"
                )

            # Commit all changes
            conn.commit()

            print()
            print("=" * 80)
            print("✅ Migration completed successfully!")
            print(f"   - Documents migrated: {len(migration_map)}")
            print(f"   - Chunks updated: {total_updated}")
            print("=" * 80)

            return migration_map


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate document IDs to new format")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute migration (default is dry-run preview)",
    )

    args = parser.parse_args()

    try:
        execute_migration(dry_run=not args.execute)
    except KeyboardInterrupt:
        print("\n\n❌ Migration cancelled by user")
    except Exception as e:
        print(f"\n\n❌ Error during migration: {e}")
        import traceback

        traceback.print_exc()
