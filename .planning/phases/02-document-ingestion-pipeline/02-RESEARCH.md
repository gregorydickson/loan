# Phase 2: Document Ingestion Pipeline - Research

**Researched:** 2026-01-23
**Domain:** Document processing (Docling), cloud storage (GCS), async database (SQLAlchemy/Alembic), task queuing (Cloud Tasks)
**Confidence:** HIGH

---

## Summary

This research covers the document ingestion pipeline for processing uploaded documents (PDF, DOCX, images) through Docling, storing in Google Cloud Storage, and tracking in PostgreSQL. The key components are: Docling 2.70.0 for document conversion with OCR support, google-cloud-storage for GCS upload/download with signed URLs, SQLAlchemy 2.0 async patterns with asyncpg, Alembic for migrations, and Cloud Tasks for background processing.

The standard approach uses Docling's `DocumentConverter` for PDF/DOCX/image processing with configurable OCR and table extraction, GCS client with Application Default Credentials (ADC) for seamless Cloud Run deployment, async SQLAlchemy sessions with repository pattern for database operations, and a sync upload endpoint that queues async processing via Cloud Tasks. Critical findings include Docling memory issues requiring fresh converter instances per document and page limits for large PDFs.

**Primary recommendation:** Process documents synchronously for small files (<10 pages) and queue via Cloud Tasks for larger documents. Use SHA-256 hash for duplicate detection before GCS upload. Create fresh Docling `DocumentConverter` instances per conversion to avoid memory leaks. Configure SQLAlchemy with `expire_on_commit=False` and use separate sessions per request.

---

## Standard Stack

The established libraries/tools for this domain (versions locked from Phase 1 pyproject.toml):

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| docling | 2.70.0 | Document conversion | Production-grade PDF/DOCX/image parsing with OCR, tables, layout understanding |
| google-cloud-storage | 2.18.0+ | GCS client | Official Python SDK, ADC support, resumable uploads |
| SQLAlchemy | 2.0.46+ | Async ORM | Native asyncio support, asyncpg integration |
| asyncpg | 0.31.0+ | PostgreSQL driver | Purpose-built for asyncio, best performance |
| Alembic | 1.18.0+ | Migrations | SQLAlchemy integration, async template support |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| fastapi-cloud-tasks | 0.3.0+ | Cloud Tasks integration | Background job queuing with FastAPI |
| python-multipart | 0.0.18+ | File uploads | Required for FastAPI UploadFile |
| tenacity | 9.0.0+ | Retry logic | GCS/Docling error recovery |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Cloud Tasks | Celery + Redis | Cloud Tasks is GCP-native, autoscales; Celery more flexible but needs infra |
| Docling | PyMuPDF + Tesseract | Docling has integrated pipeline; manual assembly requires more code |
| Signed URLs for upload | Direct GCS upload | Signed URLs bypass API for large files; adds complexity |

**Installation:**
Already in Phase 1 pyproject.toml:
```bash
pip install -e ".[dev]"
```

---

## Architecture Patterns

### Recommended Project Structure
```
backend/src/
├── ingestion/
│   ├── __init__.py
│   ├── docling_processor.py  # DocumentConverter wrapper
│   └── document_service.py   # Upload/process orchestration
├── storage/
│   ├── __init__.py
│   ├── gcs_client.py         # GCS upload/download/signed URLs
│   ├── models.py             # SQLAlchemy ORM models
│   └── repositories.py       # Async repository pattern
└── models/
    ├── borrower.py           # (from Phase 1)
    └── document.py           # (from Phase 1)
```

