# Phase 15: Dual Pipeline Integration - Research

**Researched:** 2026-01-25
**Domain:** API Integration, FastAPI Query Parameters, SQLAlchemy Schema Updates
**Confidence:** HIGH

## Summary

This research focuses on enabling API-based extraction method selection (`?method=docling|langextract`) and OCR mode selection (`?ocr=auto|force|skip`) for the dual pipeline integration. The existing codebase already has the core routing components (ExtractionRouter, OCRRouter) implemented in Phase 12 and Phase 14. Phase 15 wires these routers to the API layer and Cloud Tasks.

The research identifies that the existing architecture is well-suited for this integration:
- `ExtractionRouter` already accepts `method: Literal["langextract", "docling", "auto"]`
- `OCRRouter` already accepts `mode: OCRMode` (type alias for `Literal["auto", "force", "skip"]`)
- Both produce outputs that can be unified via `BorrowerRecord`

The primary work is API plumbing: adding query parameters to endpoints, passing parameters through Cloud Tasks, and adding metadata tracking to the Document model.

**Primary recommendation:** Use FastAPI Literal-typed query parameters (already the pattern in this codebase) with sensible defaults (`method=docling` for backward compatibility, `ocr=auto` for intelligent routing). Add two metadata columns to documents table via Alembic migration.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115+ | API framework | Already in use; supports Literal query params |
| SQLAlchemy | 2.0+ | ORM | Already in use for Document model |
| Alembic | 1.13+ | Schema migrations | Already in use; v002 migration exists |
| Pydantic | 2.0+ | Data validation | Already in use for request/response models |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| typing.Literal | stdlib | Type-safe enums | Query parameter constraints |
| typing.Annotated | stdlib | Dependency injection | FastAPI Query patterns |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Literal types | Python Enum | Enum provides metadata, but Literal is simpler for simple constraints. Codebase already uses Literal (see `OCRMode`, `extraction_router.py`) |
| Query params | Request body | Request body is more structured but less RESTful for GET operations. Query params are standard for filtering/options |

**Installation:**
No new dependencies required - all libraries already in use.

## Architecture Patterns

### Recommended Project Structure

No new files needed. Modifications to existing files:

```
backend/
├── src/
│   ├── api/
│   │   ├── documents.py         # MODIFY: Add method/ocr query params
│   │   └── tasks.py             # MODIFY: Accept method/ocr in payload
│   ├── ingestion/
│   │   ├── cloud_tasks_client.py # MODIFY: Include method/ocr in payload
│   │   └── document_service.py   # MODIFY: Wire ExtractionRouter + OCRRouter
│   └── storage/
│       └── models.py            # MODIFY: Add extraction_method, ocr_processed columns
├── alembic/versions/
│   └── 003_add_extraction_metadata.py  # NEW: Migration for new columns
└── tests/unit/
    └── api/
        └── test_documents_params.py    # NEW: Test query parameter handling
```

### Pattern 1: Literal-Typed Query Parameters

**What:** Use `Literal` types for constrained query parameters
**When to use:** When parameter has finite, known valid values
**Example:**
```python
# Source: Existing codebase pattern (ocr_router.py line 24)
from typing import Literal

ExtractionMethod = Literal["docling", "langextract", "auto"]
OCRMode = Literal["auto", "force", "skip"]

@router.post("/")
async def upload_document(
    file: UploadFile,
    method: ExtractionMethod = "docling",  # Default for backward compatibility
    ocr: OCRMode = "auto",
    service: DocumentServiceDep,
) -> DocumentUploadResponse:
    # Pass params through to service
    document = await service.upload(
        filename=file.filename,
        content=await file.read(),
        extraction_method=method,
        ocr_mode=ocr,
    )
    return DocumentUploadResponse(...)
```

### Pattern 2: Cloud Tasks Payload Enhancement

