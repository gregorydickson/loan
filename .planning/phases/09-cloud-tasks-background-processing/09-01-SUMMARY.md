---
phase: 09-cloud-tasks-background-processing
plan: 01
subsystem: infra
tags: [cloud-tasks, gcp, oidc, async, background-processing]

# Dependency graph
requires:
  - phase: 06-gcp-infrastructure
    provides: Cloud Tasks queue and IAM service account
provides:
  - CloudTasksClient wrapper for creating document processing tasks
  - Cloud Tasks configuration settings in Settings class
  - Cloud Run invoker IAM role for OIDC authentication
affects: [09-02, 09-03]

# Tech tracking
tech-stack:
  added: [google-cloud-tasks, types-protobuf]
  patterns: [OIDC token authentication for Cloud Run, async task queueing]

key-files:
  created: [backend/src/ingestion/cloud_tasks_client.py]
  modified: [backend/pyproject.toml, backend/src/config.py, infrastructure/terraform/iam.tf]

key-decisions:
  - "10-minute dispatch_deadline for Docling + LLM processing time"
  - "OIDC token with service_url as audience for Cloud Run authentication"
  - "Empty string defaults for all Cloud Tasks settings to allow local development"

patterns-established:
  - "CloudTasksClient: Wrapper class for Cloud Tasks API with typed methods"
  - "OIDC authentication: Service account invokes Cloud Run via OIDC token"

# Metrics
duration: 7min
completed: 2026-01-24
---

# Phase 9 Plan 1: Cloud Tasks Client and Configuration Summary

**CloudTasksClient wrapper with OIDC authentication for async document processing via google-cloud-tasks**

## Performance

- **Duration:** 7 min
- **Started:** 2026-01-24T20:30:00Z
- **Completed:** 2026-01-24T20:37:00Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Added google-cloud-tasks>=2.21.0 dependency with types-protobuf for mypy support
- Created CloudTasksClient class with create_document_processing_task method
- Configured Cloud Tasks settings (gcp_project_id, gcp_location, cloud_tasks_queue, cloud_run_service_url, cloud_run_service_account)
- Added roles/run.invoker IAM binding for OIDC token authentication

## Task Commits

Each task was committed atomically:

1. **Task 1: Add google-cloud-tasks dependency and Cloud Tasks settings** - `c6b8d9d3` (chore)
2. **Task 2: Create CloudTasksClient wrapper class** - `917c72f6` (feat)
3. **Task 3: Add Cloud Run invoker IAM role for task handler** - `2b59494f` (chore)

## Files Created/Modified
- `backend/pyproject.toml` - Added google-cloud-tasks and types-protobuf dependencies
- `backend/src/config.py` - Added Cloud Tasks configuration settings
- `backend/src/ingestion/cloud_tasks_client.py` - CloudTasksClient wrapper for task creation
- `infrastructure/terraform/iam.tf` - Added roles/run.invoker IAM binding

## Decisions Made
- **10-minute dispatch_deadline:** Matches Cloud Tasks queue config and allows sufficient time for Docling + LLM processing
- **OIDC token with service_url as audience:** Cloud Run validates OIDC tokens automatically, no custom auth code needed
- **Empty string defaults for config:** Allows local development without Cloud Tasks - client instantiation fails gracefully when not configured
- **types-protobuf dev dependency:** Required for mypy strict mode compliance with google.protobuf imports

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added types-protobuf for mypy strict**
- **Found during:** Task 2 (CloudTasksClient creation)
- **Issue:** mypy --strict failed with "Library stubs not installed for google.protobuf"
- **Fix:** Installed types-protobuf and added to dev dependencies
- **Files modified:** backend/pyproject.toml
- **Verification:** mypy --strict passes on cloud_tasks_client.py
- **Committed in:** 917c72f6 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Auto-fix essential for type checking compliance. No scope creep.

## Issues Encountered
- Terraform validate timed out due to backend configuration requiring network access - verified HCL syntax is correct by inspection

## User Setup Required

None - no external service configuration required. Cloud Tasks settings are provided via environment variables during deployment.

## Next Phase Readiness
- CloudTasksClient ready for use in upload endpoint (Plan 09-02)
- Task handler endpoint to be created (Plan 09-03)
- All Cloud Tasks configuration in Settings class

---
*Phase: 09-cloud-tasks-background-processing*
*Completed: 2026-01-24*
