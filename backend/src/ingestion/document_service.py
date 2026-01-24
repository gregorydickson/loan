"""Document service orchestrating upload and extraction flow.

Handles:
- File validation (type, size)
- File hash computation for duplicate detection
- GCS upload
- Database record creation
- Docling document processing (synchronous)
- Borrower extraction via LLM
- Borrower persistence with source attribution
"""

from __future__ import annotations

import hashlib
import logging
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

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

    Upload workflow:
    1. Validate file (type, size)
    2. Compute file hash (SHA-256)
    3. Check for duplicate (reject if exists)
    4. Create database record (PENDING status)
    5. Upload to GCS
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
    ) -> None:
        """Initialize DocumentService.

        Args:
            repository: DocumentRepository for document database operations
            gcs_client: GCSClient for file storage
            docling_processor: DoclingProcessor for document processing
            borrower_extractor: BorrowerExtractor for LLM-based extraction
            borrower_repository: BorrowerRepository for persisting borrowers
        """
        self.repository = repository
        self.gcs_client = gcs_client
        self.docling_processor = docling_processor
        self.borrower_extractor = borrower_extractor
        self.borrower_repository = borrower_repository

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
    ) -> Document:
        """Upload a document: validate, hash check, store in GCS, process with Docling.

        Args:
            filename: Original filename
            content: File content as bytes
            content_type: MIME type of the file

        Returns:
            Document record with status=COMPLETED or FAILED

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

        # 7. Process document with Docling (synchronous)
        try:
            result = self.docling_processor.process_bytes(content, filename)
            await self.update_processing_result(
                document_id,
                success=True,
                page_count=result.page_count,
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
