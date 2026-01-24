---
phase: 08-wire-document-to-extraction-pipeline
plan: 01
subsystem: api
tags: [fastapi, dependency-injection, extraction, borrower]

# Dependency graph
requires:
  - phase: 02-document-ingestion-pipeline
    provides: DocumentService with upload flow
  - phase: 03-llm-extraction-validation
    provides: BorrowerExtractor with all components
provides:
  - BorrowerExtractor DI factory with singleton pattern
  - DocumentService accepting extraction dependencies
  - Integration test fixtures with mock extractor
affects: [08-02 extraction-call-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Singleton pattern for expensive components (BorrowerExtractor)
    - TYPE_CHECKING for circular import avoidance

key-files:
  created: []
  modified:
    - backend/src/api/dependencies.py
    - backend/src/ingestion/document_service.py
    - backend/tests/integration/conftest.py

key-decisions:
  - "TYPE_CHECKING import to avoid circular dependency"
  - "Singleton pattern for BorrowerExtractor (expensive to instantiate)"

patterns-established:
  - "Pattern: Use TYPE_CHECKING and from __future__ import annotations for cross-module type hints that would cause circular imports"

# Metrics
duration: 6min
completed: 2026-01-24
---

# Phase 8 Plan 1: Extraction DI Wiring Summary

**BorrowerExtractor singleton injected into DocumentService via FastAPI DI, enabling extraction pipeline integration without calling it yet**

## Performance

- **Duration:** 6 min
- **Started:** 2026-01-24T19:46:02Z
- **Completed:** 2026-01-24T19:51:52Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- BorrowerExtractor DI factory with all 7 components (GeminiClient, ComplexityClassifier, DocumentChunker, FieldValidator, ConfidenceCalculator, BorrowerDeduplicator, ConsistencyValidator)
- DocumentService constructor extended to accept borrower_extractor and borrower_repository
- Integration test fixtures updated with mock_borrower_extractor, all 30 tests passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Add BorrowerExtractor DI factory** - `860d2e30` (feat)
2. **Task 2: Update DocumentService constructor** - `58d27a93` (feat)
3. **Task 3: Update integration test fixtures** - `1b1b9f74` (test)

## Files Created/Modified
- `backend/src/api/dependencies.py` - Added get_borrower_extractor() factory and BorrowerExtractorDep, updated get_document_service() to wire all 5 dependencies
- `backend/src/ingestion/document_service.py` - Extended constructor with borrower_extractor and borrower_repository parameters
- `backend/tests/integration/conftest.py` - Added mock_borrower_extractor fixture and updated all client fixtures

## Decisions Made
- **TYPE_CHECKING import pattern:** Used `from __future__ import annotations` and `TYPE_CHECKING` block to import BorrowerExtractor in document_service.py without causing circular import (extraction/extractor.py imports docling_processor from ingestion package)
- **Singleton pattern:** BorrowerExtractor instantiated once and cached, as it involves expensive component setup (GeminiClient, etc.)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Circular import resolution**
- **Found during:** Task 2 (DocumentService constructor update)
- **Issue:** Adding `from src.extraction import BorrowerExtractor` caused circular import (extraction -> ingestion -> extraction)
- **Fix:** Used TYPE_CHECKING pattern with `from __future__ import annotations` to defer type evaluation
- **Files modified:** backend/src/ingestion/document_service.py
- **Verification:** Import succeeds, DI chain resolves
- **Committed in:** 58d27a93 (Task 2 commit)

**2. [Rule 1 - Bug] Fixed ComplexityLevel enum value**
- **Found during:** Task 3 (test fixture creation)
- **Issue:** Used `ComplexityLevel.SIMPLE` which doesn't exist (correct value is `STANDARD`)
- **Fix:** Corrected to `ComplexityLevel.STANDARD` and added all required ComplexityAssessment fields
- **Files modified:** backend/tests/integration/conftest.py
- **Verification:** All 30 integration tests pass
- **Committed in:** 1b1b9f74 (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both auto-fixes necessary for correct operation. No scope creep.

## Issues Encountered
None - deviations handled automatically via deviation rules.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- DI wiring complete, DocumentService has access to BorrowerExtractor and BorrowerRepository
- Ready for Plan 08-02: Call extractor from upload() method and persist borrowers
- No blockers

---
*Phase: 08-wire-document-to-extraction-pipeline*
*Completed: 2026-01-24*
