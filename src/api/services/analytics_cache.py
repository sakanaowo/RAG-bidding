"""
Analytics Caching Service - Redis-based caching for dashboard metrics
Provides caching layer to improve dashboard performance
"""

import json
import logging
import hashlib
from datetime import datetime, date, timedelta
from typing import Optional, Any, Callable, TypeVar
from functools import wraps
from enum import Enum

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CacheKeyPrefix(str, Enum):
    """Cache key prefixes for different analytics data."""

    COST_OVERVIEW = "analytics:cost:overview"
    DAILY_USAGE = "analytics:cost:daily"
    TOP_USERS = "analytics:cost:users"
    KB_HEALTH = "analytics:kb:health"
    RAG_PERFORMANCE = "analytics:rag:performance"
    QUALITY_FEEDBACK = "analytics:quality:feedback"
    USER_ENGAGEMENT = "analytics:engagement"
    DASHBOARD_SUMMARY = "analytics:dashboard:summary"


class CacheTTL(int, Enum):
    """Cache TTL values in seconds."""

    SHORT = 60  # 1 minute - real-time data
    MEDIUM = 300  # 5 minutes - frequently updated
    LONG = 900  # 15 minutes - less frequently updated
    VERY_LONG = 3600  # 1 hour - relatively static data
    DAY = 86400  # 24 hours - historical data


class AnalyticsCacheService:
    """
    Redis-based caching service for analytics data.

    Features:
    - Automatic cache key generation
    - TTL management based on data type
    - Cache invalidation strategies
    - Fallback to direct DB query on cache miss
    - JSON serialization for complex objects
    """

    def __init__(self, redis_client: Optional[Any] = None):
        """
        Initialize cache service.

        Args:
            redis_client: Redis client instance. If None, caching is disabled.
        """
        self._redis = redis_client
        self._enabled = redis_client is not None
        self._stats = {"hits": 0, "misses": 0, "errors": 0}

    @property
    def is_enabled(self) -> bool:
        """Check if caching is enabled."""
        return self._enabled

    @property
    def stats(self) -> dict:
        """Get cache statistics."""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0
        return {**self._stats, "total": total, "hit_rate": round(hit_rate, 4)}

    def reset_stats(self):
        """Reset cache statistics."""
        self._stats = {"hits": 0, "misses": 0, "errors": 0}

    def _generate_key(self, prefix: CacheKeyPrefix, **kwargs) -> str:
        """
        Generate a unique cache key from prefix and parameters.

        Args:
            prefix: Cache key prefix
            **kwargs: Parameters to include in key

        Returns:
            Unique cache key string
        """
        # Sort kwargs for consistent key generation
        sorted_params = sorted(kwargs.items())

        # Create param string
        param_parts = []
        for key, value in sorted_params:
            if isinstance(value, date):
                value = value.isoformat()
            elif isinstance(value, Enum):
                value = value.value
            param_parts.append(f"{key}:{value}")

        param_str = ":".join(param_parts)

        if param_str:
            # Hash long param strings
            if len(param_str) > 50:
                param_hash = hashlib.md5(param_str.encode()).hexdigest()[:12]
                return f"{prefix.value}:{param_hash}"
            return f"{prefix.value}:{param_str}"

        return prefix.value

    def _serialize(self, data: Any) -> str:
        """
        Serialize data for Redis storage.

        Handles Pydantic models, dataclasses, and custom objects.
        """
        if hasattr(data, "model_dump"):
            # Pydantic v2 model
            data_dict = data.model_dump(mode="json")
        elif hasattr(data, "dict"):
            # Pydantic v1 model
            data_dict = data.dict()
        elif hasattr(data, "__dict__"):
            data_dict = self._convert_to_serializable(data.__dict__)
        else:
            data_dict = self._convert_to_serializable(data)

        return json.dumps(data_dict, default=str)

    def _convert_to_serializable(self, obj: Any) -> Any:
        """Convert object to JSON serializable format."""
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, Enum):
            return obj.value
        elif isinstance(obj, dict):
            return {k: self._convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._convert_to_serializable(item) for item in obj]
        elif hasattr(obj, "model_dump"):
            return obj.model_dump(mode="json")
        elif hasattr(obj, "dict"):
            return obj.dict()
        return obj

    def _deserialize(self, data: str) -> Any:
        """Deserialize data from Redis."""
        return json.loads(data)

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not self._enabled:
            return None

        try:
            value = await self._redis.get(key)
            if value:
                self._stats["hits"] += 1
                return self._deserialize(value)
            self._stats["misses"] += 1
            return None
        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            self._stats["errors"] += 1
            return None

    async def set(self, key: str, value: Any, ttl: int = CacheTTL.MEDIUM) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds

        Returns:
            True if successful, False otherwise
        """
        if not self._enabled:
            return False

        try:
            serialized = self._serialize(value)
            await self._redis.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            self._stats["errors"] += 1
            return False

    async def delete(self, key: str) -> bool:
        """Delete a cache key."""
        if not self._enabled:
            return False

        try:
            await self._redis.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: Redis key pattern (e.g., "analytics:cost:*")

        Returns:
            Number of keys deleted
        """
        if not self._enabled:
            return 0

        try:
            keys = []
            async for key in self._redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                await self._redis.delete(*keys)
            return len(keys)
        except Exception as e:
            logger.warning(f"Cache delete pattern error for {pattern}: {e}")
            return 0

    async def invalidate_cost_cache(self):
        """Invalidate all cost-related caches."""
        patterns = [
            f"{CacheKeyPrefix.COST_OVERVIEW.value}:*",
            f"{CacheKeyPrefix.DAILY_USAGE.value}:*",
            f"{CacheKeyPrefix.TOP_USERS.value}:*",
            f"{CacheKeyPrefix.DASHBOARD_SUMMARY.value}:*",
        ]
        for pattern in patterns:
            await self.delete_pattern(pattern)

    async def invalidate_kb_cache(self):
        """Invalidate knowledge base health cache."""
        await self.delete_pattern(f"{CacheKeyPrefix.KB_HEALTH.value}:*")
        await self.delete_pattern(f"{CacheKeyPrefix.DASHBOARD_SUMMARY.value}:*")

    async def invalidate_all(self):
        """Invalidate all analytics caches."""
        await self.delete_pattern("analytics:*")

    def get_ttl_for_period(self, period_days: int) -> int:
        """
        Get appropriate TTL based on data period.

        Longer periods get longer TTL since data changes less frequently.
        """
        if period_days <= 1:
            return CacheTTL.SHORT
        elif period_days <= 7:
            return CacheTTL.MEDIUM
        elif period_days <= 30:
            return CacheTTL.LONG
        else:
            return CacheTTL.VERY_LONG


