"""Unit tests for BorrowerRepository.

Uses SQLite in-memory with aiosqlite for fast, isolated testing.
Each test gets a fresh database with the schema created from ORM models.
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
    IncomeRecord,
    SourceReference,
)
from src.storage.repositories import BorrowerRepository


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
def sample_borrower() -> Borrower:
    """Create a sample borrower for testing."""
    return Borrower(
        id=uuid4(),
        name="John Smith",
        ssn_hash="abc123hash",
        address_json='{"street": "123 Main St", "city": "Austin"}',
        confidence_score=Decimal("0.95"),
    )


@pytest.fixture
def sample_income_record() -> IncomeRecord:
    """Create a sample income record for testing."""
    return IncomeRecord(
        id=uuid4(),
        amount=Decimal("75000.00"),
        period="annual",
        year=2024,
        source_type="W2",
        employer="Acme Corp",
    )


@pytest.fixture
def sample_account_number() -> AccountNumber:
    """Create a sample account number for testing."""
    return AccountNumber(
        id=uuid4(),
        number="ACC-12345",
        account_type="loan",
    )


@pytest.fixture
async def sample_document(session: AsyncSession) -> Document:
    """Create a sample document and persist it (needed for source_reference FK)."""
    doc = Document(
        id=uuid4(),
        filename="test.pdf",
        file_hash=f"hash_{uuid4().hex[:8]}",
        file_type="pdf",
        file_size_bytes=1024,
        status=DocumentStatus.COMPLETED,
    )
    session.add(doc)
    await session.flush()
    return doc


def sample_source_reference(document_id) -> SourceReference:
    """Create a sample source reference for testing."""
    return SourceReference(
        id=uuid4(),
        document_id=document_id,
        page_number=1,
        section="Income",
        snippet="John Smith earned $75,000 in 2024",
    )


class TestBorrowerRepository:
    """Tests for BorrowerRepository."""

    async def test_create_borrower_with_relations(
        self,
        session: AsyncSession,
        sample_borrower: Borrower,
        sample_income_record: IncomeRecord,
        sample_account_number: AccountNumber,
        sample_document: Document,
    ):
        """Test creating a borrower with all related entities."""
        repo = BorrowerRepository(session)
        source_ref = sample_source_reference(sample_document.id)

        created = await repo.create(
            borrower=sample_borrower,
            income_records=[sample_income_record],
            account_numbers=[sample_account_number],
            source_references=[source_ref],
        )

        # Assert borrower was created with ID
        assert created.id == sample_borrower.id
        assert created.name == "John Smith"
        assert created.confidence_score == Decimal("0.95")
        assert created.created_at is not None

        # CRITICAL: Assert borrower_id FK is set on all related entities
        assert sample_income_record.borrower_id == created.id
        assert sample_account_number.borrower_id == created.id
        assert source_ref.borrower_id == created.id

    async def test_get_by_id_returns_borrower_with_relations(
        self,
        session: AsyncSession,
        sample_borrower: Borrower,
        sample_income_record: IncomeRecord,
        sample_account_number: AccountNumber,
        sample_document: Document,
    ):
        """Test retrieving borrower by ID with all relationships loaded."""
        repo = BorrowerRepository(session)
        source_ref = sample_source_reference(sample_document.id)

        await repo.create(
            borrower=sample_borrower,
            income_records=[sample_income_record],
            account_numbers=[sample_account_number],
            source_references=[source_ref],
        )

        # Fetch by ID
        found = await repo.get_by_id(sample_borrower.id)

        assert found is not None
        assert found.name == "John Smith"

        # Assert all relationships are accessible (no lazy loading error)
        assert len(found.income_records) == 1
        assert found.income_records[0].amount == Decimal("75000.00")

        assert len(found.account_numbers) == 1
        assert found.account_numbers[0].number == "ACC-12345"

        assert len(found.source_references) == 1
        assert found.source_references[0].page_number == 1

        # Also verify nested document relationship on source_reference
        assert found.source_references[0].document is not None
        assert found.source_references[0].document.filename == "test.pdf"

    async def test_get_by_id_returns_none_for_missing(self, session: AsyncSession):
        """Test retrieving non-existent borrower returns None."""
        repo = BorrowerRepository(session)
        found = await repo.get_by_id(uuid4())
        assert found is None

    async def test_search_by_name_case_insensitive(
        self,
        session: AsyncSession,
        sample_borrower: Borrower,
        sample_document: Document,
    ):
        """Test searching by name is case-insensitive."""
        repo = BorrowerRepository(session)

        await repo.create(
            borrower=sample_borrower,
            income_records=[],
            account_numbers=[],
            source_references=[],
        )

        # Search with different cases
        results_lower = await repo.search_by_name("john")
        assert len(results_lower) == 1
        assert results_lower[0].name == "John Smith"

        results_upper = await repo.search_by_name("SMITH")
        assert len(results_upper) == 1
        assert results_upper[0].name == "John Smith"

        results_mixed = await repo.search_by_name("john smith")
        assert len(results_mixed) == 1
        assert results_mixed[0].name == "John Smith"

    async def test_search_by_name_partial_match(self, session: AsyncSession):
        """Test searching by partial name matches."""
        repo = BorrowerRepository(session)

        # Create borrower named "Johnson"
        borrower = Borrower(
            id=uuid4(),
            name="Johnson Williams",
            confidence_score=Decimal("0.90"),
        )
        await repo.create(
            borrower=borrower,
            income_records=[],
            account_numbers=[],
            source_references=[],
        )

        # Search "john" should find "Johnson"
        results = await repo.search_by_name("john")
        assert len(results) == 1
        assert results[0].name == "Johnson Williams"

    async def test_search_by_account_number(
        self,
        session: AsyncSession,
        sample_borrower: Borrower,
        sample_account_number: AccountNumber,
    ):
        """Test searching borrowers by account number."""
        repo = BorrowerRepository(session)

        await repo.create(
            borrower=sample_borrower,
            income_records=[],
            account_numbers=[sample_account_number],
            source_references=[],
        )

        # Search by partial account number
        results = await repo.search_by_account("12345")
        assert len(results) == 1
        assert results[0].name == "John Smith"
        assert len(results[0].account_numbers) == 1
        assert results[0].account_numbers[0].number == "ACC-12345"

    async def test_list_borrowers_pagination(self, session: AsyncSession):
        """Test listing borrowers with pagination."""
        repo = BorrowerRepository(session)

        # Create 5 borrowers
        for i in range(5):
            borrower = Borrower(
                id=uuid4(),
                name=f"Borrower {i}",
                confidence_score=Decimal("0.85"),
            )
            await repo.create(
                borrower=borrower,
                income_records=[],
                account_numbers=[],
                source_references=[],
            )

        # Get first page
        page1 = await repo.list_borrowers(limit=2, offset=0)
        assert len(page1) == 2

        # Get second page
        page2 = await repo.list_borrowers(limit=2, offset=2)
        assert len(page2) == 2

        # Get third page (partial)
        page3 = await repo.list_borrowers(limit=2, offset=4)
        assert len(page3) == 1

    async def test_count_returns_total(self, session: AsyncSession):
        """Test counting total borrowers."""
        repo = BorrowerRepository(session)

        # Initially empty
        assert await repo.count() == 0

        # Create 3 borrowers
        for i in range(3):
            borrower = Borrower(
                id=uuid4(),
                name=f"Test Borrower {i}",
                confidence_score=Decimal("0.80"),
            )
            await repo.create(
                borrower=borrower,
                income_records=[],
                account_numbers=[],
                source_references=[],
            )

        # Should be 3
        assert await repo.count() == 3
