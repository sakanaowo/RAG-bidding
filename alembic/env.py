"""
Alembic Migration Configuration - Schema v3
Auto-generated with `alembic init alembic`
"""

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import ALL models for autogenerate to detect changes
from src.models.base import Base

# Core models
from src.models.documents import Document
from src.models.embeddings import LangchainPGEmbedding, LangchainPGCollection
from src.models.document_chunks import DocumentChunk

# User & Auth models
from src.models.users import User

# Chat models
from src.models.conversations import Conversation
from src.models.messages import Message
from src.models.citations import Citation

# Analytics models
from src.models.feedback import Feedback
from src.models.queries import Query
from src.models.user_metrics import UserUsageMetric

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate
target_metadata = Base.metadata

# Override sqlalchemy.url from environment
config.set_main_option(
    "sqlalchemy.url",
    os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://sakana:sakana123@localhost:5432/rag_bidding_v3",
    ),
)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
