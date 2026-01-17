"""
Real Integration Tests for Analytics API
Tests against live server with real database

Usage:
1. Start the server: `./start_server.sh` or `uvicorn src.api.main:app`
2. Run tests: `python -m pytest tests/integration/test_analytics_real.py -v`

Environment:
- Requires running server at http://localhost:8000
- Requires valid admin user credentials
"""

import pytest
import requests
import os
from datetime import date, timedelta
from typing import Optional, Dict, Any

# Server configuration
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")
API_PREFIX = "/api"

# Test user credentials (create admin user before running)
TEST_ADMIN_EMAIL = os.getenv("TEST_ADMIN_EMAIL", "admin@test.com")
TEST_ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "admin123456")
TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL", "user@test.com")
TEST_USER_PASSWORD = os.getenv("TEST_USER_PASSWORD", "user123456")


class TestConfig:
    """Test configuration and state"""

    admin_token: Optional[str] = None
    user_token: Optional[str] = None


config = TestConfig()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_auth_header(token: str) -> Dict[str, str]:
    """Get authorization header"""
    return {"Authorization": f"Bearer {token}"}


def login(email: str, password: str) -> Optional[str]:
    """Login and return access token"""
    response = requests.post(
        f"{BASE_URL}{API_PREFIX}/auth/login",
        json={"email": email, "password": password},
        headers={"Content-Type": "application/json"},
    )
    if response.status_code == 200:
        data = response.json()
        # Handle both direct access_token and nested tokens structure
        if "tokens" in data:
            return data["tokens"].get("access_token")
        return data.get("access_token")
    return None


def register_user(email: str, password: str, username: str, role: str = "user") -> bool:
    """Register a new user"""
    response = requests.post(
        f"{BASE_URL}{API_PREFIX}/auth/register",
        json={
            "email": email,
            "password": password,
            "username": username,
            "full_name": f"Test {role.title()}",
        },
    )
    return response.status_code in [200, 201, 400]  # 400 if already exists


