"""Storage module for database models and async operations.

Exports:
- Base: SQLAlchemy declarative base
- Document, DocumentStatus, Borrower, IncomeRecord, AccountNumber, SourceReference: ORM models
- engine, async_session_factory: Database connection components
- get_db_session, DBSession: FastAPI dependency injection
- DocumentRepository: Repository for Document CRUD operations
"""

from src.storage.database import DBSession, async_session_factory, engine, get_db_session
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
    # Base
    "Base",
    # Models
    "Document",
    "DocumentStatus",
    "Borrower",
    "IncomeRecord",
    "AccountNumber",
    "SourceReference",
    # Database
    "engine",
    "async_session_factory",
    "get_db_session",
    "DBSession",
    # Repositories
    "DocumentRepository",
]
