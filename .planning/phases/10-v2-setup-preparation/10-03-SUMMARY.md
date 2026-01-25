---
phase: 10-v2-setup-preparation
plan: 03
subsystem: infra
tags: [cloudbuild, gcp, iam, service-account, cloud-run]

# Dependency graph
requires:
  - phase: 10-01
    provides: GPU quota confirmed available
  - phase: 10-02
    provides: Terraform archived, ready for CloudBuild transition
provides:
  - cloudbuild-deployer service account configured in GCP
  - IAM roles for Cloud Run deployment
  - Repeatable setup script
affects: [phase-13-gpu-deployment, phase-16-cloudbuild-configs]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dedicated service account with least-privilege IAM roles"
    - "Idempotent shell scripts for GCP configuration"

key-files:
  created:
    - infrastructure/cloudbuild/setup-service-account.sh
    - docs/cloudbuild-setup.md
  modified: []

key-decisions:
  - "5 IAM roles chosen for least-privilege: run.developer, serviceAccountUser, artifactregistry.writer, secretmanager.secretAccessor, logging.logWriter"
  - "Service account named cloudbuild-deployer for clarity"
  - "Script designed to be idempotent for safe re-runs"

patterns-established:
  - "CloudBuild service account pattern: dedicated SA with scoped permissions"
  - "Infrastructure scripts in infrastructure/cloudbuild/ directory"

# Metrics
duration: ~8min
completed: 2026-01-24
---

# Phase 10 Plan 03: CloudBuild Service Account Summary

**Dedicated cloudbuild-deployer service account configured with 5 least-privilege IAM roles for Cloud Run deployment**

## Performance

- **Duration:** ~8 min (including checkpoint for user to run script)
- **Started:** 2026-01-24
- **Completed:** 2026-01-25T00:13:42Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- Created idempotent setup script for CloudBuild service account creation
- Configured 5 IAM roles following least-privilege principle
- Documented setup process and security considerations
- User verified service account created successfully in GCP

## Task Commits

Each task was committed atomically:

1. **Task 1: Create CloudBuild service account setup script** - `718cec8f` (chore)
2. **Task 2: Create CloudBuild setup documentation** - `6a782f0a` (docs)
3. **Task 3: Execute setup script to configure service account** - Human verification checkpoint (approved)

**Plan metadata:** (this commit)

## Files Created/Modified
- `infrastructure/cloudbuild/setup-service-account.sh` - Idempotent bash script that creates cloudbuild-deployer service account and grants 5 IAM roles
- `docs/cloudbuild-setup.md` - Documentation for CloudBuild setup process, IAM roles, and security notes

## Decisions Made

1. **5 IAM roles for least-privilege access:**
   - roles/run.developer - Deploy Cloud Run services
   - roles/iam.serviceAccountUser - Act as runtime service account
   - roles/artifactregistry.writer - Push container images
   - roles/secretmanager.secretAccessor - Read secrets during builds
   - roles/logging.logWriter - Write build logs

2. **Service account naming:** `cloudbuild-deployer` chosen for clarity about purpose

3. **Idempotent design:** Script checks if service account exists before creating, safe for multiple runs

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all steps completed successfully.

## User Setup Required

None - user completed the setup script execution during checkpoint verification.

## Next Phase Readiness

- CloudBuild service account is configured and ready for use
- Phase 13 (GPU deployment) and Phase 16 (CloudBuild configs) can use this service account
- Ready for 10-04 (End-to-End Verification) to validate all Phase 10 setup

---
*Phase: 10-v2-setup-preparation*
*Completed: 2026-01-24*
