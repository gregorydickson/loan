"""SQLAlchemy ORM models for the document ingestion pipeline.

This module defines the database models for:
- Document: Uploaded document tracking with status and metadata
- Borrower: Extracted borrower information
- IncomeRecord: Income entries linked to borrowers
- AccountNumber: Account numbers linked to borrowers
- SourceReference: Source attribution for traceability
"""

from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum as PyEnum
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class DocumentStatus(str, PyEnum):
    """Document processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(Base):
    """Document record for tracking uploaded files through the ingestion pipeline."""

    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    gcs_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[DocumentStatus] = mapped_column(
        SAEnum(
            DocumentStatus,
            name="documentstatus",
            create_type=False,  # Already created by migration
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=DocumentStatus.PENDING,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Extraction metadata (v2.0 dual pipeline support)
    # Values: "docling", "langextract", or None (legacy/pre-v2.0 documents)
    extraction_method: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # True if OCR was applied, False if skipped, None (legacy)
    ocr_processed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Relationships
    source_references: Mapped[list["SourceReference"]] = relationship(
        "SourceReference", back_populates="document"
    )


class Borrower(Base):
    """Borrower extracted from loan documents."""

    __tablename__ = "borrowers"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    ssn_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    address_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # Relationships
    income_records: Mapped[list["IncomeRecord"]] = relationship(
        "IncomeRecord", back_populates="borrower", cascade="all, delete-orphan"
    )
    account_numbers: Mapped[list["AccountNumber"]] = relationship(
        "AccountNumber", back_populates="borrower", cascade="all, delete-orphan"
    )
    source_references: Mapped[list["SourceReference"]] = relationship(
        "SourceReference", back_populates="borrower", cascade="all, delete-orphan"
    )


class IncomeRecord(Base):
    """Income record linked to a borrower."""

    __tablename__ = "income_records"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    borrower_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("borrowers.id"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    employer: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    borrower: Mapped["Borrower"] = relationship("Borrower", back_populates="income_records")

    __table_args__ = (Index("ix_income_records_borrower_id", "borrower_id"),)


class AccountNumber(Base):
    """Account number linked to a borrower."""

    __tablename__ = "account_numbers"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    borrower_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("borrowers.id"), nullable=False
    )
    number: Mapped[str] = mapped_column(String(50), nullable=False)
    account_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # Relationships
    borrower: Mapped["Borrower"] = relationship("Borrower", back_populates="account_numbers")

    __table_args__ = (Index("ix_account_numbers_borrower_id", "borrower_id"),)


class SourceReference(Base):
    """Source reference linking extracted data to document location.

    Provides traceability for every extracted field - which document,
    page, and text snippet it came from.
    """

    __tablename__ = "source_references"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    borrower_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("borrowers.id"), nullable=False
    )
    document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    section: Mapped[str | None] = mapped_column(String(100), nullable=True)
    snippet: Mapped[str] = mapped_column(Text, nullable=False)
    char_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_end: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    borrower: Mapped["Borrower"] = relationship("Borrower", back_populates="source_references")
    document: Mapped["Document"] = relationship("Document", back_populates="source_references")

    __table_args__ = (
        Index("ix_source_references_borrower_id", "borrower_id"),
        Index("ix_source_references_document_id", "document_id"),
    )
