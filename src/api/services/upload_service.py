"""
Upload Processing Service - 2-Stage Workflow
============================================

Stage 1: Upload & Extract
- Receive files
- Save to permanent storage (data/uploads/{upload_id}/)
- Extract text and auto-classify
- Save to document_upload_jobs with status='pending_review'

Stage 2: Admin Review & Confirm
- Admin reviews extracted metadata
- Admin can edit metadata (document_type, category, etc.)
- Admin confirms → triggers embedding generation
- Or admin cancels → marks as cancelled, optionally deletes files
"""

import uuid
import asyncio
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
import shutil
import logging
from concurrent.futures import ThreadPoolExecutor
import json
from datetime import datetime

from fastapi import UploadFile, HTTPException

from ..schemas.upload_schemas import (
    DocumentType,
    ProcessingStatus,
    ProcessingOptions,
)
from .document_classifier import DocumentClassifier
from ...preprocessing.upload_pipeline import WorkingUploadPipeline
from ...preprocessing.loaders import DocxLoader, PdfLoader, TxtLoader
from ...preprocessing.utils.document_id_generator import DocumentIDGenerator
from ...embedding.embedders.openai_embedder import OpenAIEmbedder
from ...embedding.store.pgvector_store import PGVectorStore
from ...config.models import settings
from ...config.database import get_db_sync

logger = logging.getLogger(__name__)

# Base path for permanent file storage
UPLOAD_STORAGE_BASE = Path(__file__).parent.parent.parent.parent / "data" / "uploads"


