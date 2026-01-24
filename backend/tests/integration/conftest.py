"""Fixtures for integration tests."""

from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.dependencies import (
    get_borrower_extractor,
    get_cloud_tasks_client,
    get_docling_processor,
    get_gcs_client,
)
from src.ingestion.docling_processor import (
    DoclingProcessor,
    DocumentContent,
    DocumentProcessingError,
    PageContent,
)
from src.main import app
from src.storage.database import get_db_session
from src.storage.models import Base


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
async def db_session(async_engine):
    """Create async session for testing."""
    session_factory = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
def mock_gcs_client():
    """Create mock GCS client."""
    from src.storage.gcs_client import GCSClient

    client = MagicMock(spec=GCSClient)
    client.upload = MagicMock(return_value="gs://test-bucket/documents/test/file.pdf")
    client.download = MagicMock(return_value=b"file content")
    client.exists = MagicMock(return_value=True)
    return client


@pytest.fixture
def mock_gcs_client_failing():
    """Create mock GCS client that fails on upload."""
    from src.storage.gcs_client import GCSClient, GCSUploadError

    client = MagicMock(spec=GCSClient)
    client.upload = MagicMock(side_effect=GCSUploadError("Network error"))
    return client


@pytest.fixture
def mock_docling_processor():
    """Create mock DoclingProcessor that returns successful result."""
    processor = MagicMock(spec=DoclingProcessor)
    processor.process_bytes = MagicMock(
        return_value=DocumentContent(
            text="Test document content",
            pages=[PageContent(page_number=1, text="Page 1 content", tables=[])],
            page_count=1,
            tables=[],
            metadata={"status": "SUCCESS"},
        )
    )
    return processor


@pytest.fixture
def mock_docling_processor_failing():
    """Create mock DoclingProcessor that fails (for error testing)."""
    processor = MagicMock(spec=DoclingProcessor)
    processor.process_bytes = MagicMock(
        side_effect=DocumentProcessingError("Invalid PDF format", details="Corrupted file")
    )
    return processor


@pytest.fixture
def mock_borrower_extractor():
    """Create mock BorrowerExtractor that returns empty results."""
    from src.extraction import BorrowerExtractor, ExtractionResult
    from src.extraction.complexity_classifier import ComplexityAssessment, ComplexityLevel

    extractor = MagicMock(spec=BorrowerExtractor)
    extractor.extract = MagicMock(
        return_value=ExtractionResult(
            borrowers=[],
            complexity=ComplexityAssessment(
                level=ComplexityLevel.STANDARD,
                reasons=["Test document"],
                page_count=1,
                estimated_borrowers=1,
                has_handwritten=False,
                has_poor_quality=False,
            ),
            chunks_processed=1,
            total_tokens=100,
            validation_errors=[],
            consistency_warnings=[],
        )
    )
    return extractor


@pytest.fixture
def mock_borrower_extractor_with_data():
    """Create mock BorrowerExtractor that returns realistic borrower data.

    This fixture is used for E2E tests that need to verify borrowers
    are extracted and persisted correctly.
    """
    from decimal import Decimal
    from uuid import uuid4

    from src.extraction import BorrowerExtractor, ExtractionResult
    from src.extraction.complexity_classifier import ComplexityAssessment, ComplexityLevel
    from src.models.borrower import Address, BorrowerRecord, IncomeRecord
    from src.models.document import SourceReference

    # Create test borrower data template
    test_borrower_id = uuid4()

    def create_mock_extract(document, document_id, document_name):
        """Create extraction result with document-specific source reference."""
        # Create source reference with actual document_id
        source = SourceReference(
            document_id=document_id,
            document_name=document_name,
            page_number=1,
            snippet="John Smith, SSN: 123-45-6789, employed at Acme Corp",
        )

        # Create borrower with all fields populated
        borrower_with_source = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            ssn="123-45-6789",
            phone="(555) 123-4567",
            email="john.smith@example.com",
            address=Address(
                street="123 Main St",
                city="Austin",
                state="TX",
                zip_code="78701",
            ),
            income_history=[
                IncomeRecord(
                    amount=Decimal("75000.00"),
                    period="annual",
                    year=2024,
                    source_type="employment",
                    employer="Acme Corp",
                ),
                IncomeRecord(
                    amount=Decimal("72000.00"),
                    period="annual",
                    year=2023,
                    source_type="employment",
                    employer="Acme Corp",
                ),
            ],
            account_numbers=["1234567890"],
            loan_numbers=["LOAN-2024-001"],
            sources=[source],
            confidence_score=0.85,
        )

        return ExtractionResult(
            borrowers=[borrower_with_source],
            complexity=ComplexityAssessment(
                level=ComplexityLevel.SIMPLE if hasattr(ComplexityLevel, 'SIMPLE') else ComplexityLevel.STANDARD,
                reasons=["Single borrower document"],
                page_count=1,
                estimated_borrowers=1,
                has_handwritten=False,
                has_poor_quality=False,
            ),
            chunks_processed=1,
            total_tokens=500,
            validation_errors=[],
            consistency_warnings=[],
        )

    extractor = MagicMock(spec=BorrowerExtractor)
    extractor.extract = MagicMock(side_effect=create_mock_extract)
    return extractor


