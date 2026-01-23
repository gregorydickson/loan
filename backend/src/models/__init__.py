"""Pydantic data models for loan document extraction.

This module re-exports all data models for convenient importing:
- BorrowerRecord: Complete borrower extraction result
- Address: Structured address from loan documents
- IncomeRecord: Single income entry with source attribution
- SourceReference: Attribution to source document for traceability
- DocumentMetadata: Document tracking for ingestion pipeline
"""

from src.models.borrower import Address, BorrowerRecord, IncomeRecord
from src.models.document import DocumentMetadata, SourceReference

__all__ = [
    "Address",
    "BorrowerRecord",
    "DocumentMetadata",
    "IncomeRecord",
    "SourceReference",
]
