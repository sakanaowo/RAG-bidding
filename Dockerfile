# ===================================================
# RAG Bidding API - Production Dockerfile
# ===================================================
# Configuration: 1 worker per instance
# Cloud Run will scale instances horizontally
# ===================================================

FROM python:3.11-slim-bookworm

# ===== Environment Variables =====
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000

WORKDIR /app

# ===== System Dependencies =====
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ===== Python Dependencies =====
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ===== Application Code =====
COPY src/ ./src/
COPY gunicorn_config.py .
COPY alembic/ ./alembic/
COPY alembic.ini .

# ===== Non-root User (Security) =====
RUN useradd --create-home --shell /bin/bash appuser
RUN chown -R appuser:appuser /app
USER appuser

# ===== Health Check =====
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# ===== Expose Port =====
EXPOSE ${PORT}

# ===== Startup Command =====
# 1 worker per instance - Cloud Run scales horizontally
CMD exec gunicorn \
    --bind :${PORT} \
    --workers 1 \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 300 \
    --graceful-timeout 30 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --access-logfile - \
    --error-logfile - \
    src.api.main:app
