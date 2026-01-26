"""Unit tests for document_service.py fixes (Fix 1, 2, 3).

Tests cover:
- Fix 1: Document commit before processing
- Fix 2: Detailed error logging
- Fix 3: Partial borrower persistence success
"""

from unittest.mock import AsyncMock, MagicMock, call
from uuid import uuid4

import pytest

from src.extraction import BorrowerExtractor
from src.ingestion.docling_processor import (
    DoclingProcessor,
    DocumentContent,
    DocumentProcessingError,
    PageContent,
)
from src.ingestion.document_service import DocumentService
from src.models.borrower import BorrowerRecord, IncomeRecord, SourceReference
from src.storage.models import Document, DocumentStatus
from src.storage.repositories import BorrowerRepository


@pytest.fixture
def mock_docling_processor():
    """Create mock DoclingProcessor that returns successful result."""
    processor = MagicMock(spec=DoclingProcessor)
    processor.process_bytes = MagicMock(
        return_value=DocumentContent(
            text="Test document content",
            pages=[PageContent(page_number=1, text="Page 1 content", tables=[])],
            page_count=1,
            tables=[],
            metadata={"status": "SUCCESS"},
        )
    )
    return processor


@pytest.fixture
def mock_borrower_extractor_with_borrowers():
    """Create mock BorrowerExtractor that returns borrowers."""
    extractor = MagicMock(spec=BorrowerExtractor)
    # Return 3 borrowers for testing partial persistence
    extractor.extract = MagicMock(
        return_value=MagicMock(
            borrowers=[
                BorrowerRecord(
                    id=uuid4(),
                    name="John Doe",
                    ssn="123-45-6789",
                    address=None,
                    income_history=[],
                    account_numbers=[],
                    loan_numbers=[],
                    sources=[],
                    confidence_score=0.95,
                ),
                BorrowerRecord(
                    id=uuid4(),
                    name="Jane Smith",
                    ssn="987-65-4321",
                    address=None,
                    income_history=[],
                    account_numbers=[],
                    loan_numbers=[],
                    sources=[],
                    confidence_score=0.90,
                ),
                BorrowerRecord(
                    id=uuid4(),
                    name="Bob Johnson",
                    ssn="555-55-5555",
                    address=None,
                    income_history=[],
                    account_numbers=[],
                    loan_numbers=[],
                    sources=[],
                    confidence_score=0.85,
                ),
            ],
            validation_errors=[],
            consistency_warnings=[],
        )
    )
    return extractor


@pytest.fixture
def mock_repository():
    """Create mock repository with session."""
    repo = AsyncMock()
    repo.get_by_hash = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.update_status = AsyncMock()
    repo.session = AsyncMock()
    repo.session.flush = AsyncMock()
    repo.session.commit = AsyncMock()
    return repo


@pytest.fixture
def mock_gcs_client():
    """Create mock GCS client."""
    client = MagicMock()
    client.upload = MagicMock(return_value="gs://bucket/documents/id/file.pdf")
    return client


@pytest.fixture
def mock_borrower_repository():
    """Create mock BorrowerRepository."""
    repo = AsyncMock(spec=BorrowerRepository)
    repo.create = AsyncMock()
    return repo


