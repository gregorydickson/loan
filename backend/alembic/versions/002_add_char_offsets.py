"""Add character offset columns to source_references.

Revision ID: 002
Revises: 001
Create Date: 2026-01-25

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "source_references", sa.Column("char_start", sa.Integer(), nullable=True)
    )
    op.add_column(
        "source_references", sa.Column("char_end", sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("source_references", "char_end")
    op.drop_column("source_references", "char_start")
