"""Integration tests for document API endpoints.

Includes tests for:
- Successful uploads (PDF, DOCX, PNG)
- Validation errors (file type, size)
- Duplicate detection
- GCS failures (INGEST-14: graceful error handling)
- Document retrieval
- Document listing
"""

import pytest
from httpx import AsyncClient


class TestDocumentUpload:
    """Tests for POST /api/documents."""

    @pytest.mark.asyncio
    async def test_upload_pdf_success(self, client: AsyncClient):
        """Test successful PDF upload."""
        files = {
            "file": ("test.pdf", b"%PDF-1.4 test content", "application/pdf")
        }

        response = await client.post("/api/documents/", files=files)

        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "test.pdf"
        # CRITICAL: Status should be 'pending' (processing is async)
        assert data["status"] == "pending"
        assert "id" in data
        assert "file_hash" in data
        assert len(data["file_hash"]) == 64  # SHA-256

    @pytest.mark.asyncio
    async def test_upload_returns_pending_not_completed(self, client: AsyncClient):
        """Test that upload returns PENDING status (not COMPLETED)."""
        files = {
            "file": ("test.pdf", b"%PDF-1.4 test content", "application/pdf")
        }

        response = await client.post("/api/documents/", files=files)

        assert response.status_code == 201
        data = response.json()
        # CRITICAL: This verifies async processing model
        assert data["status"] == "pending", "Upload should return PENDING, not COMPLETED (processing is async)"
        assert "asynchronous" in data["message"].lower() or "poll" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_upload_docx_success(self, client: AsyncClient):
        """Test successful DOCX upload."""
        docx_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        files = {
            "file": ("document.docx", b"docx content", docx_mime)
        }

        response = await client.post("/api/documents/", files=files)

        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "document.docx"
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_upload_image_success(self, client: AsyncClient):
        """Test successful image upload (PNG)."""
        files = {
            "file": ("scan.png", b"\x89PNG\r\n\x1a\n fake png", "image/png")
        }

        response = await client.post("/api/documents/", files=files)

        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "scan.png"
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_upload_unsupported_type_rejected(self, client: AsyncClient):
        """Test that unsupported file types are rejected (INGEST-14: graceful error)."""
        files = {
            "file": ("readme.txt", b"text content", "text/plain")
        }

        response = await client.post("/api/documents/", files=files)

        # Should return 400, not crash
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_duplicate_rejected(self, client: AsyncClient):
        """Test that duplicate uploads are rejected (INGEST-14: graceful error)."""
        content = b"%PDF-1.4 duplicate test"
        files = {
            "file": ("first.pdf", content, "application/pdf")
        }

        # First upload succeeds
        response1 = await client.post("/api/documents/", files=files)
        assert response1.status_code == 201

        # Second upload with same content fails
        files2 = {
            "file": ("second.pdf", content, "application/pdf")
        }
        response2 = await client.post("/api/documents/", files=files2)

        # Should return 409, not crash
        assert response2.status_code == 409
        data = response2.json()["detail"]
        assert data["message"] == "Duplicate document detected"
        assert "existing_id" in data


class TestDocumentUploadErrorHandling:
    """Tests for error handling (INGEST-14: graceful error handling without crash)."""

    @pytest.mark.asyncio
    async def test_gcs_failure_returns_500_not_crash(self, client_with_failing_gcs: AsyncClient):
        """Test that GCS upload failure returns 500, doesn't crash app (INGEST-14)."""
        files = {
            "file": ("test.pdf", b"%PDF-1.4 test content", "application/pdf")
        }

        response = await client_with_failing_gcs.post("/api/documents/", files=files)

        # Should return 500, not crash
        assert response.status_code == 500
        detail = response.json()["detail"].lower()
        assert "upload" in detail or "storage" in detail

    @pytest.mark.asyncio
    async def test_empty_file_handled_gracefully(self, client: AsyncClient):
        """Test that empty file is handled gracefully (INGEST-14)."""
        files = {
            "file": ("empty.pdf", b"", "application/pdf")
        }

        response = await client.post("/api/documents/", files=files)

        # Should either succeed (empty is technically valid) or return error
        # It should NOT crash
        assert response.status_code in [201, 400, 500]

    @pytest.mark.asyncio
    async def test_missing_filename_handled(self, client: AsyncClient):
        """Test that missing filename is handled gracefully."""
        files = {
            "file": (None, b"%PDF-1.4 test", "application/pdf")
        }

        response = await client.post("/api/documents/", files=files)

        # Should handle gracefully - 422 is valid (FastAPI validation), 201/400 also acceptable
        assert response.status_code in [201, 400, 422]

    @pytest.mark.asyncio
    async def test_invalid_content_type_handled(self, client: AsyncClient):
        """Test that invalid content type is handled gracefully."""
        files = {
            "file": ("test.xyz", b"some content", "application/x-unknown")
        }

        response = await client.post("/api/documents/", files=files)

        # Should return 400, not crash
        assert response.status_code == 400
        assert "Unsupported" in response.json()["detail"]


class TestDocumentGet:
    """Tests for GET /api/documents/{id}."""

    @pytest.mark.asyncio
    async def test_get_document_success(self, client: AsyncClient):
        """Test getting document by ID."""
        # First upload a document
        files = {
            "file": ("test.pdf", b"%PDF get test", "application/pdf")
        }
        upload_response = await client.post("/api/documents/", files=files)
        document_id = upload_response.json()["id"]

        # Then get it by ID
        response = await client.get(f"/api/documents/{document_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == document_id
        assert data["filename"] == "test.pdf"
        assert data["file_type"] == "pdf"
        assert data["status"] == "pending"  # Still pending (not processed)

    @pytest.mark.asyncio
    async def test_get_document_not_found(self, client: AsyncClient):
        """Test getting non-existent document (INGEST-14: graceful error)."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/api/documents/{fake_id}")

        # Should return 404, not crash
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_document_invalid_uuid(self, client: AsyncClient):
        """Test getting document with invalid UUID format."""
        response = await client.get("/api/documents/not-a-uuid")

        # Should return 422 (validation error), not crash
        assert response.status_code == 422


class TestDocumentList:
    """Tests for GET /api/documents."""

    @pytest.mark.asyncio
    async def test_list_documents_empty(self, client: AsyncClient):
        """Test listing documents when none exist."""
        response = await client.get("/api/documents/")

        assert response.status_code == 200
        data = response.json()
        assert data["documents"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_documents_with_data(self, client: AsyncClient):
        """Test listing documents after uploads."""
        # Upload two documents
        for i in range(2):
            files = {
                "file": (f"doc{i}.pdf", f"content {i}".encode(), "application/pdf")
            }
            await client.post("/api/documents/", files=files)

        response = await client.get("/api/documents/")

        assert response.status_code == 200
        data = response.json()
        assert len(data["documents"]) == 2

    @pytest.mark.asyncio
    async def test_list_documents_pagination(self, client: AsyncClient):
        """Test document list pagination."""
        # Upload 3 documents
        for i in range(3):
            files = {
                "file": (f"page{i}.pdf", f"page content {i}".encode(), "application/pdf")
            }
            await client.post("/api/documents/", files=files)

        # Get first page
        response = await client.get("/api/documents/?limit=2&offset=0")
        data = response.json()
        assert len(data["documents"]) == 2
        assert data["limit"] == 2
        assert data["offset"] == 0

        # Get second page
        response = await client.get("/api/documents/?limit=2&offset=2")
        data = response.json()
        assert len(data["documents"]) == 1


class TestHealthCheck:
    """Tests for health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test health check returns healthy."""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