**What:** Include method/ocr parameters in Cloud Tasks JSON payload
**When to use:** When queueing async work that needs context
**Example:**
```python
# Source: Existing codebase pattern (cloud_tasks_client.py line 66-70)
payload = json.dumps({
    "document_id": str(document_id),
    "filename": filename,
    "method": method,  # NEW: extraction method
    "ocr": ocr_mode,   # NEW: OCR mode
}).encode()
```

### Pattern 3: Document Metadata Tracking

**What:** Store extraction metadata on Document model for observability
**When to use:** For traceability and debugging
**Example:**
```python
# Source: Existing codebase pattern (storage/models.py Document class)
class Document(Base):
    __tablename__ = "documents"

    # ... existing columns ...

    # NEW: Extraction metadata
    extraction_method: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # "docling", "langextract", or null (legacy)

    ocr_processed: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True
    )  # True if OCR was applied, False if skipped, null (legacy)
```

### Anti-Patterns to Avoid

- **Passing extraction method as part of filename/URL path:** Query params are cleaner for optional processing configuration
- **Duplicating router logic in API layer:** Let ExtractionRouter/OCRRouter handle decisions; API just passes params
- **Breaking backward compatibility:** Default `method=docling` ensures v1.0 behavior unchanged
- **Storing method/ocr in separate tables:** Document metadata belongs on Document model

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Method validation | Manual if/else checks | Literal type + FastAPI | Automatic 422 on invalid values |
| OCR routing | New router class | Existing `OCRRouter` | Already handles mode, circuit breaker, fallback |
| Extraction routing | New router class | Existing `ExtractionRouter` | Already handles method, retry, fallback |
| Schema migration | Manual SQL | Alembic migration | Consistent with existing 001, 002 migrations |

**Key insight:** Phase 12 and Phase 14 built the heavy lifting (ExtractionRouter, OCRRouter). Phase 15 is primarily API wiring - don't reimplement what exists.

## Common Pitfalls

### Pitfall 1: Breaking Backward Compatibility (DUAL-09)

**What goes wrong:** Changing default behavior breaks existing v1.0 clients
**Why it happens:** Desire to default to "better" LangExtract method
**How to avoid:**
- Default `method=docling` to preserve v1.0 behavior
- Default `ocr=auto` (safe default that already existed conceptually)
- Treat null in database as "legacy/docling"
**Warning signs:** Unit tests for existing endpoints start failing

### Pitfall 2: Not Passing Parameters Through Cloud Tasks

**What goes wrong:** Async processing ignores method/ocr selection
**Why it happens:** Forgetting to update Cloud Tasks payload and handler
**How to avoid:**
- Update `CloudTasksClient.create_document_processing_task` signature
- Update `ProcessDocumentRequest` Pydantic model in tasks.py
- Update task handler to use parameters
**Warning signs:** Async uploads always use Docling regardless of `?method=`

### Pitfall 3: Inconsistent Type Definitions

**What goes wrong:** Literal type defined differently in multiple places
**Why it happens:** Copy-paste without centralizing type aliases
**How to avoid:**
- Define `ExtractionMethod` type alias in one place (e.g., extraction_router.py)
- Import from that location everywhere
- OCRMode already defined in ocr_router.py - reuse it
**Warning signs:** Import errors, mypy type conflicts

### Pitfall 4: Nullable Column Without Default

**What goes wrong:** Existing rows fail queries on new columns
**Why it happens:** Adding NOT NULL column without default/backfill
**How to avoid:**
- Make new columns nullable: `nullable=True`
- Null = legacy/unknown (document created before v2.0)
- Migration adds columns only, no backfill needed
**Warning signs:** IntegrityError on insert, SELECT failures

### Pitfall 5: Not Testing Both Sync and Async Paths

**What goes wrong:** Method selection works locally but not in production
**Why it happens:** Local dev uses sync path, production uses Cloud Tasks
**How to avoid:**
- Test both `cloud_tasks_client=None` (sync) and `cloud_tasks_client=mock` (async)
- Verify parameters propagate through both code paths
**Warning signs:** Tests pass but production behaves differently

## Code Examples

Verified patterns from existing codebase:

