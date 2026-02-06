# ===================================================
# RAG Bidding API - Production Dockerfile
# ===================================================
# Features:
# - Embedded Redis server (all 5 DBs: cache, sessions, answer, semantic, rate-limit)
# - Supervisord for process management
# - 1 worker/instance for Cloud Run horizontal scaling
# - antiword for .doc file support
# ===================================================

FROM python:3.11-slim-bookworm

# ===== Environment Variables =====
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8080 \
    # Redis runs locally inside container
    REDIS_HOST=127.0.0.1 \
    REDIS_PORT=6379 \
    # Redis DBs for different purposes
    REDIS_DB_CACHE=0 \
    REDIS_DB_SESSIONS=1 \
    ANSWER_CACHE_DB=2 \
    SEMANTIC_CACHE_DB=3 \
    RATE_LIMIT_REDIS_DB=4 \
    # Enable all Redis features
    ENABLE_REDIS_CACHE=true \
    ENABLE_REDIS_SESSIONS=true \
    ENABLE_ANSWER_CACHE=true \
    ENABLE_SEMANTIC_CACHE=true \
    RATE_LIMIT_ENABLED=true \
    # Cache settings
    CACHE_TTL=3600 \
    ANSWER_CACHE_TTL=86400 \
    SEMANTIC_CACHE_THRESHOLD=0.95 \
    MAX_SEMANTIC_SEARCH=100 \
    RATE_LIMIT_DAILY_QUERIES=200 \
    # Suppress deprecation warnings
    PYTHONWARNINGS="ignore::FutureWarning"

WORKDIR /app

# ===== System Dependencies =====
# Install Redis, supervisord, antiword (for .doc files), and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    redis-server \
    supervisor \
    antiword \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/log/supervisor /var/run/redis

# ===== Python Dependencies =====
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ===== Application Code =====
COPY src/ ./src/
COPY gunicorn_config.py .
COPY alembic/ ./alembic/
COPY alembic.ini .

# ===== Supervisord Configuration =====
# Manages both Redis and Gunicorn processes
RUN mkdir -p /etc/supervisor/conf.d /etc/redis
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# ===== Redis Configuration =====
COPY docker/redis.conf /etc/redis/redis.conf

# ===== Health Check =====
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health && redis-cli ping || exit 1

# ===== Expose Port =====
EXPOSE ${PORT}

# ===== Startup Command =====
# Use supervisord to manage Redis + Gunicorn
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
