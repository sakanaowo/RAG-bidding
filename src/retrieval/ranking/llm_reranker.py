"""
⚠️ DEPRECATED: LLMReranker

This file was never implemented and is now deprecated.

⚠️ WARNING: LLM-based reranking is NOT RECOMMENDED for production:
    - Extremely slow (~2-5s vs 150ms for BGE)
    - Expensive (GPT API costs per query)
    - Overkill for most cases (BGE accuracy is sufficient)

Migration Guide:
    Use BGEReranker instead (10-30x faster, free, proven accuracy):

    # OLD (not implemented):
    from src.retrieval.ranking import LLMReranker
    reranker = LLMReranker()

    # NEW (recommended):
    from src.retrieval.ranking import get_singleton_reranker
    reranker = get_singleton_reranker()

When to consider LLM reranking (rare cases):
    - Complex reasoning required beyond semantic similarity
    - Budget allows ~$0.01 per query
    - Latency requirements relaxed (acceptable 5s response time)

See: src/retrieval/ranking/DEPRECATED_RERANKERS.md for full migration guide.

Timeline:
    - 2025-01-10: Deprecated
    - 2025-02-01: Moved to archive/
    - 2025-03-01: Deleted
"""

# File intentionally left empty (never implemented)
# Use BGEReranker for production (10-30x faster, free, accurate)
