"""
Unit Tests for Analytics Cache Service
Tests caching functionality with mocked Redis
"""

import pytest
import json
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from src.api.services.analytics_cache import (
    SyncAnalyticsCacheService,
    CacheKeyPrefix,
    CacheTTL,
)
from src.api.schemas.analytics_schemas import TimePeriod


class TestCacheKeyGeneration:
    """Tests for cache key generation"""

    def test_generate_key_no_params(self, cache_service_disabled):
        """Test key generation without parameters"""
        key = cache_service_disabled._generate_key(CacheKeyPrefix.COST_OVERVIEW)
        assert key == "analytics:cost:overview"

    def test_generate_key_with_params(self, cache_service_disabled):
        """Test key generation with parameters"""
        key = cache_service_disabled._generate_key(
            CacheKeyPrefix.COST_OVERVIEW, period="month", user_id="123"
        )
        assert "analytics:cost:overview:" in key
        assert "period:month" in key
        assert "user_id:123" in key

    def test_generate_key_with_date(self, cache_service_disabled):
        """Test key generation with date parameter"""
        test_date = date(2026, 1, 10)
        key = cache_service_disabled._generate_key(
            CacheKeyPrefix.DAILY_USAGE, start_date=test_date
        )
        assert "2026-01-10" in key

    def test_generate_key_with_enum(self, cache_service_disabled):
        """Test key generation with enum parameter"""
        key = cache_service_disabled._generate_key(
            CacheKeyPrefix.RAG_PERFORMANCE, period=TimePeriod.MONTH
        )
        assert "period:month" in key

    def test_generate_key_long_params_hashed(self, cache_service_disabled):
        """Test that long parameter strings are hashed"""
        key = cache_service_disabled._generate_key(
            CacheKeyPrefix.USER_ENGAGEMENT, param1="a" * 30, param2="b" * 30
        )
        # Key should be shortened with hash
        assert len(key) < 100


class TestCacheServiceDisabled:
    """Tests for disabled cache service"""

    def test_is_enabled_false(self, cache_service_disabled):
        """Test that cache is disabled when no Redis"""
        assert cache_service_disabled.is_enabled is False

    def test_get_returns_none(self, cache_service_disabled):
        """Test get returns None when disabled"""
        result = cache_service_disabled.get("any_key")
        assert result is None

    def test_set_returns_false(self, cache_service_disabled):
        """Test set returns False when disabled"""
        result = cache_service_disabled.set("any_key", {"data": "test"})
        assert result is False

    def test_delete_returns_false(self, cache_service_disabled):
        """Test delete returns False when disabled"""
        result = cache_service_disabled.delete("any_key")
        assert result is False

    def test_stats_empty(self, cache_service_disabled):
        """Test stats are zeros when disabled"""
        stats = cache_service_disabled.stats
        assert stats["total"] == 0
        assert stats["hit_rate"] == 0


class TestCacheServiceEnabled:
    """Tests for enabled cache service with mocked Redis"""

    def test_is_enabled_true(self, cache_service_with_mock_redis):
        """Test that cache is enabled with Redis"""
        assert cache_service_with_mock_redis.is_enabled is True

    def test_get_cache_miss(self, cache_service_with_mock_redis, mock_redis_client):
        """Test cache miss returns None"""
        mock_redis_client.get.return_value = None
        result = cache_service_with_mock_redis.get("test_key")
        assert result is None
        assert cache_service_with_mock_redis.stats["misses"] == 1

    def test_get_cache_hit(self, cache_service_with_mock_redis, mock_redis_client):
        """Test cache hit returns data"""
        cached_data = json.dumps({"total_cost": 12.50})
        mock_redis_client.get.return_value = cached_data

        result = cache_service_with_mock_redis.get("test_key")
        assert result == {"total_cost": 12.50}
        assert cache_service_with_mock_redis.stats["hits"] == 1

    def test_set_success(self, cache_service_with_mock_redis, mock_redis_client):
        """Test successful set operation"""
        mock_redis_client.setex.return_value = True

        result = cache_service_with_mock_redis.set(
            "test_key", {"data": "value"}, ttl=300
        )
        assert result is True
        mock_redis_client.setex.assert_called_once()

    def test_set_with_pydantic_model(
        self, cache_service_with_mock_redis, mock_redis_client
    ):
        """Test set with Pydantic model"""
        from src.api.schemas.analytics_schemas import TokenBreakdown

        token_data = TokenBreakdown(
            input_tokens=1000, output_tokens=200, total_tokens=1200
        )

        result = cache_service_with_mock_redis.set("test_key", token_data)
        assert result is True

        # Verify serialization was called correctly
        call_args = mock_redis_client.setex.call_args
        serialized_data = json.loads(call_args[0][2])
        assert serialized_data["input_tokens"] == 1000

    def test_delete_success(self, cache_service_with_mock_redis, mock_redis_client):
        """Test successful delete operation"""
        mock_redis_client.delete.return_value = True

        result = cache_service_with_mock_redis.delete("test_key")
        assert result is True
        mock_redis_client.delete.assert_called_once_with("test_key")

    def test_delete_pattern(self, cache_service_with_mock_redis, mock_redis_client):
        """Test delete by pattern"""
        mock_redis_client.scan_iter.return_value = iter(["key1", "key2", "key3"])

        result = cache_service_with_mock_redis.delete_pattern("test:*")
        assert result == 3
        mock_redis_client.delete.assert_called_once()

    def test_get_error_handling(self, cache_service_with_mock_redis, mock_redis_client):
        """Test error handling on get"""
        mock_redis_client.get.side_effect = Exception("Redis error")

        result = cache_service_with_mock_redis.get("test_key")
        assert result is None
        assert cache_service_with_mock_redis.stats["errors"] == 1

    def test_set_error_handling(self, cache_service_with_mock_redis, mock_redis_client):
        """Test error handling on set"""
        mock_redis_client.setex.side_effect = Exception("Redis error")

        result = cache_service_with_mock_redis.set("test_key", {"data": "value"})
        assert result is False
        assert cache_service_with_mock_redis.stats["errors"] == 1


