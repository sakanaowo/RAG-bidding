"""
Document Management API - Document-level operations (not chunk-level)

Endpoints for managing DOCUMENTS (aggregated from chunks):
- GET /documents/catalog - List unique documents (grouped by document_id)
- GET /documents/catalog/{document_id} - Get full document with all chunks
- PATCH /documents/catalog/{document_id}/status - Update document status
- GET /documents/catalog/{document_id}/stats - Get document statistics

This is different from /documents which returns individual CHUNKS.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import json
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db

logger = logging.getLogger(__name__)

# Load document name mapping
MAPPING_FILE = (
    Path(__file__).parent.parent.parent / "config" / "document_name_mapping.json"
)
DOCUMENT_NAME_MAPPING = {}

try:
    with open(MAPPING_FILE, encoding="utf-8") as f:
        DOCUMENT_NAME_MAPPING = json.load(f)
    logger.info(
        f"✅ Loaded document name mapping: {len(DOCUMENT_NAME_MAPPING)} documents"
    )
except FileNotFoundError:
    logger.warning(f"⚠️  Document name mapping not found at {MAPPING_FILE}")
except Exception as e:
    logger.error(f"❌ Error loading document name mapping: {e}")

router = APIRouter(prefix="/documents", tags=["Documents"])


# ===== MODELS =====


class DocumentMetadata(BaseModel):
    """Document metadata from documents table."""

    document_id: str = Field(..., description="Unique document identifier")
    document_name: Optional[str] = Field(None, description="Document name/title")
    document_type: str = Field(..., description="Type: law, decree, bidding, etc.")
    category: Optional[str] = Field(None, description="Category classification")
    filename: Optional[str] = Field(None, description="Original file name")
    total_chunks: int = Field(0, description="Number of chunks")
    status: str = Field("active", description="Document status: active, archived, etc.")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class DocumentSummary(BaseModel):
    """Summary of a complete document (aggregated from chunks)."""

    document_id: str = Field(..., description="Unique document identifier")
    title: str = Field(..., description="Document title from first chunk")
    document_type: str = Field(..., description="Type: law, decree, bidding, etc.")
    total_chunks: int = Field(..., description="Number of chunks in document")
    status: Optional[str] = Field(None, description="Current document status")
    published_date: Optional[str] = None
    effective_date: Optional[str] = None
    last_modified: Optional[str] = None
    hierarchy_path: Optional[List[str]] = Field(
        None, description="Full hierarchy from metadata"
    )
    chunk_ids: List[str] = Field(..., description="List of all chunk IDs in document")


class DocumentDetail(BaseModel):
    """Complete document with all chunks and metadata."""

    document_id: str
    title: str
    document_type: str
    total_chunks: int
    status: Optional[str] = None
    metadata: Dict[str, Any] = Field(..., description="Aggregated metadata")
    chunks: List[Dict[str, Any]] = Field(..., description="All chunks in order")
    status_history: List[Dict[str, Any]] = Field(
        default_factory=list, description="Status change history"
    )


class UpdateDocumentStatusRequest(BaseModel):
    """Request to update document status."""

    status: str = Field(
        ..., description="New status: draft, active, superseded, archived, expired"
    )
    reason: Optional[str] = Field(None, description="Reason for status change")
    superseded_by: Optional[str] = Field(
        None,
        description="ID of document that supersedes this one (if status=superseded)",
    )
    notes: Optional[str] = Field(None, description="Additional notes")


class DocumentStats(BaseModel):
    """Statistics for a document."""

    document_id: str
    total_chunks: int
    total_characters: int
    avg_chunk_size: float
    has_tables: int
    has_lists: int
    hierarchy_levels: List[str]
    concepts: List[str]


# ===== HELPER FUNCTIONS =====


def extract_title_from_metadata(cmetadata: dict) -> str:
    """Extract title from chunk metadata using mapping table."""
    # Try mapping table first
    document_id = cmetadata.get("document_id")
    if document_id and document_id in DOCUMENT_NAME_MAPPING:
        return DOCUMENT_NAME_MAPPING[document_id]["name"]

    # Fallback 1: Try section_title (better than hierarchy[0])
    if "section_title" in cmetadata and cmetadata["section_title"]:
        section_title = cmetadata["section_title"]
        # Truncate if too long
        return (
            section_title[:100] + "..." if len(section_title) > 100 else section_title
        )

    # Fallback 2: Try hierarchy (but truncate to avoid confusion)
    if "hierarchy" in cmetadata:
        try:
            hierarchy = json.loads(cmetadata["hierarchy"])
            if hierarchy and len(hierarchy) > 0:
                title = hierarchy[0]
                # Truncate long hierarchy titles
                return title[:100] + "..." if len(title) > 100 else title
        except:
            pass

    # Fallback 3: Use document_id
    if document_id:
        return f"Document {document_id}"

    return "Untitled Document"


def extract_current_status(cmetadata: dict) -> Optional[str]:
    """Extract current status from processing_metadata."""
    if "processing_metadata" in cmetadata:
        processing = cmetadata["processing_metadata"]
        if isinstance(processing, dict):
            # Check processing_status first
            if "processing_status" in processing:
                return processing["processing_status"]

            # Check last item in status_change_history
            if "status_change_history" in processing:
                history = processing["status_change_history"]
                if isinstance(history, list) and len(history) > 0:
                    return history[-1].get("to_status")

    # Check document_info.document_status
    if "document_info" in cmetadata:
        doc_info = cmetadata["document_info"]
        if isinstance(doc_info, dict) and "document_status" in doc_info:
            return doc_info["document_status"]

    return None


def extract_status_history(cmetadata: dict) -> List[Dict[str, Any]]:
    """Extract full status change history."""
    if "processing_metadata" in cmetadata:
        processing = cmetadata["processing_metadata"]
        if isinstance(processing, dict) and "status_change_history" in processing:
            return processing["status_change_history"]
    return []


# ===== ENDPOINTS =====


@router.get("", response_model=List[DocumentMetadata])
async def list_documents(
    limit: int = Query(default=50, le=500, description="Max results"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    category: Optional[str] = Query(None, description="Filter by category"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
):
    """
    List all documents from documents table.

    Returns documents uploaded via /api/upload with:
    - Document ID, name, type, category
    - File information
    - Status (active, archived, etc.)
    - Total chunks count
    - Timestamps

    Example:
        GET /documents?document_type=bidding&status=active&limit=20
    """
    try:
        # Build query from documents table
        query = """
            SELECT 
                document_id,
                document_name,
                document_type,
                category,
                filename,
                total_chunks,
                status,
                created_at,
                updated_at
            FROM documents
            WHERE 1=1
        """

        params = {}

        # Add filters
        if document_type:
            query += " AND document_type = :document_type"
            params["document_type"] = document_type

        if category:
            query += " AND category = :category"
            params["category"] = category

        if status:
            query += " AND status = :status"
            params["status"] = status

        # Add pagination
        query += """
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """
        params["limit"] = limit
        params["offset"] = offset

        # Execute query
        result = await db.execute(text(query), params)
        rows = result.fetchall()

        # Format response
        documents = [
            DocumentMetadata(
                document_id=row.document_id,
                document_name=row.document_name,
                document_type=row.document_type,
                category=row.category,
                filename=row.filename,
                total_chunks=row.total_chunks,
                status=row.status,
                created_at=row.created_at.isoformat() if row.created_at else None,
                updated_at=row.updated_at.isoformat() if row.updated_at else None,
            )
            for row in rows
        ]

        logger.info(
            f"📄 Listed {len(documents)} documents from documents table (limit={limit}, offset={offset})"
        )
        return documents

    except Exception as e:
        logger.error(f"❌ Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== CATALOG ENDPOINTS (must be before /{document_id}) =====


@router.get("/catalog", response_model=List[DocumentSummary])
async def list_document_catalog(
    document_type: Optional[str] = Query(None, description="Filter by type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Get catalog of unique documents (grouped by document_id).

    Returns one entry per document, NOT per chunk.
    Includes total chunk count, title, status, etc.
    """
    logger.info(
        f"📚 Catalog request: type={document_type}, status={status}, limit={limit}"
    )
    try:
        # Build WHERE clause
        where_clauses = []
        if document_type:
            where_clauses.append(f"cmetadata->>'document_type' = '{document_type}'")

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        # Query to get unique documents with aggregated data
        # JOIN with documents table to get status
        query = text(
            f"""
            WITH document_groups AS (
                SELECT 
                    cmetadata->>'document_id' as document_id,
                    cmetadata->>'document_type' as document_type,
                    COUNT(*) as chunk_count,
                    MIN((cmetadata->>'chunk_index')::int) as first_chunk_idx,
                    MAX(CAST(cmetadata->>'created_at' AS TIMESTAMP)) as created_at,
                    array_agg(id ORDER BY (cmetadata->>'chunk_index')::int) as chunk_ids,
                    (array_agg(cmetadata ORDER BY (cmetadata->>'chunk_index')::int))[1] as first_chunk_metadata
                FROM langchain_pg_embedding
                {where_sql}
                GROUP BY cmetadata->>'document_id', cmetadata->>'document_type'
            )
            SELECT 
                dg.*,
                COALESCE(d.status, 'active') as doc_status
            FROM document_groups dg
            LEFT JOIN documents d ON d.document_id = dg.document_id
            ORDER BY dg.created_at DESC NULLS LAST, dg.document_id
            LIMIT :limit OFFSET :offset
            """
        )

        result = await db.execute(query, {"limit": limit, "offset": offset})
        rows = result.fetchall()

        logger.info(f"📊 Query returned {len(rows)} document groups")

        documents = []
        for row in rows:
            metadata = row.first_chunk_metadata

            # Extract title
            title = extract_title_from_metadata(metadata)

            # Get status from documents table (via JOIN)
            current_status = row.doc_status

            # Filter by status if requested
            if status and current_status != status:
                continue

            # Extract hierarchy
            hierarchy = None
            if "hierarchy" in metadata:
                try:
                    hierarchy = json.loads(metadata["hierarchy"])
                except:
                    pass

            # Extract dates
            published_date = metadata.get("published_date")
            effective_date = metadata.get("effective_date")

            # Last modified from processing_metadata
            last_modified = None
            if "processing_metadata" in metadata:
                proc = metadata["processing_metadata"]
                if isinstance(proc, dict):
                    last_modified = proc.get("last_processed_at")

            documents.append(
                DocumentSummary(
                    document_id=row.document_id,
                    title=title,
                    document_type=row.document_type,
                    total_chunks=row.chunk_count,
                    status=current_status,
                    published_date=published_date,
                    effective_date=effective_date,
                    last_modified=last_modified,
                    hierarchy_path=hierarchy,
                    chunk_ids=row.chunk_ids,
                )
            )

        logger.info(
            f"📚 Document catalog: Retrieved {len(documents)} documents (filtered)"
        )
        return documents

    except Exception as e:
        logger.error(f"❌ Failed to get document catalog: {e}")
        logger.exception("Full traceback:")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/catalog/{document_id}", response_model=DocumentDetail)
