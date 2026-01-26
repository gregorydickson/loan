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
        # CRITICAL: Status should be 'completed' (processing is synchronous)
        assert data["status"] == "completed"
        assert "id" in data
        assert "file_hash" in data
        assert len(data["file_hash"]) == 64  # SHA-256

    @pytest.mark.asyncio
    async def test_upload_processes_pdf_to_completed(self, client: AsyncClient):
        """Test that upload processes document and status becomes COMPLETED."""
        files = {"file": ("test.pdf", b"%PDF-1.4 test", "application/pdf")}
        response = await client.post("/api/documents/", files=files)

        assert response.status_code == 201
        data = response.json()
        # CRITICAL: Status should now be 'completed' (not 'pending')
        assert data["status"] == "completed"
        assert data["page_count"] == 1

    @pytest.mark.asyncio
    async def test_upload_populates_page_count(self, client: AsyncClient):
        """Test that page_count is set after processing."""
        files = {"file": ("doc.pdf", b"%PDF-1.4 content", "application/pdf")}
        response = await client.post("/api/documents/", files=files)

        assert response.status_code == 201
        assert response.json()["page_count"] is not None
        assert response.json()["page_count"] >= 1

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
        assert data["status"] == "completed"

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
        assert data["status"] == "completed"

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


class TestDocumentProcessingErrors:
    """Tests for processing error handling (Gap 2 closure)."""

    @pytest.mark.asyncio
    async def test_corrupted_pdf_becomes_failed(self, client_with_failing_docling: AsyncClient):
        """Test that corrupted PDF results in FAILED status (INGEST-14)."""
        files = {"file": ("bad.pdf", b"not a pdf", "application/pdf")}
        response = await client_with_failing_docling.post("/api/documents/", files=files)

        # Upload succeeds (201) but status is 'failed'
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "failed"
        assert data.get("error_message") is not None

    @pytest.mark.asyncio
    async def test_processing_error_does_not_crash(self, client_with_failing_docling: AsyncClient):
        """Test that processing error doesn't crash the app (INGEST-14)."""
        files = {"file": ("corrupt.pdf", b"corrupted", "application/pdf")}
        response = await client_with_failing_docling.post("/api/documents/", files=files)

        # Should return 201 (upload succeeded), not 500 (crash)
        assert response.status_code == 201
        # Server is still running - make another request
        health = await client_with_failing_docling.get("/health")
        assert health.status_code == 200

    @pytest.mark.asyncio
    async def test_processing_error_includes_error_message(
        self, client_with_failing_docling: AsyncClient
    ):
        """Test that processing error includes error_message in response."""
        files = {"file": ("invalid.pdf", b"invalid content", "application/pdf")}
        response = await client_with_failing_docling.post("/api/documents/", files=files)

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "failed"
        assert "error_message" in data
        assert data["error_message"] is not None
        assert "processing failed" in data["error_message"].lower()


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
        assert data["status"] == "completed"  # Processed synchronously

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
    async def test_list_documents_rejects_negative_offset(self, client: AsyncClient):
        """Test that negative offset is rejected (TDD Issue #3)."""
        response = await client.get("/api/documents/?offset=-1")

        # Should return 422 validation error, not crash
        assert response.status_code == 422
        assert "detail" in response.json()

    @pytest.mark.asyncio
    async def test_list_documents_rejects_excessive_limit(self, client: AsyncClient):
        """Test that limit > 1000 is rejected (TDD Issue #3)."""
        response = await client.get("/api/documents/?limit=999999")

        # Should return 422 validation error, not try to load 999999 documents
        assert response.status_code == 422
        assert "detail" in response.json()

    @pytest.mark.asyncio
    async def test_list_documents_rejects_zero_limit(self, client: AsyncClient):
        """Test that limit=0 is rejected (TDD Issue #3)."""
        response = await client.get("/api/documents/?limit=0")

        # Should return 422 validation error
        assert response.status_code == 422
        assert "detail" in response.json()

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

    @pytest.mark.asyncio
    async def test_list_documents_total_is_accurate(self, client: AsyncClient):
        """Test that 'total' reflects total count in DB, not just page size.

        TDD: This test should fail initially because current implementation
        returns len(documents) instead of total count from database.
        """
        # Upload 5 documents
        for i in range(5):
            files = {
                "file": (f"total{i}.pdf", f"total content {i}".encode(), "application/pdf")
            }
            await client.post("/api/documents/", files=files)

        # Request first page with limit=2
        response = await client.get("/api/documents/?limit=2&offset=0")
        data = response.json()

        # CRITICAL: total should be 5 (all docs), not 2 (page size)
        assert data["total"] == 5, f"Expected total=5, got total={data['total']}"
        assert len(data["documents"]) == 2  # Page contains 2
        assert data["limit"] == 2
        assert data["offset"] == 0

        # Request second page
        response = await client.get("/api/documents/?limit=2&offset=2")
        data = response.json()

        # total should still be 5 on every page
        assert data["total"] == 5
        assert len(data["documents"]) == 2  # Page contains 2

        # Request third page (last page, only 1 doc)
        response = await client.get("/api/documents/?limit=2&offset=4")
        data = response.json()

        # total should still be 5
        assert data["total"] == 5
        assert len(data["documents"]) == 1  # Last page has remainder


