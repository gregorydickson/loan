# CloudBuild Deployment Guide

Complete guide for deploying the loan extraction application using CloudBuild and gcloud CLI.

## Overview

CloudBuild replaces Terraform for application deployments in v2.0+:

| Component | Management Approach | When |
|-----------|-------------------|------|
| VPC, Cloud SQL, Cloud Tasks | gcloud CLI scripts | One-time setup |
| Backend, Frontend, GPU services | CloudBuild + GitHub triggers | On every push to main |
| Rollback | gcloud CLI | Manual when needed |

**Benefits:**
- Native GitHub integration with automatic build status on commits
- No Terraform state to manage for frequent deployments
- Built-in revision-based rollback via Cloud Run
- Simpler CI/CD configuration

For a complete resource mapping, see [terraform-to-gcloud-inventory.md](./terraform-to-gcloud-inventory.md).

## Prerequisites

Before deploying, ensure you have:

1. **GCP Project** with billing enabled
2. **gcloud CLI** installed and authenticated
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```
3. **GitHub repository** connected to Cloud Build via Developer Connect
   - Console: Cloud Build > Repositories > Connect Repository
   - Select GitHub provider and authorize
   - Note the connection name (e.g., "github-connection")

## One-Time Setup

Run these scripts once to create infrastructure and configure CloudBuild.

### 1. Enable APIs and Create Artifact Registry

```bash
./infrastructure/scripts/setup-gcp.sh
```

This enables required GCP APIs and creates the Artifact Registry repository.

### 2. Create CloudBuild Service Account

```bash
./infrastructure/cloudbuild/setup-service-account.sh YOUR_PROJECT_ID
```

Creates `cloudbuild-deployer` service account with required IAM roles:
- `roles/run.developer` - Deploy Cloud Run services
- `roles/iam.serviceAccountUser` - Act as Cloud Run service account
- `roles/artifactregistry.writer` - Push container images
- `roles/secretmanager.secretAccessor` - Access secrets
- `roles/logging.logWriter` - Write build logs

### 3. Provision Infrastructure

```bash
./infrastructure/scripts/provision-infra.sh YOUR_PROJECT_ID us-central1
```

Creates:
- VPC network and Cloud Run subnet
- VPC peering for Cloud SQL private connectivity
- Cloud SQL PostgreSQL 16 instance
- loan_extraction database
- document-processing Cloud Tasks queue

**Note:** Cloud SQL instance creation takes 5-10 minutes.

### 4. Create Secrets in Secret Manager

Create secrets for sensitive configuration:

```bash
# Database URL (get private IP from Cloud SQL Console)
gcloud secrets create database-url --replication-policy=automatic
echo -n "postgresql://loan_user:PASSWORD@PRIVATE_IP:5432/loan_extraction" | \
    gcloud secrets versions add database-url --data-file=-

# Gemini API key
gcloud secrets create gemini-api-key --replication-policy=automatic
echo -n "your-gemini-api-key" | \
    gcloud secrets versions add gemini-api-key --data-file=-
```

Grant the Cloud Run service account access:

```bash
gcloud secrets add-iam-policy-binding database-url \
    --member="serviceAccount:loan-cloud-run@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding gemini-api-key \
    --member="serviceAccount:loan-cloud-run@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### 5. Connect GitHub Repository

This is a one-time manual step in the Console:

