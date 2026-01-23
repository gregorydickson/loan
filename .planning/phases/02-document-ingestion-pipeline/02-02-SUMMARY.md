---
phase: 02-document-ingestion-pipeline
plan: 02
subsystem: ingestion
tags: [docling, gcs, document-processing, pdf, storage]

dependency-graph:
  requires: ["02-01"]
  provides:
    - DoclingProcessor with page-level text extraction
    - GCSClient with signed URL support
    - Integration tests for INGEST-13/INGEST-14
  affects: ["02-03"]

tech-stack:
  added:
    - docling.DocumentConverter (PDF/DOCX/image processing)
    - google-cloud-storage (GCS operations)
  patterns:
    - Fresh converter per document (memory-safe)
    - Lazy bucket loading for testability
    - Application Default Credentials (ADC)

key-files:
  created:
    - backend/src/ingestion/__init__.py
    - backend/src/ingestion/docling_processor.py
    - backend/tests/unit/test_docling_processor.py
    - backend/src/storage/gcs_client.py
    - backend/tests/unit/test_gcs_client.py
    - backend/tests/integration/__init__.py
    - backend/tests/integration/test_docling_integration.py
  modified:
    - backend/src/storage/__init__.py
    - backend/pyproject.toml

decisions:
  - id: fresh-converter-pattern
    choice: Create fresh DocumentConverter per document
    rationale: Avoids memory leak (GitHub issue #2209)
  - id: page-text-extraction
    choice: Use iterate_items() with provenance for page text
    rationale: Docling items have prov attribute with page_no
  - id: gcs-adc
    choice: Use Application Default Credentials
    rationale: Works on Cloud Run, no credential management

metrics:
  duration: 8 min
  completed: 2026-01-23
---

# Phase 2 Plan 2: DoclingProcessor and GCS Client Summary

DoclingProcessor wrapper with page-level text extraction via iterate_items() provenance, GCS client with ADC and signed URLs, integration tests for INGEST-13/INGEST-14.

## What Was Built

### 1. DoclingProcessor (backend/src/ingestion/docling_processor.py)

Document conversion wrapper with memory-safe patterns:

- **Memory-safe pattern**: Fresh DocumentConverter instance per document (avoids #2209 leak)
- **Page-level text extraction**: Uses `doc.iterate_items()` with provenance to extract actual text per page
- **Configurable options**: enable_ocr, enable_tables, max_pages
- **Error handling**: Wraps all errors in DocumentProcessingError without crashing
- **File support**: PDF, DOCX, PNG, JPG via Docling

```python
class PageContent(BaseModel):
    page_number: int  # 1-indexed
    text: str         # ACTUAL page text, not empty
    tables: list[dict]

class DocumentContent(BaseModel):
    text: str         # Full markdown
    pages: list[PageContent]
    page_count: int
    tables: list[dict]
    metadata: dict
```

### 2. GCSClient (backend/src/storage/gcs_client.py)

Google Cloud Storage operations with ADC:

- **Upload**: bytes or file-like objects with content type
- **Download**: to bytes or file-like objects
- **Signed URLs**: Temporary access with configurable expiration
- **Existence check**: Fast blob.exists() check
- **Delete**: Idempotent (ignores NotFound)
- **URI parsing**: Parse gs:// URIs to bucket/path

```python
client = GCSClient("my-bucket")
uri = client.upload(data, "path/file.pdf", "application/pdf")
url = client.get_signed_url("path/file.pdf", expiration_minutes=15)
```

### 3. Integration Tests (backend/tests/integration/test_docling_integration.py)

Tests for critical requirements:

- **INGEST-13**: Page boundary preservation - verifies page numbers are sequential
- **INGEST-14**: Graceful error handling - corrupted/empty files raise DocumentProcessingError

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Memory safety | Fresh converter per doc | GitHub #2209 memory leak |
| Page text extraction | iterate_items() with prov | Direct access to page provenance |
| GCS auth | Application Default Credentials | Works on Cloud Run, no keys |
| Error handling | DocumentProcessingError wrapper | Graceful degradation |
| Test separation | @pytest.mark.integration | Real Docling tests can be skipped |

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 41bcbea6 | feat | DoclingProcessor with page-level text extraction |
| ebc389ee | feat | GCSClient with upload, download, signed URLs |
| ff6ea044 | test | Integration tests for INGEST-13/INGEST-14 |

## Test Coverage

- **Unit tests**: 25 total (12 DoclingProcessor + 13 GCSClient)
- **Integration tests**: 11 (marked with @pytest.mark.integration)
- **All tests passing**

## Deviations from Plan

None - plan executed exactly as written.

## Dependencies

**Requires:**
- 02-01 Database Layer (completed)

**Provides:**
- DoclingProcessor for document text extraction
- GCSClient for cloud storage operations
- Page-level content with actual text

**Enables:**
- 02-03 Document Service and Upload API

## Next Phase Readiness

Ready for 02-03 (Document Service):
- DoclingProcessor available for async processing
- GCSClient available for file storage
- Page boundaries preserved for source attribution
