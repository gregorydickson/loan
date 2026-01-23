"""FastAPI dependencies for service injection."""

from typing import Annotated

from fastapi import Depends

from src.config import settings
from src.ingestion.document_service import DocumentService
from src.storage.database import DBSession
from src.storage.gcs_client import GCSClient
from src.storage.repositories import DocumentRepository

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


def get_document_repository(session: DBSession) -> DocumentRepository:
    """Get document repository with session."""
    return DocumentRepository(session)


DocumentRepoDep = Annotated[DocumentRepository, Depends(get_document_repository)]


def get_document_service(
    repository: DocumentRepoDep,
    gcs_client: GCSClientDep,
) -> DocumentService:
    """Get document service with dependencies."""
    return DocumentService(
        repository=repository,
        gcs_client=gcs_client,
    )


DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]