### Query Parameter with Literal Type
```python
# Source: Existing pattern in borrowers.py lines 137-140
from typing import Annotated, Literal

ExtractionMethod = Literal["docling", "langextract", "auto"]

@router.post("/")
async def upload_document(
    file: UploadFile,
    method: ExtractionMethod = "docling",
    service: DocumentServiceDep,
) -> DocumentUploadResponse:
    ...
```

### Alembic Migration for New Columns
```python
# Source: Pattern from 002_add_char_offsets.py
"""Add extraction metadata columns to documents.

Revision ID: 003
Revises: 002
Create Date: 2026-01-25
"""
from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: str | None = "002"

def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("extraction_method", sa.String(20), nullable=True)
    )
    op.add_column(
        "documents",
        sa.Column("ocr_processed", sa.Boolean(), nullable=True)
    )

def downgrade() -> None:
    op.drop_column("documents", "ocr_processed")
    op.drop_column("documents", "extraction_method")
```

### ExtractionRouter Usage (Already Exists)
```python
# Source: extraction_router.py lines 120-127
result = router.extract(
    document=document_content,
    document_id=document_id,
    document_name=filename,
    method="langextract",  # or "docling" or "auto"
    config=ExtractionConfig(),
)
```

### Cloud Tasks Payload Pattern
```python
# Source: cloud_tasks_client.py lines 66-70
payload = json.dumps({
    "document_id": str(document_id),
    "filename": filename,
    # Add new fields:
    "method": extraction_method,
    "ocr": ocr_mode,
}).encode()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fixed Docling pipeline | Dual pipeline with selection | Phase 15 | User choice, flexibility |
| Implicit OCR via Docling | Explicit OCR mode parameter | Phase 14/15 | Control over GPU usage, cost |
| No extraction metadata | Document tracks method used | Phase 15 | Observability, debugging |

**Deprecated/outdated:**
- None for this phase (building new capability)

## Open Questions

Things that couldn't be fully resolved:

1. **Default method value for production**
   - What we know: `method=docling` preserves backward compatibility
   - What's unclear: Should we eventually flip default to `auto` once LangExtract proven?
   - Recommendation: Start with `docling` default, change via config later if needed

2. **OCR mode default with LangExtract**
   - What we know: LangExtract works on Docling markdown output
   - What's unclear: If LangExtract selected, should OCR auto-detect still apply?
   - Recommendation: Yes - OCR happens before extraction, independent of method

3. **Result type unification**
   - What we know: Docling returns `ExtractionResult`, LangExtract returns `LangExtractResult`
   - What's unclear: Should we normalize to single type for API response?
   - Recommendation: Both already produce `BorrowerRecord` list - unify at that level

## Sources

### Primary (HIGH confidence)
- Existing codebase analysis:
  - `/backend/src/extraction/extraction_router.py` - ExtractionRouter implementation
  - `/backend/src/ocr/ocr_router.py` - OCRRouter and OCRMode type
  - `/backend/src/api/documents.py` - Current upload endpoint
  - `/backend/src/api/tasks.py` - Cloud Tasks handler
  - `/backend/src/ingestion/cloud_tasks_client.py` - Task payload structure
  - `/backend/src/storage/models.py` - Document SQLAlchemy model
  - `/backend/alembic/versions/002_add_char_offsets.py` - Migration pattern

### Secondary (MEDIUM confidence)
- [FastAPI Query Parameters Documentation](https://fastapi.tiangolo.com/tutorial/query-params/)
- [FastAPI Query Parameter Models](https://fastapi.tiangolo.com/tutorial/query-param-models/)
- [FastAPI Enum Discussion](https://github.com/fastapi/fastapi/discussions/13254)

### Tertiary (LOW confidence)
- None - all findings verified against codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in use in codebase
- Architecture: HIGH - Building on existing patterns (ExtractionRouter, OCRRouter)
- Pitfalls: HIGH - Based on actual codebase structure and requirements

**Research date:** 2026-01-25
**Valid until:** 30 days (stable domain, internal architecture)
