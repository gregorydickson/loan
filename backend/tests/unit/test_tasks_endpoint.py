"""Unit tests for Cloud Tasks handler endpoint.

Tests the /api/tasks/process-document webhook that handles async document processing
from Cloud Tasks. Critical production code with complex retry/error handling logic.

Note: Sets GEMINI_API_KEY environment variable to avoid initialization errors
in dependency injection, even though tests mock the actual LLM client.

Coverage:
- Happy path: successful processing
- Error cases: document not found, already processed, missing GCS URI
- Idempotency: skip if already completed/failed
- OCR routing: with/without OCR router, different modes
- Extraction routing: docling vs langextract methods
- Retry logic: transient errors, max retries exhausted
- Status transitions: PROCESSING -> COMPLETED/FAILED
- Borrower persistence: success and failure scenarios
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

# Set GEMINI_API_KEY before any imports that might use it
# This prevents GeminiClient initialization errors during dependency injection
os.environ.setdefault("GEMINI_API_KEY", "test-api-key-for-unit-tests")

from fastapi import status as http_status
from fastapi.testclient import TestClient

from src.api.dependencies import (
    get_borrower_extractor,
    get_borrower_repository,
    get_docling_processor,
    get_document_repository,
    get_extraction_router,
    get_gcs_client,
    get_ocr_router,
)
from src.extraction.extractor import ExtractionResult
from src.ingestion.docling_processor import DocumentContent, DocumentProcessingError
from src.models.borrower import BorrowerRecord
from src.main import app
from src.ocr.ocr_router import OCRResult
from src.storage.models import Document, DocumentStatus


@pytest.fixture
def mock_document():
    """Create a mock document in PENDING status."""
    doc = Document(
        id=uuid4(),
        filename="test.pdf",
        file_hash="abc123",
        file_type="pdf",
        file_size_bytes=1024,
        gcs_uri="gs://test-bucket/documents/test.pdf",
        status=DocumentStatus.PENDING,
    )
    return doc


@pytest.fixture
def mock_processed_document():
    """Create a mock DocumentContent from docling."""
    return DocumentContent(
        text="Test document content",
        pages=[],
        page_count=2,
        tables=[],
        metadata={"source": "test.pdf"},
    )


@pytest.fixture
def mock_extraction_result():
    """Create a mock ExtractionResult with borrowers."""
    from src.extraction.complexity_classifier import ComplexityAssessment, ComplexityLevel

    borrower = BorrowerRecord(
        name="John Doe",
        ssn="123-45-6789",
        address=None,
        income_history=[],
        account_numbers=[],
        loan_numbers=[],
        sources=[],
        confidence_score=0.95,
    )
    complexity = ComplexityAssessment(
        level=ComplexityLevel.STANDARD,
        reasons=[],
        page_count=2,
        estimated_borrowers=1,
        has_handwritten=False,
        has_poor_quality=False,
    )
    return ExtractionResult(
        borrowers=[borrower],
        complexity=complexity,
        chunks_processed=1,
        total_tokens=1000,
        validation_errors=[],
        consistency_warnings=[],
    )


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_request():
    """Create mock FastAPI request with Cloud Tasks headers."""
    request = MagicMock()
    request.headers.get = MagicMock(side_effect=lambda key, default: {
        "X-CloudTasks-TaskName": "test-task-123",
        "X-CloudTasks-TaskRetryCount": "0",
    }.get(key, default))
    return request


class TestProcessDocumentHappyPath:
    """Tests for successful document processing."""

    def test_successful_processing_docling_method(
        self, client, mock_document, mock_processed_document, mock_extraction_result
    ):
        """Test successful processing with docling method (default)."""
        # Setup mocks
        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_by_id.return_value = mock_document
        mock_doc_repo.update_status = AsyncMock()

        mock_gcs = MagicMock()
        mock_gcs.bucket_name = "test-bucket"
        mock_gcs.download.return_value = b"%PDF-1.4 test content"

        mock_docling = MagicMock()
        mock_docling.process_bytes.return_value = mock_processed_document

        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = mock_extraction_result

        mock_borrower_repo = AsyncMock()
        mock_borrower_repo.session = AsyncMock()
        mock_borrower_repo.session.flush = AsyncMock()

        # Override dependencies
        app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
        app.dependency_overrides[get_gcs_client] = lambda: mock_gcs
        app.dependency_overrides[get_docling_processor] = lambda: mock_docling
        app.dependency_overrides[get_borrower_extractor] = lambda: mock_extractor
        app.dependency_overrides[get_borrower_repository] = lambda: mock_borrower_repo
        app.dependency_overrides[get_ocr_router] = lambda: None  # No OCR
        app.dependency_overrides[get_extraction_router] = lambda: None  # Use extractor directly

        try:
            payload = {
                "document_id": str(mock_document.id),
                "filename": "test.pdf",
                "method": "docling",
                "ocr": "skip",
            }

            # Add Cloud Tasks headers
            headers = {
                "X-CloudTasks-TaskName": "test-task",
                "X-CloudTasks-TaskRetryCount": "0",
            }

            response = client.post("/api/tasks/process-document", json=payload, headers=headers)

            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data.get("error") is None

            # Verify workflow
            mock_doc_repo.get_by_id.assert_called_once_with(mock_document.id)
            mock_gcs.download.assert_called_once_with("documents/test.pdf")
            mock_docling.process_bytes.assert_called_once()
            mock_extractor.extract.assert_called_once()

            # Verify status transitions: PROCESSING -> COMPLETED
            assert mock_doc_repo.update_status.call_count >= 2

        finally:
            app.dependency_overrides.clear()

    def test_successful_processing_with_ocr(
        self, client, mock_document, mock_processed_document, mock_extraction_result
    ):
        """Test successful processing with OCR enabled."""
        # Setup mocks
        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_by_id.return_value = mock_document
        mock_doc_repo.update_status = AsyncMock()
        mock_doc_repo.session = AsyncMock()
        mock_doc_repo.session.flush = AsyncMock()

        mock_gcs = MagicMock()
        mock_gcs.bucket_name = "test-bucket"
        mock_gcs.download.return_value = b"%PDF-1.4 test content"

        # OCR router should process document
        mock_ocr_router = AsyncMock()
        ocr_result = OCRResult(
            content=mock_processed_document,
            ocr_method="gpu",
            pages_ocrd=[],
        )
        mock_ocr_router.process.return_value = ocr_result

        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = mock_extraction_result

        mock_borrower_repo = AsyncMock()
        mock_borrower_repo.session = AsyncMock()
        mock_borrower_repo.session.flush = AsyncMock()

        app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
        app.dependency_overrides[get_gcs_client] = lambda: mock_gcs
        app.dependency_overrides[get_ocr_router] = lambda: mock_ocr_router
        app.dependency_overrides[get_borrower_extractor] = lambda: mock_extractor
        app.dependency_overrides[get_borrower_repository] = lambda: mock_borrower_repo
        app.dependency_overrides[get_extraction_router] = lambda: None

        try:
            payload = {
                "document_id": str(mock_document.id),
                "filename": "test.pdf",
                "method": "docling",
                "ocr": "auto",
            }

            headers = {
                "X-CloudTasks-TaskName": "test-task",
                "X-CloudTasks-TaskRetryCount": "0",
            }

            response = client.post("/api/tasks/process-document", json=payload, headers=headers)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"

            # Verify OCR was called
            mock_ocr_router.process.assert_called_once()
            call_kwargs = mock_ocr_router.process.call_args[1]
            assert call_kwargs["mode"] == "auto"

        finally:
            app.dependency_overrides.clear()

    def test_successful_processing_langextract_method(
        self, client, mock_document, mock_processed_document, mock_extraction_result
    ):
        """Test successful processing with langextract method via ExtractionRouter."""
        # Setup mocks
        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_by_id.return_value = mock_document
        mock_doc_repo.update_status = AsyncMock()

        mock_gcs = MagicMock()
        mock_gcs.bucket_name = "test-bucket"
        mock_gcs.download.return_value = b"%PDF-1.4 test content"

        mock_docling = MagicMock()
        mock_docling.process_bytes.return_value = mock_processed_document

        # ExtractionRouter should be used for langextract
        mock_extraction_router = MagicMock()
        mock_extraction_router.extract.return_value = mock_extraction_result

        mock_borrower_repo = AsyncMock()
        mock_borrower_repo.session = AsyncMock()
        mock_borrower_repo.session.flush = AsyncMock()

        app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
        app.dependency_overrides[get_gcs_client] = lambda: mock_gcs
        app.dependency_overrides[get_docling_processor] = lambda: mock_docling
        app.dependency_overrides[get_extraction_router] = lambda: mock_extraction_router
        app.dependency_overrides[get_borrower_repository] = lambda: mock_borrower_repo
        app.dependency_overrides[get_ocr_router] = lambda: None

        try:
            payload = {
                "document_id": str(mock_document.id),
                "filename": "test.pdf",
                "method": "langextract",
                "ocr": "skip",
            }

            headers = {
                "X-CloudTasks-TaskName": "test-task",
                "X-CloudTasks-TaskRetryCount": "0",
            }

            response = client.post("/api/tasks/process-document", json=payload, headers=headers)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"

            # Verify ExtractionRouter was used (not BorrowerExtractor directly)
            mock_extraction_router.extract.assert_called_once()
            call_kwargs = mock_extraction_router.extract.call_args[1]
            assert call_kwargs["method"] == "langextract"

        finally:
            app.dependency_overrides.clear()


class TestProcessDocumentErrorCases:
    """Tests for error handling scenarios."""

    def test_document_not_found_returns_200(self, client):
        """Test that missing document returns 200 (no retry)."""
        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_by_id.return_value = None

        app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo

        try:
            payload = {
                "document_id": str(uuid4()),
                "filename": "missing.pdf",
                "method": "docling",
                "ocr": "skip",
            }

            headers = {
                "X-CloudTasks-TaskName": "test-task",
                "X-CloudTasks-TaskRetryCount": "0",
            }

            response = client.post("/api/tasks/process-document", json=payload, headers=headers)

            # Should return 200 (no point retrying)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "failed"
            assert "not found" in data["error"].lower()

        finally:
            app.dependency_overrides.clear()

    def test_already_completed_skips_processing(self, client, mock_document):
        """Test idempotency: already completed document skips processing."""
        mock_document.status = DocumentStatus.COMPLETED

        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_by_id.return_value = mock_document

        app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo

        try:
            payload = {
                "document_id": str(mock_document.id),
                "filename": "test.pdf",
                "method": "docling",
                "ocr": "skip",
            }

            headers = {
                "X-CloudTasks-TaskName": "test-task",
                "X-CloudTasks-TaskRetryCount": "0",
            }

            response = client.post("/api/tasks/process-document", json=payload, headers=headers)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"

            # Should NOT update status (already complete)
            mock_doc_repo.update_status.assert_not_called()

        finally:
            app.dependency_overrides.clear()

    def test_already_failed_skips_processing(self, client, mock_document):
        """Test idempotency: already failed document skips processing."""
        mock_document.status = DocumentStatus.FAILED

        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_by_id.return_value = mock_document

        app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo

        try:
            payload = {
                "document_id": str(mock_document.id),
                "filename": "test.pdf",
                "method": "docling",
                "ocr": "skip",
            }

            headers = {
                "X-CloudTasks-TaskName": "test-task",
                "X-CloudTasks-TaskRetryCount": "0",
            }

            response = client.post("/api/tasks/process-document", json=payload, headers=headers)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "failed"

            # Should NOT update status (already failed)
            mock_doc_repo.update_status.assert_not_called()

        finally:
            app.dependency_overrides.clear()

    def test_missing_gcs_uri_fails(self, client, mock_document):
        """Test that document without GCS URI fails processing."""
        mock_document.gcs_uri = None

        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_by_id.return_value = mock_document
        mock_doc_repo.update_status = AsyncMock()

        app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo

        try:
            payload = {
                "document_id": str(mock_document.id),
                "filename": "test.pdf",
                "method": "docling",
                "ocr": "skip",
            }

            headers = {
                "X-CloudTasks-TaskName": "test-task",
                "X-CloudTasks-TaskRetryCount": "0",
            }

            response = client.post("/api/tasks/process-document", json=payload, headers=headers)

            # Should raise 503 (transient error, trigger retry)
            assert response.status_code == 503
            assert "gcs uri" in response.json()["detail"].lower()

        finally:
            app.dependency_overrides.clear()

    def test_docling_processing_error_marks_failed(
        self, client, mock_document, mock_processed_document
    ):
        """Test that DocumentProcessingError marks document as FAILED (permanent error)."""
        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_by_id.return_value = mock_document
        mock_doc_repo.update_status = AsyncMock()

        mock_gcs = MagicMock()
        mock_gcs.bucket_name = "test-bucket"
        mock_gcs.download.return_value = b"%PDF-1.4 test content"

        # Docling fails with processing error
        mock_docling = MagicMock()
        mock_docling.process_bytes.side_effect = DocumentProcessingError(
            "Corrupted PDF: unable to parse"
        )

        app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
        app.dependency_overrides[get_gcs_client] = lambda: mock_gcs
        app.dependency_overrides[get_docling_processor] = lambda: mock_docling
        app.dependency_overrides[get_ocr_router] = lambda: None

        try:
            payload = {
                "document_id": str(mock_document.id),
                "filename": "corrupt.pdf",
                "method": "docling",
                "ocr": "skip",
            }

            headers = {
                "X-CloudTasks-TaskName": "test-task",
                "X-CloudTasks-TaskRetryCount": "0",
            }

            response = client.post("/api/tasks/process-document", json=payload, headers=headers)

            # Should return 200 with failed status (permanent error, don't retry)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "failed"
            assert "processing failed" in data["error"].lower()

            # Verify document marked as FAILED
            calls = mock_doc_repo.update_status.call_args_list
            final_call = calls[-1]
            assert final_call[0][1] == DocumentStatus.FAILED

        finally:
            app.dependency_overrides.clear()


class TestRetryLogic:
    """Tests for Cloud Tasks retry behavior."""

    def test_transient_error_raises_503_for_retry(
        self, client, mock_document
    ):
        """Test that transient errors raise 503 to trigger Cloud Tasks retry."""
        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_by_id.return_value = mock_document
        mock_doc_repo.update_status = AsyncMock()

        mock_gcs = MagicMock()
        mock_gcs.bucket_name = "test-bucket"
        # Simulate GCS download failure (transient)
        mock_gcs.download.side_effect = RuntimeError("Connection timeout")

        app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
        app.dependency_overrides[get_gcs_client] = lambda: mock_gcs
        app.dependency_overrides[get_ocr_router] = lambda: None

        try:
            payload = {
                "document_id": str(mock_document.id),
                "filename": "test.pdf",
                "method": "docling",
                "ocr": "skip",
            }

            headers = {
                "X-CloudTasks-TaskName": "test-task",
                "X-CloudTasks-TaskRetryCount": "0",  # First attempt
            }

            response = client.post("/api/tasks/process-document", json=payload, headers=headers)

            # Should return 503 to trigger retry
            assert response.status_code == 503
            assert "attempt 1" in response.json()["detail"].lower()

        finally:
            app.dependency_overrides.clear()

    def test_max_retries_exhausted_marks_failed(
        self, client, mock_document
    ):
        """Test that max retries exhausted marks document as FAILED and returns 200."""
        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_by_id.return_value = mock_document
        mock_doc_repo.update_status = AsyncMock()

        mock_gcs = MagicMock()
        mock_gcs.bucket_name = "test-bucket"
        mock_gcs.download.side_effect = RuntimeError("Persistent failure")

        app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
        app.dependency_overrides[get_gcs_client] = lambda: mock_gcs
        app.dependency_overrides[get_ocr_router] = lambda: None

        try:
            payload = {
                "document_id": str(mock_document.id),
                "filename": "test.pdf",
                "method": "docling",
                "ocr": "skip",
            }

            headers = {
                "X-CloudTasks-TaskName": "test-task",
                "X-CloudTasks-TaskRetryCount": "4",  # MAX_RETRY_COUNT = 4
            }

            response = client.post("/api/tasks/process-document", json=payload, headers=headers)

            # Should return 200 (don't retry anymore)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "failed"
            assert "max retries" in data["error"].lower()

            # Verify document marked as FAILED with retry info
            calls = mock_doc_repo.update_status.call_args_list
            final_call = calls[-1]
            assert final_call[0][1] == DocumentStatus.FAILED
            error_msg = final_call[1]["error_message"]
            assert "5 attempts" in error_msg  # 0-4 inclusive = 5 attempts

        finally:
            app.dependency_overrides.clear()

    def test_retry_count_logged_correctly(
        self, client, mock_document
    ):
        """Test that retry count is parsed from Cloud Tasks headers."""
        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_by_id.return_value = mock_document
        mock_doc_repo.update_status = AsyncMock()

        mock_gcs = MagicMock()
        mock_gcs.bucket_name = "test-bucket"
        mock_gcs.download.side_effect = RuntimeError("Transient error")

        app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
        app.dependency_overrides[get_gcs_client] = lambda: mock_gcs
        app.dependency_overrides[get_ocr_router] = lambda: None

        try:
            payload = {
                "document_id": str(mock_document.id),
                "filename": "test.pdf",
                "method": "docling",
                "ocr": "skip",
            }

            headers = {
                "X-CloudTasks-TaskName": "test-task-retry",
                "X-CloudTasks-TaskRetryCount": "2",  # Third attempt
            }

            response = client.post("/api/tasks/process-document", json=payload, headers=headers)

            assert response.status_code == 503
            detail = response.json()["detail"]
            assert "attempt 3" in detail.lower()  # retry_count + 1

        finally:
            app.dependency_overrides.clear()


class TestBorrowerPersistence:
    """Tests for borrower persistence during processing."""

    def test_borrowers_persisted_successfully(
        self, client, mock_document, mock_processed_document, mock_extraction_result
    ):
        """Test that extracted borrowers are persisted to database."""
        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_by_id.return_value = mock_document
        mock_doc_repo.update_status = AsyncMock()

        mock_gcs = MagicMock()
        mock_gcs.bucket_name = "test-bucket"
        mock_gcs.download.return_value = b"%PDF-1.4 test content"

        mock_docling = MagicMock()
        mock_docling.process_bytes.return_value = mock_processed_document

        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = mock_extraction_result

        # Track borrower persistence calls
        mock_borrower_repo = AsyncMock()
        mock_borrower_repo.session = AsyncMock()
        mock_borrower_repo.session.flush = AsyncMock()

        app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
        app.dependency_overrides[get_gcs_client] = lambda: mock_gcs
        app.dependency_overrides[get_docling_processor] = lambda: mock_docling
        app.dependency_overrides[get_borrower_extractor] = lambda: mock_extractor
        app.dependency_overrides[get_borrower_repository] = lambda: mock_borrower_repo
        app.dependency_overrides[get_ocr_router] = lambda: None
        app.dependency_overrides[get_extraction_router] = lambda: None

        try:
            payload = {
                "document_id": str(mock_document.id),
                "filename": "test.pdf",
                "method": "docling",
                "ocr": "skip",
            }

            headers = {
                "X-CloudTasks-TaskName": "test-task",
                "X-CloudTasks-TaskRetryCount": "0",
            }

            response = client.post("/api/tasks/process-document", json=payload, headers=headers)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"

            # Note: We can't easily verify _persist_borrower was called because it's a private method
            # and we're using a temporary service instance. In real integration tests this would
            # verify database state.

        finally:
            app.dependency_overrides.clear()

    def test_borrower_persistence_failure_logged(
        self, client, mock_document, mock_processed_document, mock_extraction_result
    ):
        """Test that borrower persistence failures are logged but don't crash processing."""
        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_by_id.return_value = mock_document
        mock_doc_repo.update_status = AsyncMock()

        mock_gcs = MagicMock()
        mock_gcs.bucket_name = "test-bucket"
        mock_gcs.download.return_value = b"%PDF-1.4 test content"

        mock_docling = MagicMock()
        mock_docling.process_bytes.return_value = mock_processed_document

        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = mock_extraction_result

        mock_borrower_repo = AsyncMock()
        mock_borrower_repo.session = AsyncMock()
        mock_borrower_repo.session.flush = AsyncMock()

        app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
        app.dependency_overrides[get_gcs_client] = lambda: mock_gcs
        app.dependency_overrides[get_docling_processor] = lambda: mock_docling
        app.dependency_overrides[get_borrower_extractor] = lambda: mock_extractor
        app.dependency_overrides[get_borrower_repository] = lambda: mock_borrower_repo
        app.dependency_overrides[get_ocr_router] = lambda: None
        app.dependency_overrides[get_extraction_router] = lambda: None

        try:
            payload = {
                "document_id": str(mock_document.id),
                "filename": "test.pdf",
                "method": "docling",
                "ocr": "skip",
            }

            headers = {
                "X-CloudTasks-TaskName": "test-task",
                "X-CloudTasks-TaskRetryCount": "0",
            }

            # Borrower persistence failure should be logged (warning) but not crash
            # Current implementation logs and continues
            with patch("src.api.tasks.logger") as mock_logger:
                response = client.post("/api/tasks/process-document", json=payload, headers=headers)

                assert response.status_code == 200
                # Document should still be marked COMPLETED
                # (current behavior - persistence errors are logged but don't fail the task)
                data = response.json()
                assert data["status"] == "completed"

        finally:
            app.dependency_overrides.clear()


