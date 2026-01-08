"""
SQLAlchemy Base Configuration
Database connection and session management
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Generator
import os
from dotenv import load_dotenv

load_dotenv()

# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL is None:
    raise ValueError("DATABASE_URL environment variable is not set")

# =============================================================================
# Connection Pool Configuration
# =============================================================================
# With 4 workers, each worker has its own pool:
# - Per worker: 50 connections + 10 overflow = 60 max
# - Total max: 4 workers × 60 = 240 connections
# - PostgreSQL max_connections should be >= 250 (240 + reserved)
#
# Adjust these values based on your PostgreSQL max_connections setting.
# Default PostgreSQL max_connections = 100, adjust in postgresql.conf if needed.
# =============================================================================

POOL_SIZE = int(os.getenv("DATABASE_POOL_SIZE", "50"))
MAX_OVERFLOW = int(os.getenv("DATABASE_MAX_OVERFLOW", "10"))
POOL_TIMEOUT = int(os.getenv("DATABASE_POOL_TIMEOUT", "30"))
POOL_RECYCLE = int(os.getenv("DATABASE_POOL_RECYCLE", "3600"))
SQL_DEBUG = os.getenv("SQL_DEBUG", "false").lower() == "true"

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=POOL_SIZE,  # Connections per worker
    max_overflow=MAX_OVERFLOW,  # Extra connections per worker
    pool_timeout=POOL_TIMEOUT,  # Timeout for getting connection
    pool_recycle=POOL_RECYCLE,  # Recycle connections after N seconds
    pool_pre_ping=True,  # Verify connections before using
    echo=SQL_DEBUG,  # Set True for SQL debugging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI to get database session

    Usage:
        @app.get("/documents")
        def get_documents(db: Session = Depends(get_db)):
            return db.query(Document).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database - create all tables
    Only use in development! Use Alembic for production.
    """
    Base.metadata.create_all(bind=engine)


def drop_db():
    """
    Drop all tables - DANGEROUS!
    Only use in development/testing
    """
    Base.metadata.drop_all(bind=engine)