class UploadJobRepository:
    """Database repository for upload job tracking."""

    @staticmethod
    def create_job(
        upload_id: str,
        files_data: List[Dict],
        storage_path: str,
        extracted_metadata: Dict,
        options: Optional[Dict] = None,
        uploaded_by: Optional[str] = None,
    ) -> bool:
        """Create a new upload job in pending_review status."""
        conn = None
        try:
            conn = get_db_sync()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO document_upload_jobs (
                    upload_id, status, total_files, 
                    files_data, storage_path, extracted_metadata,
                    options, uploaded_by,
                    created_at, updated_at
                ) VALUES (
                    %(upload_id)s, 'pending_review', %(total_files)s,
                    %(files_data)s, %(storage_path)s, %(extracted_metadata)s,
                    %(options)s, %(uploaded_by)s,
                    NOW(), NOW()
                )
            """,
                {
                    "upload_id": upload_id,
                    "total_files": len(files_data),
                    "files_data": json.dumps(files_data),
                    "storage_path": storage_path,
                    "extracted_metadata": json.dumps(extracted_metadata),
                    "options": json.dumps(options) if options else None,
                    "uploaded_by": uploaded_by,
                },
            )
            conn.commit()
            logger.info(
                f"✅ Created upload job {upload_id} with {len(files_data)} files"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to create upload job: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_job(upload_id: str) -> Optional[Dict]:
        """Get upload job by upload_id."""
        conn = None
        try:
            conn = get_db_sync()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT 
                    j.upload_id, j.status, j.total_files, j.completed_files, j.failed_files,
                    j.files_data, j.storage_path, j.extracted_metadata, j.admin_metadata,
                    j.options, j.error_message, j.uploaded_by, j.confirmed_by,
                    j.created_at, j.updated_at, j.confirmed_at, j.cancelled_at, j.cancel_reason,
                    j.progress_data,
                    u.email as uploader_email, u.username as uploader_username, u.full_name as uploader_full_name
                FROM document_upload_jobs j
                LEFT JOIN users u ON j.uploaded_by::uuid = u.id
                WHERE j.upload_id = %(upload_id)s
            """,
                {"upload_id": upload_id},
            )

            row = cursor.fetchone()
            if not row:
                return None

            return {
                "upload_id": row[0],
                "status": row[1],
                "total_files": row[2],
                "completed_files": row[3],
                "failed_files": row[4],
                "files_data": row[5] if row[5] else [],
                "storage_path": row[6],
                "extracted_metadata": row[7] if row[7] else {},
                "admin_metadata": row[8] if row[8] else {},
                "options": row[9] if row[9] else {},
                "error_message": row[10],
                "uploaded_by": str(row[11]) if row[11] else None,
                "confirmed_by": str(row[12]) if row[12] else None,
                "created_at": row[13].isoformat() if row[13] else None,
                "updated_at": row[14].isoformat() if row[14] else None,
                "confirmed_at": row[15].isoformat() if row[15] else None,
                "cancelled_at": row[16].isoformat() if row[16] else None,
                "cancel_reason": row[17],
                "progress_data": row[18] if row[18] else [],
                "uploader_email": row[19],
                "uploader_username": row[20],
                "uploader_full_name": row[21],
            }
        except Exception as e:
            logger.error(f"Failed to get upload job: {e}")
            return None
        finally:
            if conn:
                conn.close()

    @staticmethod
    def list_pending_jobs(limit: int = 50, offset: int = 0) -> List[Dict]:
        """List all jobs with pending_review status."""
        conn = None
        try:
            conn = get_db_sync()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT 
                    j.upload_id, j.status, j.total_files,
                    j.files_data, j.extracted_metadata, j.admin_metadata,
                    j.uploaded_by, j.created_at, j.updated_at,
                    u.email as uploader_email, u.username as uploader_username, u.full_name as uploader_full_name
                FROM document_upload_jobs j
                LEFT JOIN users u ON j.uploaded_by::uuid = u.id
                WHERE j.status = 'pending_review'
                ORDER BY j.created_at DESC
                LIMIT %(limit)s OFFSET %(offset)s
            """,
                {"limit": limit, "offset": offset},
            )

            jobs = []
            for row in cursor.fetchall():
                jobs.append(
                    {
                        "upload_id": row[0],
                        "status": row[1],
                        "total_files": row[2],
                        "files_data": row[3] if row[3] else [],
                        "extracted_metadata": row[4] if row[4] else {},
                        "admin_metadata": row[5] if row[5] else {},
                        "uploaded_by": str(row[6]) if row[6] else None,
                        "created_at": row[7].isoformat() if row[7] else None,
                        "updated_at": row[8].isoformat() if row[8] else None,
                        "uploader_email": row[9],
                        "uploader_username": row[10],
                        "uploader_full_name": row[11],
                    }
                )
            return jobs
        except Exception as e:
            logger.error(f"Failed to list pending jobs: {e}")
            return []
        finally:
            if conn:
                conn.close()

    @staticmethod
    def update_admin_metadata(upload_id: str, admin_metadata: Dict) -> bool:
        """Update admin-edited metadata for a job."""
        conn = None
        try:
            conn = get_db_sync()
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE document_upload_jobs
                SET admin_metadata = %(admin_metadata)s
                WHERE upload_id = %(upload_id)s AND status = 'pending_review'
            """,
                {
                    "upload_id": upload_id,
                    "admin_metadata": json.dumps(admin_metadata),
                },
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to update admin metadata: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    @staticmethod
    def confirm_job(upload_id: str, confirmed_by: Optional[str] = None) -> bool:
        """Mark job as confirmed and ready for processing."""
        conn = None
        try:
            conn = get_db_sync()
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE document_upload_jobs
                SET status = 'confirmed',
                    confirmed_by = %(confirmed_by)s,
                    confirmed_at = NOW()
                WHERE upload_id = %(upload_id)s AND status = 'pending_review'
            """,
                {
                    "upload_id": upload_id,
                    "confirmed_by": confirmed_by,
                },
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to confirm job: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    @staticmethod
    def update_job_status(
        upload_id: str, status: str, error_message: Optional[str] = None
    ) -> bool:
        """Update job status."""
        conn = None
        try:
            conn = get_db_sync()
            cursor = conn.cursor()

            completed_at_clause = (
                ", completed_at = NOW()" if status in ("completed", "failed") else ""
            )

            cursor.execute(
                f"""
                UPDATE document_upload_jobs
                SET status = %(status)s,
                    error_message = %(error_message)s
                    {completed_at_clause}
                WHERE upload_id = %(upload_id)s
            """,
                {
                    "upload_id": upload_id,
                    "status": status,
                    "error_message": error_message,
                },
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update job status: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    @staticmethod
    def update_progress(
        upload_id: str, progress_data: List[Dict], completed: int = 0, failed: int = 0
    ) -> bool:
        """Update processing progress."""
        conn = None
        try:
            conn = get_db_sync()
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE document_upload_jobs
                SET progress_data = %(progress_data)s,
                    completed_files = %(completed)s,
                    failed_files = %(failed)s
                WHERE upload_id = %(upload_id)s
            """,
                {
                    "upload_id": upload_id,
                    "progress_data": json.dumps(progress_data),
                    "completed": completed,
                    "failed": failed,
                },
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update progress: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    @staticmethod
    def cancel_job(upload_id: str, reason: Optional[str] = None) -> bool:
        """Cancel a pending job."""
        conn = None
        try:
            conn = get_db_sync()
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE document_upload_jobs
                SET status = 'cancelled',
                    cancelled_at = NOW(),
                    cancel_reason = %(reason)s
                WHERE upload_id = %(upload_id)s AND status = 'pending_review'
            """,
                {
                    "upload_id": upload_id,
                    "reason": reason,
                },
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to cancel job: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()


class UploadProcessingService:
    """
    Service for handling file uploads with 2-stage workflow.

    Stage 1: upload_files() - Save files and extract metadata
    Stage 2: confirm_upload() - Process confirmed files (chunking + embedding)
    """

    def __init__(self):
        self.classifier = DocumentClassifier()
        self.embedder = OpenAIEmbedder()
        self.vector_store = PGVectorStore()
        self.doc_id_generator = DocumentIDGenerator()
        self.job_repo = UploadJobRepository()
        self.executor = ThreadPoolExecutor(max_workers=4)

        # Initialize working pipeline
        self.working_pipeline = WorkingUploadPipeline(enable_enrichment=True)

        # Loader mapping by file extension
        self.loaders = {
            ".docx": DocxLoader,
            ".pdf": PdfLoader,
            ".txt": TxtLoader,
        }

        # Ensure upload storage directory exists
        UPLOAD_STORAGE_BASE.mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # STAGE 1: Upload & Extract
    # =========================================================================

    async def upload_files(
        self,
        files: List[UploadFile],
        options: Optional[ProcessingOptions] = None,
        uploaded_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Stage 1: Upload files, save to storage, extract metadata.
        Does NOT process embeddings yet - waits for admin confirmation.
        """
        upload_id = str(uuid.uuid4())
        storage_path = UPLOAD_STORAGE_BASE / upload_id

        try:
            # Validate files
            validated_files = await self._validate_files(files)

            # Create storage directory
            storage_path.mkdir(parents=True, exist_ok=True)

            # Save files and extract metadata
            files_data = []
            extracted_metadata = {"files": []}

            for file in validated_files:
                file_id = str(uuid.uuid4())
                filename = file.filename or f"unknown_{file_id}"
                ext = Path(filename).suffix.lower()
                file_path = storage_path / filename

                # Save file content
                content = await file.read()
                file_path.write_bytes(content)
                await file.seek(0)

                # Extract text preview and classify
                text_preview = ""
                doc_type = DocumentType.OTHER
                confidence = 0.0

                try:
                    loader_class = self.loaders.get(ext)
                    if loader_class:
                        loader = loader_class()
                        loaded_content = loader.load(str(file_path))
                        full_text = (
                            loaded_content.content
                            if hasattr(loaded_content, "content")
                            else str(loaded_content)
                        )
                        text_preview = full_text[:1000]  # First 1000 chars as preview

                        # Auto-classify
                        doc_type, confidence, reasoning = (
                            self.classifier.classify_document(filename, full_text)
                        )
                except Exception as e:
                    logger.warning(f"Failed to extract text from {filename}: {e}")

                file_info = {
                    "file_id": file_id,
                    "filename": filename,
                    "file_path": str(file_path),
                    "size_bytes": len(content),
                    "content_type": file.content_type,
                    "extension": ext,
                }
                files_data.append(file_info)

                extracted_metadata["files"].append(
                    {
                        "file_id": file_id,
                        "filename": filename,
                        "detected_type": (
                            doc_type.value
                            if hasattr(doc_type, "value")
                            else str(doc_type)
                        ),
                        "confidence": confidence,
                        "text_preview": text_preview,
                    }
                )

            # Prepare options dict
            options_dict = None
            if options:
                options_dict = {
                    "batch_name": options.batch_name,
                    "chunk_size": options.chunk_size,
                    "chunk_overlap": options.chunk_overlap,
                    "enable_enrichment": options.enable_enrichment,
                    "enable_validation": options.enable_validation,
                }

            # Save to database
            if not self.job_repo.create_job(
                upload_id=upload_id,
                files_data=files_data,
                storage_path=str(storage_path),
                extracted_metadata=extracted_metadata,
                options=options_dict,
                uploaded_by=uploaded_by,
            ):
                raise Exception("Failed to save upload job to database")

            logger.info(
                f"✅ Stage 1 complete: Upload {upload_id} saved with {len(files_data)} files"
            )

            return {
                "upload_id": upload_id,
                "status": "pending_review",
                "total_files": len(files_data),
                "files": [
                    {
                        "file_id": f["file_id"],
                        "filename": f["filename"],
                        "size_bytes": f["size_bytes"],
                    }
                    for f in files_data
                ],
                "extracted_metadata": extracted_metadata,
                "message": "Files uploaded successfully. Awaiting admin review and confirmation.",
            }

        except Exception as e:
            # Cleanup on failure
            if storage_path.exists():
                shutil.rmtree(storage_path, ignore_errors=True)
            logger.error(f"Upload failed for {upload_id}: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Upload failed: {str(e)}")

    # =========================================================================
    # STAGE 2: Admin Review
    # =========================================================================

    def _transform_job_for_frontend(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Transform job data to match frontend expected format."""
        files_data = job.get("files_data", [])
        extracted_metadata = job.get("extracted_metadata", {})
        extracted_files = extracted_metadata.get("files", [])

        # Build files array matching FE FileInfo interface
        files = []
        for fd in files_data:
            # Find matching extracted metadata
            extracted = next(
                (
                    ef
                    for ef in extracted_files
                    if ef.get("file_id") == fd.get("file_id")
                ),
                {},
            )
            files.append(
                {
                    "file_id": fd.get("file_id"),
                    "filename": fd.get("filename"),
                    "original_filename": fd.get("filename"),
                    "file_size": fd.get("size_bytes", 0),
                    "file_path": fd.get("file_path"),
                    "content_type": fd.get("content_type"),
                    "extracted_text_preview": extracted.get("text_preview"),
                    "auto_detected_type": extracted.get("detected_type"),
                    "confidence": extracted.get("confidence"),
                }
            )

        return {
            "upload_id": job.get("upload_id"),
            "batch_name": (
                job.get("options", {}).get("batch_name") if job.get("options") else None
            ),
            "status": job.get("status"),
            "total_files": job.get("total_files"),
            "files": files,
            "auto_metadata": {
                "document_type": (
                    extracted_files[0].get("detected_type") if extracted_files else None
                ),
                "confidence": (
                    extracted_files[0].get("confidence") if extracted_files else None
                ),
            },
            "admin_metadata": job.get("admin_metadata", {}),
            "uploaded_by": job.get("uploaded_by"),
            "uploader_email": job.get("uploader_email"),
            "uploader_username": job.get("uploader_username"),
            "uploader_full_name": job.get("uploader_full_name"),
            "created_at": job.get("created_at"),
            "updated_at": job.get("updated_at"),
        }

    async def get_pending_uploads(
        self, limit: int = 50, offset: int = 0
    ) -> Dict[str, Any]:
        """Get list of uploads pending admin review."""
        jobs = self.job_repo.list_pending_jobs(limit, offset)
        # Transform each job to FE-expected format
        transformed = [self._transform_job_for_frontend(job) for job in jobs]
        return {
            "pending_count": len(transformed),
            "uploads": transformed,
        }

    async def get_upload_detail(self, upload_id: str) -> Dict[str, Any]:
        """Get detailed info about a specific upload."""
        job = self.job_repo.get_job(upload_id)
        if not job:
            raise HTTPException(status_code=404, detail="Upload not found")
        return self._transform_job_for_frontend(job)

    async def update_metadata(
        self, upload_id: str, admin_metadata: Dict
    ) -> Dict[str, Any]:
        """Update admin-edited metadata for an upload."""
        job = self.job_repo.get_job(upload_id)
        if not job:
            raise HTTPException(status_code=404, detail="Upload not found")

        if job["status"] != "pending_review":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot edit metadata for upload with status '{job['status']}'",
            )

        if not self.job_repo.update_admin_metadata(upload_id, admin_metadata):
            raise HTTPException(status_code=500, detail="Failed to update metadata")

        return {"message": "Metadata updated successfully", "upload_id": upload_id}

    async def cancel_upload(
        self, upload_id: str, reason: Optional[str] = None, delete_files: bool = False
    ) -> Dict[str, Any]:
        """Cancel a pending upload."""
        job = self.job_repo.get_job(upload_id)
        if not job:
            raise HTTPException(status_code=404, detail="Upload not found")

        if job["status"] != "pending_review":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel upload with status '{job['status']}'",
            )

        if not self.job_repo.cancel_job(upload_id, reason):
            raise HTTPException(status_code=500, detail="Failed to cancel upload")

        # Optionally delete files
        if delete_files and job.get("storage_path"):
            storage_path = Path(job["storage_path"])
            if storage_path.exists():
                shutil.rmtree(storage_path, ignore_errors=True)
                logger.info(f"Deleted files for cancelled upload {upload_id}")

        return {
            "message": "Upload cancelled successfully",
            "upload_id": upload_id,
            "files_deleted": delete_files,
        }

    # =========================================================================
    # STAGE 3: Confirm & Process Embeddings
    # =========================================================================

    async def confirm_and_process(
        self, upload_id: str, confirmed_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Stage 2: Admin confirms upload → process embeddings.
        """
        job = self.job_repo.get_job(upload_id)
        if not job:
            raise HTTPException(status_code=404, detail="Upload not found")

        if job["status"] != "pending_review":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot confirm upload with status '{job['status']}'. Must be 'pending_review'.",
            )

        # Mark as confirmed
        if not self.job_repo.confirm_job(upload_id, confirmed_by):
            raise HTTPException(status_code=500, detail="Failed to confirm upload")

        # Start async processing
        asyncio.create_task(self._process_confirmed_upload(upload_id))

        return {
            "message": "Upload confirmed. Processing started.",
            "upload_id": upload_id,
            "status": "processing",
        }

    async def _process_confirmed_upload(self, upload_id: str):
        """Process confirmed upload: chunking + embedding."""
        try:
            job = self.job_repo.get_job(upload_id)
            if not job:
                logger.error(f"Job not found for processing: {upload_id}")
                return

            self.job_repo.update_job_status(upload_id, "processing")

            files_data = job.get("files_data", [])
            admin_metadata = job.get("admin_metadata", {})
            extracted_metadata = job.get("extracted_metadata", {})
            options = job.get("options", {})

            progress_data = []
            completed = 0
            failed = 0

            for i, file_info in enumerate(files_data):
                file_progress = {
                    "file_id": file_info["file_id"],
                    "filename": file_info["filename"],
                    "status": "processing",
                    "progress_percent": 0,
                    "error_message": None,
                    "document_id": None,
                    "chunks_created": 0,
                }
                progress_data.append(file_progress)

                try:
                    # Get metadata for this file
                    file_metadata = next(
                        (
                            f
                            for f in extracted_metadata.get("files", [])
                            if f["file_id"] == file_info["file_id"]
                        ),
                        {},
                    )

                    # Use admin metadata if provided, otherwise use extracted
                    doc_type = admin_metadata.get("document_type") or file_metadata.get(
                        "detected_type", "other"
                    )

                    # Process file
                    file_progress["progress_percent"] = 20
                    self.job_repo.update_progress(
                        upload_id, progress_data, completed, failed
                    )

                    # Run pipeline
                    batch_name = options.get("batch_name")
                    chunks = await self._run_working_pipeline(
                        file_info["file_path"], doc_type, batch_name
                    )

                    file_progress["progress_percent"] = 50
                    self.job_repo.update_progress(
                        upload_id, progress_data, completed, failed
                    )

                    # Convert chunks to LangChain Documents and store
                    from langchain_core.documents import Document

                    if not chunks:
                        raise Exception("No chunks generated from document")

                    documents = []
                    for chunk in chunks:
                        chunk_metadata = chunk.to_dict()
                        chunk_metadata.pop("content", None)
                        doc = Document(
                            page_content=chunk.content, metadata=chunk_metadata
                        )
                        documents.append(doc)

                    file_progress["progress_percent"] = 70
                    self.job_repo.update_progress(
                        upload_id, progress_data, completed, failed
                    )

                    # Store embeddings
                    self.vector_store.add_documents(documents)

                    file_progress["progress_percent"] = 90

                    # Insert into documents table
                    if chunks:
                        first_chunk = chunks[0]
                        document_id = first_chunk.document_id
                        document_name = (
                            first_chunk.section_title
                            or first_chunk.extra_metadata.get("title")
                            or file_info["filename"]
                        )

                        category_mapping = {
                            "law": "Luật chính",
                            "decree": "Nghị định",
                            "circular": "Thông tư",
                            "decision": "Quyết định",
                            "bidding": "Hồ sơ mời thầu",
                            "template": "Mẫu báo cáo",
                            "exam": "Câu hỏi thi",
                            "other": "Khác",
                        }
                        category = admin_metadata.get(
                            "category"
                        ) or category_mapping.get(doc_type, "Khác")

                        self._insert_into_documents_table(
                            document_id=document_id,
                            document_name=document_name,
                            document_type=doc_type,
                            category=category,
                            filename=file_info["filename"],
                            source_file=file_info["file_path"],
                            total_chunks=len(chunks),
                        )

                        file_progress["document_id"] = document_id

                    file_progress["status"] = "completed"
                    file_progress["progress_percent"] = 100
                    file_progress["chunks_created"] = len(chunks)
                    completed += 1

                except Exception as e:
                    logger.error(f"Failed to process file {file_info['filename']}: {e}")
                    file_progress["status"] = "failed"
                    file_progress["error_message"] = str(e)
                    failed += 1

                self.job_repo.update_progress(
                    upload_id, progress_data, completed, failed
                )

            # Final status
            if failed == 0:
                self.job_repo.update_job_status(upload_id, "completed")
            elif completed > 0:
                self.job_repo.update_job_status(
                    upload_id, "completed"
                )  # Partial success
            else:
                self.job_repo.update_job_status(
                    upload_id, "failed", "All files failed to process"
                )

            logger.info(
                f"✅ Processing complete for upload {upload_id}: {completed} completed, {failed} failed"
            )

        except Exception as e:
            logger.error(f"Processing failed for upload {upload_id}: {e}")
            self.job_repo.update_job_status(upload_id, "failed", str(e))

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _validate_files(self, files: List[UploadFile]) -> List[UploadFile]:
        """Validate uploaded files."""
        if not files:
            raise ValueError("No files provided")

        if len(files) > 10:
            raise ValueError("Maximum 10 files per upload")

        validated = []
        for file in files:
            filename = file.filename or f"unknown_file"
            if hasattr(file, "size") and file.size and file.size > 50 * 1024 * 1024:
                raise ValueError(f"File {filename} exceeds 50MB limit")

            ext = Path(filename).suffix.lower()
            if ext not in self.loaders:
                raise ValueError(f"Unsupported file type: {ext}")

            validated.append(file)

        return validated

    async def _run_working_pipeline(
        self, file_path: str, document_type: str, batch_name: Optional[str] = None
    ):
        """Run document through working pipeline."""

        def _sync_pipeline():
            success, chunks, error_msg = self.working_pipeline.process_file(
                Path(file_path), document_type=document_type, batch_name=batch_name
            )
            if not success:
                raise Exception(f"Pipeline failed: {error_msg}")
            return chunks

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, _sync_pipeline)

    def _insert_into_documents_table(
        self,
        document_id: str,
        document_name: str,
        document_type: str,
        category: str,
        filename: str,
        source_file: str,
        total_chunks: int,
    ):
        """Insert document record into documents table."""
        conn = None
        try:
            conn = get_db_sync()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO documents (
                    document_id, document_name, document_type, category,
                    filename, source_file, total_chunks, status,
                    created_at, updated_at
                ) VALUES (
                    %(document_id)s, %(document_name)s, %(document_type)s, %(category)s,
                    %(filename)s, %(source_file)s, %(total_chunks)s, 'active',
                    NOW(), NOW()
                )
                ON CONFLICT (document_id) DO UPDATE SET
                    document_name = EXCLUDED.document_name,
                    total_chunks = EXCLUDED.total_chunks,
                    updated_at = NOW()
            """,
                {
                    "document_id": document_id,
                    "document_name": document_name[:200],
                    "document_type": document_type,
                    "category": category,
                    "filename": filename,
                    "source_file": source_file,
                    "total_chunks": total_chunks,
                },
            )
            conn.commit()
            logger.info(f"✅ Inserted document: {document_id} ({total_chunks} chunks)")
        except Exception as e:
            logger.error(f"❌ Failed to insert document: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    # Legacy method for backward compatibility
    async def get_processing_status(self, upload_id: str) -> Dict[str, Any]:
        """Get current processing status for upload job."""
        return await self.get_upload_detail(upload_id)
