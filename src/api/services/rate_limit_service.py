"""
Rate Limit Service - Query-based Daily Rate Limiting

Provides rate limiting functionality using Redis to track
daily query count per user. Limits users to a configurable
number of queries per day.

Key design:
- Redis key: rate_limit:{user_id}:{YYYY-MM-DD}
- TTL: 86400 seconds (24 hours)
- Atomic increment with INCR command
"""

import logging
from datetime import date
from typing import Optional, NamedTuple
from uuid import UUID

import redis

from src.config.feature_flags import (
    ENABLE_REDIS_CACHE,
    REDIS_HOST,
    REDIS_PORT,
)

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

# Rate limit settings (can be overridden via environment variables)
import os

RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_DAILY_QUERIES = int(os.getenv("RATE_LIMIT_DAILY_QUERIES"))
RATE_LIMIT_REDIS_DB = int(os.getenv("RATE_LIMIT_REDIS_DB"))

# Key prefix for rate limiting
RATE_LIMIT_KEY_PREFIX = "rate_limit"

# TTL for rate limit keys (24 hours)
RATE_LIMIT_TTL_SECONDS = 86400


# ============================================================================
# RESULT TYPES
# ============================================================================


class RateLimitResult(NamedTuple):
    """Result of a rate limit check."""
    
    allowed: bool
    current_count: int
    limit: int
    remaining: int
    reset_at: str  # ISO format date when limit resets


class RateLimitExceededError(Exception):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, message: str, result: RateLimitResult):
        super().__init__(message)
        self.result = result


# ============================================================================
# REDIS CONNECTION
# ============================================================================

_redis_client: Optional[redis.Redis] = None


def _get_redis_client() -> Optional[redis.Redis]:
    """Get or create Redis client for rate limiting."""
    global _redis_client
    
    if not ENABLE_REDIS_CACHE:
        logger.debug("Redis cache disabled, rate limiting will use fallback")
        return None
    
    if _redis_client is None:
        try:
            _redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=RATE_LIMIT_REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            # Test connection
            _redis_client.ping()
            logger.info(
                f"✅ Rate limit Redis connected: {REDIS_HOST}:{REDIS_PORT}/db{RATE_LIMIT_REDIS_DB}"
            )
        except redis.ConnectionError as e:
            logger.warning(f"⚠️ Rate limit Redis connection failed: {e}")
            _redis_client = None
    
    return _redis_client


# ============================================================================
# RATE LIMIT SERVICE
# ============================================================================