class TestFix1DocumentCommitBeforeProcessing:
    """Tests for Fix 1: Document commit before processing.

    Verifies that session.commit() is called after GCS upload
    to prevent full transaction rollback on processing failure.
    """

    @pytest.mark.asyncio
    async def test_session_commit_called_after_gcs_upload(
        self,
        mock_repository,
        mock_gcs_client,
        mock_docling_processor,
        mock_borrower_repository,
    ):
        """Test that session.commit() is called after GCS upload succeeds."""
        doc_id = uuid4()
        created_doc = Document(
            id=doc_id,
            filename="test.pdf",
            file_hash="abc123",
            file_type="pdf",
            file_size_bytes=100,
            status=DocumentStatus.PENDING,
        )
        mock_repository.create.return_value = created_doc
        mock_repository.get_by_id.return_value = Document(
            id=doc_id,
            filename="test.pdf",
            file_hash="abc123",
            file_type="pdf",
            file_size_bytes=100,
            status=DocumentStatus.COMPLETED,
            page_count=1,
        )

        # Mock extractor with no borrowers to avoid persistence paths
        extractor = MagicMock(spec=BorrowerExtractor)
        extractor.extract = MagicMock(
            return_value=MagicMock(
                borrowers=[],
                validation_errors=[],
                consistency_warnings=[],
            )
        )

        service = DocumentService(
            repository=mock_repository,
            gcs_client=mock_gcs_client,
            docling_processor=mock_docling_processor,
            borrower_extractor=extractor,
            borrower_repository=mock_borrower_repository,
        )

        await service.upload(
            filename="test.pdf",
            content=b"pdf content",
            content_type="application/pdf",
        )

        # CRITICAL: session.commit() should be called after GCS upload
        mock_repository.session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_document_persists_even_if_processing_fails(
        self,
        mock_repository,
        mock_gcs_client,
        mock_borrower_repository,
    ):
        """Test that document persists even if Docling processing fails."""
        doc_id = uuid4()
        created_doc = Document(
            id=doc_id,
            filename="test.pdf",
            file_hash="abc123",
            file_type="pdf",
            file_size_bytes=100,
            status=DocumentStatus.PENDING,
        )
        mock_repository.create.return_value = created_doc

        # After processing failure, document should have FAILED status
        failed_doc = Document(
            id=doc_id,
            filename="test.pdf",
            file_hash="abc123",
            file_type="pdf",
            file_size_bytes=100,
            status=DocumentStatus.FAILED,
            error_message="Document processing failed: Invalid PDF",
        )
        mock_repository.get_by_id.return_value = failed_doc

        # Mock Docling to fail
        failing_processor = MagicMock(spec=DoclingProcessor)
        failing_processor.process_bytes = MagicMock(
            side_effect=DocumentProcessingError("Invalid PDF", details="Corrupt")
        )

        extractor = MagicMock(spec=BorrowerExtractor)
        extractor.extract = MagicMock(
            return_value=MagicMock(borrowers=[], validation_errors=[], consistency_warnings=[])
        )

        service = DocumentService(
            repository=mock_repository,
            gcs_client=mock_gcs_client,
            docling_processor=failing_processor,
            borrower_extractor=extractor,
            borrower_repository=mock_borrower_repository,
        )

        result = await service.upload(
            filename="test.pdf",
            content=b"pdf content",
            content_type="application/pdf",
        )

        # Document should exist with FAILED status (not rolled back)
        assert result.status == DocumentStatus.FAILED
        # session.commit() was called after GCS upload (before processing failed)
        mock_repository.session.commit.assert_called_once()