### Pattern 1: Docling Document Processing
**What:** Wrap Docling `DocumentConverter` for PDF/DOCX/image extraction
**When to use:** All document processing operations
**Example:**
```python
# Source: https://docling-project.github.io/docling/reference/document_converter/
from pathlib import Path
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from pydantic import BaseModel


class PageContent(BaseModel):
    """Content extracted from a single page."""
    page_number: int
    text: str
    tables: list[dict]  # Simplified table representation


class DocumentContent(BaseModel):
    """Complete document extraction result."""
    text: str
    pages: list[PageContent]
    page_count: int
    tables: list[dict]
    metadata: dict


class DoclingProcessor:
    """Wrapper for Docling document conversion."""

    def __init__(self, enable_ocr: bool = True, enable_tables: bool = True) -> None:
        # Configure pipeline options
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = enable_ocr
        pipeline_options.do_table_structure = enable_tables

        self.format_options = {
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        }

    def process(self, file_path: Path, max_pages: int = 100) -> DocumentContent:
        """Process a document and extract structured content.

        IMPORTANT: Create a fresh converter per document to avoid memory leaks.
        """
        # Create fresh converter instance (avoid memory leak)
        converter = DocumentConverter(format_options=self.format_options)

        result = converter.convert(
            source=file_path,
            raises_on_error=False,
            max_num_pages=max_pages,
        )

        if result.status.name == "FAILURE":
            raise ValueError(f"Document conversion failed: {result.errors}")

        doc = result.document

        # Extract page-level content
        pages = []
        for page_no, page_item in enumerate(doc.pages, start=1):
            # Get text for this page
            page_text = ""  # Extract from doc structure
            page_tables = []  # Extract tables on this page
            pages.append(PageContent(
                page_number=page_no,
                text=page_text,
                tables=page_tables,
            ))

        return DocumentContent(
            text=doc.export_to_markdown(),
            pages=pages,
            page_count=len(doc.pages),
            tables=[],  # Aggregate all tables
            metadata={"status": result.status.name},
        )

    def process_bytes(self, data: bytes, filename: str, max_pages: int = 100) -> DocumentContent:
        """Process document from bytes (for uploaded files)."""
        import tempfile

        suffix = Path(filename).suffix
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp.flush()
            return self.process(Path(tmp.name), max_pages=max_pages)
```

### Pattern 2: GCS Client with Signed URLs
**What:** Upload/download files to GCS with temporary access URLs
**When to use:** All file storage operations
**Example:**
```python
# Source: https://cloud.google.com/storage/docs/samples/storage-generate-signed-url-v4
from datetime import timedelta
from google.cloud import storage
from google.cloud.storage import Blob


class GCSClient:
    """Google Cloud Storage client for document storage."""

    def __init__(self, bucket_name: str) -> None:
        # Uses Application Default Credentials (ADC)
        # Works automatically on Cloud Run with service account
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

    def upload(self, data: bytes, path: str, content_type: str = "application/octet-stream") -> str:
        """Upload data and return gs:// URI."""
        blob = self.bucket.blob(path)
        blob.upload_from_string(data, content_type=content_type)
        return f"gs://{self.bucket.name}/{path}"

    def upload_from_file(self, file_obj, path: str, content_type: str = "application/octet-stream") -> str:
        """Upload from file-like object (memory efficient for large files)."""
        blob = self.bucket.blob(path)
        file_obj.seek(0)
        blob.upload_from_file(file_obj, content_type=content_type)
        return f"gs://{self.bucket.name}/{path}"

    def download(self, path: str) -> bytes:
        """Download file content as bytes."""
        blob = self.bucket.blob(path)
        return blob.download_as_bytes()

    def delete(self, path: str) -> None:
        """Delete a file from storage."""
        blob = self.bucket.blob(path)
        blob.delete()

    def exists(self, path: str) -> bool:
        """Check if file exists."""
        blob = self.bucket.blob(path)
        return blob.exists()

    def get_signed_url(
        self, path: str, expiration_minutes: int = 15, method: str = "GET"
    ) -> str:
        """Generate a signed URL for temporary access.

        Note: Requires service account credentials for signing.
        On Cloud Run, uses impersonated credentials automatically.
        """
        blob = self.bucket.blob(path)
        return blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=expiration_minutes),
            method=method,
        )
```

