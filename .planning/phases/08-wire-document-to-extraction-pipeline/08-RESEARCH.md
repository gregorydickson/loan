# Phase 8: Wire Document-to-Extraction Pipeline - Research

**Researched:** 2026-01-24
**Domain:** Service Integration / Pipeline Orchestration
**Confidence:** HIGH

## Summary

This phase closes the critical integration gap identified in the v1.0 milestone audit: the extraction subsystem (BorrowerExtractor, 4,842 lines of code, 38 requirements) exists and is fully tested but is never called from the document processing pipeline. The research focused on understanding the existing codebase architecture and identifying the integration points needed to wire the pipeline together.

The integration is straightforward because both subsystems follow clean architecture patterns and use FastAPI's dependency injection. The DocumentService currently calls DoclingProcessor and returns - it needs to additionally inject and call BorrowerExtractor, then persist results via BorrowerRepository. The primary challenge is translating between Pydantic domain models (BorrowerRecord) and SQLAlchemy ORM models (Borrower) with proper handling of related entities (income_records, account_numbers, source_references).

**Primary recommendation:** Inject BorrowerExtractor into DocumentService, call it after DoclingProcessor succeeds, then use BorrowerRepository.create() to persist each extracted borrower with all related entities.

## Standard Stack

The established libraries/tools for this domain:

### Core (Already In Use)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.109+ | Async web framework | Already used, native DI support |
| SQLAlchemy | 2.0+ | Async ORM | Already used for repositories |
| Pydantic | 2.5+ | Data validation | Already used for domain models |

### Supporting (Already In Use)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| google-genai | 1.0+ | Gemini API client | LLM extraction (already in GeminiClient) |
| tenacity | 8.2+ | Retry logic | Already used in GeminiClient |
| hashlib | stdlib | SSN hashing | PII protection (SSN -> ssn_hash) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Direct wiring | Cloud Tasks | Async queue adds complexity - existing sync approach matches Phase 02-04 decision |
| Manual conversion | SQLModel | Would require refactoring existing models - not worth it for this integration |

**Installation:**
No new dependencies required - all needed libraries are already installed.

## Architecture Patterns

### Current Project Structure (Relevant Files)
```
backend/src/
├── ingestion/
│   ├── document_service.py    # Orchestrator - NEEDS MODIFICATION
│   └── docling_processor.py   # Returns DocumentContent
├── extraction/
│   ├── extractor.py           # BorrowerExtractor - orphaned, needs injection
│   └── __init__.py            # Exports all extraction components
├── storage/
│   ├── repositories.py        # BorrowerRepository - needs to be called
│   └── models.py              # SQLAlchemy models (Borrower, IncomeRecord, etc.)
├── models/
│   └── borrower.py            # Pydantic models (BorrowerRecord, etc.)
└── api/
    └── dependencies.py        # FastAPI DI - NEEDS get_borrower_extractor()
```

### Pattern 1: Service Layer Orchestration
**What:** DocumentService orchestrates the full pipeline: validate -> store -> process -> extract -> persist
**When to use:** Document upload workflow
**Example:**
```python
# Source: Existing document_service.py pattern, extended
class DocumentService:
    def __init__(
        self,
        repository: DocumentRepository,
        gcs_client: GCSClient,
        docling_processor: DoclingProcessor,
        borrower_extractor: BorrowerExtractor,  # NEW
        borrower_repository: BorrowerRepository,  # NEW
    ) -> None:
        self.repository = repository
        self.gcs_client = gcs_client
        self.docling_processor = docling_processor
        self.borrower_extractor = borrower_extractor
        self.borrower_repository = borrower_repository

    async def upload(self, filename: str, content: bytes, ...) -> Document:
        # ... existing validation, hash, GCS upload ...

        # After Docling processing succeeds:
        result = self.docling_processor.process_bytes(content, filename)

        # NEW: Extract borrowers
        extraction_result = self.borrower_extractor.extract(
            document=result,
            document_id=document_id,
            document_name=filename,
        )

        # NEW: Persist borrowers
        for borrower_record in extraction_result.borrowers:
            await self._persist_borrower(borrower_record, document_id)

        return document
```

