"""Repository pattern for async database operations.

Provides clean separation between business logic and database access
with async-first design for FastAPI integration.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.storage.models import (
    AccountNumber,
    Borrower,
    Document,
    DocumentStatus,
    IncomeRecord,
    SourceReference,
)


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

    async def count(self) -> int:
        """Get total count of documents in database.

        Returns:
            Total number of documents
        """
        result = await self.session.execute(select(func.count()).select_from(Document))
        return result.scalar_one()

    async def delete(self, document_id: UUID) -> bool:
        """Delete a document by ID.

        Also deletes associated borrowers via cascade (source_references FK).

        Args:
            document_id: UUID of the document to delete

        Returns:
            True if document was deleted, False if not found
        """
        document = await self.get_by_id(document_id)
        if not document:
            return False

        # Delete associated borrowers first (via their source references)
        # Find borrowers that only reference this document
        borrowers_result = await self.session.execute(
            select(SourceReference.borrower_id)
            .where(SourceReference.document_id == document_id)
            .distinct()
        )
        borrower_ids = [row[0] for row in borrowers_result.fetchall()]

        # Delete borrowers (cascade will handle income_records, account_numbers, source_references)
        if borrower_ids:
            for borrower_id in borrower_ids:
                with self.session.no_autoflush:
                    borrower = await self.session.get(Borrower, borrower_id)
                if borrower:
                    await self.session.delete(borrower)

        # Delete the document
        await self.session.delete(document)
        await self.session.flush()
        return True


class BorrowerRepository:
    """Repository for Borrower database operations.

    Provides async CRUD operations with eager loading of relationships
    (income_records, account_numbers, source_references).
    Uses flush() to get generated values without committing (caller controls transaction).
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with async session.

        Args:
            session: SQLAlchemy async session for database operations
        """
        self.session = session

    async def create(
        self,
        borrower: Borrower,
        income_records: list[IncomeRecord],
        account_numbers: list[AccountNumber],
        source_references: list[SourceReference],
    ) -> Borrower:
        """Create a borrower with all related entities.

        Args:
            borrower: Borrower instance to persist
            income_records: List of income records to associate
            account_numbers: List of account numbers to associate
            source_references: List of source references to associate

        Returns:
            The persisted borrower with all relationships
        """
        self.session.add(borrower)
        await self.session.flush()

        # Set borrower_id on all related entities and add them
        for income in income_records:
            income.borrower_id = borrower.id
            self.session.add(income)

        for account in account_numbers:
            account.borrower_id = borrower.id
            self.session.add(account)

        for source in source_references:
            source.borrower_id = borrower.id
            self.session.add(source)

        await self.session.flush()
        await self.session.refresh(borrower)
        return borrower

    async def get_by_id(self, borrower_id: UUID) -> Borrower | None:
        """Get borrower by ID with all relationships eagerly loaded.

        Args:
            borrower_id: UUID of the borrower to retrieve

        Returns:
            Borrower if found, None otherwise
        """
        result = await self.session.execute(
            select(Borrower)
            .where(Borrower.id == borrower_id)
            .options(
                selectinload(Borrower.income_records),
                selectinload(Borrower.account_numbers),
                selectinload(Borrower.source_references).selectinload(
                    SourceReference.document
                ),
            )
        )
        return result.scalar_one_or_none()

    async def search_by_name(
        self, name: str, limit: int = 100, offset: int = 0
    ) -> Sequence[Borrower]:
        """Search borrowers by name (case-insensitive partial match).

        Args:
            name: Name or partial name to search for
            limit: Maximum number of borrowers to return
            offset: Number of borrowers to skip

        Returns:
            Sequence of matching borrowers ordered by name
        """
        result = await self.session.execute(
            select(Borrower)
            .where(Borrower.name.ilike(f"%{name}%"))
            .options(selectinload(Borrower.income_records))
            .order_by(Borrower.name)
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()

    async def search_by_account(
        self, account_number: str, limit: int = 100, offset: int = 0
    ) -> Sequence[Borrower]:
        """Search borrowers by account number (case-insensitive partial match).

        Args:
            account_number: Account number or partial to search for
            limit: Maximum number of borrowers to return
            offset: Number of borrowers to skip

        Returns:
            Sequence of matching borrowers with income_records and account_numbers loaded
        """
        result = await self.session.execute(
            select(Borrower)
            .join(AccountNumber)
            .where(AccountNumber.number.ilike(f"%{account_number}%"))
            .options(
                selectinload(Borrower.income_records),
                selectinload(Borrower.account_numbers),
            )
            .order_by(Borrower.name)
            .offset(offset)
            .limit(limit)
        )
        return result.unique().scalars().all()

    async def list_borrowers(
        self, limit: int = 100, offset: int = 0
    ) -> Sequence[Borrower]:
        """List borrowers with pagination.

        Args:
            limit: Maximum number of borrowers to return
            offset: Number of borrowers to skip

        Returns:
            Sequence of borrowers ordered by created_at descending
        """
        result = await self.session.execute(
            select(Borrower)
            .options(selectinload(Borrower.income_records))
            .order_by(Borrower.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()

    async def count(self) -> int:
        """Count total number of borrowers.

        Returns:
            Total count of borrowers in database
        """
        result = await self.session.execute(
            select(func.count()).select_from(Borrower)
        )
        return result.scalar() or 0
