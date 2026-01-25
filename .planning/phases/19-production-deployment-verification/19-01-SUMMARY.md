---
phase: 19-production-deployment-verification
plan: 01
subsystem: infra
tags: [gcp, cloud-run, cloudBuild, deployment, docker]

# Dependency graph
requires:
  - phase: 16-cloudbuild-deployment
    provides: CloudBuild configurations for all services
provides:
  - Backend Cloud Run service deployed and accessible
  - Backend URL for frontend deployment (Plan 19-02)
  - Artifact Registry repository (loan-repo)
  - VPC and subnet for Cloud Run egress
  - Service account (loan-cloud-run) with required IAM roles
affects: [19-02, 19-03, 20-chrome-verification, 21-final-validation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Cloud Run with VPC egress for Cloud SQL connectivity
    - Secret Manager for database and API credentials

key-files:
  created: []
  modified:
    - backend/Dockerfile

key-decisions:
  - "Used memorygraph-prod GCP project for loan deployment (user decision)"
  - "Created loan-specific Artifact Registry repository to avoid conflicts"
  - "Created dedicated VPC (memorygraph-prod-vpc) with cloud-run-subnet for Cloud Run"
  - "Used placeholder gemini-api-key secret (needs real key for extraction)"

patterns-established:
  - "CloudBuild deploys to loan-backend-prod with --allow-unauthenticated"
  - "VPC egress private-ranges-only for Cloud SQL connectivity"
  - "Cloud SQL Auth Proxy via --add-cloudsql-instances flag"

# Metrics
duration: 75min
completed: 2026-01-25
---

# Phase 19 Plan 01: Backend Deployment Summary

**Backend deployed to Cloud Run at https://loan-backend-prod-793446666872.us-central1.run.app with /health returning 200**

## Performance

- **Duration:** 75 min
- **Started:** 2026-01-25T21:04:43Z
- **Completed:** 2026-01-25T23:45:00Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- Backend service `loan-backend-prod` deployed and accessible
- Health endpoint `/health` returns `{"status":"healthy"}` with HTTP 200
- Created required GCP infrastructure: VPC, subnet, service account, secrets
- Fixed Dockerfile bugs discovered during deployment (missing examples directory, wrong module path)

## Task Commits

Each task was committed atomically:

1. **Task 1: Check existing Cloud Run deployments** - Verification only, no commit required
2. **Task 2: Deploy backend to Cloud Run** - Multiple bug-fix commits during deployment:
   - `c6adffb9` - fix(19-01): add missing examples directory and PYTHONPATH to Dockerfile
   - `f75947c6` - chore(19-01): add --no-cache flag to backend build (debugging)
   - `4b5af626` - fix(19-01): correct uvicorn module path to src.main:app
   - `46e1c897` - chore(19-01): remove --no-cache flag from backend build
3. **Task 3: Verify backend health** - Verification only, no commit required

## Files Created/Modified
- `backend/Dockerfile` - Added examples/ COPY, PYTHONPATH=/app, fixed CMD module path

## Decisions Made
- Used memorygraph-prod project per user decision (accepted potential naming conflicts)
- Created loan-repo Artifact Registry repository (isolated from other project images)
- Created memorygraph-prod-vpc with cloud-run-subnet (10.0.0.0/24) for VPC egress
- Created loan-cloud-run service account with minimal required roles
- Created placeholder gemini-api-key secret (extraction will fail until real key provided)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created missing Artifact Registry repository**
- **Found during:** Task 2 (first deployment attempt)
- **Issue:** loan-repo repository didn't exist in memorygraph-prod project
- **Fix:** `gcloud artifacts repositories create loan-repo`
- **Files modified:** None (GCP resource creation)
- **Verification:** `gcloud artifacts repositories list` shows loan-repo

**2. [Rule 3 - Blocking] Created VPC network and subnet**
- **Found during:** Task 2 (CloudBuild deploy step failed)
- **Issue:** VPC memorygraph-prod-vpc and cloud-run-subnet didn't exist
- **Fix:** `gcloud compute networks create` and `gcloud compute networks subnets create`
- **Files modified:** None (GCP resource creation)
- **Verification:** `gcloud compute networks list` shows VPC

**3. [Rule 3 - Blocking] Created service account with IAM roles**
- **Found during:** Task 2 (CloudBuild deploy step)
- **Issue:** loan-cloud-run@memorygraph-prod.iam.gserviceaccount.com didn't exist
- **Fix:** Created SA and granted cloudsql.client, secretmanager.secretAccessor, cloudtasks.enqueuer, logging.logWriter, run.invoker roles
- **Files modified:** None (GCP resource creation)
- **Verification:** `gcloud iam service-accounts list` shows SA

**4. [Rule 3 - Blocking] Created gemini-api-key secret with placeholder**
- **Found during:** Task 2 (deployment failed on secret reference)
- **Issue:** gemini-api-key secret didn't exist (database-url existed)
- **Fix:** Created secret with placeholder value "PLACEHOLDER"
- **Files modified:** None (GCP resource creation)
- **Verification:** `gcloud secrets list` shows gemini-api-key

**5. [Rule 1 - Bug] Fixed missing examples directory in Dockerfile**
- **Found during:** Task 2 (container failed to start - ModuleNotFoundError)
- **Issue:** Dockerfile didn't COPY examples/ directory needed for LangExtract
- **Fix:** Added `COPY examples/ ./examples/` and `ENV PYTHONPATH=/app`
- **Files modified:** backend/Dockerfile
- **Committed in:** c6adffb9

**6. [Rule 1 - Bug] Fixed incorrect uvicorn module path**
- **Found during:** Task 2 (container failed to start after previous fix)
- **Issue:** CMD used `src.api.main:app` but app is at `src.main:app`
- **Fix:** Changed CMD to `["python", "-m", "uvicorn", "src.main:app", ...]`
- **Files modified:** backend/Dockerfile
- **Committed in:** 4b5af626

**7. [Rule 3 - Blocking] Added Cloud SQL connection to Cloud Run service**
- **Found during:** Task 3 (database queries failed with FileNotFoundError)
- **Issue:** Cloud SQL Auth Proxy socket not available in container
- **Fix:** `gcloud run services update --add-cloudsql-instances=memorygraph-prod:us-central1:memorygraph-db`
- **Files modified:** None (Cloud Run config)
- **Verification:** Health endpoint still returns 200

---

**Total deviations:** 7 auto-fixed (4 blocking infrastructure, 2 bugs, 1 config)
**Impact on plan:** Infrastructure gaps expected when deploying to different project. All fixes necessary for successful deployment.

## Issues Encountered

1. **Multiple CloudBuild failures**: Build succeeded but deployment failed repeatedly due to missing infrastructure. Each failure required investigating Cloud Run logs and fixing the underlying issue.

2. **Docker cache issue**: Changed Dockerfile wasn't being used because CloudBuild cached layers. Added --no-cache temporarily to force rebuild (later removed).

3. **Database connectivity**: API endpoints return 500 because the database-url secret points to memorygraph_auth database which doesn't have the loan application schema. This is expected behavior - health endpoint works, full functionality requires database setup.

## Authentication Gates

During execution, the following authentication/credential requirements were identified:

1. **gemini-api-key secret**: Created with placeholder value. Actual Gemini API key needed for extraction functionality.

2. **Database schema**: The existing database-url points to memorygraph_auth database. Full loan application functionality requires either:
   - Creating loan_extraction database with proper schema
   - Or updating database-url to point to a properly configured database

## Next Phase Readiness

**Ready for Plan 19-02 (Frontend Deployment):**
- Backend URL available: https://loan-backend-prod-793446666872.us-central1.run.app
- Backend health endpoint responding with 200

**Blockers for full functionality:**
- Database not configured for loan application (API endpoints return 500)
- Gemini API key is placeholder (extraction will fail)

**Recommended follow-up:**
1. User to provide real Gemini API key: `gcloud secrets versions add gemini-api-key --data-file=-`
2. Create loan_extraction database or configure database-url for existing compatible database
3. Run database migrations: `alembic upgrade head`

---
*Phase: 19-production-deployment-verification*
*Completed: 2026-01-25*