### Pattern 3: Async SQLAlchemy Repository
**What:** Repository pattern with async sessions for database operations
**When to use:** All database access
**Example:**
```python
# Source: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.models import Document, DocumentStatus


class DocumentRepository:
    """Repository for Document database operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, document: Document) -> Document:
        """Create a new document record."""
        self.session.add(document)
        await self.session.flush()
        await self.session.refresh(document)
        return document

    async def get_by_id(self, document_id: UUID) -> Document | None:
        """Get document by ID."""
        result = await self.session.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()

    async def get_by_hash(self, file_hash: str) -> Document | None:
        """Get document by file hash (for duplicate detection)."""
        result = await self.session.execute(
            select(Document).where(Document.file_hash == file_hash)
        )
        return result.scalar_one_or_none()

    async def update_status(
        self, document_id: UUID, status: DocumentStatus, error_message: str | None = None
    ) -> None:
        """Update document processing status."""
        document = await self.get_by_id(document_id)
        if document:
            document.status = status
            document.error_message = error_message
            await self.session.flush()

    async def list_pending(self, limit: int = 100) -> Sequence[Document]:
        """List documents pending processing."""
        result = await self.session.execute(
            select(Document)
            .where(Document.status == DocumentStatus.PENDING)
            .limit(limit)
        )
        return result.scalars().all()
```

### Pattern 4: SQLAlchemy ORM Models
**What:** Async-compatible SQLAlchemy 2.0 models
**When to use:** Database schema definition
**Example:**
```python
# Source: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class DocumentStatus(str, PyEnum):
    """Document processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(Base):
    """SQLAlchemy model for documents."""
    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    gcs_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.PENDING, nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    borrowers: Mapped[list["Borrower"]] = relationship(
        back_populates="source_documents", secondary="source_references"
    )


class Borrower(Base):
    """SQLAlchemy model for borrowers."""
    __tablename__ = "borrowers"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    ssn_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    # Store address as JSON for flexibility
    address_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    income_records: Mapped[list["IncomeRecord"]] = relationship(back_populates="borrower")
    account_numbers: Mapped[list["AccountNumber"]] = relationship(back_populates="borrower")
    source_references: Mapped[list["SourceReference"]] = relationship(back_populates="borrower")
```

### Pattern 5: FastAPI Dependency Injection for Sessions
**What:** Async session management with dependency injection
**When to use:** All FastAPI route handlers
**Example:**
```python
# Source: https://fastapi.tiangolo.com/advanced/events/
from typing import Annotated, AsyncGenerator

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import settings

# Create engine once at startup
engine = create_async_engine(
    str(settings.database_url),
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    echo=settings.debug,
)

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Critical: prevents attribute expiration
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Type alias for cleaner signatures
DBSession = Annotated[AsyncSession, Depends(get_db_session)]


# Usage in routes
@app.get("/documents/{document_id}")
async def get_document(document_id: UUID, session: DBSession):
    repo = DocumentRepository(session)
    document = await repo.get_by_id(document_id)
    if not document:
        raise HTTPException(status_code=404)
    return document
```

### Anti-Patterns to Avoid
- **Reusing Docling DocumentConverter instance:** Creates memory leaks (13GB+ reported). Create fresh instance per conversion.
- **Processing large PDFs without page limits:** Can hang for hours on 3000+ page documents. Set `max_num_pages`.
- **Sharing AsyncSession across tasks:** Not thread/task safe. One session per request/task.
- **Using `expire_on_commit=True` with async:** Forces implicit IO on attribute access.
- **Storing service account keys in code:** Use ADC (Application Default Credentials) instead.
- **Checking hash after upload:** Check before upload to avoid wasted GCS storage/bandwidth.

---

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF/DOCX/image parsing | Custom parsers per format | Docling DocumentConverter | Handles layout, tables, OCR, images uniformly |
| GCS signed URLs | Manual JWT signing | `blob.generate_signed_url()` | Handles all V4 signing complexity |
| SHA-256 hashing | Manual byte reading | `hashlib.sha256()` with `file.read()` | Streaming support, handles large files |
| File upload handling | Manual multipart parsing | FastAPI `UploadFile` | SpooledTemporaryFile handles large files |
| Async DB sessions | Manual connection management | `async_sessionmaker` | Pool management, transaction handling |
| Migration management | Raw SQL scripts | Alembic | Version tracking, rollback support |
| Retry logic | try/except loops | `tenacity` library | Exponential backoff, configurable strategies |
| Background tasks | Custom threading | Cloud Tasks / `fastapi-cloud-tasks` | Managed queue, retries, monitoring |

