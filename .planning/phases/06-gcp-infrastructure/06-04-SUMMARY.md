---
phase: 06-gcp-infrastructure
plan: 04
subsystem: infra
tags: [terraform, gcp, cloud-run, docker, serverless, vpc-egress]

# Dependency graph
requires:
  - phase: 06-02
    provides: "Dockerfiles for backend and frontend services"
  - phase: 06-03
    provides: "Cloud SQL, Secret Manager, Cloud Storage, Cloud Tasks"
provides:
  - "Backend Cloud Run service with VPC egress for database access"
  - "Frontend Cloud Run service with backend API URL injection"
  - "Public access IAM bindings for both services"
  - "Terraform outputs for service URLs and infrastructure endpoints"
  - "Example tfvars for deployment configuration"
affects: [07-production-hardening]

# Tech tracking
tech-stack:
  added: [cloud-run-v2, direct-vpc-egress]
  patterns: [secret-injection, scale-to-zero, health-probes, container-deployment]

key-files:
  created:
    - infrastructure/terraform/cloud_run.tf
    - infrastructure/terraform/outputs.tf
    - infrastructure/terraform/terraform.tfvars.example
  modified:
    - .gitignore

key-decisions:
  - "Cloud Run v2 API for direct VPC egress (no VPC connector cost)"
  - "Backend: 1Gi memory for Docling processing, scale 0-10"
  - "Frontend: 512Mi memory, scale 0-5"
  - "PRIVATE_RANGES_ONLY egress for Cloud SQL private IP access"
  - "Secret injection via secret_key_ref for DATABASE_URL and GEMINI_API_KEY"
  - "allUsers invoker role for public access (no auth on endpoints)"
  - "Startup probe on /health endpoint with 10s initial delay"

patterns-established:
  - "google_cloud_run_v2_service with vpc_access.network_interfaces for direct egress"
  - "Environment variables via Secret Manager value_source blocks"
  - "Frontend references backend.uri for API URL configuration"
  - "cpu_idle=true for scale-to-zero cost optimization"

# Metrics
duration: 2 min
completed: 2026-01-24
---

# Phase 6 Plan 4: Cloud Run Deployment Summary

**Cloud Run v2 services for backend (VPC egress, secrets, health probes) and frontend (API URL injection) with Terraform outputs and deployment configuration**

## Performance

- **Duration:** 2 min
- **Started:** 2026-01-24T16:35:22Z
- **Completed:** 2026-01-24T16:36:20Z
- **Tasks:** 3 (2 implementation + 1 verification checkpoint)
- **Files created:** 3
- **Files modified:** 1

## Accomplishments

- Backend Cloud Run service with VPC egress connecting to Cloud SQL via private IP
- Secret Manager injection for DATABASE_URL and GEMINI_API_KEY environment variables
- Frontend Cloud Run service with automatic backend URL configuration
- Public access IAM bindings (allUsers invoker) for both services
- 7 Terraform outputs for service URLs, database info, bucket, and queue
- Example tfvars file documenting required variables and sensitive value handling

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Cloud Run service configurations** - `48056a79` (feat)
2. **Task 2: Create outputs and example tfvars** - `69266474` (feat)
3. **Task 3: Checkpoint verification** - User approved configuration

## Files Created/Modified

- `infrastructure/terraform/cloud_run.tf` - Backend and frontend Cloud Run v2 services with VPC egress, secrets, probes, and IAM
- `infrastructure/terraform/outputs.tf` - 7 outputs: backend_url, frontend_url, database info, bucket, queue
- `infrastructure/terraform/terraform.tfvars.example` - Required variables with sensitive value guidance
- `.gitignore` - Added terraform.tfvars exclusion for secrets

## Decisions Made

1. **Cloud Run v2 API** - Uses google_cloud_run_v2_service for direct VPC egress without VPC connector cost
2. **1Gi backend memory** - Docling document processing requires more memory than typical APIs
3. **512Mi frontend memory** - Next.js standalone output is lightweight
4. **PRIVATE_RANGES_ONLY egress** - Only routes to Cloud SQL private IP, not all internet traffic
5. **cpu_idle=true** - Scale-to-zero for cost optimization during idle periods
6. **allUsers invoker** - Public API access; authentication handled at application layer
7. **Startup probe on /health** - 10s delay, 5s timeout, 3 failure threshold for reliable startup

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - Terraform infrastructure created via `terraform apply` with appropriate variables.

## Complete Infrastructure Summary

Phase 6 GCP Infrastructure is now complete with all 10 Terraform files:

| File | Purpose |
|------|---------|
| main.tf | Provider configuration, state backend |
| variables.tf | Input variables with defaults |
| vpc.tf | VPC, subnet, private services access |
| iam.tf | Service account, role bindings |
| cloud_sql.tf | PostgreSQL 16, database, user |
| secrets.tf | Secret Manager, IAM bindings |
| cloud_storage.tf | Document bucket, lifecycle policies |
| cloud_tasks.tf | Processing queue, rate limiting |
| cloud_run.tf | Backend and frontend services |
| outputs.tf | Service URLs, connection info |

## Next Phase Readiness

- Full Terraform configuration ready for `terraform apply`
- Both Dockerfiles exist for container builds
- Deployment scripts (setup-gcp.sh, deploy.sh) available
- Ready for Phase 7: Production Hardening (if planned) or deployment

---
*Phase: 06-gcp-infrastructure*
*Completed: 2026-01-24*
