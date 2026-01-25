"""Cloud Tasks handler endpoints.

Receives callbacks from Cloud Tasks for async document processing.
Cloud Run validates OIDC tokens automatically via IAM.
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from src.api.dependencies import (
    BorrowerExtractorDep,
    BorrowerRepoDep,
    DoclingProcessorDep,
    DocumentRepoDep,
    ExtractionRouterDep,
    GCSClientDep,
    OCRRouterDep,
)
from src.storage.models import DocumentStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

# Maximum retry attempts (0-indexed, so 4 = 5 total attempts)
MAX_RETRY_COUNT = 4


class ProcessDocumentRequest(BaseModel):
    """Request payload from Cloud Tasks.

    Fields method/ocr have defaults for backward compatibility with
    tasks queued before Phase 15.
    """

    document_id: UUID = Field(..., description="Document UUID to process")
    filename: str = Field(..., description="Original filename")
    method: str = Field(
        default="docling",
        description="Extraction method: docling|langextract|auto. Default 'docling' for backward compat.",
    )
    ocr: str = Field(
        default="auto",
        description="OCR mode: auto|force|skip. Default 'auto'.",
    )


class ProcessDocumentResponse(BaseModel):
    """Response for task processing."""

    status: str = Field(..., description="Processing result: completed, failed, or retrying")
    error: str | None = Field(default=None, description="Error message if failed")


@router.post(
    "/process-document",
    response_model=ProcessDocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Process document (Cloud Tasks handler)",
    description="""Handle document processing task from Cloud Tasks.

