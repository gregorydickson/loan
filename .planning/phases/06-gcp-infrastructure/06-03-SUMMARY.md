---
phase: 06-gcp-infrastructure
plan: 03
subsystem: infra
tags: [terraform, gcp, cloud-sql, cloud-storage, cloud-tasks, secret-manager]

# Dependency graph
requires:
  - phase: 06-01
    provides: "VPC with private services access, IAM service account"
provides:
  - "Cloud SQL PostgreSQL 16 with private IP"
  - "Secret Manager secrets for database URL and Gemini API key"
  - "Cloud Storage bucket with lifecycle policies"
  - "Cloud Tasks queue with rate limiting"
affects: [06-04-cloud-run]

# Tech tracking
tech-stack:
  added: [cloud-sql-postgres-16, secret-manager, cloud-storage, cloud-tasks]
  patterns: [private-ip-database, secret-manager-integration, lifecycle-policies, async-queue]

key-files:
  created:
    - infrastructure/terraform/cloud_sql.tf
    - infrastructure/terraform/secrets.tf
    - infrastructure/terraform/cloud_storage.tf
    - infrastructure/terraform/cloud_tasks.tf
  modified: []

key-decisions:
  - "PostgreSQL 16 on db-f1-micro tier (smallest, sufficient for demo)"
  - "Private IP only via VPC peering (ipv4_enabled=false)"
  - "7-day backup retention with point-in-time recovery"
  - "Secret Manager stores connection strings (not in Terraform state)"
  - "Per-secret IAM bindings for Cloud Run service account"
  - "Storage lifecycle: NEARLINE at 90d, COLDLINE at 365d, 5 version limit"
  - "Queue rate limits: 10/s dispatches, 5 concurrent"
  - "Queue retry: 5 attempts, exponential backoff, 1 hour max duration"

patterns-established:
  - "google_secret_manager_secret_iam_member for per-secret access control"
  - "google_storage_bucket_iam_member for bucket-level permissions"
  - "depends_on for Cloud SQL to ensure VPC peering is ready"

# Metrics
duration: 3 min
completed: 2026-01-24
---

# Phase 6 Plan 3: Managed Services Summary

**Cloud SQL PostgreSQL, Secret Manager, Cloud Storage, and Cloud Tasks Terraform configuration with private networking and least-privilege access**

## Performance

- **Duration:** 3 min
- **Started:** 2026-01-24T16:25:10Z
- **Completed:** 2026-01-24T16:28:25Z
- **Tasks:** 2
- **Files created:** 4

## Accomplishments

- Cloud SQL PostgreSQL 16 instance with private IP via VPC peering
- Database and application user for loan_extraction database
- Secret Manager secrets for database URL (asyncpg connection string) and Gemini API key
- IAM bindings for Cloud Run service account to access secrets
- Cloud Storage bucket with lifecycle policies for cost optimization
- Cloud Tasks queue with rate limiting and exponential backoff retry

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Cloud SQL and Secret Manager configuration** - `0e6da40c` (feat)
2. **Task 2: Create Cloud Storage and Cloud Tasks configuration** - `894b4ed4` (feat)

## Files Created/Modified

- `infrastructure/terraform/cloud_sql.tf` - PostgreSQL 16 instance, database, user, private IP config
- `infrastructure/terraform/secrets.tf` - Database URL and Gemini API key secrets with IAM bindings
- `infrastructure/terraform/cloud_storage.tf` - Document bucket with versioning and lifecycle rules
- `infrastructure/terraform/cloud_tasks.tf` - Document processing queue with rate limiting

## Decisions Made

1. **db-f1-micro tier for Cloud SQL** - Smallest tier sufficient for demo; upgrade to db-custom-2-4096 for production
2. **deletion_protection=false** - Allows terraform destroy for demo; set true for production
3. **ZONAL availability** - Cost-effective for demo; use REGIONAL for HA in production
4. **asyncpg connection string in Secret Manager** - Full connection URL stored securely, not in Terraform state
5. **Per-secret IAM bindings** - More granular than project-level secretAccessor role
6. **Uniform bucket-level access** - Simpler permissions model, no per-object ACLs
7. **5 version limit for old objects** - Prevents unbounded version accumulation

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - infrastructure is created via `terraform apply`.

## Next Phase Readiness

- Cloud SQL ready for Cloud Run backend connection via private IP
- Secret Manager ready for Cloud Run environment variable injection
- Storage bucket ready for document uploads
- Cloud Tasks queue ready for async document processing
- All IAM bindings in place for Cloud Run service account

---
*Phase: 06-gcp-infrastructure*
*Completed: 2026-01-24*
