"""
Context Window Cache - Redis-backed conversation history cache

Caches recent messages for each conversation to avoid repeated DB queries.
Uses Write-through strategy: update cache on every new message.

Design:
- Key: context:{conversation_id}
- Value: JSON list of recent messages (max N)
- TTL: Same as session TTL (1 hour default)
- Strategy: Write-through (update on every message)

Performance benefit:
- DB query avoided: ~50ms saved per RAG request
- Especially important when messages table grows large
"""

import json
import logging
from typing import List, Dict, Any, Optional, Callable
from uuid import UUID

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None  # type: ignore

from src.config.feature_flags import (
    ENABLE_REDIS_CACHE,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB_SESSIONS,  # Use sessions DB for context
    SESSION_TTL_SECONDS,
    SESSION_MAX_MESSAGES,
)

logger = logging.getLogger(__name__)

# Configuration
MAX_CONTEXT_MESSAGES = 20  # Match SummaryService.MAX_CONTEXT_MESSAGES * 2


class ConversationContextCache:
    """
    Redis-backed cache for conversation context (recent messages).

    Write-through strategy:
    - Read: Try cache first, fallback to DB
    - Write: Update DB first, then update cache

    Cache structure:
    - Key: context:{conversation_id}
    - Value: JSON array of message dicts (newest last)
    - TTL: SESSION_TTL_SECONDS (default 1 hour)
    """

    # Type annotations
    redis: Any
    enabled: bool
    ttl: int
    max_messages: int
    _stats: Dict[str, int]

    def __init__(
        self,
        redis_host: str = REDIS_HOST,
        redis_port: int = REDIS_PORT,
        redis_db: int = REDIS_DB_SESSIONS,
        ttl: int = SESSION_TTL_SECONDS,
        max_messages: int = MAX_CONTEXT_MESSAGES,
        enabled: bool = ENABLE_REDIS_CACHE,
    ):
        self.enabled = enabled and REDIS_AVAILABLE
        self.ttl = ttl
        self.max_messages = max_messages
        self.redis = None
        self._stats = {"hits": 0, "misses": 0}

        if self.enabled and REDIS_AVAILABLE:
            try:
                self.redis = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    decode_responses=True,  # Return strings, not bytes
                )
                # Test connection
                self.redis.ping()
                logger.info(
                    f"✅ Context cache enabled: Redis DB {redis_db}, "
                    f"TTL={ttl}s, max_messages={max_messages}"
                )
            except Exception as e:
                logger.warning(
                    f"⚠️ Redis connection failed: {e}. Context cache disabled."
                )
                self.enabled = False
                self.redis = None
        else:
            self.redis = None
            logger.info("ℹ️ Context cache disabled")

    def _cache_key(self, conversation_id: UUID) -> str:
        """Generate cache key for conversation context."""
        return f"context:{str(conversation_id)}"

    def _serialize_message(self, msg) -> Dict[str, Any]:
        """
        Serialize a Message object or dict to dict for caching.

        Handles both:
        - SQLAlchemy Message objects (from DB)
        - Dict objects (from cache or tests)
        """
        # If already a dict, normalize it
        if isinstance(msg, dict):
            return {
                "id": str(msg.get("id", "")),
                "role": msg.get("role", ""),
                "content": msg.get("content", ""),
                "created_at": msg.get("created_at"),
                "rag_mode": msg.get("rag_mode"),
            }

        # SQLAlchemy Message object
        return {
            "id": str(msg.id),
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
            "rag_mode": getattr(msg, "rag_mode", None),
        }

    def _serialize_messages(self, messages: List[Any]) -> str:
        """Serialize list of messages to JSON string."""
        return json.dumps([self._serialize_message(m) for m in messages])

    def get_recent_messages(
        self,
        conversation_id: UUID,
        db_fallback_fn: Optional[Callable[[], List[Any]]] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get recent messages from cache (or DB fallback).

        Args:
            conversation_id: Conversation UUID
            db_fallback_fn: Optional callable that returns messages from DB
                           Signature: fn() -> List[Message]

        Returns:
            List of message dicts, or None if cache miss and no fallback
        """
        if not self.enabled or self.redis is None:
            # Cache disabled, use fallback (still apply limit)
            if db_fallback_fn:
                messages = db_fallback_fn()
                recent = (
                    messages[-self.max_messages :]
                    if len(messages) > self.max_messages
                    else messages
                )
                return [self._serialize_message(m) for m in recent]
            return None

        cache_key = self._cache_key(conversation_id)

        try:
            # Try cache first
            cached = self.redis.get(cache_key)
            if cached:
                self._stats["hits"] += 1
                logger.debug(f"✅ Context cache HIT for {conversation_id}")
                return json.loads(str(cached))  # Ensure string type

            self._stats["misses"] += 1
            logger.debug(f"❌ Context cache MISS for {conversation_id}")

            # Cache miss - use fallback and populate cache
            if db_fallback_fn:
                messages = db_fallback_fn()
                self._populate_cache(conversation_id, messages)
                # Return limited messages (same as what's cached)
                recent = (
                    messages[-self.max_messages :]
                    if len(messages) > self.max_messages
                    else messages
                )
                return [self._serialize_message(m) for m in recent]

            return None

        except Exception as e:
            logger.warning(f"⚠️ Context cache error: {e}")
            # Fallback to DB (still apply limit)
            if db_fallback_fn:
                messages = db_fallback_fn()
                recent = (
                    messages[-self.max_messages :]
                    if len(messages) > self.max_messages
                    else messages
                )
                return [self._serialize_message(m) for m in recent]
            return None

    def _populate_cache(self, conversation_id: UUID, messages: List[Any]) -> bool:
        """Populate cache from DB messages."""
        if not self.enabled or self.redis is None:
            return False

        cache_key = self._cache_key(conversation_id)

        try:
            # Take last N messages
            recent = (
                messages[-self.max_messages :]
                if len(messages) > self.max_messages
                else messages
            )
            cached_json = self._serialize_messages(recent)

            self.redis.setex(cache_key, self.ttl, cached_json)
            logger.debug(
                f"📝 Context cache populated for {conversation_id}: {len(recent)} messages"
            )
            return True

        except Exception as e:
            logger.warning(f"⚠️ Failed to populate context cache: {e}")
            return False

    def append_message(
        self,
        conversation_id: UUID,
        message: Any,
    ) -> bool:
        """
        Append a new message to the cache (write-through).

        Call this AFTER saving message to DB.

        Args:
            conversation_id: Conversation UUID
            message: Message object to append

        Returns:
            True if cache updated successfully
        """
        if not self.enabled or self.redis is None:
            return False

        cache_key = self._cache_key(conversation_id)

        try:
            # Get current cached messages
            cached = self.redis.get(cache_key)

            if cached:
                messages = json.loads(str(cached))
            else:
                messages = []

            # Append new message
            messages.append(self._serialize_message(message))

            # Trim to max size
            if len(messages) > self.max_messages:
                messages = messages[-self.max_messages :]

            # Save back with TTL refresh
            self.redis.setex(cache_key, self.ttl, json.dumps(messages))

            logger.debug(
                f"📝 Context cache updated for {conversation_id}: "
                f"appended {getattr(message, 'role', 'unknown')} message, total={len(messages)}"
            )
            return True

        except Exception as e:
            logger.warning(f"⚠️ Failed to append to context cache: {e}")
            return False

    def invalidate(self, conversation_id: UUID) -> bool:
        """
        Invalidate cache for a conversation.

        Call this when:
        - Conversation is deleted
        - Messages are deleted
        - Full refresh needed
        """
        if not self.enabled or self.redis is None:
            return False

        cache_key = self._cache_key(conversation_id)

        try:
            self.redis.delete(cache_key)
            logger.debug(f"🗑️ Context cache invalidated for {conversation_id}")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Failed to invalidate context cache: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.enabled or self.redis is None:
            return {
                "enabled": False,
                "redis_hits": self._stats["hits"],
                "redis_misses": self._stats["misses"],
            }

        try:
            keys = self.redis.keys("context:*")
            keys_list = list(keys) if keys else []

            return {
                "enabled": True,
                "active_conversations": len(keys_list),
                "redis_hits": self._stats["hits"],
                "redis_misses": self._stats["misses"],
                "ttl_seconds": self.ttl,
                "max_messages": self.max_messages,
            }
        except Exception as e:
            return {
                "enabled": True,
                "error": str(e),
                "redis_hits": self._stats["hits"],
                "redis_misses": self._stats["misses"],
            }


# Singleton instance
context_cache = ConversationContextCache()


def get_context_cache() -> ConversationContextCache:
    """Get the singleton context cache instance."""
    return context_cache
