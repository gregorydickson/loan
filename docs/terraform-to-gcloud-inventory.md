# Terraform to gcloud CLI Inventory

This document maps Terraform-managed resources to their gcloud CLI equivalents for the loan extraction application's migration from Terraform to CloudBuild + gcloud CLI.

## Overview

The infrastructure management approach has evolved:

| Era | Management Tool | Scope |
|-----|-----------------|-------|
| v1.0 | Terraform | All infrastructure including Cloud Run services |
| v2.0+ | CloudBuild + gcloud CLI | Application deployments via CloudBuild; one-time infra via gcloud scripts |

**Why the change:**
- CloudBuild provides simpler CI/CD with native GitHub integration
- No Terraform state management for repeating deployments
- Cloud Run revisions provide built-in rollback capability
- gcloud CLI is sufficient for one-time infrastructure setup

## Resource Categories

### One-Time Resources

These resources are created once and rarely modified. Use `provision-infra.sh` for initial setup.

| Terraform Resource | gcloud Equivalent | Command |
|-------------------|-------------------|---------|
| `google_compute_network` | `gcloud compute networks create` | `gcloud compute networks create ${PROJECT_ID}-vpc --subnet-mode=custom` |
| `google_compute_subnetwork` | `gcloud compute networks subnets create` | `gcloud compute networks subnets create cloud-run-subnet --network=${PROJECT_ID}-vpc --region=${REGION} --range=10.0.0.0/24` |
| `google_compute_global_address` | `gcloud compute addresses create --global` | `gcloud compute addresses create private-ip-address --global --purpose=VPC_PEERING --addresses=10.1.0.0 --prefix-length=16` |
| `google_service_networking_connection` | `gcloud services vpc-peerings connect` | `gcloud services vpc-peerings connect --service=servicenetworking.googleapis.com --ranges=private-ip-address --network=${PROJECT_ID}-vpc` |
| `google_sql_database_instance` | `gcloud sql instances create` | `gcloud sql instances create loan-db-prod --database-version=POSTGRES_16 --tier=db-f1-micro --region=${REGION} --network=${PROJECT_ID}-vpc --no-assign-ip` |
| `google_sql_database` | `gcloud sql databases create` | `gcloud sql databases create loan_extraction --instance=loan-db-prod` |
| `google_sql_user` | `gcloud sql users create` | `gcloud sql users create loan_user --instance=loan-db-prod --password=${DB_PASSWORD}` |
| `google_cloud_tasks_queue` | `gcloud tasks queues create` | `gcloud tasks queues create document-processing --location=${REGION}` |
| `google_storage_bucket` | `gcloud storage buckets create` | `gcloud storage buckets create gs://${PROJECT_ID}-documents --location=${REGION}` |
| `google_secret_manager_secret` | `gcloud secrets create` | `gcloud secrets create database-url --replication-policy=automatic` |
| `google_service_account` | `gcloud iam service-accounts create` | `gcloud iam service-accounts create loan-cloud-run --display-name="Loan Cloud Run Service Account"` |
| `google_project_iam_member` | `gcloud projects add-iam-policy-binding` | `gcloud projects add-iam-policy-binding ${PROJECT_ID} --member=serviceAccount:${SA_EMAIL} --role=${ROLE}` |

### Repeating Resources (Managed by CloudBuild)

These resources are deployed on every push to main branch via CloudBuild.

| Terraform Resource | CloudBuild Equivalent | Configuration |
|-------------------|----------------------|---------------|
| `google_cloud_run_v2_service` (backend) | `gcloud run deploy` | `infrastructure/cloudbuild/backend-cloudbuild.yaml` |
| `google_cloud_run_v2_service` (frontend) | `gcloud run deploy` | `infrastructure/cloudbuild/frontend-cloudbuild.yaml` |
| `google_cloud_run_v2_service` (GPU) | `gcloud run deploy` | `infrastructure/cloudbuild/gpu-cloudbuild.yaml` |