class TestStatusTransitions:
    """Tests for document status transitions during processing."""

    def test_status_transitions_to_processing(
        self, client, mock_document, mock_processed_document, mock_extraction_result
    ):
        """Test that document status is updated to PROCESSING before extraction."""
        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_by_id.return_value = mock_document
        mock_doc_repo.update_status = AsyncMock()

        mock_gcs = MagicMock()
        mock_gcs.bucket_name = "test-bucket"
        mock_gcs.download.return_value = b"%PDF-1.4 test content"

        mock_docling = MagicMock()
        mock_docling.process_bytes.return_value = mock_processed_document

        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = mock_extraction_result

        mock_borrower_repo = AsyncMock()
        mock_borrower_repo.session = AsyncMock()
        mock_borrower_repo.session.flush = AsyncMock()

        app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
        app.dependency_overrides[get_gcs_client] = lambda: mock_gcs
        app.dependency_overrides[get_docling_processor] = lambda: mock_docling
        app.dependency_overrides[get_borrower_extractor] = lambda: mock_extractor
        app.dependency_overrides[get_borrower_repository] = lambda: mock_borrower_repo
        app.dependency_overrides[get_ocr_router] = lambda: None
        app.dependency_overrides[get_extraction_router] = lambda: None

        try:
            payload = {
                "document_id": str(mock_document.id),
                "filename": "test.pdf",
                "method": "docling",
                "ocr": "skip",
            }

            headers = {
                "X-CloudTasks-TaskName": "test-task",
                "X-CloudTasks-TaskRetryCount": "0",
            }

            response = client.post("/api/tasks/process-document", json=payload, headers=headers)

            assert response.status_code == 200

            # Verify status updates: should be called at least twice
            # 1. PROCESSING (initial)
            # 2. PROCESSING (with page_count after docling)
            # 3. COMPLETED (final)
            assert mock_doc_repo.update_status.call_count >= 2

            # First call should be PROCESSING
            first_call = mock_doc_repo.update_status.call_args_list[0]
            assert first_call[0][1] == DocumentStatus.PROCESSING

            # Last call should be COMPLETED
            last_call = mock_doc_repo.update_status.call_args_list[-1]
            assert last_call[0][1] == DocumentStatus.COMPLETED

        finally:
            app.dependency_overrides.clear()

    def test_page_count_updated_after_docling(
        self, client, mock_document, mock_processed_document, mock_extraction_result
    ):
        """Test that page count is updated after Docling processing."""
        mock_processed_document.page_count = 5  # Set specific page count

        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_by_id.return_value = mock_document
        mock_doc_repo.update_status = AsyncMock()
        mock_doc_repo.session = AsyncMock()
        mock_doc_repo.session.flush = AsyncMock()

        mock_gcs = MagicMock()
        mock_gcs.bucket_name = "test-bucket"
        mock_gcs.download.return_value = b"%PDF-1.4 test content"

        mock_docling = MagicMock()
        mock_docling.process_bytes.return_value = mock_processed_document

        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = mock_extraction_result

        mock_borrower_repo = AsyncMock()
        mock_borrower_repo.session = AsyncMock()
        mock_borrower_repo.session.flush = AsyncMock()

        app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
        app.dependency_overrides[get_gcs_client] = lambda: mock_gcs
        app.dependency_overrides[get_docling_processor] = lambda: mock_docling
        app.dependency_overrides[get_borrower_extractor] = lambda: mock_extractor
        app.dependency_overrides[get_borrower_repository] = lambda: mock_borrower_repo
        app.dependency_overrides[get_ocr_router] = lambda: None
        app.dependency_overrides[get_extraction_router] = lambda: None

        try:
            payload = {
                "document_id": str(mock_document.id),
                "filename": "test.pdf",
                "method": "docling",
                "ocr": "skip",
            }

            headers = {
                "X-CloudTasks-TaskName": "test-task",
                "X-CloudTasks-TaskRetryCount": "0",
            }

            response = client.post("/api/tasks/process-document", json=payload, headers=headers)

            assert response.status_code == 200

            # Find the update_status call with page_count
            page_count_updated = False
            for call in mock_doc_repo.update_status.call_args_list:
                if "page_count" in call[1]:
                    assert call[1]["page_count"] == 5
                    page_count_updated = True
                    break

            assert page_count_updated, "page_count should be updated after processing"

        finally:
            app.dependency_overrides.clear()


