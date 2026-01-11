# Real Integration Tests for Analytics API

This directory contains real integration tests that test against a live running server with actual database connections.

## Prerequisites

1. **PostgreSQL Database**: Running and migrated
2. **Redis Server**: Running on localhost:6379
3. **API Server**: Running on localhost:8000

## Setup

### 1. Create Test Admin User

```bash
# Run from RAG-bidding directory
python scripts/tests/create_test_admin.py

# Or with options:
python scripts/tests/create_test_admin.py --with-user  # Also create regular user
python scripts/tests/create_test_admin.py --force      # Force update existing to admin
```

This creates:
- Admin user: `admin@example.com` / `Admin123456`
- Regular user (optional): `user@example.com` / `User123456`

### 2. Start the Server

```bash
./start_server.sh
# or
uvicorn src.api.main:app --reload
```

### 3. Run Integration Tests

```bash
# Run the new dashboard integration tests
pytest tests/integration/test_analytics_dashboard.py -v

# Run all integration tests
pytest tests/integration/test_analytics_real.py -v

# Run specific test class
pytest tests/integration/test_analytics_dashboard.py::TestDashboardOverview -v

# Run with detailed output
pytest tests/integration/test_analytics_dashboard.py -v --tb=long
```

## Test Categories

### Dashboard Overview Tests
- `TestDashboardOverview`: Tests for `/analytics/overview` endpoint

### Cost Analytics Tests
- `TestCostAnalytics`: Tests for cost-related endpoints (`/cost`, `/cost/daily`, `/cost/users`)

### Knowledge Base Health Tests
- `TestKnowledgeBaseHealth`: Tests for `/analytics/knowledge-base` endpoint

### RAG Performance Tests
- `TestRAGPerformance`: Tests for `/analytics/performance` endpoint

### Quality & Feedback Tests
- `TestQualityFeedback`: Tests for `/analytics/feedback` endpoint

### User Engagement Tests
- `TestUserEngagement`: Tests for `/analytics/engagement` endpoint

### Admin Endpoints Tests
- `TestAdminEndpoints`: Tests for admin-only endpoints

### Performance Tests
- `TestAPIPerformance`: Response time and concurrent request tests

### Data Consistency Tests
- `TestDataConsistency`: Cross-endpoint data consistency validation

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TEST_BASE_URL` | `http://localhost:8000` | Server URL |
| `TEST_ADMIN_EMAIL` | `admin@test.com` | Admin email |
| `TEST_ADMIN_PASSWORD` | `admin123456` | Admin password |
| `TEST_USER_EMAIL` | `user@test.com` | User email |
| `TEST_USER_PASSWORD` | `user123456` | User password |

## Troubleshooting

### Server not available
```
SKIPPED [1] - Server not available at http://localhost:8000
```
**Solution**: Start the server with `./start_server.sh`

### Authentication failed
```
SKIPPED [1] - Could not authenticate any test user
```
**Solution**: Run `python scripts/tests/setup_integration_test_data.py` to create test users

### Admin endpoints skipped
```
SKIPPED [1] - User does not have admin role
```
**Solution**: Ensure the admin user has `role=admin` in the database