@pytest.fixture
async def client(async_engine, db_session, mock_gcs_client, mock_docling_processor, mock_borrower_extractor):
    """Create test client with mocked dependencies."""
    session_factory = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_db_session():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    def override_get_gcs_client():
        return mock_gcs_client

    def override_get_docling_processor():
        return mock_docling_processor

    def override_get_borrower_extractor():
        return mock_borrower_extractor

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_gcs_client] = override_get_gcs_client
    app.dependency_overrides[get_docling_processor] = override_get_docling_processor
    app.dependency_overrides[get_borrower_extractor] = override_get_borrower_extractor

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def client_with_failing_gcs(
    async_engine, db_session, mock_gcs_client_failing, mock_docling_processor, mock_borrower_extractor
):
    """Create test client with GCS that fails (for error testing)."""
    session_factory = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_db_session():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    def override_get_gcs_client():
        return mock_gcs_client_failing

    def override_get_docling_processor():
        return mock_docling_processor

    def override_get_borrower_extractor():
        return mock_borrower_extractor

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_gcs_client] = override_get_gcs_client
    app.dependency_overrides[get_docling_processor] = override_get_docling_processor
    app.dependency_overrides[get_borrower_extractor] = override_get_borrower_extractor

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def client_with_failing_docling(
    async_engine, db_session, mock_gcs_client, mock_docling_processor_failing, mock_borrower_extractor
):
    """Create test client with DoclingProcessor that fails (for error testing)."""
    session_factory = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_db_session():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    def override_get_gcs_client():
        return mock_gcs_client

    def override_get_docling_processor():
        return mock_docling_processor_failing

    def override_get_borrower_extractor():
        return mock_borrower_extractor

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_gcs_client] = override_get_gcs_client
    app.dependency_overrides[get_docling_processor] = override_get_docling_processor
    app.dependency_overrides[get_borrower_extractor] = override_get_borrower_extractor

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def client_with_extraction(
    async_engine, db_session, mock_gcs_client, mock_docling_processor, mock_borrower_extractor_with_data
):
    """Create test client with extractor that returns borrower data.

    Use this fixture for tests that need to verify the full extraction
    pipeline: upload -> extract -> persist -> retrieve.
    """
    session_factory = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_db_session():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    def override_get_gcs_client():
        return mock_gcs_client

    def override_get_docling_processor():
        return mock_docling_processor

    def override_get_borrower_extractor():
        return mock_borrower_extractor_with_data

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_gcs_client] = override_get_gcs_client
    app.dependency_overrides[get_docling_processor] = override_get_docling_processor
    app.dependency_overrides[get_borrower_extractor] = override_get_borrower_extractor

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def client_with_task_handler(
    async_engine,
    mock_gcs_client,
    mock_docling_processor,
    mock_borrower_extractor_with_data,
):
    """Test client for task handler testing with real document processing.

    This fixture is for testing the Cloud Tasks handler endpoint directly.
    It sets cloud_tasks_client to None (simulating local dev mode) so the
    handler can be invoked directly via HTTP requests.

    Use this fixture for tests that need to verify:
    - Task handler processes documents correctly
    - Task handler persists borrowers
    - Task handler handles errors appropriately
    """
    session_factory = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_db_session():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    def override_get_gcs_client():
        return mock_gcs_client

    def override_get_docling_processor():
        return mock_docling_processor

    def override_get_borrower_extractor():
        return mock_borrower_extractor_with_data

    def override_cloud_tasks_client():
        # Return None to simulate local dev (no async queueing)
        return None

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_gcs_client] = override_get_gcs_client
    app.dependency_overrides[get_docling_processor] = override_get_docling_processor
    app.dependency_overrides[get_borrower_extractor] = override_get_borrower_extractor
    app.dependency_overrides[get_cloud_tasks_client] = override_cloud_tasks_client

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client

    app.dependency_overrides.clear()
