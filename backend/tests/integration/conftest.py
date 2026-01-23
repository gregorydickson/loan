"""Fixtures for integration tests."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from unittest.mock import MagicMock

from src.main import app
from src.storage.models import Base
from src.storage.database import get_db_session
from src.api.dependencies import get_gcs_client, get_docling_processor
from src.ingestion.docling_processor import (
    DoclingProcessor,
    DocumentContent,
    DocumentProcessingError,
    PageContent,
)


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
async def client(async_engine, db_session, mock_gcs_client, mock_docling_processor):
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

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_gcs_client] = override_get_gcs_client
    app.dependency_overrides[get_docling_processor] = override_get_docling_processor

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def client_with_failing_gcs(
    async_engine, db_session, mock_gcs_client_failing, mock_docling_processor
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

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_gcs_client] = override_get_gcs_client
    app.dependency_overrides[get_docling_processor] = override_get_docling_processor

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def client_with_failing_docling(
    async_engine, db_session, mock_gcs_client, mock_docling_processor_failing
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

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_gcs_client] = override_get_gcs_client
    app.dependency_overrides[get_docling_processor] = override_get_docling_processor

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
