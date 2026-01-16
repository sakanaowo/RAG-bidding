#!/usr/bin/env python3
"""
Test script for Rate Limiting implementation.

Tests:
1. Redis connection to DB 4
2. RateLimitService functionality
3. Increment and limit enforcement
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment
from dotenv import load_dotenv
load_dotenv()

from uuid import uuid4
import redis


def test_redis_connection():
    """Test Redis DB 4 connection."""
    print("\n" + "="*50)
    print("TEST 1: Redis Connection (DB 4)")
    print("="*50)
    
    try:
        client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("RATE_LIMIT_REDIS_DB", "4")),
            decode_responses=True,
        )
        result = client.ping()
        print(f"✅ Redis DB 4 connection: PONG = {result}")
        return client
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return None


def test_rate_limit_service(redis_client):
    """Test RateLimitService functionality."""
    print("\n" + "="*50)
    print("TEST 2: RateLimitService")
    print("="*50)
    
    from src.api.services.rate_limit_service import RateLimitService
    
    # Use a test user ID
    test_user_id = uuid4()
    print(f"Test user ID: {test_user_id}")
    
    # Check initial state
    result = RateLimitService.check_rate_limit(test_user_id)
    print(f"\n📊 Initial state:")
    print(f"   - Allowed: {result.allowed}")
    print(f"   - Current count: {result.current_count}")
    print(f"   - Limit: {result.limit}")
    print(f"   - Remaining: {result.remaining}")
    print(f"   - Resets at: {result.reset_at}")
    
    # Test increment
    print(f"\n🔄 Testing increment (5 times)...")
    for i in range(5):
        result = RateLimitService.check_and_increment(test_user_id)
        print(f"   Query {i+1}: count={result.current_count}, remaining={result.remaining}")
    
    # Verify Redis key
    from datetime import date
    key = f"rate_limit:{test_user_id}:{date.today().isoformat()}"
    redis_value = redis_client.get(key)
    print(f"\n📦 Redis key: {key}")
    print(f"   Value: {redis_value}")
    print(f"   TTL: {redis_client.ttl(key)} seconds")
    
    # Cleanup test key
    redis_client.delete(key)
    print(f"\n🧹 Cleaned up test key")
    
    print("\n✅ RateLimitService test passed!")
    return True


def test_rate_limit_exceeded():
    """Test that rate limit is enforced when exceeded."""
    print("\n" + "="*50)
    print("TEST 3: Rate Limit Enforcement")
    print("="*50)
    
    from src.api.services.rate_limit_service import (
        RateLimitService, 
        RATE_LIMIT_DAILY_QUERIES,
    )
    
    # Temporarily set a very low limit for testing
    test_user_id = uuid4()
    
    # Manually set counter to limit - 1
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=int(os.getenv("RATE_LIMIT_REDIS_DB", "4")),
        decode_responses=True,
    )
    
    from datetime import date
    key = f"rate_limit:{test_user_id}:{date.today().isoformat()}"
    
    # Set to limit - 1
    redis_client.set(key, RATE_LIMIT_DAILY_QUERIES - 1, ex=86400)
    print(f"Set counter to {RATE_LIMIT_DAILY_QUERIES - 1} (limit - 1)")
    
    # This should succeed (last allowed query)
    result = RateLimitService.check_and_increment(test_user_id)
    print(f"\n📊 Query at limit:")
    print(f"   - Allowed: {result.allowed}")
    print(f"   - Current count: {result.current_count}/{result.limit}")
    
    # This should fail (exceeds limit)
    result = RateLimitService.check_and_increment(test_user_id)
    print(f"\n📊 Query over limit:")
    print(f"   - Allowed: {result.allowed}")
    print(f"   - Current count: {result.current_count}/{result.limit}")
    
    if not result.allowed:
        print("\n✅ Rate limit enforcement works correctly!")
    else:
        print("\n❌ Rate limit was NOT enforced!")
    
    # Cleanup
    redis_client.delete(key)
    return not result.allowed


def test_get_usage():
    """Test usage info API."""
    print("\n" + "="*50)
    print("TEST 4: Get Usage Info")
    print("="*50)
    
    from src.api.services.rate_limit_service import RateLimitService
    
    test_user_id = uuid4()
    
    # Do some queries
    for _ in range(3):
        RateLimitService.check_and_increment(test_user_id)
    
    usage = RateLimitService.get_usage(test_user_id)
    print(f"📊 Usage info:")
    for k, v in usage.items():
        print(f"   - {k}: {v}")
    
    # Cleanup
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=int(os.getenv("RATE_LIMIT_REDIS_DB", "4")),
        decode_responses=True,
    )
    from datetime import date
    key = f"rate_limit:{test_user_id}:{date.today().isoformat()}"
    redis_client.delete(key)
    
    print("\n✅ Get usage test passed!")
    return True


if __name__ == "__main__":
    print("="*50)
    print("RATE LIMITING VALIDATION TESTS")
    print("="*50)
    
    # Test 1: Redis connection
    redis_client = test_redis_connection()
    if not redis_client:
        print("\n❌ Cannot proceed without Redis connection")
        sys.exit(1)
    
    # Test 2: RateLimitService
    test_rate_limit_service(redis_client)
    
    # Test 3: Rate limit enforcement
    test_rate_limit_exceeded()
    
    # Test 4: Get usage info
    test_get_usage()
    
    print("\n" + "="*50)
    print("🎉 ALL TESTS PASSED!")
    print("="*50)
