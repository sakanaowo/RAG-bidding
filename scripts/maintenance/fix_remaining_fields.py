#!/usr/bin/env python3
"""
Fix remaining NULL fields in documents table:
- file_size_bytes: Estimate from total_chunks and average chunk size
- metadata: Populate from chunk metadata
- uploaded_by: Set to system user for batch-imported docs

Usage:
    python scripts/maintenance/fix_remaining_fields.py --dry-run
    python scripts/maintenance/fix_remaining_fields.py --apply
"""

import sys
import json
import argparse
import logging
from pathlib import Path
from uuid import UUID
from typing import Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text
from sqlalchemy.orm import Session
from src.models.base import SessionLocal
from src.models.documents import Document
from src.models.users import User

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# Average bytes per chunk (estimated from typical document content)
AVG_BYTES_PER_CHUNK = 1500  # ~1.5KB average


def get_or_create_system_user(db: Session) -> Optional[UUID]:
    """Get or create a system user for batch-imported documents"""
    system_user = db.query(User).filter(User.username == "system").first()

    if not system_user:
        # Check if any admin user exists
        admin_user = db.query(User).filter(User.role == "admin").first()
        if admin_user:
            return admin_user.id

        # No users at all - return None
        logger.warning("No users found in database, skipping uploaded_by")
        return None

    return system_user.id


def estimate_file_size(total_chunks: int) -> int:
    """Estimate file size based on number of chunks"""
    if not total_chunks or total_chunks <= 0:
        return 50000  # Default 50KB

    # Estimate: each chunk ~1.5KB of text content
    # Original file likely 2-3x larger due to formatting, images, etc.
    estimated_size = total_chunks * AVG_BYTES_PER_CHUNK * 2.5
    return int(estimated_size)


def build_metadata_from_document(doc: Document) -> Dict[str, Any]:
    """Build metadata dict from document fields"""
    metadata = {
        "document_id": doc.document_id,
        "document_name": doc.document_name,
        "document_type": doc.document_type,
        "category": doc.category,
        "source_file": doc.source_file,
        "total_chunks": doc.total_chunks,
    }

    # Add any existing extra_metadata
    if doc.extra_metadata and isinstance(doc.extra_metadata, dict):
        metadata.update(doc.extra_metadata)

    return metadata


def fix_fields(dry_run: bool = True):
    """Fix file_size_bytes, metadata, and uploaded_by fields"""
    db = SessionLocal()

    try:
        # Get system user for uploaded_by
        system_user_id = get_or_create_system_user(db)

        # Get all documents
        documents = db.query(Document).all()

        logger.info(f"Processing {len(documents)} documents...")
        logger.info(f"Dry run: {dry_run}")

        stats = {
            "file_size_updated": 0,
            "metadata_updated": 0,
            "uploaded_by_updated": 0,
            "errors": 0,
        }

        for doc in documents:
            changes = []

            try:
                # 1. Fix file_size_bytes if NULL
                if doc.file_size_bytes is None:
                    estimated_size = estimate_file_size(doc.total_chunks)
                    if not dry_run:
                        doc.file_size_bytes = estimated_size
                    changes.append(f"file_size_bytes: NULL → {estimated_size:,}")
                    stats["file_size_updated"] += 1

                # 2. Fix metadata if NULL or empty
                current_meta = doc.extra_metadata
                if current_meta is None or current_meta == {} or current_meta == "{}":
                    new_metadata = build_metadata_from_document(doc)
                    if not dry_run:
                        doc.extra_metadata = new_metadata
                    changes.append(f"metadata: empty → populated")
                    stats["metadata_updated"] += 1

                # 3. Fix uploaded_by if NULL and we have a system user
                if doc.uploaded_by is None and system_user_id:
                    if not dry_run:
                        doc.uploaded_by = system_user_id
                    changes.append(f"uploaded_by: NULL → {str(system_user_id)[:8]}...")
                    stats["uploaded_by_updated"] += 1

                # Log changes
                if changes:
                    logger.info(f"\n  📄 {doc.document_id}")
                    for change in changes:
                        logger.info(f"      {change}")

            except Exception as e:
                logger.error(f"Error processing {doc.document_id}: {e}")
                stats["errors"] += 1

        # Commit if not dry run
        if not dry_run:
            db.commit()
            logger.info("\n✅ Changes committed to database")
        else:
            logger.info("\n💡 Dry run - no changes made. Use --apply to apply changes.")

        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("SUMMARY")
        logger.info("=" * 60)
        logger.info(f"  file_size_bytes updated: {stats['file_size_updated']}")
        logger.info(f"  metadata updated:        {stats['metadata_updated']}")
        logger.info(f"  uploaded_by updated:     {stats['uploaded_by_updated']}")
        logger.info(f"  errors:                  {stats['errors']}")

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Fix remaining NULL fields in documents"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Only show what would be done"
    )
    parser.add_argument("--apply", action="store_true", help="Actually apply changes")

    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("Please specify --dry-run or --apply")
        sys.exit(1)

    dry_run = not args.apply
    fix_fields(dry_run=dry_run)


if __name__ == "__main__":
    main()
