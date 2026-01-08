"""Fix CASCADE DELETE constraints for user and conversation deletion

Revision ID: fix_cascade_delete
Revises: add_rag_mode_msg
Create Date: 2026-01-06 14:00:00

This migration fixes foreign key constraints to properly support CASCADE DELETE:
1. User deletion → cascade to conversations, messages, feedback, user_metrics
2. Conversation deletion → cascade to messages
3. Message deletion → cascade to citations, feedback

Analytics tables (queries) use SET NULL to preserve historical data.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "fix_cascade_delete"
down_revision: Union[str, None] = "add_rag_mode_msg"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add CASCADE DELETE to foreign key constraints.

    Tables affected:
    - messages (user_id, conversation_id)
    - conversations (user_id)
    - feedback (user_id, message_id)
    - citations (message_id, document_id, chunk_id)
    - user_usage_metrics (user_id)
    """

    # =====================================================
    # 1. MESSAGES TABLE
    # =====================================================

    # Drop existing constraints
    op.drop_constraint("messages_user_id_fkey", "messages", type_="foreignkey")
    op.drop_constraint("messages_conversation_id_fkey", "messages", type_="foreignkey")

    # Recreate with CASCADE
    op.create_foreign_key(
        "messages_user_id_fkey",
        "messages",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "messages_conversation_id_fkey",
        "messages",
        "conversations",
        ["conversation_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # =====================================================
    # 2. CONVERSATIONS TABLE
    # =====================================================

    # Drop existing constraint
    op.drop_constraint(
        "conversations_user_id_fkey", "conversations", type_="foreignkey"
    )

    # Recreate with CASCADE
    op.create_foreign_key(
        "conversations_user_id_fkey",
        "conversations",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # =====================================================
    # 3. FEEDBACK TABLE
    # =====================================================

    # Drop existing constraints
    op.drop_constraint("feedback_user_id_fkey", "feedback", type_="foreignkey")
    op.drop_constraint("feedback_message_id_fkey", "feedback", type_="foreignkey")

    # Recreate with CASCADE
    op.create_foreign_key(
        "feedback_user_id_fkey",
        "feedback",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "feedback_message_id_fkey",
        "feedback",
        "messages",
        ["message_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # =====================================================
    # 4. CITATIONS TABLE
    # =====================================================

    # Drop existing constraints
    op.drop_constraint("citations_message_id_fkey", "citations", type_="foreignkey")
    op.drop_constraint("citations_document_id_fkey", "citations", type_="foreignkey")
    op.drop_constraint("citations_chunk_id_fkey", "citations", type_="foreignkey")

    # Recreate with CASCADE
    op.create_foreign_key(
        "citations_message_id_fkey",
        "citations",
        "messages",
        ["message_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "citations_document_id_fkey",
        "citations",
        "documents",
        ["document_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "citations_chunk_id_fkey",
        "citations",
        "document_chunks",
        ["chunk_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # =====================================================
    # 5. USER_USAGE_METRICS TABLE
    # =====================================================

    # Drop existing constraint
    op.drop_constraint(
        "user_usage_metrics_user_id_fkey", "user_usage_metrics", type_="foreignkey"
    )

    # Recreate with CASCADE
    op.create_foreign_key(
        "user_usage_metrics_user_id_fkey",
        "user_usage_metrics",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # =====================================================
    # 6. QUERIES TABLE (SET NULL for analytics)
    # =====================================================

    # Drop existing constraints
    op.drop_constraint("queries_user_id_fkey", "queries", type_="foreignkey")
    op.drop_constraint("queries_conversation_id_fkey", "queries", type_="foreignkey")
    op.drop_constraint("queries_message_id_fkey", "queries", type_="foreignkey")

    # Recreate with SET NULL to preserve analytics
    op.create_foreign_key(
        "queries_user_id_fkey",
        "queries",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_foreign_key(
        "queries_conversation_id_fkey",
        "queries",
        "conversations",
        ["conversation_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_foreign_key(
        "queries_message_id_fkey",
        "queries",
        "messages",
        ["message_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """
    Revert to original constraints without CASCADE.
    WARNING: This will prevent cascade deletion!
    """

    # =====================================================
    # 1. MESSAGES TABLE
    # =====================================================

    op.drop_constraint("messages_user_id_fkey", "messages", type_="foreignkey")
    op.drop_constraint("messages_conversation_id_fkey", "messages", type_="foreignkey")

    op.create_foreign_key(
        "messages_user_id_fkey", "messages", "users", ["user_id"], ["id"]
    )

    op.create_foreign_key(
        "messages_conversation_id_fkey",
        "messages",
        "conversations",
        ["conversation_id"],
        ["id"],
    )

    # =====================================================
    # 2. CONVERSATIONS TABLE
    # =====================================================

    op.drop_constraint(
        "conversations_user_id_fkey", "conversations", type_="foreignkey"
    )

    op.create_foreign_key(
        "conversations_user_id_fkey", "conversations", "users", ["user_id"], ["id"]
    )

    # =====================================================
    # 3. FEEDBACK TABLE
    # =====================================================

    op.drop_constraint("feedback_user_id_fkey", "feedback", type_="foreignkey")
    op.drop_constraint("feedback_message_id_fkey", "feedback", type_="foreignkey")

    op.create_foreign_key(
        "feedback_user_id_fkey", "feedback", "users", ["user_id"], ["id"]
    )

    op.create_foreign_key(
        "feedback_message_id_fkey", "feedback", "messages", ["message_id"], ["id"]
    )

    # =====================================================
    # 4. CITATIONS TABLE
    # =====================================================

    op.drop_constraint("citations_message_id_fkey", "citations", type_="foreignkey")
    op.drop_constraint("citations_document_id_fkey", "citations", type_="foreignkey")
    op.drop_constraint("citations_chunk_id_fkey", "citations", type_="foreignkey")

    op.create_foreign_key(
        "citations_message_id_fkey", "citations", "messages", ["message_id"], ["id"]
    )

    op.create_foreign_key(
        "citations_document_id_fkey", "citations", "documents", ["document_id"], ["id"]
    )

    op.create_foreign_key(
        "citations_chunk_id_fkey", "citations", "document_chunks", ["chunk_id"], ["id"]
    )

    # =====================================================
    # 5. USER_USAGE_METRICS TABLE
    # =====================================================

    op.drop_constraint(
        "user_usage_metrics_user_id_fkey", "user_usage_metrics", type_="foreignkey"
    )

    op.create_foreign_key(
        "user_usage_metrics_user_id_fkey",
        "user_usage_metrics",
        "users",
        ["user_id"],
        ["id"],
    )

    # =====================================================
    # 6. QUERIES TABLE
    # =====================================================

    op.drop_constraint("queries_user_id_fkey", "queries", type_="foreignkey")
    op.drop_constraint("queries_conversation_id_fkey", "queries", type_="foreignkey")
    op.drop_constraint("queries_message_id_fkey", "queries", type_="foreignkey")

    op.create_foreign_key(
        "queries_user_id_fkey", "queries", "users", ["user_id"], ["id"]
    )

    op.create_foreign_key(
        "queries_conversation_id_fkey",
        "queries",
        "conversations",
        ["conversation_id"],
        ["id"],
    )

    op.create_foreign_key(
        "queries_message_id_fkey", "queries", "messages", ["message_id"], ["id"]
    )
