"""
Router cho Document Status Management API
"""

from fastapi import APIRouter, HTTPException
from src.api.schemas.document_status import (
    UpdateDocumentStatusRequest,
    UpdateDocumentStatusResponse,
    GetDocumentStatusResponse,
)
from src.api.services.document_status import DocumentStatusService


router = APIRouter(
    prefix="/document-status",
    tags=["Document Status"],
)


@router.post(
    "/update",
    response_model=UpdateDocumentStatusResponse,
    summary="Cập nhật status của văn bản",
    description="""
    Cập nhật trạng thái hiệu lực của một văn bản pháp lý.
    
    **Lưu ý:** Thay đổi sẽ áp dụng cho TẤT CẢ chunks của document.
    
    **Ví dụ:**
    - Đánh dấu văn bản hết hạn (EXPIRED)
    - Đánh dấu văn bản bị thay thế (SUPERSEDED)
    - Đánh dấu văn bản lỗi thời (OUTDATED)
    """,
)
def update_document_status(request: UpdateDocumentStatusRequest):
    """
    Endpoint để cập nhật status của một document.

    **Example:**
    ```json
    {
        "document_id": "43/2022/NĐ-CP",
        "new_status": "superseded",
        "reason": "Được thay thế bởi Nghị định 50/2024/NĐ-CP",
        "superseded_by": "50/2024/NĐ-CP"
    }
    ```
    """
    service = DocumentStatusService()
    result = service.update_document_status(request)

    if not result.success:
        raise HTTPException(status_code=404, detail=result.message)

    return result


@router.get(
    "",
    response_model=GetDocumentStatusResponse,
    summary="Lấy thông tin status của văn bản",
    description="Truy vấn status hiện tại của một document.",
)
def get_document_status(document_id: str):
    """
    Endpoint để lấy thông tin status của một document.

    **Example:**
    - GET /document-status?document_id=FORM-Bidding/2025%23bee720
    - GET /document-status?document_id=ND-43/2022%23a7f3c9

    **Lưu ý:** Document ID có ký tự đặc biệt (/, #) cần được URL-encode.
    """
    service = DocumentStatusService()
    result = service.get_document_status(document_id)

    if not result:
        raise HTTPException(
            status_code=404, detail=f"Không tìm thấy document với ID '{document_id}'"
        )

    return result
