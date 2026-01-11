# Postman Collections for RAG Analytics API

This folder contains Postman collections and environments for testing the Analytics Dashboard API.

## Files

| File | Description |
|------|-------------|
| `RAG_Analytics_API.postman_collection.json` | Main collection with all analytics endpoints |
| `RAG_Analytics_Local.postman_environment.json` | Environment variables for local development |
| `RAG_Cache_Testing.postman_collection.json` | Cache testing collection (existing) |

## Setup Instructions

### 1. Import Collection

1. Open Postman
2. Click **Import** button
3. Drag and drop `RAG_Analytics_API.postman_collection.json`
4. Import the environment file `RAG_Analytics_Local.postman_environment.json`

### 2. Configure Environment

Select the "RAG Analytics - Local" environment and update variables if needed:

| Variable | Default | Description |
|----------|---------|-------------|
| `base_url` | `http://localhost:8000` | API base URL |
| `admin_email` | `admin@test.com` | Admin user email |
| `admin_password` | `admin123456` | Admin password |
| `user_email` | `user@test.com` | Regular user email |
| `user_password` | `user123456` | User password |

### 3. Create Test Users

Before testing, create the test users by running:

```bash
cd RAG-bidding
python scripts/tests/setup_integration_test_data.py
```

### 4. Start the Server

```bash
./start_server.sh
# or
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### 5. Run Tests

1. **Login first**: Run "Login as Admin" or "Login as User" to get access token
2. **Run individual requests** or use Collection Runner to run all

## Collection Structure

```
RAG Analytics API
├── Authentication
│   ├── Login as Admin          # Get admin token
│   └── Login as User           # Get user token
├── Dashboard Overview
│   ├── Get Dashboard Overview
│   └── Get Dashboard Overview (with details)
├── Cost Analytics
│   ├── Get Cost Overview
│   ├── Get Cost Overview (custom dates)
│   ├── Get Daily Token Usage
│   └── Get Cost Per User (Admin)
├── Knowledge Base
│   └── Get Knowledge Base Health
├── RAG Performance
│   └── Get RAG Performance
├── Quality & Feedback
│   └── Get Quality Feedback
├── User Engagement
│   └── Get User Engagement
├── Admin Endpoints
│   ├── Trigger Aggregation (single date)
│   ├── Trigger Aggregation (date range)
│   ├── Get Aggregation Status
│   ├── Recalculate Token Split
│   ├── Get Cache Stats
│   ├── Invalidate Cache (All)
│   └── Invalidate Cache (Cost only)
└── Error Cases
    ├── Unauthorized Request
    ├── Invalid Date Range
    └── Admin Endpoint as User
```

## Endpoints Summary

### Public Endpoints (Authenticated Users)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/analytics/overview` | Dashboard summary |
| GET | `/api/analytics/cost` | Cost overview |
| GET | `/api/analytics/cost/daily` | Daily token usage |
| GET | `/api/analytics/knowledge-base` | KB health metrics |
| GET | `/api/analytics/performance` | RAG performance |
| GET | `/api/analytics/feedback` | Quality feedback |
| GET | `/api/analytics/engagement` | User engagement |

### Admin-Only Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/analytics/cost/users` | Top users by cost |
| POST | `/api/analytics/admin/aggregate` | Trigger aggregation |
| GET | `/api/analytics/admin/aggregation-status` | Check aggregation gaps |
| POST | `/api/analytics/admin/recalculate-tokens` | Fix token split |
| GET | `/api/analytics/admin/cache-stats` | Cache statistics |
| POST | `/api/analytics/admin/invalidate-cache` | Clear cache |

## Query Parameters

### Time Periods
Most endpoints support `period` parameter:
- `day` - Last 24 hours
- `week` - Last 7 days
- `month` - Last 30 days (default)
- `quarter` - Last 90 days
- `year` - Last 365 days
- `all_time` - All data

### Custom Date Range
Some endpoints support `start_date` and `end_date` parameters (format: `YYYY-MM-DD`).

## Test Scripts

Each request includes Postman test scripts that:
- Verify status codes
- Check response structure
- Validate data types and relationships

## Running Collection Tests

Use Postman Collection Runner:

1. Click **Runner** button
2. Select "RAG Analytics API" collection
3. Select "RAG Analytics - Local" environment
4. Click **Run**

Expected results: All tests should pass (except admin tests if logged in as user).

## Troubleshooting

### "Could not get any response"
- Check if server is running: `curl http://localhost:8000/health`

### 401 Unauthorized
- Run "Login as Admin" first to get token

### 403 Forbidden
- Admin endpoints require admin role
- Login as admin user instead of regular user

### 500 Internal Server Error
- Check server logs: `tail -f /tmp/uvicorn.log`
- Verify database connection
