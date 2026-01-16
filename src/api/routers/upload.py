"""
Upload Router - 2-Stage Workflow
================================

Stage 1: Upload & Extract (No embedding yet)
    POST /files              - Upload files, extract metadata, save to storage

Stage 2: Admin Review
    GET  /pending            - List uploads pending review
    GET  /{upload_id}        - Get upload details
    PATCH /{upload_id}       - Edit metadata
    DELETE /{upload_id}      - Cancel upload

Stage 3: Confirm & Process
    POST /{upload_id}/confirm - Confirm upload, start embedding processing
    GET  /{upload_id}/status  - Get processing status (after confirm)
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Body, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..schemas.upload_schemas import (
    DocumentType,
    ProcessingOptions,
)
from ..services.upload_service import UploadProcessingService
from src.auth.dependencies import get_current_user
from src.models.users import User

router = APIRouter(prefix="/upload", tags=["Upload & Processing"])

# Global service instance
upload_service = UploadProcessingService()


# =============================================================================
# Request/Response Models
# =============================================================================


class MetadataUpdateRequest(BaseModel):
    """Request body for updating metadata."""

    document_type: Optional[str] = None
    category: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    custom_fields: Optional[Dict[str, Any]] = None


class CancelRequest(BaseModel):
    """Request body for cancelling upload."""

    reason: Optional[str] = None
    delete_files: bool = False


# =============================================================================
# STAGE 1: Upload Files
# =============================================================================


@router.post("/files", response_model=dict)
async def upload_files(
    files: List[UploadFile] = File(...),
    batch_name: Optional[str] = None,
    chunk_size: Optional[int] = 1000,
    chunk_overlap: Optional[int] = 200,
    enable_enrichment: bool = True,
    enable_validation: bool = True,
    current_user: User = Depends(get_current_user),
):
    """
    Upload files for processing (Stage 1).

    Files are saved to permanent storage and metadata is extracted.
    **NO embedding is generated yet** - awaits admin review and confirmation.

    **Workflow:**
    1. Upload files here
    2. Review extracted metadata at GET /upload/{upload_id}
    3. Edit metadata if needed with PATCH /upload/{upload_id}
    4. Confirm to process embeddings with POST /upload/{upload_id}/confirm

    **Supported formats:** .docx, .pdf, .txt
    **Max files per batch:** 10 files
    **Max file size:** 50MB per file

    Returns upload_id for tracking.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files per upload")

    options = ProcessingOptions(
        batch_name=batch_name,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        enable_enrichment=enable_enrichment,
        enable_validation=enable_validation,
    )

    try:
        result = await upload_service.upload_files(
            files, options, uploaded_by=str(current_user.id)
        )
        return JSONResponse(status_code=202, content=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# STAGE 2: Admin Review
# =============================================================================


@router.get("/pending")
async def list_pending_uploads(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    List all uploads pending admin review.

    Returns uploads with status='pending_review' that need confirmation
    before embeddings are generated.
    """
    try:
        return await upload_service.get_pending_uploads(limit, offset)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{upload_id}")
async def get_upload_detail(upload_id: str):
    """
    Get detailed information about a specific upload.

    Includes:
    - File information (name, size, path)
    - Extracted metadata (auto-detected type, text preview)
    - Admin-edited metadata (if any)
    - Processing status and progress
    """
    try:
        return await upload_service.get_upload_detail(upload_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{upload_id}")
async def update_upload_metadata(
    upload_id: str,
    metadata: MetadataUpdateRequest,
):
    """
    Update metadata for a pending upload.

    Only works for uploads with status='pending_review'.
    Use this to correct auto-detected document type, add tags, etc.
    """
    try:
        admin_metadata = metadata.model_dump(exclude_none=True)
        return await upload_service.update_metadata(upload_id, admin_metadata)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{upload_id}")
async def cancel_upload(
    upload_id: str,
    request: CancelRequest = Body(default=CancelRequest()),
):
    """
    Cancel a pending upload.

    Only works for uploads with status='pending_review'.
    Optionally delete the uploaded files from storage.
    """
    try:
        return await upload_service.cancel_upload(
            upload_id,
            reason=request.reason,
            delete_files=request.delete_files,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# STAGE 3: Confirm & Process
# =============================================================================


@router.post("/{upload_id}/confirm")
async def confirm_upload(upload_id: str):
    """
    Confirm upload and start embedding processing.

    Only works for uploads with status='pending_review'.

    After confirmation:
    - Documents are chunked
    - Embeddings are generated (OpenAI API)
    - Data is stored in vector database
    - Document is registered in documents table

    Use GET /{upload_id} to track processing progress.
    """
    try:
        return await upload_service.confirm_and_process(upload_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{upload_id}/status")
async def get_upload_status(upload_id: str):
    """
    Get processing status for an upload.

    Alias for GET /{upload_id} - returns same data.
    Useful for polling after confirmation.
    """
    try:
        return await upload_service.get_upload_detail(upload_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Legacy Endpoints (backward compatibility)
# =============================================================================


@router.get("/status/{upload_id}")
async def get_upload_status_legacy(upload_id: str):
    """
    [LEGACY] Get processing status.

    Use GET /{upload_id} instead.
    """
    try:
        return await upload_service.get_processing_status(upload_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# File Preview Endpoint
# =============================================================================

from fastapi.responses import FileResponse, PlainTextResponse
from pathlib import Path


@router.head("/{upload_id}/files/{file_id}/content")
@router.get("/{upload_id}/files/{file_id}/content")
async def get_file_content(
    upload_id: str,
    file_id: str,
    as_text: bool = Query(False, description="Return extracted text instead of raw file"),
):
    """
    Get file content for preview.

    By default returns raw file for download/preview.
    Set as_text=true to get extracted text content instead.
    """
    try:
        # Get upload detail to find file path
        detail = await upload_service.get_upload_detail(upload_id)
        
        if not detail:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        # Find the file
        files = detail.get("files", [])
        target_file = None
        for f in files:
            if f.get("file_id") == file_id:
                target_file = f
                break
        
        if not target_file:
            raise HTTPException(status_code=404, detail="File not found in upload")
        
        file_path = target_file.get("file_path")
        
        if not file_path or not Path(file_path).exists():
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        if as_text:
            # Return extracted text if available
            text_preview = target_file.get("extracted_text_preview", "")
            return PlainTextResponse(content=text_preview)
        
        # Return the raw file
        filename = target_file.get("filename", target_file.get("original_filename", "document"))
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=target_file.get("content_type", "application/octet-stream"),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

