"""Borrower data models for loan document extraction output.

This module provides the core data models that represent extracted
borrower information from loan documents:
- Address: Structured address from loan documents
- IncomeRecord: Single income entry with source attribution
- BorrowerRecord: Complete borrower extraction result (main output)
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.models.document import SourceReference


class Address(BaseModel):
    """Structured address extracted from loan documents."""

    street: str = Field(..., min_length=1, description="Street address line")
    city: str = Field(..., min_length=1, description="City name")
    state: str = Field(
        ...,
        min_length=2,
        max_length=2,
        description="Two-letter state code (e.g., TX, CA)",
    )
    zip_code: str = Field(
        ...,
        pattern=r"^\d{5}(-\d{4})?$",
        description="ZIP code in 5-digit or 5+4 format",
    )
    country: str = Field(default="USA", description="Country code")

    model_config = ConfigDict(from_attributes=True)


class IncomeRecord(BaseModel):
    """Single income entry extracted from loan documents.

    Represents one year's income from a specific source (employment,
    self-employment, etc.) with period normalization.
    """

    amount: Decimal = Field(
        ..., gt=0, description="Income amount in USD (must be positive)"
    )
    period: str = Field(
        ..., description="Income period: annual, monthly, weekly, biweekly"
    )
    year: int = Field(..., ge=1900, le=2100, description="Tax year for this income")
    source_type: str = Field(
        ..., description="Income source type: employment, self-employment, other"
    )
    employer: str | None = Field(
        default=None, description="Employer name if employment income"
    )

    model_config = ConfigDict(from_attributes=True)

    @field_validator("period")
    @classmethod
    def validate_period(cls, v: str) -> str:
        """Validate and normalize income period to lowercase."""
        allowed = {"annual", "monthly", "weekly", "biweekly"}
        if v.lower() not in allowed:
            raise ValueError(f"period must be one of {allowed}, got '{v}'")
        return v.lower()


class BorrowerRecord(BaseModel):
    """Complete borrower extraction result from loan documents.

    This is the main output model from the extraction pipeline. It contains
    all extracted borrower information along with source references for
    traceability.

    Note: SSN is stored if extracted but should be handled as sensitive PII.
    """

    id: UUID = Field(
        default_factory=uuid4, description="Unique identifier for this extraction"
    )
    name: str = Field(..., min_length=1, description="Borrower's full name")
    ssn: str | None = Field(
        default=None,
        pattern=r"^\d{3}-\d{2}-\d{4}$",
        description="Social Security Number in XXX-XX-XXXX format (SENSITIVE)",
    )
    phone: str | None = Field(
        default=None, description="Contact phone number"
    )
    email: str | None = Field(
        default=None, description="Contact email address"
    )
    address: Address | None = Field(
        default=None, description="Borrower's address if extracted"
    )
    income_history: list[IncomeRecord] = Field(
        default_factory=list, description="Income records extracted from documents"
    )
    account_numbers: list[str] = Field(
        default_factory=list, description="Bank account numbers found in documents"
    )
    loan_numbers: list[str] = Field(
        default_factory=list, description="Loan reference numbers found in documents"
    )
    sources: list[SourceReference] = Field(
        default_factory=list,
        description="Source references for extraction traceability",
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall extraction confidence (0.0 to 1.0)",
    )
    extracted_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when extraction was performed",
    )

    model_config = ConfigDict(from_attributes=True)
