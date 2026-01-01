"""
Upload Processing Service
Handles file upload, classification, and processing pipeline
"""

import uuid
import asyncio
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
import tempfile
import shutil
import logging
from concurrent.futures import ThreadPoolExecutor

from fastapi import UploadFile, HTTPException

from ..schemas.upload_schemas import (
    DocumentType,
    ProcessingStatus,
    ClassificationResult,
    ProcessingProgress,
    ProcessingResult,
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
from sqlalchemy import text

logger = logging.getLogger(__name__)


class UploadProcessingService:
    """
    Service for handling file uploads and processing pipeline.

    Workflow:
    1. Receive files → Store temporarily
    2. Classify document types → Auto-detection
    3. Route to appropriate pipeline → Preprocessing
    4. Generate embeddings → Store in vector DB
    5. Track progress → Return results
    """

    def __init__(self):
        self.classifier = DocumentClassifier()
        self.embedder = OpenAIEmbedder()
        self.vector_store = PGVectorStore()
        self.doc_id_generator = DocumentIDGenerator()
        self.processing_jobs: Dict[str, Dict] = {}
        self.executor = ThreadPoolExecutor(max_workers=4)

        # Initialize working pipeline
        self.working_pipeline = WorkingUploadPipeline(enable_enrichment=True)

        # Loader mapping by file extension
        self.loaders = {
            ".docx": DocxLoader,
            ".pdf": PdfLoader,
            ".txt": TxtLoader,
        }

    async def upload_files(
        self, files: List[UploadFile], options: ProcessingOptions = None
    ) -> Dict[str, Any]:
        """
        Handle multiple file uploads and start processing.

        Args:
            files: List of uploaded files
            options: Processing configuration options

        Returns:
            Upload response with job ID and initial status
        """
        upload_id = str(uuid.uuid4())

        try:
            # Validate files
            validated_files = await self._validate_files(files)

            # Store files temporarily
            temp_files = await self._store_temp_files(validated_files, upload_id)

            # Initialize processing job
            job_data = {
                "upload_id": upload_id,
                "files": temp_files,
                "options": options or ProcessingOptions(),
                "status": ProcessingStatus.PENDING,
                "created_at": time.time(),
                "progress": [],
            }

            self.processing_jobs[upload_id] = job_data

            # Start async processing
            asyncio.create_task(self._process_files_async(upload_id))

            # Return immediate response
            return {
                "upload_id": upload_id,
                "files_received": len(validated_files),
                "status": ProcessingStatus.PENDING,
                "message": f"Received {len(validated_files)} files. Processing started.",
                "estimated_time_minutes": self._estimate_processing_time(
                    validated_files
                ),
            }

        except Exception as e:
            logger.error(f"Upload failed for {upload_id}: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Upload failed: {str(e)}")

    async def get_processing_status(self, upload_id: str) -> Dict[str, Any]:
        """Get current processing status for upload job"""
        if upload_id not in self.processing_jobs:
            raise HTTPException(status_code=404, detail="Upload job not found")

        job = self.processing_jobs[upload_id]

        return {
            "upload_id": upload_id,
            "status": job["status"],
            "progress": job["progress"],
            "total_files": len(job["files"]),
            "completed_files": len(
                [p for p in job["progress"] if p.status == ProcessingStatus.COMPLETED]
            ),
            "failed_files": len(
                [p for p in job["progress"] if p.status == ProcessingStatus.FAILED]
            ),
        }

    async def _validate_files(self, files: List[UploadFile]) -> List[UploadFile]:
        """Validate uploaded files"""
        if not files:
            raise ValueError("No files provided")

        if len(files) > 10:  # Limit batch size
            raise ValueError("Maximum 10 files per upload")

        validated = []
        for file in files:
            # Check file size (50MB limit)
            if hasattr(file, "size") and file.size > 50 * 1024 * 1024:
                raise ValueError(f"File {file.filename} exceeds 50MB limit")

            # Check file extension
            ext = Path(file.filename).suffix.lower()
            if ext not in self.loaders:
                raise ValueError(f"Unsupported file type: {ext}")

            validated.append(file)

        return validated

    async def _store_temp_files(
        self, files: List[UploadFile], upload_id: str
    ) -> List[Dict]:
        """Store files in temporary directory"""
        temp_dir = Path(tempfile.gettempdir()) / "rag_uploads" / upload_id
        temp_dir.mkdir(parents=True, exist_ok=True)

        stored_files = []

        for file in files:
            # Generate unique filename but preserve original name for pipeline compatibility
            file_id = str(uuid.uuid4())
            ext = Path(file.filename).suffix
            # Use original filename for pipeline compatibility
            temp_path = temp_dir / file.filename

            # Save file content
            content = await file.read()
            temp_path.write_bytes(content)

            stored_files.append(
                {
                    "file_id": file_id,
                    "original_name": file.filename,
                    "temp_path": str(temp_path),
                    "size_bytes": len(content),
                    "content_type": file.content_type,
                    "extension": ext,
                }
            )

            # Reset file pointer for potential reuse
            await file.seek(0)

        return stored_files

    async def _process_files_async(self, upload_id: str):
        """Async file processing workflow"""
        try:
            job = self.processing_jobs[upload_id]
            job["status"] = ProcessingStatus.CLASSIFYING

            # Initialize progress tracking
            for file_info in job["files"]:
                progress = ProcessingProgress(
                    file_id=file_info["file_id"],
                    filename=file_info["original_name"],
                    status=ProcessingStatus.PENDING,
                    progress_percent=0,
                )
                job["progress"].append(progress)

            # Process each file
            for i, file_info in enumerate(job["files"]):
                try:
                    await self._process_single_file(upload_id, i, file_info)
                except Exception as e:
                    logger.error(
                        f"Failed to process file {file_info['original_name']}: {str(e)}"
                    )
                    job["progress"][i].status = ProcessingStatus.FAILED
                    job["progress"][i].error_message = str(e)

            # Update overall status
            completed = sum(
                1 for p in job["progress"] if p.status == ProcessingStatus.COMPLETED
            )
            failed = sum(
                1 for p in job["progress"] if p.status == ProcessingStatus.FAILED
            )

            if failed == 0:
                job["status"] = ProcessingStatus.COMPLETED
            elif completed > 0:
                job["status"] = ProcessingStatus.COMPLETED  # Partial success
            else:
                job["status"] = ProcessingStatus.FAILED

            # Cleanup temp files
            await self._cleanup_temp_files(upload_id)

        except Exception as e:
            logger.error(f"Processing job {upload_id} failed: {str(e)}")
            job["status"] = ProcessingStatus.FAILED

    async def _process_single_file(
        self, upload_id: str, file_index: int, file_info: Dict
    ):
        """Process a single file through the pipeline"""
        job = self.processing_jobs[upload_id]
        progress = job["progress"][file_index]
        start_time = time.time()

        try:
            # Step 1: Load file content
            progress.status = ProcessingStatus.CLASSIFYING
            progress.current_step = "Loading file content"
            progress.progress_percent = 10

            loader_class = self.loaders[file_info["extension"]]
            loader = loader_class()
            content = loader.load(file_info["temp_path"])

            # Step 2: Classify document type
            progress.current_step = "Classifying document type"
            progress.progress_percent = 20

            doc_type, confidence, reasoning = self.classifier.classify_document(
                file_info["original_name"],
                content.content if hasattr(content, "content") else str(content),
            )

            # Step 3: Process with working pipeline
            progress.status = ProcessingStatus.PREPROCESSING
            progress.current_step = f"Processing as {doc_type.value}"
            progress.progress_percent = 40

            # Use working pipeline for all document types
            batch_name = job["options"].batch_name
            chunks = await self._run_working_pipeline(
                file_info["temp_path"], doc_type.value, batch_name
            )

            # Step 4: Prepare documents for embedding (no embedding yet)
            progress.status = ProcessingStatus.EMBEDDING
            progress.current_step = "Preparing documents for embedding"
            progress.progress_percent = 70

            # Convert chunks to LangChain Documents
            from langchain_core.documents import Document

            documents = []
            for chunk in chunks:
                # Convert UniversalChunk to metadata dict
                chunk_metadata = chunk.to_dict()
                # Remove content from metadata to avoid duplication
                chunk_metadata.pop("content", None)

                doc = Document(page_content=chunk.content, metadata=chunk_metadata)
                documents.append(doc)

            # Step 5: Store in vector database (embeddings generated in batch internally)
            progress.status = ProcessingStatus.STORING
            progress.current_step = "Generating embeddings and storing in database"
            progress.progress_percent = 80

            # add_documents() will batch embed all texts internally via LangChain
            # This is MUCH faster than individual embed_text() calls
            self.vector_store.add_documents(documents)
            stored_count = len(documents)

            # Step 5.5: Insert into documents table
            progress.current_step = "Registering in documents table"
            progress.progress_percent = 95

            # Extract document info from first chunk
            first_chunk = chunks[0]
            # UniversalChunk has direct fields, not .metadata wrapper
            document_id = first_chunk.document_id
            # Use section_title or original filename as document name
            document_name = (
                first_chunk.section_title
                or first_chunk.extra_metadata.get("title")
                or file_info["original_name"]
            )
            source_file = file_info["temp_path"]
            filename = file_info["original_name"]

            # Determine category from doc_type
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
            category = category_mapping.get(doc_type, "Khác")

            # Insert into documents table
            self._insert_into_documents_table(
                document_id=document_id,
                document_name=document_name,
                document_type=doc_type,
                category=category,
                filename=filename,
                source_file=source_file,
                total_chunks=len(chunks),
            )

            # Step 6: Complete
            progress.status = ProcessingStatus.COMPLETED
            progress.current_step = "Completed"
            progress.progress_percent = 100
            progress.chunks_created = len(chunks)
            progress.embeddings_created = stored_count
            progress.processing_time_ms = int((time.time() - start_time) * 1000)
            progress.document_id = document_id  # Add document_id for easy access

        except Exception as e:
            logger.error(f"Single file processing failed: {str(e)}")
            progress.status = ProcessingStatus.FAILED
            progress.error_message = str(e)
            progress.processing_time_ms = int((time.time() - start_time) * 1000)

    async def _run_working_pipeline(
        self, file_path: str, document_type: str, batch_name: str = None
    ):
        """Run document through working pipeline"""

        def _sync_pipeline():
            from pathlib import Path

            success, chunks, error_msg = self.working_pipeline.process_file(
                Path(file_path), document_type=document_type, batch_name=batch_name
            )
            if not success:
                raise Exception(f"Working pipeline failed: {error_msg}")
            return chunks

        # Run in thread pool for CPU-intensive work
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, _sync_pipeline)

    async def _basic_chunking(self, content, file_info: Dict):
        """Fallback basic chunking for unsupported document types"""
        from ...preprocessing.chunking.semantic_chunker import SemanticChunker
        from ...preprocessing.schema import (
            UnifiedLegalChunk,
            DocumentInfo,
            LegalMetadata,
        )

        chunker = SemanticChunker(
            chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap
        )

        text_content = content.content if hasattr(content, "content") else str(content)
        basic_chunks = chunker.chunk_text(text_content)

        # Convert to UnifiedLegalChunk format
        unified_chunks = []
        for i, chunk_text in enumerate(basic_chunks):
            doc_info = DocumentInfo(
                title=file_info["original_name"],
                file_path=file_info["temp_path"],
                file_size=file_info["size_bytes"],
            )

            metadata = LegalMetadata(
                document_info=doc_info, chunk_index=i, total_chunks=len(basic_chunks)
            )

            chunk = UnifiedLegalChunk(content=chunk_text, metadata=metadata)
            unified_chunks.append(chunk)

        return unified_chunks

    async def _cleanup_temp_files(self, upload_id: str):
        """Clean up temporary files"""
        try:
            temp_dir = Path(tempfile.gettempdir()) / "rag_uploads" / upload_id
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp files for {upload_id}: {str(e)}")

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
        """
        Insert document record into documents table.

        Called after successful vector DB storage to maintain consistency.
        Uses UPSERT to handle potential duplicates.
        """
        conn = None
        try:
            conn = get_db_sync()
            cursor = conn.cursor()

            insert_query = """
                INSERT INTO documents (
                    document_id,
                    document_name,
                    document_type,
                    category,
                    filename,
                    source_file,
                    total_chunks,
                    status,
                    created_at,
                    updated_at
                ) VALUES (
                    %(document_id)s,
                    %(document_name)s,
                    %(document_type)s,
                    %(category)s,
                    %(filename)s,
                    %(source_file)s,
                    %(total_chunks)s,
                    'active',
                    NOW(),
                    NOW()
                )
                ON CONFLICT (document_id) DO UPDATE SET
                    document_name = EXCLUDED.document_name,
                    total_chunks = EXCLUDED.total_chunks,
                    updated_at = NOW()
            """

            cursor.execute(
                insert_query,
                {
                    "document_id": document_id,
                    "document_name": document_name[:200],  # Truncate if needed
                    "document_type": document_type,
                    "category": category,
                    "filename": filename,
                    "source_file": source_file,
                    "total_chunks": total_chunks,
                },
            )
            conn.commit()

            logger.info(
                f"✅ Inserted document into documents table: {document_id} ({total_chunks} chunks)"
            )

        except Exception as e:
            logger.error(f"❌ Failed to insert into documents table: {e}")
            if conn:
                conn.rollback()
            # Don't raise - vector DB storage succeeded, this is supplementary

        finally:
            if conn:
                conn.close()

    def _estimate_processing_time(self, files: List[UploadFile]) -> int:
        """Estimate processing time in minutes"""
        # Rough estimate: 1-2 minutes per file depending on size
        base_time = len(files) * 1.5

        # Add time based on file sizes (if available)
        for file in files:
            if hasattr(file, "size"):
                # Add 1 minute per 10MB
                size_mb = file.size / (1024 * 1024)
                base_time += size_mb / 10

        return max(1, int(base_time))  # At least 1 minute
