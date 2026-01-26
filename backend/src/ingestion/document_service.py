"""Document service orchestrating upload and extraction flow.

Handles:
- File validation (type, size)
- File hash computation for duplicate detection
- GCS upload
- Database record creation
- Docling document processing (synchronous)
- OCR routing (auto/force/skip via OCRRouter)
- Extraction routing (docling/langextract/auto via ExtractionRouter)
- Borrower extraction via LLM
- Borrower persistence with source attribution
"""

from __future__ import annotations

import hashlib
import logging
from decimal import Decimal
from typing import TYPE_CHECKING, Literal
from uuid import UUID, uuid4

from src.ingestion.cloud_tasks_client import CloudTasksClient
from src.ingestion.docling_processor import DoclingProcessor, DocumentProcessingError
from src.models.borrower import BorrowerRecord
from src.storage.gcs_client import GCSClient
from src.storage.models import (
    AccountNumber,
    Borrower,
    Document,
    DocumentStatus,
    IncomeRecord as IncomeRecordModel,
    SourceReference as SourceReferenceModel,
)
from src.storage.repositories import BorrowerRepository, DocumentRepository

if TYPE_CHECKING:
    from src.extraction import BorrowerExtractor
    from src.extraction.extraction_router import ExtractionRouter
    from src.ocr.ocr_router import OCRRouter

logger = logging.getLogger(__name__)


class DuplicateDocumentError(Exception):
    """Raised when a duplicate document is detected via file hash."""

    def __init__(self, existing_id: UUID, file_hash: str):
        self.existing_id = existing_id
        self.file_hash = file_hash
        super().__init__(f"Duplicate document exists with ID: {existing_id}")


class DocumentUploadError(Exception):
    """Raised when document upload fails."""

    pass