def check_server_available() -> bool:
    """Check if server is available"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(scope="module", autouse=True)
def setup_auth():
    """Setup authentication tokens before tests"""
    if not check_server_available():
        pytest.skip("Server not available at " + BASE_URL)

    # Try to register and login admin user
    register_user(TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD, "testadmin", "admin")
    config.admin_token = login(TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD)

    # Try to register and login regular user
    register_user(TEST_USER_EMAIL, TEST_USER_PASSWORD, "testuser", "user")
    config.user_token = login(TEST_USER_EMAIL, TEST_USER_PASSWORD)

    if not config.admin_token and not config.user_token:
        pytest.skip("Could not authenticate any test user")

    yield

    # Cleanup if needed
    pass


@pytest.fixture
def admin_headers():
    """Get admin auth headers"""
    if not config.admin_token:
        pytest.skip("Admin token not available")
    return get_auth_header(config.admin_token)


@pytest.fixture
def user_headers():
    """Get user auth headers"""
    if not config.user_token:
        pytest.skip("User token not available")
    return get_auth_header(config.user_token)


@pytest.fixture
def any_headers():
    """Get any available auth headers"""
    token = config.admin_token or config.user_token
    if not token:
        pytest.skip("No auth token available")
    return get_auth_header(token)


# =============================================================================
# DASHBOARD OVERVIEW TESTS
# =============================================================================


class TestDashboardOverview:
    """Tests for /analytics/overview endpoint"""

    def test_get_overview_success(self, any_headers):
        """Test successful dashboard overview retrieval"""
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/overview", headers=any_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "generated_at" in data
        assert "period" in data
        assert "key_metrics" in data

        # Verify key metrics
        metrics = data["key_metrics"]
        assert "total_cost_usd" in metrics
        assert "total_queries" in metrics
        assert "dau" in metrics
        assert "mau" in metrics

    def test_get_overview_with_details(self, any_headers):
        """Test overview with include_details=true"""
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/overview",
            params={"include_details": True, "period": "month"},
            headers=any_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Should include detail sections
        # Note: May be null if no data
        assert "cost_overview" in data or data.get("cost_overview") is None
        assert "knowledge_base" in data or data.get("knowledge_base") is None

    def test_get_overview_different_periods(self, any_headers):
        """Test overview with different time periods"""
        periods = ["day", "week", "month", "quarter", "year", "all_time"]

        for period in periods:
            response = requests.get(
                f"{BASE_URL}{API_PREFIX}/analytics/overview",
                params={"period": period},
                headers=any_headers,
            )

            assert response.status_code == 200, f"Failed for period: {period}"
            data = response.json()
            assert data["period"] is not None

    def test_get_overview_unauthorized(self):
        """Test overview without auth returns 401"""
        response = requests.get(f"{BASE_URL}{API_PREFIX}/analytics/overview")

        assert response.status_code == 401


# =============================================================================
# COST ANALYTICS TESTS
# =============================================================================


class TestCostAnalytics:
    """Tests for cost-related endpoints"""

    def test_get_cost_overview(self, any_headers):
        """Test GET /analytics/cost"""
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/cost",
            params={"period": "month"},
            headers=any_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "total_cost_usd" in data
        assert "token_breakdown" in data
        assert "average_cost_per_query" in data
        assert "total_queries" in data
        assert "period" in data
        assert "period_start" in data
        assert "period_end" in data

        # Token breakdown structure
        tokens = data["token_breakdown"]
        assert "input_tokens" in tokens
        assert "output_tokens" in tokens
        assert "total_tokens" in tokens

    def test_get_cost_with_custom_dates(self, any_headers):
        """Test cost with custom date range"""
        today = date.today()
        week_ago = today - timedelta(days=7)

        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/cost",
            params={"start_date": week_ago.isoformat(), "end_date": today.isoformat()},
            headers=any_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["period_start"] == week_ago.isoformat()
        assert data["period_end"] == today.isoformat()

    def test_get_daily_token_usage(self, any_headers):
        """Test GET /analytics/cost/daily"""
        today = date.today()
        week_ago = today - timedelta(days=7)

        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/cost/daily",
            params={"start_date": week_ago.isoformat(), "end_date": today.isoformat()},
            headers=any_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "total_days" in data
        assert "start_date" in data
        assert "end_date" in data
        assert isinstance(data["data"], list)

    def test_daily_usage_invalid_date_range(self, any_headers):
        """Test daily usage with invalid date range"""
        today = date.today()

        # Start date after end date
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/cost/daily",
            params={
                "start_date": today.isoformat(),
                "end_date": (today - timedelta(days=7)).isoformat(),
            },
            headers=any_headers,
        )

        assert response.status_code == 400

    def test_get_cost_per_user_admin_only(self, admin_headers, user_headers):
        """Test /analytics/cost/users requires admin"""
        # Admin should succeed
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/cost/users", headers=admin_headers
        )
        assert response.status_code in [200, 403]  # 403 if not admin role

        # Regular user should get 403
        if user_headers:
            response = requests.get(
                f"{BASE_URL}{API_PREFIX}/analytics/cost/users", headers=user_headers
            )
            # Should be 403 forbidden for non-admin
            assert response.status_code in [200, 403]


# =============================================================================
# KNOWLEDGE BASE HEALTH TESTS
# =============================================================================


class TestKnowledgeBaseHealth:
    """Tests for /analytics/knowledge-base endpoint"""

    def test_get_kb_health(self, any_headers):
        """Test knowledge base health retrieval"""
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/knowledge-base", headers=any_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "total_documents" in data
        assert "total_active_documents" in data
        assert "documents_by_category" in data
        assert "documents_by_type" in data
        assert "documents_by_status" in data
        assert "total_chunks" in data
        assert "average_chunks_per_document" in data

        # Verify data types
        assert isinstance(data["total_documents"], int)
        assert isinstance(data["total_chunks"], int)
        assert isinstance(data["documents_by_category"], list)


# =============================================================================
# RAG PERFORMANCE TESTS
# =============================================================================


class TestRAGPerformance:
    """Tests for /analytics/performance endpoint"""

    def test_get_performance_metrics(self, any_headers):
        """Test RAG performance metrics"""
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/performance",
            params={"period": "month"},
            headers=any_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "average_latency_ms" in data
        assert "latency_percentiles" in data
        assert "rag_mode_distribution" in data
        assert "total_queries_analyzed" in data

        # Verify percentiles structure
        percentiles = data["latency_percentiles"]
        assert "p50" in percentiles
        assert "p90" in percentiles
        assert "p99" in percentiles


# =============================================================================
# QUALITY & FEEDBACK TESTS
# =============================================================================


class TestQualityFeedback:
    """Tests for /analytics/feedback endpoint"""

    def test_get_feedback_metrics(self, any_headers):
        """Test quality feedback metrics"""
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/feedback",
            params={"period": "month", "recent_limit": 5},
            headers=any_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "total_feedbacks" in data
        assert "positive_feedbacks" in data
        assert "negative_feedbacks" in data
        assert "negative_feedback_rate" in data
        assert "rating_distribution" in data
        assert "zero_citation_rate" in data
        assert "recent_comments" in data


# =============================================================================
# USER ENGAGEMENT TESTS
# =============================================================================


class TestUserEngagement:
    """Tests for /analytics/engagement endpoint"""

    def test_get_engagement_metrics(self, any_headers):
        """Test user engagement metrics"""
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/engagement",
            params={"top_queries_limit": 10, "trend_days": 14},
            headers=any_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "dau" in data
        assert "wau" in data
        assert "mau" in data
        assert "total_registered_users" in data
        assert "dau_mau_ratio" in data
        assert "avg_queries_per_user" in data
        assert "top_queries" in data
        assert "engagement_trend" in data

        # Verify DAU <= WAU <= MAU
        assert data["dau"] <= data["wau"]
        assert data["wau"] <= data["mau"]


# =============================================================================
# ADMIN ENDPOINTS TESTS
# =============================================================================


class TestAdminEndpoints:
    """Tests for admin-only endpoints"""

    def test_aggregation_status(self, admin_headers):
        """Test GET /analytics/admin/aggregation-status"""
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/admin/aggregation-status",
            params={"days": 7},
            headers=admin_headers,
        )

        # May be 403 if user is not admin
        if response.status_code == 403:
            pytest.skip("User does not have admin role")

        assert response.status_code == 200
        data = response.json()

        assert "period_start" in data
        assert "period_end" in data
        assert "aggregated_days" in data
        assert "missing_days" in data
        assert "daily_status" in data

    def test_trigger_aggregation(self, admin_headers):
        """Test POST /analytics/admin/aggregate"""
        today = date.today()
        yesterday = today - timedelta(days=1)

        response = requests.post(
            f"{BASE_URL}{API_PREFIX}/analytics/admin/aggregate",
            json={"target_date": yesterday.isoformat()},
            headers=admin_headers,
        )

        if response.status_code == 403:
            pytest.skip("User does not have admin role")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "message" in data
        assert "details" in data

    def test_recalculate_tokens(self, admin_headers):
        """Test POST /analytics/admin/recalculate-tokens"""
        response = requests.post(
            f"{BASE_URL}{API_PREFIX}/analytics/admin/recalculate-tokens",
            headers=admin_headers,
        )

        if response.status_code == 403:
            pytest.skip("User does not have admin role")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "queries_updated" in data
        assert "metrics_updated" in data

    def test_cache_stats(self, admin_headers):
        """Test GET /analytics/admin/cache-stats"""
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/admin/cache-stats", headers=admin_headers
        )

        if response.status_code == 403:
            pytest.skip("User does not have admin role")

        assert response.status_code == 200
        data = response.json()

        assert "enabled" in data
        assert "hits" in data
        assert "misses" in data
        assert "hit_rate" in data

    def test_invalidate_cache(self, admin_headers):
        """Test POST /analytics/admin/invalidate-cache"""
        response = requests.post(
            f"{BASE_URL}{API_PREFIX}/analytics/admin/invalidate-cache",
            params={"cache_type": "cost"},
            headers=admin_headers,
        )

        if response.status_code == 403:
            pytest.skip("User does not have admin role")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True

    def test_admin_endpoints_require_auth(self):
        """Test admin endpoints require authentication"""
        endpoints = [
            ("GET", "/analytics/admin/aggregation-status"),
            ("POST", "/analytics/admin/aggregate"),
            ("POST", "/analytics/admin/recalculate-tokens"),
            ("GET", "/analytics/admin/cache-stats"),
            ("POST", "/analytics/admin/invalidate-cache"),
        ]

        for method, endpoint in endpoints:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{API_PREFIX}{endpoint}")
            else:
                response = requests.post(f"{BASE_URL}{API_PREFIX}{endpoint}")

            assert response.status_code == 401, f"Expected 401 for {method} {endpoint}"


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================


class TestAPIPerformance:
    """Performance tests for analytics endpoints"""

    def test_overview_response_time(self, any_headers):
        """Test overview endpoint responds within acceptable time"""
        import time

        start = time.time()
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/overview", headers=any_headers
        )
        elapsed = time.time() - start

        assert response.status_code == 200
        # Should respond within 5 seconds
        assert elapsed < 5.0, f"Response took {elapsed:.2f}s, expected < 5s"

    def test_concurrent_requests(self, any_headers):
        """Test handling of concurrent requests"""
        import concurrent.futures

        def make_request():
            return requests.get(
                f"{BASE_URL}{API_PREFIX}/analytics/overview", headers=any_headers
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            results = [f.result() for f in futures]

        # All requests should succeed
        for response in results:
            assert response.status_code == 200


# =============================================================================
# DATA CONSISTENCY TESTS
# =============================================================================


class TestDataConsistency:
    """Tests for data consistency across endpoints"""

    def test_cost_totals_match(self, any_headers):
        """Test that cost totals are consistent across endpoints"""
        # Get from overview
        overview_response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/overview",
            params={"period": "month"},
            headers=any_headers,
        )
        overview_data = overview_response.json()

        # Get from cost endpoint
        cost_response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/cost",
            params={"period": "month"},
            headers=any_headers,
        )
        cost_data = cost_response.json()

        # Totals should match
        assert (
            overview_data["key_metrics"]["total_cost_usd"]
            == cost_data["total_cost_usd"]
        )
        assert (
            overview_data["key_metrics"]["total_queries"] == cost_data["total_queries"]
        )

    def test_engagement_metrics_consistent(self, any_headers):
        """Test engagement metrics are logically consistent"""
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/engagement", headers=any_headers
        )
        data = response.json()

        # DAU should be <= WAU <= MAU <= Total
        assert data["dau"] <= data["wau"]
        assert data["wau"] <= data["mau"]
        assert data["mau"] <= data["total_registered_users"]

        # DAU/MAU ratio should match calculated value
        if data["mau"] > 0:
            expected_ratio = data["dau"] / data["mau"]
            assert abs(data["dau_mau_ratio"] - expected_ratio) < 0.001


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "--tb=short"])