class TestDocumentStatus:
    """Tests for GET /api/documents/{id}/status endpoint."""

    @pytest.mark.asyncio
    async def test_get_status_success(self, client: AsyncClient):
        """Test getting document status returns correct fields."""
        # First upload a document
        files = {"file": ("test.pdf", b"%PDF status test", "application/pdf")}
        upload_response = await client.post("/api/documents/", files=files)
        document_id = upload_response.json()["id"]

        # Get status
        response = await client.get(f"/api/documents/{document_id}/status")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == document_id
        assert data["status"] == "completed"
        assert data["page_count"] is not None

    @pytest.mark.asyncio
    async def test_get_status_not_found(self, client: AsyncClient):
        """Test getting status for non-existent document returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/api/documents/{fake_id}/status")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_status_failed_document(
        self, client_with_failing_docling: AsyncClient
    ):
        """Test getting status for failed document includes error_message."""
        files = {"file": ("bad.pdf", b"not a pdf", "application/pdf")}
        upload_response = await client_with_failing_docling.post(
            "/api/documents/", files=files
        )
        document_id = upload_response.json()["id"]

        response = await client_with_failing_docling.get(
            f"/api/documents/{document_id}/status"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error_message"] is not None


class TestBorrowerPersistenceTransaction:
    """Tests for borrower persistence transaction boundaries (TDD Issue #2)."""

    @pytest.mark.asyncio
    async def test_partial_borrower_failure_marks_document_failed(
        self, client_with_three_borrowers, monkeypatch
    ):
        """Test that if any borrower fails to persist, document is marked FAILED.

        TDD: This test should fail initially because current implementation
        logs the error and continues, leaving document as COMPLETED even when
        borrower persistence fails.
        """
        from src.ingestion.document_service import DocumentService

        # Track calls to _persist_borrower
        persist_call_count = 0
        original_persist = DocumentService._persist_borrower

        async def mock_persist_borrower(self, borrower_record, document_id):
            nonlocal persist_call_count
            persist_call_count += 1

            # Fail on second borrower to simulate partial failure
            if persist_call_count == 2:
                raise ValueError("Simulated database constraint violation for borrower 2")

            # Call original for other borrowers
            return await original_persist(self, borrower_record, document_id)

        monkeypatch.setattr(
            DocumentService, "_persist_borrower", mock_persist_borrower
        )

        # Upload a PDF (will extract 3 borrowers via fixture)
        pdf_content = b"%PDF-1.4 test content"
        files = {"file": ("test.pdf", pdf_content, "application/pdf")}

        response = await client_with_three_borrowers.post("/api/documents/", files=files)

        # The upload endpoint should catch the persistence failure
        # and mark document as FAILED (not COMPLETED)
        assert response.status_code == 201
        data = response.json()

        # CRITICAL: If any borrower fails to persist, document should be FAILED
        # Current implementation: status='completed' (BUG!)
        # Expected behavior: status='failed'
        assert data["status"] == "failed", (
            f"Expected document to be marked FAILED when borrower persistence fails, "
            f"got status='{data['status']}'. "
            f"Persistence was called {persist_call_count} times, "
            f"simulated failure on call #2."
        )
        assert data.get("error_message") is not None
        assert ("persist" in data["error_message"].lower()
                or "borrower" in data["error_message"].lower()
                or "database" in data["error_message"].lower())


class TestHealthCheck:
    """Tests for health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test health check returns healthy."""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
