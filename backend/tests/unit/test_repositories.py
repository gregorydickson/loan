"""Unit tests for DocumentRepository.

Uses SQLite in-memory with aiosqlite for fast, isolated testing.
Each test gets a fresh database with the schema created from ORM models.
"""

import pytest
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.storage.models import Base, Document, DocumentStatus
from src.storage.repositories import DocumentRepository


@pytest.fixture
async def async_engine():
    """Create async SQLite engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(async_engine):
    """Create async session for testing."""
    session_factory = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
def sample_document() -> Document:
    """Create a sample document for testing."""
    return Document(
        id=uuid4(),
        filename="test.pdf",
        file_hash="abc123def456",
        file_type="pdf",
        file_size_bytes=1024,
        status=DocumentStatus.PENDING,
    )


class TestDocumentRepository:
    """Tests for DocumentRepository."""

    async def test_create_document(self, session: AsyncSession, sample_document: Document):
        """Test creating a document."""
        repo = DocumentRepository(session)
        created = await repo.create(sample_document)

        assert created.id == sample_document.id
        assert created.filename == "test.pdf"
        assert created.status == DocumentStatus.PENDING
        assert created.created_at is not None

    async def test_get_by_id(self, session: AsyncSession, sample_document: Document):
        """Test retrieving document by ID."""
        repo = DocumentRepository(session)
        await repo.create(sample_document)

        found = await repo.get_by_id(sample_document.id)
        assert found is not None
        assert found.filename == "test.pdf"

    async def test_get_by_id_not_found(self, session: AsyncSession):
        """Test retrieving non-existent document."""
        repo = DocumentRepository(session)
        found = await repo.get_by_id(uuid4())
        assert found is None

    async def test_get_by_hash(self, session: AsyncSession, sample_document: Document):
        """Test retrieving document by file hash."""
        repo = DocumentRepository(session)
        await repo.create(sample_document)

        found = await repo.get_by_hash("abc123def456")
        assert found is not None
        assert found.id == sample_document.id

    async def test_get_by_hash_not_found(self, session: AsyncSession):
        """Test retrieving non-existent hash."""
        repo = DocumentRepository(session)
        found = await repo.get_by_hash("nonexistent")
        assert found is None

    async def test_update_status_to_processing(
        self, session: AsyncSession, sample_document: Document
    ):
        """Test updating document status to processing."""
        repo = DocumentRepository(session)
        await repo.create(sample_document)

        updated = await repo.update_status(
            sample_document.id,
            DocumentStatus.PROCESSING,
        )

        assert updated is not None
        assert updated.status == DocumentStatus.PROCESSING
        assert updated.processed_at is None  # Not set until completed

    async def test_update_status_to_completed(
        self, session: AsyncSession, sample_document: Document
    ):
        """Test updating document status to completed."""
        repo = DocumentRepository(session)
        await repo.create(sample_document)

        updated = await repo.update_status(
            sample_document.id,
            DocumentStatus.COMPLETED,
            page_count=5,
        )

        assert updated is not None
        assert updated.status == DocumentStatus.COMPLETED
        assert updated.page_count == 5
        assert updated.processed_at is not None

    async def test_update_status_to_failed(
        self, session: AsyncSession, sample_document: Document
    ):
        """Test updating document status to failed with error."""
        repo = DocumentRepository(session)
        await repo.create(sample_document)

        updated = await repo.update_status(
            sample_document.id,
            DocumentStatus.FAILED,
            error_message="OCR failed",
        )

        assert updated is not None
        assert updated.status == DocumentStatus.FAILED
        assert updated.error_message == "OCR failed"

    async def test_update_status_not_found(self, session: AsyncSession):
        """Test updating non-existent document."""
        repo = DocumentRepository(session)
        updated = await repo.update_status(
            uuid4(),
            DocumentStatus.COMPLETED,
        )
        assert updated is None

    async def test_list_documents_pagination(self, session: AsyncSession):
        """Test listing documents with pagination."""
        repo = DocumentRepository(session)

        # Create 5 documents
        for i in range(5):
            doc = Document(
                id=uuid4(),
                filename=f"doc{i}.pdf",
                file_hash=f"hash{i}",
                file_type="pdf",
                file_size_bytes=1000 + i,
                status=DocumentStatus.PENDING,
            )
            await repo.create(doc)

        # Get first page
        page1 = await repo.list_documents(limit=2, offset=0)
        assert len(page1) == 2

        # Get second page
        page2 = await repo.list_documents(limit=2, offset=2)
        assert len(page2) == 2

        # Get third page (partial)
        page3 = await repo.list_documents(limit=2, offset=4)
        assert len(page3) == 1

    async def test_list_documents_empty(self, session: AsyncSession):
        """Test listing documents when none exist."""
        repo = DocumentRepository(session)
        documents = await repo.list_documents()
        assert len(documents) == 0

    async def test_list_pending(self, session: AsyncSession):
        """Test listing pending documents."""
        repo = DocumentRepository(session)

        # Create mix of statuses
        pending = Document(
            id=uuid4(),
            filename="pending.pdf",
            file_hash="h1",
            file_type="pdf",
            file_size_bytes=100,
            status=DocumentStatus.PENDING,
        )
        processing = Document(
            id=uuid4(),
            filename="processing.pdf",
            file_hash="h2",
            file_type="pdf",
            file_size_bytes=100,
            status=DocumentStatus.PROCESSING,
        )
        completed = Document(
            id=uuid4(),
            filename="done.pdf",
            file_hash="h3",
            file_type="pdf",
            file_size_bytes=100,
            status=DocumentStatus.COMPLETED,
        )
        failed = Document(
            id=uuid4(),
            filename="failed.pdf",
            file_hash="h4",
            file_type="pdf",
            file_size_bytes=100,
            status=DocumentStatus.FAILED,
        )

        await repo.create(pending)
        await repo.create(processing)
        await repo.create(completed)
        await repo.create(failed)

        pending_list = await repo.list_pending()
        assert len(pending_list) == 1
        assert pending_list[0].filename == "pending.pdf"

    async def test_list_pending_respects_limit(self, session: AsyncSession):
        """Test that list_pending respects limit parameter."""
        repo = DocumentRepository(session)

        # Create 5 pending documents
        for i in range(5):
            doc = Document(
                id=uuid4(),
                filename=f"pending{i}.pdf",
                file_hash=f"phash{i}",
                file_type="pdf",
                file_size_bytes=100,
                status=DocumentStatus.PENDING,
            )
            await repo.create(doc)

        pending_list = await repo.list_pending(limit=2)
        assert len(pending_list) == 2
