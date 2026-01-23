---
phase: 02-document-ingestion-pipeline
plan: 03
subsystem: ingestion
tags: [fastapi, api, upload, gcs, document-service, duplicate-detection]

dependency-graph:
  requires: [02-01]
  provides: [document-upload-api, document-service, gcs-client]
  affects: [02-04, 03-01]

tech-stack:
  added: []
  patterns: [repository-pattern, dependency-injection, async-upload]

key-files:
  created:
    - backend/src/ingestion/document_service.py
    - backend/src/api/__init__.py
    - backend/src/api/dependencies.py
    - backend/src/api/documents.py
    - backend/src/storage/gcs_client.py
    - backend/tests/unit/test_document_service.py
    - backend/tests/integration/conftest.py
    - backend/tests/integration/test_documents_api.py
  modified:
    - backend/src/main.py
    - backend/src/ingestion/__init__.py
    - backend/src/storage/__init__.py

decisions:
  - decision: "Upload returns PENDING immediately"
    rationale: "Docling processing takes 5-60s; blocking upload unacceptable"
    alternatives: ["Synchronous processing", "Websocket notification"]
  - decision: "Mock GCS client when bucket not configured"
    rationale: "Enables local development without GCS credentials"
    alternatives: ["Fail without config", "File-based mock"]
  - decision: "SHA-256 hash computed before DB insert"
    rationale: "Enables duplicate detection before storage costs incurred"
    alternatives: ["Post-upload hash check"]

metrics:
  duration: "10 min"
  completed: "2026-01-23"
  tasks: 3/3
  tests-added: 33
  test-coverage: "89%"
---

# Phase 2 Plan 3: DocumentService and Upload API Summary

## One-liner
DocumentService with SHA-256 duplicate detection and POST /api/documents returning PENDING immediately for async Docling processing.

## What Was Built

### DocumentService (`backend/src/ingestion/document_service.py`)
- Upload orchestration with validation, hashing, and storage
- SHA-256 hash computation before database insert for duplicate detection
- `DuplicateDocumentError` with 409 Conflict for duplicate files
- `DocumentUploadError` for GCS failures with proper status updates
- Upload returns PENDING status (Docling processing deferred to Phase 3 Cloud Tasks)
- `update_processing_result()` method for Cloud Tasks handler (Phase 3)

### GCS Client (`backend/src/storage/gcs_client.py`)
- Google Cloud Storage client using Application Default Credentials
- `upload()`, `download()`, `exists()`, `delete()` operations
- `GCSUploadError` and `GCSDownloadError` for error handling
- Signed URL generation for temporary access

### API Endpoints (`backend/src/api/documents.py`)
- `POST /api/documents/` - Multipart file upload (PDF, DOCX, PNG, JPG)
- `GET /api/documents/{id}` - Document details including processing status
- `GET /api/documents/` - Paginated document listing
- 400 for validation errors, 409 for duplicates, 500 for storage errors

### Dependencies (`backend/src/api/dependencies.py`)
- FastAPI dependency injection for GCSClient and DocumentService
- Mock GCS client when bucket not configured (local development)
- Type aliases: `DocumentServiceDep`, `DocumentRepoDep`, `GCSClientDep`

## Key Design Decisions

### 1. Async Processing Model
Upload returns immediately with `status=pending`. Docling processing (5-60 seconds per document) happens asynchronously via Cloud Tasks (Phase 3). This prevents blocking the API during long-running conversions.

### 2. SHA-256 Before Insert
File hash is computed before database insert to detect duplicates early. This prevents storing duplicate files in GCS and saves storage costs.

### 3. Error Handling (INGEST-14)
All error scenarios return proper HTTP status codes without crashing:
- 400: Invalid file type/size
- 409: Duplicate file (same hash exists)
- 500: GCS upload failure
- 404: Document not found
- 422: Invalid UUID format

## Tests Added

### Unit Tests (16 tests)
- `test_compute_file_hash` - SHA-256 computation
- `test_validate_file_*` - File type and size validation
- `test_upload_success_returns_pending` - Async model verification
- `test_upload_duplicate_rejected` - Duplicate detection
- `test_upload_gcs_failure_marks_failed` - Error handling
- `test_upload_does_not_call_docling` - Confirms no sync processing

### Integration Tests (17 tests)
- Upload success (PDF, DOCX, PNG)
- Validation errors (unsupported type, duplicate, empty file)
- GCS failure handling
- Document retrieval and listing
- Pagination
- Health check

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 53319a45 | DocumentService with upload orchestration |
| 2 | 61167ed0 | Document upload API endpoint |
| 3 | 0b455a94 | Integration tests for upload API |

## Verification Checklist

- [x] `python -c "from src.ingestion import DocumentService, DuplicateDocumentError"` succeeds
- [x] All 33 tests pass (16 unit + 17 integration)
- [x] `ruff check backend/src/` passes
- [x] Upload returns 201 with `status=pending`
- [x] Duplicate upload returns 409
- [x] GCS failure returns 500 without crash

## Deviations from Plan

### Auto-added (Rule 3 - Blocking)
**GCSClient creation**: Plan referenced `src/storage/gcs_client.py` but it didn't exist. Created the GCS client module to unblock DocumentService implementation.

## Next Phase Readiness

Phase 3 (Async Processing) can now:
1. Receive document_id from upload endpoint
2. Call `DocumentService.get_document()` to fetch document
3. Download from GCS using `gcs_uri`
4. Process with DoclingProcessor
5. Call `DocumentService.update_processing_result()` with status

No blockers identified for Phase 3.
