"""
⚠️ DEPRECATED: LegalScoreReranker

This file was never implemented and is now deprecated.

Migration Guide:
    Option 1 (Recommended): Use BGEReranker
        from src.retrieval.ranking import get_singleton_reranker
        reranker = get_singleton_reranker()

    Option 2 (Custom): Implement your own legal scoring on top of BGE
        See DEPRECATED_RERANKERS.md for example implementation

If you need legal-specific boosting (e.g. prioritize Luật > Nghị định),
you can implement a custom reranker that:
    1. Calls BGEReranker for base scores
    2. Applies legal-specific boost factors based on metadata
    3. Re-sorts results

See: src/retrieval/ranking/DEPRECATED_RERANKERS.md for full migration guide.

Timeline:
    - 2025-01-10: Deprecated
    - 2025-02-01: Moved to archive/
    - 2025-03-01: Deleted
"""

# File intentionally left empty (never implemented)
# For legal-specific scoring, extend BGEReranker with custom boosting