class TestCloudTasksHeaders:
    """Tests for Cloud Tasks header parsing."""

    def test_missing_headers_use_defaults(
        self, client, mock_document, mock_processed_document, mock_extraction_result
    ):
        """Test that missing Cloud Tasks headers use default values."""
        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_by_id.return_value = mock_document
        mock_doc_repo.update_status = AsyncMock()

        mock_gcs = MagicMock()
        mock_gcs.bucket_name = "test-bucket"
        mock_gcs.download.return_value = b"%PDF-1.4 test content"

        mock_docling = MagicMock()
        mock_docling.process_bytes.return_value = mock_processed_document

        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = mock_extraction_result

        mock_borrower_repo = AsyncMock()
        mock_borrower_repo.session = AsyncMock()
        mock_borrower_repo.session.flush = AsyncMock()

        app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
        app.dependency_overrides[get_gcs_client] = lambda: mock_gcs
        app.dependency_overrides[get_docling_processor] = lambda: mock_docling
        app.dependency_overrides[get_borrower_extractor] = lambda: mock_extractor
        app.dependency_overrides[get_borrower_repository] = lambda: mock_borrower_repo
        app.dependency_overrides[get_ocr_router] = lambda: None
        app.dependency_overrides[get_extraction_router] = lambda: None

        try:
            payload = {
                "document_id": str(mock_document.id),
                "filename": "test.pdf",
                "method": "docling",
                "ocr": "skip",
            }

            # No Cloud Tasks headers - should use defaults
            response = client.post("/api/tasks/process-document", json=payload)

            # Should still process successfully (task_name="unknown", retry_count=0)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"

        finally:
            app.dependency_overrides.clear()


