---
phase: 16-cloudbuild-deployment
plan: 01
subsystem: infra
tags: [cloudbuild, cloud-run, docker, artifact-registry, gcp, cicd, gpu, secret-manager]

# Dependency graph
requires:
  - phase: 10-v2.0-setup
    provides: "CloudBuild service account setup and foundation"
  - phase: 13-lightonocr-gpu-service
    provides: "GPU service Dockerfile and deploy patterns"
provides:
  - "Backend CloudBuild configuration with Secret Manager integration"
  - "Frontend CloudBuild configuration with build-time environment variables"
  - "GPU service CloudBuild configuration with L4 GPU and extended timeouts"
affects: [16-02-trigger-setup, 16-03-rollback-procedures, deployment]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CloudBuild 3-step pattern: build → push → deploy"
    - "SHORT_SHA tagging for git-traceable deployments"
    - "Secret Manager runtime integration via --set-secrets"
    - "Build-arg pattern for Next.js NEXT_PUBLIC_* variables"
    - "Extended timeouts for GPU image builds (3600s step, 4800s total)"

key-files:
  created:
    - "infrastructure/cloudbuild/backend-cloudbuild.yaml"
    - "infrastructure/cloudbuild/frontend-cloudbuild.yaml"
    - "infrastructure/cloudbuild/gpu-cloudbuild.yaml"
  modified: []

key-decisions:
  - "Use --set-secrets for runtime secrets instead of build-time availableSecrets"
  - "Pass NEXT_PUBLIC_API_URL as build-arg for Next.js build-time baking"
  - "E2_HIGHCPU_32 machine type for GPU service builds (faster model download)"
  - "80-minute total timeout for GPU builds accommodates large base image + model"

patterns-established:
  - "CloudBuild YAML per service for independent deployments"
  - "Standard step IDs: build-{service}, push-{service}, deploy-{service}"
  - "Consistent substitution pattern: _REGION with default us-central1"

# Metrics
duration: 4min
completed: 2026-01-25
---

# Phase 16 Plan 01: CloudBuild Configuration Files Summary

**CloudBuild YAML configs for backend, frontend, and GPU services with Secret Manager and L4 GPU support**

## Performance

- **Duration:** 4 min
- **Started:** 2026-01-25T17:15:01Z
- **Completed:** 2026-01-25T17:19:00Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Backend CloudBuild with VPC egress for Cloud SQL and Secret Manager integration
- Frontend CloudBuild with NEXT_PUBLIC_API_URL build-arg pattern
- GPU service CloudBuild with L4 GPU configuration and extended timeouts

## Task Commits

Each task was committed atomically:

1. **Task 1: Create backend-cloudbuild.yaml** - `76063f17` (feat)
2. **Task 2: Create frontend-cloudbuild.yaml** - `b9174263` (feat)
3. **Task 3: Create gpu-cloudbuild.yaml** - `32519ed5` (feat)

## Files Created/Modified
- `infrastructure/cloudbuild/backend-cloudbuild.yaml` - Backend build/push/deploy with Secret Manager
- `infrastructure/cloudbuild/frontend-cloudbuild.yaml` - Frontend build/push/deploy with _BACKEND_URL substitution
- `infrastructure/cloudbuild/gpu-cloudbuild.yaml` - GPU service build/push/deploy with L4 GPU flags

## Decisions Made
- **Secret Manager via --set-secrets:** Runtime injection instead of build-time for security
- **Build-arg for NEXT_PUBLIC_API_URL:** Next.js requires env vars at build time
- **E2_HIGHCPU_32 for GPU builds:** Faster download/build for 8GB+ base image
- **loan-repo Artifact Registry:** Consistent repository name across all services

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required. Triggers will be configured in plan 16-02.

## Next Phase Readiness
- CloudBuild configs ready for GitHub trigger setup (plan 16-02)
- All three services can be manually deployed via `gcloud builds submit`
- Rollback procedures to be documented in plan 16-03

---
*Phase: 16-cloudbuild-deployment*
*Completed: 2026-01-25*
