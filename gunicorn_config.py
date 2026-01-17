#!/usr/bin/env python3
"""
Gunicorn configuration for production deployment.

Configuration:
- 4 workers (recommended: 2-4 x CPU cores)
- 50 connections per worker (via connection pool)
- Graceful timeout for shutdown
- Preload app for memory efficiency

Usage:
    gunicorn -c gunicorn_config.py src.api.main:app

Or with uvicorn workers:
    gunicorn -c gunicorn_config.py -k uvicorn.workers.UvicornWorker src.api.main:app
"""

import os
import multiprocessing

# =============================================================================
# SERVER SOCKET
# =============================================================================

bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")
backlog = 2048

# =============================================================================
# WORKER PROCESSES
# =============================================================================

# Number of workers: 4 (as specified)
# Formula: 2-4 x $(NUM_CORES)
workers = int(os.getenv("GUNICORN_WORKERS", "4"))

# Worker class for async support
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "uvicorn.workers.UvicornWorker")

# Threads per worker (for sync workers only)
threads = int(os.getenv("GUNICORN_THREADS", "1"))

# Maximum concurrent connections per worker
worker_connections = int(os.getenv("GUNICORN_WORKER_CONNECTIONS", "50"))

# Maximum requests per worker before restart (prevents memory leaks)
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "5000"))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "500"))

# =============================================================================
# TIMEOUTS
# =============================================================================

# Request timeout (seconds)
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))

# Keep-alive timeout
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))

# Graceful timeout for shutdown
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "30"))

# =============================================================================
# PROCESS NAMING
# =============================================================================

proc_name = "rag-bidding-api"

# =============================================================================
# SERVER MECHANICS
# =============================================================================

# Preload app for memory efficiency (share code between workers)
preload_app = True

# Daemonize (run in background) - set to False for Docker
daemon = False

# PID file
pidfile = os.getenv("GUNICORN_PIDFILE", "/tmp/gunicorn-rag-bidding.pid")

# User and group (uncomment for production)
# user = "www-data"
# group = "www-data"

# =============================================================================
# LOGGING
# =============================================================================

# Logging level
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")

# Access log
accesslog = os.getenv("GUNICORN_ACCESS_LOG", "-")  # "-" for stdout

# Error log
errorlog = os.getenv("GUNICORN_ERROR_LOG", "-")  # "-" for stderr

# Access log format
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sμs'
)

# Capture stdout/stderr from workers
capture_output = True

# Enable statistics
enable_stdio_inheritance = True

# =============================================================================
# SECURITY
# =============================================================================

# Limit request line size
limit_request_line = 4094

# Limit request fields
limit_request_fields = 100

# Limit request field size
limit_request_field_size = 8190

# =============================================================================
# SSL (uncomment for HTTPS)
# =============================================================================

# keyfile = "/path/to/keyfile.pem"
# certfile = "/path/to/certfile.pem"
# ssl_version = "TLSv1_2"

# =============================================================================
# HOOKS
# =============================================================================


def on_starting(server):
    """Called just before the master process is initialized."""
    print(f"🚀 Starting RAG Bidding API server...")
    print(f"   Workers: {workers}")
    print(f"   Worker connections: {worker_connections}")
    print(f"   Bind: {bind}")
    print(f"   Timeout: {timeout}s")


def on_reload(server):
    """Called before reloading."""
    print("🔄 Reloading server configuration...")


def post_fork(server, worker):
    """Called just after a worker has been forked."""
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"Worker {worker.pid} started")

    # Initialize per-worker resources here
    # Example: Create new database connection pool
    print(f"   ✅ Worker {worker.pid} initialized")


def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass


def pre_exec(server):
    """Called just before a new master process is forked."""
    print("📋 Preparing to fork master process...")


def when_ready(server):
    """Called just after the server is started."""
    print(f"✅ Server is ready. Listening on {bind}")
    print(f"   PID: {server.pid}")
    print(f"   Workers: {workers}")


def worker_int(worker):
    """Called when a worker receives SIGINT or SIGQUIT."""
    print(f"⚠️ Worker {worker.pid} received interrupt signal")


def worker_abort(worker):
    """Called when a worker receives SIGABRT."""
    print(f"❌ Worker {worker.pid} aborted")


def child_exit(server, worker):
    """Called when a worker exits."""
    print(f"👋 Worker {worker.pid} exited")


def worker_exit(server, worker):
    """Called just after a worker has been exited."""
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"Worker {worker.pid} exited")


def nworkers_changed(server, new_value, old_value):
    """Called when number of workers changes."""
    print(f"📊 Workers changed: {old_value} → {new_value}")


def on_exit(server):
    """Called just before exiting Gunicorn."""
    print("👋 Server shutting down...")


# =============================================================================
# ENVIRONMENT VARIABLES REFERENCE
# =============================================================================

"""
Environment variables for configuration:

GUNICORN_BIND=0.0.0.0:8000
GUNICORN_WORKERS=4
GUNICORN_WORKER_CLASS=uvicorn.workers.UvicornWorker
GUNICORN_WORKER_CONNECTIONS=50
GUNICORN_TIMEOUT=120
GUNICORN_KEEPALIVE=5
GUNICORN_MAX_REQUESTS=5000
GUNICORN_LOG_LEVEL=info
GUNICORN_ACCESS_LOG=-
GUNICORN_ERROR_LOG=-

Database connection pool (configure in .env):
DATABASE_POOL_SIZE=50
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=1800
"""
