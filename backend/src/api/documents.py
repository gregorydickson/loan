"""Document API endpoints.

In production (Cloud Tasks configured): Upload returns immediately with PENDING status.
In development (no Cloud Tasks): Upload returns after synchronous processing completes.
"""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field

from src.api.dependencies import DocumentRepoDep, DocumentServiceDep
from src.ingestion.document_service import DocumentUploadError, DuplicateDocumentError

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Type aliases for dual pipeline support (v2.0)
# ExtractionMethod: Which extraction pipeline to use
#   - "docling": Docling-based extraction (v1.0 default)
#   - "langextract": LangExtract pipeline (v2.0 structured extraction)
#   - "auto": Automatically select based on document type (future enhancement)
ExtractionMethod = Literal["docling", "langextract", "auto"]

# OCRMode: How to handle OCR for scanned documents
#   - "auto": Detect scanned pages and apply OCR if needed
#   - "force": Always apply OCR regardless of content
#   - "skip": Never apply OCR (assume all text is extractable)
OCRMode = Literal["auto", "force", "skip"]


class DocumentUploadResponse(BaseModel):
    """Response for document upload.

    In async mode (production): status='pending', poll /status endpoint.
    In sync mode (development): status='completed' or 'failed' immediately.
    """

    id: UUID = Field(..., description="Document ID")
    filename: str = Field(..., description="Original filename")
    file_hash: str = Field(..., description="SHA-256 hash of file")
    file_size_bytes: int = Field(..., description="File size in bytes")
    status: str = Field(..., description="Processing status (completed/failed)")
    page_count: int | None = Field(None, description="Number of pages (if processing succeeded)")
    error_message: str | None = Field(None, description="Error details (if processing failed)")
    message: str = Field(..., description="Status message")
    # Extraction metadata (v2.0)
    extraction_method: str | None = Field(
        None, description="Extraction method used (docling/langextract)"
    )
    ocr_processed: bool | None = Field(
        None, description="Whether OCR was applied to the document"
    )


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

**Extraction Method (v2.0):**
- `docling` (default): Docling-based extraction, preserves v1.0 behavior
- `langextract`: LangExtract structured extraction pipeline
- `auto`: Automatically select based on document type

**OCR Mode:**
- `auto` (default): Detect scanned pages and apply OCR if needed
- `force`: Always apply OCR regardless of content
- `skip`: Never apply OCR

In production (Cloud Tasks configured): Returns immediately with status='pending'.
Poll GET /api/documents/{id}/status to check processing progress.

In development (no Cloud Tasks): Processing is synchronous.
Response will include status='completed' or status='failed'.""",
)
async def upload_document(
    file: UploadFile,
    service: DocumentServiceDep,
    method: ExtractionMethod = Query(
        default="docling",
        description="Extraction method: docling (default), langextract, or auto",
    ),
    ocr: OCRMode = Query(
        default="auto",
        description="OCR mode: auto (default), force, or skip",
    ),
) -> DocumentUploadResponse:
    """Upload a document for processing.

    Args:
        file: Uploaded file (multipart form)
        service: DocumentService (injected)
        method: Extraction method (docling/langextract/auto). Default 'docling' for backward compatibility.
        ocr: OCR mode (auto/force/skip). Default 'auto' for automatic detection.

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

        # Upload and process document (creates DB record + uploads to GCS + extraction)
        # Pass extraction method and OCR mode for dual pipeline support (v2.0)
        document = await service.upload(
            filename=file.filename or "unknown",
            content=content,
            content_type=file.content_type,
            extraction_method=method,
            ocr_mode=ocr,
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
            # PENDING or PROCESSING
            message = "Document uploaded and queued for processing. Poll status endpoint for updates."

        return DocumentUploadResponse(
            id=document.id,
            filename=document.filename,
            file_hash=document.file_hash,
            file_size_bytes=document.file_size_bytes,
            status=document.status.value,
            page_count=document.page_count,
            error_message=document.error_message,
            message=message,
            extraction_method=document.extraction_method,
            ocr_processed=document.ocr_processed,
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
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> DocumentListResponse:
    """List documents with pagination.

    Args:
        repository: DocumentRepository (injected)
        limit: Maximum documents to return (1-1000, default 100)
        offset: Number of documents to skip (>= 0, default 0)

    Returns:
        DocumentListResponse with documents and pagination info
    """
    documents = await repository.list_documents(limit=limit, offset=offset)
    total = await repository.count()

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
        total=total,
        limit=limit,
        offset=offset,
    )
