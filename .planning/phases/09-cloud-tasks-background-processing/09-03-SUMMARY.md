---
phase: 09-cloud-tasks-background-processing
plan: 03
subsystem: ingestion
tags: [cloud-tasks, fastapi, dependency-injection, async-processing]

# Dependency graph
requires:
  - phase: 09-01
    provides: CloudTasksClient for creating processing tasks
  - phase: 09-02
    provides: Task handler endpoint to receive callbacks
provides:
  - CloudTasksClient dependency injection in FastAPI
  - Async task queueing in DocumentService.upload()
  - Sync fallback for local development
affects: [09-04]

# Tech tracking
tech-stack:
  added: []
  patterns: [async-first-upload, sync-fallback-pattern]

key-files:
  created: []
  modified:
    - backend/src/api/dependencies.py
    - backend/src/ingestion/document_service.py
    - backend/src/api/documents.py

key-decisions:
  - "CloudTasksClient returns None when GCP settings not configured (local dev)"
  - "Async mode queues task and returns PENDING immediately"
  - "Sync mode (local dev) processes inline for testing without Cloud Tasks"

patterns-established:
  - "Async-first upload: Queue task, return PENDING, let handler process"
  - "Config-based feature toggle: Check settings.gcp_project_id to enable/disable Cloud Tasks"

# Metrics
duration: 5min
completed: 2026-01-24
---

# Phase 9 Plan 3: Wire Async Task Queueing into Document Upload Flow Summary

**DocumentService.upload() now queues Cloud Tasks in production, falls back to sync processing for local development**

## Performance

- **Duration:** 5 min
- **Started:** 2026-01-24T21:10:07Z
- **Completed:** 2026-01-24T21:14:44Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- CloudTasksClient injected via FastAPI dependencies with singleton pattern
- DocumentService.upload() queues Cloud Task when configured, returns PENDING immediately
- Local development continues to work without Cloud Tasks (sync processing)
- Upload endpoint documentation updated to reflect async behavior

## Task Commits

Each task was committed atomically:

1. **Task 1: Add CloudTasksClient dependency injection** - `63a7b275` (feat)
2. **Task 2: Modify DocumentService to queue tasks** - `01640e41` (feat)
3. **Task 3: Update upload endpoint response messaging** - `5ab85623` (docs)

## Files Created/Modified

- `backend/src/api/dependencies.py` - Added CloudTasksClient singleton and dependency, updated get_document_service
- `backend/src/ingestion/document_service.py` - Added cloud_tasks_client parameter, async task queueing in upload()
- `backend/src/api/documents.py` - Updated docstrings and PENDING status message

## Decisions Made

- **CloudTasksClient returns None for local dev:** Check `settings.gcp_project_id` and `settings.cloud_run_service_url` - if either empty, return None
- **Async mode queues and returns PENDING:** No waiting for processing, immediate response
- **Sync mode preserved for local development:** When cloud_tasks_client is None, existing Docling+extraction flow runs inline
- **Task queueing failure marks document FAILED:** If we can't queue, document status becomes FAILED with error message

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all tasks completed successfully.

## User Setup Required

None - no external service configuration required. Cloud Tasks settings are already defined in config.py from Phase 09-01.

## Next Phase Readiness

- Async upload flow is complete and ready for integration testing
- Task handler (09-02) is ready to receive callbacks
- Next: 09-04 will add integration tests for the full async flow

---
*Phase: 09-cloud-tasks-background-processing*
*Completed: 2026-01-24*