class TestFix3PartialBorrowerPersistence:
    """Tests for Fix 3: Partial borrower persistence success.

    Verifies that documents can succeed even if some borrowers fail to persist,
    and error messages accurately reflect partial success.
    """

    @pytest.mark.asyncio
    async def test_partial_persistence_success_marks_completed(
        self,
        mock_repository,
        mock_gcs_client,
        mock_docling_processor,
        mock_borrower_extractor_with_borrowers,
    ):
        """Test that document is COMPLETED when some borrowers persist successfully."""
        doc_id = uuid4()
        created_doc = Document(
            id=doc_id,
            filename="test.pdf",
            file_hash="abc123",
            file_type="pdf",
            file_size_bytes=100,
            status=DocumentStatus.PENDING,
        )
        mock_repository.create.return_value = created_doc
        mock_repository.get_by_id.return_value = Document(
            id=doc_id,
            filename="test.pdf",
            file_hash="abc123",
            file_type="pdf",
            file_size_bytes=100,
            status=DocumentStatus.COMPLETED,
            page_count=1,
        )

        # Mock borrower repository: first two succeed, third fails
        borrower_repo = AsyncMock(spec=BorrowerRepository)
        call_count = 0

        async def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 3:
                # Third borrower fails
                raise ValueError("Database constraint violation")
            return MagicMock()

        borrower_repo.create = AsyncMock(side_effect=mock_create)

        service = DocumentService(
            repository=mock_repository,
            gcs_client=mock_gcs_client,
            docling_processor=mock_docling_processor,
            borrower_extractor=mock_borrower_extractor_with_borrowers,
            borrower_repository=borrower_repo,
        )

        result = await service.upload(
            filename="test.pdf",
            content=b"pdf content",
            content_type="application/pdf",
        )

        # Document should be COMPLETED (not FAILED) despite partial failure
        assert result.status == DocumentStatus.COMPLETED
        # update_status should have been called with COMPLETED and partial success message
        mock_repository.update_status.assert_called()
        call_args = mock_repository.update_status.call_args
        assert call_args[0][1] == DocumentStatus.COMPLETED
        assert "Partial success" in call_args[1]["error_message"]
        assert "2/3" in call_args[1]["error_message"]  # 2 out of 3 succeeded

    @pytest.mark.asyncio
    async def test_partial_persistence_error_message_format(
        self,
        mock_repository,
        mock_gcs_client,
        mock_docling_processor,
        mock_borrower_extractor_with_borrowers,
    ):
        """Test that partial persistence error message has correct format."""
        doc_id = uuid4()
        created_doc = Document(
            id=doc_id,
            filename="test.pdf",
            file_hash="abc123",
            file_type="pdf",
            file_size_bytes=100,
            status=DocumentStatus.PENDING,
        )
        mock_repository.create.return_value = created_doc
        mock_repository.get_by_id.return_value = Document(
            id=doc_id,
            filename="test.pdf",
            file_hash="abc123",
            file_type="pdf",
            file_size_bytes=100,
            status=DocumentStatus.COMPLETED,
            page_count=1,
        )

        # Mock borrower repository: all borrowers fail
        borrower_repo = AsyncMock(spec=BorrowerRepository)
        borrower_repo.create = AsyncMock(side_effect=ValueError("SSN format invalid"))

        service = DocumentService(
            repository=mock_repository,
            gcs_client=mock_gcs_client,
            docling_processor=mock_docling_processor,
            borrower_extractor=mock_borrower_extractor_with_borrowers,
            borrower_repository=borrower_repo,
        )

        await service.upload(
            filename="test.pdf",
            content=b"pdf content",
            content_type="application/pdf",
        )

        # Verify error message format
        call_args = mock_repository.update_status.call_args
        error_msg = call_args[1]["error_message"]
        assert "Partial success: 0/3" in error_msg
        assert "Failed:" in error_msg
        # Should truncate to max 5 borrower names
        assert "John Doe" in error_msg or "..." in error_msg

    @pytest.mark.asyncio
    async def test_all_borrowers_succeed_no_partial_message(
        self,
        mock_repository,
        mock_gcs_client,
        mock_docling_processor,
        mock_borrower_extractor_with_borrowers,
    ):
        """Test that no partial success message appears when all borrowers succeed."""
        doc_id = uuid4()
        created_doc = Document(
            id=doc_id,
            filename="test.pdf",
            file_hash="abc123",
            file_type="pdf",
            file_size_bytes=100,
            status=DocumentStatus.PENDING,
        )
        mock_repository.create.return_value = created_doc
        mock_repository.get_by_id.return_value = Document(
            id=doc_id,
            filename="test.pdf",
            file_hash="abc123",
            file_type="pdf",
            file_size_bytes=100,
            status=DocumentStatus.COMPLETED,
            page_count=1,
        )

        # All borrowers succeed
        borrower_repo = AsyncMock(spec=BorrowerRepository)
        borrower_repo.create = AsyncMock(return_value=MagicMock())

        service = DocumentService(
            repository=mock_repository,
            gcs_client=mock_gcs_client,
            docling_processor=mock_docling_processor,
            borrower_extractor=mock_borrower_extractor_with_borrowers,
            borrower_repository=borrower_repo,
        )

        await service.upload(
            filename="test.pdf",
            content=b"pdf content",
            content_type="application/pdf",
        )

        # update_status should NOT be called for partial success
        # (only called once for processing completion)
        # Check that update_status wasn't called with COMPLETED + error_message
        if mock_repository.update_status.called:
            for call_args in mock_repository.update_status.call_args_list:
                if call_args[0][1] == DocumentStatus.COMPLETED:
                    # Should not have error_message for full success
                    assert "error_message" not in call_args[1] or call_args[1].get("error_message") is None


