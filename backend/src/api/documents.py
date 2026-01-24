"""Document API endpoints.

Document upload includes synchronous Docling processing. Uploads return
with status=COMPLETED or status=FAILED after processing completes.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from src.api.dependencies import DocumentRepoDep, DocumentServiceDep
from src.ingestion.document_service import DocumentUploadError, DuplicateDocumentError

router = APIRouter(prefix="/api/documents", tags=["documents"])


class DocumentUploadResponse(BaseModel):
    """Response for document upload.

    Processing is synchronous - status will be 'completed' or 'failed' after upload.
    """

    id: UUID = Field(..., description="Document ID")
    filename: str = Field(..., description="Original filename")
    file_hash: str = Field(..., description="SHA-256 hash of file")
    file_size_bytes: int = Field(..., description="File size in bytes")
    status: str = Field(..., description="Processing status (completed/failed)")
    page_count: int | None = Field(None, description="Number of pages (if processing succeeded)")
    error_message: str | None = Field(None, description="Error details (if processing failed)")
    message: str = Field(..., description="Status message")


class DocumentResponse(BaseModel):
    """Response for document details."""

    id: UUID
    filename: str
    file_hash: str
    file_type: str
    file_size_bytes: int
    gcs_uri: str | None
    status: str
    error_message: str | None
    page_count: int | None


class DocumentListResponse(BaseModel):
    """Response for document list."""

    documents: list[DocumentResponse]
    total: int
    limit: int
    offset: int


class DocumentStatusResponse(BaseModel):
    """Lightweight status response for polling."""

    id: UUID
    status: str
    page_count: int | None = None
    error_message: str | None = None


@router.post(
    "/",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document",
    description="""Upload a document for processing. Supports PDF, DOCX, PNG, and JPG files.

Document processing (text extraction via Docling) is synchronous.
Response will include status='completed' with page_count, or status='failed' with error_message.""",
)
async def upload_document(
    file: UploadFile,
    service: DocumentServiceDep,
) -> DocumentUploadResponse:
    """Upload a document for processing.

    Args:
        file: Uploaded file (multipart form)
        service: DocumentService (injected)

    Returns:
        DocumentUploadResponse with document ID and processing status

    Raises:
        400: Invalid file type or size
        409: Duplicate file (same hash exists)
        500: Upload failed
    """
    from src.storage.models import DocumentStatus

    try:
        # Read file content
        content = await file.read()

        # Upload and process document (creates DB record + uploads to GCS + Docling)
        document = await service.upload(
            filename=file.filename or "unknown",
            content=content,
            content_type=file.content_type,
        )

        # Generate processing-aware message
        if document.status == DocumentStatus.COMPLETED:
            message = f"Document processed successfully with {document.page_count} page(s)"
        elif document.status == DocumentStatus.FAILED:
            message = (
                f"Document upload succeeded but processing failed: "
                f"{document.error_message or 'Unknown error'}"
            )
        else:
            message = "Document uploaded. Processing status: pending"

        return DocumentUploadResponse(
            id=document.id,
            filename=document.filename,
            file_hash=document.file_hash,
            file_size_bytes=document.file_size_bytes,
            status=document.status.value,
            page_count=document.page_count,
            error_message=document.error_message,
            message=message,
        )

    except ValueError as e:
        # Validation errors (file type, size)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    except DuplicateDocumentError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Duplicate document detected",
                "existing_id": str(e.existing_id),
                "file_hash": e.file_hash,
            },
        ) from e

    except DocumentUploadError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e

    finally:
        await file.close()


@router.get(
    "/{document_id}/status",
    response_model=DocumentStatusResponse,
    summary="Get document processing status",
    description="Lightweight endpoint for polling document status. Use this instead of GET /{id} when only status is needed.",
)
async def get_document_status(
    document_id: UUID,
    repository: DocumentRepoDep,
) -> DocumentStatusResponse:
    """Get document processing status.

    Args:
        document_id: Document UUID
        repository: DocumentRepository (injected)

    Returns:
        DocumentStatusResponse with status, page_count, error_message

    Raises:
        404: Document not found
    """
    document = await repository.get_by_id(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}",
        )

    return DocumentStatusResponse(
        id=document.id,
        status=document.status.value,
        page_count=document.page_count,
        error_message=document.error_message,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document by ID",
    description="Get document details including processing status. Poll this endpoint to check when processing completes.",
)
async def get_document(
    document_id: UUID,
    service: DocumentServiceDep,
) -> DocumentResponse:
    """Get document details by ID.

    Args:
        document_id: Document UUID
        service: DocumentService (injected)

    Returns:
        DocumentResponse with document details

    Raises:
        404: Document not found
    """
    document = await service.get_document(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}",
        )

    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        file_hash=document.file_hash,
        file_type=document.file_type,
        file_size_bytes=document.file_size_bytes,
        gcs_uri=document.gcs_uri,
        status=document.status.value,
        error_message=document.error_message,
        page_count=document.page_count,
    )


@router.get(
    "/",
    response_model=DocumentListResponse,
    summary="List documents",
)
async def list_documents(
    repository: DocumentRepoDep,
    limit: int = 100,
    offset: int = 0,
) -> DocumentListResponse:
    """List documents with pagination.

    Args:
        repository: DocumentRepository (injected)
        limit: Maximum documents to return (default 100)
        offset: Number of documents to skip (default 0)

    Returns:
        DocumentListResponse with documents and pagination info
    """
    documents = await repository.list_documents(limit=limit, offset=offset)

    return DocumentListResponse(
        documents=[
            DocumentResponse(
                id=doc.id,
                filename=doc.filename,
                file_hash=doc.file_hash,
                file_type=doc.file_type,
                file_size_bytes=doc.file_size_bytes,
                gcs_uri=doc.gcs_uri,
                status=doc.status.value,
                error_message=doc.error_message,
                page_count=doc.page_count,
            )
            for doc in documents
        ],
        total=len(documents),  # Simplified - would need count query for true total
        limit=limit,
        offset=offset,
    )