def cached(
    prefix: CacheKeyPrefix,
    ttl: int = CacheTTL.MEDIUM,
    key_params: Optional[list[str]] = None,
):
    """
    Decorator for caching async function results.

    Args:
        prefix: Cache key prefix
        ttl: Cache TTL in seconds
        key_params: List of function parameter names to include in cache key

    Usage:
        @cached(CacheKeyPrefix.COST_OVERVIEW, ttl=300, key_params=['period'])
        async def get_cost_overview(db, period):
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get cache service from kwargs or use default
            cache = kwargs.pop("cache", None)

            if cache is None or not cache.is_enabled:
                return await func(*args, **kwargs)

            # Build cache key from specified parameters
            cache_params = {}
            if key_params:
                for param in key_params:
                    if param in kwargs:
                        cache_params[param] = kwargs[param]

            cache_key = cache._generate_key(prefix, **cache_params)

            # Try to get from cache
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_value

            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl)

            return result

        return wrapper

    return decorator


# Synchronous cache service for non-async contexts
class SyncAnalyticsCacheService:
    """
    Synchronous version of analytics cache service.
    Uses sync Redis client for non-async code paths.
    """

    def __init__(self, redis_client: Optional[Any] = None):
        self._redis = redis_client
        self._enabled = redis_client is not None
        self._stats = {"hits": 0, "misses": 0, "errors": 0}

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    @property
    def stats(self) -> dict:
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0
        return {**self._stats, "total": total, "hit_rate": round(hit_rate, 4)}

    def reset_stats(self):
        """Reset cache statistics."""
        self._stats = {"hits": 0, "misses": 0, "errors": 0}

    def _generate_key(self, prefix: CacheKeyPrefix, **kwargs) -> str:
        sorted_params = sorted(kwargs.items())
        param_parts = []
        for key, value in sorted_params:
            if isinstance(value, date):
                value = value.isoformat()
            elif isinstance(value, Enum):
                value = value.value
            param_parts.append(f"{key}:{value}")

        param_str = ":".join(param_parts)

        if param_str:
            if len(param_str) > 50:
                param_hash = hashlib.md5(param_str.encode()).hexdigest()[:12]
                return f"{prefix.value}:{param_hash}"
            return f"{prefix.value}:{param_str}"

        return prefix.value

    def _serialize(self, data: Any) -> str:
        if hasattr(data, "model_dump"):
            data_dict = data.model_dump(mode="json")
        elif hasattr(data, "dict"):
            data_dict = data.dict()
        elif hasattr(data, "__dict__"):
            data_dict = self._convert_to_serializable(data.__dict__)
        else:
            data_dict = self._convert_to_serializable(data)
        return json.dumps(data_dict, default=str)

    def _convert_to_serializable(self, obj: Any) -> Any:
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, Enum):
            return obj.value
        elif isinstance(obj, dict):
            return {k: self._convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._convert_to_serializable(item) for item in obj]
        elif hasattr(obj, "model_dump"):
            return obj.model_dump(mode="json")
        elif hasattr(obj, "dict"):
            return obj.dict()
        return obj

    def _deserialize(self, data: str) -> Any:
        return json.loads(data)

    def get(self, key: str) -> Optional[Any]:
        if not self._enabled:
            return None
        try:
            value = self._redis.get(key)
            if value:
                self._stats["hits"] += 1
                return self._deserialize(value)
            self._stats["misses"] += 1
            return None
        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            self._stats["errors"] += 1
            return None

    def set(self, key: str, value: Any, ttl: int = CacheTTL.MEDIUM) -> bool:
        if not self._enabled:
            return False
        try:
            serialized = self._serialize(value)
            self._redis.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            self._stats["errors"] += 1
            return False

    def delete(self, key: str) -> bool:
        if not self._enabled:
            return False
        try:
            self._redis.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        if not self._enabled:
            return 0
        try:
            keys = list(self._redis.scan_iter(match=pattern))
            if keys:
                self._redis.delete(*keys)
            return len(keys)
        except Exception as e:
            logger.warning(f"Cache delete pattern error for {pattern}: {e}")
            return 0

    def invalidate_cost_cache(self):
        patterns = [
            f"{CacheKeyPrefix.COST_OVERVIEW.value}:*",
            f"{CacheKeyPrefix.DAILY_USAGE.value}:*",
            f"{CacheKeyPrefix.TOP_USERS.value}:*",
            f"{CacheKeyPrefix.DASHBOARD_SUMMARY.value}:*",
        ]
        for pattern in patterns:
            self.delete_pattern(pattern)

    def invalidate_kb_cache(self):
        self.delete_pattern(f"{CacheKeyPrefix.KB_HEALTH.value}:*")
        self.delete_pattern(f"{CacheKeyPrefix.DASHBOARD_SUMMARY.value}:*")

    def invalidate_all(self):
        self.delete_pattern("analytics:*")


# Default cache service instance (disabled until Redis is configured)
analytics_cache = SyncAnalyticsCacheService(None)


def get_analytics_cache() -> SyncAnalyticsCacheService:
    """Get the analytics cache service instance."""
    return analytics_cache


def configure_analytics_cache(redis_client: Any) -> SyncAnalyticsCacheService:
    """
    Configure the analytics cache with a Redis client.

    Args:
        redis_client: Redis client instance

    Returns:
        Configured cache service
    """
    global analytics_cache
    analytics_cache = SyncAnalyticsCacheService(redis_client)
    logger.info("Analytics cache configured with Redis")
    return analytics_cache