**Key insight:** Docling is the critical component - it replaces what would be 3-4 separate libraries (PDF parsing, DOCX parsing, OCR, table extraction) with a unified interface. The memory leak issue is significant but manageable with fresh instances per conversion.

---

## Common Pitfalls

### Pitfall 1: Docling Memory Leak with Reused Converter
**What goes wrong:** Memory grows to 10GB+ after processing multiple documents
**Why it happens:** DoclingParseV2DocumentBackend accumulates state between conversions
**How to avoid:** Create a new `DocumentConverter` instance for each document:
```python
# BAD: Reusing converter
converter = DocumentConverter()
for doc in documents:
    converter.convert(doc)  # Memory accumulates!

# GOOD: Fresh converter per document
for doc in documents:
    converter = DocumentConverter()
    converter.convert(doc)
```
**Warning signs:** Memory usage climbing steadily, OOM kills

### Pitfall 2: Large PDF Processing Hangs
**What goes wrong:** Processing hangs indefinitely on large PDFs (3000+ pages)
**Why it happens:** Sequential processing, expensive operations (OCR, table detection)
**How to avoid:**
- Set `max_num_pages` limit (recommended: 100 for standard, 500 max)
- Disable OCR for digital PDFs: `pipeline_options.do_ocr = False`
- Disable table extraction if not needed: `pipeline_options.do_table_structure = False`
```python
result = converter.convert(
    source=file_path,
    max_num_pages=100,  # Limit pages
)
```
**Warning signs:** Processing takes >10 minutes, no progress indication

### Pitfall 3: GCS Authentication Failures in Different Environments
**What goes wrong:** Code works locally but fails on Cloud Run, or vice versa
**Why it happens:** Different credential sources (ADC vs. service account key)
**How to avoid:**
- Local dev: Set `GOOGLE_APPLICATION_CREDENTIALS` to service account JSON path
- Cloud Run: Service account attached to service, ADC works automatically
- Never commit credentials to git
```python
# This works everywhere with proper ADC setup
client = storage.Client()  # No explicit credentials
```
**Warning signs:** "Could not automatically determine credentials" errors

### Pitfall 4: Race Condition in Duplicate Detection
**What goes wrong:** Duplicate files uploaded when two requests arrive simultaneously
**Why it happens:** Hash check and insert not atomic
**How to avoid:** Use database unique constraint on `file_hash` column, handle integrity error:
```python
from sqlalchemy.exc import IntegrityError

try:
    await session.flush()  # Tries to insert
except IntegrityError:
    await session.rollback()
    existing = await repo.get_by_hash(file_hash)
    raise DuplicateDocumentError(existing.id)
```
**Warning signs:** Duplicate documents in database with same hash

### Pitfall 5: Alembic Migration in Async Context
**What goes wrong:** `RuntimeError: This event loop is already running`
**Why it happens:** Alembic's async template uses `asyncio.run()` which fails inside existing loop
**How to avoid:** For programmatic migrations, pass connection to env.py:
```python
# In env.py
connectable = config.attributes.get("connection", None)
if connectable is None:
    asyncio.run(run_async_migrations())
else:
    do_run_migrations(connectable)  # Reuse existing connection
```
**Warning signs:** Migration errors in FastAPI lifespan context

### Pitfall 6: UploadFile Not Properly Closed
**What goes wrong:** File handles leak, temp files accumulate
**Why it happens:** FastAPI UploadFile must be explicitly closed
**How to avoid:**
```python
@app.post("/upload")
async def upload(file: UploadFile):
    try:
        content = await file.read()
        # process content
    finally:
        await file.close()  # Always close!
```
**Warning signs:** "Too many open files" errors, disk space issues

---

## Code Examples

Verified patterns from official sources:

### SHA-256 Hash for Duplicate Detection

