---
phase: 14-ocr-routing-fallback
plan: 02
subsystem: ocr
tags: [aiobreaker, circuit-breaker, ocr-routing, docling, lightonocr, pypdfium2]

# Dependency graph
requires:
  - phase: 13-lightonocr-gpu-service
    provides: LightOnOCRClient for GPU OCR
  - phase: 14-01
    provides: ScannedDocumentDetector for PDF classification
provides:
  - OCRRouter with circuit breaker protection
  - OCRMode type (auto/force/skip)
  - OCRResult dataclass for tracking OCR method
  - Automatic Docling fallback on GPU unavailability
affects: [15-dual-pipeline-integration, 16-api-parameters]

# Tech tracking
tech-stack:
  added: [aiobreaker>=1.2.0]
  patterns: [circuit-breaker-pattern, gpu-service-fallback, ocr-mode-routing]

key-files:
  created:
    - backend/src/ocr/ocr_router.py
    - backend/tests/unit/ocr/test_ocr_router.py
  modified:
    - backend/pyproject.toml
    - backend/src/ocr/__init__.py

key-decisions:
  - "Circuit breaker: fail_max=3, timeout_duration=60s via aiobreaker"
  - "aiobreaker uses timeout_duration parameter (not reset_timeout as in docs)"
  - "OCR modes: auto (detect), force (always OCR), skip (never OCR)"
  - "GPU health check before OCR attempt for fast-fail behavior"
  - "Circuit breaker state exposed as lowercase string via get_circuit_breaker_state()"

patterns-established:
  - "Circuit breaker pattern: module-level breaker with decorator on async methods"
  - "OCR fallback pattern: try GPU health check, fall back to Docling on error"
  - "Mode-based routing: Literal type alias for constrained parameter values"

# Metrics
duration: 6min
completed: 2026-01-25
---

# Phase 14 Plan 02: OCR Router Summary

**OCRRouter with aiobreaker circuit breaker (fail_max=3, 60s timeout), OCR mode parameter (auto/force/skip), and automatic Docling fallback on GPU unavailability**

## Performance

- **Duration:** 6 min
- **Started:** 2026-01-25T15:41:00Z
- **Completed:** 2026-01-25T15:47:00Z
- **Tasks:** 4
- **Files modified:** 4

## Accomplishments
- OCRRouter class with intelligent routing between GPU OCR and Docling fallback
- Circuit breaker protection with fail_max=3 failures, 60-second timeout
- OCR mode parameter: "auto" (detect), "force" (always), "skip" (never)
- 18 comprehensive unit tests covering all routing scenarios

## Task Commits

Each task was committed atomically:

1. **Task 1: Add aiobreaker dependency** - `7a49d951` (chore)
2. **Task 2: Create OCRRouter with circuit breaker** - `48ade78f` (feat)
3. **Task 3: Update OCR module exports** - `60ad5b90` (chore)
4. **Task 4: Create unit tests for OCRRouter** - `97165649` (test)

## Files Created/Modified
- `backend/pyproject.toml` - Added aiobreaker>=1.2.0 dependency
- `backend/src/ocr/ocr_router.py` - OCRRouter with circuit breaker and fallback (286 lines)
- `backend/src/ocr/__init__.py` - Exported OCRRouter, OCRMode, OCRResult
- `backend/tests/unit/ocr/test_ocr_router.py` - 18 unit tests (346 lines)

## Decisions Made
- **aiobreaker API:** Uses `timeout_duration` parameter (not `reset_timeout` as in some docs)
- **Circuit breaker state:** Returns lowercase string (e.g., "closed") via `.name.lower()` on enum
- **CircuitBreakerError constructor:** Requires `(message: str, reopen_time: datetime)` signature
- **Health check first:** GPU health_check() called before OCR attempt for fast-fail

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed aiobreaker API parameter name**
- **Found during:** Task 2 (Create OCRRouter)
- **Issue:** Plan specified `reset_timeout` but aiobreaker uses `timeout_duration`
- **Fix:** Changed parameter name to `timeout_duration=timedelta(seconds=60)`
- **Files modified:** backend/src/ocr/ocr_router.py
- **Verification:** Import succeeds, circuit breaker configured correctly
- **Committed in:** 48ade78f (Task 2 commit)

**2. [Rule 1 - Bug] Fixed get_circuit_breaker_state return type**
- **Found during:** Task 4 (Unit tests)
- **Issue:** current_state returns enum, not string - tests failing
- **Fix:** Changed to return `_gpu_ocr_breaker.current_state.name.lower()`
- **Files modified:** backend/src/ocr/ocr_router.py
- **Verification:** All tests pass
- **Committed in:** 97165649 (Task 4 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both fixes necessary for correct operation. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- LOCR-05 complete: Scanned document detection with routing
- LOCR-11 complete: Docling OCR fallback when GPU unavailable
- Phase 14 complete, ready for Phase 15 (Dual Pipeline Integration)
- OCRRouter ready for API endpoint integration

---
*Phase: 14-ocr-routing-fallback*
*Completed: 2026-01-25*
