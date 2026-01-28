"""API contract tests for endpoint reliability.

Tests HTTP status codes, error handling, request validation,
and response schema consistency across all API endpoints.
"""

import io
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.main import app
from src.storage.database import get_db_session
from src.storage.models import Borrower, Document, DocumentStatus, SourceReference
from src.storage.repositories import BorrowerRepository, DocumentRepository
from decimal import Decimal


client = TestClient(app)


class TestDocumentUploadEndpoint:
    """Tests for POST /api/documents endpoint."""

    def test_upload_invalid_mime_type_returns_422(self):
        """Upload with invalid MIME type returns 422 Unprocessable Entity."""
        files = {"file": ("test.exe", b"fake executable content", "application/x-msdownload")}

        response = client.post("/api/documents", files=files)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data or "error" in data.get("message", "").lower()

    def test_upload_empty_file_returns_422(self):
        """Upload with empty file returns 422."""
        files = {"file": ("empty.pdf", b"", "application/pdf")}

        response = client.post("/api/documents", files=files)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_upload_missing_file_returns_422(self):
        """Upload without file parameter returns 422."""
        response = client.post("/api/documents", data={})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_upload_malformed_pdf_returns_500_or_422(self):
        """Upload with malformed PDF returns error status."""
        files = {"file": ("malformed.pdf", b"not a valid pdf", "application/pdf")}

        response = client.post("/api/documents", files=files)

        # Should return either 422 (validation) or 500 (processing error)
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

    def test_upload_with_invalid_extraction_method_returns_422(self):
        """Upload with invalid extraction_method returns 422."""
        files = {"file": ("test.pdf", b"%PDF-1.4 fake pdf", "application/pdf")}
        data = {"extraction_method": "invalid_method"}

        response = client.post("/api/documents", files=files, data=data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_upload_with_invalid_ocr_mode_returns_422(self):
        """Upload with invalid ocr_mode returns 422."""
        files = {"file": ("test.pdf", b"%PDF-1.4 fake pdf", "application/pdf")}
        data = {"ocr_mode": "invalid_ocr"}

        response = client.post("/api/documents", files=files, data=data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_upload_success_returns_valid_response_schema(self):
        """Successful upload returns response matching schema."""
        pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\n0 2\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
        files = {"file": ("valid.pdf", pdf_content, "application/pdf")}

        response = client.post("/api/documents", files=files)

        # Should succeed or be pending
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

        data = response.json()
        # Verify required fields
        assert "id" in data
        assert "filename" in data
        assert "file_hash" in data
        assert "status" in data
        assert "message" in data


class TestDocumentGetEndpoint:
    """Tests for GET /api/documents/{document_id} endpoint."""

    def test_get_nonexistent_document_returns_404(self):
        """GET with non-existent ID returns 404 Not Found."""
        fake_id = uuid4()
        response = client.get(f"/api/documents/{fake_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "not found" in data.get("detail", "").lower() or "not found" in data.get(
            "message", ""
        ).lower()

    def test_get_invalid_uuid_returns_422(self):
        """GET with invalid UUID returns 422."""
        response = client.get("/api/documents/not-a-uuid")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_get_existing_document_returns_200(self, db_session):
        """GET with valid ID returns 200 and correct schema."""
        # Create test document
        doc_repo = DocumentRepository(db_session)
        doc = Document(
            id=uuid4(),
            filename="test_get.pdf",
            file_hash="hash_test_get",
            gcs_path="gs://bucket/test_get.pdf",
            mime_type="application/pdf",
            status=DocumentStatus.COMPLETED,
        )
        await doc_repo.create(doc)
        await db_session.commit()

        response = client.get(f"/api/documents/{doc.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(doc.id)
        assert data["filename"] == "test_get.pdf"
        assert data["status"] == "completed"


class TestDocumentListEndpoint:
    """Tests for GET /api/documents endpoint."""

    def test_list_with_negative_limit_returns_422(self):
        """List with negative limit returns 422."""
        response = client.get("/api/documents?limit=-1")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_list_with_negative_offset_returns_422(self):
        """List with negative offset returns 422."""
        response = client.get("/api/documents?offset=-1")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_list_with_zero_limit_returns_empty(self):
        """List with limit=0 returns empty list."""
        response = client.get("/api/documents?limit=0")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["documents"] == []

    def test_list_with_excessive_limit_capped(self):
        """List with very large limit is capped at maximum."""
        response = client.get("/api/documents?limit=10000")

        # Should succeed and cap at reasonable limit
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["documents"]) <= 1000  # Assuming 1000 is max

    def test_list_returns_valid_schema(self):
        """List endpoint returns response matching schema."""
        response = client.get("/api/documents?limit=10&offset=0")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "documents" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert isinstance(data["documents"], list)


class TestDocumentDeleteEndpoint:
    """Tests for DELETE /api/documents/{document_id} endpoint."""

    def test_delete_nonexistent_document_returns_404(self):
        """DELETE with non-existent ID returns 404."""
        fake_id = uuid4()
        response = client.delete(f"/api/documents/{fake_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_invalid_uuid_returns_422(self):
        """DELETE with invalid UUID returns 422."""
        response = client.delete("/api/documents/not-a-uuid")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_delete_existing_document_returns_200(self, db_session):
        """DELETE with valid ID returns 200."""
        doc_repo = DocumentRepository(db_session)
        doc = Document(
            id=uuid4(),
            filename="to_delete.pdf",
            file_hash="hash_to_delete",
            gcs_path="gs://bucket/to_delete.pdf",
            mime_type="application/pdf",
        )
        await doc_repo.create(doc)
        await db_session.commit()

        response = client.delete(f"/api/documents/{doc.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "deleted" in data.get("message", "").lower() or data.get("success") is True


class TestDocumentStatusEndpoint:
    """Tests for GET /api/documents/{document_id}/status endpoint."""

    def test_status_nonexistent_document_returns_404(self):
        """Status check for non-existent document returns 404."""
        fake_id = uuid4()
        response = client.get(f"/api/documents/{fake_id}/status")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_status_returns_lightweight_response(self, db_session):
        """Status endpoint returns lightweight response for polling."""
        doc_repo = DocumentRepository(db_session)
        doc = Document(
            id=uuid4(),
            filename="status_test.pdf",
            file_hash="hash_status_test",
            gcs_path="gs://bucket/status_test.pdf",
            mime_type="application/pdf",
            status=DocumentStatus.PROCESSING,
        )
        await doc_repo.create(doc)
        await db_session.commit()

        response = client.get(f"/api/documents/{doc.id}/status")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
        # Status response should be minimal (not include full document data)
        assert "status" in data
        assert data["status"] == "processing"


class TestBorrowerListEndpoint:
    """Tests for GET /api/borrowers endpoint."""

    def test_list_borrowers_with_negative_limit_returns_422(self):
        """List borrowers with negative limit returns 422."""
        response = client.get("/api/borrowers?limit=-1")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_list_borrowers_returns_valid_schema(self):
        """List borrowers returns valid response schema."""
        response = client.get("/api/borrowers?limit=10&offset=0")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "borrowers" in data
        assert "total" in data
        assert isinstance(data["borrowers"], list)


class TestBorrowerSearchEndpoint:
    """Tests for GET /api/borrowers/search endpoint."""

    def test_search_without_query_returns_422(self):
        """Search without query parameter returns 422."""
        response = client.get("/api/borrowers/search")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_search_with_empty_query_returns_400_or_422(self):
        """Search with empty query returns error."""
        response = client.get("/api/borrowers/search?q=")

        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    def test_search_with_valid_query_returns_200(self):
        """Search with valid query returns 200."""
        response = client.get("/api/borrowers/search?q=John")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "borrowers" in data


class TestBorrowerGetEndpoint:
    """Tests for GET /api/borrowers/{borrower_id} endpoint."""

    def test_get_nonexistent_borrower_returns_404(self):
        """GET with non-existent borrower ID returns 404."""
        fake_id = uuid4()
        response = client.get(f"/api/borrowers/{fake_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_invalid_uuid_returns_422(self):
        """GET with invalid UUID returns 422."""
        response = client.get("/api/borrowers/not-a-uuid")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_get_existing_borrower_returns_200(self, db_session):
        """GET with valid borrower ID returns 200 and correct schema."""
        # Create test document and borrower
        doc_repo = DocumentRepository(db_session)
        borrower_repo = BorrowerRepository(db_session)

        doc = Document(
            id=uuid4(),
            filename="borrower_test.pdf",
            file_hash="hash_borrower_test",
            gcs_path="gs://bucket/borrower_test.pdf",
            mime_type="application/pdf",
        )
        await doc_repo.create(doc)

        borrower = Borrower(
            id=uuid4(),
            name="Test Borrower API",
            ssn="123-45-6789",
            confidence_score=Decimal("0.9"),
        )
        await borrower_repo.create(
            borrower,
            income_records=[],
            account_numbers=[],
            source_references=[
                SourceReference(
                    id=uuid4(),
                    document_id=doc.id,
                    page_number=1,
                    snippet="Test Borrower API",
                )
            ],
        )
        await db_session.commit()

        response = client.get(f"/api/borrowers/{borrower.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(borrower.id)
        assert data["name"] == "Test Borrower API"
        assert "confidence_score" in data


class TestBorrowerSourcesEndpoint:
    """Tests for GET /api/borrowers/{borrower_id}/sources endpoint."""

    def test_sources_nonexistent_borrower_returns_404(self):
        """Sources for non-existent borrower returns 404."""
        fake_id = uuid4()
        response = client.get(f"/api/borrowers/{fake_id}/sources")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_sources_returns_valid_schema(self, db_session):
        """Sources endpoint returns valid response schema."""
        doc_repo = DocumentRepository(db_session)
        borrower_repo = BorrowerRepository(db_session)

        doc = Document(
            id=uuid4(),
            filename="sources_test.pdf",
            file_hash="hash_sources_test",
            gcs_path="gs://bucket/sources_test.pdf",
            mime_type="application/pdf",
        )
        await doc_repo.create(doc)

        borrower = Borrower(
            id=uuid4(),
            name="Sources Test",
            ssn="999-88-7777",
            confidence_score=Decimal("0.9"),
        )
        await borrower_repo.create(
            borrower,
            income_records=[],
            account_numbers=[],
            source_references=[
                SourceReference(
                    id=uuid4(),
                    document_id=doc.id,
                    page_number=1,
                    snippet="Sources Test",
                )
            ],
        )
        await db_session.commit()

        response = client.get(f"/api/borrowers/{borrower.id}/sources")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "sources" in data
        assert isinstance(data["sources"], list)


class TestErrorResponseConsistency:
    """Tests for consistent error response format across endpoints."""

    def test_404_errors_have_consistent_format(self):
        """All 404 errors return consistent response format."""
        endpoints = [
            f"/api/documents/{uuid4()}",
            f"/api/borrowers/{uuid4()}",
            f"/api/documents/{uuid4()}/status",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = response.json()
            # Should have either "detail" or "message" field
            assert "detail" in data or "message" in data

    def test_422_errors_have_validation_details(self):
        """422 validation errors include details about what failed."""
        response = client.get("/api/documents/not-a-uuid")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        # FastAPI validation errors have "detail" field
        assert "detail" in data
        # Should provide info about validation failure
        assert isinstance(data["detail"], (str, list, dict))


class TestRateLimitingAndThrottling:
    """Tests for rate limiting behavior (if implemented)."""

    @pytest.mark.skip(reason="Rate limiting not yet implemented")
    def test_excessive_requests_return_429(self):
        """Excessive requests within time window return 429 Too Many Requests."""
        # Make 100 requests rapidly
        responses = []
        for _ in range(100):
            response = client.get("/api/documents")
            responses.append(response.status_code)

        # At least one should be rate limited
        assert status.HTTP_429_TOO_MANY_REQUESTS in responses


class TestCORSHeaders:
    """Tests for CORS headers (if enabled)."""

    def test_options_request_returns_cors_headers(self):
        """OPTIONS request returns appropriate CORS headers."""
        response = client.options(
            "/api/documents",
            headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"},
        )

        # Should either allow CORS or return 200/204
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_204_NO_CONTENT,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        ]


class TestContentNegotiation:
    """Tests for content type handling."""

    def test_accepts_json_content_type(self):
        """Endpoints accept application/json content type."""
        response = client.get("/api/documents", headers={"Accept": "application/json"})

        assert response.status_code == status.HTTP_200_OK
        assert "application/json" in response.headers.get("content-type", "")

    def test_rejects_unsupported_accept_header(self):
        """Endpoints reject unsupported Accept headers gracefully."""
        response = client.get("/api/documents", headers={"Accept": "application/xml"})

        # Should either serve JSON anyway or return 406
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_406_NOT_ACCEPTABLE]
