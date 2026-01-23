"""Storage module for database and GCS operations."""

from src.storage.database import (
    DBSession,
    async_session_factory,
    engine,
    get_db_session,
)
from src.storage.gcs_client import GCSClient, GCSDownloadError, GCSError, GCSUploadError
from src.storage.models import (
    AccountNumber,
    Base,
    Borrower,
    Document,
    DocumentStatus,
    IncomeRecord,
    SourceReference,
)
from src.storage.repositories import DocumentRepository

__all__ = [
    # Database
    "Base",
    "Document",
    "DocumentStatus",
    "Borrower",
    "IncomeRecord",
    "AccountNumber",
    "SourceReference",
    "engine",
    "async_session_factory",
    "get_db_session",
    "DBSession",
    "DocumentRepository",
    # GCS
    "GCSClient",
    "GCSError",
    "GCSUploadError",
    "GCSDownloadError",
]
