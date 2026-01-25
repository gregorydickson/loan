# Terraform Migration Guide

This guide documents the migration from Terraform-managed deployments to CloudBuild for the v2.0 release.

## Background

v1.0 used Terraform for all infrastructure including Cloud Run service deployments. v2.0 separates concerns:
- **Infrastructure** (Cloud SQL, VPC, IAM): One-time provisioning via gcloud CLI scripts
- **Services** (Cloud Run): Continuous deployment via CloudBuild

**Why the change:**
- CloudBuild provides simpler CI/CD with native GitHub integration
- No Terraform state management for repeating deployments
- Cloud Run revisions provide built-in rollback capability
- gcloud CLI is sufficient for one-time infrastructure setup

## Migration Date

Completed: 2026-01-25 (Phase 10)

## Archived Terraform State

Terraform state has been archived (not deleted) for recovery capability:

```
archive/terraform/
├── .terraform/           # Provider plugins
├── .terraform.lock.hcl   # Dependency lock
├── main.tf               # Infrastructure definitions
├── variables.tf          # Variable declarations
├── outputs.tf            # Output definitions
├── terraform.tfvars      # Variable values (secrets redacted)
└── terraform.tfstate     # Last known state (READ-ONLY)
```

**Important:** Do not modify archived state. It serves as documentation and disaster recovery reference.

## State Location

Terraform state remains in GCS bucket (not copied locally):
- Bucket: `gs://{project-id}-terraform-state/`
- File: `terraform.tfstate`

The remote state was intentionally NOT copied to local archive to:
1. Avoid duplicating secrets stored in state
2. Maintain single source of truth
3. Preserve state locking semantics

## Resource Inventory

See `docs/terraform-to-gcloud-inventory.md` for mapping of Terraform resources to gcloud equivalents.

**Summary:**
| Category | Management | Location |
|----------|------------|----------|
| VPC, Subnet | One-time gcloud | `infrastructure/scripts/provision-infra.sh` |
| Cloud SQL | One-time gcloud | `infrastructure/scripts/provision-infra.sh` |
| Cloud Tasks | One-time gcloud | `infrastructure/scripts/provision-infra.sh` |
| IAM, Service Accounts | One-time gcloud | `infrastructure/cloudbuild/setup-service-account.sh` |
| Cloud Run Services | CloudBuild | `infrastructure/cloudbuild/*.yaml` |

## Recovery Procedures

### If CloudBuild Fails Catastrophically

1. Review archived Terraform definitions in `archive/terraform/`
2. Import existing GCP resources into new Terraform state:
   ```bash
   terraform import google_cloud_run_v2_service.backend projects/{project}/locations/{region}/services/loan-backend-prod
   ```
3. Resume Terraform management for affected resources

### If Infrastructure Needs Modification

1. Use `infrastructure/scripts/provision-infra.sh` for additive changes
2. For destructive changes, use gcloud CLI directly with caution:
   ```bash
   # Example: Delete and recreate Cloud Tasks queue
   gcloud tasks queues delete document-processing --location=us-central1
   gcloud tasks queues create document-processing --location=us-central1
   ```
3. Document changes in this guide under "Post-Migration Changes" section

### If State Recovery is Needed

1. Access GCS bucket:
   ```bash
   gsutil ls gs://{project-id}-terraform-state/
   ```
2. Download state for inspection (READ-ONLY):
   ```bash
   gsutil cp gs://{project-id}-terraform-state/terraform.tfstate ./recovered-state.json
   ```
3. Use `terraform import` to rebuild local state if needed

## CloudBuild Deployment

Services are now deployed via CloudBuild:
- `backend-cloudbuild.yaml` - Backend API service with VPC egress and Secret Manager
- `frontend-cloudbuild.yaml` - Frontend Next.js service with NEXT_PUBLIC_API_URL
- `gpu-cloudbuild.yaml` - LightOnOCR GPU service with L4 configuration

See `docs/cloudbuild-deployment-guide.md` for deployment procedures.

### Deployment Flow

```
Push to main -> GitHub Trigger -> CloudBuild -> Cloud Run Revision
```

### Manual Deployment

If GitHub triggers fail, deploy manually:
```bash
# Backend
gcloud builds submit --config=infrastructure/cloudbuild/backend-cloudbuild.yaml

# Frontend
gcloud builds submit --config=infrastructure/cloudbuild/frontend-cloudbuild.yaml

# GPU Service
gcloud builds submit --config=infrastructure/cloudbuild/gpu-cloudbuild.yaml
```

## Rollback Procedures

See `infrastructure/scripts/rollback.sh` for service version rollback.

```bash
# List available revisions
./infrastructure/scripts/rollback.sh loan-backend-prod

# Rollback to specific revision
./infrastructure/scripts/rollback.sh loan-backend-prod loan-backend-prod-00042-abc
```

Cloud Run maintains revision history automatically, providing instant rollback capability without rebuilding images.

## Post-Migration Changes

Document any infrastructure modifications made after migration:

| Date | Change | Reason | Files Modified |
|------|--------|--------|----------------|
| 2026-01-25 | Initial migration | v2.0 release | All CloudBuild configs |

## Related Documentation

- `docs/terraform-to-gcloud-inventory.md` - Resource mapping
- `docs/cloudbuild-deployment-guide.md` - Deployment procedures
- `archive/terraform/MIGRATION.md` - Original migration notes
