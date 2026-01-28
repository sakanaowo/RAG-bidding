"""
Feature Flags & Configuration cho Production Features

File này quản lý các tính năng đang development/production.
Cập nhật flags này khi triển khai các features mới.

See: documents/technical/POOLING_CACHE_PLAN.md
"""

import os
from typing import Literal

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # dotenv not installed


# ========================================
# DATABASE CONFIGURATION
# ========================================

# Current: SQLAlchemy with NullPool (async compatible)
# TODO: Switch to pgBouncer for connection pooling
# See: POOLING_CACHE_PLAN.md - Phase 1
USE_PGBOUNCER = False

if USE_PGBOUNCER:
    # pgBouncer port (default: 6432)
    DATABASE_PORT = 6432
    DATABASE_POOL_MODE = "transaction"  # or "session"
else:
    # Direct PostgreSQL connection
    DATABASE_PORT = 5432


# Database URL will be constructed based on flag
def get_database_url() -> str:
    """Get database URL based on configuration."""
    base_url = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rag_bidding_v3"
    )

    if USE_PGBOUNCER:
        # Replace port with pgBouncer port
        base_url = base_url.replace(":5432", f":{DATABASE_PORT}")

    # Convert to async driver
    return base_url.replace("postgresql://", "postgresql+asyncpg://")


# ========================================
# CACHE CONFIGURATION
# ========================================

# Redis cache for embeddings & retrieval
# Read from .env - default to False if not set
# See: POOLING_CACHE_PLAN.md - Phase 2
ENABLE_REDIS_CACHE = os.getenv("ENABLE_REDIS_CACHE", "false").lower() == "true"

# Cache settings (only used if ENABLE_REDIS_CACHE=True)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB_CACHE = int(os.getenv("REDIS_DB_CACHE", "0"))  # Database 0 for cache
REDIS_DB_SESSIONS = int(
    os.getenv("REDIS_DB_SESSIONS", "1")
)  # Database 1 for chat sessions

# Cache layers
ENABLE_L1_CACHE = True  # In-memory LRU cache (always safe)
ENABLE_L2_CACHE = ENABLE_REDIS_CACHE  # Redis cache (requires Redis)
ENABLE_L3_CACHE = True  # PostgreSQL fallback (always enabled)

# Cache TTL (time-to-live)
CACHE_TTL_EMBEDDINGS = 86400  # 24 hours (embeddings are immutable)
CACHE_TTL_RETRIEVAL = 3600  # 1 hour (retrieval results may change)
CACHE_TTL_SESSIONS = 3600  # 1 hour (chat sessions)

# L1 cache size (in-memory)
L1_CACHE_MAXSIZE = 500  # Max 500 queries in memory (~50MB)


# ========================================
# ANSWER CACHE CONFIGURATION (Phase 1)
# ========================================

# Answer-level cache - caches final RAG responses
# See: documents/CACHE_IMPLEMENTATION_PLAN.md - Phase 1
ENABLE_ANSWER_CACHE = os.getenv("ENABLE_ANSWER_CACHE", "true").lower() == "true"
ANSWER_CACHE_TTL = int(os.getenv("ANSWER_CACHE_TTL", "86400"))  # 24 hours
ANSWER_CACHE_DB = int(os.getenv("ANSWER_CACHE_DB", "2"))  # Redis DB 2 for answers


# ========================================
# SEMANTIC CACHE CONFIGURATION (Phase 2 - V2 Hybrid)
# ========================================

# Semantic similarity cache - finds similar queries using Cosine + BGE hybrid
# See: documents/CACHE_IMPLEMENTATION_PLAN.md - Phase 2
ENABLE_SEMANTIC_CACHE = os.getenv("ENABLE_SEMANTIC_CACHE", "true").lower() == "true"
SEMANTIC_CACHE_DB = int(
    os.getenv("SEMANTIC_CACHE_DB", "3")
)  # Redis DB 3 for embeddings
MAX_SEMANTIC_SEARCH = int(
    os.getenv("MAX_SEMANTIC_SEARCH", "100")
)  # Max queries to scan

