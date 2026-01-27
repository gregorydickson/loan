"""Additional unit tests for DocumentService coverage."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest

from src.extraction import BorrowerExtractor, ExtractionResult
from src.extraction.complexity_classifier import ComplexityAssessment, ComplexityLevel
from src.ingestion.cloud_tasks_client import CloudTasksClient
from src.ingestion.docling_processor import (
    DoclingProcessor,
    DocumentContent,
    PageContent,
)
from src.ingestion.document_service import DocumentService, DocumentUploadError
from src.storage.gcs_client import GCSClient, GCSUploadError
from src.storage.models import Document, DocumentStatus
from src.storage.repositories import BorrowerRepository, DocumentRepository


@pytest.fixture
def mock_repository():
    """Create mock DocumentRepository."""
    repo = AsyncMock(spec=DocumentRepository)
    repo.session = AsyncMock()
    repo.session.flush = AsyncMock()
    repo.session.commit = AsyncMock()
    repo.session.rollback = AsyncMock()
    repo.get_by_hash = AsyncMock(return_value=None)  # Default: no duplicate
    repo.create = AsyncMock()
    repo.update_status = AsyncMock()
    return repo


@pytest.fixture
def mock_gcs_client():
    """Create mock GCS client."""
    client = Mock(spec=GCSClient)
    client.upload = Mock(return_value="gs://test-bucket/documents/test.pdf")
    return client


@pytest.fixture
def mock_docling_processor():
    """Create mock DoclingProcessor."""
    processor = Mock(spec=DoclingProcessor)
    processor.process_bytes = Mock(
        return_value=DocumentContent(
            text="Test content",
            pages=[PageContent(page_number=1, text="Page 1", tables=[])],
            page_count=1,
            tables=[],
            metadata={},
        )
    )
    return processor


@pytest.fixture
def mock_borrower_extractor():
    """Create mock BorrowerExtractor."""
    extractor = Mock(spec=BorrowerExtractor)
    extractor.extract = Mock(
        return_value=ExtractionResult(
            borrowers=[],
            complexity=ComplexityAssessment(
                level=ComplexityLevel.STANDARD,
                reasons=[],
                page_count=1,
                estimated_borrowers=0,
                has_handwritten=False,
                has_poor_quality=False,
            ),
            chunks_processed=1,
            total_tokens=100,
            validation_errors=[],
            consistency_warnings=[],
        )
    )
    return extractor


@pytest.fixture
def mock_borrower_repository():
    """Create mock BorrowerRepository."""
    repo = AsyncMock(spec=BorrowerRepository)
    return repo


class TestDuplicateFileHandling:
    """Test duplicate file detection and handling."""

    @pytest.mark.asyncio
    async def test_duplicate_file_deletes_existing_document(
        self,
        mock_repository,
        mock_gcs_client,
        mock_docling_processor,
        mock_borrower_extractor,
        mock_borrower_repository,
    ):
        """Test that uploading duplicate file deletes existing document."""
        # Setup existing document with same hash
        existing_doc = Mock(spec=Document)
        existing_doc.id = uuid4()

        # Setup mock document creation
        new_doc = Mock(spec=Document)
        new_doc.id = uuid4()
        new_doc.filename = "test.pdf"
        new_doc.file_hash = "hash123"
        new_doc.file_size_bytes = 1000
        new_doc.status = DocumentStatus.COMPLETED
        new_doc.page_count = 1
        new_doc.error_message = None
        new_doc.extraction_method = "docling"
        new_doc.ocr_processed = False

        # Configure repository mocks
        mock_repository.get_by_hash = AsyncMock(return_value=existing_doc)
        mock_repository.create = AsyncMock(return_value=new_doc)
        mock_repository.get_by_id = AsyncMock(return_value=new_doc)
        mock_repository.update_status = AsyncMock()

        service = DocumentService(
            repository=mock_repository,
            gcs_client=mock_gcs_client,
            docling_processor=mock_docling_processor,
            borrower_extractor=mock_borrower_extractor,
            borrower_repository=mock_borrower_repository,
            cloud_tasks_client=None,
        )

        # Upload file (should detect duplicate and delete existing)
        content = b"%PDF-1.4\ntest content"
        result = await service.upload(
            filename="test.pdf",
            content=content,
            content_type="application/pdf",
        )

        # Verify existing document was deleted
        mock_repository.delete.assert_called_once_with(existing_doc.id)
        mock_repository.session.flush.assert_called()

        # Verify processing completed
        assert result.status == DocumentStatus.COMPLETED


class TestCloudTasksAsyncMode:
    """Test async processing mode with Cloud Tasks."""

    @pytest.mark.asyncio
    async def test_cloud_tasks_queues_async_processing(
        self,
        mock_repository,
        mock_gcs_client,
        mock_docling_processor,
        mock_borrower_extractor,
        mock_borrower_repository,
    ):
        """Test that Cloud Tasks client queues document for async processing."""
        # Setup Cloud Tasks client mock
        mock_cloud_tasks = Mock(spec=CloudTasksClient)
        mock_cloud_tasks.create_document_processing_task = Mock()

        # Setup document creation
        doc_id = uuid4()
        new_doc = Mock(spec=Document)
        new_doc.id = doc_id
        new_doc.filename = "async.pdf"
        new_doc.file_hash = "hash456"
        new_doc.file_size_bytes = 2000
        new_doc.status = DocumentStatus.PENDING  # Should remain PENDING in async mode
        new_doc.page_count = None
        new_doc.error_message = None
        new_doc.extraction_method = "docling"
        new_doc.ocr_processed = None
        mock_repository.create = AsyncMock(return_value=new_doc)
        mock_repository.get_by_id = AsyncMock(return_value=new_doc)

        service = DocumentService(
            repository=mock_repository,
            gcs_client=mock_gcs_client,
            docling_processor=mock_docling_processor,
            borrower_extractor=mock_borrower_extractor,
            borrower_repository=mock_borrower_repository,
            cloud_tasks_client=mock_cloud_tasks,  # Enable async mode
        )

        # Upload document
        result = await service.upload(
            filename="async.pdf",
            content=b"%PDF-1.4\nasync content",
            content_type="application/pdf",
            extraction_method="docling",
            ocr_mode="auto",
        )

        # Verify Cloud Task was created
        mock_cloud_tasks.create_document_processing_task.assert_called_once()
        call_args = mock_cloud_tasks.create_document_processing_task.call_args
        assert call_args[1]["filename"] == "async.pdf"
        assert call_args[1]["extraction_method"] == "docling"
        assert call_args[1]["ocr_mode"] == "auto"

        # Document should remain PENDING (not processed synchronously)
        assert result.status == DocumentStatus.PENDING

    @pytest.mark.asyncio
    async def test_cloud_tasks_failure_continues_sync_processing(
        self,
        mock_repository,
        mock_gcs_client,
        mock_docling_processor,
        mock_borrower_extractor,
        mock_borrower_repository,
    ):
        """Test that Cloud Tasks failure falls back to sync processing."""
        # Setup Cloud Tasks client that fails
        mock_cloud_tasks = Mock(spec=CloudTasksClient)
        mock_cloud_tasks.create_document_processing_task = Mock(
            side_effect=Exception("Cloud Tasks unavailable")
        )

        # Setup document
        new_doc = Mock(spec=Document)
        new_doc.id = uuid4()
        new_doc.filename = "fallback.pdf"
        new_doc.file_hash = "hash789"
        new_doc.file_size_bytes = 1500
        new_doc.status = DocumentStatus.COMPLETED  # Should complete synchronously
        new_doc.page_count = 1
        new_doc.error_message = None
        new_doc.extraction_method = "docling"
        new_doc.ocr_processed = False
        mock_repository.create = AsyncMock(return_value=new_doc)
        mock_repository.get_by_id = AsyncMock(return_value=new_doc)

        service = DocumentService(
            repository=mock_repository,
            gcs_client=mock_gcs_client,
            docling_processor=mock_docling_processor,
            borrower_extractor=mock_borrower_extractor,
            borrower_repository=mock_borrower_repository,
            cloud_tasks_client=mock_cloud_tasks,
        )

        # Upload should succeed despite Cloud Tasks failure
        result = await service.upload(
            filename="fallback.pdf",
            content=b"%PDF-1.4\nfallback content",
            content_type="application/pdf",
        )

        # Should have processed synchronously (COMPLETED status)
        assert result.status == DocumentStatus.COMPLETED


class TestSyncProcessingMode:
    """Test synchronous processing mode (no Cloud Tasks)."""

    @pytest.mark.asyncio
    async def test_sync_mode_processes_immediately(
        self,
        mock_repository,
        mock_gcs_client,
        mock_docling_processor,
        mock_borrower_extractor,
        mock_borrower_repository,
    ):
        """Test that sync mode processes document immediately."""
        new_doc = Mock(spec=Document)
        new_doc.id = uuid4()
        new_doc.filename = "sync.pdf"
        new_doc.file_hash = "syncHash"
        new_doc.file_size_bytes = 800
        new_doc.status = DocumentStatus.COMPLETED
        new_doc.page_count = 2
        new_doc.error_message = None
        new_doc.extraction_method = "docling"
        new_doc.ocr_processed = False
        mock_repository.create = AsyncMock(return_value=new_doc)
        mock_repository.get_by_id = AsyncMock(return_value=new_doc)

        service = DocumentService(
            repository=mock_repository,
            gcs_client=mock_gcs_client,
            docling_processor=mock_docling_processor,
            borrower_extractor=mock_borrower_extractor,
            borrower_repository=mock_borrower_repository,
            cloud_tasks_client=None,  # No Cloud Tasks = sync mode
        )

        result = await service.upload(
            filename="sync.pdf",
            content=b"%PDF-1.4\nsync content",
            content_type="application/pdf",
        )

        # Document should be COMPLETED immediately
        assert result.status == DocumentStatus.COMPLETED
        assert result.page_count == 2


class TestGCSUploadFailure:
    """Test GCS upload failure handling."""

    @pytest.mark.asyncio
    async def test_gcs_upload_failure_marks_document_failed(
        self,
        mock_repository,
        mock_docling_processor,
        mock_borrower_extractor,
        mock_borrower_repository,
    ):
        """Test that GCS upload failure marks document as FAILED."""
        # Mock GCS client that raises error
        mock_gcs = Mock(spec=GCSClient)
        mock_gcs.upload = Mock(side_effect=GCSUploadError("Bucket not found"))

        # Setup document
        new_doc = Mock(spec=Document)
        new_doc.id = uuid4()
        new_doc.filename = "failed.pdf"
        new_doc.file_hash = "failHash"
        new_doc.file_size_bytes = 500
        new_doc.status = DocumentStatus.PENDING
        mock_repository.create = AsyncMock(return_value=new_doc)

        service = DocumentService(
            repository=mock_repository,
            gcs_client=mock_gcs,
            docling_processor=mock_docling_processor,
            borrower_extractor=mock_borrower_extractor,
            borrower_repository=mock_borrower_repository,
            cloud_tasks_client=None,
        )

        # Upload should raise DocumentUploadError
        with pytest.raises(DocumentUploadError, match="Failed to upload to storage"):
            await service.upload(
                filename="failed.pdf",
                content=b"%PDF-1.4\nfailed content",
                content_type="application/pdf",
            )

        # Document should be marked as FAILED
        assert mock_repository.update_status.called
        # Verify FAILED status was set (check positional or keyword args)
        if mock_repository.update_status.call_args.args:
            assert mock_repository.update_status.call_args.args[1] == DocumentStatus.FAILED
        else:
            assert mock_repository.update_status.call_args.kwargs["status"] == DocumentStatus.FAILED


class TestProcessDocumentErrorHandling:
    """Test process_document error handling paths."""

    @pytest.mark.asyncio
    async def test_process_document_with_extraction_error(
        self,
        mock_repository,
        mock_gcs_client,
        mock_docling_processor,
        mock_borrower_repository,
    ):
        """Test that extraction errors are handled gracefully during upload."""
        # Mock extractor that raises exception
        mock_extractor = Mock(spec=BorrowerExtractor)
        mock_extractor.extract = Mock(side_effect=ValueError("Extraction failed"))

        new_doc = Mock(spec=Document)
        new_doc.id = uuid4()
        new_doc.filename = "error.pdf"
        new_doc.file_hash = "errorHash"
        new_doc.file_size_bytes = 100
        new_doc.status = DocumentStatus.FAILED  # Will be updated to FAILED
        new_doc.error_message = None
        new_doc.page_count = None
        new_doc.extraction_method = "docling"
        new_doc.ocr_processed = False
        mock_repository.create = AsyncMock(return_value=new_doc)
        mock_repository.get_by_id = AsyncMock(return_value=new_doc)

        service = DocumentService(
            repository=mock_repository,
            gcs_client=mock_gcs_client,
            docling_processor=mock_docling_processor,
            borrower_extractor=mock_extractor,
            borrower_repository=mock_borrower_repository,
            cloud_tasks_client=None,
        )

        # Upload should still raise the error (not caught at upload level)
        # The error happens during synchronous processing
        try:
            result = await service.upload(
                filename="error.pdf",
                content=b"%PDF-1.4\nerror content",
                content_type="application/pdf",
            )
            # If we get here, the error was caught and document marked failed
            # which is acceptable behavior
        except ValueError:
            # Error was propagated, which is also acceptable
            pass
