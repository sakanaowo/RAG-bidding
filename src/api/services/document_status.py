"""
Service cho Document Status Management
Sử dụng psycopg2 synchronous connection (đơn giản, ổn định)
"""

import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime
import psycopg

from src.config.models import settings
from src.preprocessing.schema.enums import DocumentStatus
from src.api.schemas.document_status import (
    UpdateDocumentStatusRequest,
    UpdateDocumentStatusResponse,
    GetDocumentStatusResponse,
)

logger = logging.getLogger(__name__)


class DocumentStatusService:
    """Service quản lý status của documents trong vector store"""

    def __init__(self):
        # Chuyển đổi database URL từ async sang sync format
        self.db_url = settings.database_url.replace("postgresql+psycopg", "postgresql")

    def _get_connection(self):
        """Tạo connection đến database"""
        return psycopg.connect(self.db_url)

    def update_document_status(
        self, request: UpdateDocumentStatusRequest
    ) -> UpdateDocumentStatusResponse:
        """
        Cập nhật status cho TẤT CẢ chunks của một document.

        Logic:
        1. Tìm tất cả chunks có document_id matching
        2. Lấy status cũ từ chunk đầu tiên
        3. Update metadata của TẤT CẢ chunks:
           - document_info.document_status = new_status
           - Thêm vào status_change_history
           - Update superseded_by nếu có
        4. Commit tất cả thay đổi

        Args:
            request: Thông tin update request

        Returns:
            UpdateDocumentStatusResponse với kết quả
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # 1. Tìm tất cả chunks của document này
                    cur.execute(
                        """
                        SELECT id, cmetadata
                        FROM langchain_pg_embedding
                        WHERE cmetadata->>'document_id' = %s
                    """,
                        (request.document_id,),
                    )

                    chunks = cur.fetchall()

                    if not chunks:
                        return UpdateDocumentStatusResponse(
                            success=False,
                            message=f"Không tìm thấy document với ID '{request.document_id}'",
                            document_id=request.document_id,
                            chunks_updated=0,
                        )

                    # 2. Lấy status cũ từ chunk đầu tiên
                    first_metadata = chunks[0][1]
                    old_status = first_metadata.get("document_info", {}).get(
                        "document_status"
                    )

                    # 3. Chuẩn bị status change history entry
                    status_change_entry = {
                        "timestamp": datetime.now().isoformat(),
                        "from_status": old_status,
                        "to_status": request.new_status.value,
                        "reason": request.reason,
                        "changed_by": "api",
                    }

                    # 4. Update từng chunk
                    updated_count = 0
                    for chunk_id, metadata in chunks:
                        # Copy metadata để modify
                        new_metadata = metadata.copy()

                        # Update document_status trong document_info
                        if "document_info" not in new_metadata:
                            new_metadata["document_info"] = {}
                        new_metadata["document_info"][
                            "document_status"
                        ] = request.new_status.value

                        # Update superseded_by nếu có
                        if request.superseded_by:
                            new_metadata["document_info"][
                                "superseded_by"
                            ] = request.superseded_by

                        # Thêm vào status_change_history trong processing_metadata
                        if "processing_metadata" not in new_metadata:
                            new_metadata["processing_metadata"] = {}

                        if (
                            "status_change_history"
                            not in new_metadata["processing_metadata"]
                        ):
                            new_metadata["processing_metadata"][
                                "status_change_history"
                            ] = []

                        new_metadata["processing_metadata"][
                            "status_change_history"
                        ].append(status_change_entry)

                        # Update chunk
                        cur.execute(
                            """
                            UPDATE langchain_pg_embedding
                            SET cmetadata = %s
                            WHERE id = %s
                        """,
                            (json.dumps(new_metadata), chunk_id),
                        )

                        updated_count += 1

                    # 5. Commit tất cả changes
                    conn.commit()

                    logger.info(
                        f"Updated status for document '{request.document_id}': "
                        f"{old_status} → {request.new_status.value} ({updated_count} chunks)"
                    )

                    # 6. Invalidate retrieval cache
                    # Document status change affects many queries -> clear all cache
                    try:
                        from src.embedding.store.pgvector_store import vector_store

                        logger.info(
                            f"🔄 Clearing retrieval cache after status update: "
                            f"{request.document_id} ({old_status} → {request.new_status.value})"
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

                    return UpdateDocumentStatusResponse(
                        success=True,
                        message=f"Đã cập nhật status cho {updated_count} chunks và làm mới cache",
                        document_id=request.document_id,
                        chunks_updated=updated_count,
                        old_status=DocumentStatus(old_status) if old_status else None,
                        new_status=request.new_status,
                    )

        except Exception as e:
            logger.error(f"Error updating document status: {e}", exc_info=True)
            return UpdateDocumentStatusResponse(
                success=False,
                message=f"Lỗi khi cập nhật status: {str(e)}",
                document_id=request.document_id,
                chunks_updated=0,
            )

    def get_document_status(
        self, document_id: str
    ) -> Optional[GetDocumentStatusResponse]:
        """
        Lấy thông tin status hiện tại của một document.

        Args:
            document_id: ID của document

        Returns:
            GetDocumentStatusResponse hoặc None nếu không tìm thấy
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Query để lấy thông tin từ một chunk bất kỳ (tất cả chunks có cùng status)
                    cur.execute(
                        """
                        SELECT cmetadata
                        FROM langchain_pg_embedding
                        WHERE cmetadata->>'document_id' = %s
                        LIMIT 1
                    """,
                        (document_id,),
                    )

                    result = cur.fetchone()

                    if not result:
                        return None

                    metadata = result[0]

                    # Count total chunks
                    cur.execute(
                        """
                        SELECT COUNT(*)
                        FROM langchain_pg_embedding
                        WHERE cmetadata->>'document_id' = %s
                    """,
                        (document_id,),
                    )

                    chunk_count = cur.fetchone()[0]

                    # Extract thông tin
                    document_info = metadata.get("document_info", {})
                    current_status = document_info.get("document_status", "active")
                    superseded_by = document_info.get("superseded_by")

                    # Lấy timestamp từ status_change_history nếu có
                    processing_metadata = metadata.get("processing_metadata", {})
                    status_history = processing_metadata.get(
                        "status_change_history", []
                    )
                    last_updated = None
                    if status_history:
                        last_change = status_history[-1]
                        last_updated = datetime.fromisoformat(last_change["timestamp"])

                    return GetDocumentStatusResponse(
                        document_id=document_id,
                        current_status=DocumentStatus(current_status),
                        chunk_count=chunk_count,
                        last_updated=last_updated,
                        superseded_by=superseded_by,
                    )

        except Exception as e:
            logger.error(f"Error getting document status: {e}", exc_info=True)
            return None
