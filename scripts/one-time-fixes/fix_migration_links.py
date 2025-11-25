#!/usr/bin/env python3
"""
Fix Migration Links - Backfill documents table and fix inconsistencies

Issues to fix:
1. bidding_untitled (767 chunks) - Old format, needs proper document_id
2. FORM-Bidding/2025#bee720 (3 chunks) - Missing in documents table
3. 4 exam documents with 0 chunks - Either delete or mark as pending

Run with: python scripts/fix_migration_links.py --dry-run
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import psycopg2
import argparse
import json
from datetime import datetime
from typing import Dict, List, Any
from tabulate import tabulate


# Database config
DB_CONFIG = {
    "host": "localhost",
    "database": "rag_bidding_v2",
    "user": "sakana",
    "password": "sakana123",
}


def get_connection():
    """Get database connection."""
    return psycopg2.connect(**DB_CONFIG)


def print_section(title: str):
    """Print formatted section header."""
    print("\n" + "=" * 80)
    print(f"📊 {title}")
    print("=" * 80 + "\n")


def determine_category(doc_type: str) -> str:
    """Determine document category from type."""
    mapping = {
        "law": "Luật chính",
        "decree": "Nghị định",
        "circular": "Thông tư",
        "decision": "Quyết định",
        "bidding": "Hồ sơ mời thầu",
        "template": "Mẫu báo cáo",
        "exam": "Câu hỏi thi",
    }
    return mapping.get(doc_type, "Khác")


def analyze_missing_documents(conn) -> List[Dict]:
    """Find documents in vector DB but not in documents table."""
    print_section("Analyzing Missing Documents")

    cursor = conn.cursor()

    query = """
    WITH vector_docs AS (
        SELECT 
            cmetadata->>'document_id' as document_id,
            cmetadata->>'document_type' as document_type,
            cmetadata->>'title' as title,
            cmetadata->>'source_file' as source_file,
            COUNT(*) as total_chunks
        FROM langchain_pg_embedding
        GROUP BY 
            cmetadata->>'document_id',
            cmetadata->>'document_type',
            cmetadata->>'title',
            cmetadata->>'source_file'
    )
    SELECT v.*
    FROM vector_docs v
    LEFT JOIN documents d ON v.document_id = d.document_id
    WHERE d.document_id IS NULL;
    """

    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]

    if results:
        print(
            f"⚠️ Found {len(results)} documents in vector DB but NOT in documents table:\n"
        )

        table_data = []
        for doc in results:
            table_data.append(
                [
                    doc["document_id"],
                    doc["document_type"] or "unknown",
                    doc["total_chunks"],
                    (doc["title"] or doc["document_id"])[:50],
                ]
            )

        print(
            tabulate(
                table_data,
                headers=["Document ID", "Type", "Chunks", "Title"],
                tablefmt="grid",
            )
        )
    else:
        print("✅ All documents in vector DB exist in documents table")

    return results


def analyze_zero_chunk_documents(conn) -> List[Dict]:
    """Find documents with 0 chunks."""
    print_section("Analyzing Zero-Chunk Documents")

    cursor = conn.cursor()

    query = """
    SELECT 
        document_id,
        document_name,
        document_type,
        category,
        status,
        source_file,
        created_at
    FROM documents
    WHERE total_chunks = 0;
    """

    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]

    if results:
        print(f"⚠️ Found {len(results)} documents with 0 chunks:\n")

        table_data = []
        for doc in results:
            table_data.append(
                [
                    doc["document_id"],
                    doc["document_type"],
                    doc["status"],
                    doc["source_file"] or "N/A",
                ]
            )

        print(
            tabulate(
                table_data,
                headers=["Document ID", "Type", "Status", "Source File"],
                tablefmt="grid",
            )
        )
    else:
        print("✅ All documents have chunks")

    return results


def analyze_old_format_chunks(conn) -> Dict[str, int]:
    """Find chunks with old format document_id."""
    print_section("Analyzing Old Format Chunks")

    cursor = conn.cursor()

    query = """
    SELECT 
        cmetadata->>'document_id' as document_id,
        COUNT(*) as chunk_count
    FROM langchain_pg_embedding
    WHERE cmetadata->>'document_id' LIKE '%untitled%'
    GROUP BY cmetadata->>'document_id'
    ORDER BY chunk_count DESC;
    """

    cursor.execute(query)
    results = {row[0]: row[1] for row in cursor.fetchall()}

    if results:
        print(f"⚠️ Found {sum(results.values())} chunks with old format:\n")

        for doc_id, count in results.items():
            print(f"   - {doc_id}: {count} chunks")
    else:
        print("✅ No old format chunks found")

    return results


def backfill_missing_documents(conn, missing_docs: List[Dict], dry_run: bool = True):
    """Backfill documents table with missing documents."""
    print_section("Backfilling Missing Documents")

    if not missing_docs:
        print("✅ No missing documents to backfill")
        return

    cursor = conn.cursor()

    insert_query = """
    INSERT INTO documents (
        document_id,
        document_name,
        document_type,
        category,
        total_chunks,
        status,
        source_file,
        created_at,
        updated_at
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
    ON CONFLICT (document_id) DO UPDATE SET
        total_chunks = EXCLUDED.total_chunks,
        updated_at = NOW();
    """

    for doc in missing_docs:
        doc_id = doc["document_id"]
        doc_type = doc["document_type"] or "unknown"
        title = doc["title"] or doc_id
        source_file = doc["source_file"]
        chunks = doc["total_chunks"]

        category = determine_category(doc_type)

        print(f"\n{'[DRY RUN] ' if dry_run else ''}Inserting: {doc_id}")
        print(f"   - Type: {doc_type}")
        print(f"   - Category: {category}")
        print(f"   - Chunks: {chunks}")
        print(f"   - Title: {title[:60]}...")

        if not dry_run:
            cursor.execute(
                insert_query,
                (
                    doc_id,
                    title[:200],  # Truncate if too long
                    doc_type,
                    category,
                    chunks,
                    "active",
                    source_file,
                ),
            )

    if not dry_run:
        conn.commit()
        print(f"\n✅ Backfilled {len(missing_docs)} documents")
    else:
        print(f"\n🔍 DRY RUN: Would backfill {len(missing_docs)} documents")


def handle_zero_chunk_documents(
    conn,
    zero_chunk_docs: List[Dict],
    action: str = "mark_pending",
    dry_run: bool = True,
):
    """
    Handle documents with 0 chunks.

    Actions:
    - 'mark_pending': Update status to 'pending'
    - 'delete': Delete from documents table
    """
    print_section(f"Handling Zero-Chunk Documents ({action})")

    if not zero_chunk_docs:
        print("✅ No zero-chunk documents to handle")
        return

    cursor = conn.cursor()
    doc_ids = [doc["document_id"] for doc in zero_chunk_docs]

    if action == "mark_pending":
        query = """
        UPDATE documents
        SET status = 'pending', updated_at = NOW()
        WHERE document_id = ANY(%s);
        """

        print(
            f"{'[DRY RUN] ' if dry_run else ''}Marking {len(doc_ids)} documents as pending..."
        )

        if not dry_run:
            cursor.execute(query, (doc_ids,))
            conn.commit()
            print(f"✅ Marked {len(doc_ids)} documents as pending")
        else:
            print(f"🔍 DRY RUN: Would mark {len(doc_ids)} documents as pending")

    elif action == "delete":
        query = "DELETE FROM documents WHERE document_id = ANY(%s);"

        print(
            f"⚠️ {'[DRY RUN] ' if dry_run else ''}Deleting {len(doc_ids)} documents..."
        )

        if not dry_run:
            cursor.execute(query, (doc_ids,))
            conn.commit()
            print(f"✅ Deleted {len(doc_ids)} documents")
        else:
            print(f"🔍 DRY RUN: Would delete {len(doc_ids)} documents")

    else:
        print(f"❌ Unknown action: {action}")


def fix_old_format_chunks(conn, old_format_docs: Dict[str, int], dry_run: bool = True):
    """
    Fix old format chunks by updating document_id.

    NOTE: This requires manual mapping of old IDs to new IDs!
    """
    print_section("Fixing Old Format Chunks")

    if not old_format_docs:
        print("✅ No old format chunks to fix")
        return

    print("⚠️ WARNING: This requires manual mapping!")
    print("   Please inspect the chunks and determine proper document_id\n")

    cursor = conn.cursor()

    # For bidding_untitled, we need to determine the proper ID
    if "bidding_untitled" in old_format_docs:
        print("📋 bidding_untitled analysis:\n")

        # Get sample chunks to understand content
        query = """
        SELECT 
            cmetadata->>'title' as title,
            cmetadata->>'source_file' as source_file,
            cmetadata->>'document_type' as doc_type,
            LEFT(document, 100) as content_preview
        FROM langchain_pg_embedding
        WHERE cmetadata->>'document_id' = 'bidding_untitled'
        LIMIT 5;
        """

        cursor.execute(query)
        results = cursor.fetchall()

        for idx, row in enumerate(results, 1):
            print(f"Sample {idx}:")
            print(f"   Title: {row[0]}")
            print(f"   Source: {row[1]}")
            print(f"   Type: {row[2]}")
            print(f"   Content: {row[3]}...")
            print()

        print("💡 Options:")
        print("   1. Update to proper FORM-* ID (requires manual decision)")
        print("   2. Delete if not needed")
        print("   3. Skip for now")
        print("\n⏸️  Skipping automatic fix - manual intervention required")


def verify_consistency(conn):
    """Verify final consistency between tables."""
    print_section("Verifying Consistency")

    cursor = conn.cursor()

    # Check document counts
    query = """
    SELECT 
        (SELECT COUNT(DISTINCT cmetadata->>'document_id') FROM langchain_pg_embedding) as vector_db_docs,
        (SELECT COUNT(*) FROM documents) as documents_table_docs,
        (SELECT COUNT(*) FROM documents WHERE total_chunks = 0) as zero_chunk_docs;
    """

    cursor.execute(query)
    result = cursor.fetchone()

    vector_docs, table_docs, zero_docs = result

    print(f"📊 Document Counts:")
    print(f"   Vector DB: {vector_docs}")
    print(f"   Documents table: {table_docs}")
    print(f"   Zero-chunk docs: {zero_docs}")

    if vector_docs == table_docs - zero_docs:
        print("\n✅ Consistency check PASSED")
    else:
        print(
            f"\n⚠️ Inconsistency: {abs(vector_docs - (table_docs - zero_docs))} documents mismatch"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Fix migration links and inconsistencies"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--backfill", action="store_true", help="Backfill missing documents"
    )
    parser.add_argument(
        "--handle-zero-chunks",
        choices=["mark_pending", "delete"],
        help="How to handle zero-chunk documents",
    )
    parser.add_argument(
        "--fix-old-format",
        action="store_true",
        help="Attempt to fix old format chunks (requires manual input)",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("🔧 Fix Migration Links")
    print("=" * 80)

    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made\n")

    conn = get_connection()

    try:
        # Step 1: Analyze issues
        missing_docs = analyze_missing_documents(conn)
        zero_chunk_docs = analyze_zero_chunk_documents(conn)
        old_format_docs = analyze_old_format_chunks(conn)

        # Step 2: Fix issues (if requested)
        if args.backfill and missing_docs:
            backfill_missing_documents(conn, missing_docs, dry_run=args.dry_run)

        if args.handle_zero_chunks and zero_chunk_docs:
            handle_zero_chunk_documents(
                conn,
                zero_chunk_docs,
                action=args.handle_zero_chunks,
                dry_run=args.dry_run,
            )

        if args.fix_old_format and old_format_docs:
            fix_old_format_chunks(conn, old_format_docs, dry_run=args.dry_run)

        # Step 3: Verify
        if not args.dry_run:
            verify_consistency(conn)

        print("\n" + "=" * 80)
        print("✅ Analysis complete")
        print("=" * 80)

        if args.dry_run:
            print("\n💡 To apply fixes, run without --dry-run:")
            print(
                "   python scripts/fix_migration_links.py --backfill --handle-zero-chunks mark_pending"
            )

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        conn.rollback()

    finally:
        conn.close()


if __name__ == "__main__":
    main()
