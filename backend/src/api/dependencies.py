"""FastAPI dependencies for service injection."""

from typing import Annotated

from fastapi import Depends

from src.api.errors import EntityNotFoundError
from src.config import settings
from src.extraction import (
    BorrowerDeduplicator,
    BorrowerExtractor,
    ComplexityClassifier,
    ConfidenceCalculator,
    ConsistencyValidator,
    DocumentChunker,
    FieldValidator,
    GeminiClient,
)
from src.extraction.extraction_router import ExtractionRouter
from src.extraction.langextract_processor import LangExtractProcessor
from src.ingestion.cloud_tasks_client import CloudTasksClient
from src.ingestion.docling_processor import DoclingProcessor
from src.ingestion.document_service import DocumentService
from src.ocr.lightonocr_client import LightOnOCRClient
from src.ocr.ocr_router import OCRRouter
from src.storage.database import DBSession
from src.storage.gcs_client import GCSClient
from src.storage.repositories import BorrowerRepository, DocumentRepository

# GCS Client dependency
_gcs_client: GCSClient | None = None


def get_gcs_client() -> GCSClient:
    """Get or create GCS client singleton.

    Returns:
        GCSClient instance

    Note:
        Returns a mock client if GCS bucket is not configured.
        This allows running locally without GCS.
    """
    global _gcs_client

    if _gcs_client is None:
        bucket_name = settings.gcs_bucket
        if not bucket_name:
            # For local development without GCS, use a mock
            from unittest.mock import MagicMock
            _gcs_client = MagicMock(spec=GCSClient)
            _gcs_client.upload = MagicMock(return_value="gs://mock-bucket/mock-path")
            _gcs_client.download = MagicMock(return_value=b"mock content")
            _gcs_client.exists = MagicMock(return_value=True)
        else:
            _gcs_client = GCSClient(bucket_name)

    return _gcs_client


GCSClientDep = Annotated[GCSClient, Depends(get_gcs_client)]


# DoclingProcessor dependency
_docling_processor: DoclingProcessor | None = None


def get_docling_processor() -> DoclingProcessor:
    """Get or create DoclingProcessor singleton.

    Returns:
        DoclingProcessor instance
    """
    global _docling_processor

    if _docling_processor is None:
        # OCR disabled: RapidOCR model downloads fail in Cloud Run
        # For scanned documents, configure LIGHTONOCR_SERVICE_URL to use GPU OCR
        # Text-based PDFs (W2s, paystubs) work fine without OCR
        _docling_processor = DoclingProcessor(
            enable_ocr=False,
            enable_tables=True,
            max_pages=100,
        )

    return _docling_processor


DoclingProcessorDep = Annotated[DoclingProcessor, Depends(get_docling_processor)]


# BorrowerExtractor dependency
_borrower_extractor: BorrowerExtractor | None = None


def get_borrower_extractor() -> BorrowerExtractor:
    """Get or create BorrowerExtractor singleton with all components.

    Returns:
        BorrowerExtractor instance configured with:
        - GeminiClient for LLM extraction
        - ComplexityClassifier for model routing
        - DocumentChunker for large documents
        - FieldValidator for format validation
        - ConfidenceCalculator for scoring
        - BorrowerDeduplicator for merging duplicates
        - ConsistencyValidator for data quality checks
    """
    global _borrower_extractor

    if _borrower_extractor is None:
        _borrower_extractor = BorrowerExtractor(
            llm_client=GeminiClient(),
            classifier=ComplexityClassifier(),
            chunker=DocumentChunker(),
            validator=FieldValidator(),
            confidence_calc=ConfidenceCalculator(),
            deduplicator=BorrowerDeduplicator(),
            consistency_validator=ConsistencyValidator(),
        )

    return _borrower_extractor


BorrowerExtractorDep = Annotated[BorrowerExtractor, Depends(get_borrower_extractor)]


# CloudTasksClient dependency
_cloud_tasks_client: CloudTasksClient | None = None


