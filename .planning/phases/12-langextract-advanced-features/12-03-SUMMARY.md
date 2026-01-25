---
phase: 12-langextract-advanced-features
plan: 03
subsystem: extraction
tags: [tenacity, retry, fallback, langextract, docling, error-handling]

# Dependency graph
requires:
  - phase: 12-01
    provides: ExtractionConfig dataclass for configurable extraction parameters
  - phase: 11-03
    provides: LangExtractProcessor and LangExtractResult for primary extraction
  - phase: 03-01
    provides: BorrowerExtractor for Docling-based fallback extraction
provides:
  - ExtractionRouter with method selection (langextract, docling, auto)
  - Tenacity retry with exponential backoff for transient errors
  - Graceful fallback to Docling on LangExtract failures
  - LangExtractTransientError and LangExtractFatalError exception classes
affects: [13-api-integration, 14-extraction-endpoints]

# Tech tracking
tech-stack:
  added: []  # tenacity already installed
  patterns: [tenacity-retry, dual-extraction-fallback, error-classification]

key-files:
  created:
    - backend/src/extraction/extraction_router.py
    - backend/tests/unit/extraction/test_extraction_router.py
  modified: []

key-decisions:
  - "Transient errors (503, 429, timeout, overloaded, rate limit) retry 3x with exponential backoff"
  - "Fatal errors trigger immediate fallback without retry"
  - "method='auto' (default) tries LangExtract first, falls back to Docling on failure"
  - "method='langextract' raises exception on failure (no fallback)"

patterns-established:
  - "Error classification: string pattern matching for transient vs fatal"
  - "Retry config: multiplier=2, min=4s, max=60s, 3 attempts"

# Metrics
duration: 4min
completed: 2026-01-25
---

# Phase 12 Plan 03: Extraction Router Summary

**ExtractionRouter with tenacity retry, transient/fatal error classification, and graceful Docling fallback for LXTR-11**

## Performance

- **Duration:** 4 min
- **Started:** 2026-01-25T12:09:25Z
- **Completed:** 2026-01-25T12:13:25Z
- **Tasks:** 2/2
- **Files created:** 2

## Accomplishments

- ExtractionRouter routes between LangExtract and Docling extraction methods
- Tenacity @retry decorator with exponential backoff (2, 4, 8... max 60 seconds)
- Transient error classification: 503, 429, timeout, overloaded, rate limit
- 25 comprehensive unit tests with mocking for all scenarios

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ExtractionRouter with tenacity retry** - `e97bd83c` (feat)
2. **Task 2: Create unit tests for ExtractionRouter** - `2146feb7` (test)

## Files Created

- `backend/src/extraction/extraction_router.py` - Router with method selection, retry logic, and fallback (172 lines)
- `backend/tests/unit/extraction/test_extraction_router.py` - Unit tests for all router functionality (255 lines)

## Decisions Made

- **Transient error patterns:** 503, 429, timeout, overloaded, rate limit - all retry with backoff
- **Retry configuration:** 3 attempts, exponential backoff (multiplier=2, min=4s, max=60s)
- **Method parameter:** "auto" (default) provides fallback; "langextract" raises on error; "docling" uses Docling only

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - implementation followed plan specification.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 12 complete with all 3 plans executed
- ExtractionConfig, LangExtractVisualizer, and ExtractionRouter all ready
- Ready for Phase 13: API Integration to wire router into extraction endpoints
- Requirements satisfied: LXTR-06, LXTR-07, LXTR-10, LXTR-11

---
*Phase: 12-langextract-advanced-features*
*Completed: 2026-01-25*