## Complete Resource Inventory

| Terraform Resource | gcloud Equivalent | One-Time/Repeating | Script Location |
|-------------------|-------------------|-------------------|-----------------|
| `google_compute_network` | `gcloud compute networks create` | One-time | `infrastructure/scripts/provision-infra.sh` |
| `google_compute_subnetwork` | `gcloud compute networks subnets create` | One-time | `infrastructure/scripts/provision-infra.sh` |
| `google_compute_global_address` | `gcloud compute addresses create --global` | One-time | `infrastructure/scripts/provision-infra.sh` |
| `google_service_networking_connection` | `gcloud services vpc-peerings connect` | One-time | `infrastructure/scripts/provision-infra.sh` |
| `google_sql_database_instance` | `gcloud sql instances create` | One-time | `infrastructure/scripts/provision-infra.sh` |
| `google_sql_database` | `gcloud sql databases create` | One-time | `infrastructure/scripts/provision-infra.sh` |
| `google_sql_user` | `gcloud sql users create` | One-time | Manual (contains password) |
| `google_cloud_tasks_queue` | `gcloud tasks queues create` | One-time | `infrastructure/scripts/provision-infra.sh` |
| `google_storage_bucket` | `gcloud storage buckets create` | One-time | `infrastructure/scripts/setup-gcp.sh` |
| `google_secret_manager_secret` | `gcloud secrets create` | One-time | Manual (per secret) |
| `google_service_account` | `gcloud iam service-accounts create` | One-time | `infrastructure/cloudbuild/setup-service-account.sh` |
| `google_project_iam_member` | `gcloud projects add-iam-policy-binding` | One-time | `infrastructure/cloudbuild/setup-service-account.sh` |
| `google_cloud_run_v2_service` | `gcloud run deploy` | Repeating | CloudBuild YAML files |

## Script References

### One-Time Infrastructure Setup

**Script:** `infrastructure/scripts/provision-infra.sh`

Creates VPC, subnet, VPC peering, Cloud SQL instance, database, and Cloud Tasks queue.

```bash
# Usage
./infrastructure/scripts/provision-infra.sh PROJECT_ID [REGION]

# Example
./infrastructure/scripts/provision-infra.sh my-gcp-project us-central1
```

### Service Account Setup

**Script:** `infrastructure/cloudbuild/setup-service-account.sh`

Creates CloudBuild service account with required IAM roles.

```bash
# Usage
./infrastructure/cloudbuild/setup-service-account.sh [PROJECT_ID]
```

### Rollback Procedure

**Script:** `infrastructure/scripts/rollback.sh`

Helper for rolling back Cloud Run services to previous revisions.

```bash
# Usage
./infrastructure/scripts/rollback.sh SERVICE [REVISION]

# Example - list revisions and prompt
./infrastructure/scripts/rollback.sh loan-backend-prod

# Example - rollback to specific revision
./infrastructure/scripts/rollback.sh loan-backend-prod loan-backend-prod-00042-abc
```

## Migration Checklist

When migrating from Terraform to gcloud CLI:

1. [ ] Run `provision-infra.sh` to create one-time infrastructure (if not already via Terraform)
2. [ ] Run `setup-service-account.sh` to create CloudBuild service account
3. [ ] Set up GitHub connection in Cloud Console (one-time manual step)
4. [ ] Create CloudBuild triggers for each service
5. [ ] Verify secrets exist in Secret Manager
6. [ ] Push to main to trigger first CloudBuild deployment
7. [ ] Archive Terraform files (done in v2.0, see `infrastructure/terraform-archive/`)

## Notes

- Terraform state remains in GCS bucket for recovery capability
- VPC peering can take 1-2 minutes to complete
- Cloud SQL instance creation can take 5-10 minutes
- All gcloud commands are idempotent (safe to re-run)
