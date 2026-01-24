"""Integration tests for async document processing with Cloud Tasks."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.api.dependencies import (
    get_borrower_extractor,
    get_cloud_tasks_client,
    get_docling_processor,
    get_gcs_client,
)
from src.main import app
from src.storage.database import get_db_session
from src.storage.models import Base


@pytest.fixture
def mock_cloud_tasks_client():
    """Mock CloudTasksClient for testing async flow."""
    mock_client = MagicMock()
    mock_task = MagicMock()
    mock_task.name = "projects/test/locations/us-central1/queues/doc-processing/tasks/123"
    mock_client.create_document_processing_task.return_value = mock_task
    return mock_client


@pytest.fixture
async def client_with_async_upload(
    async_engine,
    mock_gcs_client,
    mock_docling_processor,
    mock_borrower_extractor,
    mock_cloud_tasks_client,
):
    """Test client configured for async upload testing with Cloud Tasks."""
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

    def override_get_gcs_client():
        return mock_gcs_client

    def override_get_docling_processor():
        return mock_docling_processor

    def override_get_borrower_extractor():
        return mock_borrower_extractor

    def override_cloud_tasks_client():
        return mock_cloud_tasks_client

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_gcs_client] = override_get_gcs_client
    app.dependency_overrides[get_docling_processor] = override_get_docling_processor
    app.dependency_overrides[get_borrower_extractor] = override_get_borrower_extractor
    app.dependency_overrides[get_cloud_tasks_client] = override_cloud_tasks_client

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as test_client:
        yield test_client, mock_cloud_tasks_client

    app.dependency_overrides.clear()


@pytest.fixture
async def client_with_failing_tasks(
    async_engine,
    mock_gcs_client,
    mock_docling_processor,
    mock_borrower_extractor,
):
    """Test client with Cloud Tasks that fails to queue."""
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

    def override_get_gcs_client():
        return mock_gcs_client

    def override_get_docling_processor():
        return mock_docling_processor

    def override_get_borrower_extractor():
        return mock_borrower_extractor

    def override_cloud_tasks_client():
        mock_client = MagicMock()
        mock_client.create_document_processing_task.side_effect = Exception(
            "Cloud Tasks unavailable"
        )
        return mock_client

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_gcs_client] = override_get_gcs_client
    app.dependency_overrides[get_docling_processor] = override_get_docling_processor
    app.dependency_overrides[get_borrower_extractor] = override_get_borrower_extractor
    app.dependency_overrides[get_cloud_tasks_client] = override_cloud_tasks_client

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.mark.integration
class TestAsyncUpload:
    """Tests for async document upload flow."""

    @pytest.mark.asyncio
    async def test_upload_with_cloud_tasks_returns_pending(
        self,
        client_with_async_upload,
    ):
        """Test that upload with Cloud Tasks configured returns PENDING status."""
        client, mock_tasks = client_with_async_upload

        # Create test file
        files = {"file": ("test.pdf", b"fake pdf content", "application/pdf")}

        response = await client.post("/api/documents/", files=files)

        assert response.status_code == 201
        data = response.json()

        # Should return PENDING since we're using Cloud Tasks
        assert data["status"] == "pending"
        assert "queued for processing" in data["message"].lower()

        # Verify task was created
        mock_tasks.create_document_processing_task.assert_called_once()
        call_kwargs = mock_tasks.create_document_processing_task.call_args.kwargs
        assert call_kwargs["filename"] == "test.pdf"

    @pytest.mark.asyncio
    async def test_upload_creates_document_record(
        self,
        client_with_async_upload,
    ):
        """Test that document record is created before task is queued."""
        client, mock_tasks = client_with_async_upload

        files = {"file": ("test.pdf", b"fake pdf content", "application/pdf")}

        response = await client.post("/api/documents/", files=files)

        assert response.status_code == 201
        document_id = response.json()["id"]

        # Document was created (we can verify it exists via the returned ID)
        assert document_id is not None

    @pytest.mark.asyncio
    async def test_async_upload_queues_with_document_id(
        self,
        client_with_async_upload,
    ):
        """Test that Cloud Task is queued with correct document_id."""
        client, mock_tasks = client_with_async_upload

        files = {"file": ("loan_doc.pdf", b"loan document content", "application/pdf")}

        response = await client.post("/api/documents/", files=files)

        assert response.status_code == 201
        document_id = response.json()["id"]

        # Verify task was created with correct document_id
        mock_tasks.create_document_processing_task.assert_called_once()
        call_kwargs = mock_tasks.create_document_processing_task.call_args.kwargs
        assert str(call_kwargs["document_id"]) == document_id
        assert call_kwargs["filename"] == "loan_doc.pdf"


@pytest.mark.integration
class TestTaskHandler:
    """Tests for Cloud Tasks handler endpoint."""

    @pytest.mark.asyncio
    async def test_process_document_endpoint_exists(self, client):
        """Test that process-document endpoint is registered."""
        # Just verify the endpoint exists (will return 422 without valid payload)
        response = await client.post(
            "/api/tasks/process-document",
            json={},
        )

        # Should be 422 (validation error) not 404
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_process_document_with_missing_document(
        self,
        client,
    ):
        """Test handler returns success for missing document (no retry)."""
        response = await client.post(
            "/api/tasks/process-document",
            json={
                "document_id": str(uuid4()),
                "filename": "test.pdf",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert "not found" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_process_document_validates_payload(self, client):
        """Test handler validates required fields."""
        # Missing document_id
        response = await client.post(
            "/api/tasks/process-document",
            json={"filename": "test.pdf"},
        )
        assert response.status_code == 422

        # Missing filename
        response = await client.post(
            "/api/tasks/process-document",
            json={"document_id": str(uuid4())},
        )
        assert response.status_code == 422


@pytest.mark.integration
class TestSyncFallback:
    """Tests for sync processing fallback (local development)."""

    @pytest.mark.asyncio
    async def test_upload_without_cloud_tasks_processes_sync(
        self,
        client_with_extraction,
    ):
        """Test that upload without Cloud Tasks config processes synchronously.

        The client_with_extraction fixture doesn't override cloud_tasks_client,
        so get_cloud_tasks_client returns None (simulating local dev mode).
        """
        files = {"file": ("test.pdf", b"fake pdf content", "application/pdf")}

        response = await client_with_extraction.post("/api/documents/", files=files)

        assert response.status_code == 201
        data = response.json()

        # Should return COMPLETED since sync processing runs
        assert data["status"] == "completed"
        assert data["page_count"] is not None

    @pytest.mark.asyncio
    async def test_sync_fallback_extracts_borrowers(
        self,
        client_with_extraction,
    ):
        """Test that sync fallback extracts and persists borrowers."""
        files = {"file": ("borrower_doc.pdf", b"fake pdf content", "application/pdf")}

        response = await client_with_extraction.post("/api/documents/", files=files)

        assert response.status_code == 201

        # Verify borrowers were extracted
        borrowers_response = await client_with_extraction.get("/api/borrowers/")
        assert borrowers_response.status_code == 200
        borrowers_data = borrowers_response.json()

        assert borrowers_data["total"] >= 1


@pytest.mark.integration
class TestTaskQueueingFailure:
    """Tests for task queueing failure handling."""

    @pytest.mark.asyncio
    async def test_task_queueing_failure_marks_document_failed(
        self,
        client_with_failing_tasks,
    ):
        """Test that task queueing failure marks document as FAILED."""
        files = {"file": ("test.pdf", b"fake pdf content", "application/pdf")}

        response = await client_with_failing_tasks.post("/api/documents/", files=files)

        assert response.status_code == 201
        data = response.json()

        # Document should be marked as FAILED
        assert data["status"] == "failed"
        assert "queue" in data["error_message"].lower()
