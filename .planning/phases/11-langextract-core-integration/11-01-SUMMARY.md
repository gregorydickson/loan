---
phase: 11-langextract-core-integration
plan: 01
subsystem: database
tags: [pydantic, sqlalchemy, alembic, source-reference, char-offset]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: Initial SourceReference model structure
provides:
  - char_start/char_end fields on Pydantic SourceReference
  - char_start/char_end columns on ORM SourceReference
  - Alembic migration 002_add_char_offsets.py
affects: [11-02, 11-03, 11-04, dual-pipeline, langextract]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Nullable optional fields for backward compatibility"
    - "Matching Pydantic/ORM field names for seamless conversion"

key-files:
  created:
    - backend/alembic/versions/002_add_char_offsets.py
  modified:
    - backend/src/models/document.py
    - backend/src/storage/models.py

key-decisions:
  - "Fields are nullable with None default for v1.0 backward compatibility"
  - "ge=0 constraint on Pydantic fields prevents negative character positions"

patterns-established:
  - "Schema evolution: Add nullable columns first, migrate data later"

# Metrics
duration: 3min
completed: 2026-01-25
---

# Phase 11 Plan 01: Schema Updates for Character Offsets Summary

**char_start/char_end fields added to SourceReference Pydantic and ORM models with Alembic migration for LangExtract character-level source grounding**

## Performance

- **Duration:** 3 min
- **Started:** 2026-01-25T02:13:57Z
- **Completed:** 2026-01-25T02:17:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added char_start and char_end optional integer fields to Pydantic SourceReference with ge=0 constraint
- Added char_start and char_end nullable Integer columns to ORM SourceReference
- Created Alembic migration 002_add_char_offsets.py with proper upgrade/downgrade functions
- Maintained backward compatibility - existing v1.0 code works with null char offsets

## Task Commits

Each task was committed atomically:

1. **Task 1: Add char_start/char_end to Pydantic SourceReference** - `21c847d3` (feat)
2. **Task 2: Add char_start/char_end to ORM SourceReference and create migration** - `8c3be227` (feat)

## Files Created/Modified
- `backend/src/models/document.py` - Added char_start/char_end optional fields with Field constraints
- `backend/src/storage/models.py` - Added char_start/char_end nullable Integer mapped columns
- `backend/alembic/versions/002_add_char_offsets.py` - Migration to add columns to source_references table

## Decisions Made
- Fields default to None for backward compatibility with existing v1.0 Docling extractions
- Using ge=0 constraint on Pydantic fields to prevent invalid negative positions
- Placed fields after snippet column in both models for logical grouping

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Schema updates complete for LangExtract integration
- Ready for 11-02 (few-shot examples) and 11-03 (LangExtractProcessor)
- No blockers for next plans in phase

---
*Phase: 11-langextract-core-integration*
*Plan: 01*
*Completed: 2026-01-25*
