"""
Cache Management Router

Provides endpoints for monitoring and managing caches:
- RAG Retrieval Cache (L1: Memory, L2: Redis)
- Answer Cache (L1: Memory, L2: Redis) - Phase 1
- Semantic Cache (embeddings for similarity) - Phase 2
- Context Window Cache (Redis)
- Cache invalidation

Admin-only endpoints for cache management.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.config.feature_flags import (
    ENABLE_REDIS_CACHE,
    ENABLE_L1_CACHE,
    CACHE_TTL_RETRIEVAL,
    ENABLE_ANSWER_CACHE,
    ANSWER_CACHE_TTL,
    ENABLE_SEMANTIC_CACHE,
    SEMANTIC_CACHE_THRESHOLD,
    get_feature_status,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cache", tags=["cache"])


@router.get("/stats", response_model=Dict[str, Any])
async def get_cache_stats():
    """
    Get comprehensive cache statistics.

    Returns:
        - retrieval_cache: L1/L2 retrieval cache stats
        - answer_cache: Answer-level cache stats (Phase 1)
        - semantic_cache: Semantic similarity cache stats (Phase 2)
        - context_cache: Conversation context cache stats
        - configuration: Current cache configuration
    """
    stats = {
        "retrieval_cache": {},
        "answer_cache": {},
        "semantic_cache": {},
        "context_cache": {},
        "configuration": {
            "redis_enabled": ENABLE_REDIS_CACHE,
            "l1_enabled": ENABLE_L1_CACHE,
            "retrieval_ttl_seconds": CACHE_TTL_RETRIEVAL,
            "answer_cache_enabled": ENABLE_ANSWER_CACHE,
            "answer_cache_ttl_seconds": ANSWER_CACHE_TTL,
            "semantic_cache_enabled": ENABLE_SEMANTIC_CACHE,
            "semantic_cache_threshold": SEMANTIC_CACHE_THRESHOLD,
        },
    }

    # Get retrieval cache stats
    try:
        from src.embedding.store.pgvector_store import vector_store

        if hasattr(vector_store, "get_stats"):
            stats["retrieval_cache"] = vector_store.get_stats()
        else:
            stats["retrieval_cache"] = {
                "status": "disabled",
                "reason": "Cache wrapper not active",
            }
    except Exception as e:
        stats["retrieval_cache"] = {"error": str(e)}

    # Get answer cache stats (Phase 1)
    try:
        from src.retrieval.answer_cache import get_answer_cache

        answer_cache = get_answer_cache()
        stats["answer_cache"] = answer_cache.get_stats()
    except Exception as e:
        stats["answer_cache"] = {"error": str(e)}

    # Get semantic cache stats (Phase 2 - V2 Hybrid)
    try:
        from src.retrieval.semantic_cache_v2 import get_semantic_cache_v2

        semantic_cache = get_semantic_cache_v2()
        stats["semantic_cache"] = semantic_cache.get_stats()
    except Exception as e:
        stats["semantic_cache"] = {"error": str(e)}

    # Get context cache stats
    try:
        from src.retrieval.context_cache import get_context_cache

        context_cache = get_context_cache()
        stats["context_cache"] = context_cache.get_stats()
    except Exception as e:
        stats["context_cache"] = {"error": str(e)}

    return stats


@router.get("/features", response_model=Dict[str, Any])
async def get_features():
    """
    Get current feature flags and their status.

    Returns all feature flags including cache, pooling, and reranking configuration.
    """
    return get_feature_status()


@router.post("/clear/retrieval")
async def clear_retrieval_cache():
    """
    Clear the RAG retrieval cache (L1 + L2).

    Use this when:
    - Documents have been updated/reindexed
    - Cache appears stale
    - Testing cache behavior

    Returns:
        Number of entries cleared from each cache layer
    """
    try:
        from src.embedding.store.pgvector_store import vector_store

        if hasattr(vector_store, "clear_all_caches"):
            result = vector_store.clear_all_caches()
            logger.info(f"✅ Retrieval cache cleared: {result}")
            return {"success": True, "cleared": result}
        elif hasattr(vector_store, "clear_cache"):
            result = vector_store.clear_cache()
            logger.info(f"✅ Retrieval cache cleared: {result}")
            return {"success": True, "cleared": result}
        else:
            return {"success": False, "message": "Cache not enabled"}

    except Exception as e:
        logger.error(f"❌ Failed to clear retrieval cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear/answer")
async def clear_answer_cache():
    """
    Clear the answer cache (L1 memory + L2 Redis).

    Use this when:
    - Documents have been updated/reindexed
    - LLM prompts have been modified
    - Need to force fresh RAG responses

    Returns:
        Number of entries cleared from each cache layer
    """
    try:
        from src.retrieval.answer_cache import get_answer_cache

        answer_cache = get_answer_cache()
        result = answer_cache.clear_all()
        logger.info(f"✅ Answer cache cleared: {result}")
        return {"success": True, "cleared": result}

    except Exception as e:
        logger.error(f"❌ Failed to clear answer cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear/semantic")
async def clear_semantic_cache():
    """
    Clear the semantic cache (query embeddings).

    Use this when:
    - Embedding model has been changed
    - Need to rebuild similarity index
    - Testing semantic matching behavior

    Returns:
        Number of embeddings cleared
    """
    try:
        from src.retrieval.semantic_cache_v2 import get_semantic_cache_v2

        semantic_cache = get_semantic_cache_v2()
        result = semantic_cache.clear_all()
        logger.info(f"✅ Semantic cache V2 cleared: {result}")
        return {"success": True, "cleared": result}

    except Exception as e:
        logger.error(f"❌ Failed to clear semantic cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/invalidate/query")
async def invalidate_query_cache(query: str):
    """
    Invalidate cache for a specific query.

    Removes from both answer cache and semantic cache.
    Useful for forcing re-generation of a specific answer.

    Args:
        query: The query to invalidate

    Returns:
        Status of invalidation for each cache
    """
    results: Dict[str, Any] = {
        "answer_cache": False,
        "semantic_cache": False,
    }

    try:
        from src.retrieval.answer_cache import get_answer_cache

        answer_cache = get_answer_cache()
        results["answer_cache"] = answer_cache.invalidate(query)
    except Exception as e:
        results["answer_cache_error"] = str(e)

    try:
        from src.retrieval.semantic_cache_v2 import get_semantic_cache_v2

        semantic_cache = get_semantic_cache_v2()
        # Remove embedding for this query
        if semantic_cache._redis:
            key = semantic_cache._generate_key(query)
            semantic_cache._redis.delete(key)
            results["semantic_cache"] = True
    except Exception as e:
        results["semantic_cache_error"] = str(e)

    logger.info(f"✅ Cache invalidated for query: '{query[:50]}...' - {results}")
    return {"success": True, "query": query[:100], "results": results}


@router.post("/clear/context/{conversation_id}")
async def clear_context_cache(conversation_id: str):
    """
    Clear the context cache for a specific conversation.

    Args:
        conversation_id: UUID of the conversation

    Use this when:
    - Conversation data appears stale
    - Messages have been manually modified
    - Testing cache behavior
    """
    from uuid import UUID

    try:
        conv_uuid = UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation_id format")

    try:
        from src.retrieval.context_cache import get_context_cache

        context_cache = get_context_cache()
        result = context_cache.invalidate(conv_uuid)

        return {
            "success": result,
            "conversation_id": conversation_id,
            "message": (
                "Context cache cleared" if result else "Cache not enabled or not found"
            ),
        }

    except Exception as e:
        logger.error(f"❌ Failed to clear context cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear/all")
async def clear_all_caches():
    """
    Clear ALL caches (retrieval + answer + semantic + context).

    ⚠️ Use with caution - this will cause cache misses for all users.

    Use this after:
    - Major data updates
    - Database migrations
    - System restarts
    """
    results = {
        "retrieval_cache": {},
        "answer_cache": {},
        "semantic_cache": {},
        "context_cache": {},
    }

    # Clear retrieval cache
    try:
        from src.embedding.store.pgvector_store import vector_store

        if hasattr(vector_store, "clear_all_caches"):
            results["retrieval_cache"] = vector_store.clear_all_caches()
        elif hasattr(vector_store, "clear_cache"):
            results["retrieval_cache"] = vector_store.clear_cache()
        else:
            results["retrieval_cache"] = {"status": "disabled"}
    except Exception as e:
        results["retrieval_cache"] = {"error": str(e)}

    # Clear answer cache (Phase 1)
    try:
        from src.retrieval.answer_cache import get_answer_cache

        answer_cache = get_answer_cache()
        results["answer_cache"] = answer_cache.clear_all()
    except Exception as e:
        results["answer_cache"] = {"error": str(e)}

    # Clear semantic cache (Phase 2 - V2 Hybrid)
    try:
        from src.retrieval.semantic_cache_v2 import get_semantic_cache_v2

        semantic_cache = get_semantic_cache_v2()
        results["semantic_cache"] = semantic_cache.clear_all()
    except Exception as e:
        results["semantic_cache"] = {"error": str(e)}

    # Clear all context caches
    try:
        from src.retrieval.context_cache import get_context_cache
        import redis
        from src.config.feature_flags import REDIS_HOST, REDIS_PORT, REDIS_DB_SESSIONS

        context_cache = get_context_cache()
        if context_cache.enabled and context_cache.redis is not None:
            # Clear all context keys
            pattern = "context:*"
            deleted_count = 0
            for key in context_cache.redis.scan_iter(match=pattern):
                context_cache.redis.delete(key)
                deleted_count += 1

            results["context_cache"] = {"cleared_conversations": deleted_count}
        else:
            results["context_cache"] = {"status": "disabled"}
    except Exception as e:
        results["context_cache"] = {"error": str(e)}

    logger.info(f"✅ All caches cleared: {results}")
    return {"success": True, "results": results}


@router.get("/health")
async def cache_health():
    """
    Check cache health/connectivity.

    Returns:
        Status of Redis connection and cache availability
    """
    health = {
        "redis_available": False,
        "retrieval_cache": "unknown",
        "answer_cache": "unknown",
        "semantic_cache": "unknown",
        "context_cache": "unknown",
    }

    # Check Redis connectivity
    try:
        import redis as redis_lib
        from src.config.feature_flags import REDIS_HOST, REDIS_PORT

        r = redis_lib.Redis(host=REDIS_HOST, port=REDIS_PORT)
        r.ping()
        health["redis_available"] = True
    except Exception as e:
        health["redis_error"] = str(e)

    # Check retrieval cache
    try:
        from src.embedding.store.pgvector_store import vector_store

        if hasattr(vector_store, "redis"):
            vector_store.redis.ping()
            health["retrieval_cache"] = "healthy"
        else:
            health["retrieval_cache"] = "disabled"
    except Exception as e:
        health["retrieval_cache"] = f"error: {e}"

    # Check answer cache (Phase 1)
    try:
        from src.retrieval.answer_cache import get_answer_cache

        answer_cache = get_answer_cache()
        if answer_cache.enabled and answer_cache._redis:
            answer_cache._redis.ping()
            health["answer_cache"] = "healthy"
        else:
            health["answer_cache"] = "disabled"
    except Exception as e:
        health["answer_cache"] = f"error: {e}"

    # Check semantic cache (Phase 2 - V2 Hybrid)
    try:
        from src.retrieval.semantic_cache_v2 import get_semantic_cache_v2

        semantic_cache = get_semantic_cache_v2()
        if semantic_cache.enabled and semantic_cache._redis:
            semantic_cache._redis.ping()
            health["semantic_cache"] = "healthy (v2 hybrid)"
        else:
            health["semantic_cache"] = "disabled"
    except Exception as e:
        health["semantic_cache"] = f"error: {e}"

    # Check context cache
    try:
        from src.retrieval.context_cache import get_context_cache

        context_cache = get_context_cache()
        if context_cache.enabled and context_cache.redis:
            context_cache.redis.ping()
            health["context_cache"] = "healthy"
        else:
            health["context_cache"] = "disabled"
    except Exception as e:
        health["context_cache"] = f"error: {e}"

    return health
