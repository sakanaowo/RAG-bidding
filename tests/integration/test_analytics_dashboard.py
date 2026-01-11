"""
Integration Tests for Analytics Dashboard API
Tests against live server with real database

Credentials: admin@example.com / Admin123456

Usage:
1. Start the server: `./start_server.sh` or `uvicorn src.api.main:app`
2. Create admin user if not exists (see scripts/tests/create_test_admin.py)
3. Run tests: `pytest tests/integration/test_analytics_dashboard.py -v`
"""

import pytest
import requests
import os
from datetime import date, timedelta
from typing import Optional, Dict, Any

# =============================================================================
# CONFIGURATION
# =============================================================================

# Server configuration
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")
API_PREFIX = "/api"

# Test credentials (for internal use)
ADMIN_EMAIL = os.getenv("TEST_ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "Admin123456")

# Alternative test user (non-admin)
USER_EMAIL = os.getenv("TEST_USER_EMAIL", "user@example.com")
USER_PASSWORD = os.getenv("TEST_USER_PASSWORD", "User123456")


class TestSession:
    """Test session state"""

    admin_token: Optional[str] = None
    user_token: Optional[str] = None
    is_server_available: bool = False


session = TestSession()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_auth_header(token: str) -> Dict[str, str]:
    """Get authorization header"""
    return {"Authorization": f"Bearer {token}"}


def login(email: str, password: str) -> Optional[str]:
    """Login and return access token"""
    try:
        response = requests.post(
            f"{BASE_URL}{API_PREFIX}/auth/login",
            json={"email": email, "password": password},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            # Handle both direct access_token and nested tokens structure
            if "tokens" in data:
                return data["tokens"].get("access_token")
            return data.get("access_token")
    except Exception as e:
        print(f"Login error: {e}")
    return None


def check_server_available() -> bool:
    """Check if server is available"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


def get_user_info(token: str) -> Optional[Dict]:
    """Get current user info"""
    try:
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/auth/me",
            headers=get_auth_header(token),
            timeout=10,
        )
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(scope="module", autouse=True)
def setup_session():
    """Setup test session - authenticate and check server availability"""
    # Check server
    session.is_server_available = check_server_available()
    if not session.is_server_available:
        pytest.skip(f"Server not available at {BASE_URL}")

    # Login as admin
    session.admin_token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    if not session.admin_token:
        # Try to provide helpful message
        print(f"\n⚠️  Could not login with {ADMIN_EMAIL}")
        print("Please ensure admin user exists. Run:")
        print("  python scripts/tests/create_test_admin.py")

    # Login as regular user (optional)
    session.user_token = login(USER_EMAIL, USER_PASSWORD)

    if not session.admin_token and not session.user_token:
        pytest.skip("Could not authenticate any test user")

    yield

    # Cleanup (if needed)
    pass


@pytest.fixture
def admin_headers():
    """Get admin auth headers"""
    if not session.admin_token:
        pytest.skip("Admin token not available - admin user may not exist")
    return get_auth_header(session.admin_token)


@pytest.fixture
def user_headers():
    """Get regular user auth headers"""
    if not session.user_token:
        pytest.skip("User token not available")
    return get_auth_header(session.user_token)


@pytest.fixture
def any_auth_headers():
    """Get any available auth headers (admin preferred)"""
    token = session.admin_token or session.user_token
    if not token:
        pytest.skip("No auth token available")
    return get_auth_header(token)


# =============================================================================
# AUTHENTICATION TESTS
# =============================================================================


class TestAuthentication:
    """Tests for authentication with test credentials"""

    def test_server_is_available(self):
        """Verify server is running and accessible"""
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert data.get("db") is True, "Database connection failed"

    def test_admin_login_successful(self):
        """Test admin login with configured credentials"""
        response = requests.post(
            f"{BASE_URL}{API_PREFIX}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        if response.status_code != 200:
            pytest.skip(
                f"Admin login failed - user may not exist. Status: {response.status_code}"
            )

        data = response.json()
        assert "tokens" in data or "access_token" in data

        # Check user role
        if "user" in data:
            assert data["user"].get("role") == "admin", "User should have admin role"

    def test_admin_token_is_valid(self, admin_headers):
        """Verify admin token works for authenticated endpoint"""
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/auth/me",
            headers=admin_headers,
            timeout=10,
        )

        assert response.status_code == 200
        data = response.json()
        assert data.get("email") == ADMIN_EMAIL
        assert data.get("role") == "admin"


# =============================================================================
# DASHBOARD OVERVIEW TESTS
# =============================================================================


class TestDashboardOverview:
    """Tests for /analytics/overview endpoint"""

    def test_get_overview_success(self, any_auth_headers):
        """Test successful dashboard overview retrieval"""
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/overview",
            headers=any_auth_headers,
            timeout=30,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "generated_at" in data
        assert "period" in data
        assert "key_metrics" in data

        # Verify key metrics structure
        metrics = data["key_metrics"]
        expected_keys = ["total_cost_usd", "total_queries", "dau", "mau"]
        for key in expected_keys:
            assert key in metrics, f"Missing key: {key}"

    def test_get_overview_with_details(self, any_auth_headers):
        """Test overview with include_details=true"""
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/overview",
            params={"include_details": True, "period": "month"},
            headers=any_auth_headers,
            timeout=30,
        )

        assert response.status_code == 200
        data = response.json()

        # Should include detail sections (may be null if no data)
        assert "cost_overview" in data
        assert "knowledge_base" in data

    def test_get_overview_different_periods(self, any_auth_headers):
        """Test overview with different time periods"""
        periods = ["day", "week", "month", "all_time"]

        for period in periods:
            response = requests.get(
                f"{BASE_URL}{API_PREFIX}/analytics/overview",
                params={"period": period},
                headers=any_auth_headers,
                timeout=30,
            )

            assert response.status_code == 200, f"Failed for period: {period}"
            data = response.json()
            assert data["period"] is not None

    def test_overview_requires_auth(self):
        """Test that overview requires authentication"""
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/overview",
            timeout=10,
        )

        assert response.status_code == 401


# =============================================================================
# COST ANALYTICS TESTS
# =============================================================================


class TestCostAnalytics:
    """Tests for cost-related analytics endpoints"""

    def test_get_cost_overview(self, any_auth_headers):
        """Test GET /analytics/cost"""
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/cost",
            params={"period": "month"},
            headers=any_auth_headers,
            timeout=30,
        )

        assert response.status_code == 200
        data = response.json()

        # Required fields
        assert "total_cost_usd" in data
        assert "token_breakdown" in data
        assert "average_cost_per_query" in data
        assert "total_queries" in data
        assert "period" in data

        # Token breakdown structure
        tokens = data["token_breakdown"]
        assert "input_tokens" in tokens
        assert "output_tokens" in tokens
        assert "total_tokens" in tokens

    def test_get_cost_with_custom_dates(self, any_auth_headers):
        """Test cost with custom date range"""
        today = date.today()
        week_ago = today - timedelta(days=7)

        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/cost",
            params={
                "start_date": week_ago.isoformat(),
                "end_date": today.isoformat(),
            },
            headers=any_auth_headers,
            timeout=30,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["period_start"] == week_ago.isoformat()
        assert data["period_end"] == today.isoformat()

    def test_get_daily_token_usage(self, any_auth_headers):
        """Test GET /analytics/cost/daily"""
        today = date.today()
        week_ago = today - timedelta(days=7)

        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/cost/daily",
            params={
                "start_date": week_ago.isoformat(),
                "end_date": today.isoformat(),
            },
            headers=any_auth_headers,
            timeout=30,
        )

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "total_days" in data
        assert isinstance(data["data"], list)

    def test_daily_usage_invalid_date_range(self, any_auth_headers):
        """Test daily usage with invalid date range (start > end)"""
        today = date.today()

        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/cost/daily",
            params={
                "start_date": today.isoformat(),
                "end_date": (today - timedelta(days=7)).isoformat(),
            },
            headers=any_auth_headers,
            timeout=10,
        )

        assert response.status_code == 400

    def test_cost_per_user_admin_only(self, admin_headers):
        """Test /analytics/cost/users requires admin role"""
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/cost/users",
            params={"limit": 10},
            headers=admin_headers,
            timeout=30,
        )

        # Admin should be able to access
        assert response.status_code == 200
        data = response.json()
        assert "top_users" in data


# =============================================================================
# KNOWLEDGE BASE HEALTH TESTS
# =============================================================================


class TestKnowledgeBaseHealth:
    """Tests for /analytics/knowledge-base endpoint"""

    def test_get_kb_health(self, any_auth_headers):
        """Test knowledge base health retrieval"""
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/knowledge-base",
            headers=any_auth_headers,
            timeout=30,
        )

        assert response.status_code == 200
        data = response.json()

        # Required fields
        assert "total_documents" in data
        assert "total_active_documents" in data
        assert "documents_by_category" in data
        assert "total_chunks" in data

        # Data types
        assert isinstance(data["total_documents"], int)
        assert isinstance(data["total_chunks"], int)


# =============================================================================
# RAG PERFORMANCE TESTS
# =============================================================================


class TestRAGPerformance:
    """Tests for /analytics/performance endpoint"""

    def test_get_performance_metrics(self, any_auth_headers):
        """Test RAG performance metrics"""
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/performance",
            params={"period": "month"},
            headers=any_auth_headers,
            timeout=30,
        )

        assert response.status_code == 200
        data = response.json()

        # Required fields
        assert "average_latency_ms" in data
        assert "latency_percentiles" in data
        assert "rag_mode_distribution" in data
        assert "total_queries_analyzed" in data

        # Percentiles structure
        percentiles = data["latency_percentiles"]
        assert "p50" in percentiles
        assert "p90" in percentiles
        assert "p99" in percentiles


# =============================================================================
# QUALITY & FEEDBACK TESTS
# =============================================================================


class TestQualityFeedback:
    """Tests for /analytics/feedback endpoint"""

    def test_get_feedback_metrics(self, any_auth_headers):
        """Test quality feedback metrics"""
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/feedback",
            params={"period": "month", "recent_limit": 5},
            headers=any_auth_headers,
            timeout=30,
        )

        assert response.status_code == 200
        data = response.json()

        # Required fields
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

    def test_get_engagement_metrics(self, any_auth_headers):
        """Test user engagement metrics"""
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/engagement",
            params={"top_queries_limit": 10, "trend_days": 14},
            headers=any_auth_headers,
            timeout=30,
        )

        assert response.status_code == 200
        data = response.json()

        # Required fields
        assert "dau" in data
        assert "wau" in data
        assert "mau" in data
        assert "total_registered_users" in data
        assert "dau_mau_ratio" in data
        assert "top_queries" in data

        # Logical consistency: DAU <= WAU <= MAU
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
            timeout=30,
        )

        assert response.status_code == 200
        data = response.json()

        assert "period_start" in data
        assert "period_end" in data
        assert "aggregated_days" in data
        assert "missing_days" in data

    def test_trigger_aggregation(self, admin_headers):
        """Test POST /analytics/admin/aggregate"""
        yesterday = date.today() - timedelta(days=1)

        response = requests.post(
            f"{BASE_URL}{API_PREFIX}/analytics/admin/aggregate",
            json={"target_date": yesterday.isoformat()},
            headers=admin_headers,
            timeout=60,
        )

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
            timeout=60,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "queries_updated" in data
        assert "metrics_updated" in data

    def test_cache_stats(self, admin_headers):
        """Test GET /analytics/admin/cache-stats"""
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/admin/cache-stats",
            headers=admin_headers,
            timeout=10,
        )

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
            timeout=10,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_admin_endpoints_require_auth(self):
        """Test that admin endpoints require authentication"""
        endpoints = [
            ("GET", "/analytics/admin/aggregation-status"),
            ("POST", "/analytics/admin/aggregate"),
            ("POST", "/analytics/admin/recalculate-tokens"),
            ("GET", "/analytics/admin/cache-stats"),
            ("POST", "/analytics/admin/invalidate-cache"),
        ]

        for method, endpoint in endpoints:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{API_PREFIX}{endpoint}", timeout=10)
            else:
                response = requests.post(
                    f"{BASE_URL}{API_PREFIX}{endpoint}", timeout=10
                )

            assert response.status_code == 401, f"Expected 401 for {method} {endpoint}"


# =============================================================================
# DATA CONSISTENCY TESTS
# =============================================================================


class TestDataConsistency:
    """Tests for data consistency across endpoints"""

    def test_cost_totals_match(self, any_auth_headers):
        """Test that cost totals are consistent between overview and cost endpoint"""
        # Get from overview
        overview_response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/overview",
            params={"period": "month"},
            headers=any_auth_headers,
            timeout=30,
        )
        overview_data = overview_response.json()

        # Get from cost endpoint
        cost_response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/cost",
            params={"period": "month"},
            headers=any_auth_headers,
            timeout=30,
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

    def test_engagement_metrics_logical(self, any_auth_headers):
        """Test that engagement metrics are logically consistent"""
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/engagement",
            headers=any_auth_headers,
            timeout=30,
        )
        data = response.json()

        # DAU <= WAU <= MAU <= Total Users
        assert data["dau"] <= data["wau"], "DAU should be <= WAU"
        assert data["wau"] <= data["mau"], "WAU should be <= MAU"
        assert (
            data["mau"] <= data["total_registered_users"]
        ), "MAU should be <= total users"

        # DAU/MAU ratio should match calculation
        if data["mau"] > 0:
            expected_ratio = data["dau"] / data["mau"]
            assert abs(data["dau_mau_ratio"] - expected_ratio) < 0.001


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================


class TestAPIPerformance:
    """Performance tests for analytics endpoints"""

    def test_overview_response_time(self, any_auth_headers):
        """Test that overview responds within acceptable time"""
        import time

        start = time.time()
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/analytics/overview",
            headers=any_auth_headers,
            timeout=30,
        )
        elapsed = time.time() - start

        assert response.status_code == 200
        # Should respond within 5 seconds
        assert elapsed < 5.0, f"Response took {elapsed:.2f}s, expected < 5s"

    def test_concurrent_requests(self, any_auth_headers):
        """Test handling of concurrent requests"""
        import concurrent.futures

        def make_request():
            return requests.get(
                f"{BASE_URL}{API_PREFIX}/analytics/overview",
                headers=any_auth_headers,
                timeout=30,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(make_request) for _ in range(3)]
            results = [f.result() for f in futures]

        # All requests should succeed
        for response in results:
            assert response.status_code == 200


# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "--tb=short"])
