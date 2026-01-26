---
phase: 21-ui-feature-verification
plan: 01
subsystem: api, ui
tags: [pydantic, typescript, source-attribution, char-offset, react]

# Dependency graph
requires:
  - phase: 20-core-extraction-verification
    provides: char_start/char_end stored in database via LangExtract
provides:
  - char_start/char_end fields exposed in API SourceReferenceResponse
  - SourceReference TypeScript interface with offset fields
  - "Exact Match" badge visual indicator for LangExtract extractions
affects: [21-02-ui-verification, future-highlighting-features]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Conditional badge rendering based on null check"
    - "API-frontend type contract alignment"

key-files:
  created: []
  modified:
    - backend/src/api/borrowers.py
    - frontend/src/lib/api/types.ts
    - frontend/src/components/borrowers/source-references.tsx

key-decisions:
  - "Badge indicator vs text highlighting - chose badge for simplicity (char offsets are document-level, not snippet-level)"

patterns-established:
  - "Pattern: Visual badge differentiation for extraction method (LangExtract vs Docling)"

# Metrics
duration: 40min
completed: 2026-01-26
---

# Phase 21 Plan 01: API and Frontend Offset Fields Summary

**Exposed char_start/char_end in SourceReferenceResponse API and added visual "Exact Match" badge in frontend for LangExtract extractions**

## Performance

- **Duration:** 40 min
- **Started:** 2026-01-26T17:15:57Z
- **Completed:** 2026-01-26T17:55:36Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- API now returns char_start and char_end fields in source reference responses
- Frontend TypeScript types updated to match API contract
- SourceReferences component displays "Exact Match" badge when character offsets present
- Backend deployed with CloudBuild (build 793308eb, 29 min)
- Frontend deployed with CloudBuild (build 18427397, 5 min)
- Verified API returns new fields and frontend loads successfully

## Task Commits

Each task was committed atomically:

1. **Task 1: Expose char_start/char_end in API response** - `0c9fbc30` (feat)
2. **Task 2: Update frontend types and add visual badge indicator** - `3fd06d4d` (feat)
3. **Task 3: Redeploy services to production** - No code changes, deployment only

## Files Created/Modified

- `backend/src/api/borrowers.py` - Added char_start/char_end to SourceReferenceResponse Pydantic model
- `backend/src/ingestion/__init__.py` - Fixed missing DuplicateDocumentError export (blocking issue)
- `frontend/src/lib/api/types.ts` - Added char_start/char_end to SourceReference interface
- `frontend/src/components/borrowers/source-references.tsx` - Added "Exact Match" badge display

## Decisions Made

- **Badge vs highlighting:** Chose visual badge indicator instead of text highlighting because char_start/char_end are positions in the full document text, not the snippet. Attempting substring highlighting within the snippet would require complex offset translation and could be error-prone. The badge clearly differentiates LangExtract results (have exact character positions) from Docling results (page-level only).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed missing DuplicateDocumentError export**
- **Found during:** Task 1 (API update)
- **Issue:** `DuplicateDocumentError` was removed in commit fe63aa66 but still exported in `__init__.py`, causing import failures
- **Fix:** Removed the stale export from `src/ingestion/__init__.py`
- **Files modified:** backend/src/ingestion/__init__.py
- **Verification:** All borrower route tests pass (12/12)
- **Committed in:** 0c9fbc30 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (blocking import fix)
**Impact on plan:** Essential fix to allow tests and deployment to proceed. No scope creep.

## Issues Encountered

- CloudBuild config files were in `infrastructure/cloudbuild/` not root directory (plan had incorrect path)
- Backend build took ~29 min due to Docling model downloads during Docker build

## Deployment Verification

| Service | Build ID | Status | Verification |
|---------|----------|--------|--------------|
| Backend | 793308eb | SUCCESS | /health returns 200, char_start in API |
| Frontend | 18427397 | SUCCESS | HTTP 200, loads without errors |

**API Contract Verification:**
```json
{
  "id": "eba6aff3-8a7b-4561-8b6d-cc74fe6a57c6",
  "document_id": "db645fd6-64b1-41c5-9833-6e4309d0a34b",
  "page_number": 1,
  "section": null,
  "snippet": "## Uniform Underwriting and Transmittal Summary...",
  "char_start": null,
  "char_end": null
}
```

Note: char_start/char_end are null for Docling extractions (page-level only). They will be populated for LangExtract extractions.

## Next Phase Readiness

- TEST-07 (character-level offset display) is now verifiable - API exposes fields, UI shows badge
- Plan 21-02 can proceed with manual UI verification of all tests (TEST-06 through TEST-09)
- "Exact Match" badge will appear for borrowers extracted via LangExtract method

---
*Phase: 21-ui-feature-verification*
*Completed: 2026-01-26*