### Pattern 2: Pydantic to SQLAlchemy Conversion
**What:** Convert BorrowerRecord (Pydantic) to Borrower (SQLAlchemy) with related entities
**When to use:** Persisting extraction results
**Example:**
```python
# Source: Existing models, conversion pattern from Pydantic docs
async def _persist_borrower(
    self,
    record: BorrowerRecord,
    document_id: UUID,
) -> Borrower:
    """Convert Pydantic BorrowerRecord to SQLAlchemy Borrower and persist."""
    import hashlib
    import json

    # Hash SSN for storage (never store raw SSN)
    ssn_hash = None
    if record.ssn:
        ssn_hash = hashlib.sha256(record.ssn.encode()).hexdigest()

    # Convert address to JSON
    address_json = None
    if record.address:
        address_json = record.address.model_dump_json()

    # Create SQLAlchemy model
    borrower = Borrower(
        id=record.id,
        name=record.name,
        ssn_hash=ssn_hash,
        address_json=address_json,
        confidence_score=Decimal(str(record.confidence_score)),
    )

    # Convert related entities
    income_records = [
        IncomeRecord(
            amount=income.amount,
            period=income.period,
            year=income.year,
            source_type=income.source_type,
            employer=income.employer,
        )
        for income in record.income_history
    ]

    account_numbers = [
        AccountNumber(number=acct, account_type="bank")
        for acct in record.account_numbers
    ] + [
        AccountNumber(number=loan, account_type="loan")
        for loan in record.loan_numbers
    ]

    source_references = [
        SourceReference(
            document_id=src.document_id,
            page_number=src.page_number,
            section=src.section,
            snippet=src.snippet,
        )
        for src in record.sources
    ]

    return await self.borrower_repository.create(
        borrower=borrower,
        income_records=income_records,
        account_numbers=account_numbers,
        source_references=source_references,
    )
```

### Pattern 3: FastAPI Dependency Injection Factory
**What:** Create factory functions that wire dependencies together
**When to use:** Providing BorrowerExtractor to DocumentService
**Example:**
```python
# Source: Existing dependencies.py pattern
_borrower_extractor: BorrowerExtractor | None = None

def get_borrower_extractor() -> BorrowerExtractor:
    """Get or create BorrowerExtractor singleton with all components."""
    global _borrower_extractor

    if _borrower_extractor is None:
        _borrower_extractor = BorrowerExtractor(
            llm_client=GeminiClient(),
            classifier=ComplexityClassifier(),
            chunker=DocumentChunker(),
            validator=FieldValidator(),
            confidence_calc=ConfidenceCalculator(),
            deduplicator=BorrowerDeduplicator(),
            consistency_validator=ConsistencyValidator(),
        )

    return _borrower_extractor

BorrowerExtractorDep = Annotated[BorrowerExtractor, Depends(get_borrower_extractor)]
```

### Anti-Patterns to Avoid
- **Creating BorrowerExtractor per-request:** Expensive component creation. Use singleton pattern for LLM client.
- **Storing raw SSN in database:** Always hash SSN before storage for PII protection.
- **Ignoring extraction failures:** Log and handle extraction errors; don't let them silently fail.
- **Synchronous LLM calls in async context:** BorrowerExtractor.extract() is sync; wrap with asyncio.to_thread() if needed for large batches.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSN validation | Custom regex | FieldValidator.validate_ssn() | Already handles edge cases |
| Duplicate detection | Manual matching | BorrowerDeduplicator | Handles SSN match, fuzzy name match, source merging |
| Confidence scoring | Manual calculation | ConfidenceCalculator | Weights all factors correctly |
| JSON serialization | Manual dict building | Pydantic model_dump_json() | Handles all field types |
| Retry logic | Custom loops | tenacity @retry | Already configured in GeminiClient |