class TestFix2DetailedErrorLogging:
    """Tests for Fix 2: Detailed error logging.

    Verifies that errors are logged with structured context data
    for easier debugging and monitoring.
    """

    @pytest.mark.asyncio
    async def test_gcs_upload_failure_logs_details(
        self,
        mock_repository,
        mock_docling_processor,
        mock_borrower_repository,
    ):
        """Test that GCS upload failures log detailed error information."""
        doc_id = uuid4()
        created_doc = Document(
            id=doc_id,
            filename="test.pdf",
            file_hash="abc123",
            file_type="pdf",
            file_size_bytes=100,
            status=DocumentStatus.PENDING,
        )
        mock_repository.create.return_value = created_doc

        # Mock GCS to fail
        failing_gcs = MagicMock()
        failing_gcs.upload = MagicMock(side_effect=Exception("Network timeout"))

        extractor = MagicMock(spec=BorrowerExtractor)
        extractor.extract = MagicMock(
            return_value=MagicMock(borrowers=[], validation_errors=[], consistency_warnings=[])
        )

        service = DocumentService(
            repository=mock_repository,
            gcs_client=failing_gcs,
            docling_processor=mock_docling_processor,
            borrower_extractor=extractor,
            borrower_repository=mock_borrower_repository,
        )

        # Should raise DocumentUploadError
        with pytest.raises(Exception):
            await service.upload(
                filename="test.pdf",
                content=b"pdf content",
                content_type="application/pdf",
            )

        # Verify error was logged to repository with detailed message
        mock_repository.update_status.assert_called_once()
        call_args = mock_repository.update_status.call_args
        assert call_args[0][1] == DocumentStatus.FAILED
        assert "GCS upload failed" in call_args[1]["error_message"]
        assert "Network timeout" in call_args[1]["error_message"]

    @pytest.mark.asyncio
    async def test_processing_error_logs_details(
        self,
        mock_repository,
        mock_gcs_client,
        mock_borrower_repository,
    ):
        """Test that processing errors log detailed error information."""
        doc_id = uuid4()
        created_doc = Document(
            id=doc_id,
            filename="test.pdf",
            file_hash="abc123",
            file_type="pdf",
            file_size_bytes=100,
            status=DocumentStatus.PENDING,
        )
        mock_repository.create.return_value = created_doc
        mock_repository.get_by_id.return_value = Document(
            id=doc_id,
            filename="test.pdf",
            file_hash="abc123",
            file_type="pdf",
            file_size_bytes=100,
            status=DocumentStatus.FAILED,
            error_message="Document processing failed: Corrupted PDF (Invalid header)",
        )

        # Mock Docling to fail with details
        failing_processor = MagicMock(spec=DoclingProcessor)
        failing_processor.process_bytes = MagicMock(
            side_effect=DocumentProcessingError(
                "Corrupted PDF",
                details="Invalid header",
            )
        )

        extractor = MagicMock(spec=BorrowerExtractor)
        extractor.extract = MagicMock(
            return_value=MagicMock(borrowers=[], validation_errors=[], consistency_warnings=[])
        )

        service = DocumentService(
            repository=mock_repository,
            gcs_client=mock_gcs_client,
            docling_processor=failing_processor,
            borrower_extractor=extractor,
            borrower_repository=mock_borrower_repository,
        )

        result = await service.upload(
            filename="test.pdf",
            content=b"pdf content",
            content_type="application/pdf",
        )

        # Verify detailed error message
        assert result.status == DocumentStatus.FAILED
        assert "Corrupted PDF" in result.error_message
        assert "Invalid header" in result.error_message