class RateLimitService:
    """
    Service for managing query-based rate limits using Redis.
    
    Usage:
        result = RateLimitService.check_and_increment(user_id)
        if not result.allowed:
            raise RateLimitExceededError("Limit reached", result)
    
    TODO (Future):
        - User tier support with different limits per tier
        - Token-based rate limiting
        - Cost-based rate limiting
    """
    
    @staticmethod
    def _get_key(user_id: UUID) -> str:
        """Generate Redis key for user's daily rate limit."""
        today = date.today().isoformat()  # YYYY-MM-DD
        return f"{RATE_LIMIT_KEY_PREFIX}:{user_id}:{today}"
    
    @staticmethod
    def _get_tomorrow() -> str:
        """Get tomorrow's date in ISO format (when limit resets)."""
        from datetime import timedelta
        tomorrow = date.today() + timedelta(days=1)
        return tomorrow.isoformat()
    
    @staticmethod
    def check_rate_limit(user_id: UUID) -> RateLimitResult:
        """
        Check current rate limit status without incrementing.
        
        Args:
            user_id: User UUID to check
            
        Returns:
            RateLimitResult with current status
        """
        if not RATE_LIMIT_ENABLED:
            return RateLimitResult(
                allowed=True,
                current_count=0,
                limit=RATE_LIMIT_DAILY_QUERIES,
                remaining=RATE_LIMIT_DAILY_QUERIES,
                reset_at=RateLimitService._get_tomorrow(),
            )
        
        redis_client = _get_redis_client()
        
        if redis_client is None:
            # Fallback: allow all requests if Redis unavailable
            logger.warning("Redis unavailable, allowing request (fallback mode)")
            return RateLimitResult(
                allowed=True,
                current_count=0,
                limit=RATE_LIMIT_DAILY_QUERIES,
                remaining=RATE_LIMIT_DAILY_QUERIES,
                reset_at=RateLimitService._get_tomorrow(),
            )
        
        try:
            key = RateLimitService._get_key(user_id)
            current_count = redis_client.get(key)
            current_count = int(current_count) if current_count else 0
            
            remaining = max(0, RATE_LIMIT_DAILY_QUERIES - current_count)
            allowed = current_count < RATE_LIMIT_DAILY_QUERIES
            
            return RateLimitResult(
                allowed=allowed,
                current_count=current_count,
                limit=RATE_LIMIT_DAILY_QUERIES,
                remaining=remaining,
                reset_at=RateLimitService._get_tomorrow(),
            )
            
        except redis.RedisError as e:
            logger.error(f"Redis error in check_rate_limit: {e}")
            # Fallback: allow request
            return RateLimitResult(
                allowed=True,
                current_count=0,
                limit=RATE_LIMIT_DAILY_QUERIES,
                remaining=RATE_LIMIT_DAILY_QUERIES,
                reset_at=RateLimitService._get_tomorrow(),
            )
    
    @staticmethod
    def check_and_increment(user_id: UUID) -> RateLimitResult:
        """
        Check rate limit and increment counter atomically.
        
        This is the main method to call before processing a query.
        
        Args:
            user_id: User UUID
            
        Returns:
            RateLimitResult with updated status
            
        Note:
            The counter is incremented even if limit is exceeded,
            but `allowed` will be False in that case.
        """
        if not RATE_LIMIT_ENABLED:
            return RateLimitResult(
                allowed=True,
                current_count=0,
                limit=RATE_LIMIT_DAILY_QUERIES,
                remaining=RATE_LIMIT_DAILY_QUERIES,
                reset_at=RateLimitService._get_tomorrow(),
            )
        
        redis_client = _get_redis_client()
        
        if redis_client is None:
            # Fallback: allow all requests if Redis unavailable
            logger.warning("Redis unavailable, allowing request (fallback mode)")
            return RateLimitResult(
                allowed=True,
                current_count=0,
                limit=RATE_LIMIT_DAILY_QUERIES,
                remaining=RATE_LIMIT_DAILY_QUERIES,
                reset_at=RateLimitService._get_tomorrow(),
            )
        
        try:
            key = RateLimitService._get_key(user_id)
            
            # Use pipeline for atomic increment + TTL set
            pipe = redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, RATE_LIMIT_TTL_SECONDS)
            results = pipe.execute()
            
            new_count = results[0]  # Result of INCR
            
            # Check if this request exceeds the limit
            # Note: We increment first, then check, so new_count is post-increment
            allowed = new_count <= RATE_LIMIT_DAILY_QUERIES
            remaining = max(0, RATE_LIMIT_DAILY_QUERIES - new_count)
            
            if not allowed:
                logger.warning(
                    f"🚫 Rate limit exceeded for user {user_id}: "
                    f"{new_count}/{RATE_LIMIT_DAILY_QUERIES} queries today"
                )
            else:
                logger.debug(
                    f"📊 Rate limit: user {user_id} - "
                    f"{new_count}/{RATE_LIMIT_DAILY_QUERIES} queries today"
                )
            
            return RateLimitResult(
                allowed=allowed,
                current_count=new_count,
                limit=RATE_LIMIT_DAILY_QUERIES,
                remaining=remaining,
                reset_at=RateLimitService._get_tomorrow(),
            )
            
        except redis.RedisError as e:
            logger.error(f"Redis error in check_and_increment: {e}")
            # Fallback: allow request but log error
            return RateLimitResult(
                allowed=True,
                current_count=0,
                limit=RATE_LIMIT_DAILY_QUERIES,
                remaining=RATE_LIMIT_DAILY_QUERIES,
                reset_at=RateLimitService._get_tomorrow(),
            )
    
    @staticmethod
    def get_usage(user_id: UUID) -> dict:
        """
        Get current usage info for a user (for API response).
        
        Returns:
            Dict with usage info suitable for API response
        """
        result = RateLimitService.check_rate_limit(user_id)
        return {
            "daily_queries_used": result.current_count,
            "daily_queries_limit": result.limit,
            "daily_queries_remaining": result.remaining,
            "resets_at": result.reset_at,
        }
    
    @staticmethod
    def reset_user_limit(user_id: UUID) -> bool:
        """
        Reset a user's rate limit (admin function).
        
        Args:
            user_id: User UUID to reset
            
        Returns:
            True if reset successful, False otherwise
        """
        redis_client = _get_redis_client()
        
        if redis_client is None:
            return False
        
        try:
            key = RateLimitService._get_key(user_id)
            redis_client.delete(key)
            logger.info(f"🔄 Rate limit reset for user {user_id}")
            return True
        except redis.RedisError as e:
            logger.error(f"Failed to reset rate limit: {e}")
            return False
