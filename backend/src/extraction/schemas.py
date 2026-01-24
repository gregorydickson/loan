"""Gemini-compatible extraction schemas for LLM borrower data extraction.

This module provides Pydantic models designed for Gemini structured output.
These are SEPARATE from models in src/models/borrower.py because:
- These are for LLM output parsing (simpler, no UUIDs, no sources)
- The borrower.py models are for storage (with IDs, sources, timestamps)

CRITICAL: Do NOT use Field(default=...) - this causes issues with Gemini.
Use Optional[T] = None pattern instead.
"""

from pydantic import BaseModel


class ExtractedAddress(BaseModel):
    """Address extracted by LLM from loan documents."""

    street: str
    city: str
    state: str  # Two-letter state code (e.g., TX, CA)
    zip_code: str


class ExtractedIncome(BaseModel):
    """Income record extracted by LLM from loan documents.

    Uses float instead of Decimal for JSON serialization compatibility.
    """

    amount: float  # Use float for JSON, convert to Decimal in BorrowerRecord
    period: str  # annual, monthly, weekly, biweekly
    year: int
    source_type: str  # employment, self-employment, other
    employer: str | None = None


class ExtractedBorrower(BaseModel):
    """Borrower information extracted by LLM from loan documents.

    This is the raw extraction result before validation and enrichment.
    """

    name: str
    ssn: str | None = None
    phone: str | None = None
    email: str | None = None
    address: ExtractedAddress | None = None
    income_history: list[ExtractedIncome] = []
    account_numbers: list[str] = []
    loan_numbers: list[str] = []


class BorrowerExtractionResult(BaseModel):
    """Complete LLM extraction result containing all extracted borrowers.

    This is the top-level schema passed to Gemini for structured output.
    """

    borrowers: list[ExtractedBorrower] = []
    extraction_notes: str | None = None  # Quality issues noted by LLM