1. Go to [Cloud Build > Repositories](https://console.cloud.google.com/cloud-build/repositories)
2. Click "Connect Repository"
3. Select "GitHub" as the provider
4. Authorize Cloud Build to access your GitHub account
5. Select the repository (e.g., "loan")
6. Note the **connection name** (e.g., "github-connection")

### 6. Create GitHub Triggers

```bash
./infrastructure/scripts/setup-github-triggers.sh YOUR_PROJECT_ID CONNECTION_NAME
```

Creates three triggers:
- **backend-deploy**: Triggered by changes to `backend/**`
- **frontend-deploy**: Triggered by changes to `frontend/**`
- **gpu-deploy**: Triggered by changes to `infrastructure/lightonocr-gpu/**`

Each trigger uses `--included-files` to scope builds to relevant changes only.

## Automated Deployments

After setup, deployments happen automatically:

1. **Push to main** - Any push to the main branch triggers relevant builds
2. **File scoping** - Only services with changed files rebuild
3. **GitHub status** - Build status appears on commits and PRs
4. **Build logs** - Available in Cloud Build Console

### Monitoring Builds

View build history and logs:
- Console: [Cloud Build > History](https://console.cloud.google.com/cloud-build/builds)
- CLI: `gcloud builds list --limit=10`

### Build Status on GitHub

After triggers are configured, GitHub shows build status:
- Pending: Build queued or running
- Success: Build and deploy completed
- Failure: Build error (check logs)

## Manual Deployments

For emergency fixes or testing, deploy directly:

### Backend

```bash
gcloud builds submit \
    --config=infrastructure/cloudbuild/backend-cloudbuild.yaml \
    --substitutions=SHORT_SHA=$(git rev-parse --short HEAD) \
    .
```

### Frontend

```bash
gcloud builds submit \
    --config=infrastructure/cloudbuild/frontend-cloudbuild.yaml \
    --substitutions=SHORT_SHA=$(git rev-parse --short HEAD),_BACKEND_URL=https://loan-backend-prod-xxx.run.app \
    .
```

### GPU Service

```bash
gcloud builds submit \
    --config=infrastructure/cloudbuild/gpu-cloudbuild.yaml \
    --substitutions=SHORT_SHA=$(git rev-parse --short HEAD) \
    .
```

**Note:** GPU builds take 15-30 minutes due to model download.

## Multi-Service Orchestration

Per the proof-of-concept approach, services deploy independently:

| Aspect | Approach |
|--------|----------|
| Deployment order | No dependency ordering - services deploy independently |
| Parallel builds | Acceptable if multiple changes merge simultaneously |
| Unavailability handling | Services gracefully handle dependent services being unavailable |
| Coordination | None - each trigger operates independently |

**Why no orchestration:**
- Simpler configuration and debugging
- Cloud Run handles traffic gracefully during deploys
- Services have retry logic for transient failures
- Can add orchestration later if needed for production

## Rollback Procedures

Cloud Run maintains recent revisions for quick rollback.

### List Revisions

```bash
# Interactive mode - shows revisions and prompts for selection
./infrastructure/scripts/rollback.sh loan-backend-prod

# Output example:
# Recent revisions for loan-backend-prod:
#
# NAME                                ACTIVE  CREATED
# loan-backend-prod-00042-abc         *       2026-01-25T10:15:30Z
# loan-backend-prod-00041-def                 2026-01-24T14:22:10Z
# loan-backend-prod-00040-ghi                 2026-01-23T09:45:00Z
```

### Rollback to Specific Revision

```bash
# Direct rollback without prompt
./infrastructure/scripts/rollback.sh loan-backend-prod loan-backend-prod-00041-def
```

### Verify Rollback

```bash
gcloud run services describe loan-backend-prod --region=us-central1 --format="value(status.traffic)"
```

### Restore After Fix

After fixing the issue and pushing a new deployment:

```bash
gcloud run services update-traffic loan-backend-prod --region=us-central1 --to-revisions=LATEST=100
```

### Rollback All Services

If multiple services need rollback, run the script for each:

```bash
./infrastructure/scripts/rollback.sh loan-backend-prod
./infrastructure/scripts/rollback.sh loan-frontend-prod
./infrastructure/scripts/rollback.sh lightonocr-gpu
```

## Troubleshooting

### Permission Denied Errors

**Symptom:** Build fails with "PERMISSION_DENIED"

**Solution:** Verify service account roles:
```bash
gcloud projects get-iam-policy YOUR_PROJECT_ID \
    --flatten="bindings[].members" \
    --filter="bindings.members:cloudbuild-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com"
```

Re-run `setup-service-account.sh` if roles are missing.

### VPC Connectivity Errors

**Symptom:** Backend cannot connect to Cloud SQL

**Solution:** Verify VPC configuration:
```bash
# Check subnet exists
gcloud compute networks subnets describe cloud-run-subnet --region=us-central1

# Check VPC peering
gcloud services vpc-peerings list --network=YOUR_PROJECT_ID-vpc
```

### Secret Access Errors

**Symptom:** Service fails with "Permission denied on secret"

**Solution:** Grant secret access to Cloud Run service account:
```bash
gcloud secrets add-iam-policy-binding SECRET_NAME \
    --member="serviceAccount:loan-cloud-run@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### Build Timeout

**Symptom:** GPU build times out

**Solution:** GPU builds have 80-minute timeout. If still timing out:
1. Check if model download is failing (network issues)
2. Consider using larger machine type in cloudbuild.yaml

### Trigger Not Firing

**Symptom:** Push to main doesn't trigger build

**Solution:**
1. Verify GitHub connection is active in Console
2. Check file changes match `--included-files` pattern
3. Verify branch pattern matches (default: `^main$`)

```bash
# List triggers and their configuration
gcloud builds triggers list --region=us-central1
```

### Checking Build Logs

For detailed error information:

```bash
# List recent builds
gcloud builds list --limit=5

# Get specific build logs
gcloud builds log BUILD_ID
```

Or view in Console: Cloud Build > History > Click on build

## Configuration Files

| File | Purpose |
|------|---------|
| `infrastructure/cloudbuild/backend-cloudbuild.yaml` | Backend build and deploy config |
| `infrastructure/cloudbuild/frontend-cloudbuild.yaml` | Frontend build and deploy config |
| `infrastructure/cloudbuild/gpu-cloudbuild.yaml` | GPU service build and deploy config |
| `infrastructure/scripts/setup-github-triggers.sh` | GitHub trigger creation |
| `infrastructure/scripts/provision-infra.sh` | One-time infrastructure setup |
| `infrastructure/scripts/rollback.sh` | Cloud Run rollback helper |
| `docs/terraform-to-gcloud-inventory.md` | Terraform to gcloud resource mapping |

## Quick Reference

### Common Commands

```bash
# Check trigger status
gcloud builds triggers list --region=us-central1

# List recent builds
gcloud builds list --limit=10

# Check service status
gcloud run services describe loan-backend-prod --region=us-central1

# View service logs
gcloud run services logs loan-backend-prod --region=us-central1 --limit=50

# Manual rollback
./infrastructure/scripts/rollback.sh SERVICE_NAME

# Restore to latest
gcloud run services update-traffic SERVICE_NAME --region=us-central1 --to-revisions=LATEST=100
```

### Service URLs

After deployment, services are available at:
- Backend: `https://loan-backend-prod-xxx.run.app`
- Frontend: `https://loan-frontend-prod-xxx.run.app`
- GPU: `https://lightonocr-gpu-xxx.run.app` (authenticated access only)

Get actual URLs:
```bash
gcloud run services list --region=us-central1 --format="table(metadata.name,status.url)"
```