Source: [Python hashlib](https://docs.python.org/3/library/hashlib.html)

```python
import hashlib
from fastapi import UploadFile


async def compute_file_hash(file: UploadFile) -> str:
    """Compute SHA-256 hash of uploaded file."""
    sha256 = hashlib.sha256()

    # Read in chunks to handle large files
    chunk_size = 8192
    await file.seek(0)

    while chunk := await file.read(chunk_size):
        sha256.update(chunk)

    # Reset file position for later use
    await file.seek(0)

    return sha256.hexdigest()
```

### Document Upload Endpoint

Source: [FastAPI Request Files](https://fastapi.tiangolo.com/tutorial/request-files/)

```python
from uuid import UUID
from fastapi import APIRouter, HTTPException, UploadFile, status
from pydantic import BaseModel

from src.ingestion.document_service import DocumentService
from src.storage.repositories import DocumentRepository


class DocumentUploadResponse(BaseModel):
    id: UUID
    filename: str
    status: str
    message: str


router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile,
    session: DBSession,
    gcs_client: Annotated[GCSClient, Depends(get_gcs_client)],
):
    """Upload a document for processing."""
    # Validate file type
    allowed_types = {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "image/png", "image/jpeg"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file.content_type} not supported"
        )

    # Limit file size (50MB)
    max_size = 50 * 1024 * 1024
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {max_size // (1024*1024)}MB"
        )

    try:
        service = DocumentService(
            repository=DocumentRepository(session),
            gcs_client=gcs_client,
        )
        document = await service.upload(
            filename=file.filename or "unknown",
            content=content,
            content_type=file.content_type or "application/octet-stream",
        )
        return DocumentUploadResponse(
            id=document.id,
            filename=document.filename,
            status=document.status.value,
            message="Document uploaded and queued for processing",
        )
    finally:
        await file.close()
```

### Alembic Async env.py Configuration

Source: [Alembic Cookbook](https://alembic.sqlalchemy.org/en/latest/cookbook.html)

```python
# alembic/env.py
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import your models' Base
from src.storage.models import Base

config = context.config
target_metadata = Base.metadata

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def do_run_migrations(connection):
    """Run migrations using the provided connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        # Naming conventions for auto-generated constraint names
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    """Create an async engine and run migrations."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # Don't use pooling for migrations
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    # Check if connection was passed (programmatic migration)
    connectable = config.attributes.get("connection", None)

    if connectable is None:
        # CLI invocation - run async
        asyncio.run(run_async_migrations())
    else:
        # Programmatic invocation - reuse connection
        do_run_migrations(connectable)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### Document Service with Status Tracking

```python
from datetime import datetime, timezone
from uuid import UUID, uuid4
import hashlib

from src.storage.models import Document, DocumentStatus
from src.storage.repositories import DocumentRepository
from src.storage.gcs_client import GCSClient


class DuplicateDocumentError(Exception):
    """Raised when a duplicate document is detected."""
    def __init__(self, existing_id: UUID):
        self.existing_id = existing_id
        super().__init__(f"Duplicate document exists with ID: {existing_id}")


class DocumentService:
    """Orchestrates document upload and processing."""

    def __init__(self, repository: DocumentRepository, gcs_client: GCSClient) -> None:
        self.repository = repository
        self.gcs_client = gcs_client

    async def upload(
        self,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> Document:
        """Upload a document: hash check, GCS upload, DB record."""
        # 1. Compute hash for duplicate detection
        file_hash = hashlib.sha256(content).hexdigest()

        # 2. Check for existing document with same hash
        existing = await self.repository.get_by_hash(file_hash)
        if existing:
            raise DuplicateDocumentError(existing.id)

        # 3. Determine file type from content_type
        file_type_map = {
            "application/pdf": "pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
            "image/png": "png",
            "image/jpeg": "jpg",
        }
        file_type = file_type_map.get(content_type, "unknown")

        # 4. Create document record with PENDING status
        document = Document(
            id=uuid4(),
            filename=filename,
            file_hash=file_hash,
            file_type=file_type,
            file_size_bytes=len(content),
            status=DocumentStatus.PENDING,
        )
        document = await self.repository.create(document)

        # 5. Upload to GCS
        gcs_path = f"documents/{document.id}/{filename}"
        gcs_uri = self.gcs_client.upload(content, gcs_path, content_type)

        # 6. Update document with GCS URI
        document.gcs_uri = gcs_uri
        await self.repository.session.flush()

        return document

    async def update_status(
        self,
        document_id: UUID,
        status: DocumentStatus,
        error_message: str | None = None,
        page_count: int | None = None,
    ) -> None:
        """Update document processing status."""
        document = await self.repository.get_by_id(document_id)
        if document:
            document.status = status
            document.error_message = error_message
            if page_count:
                document.page_count = page_count
            if status == DocumentStatus.COMPLETED:
                document.processed_at = datetime.now(timezone.utc)
            await self.repository.session.flush()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PyMuPDF + Tesseract | Docling | 2024-2025 | Unified pipeline, better table extraction |
| Service account JSON files | Application Default Credentials (ADC) | 2023+ | No credential management needed |
| SQLAlchemy 1.x async | SQLAlchemy 2.0 `async_sessionmaker` | 2023 | Native async, cleaner API |
| Celery for task queue | Cloud Tasks + FastAPI | 2024+ | Managed infrastructure, autoscaling |
| Manual migration scripts | Alembic with async template | 2023+ | Version control, auto-generation |

**Deprecated/outdated:**
- `google-generativeai`: Use `google-genai` (already in pyproject.toml)
- Storing GCS credentials as JSON in code: Use ADC
- SQLAlchemy `sessionmaker` with `AsyncSession`: Use `async_sessionmaker`
- Alembic `init` without `-t async`: Use `alembic init -t async` for async projects

---

## Open Questions

Things that couldn't be fully resolved:

1. **Docling performance with concurrent processing**
   - What we know: Python GIL limits true parallelism, ProcessPoolExecutor works but duplicates models in memory
   - What's unclear: Optimal thread/process count for loan document batch processing
   - Recommendation: Start with sequential processing, add concurrency only if proven bottleneck

2. **GCS signed URL generation on Cloud Run**
   - What we know: Requires either service account credentials or impersonated credentials
   - What's unclear: Exact configuration for impersonated credentials in Cloud Run
   - Recommendation: Use ADC for uploads, test signed URL generation during integration testing

3. **Cloud Tasks vs. FastAPI BackgroundTasks**
   - What we know: BackgroundTasks for quick operations, Cloud Tasks for resilient queuing
   - What's unclear: Threshold for when to use Cloud Tasks vs. BackgroundTasks
   - Recommendation: Use Cloud Tasks for any processing >10 seconds to ensure resilience

---

## Sources

### Primary (HIGH confidence)
- [Docling Documentation](https://docling-project.github.io/docling/) - Document conversion API, formats
- [Docling PyPI](https://pypi.org/project/docling/) - Version 2.70.0, dependencies
- [SQLAlchemy Async Documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) - Session management, engine configuration
- [Alembic Cookbook](https://alembic.sqlalchemy.org/en/latest/cookbook.html) - Async migration patterns
- [Google Cloud Storage Samples](https://cloud.google.com/storage/docs/samples/) - Upload, signed URLs
- [FastAPI Request Files](https://fastapi.tiangolo.com/tutorial/request-files/) - UploadFile handling

### Secondary (MEDIUM confidence)
- [Docling Memory Leak Issue #2209](https://github.com/docling-project/docling/issues/2209) - Memory leak with reused converter
- [Docling Large PDF Issue #1283](https://github.com/docling-project/docling/issues/1283) - Performance on large documents
- [fastapi-cloud-tasks GitHub](https://github.com/Adori/fastapi-cloud-tasks) - Cloud Tasks integration pattern
- [TestDriven.io FastAPI SQLAlchemy Tutorial](https://testdriven.io/blog/fastapi-sqlmodel/) - Alembic async setup

### Tertiary (LOW confidence)
- Medium articles on FastAPI file uploads - Patterns vary, validate against official docs
- Stack Overflow discussions on async SQLAlchemy - Edge cases may not apply

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Versions from Phase 1 pyproject.toml, verified with official docs
- Docling integration: HIGH - Official documentation + validated GitHub issues
- GCS patterns: HIGH - Official Google Cloud samples
- SQLAlchemy async: HIGH - Official SQLAlchemy 2.0 documentation
- Alembic async: MEDIUM - Community patterns, verify during implementation
- Memory/performance issues: HIGH - Multiple confirmed GitHub issues

**Research date:** 2026-01-23
**Valid until:** 2026-02-23 (30 days - stable libraries, verify Docling version updates)
