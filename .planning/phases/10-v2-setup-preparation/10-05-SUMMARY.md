---
phase: 10-v2-setup-preparation
plan: 05
subsystem: infra
tags: [cloudbuild, gcp, iam, service-account, gap-closure]

# Dependency graph
requires:
  - phase: 10-03
    provides: setup-service-account.sh script (was never executed)
provides:
  - cloudbuild-deployer service account exists in GCP
  - 5 IAM roles granted for Cloud Run deployment
  - CBLD-08 requirement satisfied
affects: [phase-13-gpu-deployment, phase-16-cloudbuild-configs]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Gap closure plan pattern: Execute existing scripts that were missed"

key-files:
  created: []
  modified: []

key-decisions:
  - "Service account execution confirmed via gcloud verification commands"
  - "Gap closure plan created to address verification gaps without code changes"

patterns-established:
  - "Verification-driven gap closure: When verification finds execution gaps, create targeted plans"

# Metrics
duration: ~2min
completed: 2026-01-25
---

# Phase 10 Plan 05: CloudBuild Service Account Gap Closure Summary

**Executed setup-service-account.sh to create cloudbuild-deployer service account with 5 IAM roles, closing CBLD-08 gap**

## Performance

- **Duration:** ~2 min (checkpoint for user execution + verification)
- **Started:** 2026-01-24
- **Completed:** 2026-01-25T01:19:45Z
- **Tasks:** 1 (checkpoint:human-action)
- **Files modified:** 0 (GCP IAM changes only)

## Accomplishments
- Executed setup-service-account.sh script that was previously missed
- Created cloudbuild-deployer@memorygraph-prod.iam.gserviceaccount.com in GCP
- Granted all 5 required IAM roles for Cloud Run deployment
- Closed CBLD-08 gap identified in 10-VERIFICATION.md
- Unblocked Phase 13 (LightOnOCR GPU) and Phase 16 (CloudBuild configs)

## Task Commits

1. **Task 1: Execute CloudBuild service account setup script** - Human action checkpoint (approved)
   - No git commit (GCP IAM changes are external)

**Plan metadata:** (this commit)

## Files Created/Modified

No local files created or modified. This plan executed an existing script to configure GCP IAM resources.

**External resources created:**
- GCP Service Account: `cloudbuild-deployer@memorygraph-prod.iam.gserviceaccount.com`
  - Description: Service account for CloudBuild deployments to Cloud Run
  - Display Name: CloudBuild Deployer Service Account

**IAM roles granted:**
| Role | Purpose |
|------|---------|
| roles/artifactregistry.writer | Push container images to Artifact Registry |
| roles/iam.serviceAccountUser | Act as runtime service account during deployment |
| roles/logging.logWriter | Write build and deployment logs |
| roles/run.developer | Deploy and manage Cloud Run services |
| roles/secretmanager.secretAccessor | Read secrets during builds |

## Decisions Made

None - executed plan exactly as written. This was a straightforward gap closure.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - script executed successfully on first attempt.

## User Setup Required

None - user completed the setup script execution during checkpoint.

## Verification Evidence

**Service Account Details (verified):**
```
description: Service account for CloudBuild deployments to Cloud Run
displayName: CloudBuild Deployer Service Account
email: cloudbuild-deployer@memorygraph-prod.iam.gserviceaccount.com
```

**IAM Roles (5/5 confirmed):**
```
ROLE
roles/artifactregistry.writer
roles/iam.serviceAccountUser
roles/logging.logWriter
roles/run.developer
roles/secretmanager.secretAccessor
```

## Gap Closure Context

**Background:**
Plan 10-03-PLAN.md created the setup script but the checkpoint was marked approved without actual execution. The 10-VERIFICATION.md audit discovered this gap (service account NOT_FOUND in GCP).

**Resolution:**
This gap closure plan (10-05) provided explicit instructions to execute the script and verify the results. User confirmed execution with verification output.

**Requirements satisfied:**
- CBLD-08: CloudBuild service account configured with necessary permissions - NOW SATISFIED

## Next Phase Readiness

- Phase 10 fully complete (all gaps closed)
- Phase 13 (LightOnOCR GPU) unblocked - can deploy using cloudbuild-deployer service account
- Phase 16 (CloudBuild configs) unblocked - can configure deployments
- Ready to proceed with Phase 11 (LangExtract Integration)

---
*Phase: 10-v2-setup-preparation*
*Completed: 2026-01-25*
