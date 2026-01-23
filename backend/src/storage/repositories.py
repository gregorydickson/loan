"""Repository pattern for async database operations.

Provides clean separation between business logic and database access
with async-first design for FastAPI integration.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.models import Document, DocumentStatus


class DocumentRepository:
    """Repository for Document database operations.

    Provides async CRUD operations with proper session management.
    Uses flush() to get generated values without committing (caller controls transaction).
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with async session.

        Args:
            session: SQLAlchemy async session for database operations
        """
        self.session = session

    async def create(self, document: Document) -> Document:
        """Create a new document record.

        Args:
            document: Document instance to persist

        Returns:
            The persisted document with any database-generated values (id, created_at)
        """
        self.session.add(document)
        await self.session.flush()
        await self.session.refresh(document)
        return document

    async def get_by_id(self, document_id: UUID) -> Document | None:
        """Get document by ID.

        Args:
            document_id: UUID of the document to retrieve

        Returns:
            Document if found, None otherwise
        """
        result = await self.session.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()

    async def get_by_hash(self, file_hash: str) -> Document | None:
        """Get document by file hash (for duplicate detection).

        Args:
            file_hash: SHA-256 hash of file content

        Returns:
            Document if found, None otherwise
        """
        result = await self.session.execute(
            select(Document).where(Document.file_hash == file_hash)
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        document_id: UUID,
        status: DocumentStatus,
        error_message: str | None = None,
        page_count: int | None = None,
    ) -> Document | None:
        """Update document processing status.

        Args:
            document_id: UUID of the document to update
            status: New status value
            error_message: Error message if status is FAILED
            page_count: Number of pages if known

        Returns:
            Updated document if found, None otherwise
        """
        document = await self.get_by_id(document_id)
        if document:
            document.status = status
            document.error_message = error_message
            if page_count is not None:
                document.page_count = page_count
            if status == DocumentStatus.COMPLETED:
                document.processed_at = datetime.now(UTC)
            await self.session.flush()
        return document

    async def list_documents(
        self, limit: int = 100, offset: int = 0
    ) -> Sequence[Document]:
        """List documents with pagination.

        Args:
            limit: Maximum number of documents to return
            offset: Number of documents to skip

        Returns:
            Sequence of documents ordered by created_at descending
        """
        result = await self.session.execute(
            select(Document)
            .order_by(Document.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()

    async def list_pending(self, limit: int = 100) -> Sequence[Document]:
        """List documents pending processing.

        Args:
            limit: Maximum number of documents to return

        Returns:
            Sequence of pending documents ordered by created_at ascending (FIFO)
        """
        result = await self.session.execute(
            select(Document)
            .where(Document.status == DocumentStatus.PENDING)
            .order_by(Document.created_at.asc())
            .limit(limit)
        )
        return result.scalars().all()
