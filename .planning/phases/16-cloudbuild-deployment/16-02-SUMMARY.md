---
phase: 16-cloudbuild-deployment
plan: 02
name: Infrastructure Scripts & Rollback
subsystem: infrastructure
tags: [gcloud, terraform, rollback, cloud-sql, vpc, cloud-tasks]

dependency-graph:
  requires: [16-RESEARCH]
  provides: [provision-infra.sh, rollback.sh, terraform-inventory]
  affects: [16-03]

tech-stack:
  added: []
  patterns: [idempotent-scripts, revision-rollback]

key-files:
  created:
    - docs/terraform-to-gcloud-inventory.md
    - infrastructure/scripts/provision-infra.sh
    - infrastructure/scripts/rollback.sh
  modified: []

decisions:
  - id: DEC-16-02-01
    decision: "All gcloud commands use existence checks for idempotency"
    rationale: "Scripts can be re-run safely without errors"

metrics:
  duration: 3 min
  completed: 2026-01-25
---

# Phase 16 Plan 02: Infrastructure Scripts & Rollback Summary

**One-liner:** gcloud CLI alternatives to Terraform for one-time infra setup plus Cloud Run rollback helper

## What Was Built

### 1. Terraform to gcloud Inventory (docs/terraform-to-gcloud-inventory.md)

Comprehensive documentation mapping Terraform resources to gcloud CLI equivalents:

| Category | Resources Mapped |
|----------|------------------|
| VPC/Networking | network, subnet, global address, vpc-peering |
| Database | sql instance, database, user |
| Async Processing | Cloud Tasks queue |
| IAM | service account, iam bindings |
| Application | Cloud Run services (via CloudBuild) |

Key structure:
- Overview of migration from Terraform to CloudBuild + gcloud
- One-time resources table with full gcloud commands
- Repeating resources managed by CloudBuild
- Complete inventory table with script locations
- Migration checklist

### 2. Infrastructure Provisioning Script (infrastructure/scripts/provision-infra.sh)

One-time gcloud CLI script for foundational infrastructure:

```bash
./provision-infra.sh PROJECT_ID [REGION]
```

**Resources created:**
1. Enable 8 required GCP APIs
2. VPC network (custom subnet mode)
3. Cloud Run subnet (10.0.0.0/24)
4. Private IP range for VPC peering (10.1.0.0/16)
5. VPC peering for Cloud SQL connectivity
6. Cloud SQL PostgreSQL 16 instance (private IP only)
7. loan_extraction database
8. document-processing Cloud Tasks queue

**Idempotency pattern:**
```bash
if gcloud ... describe ... &>/dev/null; then
    echo "Resource already exists"
else
    gcloud ... create ...
fi
```

### 3. Rollback Helper Script (infrastructure/scripts/rollback.sh)

Cloud Run revision rollback utility:

```bash
# List revisions and prompt
./rollback.sh loan-backend-prod

# Direct rollback to revision
./rollback.sh loan-backend-prod loan-backend-prod-00042-abc

# Override region
REGION=us-west1 ./rollback.sh loan-frontend-prod
```

**Features:**
- List recent 5 revisions with creation time
- Interactive revision selection
- Confirmation prompt before rollback
- Traffic verification after rollback
- Restore command output for after fix

## Requirements Satisfied

| Requirement | Description | How Satisfied |
|-------------|-------------|---------------|
| CBLD-05 | Terraform resource inventory | terraform-to-gcloud-inventory.md with complete mapping |
| CBLD-06 | One-time gcloud scripts | provision-infra.sh for VPC, Cloud SQL, Cloud Tasks |
| CBLD-11 | Rollback procedures | rollback.sh with revision listing and traffic shift |

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| DEC-16-02-01 | All gcloud commands use existence checks | Scripts can be re-run safely without errors |

## Deviations from Plan

None - plan executed exactly as written.

## Files Changed

| File | Change | Lines |
|------|--------|-------|
| docs/terraform-to-gcloud-inventory.md | Created | +130 |
| infrastructure/scripts/provision-infra.sh | Created | +179 |
| infrastructure/scripts/rollback.sh | Created | +92 |

**Total:** 3 files, +401 lines

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 5aec2e8a | docs | Terraform to gcloud inventory documentation |
| 640b48ea | feat | Infrastructure provisioning script |
| 9b025090 | feat | Cloud Run rollback helper script |

## Verification

All verification checks passed:
- terraform-to-gcloud-inventory.md contains 28 google_* resource references
- provision-infra.sh passes bash -n syntax check
- rollback.sh passes bash -n syntax check
- Both scripts use idempotent patterns (7 existence checks in provision-infra.sh)

## Next Phase Readiness

**Ready for:** 16-03 (GitHub Triggers & Build Verification)

**Prerequisites satisfied:**
- Terraform resource mapping documented
- One-time infrastructure script available
- Rollback procedure documented and scripted
