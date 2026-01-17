#!/usr/bin/env python3
"""
Re-index Documents for Schema v3

This script:
1. Reads all chunks from data/processed/chunks/
2. Creates/updates Document records in PostgreSQL
3. Creates DocumentChunk records for tracking
4. Generates embeddings using text-embedding-3-small (1536 dim)
5. Stores embeddings in langchain_pg_embedding

Usage:
    python scripts/reindex_documents_v3.py [--clear] [--dry-run] [--limit N]

Options:
    --clear     Clear existing embeddings before re-indexing
    --dry-run   Only show what would be done, don't write
    --limit N   Only process first N documents (for testing)
"""

import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.orm import Session
from langchain_core.documents import Document as LCDocument

from src.models.base import SessionLocal
from src.models.documents import Document
from src.models.document_chunks import DocumentChunk
from src.config.models import settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

CHUNKS_DIR = Path(__file__).parent.parent / "data" / "processed" / "chunks"
METADATA_FILE = (
    Path(__file__).parent.parent / "data" / "processed" / "documents_metadata.json"
)

# Category mapping from document_type
CATEGORY_MAP = {
    "law": "Luật",
    "decree": "Nghị định",
    "circular": "Thông tư",
    "decision": "Quyết định",
    "template": "Mẫu biểu",
    "guidance": "Hướng dẫn",
    "exam": "Câu hỏi thi",
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def load_documents_metadata() -> Dict[str, Any]:
    """Load documents metadata from JSON file and convert to dict by document_id"""
    if not METADATA_FILE.exists():
        logger.warning(f"Metadata file not found: {METADATA_FILE}")
        return {}

    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Convert list to dict keyed by document_id
    if isinstance(data, list):
        return {
            item.get("document_id", f"doc_{i}"): item for i, item in enumerate(data)
        }
    return data


def load_chunks_from_file(chunk_file: Path) -> List[Dict[str, Any]]:
    """Load chunks from a JSONL file"""
    chunks = []
    with open(chunk_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    chunks.append(json.loads(line))
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse line in {chunk_file}: {e}")
    return chunks


def get_or_create_document(
    db: Session,
    doc_id: str,
    chunk_data: Dict[str, Any],
    metadata: Dict[str, Any],
    uploaded_by_id: Optional[Any] = None,
) -> Document:
    """Get existing or create new document record"""
    # Check if document exists
    existing = db.query(Document).filter(Document.document_id == doc_id).first()
    if existing:
        return existing

    # Determine category from document_type
    doc_type = chunk_data.get("document_type", "other")
    category = CATEGORY_MAP.get(doc_type, "Khác")

    # Extract document name from metadata or chunk
    doc_name = (
        metadata.get("title")
        or metadata.get("document_name")
        or doc_id.replace("_", " ").title()
    )

    # Get filename and filepath
    filename = metadata.get("filename") or metadata.get("file_name") or f"{doc_id}.pdf"
    filepath = metadata.get("filepath") or metadata.get("source_file")
    source_file = metadata.get("source_file") or filepath

    # Estimate file_size_bytes from total_chunks if not provided
    total_chunks = chunk_data.get("total_chunks", 0)
    file_size_bytes = metadata.get("file_size_bytes")
    if not file_size_bytes and total_chunks > 0:
        # Estimate: ~1.5KB per chunk, original file ~2.5x larger
        file_size_bytes = int(total_chunks * 1500 * 2.5)
    elif not file_size_bytes:
        file_size_bytes = 50000  # Default 50KB

    # Build metadata dict
    doc_metadata = {
        "document_id": doc_id,
        "document_name": doc_name,
        "document_type": doc_type,
        "category": category,
        "source_file": source_file,
        "total_chunks": total_chunks,
    }
    # Merge any extra metadata
    if metadata.get("extra_metadata"):
        doc_metadata.update(metadata.get("extra_metadata"))

    # Create new document
    doc = Document(
        id=uuid4(),
        document_id=doc_id,
        document_name=doc_name,
        document_type=doc_type,
        category=category,
        status="active",
        filename=filename,
        filepath=filepath,
        source_file=source_file,
        total_chunks=total_chunks,
        file_size_bytes=file_size_bytes,
        uploaded_by=uploaded_by_id,  # Set uploader if provided
        extra_metadata=doc_metadata,
        created_at=datetime.utcnow(),
    )

    db.add(doc)
    db.flush()  # Get the ID without committing

    logger.info(f"  Created document: {doc_id} ({doc_name})")
    return doc


def create_document_chunk(
    db: Session,
    document: Document,
    chunk_data: Dict[str, Any],
    chunk_index: int,
    file_prefix: str = "",
) -> DocumentChunk:
    """Create document chunk record"""
    # Use file_prefix to ensure unique chunk_id across files with same document_id
    original_chunk_id = chunk_data.get(
        "chunk_id", f"{document.document_id}_{chunk_index}"
    )
    unique_chunk_id = (
        f"{file_prefix}_{original_chunk_id}" if file_prefix else original_chunk_id
    )

    chunk = DocumentChunk(
        id=uuid4(),
        document_id=document.id,
        chunk_id=unique_chunk_id,
        content=chunk_data["content"],
        chunk_index=chunk_index,
        section_title=chunk_data.get("section_title"),
        hierarchy_path=chunk_data.get("hierarchy"),
        char_count=chunk_data.get("char_count", len(chunk_data["content"])),
        has_table=chunk_data.get("has_table", False),
        has_list=chunk_data.get("has_list", False),
        keywords=chunk_data.get("extra_metadata", {}).get("keywords"),
        concepts=chunk_data.get("extra_metadata", {}).get("concepts"),
        entities=chunk_data.get("extra_metadata", {}).get("entities"),
    )

    db.add(chunk)
    return chunk


def clear_existing_embeddings(db: Session):
    """Clear all existing embeddings"""
    logger.info("Clearing existing embeddings...")

    # Clear langchain_pg_embedding
    result = db.execute(text("DELETE FROM langchain_pg_embedding"))
    logger.info(f"  Deleted {result.rowcount} embeddings from langchain_pg_embedding")

    # Clear document_chunks
    result = db.execute(text("DELETE FROM document_chunks"))
    logger.info(f"  Deleted {result.rowcount} document chunks")

    # Reset documents (optional - keep if you want to preserve document records)
    # result = db.execute(text("DELETE FROM documents"))
    # logger.info(f"  Deleted {result.rowcount} documents")

    db.commit()
    logger.info("✅ Cleared existing data")


def verify_embedding_model():
    """Verify embedding model is configured correctly"""
    logger.info(f"Embedding model: {settings.embed_model}")

    if "small" not in settings.embed_model.lower():
        logger.warning(
            f"⚠️ Expected text-embedding-3-small but got: {settings.embed_model}"
        )
        logger.warning("   Make sure EMBED_MODEL=text-embedding-3-small in .env")
        return False

    logger.info("✅ Embedding model verified: text-embedding-3-small (1536 dim)")
    return True


# =============================================================================
# MAIN REINDEX FUNCTION
# =============================================================================


def reindex_documents(
    clear: bool = False, dry_run: bool = False, limit: Optional[int] = None
):
    """
    Main re-indexing function

    Args:
        clear: Whether to clear existing embeddings first
        dry_run: If True, only show what would be done
        limit: Limit number of documents to process
    """
    logger.info("=" * 60)
    logger.info("Starting Document Re-indexing for Schema v3")
    logger.info("=" * 60)

    # Verify embedding model
    if not verify_embedding_model():
        if not dry_run:
            logger.error("Aborting due to embedding model mismatch")
            return

    # Load metadata
    metadata = load_documents_metadata()
    logger.info(f"Loaded metadata for {len(metadata)} documents")

    # Get chunk files
    chunk_files = sorted(CHUNKS_DIR.glob("*.jsonl"))
    logger.info(f"Found {len(chunk_files)} chunk files")

    if limit:
        chunk_files = chunk_files[:limit]
        logger.info(f"Processing first {limit} files only")

    if dry_run:
        logger.info("\n[DRY RUN MODE - No changes will be made]\n")

    # Database session
    db = SessionLocal()

    try:
        # Clear existing data if requested
        if clear and not dry_run:
            clear_existing_embeddings(db)

        # Import embedding components (after verification)
        from src.embedding.store.pgvector_store import PGVectorStore

        vector_store = PGVectorStore()

        total_chunks = 0
        total_documents = 0

        for chunk_file in chunk_files:
            doc_name = chunk_file.stem
            logger.info(f"\nProcessing: {doc_name}")

            # Load chunks
            chunks = load_chunks_from_file(chunk_file)
            if not chunks:
                logger.warning(f"  No chunks found in {chunk_file}")
                continue

            # Get document ID from first chunk
            first_chunk = chunks[0]
            doc_id = first_chunk.get("document_id", doc_name)

            # Get metadata for this document
            doc_metadata = metadata.get(doc_id, {})

            if dry_run:
                logger.info(f"  Would create document: {doc_id}")
                logger.info(f"  Would create {len(chunks)} chunks")
                logger.info(f"  Would generate {len(chunks)} embeddings")
                total_chunks += len(chunks)
                total_documents += 1
                continue

            # Create/get document record
            # Use filename as unique identifier when multiple files have same document_id
            file_prefix = doc_name  # Use filename stem as prefix
            document = get_or_create_document(
                db, f"{doc_id}_{file_prefix}", first_chunk, doc_metadata
            )

            # Update total_chunks
            document.total_chunks = len(chunks)

            # Create document chunks and prepare for embedding
            lc_documents = []

            for i, chunk_data in enumerate(chunks):
                # Create chunk record with file prefix for uniqueness
                doc_chunk = create_document_chunk(
                    db, document, chunk_data, i, file_prefix
                )

                # Prepare LangChain document for embedding
                lc_doc = LCDocument(
                    page_content=chunk_data["content"],
                    metadata={
                        "document_id": doc_id,
                        "chunk_id": doc_chunk.chunk_id,
                        "document_type": chunk_data.get("document_type", "other"),
                        "section_title": chunk_data.get("section_title"),
                        "hierarchy": chunk_data.get("hierarchy", []),
                        "chunk_index": i,
                        # Add more metadata as needed for retrieval filtering
                        "category": document.category,
                        "document_name": document.document_name,
                    },
                )
                lc_documents.append(lc_doc)

            # Commit document and chunks
            db.commit()

            # Add to vector store (generates embeddings)
            logger.info(f"  Generating embeddings for {len(lc_documents)} chunks...")
            vector_store.add_documents(lc_documents)

            total_chunks += len(chunks)
            total_documents += 1

            logger.info(f"  ✅ Indexed {len(chunks)} chunks")

        # Final summary
        logger.info("\n" + "=" * 60)
        logger.info("Re-indexing Complete!")
        logger.info("=" * 60)
        logger.info(f"Documents processed: {total_documents}")
        logger.info(f"Chunks indexed: {total_chunks}")

        if not dry_run:
            # Verify counts
            embed_count = db.execute(
                text("SELECT COUNT(*) FROM langchain_pg_embedding")
            ).scalar()
            doc_count = db.execute(text("SELECT COUNT(*) FROM documents")).scalar()
            chunk_count = db.execute(
                text("SELECT COUNT(*) FROM document_chunks")
            ).scalar()

            logger.info(f"\nDatabase state:")
            logger.info(f"  langchain_pg_embedding: {embed_count}")
            logger.info(f"  documents: {doc_count}")
            logger.info(f"  document_chunks: {chunk_count}")

    except Exception as e:
        logger.error(f"Error during re-indexing: {e}")
        db.rollback()
        raise
    finally:
        db.close()


# =============================================================================
# CLI
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Re-index documents for Schema v3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing embeddings before re-indexing",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only show what would be done, don't write",
    )

    parser.add_argument(
        "--limit", type=int, default=None, help="Limit number of documents to process"
    )

    args = parser.parse_args()

    reindex_documents(clear=args.clear, dry_run=args.dry_run, limit=args.limit)


if __name__ == "__main__":
    main()
