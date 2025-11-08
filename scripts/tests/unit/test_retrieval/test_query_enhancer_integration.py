"""
Integration test for QueryEnhancer
"""

import pytest
from unittest.mock import patch, Mock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.retrieval.query_processing import (
    QueryEnhancer,
    QueryEnhancerConfig,
    EnhancementStrategy,
)


@pytest.fixture
def mock_openai_key():
    """Mock OpenAI API key"""
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key-12345"}):
        yield


def test_enhancer_initialization(mock_openai_key):
    """Test basic initialization"""
    config = QueryEnhancerConfig(
        strategies=[EnhancementStrategy.MULTI_QUERY], max_queries=3
    )

    enhancer = QueryEnhancer(config)

    assert len(enhancer.strategies) == 1
    assert EnhancementStrategy.MULTI_QUERY in enhancer.strategies
    assert enhancer.cache is not None


def test_multi_strategy_initialization(mock_openai_key):
    """Test with multiple strategies"""
    config = QueryEnhancerConfig(
        strategies=[
            EnhancementStrategy.MULTI_QUERY,
            EnhancementStrategy.HYDE,
            EnhancementStrategy.STEP_BACK,
        ]
    )

    enhancer = QueryEnhancer(config)

    assert len(enhancer.strategies) == 3


def test_deduplication():
    """Test deduplication logic"""
    config = QueryEnhancerConfig(strategies=[])
    enhancer = QueryEnhancer(config)

    queries = [
        "Query 1",
        "Query 2",
        "query 1",  # Duplicate (case insensitive)
        "Query 3",
        "Query 2",  # Duplicate
        "  Query 3  ",  # Duplicate (with whitespace)
    ]

    result = enhancer._deduplicate(queries)

    assert len(result) == 3
    assert "Query 1" in result
    assert "Query 2" in result
    assert "Query 3" in result


def test_cache_functionality(mock_openai_key):
    """Test caching works"""
    config = QueryEnhancerConfig(
        strategies=[EnhancementStrategy.MULTI_QUERY], enable_caching=True
    )

    enhancer = QueryEnhancer(config)

    # Mock strategy response
    for strategy in enhancer.strategies.values():
        strategy.client = Mock()
        mock_resp = Mock()
        mock_resp.content = "Enhanced 1\nEnhanced 2"
        strategy.client.invoke.return_value = mock_resp

    query = "Test query"

    # First call
    result1 = enhancer.enhance(query)

    # Should be in cache
    assert query in enhancer.cache

    # Second call (from cache)
    result2 = enhancer.enhance(query)

    assert result1 == result2


def test_empty_query_handling():
    """Test empty query handling"""
    config = QueryEnhancerConfig(strategies=[])
    enhancer = QueryEnhancer(config)

    assert enhancer.enhance("") == [""]
    assert enhancer.enhance("   ") == ["   "]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