def get_cloud_tasks_client() -> CloudTasksClient | None:
    """Get or create CloudTasksClient singleton.

    Returns:
        CloudTasksClient if configured, None for local development.

    Note:
        Returns None if Cloud Tasks settings are not configured.
        This allows running locally without Cloud Tasks.
    """
    global _cloud_tasks_client

    if _cloud_tasks_client is None:
        # Check if Cloud Tasks is configured
        if not settings.gcp_project_id or not settings.cloud_run_service_url:
            # Local development - no Cloud Tasks
            return None

        _cloud_tasks_client = CloudTasksClient(
            project_id=settings.gcp_project_id,
            location=settings.gcp_location,
            queue_id=settings.cloud_tasks_queue,
            service_url=settings.cloud_run_service_url,
            service_account_email=settings.cloud_run_service_account,
        )

    return _cloud_tasks_client


CloudTasksClientDep = Annotated[CloudTasksClient | None, Depends(get_cloud_tasks_client)]


# OCRRouter dependency (Phase 14-15)
_ocr_router: OCRRouter | None = None


def get_ocr_router(
    docling_processor: DoclingProcessorDep,
) -> OCRRouter | None:
    """Get or create OCRRouter singleton.

    Returns:
        OCRRouter if LightOnOCR service is configured, None otherwise.

    Note:
        Returns None if LIGHTONOCR_SERVICE_URL is not configured.
        This allows running locally without GPU OCR service.
    """
    global _ocr_router

    if _ocr_router is None:
        if not settings.lightonocr_service_url:
            # Local development - no GPU OCR service
            return None

        gpu_client = LightOnOCRClient(settings.lightonocr_service_url)
        _ocr_router = OCRRouter(
            gpu_client=gpu_client,
            docling_processor=docling_processor,
        )

    return _ocr_router


OCRRouterDep = Annotated[OCRRouter | None, Depends(get_ocr_router)]


# ExtractionRouter dependency (Phase 12-15)
_extraction_router: ExtractionRouter | None = None


def get_extraction_router(
    borrower_extractor: BorrowerExtractorDep,
) -> ExtractionRouter:
    """Get or create ExtractionRouter singleton.

    Returns:
        ExtractionRouter configured with LangExtract and Docling extractors.
    """
    global _extraction_router

    if _extraction_router is None:
        langextract_processor = LangExtractProcessor()
        _extraction_router = ExtractionRouter(
            langextract_processor=langextract_processor,
            docling_extractor=borrower_extractor,
        )

    return _extraction_router


ExtractionRouterDep = Annotated[ExtractionRouter, Depends(get_extraction_router)]


def get_document_repository(session: DBSession) -> DocumentRepository:
    """Get document repository with session."""
    return DocumentRepository(session)


DocumentRepoDep = Annotated[DocumentRepository, Depends(get_document_repository)]


def get_borrower_repository(session: DBSession) -> BorrowerRepository:
    """Get borrower repository with session."""
    return BorrowerRepository(session)


BorrowerRepoDep = Annotated[BorrowerRepository, Depends(get_borrower_repository)]


def get_document_service(
    repository: DocumentRepoDep,
    gcs_client: GCSClientDep,
    docling_processor: DoclingProcessorDep,
    borrower_extractor: BorrowerExtractorDep,
    borrower_repository: BorrowerRepoDep,
    cloud_tasks_client: CloudTasksClientDep,
    ocr_router: OCRRouterDep,
    extraction_router: ExtractionRouterDep,
) -> DocumentService:
    """Get document service with all dependencies."""
    return DocumentService(
        repository=repository,
        gcs_client=gcs_client,
        docling_processor=docling_processor,
        borrower_extractor=borrower_extractor,
        borrower_repository=borrower_repository,
        cloud_tasks_client=cloud_tasks_client,
        ocr_router=ocr_router,
        extraction_router=extraction_router,
    )


DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]

__all__ = [
    "DBSession",
    "GCSClientDep",
    "DoclingProcessorDep",
    "BorrowerExtractorDep",
    "DocumentRepoDep",
    "DocumentServiceDep",
    "BorrowerRepoDep",
    "CloudTasksClientDep",
    "OCRRouterDep",
    "ExtractionRouterDep",
    "EntityNotFoundError",
    "get_borrower_extractor",
    "get_borrower_repository",
    "get_cloud_tasks_client",
    "get_ocr_router",
    "get_extraction_router",
]
