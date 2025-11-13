"""
⚠️ DEPRECATED: CrossEncoderReranker

This file was never implemented and is now deprecated.

Note: BGEReranker ALREADY uses CrossEncoder internally!

Migration Guide:
    BGE is a cross-encoder model, so no separate implementation needed:
    
    # OLD (not implemented):
    from src.retrieval.ranking import CrossEncoderReranker
    reranker = CrossEncoderReranker()
    
    # NEW (BGE IS a cross-encoder):
    from src.retrieval.ranking import get_singleton_reranker
    reranker = get_singleton_reranker()

See: src/retrieval/ranking/DEPRECATED_RERANKERS.md for full migration guide.

Timeline:
    - 2025-01-10: Deprecated
    - 2025-02-01: Moved to archive/
    - 2025-03-01: Deleted
"""

# File intentionally left empty (never implemented)
# BGEReranker already uses CrossEncoder architecture
