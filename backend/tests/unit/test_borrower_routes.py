"""Unit tests for borrower API endpoints.

Uses FastAPI TestClient with dependency injection overrides
to mock the BorrowerRepository for isolated unit testing.
"""

from datetime import datetime, UTC
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import get_borrower_repository
from src.main import app
from src.storage.models import (
    AccountNumber,
    Borrower,
    Document,
    DocumentStatus,
    IncomeRecord,
    SourceReference,
)


@pytest.fixture
def mock_borrower() -> Borrower:
    """Create a mock borrower for testing."""
    borrower = Borrower(
        id=uuid4(),
        name="John Smith",
        ssn_hash="abc123hash",
        address_json='{"street": "123 Main St", "city": "Austin"}',
        confidence_score=Decimal("0.95"),
    )
    borrower.created_at = datetime.now(UTC)
    return borrower


@pytest.fixture
def mock_borrower_with_relations(mock_borrower: Borrower) -> Borrower:
    """Create a mock borrower with income, accounts, and sources."""
    # Add income record
    income = IncomeRecord(
        id=uuid4(),
        borrower_id=mock_borrower.id,
        amount=Decimal("75000.00"),
        period="annual",
        year=2024,
        source_type="W2",
        employer="Acme Corp",
    )
    mock_borrower.income_records = [income]

    # Add account number
    account = AccountNumber(
        id=uuid4(),
        borrower_id=mock_borrower.id,
        number="ACC-12345",
        account_type="loan",
    )
    mock_borrower.account_numbers = [account]

    # Add source reference with document
    doc = Document(
        id=uuid4(),
        filename="test.pdf",
        file_hash="hash123",
        file_type="pdf",
        file_size_bytes=1024,
        status=DocumentStatus.COMPLETED,
    )
    source = SourceReference(
        id=uuid4(),
        borrower_id=mock_borrower.id,
        document_id=doc.id,
        page_number=1,
        section="Income",
        snippet="John Smith earned $75,000 in 2024",
    )
    source.document = doc
    mock_borrower.source_references = [source]

    return mock_borrower


@pytest.fixture
def client() -> TestClient:
    """Create test client without async (for sync tests)."""
    return TestClient(app)


class TestListBorrowers:
    """Tests for GET /api/borrowers/ endpoint."""

    def test_list_borrowers_returns_paginated_response(
        self, client: TestClient, mock_borrower: Borrower
    ):
        """Test listing borrowers returns paginated response."""
        mock_repo = AsyncMock()
        mock_borrower.income_records = []  # Empty for list view
        mock_repo.list_borrowers.return_value = [mock_borrower]
        mock_repo.count.return_value = 1

        app.dependency_overrides[get_borrower_repository] = lambda: mock_repo

        try:
            response = client.get("/api/borrowers/")
            assert response.status_code == 200

            data = response.json()
            assert "borrowers" in data
            assert "total" in data
            assert "limit" in data
            assert "offset" in data
            assert data["total"] == 1
            assert data["limit"] == 100
            assert data["offset"] == 0
            assert len(data["borrowers"]) == 1
            assert data["borrowers"][0]["name"] == "John Smith"
        finally:
            app.dependency_overrides.clear()

    def test_list_borrowers_respects_pagination(
        self, client: TestClient, mock_borrower: Borrower
    ):
        """Test listing borrowers with custom pagination params."""
        mock_repo = AsyncMock()
        mock_borrower.income_records = []
        mock_repo.list_borrowers.return_value = [mock_borrower]
        mock_repo.count.return_value = 50

        app.dependency_overrides[get_borrower_repository] = lambda: mock_repo

        try:
            response = client.get("/api/borrowers/?limit=10&offset=5")
            assert response.status_code == 200

            # Verify repository was called with correct params
            mock_repo.list_borrowers.assert_called_once_with(limit=10, offset=5)

            data = response.json()
            assert data["limit"] == 10
            assert data["offset"] == 5
        finally:
            app.dependency_overrides.clear()

    def test_list_borrowers_returns_income_count(
        self, client: TestClient, mock_borrower_with_relations: Borrower
    ):
        """Test listing borrowers includes computed income_count."""
        mock_repo = AsyncMock()
        mock_repo.list_borrowers.return_value = [mock_borrower_with_relations]
        mock_repo.count.return_value = 1

        app.dependency_overrides[get_borrower_repository] = lambda: mock_repo

        try:
            response = client.get("/api/borrowers/")
            assert response.status_code == 200

            data = response.json()
            assert data["borrowers"][0]["income_count"] == 1
        finally:
            app.dependency_overrides.clear()


