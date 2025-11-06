"""
Upload Router
API endpoints for file upload and document processing
"""

from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse

from ..schemas.upload_schemas import (
    DocumentType,
    ProcessingOptions,
    UploadResponse,
    BatchProcessingResponse,
    ClassificationResult,
)
from ..services.upload_service import UploadProcessingService
from ..services.document_classifier import DocumentClassifier

router = APIRouter(prefix="/upload", tags=["Upload & Processing"])

# Global service instances
upload_service = UploadProcessingService()
classifier = DocumentClassifier()


@router.post("/files", response_model=dict)
async def upload_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    auto_classify: bool = True,
    override_type: Optional[DocumentType] = None,
    chunk_size: Optional[int] = 1000,
    chunk_overlap: Optional[int] = 200,
    enable_enrichment: bool = True,
    enable_validation: bool = True,
    force_reprocess: bool = False,
):
    """
    Upload multiple files for processing.

    **Features:**
    - Automatic document type classification
    - Parallel processing pipeline
    - Progress tracking
    - Error handling and recovery

    **Supported formats:** .docx, .pdf, .txt
    **Max files per batch:** 10 files
    **Max file size:** 50MB per file

    **Processing steps:**
    1. File validation and temporary storage
    2. Document type classification (Law, Decree, Circular, etc.)
    3. Route to appropriate preprocessing pipeline
    4. Text chunking and enrichment
    5. Embedding generation (OpenAI text-embedding-3-large)
    6. Vector database storage (PostgreSQL + pgvector)

    Returns upload_id for tracking progress.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    # Validate file count
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files per upload")

    # Create processing options
    options = ProcessingOptions(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        enable_enrichment=enable_enrichment,
        enable_validation=enable_validation,
        force_reprocess=force_reprocess,
    )

    try:
        result = await upload_service.upload_files(files, options)
        return JSONResponse(
            status_code=202, content=result  # Accepted - processing started
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status/{upload_id}")
async def get_upload_status(upload_id: str):
    """
    Get processing status for uploaded files.

    **Status types:**
    - pending: Queued for processing
    - classifying: Analyzing document type
    - preprocessing: Pipeline processing
    - chunking: Text segmentation
    - embedding: Generating vectors
    - storing: Saving to database
    - completed: Successfully processed
    - failed: Error occurred

    **Progress tracking:**
    - Overall batch status
    - Per-file progress percentage
    - Error details (if any)
    - Processing time metrics
    """
    try:
        status = await upload_service.get_processing_status(upload_id)
        return status
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/classify")
async def classify_document_type(filename: str, content: Optional[str] = None):
    """
    Classify document type without processing.

    **Classification logic:**
    - Filename pattern analysis
    - Content keyword matching
    - Legal structure detection
    - Authority indicator recognition

    **Document types detected:**
    - law: Luật (Laws from National Assembly)
    - decree: Nghị định (Government Decrees)
    - circular: Thông tư (Ministry Circulars)
    - decision: Quyết định (Administrative Decisions)
    - bidding: Hồ sơ mời thầu (Bidding Documents)
    - report: Mẫu báo cáo (Report Templates)
    - exam: Câu hỏi thi (Exam Questions)
    - other: Unclassified documents

    Useful for preview before batch upload.
    """
    try:
        doc_type, confidence, reasoning = classifier.classify_document(
            filename, content
        )
        features = classifier.get_features_detected(filename, content)

        return ClassificationResult(
            filename=filename,
            detected_type=doc_type,
            confidence=confidence,
            reasoning=reasoning,
            features_detected=features,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")


@router.get("/supported-types")
async def get_supported_document_types():
    """
    Get list of supported document types and their descriptions.

    Returns classification criteria and processing capabilities
    for each document type.
    """
    return {
        "document_types": {
            DocumentType.LAW: {
                "name_vi": "Luật",
                "description": "Laws issued by National Assembly",
                "authority": "Quốc hội",
                "legal_level": 2,
                "pipeline_available": True,
                "sample_patterns": ["Luật số 123/2024/QH15", "Law on Investment"],
            },
            DocumentType.DECREE: {
                "name_vi": "Nghị định",
                "description": "Government implementation decrees",
                "authority": "Chính phủ",
                "legal_level": 3,
                "pipeline_available": False,  # TODO: Implement
                "sample_patterns": ["Nghị định số 456/2024/NĐ-CP"],
            },
            DocumentType.CIRCULAR: {
                "name_vi": "Thông tư",
                "description": "Ministry guidance circulars",
                "authority": "Bộ, ngành",
                "legal_level": 4,
                "pipeline_available": False,  # TODO: Implement
                "sample_patterns": ["Thông tư số 789/2024/TT-BTC"],
            },
            DocumentType.DECISION: {
                "name_vi": "Quyết định",
                "description": "Administrative decisions",
                "authority": "Various authorities",
                "legal_level": 4,
                "pipeline_available": False,  # TODO: Implement
                "sample_patterns": ["Quyết định số 101/2024/QĐ-TTg"],
            },
            DocumentType.BIDDING: {
                "name_vi": "Hồ sơ mời thầu",
                "description": "Tender and bidding documents",
                "authority": "Chủ đầu tư",
                "legal_level": None,
                "pipeline_available": False,  # TODO: Implement
                "sample_patterns": ["HSMT-2024-001", "Tender Package XYZ"],
            },
            DocumentType.REPORT: {
                "name_vi": "Mẫu báo cáo",
                "description": "Report templates and forms",
                "authority": "Various agencies",
                "legal_level": None,
                "pipeline_available": False,  # TODO: Implement
                "sample_patterns": ["Mẫu BC-01", "Form Template 2024"],
            },
            DocumentType.EXAM: {
                "name_vi": "Câu hỏi thi",
                "description": "Exam questions and tests",
                "authority": "Educational institutions",
                "legal_level": None,
                "pipeline_available": False,  # TODO: Implement
                "sample_patterns": ["Đề thi 2024", "Quiz Questions"],
            },
            DocumentType.OTHER: {
                "name_vi": "Khác",
                "description": "Other document types",
                "authority": "Various",
                "legal_level": None,
                "pipeline_available": False,
                "sample_patterns": ["General documents"],
            },
        },
        "file_formats": {
            ".docx": "Microsoft Word documents",
            ".pdf": "Portable Document Format",
            ".txt": "Plain text files",
        },
        "processing_capabilities": {
            "max_files_per_batch": 10,
            "max_file_size_mb": 50,
            "supported_languages": ["Vietnamese", "English"],
            "embedding_model": "text-embedding-3-large",
            "embedding_dimensions": 3072,
            "chunk_size_range": [100, 5000],
            "chunk_overlap_range": [0, 1000],
        },
    }


@router.delete("/job/{upload_id}")
async def cancel_upload_job(upload_id: str):
    """
    Cancel a processing job and clean up resources.

    **Note:** Jobs that have already completed cannot be cancelled.
    In-progress jobs will be stopped at the next safe checkpoint.
    """
    try:
        # TODO: Implement job cancellation logic
        return {
            "message": f"Job {upload_id} cancellation requested",
            "status": "not_implemented",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_upload_statistics():
    """
    Get upload and processing statistics.

    Returns metrics about:
    - Total files processed
    - Success/failure rates
    - Processing time averages
    - Document type distribution
    - Storage utilization
    """
    try:
        # TODO: Implement statistics collection
        return {
            "total_uploads": 0,
            "successful_uploads": 0,
            "failed_uploads": 0,
            "avg_processing_time_ms": 0,
            "document_type_distribution": {},
            "total_chunks_stored": 0,
            "total_embeddings_stored": 0,
            "message": "Statistics collection not implemented yet",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