# V2 Hybrid Cache Configuration (Cosine pre-filter + BGE rerank)
# Cosine pre-filter: Fast O(n) scan to find candidates
SEMANTIC_CACHE_COSINE_THRESHOLD = float(
    os.getenv("SEMANTIC_CACHE_COSINE_THRESHOLD", "0.25")
)  # Low threshold to avoid missing candidates
SEMANTIC_CACHE_COSINE_TOP_K = int(
    os.getenv("SEMANTIC_CACHE_COSINE_TOP_K", "30")
)  # Max candidates for BGE reranking

# BGE rerank: Accurate cross-encoder scoring (final decision)
# Optimized via evaluation: 78.9% accuracy, 76.7% recall, 87.5% precision
SEMANTIC_CACHE_BGE_THRESHOLD = float(
    os.getenv("SEMANTIC_CACHE_BGE_THRESHOLD", "0.55")
)  # Min BGE score for match

# Legacy V1 threshold (deprecated, kept for reference)
SEMANTIC_CACHE_THRESHOLD = float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.60"))


# ========================================
# CHAT SESSION CONFIGURATION
# ========================================

# Redis sessions (persistent, multi-instance support)
# Read from .env - default to False if not set
# See: src/api/routers/documents_chat.py
ENABLE_REDIS_SESSIONS = os.getenv("ENABLE_REDIS_SESSIONS", "false").lower() == "true"

# Session settings
SESSION_TTL_SECONDS = 3600  # 1 hour
SESSION_MAX_MESSAGES = 100  # Max messages per session


# ========================================
# RERANKING CONFIGURATION
# ========================================

# Reranker type: "bge" or "openai"
DEFAULT_RERANKER_TYPE: Literal["bge", "openai"] = "bge"

# BGE Reranker
BGE_MODEL_NAME = "BAAI/bge-reranker-v2-m3"
BGE_DEVICE = "auto"  # auto-detect GPU/CPU

# OpenAI Reranker settings
OPENAI_RERANKER_MODEL = "gpt-4o-mini"
OPENAI_RERANKER_USE_PARALLEL = True  # Parallel API calls (8.38x faster)
OPENAI_RERANKER_MAX_WORKERS = 10  # Max concurrent API calls


# ========================================
# PERFORMANCE SETTINGS
# ========================================

# Query enhancement strategies
DEFAULT_ENHANCEMENT_STRATEGIES = ["multi_query", "step_back"]  # balanced mode

# Retrieval settings
DEFAULT_RETRIEVAL_K = 10  # Top-k documents to retrieve
DEFAULT_RERANK_TOP_N = 5  # Top-n after reranking

# ========================================
# RATE LIMITING CONFIGURATION
# ========================================

# Enable/disable rate limiting
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"

# Daily query limit per user (default: 100 queries/day)
RATE_LIMIT_DAILY_QUERIES = int(os.getenv("RATE_LIMIT_DAILY_QUERIES", "100"))

# Redis DB for rate limiting (separate from other caches)
RATE_LIMIT_REDIS_DB = int(os.getenv("RATE_LIMIT_REDIS_DB", "4"))

# TTL for rate limit keys (24 hours)
RATE_LIMIT_TTL_SECONDS = 86400

# TODO (Future): Token-based and cost-based limits
# RATE_LIMIT_DAILY_TOKENS = int(os.getenv("RATE_LIMIT_DAILY_TOKENS", "50000"))
# RATE_LIMIT_DAILY_COST_USD = float(os.getenv("RATE_LIMIT_DAILY_COST_USD", "0.05"))

# TODO (Future): User tier support
# User tiers would have different limits (Free/Basic/Pro/Admin)
# Requires: ALTER TABLE users ADD COLUMN rate_limit_tier VARCHAR(20) DEFAULT 'basic';


# ========================================
# MONITORING & OBSERVABILITY
# ========================================

# Metrics endpoint
ENABLE_METRICS_ENDPOINT = True  # /metrics endpoint

# Detailed logging
LOG_CACHE_STATS = True  # Log cache hit/miss rates
LOG_QUERY_PERFORMANCE = True  # Log query timings
LOG_POOL_STATUS = False  # Log connection pool status (when using pgBouncer)


