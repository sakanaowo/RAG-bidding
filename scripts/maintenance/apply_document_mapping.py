#!/usr/bin/env python3
"""
Apply Document Name Mapping - Fix document metadata using the data map

This script applies the manual document name mapping to fix:
1. document_name: Replace auto-generated names with correct titles
2. document_id: Replace "untitled" patterns with proper IDs
3. document_type: Fix file extension as type
4. category: Correct category based on document type

Usage:
    # Dry run - see what would change
    python scripts/maintenance/apply_document_mapping.py --dry-run

    # Apply changes
    python scripts/maintenance/apply_document_mapping.py --apply

    # Apply to specific documents
    python scripts/maintenance/apply_document_mapping.py --apply --ids "uuid1,uuid2"

Author: RAG Bidding Team
Date: 2026-01-11
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import Session
from src.models.base import SessionLocal
from src.models.documents import Document

from document_name_mapping import DOCUMENT_NAME_MAP, get_document_metadata

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def apply_mapping(
    db: Session, doc_ids: Optional[List[str]] = None, dry_run: bool = True
) -> dict:
    """
    Apply document name mapping to database.

    Args:
        db: Database session
        doc_ids: Optional list of specific document IDs to update. If None, updates all mapped docs.
        dry_run: If True, don't commit changes

    Returns:
        Dictionary with statistics
    """
    results = {
        "total_processed": 0,
        "updated": 0,
        "skipped_not_found": 0,
        "skipped_no_change": 0,
        "errors": [],
        "changes": [],
    }

    # Get documents to process
    if doc_ids:
        target_ids = doc_ids
    else:
        target_ids = list(DOCUMENT_NAME_MAP.keys())

    logger.info(f"Processing {len(target_ids)} documents...")
    logger.info(f"Dry run: {dry_run}")
    logger.info("=" * 60)

    for doc_uuid in target_ids:
        results["total_processed"] += 1

        # Get mapping
        mapping = get_document_metadata(doc_uuid)
        if not mapping:
            logger.warning(f"  {doc_uuid}: No mapping found, skipping")
            results["skipped_not_found"] += 1
            continue

        # Get document from database
        doc = db.query(Document).filter(Document.id == doc_uuid).first()
        if not doc:
            logger.warning(f"  {doc_uuid}: Document not found in database")
            results["skipped_not_found"] += 1
            continue

        # Check what needs to change
        changes = []

        # Check document_name
        new_name = mapping.get("document_name")
        if new_name and doc.document_name != new_name:
            changes.append(("document_name", doc.document_name, new_name))

        # Check document_id
        new_doc_id = mapping.get("document_id")
        if new_doc_id and doc.document_id != new_doc_id:
            changes.append(("document_id", doc.document_id, new_doc_id))

        # Check document_type
        new_type = mapping.get("document_type")
        if new_type and doc.document_type != new_type:
            changes.append(("document_type", doc.document_type, new_type))

        # Check category
        new_category = mapping.get("category")
        if new_category and doc.category != new_category:
            changes.append(("category", doc.category, new_category))

        # Check filename
        new_filename = mapping.get("filename")
        if new_filename and doc.filename != new_filename:
            changes.append(("filename", doc.filename, new_filename))

        # Check source_file - derive from filename if not set
        if doc.source_file is None or doc.source_file == "None":
            # Try to derive source_file
            if new_filename:
                new_source = f"data/raw/{new_filename}"
            elif mapping.get("document_type") and mapping.get("document_id"):
                new_source = (
                    f"data/raw/{mapping['document_type']}/{mapping['document_id']}.pdf"
                )
            else:
                new_source = None

            if new_source:
                changes.append(("source_file", doc.source_file, new_source))

        if not changes:
            results["skipped_no_change"] += 1
            continue

        # Log changes
        logger.info(f"\n  📄 {doc_uuid}")
        for field, old_val, new_val in changes:
            old_display = (
                (old_val[:40] + "...") if old_val and len(old_val) > 40 else old_val
            )
            new_display = (
                (new_val[:40] + "...") if new_val and len(new_val) > 40 else new_val
            )
            logger.info(f"     {field}: '{old_display}' → '{new_display}'")

        results["changes"].append({"id": doc_uuid, "changes": changes})

        # Apply changes if not dry run
        if not dry_run:
            try:
                for field, old_val, new_val in changes:
                    if field == "document_name":
                        doc.document_name = new_val
                    elif field == "document_id":
                        doc.document_id = new_val
                    elif field == "document_type":
                        doc.document_type = new_val
                    elif field == "category":
                        doc.category = new_val
                    elif field == "filename":
                        doc.filename = new_val
                    elif field == "source_file":
                        doc.source_file = new_val

                results["updated"] += 1
            except Exception as e:
                logger.error(f"     ERROR: {str(e)}")
                results["errors"].append({"id": doc_uuid, "error": str(e)})

    # Commit if not dry run
    if not dry_run and results["updated"] > 0:
        try:
            db.commit()
            logger.info(f"\n✅ Committed {results['updated']} changes to database")
        except Exception as e:
            db.rollback()
            logger.error(f"\n❌ Failed to commit: {str(e)}")
            results["errors"].append({"commit_error": str(e)})

    return results


def print_summary(results: dict):
    """Print summary of results."""
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"  Total processed:    {results['total_processed']}")
    logger.info(f"  Updated:            {results['updated']}")
    logger.info(f"  Would update:       {len(results['changes'])}")
    logger.info(f"  Skipped (no map):   {results['skipped_not_found']}")
    logger.info(f"  Skipped (no change):{results['skipped_no_change']}")
    logger.info(f"  Errors:             {len(results['errors'])}")


def main():
    parser = argparse.ArgumentParser(
        description="Apply document name mapping to fix metadata"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would change without applying"
    )
    parser.add_argument(
        "--apply", action="store_true", help="Apply changes to database"
    )
    parser.add_argument(
        "--ids", type=str, help="Comma-separated list of document UUIDs to update"
    )

    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        parser.print_help()
        print("\nError: Specify either --dry-run or --apply")
        return 1

    # Parse IDs if provided
    doc_ids = None
    if args.ids:
        doc_ids = [id.strip() for id in args.ids.split(",")]

    # Run
    db = SessionLocal()
    try:
        results = apply_mapping(db=db, doc_ids=doc_ids, dry_run=not args.apply)
        print_summary(results)

        if args.dry_run:
            logger.info("\n💡 Run with --apply to make these changes")

        return 0 if not results["errors"] else 1

    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
