#!/bin/bash

# =============================================================================
# RAG Bidding API Server Startup Script
# =============================================================================
# Configuration:
#   - Workers: 4 (uvicorn/gunicorn)
#   - Connection Pool: 50 per worker (configured in base.py)
#   - Total DB Connections: 4 × 60 = 240 max (50 + 10 overflow per worker)
#
# Environment Variables (optional):
#   DATABASE_POOL_SIZE=50      # Connections per worker
#   DATABASE_MAX_OVERFLOW=10   # Extra connections per worker
#   DATABASE_POOL_TIMEOUT=30   # Connection timeout
#   DATABASE_POOL_RECYCLE=3600 # Recycle connections after N seconds
#   SQL_DEBUG=false            # Enable SQL query logging
#   GUNICORN_WORKERS=4         # Number of workers
#   GUNICORN_TIMEOUT=120       # Request timeout
# =============================================================================

# Activate conda environment
# source ~/anaconda3/etc/profile.d/conda.sh
conda activate venv

# Export default environment variables if not set
export DATABASE_POOL_SIZE=${DATABASE_POOL_SIZE:-50}
export DATABASE_MAX_OVERFLOW=${DATABASE_MAX_OVERFLOW:-10}
export DATABASE_POOL_TIMEOUT=${DATABASE_POOL_TIMEOUT:-30}
export DATABASE_POOL_RECYCLE=${DATABASE_POOL_RECYCLE:-3600}

echo "🚀 Starting RAG Bidding API Server..."
echo "   Workers: 4"
echo "   Pool Size per Worker: ${DATABASE_POOL_SIZE}"
echo "   Max Overflow per Worker: ${DATABASE_MAX_OVERFLOW}"
echo "   Total Max DB Connections: $((4 * (DATABASE_POOL_SIZE + DATABASE_MAX_OVERFLOW)))"

# Option 1: Use uvicorn directly (development/simple deployment)
python -m uvicorn --workers 4 src.api.main:app --host 0.0.0.0 --port 8000

# Option 2: Use gunicorn with uvicorn workers (production)
# Uncomment the following line and comment out Option 1
# gunicorn -c gunicorn_config.py src.api.main:app
