"""
Pydantic schemas cho Document Status Management API
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from src.preprocessing.schema.enums import DocumentStatus


class UpdateDocumentStatusRequest(BaseModel):
    """Request để cập nhật status của một văn bản"""

    document_id: str = Field(..., description="ID của văn bản cần cập nhật")
    new_status: DocumentStatus = Field(..., description="Status mới")
    reason: Optional[str] = Field(None, description="Lý do thay đổi status")
    superseded_by: Optional[str] = Field(
        None, description="ID của văn bản thay thế (nếu status là SUPERSEDED)"
    )
    effective_date: Optional[datetime] = Field(
        None, description="Ngày hiệu lực của thay đổi"
    )
    notes: Optional[str] = Field(None, description="Ghi chú thêm")

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "43/2022/NĐ-CP",
                "new_status": "superseded",
                "reason": "Được thay thế bởi Nghị định 50/2024/NĐ-CP",
                "superseded_by": "50/2024/NĐ-CP",
                "effective_date": "2024-06-01T00:00:00",
                "notes": "Văn bản mới có hiệu lực từ 01/06/2024",
            }
        }


class UpdateDocumentStatusResponse(BaseModel):
    """Response sau khi cập nhật status"""

    success: bool = Field(..., description="Kết quả thành công hay thất bại")
    message: str = Field(..., description="Thông báo kết quả")
    document_id: str = Field(..., description="ID của văn bản đã cập nhật")
    chunks_updated: int = Field(..., description="Số lượng chunks đã được cập nhật")
    old_status: Optional[DocumentStatus] = Field(None, description="Status cũ")
    new_status: Optional[DocumentStatus] = Field(None, description="Status mới")


class GetDocumentStatusResponse(BaseModel):
    """Response khi query status của một văn bản"""

    document_id: str = Field(..., description="ID của văn bản")
    current_status: DocumentStatus = Field(..., description="Status hiện tại")
    chunk_count: int = Field(..., description="Tổng số chunks của văn bản này")
    last_updated: Optional[datetime] = Field(
        None, description="Thời điểm cập nhật cuối"
    )
    superseded_by: Optional[str] = Field(
        None, description="ID văn bản thay thế (nếu có)"
    )