**Key insight:** The extraction subsystem was built with all edge cases handled. The only task is wiring it to DocumentService and persisting results.

## Common Pitfalls

### Pitfall 1: Not Handling Extraction Failures Gracefully
**What goes wrong:** Extraction fails (LLM timeout, invalid response) and document is marked as COMPLETED anyway
**Why it happens:** Only checking Docling success, not extraction success
**How to avoid:**
- Add extraction_status field to Document model (separate from processing status)
- Catch extraction exceptions and update document.error_message
- Still mark document as COMPLETED (processing worked) but track extraction failures
**Warning signs:** Documents show COMPLETED but no borrowers appear

### Pitfall 2: Transaction Boundary Issues
**What goes wrong:** Borrower saved but income_records fail, leaving orphan record
**Why it happens:** Not using repository's built-in transaction handling
**How to avoid:**
- BorrowerRepository.create() already handles all related entities in one flush()
- Caller (DocumentService) controls commit via session
- Use flush() not commit() within repository
**Warning signs:** Borrowers exist but have no income_records or sources

### Pitfall 3: Mixing Sync and Async Incorrectly
**What goes wrong:** Blocking async event loop during LLM calls
**Why it happens:** BorrowerExtractor.extract() is synchronous; calling it directly in async upload()
**How to avoid:**
- For single-document uploads: Sync extraction is acceptable (matches current Docling pattern)
- For batch operations: Use asyncio.to_thread() to run extraction in thread pool
- Current design (sync in upload) is fine for demo/portfolio scope
**Warning signs:** Upload requests hang for 10+ seconds

### Pitfall 4: SSN Stored in Plain Text
**What goes wrong:** PII exposure if database is compromised
**Why it happens:** Copying raw SSN from BorrowerRecord to Borrower.ssn_hash field
**How to avoid:**
- Always hash: `ssn_hash = hashlib.sha256(record.ssn.encode()).hexdigest()`
- Borrower model has ssn_hash field (not ssn) specifically for this
- Never log raw SSN
**Warning signs:** ssn_hash field contains "123-45-6789" instead of hex hash

### Pitfall 5: Circular Import Issues
**What goes wrong:** ImportError when adding BorrowerExtractor to DocumentService
**Why it happens:** Extraction imports models which import docling which imports...
**How to avoid:**
- Use TYPE_CHECKING imports for type hints
- Import BorrowerExtractor in dependencies.py (already isolated)
- Keep DocumentService imports minimal
**Warning signs:** ImportError at startup mentioning circular reference

## Code Examples

Verified patterns from existing codebase:

### DocumentService.upload() Extension Point
```python
# Source: backend/src/ingestion/document_service.py lines 199-220
# Current code ends here - extraction call goes AFTER this block
try:
    result = self.docling_processor.process_bytes(content, filename)
    await self.update_processing_result(
        document_id,
        success=True,
        page_count=result.page_count,
    )
    # INSERTION POINT: Call extractor here
    # extraction_result = self.borrower_extractor.extract(result, document_id, filename)
    # for borrower in extraction_result.borrowers:
    #     await self._persist_borrower(borrower, document_id)

    refreshed = await self.repository.get_by_id(document_id)
    if refreshed is not None:
        document = refreshed
except DocumentProcessingError as e:
    await self.update_processing_result(
        document_id,
        success=False,
        error_message=f"Document processing failed: {e.message}",
    )
```

### BorrowerExtractor Interface
```python
# Source: backend/src/extraction/extractor.py lines 119-133
def extract(
    self,
    document: DocumentContent,  # From DoclingProcessor
    document_id: UUID,          # From DocumentService
    document_name: str,         # Original filename
) -> ExtractionResult:
    """Returns ExtractionResult with:
    - borrowers: list[BorrowerRecord] (deduplicated)
    - complexity: ComplexityAssessment
    - chunks_processed: int
    - total_tokens: int
    - validation_errors: list[ValidationError]
    - consistency_warnings: list[ConsistencyWarning]
    """
```

