"""
Upload API Schemas
Data models for file upload and processing endpoints
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from enum import Enum


class DocumentType(str, Enum):
    """Document type classification based on content analysis"""

    LAW = "law"  # Luật
    DECREE = "decree"  # Nghị định
    CIRCULAR = "circular"  # Thông tư
    DECISION = "decision"  # Quyết định
    BIDDING = "bidding"  # Hồ sơ mời thầu
    REPORT = "report"  # Mẫu báo cáo
    EXAM = "exam"  # Câu hỏi thi
    OTHER = "other"  # Văn bản khác


class ProcessingStatus(str, Enum):
    """Processing status for uploaded files"""

    PENDING = "pending"
    CLASSIFYING = "classifying"
    PREPROCESSING = "preprocessing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    STORING = "storing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileInfo(BaseModel):
    """Information about uploaded file"""

    filename: str
    size_bytes: int
    content_type: str
    detected_type: Optional[DocumentType] = None
    confidence: Optional[float] = None


class UploadRequest(BaseModel):
    """Request model for file upload"""

    files: List[FileInfo]
    auto_classify: bool = True
    override_type: Optional[DocumentType] = None
    processing_options: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ClassificationResult(BaseModel):
    """Result of document type classification"""

    filename: str
    detected_type: DocumentType
    confidence: float
    reasoning: str
    features_detected: List[str]


class ProcessingProgress(BaseModel):
    """Progress tracking for file processing"""

    file_id: str
    filename: str
    document_id: Optional[str] = (
        None  # Actual document_id in database (available after processing)
    )
    status: ProcessingStatus
    progress_percent: int = 0
    current_step: str = ""
    error_message: Optional[str] = None
    chunks_created: int = 0
    embeddings_created: int = 0
    processing_time_ms: Optional[int] = None


class UploadResponse(BaseModel):
    """Response for upload request"""

    upload_id: str
    files_received: int
    classification_results: List[ClassificationResult]
    processing_status: List[ProcessingProgress]
    message: str


class ProcessingResult(BaseModel):
    """Final processing result"""

    file_id: str
    filename: str
    document_id: Optional[str] = None  # Actual document_id in database
    document_type: DocumentType
    status: ProcessingStatus
    chunks_created: int
    embeddings_stored: int
    processing_time_ms: int
    metadata: Dict[str, Any]
    error_details: Optional[str] = None


class BatchProcessingResponse(BaseModel):
    """Response for batch processing status"""

    upload_id: str
    total_files: int
    completed_files: int
    failed_files: int
    overall_status: ProcessingStatus
    results: List[ProcessingResult]
    total_processing_time_ms: int


class ProcessingOptions(BaseModel):
    """Configuration options for processing"""

    batch_name: Optional[str] = None
    chunk_size: Optional[int] = Field(default=1000, ge=100, le=5000)
    chunk_overlap: Optional[int] = Field(default=200, ge=0, le=1000)
    enable_enrichment: bool = True
    enable_validation: bool = True
    force_reprocess: bool = False
    custom_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
