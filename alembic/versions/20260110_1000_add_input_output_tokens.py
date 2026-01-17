"""Add input_tokens and output_tokens columns for detailed token tracking

Revision ID: add_token_split
Revises: fix_cascade_delete
Create Date: 2026-01-10 10:00:00.000000+07:00

This migration adds separate columns to track input and output tokens
for more accurate cost calculation and analytics.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_token_split"
down_revision: Union[str, None] = "fix_cascade_delete"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add input_tokens and output_tokens columns to queries and user_usage_metrics tables."""

    # Add columns to queries table
    op.add_column(
        "queries",
        sa.Column(
            "input_tokens",
            sa.Integer(),
            nullable=True,
            comment="Number of input/prompt tokens",
        ),
    )
    op.add_column(
        "queries",
        sa.Column(
            "output_tokens",
            sa.Integer(),
            nullable=True,
            comment="Number of output/completion tokens",
        ),
    )

    # Add columns to user_usage_metrics table
    op.add_column(
        "user_usage_metrics",
        sa.Column(
            "total_input_tokens",
            sa.BigInteger(),
            default=0,
            nullable=True,
            comment="Total input tokens consumed",
        ),
    )
    op.add_column(
        "user_usage_metrics",
        sa.Column(
            "total_output_tokens",
            sa.BigInteger(),
            default=0,
            nullable=True,
            comment="Total output tokens consumed",
        ),
    )

    # Backfill existing data with estimated values (80/20 split)
    # This is a one-time operation to populate historical data
    op.execute(
        """
        UPDATE queries 
        SET input_tokens = FLOOR(tokens_total * 0.8)::INTEGER,
            output_tokens = tokens_total - FLOOR(tokens_total * 0.8)::INTEGER
        WHERE tokens_total IS NOT NULL 
        AND input_tokens IS NULL
    """
    )

    op.execute(
        """
        UPDATE user_usage_metrics 
        SET total_input_tokens = FLOOR(total_tokens * 0.8)::BIGINT,
            total_output_tokens = total_tokens - FLOOR(total_tokens * 0.8)::BIGINT
        WHERE total_tokens IS NOT NULL 
        AND total_input_tokens IS NULL
    """
    )


def downgrade() -> None:
    """Remove input_tokens and output_tokens columns."""

    op.drop_column("user_usage_metrics", "total_output_tokens")
    op.drop_column("user_usage_metrics", "total_input_tokens")
    op.drop_column("queries", "output_tokens")
    op.drop_column("queries", "input_tokens")
