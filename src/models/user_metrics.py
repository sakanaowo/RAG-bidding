"""
UserUsageMetric Model - Schema v3
Represents daily usage metrics per user for billing and analytics
"""

from sqlalchemy import (
    Column,
    Integer,
    TIMESTAMP,
    ForeignKey,
    Index,
    Numeric,
    Date,
    BigInteger,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import Text
from typing import TYPE_CHECKING
import uuid

from .base import Base

if TYPE_CHECKING:
    from .users import User


class UserUsageMetric(Base):
    """
    UserUsageMetric model for daily usage tracking

    Aggregates daily usage per user:
    - Number of queries and messages
    - Token consumption
    - Cost estimation
    - Categories accessed
    """

    __tablename__ = "user_usage_metrics"

    # Primary Key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        comment="Primary key",
    )

    # Foreign key
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User ID",
    )

    # Date for aggregation
    date = Column(Date, nullable=False, index=True, comment="Metric date (YYYY-MM-DD)")

    # Usage counts
    total_queries = Column(
        Integer, default=0, nullable=True, comment="Total queries made"
    )

    total_messages = Column(
        Integer, default=0, nullable=True, comment="Total messages sent"
    )

    total_tokens = Column(
        BigInteger, default=0, nullable=True, comment="Total tokens consumed"
    )

    total_input_tokens = Column(
        BigInteger, default=0, nullable=True, comment="Total input tokens consumed"
    )

    total_output_tokens = Column(
        BigInteger, default=0, nullable=True, comment="Total output tokens consumed"
    )

    total_cost_usd = Column(
        Numeric(10, 4), default=0, nullable=True, comment="Total estimated cost in USD"
    )

    categories_accessed = Column(
        ARRAY(Text), nullable=True, comment="Categories accessed during the day"
    )

    # Timestamp
    created_at = Column(
        TIMESTAMP(timezone=False),
        server_default=func.current_timestamp(),
        nullable=True,
        comment="Record creation timestamp",
    )

    # Relationships
    user = relationship("User", back_populates="usage_metrics")

    # Indexes
    __table_args__ = (
        Index("idx_usage_user_date", "user_id", "date", unique=True),
        Index("idx_usage_date", "date"),
        {"comment": "Daily user usage metrics (v3)"},
    )

    def __repr__(self):
        return f"<UserUsageMetric(user_id={self.user_id}, date={self.date}, queries={self.total_queries})>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "date": self.date.isoformat() if self.date else None,
            "total_queries": self.total_queries,
            "total_messages": self.total_messages,
            "total_tokens": self.total_tokens,
            "total_cost_usd": float(self.total_cost_usd) if self.total_cost_usd else 0,
            "categories_accessed": self.categories_accessed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
