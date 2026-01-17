"""
Pytest Configuration and Fixtures
Shared fixtures for all tests

Supports both:
- Unit tests: Using mocked objects and SQLite (fast)
- Integration tests: Using PostgreSQL (when available)
"""

import pytest
import sys
import os
from datetime import date, datetime, timedelta
from uuid import uuid4
from decimal import Decimal
from typing import Generator
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests (fast, mocked)")
    config.addinivalue_line(
        "markers", "integration: Integration tests (require database)"
    )
    config.addinivalue_line("markers", "slow: Slow tests that take > 1 second")
    config.addinivalue_line("markers", "api: API endpoint tests")
    config.addinivalue_line("markers", "requires_postgres: Tests requiring PostgreSQL")


# =============================================================================
# ENVIRONMENT DETECTION
# =============================================================================


def is_postgres_available() -> bool:
    """Check if PostgreSQL database is available for testing."""
    return bool(os.environ.get("DATABASE_URL") or os.environ.get("TEST_DATABASE_URL"))


# =============================================================================
# MOCK FIXTURES FOR UNIT TESTS
# =============================================================================


@pytest.fixture
def mock_user():
    """Create a mock user for unit tests"""
    user = MagicMock()
    user.id = uuid4()
    user.email = "test@example.com"
    user.username = "testuser"
    user.full_name = "Test User"
    user.role = "admin"
    user.is_active = True
    user.is_verified = True
    user.deleted_at = None
    return user


@pytest.fixture
def mock_regular_user():
    """Create a mock regular (non-admin) user for unit tests"""
    user = MagicMock()
    user.id = uuid4()
    user.email = "user@example.com"
    user.username = "regularuser"
    user.full_name = "Regular User"
    user.role = "user"
    user.is_active = True
    user.is_verified = True
    user.deleted_at = None
    return user


@pytest.fixture
def mock_db_session():
    """Create a mock database session for unit tests"""
    session = MagicMock()
    session.query.return_value = session
    session.filter.return_value = session
    session.all.return_value = []
    session.first.return_value = None
    session.scalar.return_value = None
    session.count.return_value = 0
    return session


@pytest.fixture
def mock_document():
    """Create a mock document for unit tests"""
    doc = MagicMock()
    doc.id = uuid4()
    doc.document_id = "DOC-001"
    doc.document_name = "Test Document"
    doc.filename = "test.pdf"
    doc.category = "Luat chinh"
    doc.document_type = "law"
    doc.status = "active"
    doc.total_chunks = 10
    doc.created_at = datetime.now()
    doc.updated_at = datetime.now()
    return doc


@pytest.fixture
def mock_query():
    """Create a mock query for unit tests"""
    query = MagicMock()
    query.id = uuid4()
    query.user_id = uuid4()
    query.query_text = "Test query"
    query.query_hash = "hash123"
    query.rag_mode = "balanced"
    query.retrieval_count = 5
    query.total_latency_ms = 1500
    query.tokens_total = 800
    query.input_tokens = 640
    query.output_tokens = 160
    query.estimated_cost_usd = Decimal("0.015")
    query.created_at = datetime.now()
    return query


@pytest.fixture
def mock_feedback():
    """Create a mock feedback for unit tests"""
    feedback = MagicMock()
    feedback.id = uuid4()
    feedback.user_id = uuid4()
    feedback.message_id = uuid4()
    feedback.rating = 4
    feedback.feedback_type = "helpfulness"
    feedback.comment = "Helpful response"
    feedback.created_at = datetime.now()
    return feedback


@pytest.fixture
def mock_usage_metric():
    """Create a mock usage metric for unit tests"""
    metric = MagicMock()
    metric.id = uuid4()
    metric.user_id = uuid4()
    metric.date = date.today()
    metric.total_queries = 15
    metric.total_messages = 30
    metric.total_tokens = 8000
    metric.total_input_tokens = 6400
    metric.total_output_tokens = 1600
    metric.total_cost_usd = Decimal("0.80")
    metric.categories_accessed = ["Luat chinh", "Nghi dinh"]
    metric.created_at = datetime.now()
    return metric


# =============================================================================
# FIXTURES FOR TESTING ANALYTICS SERVICE
# =============================================================================


@pytest.fixture
def sample_cost_data():
    """Sample data for cost overview tests"""
    return {
        "total_cost": Decimal("12.50"),
        "total_tokens": 50000,
        "input_tokens": 40000,
        "output_tokens": 10000,
        "query_count": 100,
        "conv_count": 25,
    }


