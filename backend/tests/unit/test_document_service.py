"""Unit tests for DocumentService."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.extraction import BorrowerExtractor
from src.ingestion.docling_processor import (
    DoclingProcessor,
    DocumentContent,
    DocumentProcessingError,
    PageContent,
)
from src.ingestion.document_service import (
    DocumentService,
    DocumentUploadError,
    DuplicateDocumentError,
)
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
def mock_docling_processor_failing():
    """Create mock DoclingProcessor that fails (for error testing)."""
    processor = MagicMock(spec=DoclingProcessor)
    processor.process_bytes = MagicMock(
        side_effect=DocumentProcessingError("Invalid PDF format", details="Corrupted file")
    )
    return processor


@pytest.fixture
def mock_borrower_extractor():
    """Create mock BorrowerExtractor."""
    extractor = MagicMock(spec=BorrowerExtractor)
    extractor.extract = MagicMock(
        return_value=MagicMock(
            borrowers=[],
            validation_errors=[],
            consistency_warnings=[],
        )
    )
    return extractor


@pytest.fixture
def mock_borrower_repository():
    """Create mock BorrowerRepository."""
    repo = AsyncMock(spec=BorrowerRepository)
    repo.create = AsyncMock()
    return repo


class TestDocumentServiceValidation:
    """Tests for DocumentService validation."""

    def test_compute_file_hash(self):
        """Test SHA-256 hash computation."""
        content = b"test content"
        hash1 = DocumentService.compute_file_hash(content)
        hash2 = DocumentService.compute_file_hash(content)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 produces 64 hex chars

    def test_compute_file_hash_different_content(self):
        """Test that different content produces different hash."""
        hash1 = DocumentService.compute_file_hash(b"content 1")
        hash2 = DocumentService.compute_file_hash(b"content 2")
        assert hash1 != hash2

    def test_validate_file_pdf(
        self, mock_docling_processor, mock_borrower_extractor, mock_borrower_repository
    ):
        """Test PDF validation."""
        service = DocumentService(
            repository=MagicMock(),
            gcs_client=MagicMock(),
            docling_processor=mock_docling_processor,
            borrower_extractor=mock_borrower_extractor,
            borrower_repository=mock_borrower_repository,
        )
        content_type, file_type = service.validate_file(
            b"pdf content",
            "application/pdf",
            "test.pdf",
        )
        assert content_type == "application/pdf"
        assert file_type == "pdf"

    def test_validate_file_docx(
        self, mock_docling_processor, mock_borrower_extractor, mock_borrower_repository
    ):
        """Test DOCX validation."""
        service = DocumentService(
            repository=MagicMock(),
            gcs_client=MagicMock(),
            docling_processor=mock_docling_processor,
            borrower_extractor=mock_borrower_extractor,
            borrower_repository=mock_borrower_repository,
        )
        docx_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        content_type, file_type = service.validate_file(
            b"docx content",
            docx_mime,
            "test.docx",
        )
        assert file_type == "docx"

    def test_validate_file_infer_from_filename(
        self, mock_docling_processor, mock_borrower_extractor, mock_borrower_repository
    ):
        """Test content type inference from filename."""
        service = DocumentService(
            repository=MagicMock(),
            gcs_client=MagicMock(),
            docling_processor=mock_docling_processor,
            borrower_extractor=mock_borrower_extractor,
            borrower_repository=mock_borrower_repository,
        )
        content_type, file_type = service.validate_file(
            b"pdf content",
            None,  # No content type provided
            "document.pdf",
        )
        assert content_type == "application/pdf"
        assert file_type == "pdf"

    def test_validate_file_unsupported_type(
        self, mock_docling_processor, mock_borrower_extractor, mock_borrower_repository
    ):
        """Test rejection of unsupported file types."""
        service = DocumentService(
            repository=MagicMock(),
            gcs_client=MagicMock(),
            docling_processor=mock_docling_processor,
            borrower_extractor=mock_borrower_extractor,
            borrower_repository=mock_borrower_repository,
        )
        with pytest.raises(ValueError, match="Unsupported file type"):
            service.validate_file(
                b"content",
                "text/plain",
                "test.txt",
            )

    def test_validate_file_too_large(
        self, mock_docling_processor, mock_borrower_extractor, mock_borrower_repository
    ):
        """Test rejection of oversized files."""
        service = DocumentService(
            repository=MagicMock(),
            gcs_client=MagicMock(),
            docling_processor=mock_docling_processor,
            borrower_extractor=mock_borrower_extractor,
            borrower_repository=mock_borrower_repository,
        )
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB
        with pytest.raises(ValueError, match="File too large"):
            service.validate_file(
                large_content,
                "application/pdf",
                "large.pdf",
            )


class TestDocumentServiceUpload:
    """Tests for DocumentService.upload method."""

    @pytest.fixture
    def mock_repository(self):
        """Create mock repository."""
        repo = AsyncMock()
        repo.get_by_hash = AsyncMock(return_value=None)
        repo.create = AsyncMock()
        repo.get_by_id = AsyncMock()
        repo.update_status = AsyncMock()
        repo.session = AsyncMock()
        repo.session.flush = AsyncMock()
        return repo

    @pytest.fixture
    def mock_gcs_client(self):
        """Create mock GCS client."""
        client = MagicMock()
        client.upload = MagicMock(return_value="gs://bucket/documents/id/file.pdf")
        return client

    @pytest.mark.asyncio
    async def test_upload_success_returns_completed(
        self,
        mock_repository,
        mock_gcs_client,
        mock_docling_processor,
        mock_borrower_extractor,
        mock_borrower_repository,
    ):
        """Test successful upload returns document with COMPLETED status."""
        # Setup mock to return the created document
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

        # After processing, get_by_id returns completed document
        completed_doc = Document(
            id=doc_id,
            filename="test.pdf",
            file_hash="abc123",
            file_type="pdf",
            file_size_bytes=100,
            status=DocumentStatus.COMPLETED,
            page_count=1,
        )
        mock_repository.get_by_id.return_value = completed_doc

        service = DocumentService(
            repository=mock_repository,
            gcs_client=mock_gcs_client,
            docling_processor=mock_docling_processor,
            borrower_extractor=mock_borrower_extractor,
            borrower_repository=mock_borrower_repository,
        )

        result = await service.upload(
            filename="test.pdf",
            content=b"pdf content",
            content_type="application/pdf",
        )

        assert result.filename == "test.pdf"
        # CRITICAL: Status should be COMPLETED (processing is synchronous)
        assert result.status == DocumentStatus.COMPLETED
        assert result.page_count == 1
        mock_repository.get_by_hash.assert_called_once()
        mock_repository.create.assert_called_once()
        mock_gcs_client.upload.assert_called_once()
        mock_docling_processor.process_bytes.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_duplicate_rejected(
        self,
        mock_repository,
        mock_gcs_client,
        mock_docling_processor,
        mock_borrower_extractor,
        mock_borrower_repository,
    ):
        """Test that duplicate file is rejected."""
        existing_doc = Document(
            id=uuid4(),
            filename="existing.pdf",
            file_hash="samehash",
            file_type="pdf",
            file_size_bytes=100,
            status=DocumentStatus.COMPLETED,
        )
        mock_repository.get_by_hash.return_value = existing_doc

        service = DocumentService(
            repository=mock_repository,
            gcs_client=mock_gcs_client,
            docling_processor=mock_docling_processor,
            borrower_extractor=mock_borrower_extractor,
            borrower_repository=mock_borrower_repository,
        )

        with pytest.raises(DuplicateDocumentError) as exc_info:
            await service.upload(
                filename="duplicate.pdf",
                content=b"same content",
                content_type="application/pdf",
            )

        assert exc_info.value.existing_id == existing_doc.id
        mock_repository.create.assert_not_called()
        mock_gcs_client.upload.assert_not_called()

    @pytest.mark.asyncio
    async def test_upload_gcs_failure_marks_failed(
        self,
        mock_repository,
        mock_gcs_client,
        mock_docling_processor,
        mock_borrower_extractor,
        mock_borrower_repository,
    ):
        """Test that GCS upload failure marks document as FAILED."""
        created_doc = Document(
            id=uuid4(),
            filename="test.pdf",
            file_hash="abc123",
            file_type="pdf",
            file_size_bytes=100,
            status=DocumentStatus.PENDING,
        )
        mock_repository.create.return_value = created_doc
        mock_gcs_client.upload.side_effect = Exception("GCS error")

        service = DocumentService(
            repository=mock_repository,
            gcs_client=mock_gcs_client,
            docling_processor=mock_docling_processor,
            borrower_extractor=mock_borrower_extractor,
            borrower_repository=mock_borrower_repository,
        )

        with pytest.raises(DocumentUploadError, match="Failed to upload"):
            await service.upload(
                filename="test.pdf",
                content=b"content",
                content_type="application/pdf",
            )

        # Verify status was updated to FAILED
        mock_repository.update_status.assert_called_once()
        call_args = mock_repository.update_status.call_args
        assert call_args[0][1] == DocumentStatus.FAILED
        # Error message should mention GCS
        assert "GCS" in call_args[1]["error_message"]

    @pytest.mark.asyncio
    async def test_upload_calls_docling_processor(
        self,
        mock_repository,
        mock_gcs_client,
        mock_docling_processor,
        mock_borrower_extractor,
        mock_borrower_repository,
    ):
        """Test that upload calls DoclingProcessor.process_bytes."""
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

        completed_doc = Document(
            id=doc_id,
            filename="test.pdf",
            file_hash="abc123",
            file_type="pdf",
            file_size_bytes=100,
            status=DocumentStatus.COMPLETED,
            page_count=1,
        )
        mock_repository.get_by_id.return_value = completed_doc

        service = DocumentService(
            repository=mock_repository,
            gcs_client=mock_gcs_client,
            docling_processor=mock_docling_processor,
            borrower_extractor=mock_borrower_extractor,
            borrower_repository=mock_borrower_repository,
        )

        await service.upload(
            filename="test.pdf",
            content=b"pdf content",
            content_type="application/pdf",
        )

        # DoclingProcessor should be called with content and filename
        mock_docling_processor.process_bytes.assert_called_once_with(b"pdf content", "test.pdf")

    @pytest.mark.asyncio
    async def test_upload_processing_error_marks_failed(
        self,
        mock_repository,
        mock_gcs_client,
        mock_docling_processor_failing,
        mock_borrower_extractor,
        mock_borrower_repository,
    ):
        """Test that processing errors mark document as FAILED."""
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

        failed_doc = Document(
            id=doc_id,
            filename="test.pdf",
            file_hash="abc123",
            file_type="pdf",
            file_size_bytes=100,
            status=DocumentStatus.FAILED,
            error_message="Document processing failed: Invalid PDF format",
        )
        mock_repository.get_by_id.return_value = failed_doc

        service = DocumentService(
            repository=mock_repository,
            gcs_client=mock_gcs_client,
            docling_processor=mock_docling_processor_failing,
            borrower_extractor=mock_borrower_extractor,
            borrower_repository=mock_borrower_repository,
        )

        result = await service.upload(
            filename="test.pdf",
            content=b"content",
            content_type="application/pdf",
        )

        # Document should be FAILED (not crash)
        assert result.status == DocumentStatus.FAILED
        assert result.error_message is not None


class TestDocumentServiceProcessing:
    """Tests for DocumentService processing methods."""

    @pytest.mark.asyncio
    async def test_update_processing_success(
        self, mock_docling_processor, mock_borrower_extractor, mock_borrower_repository
    ):
        """Test updating document after successful processing."""
        mock_repository = AsyncMock()
        updated_doc = Document(
            id=uuid4(),
            filename="test.pdf",
            file_hash="abc",
            file_type="pdf",
            file_size_bytes=100,
            status=DocumentStatus.COMPLETED,
            page_count=5,
        )
        mock_repository.update_status.return_value = updated_doc

        service = DocumentService(
            repository=mock_repository,
            gcs_client=MagicMock(),
            docling_processor=mock_docling_processor,
            borrower_extractor=mock_borrower_extractor,
            borrower_repository=mock_borrower_repository,
        )

        result = await service.update_processing_result(
            document_id=updated_doc.id,
            success=True,
            page_count=5,
        )

        assert result is not None
        assert result.status == DocumentStatus.COMPLETED
        mock_repository.update_status.assert_called_once_with(
            updated_doc.id,
            DocumentStatus.COMPLETED,
            error_message=None,
            page_count=5,
        )

    @pytest.mark.asyncio
    async def test_update_processing_failure(
        self, mock_docling_processor, mock_borrower_extractor, mock_borrower_repository
    ):
        """Test updating document after failed processing."""
        mock_repository = AsyncMock()
        doc_id = uuid4()
        mock_repository.update_status.return_value = Document(
            id=doc_id,
            filename="test.pdf",
            file_hash="abc",
            file_type="pdf",
            file_size_bytes=100,
            status=DocumentStatus.FAILED,
            error_message="OCR failed",
        )

        service = DocumentService(
            repository=mock_repository,
            gcs_client=MagicMock(),
            docling_processor=mock_docling_processor,
            borrower_extractor=mock_borrower_extractor,
            borrower_repository=mock_borrower_repository,
        )

        result = await service.update_processing_result(
            document_id=doc_id,
            success=False,
            error_message="OCR failed",
        )

        assert result is not None
        assert result.status == DocumentStatus.FAILED
        mock_repository.update_status.assert_called_once_with(
            doc_id,
            DocumentStatus.FAILED,
            error_message="OCR failed",
            page_count=None,
        )


class TestDocumentServiceErrorHandling:
    """Tests for error handling (INGEST-14 coverage)."""

    @pytest.mark.asyncio
    async def test_validation_error_does_not_crash(
        self, mock_docling_processor, mock_borrower_extractor, mock_borrower_repository
    ):
        """Test that validation errors are raised properly without crashing."""
        service = DocumentService(
            repository=MagicMock(),
            gcs_client=MagicMock(),
            docling_processor=mock_docling_processor,
            borrower_extractor=mock_borrower_extractor,
            borrower_repository=mock_borrower_repository,
        )

        # Invalid file type should raise ValueError, not crash
        with pytest.raises(ValueError) as exc_info:
            await service.upload(
                filename="test.txt",
                content=b"text content",
                content_type="text/plain",
            )

        assert "Unsupported file type" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_duplicate_error_does_not_crash(
        self, mock_docling_processor, mock_borrower_extractor, mock_borrower_repository
    ):
        """Test that duplicate detection errors are raised properly."""
        mock_repository = AsyncMock()
        existing_doc = Document(
            id=uuid4(),
            filename="existing.pdf",
            file_hash="hash123",
            file_type="pdf",
            file_size_bytes=100,
            status=DocumentStatus.COMPLETED,
        )
        mock_repository.get_by_hash.return_value = existing_doc

        service = DocumentService(
            repository=mock_repository,
            gcs_client=MagicMock(),
            docling_processor=mock_docling_processor,
            borrower_extractor=mock_borrower_extractor,
            borrower_repository=mock_borrower_repository,
        )

        with pytest.raises(DuplicateDocumentError) as exc_info:
            await service.upload(
                filename="test.pdf",
                content=b"content",
                content_type="application/pdf",
            )

        # Error should contain useful information
        assert exc_info.value.existing_id == existing_doc.id
        assert exc_info.value.file_hash is not None

    @pytest.mark.asyncio
    async def test_gcs_error_wrapped_properly(
        self, mock_docling_processor, mock_borrower_extractor, mock_borrower_repository
    ):
        """Test that GCS errors are wrapped in DocumentUploadError."""
        mock_repository = AsyncMock()
        mock_repository.get_by_hash.return_value = None
        mock_repository.create.return_value = Document(
            id=uuid4(),
            filename="test.pdf",
            file_hash="abc",
            file_type="pdf",
            file_size_bytes=100,
            status=DocumentStatus.PENDING,
        )

        mock_gcs = MagicMock()
        mock_gcs.upload.side_effect = RuntimeError("Network timeout")

        service = DocumentService(
            repository=mock_repository,
            gcs_client=mock_gcs,
            docling_processor=mock_docling_processor,
            borrower_extractor=mock_borrower_extractor,
            borrower_repository=mock_borrower_repository,
        )

        with pytest.raises(DocumentUploadError) as exc_info:
            await service.upload(
                filename="test.pdf",
                content=b"content",
                content_type="application/pdf",
            )

        # Original error should be chained
        assert exc_info.value.__cause__ is not None
