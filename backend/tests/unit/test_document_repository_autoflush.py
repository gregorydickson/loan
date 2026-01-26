"""Unit tests for DocumentRepository.delete() autoflush fix.

Tests the specific fix in DocumentRepository.delete() that prevents
IntegrityError when deleting documents with pending objects in the session.

The fix wraps the entire delete() method in session.no_autoflush to prevent
queries from triggering premature flush of pending objects.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.storage.models import (
    AccountNumber,
    Base,
    Borrower,
    Document,
    DocumentStatus,
    SourceReference,
)
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
        await session.rollback()


@pytest.mark.asyncio
async def test_delete_document_with_borrowers(session: AsyncSession):
    """Test that delete successfully removes document and associated borrowers.

    This is the happy path - verify the no_autoflush fix doesn't break
    normal delete functionality.
    """
    doc_repo = DocumentRepository(session)

    # Create document with borrower and account numbers
    document = Document(
        id=uuid4(),
        filename="test.pdf",
        file_hash="hash123",
        file_type="application/pdf",
        file_size_bytes=1000,
        status=DocumentStatus.COMPLETED,
    )
    session.add(document)
    await session.flush()

    borrower = Borrower(
        id=uuid4(),
        name="John Doe",
        ssn_hash="ssn_hash_123",
        confidence_score=Decimal("0.85"),
    )
    account = AccountNumber(
        id=uuid4(),
        borrower_id=borrower.id,
        number="ACC123",
        account_type="bank",
    )
    source = SourceReference(
        id=uuid4(),
        borrower_id=borrower.id,
        document_id=document.id,
        page_number=1,
        snippet="Test snippet",
    )

    session.add_all([borrower, account, source])
    await session.flush()
    await session.commit()

    doc_id = document.id
    borrower_id = borrower.id

    # Delete the document
    result = await doc_repo.delete(doc_id)
    assert result is True, "Delete should succeed"

    # Verify borrower was deleted (cascade)
    await session.commit()
    deleted_borrower = await session.get(Borrower, borrower_id)
    assert deleted_borrower is None, "Borrower should be deleted"

    # Verify document was deleted
    deleted_doc = await session.get(Document, doc_id)
    assert deleted_doc is None, "Document should be deleted"


@pytest.mark.asyncio
async def test_delete_with_multiple_borrowers(session: AsyncSession):
    """Test delete with multiple borrowers verifies no_autoflush in loop."""
    doc_repo = DocumentRepository(session)

    # Create document
    document = Document(
        id=uuid4(),
        filename="multi_borrower.pdf",
        file_hash="hash456",
        file_type="application/pdf",
        file_size_bytes=2000,
        status=DocumentStatus.COMPLETED,
    )
    session.add(document)
    await session.flush()

    # Create 3 borrowers
    borrower_ids = []
    for i in range(3):
        borrower = Borrower(
            id=uuid4(),
            name=f"Borrower {i+1}",
            ssn_hash=f"ssn_hash_{i+1}",
            confidence_score=Decimal("0.85"),
        )
        account = AccountNumber(
            id=uuid4(),
            borrower_id=borrower.id,
            number=f"ACC{i+1}",
            account_type="bank",
        )
        source = SourceReference(
            id=uuid4(),
            borrower_id=borrower.id,
            document_id=document.id,
            page_number=1,
            snippet=f"Snippet {i+1}",
        )
        session.add_all([borrower, account, source])
        borrower_ids.append(borrower.id)

    await session.flush()
    await session.commit()

    # Delete document - should handle all 3 borrowers
    result = await doc_repo.delete(document.id)
    assert result is True

    # All borrowers should be deleted
    await session.commit()
    for borrower_id in borrower_ids:
        deleted = await session.get(Borrower, borrower_id)
        assert deleted is None, f"Borrower {borrower_id} should be deleted"


@pytest.mark.asyncio
async def test_delete_nonexistent_document(session: AsyncSession):
    """Test deleting non-existent document returns False."""
    doc_repo = DocumentRepository(session)

    # Try to delete document that doesn't exist
    result = await doc_repo.delete(uuid4())
    assert result is False, "Should return False for non-existent document"


@pytest.mark.asyncio
async def test_delete_document_without_borrowers(session: AsyncSession):
    """Test deleting document without borrowers (baseline case)."""
    doc_repo = DocumentRepository(session)

    # Create document without any borrowers
    document = Document(
        id=uuid4(),
        filename="no_borrowers.pdf",
        file_hash="hash789",
        file_type="application/pdf",
        file_size_bytes=500,
        status=DocumentStatus.PENDING,
    )
    session.add(document)
    await session.flush()
    await session.commit()

    doc_id = document.id

    # Delete should work
    result = await doc_repo.delete(doc_id)
    assert result is True

    # Document should be deleted
    await session.commit()
    deleted_doc = await session.get(Document, doc_id)
    assert deleted_doc is None


@pytest.mark.asyncio
async def test_delete_uses_no_autoflush_context(session: AsyncSession):
    """Test that delete method uses no_autoflush to prevent premature flush.

    This verifies the fix is applied by checking that we can perform
    delete operations even when there are dirty objects in the session.
    """
    doc_repo = DocumentRepository(session)

    # Create document with borrower
    document = Document(
        id=uuid4(),
        filename="autoflush_test.pdf",
        file_hash="hash_test",
        file_type="application/pdf",
        file_size_bytes=1000,
        status=DocumentStatus.COMPLETED,
    )
    borrower = Borrower(
        id=uuid4(),
        name="Test Borrower",
        ssn_hash="ssn_test",
        confidence_score=Decimal("0.85"),
    )
    source = SourceReference(
        id=uuid4(),
        borrower_id=borrower.id,
        document_id=document.id,
        page_number=1,
        snippet="Test snippet",
    )

    session.add_all([document, borrower, source])
    await session.flush()
    await session.commit()

    doc_id = document.id

    # Create a new document (dirty object in session)
    new_doc = Document(
        id=uuid4(),
        filename="new.pdf",
        file_hash="hash_new",
        file_type="application/pdf",
        file_size_bytes=500,
        status=DocumentStatus.PENDING,
    )
    session.add(new_doc)
    # Don't flush - keep it dirty

    # Delete old document - should work with dirty object in session
    result = await doc_repo.delete(doc_id)
    assert result is True, "Delete should succeed with dirty objects in session"

    # Both operations can be flushed together
    await session.flush()
    await session.commit()

    # Verify results
    deleted_doc = await session.get(Document, doc_id)
    assert deleted_doc is None, "Old document should be deleted"

    new_doc_check = await session.get(Document, new_doc.id)
    assert new_doc_check is not None, "New document should be created"
