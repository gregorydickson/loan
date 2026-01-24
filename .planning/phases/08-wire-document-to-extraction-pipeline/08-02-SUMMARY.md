---
phase: 08-wire-document-to-extraction-pipeline
plan: 02
subsystem: extraction
tags: [borrower-extraction, document-pipeline, sse-hash, pii-protection, sqlalchemy]

# Dependency graph
requires:
  - phase: 08-01
    provides: BorrowerExtractor DI wiring into DocumentService
  - phase: 02
    provides: DocumentService with Docling processing
  - phase: 03
    provides: BorrowerExtractor pipeline with validation
  - phase: 04
    provides: BorrowerRepository for database persistence
provides:
  - Complete document-to-extraction pipeline integration
  - SSN hashing for PII protection
  - Borrower persistence with source attribution
affects: [09-extraction-quality-monitoring, frontend-borrower-views]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pydantic to SQLAlchemy model conversion pattern"
    - "Graceful degradation on extraction failures"
    - "Nested exception handling for partial success"

key-files:
  created: []
  modified:
    - backend/src/ingestion/document_service.py

key-decisions:
  - "SSN hashed with SHA-256 before storage (never stored raw)"
  - "Extraction failures logged but don't fail document upload"
  - "Individual borrower persistence errors don't fail extraction"

patterns-established:
  - "Model conversion: Pydantic -> SQLAlchemy with intermediate processing"
  - "Graceful degradation: log warnings, continue processing"

# Metrics
duration: 8min
completed: 2026-01-24
---

# Phase 08 Plan 02: Pipeline Integration Summary

**DocumentService.upload() now extracts and persists borrowers with SSN hashing after Docling processing**

## Performance

- **Duration:** 8 min
- **Started:** 2026-01-24T20:00:00Z
- **Completed:** 2026-01-24T20:08:00Z
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments
- Integrated BorrowerExtractor.extract() call into upload() workflow
- Added _persist_borrower() method to convert Pydantic models to SQLAlchemy
- Implemented SSN hashing with SHA-256 for PII protection
- Graceful error handling: extraction failures don't fail document upload

## Task Commits

Each task was committed atomically:

1. **Task 1: Add _persist_borrower helper method** - `d5a2c9b8` (feat)
2. **Task 2: Integrate extraction into upload() method** - `f19f5d07` (feat)
3. **Task 3: Update docstrings** - included in Task 1 commit

**Plan metadata:** pending (docs: complete plan)

## Files Created/Modified
- `backend/src/ingestion/document_service.py` - Added extraction integration and _persist_borrower helper

## Decisions Made
- **SSN hashing:** SHA-256 hash stored instead of raw SSN for PII protection
- **Address serialization:** Address model serialized to JSON for storage
- **Error handling:** Extraction failures logged as warnings, don't fail document
- **Persistence errors:** Individual borrower persistence errors logged, don't stop extraction loop

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - implementation proceeded as planned.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Document-to-extraction pipeline is now fully wired
- Uploading a document triggers borrower extraction automatically
- Phase 8 complete: gap between document ingestion and extraction is closed
- Ready for Phase 9: extraction quality monitoring

---
*Phase: 08-wire-document-to-extraction-pipeline*
*Completed: 2026-01-24*
