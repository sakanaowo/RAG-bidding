"""Extend document_upload_jobs for 2-stage upload workflow

Revision ID: extend_upload_jobs
Revises: add_upload_jobs
Create Date: 2026-01-11 18:00:00.000000+07:00

Adds support for:
- Stage 1: Upload files, extract metadata, save to storage (pending_review)
- Stage 2: Admin review/edit metadata, confirm to process embeddings
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "extend_upload_jobs"
down_revision: Union[str, None] = "add_upload_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add columns for 2-stage upload workflow."""

    # Add new columns to document_upload_jobs
    op.add_column(
        "document_upload_jobs",
        sa.Column(
            "files_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Array of file info: file_id, filename, file_path, size_bytes, content_type, extracted_text_preview",
        ),
    )

    op.add_column(
        "document_upload_jobs",
        sa.Column(
            "extracted_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Auto-extracted metadata from files: detected_type, confidence, title, keywords, etc.",
        ),
    )

    op.add_column(
        "document_upload_jobs",
        sa.Column(
            "admin_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Admin-edited/confirmed metadata: document_type, category, custom fields",
        ),
    )

    op.add_column(
        "document_upload_jobs",
        sa.Column(
            "storage_path",
            sa.Text(),
            nullable=True,
            comment="Permanent storage path for uploaded files: data/uploads/{upload_id}/",
        ),
    )

    op.add_column(
        "document_upload_jobs",
        sa.Column(
            "uploaded_by",
            sa.UUID(),
            nullable=True,
            comment="User who uploaded the files",
        ),
    )

    op.add_column(
        "document_upload_jobs",
        sa.Column(
            "confirmed_by",
            sa.UUID(),
            nullable=True,
            comment="Admin who confirmed the upload for processing",
        ),
    )

    op.add_column(
        "document_upload_jobs",
        sa.Column(
            "confirmed_at",
            sa.TIMESTAMP(),
            nullable=True,
            comment="When admin confirmed for processing",
        ),
    )

    op.add_column(
        "document_upload_jobs",
        sa.Column(
            "cancelled_at",
            sa.TIMESTAMP(),
            nullable=True,
            comment="When upload was cancelled",
        ),
    )

    op.add_column(
        "document_upload_jobs",
        sa.Column(
            "cancel_reason", sa.Text(), nullable=True, comment="Reason for cancellation"
        ),
    )

    # Update status enum values - use VARCHAR for flexibility
    # New statuses: pending_review, confirmed, processing, completed, failed, cancelled

    # Add index for uploaded_by
    op.create_index(
        "ix_upload_jobs_uploaded_by", "document_upload_jobs", ["uploaded_by"]
    )


def downgrade() -> None:
    """Remove added columns."""

    op.drop_index("ix_upload_jobs_uploaded_by", table_name="document_upload_jobs")

    op.drop_column("document_upload_jobs", "cancel_reason")
    op.drop_column("document_upload_jobs", "cancelled_at")
    op.drop_column("document_upload_jobs", "confirmed_at")
    op.drop_column("document_upload_jobs", "confirmed_by")
    op.drop_column("document_upload_jobs", "uploaded_by")
    op.drop_column("document_upload_jobs", "storage_path")
    op.drop_column("document_upload_jobs", "admin_metadata")
    op.drop_column("document_upload_jobs", "extracted_metadata")
    op.drop_column("document_upload_jobs", "files_data")
