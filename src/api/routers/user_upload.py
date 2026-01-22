"""
User Upload Router - User Document Contribution
================================================

Allows authenticated users to upload documents for admin review.
Simplified version of admin upload with rate limiting and file restrictions.

Endpoints:
    POST /user/uploads        - Upload files (max 5/day, 10MB, .pdf/.docx/.txt)
    GET  /user/uploads        - List user's own uploads
    DELETE /user/uploads/{id} - Cancel own pending upload
"""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..schemas.upload_schemas import ProcessingOptions
from ..services.upload_service import UploadProcessingService, UploadJobRepository
from src.auth.dependencies import get_current_user
from src.models.users import User
from src.config.database import get_db_sync

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user/uploads", tags=["User Document Contribution"])

# Global service instance (reuse existing)
upload_service = UploadProcessingService()
job_repo = UploadJobRepository()


# =============================================================================
# Constants
# =============================================================================

MAX_FILES_PER_DAY = 5
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".doc"}


# =============================================================================
# Request/Response Models
# =============================================================================


class UserUploadResponse(BaseModel):
    """Response for user upload."""
    upload_id: str
    status: str
    message: str
    files_count: int
    uploads_remaining_today: int


class UserUploadItem(BaseModel):
    """Single upload item for listing."""
    upload_id: str
    status: str
    files_count: int
    created_at: str
    note: Optional[str] = None
    reject_reason: Optional[str] = None


# =============================================================================
# Rate Limiting Helper
# =============================================================================