class TestSearchBorrowers:
    """Tests for GET /api/borrowers/search endpoint."""

    def test_search_by_name_returns_matches(
        self, client: TestClient, mock_borrower: Borrower
    ):
        """Test searching by name returns matching borrowers."""
        mock_repo = AsyncMock()
        mock_borrower.income_records = []
        mock_repo.search_by_name.return_value = [mock_borrower]

        app.dependency_overrides[get_borrower_repository] = lambda: mock_repo

        try:
            response = client.get("/api/borrowers/search?name=john")
            assert response.status_code == 200

            data = response.json()
            assert len(data["borrowers"]) == 1
            assert data["borrowers"][0]["name"] == "John Smith"

            mock_repo.search_by_name.assert_called_once_with(
                "john", limit=100, offset=0
            )
        finally:
            app.dependency_overrides.clear()

    def test_search_by_account_returns_matches(
        self, client: TestClient, mock_borrower_with_relations: Borrower
    ):
        """Test searching by account number returns matching borrowers."""
        mock_repo = AsyncMock()
        mock_repo.search_by_account.return_value = [mock_borrower_with_relations]

        app.dependency_overrides[get_borrower_repository] = lambda: mock_repo

        try:
            response = client.get("/api/borrowers/search?account_number=12345")
            assert response.status_code == 200

            data = response.json()
            assert len(data["borrowers"]) == 1
            assert data["borrowers"][0]["name"] == "John Smith"

            mock_repo.search_by_account.assert_called_once_with(
                "12345", limit=100, offset=0
            )
        finally:
            app.dependency_overrides.clear()

    def test_search_requires_parameter(self, client: TestClient):
        """Test search without name or account_number returns 400."""
        mock_repo = AsyncMock()
        app.dependency_overrides[get_borrower_repository] = lambda: mock_repo

        try:
            response = client.get("/api/borrowers/search")
            assert response.status_code == 400
            assert "required" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_search_name_minimum_length(self, client: TestClient):
        """Test search with too short name returns validation error."""
        mock_repo = AsyncMock()
        app.dependency_overrides[get_borrower_repository] = lambda: mock_repo

        try:
            response = client.get("/api/borrowers/search?name=j")
            assert response.status_code == 422  # Validation error
        finally:
            app.dependency_overrides.clear()


class TestGetBorrower:
    """Tests for GET /api/borrowers/{id} endpoint."""

    def test_get_borrower_returns_detail(
        self, client: TestClient, mock_borrower_with_relations: Borrower
    ):
        """Test getting borrower by ID returns full details."""
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = mock_borrower_with_relations

        app.dependency_overrides[get_borrower_repository] = lambda: mock_repo

        try:
            borrower_id = str(mock_borrower_with_relations.id)
            response = client.get(f"/api/borrowers/{borrower_id}")
            assert response.status_code == 200

            data = response.json()
            assert data["id"] == borrower_id
            assert data["name"] == "John Smith"
            assert data["confidence_score"] == "0.95"

            # Check relationships are included
            assert len(data["income_records"]) == 1
            assert data["income_records"][0]["amount"] == "75000.00"
            assert data["income_records"][0]["employer"] == "Acme Corp"

            assert len(data["account_numbers"]) == 1
            assert data["account_numbers"][0]["number"] == "ACC-12345"

            assert len(data["source_references"]) == 1
            assert data["source_references"][0]["page_number"] == 1
        finally:
            app.dependency_overrides.clear()

    def test_get_borrower_not_found(self, client: TestClient):
        """Test getting non-existent borrower returns 404."""
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None

        app.dependency_overrides[get_borrower_repository] = lambda: mock_repo

        try:
            fake_id = str(uuid4())
            response = client.get(f"/api/borrowers/{fake_id}")
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_get_borrower_invalid_uuid(self, client: TestClient):
        """Test getting borrower with invalid UUID returns 422."""
        mock_repo = AsyncMock()
        app.dependency_overrides[get_borrower_repository] = lambda: mock_repo

        try:
            response = client.get("/api/borrowers/not-a-uuid")
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()


class TestGetBorrowerSources:
    """Tests for GET /api/borrowers/{id}/sources endpoint."""

    def test_get_borrower_sources(
        self, client: TestClient, mock_borrower_with_relations: Borrower
    ):
        """Test getting source documents for a borrower."""
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = mock_borrower_with_relations

        app.dependency_overrides[get_borrower_repository] = lambda: mock_repo

        try:
            borrower_id = str(mock_borrower_with_relations.id)
            response = client.get(f"/api/borrowers/{borrower_id}/sources")
            assert response.status_code == 200

            data = response.json()
            assert data["borrower_id"] == borrower_id
            assert data["borrower_name"] == "John Smith"
            assert len(data["sources"]) == 1
            assert data["sources"][0]["page_number"] == 1
            assert data["sources"][0]["section"] == "Income"
            assert "75,000" in data["sources"][0]["snippet"]
        finally:
            app.dependency_overrides.clear()

    def test_get_borrower_sources_not_found(self, client: TestClient):
        """Test getting sources for non-existent borrower returns 404."""
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None

        app.dependency_overrides[get_borrower_repository] = lambda: mock_repo

        try:
            fake_id = str(uuid4())
            response = client.get(f"/api/borrowers/{fake_id}/sources")
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()
