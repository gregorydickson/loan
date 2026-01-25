"""Add extraction metadata columns to documents.

Revision ID: 003
Revises: 002
Create Date: 2026-01-25

Adds columns for dual pipeline support (DUAL-09):
- extraction_method: Which extraction pipeline was used (docling/langextract)
- ocr_processed: Whether OCR was applied to the document

Both columns are nullable for backward compatibility with existing documents.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "documents", sa.Column("extraction_method", sa.String(20), nullable=True)
    )
    op.add_column(
        "documents", sa.Column("ocr_processed", sa.Boolean(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("documents", "ocr_processed")
    op.drop_column("documents", "extraction_method")