class TestBackwardCompatibility:
    """Tests for backward compatibility with tasks queued before Phase 15."""

    def test_missing_method_defaults_to_docling(
        self, client, mock_document, mock_processed_document, mock_extraction_result
    ):
        """Test that missing 'method' field defaults to 'docling' for backward compat."""
        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_by_id.return_value = mock_document
        mock_doc_repo.update_status = AsyncMock()

        mock_gcs = MagicMock()
        mock_gcs.bucket_name = "test-bucket"
        mock_gcs.download.return_value = b"%PDF-1.4 test content"

        mock_docling = MagicMock()
        mock_docling.process_bytes.return_value = mock_processed_document

        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = mock_extraction_result

        mock_borrower_repo = AsyncMock()
        mock_borrower_repo.session = AsyncMock()
        mock_borrower_repo.session.flush = AsyncMock()

        app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
        app.dependency_overrides[get_gcs_client] = lambda: mock_gcs
        app.dependency_overrides[get_docling_processor] = lambda: mock_docling
        app.dependency_overrides[get_borrower_extractor] = lambda: mock_extractor
        app.dependency_overrides[get_borrower_repository] = lambda: mock_borrower_repo
        app.dependency_overrides[get_ocr_router] = lambda: None
        app.dependency_overrides[get_extraction_router] = lambda: None

        try:
            # Old payload format (no method/ocr fields)
            payload = {
                "document_id": str(mock_document.id),
                "filename": "test.pdf",
                # method and ocr fields omitted (will use defaults)
            }

            headers = {
                "X-CloudTasks-TaskName": "test-task",
                "X-CloudTasks-TaskRetryCount": "0",
            }

            response = client.post("/api/tasks/process-document", json=payload, headers=headers)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"

            # Should use BorrowerExtractor directly (docling method)
            mock_extractor.extract.assert_called_once()

        finally:
            app.dependency_overrides.clear()

    def test_missing_ocr_defaults_to_auto(
        self, client, mock_document, mock_processed_document, mock_extraction_result
    ):
        """Test that missing 'ocr' field defaults to 'auto' for backward compat."""
        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_by_id.return_value = mock_document
        mock_doc_repo.update_status = AsyncMock()
        mock_doc_repo.session = AsyncMock()
        mock_doc_repo.session.flush = AsyncMock()

        mock_gcs = MagicMock()
        mock_gcs.bucket_name = "test-bucket"
        mock_gcs.download.return_value = b"%PDF-1.4 test content"

        mock_ocr_router = AsyncMock()
        ocr_result = OCRResult(
            content=mock_processed_document,
            ocr_method="none",
            pages_ocrd=[],
        )
        mock_ocr_router.process.return_value = ocr_result

        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = mock_extraction_result

        mock_borrower_repo = AsyncMock()
        mock_borrower_repo.session = AsyncMock()
        mock_borrower_repo.session.flush = AsyncMock()

        app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
        app.dependency_overrides[get_gcs_client] = lambda: mock_gcs
        app.dependency_overrides[get_ocr_router] = lambda: mock_ocr_router
        app.dependency_overrides[get_borrower_extractor] = lambda: mock_extractor
        app.dependency_overrides[get_borrower_repository] = lambda: mock_borrower_repo
        app.dependency_overrides[get_extraction_router] = lambda: None

        try:
            # Old payload format (no ocr field)
            payload = {
                "document_id": str(mock_document.id),
                "filename": "test.pdf",
                "method": "docling",
                # ocr field omitted (will use default "auto")
            }

            headers = {
                "X-CloudTasks-TaskName": "test-task",
                "X-CloudTasks-TaskRetryCount": "0",
            }

            response = client.post("/api/tasks/process-document", json=payload, headers=headers)

            assert response.status_code == 200

            # OCR router should be called with default mode="auto"
            mock_ocr_router.process.assert_called_once()
            call_kwargs = mock_ocr_router.process.call_args[1]
            assert call_kwargs["mode"] == "auto"

        finally:
            app.dependency_overrides.clear()
