"""
⚠️ DEPRECATED: CohereReranker

This file was never implemented and is now deprecated.

Migration Guide:
    Use BGEReranker instead (free, offline, privacy-friendly):

    # OLD (not implemented):
    from src.retrieval.ranking import CohereReranker
    reranker = CohereReranker()

    # NEW (recommended):
    from src.retrieval.ranking import get_singleton_reranker
    reranker = get_singleton_reranker()

See: src/retrieval/ranking/DEPRECATED_RERANKERS.md for full migration guide.

Timeline:
    - 2025-01-10: Deprecated
    - 2025-02-01: Moved to archive/
    - 2025-03-01: Deleted
"""

# File intentionally left empty (never implemented)
# Use BGEReranker for production reranking