def get_user_upload_count_today(user_id: str) -> int:
    """Count user's uploads in the last 24 hours."""
    conn = None
    try:
        conn = get_db_sync()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT COUNT(*) 
            FROM document_upload_jobs 
            WHERE uploaded_by = %(user_id)s 
            AND created_at >= NOW() - INTERVAL '24 hours'
            """,
            {"user_id": user_id}
        )
        result = cursor.fetchone()
        return result[0] if result else 0
    except Exception as e:
        logger.error(f"Failed to get upload count: {e}")
        return 0
    finally:
        if conn:
            conn.close()


def check_rate_limit(user_id: str) -> int:
    """
    Check if user can upload more files today.
    
    Returns remaining uploads count.
    Raises HTTPException if limit exceeded.
    """
    count = get_user_upload_count_today(user_id)
    remaining = MAX_FILES_PER_DAY - count
    
    if remaining <= 0:
        raise HTTPException(
            status_code=429,
            detail=f"Đã đạt giới hạn {MAX_FILES_PER_DAY} lần upload/ngày. Vui lòng thử lại vào ngày mai."
        )
    
    return remaining


def validate_file(file: UploadFile) -> None:
    """
    Validate file extension and size.
    
    Raises HTTPException if invalid.
    """
    # Check extension
    filename = file.filename or ""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' không được hỗ trợ. Chỉ chấp nhận: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Check size (if available)
    if file.size and file.size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File '{filename}' vượt quá giới hạn {MAX_FILE_SIZE_MB}MB."
        )


# =============================================================================
# Endpoints
# =============================================================================


@router.post("", response_model=dict)
async def upload_user_documents(
    files: List[UploadFile] = File(..., description="Files to upload (max 3 files, 10MB each)"),
    note: Optional[str] = Query(None, description="Ghi chú về tài liệu"),
    current_user: User = Depends(get_current_user),
):
    """
    Upload documents for contribution (requires login).
    
    **Limits:**
    - Max 3 files per upload
    - Max 10MB per file
    - Max 5 uploads per day
    - Supported formats: .pdf, .docx, .txt
    
    **Workflow:**
    1. Files are uploaded and metadata extracted
    2. Admin reviews and approves/rejects
    3. If approved, documents are processed into knowledge base
    
    **Returns:** Upload ID to track status
    """
    # Rate limit check
    remaining = check_rate_limit(str(current_user.id))
    
    # Validate files
    if not files:
        raise HTTPException(status_code=400, detail="Không có file nào được chọn")
    
    if len(files) > 3:
        raise HTTPException(status_code=400, detail="Tối đa 3 files mỗi lần upload")
    
    for file in files:
        validate_file(file)
    
    # Use existing upload service - use full_name for better display
    user_display_name = current_user.full_name or current_user.username or current_user.email
    options = ProcessingOptions(
        batch_name=f"Đóng góp: {user_display_name}",
        chunk_size=1000,
        chunk_overlap=200,
        enable_enrichment=True,
        enable_validation=True,
    )
    
    try:
        result = await upload_service.upload_files(
            files,
            options,
            uploaded_by=str(current_user.id),
        )
        
        # Add user note to metadata if provided
        if note and result.get("upload_id"):
            # Use repository to update admin_metadata
            current_job = job_repo.get_job(result["upload_id"])
            if current_job:
                admin_meta = current_job.get("admin_metadata", {}) or {}
                admin_meta["user_note"] = note
                job_repo.update_admin_metadata(result["upload_id"], admin_meta)
        
        logger.info(f"📤 User {current_user.email} uploaded {len(files)} files: {result.get('upload_id')}")
        
        return JSONResponse(
            status_code=202,
            content={
                "upload_id": result.get("upload_id"),
                "status": "pending_review",
                "message": "Đã upload thành công! Tài liệu đang chờ admin duyệt.",
                "files_count": len(files),
                "uploads_remaining_today": remaining - 1,
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi upload: {str(e)}")


@router.get("")
async def list_user_uploads(
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
):
    """
    List current user's uploads.
    
    Shows all uploads by this user with their status:
    - pending_review: Waiting for admin review
    - processing: Being processed into knowledge base
    - completed: Successfully added to knowledge base
    - cancelled: Rejected by admin (see reject_reason)
    """
    conn = None
    try:
        conn = get_db_sync()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT upload_id, status, total_files, files_data, admin_metadata, 
                   cancel_reason, created_at
            FROM document_upload_jobs
            WHERE uploaded_by = %(user_id)s
            ORDER BY created_at DESC
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            {"user_id": str(current_user.id), "limit": limit, "offset": offset}
        )
        
        result = []
        for row in cursor.fetchall():
            files_data = row[3] or []
            admin_meta = row[4] or {}
            
            # Handle files list
            files_list = []
            if isinstance(files_data, list):
                files_list = [
                    {"filename": f.get("filename", f.get("original_filename", "Unknown"))}
                    for f in files_data
                ]
            
            result.append({
                "upload_id": row[0],
                "status": row[1],
                "file_count": len(files_data) if isinstance(files_data, list) else row[2],
                "filename": files_list[0]["filename"] if files_list else "Tài liệu",
                "created_at": row[6].isoformat() if row[6] else None,
                "user_note": admin_meta.get("user_note") if isinstance(admin_meta, dict) else None,
                "cancel_reason": row[5],
                "files": files_list
            })
        
        return {"uploads": result, "total": len(result)}
        
    finally:
        if conn:
            conn.close()


@router.delete("/{upload_id}")
async def cancel_user_upload(
    upload_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Cancel a pending upload.
    
    Only works for uploads with status='pending_review' that belong to the current user.
    """
    try:
        # Get job to verify ownership
        job = job_repo.get_job(upload_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Upload không tồn tại")
        
        if job.get("uploaded_by") != str(current_user.id):
            raise HTTPException(status_code=403, detail="Bạn không có quyền hủy upload này")
        
        if job.get("status") != "pending_review":
            raise HTTPException(
                status_code=400,
                detail=f"Không thể hủy upload với trạng thái '{job.get('status')}'"
            )
        
        # Cancel via existing service
        result = await upload_service.cancel_upload(
            upload_id,
            reason="Người dùng tự hủy",
            delete_files=False,  # Keep files for audit
        )
        
        logger.info(f"📤 User {current_user.email} cancelled upload: {upload_id}")
        
        return {"message": "Đã hủy upload thành công", "upload_id": upload_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cancel upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/limits")
async def get_upload_limits(
    current_user: User = Depends(get_current_user),
):
    """
    Get current user's upload limits and remaining quota.
    """
    count = get_user_upload_count_today(str(current_user.id))
    
    return {
        "max_files_per_upload": 3,
        "max_file_size_mb": MAX_FILE_SIZE_MB,
        "max_uploads_per_day": MAX_FILES_PER_DAY,
        "uploads_today": count,
        "uploads_remaining": max(0, MAX_FILES_PER_DAY - count),
        "allowed_extensions": list(ALLOWED_EXTENSIONS),
    }
