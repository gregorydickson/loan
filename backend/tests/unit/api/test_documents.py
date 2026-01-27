"""Unit tests for documents API endpoints."""

from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.api.documents import (
    delete_document,
    get_document,
    get_document_status,
    list_documents,
    upload_document,
)
from src.ingestion.document_service import DocumentUploadError
from src.storage.models import DocumentStatus


class TestUploadDocumentErrors:
    """Test upload_document error handling."""

    @pytest.mark.asyncio
    async def test_upload_document_value_error_returns_400(self):
        """Test that ValueError during upload returns 400 Bad Request."""
        # Setup mock file
        mock_file = Mock()
        mock_file.filename = "test.txt"
        mock_file.content_type = "text/plain"
        mock_file.read = AsyncMock(return_value=b"content")
        mock_file.close = AsyncMock()

        # Setup mock service that raises ValueError
        mock_service = Mock()
        mock_service.upload = AsyncMock(
            side_effect=ValueError("Invalid file type: text/plain")
        )

        # Call should raise HTTPException with 400
        with pytest.raises(HTTPException) as exc_info:
            await upload_document(
                file=mock_file, service=mock_service, method="docling", ocr="auto"
            )

        assert exc_info.value.status_code == 400
        assert "Invalid file type" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_upload_document_upload_error_returns_500(self):
        """Test that DocumentUploadError returns 500 Internal Server Error."""
        # Setup mock file
        mock_file = Mock()
        mock_file.filename = "test.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.read = AsyncMock(return_value=b"pdf content")
        mock_file.close = AsyncMock()

        # Setup mock service that raises DocumentUploadError
        mock_service = Mock()
        mock_service.upload = AsyncMock(
            side_effect=DocumentUploadError("GCS upload failed")
        )

        # Call should raise HTTPException with 500
        with pytest.raises(HTTPException) as exc_info:
            await upload_document(
                file=mock_file, service=mock_service, method="docling", ocr="auto"
            )

        assert exc_info.value.status_code == 500
        assert "GCS upload failed" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_upload_document_file_closed_on_success(self):
        """Test that uploaded file is closed even on success."""
        # Setup mock file
        mock_file = Mock()
        mock_file.filename = "test.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.read = AsyncMock(return_value=b"pdf content")
        mock_file.close = AsyncMock()

        # Setup mock service with successful upload
        mock_document = Mock()
        mock_document.id = uuid4()
        mock_document.filename = "test.pdf"
        mock_document.file_hash = "abc123"
        mock_document.file_size_bytes = 100
        mock_document.status = DocumentStatus.COMPLETED
        mock_document.page_count = 5
        mock_document.error_message = None
        mock_document.extraction_method = "docling"
        mock_document.ocr_processed = False

        mock_service = Mock()
        mock_service.upload = AsyncMock(return_value=mock_document)

        # Upload document
        await upload_document(
            file=mock_file, service=mock_service, method="docling", ocr="auto"
        )

        # Verify file was closed
        mock_file.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_document_file_closed_on_error(self):
        """Test that uploaded file is closed even when error occurs."""
        # Setup mock file
        mock_file = Mock()
        mock_file.filename = "test.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.read = AsyncMock(return_value=b"pdf content")
        mock_file.close = AsyncMock()

        # Setup mock service that raises error
        mock_service = Mock()
        mock_service.upload = AsyncMock(side_effect=ValueError("Error"))

        # Upload should fail but file should still be closed
        with pytest.raises(HTTPException):
            await upload_document(
                file=mock_file, service=mock_service, method="docling", ocr="auto"
            )

        # Verify file was closed even though error occurred
        mock_file.close.assert_called_once()


