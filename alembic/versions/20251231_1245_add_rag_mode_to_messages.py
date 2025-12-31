"""add rag_mode column to messages table

Revision ID: add_rag_mode_msg
Revises: 0dd6951d6844
Create Date: 2025-12-31 12:45:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_rag_mode_msg'
down_revision: Union[str, None] = '0dd6951d6844'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add rag_mode column to messages table to track RAG mode per message."""
    op.add_column(
        'messages',
        sa.Column(
            'rag_mode',
            sa.String(50),
            nullable=True,
            comment='RAG mode used: fast, balanced, quality, adaptive'
        )
    )


def downgrade() -> None:
    """Remove rag_mode column from messages table."""
    op.drop_column('messages', 'rag_mode')
