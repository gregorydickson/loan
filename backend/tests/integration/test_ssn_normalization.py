"""TDD tests for SSN normalization issue.

Critical Issue: FieldValidator accepts SSNs with or without dashes, but
BorrowerRecord Pydantic model requires dashes. This causes valid SSNs to be rejected.
"""

from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.api.dependencies import (
    get_borrower_extractor,
    get_docling_processor,
    get_gcs_client,
)
from src.extraction import BorrowerExtractor, ExtractionResult
from src.extraction.complexity_classifier import ComplexityAssessment, ComplexityLevel
from src.ingestion.docling_processor import DocumentContent, PageContent
from src.main import app
from src.models.borrower import Address, BorrowerRecord, IncomeRecord
from src.models.document import SourceReference
from src.storage.database import get_db_session
from src.storage.models import Borrower


@pytest.fixture
def mock_borrower_extractor_with_ssn_no_dashes():
    """Create mock BorrowerExtractor that returns borrower with SSN without dashes.

    This simulates the extraction returning an SSN in the format "987654321"
    instead of "987-65-4321", which should be normalized during persistence.
    """
    from src.models.borrower import Address, BorrowerRecord, IncomeRecord
    from src.models.document import SourceReference

    extractor = MagicMock(spec=BorrowerExtractor)

    def create_mock_extract(document, document_id, document_name):
        """Create extraction result with SSN without dashes."""
        source = SourceReference(
            document_id=document_id,
            document_name=document_name,
            page_number=1,
            snippet="Jane Doe, SSN: 987654321, employed at Tech Corp",
        )

        # CRITICAL: SSN has NO DASHES - should be normalized by the system
        borrower = BorrowerRecord(
            id=uuid4(),
            name="Jane Doe",
            ssn="987654321",  # NO DASHES - this should be normalized
            phone="(555) 987-6543",
            email="jane.doe@example.com",
            address=Address(
                street="456 Oak Ave",
                city="Dallas",
                state="TX",
                zip_code="75201",
            ),
            income_history=[
                IncomeRecord(
                    amount=Decimal("85000.00"),
                    period="annual",
                    year=2024,
                    source_type="employment",
                    employer="Tech Corp",
                ),
            ],
            account_numbers=["9876543210"],
            loan_numbers=["LOAN-2024-002"],
            sources=[source],
            confidence_score=Decimal("0.95"),
        )

        return ExtractionResult(
            borrowers=[borrower],
            complexity=ComplexityAssessment(
                level=ComplexityLevel.STANDARD,
                reasons=["Single borrower, standard format"],
                page_count=1,
                estimated_borrowers=1,
                has_handwritten=False,
                has_poor_quality=False,
            ),
            chunks_processed=1,
            total_tokens=150,
            validation_errors=[],
            consistency_warnings=[],
        )

    extractor.extract = MagicMock(side_effect=create_mock_extract)
    return extractor


@pytest.fixture
async def client_with_ssn_no_dashes(
    async_engine,
    mock_gcs_client,
    mock_docling_processor,
    mock_borrower_extractor_with_ssn_no_dashes,
):
    """Test client that extracts SSN without dashes."""
    session_factory = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_db_session():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    def override_get_borrower_extractor():
        return mock_borrower_extractor_with_ssn_no_dashes

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_gcs_client] = lambda: mock_gcs_client
    app.dependency_overrides[get_docling_processor] = lambda: mock_docling_processor
    app.dependency_overrides[get_borrower_extractor] = override_get_borrower_extractor

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as test_client:
        yield test_client, async_engine

    app.dependency_overrides.clear()


@pytest.mark.integration
class TestSSNNormalization:
    """TDD tests for SSN normalization issue."""

    @pytest.mark.asyncio
    async def test_ssn_without_dashes_should_be_normalized_and_persisted(
        self,
        client_with_ssn_no_dashes,
    ):
        """Test that SSN without dashes is normalized to include dashes.

        This test exposes the bug where:
        1. LLM extracts SSN as "987654321" (no dashes)
        2. FieldValidator accepts it (regex allows optional dashes)
        3. BorrowerRecord creation FAILS (Pydantic requires dashes)
        4. Borrower is skipped instead of being persisted with normalized SSN

        Expected: SSN should be normalized to "987-65-4321" and persisted.
        Current (buggy): Borrower is skipped due to Pydantic validation error.
        """
        client, async_engine = client_with_ssn_no_dashes

        # Upload a document (will trigger extraction with SSN without dashes)
        files = {"file": ("loan_doc.pdf", b"fake pdf content", "application/pdf")}
        response = await client.post("/api/documents/", files=files)

        if response.status_code != 201:
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "completed"

        # Verify borrower was persisted with normalized SSN
        async with async_sessionmaker(async_engine, expire_on_commit=False)() as session:
            result = await session.execute(select(Borrower))
            borrowers = result.scalars().all()

            # CRITICAL ASSERTION: Borrower should be persisted
            assert len(borrowers) == 1, (
                f"Expected 1 borrower to be persisted, but found {len(borrowers)}. "
                f"This indicates the SSN without dashes caused Pydantic validation "
                f"to fail, and the borrower was skipped."
            )

            borrower = borrowers[0]
            assert borrower.name == "Jane Doe"

            # SSN should be normalized to include dashes
            # Note: It's stored as a hash, so we can't check the actual value
            # But the fact that it was persisted means normalization worked

    @pytest.mark.asyncio
    async def test_ssn_with_dashes_should_work_as_before(
        self,
        client_with_extraction,  # Uses existing fixture with dashed SSN
    ):
        """Test that SSN with dashes continues to work (regression test)."""
        files = {"file": ("loan_doc.pdf", b"fake pdf content", "application/pdf")}
        response = await client_with_extraction.post("/api/documents/", files=files)

        assert response.status_code == 201

        # Verify borrower was persisted
        borrowers_response = await client_with_extraction.get("/api/borrowers/")
        assert borrowers_response.status_code == 200
        data = borrowers_response.json()
        assert data.get("total", 0) >= 1
