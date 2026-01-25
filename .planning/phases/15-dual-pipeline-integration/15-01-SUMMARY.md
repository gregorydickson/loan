---
phase: 15-dual-pipeline-integration
plan: 01
subsystem: api
tags: [fastapi, sqlalchemy, alembic, dual-pipeline, extraction-method, ocr]

# Dependency graph
requires:
  - phase: 14-ocr-routing-fallback
    provides: OCRRouter and OCRMode type alias
provides:
  - Document model with extraction_method and ocr_processed columns
  - Alembic migration 003 for new columns
  - Upload endpoint with method and ocr query parameters
  - ExtractionMethod and OCRMode type aliases in API
affects: [15-02, service-layer, cloud-tasks]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Query parameter defaults for backward compatibility (DUAL-09)
    - Nullable columns for legacy document support

key-files:
  created:
    - backend/alembic/versions/003_add_extraction_metadata.py
  modified:
    - backend/src/storage/models.py
    - backend/src/api/documents.py

key-decisions:
  - "Default method=docling preserves v1.0 backward compatibility (DUAL-09)"
  - "Nullable columns allow legacy documents to coexist without migration"
  - "ExtractionMethod includes 'auto' option for future auto-detection"

patterns-established:
  - "Dual pipeline parameters: method and ocr query params on upload endpoint"
  - "Extraction metadata tracking: extraction_method and ocr_processed on Document"

# Metrics
duration: 3min
completed: 2026-01-25
---

# Phase 15 Plan 01: Schema & API Parameters Summary

**Document model extended with extraction metadata columns; upload endpoint accepts method (docling|langextract|auto) and ocr (auto|force|skip) query parameters**

## Performance

- **Duration:** 3 min
- **Started:** 2026-01-25T16:21:39Z
- **Completed:** 2026-01-25T16:24:58Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Document model extended with extraction_method (String(20), nullable) and ocr_processed (Boolean, nullable) columns
- Alembic migration 003 created for backward-compatible schema changes
- Upload endpoint accepts ?method=docling|langextract|auto query parameter (default: docling)
- Upload endpoint accepts ?ocr=auto|force|skip query parameter (default: auto)
- DocumentUploadResponse includes extraction_method and ocr_processed fields

## Task Commits

Each task was committed atomically:

1. **Task 1: Add extraction metadata to Document model and create migration** - `a44a3946` (feat)
2. **Task 2: Add method and ocr query parameters to upload endpoint** - `bf4db07e` (feat)

## Files Created/Modified
- `backend/src/storage/models.py` - Added extraction_method and ocr_processed columns to Document model
- `backend/alembic/versions/003_add_extraction_metadata.py` - Migration for new columns
- `backend/src/api/documents.py` - Added ExtractionMethod/OCRMode types, method/ocr query params

## Decisions Made
- Default method=docling ensures existing clients continue to work (DUAL-09 backward compatibility)
- Columns are nullable so existing documents don't require migration data backfill
- ExtractionMethod includes 'auto' for future automatic pipeline selection

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Schema ready for dual pipeline tracking
- API accepts extraction parameters (not yet wired to service layer)
- Plan 02 will update DocumentService to use these parameters and route to correct extraction pipeline

---
*Phase: 15-dual-pipeline-integration*
*Completed: 2026-01-25*
