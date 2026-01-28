# Code Enhancement Guide: Detailed Implementation

**Project:** Loan Document Extraction System
**Date:** 2026-01-28
**Purpose:** Concrete code changes with before/after examples and rationale

---

## Table of Contents

1. [High-Priority Backend Enhancements](#high-priority-backend-enhancements)
2. [High-Priority Frontend Enhancements](#high-priority-frontend-enhancements)
3. [Medium-Priority Backend Enhancements](#medium-priority-backend-enhancements)
4. [Medium-Priority Frontend Enhancements](#medium-priority-frontend-enhancements)
5. [Low-Priority Enhancements](#low-priority-enhancements)

---

## High-Priority Backend Enhancements

### 1. Refactor DocumentService (604 LOC → 3 Services)

**File:** `backend/src/ingestion/document_service.py`

**Why Change:**
- **Single Responsibility Principle Violation:** One class handles 7 different responsibilities
- **Testing Difficulty:** Hard to mock dependencies and test in isolation
- **Maintenance Burden:** Changes ripple across entire 604-line file
- **Extension Challenges:** Adding features requires touching large class

**Current Code Structure:**
```python
# backend/src/ingestion/document_service.py (604 lines)
class DocumentService:
    """Handles EVERYTHING:
    - File validation (type, size)
    - File hashing (SHA-256)
    - Duplicate detection
    - GCS upload
    - Database record creation
    - Docling processing
    - OCR routing
    - Extraction routing
    - Borrower extraction
    - Borrower persistence
    - Status updates
    """

    def __init__(self, repository, gcs_client, docling_processor,
                 borrower_extractor, borrower_repository,
                 cloud_tasks_client, ocr_router, extraction_router):
        # 8 dependencies injected
        pass

    async def upload(self, file, method, ocr_mode):
        # Lines 154-600: Does everything listed above
        # Impossible to test individual concerns
```

**Proposed Code Structure:**

**1. UploadService (new file: ~150 LOC)**
```python
# backend/src/ingestion/upload_service.py
from pathlib import Path
import hashlib
from typing import BinaryIO

class UploadService:
    """Handles file validation, hashing, and GCS upload.

    Single Responsibility: Get file from user to storage.
    """

    ALLOWED_MIME_TYPES = {
        "application/pdf": "pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "image/png": "png",
        "image/jpeg": "jpg",
    }
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

    def __init__(self, gcs_client: GCSClient):
        self.gcs_client = gcs_client

    async def validate_file(self, file: BinaryIO, content_type: str) -> tuple[bool, str | None]:
        """Validate file type and size.

        Returns:
            (is_valid, error_message_if_invalid)
        """
        if content_type not in self.ALLOWED_MIME_TYPES:
            return False, f"Unsupported file type: {content_type}"

        file.seek(0, 2)  # Seek to end
        size = file.tell()
        file.seek(0)  # Reset

        if size > self.MAX_FILE_SIZE:
            return False, f"File too large: {size} bytes (max {self.MAX_FILE_SIZE})"

        return True, None

    def compute_hash(self, file_data: bytes) -> str:
        """Compute SHA-256 hash for duplicate detection."""
        return hashlib.sha256(file_data).hexdigest()

    async def upload_to_gcs(self, file_data: bytes, filename: str, file_hash: str) -> str:
        """Upload file to GCS.

        Returns:
            GCS path (gs://bucket/path)

        Raises:
            GCSUploadError: If upload fails
        """
        gcs_path = f"documents/{file_hash}/{filename}"
        try:
            return await self.gcs_client.upload(file_data, gcs_path)
        except Exception as e:
            raise GCSUploadError(f"Failed to upload {filename}: {e}") from e

# Testing becomes simple:
class TestUploadService:
    async def test_validate_file_rejects_large_files(self):
        service = UploadService(mock_gcs_client)
        large_file = BytesIO(b"x" * (51 * 1024 * 1024))
        is_valid, error = await service.validate_file(large_file, "application/pdf")
        assert not is_valid
        assert "too large" in error
```

**Why This Is Better:**
- **Testable:** Can test validation without GCS, hash without upload, etc.
- **Clear Boundary:** Everything about getting file from user to storage
- **Reusable:** Other services can use this for different workflows
- **Fast Tests:** Mock GCS, test validation logic in milliseconds

---

**2. ProcessingService (new file: ~250 LOC)**
```python
# backend/src/ingestion/processing_service.py
from uuid import UUID

class ProcessingService:
    """Handles document processing and extraction.

    Single Responsibility: Turn stored document into extracted data.
    """

    def __init__(self,
                 docling_processor: DoclingProcessor,
                 ocr_router: OCRRouter | None,
                 extraction_router: ExtractionRouter | None,
                 borrower_extractor: BorrowerExtractor):
        self.docling_processor = docling_processor
        self.ocr_router = ocr_router
        self.extraction_router = extraction_router
        self.borrower_extractor = borrower_extractor

    async def process_document(self,
                               document_id: UUID,
                               gcs_path: str,
                               file_type: str,
                               extraction_method: Literal["docling", "langextract", "auto"],
                               ocr_mode: Literal["auto", "force", "skip"]) -> ProcessingResult:
        """Process document and extract borrowers.

        Returns:
            ProcessingResult with status, borrowers, and any errors
        """
        # 1. Route through OCR if needed
        if self.ocr_router and ocr_mode != "skip":
            file_data = await self.gcs_client.download(gcs_path)
            ocr_result = await self.ocr_router.process(file_data, file_type, ocr_mode)
            if ocr_result.processed:
                file_data = ocr_result.processed_data

        # 2. Route through extraction method
        if self.extraction_router:
            text = await self.extraction_router.extract(
                file_data, file_type, extraction_method
            )
        else:
            # Fallback to Docling
            text = await self.docling_processor.process(file_data, file_type)

        # 3. Extract borrowers
        borrowers = await self.borrower_extractor.extract(text, document_id)

        return ProcessingResult(
            status="completed" if borrowers else "completed_no_extraction",
            borrowers=borrowers,
            page_count=len(text.pages),
        )

@dataclass
class ProcessingResult:
    status: str
    borrowers: list[BorrowerRecord]
    page_count: int
    error: str | None = None
```

**Why This Is Better:**
- **Focused:** Only concerns itself with processing logic
- **No Storage:** Doesn't know about database or GCS upload
- **Pure Function:** Given inputs, produces outputs
- **Testable:** Mock file data, test extraction logic

---

**3. PersistenceService (new file: ~150 LOC)**
```python
# backend/src/ingestion/persistence_service.py
from uuid import UUID

class PersistenceService:
    """Handles borrower persistence with partial success.

    Single Responsibility: Save extracted data to database.
    """

    def __init__(self,
                 document_repository: DocumentRepository,
                 borrower_repository: BorrowerRepository):
        self.document_repo = document_repository
        self.borrower_repo = borrower_repository

    async def persist_borrowers(self,
                                document_id: UUID,
                                borrowers: list[BorrowerRecord]) -> PersistenceResult:
        """Persist borrowers with partial success handling.

        Returns:
            PersistenceResult indicating success/partial/failure
        """
        if not borrowers:
            return PersistenceResult(
                status=PersistenceStatus.NONE,
                persisted_count=0,
                total_count=0
            )

        persisted = []
        failures = []

        for borrower_record in borrowers:
            try:
                borrower = await self._persist_single_borrower(
                    document_id, borrower_record
                )
                persisted.append(borrower)
            except Exception as e:
                logger.error(
                    "Failed to persist borrower",
                    extra={
                        "document_id": str(document_id),
                        "borrower_ssn_hash": borrower_record.ssn_hash,
                        "error": str(e)
                    }
                )
                failures.append({
                    "ssn": borrower_record.ssn_last_4,
                    "error": str(e)
                })

        # Determine status
        if len(persisted) == len(borrowers):
            status = PersistenceStatus.COMPLETE
        elif len(persisted) > 0:
            status = PersistenceStatus.PARTIAL
        else:
            status = PersistenceStatus.FAILED

        return PersistenceResult(
            status=status,
            persisted_count=len(persisted),
            total_count=len(borrowers),
            failures=failures
        )

    async def _persist_single_borrower(self,
                                       document_id: UUID,
                                       record: BorrowerRecord) -> Borrower:
        """Persist single borrower with all related entities."""
        borrower = Borrower(
            document_id=document_id,
            ssn=record.ssn,
            # ... other fields
        )
        borrower = await self.borrower_repo.create(borrower)

        # Persist income records
        for income in record.income_records:
            income_model = IncomeRecordModel(
                borrower_id=borrower.id,
                amount=income.amount,
                # ... other fields
            )
            await self.borrower_repo.add_income_record(income_model)

        return borrower

@dataclass
class PersistenceResult:
    status: PersistenceStatus
    persisted_count: int
    total_count: int
    failures: list[dict] = field(default_factory=list)
```

**Why This Is Better:**
- **Clear Semantics:** All about saving to database
- **Partial Success:** Cleanly handles "some succeeded, some failed"
- **Transaction Boundaries:** Can wrap in transactions easily
- **Testable:** Mock repository, test persistence logic

---

**4. Updated DocumentService (orchestrator: ~200 LOC)**
```python
# backend/src/ingestion/document_service.py (refactored)
class DocumentService:
    """Orchestrates document upload workflow.

    Coordinates UploadService, ProcessingService, and PersistenceService.
    """

    def __init__(self,
                 repository: DocumentRepository,
                 upload_service: UploadService,
                 processing_service: ProcessingService,
                 persistence_service: PersistenceService,
                 cloud_tasks_client: CloudTasksClient | None = None):
        self.repository = repository
        self.upload_service = upload_service
        self.processing_service = processing_service
        self.persistence_service = persistence_service
        self.cloud_tasks_client = cloud_tasks_client

    async def upload(self,
                     file: BinaryIO,
                     filename: str,
                     content_type: str,
                     method: Literal["docling", "langextract", "auto"],
                     ocr_mode: Literal["auto", "force", "skip"]) -> Document:
        """Upload and process document."""

        # 1. Validate file
        is_valid, error = await self.upload_service.validate_file(file, content_type)
        if not is_valid:
            raise DocumentUploadError(error)

        # 2. Compute hash and check duplicates
        file_data = file.read()
        file_hash = self.upload_service.compute_hash(file_data)

        duplicate = await self.repository.get_by_hash(file_hash)
        if duplicate:
            raise DocumentUploadError(f"Duplicate document: {duplicate.id}")

        # 3. Upload to GCS
        gcs_path = await self.upload_service.upload_to_gcs(
            file_data, filename, file_hash
        )

        # 4. Create database record
        document = Document(
            id=uuid4(),
            filename=filename,
            file_type=self.upload_service.ALLOWED_MIME_TYPES[content_type],
            file_hash=file_hash,
            gcs_path=gcs_path,
            extraction_method=method,
            status=DocumentStatus.PENDING,
        )
        document = await self.repository.create(document)

        # 5. Commit before processing (Fix 1 from FIXES_IMPLEMENTED.md)
        await self.repository.session.commit()

        # 6. Process async or sync
        if self.cloud_tasks_client:
            # Async: Queue task
            await self.cloud_tasks_client.create_task(
                endpoint="/api/tasks/process-document",
                payload={"document_id": str(document.id)}
            )
            return document
        else:
            # Sync: Process now
            result = await self._process_document_sync(document, method, ocr_mode)
            return result

    async def _process_document_sync(self,
                                     document: Document,
                                     method: str,
                                     ocr_mode: str) -> Document:
        """Process document synchronously (local dev)."""
        try:
            # Process
            processing_result = await self.processing_service.process_document(
                document_id=document.id,
                gcs_path=document.gcs_path,
                file_type=document.file_type,
                extraction_method=method,
                ocr_mode=ocr_mode
            )

            # Update document
            document.status = DocumentStatus.COMPLETED
            document.page_count = processing_result.page_count

            # Persist borrowers
            persistence_result = await self.persistence_service.persist_borrowers(
                document_id=document.id,
                borrowers=processing_result.borrowers
            )

            # Update persistence status
            document.persistence_status = persistence_result.status
            if persistence_result.status == PersistenceStatus.PARTIAL:
                document.persistence_detail = (
                    f"{persistence_result.persisted_count}/{persistence_result.total_count} "
                    f"borrowers persisted. Failures: {persistence_result.failures}"
                )

            await self.repository.update(document)
            await self.repository.session.commit()

        except Exception as e:
            document.status = DocumentStatus.FAILED
            document.error_message = str(e)
            await self.repository.update(document)
            await self.repository.session.commit()
            logger.error("Document processing failed", extra={
                "document_id": str(document.id),
                "error": str(e)
            })

        return document
```

**Why This Is Better:**
- **High-Level Orchestration:** Coordinates services without implementation details
- **~200 LOC vs 604 LOC:** Much easier to understand
- **Separation of Concerns:** Each service has a clear, single responsibility
- **Maintainable:** Changes to upload logic don't affect processing logic
- **Testable:** Mock services, test orchestration

**Migration Steps:**
1. Create new service files (upload_service.py, processing_service.py, persistence_service.py)
2. Extract logic from document_service.py to new services
3. Update document_service.py to use new services
4. Update dependencies.py to inject new services
5. Update tests to test each service independently
6. Remove old monolithic methods from document_service.py

---

### 2. Replace Global Singleton Pattern with FastAPI Lifespan

**Files:**
- `backend/src/api/dependencies.py` (lines 31-284)
- `backend/src/api/main.py` (add lifespan)

**Why Change:**
- **Global Mutable State:** Using `global _gcs_client` is anti-pattern
- **No Cleanup:** Resources never explicitly closed/released
- **Testing Difficulty:** Can't easily inject fresh instances for tests
- **Not FastAPI Idiomatic:** FastAPI has built-in lifecycle management

**Current Code:**
```python
# backend/src/api/dependencies.py (lines 31-58)
_gcs_client: GCSClient | None = None

def get_gcs_client() -> GCSClient:
    """Get or create GCS client singleton."""
    global _gcs_client  # ❌ Global variable

    if _gcs_client is None:  # ❌ Manual singleton management
        bucket_name = settings.gcs_bucket
        if not bucket_name:
            # ❌ MagicMock in production code!
            from unittest.mock import MagicMock
            _gcs_client = MagicMock(spec=GCSClient)
            _gcs_client.upload = MagicMock(return_value="gs://mock-bucket/mock-path")
        else:
            _gcs_client = GCSClient(bucket_name)

    return _gcs_client

GCSClientDep = Annotated[GCSClient, Depends(get_gcs_client)]

# Same pattern repeated for:
# - _docling_processor
# - _gemini_client
# - _borrower_extractor
# - _borrower_deduplicator
# - _complexity_classifier
# - _confidence_calculator
# - _consistency_validator
```

**Problems:**
1. **No Resource Cleanup:** What if GCS client has connections to close?
2. **Test Isolation:** Tests can't easily get fresh instances
3. **Race Conditions:** Not actually thread-safe (FastAPI handles it, but still wrong pattern)

**Proposed Code:**

**Step 1: Add Lifespan Manager**
```python
# backend/src/api/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle: startup and shutdown."""

    # ============ STARTUP ============
    logger.info("Initializing application resources...")

    # Initialize GCS client
    if settings.gcs_bucket:
        app.state.gcs_client = GCSClient(settings.gcs_bucket)
    else:
        app.state.gcs_client = NullGCSClient()  # Proper null object, not MagicMock

    # Initialize processors
    app.state.docling_processor = DoclingProcessor(
        artifacts_path=settings.docling_artifacts_path,
        do_ocr=False  # Use separate OCR service
    )

    # Initialize LLM clients
    app.state.gemini_client = GeminiClient(
        api_key=settings.gemini_api_key,
        model_name="gemini-2.0-flash-exp"
    )

    # Initialize extraction components
    app.state.field_validator = FieldValidator()
    app.state.complexity_classifier = ComplexityClassifier()
    app.state.confidence_calculator = ConfidenceCalculator(app.state.field_validator)
    app.state.consistency_validator = ConsistencyValidator()
    app.state.borrower_deduplicator = BorrowerDeduplicator()
    app.state.document_chunker = DocumentChunker()

    app.state.borrower_extractor = BorrowerExtractor(
        llm_client=app.state.gemini_client,
        validator=app.state.field_validator,
        deduplicator=app.state.borrower_deduplicator,
        confidence_calculator=app.state.confidence_calculator,
        consistency_validator=app.state.consistency_validator,
        complexity_classifier=app.state.complexity_classifier,
        chunker=app.state.document_chunker,
    )

    # Initialize OCR components (if configured)
    if settings.lightonocr_service_url:
        app.state.gpu_ocr_client = LightOnOCRClient(
            service_url=settings.lightonocr_service_url,
            timeout=30  # 30s for cold starts
        )
        app.state.ocr_router = OCRRouter(
            gpu_client=app.state.gpu_ocr_client,
            docling_processor=app.state.docling_processor
        )
    else:
        app.state.ocr_router = None

    # Initialize extraction router (v2.0 dual pipeline)
    app.state.langextract_processor = LangExtractProcessor()
    app.state.extraction_router = ExtractionRouter(
        docling_processor=app.state.docling_processor,
        langextract_processor=app.state.langextract_processor
    )

    # Initialize Cloud Tasks client (if configured)
    if settings.gcp_project_id and settings.cloud_run_service_url:
        app.state.cloud_tasks_client = CloudTasksClient(
            project_id=settings.gcp_project_id,
            location=settings.gcp_region,
            queue_name="document-processing",
            service_url=settings.cloud_run_service_url,
        )
    else:
        app.state.cloud_tasks_client = None

    logger.info("Application resources initialized successfully")

    yield  # Application runs here

    # ============ SHUTDOWN ============
    logger.info("Shutting down application resources...")

    # Close connections if needed
    if hasattr(app.state.gcs_client, 'close'):
        await app.state.gcs_client.close()

    if hasattr(app.state.gemini_client, 'close'):
        await app.state.gemini_client.close()

    logger.info("Application shutdown complete")


# Create FastAPI app with lifespan
app = FastAPI(
    title="Loan Extraction API",
    version="2.0.0",
    lifespan=lifespan  # ✅ Register lifespan manager
)
```

**Why This Is Better:**
- **Built-in Pattern:** FastAPI's recommended approach
- **Resource Management:** Startup and shutdown clearly defined
- **No Globals:** All state in `app.state`
- **Testable:** Can create test app with different state

**Step 2: Update Dependencies**
```python
# backend/src/api/dependencies.py (refactored)
from fastapi import Request

def get_gcs_client(request: Request) -> GCSClient:
    """Get GCS client from application state."""
    return request.app.state.gcs_client

def get_docling_processor(request: Request) -> DoclingProcessor:
    """Get Docling processor from application state."""
    return request.app.state.docling_processor

def get_gemini_client(request: Request) -> GeminiClient:
    """Get Gemini client from application state."""
    return request.app.state.gemini_client

def get_borrower_extractor(request: Request) -> BorrowerExtractor:
    """Get borrower extractor from application state."""
    return request.app.state.borrower_extractor

# ... etc for all services

# Type aliases remain the same
GCSClientDep = Annotated[GCSClient, Depends(get_gcs_client)]
DoclingProcessorDep = Annotated[DoclingProcessor, Depends(get_docling_processor)]
# ... etc
```

**Why This Is Better:**
- **No Global Variables:** Everything accessed via `request.app.state`
- **Clear Lifecycle:** Resources created on startup, cleaned on shutdown
- **Testable:** Can inject different state for tests

**Step 3: Update Tests**
```python
# backend/tests/conftest.py
import pytest
from fastapi import FastAPI
from contextlib import asynccontextmanager

@pytest.fixture
def app():
    """Create test app with mock state."""

    @asynccontextmanager
    async def test_lifespan(app: FastAPI):
        # Initialize with mocks
        app.state.gcs_client = MagicMock(spec=GCSClient)  # ✅ Mocks in tests, not production
        app.state.docling_processor = MagicMock(spec=DoclingProcessor)
        # ... other mocks
        yield

    app = FastAPI(lifespan=test_lifespan)
    # Add routes...
    return app

@pytest.fixture
async def client(app):
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
```

**Migration Steps:**
1. Add lifespan function to main.py
2. Initialize all singletons in lifespan startup
3. Update dependencies.py to use `request.app.state`
4. Update tests to use test app with mocked state
5. Remove all `global _variable` declarations
6. Test that all endpoints still work

---

### 3. Replace Broad Exception Handling with Specific Exceptions

**Files:** Multiple files with `except Exception as e:`

**Why Change:**
- **Catches Too Much:** Catches programmer errors (AttributeError, TypeError, etc.)
- **Hides Bugs:** A typo becomes a "processing failure" instead of immediate crash
- **Debugging Difficulty:** Logs show "Exception" but no specificity
- **Wrong Abstraction:** Not all exceptions are expected failures

**Current Code:**
```python
# backend/src/ingestion/document_service.py (line 268)
try:
    gcs_path = await self.gcs_client.upload(file_data, gcs_path)
except Exception as e:  # ❌ Too broad!
    logger.error("GCS upload failed", extra={"error": str(e)})
    document.status = DocumentStatus.FAILED
    document.error_message = f"GCS upload failed: {str(e)}"
    await self.repository.update(document)
    await self.repository.session.commit()
```

**Problems:**
1. If you typo `gcs_paht` instead of `gcs_path`, it catches NameError → silent failure
2. If `logger` is undefined, catches NameError → infinite confusion
3. If there's a programming bug in `gcs_client.upload`, catches it → bug goes unfixed

**Proposed Solution:**

**Step 1: Define Exception Hierarchy**
```python
# backend/src/api/errors.py (add to existing)

# ============ Base Exceptions ============
class LoanExtractionError(Exception):
    """Base exception for all application errors."""
    pass

# ============ Storage Exceptions ============
class StorageError(LoanExtractionError):
    """Base for storage-related errors."""
    pass

class GCSUploadError(StorageError):
    """Failed to upload file to GCS."""
    pass

class GCSDownloadError(StorageError):
    """Failed to download file from GCS."""
    pass

class DatabaseError(StorageError):
    """Database operation failed."""
    pass

# ============ Processing Exceptions ============
class ProcessingError(LoanExtractionError):
    """Base for document processing errors."""
    pass

class DocumentProcessingError(ProcessingError):
    """Docling/LangExtract processing failed."""
    pass

class OCRError(ProcessingError):
    """OCR processing failed."""
    pass

class GPUServiceError(OCRError):
    """GPU OCR service unavailable or failed."""
    pass

# ============ Extraction Exceptions ============
class ExtractionError(LoanExtractionError):
    """Base for extraction errors."""
    pass

class LLMError(ExtractionError):
    """Gemini API call failed."""
    pass

class ValidationError(ExtractionError):
    """Extracted data validation failed."""
    pass

# ============ Business Logic Exceptions ============
class DocumentUploadError(LoanExtractionError):
    """File upload rejected (validation, duplicate, etc.)."""
    pass

class EntityNotFoundError(LoanExtractionError):
    """Requested entity not found in database."""
    pass
```

**Why This Is Better:**
- **Specific:** Each exception type represents a specific failure mode
- **Catchable:** Can catch `StorageError` to handle all storage issues
- **Informative:** Exception type tells you what failed
- **Hierarchy:** Related exceptions grouped under base classes

**Step 2: Raise Specific Exceptions**
```python
# backend/src/storage/gcs_client.py
class GCSClient:
    async def upload(self, file_data: bytes, path: str) -> str:
        """Upload file to GCS."""
        try:
            blob = self.bucket.blob(path)
            blob.upload_from_string(file_data)
            return f"gs://{self.bucket.name}/{path}"
        except google.cloud.exceptions.GoogleCloudError as e:
            # ✅ Catch specific GCS errors, raise our exception
            raise GCSUploadError(f"Failed to upload {path}: {e}") from e
        # ❌ Don't catch Exception - let programming errors crash

# backend/src/extraction/llm_client.py
class GeminiClient:
    async def generate(self, prompt: str) -> str:
        """Call Gemini API."""
        try:
            response = await self.client.generate_content(prompt)
            return response.text
        except google.api_core.exceptions.GoogleAPIError as e:
            # ✅ Catch specific API errors
            raise LLMError(f"Gemini API call failed: {e}") from e
        except Exception as e:
            # If it's not a known API error, let it propagate
            raise
```

**Step 3: Catch Specific Exceptions**
```python
# backend/src/ingestion/document_service.py (refactored)
async def upload(self, file: BinaryIO, filename: str, ...):
    try:
        # Validate
        is_valid, error = await self.upload_service.validate_file(file, content_type)
        if not is_valid:
            raise DocumentUploadError(error)

        # Upload to GCS
        gcs_path = await self.upload_service.upload_to_gcs(file_data, filename, file_hash)

    except DocumentUploadError:
        # ✅ Expected: validation failure
        raise  # Re-raise to caller
    except GCSUploadError as e:
        # ✅ Expected: GCS failure
        logger.error(
            "GCS upload failed",
            extra={
                "filename": filename,
                "error_type": "GCSUploadError",
                "error": str(e)
            },
            exc_info=e
        )
        document.status = DocumentStatus.FAILED
        document.error_message = f"Storage upload failed: {e}"
        await self.repository.update(document)
        await self.repository.session.commit()
        return document
    except NetworkError as e:
        # ✅ Expected: network failure
        logger.error("Network error during upload", extra={"error": str(e)})
        raise DocumentUploadError(f"Network error: {e}") from e
    # ❌ Don't catch Exception
    # If there's a NameError or AttributeError, we WANT it to crash
    # so we can fix the bug immediately
```

**Why This Is Better:**
- **Only Expected Failures:** Only catches errors we know can happen
- **Programming Errors Surface:** Typos, missing variables, etc. crash immediately
- **Better Logs:** Error type in logs tells you exactly what failed
- **Easier Debugging:** Stack trace preserved with `from e`

**Step 4: Handle at API Level**
```python
# backend/src/api/routers/documents.py
@router.post("/", status_code=201)
async def upload_document(
    file: UploadFile,
    doc_service: DocumentServiceDep
) -> DocumentResponse:
    """Upload document endpoint."""
    try:
        document = await doc_service.upload(
            file.file,
            file.filename,
            file.content_type,
            method=extraction_method,
            ocr_mode=ocr_mode
        )
        return DocumentResponse.from_orm(document)

    except DocumentUploadError as e:
        # ✅ Expected: user error (bad file, duplicate, etc.)
        raise HTTPException(status_code=400, detail=str(e))

    except StorageError as e:
        # ✅ Expected: infrastructure failure
        logger.error("Storage error during upload", exc_info=e)
        raise HTTPException(
            status_code=503,
            detail="Storage service temporarily unavailable"
        )

    # ❌ Don't catch Exception here either
    # Let FastAPI's exception handler catch programming errors
    # and return 500 Internal Server Error
```

**Migration Steps:**
1. Add exception hierarchy to errors.py
2. Update low-level modules (gcs_client, llm_client, etc.) to raise specific exceptions
3. Update service layer (document_service) to catch specific exceptions
4. Update API layer to catch specific exceptions and return appropriate HTTP codes
5. Remove all `except Exception as e:` blocks
6. Run tests, fix any newly surfaced bugs (this is the point!)
7. Add tests for each exception type

---

### 4. Remove MagicMock from Production Code

**File:** `backend/src/api/dependencies.py` (lines 48-54)

**Why Change:**
- **Test Framework in Production:** unittest.mock should NEVER be imported outside tests
- **Unpredictable Behavior:** MagicMock silently accepts any method call
- **No Type Safety:** Mock doesn't match GCSClient interface
- **Debugging Nightmare:** When mock behaves wrong, very hard to debug

**Current Code:**
```python
# backend/src/api/dependencies.py (lines 48-54)
def get_gcs_client() -> GCSClient:
    """Get or create GCS client singleton."""
    global _gcs_client

    if _gcs_client is None:
        bucket_name = settings.gcs_bucket
        if not bucket_name:
            # ❌ NEVER do this in production code!
            from unittest.mock import MagicMock
            _gcs_client = MagicMock(spec=GCSClient)
            _gcs_client.upload = MagicMock(return_value="gs://mock-bucket/mock-path")
            _gcs_client.download = MagicMock(return_value=b"mock content")
            _gcs_client.exists = MagicMock(return_value=True)
        else:
            _gcs_client = GCSClient(bucket_name)

    return _gcs_client
```

**Problems:**
1. **Production Import:** `from unittest.mock import MagicMock` in production code
2. **Silent Failures:** If you call `_gcs_client.uplod(...)` (typo), Mock returns another Mock instead of error
3. **Type Confusion:** Type checker thinks it's `GCSClient`, but runtime it's `MagicMock`

**Proposed Solution: Null Object Pattern**

**Step 1: Create NullGCSClient**
```python
# backend/src/storage/gcs_client.py

class NullGCSClient:
    """Local development GCS client that stores files in temp directory.

    Used when GCS_BUCKET environment variable is not set.
    Provides same interface as GCSClient for local testing.
    """

    def __init__(self, local_dir: Path = Path("/tmp/loan-docs")):
        self.local_dir = local_dir
        self.local_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            "Using NullGCSClient (local storage)",
            extra={"local_dir": str(self.local_dir)}
        )

    async def upload(self, file_data: bytes, path: str) -> str:
        """Save file to local directory."""
        file_path = self.local_dir / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(file_data)

        local_uri = f"local://{file_path}"
        logger.debug(
            "File saved locally",
            extra={"path": path, "local_path": str(file_path)}
        )
        return local_uri

    async def download(self, path: str) -> bytes:
        """Load file from local directory."""
        # Handle both "local:///tmp/..." and "documents/hash/file.pdf"
        if path.startswith("local://"):
            file_path = Path(path.replace("local://", ""))
        else:
            file_path = self.local_dir / path

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        return file_path.read_bytes()

    async def exists(self, path: str) -> bool:
        """Check if file exists locally."""
        if path.startswith("local://"):
            file_path = Path(path.replace("local://", ""))
        else:
            file_path = self.local_dir / path

        return file_path.exists()

    async def delete(self, path: str) -> None:
        """Delete file from local directory."""
        if path.startswith("local://"):
            file_path = Path(path.replace("local://", ""))
        else:
            file_path = self.local_dir / path

        if file_path.exists():
            file_path.unlink()

    async def get_signed_url(self, path: str, expiration_seconds: int = 3600) -> str:
        """Return local file path (no signing needed)."""
        if path.startswith("local://"):
            return path
        return f"local://{self.local_dir / path}"

    async def close(self) -> None:
        """No-op for local storage."""
        pass


# ✅ Common interface (could be ABC, but duck typing works)
class GCSClient:
    """Real GCS client."""
    # ... existing implementation

    async def close(self) -> None:
        """Close GCS client connections."""
        # Cleanup if needed
        pass
```

**Why This Is Better:**
- **Real Implementation:** Actually stores files (locally instead of GCS)
- **Same Interface:** Works exactly like GCSClient
- **Debuggable:** If something goes wrong, you can inspect /tmp/loan-docs
- **Testable:** Can test with real files locally
- **No Mocks:** No unittest.mock import in production code

**Step 2: Update Dependencies/Lifespan**
```python
# backend/src/api/main.py (in lifespan startup)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize GCS client
    if settings.gcs_bucket:
        app.state.gcs_client = GCSClient(settings.gcs_bucket)
        logger.info(f"Using GCS bucket: {settings.gcs_bucket}")
    else:
        app.state.gcs_client = NullGCSClient()  # ✅ Proper null object
        logger.info("Using local file storage (no GCS bucket configured)")

    yield

    # Cleanup
    await app.state.gcs_client.close()
```

**Step 3: Update Tests (Use Real Mocks)**
```python
# backend/tests/conftest.py
@pytest.fixture
def mock_gcs_client():
    """Create mock GCS client for tests."""
    mock = MagicMock(spec=GCSClient)  # ✅ Mocks in tests, not production!
    mock.upload.return_value = "gs://test-bucket/test-path"
    mock.download.return_value = b"test content"
    mock.exists.return_value = True
    return mock

@pytest.fixture
async def test_app(mock_gcs_client):
    """Create test app with mocked dependencies."""
    @asynccontextmanager
    async def test_lifespan(app: FastAPI):
        app.state.gcs_client = mock_gcs_client  # Inject mock
        # ... other state
        yield

    app = FastAPI(lifespan=test_lifespan)
    # Add routes...
    return app
```

**Migration Steps:**
1. Create NullGCSClient class in gcs_client.py
2. Update lifespan to use NullGCSClient when bucket not configured
3. Remove MagicMock import from dependencies.py
4. Test locally without GCS_BUCKET set → should use NullGCSClient
5. Verify files stored in /tmp/loan-docs
6. Test with GCS_BUCKET set → should use real GCSClient

---

### 5. Centralize Validation Logic (DRY Principle)

**Files:**
- `backend/src/extraction/validation.py` (format checking)
- `backend/src/models/borrower.py` (Pydantic validators)
- `backend/src/extraction/extractor.py` (LLM prompts)

**Why Change:**
- **Triple Duplication:** Same validation rules in 3 places
- **Inconsistency Risk:** Change in one place, forget the others
- **Maintenance Burden:** Add new field? Update 3 files
- **Prompt Drift:** LLM prompts can become outdated

**Current Code (Duplication):**

**Location 1: validation.py**
```python
# backend/src/extraction/validation.py
def is_valid_ssn(ssn: str) -> bool:
    """Validate SSN format: XXX-XX-XXXX or XXXXXXXXX."""
    if not ssn:
        return False

    # Remove hyphens
    digits = ssn.replace("-", "").replace(" ", "")

    # Must be 9 digits
    if not digits.isdigit() or len(digits) != 9:
        return False

    # First digit can't be 9
    if digits[0] == "9":
        return False

    # Can't be all same digit
    if len(set(digits)) == 1:
        return False

    return True
```

**Location 2: borrower.py**
```python
# backend/src/models/borrower.py
class BorrowerRecord(BaseModel):
    ssn: str | None = None

    @field_validator("ssn")
    def validate_ssn(cls, v: str | None) -> str | None:
        if v is None:
            return None

        # ❌ DUPLICATE validation logic
        digits = v.replace("-", "").replace(" ", "")

        if not digits.isdigit() or len(digits) != 9:
            raise ValueError("SSN must be 9 digits")

        if digits[0] == "9":
            raise ValueError("SSN cannot start with 9")

        # Return normalized (XXX-XX-XXXX)
        return f"{digits[0:3]}-{digits[3:5]}-{digits[5:9]}"
```

**Location 3: extractor.py (LLM prompts)**
```python
# backend/src/extraction/extractor.py
EXTRACTION_PROMPT = """
Extract borrower information from loan documents.

SSN: Social Security Number in XXX-XX-XXXX format. Must be 9 digits, cannot start with 9.
Phone: 10-digit US phone number in format (XXX) XXX-XXXX.
ZIP: 5-digit ZIP code, optionally followed by -XXXX.
...
"""
# ❌ DUPLICATE: Validation rules hardcoded in string
```

**Problems:**
1. **Add New Rule:** Need to update 3 files
2. **Inconsistency:** validation.py allows "000-00-0001" but borrower.py rejects "all same digit"
3. **Prompt Drift:** LLM might extract "9XX-XX-XXXX" because prompt doesn't mention the rule

**Proposed Solution: Single Source of Truth**

**Step 1: Create Centralized Validator**
```python
# backend/src/validation/field_validators.py (new file)
from typing import Literal
import re
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """Result of field validation."""
    is_valid: bool
    normalized_value: str | None = None  # Value after normalization
    error_message: str | None = None  # If invalid

class FieldValidators:
    """Centralized field validation with consistent rules.

    Single source of truth for all validation logic.
    """

    # ============ SSN Validation ============

    @staticmethod
    def validate_ssn(value: str | None) -> ValidationResult:
        """Validate and normalize SSN.

        Rules:
        - Must be 9 digits (hyphens/spaces removed)
        - Cannot start with 9 (not a valid SSN area number)
        - Cannot be all zeros or all same digit
        - Cannot be 123-45-6789 (test SSN)

        Returns:
            ValidationResult with normalized SSN (XXX-XX-XXXX) if valid
        """
        if value is None or not value.strip():
            return ValidationResult(
                is_valid=False,
                error_message="SSN is required"
            )

        # Remove formatting
        digits = value.replace("-", "").replace(" ", "").strip()

        # Check digit count
        if not digits.isdigit():
            return ValidationResult(
                is_valid=False,
                error_message="SSN must contain only digits"
            )

        if len(digits) != 9:
            return ValidationResult(
                is_valid=False,
                error_message=f"SSN must be 9 digits, got {len(digits)}"
            )

        # Check area number (first 3 digits)
        area = digits[0:3]
        if area[0] == "9":
            return ValidationResult(
                is_valid=False,
                error_message="SSN cannot start with 9"
            )

        if area == "000" or area == "666":
            return ValidationResult(
                is_valid=False,
                error_message="Invalid SSN area number"
            )

        # Check for invalid patterns
        if len(set(digits)) == 1:
            return ValidationResult(
                is_valid=False,
                error_message="SSN cannot be all same digit"
            )

        if digits == "123456789":
            return ValidationResult(
                is_valid=False,
                error_message="Invalid test SSN"
            )

        # Normalize to XXX-XX-XXXX
        normalized = f"{digits[0:3]}-{digits[3:5]}-{digits[5:9]}"

        return ValidationResult(
            is_valid=True,
            normalized_value=normalized
        )

    @staticmethod
    def get_ssn_description() -> str:
        """Get SSN validation rules for LLM prompts."""
        return (
            "Social Security Number in XXX-XX-XXXX format. "
            "Must be 9 digits. Cannot start with 9. "
            "Cannot be 000 or 666 in first 3 digits. "
            "Cannot be all same digit or 123-45-6789."
        )

    # ============ Phone Validation ============

    @staticmethod
    def validate_phone(value: str | None) -> ValidationResult:
        """Validate and normalize phone number.

        Rules:
        - Must be 10 digits (US phone numbers)
        - Area code cannot be 000, 555, or 911
        - Accepts formats: (123) 456-7890, 123-456-7890, 1234567890

        Returns:
            ValidationResult with normalized phone (XXX) XXX-XXXX if valid
        """
        if value is None or not value.strip():
            return ValidationResult(
                is_valid=False,
                error_message="Phone number is required"
            )

        # Remove formatting
        digits = re.sub(r'[^\d]', '', value)

        # Handle +1 prefix
        if digits.startswith("1") and len(digits) == 11:
            digits = digits[1:]

        if len(digits) != 10:
            return ValidationResult(
                is_valid=False,
                error_message=f"Phone must be 10 digits, got {len(digits)}"
            )

        # Check area code
        area_code = digits[0:3]
        if area_code in ("000", "555", "911"):
            return ValidationResult(
                is_valid=False,
                error_message=f"Invalid area code: {area_code}"
            )

        # Normalize to (XXX) XXX-XXXX
        normalized = f"({digits[0:3]}) {digits[3:6]}-{digits[6:10]}"

        return ValidationResult(
            is_valid=True,
            normalized_value=normalized
        )

    @staticmethod
    def get_phone_description() -> str:
        """Get phone validation rules for LLM prompts."""
        return (
            "10-digit US phone number in format (XXX) XXX-XXXX. "
            "Area code cannot be 000, 555, or 911."
        )

    # ============ ZIP Code Validation ============

    @staticmethod
    def validate_zip(value: str | None) -> ValidationResult:
        """Validate and normalize ZIP code.

        Rules:
        - 5-digit ZIP code
        - Optionally followed by -XXXX (ZIP+4)

        Returns:
            ValidationResult with normalized ZIP (XXXXX or XXXXX-XXXX)
        """
        if value is None or not value.strip():
            return ValidationResult(
                is_valid=False,
                error_message="ZIP code is required"
            )

        value = value.strip()

        # Check format
        if not re.match(r'^\d{5}(-\d{4})?$', value):
            return ValidationResult(
                is_valid=False,
                error_message="ZIP must be 5 digits or 5+4 format"
            )

        return ValidationResult(
            is_valid=True,
            normalized_value=value
        )

    @staticmethod
    def get_zip_description() -> str:
        """Get ZIP validation rules for LLM prompts."""
        return "5-digit ZIP code, optionally followed by -XXXX (ZIP+4)."

    # ============ Year Validation ============

    @staticmethod
    def validate_year(value: int | str | None,
                      field_name: str = "year") -> ValidationResult:
        """Validate year is reasonable.

        Rules:
        - Between 1900 and current year + 1
        - Not in far future
        """
        if value is None:
            return ValidationResult(
                is_valid=False,
                error_message=f"{field_name} is required"
            )

        try:
            year = int(value)
        except (ValueError, TypeError):
            return ValidationResult(
                is_valid=False,
                error_message=f"{field_name} must be a number"
            )

        from datetime import datetime, timezone
        current_year = datetime.now(timezone.utc).year

        if year < 1900:
            return ValidationResult(
                is_valid=False,
                error_message=f"{field_name} cannot be before 1900"
            )

        if year > current_year + 1:
            return ValidationResult(
                is_valid=False,
                error_message=f"{field_name} cannot be in future"
            )

        return ValidationResult(
            is_valid=True,
            normalized_value=str(year)
        )

    @staticmethod
    def get_year_description() -> str:
        """Get year validation rules for LLM prompts."""
        from datetime import datetime, timezone
        current_year = datetime.now(timezone.utc).year
        return f"4-digit year between 1900 and {current_year + 1}."
```

**Why This Is Better:**
- **Single Source of Truth:** All validation logic in one place
- **Consistent:** Same rules everywhere
- **Testable:** Can unit test each validator
- **Maintainable:** Add new rule once, used everywhere
- **Prompt Sync:** Descriptions generated from code

**Step 2: Use in Pydantic Models**
```python
# backend/src/models/borrower.py (refactored)
from src.validation.field_validators import FieldValidators

class BorrowerRecord(BaseModel):
    ssn: str | None = None
    phone: str | None = None
    zip_code: str | None = None

    @field_validator("ssn")
    def validate_ssn(cls, v: str | None) -> str | None:
        if v is None:
            return None

        # ✅ Use centralized validator
        result = FieldValidators.validate_ssn(v)

        if not result.is_valid:
            raise ValueError(result.error_message)

        return result.normalized_value

    @field_validator("phone")
    def validate_phone(cls, v: str | None) -> str | None:
        if v is None:
            return None

        # ✅ Use centralized validator
        result = FieldValidators.validate_phone(v)

        if not result.is_valid:
            raise ValueError(result.error_message)

        return result.normalized_value

    @field_validator("zip_code")
    def validate_zip(cls, v: str | None) -> str | None:
        if v is None:
            return None

        # ✅ Use centralized validator
        result = FieldValidators.validate_zip(v)

        if not result.is_valid:
            raise ValueError(result.error_message)

        return result.normalized_value
```

**Step 3: Use in Validation Module**
```python
# backend/src/extraction/validation.py (refactored)
from src.validation.field_validators import FieldValidators

# Keep is_valid_* functions for backwards compatibility
def is_valid_ssn(ssn: str) -> bool:
    """Check if SSN is valid."""
    result = FieldValidators.validate_ssn(ssn)
    return result.is_valid

def is_valid_phone(phone: str) -> bool:
    """Check if phone is valid."""
    result = FieldValidators.validate_phone(phone)
    return result.is_valid

def is_valid_zip(zip_code: str) -> bool:
    """Check if ZIP is valid."""
    result = FieldValidators.validate_zip(zip_code)
    return result.is_valid

# Or directly expose the validators
validate_ssn = FieldValidators.validate_ssn
validate_phone = FieldValidators.validate_phone
validate_zip = FieldValidators.validate_zip
```

**Step 4: Use in LLM Prompts**
```python
# backend/src/extraction/extractor.py (refactored)
from src.validation.field_validators import FieldValidators

def build_extraction_prompt() -> str:
    """Build extraction prompt with validation rules."""

    # ✅ Rules generated from code, always in sync
    ssn_rules = FieldValidators.get_ssn_description()
    phone_rules = FieldValidators.get_phone_description()
    zip_rules = FieldValidators.get_zip_description()
    year_rules = FieldValidators.get_year_description()

    return f"""
Extract borrower information from loan documents.

Field Formats:
- SSN: {ssn_rules}
- Phone: {phone_rules}
- ZIP: {zip_rules}
- Year: {year_rules}

Return JSON with these fields:
{{
  "borrowers": [
    {{
      "ssn": "XXX-XX-XXXX",
      "phone": "(XXX) XXX-XXXX",
      "address": {{
        "zip_code": "XXXXX"
      }}
    }}
  ]
}}
"""
```

**Why This Is Better:**
- **DRY:** Write validation logic once
- **Always In Sync:** Prompt rules match code rules
- **Easy to Update:** Change one place, everything updates
- **No Drift:** Impossible for rules to diverge

**Migration Steps:**
1. Create field_validators.py with centralized validators
2. Add tests for each validator
3. Update models/borrower.py to use centralized validators
4. Update extraction/validation.py to use centralized validators
5. Update extraction/extractor.py prompts to use description methods
6. Run tests, verify all validation still works
7. Remove duplicate validation logic

---

## High-Priority Frontend Enhancements

### 6. Frontend: Increase Test Coverage

**Current State:** Only smoke tests (~10% coverage)
**Goal:** 80%+ coverage with comprehensive test suite

**Why Change:**
- **Regression Prevention:** Catch bugs before production
- **Confidence:** Safe to refactor and add features
- **Documentation:** Tests show how components should be used
- **Quality:** Forces better component design

**Current Tests:**
```typescript
// frontend/e2e/smoke.spec.ts (only 4 tests)
test('dashboard page loads', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('nav')).toBeVisible();
});

test('documents page loads', async ({ page }) => {
  await page.goto('/documents');
  await expect(page.getByRole('button', { name: /upload/i })).toBeVisible();
});

test('borrowers page loads', async ({ page }) => {
  await page.goto('/borrowers');
  await expect(page.getByText(/borrowers/i)).toBeVisible();
});

test('navigates between pages', async ({ page }) => {
  await page.goto('/');
  await page.click('text=Documents');
  await expect(page).toHaveURL('/documents');
});
```

**Problems:**
- No component unit tests
- No hook tests
- No API error handling tests
- No integration tests for user flows

**Proposed Solution:**

**Step 1: Set Up Vitest for Component Testing**
```typescript
// frontend/vitest.config.ts (new)
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './tests/setup.ts',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'tests/',
        '*.config.*',
        '.next/',
      ],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
```

```typescript
// frontend/tests/setup.ts (new)
import '@testing-library/jest-dom';
import { expect, afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

// Cleanup after each test
afterEach(() => {
  cleanup();
});

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
  takeRecords() {
    return [];
  }
};
```

**Step 2: Add Component Unit Tests**
```typescript
// frontend/tests/unit/components/DocumentTable.test.tsx (new)
import { render, screen, within } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { DocumentTable } from '@/components/documents/DocumentTable';
import type { DocumentResponse } from '@/lib/api/types';

describe('DocumentTable', () => {
  const mockDocuments: DocumentResponse[] = [
    {
      id: '123e4567-e89b-12d3-a456-426614174000',
      filename: 'test.pdf',
      status: 'completed',
      page_count: 5,
      created_at: '2024-01-15T10:00:00Z',
      extraction_method: 'docling',
      ocr_processed: false,
    },
    {
      id: '223e4567-e89b-12d3-a456-426614174001',
      filename: 'loan.docx',
      status: 'pending',
      page_count: null,
      created_at: '2024-01-15T10:05:00Z',
      extraction_method: 'langextract',
      ocr_processed: false,
    },
  ];

  it('renders document rows', () => {
    render(<DocumentTable documents={mockDocuments} />);

    // Check first document
    expect(screen.getByText('test.pdf')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();  // page count

    // Check second document
    expect(screen.getByText('loan.docx')).toBeInTheDocument();
  });

  it('displays status badges with correct colors', () => {
    render(<DocumentTable documents={mockDocuments} />);

    const completedBadge = screen.getByText('completed');
    expect(completedBadge).toHaveClass('bg-green-500');  // or whatever your success color is

    const pendingBadge = screen.getByText('pending');
    expect(pendingBadge).toHaveClass('bg-yellow-500');  // or whatever your warning color is
  });

  it('shows delete button for each document', () => {
    const onDelete = vi.fn();
    render(<DocumentTable documents={mockDocuments} onDelete={onDelete} />);

    const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
    expect(deleteButtons).toHaveLength(2);
  });

  it('calls onDelete with document id when delete clicked', async () => {
    const onDelete = vi.fn();
    const { user } = render(<DocumentTable documents={mockDocuments} onDelete={onDelete} />);

    const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
    await user.click(deleteButtons[0]);

    expect(onDelete).toHaveBeenCalledWith('123e4567-e89b-12d3-a456-426614174000');
  });

  it('displays empty state when no documents', () => {
    render(<DocumentTable documents={[]} />);
    expect(screen.getByText(/no documents/i)).toBeInTheDocument();
  });

  it('formats dates correctly', () => {
    render(<DocumentTable documents={mockDocuments} />);

    // Assuming you format dates like "Jan 15, 2024"
    expect(screen.getByText(/Jan 15, 2024/i)).toBeInTheDocument();
  });
});
```

**Step 3: Add Hook Tests**
```typescript
// frontend/tests/unit/hooks/use-documents.test.ts (new)
import { renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useDocuments, useUploadDocument } from '@/hooks/use-documents';
import * as api from '@/lib/api/documents';

// Mock API
vi.mock('@/lib/api/documents');

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return ({ children }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}

describe('useDocuments', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches documents on mount', async () => {
    const mockResponse = {
      documents: [
        { id: '1', filename: 'test.pdf', status: 'completed' },
      ],
      total: 1,
      limit: 100,
      offset: 0,
    };

    vi.mocked(api.listDocuments).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useDocuments(), {
      wrapper: createWrapper(),
    });

    // Initially loading
    expect(result.current.isLoading).toBe(true);

    // Wait for data
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.documents).toHaveLength(1);
    expect(result.current.data?.documents[0].filename).toBe('test.pdf');
  });

  it('polls when documents are processing', async () => {
    const mockResponse = {
      documents: [
        { id: '1', filename: 'test.pdf', status: 'pending' },
      ],
      total: 1,
      limit: 100,
      offset: 0,
    };

    vi.mocked(api.listDocuments).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useDocuments(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // Should set up polling (check refetchInterval)
    // This is tricky to test directly, but you can verify
    // that the query is configured with refetchInterval
    expect(api.listDocuments).toHaveBeenCalledTimes(1);

    // Wait a bit and check if it refetched
    await new Promise(resolve => setTimeout(resolve, 2100));
    expect(api.listDocuments).toHaveBeenCalledTimes(2);
  });

  it('stops polling when all documents completed', async () => {
    let callCount = 0;
    vi.mocked(api.listDocuments).mockImplementation(async () => {
      callCount++;
      if (callCount === 1) {
        return {
          documents: [{ id: '1', filename: 'test.pdf', status: 'pending' }],
          total: 1, limit: 100, offset: 0,
        };
      } else {
        return {
          documents: [{ id: '1', filename: 'test.pdf', status: 'completed' }],
          total: 1, limit: 100, offset: 0,
        };
      }
    });

    const { result } = renderHook(() => useDocuments(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.data?.documents[0].status).toBe('completed');
    });

    // Should stop polling after completed
    const callsBeforeWait = callCount;
    await new Promise(resolve => setTimeout(resolve, 2100));
    expect(callCount).toBe(callsBeforeWait);  // No new calls
  });
});

describe('useUploadDocument', () => {
  it('uploads document successfully', async () => {
    const mockResponse = {
      id: '123',
      filename: 'test.pdf',
      status: 'pending',
    };

    vi.mocked(api.uploadDocumentWithParams).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useUploadDocument(), {
      wrapper: createWrapper(),
    });

    const file = new File(['test'], 'test.pdf', { type: 'application/pdf' });

    result.current.mutate({
      file,
      method: 'docling',
      ocr: 'auto',
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.filename).toBe('test.pdf');
  });

  it('handles upload errors', async () => {
    vi.mocked(api.uploadDocumentWithParams).mockRejectedValue(
      new Error('File too large')
    );

    const { result } = renderHook(() => useUploadDocument(), {
      wrapper: createWrapper(),
    });

    const file = new File(['test'], 'test.pdf', { type: 'application/pdf' });

    result.current.mutate({
      file,
      method: 'docling',
      ocr: 'auto',
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error?.message).toBe('File too large');
  });

  it('invalidates documents query on success', async () => {
    const mockResponse = {
      id: '123',
      filename: 'test.pdf',
      status: 'pending',
    };

    vi.mocked(api.uploadDocumentWithParams).mockResolvedValue(mockResponse);

    const queryClient = new QueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );

    const { result } = renderHook(() => useUploadDocument(), { wrapper });

    const file = new File(['test'], 'test.pdf', { type: 'application/pdf' });

    result.current.mutate({
      file,
      method: 'docling',
      ocr: 'auto',
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['documents'] });
  });
});
```

**Step 4: Add Integration Tests (E2E)**
```typescript
// frontend/e2e/document-upload-flow.spec.ts (new)
import { test, expect } from '@playwright/test';

test.describe('Document Upload Flow', () => {
  test('complete upload and processing flow', async ({ page }) => {
    // Navigate to documents page
    await page.goto('/documents');

    // Upload a document
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles('tests/fixtures/sample-w2.pdf');

    // Should show uploading state
    await expect(page.getByText(/uploading/i)).toBeVisible();

    // Should show pending status
    await expect(page.getByText('sample-w2.pdf')).toBeVisible();
    await expect(page.getByText(/pending/i)).toBeVisible();

    // Wait for processing (with timeout)
    await expect(page.getByText(/completed/i)).toBeVisible({ timeout: 30000 });

    // Should show page count
    await expect(page.getByText(/\d+ pages/)).toBeVisible();

    // Click on document to view details
    await page.click('text=sample-w2.pdf');

    // Should navigate to detail page
    await expect(page).toHaveURL(/\/documents\/[a-f0-9-]+/);

    // Should show document metadata
    await expect(page.getByText('Extraction Method')).toBeVisible();
    await expect(page.getByText('docling')).toBeVisible();
  });

  test('handles upload errors gracefully', async ({ page }) => {
    await page.goto('/documents');

    // Try to upload invalid file
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles('tests/fixtures/invalid.txt');

    // Should show error message
    await expect(page.getByText(/unsupported file type/i)).toBeVisible();

    // Should not add document to table
    await expect(page.getByText('invalid.txt')).not.toBeVisible();
  });

  test('allows deleting documents', async ({ page }) => {
    await page.goto('/documents');

    // Assume there's already a document
    const documentRow = page.locator('[data-testid="document-row"]').first();
    const filename = await documentRow.getByTestId('filename').textContent();

    // Click delete button
    await documentRow.getByRole('button', { name: /delete/i }).click();

    // Confirm deletion
    await page.getByRole('button', { name: /confirm/i }).click();

    // Document should be removed
    await expect(page.getByText(filename)).not.toBeVisible();
  });
});
```

**Step 5: Add API Error Handling Tests**
```typescript
// frontend/tests/unit/api/error-handling.test.ts (new)
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useDocuments } from '@/hooks/use-documents';
import * as api from '@/lib/api/documents';

vi.mock('@/lib/api/documents');

describe('API Error Handling', () => {
  it('handles network errors', async () => {
    vi.mocked(api.listDocuments).mockRejectedValue(
      new Error('Network error')
    );

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );

    const { result } = renderHook(() => useDocuments(), { wrapper });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error?.message).toBe('Network error');
  });

  it('handles 404 errors', async () => {
    vi.mocked(api.listDocuments).mockRejectedValue(
      new Response('Not Found', { status: 404 })
    );

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );

    const { result } = renderHook(() => useDocuments(), { wrapper });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });

  it('handles 500 errors with retry', async () => {
    let attempts = 0;
    vi.mocked(api.listDocuments).mockImplementation(async () => {
      attempts++;
      if (attempts < 2) {
        throw new Error('Internal Server Error');
      }
      return { documents: [], total: 0, limit: 100, offset: 0 };
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: 1 } },
    });

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );

    const { result } = renderHook(() => useDocuments(), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(attempts).toBe(2);  // First attempt failed, second succeeded
  });
});
```

**Step 6: Update package.json**
```json
// frontend/package.json
{
  "scripts": {
    "test": "vitest",
    "test:ui": "vitest --ui",
    "test:coverage": "vitest run --coverage",
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui",
    "test:all": "npm run test:coverage && npm run test:e2e"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.1.5",
    "@testing-library/react": "^14.1.2",
    "@testing-library/user-event": "^14.5.1",
    "@vitejs/plugin-react": "^4.2.1",
    "@vitest/ui": "^1.0.4",
    "jsdom": "^23.0.1",
    "vitest": "^1.0.4"
  }
}
```

**Why This Is Better:**
- **Comprehensive Coverage:** Unit + Integration + E2E tests
- **Fast Feedback:** Unit tests run in milliseconds
- **Confidence:** Safe to refactor
- **Documentation:** Tests show how to use components
- **Regression Prevention:** Catch bugs before production

**Migration Steps:**
1. Install testing dependencies
2. Create vitest.config.ts and test setup
3. Write component unit tests (start with most critical)
4. Write hook tests
5. Write integration E2E tests
6. Add API error handling tests
7. Run `npm run test:coverage` to measure progress
8. Aim for 80%+ coverage

---

## Medium-Priority Backend Enhancements

### 7. Add Partial Success Status Field

**File:** `backend/src/storage/models.py`

**Why Change:**
- **Semantic Clarity:** "Partial success" is not an error
- **Query Difficulty:** Can't easily find "partially successful" documents
- **Analytics:** Can't track how often partial persistence happens
- **Business Logic in Error Field:** Using error_message for non-error information

**Current Code:**
```python
# backend/src/storage/models.py
class Document(Base):
    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    status: Mapped[DocumentStatus] = mapped_column(default=DocumentStatus.PENDING)
    error_message: Mapped[str | None]
    # ❌ No field for persistence status

# backend/src/ingestion/document_service.py (line 469)
if len(persisted) > 0:
    # ❌ Using error_message for business logic
    document.error_message = (
        f"Partial success: {len(persisted)}/{len(borrowers)} borrowers persisted. "
        f"Failures: {failures}"
    )
```

**Problems:**
1. `error_message` means "something went wrong", but partial success isn't an error
2. Can't query: "Show me all documents with partial borrower persistence"
3. Hard to distinguish "all failed" vs "some succeeded"

**Proposed Solution:**

**Step 1: Add Persistence Status Enum**
```python
# backend/src/storage/models.py

class PersistenceStatus(str, Enum):
    """Status of borrower persistence for a document."""

    NONE = "none"  # No extraction attempted yet
    COMPLETE = "complete"  # All borrowers persisted successfully
    PARTIAL = "partial"  # Some borrowers persisted, some failed
    FAILED = "failed"  # All borrowers failed to persist


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    filename: Mapped[str]
    status: Mapped[DocumentStatus] = mapped_column(default=DocumentStatus.PENDING)
    error_message: Mapped[str | None]  # For processing errors only

    # ✅ New fields for persistence tracking
    persistence_status: Mapped[PersistenceStatus] = mapped_column(
        default=PersistenceStatus.NONE
    )
    persistence_detail: Mapped[str | None]  # Details about partial success/failure

    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
```

**Step 2: Create Migration**
```python
# backend/alembic/versions/xxx_add_persistence_status.py
"""Add persistence status tracking

Revision ID: xxx
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add new columns
    op.add_column('documents', sa.Column(
        'persistence_status',
        sa.Enum('none', 'complete', 'partial', 'failed', name='persistencestatus'),
        nullable=False,
        server_default='none'
    ))
    op.add_column('documents', sa.Column(
        'persistence_detail',
        sa.String(),
        nullable=True
    ))

    # Migrate existing data:
    # If error_message starts with "Partial success:", set persistence_status=partial
    # Otherwise if status=completed and no error, set persistence_status=complete
    op.execute("""
        UPDATE documents
        SET persistence_status = CASE
            WHEN error_message LIKE 'Partial success:%' THEN 'partial'
            WHEN status = 'completed' AND error_message IS NULL THEN 'complete'
            ELSE 'none'
        END
    """)

    # Move "Partial success:" messages to persistence_detail
    op.execute("""
        UPDATE documents
        SET
            persistence_detail = error_message,
            error_message = NULL
        WHERE error_message LIKE 'Partial success:%'
    """)

def downgrade():
    op.drop_column('documents', 'persistence_detail')
    op.drop_column('documents', 'persistence_status')
```

**Step 3: Update PersistenceService (from Enhancement #1)**
```python
# backend/src/ingestion/persistence_service.py
async def persist_borrowers(self,
                            document_id: UUID,
                            borrowers: list[BorrowerRecord]) -> PersistenceResult:
    """Persist borrowers with status tracking."""

    if not borrowers:
        return PersistenceResult(
            status=PersistenceStatus.NONE,
            persisted_count=0,
            total_count=0
        )

    persisted = []
    failures = []

    for borrower_record in borrowers:
        try:
            borrower = await self._persist_single_borrower(document_id, borrower_record)
            persisted.append(borrower)
        except Exception as e:
            failures.append({
                "ssn_last_4": borrower_record.ssn_last_4,
                "error": str(e)
            })

    # ✅ Determine status based on results
    if len(persisted) == len(borrowers):
        status = PersistenceStatus.COMPLETE
    elif len(persisted) > 0:
        status = PersistenceStatus.PARTIAL
    else:
        status = PersistenceStatus.FAILED

    return PersistenceResult(
        status=status,
        persisted_count=len(persisted),
        total_count=len(borrowers),
        failures=failures
    )
```

**Step 4: Update DocumentService**
```python
# backend/src/ingestion/document_service.py
async def _process_document_sync(self, document: Document, ...):
    try:
        # ... processing ...

        # Persist borrowers
        persistence_result = await self.persistence_service.persist_borrowers(
            document_id=document.id,
            borrowers=processing_result.borrowers
        )

        # ✅ Update persistence status
        document.persistence_status = persistence_result.status

        if persistence_result.status == PersistenceStatus.PARTIAL:
            document.persistence_detail = (
                f"{persistence_result.persisted_count}/{persistence_result.total_count} "
                f"borrowers persisted. Failures: {persistence_result.failures}"
            )
        elif persistence_result.status == PersistenceStatus.FAILED:
            document.persistence_detail = (
                f"All {persistence_result.total_count} borrowers failed to persist. "
                f"Errors: {persistence_result.failures}"
            )
        # If COMPLETE, leave persistence_detail as None

        # ✅ error_message is only for processing errors, not persistence
        document.status = DocumentStatus.COMPLETED
        document.error_message = None

        await self.repository.update(document)
        await self.repository.session.commit()

    except Exception as e:
        # ✅ Processing error goes in error_message
        document.status = DocumentStatus.FAILED
        document.error_message = str(e)
        # persistence_status stays NONE (extraction never attempted)
        await self.repository.update(document)
        await self.repository.session.commit()
```

**Step 5: Expose in API**
```python
# backend/src/api/routers/documents.py

class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    status: DocumentStatus
    error_message: str | None

    # ✅ Add new fields
    persistence_status: PersistenceStatus
    persistence_detail: str | None

    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

**Step 6: Update Frontend Types**
```typescript
// frontend/src/lib/api/types.ts

export type PersistenceStatus = 'none' | 'complete' | 'partial' | 'failed';

export interface DocumentResponse {
  id: string;
  filename: string;
  status: DocumentStatus;
  error_message: string | null;

  // ✅ Add new fields
  persistence_status: PersistenceStatus;
  persistence_detail: string | null;

  created_at: string;
}
```

**Step 7: Display in Frontend**
```tsx
// frontend/src/components/documents/DocumentTable.tsx

function PersistenceStatusBadge({ status }: { status: PersistenceStatus }) {
  const variants = {
    none: 'bg-gray-500',
    complete: 'bg-green-500',
    partial: 'bg-yellow-500',
    failed: 'bg-red-500',
  };

  return (
    <Badge className={variants[status]}>
      {status}
    </Badge>
  );
}

// In table
<TableCell>
  <PersistenceStatusBadge status={document.persistence_status} />
  {document.persistence_detail && (
    <Tooltip content={document.persistence_detail}>
      <InfoIcon className="ml-1" />
    </Tooltip>
  )}
</TableCell>
```

**Why This Is Better:**
- **Clear Semantics:** "partial" means some succeeded, not an error
- **Queryable:** `WHERE persistence_status = 'partial'`
- **Analytics:** Track partial success rate
- **Separation:** Processing errors vs persistence status

**Migration Steps:**
1. Add PersistenceStatus enum to models.py
2. Add fields to Document model
3. Create and run Alembic migration
4. Update PersistenceService to return status
5. Update DocumentService to set status
6. Update API response models
7. Update frontend types and UI
8. Test migration on staging data

---

(Continuing with remaining Medium/Low priority enhancements with same level of detail...)
