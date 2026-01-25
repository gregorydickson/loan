---
phase: 19-production-deployment-verification
plan: 02
subsystem: infra
tags: [gcp, cloud-run, cloudBuild, deployment, nextjs, frontend]

# Dependency graph
requires:
  - phase: 19-01
    provides: Backend Cloud Run service URL for NEXT_PUBLIC_API_URL build arg
  - phase: 16-cloudbuild-deployment
    provides: CloudBuild configurations for frontend service
provides:
  - Frontend Cloud Run service deployed and accessible
  - Frontend URL for Phase 20 Chrome verification
affects: [19-03, 20-chrome-verification, 21-final-validation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Frontend deployed with backend URL baked in at build time via CloudBuild substitution
    - Cloud Run allUsers IAM binding for public access

key-files:
  created: []
  modified: []

key-decisions:
  - "Added allUsers IAM binding manually (CloudBuild --allow-unauthenticated did not apply binding)"

patterns-established:
  - "Frontend CloudBuild uses _BACKEND_URL substitution for NEXT_PUBLIC_API_URL"
  - "Cloud Run services need explicit IAM binding for public access"

# Metrics
duration: 8min
completed: 2026-01-25
---

# Phase 19 Plan 02: Frontend Deployment Summary

**Next.js frontend deployed to Cloud Run at https://loan-frontend-prod-793446666872.us-central1.run.app with backend URL baked in**

## Performance

- **Duration:** 8 min
- **Started:** 2026-01-25T23:51:00Z
- **Completed:** 2026-01-26T00:00:00Z
- **Tasks:** 3
- **Files modified:** 0

## Accomplishments
- Frontend service `loan-frontend-prod` deployed and accessible
- Frontend loads with HTTP 200 showing full Next.js application
- Backend URL correctly passed via CloudBuild substitution
- IAM binding configured for public access

## Task Commits

No code changes were made during this plan execution. All work was CloudBuild deployment and GCP configuration.

- **Task 1:** Verification only - confirmed backend URL available
- **Task 2:** CloudBuild deployment - build ID `f8e52961-3d60-4adb-ba39-655c2d4f3ed1`
- **Task 3:** Verification only - confirmed frontend loads with 200

## Files Created/Modified
None - used existing CloudBuild configuration

## Decisions Made
- Added allUsers IAM binding manually after CloudBuild `--allow-unauthenticated` flag did not create the binding (behavior difference from expected)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added allUsers IAM policy binding**
- **Found during:** Task 3 (Frontend verification)
- **Issue:** Frontend returned 403 Forbidden despite CloudBuild using --allow-unauthenticated flag
- **Fix:** `gcloud run services add-iam-policy-binding loan-frontend-prod --region=us-central1 --member="allUsers" --role="roles/run.invoker"`
- **Files modified:** None (GCP IAM configuration)
- **Verification:** curl returns HTTP 200 after IAM fix

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** IAM binding required for public access. CloudBuild --allow-unauthenticated flag alone was insufficient.

## Issues Encountered
None - deployment and verification proceeded as expected after IAM fix.

## Frontend Details

**Frontend URL:** https://loan-frontend-prod-793446666872.us-central1.run.app

**Alternative URL:** https://loan-frontend-prod-fjz2snvxjq-uc.a.run.app

**Backend URL used:** https://loan-backend-prod-fjz2snvxjq-uc.a.run.app

**Build details:**
- Build ID: f8e52961-3d60-4adb-ba39-655c2d4f3ed1
- Duration: 4 min 41 sec
- Image: us-central1-docker.pkg.dev/memorygraph-prod/loan-repo/frontend:7d106364

**HTML verification:**
- Title: "Loan Document Extraction"
- Application: "Loan Doc Intel" sidebar with Documents, Borrowers, Architecture navigation
- Dashboard shows Total Documents, Total Borrowers, Recent Uploads cards

## Next Phase Readiness

**Ready for Plan 19-03 (End-to-End Verification):**
- Frontend URL accessible: https://loan-frontend-prod-793446666872.us-central1.run.app
- Frontend loads with HTTP 200
- Backend URL baked in: https://loan-backend-prod-fjz2snvxjq-uc.a.run.app

**Ready for Phase 20 (Chrome Verification):**
- Visual verification can be performed in browser
- Navigation links to /documents, /borrowers, /architecture available

**Blockers for full functionality (carried from Plan 19-01):**
- Database not configured for loan application (API endpoints return 500)
- Gemini API key is placeholder (extraction will fail)

---
*Phase: 19-production-deployment-verification*
*Completed: 2026-01-25*
