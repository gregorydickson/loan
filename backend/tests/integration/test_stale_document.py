"""TDD tests for stale document object issue in async task handler.

Critical Issue: tasks.py:172-180 modifies a stale document object after
update_status without refreshing from the database.
"""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.api.dependencies import (
    get_cloud_tasks_client,
    get_extraction_router,
    get_ocr_router,
)
from src.ingestion.docling_processor import DocumentContent, PageContent
from src.main import app
from src.storage.database import get_db_session
from src.storage.models import Document, DocumentStatus


@pytest.fixture
async def client_with_ocr_router(
    async_engine,
    mock_gcs_client,
    mock_docling_processor,
    mock_borrower_extractor_with_data,
    mock_extraction_router,
):
    """Test client with mock OCRRouter for stale document bug testing."""
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

    # Create mock OCRRouter that returns document with page_count
    mock_ocr_router = MagicMock()
    mock_result = MagicMock()
    mock_result.content = DocumentContent(
        text="Sample document text",
        page_count=5,  # Important: This should be preserved
        pages=[
            PageContent(page_number=1, text="Page 1"),
            PageContent(page_number=2, text="Page 2"),
            PageContent(page_number=3, text="Page 3"),
            PageContent(page_number=4, text="Page 4"),
            PageContent(page_number=5, text="Page 5"),
        ],
    )
    mock_result.ocr_method = "gpu"  # OCR was applied

    async def mock_process(*args, **kwargs):
        return mock_result

    mock_ocr_router.process = mock_process

    def override_get_ocr_router():
        return mock_ocr_router

    def override_cloud_tasks_client():
        return None  # Disable async queueing

    from src.api.dependencies import (
        get_borrower_extractor,
        get_docling_processor,
        get_gcs_client,
    )

    # Add bucket_name attribute to mock
    mock_gcs_client.bucket_name = "test-bucket"

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_gcs_client] = lambda: mock_gcs_client
    app.dependency_overrides[get_docling_processor] = lambda: mock_docling_processor
    app.dependency_overrides[get_borrower_extractor] = lambda: mock_borrower_extractor_with_data
    app.dependency_overrides[get_extraction_router] = lambda: mock_extraction_router
    app.dependency_overrides[get_ocr_router] = override_get_ocr_router
    app.dependency_overrides[get_cloud_tasks_client] = override_cloud_tasks_client

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.mark.integration
class TestStaleDocumentObject:
    """TDD tests for stale document object issue in task handler."""

    @pytest.mark.asyncio
    async def test_task_handler_preserves_page_count_when_setting_ocr_processed(
        self,
        client_with_ocr_router,
        async_engine,
    ):
        """Test that page_count is preserved when ocr_processed is set.

        This test exposes the stale document object bug where:
        1. update_status sets page_count=5 in the database
        2. Code modifies the stale document.ocr_processed = True
        3. flush() overwrites the page_count back to None (stale value)

        Expected: Both page_count=5 AND ocr_processed=True should be persisted.
        Current (buggy): page_count gets lost because document is stale.
        """
        # Step 1: Create a document record in PENDING status
        async with async_sessionmaker(async_engine, expire_on_commit=False)() as session:
            document = Document(
                id=uuid4(),
                filename="test.pdf",
                file_hash="abc123",
                file_type="pdf",
                file_size_bytes=1024,
                gcs_uri="gs://test-bucket/documents/test.pdf",
                status=DocumentStatus.PENDING,
                extraction_method="langextract",
            )
            session.add(document)
            await session.commit()
            document_id = document.id

        # Step 2: Call the task handler endpoint
        response = await client_with_ocr_router.post(
            "/api/tasks/process-document",
            json={
                "document_id": str(document_id),
                "filename": "test.pdf",
                "method": "langextract",
                "ocr": "auto",  # This will trigger OCR processing
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

        # Step 3: Verify BOTH page_count AND ocr_processed are correctly set
        async with async_sessionmaker(async_engine, expire_on_commit=False)() as session:
            result = await session.execute(
                select(Document).where(Document.id == document_id)
            )
            updated_doc = result.scalar_one()

            # CRITICAL ASSERTION: Both fields should be set
            # If page_count is None, the stale document bug is present
            assert updated_doc.page_count == 5, (
                f"Expected page_count=5 but got {updated_doc.page_count}. "
                f"This indicates the stale document object overwrote the page_count "
                f"when ocr_processed was flushed."
            )
            assert updated_doc.ocr_processed is True, (
                f"Expected ocr_processed=True but got {updated_doc.ocr_processed}"
            )
            assert updated_doc.status == DocumentStatus.COMPLETED
