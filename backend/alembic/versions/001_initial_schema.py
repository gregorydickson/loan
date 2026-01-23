"""Initial schema for document ingestion pipeline.

Revision ID: 001
Revises:
Create Date: 2026-01-23

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create documentstatus enum type
    documentstatus_enum = postgresql.ENUM(
        "pending", "processing", "completed", "failed",
        name="documentstatus",
        create_type=False
    )
    documentstatus_enum.create(op.get_bind(), checkfirst=True)

    # Documents table
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column(
            "file_hash", sa.String(64), nullable=False, unique=True, index=True
        ),
        sa.Column("file_type", sa.String(10), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("gcs_uri", sa.String(500), nullable=True),
        sa.Column(
            "status",
            documentstatus_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Borrowers table
    op.create_table(
        "borrowers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("ssn_hash", sa.String(64), nullable=True, index=True),
        sa.Column("address_json", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(3, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Income records table
    op.create_table(
        "income_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "borrower_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("borrowers.id"),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("period", sa.String(20), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("employer", sa.String(255), nullable=True),
    )
    op.create_index(
        "ix_income_records_borrower_id", "income_records", ["borrower_id"]
    )

    # Account numbers table
    op.create_table(
        "account_numbers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "borrower_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("borrowers.id"),
            nullable=False,
        ),
        sa.Column("number", sa.String(50), nullable=False),
        sa.Column("account_type", sa.String(20), nullable=False),
    )
    op.create_index(
        "ix_account_numbers_borrower_id", "account_numbers", ["borrower_id"]
    )

    # Source references table (linking borrowers to documents)
    op.create_table(
        "source_references",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "borrower_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("borrowers.id"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id"),
            nullable=False,
        ),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("section", sa.String(100), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=False),
    )
    op.create_index(
        "ix_source_references_borrower_id", "source_references", ["borrower_id"]
    )
    op.create_index(
        "ix_source_references_document_id", "source_references", ["document_id"]
    )


def downgrade() -> None:
    op.drop_table("source_references")
    op.drop_table("account_numbers")
    op.drop_table("income_records")
    op.drop_table("borrowers")
    op.drop_table("documents")
    op.execute("DROP TYPE IF EXISTS documentstatus")