class TestCacheSerialization:
    """Tests for cache serialization/deserialization"""

    def test_serialize_dict(self, cache_service_disabled):
        """Test serializing a dictionary"""
        data = {"key": "value", "number": 42}
        serialized = cache_service_disabled._serialize(data)
        assert json.loads(serialized) == data

    def test_serialize_datetime(self, cache_service_disabled):
        """Test serializing datetime values"""
        data = {"timestamp": datetime(2026, 1, 10, 12, 30, 45)}
        serialized = cache_service_disabled._serialize(data)
        result = json.loads(serialized)
        assert "2026-01-10" in result["timestamp"]

    def test_serialize_date(self, cache_service_disabled):
        """Test serializing date values"""
        data = {"date": date(2026, 1, 10)}
        serialized = cache_service_disabled._serialize(data)
        result = json.loads(serialized)
        assert result["date"] == "2026-01-10"

    def test_serialize_decimal(self, cache_service_disabled):
        """Test serializing Decimal values"""
        data = {"amount": Decimal("12.50")}
        serialized = cache_service_disabled._serialize(data)
        result = json.loads(serialized)
        assert result["amount"] == "12.50"

    def test_serialize_enum(self, cache_service_disabled):
        """Test serializing enum values"""
        data = {"period": TimePeriod.MONTH}
        serialized = cache_service_disabled._serialize(data)
        result = json.loads(serialized)
        assert result["period"] == "month"

    def test_serialize_nested_structure(self, cache_service_disabled):
        """Test serializing nested structures"""
        data = {
            "overview": {
                "cost": 12.50,
                "tokens": [100, 200, 300],
                "date": date(2026, 1, 10),
            }
        }
        serialized = cache_service_disabled._serialize(data)
        result = json.loads(serialized)
        assert result["overview"]["cost"] == 12.50
        assert result["overview"]["tokens"] == [100, 200, 300]


class TestCacheInvalidation:
    """Tests for cache invalidation methods"""

    def test_invalidate_cost_cache(
        self, cache_service_with_mock_redis, mock_redis_client
    ):
        """Test cost cache invalidation"""
        mock_redis_client.scan_iter.return_value = iter([])

        cache_service_with_mock_redis.invalidate_cost_cache()

        # Should call scan_iter for multiple patterns
        assert mock_redis_client.scan_iter.call_count >= 1

    def test_invalidate_kb_cache(
        self, cache_service_with_mock_redis, mock_redis_client
    ):
        """Test knowledge base cache invalidation"""
        mock_redis_client.scan_iter.return_value = iter([])

        cache_service_with_mock_redis.invalidate_kb_cache()

        assert mock_redis_client.scan_iter.call_count >= 1

    def test_invalidate_all(self, cache_service_with_mock_redis, mock_redis_client):
        """Test invalidating all caches"""
        mock_redis_client.scan_iter.return_value = iter(["key1", "key2"])

        cache_service_with_mock_redis.invalidate_all()

        mock_redis_client.scan_iter.assert_called_with(match="analytics:*")


class TestCacheStatistics:
    """Tests for cache statistics tracking"""

    def test_stats_tracking(self, cache_service_with_mock_redis, mock_redis_client):
        """Test cache statistics tracking"""
        # Simulate hits and misses
        mock_redis_client.get.return_value = json.dumps({"data": "value"})
        cache_service_with_mock_redis.get("key1")  # hit
        cache_service_with_mock_redis.get("key2")  # hit

        mock_redis_client.get.return_value = None
        cache_service_with_mock_redis.get("key3")  # miss

        stats = cache_service_with_mock_redis.stats
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["total"] == 3
        assert stats["hit_rate"] == pytest.approx(0.6667, rel=0.01)

    def test_reset_stats(self, cache_service_with_mock_redis, mock_redis_client):
        """Test resetting cache statistics"""
        mock_redis_client.get.return_value = None
        cache_service_with_mock_redis.get("key")  # miss

        cache_service_with_mock_redis.reset_stats()

        stats = cache_service_with_mock_redis.stats
        assert stats["hits"] == 0
        assert stats["misses"] == 0


class TestCacheTTLSelection:
    """Tests for TTL selection logic"""

    def test_short_ttl(self):
        """Test SHORT TTL value"""
        assert CacheTTL.SHORT == 60

    def test_medium_ttl(self):
        """Test MEDIUM TTL value"""
        assert CacheTTL.MEDIUM == 300

    def test_long_ttl(self):
        """Test LONG TTL value"""
        assert CacheTTL.LONG == 900

    def test_very_long_ttl(self):
        """Test VERY_LONG TTL value"""
        assert CacheTTL.VERY_LONG == 3600

    def test_day_ttl(self):
        """Test DAY TTL value"""
        assert CacheTTL.DAY == 86400