async def get_document_detail(
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get complete document with all chunks.

    Returns:
    - Full metadata from first chunk
    - All chunks in order
    - Status history
    - Aggregated statistics
    """
    try:
        # Query all chunks for this document + status from documents table
        query = text(
            """
            SELECT 
                e.id, 
                e.document, 
                e.cmetadata,
                COALESCE(d.status, 'active') as doc_status
            FROM langchain_pg_embedding e
            LEFT JOIN documents d ON d.document_id = e.cmetadata->>'document_id'
            WHERE e.cmetadata->>'document_id' = :document_id
            ORDER BY (e.cmetadata->>'chunk_index')::int
            """
        )

        result = await db.execute(query, {"document_id": document_id})
        rows = result.fetchall()

        if not rows:
            raise HTTPException(
                status_code=404, detail=f"Document {document_id} not found"
            )

        # Extract metadata from first chunk
        first_metadata = rows[0].cmetadata
        title = extract_title_from_metadata(first_metadata)
        doc_type = first_metadata.get("document_type", "unknown")
        current_status = rows[0].doc_status  # From documents table
        status_history = extract_status_history(first_metadata)

        # Build chunks list
        chunks = []
        for row in rows:
            chunks.append(
                {
                    "chunk_id": row.id,
                    "chunk_index": row.cmetadata.get("chunk_index", 0),
                    "content": row.document,
                    "metadata": row.cmetadata,
                }
            )

        logger.info(f"📄 Retrieved document {document_id}: {len(chunks)} chunks")

        return DocumentDetail(
            document_id=document_id,
            title=title,
            document_type=doc_type,
            total_chunks=len(chunks),
            status=current_status,
            metadata=first_metadata,
            chunks=chunks,
            status_history=status_history,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== DOCUMENT TABLE ENDPOINTS =====


@router.get("/{document_id}", response_model=DocumentMetadata)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed information for a specific document.

    Returns full document metadata from documents table.

    Example:
        GET /documents/6-Mau-so-6C-E-TVCN-tu-van-ca-nhan
    """
    try:
        query = """
            SELECT 
                document_id,
                document_name,
                document_type,
                category,
                filename,
                total_chunks,
                status,
                created_at,
                updated_at
            FROM documents
            WHERE document_id = :document_id
        """

        result = await db.execute(text(query), {"document_id": document_id})
        row = result.fetchone()

        if not row:
            raise HTTPException(
                status_code=404, detail=f"Document {document_id} not found"
            )

        document = DocumentMetadata(
            document_id=row.document_id,
            document_name=row.document_name,
            document_type=row.document_type,
            category=row.category,
            filename=row.filename,
            total_chunks=row.total_chunks,
            status=row.status,
            created_at=row.created_at.isoformat() if row.created_at else None,
            updated_at=row.updated_at.isoformat() if row.updated_at else None,
        )

        logger.info(f"📄 Retrieved document detail: {document_id}")
        return document

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{document_id}/status")
async def update_document_status(
    document_id: str,
    new_status: str = Query(
        ...,
        description="New status (active, archived, expired, superseded)",
    ),
    reason: Optional[str] = Query(None, description="Reason for status change"),
    superseded_by: Optional[str] = Query(
        None, description="Document ID that supersedes this one"
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Update document status with full metadata tracking.

    Updates:
    - documents table: status field
    - All chunks: cmetadata.status
    - All chunks: document_info.document_status
    - All chunks: processing_metadata.status_change_history
    - All chunks: document_info.superseded_by (if applicable)
    - Cache invalidation

    Example:
        PATCH /documents/{document_id}/status?new_status=superseded&reason=Replaced&superseded_by=50/2024/NĐ-CP
    """
    try:
        # Validate status
        valid_statuses = ["draft", "active", "superseded", "archived", "expired"]
        if new_status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {valid_statuses}",
            )

        # 1. Check if document exists and get old status
        check_query = text(
            """
            SELECT d.status, e.cmetadata
            FROM documents d
            LEFT JOIN langchain_pg_embedding e ON e.cmetadata->>'document_id' = d.document_id
            WHERE d.document_id = :document_id
            LIMIT 1
        """
        )
        result = await db.execute(check_query, {"document_id": document_id})
        row = result.fetchone()

        if not row:
            raise HTTPException(
                status_code=404, detail=f"Document {document_id} not found"
            )

        old_status = row.status
        first_chunk_metadata = row.cmetadata or {}

        # Extract old status from metadata if available
        old_metadata_status = (
            first_chunk_metadata.get("document_info", {}).get("document_status")
            or old_status
        )

        # 2. Create status change record
        status_change_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "from_status": old_metadata_status,
            "to_status": new_status,
            "reason": reason or "Status updated via API",
            "changed_by": "api",
        }

        # 3. Update documents table
        update_documents_query = text(
            """
            UPDATE documents 
            SET status = :new_status, updated_at = NOW()
            WHERE document_id = :document_id
        """
        )
        await db.execute(
            update_documents_query,
            {"document_id": document_id, "new_status": new_status},
        )

        # 4. Get all chunks to update metadata
        get_chunks_query = text(
            """
            SELECT id, cmetadata
            FROM langchain_pg_embedding
            WHERE cmetadata->>'document_id' = :document_id
        """
        )
        chunks_result = await db.execute(get_chunks_query, {"document_id": document_id})
        chunks = chunks_result.fetchall()

        # 5. Update each chunk's metadata
        updated_count = 0
        for chunk_row in chunks:
            chunk_id = chunk_row.id
            metadata = dict(chunk_row.cmetadata or {})

            # Update top-level status field (for simple filters)
            metadata["status"] = new_status

            # Update document_info.document_status
            if "document_info" not in metadata:
                metadata["document_info"] = {}
            metadata["document_info"]["document_status"] = new_status

            # Update superseded_by if provided
            if superseded_by:
                metadata["document_info"]["superseded_by"] = superseded_by

            # Update processing_metadata.status_change_history
            if "processing_metadata" not in metadata:
                metadata["processing_metadata"] = {}
            if "status_change_history" not in metadata["processing_metadata"]:
                metadata["processing_metadata"]["status_change_history"] = []

            metadata["processing_metadata"]["status_change_history"].append(
                status_change_entry
            )

            # Update processing_status
            metadata["processing_metadata"]["processing_status"] = new_status

            # Write back to database
            update_chunk_query = text(
                """
                UPDATE langchain_pg_embedding
                SET cmetadata = :metadata
                WHERE id = :chunk_id
            """
            )
            await db.execute(
                update_chunk_query,
                {"metadata": json.dumps(metadata), "chunk_id": chunk_id},
            )
            updated_count += 1

        # 6. Commit all changes
        await db.commit()

        logger.info(
            f"✅ Updated document {document_id} status: {old_metadata_status} → {new_status} "
            f"(synced {updated_count} chunks)"
        )

        # 7. Invalidate retrieval cache after status update
        try:
            from src.embedding.store.pgvector_store import vector_store

            logger.info(
                f"🔄 Clearing retrieval cache after status update: "
                f"{document_id} ({old_metadata_status} → {new_status})"
            )

            cache_stats = vector_store.clear_cache()

            if cache_stats:
                logger.info(
                    f"✅ Cache invalidated successfully: "
                    f"L1={cache_stats['l1_cleared']} queries, "
                    f"L2={cache_stats['l2_cleared']} Redis keys cleared"
                )
            else:
                logger.info("ℹ️  Cache is disabled - no cache to clear")

        except Exception as cache_error:
            # Log warning but don't fail the status update
            logger.warning(
                f"⚠️  Failed to clear cache after status update: {cache_error}",
                exc_info=True,
            )

        return {
            "success": True,
            "document_id": document_id,
            "old_status": old_metadata_status,
            "new_status": new_status,
            "chunks_updated": updated_count,
            "reason": reason,
            "superseded_by": superseded_by,
            "message": f"Status updated to '{new_status}' and synced to {updated_count} chunks",
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error updating document status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}/stats", response_model=DocumentStats)
async def get_document_stats(
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get statistics for a document.

    Returns:
    - Total chunks
    - Character counts
    - Tables/lists count
    - Hierarchy levels
    - Extracted concepts
    """
    try:
        query = text(
            """
            SELECT 
                COUNT(*) as total_chunks,
                SUM((cmetadata->>'char_count')::int) as total_chars,
                AVG((cmetadata->>'char_count')::int) as avg_chunk_size,
                SUM(CASE WHEN (cmetadata->>'has_table')::boolean THEN 1 ELSE 0 END) as tables_count,
                SUM(CASE WHEN (cmetadata->>'has_list')::boolean THEN 1 ELSE 0 END) as lists_count,
                (array_agg(cmetadata->>'hierarchy'))[1] as hierarchy_sample,
                (array_agg(cmetadata->>'extra_metadata'))[1] as extra_sample
            FROM langchain_pg_embedding
            WHERE cmetadata->>'document_id' = :document_id
            """
        )

        result = await db.execute(query, {"document_id": document_id})
        row = result.fetchone()

        if not row or row.total_chunks == 0:
            raise HTTPException(
                status_code=404, detail=f"Document {document_id} not found"
            )

        # Parse hierarchy
        hierarchy_levels = []
        if row.hierarchy_sample:
            try:
                hierarchy_levels = json.loads(row.hierarchy_sample)
            except:
                pass

        # Parse concepts
        concepts = []
        if row.extra_sample:
            try:
                extra = json.loads(row.extra_sample)
                if "primary_concepts" in extra:
                    concepts = extra["primary_concepts"]
            except:
                pass

        return DocumentStats(
            document_id=document_id,
            total_chunks=row.total_chunks,
            total_characters=row.total_chars or 0,
            avg_chunk_size=float(row.avg_chunk_size or 0),
            has_tables=row.tables_count or 0,
            has_lists=row.lists_count or 0,
            hierarchy_levels=hierarchy_levels,
            concepts=concepts,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get document stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