Cloud Run validates OIDC token automatically via IAM.
Returns 2xx for success, 5xx triggers Cloud Tasks retry.
After max retries, marks document as FAILED and returns 200.""",
)
async def process_document(
    request: Request,
    payload: ProcessDocumentRequest,
    document_repo: DocumentRepoDep,
    docling_processor: DoclingProcessorDep,
    borrower_extractor: BorrowerExtractorDep,
    borrower_repo: BorrowerRepoDep,
    gcs_client: GCSClientDep,
    ocr_router: OCRRouterDep,
    extraction_router: ExtractionRouterDep,
) -> ProcessDocumentResponse:
    """Process a document from Cloud Tasks callback.

    DUAL-04: OCRRouter processes documents before extraction when ocr != "skip"
    DUAL-05: ExtractionRouter routes to correct extraction method

    Args:
        request: FastAPI request (for headers)
        payload: Task payload with document_id, filename, method, ocr
        document_repo: Document repository
        docling_processor: Docling processor for text extraction
        borrower_extractor: LLM extractor for borrower data
        borrower_repo: Borrower repository for persistence
        gcs_client: GCS client for file download
        ocr_router: OCRRouter for OCR routing (None if not configured)
        extraction_router: ExtractionRouter for dual pipeline routing

    Returns:
        ProcessDocumentResponse with status

    Raises:
        HTTPException 503: On transient errors (triggers retry)
    """
    # Extract Cloud Tasks metadata from headers
    task_name = request.headers.get("X-CloudTasks-TaskName", "unknown")
    retry_count = int(request.headers.get("X-CloudTasks-TaskRetryCount", "0"))

    logger.info(
        "Processing document task: document_id=%s, task=%s, retry=%d",
        payload.document_id,
        task_name,
        retry_count,
    )

    # Get document from database
    document = await document_repo.get_by_id(payload.document_id)
    if document is None:
        logger.error("Document not found: %s", payload.document_id)
        # Return 200 - no point retrying if document doesn't exist
        return ProcessDocumentResponse(
            status="failed",
            error=f"Document not found: {payload.document_id}",
        )

    # Skip if already processed (idempotency)
    if document.status in (DocumentStatus.COMPLETED, DocumentStatus.FAILED):
        logger.info(
            "Document %s already processed (status=%s), skipping",
            payload.document_id,
            document.status.value,
        )
        return ProcessDocumentResponse(status=document.status.value)

    # Update status to PROCESSING
    await document_repo.update_status(
        payload.document_id,
        DocumentStatus.PROCESSING,
    )

    try:
        # Download document content from GCS
        if not document.gcs_uri:
            raise ValueError("Document has no GCS URI")

        # Extract path from gs:// URI
        gcs_path = document.gcs_uri.replace(f"gs://{gcs_client.bucket_name}/", "")
        content = gcs_client.download(gcs_path)

        from src.ingestion.docling_processor import DocumentProcessingError

        # Step 1: OCR routing based on payload.ocr mode (DUAL-04)
        ocr_processed = False
        if ocr_router and payload.ocr != "skip":
            ocr_result = await ocr_router.process(
                pdf_bytes=content,
                filename=payload.filename,
                mode=payload.ocr,  # type: ignore[arg-type]
            )
            result = ocr_result.content
            ocr_processed = ocr_result.ocr_method != "none"
            logger.info(
                "OCR routing for %s: method=%s, ocr_processed=%s",
                payload.document_id,
                ocr_result.ocr_method,
                ocr_processed,
            )
        else:
            # Skip OCR - use Docling directly
            result = docling_processor.process_bytes(content, payload.filename)

        # Update page count and ocr_processed status
        await document_repo.update_status(
            payload.document_id,
            DocumentStatus.PROCESSING,  # Still processing during extraction
            page_count=result.page_count,
        )

        # Update document ocr_processed field
        document.ocr_processed = ocr_processed
        await document_repo.session.flush()

        # Step 2: Extraction routing based on payload.method (DUAL-05)
        if extraction_router and payload.method != "docling":
            # Use ExtractionRouter for langextract/auto methods
            extraction_result = extraction_router.extract(
                document=result,
                document_id=payload.document_id,
                document_name=payload.filename,
                method=payload.method,  # type: ignore[arg-type]
            )
            logger.info(
                "Extraction via router for %s: method=%s",
                payload.document_id,
                payload.method,
            )
        else:
            # Use BorrowerExtractor directly for docling method
            extraction_result = borrower_extractor.extract(
                document=result,
                document_id=payload.document_id,
                document_name=payload.filename,
            )

        # Persist extracted borrowers
        from src.ingestion.document_service import DocumentService

        # Create temporary service for persistence helper
        # (This is a bit awkward but avoids duplicating persistence logic)
        temp_service = DocumentService.__new__(DocumentService)
        temp_service.borrower_repository = borrower_repo

        for borrower_record in extraction_result.borrowers:
            try:
                await temp_service._persist_borrower(borrower_record, payload.document_id)
                logger.info(
                    "Persisted borrower '%s' from document %s",
                    borrower_record.name,
                    payload.document_id,
                )
            except Exception as e:
                logger.warning(
                    "Failed to persist borrower '%s': %s",
                    borrower_record.name,
                    str(e),
                )

        # Mark as completed
        await document_repo.update_status(
            payload.document_id,
            DocumentStatus.COMPLETED,
            page_count=result.page_count,
        )

        logger.info(
            "Document %s processed successfully: %d borrowers extracted (method=%s, ocr=%s)",
            payload.document_id,
            len(extraction_result.borrowers),
            payload.method,
            payload.ocr,
        )

        return ProcessDocumentResponse(status="completed")

    except DocumentProcessingError as e:
        # Docling processing failed - permanent error, don't retry
        error_msg = f"Document processing failed: {e.message}"
        await document_repo.update_status(
            payload.document_id,
            DocumentStatus.FAILED,
            error_message=error_msg,
        )
        logger.error("Docling processing failed for %s: %s", payload.document_id, e.message)
        return ProcessDocumentResponse(status="failed", error=error_msg)

    except Exception as e:
        error_msg = str(e)
        logger.error(
            "Task failed for document %s (retry %d): %s",
            payload.document_id,
            retry_count,
            error_msg,
        )

        # Check if this is the final retry
        if retry_count >= MAX_RETRY_COUNT:
            # Final retry exhausted - mark as failed
            await document_repo.update_status(
                payload.document_id,
                DocumentStatus.FAILED,
                error_message=f"Processing failed after {retry_count + 1} attempts: {error_msg}",
            )
            return ProcessDocumentResponse(
                status="failed",
                error=f"Max retries exhausted: {error_msg}",
            )

        # Return 503 to trigger Cloud Tasks retry
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Processing failed (attempt {retry_count + 1}): {error_msg}",
        ) from e
