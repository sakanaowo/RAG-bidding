"""Add document_upload_jobs table for persistent job tracking

Revision ID: add_upload_jobs
Revises: add_token_split
Create Date: 2026-01-11 17:00:00.000000+07:00

Fixes issue: Upload job status returns 404 because jobs were stored in-memory
which doesn't persist across workers/restarts.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_upload_jobs"
down_revision: Union[str, None] = "add_token_split"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create document_upload_jobs table for tracking upload processing status."""

    # Create enum type if not exists (may already exist from previous partial migration)
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE processing_status AS ENUM (
                'pending', 'classifying', 'preprocessing', 'chunking', 
                'embedding', 'storing', 'completed', 'failed'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """
    )

    # Create the upload jobs table
    op.create_table(
        "document_upload_jobs",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Primary key",
        ),
        sa.Column(
            "upload_id",
            sa.String(36),
            nullable=False,
            unique=True,
            comment="Client-facing upload ID",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
            comment="Current processing status",
        ),
        sa.Column(
            "total_files",
            sa.Integer(),
            nullable=False,
            default=0,
            comment="Total number of files in this upload batch",
        ),
        sa.Column(
            "completed_files",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Number of successfully processed files",
        ),
        sa.Column(
            "failed_files",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Number of failed files",
        ),
        sa.Column(
            "progress_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Detailed progress for each file (file_id, filename, status, progress_percent, error_message, etc.)",
        ),
        sa.Column(
            "options",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Processing options (chunk_size, chunk_overlap, enable_enrichment, etc.)",
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
            comment="Overall error message if job failed",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("now()"),
            comment="When the upload was initiated",
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("now()"),
            comment="Last update timestamp",
        ),
        sa.Column(
            "completed_at",
            sa.TIMESTAMP(),
            nullable=True,
            comment="When processing completed/failed",
        ),
        comment="Tracks upload job status persistently across workers",
    )

    # Create indexes for common queries
    op.create_index(
        "ix_upload_jobs_upload_id", "document_upload_jobs", ["upload_id"], unique=True
    )
    op.create_index("ix_upload_jobs_status", "document_upload_jobs", ["status"])
    op.create_index("ix_upload_jobs_created_at", "document_upload_jobs", ["created_at"])

    # Create trigger function for updated_at
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_upload_jobs_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """
    )

    # Create trigger
    op.execute(
        """
        CREATE TRIGGER trigger_update_upload_jobs_updated_at
        BEFORE UPDATE ON document_upload_jobs
        FOR EACH ROW
        EXECUTE FUNCTION update_upload_jobs_updated_at();
    """
    )


def downgrade() -> None:
    """Remove document_upload_jobs table and related objects."""

    # Drop trigger
    op.execute(
        "DROP TRIGGER IF EXISTS trigger_update_upload_jobs_updated_at ON document_upload_jobs"
    )

    # Drop trigger function
    op.execute("DROP FUNCTION IF EXISTS update_upload_jobs_updated_at()")

    # Drop indexes
    op.drop_index("ix_upload_jobs_created_at", table_name="document_upload_jobs")
    op.drop_index("ix_upload_jobs_status", table_name="document_upload_jobs")
    op.drop_index("ix_upload_jobs_upload_id", table_name="document_upload_jobs")

    # Drop table
    op.drop_table("document_upload_jobs")

    # Drop enum type
    op.execute("DROP TYPE IF EXISTS processing_status")
