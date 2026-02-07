"""
Optimized Database Configuration với Connection Pooling
Giải quyết performance bottlenecks từ test results:
- Response time: 9.6s → <2s target
- Concurrent users: 10 → 50+ target
- Success rate: 37% → 95%+ target
"""

import asyncio
import logging
from typing import AsyncGenerator, Dict, Any
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool
from sqlalchemy.engine.events import event
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .models import settings

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """
    Centralized database configuration với optimized connection pooling

    Key optimizations để giải quyết performance issues:
    1. Connection pooling → Eliminate connection overhead
    2. Pre-ping validation → Prevent stale connections
    3. Pool monitoring → Track performance metrics
    4. Async session management → Better concurrency

    Note: Using NullPool for async engine compatibility.
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        self._engine: AsyncEngine = None
        self._session_factory = None
        self._pool_stats = {"connections_created": 0, "queries_executed": 0}

        self._setup_engine()
        self._setup_session_factory()
        self._setup_monitoring()

    def _setup_engine(self):
        """Setup SQLAlchemy async engine với optimized connection pool"""

        # Always use connection pooling for better performance
        # Cloud SQL db-perf-optimized-N-8 has ~220 max connections
        # With 1 worker: pool_size=50, max_overflow=50 → max 100 connections
        self._engine = create_async_engine(
            self.database_url,
            # Connection Pool Configuration
            poolclass=AsyncAdaptedQueuePool,
            pool_size=50,  # Base pool size (increased for single worker)
            max_overflow=50,  # Additional connections when pool exhausted
            pool_timeout=30,  # Wait time for connection
            pool_recycle=1800,  # Recycle connections after 30 mins
            pool_pre_ping=True,  # Validate connections before use
            # Performance Settings
            echo=False,  # Set True for SQL debugging
            echo_pool=False,  # Set True for pool debugging
            future=True,  # Enable SQLAlchemy 2.0 style
        )
        logger.info(
            f"Database engine initialized with AsyncAdaptedQueuePool (pool_size=50, max_overflow=50)"
        )

    def _setup_session_factory(self):
        """Setup async session factory"""
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Keep objects accessible after commit
            autoflush=True,  # Auto-flush changes
            autocommit=False,  # Explicit transaction control
        )

        logger.info("Async session factory configured")

    def _setup_monitoring(self):
        """Setup connection pool monitoring và logging"""

        @event.listens_for(self._engine.sync_engine, "connect")
        def receive_connect(dbapi_connection, connection_record):
            self._pool_stats["connections_created"] += 1
            logger.debug("New database connection established")

        @event.listens_for(self._engine.sync_engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            logger.debug("Connection checked out from pool")

        @event.listens_for(self._engine.sync_engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            logger.debug("Connection returned to pool")

        @event.listens_for(self._engine.sync_engine, "before_cursor_execute")
        def receive_before_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            self._pool_stats["queries_executed"] += 1

        logger.info("Connection pool monitoring setup completed")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session from pool với proper error handling

        Returns:
            AsyncSession: Database session with connection pooling
        """
        if not self._session_factory:
            raise RuntimeError("Database not properly initialized")

        session = self._session_factory()
        try:
            yield session
        except SQLAlchemyError as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        except Exception as e:
            logger.error(f"Unexpected session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()

    async def test_connection(self) -> bool:
        """
        Test database connectivity với connection pool

        Returns:
            bool: True if connection successful
        """
        try:
            async with self._engine.begin() as conn:
                result = await conn.execute(text("SELECT 1 as test_value"))
                test_value = result.scalar()

                # Test pgvector availability
                await conn.execute(
                    text(
                        "SELECT 1 WHERE EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"
                    )
                )

                logger.info("Database connectivity test passed")
                return test_value == 1

        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    async def get_pool_status(self) -> Dict[str, Any]:
        """
        Get detailed connection pool status for monitoring

        Returns:
            Dict containing pool metrics
        """
        if not self._engine:
            return {"error": "Engine not initialized"}

        pool = self._engine.pool
        pool_class = pool.__class__.__name__

        # Build metrics based on pool type
        if pool_class == "AsyncAdaptedQueuePool":
            pool_metrics = {
                "pool_class": pool_class,
                "pool_size": pool.size(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "checked_in": pool.checkedin(),
                "max_overflow": pool._max_overflow,
                "utilization": f"{pool.checkedout()}/{pool.size() + pool._max_overflow}",
            }
            recommendations = [
                "Using AsyncAdaptedQueuePool for local testing",
                "Monitor checked_out vs pool_size for saturation",
            ]
        else:
            pool_metrics = {
                "pool_class": pool_class,
                "note": "NullPool creates connections on-demand, no persistent pool",
            }
            recommendations = [
                "Using NullPool - connections created per request",
                "Consider pgBouncer for production connection pooling",
            ]

        return {
            "pool_metrics": pool_metrics,
            "performance_stats": self._pool_stats,
            "recommendations": recommendations,
        }

    async def warm_up_pool(self, min_connections: int = 5):
        """
        Warm up connection pool by pre-creating connections

        Args:
            min_connections: Minimum connections to pre-create
        """
        pool = self._engine.pool
        pool_class = pool.__class__.__name__

        if pool_class == "NullPool":
            logger.info("NullPool in use - connection warm-up not applicable")
            return

        # For QueuePool-based pools, warm up by creating initial connections
        logger.info(f"Warming up {pool_class} with {min_connections} connections...")
        try:
            connections = []
            for i in range(min(min_connections, pool.size())):
                async with self._engine.begin() as conn:
                    await conn.execute(text("SELECT 1"))
                    connections.append(conn)
            logger.info(
                f"Pool warm-up complete: {len(connections)} connections pre-created"
            )
        except Exception as e:
            logger.warning(f"Pool warm-up failed: {e}")

    async def execute_health_check(self) -> Dict[str, Any]:
        """
        Comprehensive database health check

        Returns:
            Dict with health check results
        """
        health_status = {
            "timestamp": asyncio.get_event_loop().time(),
            "database_accessible": False,
            "pool_healthy": True,  # NullPool always "healthy"
            "pgvector_available": False,
            "response_time_ms": None,
        }

        start_time = asyncio.get_event_loop().time()

        try:
            async with self._engine.begin() as conn:
                # Basic connectivity
                await conn.execute(text("SELECT 1"))
                health_status["database_accessible"] = True

                # Check pgvector extension
                result = await conn.execute(
                    text(
                        "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"
                    )
                )
                health_status["pgvector_available"] = result.scalar()

                # Calculate response time
                end_time = asyncio.get_event_loop().time()
                health_status["response_time_ms"] = round(
                    (end_time - start_time) * 1000, 2
                )

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            health_status["error"] = str(e)

        return health_status

    async def close(self):
        """Close all connections and cleanup resources"""
        if self._engine:
            await self._engine.dispose()
            logger.info("Database engine disposed and connections closed")


# Global database instance
_db_config: DatabaseConfig = None


def build_cloud_database_url() -> str:
    """
    Build Cloud SQL connection URL for direct IP connection.

    Uses settings:
        - cloud_db_host: Public IP of Cloud SQL instance
        - cloud_db_user: Database username
        - cloud_db_password: Database password
        - cloud_db_name: Database name

    Returns:
        PostgreSQL connection URL for Cloud SQL
    """
    from urllib.parse import quote_plus

    if not all(
        [
            settings.cloud_db_host,
            settings.cloud_db_user,
            settings.cloud_db_password,
            settings.cloud_db_name,
        ]
    ):
        raise ValueError(
            "Cloud DB configuration incomplete. Required: "
            "CLOUD_DB_CONNECTION_PUBLICIP, CLOUD_DB_USER, CLOUD_DB_PASSWORD, CLOUD_INSTANCE_DB"
        )

    # URL-encode password to handle special characters
    encoded_password = quote_plus(settings.cloud_db_password)

    url = (
        f"postgresql+psycopg://{settings.cloud_db_user}:{encoded_password}"
        f"@{settings.cloud_db_host}:5432/{settings.cloud_db_name}"
    )

    logger.info(f"Cloud DB URL built for host: {settings.cloud_db_host}")
    return url


def get_effective_database_url() -> str:
    """
    Get the effective database URL based on environment configuration.

    Priority:
        1. If USE_CLOUD_DB=true → Build URL from CLOUD_DB_* components
        2. Else use DATABASE_URL from environment

    Note: In Cloud Run, DATABASE_URL comes from Secret Manager and is a
    Cloud SQL URL, so USE_CLOUD_DB=false is correct (no need to build URL).

    Returns:
        Database connection URL
    """
    if settings.use_cloud_db:
        logger.info(
            f"🌐 Using Cloud SQL database (ENV_MODE={settings.env_mode}, built from CLOUD_DB_* settings)"
        )
        return build_cloud_database_url()
    else:
        # Check if DATABASE_URL looks like a cloud connection
        db_url = settings.database_url
        is_cloud = db_url and (
            "cloud" in db_url.lower()
            or "34.124" in db_url  # Cloud SQL public IP
            or "/cloudsql/" in db_url
        )

        if is_cloud:
            logger.info(
                f"🌐 Using Cloud SQL database from DATABASE_URL (ENV_MODE={settings.env_mode})"
            )
        else:
            logger.info(f"💻 Using local database (ENV_MODE={settings.env_mode})")

        return db_url


def init_database(database_url: str = None) -> DatabaseConfig:
    """
    Initialize database connection pool

    Args:
        database_url: Database connection string (uses auto-switch if not provided)

    Returns:
        DatabaseConfig: Initialized database configuration
    """
    global _db_config

    if database_url is None:
        database_url = get_effective_database_url()

    if not database_url:
        raise ValueError("DATABASE_URL must be provided in environment or as parameter")

    _db_config = DatabaseConfig(database_url)
    logger.info("Database connection pool initialized successfully")

    return _db_config


def get_db_config() -> DatabaseConfig:
    """Get global database configuration instance"""
    if _db_config is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _db_config


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions với connection pooling

    Yields:
        AsyncSession: Database session from connection pool
    """
    db_config = get_db_config()
    async with db_config.get_session() as session:
        yield session


async def startup_database():
    """Database startup routine - call in FastAPI startup event"""
    try:
        db_config = get_db_config()

        # Test connectivity
        if not await db_config.test_connection():
            raise RuntimeError("Database connectivity test failed")

        # Warm up connection pool
        await db_config.warm_up_pool(min_connections=5)

        # Log initial pool status
        pool_status = await db_config.get_pool_status()
        logger.info(
            f"Database startup completed. Pool status: {pool_status['pool_metrics']}"
        )

    except Exception as e:
        logger.error(f"Database startup failed: {e}")
        raise


async def shutdown_database():
    """Database shutdown routine - call in FastAPI shutdown event"""
    try:
        db_config = get_db_config()
        await db_config.close()
        logger.info("Database shutdown completed")

    except Exception as e:
        logger.error(f"Database shutdown error: {e}")


# Convenience functions for common operations
async def execute_query(query: str, params: Dict = None) -> Any:
    """Execute a single query với connection pooling"""
    async with get_db_config().get_session() as session:
        result = await session.execute(text(query), params or {})
        return result


async def execute_transaction(queries: list, params_list: list = None) -> bool:
    """Execute multiple queries in a transaction"""
    async with get_db_config().get_session() as session:
        try:
            async with session.begin():
                for i, query in enumerate(queries):
                    params = params_list[i] if params_list else {}
                    await session.execute(text(query), params)
            return True
        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            return False


# Synchronous database access (for non-async contexts like background tasks)
def get_db_sync():
    """
    Get synchronous database session for non-async contexts.

    WARNING: This uses synchronous SQLAlchemy and should only be used
    in background tasks or non-async code paths. Prefer async get_db() for API endpoints.

    Returns:
        Database session (psycopg style)
    """
    import psycopg
    from urllib.parse import urlparse, unquote

    # Use the same database URL logic as async engine
    db_url = get_effective_database_url()
    
    if not db_url:
        raise ValueError("DATABASE_URL not configured")

    # Convert postgresql+asyncpg:// or postgresql+psycopg:// to postgresql://
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    elif db_url.startswith("postgresql+psycopg://"):
        db_url = db_url.replace("postgresql+psycopg://", "postgresql://")

    # Parse URL
    parsed = urlparse(db_url)
    
    if not parsed.hostname:
        raise ValueError(f"Invalid DATABASE_URL: missing hostname. URL pattern: {db_url[:50]}...")

    # Create psycopg connection
    # Note: unquote() decodes URL-encoded password (e.g., %7C -> |, %3D -> =)
    conn = psycopg.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        dbname=parsed.path.lstrip("/"),
        user=parsed.username,
        password=unquote(parsed.password) if parsed.password else None,
    )

    return conn