class TestUploadDocumentStatusMessages:
    """Test upload response message generation for different statuses."""

    @pytest.mark.asyncio
    async def test_upload_completed_status_message(self):
        """Test message for completed document."""
        mock_file = Mock()
        mock_file.filename = "test.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.read = AsyncMock(return_value=b"content")
        mock_file.close = AsyncMock()

        mock_document = Mock()
        mock_document.id = uuid4()
        mock_document.filename = "test.pdf"
        mock_document.file_hash = "hash123"
        mock_document.file_size_bytes = 1000
        mock_document.status = DocumentStatus.COMPLETED
        mock_document.page_count = 3
        mock_document.error_message = None
        mock_document.extraction_method = "docling"
        mock_document.ocr_processed = False

        mock_service = Mock()
        mock_service.upload = AsyncMock(return_value=mock_document)

        response = await upload_document(
            file=mock_file, service=mock_service, method="docling", ocr="auto"
        )

        assert response.message == "Document processed successfully with 3 page(s)"

    @pytest.mark.asyncio
    async def test_upload_failed_status_message(self):
        """Test message for failed document."""
        mock_file = Mock()
        mock_file.filename = "test.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.read = AsyncMock(return_value=b"content")
        mock_file.close = AsyncMock()

        mock_document = Mock()
        mock_document.id = uuid4()
        mock_document.filename = "test.pdf"
        mock_document.file_hash = "hash123"
        mock_document.file_size_bytes = 1000
        mock_document.status = DocumentStatus.FAILED
        mock_document.page_count = None
        mock_document.error_message = "Corrupted PDF"
        mock_document.extraction_method = "docling"
        mock_document.ocr_processed = False

        mock_service = Mock()
        mock_service.upload = AsyncMock(return_value=mock_document)

        response = await upload_document(
            file=mock_file, service=mock_service, method="docling", ocr="auto"
        )

        assert (
            "Document upload succeeded but processing failed: Corrupted PDF"
            in response.message
        )

    @pytest.mark.asyncio
    async def test_upload_pending_status_message(self):
        """Test message for pending document (async processing)."""
        mock_file = Mock()
        mock_file.filename = "test.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.read = AsyncMock(return_value=b"content")
        mock_file.close = AsyncMock()

        mock_document = Mock()
        mock_document.id = uuid4()
        mock_document.filename = "test.pdf"
        mock_document.file_hash = "hash123"
        mock_document.file_size_bytes = 1000
        mock_document.status = DocumentStatus.PENDING
        mock_document.page_count = None
        mock_document.error_message = None
        mock_document.extraction_method = "docling"
        mock_document.ocr_processed = None

        mock_service = Mock()
        mock_service.upload = AsyncMock(return_value=mock_document)

        response = await upload_document(
            file=mock_file, service=mock_service, method="docling", ocr="auto"
        )

        assert (
            "Document uploaded and queued for processing" in response.message
        )


class TestGetDocumentStatusErrors:
    """Test get_document_status error handling."""

    @pytest.mark.asyncio
    async def test_get_status_not_found_raises_404(self):
        """Test that missing document returns 404."""
        document_id = uuid4()
        mock_repository = Mock()
        mock_repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await get_document_status(
                document_id=document_id, repository=mock_repository
            )

        assert exc_info.value.status_code == 404
        assert str(document_id) in str(exc_info.value.detail)


class TestGetDocumentErrors:
    """Test get_document error handling."""

    @pytest.mark.asyncio
    async def test_get_document_not_found_raises_404(self):
        """Test that missing document returns 404."""
        document_id = uuid4()
        mock_service = Mock()
        mock_service.get_document = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await get_document(document_id=document_id, service=mock_service)

        assert exc_info.value.status_code == 404
        assert str(document_id) in str(exc_info.value.detail)


class TestDeleteDocumentErrors:
    """Test delete_document error handling."""

    @pytest.mark.asyncio
    async def test_delete_document_not_found_raises_404(self):
        """Test that deleting non-existent document returns 404."""
        document_id = uuid4()
        mock_service = Mock()
        mock_service.delete_document = AsyncMock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            await delete_document(document_id=document_id, service=mock_service)

        assert exc_info.value.status_code == 404
        assert str(document_id) in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_delete_document_success(self):
        """Test successful document deletion."""
        document_id = uuid4()
        mock_service = Mock()
        mock_service.delete_document = AsyncMock(return_value=True)

        response = await delete_document(document_id=document_id, service=mock_service)

        assert response.id == document_id
        assert response.deleted is True
        assert "deleted successfully" in response.message


class TestListDocuments:
    """Test list_documents endpoint."""

    @pytest.mark.asyncio
    async def test_list_documents_returns_paginated_response(self):
        """Test that list_documents returns proper pagination info."""
        mock_doc1 = Mock()
        mock_doc1.id = uuid4()
        mock_doc1.filename = "doc1.pdf"
        mock_doc1.file_hash = "hash1"
        mock_doc1.file_type = "application/pdf"
        mock_doc1.file_size_bytes = 1000
        mock_doc1.gcs_uri = "gs://bucket/doc1.pdf"
        mock_doc1.status = DocumentStatus.COMPLETED
        mock_doc1.error_message = None
        mock_doc1.page_count = 5

        mock_doc2 = Mock()
        mock_doc2.id = uuid4()
        mock_doc2.filename = "doc2.pdf"
        mock_doc2.file_hash = "hash2"
        mock_doc2.file_type = "application/pdf"
        mock_doc2.file_size_bytes = 2000
        mock_doc2.gcs_uri = "gs://bucket/doc2.pdf"
        mock_doc2.status = DocumentStatus.COMPLETED
        mock_doc2.error_message = None
        mock_doc2.page_count = 10

        mock_repository = Mock()
        mock_repository.list_documents = AsyncMock(return_value=[mock_doc1, mock_doc2])
        mock_repository.count = AsyncMock(return_value=25)

        response = await list_documents(
            repository=mock_repository, limit=10, offset=0
        )

        assert len(response.documents) == 2
        assert response.total == 25
        assert response.limit == 10
        assert response.offset == 0
        assert response.documents[0].filename == "doc1.pdf"
        assert response.documents[1].filename == "doc2.pdf"
