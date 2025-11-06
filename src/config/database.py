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
from sqlalchemy.pool import QueuePool
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

        self._engine = create_async_engine(
            self.database_url,
            # Connection Pool Configuration
            poolclass=QueuePool,
            pool_size=20,  # Core connections kept alive
            max_overflow=30,  # Additional connections when needed
            pool_recycle=3600,  # Recycle connections after 1 hour
            pool_pre_ping=True,  # Validate connections before use
            pool_reset_on_return="commit",  # Reset state on return
            pool_timeout=30,  # Max wait time for connection
            # Performance Settings
            echo=False,  # Set True for SQL debugging
            echo_pool=False,  # Set True for pool debugging
            future=True,  # Enable SQLAlchemy 2.0 style
            # Connection Settings cho PostgreSQL + pgvector optimization
            connect_args={
                "server_settings": {
                    "application_name": "rag_bidding_app",
                    "jit": "off",  # Disable JIT for faster startup
                    "shared_preload_libraries": "vector",  # pgvector support
                },
                "command_timeout": 30,  # Individual query timeout
            },
        )

        logger.info(f"Database engine initialized with pool_size=20, max_overflow=30")

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

        # Calculate pool utilization
        total_capacity = pool.size() + pool.overflow()
        checked_out_count = pool.checkedout()
        utilization = (
            (checked_out_count / total_capacity * 100) if total_capacity > 0 else 0
        )

        return {
            "pool_metrics": {
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": checked_out_count,
                "overflow": pool.overflow(),
                "invalid": pool.invalid(),
                "total_capacity": total_capacity,
            },
            "utilization_metrics": {
                "usage_percent": round(utilization, 2),
                "available_connections": pool.size() - checked_out_count,
                "is_healthy": utilization < 85,  # Alert if >85% utilization
            },
            "performance_stats": self._pool_stats,
            "recommendations": self._generate_pool_recommendations(utilization, pool),
        }

    def _generate_pool_recommendations(self, utilization: float, pool) -> list:
        """Generate pool performance recommendations"""
        recommendations = []

        if utilization > 90:
            recommendations.append(
                "CRITICAL: Pool utilization >90%. Increase pool_size immediately."
            )
        elif utilization > 80:
            recommendations.append(
                "WARNING: High pool utilization. Consider increasing pool_size."
            )

        if pool.overflow() > 20:
            recommendations.append(
                "Frequent overflow detected. Increase max_overflow setting."
            )

        if pool.invalid() > 5:
            recommendations.append("High invalid connections. Check network stability.")

        if self._pool_stats["queries_executed"] > 10000:
            recommendations.append(
                "High query volume. Monitor for performance optimization opportunities."
            )

        if not recommendations:
            recommendations.append("Pool performing optimally.")

        return recommendations

    async def warm_up_pool(self, min_connections: int = 5):
        """
        Warm up connection pool by pre-creating connections

        Args:
            min_connections: Minimum connections to pre-create
        """
        logger.info(f"Warming up connection pool with {min_connections} connections...")

        sessions = []
        try:
            # Create multiple sessions to warm up pool
            for i in range(min_connections):
                session = self._session_factory()
                await session.execute(text("SELECT 1"))
                sessions.append(session)
                logger.debug(f"Warmed up connection {i+1}/{min_connections}")

        except Exception as e:
            logger.error(f"Pool warm-up failed: {e}")

        finally:
            # Close all warming sessions
            for session in sessions:
                await session.close()

        logger.info("Connection pool warm-up completed")

    async def execute_health_check(self) -> Dict[str, Any]:
        """
        Comprehensive database health check

        Returns:
            Dict with health check results
        """
        health_status = {
            "timestamp": asyncio.get_event_loop().time(),
            "database_accessible": False,
            "pool_healthy": False,
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

                # Pool health
                pool_status = await self.get_pool_status()
                health_status["pool_healthy"] = pool_status["utilization_metrics"][
                    "is_healthy"
                ]

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


def init_database(database_url: str = None) -> DatabaseConfig:
    """
    Initialize database connection pool

    Args:
        database_url: Database connection string (uses settings if not provided)

    Returns:
        DatabaseConfig: Initialized database configuration
    """
    global _db_config

    if database_url is None:
        database_url = settings.database_url

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