class DocumentService:
    """Orchestrates document upload, processing, and extraction.

    Upload workflow (async mode - Cloud Tasks configured):
    1. Validate file (type, size)
    2. Compute file hash (SHA-256)
    3. Check for duplicate (reject if exists)
    4. Create database record (PENDING status)
    5. Upload to GCS
    6. Queue Cloud Task for processing
    7. Return immediately with PENDING status

    Upload workflow (sync mode - local development):
    1-5. Same as async
    6. Process document with Docling
    7. Update status to COMPLETED/FAILED
    8. Extract borrowers via BorrowerExtractor
    9. Persist extracted borrowers with source references
    10. Return document with final status

    Note: Extraction failures are logged but don't fail the upload.
    A document with successful Docling processing is COMPLETED even
    if no borrowers were extracted.
    """

    # Mapping of MIME types to file type strings
    MIME_TYPE_MAP: dict[str, str] = {
        "application/pdf": "pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
    }

    ALLOWED_MIME_TYPES: set[str] = set(MIME_TYPE_MAP.keys())

    # Maximum file size: 50MB
    MAX_FILE_SIZE: int = 50 * 1024 * 1024

    def __init__(
        self,
        repository: DocumentRepository,
        gcs_client: GCSClient,
        docling_processor: DoclingProcessor,
        borrower_extractor: BorrowerExtractor,
        borrower_repository: BorrowerRepository,
        cloud_tasks_client: CloudTasksClient | None = None,
        ocr_router: OCRRouter | None = None,
        extraction_router: ExtractionRouter | None = None,
    ) -> None:
        """Initialize DocumentService.

        Args:
            repository: DocumentRepository for document database operations
            gcs_client: GCSClient for file storage
            docling_processor: DoclingProcessor for document processing
            borrower_extractor: BorrowerExtractor for LLM-based extraction
            borrower_repository: BorrowerRepository for persisting borrowers
            cloud_tasks_client: CloudTasksClient for async task queueing (None for sync mode)
            ocr_router: OCRRouter for OCR routing (Phase 14-15, None for legacy mode)
            extraction_router: ExtractionRouter for dual pipeline routing (Phase 12-15)
        """
        self.repository = repository
        self.gcs_client = gcs_client
        self.docling_processor = docling_processor
        self.borrower_extractor = borrower_extractor
        self.borrower_repository = borrower_repository
        self.cloud_tasks_client = cloud_tasks_client
        self.ocr_router = ocr_router
        self.extraction_router = extraction_router

    @staticmethod
    def compute_file_hash(content: bytes) -> str:
        """Compute SHA-256 hash of file content.

        Args:
            content: File content as bytes

        Returns:
            Hex string of SHA-256 hash
        """
        return hashlib.sha256(content).hexdigest()

    def validate_file(
        self,
        content: bytes,
        content_type: str | None,
        filename: str,
    ) -> tuple[str, str]:
        """Validate uploaded file.

        Args:
            content: File content
            content_type: MIME type from upload
            filename: Original filename

        Returns:
            Tuple of (validated_content_type, file_type)

        Raises:
            ValueError: If file is invalid
        """
        # Check file size
        if len(content) > self.MAX_FILE_SIZE:
            max_mb = self.MAX_FILE_SIZE // (1024 * 1024)
            raise ValueError(f"File too large. Maximum size is {max_mb}MB")

        # Check content type
        if not content_type:
            # Try to infer from filename
            ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
            ext_to_mime = {
                "pdf": "application/pdf",
                "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "png": "image/png",
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
            }
            content_type = ext_to_mime.get(ext, "")

        if content_type not in self.ALLOWED_MIME_TYPES:
            allowed = ", ".join(sorted(self.ALLOWED_MIME_TYPES))
            raise ValueError(f"Unsupported file type: {content_type}. Allowed: {allowed}")

        file_type = self.MIME_TYPE_MAP[content_type]
        return content_type, file_type

    async def upload(
        self,
        filename: str,
        content: bytes,
        content_type: str | None = None,
        extraction_method: str = "docling",
        ocr_mode: str = "auto",
    ) -> Document:
        """Upload a document: validate, hash check, store in GCS, queue/process.

        In async mode (cloud_tasks_client configured):
            Queues Cloud Task and returns immediately with PENDING status.

        In sync mode (cloud_tasks_client is None):
            Processes document with OCRRouter then extracts borrowers before returning.

        Args:
            filename: Original filename
            content: File content as bytes
            content_type: MIME type of the file
            extraction_method: Extraction method (docling/langextract/auto). Default 'docling'.
            ocr_mode: OCR mode (auto/force/skip). Default 'auto'.

        Returns:
            Document record with status:
            - PENDING (async mode, queued successfully)
            - COMPLETED (sync mode, processing succeeded)
            - FAILED (task queueing failed OR sync processing failed)

        Raises:
            DuplicateDocumentError: If file with same hash exists
            ValueError: If file is invalid
            DocumentUploadError: If GCS upload fails
        """
        # 1. Validate file
        content_type, file_type = self.validate_file(content, content_type, filename)

        # 2. Compute hash for duplicate detection
        file_hash = self.compute_file_hash(content)

        # 3. Check for existing document with same hash
        existing = await self.repository.get_by_hash(file_hash)
        if existing:
            raise DuplicateDocumentError(existing.id, file_hash)

        # 4. Create document record with PENDING status
        document_id = uuid4()
        document = Document(
            id=document_id,
            filename=filename,
            file_hash=file_hash,
            file_type=file_type,
            file_size_bytes=len(content),
            status=DocumentStatus.PENDING,
            extraction_method=extraction_method,  # Track selected method at upload time
        )
        document = await self.repository.create(document)

        # 5. Upload to GCS
        try:
            gcs_path = f"documents/{document_id}/{filename}"
            gcs_uri = self.gcs_client.upload(content, gcs_path, content_type)

            # 6. Update document with GCS URI
            document.gcs_uri = gcs_uri
            await self.repository.session.flush()

        except Exception as e:
            # Mark as failed if GCS upload fails
            await self.repository.update_status(
                document_id,
                DocumentStatus.FAILED,
                error_message=f"GCS upload failed: {e}",
            )
            raise DocumentUploadError(f"Failed to upload to storage: {e}") from e

        # 7. Queue for async processing OR process synchronously
        if self.cloud_tasks_client is not None:
            # Async mode: Queue Cloud Task and return immediately
            try:
                self.cloud_tasks_client.create_document_processing_task(
                    document_id=document_id,
                    filename=filename,
                    extraction_method=extraction_method,
                    ocr_mode=ocr_mode,
                )
                logger.info(
                    "Queued document %s for async processing (method=%s, ocr=%s)",
                    document_id,
                    extraction_method,
                    ocr_mode,
                )
            except Exception as e:
                logger.error("Failed to queue task for document %s: %s", document_id, e)
                # Mark as failed if we can't queue
                await self.repository.update_status(
                    document_id,
                    DocumentStatus.FAILED,
                    error_message=f"Failed to queue processing: {e}",
                )
                # Refresh and return the failed document
                refreshed = await self.repository.get_by_id(document_id)
                if refreshed is not None:
                    document = refreshed

            # Return immediately with PENDING status
            return document

        # Sync mode: Process immediately (for local development)
        # DUAL-04: OCRRouter runs BEFORE extraction when ocr != "skip"
        ocr_processed = False
        try:
            # Step 1: OCR routing if needed
            if self.ocr_router and ocr_mode != "skip":
                # Validate and cast to OCRMode literal type for type safety
                valid_modes: tuple[Literal["auto", "force", "skip"], ...] = (
                    "auto",
                    "force",
                    "skip",
                )
                ocr_mode_literal: Literal["auto", "force", "skip"] = (
                    ocr_mode  # type: ignore[assignment]
                    if ocr_mode in valid_modes
                    else "auto"
                )
                ocr_result = await self.ocr_router.process(
                    pdf_bytes=content,
                    filename=filename,
                    mode=ocr_mode_literal,
                )
                result = ocr_result.content
                ocr_processed = ocr_result.ocr_method != "none"
                logger.info(
                    "OCR routing for %s: method=%s, ocr_processed=%s",
                    document_id,
                    ocr_result.ocr_method,
                    ocr_processed,
                )
            else:
                # Skip OCR - use Docling directly
                result = self.docling_processor.process_bytes(content, filename)

            await self.update_processing_result(
                document_id,
                success=True,
                page_count=result.page_count,
            )

            # Update document with OCR status
            document.ocr_processed = ocr_processed
            await self.repository.session.flush()

            # Step 2: Extract borrowers using ExtractionRouter or BorrowerExtractor
            try:
                if self.extraction_router and extraction_method != "docling":
                    # Use ExtractionRouter for langextract/auto methods
                    extraction_result = self.extraction_router.extract(
                        document=result,
                        document_id=document_id,
                        document_name=filename,
                        method=extraction_method,  # type: ignore[arg-type]
                    )
                    logger.info(
                        "Extraction via router for %s: method=%s",
                        document_id,
                        extraction_method,
                    )
                else:
                    # Original behavior - use direct BorrowerExtractor
                    extraction_result = self.borrower_extractor.extract(
                        document=result,
                        document_id=document_id,
                        document_name=filename,
                    )

                # Persist extracted borrowers
                # Collect errors - if ANY borrower fails, the whole document should fail
                persistence_errors = []
                for borrower_record in extraction_result.borrowers:
                    try:
                        await self._persist_borrower(borrower_record, document_id)
                        logger.info(
                            "Persisted borrower '%s' from document %s",
                            borrower_record.name,
                            document_id,
                        )
                    except Exception as e:
                        error_msg = f"Failed to persist borrower '{borrower_record.name}': {e}"
                        logger.error(error_msg)
                        persistence_errors.append(error_msg)

                # If any borrower failed to persist, fail the entire document
                # Raise BEFORE logging success so it's caught by outer handler
                if persistence_errors:
                    error_summary = "; ".join(persistence_errors)
                    # Don't update status to COMPLETED - let outer handler mark as FAILED
                    raise ValueError(f"Borrower persistence failed: {error_summary}")

                # Log extraction summary - handle both ExtractionResult and LangExtractResult
                borrower_count = len(extraction_result.borrowers)
                # LangExtractResult has alignment_warnings, ExtractionResult has validation_errors
                warnings_count = len(
                    getattr(extraction_result, "validation_errors", [])
                    or getattr(extraction_result, "alignment_warnings", [])
                )
                consistency_count = len(getattr(extraction_result, "consistency_warnings", []))
                logger.info(
                    "Extraction complete for document %s: %d borrowers, "
                    "%d validation/alignment warnings, %d consistency warnings",
                    document_id,
                    borrower_count,
                    warnings_count,
                    consistency_count,
                )

            except ValueError as e:
                # Persistence failure - mark document as FAILED
                if "persistence failed" in str(e).lower():
                    await self.update_processing_result(
                        document_id,
                        success=False,
                        error_message=str(e),
                    )
                    # Refresh and return failed document
                    refreshed = await self.repository.get_by_id(document_id)
                    if refreshed is not None:
                        document = refreshed
                    return document
                # Other ValueErrors fall through to generic handler
                raise

            except Exception as e:
                # Extraction failure should not fail the document - log and continue
                # Document is COMPLETED (Docling worked), extraction just didn't find borrowers
                logger.warning(
                    "Extraction failed for document %s: %s. "
                    "Document marked completed anyway.",
                    document_id,
                    str(e),
                )

            # Refresh document to get updated status
            refreshed = await self.repository.get_by_id(document_id)
            if refreshed is not None:
                document = refreshed
        except DocumentProcessingError as e:
            await self.update_processing_result(
                document_id,
                success=False,
                error_message=f"Document processing failed: {e.message}",
            )
            # Refresh document to get updated status
            refreshed = await self.repository.get_by_id(document_id)
            if refreshed is not None:
                document = refreshed

        return document

    async def get_document(self, document_id: UUID) -> Document | None:
        """Get document by ID.

        Args:
            document_id: Document UUID

        Returns:
            Document if found, None otherwise
        """
        return await self.repository.get_by_id(document_id)

    async def update_processing_result(
        self,
        document_id: UUID,
        success: bool,
        page_count: int | None = None,
        error_message: str | None = None,
    ) -> Document | None:
        """Update document after processing completes.

        Called by Cloud Tasks handler in Phase 3.

        Args:
            document_id: Document UUID
            success: Whether processing succeeded
            page_count: Number of pages (if successful)
            error_message: Error message (if failed)

        Returns:
            Updated document
        """
        status = DocumentStatus.COMPLETED if success else DocumentStatus.FAILED
        return await self.repository.update_status(
            document_id,
            status,
            error_message=error_message,
            page_count=page_count,
        )

    async def _persist_borrower(
        self,
        record: BorrowerRecord,
        document_id: UUID,
    ) -> Borrower:
        """Convert Pydantic BorrowerRecord to SQLAlchemy Borrower and persist.

        Args:
            record: Extracted borrower data from BorrowerExtractor
            document_id: Source document UUID for reference

        Returns:
            Persisted Borrower with all relationships
        """
        # Hash SSN for storage (never store raw SSN - PII protection)
        ssn_hash = None
        if record.ssn:
            ssn_hash = hashlib.sha256(record.ssn.encode()).hexdigest()

        # Convert address to JSON string
        address_json = None
        if record.address:
            address_json = record.address.model_dump_json()

        # Create SQLAlchemy Borrower model
        borrower = Borrower(
            id=record.id,
            name=record.name,
            ssn_hash=ssn_hash,
            address_json=address_json,
            confidence_score=Decimal(str(record.confidence_score)),
        )

        # Convert income records
        income_records = [
            IncomeRecordModel(
                amount=income.amount,
                period=income.period,
                year=income.year,
                source_type=income.source_type,
                employer=income.employer,
            )
            for income in record.income_history
        ]

        # Convert account numbers (both bank accounts and loan numbers)
        account_numbers = [
            AccountNumber(number=acct, account_type="bank")
            for acct in record.account_numbers
        ] + [
            AccountNumber(number=loan, account_type="loan")
            for loan in record.loan_numbers
        ]

        # Convert source references
        source_references = [
            SourceReferenceModel(
                document_id=src.document_id,
                page_number=src.page_number,
                section=src.section,
                snippet=src.snippet,
            )
            for src in record.sources
        ]

        # Persist via repository (handles transaction)
        return await self.borrower_repository.create(
            borrower=borrower,
            income_records=income_records,
            account_numbers=account_numbers,
            source_references=source_references,
        )