# ========================================
# FEATURE FLAGS SUMMARY
# ========================================


def get_feature_status() -> dict:
    """Get current status of all features."""
    return {
        "database": {
            "pooling": "pgBouncer" if USE_PGBOUNCER else "NullPool (no pooling)",
            "port": DATABASE_PORT,
            "status": "✅ Production ready" if USE_PGBOUNCER else "⚠️ Development mode",
        },
        "cache": {
            "enabled": ENABLE_REDIS_CACHE,
            "layers": {
                "L1 (Memory)": "✅ Enabled" if ENABLE_L1_CACHE else "❌ Disabled",
                "L2 (Redis)": "✅ Enabled" if ENABLE_L2_CACHE else "❌ Disabled",
                "L3 (PostgreSQL)": "✅ Enabled" if ENABLE_L3_CACHE else "❌ Disabled",
            },
            "status": (
                "✅ Production ready" if ENABLE_REDIS_CACHE else "⚠️ Development mode"
            ),
        },
        "answer_cache": {
            "enabled": ENABLE_ANSWER_CACHE,
            "ttl_seconds": ANSWER_CACHE_TTL,
            "redis_db": ANSWER_CACHE_DB,
            "status": (
                "✅ Enabled"
                if ENABLE_ANSWER_CACHE and ENABLE_REDIS_CACHE
                else "⚠️ Disabled"
            ),
        },
        "semantic_cache": {
            "enabled": ENABLE_SEMANTIC_CACHE,
            "version": "V2 (Hybrid Cosine + BGE)",
            "redis_db": SEMANTIC_CACHE_DB,
            "max_scan": MAX_SEMANTIC_SEARCH,
            "config": {
                "cosine_threshold": SEMANTIC_CACHE_COSINE_THRESHOLD,
                "cosine_top_k": SEMANTIC_CACHE_COSINE_TOP_K,
                "bge_threshold": SEMANTIC_CACHE_BGE_THRESHOLD,
            },
            "performance": {
                "accuracy": "78.9%",
                "recall": "76.7%",
                "precision": "87.5%",
            },
            "status": (
                "✅ Enabled (V2 Hybrid)"
                if ENABLE_SEMANTIC_CACHE and ENABLE_REDIS_CACHE
                else "⚠️ Disabled"
            ),
        },
        "sessions": {
            "storage": "Redis" if ENABLE_REDIS_SESSIONS else "In-Memory",
            "persistent": ENABLE_REDIS_SESSIONS,
            "status": (
                "✅ Production ready" if ENABLE_REDIS_SESSIONS else "⚠️ Development mode"
            ),
        },
        "reranking": {
            "default_type": DEFAULT_RERANKER_TYPE,
            "bge_singleton": "✅ Enabled",
            "openai_parallel": (
                "✅ Enabled" if OPENAI_RERANKER_USE_PARALLEL else "❌ Sequential"
            ),
            "status": "✅ Production ready",
        },
    }


# ========================================
# DEPLOYMENT CHECKLIST
# ========================================

"""
Before deploying to production:

Phase 1: Connection Pooling (Week 2)
[ ] Install pgBouncer: sudo apt install pgbouncer
[ ] Configure /etc/pgbouncer/pgbouncer.ini
[ ] Set USE_PGBOUNCER = True
[ ] Test with 50+ concurrent users
[ ] Monitor pool status with SHOW POOLS

Phase 2: Redis Cache (Week 3)
[ ] Install Redis: sudo apt install redis-server
[ ] Configure /etc/redis/redis.conf (maxmemory 2gb)
[ ] Set ENABLE_REDIS_CACHE = True
[ ] Set ENABLE_REDIS_SESSIONS = True
[ ] Monitor hit rates with redis-cli INFO stats
[ ] Test cache invalidation

Phase 3: Monitoring (Week 4)
[ ] Enable metrics endpoint
[ ] Set up dashboard for pool/cache stats
[ ] Configure alerts for high pool usage
[ ] Load test with 100+ users

See: documents/technical/POOLING_CACHE_PLAN.md for detailed guide
"""