@pytest.fixture
def sample_daily_usage_data():
    """Sample data for daily usage tests"""
    today = date.today()
    return [
        {
            "date": today - timedelta(days=i),
            "total_tokens": 5000 + i * 500,
            "input_tokens": 4000 + i * 400,
            "output_tokens": 1000 + i * 100,
            "total_cost": Decimal(f"{0.50 + i * 0.1:.2f}"),
            "query_count": 20 + i * 2,
        }
        for i in range(7)
    ]


@pytest.fixture
def sample_kb_health_data():
    """Sample data for knowledge base health tests"""
    return {
        "total_documents": 150,
        "active_documents": 140,
        "categories": [
            {"name": "Luat chinh", "count": 50},
            {"name": "Nghi dinh", "count": 40},
            {"name": "Thong tu", "count": 30},
            {"name": "Quyet dinh", "count": 20},
            {"name": "Mau bao cao", "count": 10},
        ],
        "total_chunks": 3500,
    }


@pytest.fixture
def sample_rag_performance_data():
    """Sample data for RAG performance tests"""
    return {
        "avg_latency_ms": 1850.5,
        "p50": 1500.0,
        "p75": 2000.0,
        "p90": 2500.0,
        "p95": 3000.0,
        "p99": 4000.0,
        "mode_distribution": [
            {"mode": "balanced", "count": 500, "percentage": 50.0},
            {"mode": "fast", "count": 300, "percentage": 30.0},
            {"mode": "quality", "count": 200, "percentage": 20.0},
        ],
    }


@pytest.fixture
def sample_feedback_data():
    """Sample data for feedback tests"""
    return {
        "total_feedbacks": 250,
        "positive": 200,
        "negative": 30,
        "neutral": 20,
        "csat_score": 4.2,
        "rating_distribution": [
            {"rating": 5, "count": 120},
            {"rating": 4, "count": 80},
            {"rating": 3, "count": 20},
            {"rating": 2, "count": 15},
            {"rating": 1, "count": 15},
        ],
    }


@pytest.fixture
def sample_engagement_data():
    """Sample data for engagement tests"""
    return {
        "dau": 45,
        "wau": 150,
        "mau": 350,
        "total_users": 500,
        "avg_queries_per_user": 12.5,
        "top_queries": [
            {"query": "quy trinh dau thau", "count": 85},
            {"query": "ho so moi thau", "count": 72},
            {"query": "luat dau thau 2023", "count": 65},
        ],
    }


# =============================================================================
# CACHE TESTING FIXTURES
# =============================================================================


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client for cache testing"""
    redis = MagicMock()
    redis.get.return_value = None
    redis.setex.return_value = True
    redis.delete.return_value = True
    redis.scan_iter.return_value = iter([])
    return redis


@pytest.fixture
def cache_service_with_mock_redis(mock_redis_client):
    """Create cache service with mock Redis"""
    from src.api.services.analytics_cache import SyncAnalyticsCacheService

    return SyncAnalyticsCacheService(mock_redis_client)


@pytest.fixture
def cache_service_disabled():
    """Create disabled cache service (no Redis)"""
    from src.api.services.analytics_cache import SyncAnalyticsCacheService

    return SyncAnalyticsCacheService(None)


# =============================================================================
# METRICS AGGREGATOR TESTING FIXTURES
# =============================================================================


@pytest.fixture
def mock_aggregator_db_session():
    """Create mock session for metrics aggregator tests"""
    session = MagicMock()

    # Mock query chain
    query_mock = MagicMock()
    query_mock.filter.return_value = query_mock
    query_mock.group_by.return_value = query_mock
    query_mock.order_by.return_value = query_mock
    query_mock.all.return_value = []
    query_mock.first.return_value = MagicMock(
        query_count=10,
        total_tokens=5000,
        input_tokens=4000,
        output_tokens=1000,
        total_cost=Decimal("0.50"),
    )
    query_mock.scalar.return_value = 5

    session.query.return_value = query_mock
    session.add = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.execute = MagicMock(return_value=MagicMock(rowcount=10))

    return session


# =============================================================================
# UTILITY FIXTURES
# =============================================================================


@pytest.fixture
def today():
    """Get today's date"""
    return date.today()


@pytest.fixture
def week_ago():
    """Get date from a week ago"""
    return date.today() - timedelta(days=7)


@pytest.fixture
def month_ago():
    """Get date from a month ago"""
    return date.today() - timedelta(days=30)


@pytest.fixture
def sample_uuid():
    """Generate a sample UUID"""
    return uuid4()
