"""Borrower API endpoints.

Provides endpoints for listing, searching, and viewing borrower data
with full source attribution for traceability.
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from src.api.dependencies import BorrowerRepoDep

router = APIRouter(prefix="/api/borrowers", tags=["borrowers"])


class IncomeRecordResponse(BaseModel):
    """Income record in borrower response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    amount: Decimal
    period: str
    year: int
    source_type: str
    employer: str | None


class AccountNumberResponse(BaseModel):
    """Account number in borrower response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    number: str
    account_type: str


class SourceReferenceResponse(BaseModel):
    """Source reference in borrower response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    page_number: int
    section: str | None
    snippet: str
    char_start: int | None
    char_end: int | None


class BorrowerSummaryResponse(BaseModel):
    """Borrower summary for list views (fewer fields)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    confidence_score: Decimal
    created_at: datetime
    income_count: int  # Computed from len(income_records)


class BorrowerDetailResponse(BaseModel):
    """Full borrower details with all relationships."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    address_json: str | None
    confidence_score: Decimal
    created_at: datetime
    income_records: list[IncomeRecordResponse]
    account_numbers: list[AccountNumberResponse]
    source_references: list[SourceReferenceResponse]


class BorrowerListResponse(BaseModel):
    """Paginated list of borrowers."""

    borrowers: list[BorrowerSummaryResponse]
    total: int
    limit: int
    offset: int


class BorrowerSourcesResponse(BaseModel):
    """Source documents for a borrower."""

    borrower_id: UUID
    borrower_name: str
    sources: list[SourceReferenceResponse]


@router.get("/", response_model=BorrowerListResponse)
async def list_borrowers(
    repository: BorrowerRepoDep,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> BorrowerListResponse:
    """List borrowers with pagination.

    Args:
        repository: BorrowerRepository (injected)
        limit: Maximum borrowers to return (1-1000, default 100)
        offset: Number of borrowers to skip (default 0)

    Returns:
        BorrowerListResponse with borrowers and pagination info
    """
    borrowers = await repository.list_borrowers(limit=limit, offset=offset)
    total = await repository.count()
    return BorrowerListResponse(
        borrowers=[
            BorrowerSummaryResponse(
                id=b.id,
                name=b.name,
                confidence_score=b.confidence_score,
                created_at=b.created_at,
                income_count=len(b.income_records),
            )
            for b in borrowers
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/search", response_model=BorrowerListResponse)
async def search_borrowers(
    repository: BorrowerRepoDep,
    name: Annotated[str | None, Query(min_length=2)] = None,
    account_number: Annotated[str | None, Query(min_length=3)] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> BorrowerListResponse:
    """Search borrowers by name or account number.

    At least one of name or account_number must be provided.
    Search is case-insensitive partial match.

    Args:
        repository: BorrowerRepository (injected)
        name: Name to search for (min 2 chars)
        account_number: Account number to search for (min 3 chars)
        limit: Maximum borrowers to return (1-1000, default 100)
        offset: Number of borrowers to skip (default 0)

    Returns:
        BorrowerListResponse with matching borrowers

    Raises:
        400: Neither name nor account_number provided
    """
    if not name and not account_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'name' or 'account_number' query parameter is required",
        )

    if name:
        borrowers = await repository.search_by_name(name, limit=limit, offset=offset)
    else:
        borrowers = await repository.search_by_account(
            account_number, limit=limit, offset=offset  # type: ignore[arg-type]
        )

    return BorrowerListResponse(
        borrowers=[
            BorrowerSummaryResponse(
                id=b.id,
                name=b.name,
                confidence_score=b.confidence_score,
                created_at=b.created_at,
                income_count=len(b.income_records),
            )
            for b in borrowers
        ],
        total=len(borrowers),  # Search doesn't have separate count
        limit=limit,
        offset=offset,
    )


@router.get("/{borrower_id}", response_model=BorrowerDetailResponse)
async def get_borrower(
    borrower_id: UUID,
    repository: BorrowerRepoDep,
) -> BorrowerDetailResponse:
    """Get borrower details by ID.

    Args:
        borrower_id: Borrower UUID
        repository: BorrowerRepository (injected)

    Returns:
        BorrowerDetailResponse with full borrower details including relationships

    Raises:
        404: Borrower not found
    """
    borrower = await repository.get_by_id(borrower_id)
    if not borrower:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Borrower not found: {borrower_id}",
        )
    return BorrowerDetailResponse.model_validate(borrower)


@router.get("/{borrower_id}/sources", response_model=BorrowerSourcesResponse)
async def get_borrower_sources(
    borrower_id: UUID,
    repository: BorrowerRepoDep,
) -> BorrowerSourcesResponse:
    """Get source documents for a borrower.

    Returns all source references linking this borrower to their
    original documents for traceability.

    Args:
        borrower_id: Borrower UUID
        repository: BorrowerRepository (injected)

    Returns:
        BorrowerSourcesResponse with source references

    Raises:
        404: Borrower not found
    """
    borrower = await repository.get_by_id(borrower_id)
    if not borrower:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Borrower not found: {borrower_id}",
        )
    return BorrowerSourcesResponse(
        borrower_id=borrower.id,
        borrower_name=borrower.name,
        sources=[
            SourceReferenceResponse.model_validate(src)
            for src in borrower.source_references
        ],
    )
