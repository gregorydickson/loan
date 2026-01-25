---
phase: 17-testing-quality
plan: 01
subsystem: testing
tags: [pytest, mypy, type-checking, unit-tests, coverage]

# Dependency graph
requires:
  - phase: 15-dual-pipeline-integration
    provides: DocumentService with borrower_extractor and borrower_repository params
provides:
  - All unit tests passing (0 failures)
  - mypy strict mode passing (0 errors)
  - Test coverage at 87% (above 80% threshold)
affects: [17-02, 17-03, 18-verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - mypy overrides for libraries without type stubs (pypdfium2, aiobreaker, google.oauth2.id_token)
    - Type-safe conversions for library returns (Match to tuple, Any to explicit types)

key-files:
  created: []
  modified:
    - backend/tests/unit/test_document_service.py
    - backend/pyproject.toml
    - backend/src/extraction/offset_translator.py
    - backend/src/extraction/langextract_processor.py
    - backend/src/extraction/langextract_visualizer.py
    - backend/src/ocr/lightonocr_client.py
    - backend/src/ocr/ocr_router.py
    - backend/src/ingestion/document_service.py

key-decisions:
  - "Use mypy overrides with follow_imports=skip for untyped libraries"
  - "Add type:ignore[untyped-decorator] for aiobreaker circuit breaker decorator"
  - "Convert difflib Match namedtuples to explicit tuple[int,int,int] for type safety"
  - "Add explicit None checks before iteration on optional collections"

patterns-established:
  - "Pattern: Always add mock fixtures for new constructor dependencies in test files"
  - "Pattern: Use cast() or explicit type annotations when working with untyped library returns"

# Metrics
duration: 9min
completed: 2026-01-25
---

# Phase 17 Plan 01: Test Baseline & mypy Strict Summary

**Fixed 15 failing tests by updating DocumentService constructor calls and resolved 14 mypy strict mode errors across 7 source files**

## Performance

- **Duration:** 9 min
- **Started:** 2026-01-25T18:07:34Z
- **Completed:** 2026-01-25T18:16:45Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments
- All 17 tests in test_document_service.py now pass (was 15 failing)
- mypy strict mode passes with 0 errors in 41 source files (was 14 errors)
- Test suite: 476 passed, 1 skipped
- Coverage: 86.98% (above 80% threshold)
- TEST-11 (coverage) and TEST-12 (mypy strict) requirements satisfied

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix test_document_service.py constructor calls** - `6c1d872f` (fix)
2. **Task 2: Fix mypy errors in source files** - `e596f976` (fix)
3. **Task 3: Verify test suite health** - (verification only, no commit needed)

## Files Created/Modified
- `backend/tests/unit/test_document_service.py` - Added mock_borrower_extractor/mock_borrower_repository fixtures, updated all DocumentService instantiations
- `backend/pyproject.toml` - Added mypy overrides for pypdfium2, aiobreaker, google.oauth2.id_token
- `backend/src/extraction/offset_translator.py` - Fixed Match to tuple conversion in _build_alignment_map
- `backend/src/extraction/langextract_processor.py` - Added None checks for result.extractions and char offsets
- `backend/src/extraction/langextract_visualizer.py` - Added explicit type annotations for lx.visualize return
- `backend/src/ocr/lightonocr_client.py` - Added cast for id_token.fetch_id_token, annotated text variable
- `backend/src/ocr/ocr_router.py` - Added type:ignore for aiobreaker decorator, annotated state_name
- `backend/src/ingestion/document_service.py` - Added Literal type validation for ocr_mode parameter

## Decisions Made
- Used mypy overrides with `follow_imports = "skip"` for libraries without type stubs rather than inline type:ignore comments
- Added explicit tuple conversion for difflib.SequenceMatcher.get_matching_blocks() return value for type safety
- Used `type: ignore[untyped-decorator]` for aiobreaker circuit breaker since it lacks type stubs
- Added runtime validation + type cast for ocr_mode parameter to satisfy Literal type requirements

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- pypdfium2 import-untyped error persisted despite pyproject.toml override until `follow_imports = "skip"` was added
- Mypy `unused-ignore` errors when trying inline type:ignore comments for already-overridden modules

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Green test baseline established for Phase 17 Plan 02 (integration tests) and Plan 03 (API tests)
- mypy strict mode enforced for all future development
- Coverage baseline at 87% provides room for additional test coverage improvements

---
*Phase: 17-testing-quality*
*Completed: 2026-01-25*