### BorrowerRepository.create() Interface
```python
# Source: backend/src/storage/repositories.py lines 165-201
async def create(
    self,
    borrower: Borrower,                        # SQLAlchemy model
    income_records: list[IncomeRecord],        # SQLAlchemy models
    account_numbers: list[AccountNumber],      # SQLAlchemy models
    source_references: list[SourceReference],  # SQLAlchemy models
) -> Borrower:
    """Creates borrower with all related entities in single transaction.
    Sets borrower_id on all related entities automatically.
    Uses flush() to stay within caller's transaction boundary.
    """
```

### Dependency Injection Pattern
```python
# Source: backend/src/api/dependencies.py lines 90-103
def get_document_service(
    repository: DocumentRepoDep,
    gcs_client: GCSClientDep,
    docling_processor: DoclingProcessorDep,
) -> DocumentService:
    """Get document service with dependencies."""
    return DocumentService(
        repository=repository,
        gcs_client=gcs_client,
        docling_processor=docling_processor,
    )
    # EXTENSION: Add borrower_extractor and borrower_repository parameters
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Sync processing only | Async with sync extraction | Existing design | Extraction is sync (acceptable for single docs) |
| Cloud Tasks queue | Direct sync in upload | Phase 02-04 decision | Simpler architecture for demo scope |

**Deprecated/outdated:**
- None - the existing components are current and well-designed
- INGEST-08 (Cloud Tasks) remains deferred per Phase 02-04 decision

## Open Questions

Things that couldn't be fully resolved:

1. **Extraction Status Tracking**
   - What we know: Document has status field (PENDING, PROCESSING, COMPLETED, FAILED)
   - What's unclear: Should extraction have separate status? (extraction_status vs processing_status)
   - Recommendation: Keep simple - use error_message for extraction failures, document status reflects overall result

2. **Batch Extraction Performance**
   - What we know: BorrowerExtractor.extract() is synchronous
   - What's unclear: Impact on upload latency for large documents (10+ pages)
   - Recommendation: For Phase 8 scope, sync is acceptable. If latency >30s observed, consider asyncio.to_thread() as future enhancement

3. **Partial Extraction Handling**
   - What we know: Some chunks may succeed while others fail (LLM timeout)
   - What's unclear: Should partial results be saved?
   - Recommendation: Save what was extracted, log warnings for failed chunks. Partial data > no data.

## Sources

### Primary (HIGH confidence)
- Existing codebase analysis - `backend/src/ingestion/document_service.py`
- Existing codebase analysis - `backend/src/extraction/extractor.py`
- Existing codebase analysis - `backend/src/storage/repositories.py`
- Existing codebase analysis - `backend/src/api/dependencies.py`
- v1.0 Milestone Audit - `.planning/v1.0-MILESTONE-AUDIT.md`

### Secondary (MEDIUM confidence)
- [FastAPI Dependencies Documentation](https://fastapi.tiangolo.com/tutorial/dependencies/) - DI patterns
- [Pydantic ORM Mode](https://docs.pydantic.dev/latest/examples/orms/) - model_validate with from_attributes
- [Medium: FastAPI Repository Pattern](https://medium.com/@kacperwlodarczyk/fast-api-repository-pattern-and-service-layer-dad43354f07a) - Service layer patterns

### Tertiary (LOW confidence)
- WebSearch for current best practices (2026) - verified against existing codebase patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All components already exist in codebase
- Architecture: HIGH - Patterns follow existing codebase conventions
- Pitfalls: HIGH - Identified from milestone audit findings and code analysis

**Research date:** 2026-01-24
**Valid until:** N/A - Integration work, not library-specific
