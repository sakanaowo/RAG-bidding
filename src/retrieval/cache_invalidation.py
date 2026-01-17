"""
Cache Invalidation Service

Manages cache invalidation when documents are modified.
Ensures users see fresh data after document status changes.
"""

import logging
from datetime import datetime
from typing import Optional, Set, Dict, Any
from uuid import UUID

logger = logging.getLogger(__name__)


class CacheInvalidationService:
    """
    Service for invalidating caches when document data changes.

    Use cases:
    - Document status changed (active → expired)
    - Document content updated
    - Chunk data reindexed
    - Admin operations

    Cache layers affected:
    - L1: In-memory LRU (per-process)
    - L2: Redis (shared)
    """

    def __init__(self):
        self._affected_doc_ids: Set[str] = set()
        self._invalidation_count: int = 0
        self._last_invalidation: Optional[datetime] = None

    def invalidate_on_document_change(
        self, document_id: str, change_type: str = "status_change"
    ) -> Dict[str, Any]:
        """
        Invalidate all caches when a document changes.

        Args:
            document_id: The document that was modified
            change_type: Type of change (status_change, content_update, delete)

        Returns:
            Dictionary with invalidation result details
        """
        from src.embedding.store.pgvector_store import vector_store

        start_time = datetime.now()
        result: Dict[str, Any] = {
            "success": False,
            "document_id": document_id,
            "change_type": change_type,
            "timestamp": start_time.isoformat(),
            "caches_cleared": {},
        }

        try:
            # Track affected document
            self._affected_doc_ids.add(document_id)
            self._invalidation_count += 1
            self._last_invalidation = start_time

            # Clear all retrieval caches
            # Because any cached query might have included this document
            if hasattr(vector_store, "clear_all_caches"):
                cache_result = vector_store.clear_all_caches()
                result["caches_cleared"]["retrieval"] = cache_result
                logger.info(
                    f"🗑️ [CACHE_INVALIDATION] Document change invalidation completed | "
                    f"doc_id={document_id} | change_type={change_type} | "
                    f"retrieval_cleared={cache_result} | "
                    f"total_invalidations={self._invalidation_count} | "
                    f"duration_ms={(datetime.now() - start_time).total_seconds() * 1000:.2f}"
                )
            else:
                logger.warning(
                    f"⚠️ [CACHE_INVALIDATION] Cache not enabled or clear_all_caches not available | "
                    f"doc_id={document_id} | change_type={change_type}"
                )
                result["caches_cleared"]["retrieval"] = "not_available"

            result["success"] = True
            result["duration_ms"] = (datetime.now() - start_time).total_seconds() * 1000
            return result

        except Exception as e:
            logger.error(
                f"❌ [CACHE_INVALIDATION] Failed to invalidate cache | "
                f"doc_id={document_id} | change_type={change_type} | "
                f"error={str(e)}",
                exc_info=True,
            )
            result["error"] = str(e)
            return result

    def invalidate_on_reindex(self) -> Dict[str, Any]:
        """
        Invalidate all caches after reindexing documents.

        Call this after:
        - Bulk document import
        - Embedding regeneration
        - Database migration

        Returns:
            Dictionary with invalidation result details
        """
        from src.embedding.store.pgvector_store import vector_store

        start_time = datetime.now()
        result: Dict[str, Any] = {
            "success": False,
            "operation": "reindex",
            "timestamp": start_time.isoformat(),
            "caches_cleared": {},
        }

        try:
            if hasattr(vector_store, "clear_all_caches"):
                cache_result = vector_store.clear_all_caches()
                result["caches_cleared"]["retrieval"] = cache_result

                logger.info(
                    f"🗑️ [CACHE_INVALIDATION] Reindex invalidation completed | "
                    f"retrieval_cleared={cache_result} | "
                    f"duration_ms={(datetime.now() - start_time).total_seconds() * 1000:.2f}"
                )

            result["success"] = True
            result["duration_ms"] = (datetime.now() - start_time).total_seconds() * 1000
            return result

        except Exception as e:
            logger.error(
                f"❌ [CACHE_INVALIDATION] Reindex invalidation failed | error={str(e)}"
            )
            result["error"] = str(e)
            return result

    def get_affected_documents(self) -> Set[str]:
        """Get set of document IDs that triggered invalidation."""
        return self._affected_doc_ids.copy()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache invalidation statistics."""
        return {
            "total_invalidations": self._invalidation_count,
            "affected_documents_count": len(self._affected_doc_ids),
            "last_invalidation": (
                self._last_invalidation.isoformat() if self._last_invalidation else None
            ),
        }


# Singleton instance
cache_invalidation_service = CacheInvalidationService()


# Helper function for use in document update endpoints
def invalidate_cache_for_document(
    document_id: str, change_type: str = "update"
) -> Dict[str, Any]:
    """
    Convenience function to invalidate cache when document changes.

    Usage in document update endpoint:
        from src.retrieval.cache_invalidation import invalidate_cache_for_document

        @router.put("/documents/{document_id}/status")
        async def update_document_status(document_id: str, status: str, ...):
            # Update document in DB
            document.status = status
            db.commit()

            # Invalidate cache
            invalidate_cache_for_document(document_id, "status_change")

            return {"status": "updated"}

    Returns:
        Dictionary with invalidation result details
    """
    return cache_invalidation_service.invalidate_on_document_change(
        document_id, change_type
    )
