---
phase: 15-dual-pipeline-integration
plan: 02
subsystem: api
tags: [fastapi, cloud-tasks, ocr-router, extraction-router, dual-pipeline]

# Dependency graph
requires:
  - phase: 15-01
    provides: Document model with extraction_method/ocr_processed columns, API query params
  - phase: 14-ocr-routing-fallback
    provides: OCRRouter with circuit breaker and Docling fallback
  - phase: 12-extraction-router
    provides: ExtractionRouter with LangExtract/Docling method selection
provides:
  - Cloud Tasks payload with method/ocr parameters
  - DocumentService wired to OCRRouter and ExtractionRouter
  - Task handler using OCRRouter before extraction (DUAL-04)
  - Full dual pipeline wiring from API to extraction
affects: [16-api-integration, production-deployment]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - OCR before extraction (DUAL-04)
    - ExtractionRouter for method selection
    - Cloud Tasks payload extension for dual pipeline params

key-files:
  created:
    - backend/tests/integration/test_dual_pipeline.py
  modified:
    - backend/src/ingestion/cloud_tasks_client.py
    - backend/src/api/tasks.py
    - backend/src/ingestion/document_service.py
    - backend/src/api/dependencies.py
    - backend/src/config.py

key-decisions:
  - "DUAL-04: OCRRouter runs BEFORE extraction when ocr != 'skip'"
  - "DUAL-09: Default method='docling' preserves backward compatibility"
  - "ProcessDocumentRequest defaults ensure backward compat with queued tasks"

patterns-established:
  - "OCR-then-extract pipeline: OCRRouter.process() -> ExtractionRouter.extract()"
  - "Cloud Tasks payload extension: add new fields with defaults for backward compat"
  - "Dependency injection for dual pipeline: OCRRouterDep, ExtractionRouterDep"

# Metrics
duration: 8min
completed: 2026-01-25
---

# Phase 15 Plan 02: Service Layer Integration Summary

**Cloud Tasks and DocumentService fully wired to pass method/ocr parameters through OCRRouter then ExtractionRouter, with backward-compatible defaults**

## Performance

- **Duration:** 8 min
- **Started:** 2026-01-25T16:30:21Z
- **Completed:** 2026-01-25T16:38:59Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- CloudTasksClient.create_document_processing_task() accepts extraction_method and ocr_mode
- Cloud Tasks JSON payload includes method and ocr fields for dual pipeline selection
- ProcessDocumentRequest has method/ocr fields with backward-compatible defaults (docling/auto)
- DocumentService.__init__() accepts ocr_router and extraction_router
- DocumentService.upload() accepts extraction_method and ocr_mode parameters
- OCRRouter runs BEFORE extraction in sync mode (DUAL-04)
- Task handler uses OCRRouter then ExtractionRouter for dual pipeline
- Document.ocr_processed set based on OCRResult.ocr_method != "none"
- Integration tests verify DUAL-08 (LangExtract populates character offsets)

## Task Commits

Each task was committed atomically:

1. **Task 1: Enhance Cloud Tasks payload with method and ocr parameters** - `991c3d32` (feat)
2. **Task 2: Wire DocumentService and task handler to use OCRRouter and ExtractionRouter** - `fd58551f` (feat)
3. **Task 3: Verify character offset handling and add integration test** - `40cd7e51` (test)

## Files Created/Modified

- `backend/src/ingestion/cloud_tasks_client.py` - Added extraction_method/ocr_mode params, method/ocr in payload
- `backend/src/api/tasks.py` - Added method/ocr fields to ProcessDocumentRequest, OCRRouter/ExtractionRouter in handler
- `backend/src/ingestion/document_service.py` - Added ocr_router/extraction_router params, OCR-then-extract pipeline
- `backend/src/api/dependencies.py` - Added get_ocr_router(), get_extraction_router(), updated get_document_service()
- `backend/src/config.py` - Added lightonocr_service_url setting
- `backend/tests/integration/test_dual_pipeline.py` - 6 tests for DUAL-08 and extraction router

## Decisions Made

- DUAL-04: OCRRouter runs BEFORE extraction to determine OCR need and process scanned documents
- DUAL-09: Default method='docling' ensures existing clients and queued tasks continue to work
- ProcessDocumentRequest defaults (method='docling', ocr='auto') maintain backward compatibility

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Full dual pipeline wiring complete from API through Cloud Tasks to extraction
- OCR routing integrated with scanned document detection
- Extraction routing with LangExtract/Docling/auto method selection
- Ready for Phase 16 (API integration testing) or production deployment

---
*Phase: 15-dual-pipeline-integration*
*Completed: 2026-01-25*
