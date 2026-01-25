---
phase: 14-ocr-routing-fallback
plan: 01
subsystem: ocr
tags: [pypdfium2, pdf, scanned-detection, text-extraction, ocr-routing]

# Dependency graph
requires:
  - phase: 13-lightonocr-gpu-service
    provides: LightOnOCRClient for GPU OCR communication
provides:
  - ScannedDocumentDetector class with text ratio detection
  - DetectionResult dataclass for structured output
  - Page-level and document-level scanned detection
  - Configurable thresholds for detection tuning
affects: [14-02-ocr-router, 15-api-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Text ratio detection for scanned PDF identification
    - Conservative error handling (assume scanned on failure)
    - Configurable thresholds for different document types

key-files:
  created:
    - backend/src/ocr/scanned_detector.py
    - backend/tests/unit/ocr/test_scanned_detector.py
  modified:
    - backend/src/ocr/__init__.py

key-decisions:
  - "MIN_CHARS_THRESHOLD=50 as starting point for scanned page detection"
  - "SCANNED_RATIO_THRESHOLD=0.5 triggers full-document OCR"
  - "Conservative error handling: assume scanned on parse/extraction failures"
  - "pypdfium2 (via Docling) for text extraction - no new dependencies"

patterns-established:
  - "Scanned detection via text extraction ratio using pypdfium2"
  - "DetectionResult dataclass for structured detection output"
  - "Both document-level and page-level detection APIs"

# Metrics
duration: 4min
completed: 2026-01-25
---

# Phase 14 Plan 01: Scanned Document Detection Summary

**ScannedDocumentDetector using pypdfium2 text ratio detection with configurable thresholds and comprehensive test coverage**

## Performance

- **Duration:** 4 min
- **Started:** 2026-01-25T15:36:39Z
- **Completed:** 2026-01-25T15:40:06Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- ScannedDocumentDetector class with pypdfium2 text extraction ratio detection
- DetectionResult dataclass providing structured output (needs_ocr, scanned_pages, total_pages, scanned_ratio)
- Configurable thresholds for MIN_CHARS_THRESHOLD and SCANNED_PAGE_RATIO_THRESHOLD
- Both document-level detect() and page-level detect_page() methods
- 17 comprehensive unit tests with 100% coverage on scanned_detector.py
- LOCR-05 requirement satisfied: Scanned document detection implemented

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ScannedDocumentDetector** - `1b82d321` (feat)
2. **Task 2: Update OCR module exports** - `b14972e1` (feat)
3. **Task 3: Create unit tests for ScannedDocumentDetector** - `44a8d735` (test)

## Files Created/Modified

- `backend/src/ocr/scanned_detector.py` - ScannedDocumentDetector class and DetectionResult dataclass (177 lines)
- `backend/src/ocr/__init__.py` - Updated module exports to include new detector
- `backend/tests/unit/ocr/test_scanned_detector.py` - Comprehensive unit tests (323 lines, 17 test cases)

## Decisions Made

- **MIN_CHARS_THRESHOLD=50:** Starting point for detecting scanned pages; pages with <50 extractable characters considered scanned
- **SCANNED_RATIO_THRESHOLD=0.5:** Documents with >=50% scanned pages trigger full-document OCR routing
- **Conservative error handling:** On PDF parse failures or text extraction exceptions, assume document needs OCR
- **No new dependencies:** Uses pypdfium2 already installed via Docling

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all tasks completed successfully.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- ScannedDocumentDetector ready for integration into OCRRouter (14-02)
- DetectionResult provides all information needed for routing decisions
- Page-level detection enables selective OCR of mixed documents
- Thresholds are configurable for tuning based on production data

---
*Phase: 14-ocr-routing-fallback*
*Completed: 2026-01-25*
