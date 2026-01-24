# CloudBuild Setup Guide

## Service Account

CloudBuild uses a dedicated service account with least-privilege permissions.

**Service Account:** cloudbuild-deployer@PROJECT_ID.iam.gserviceaccount.com

### IAM Roles

| Role | Purpose |
|------|---------|
| roles/run.developer | Deploy and manage Cloud Run services |
| roles/iam.serviceAccountUser | Act as the Cloud Run runtime service account |
| roles/artifactregistry.writer | Push container images to Artifact Registry |
| roles/secretmanager.secretAccessor | Access secrets during builds (DB passwords, API keys) |
| roles/logging.logWriter | Write build logs to Cloud Logging |

### Setup

Run the setup script to create the service account:

```bash
./infrastructure/cloudbuild/setup-service-account.sh PROJECT_ID
```

The script is idempotent - safe to run multiple times.

## Directory Structure

```
infrastructure/
  cloudbuild/
    setup-service-account.sh  # Service account creation (this guide)
    backend.cloudbuild.yaml   # Backend deployment (Phase 16)
    frontend.cloudbuild.yaml  # Frontend deployment (Phase 16)
    gpu.cloudbuild.yaml       # GPU service deployment (Phase 16)
```

## Security Notes

- Uses dedicated service account, not legacy CloudBuild default
- Least-privilege: only roles needed for Cloud Run deployment
- No Editor or Owner roles granted
- Secrets accessed via Secret Manager, not build variables

## Related

- Phase 16: CloudBuild deployment configurations
- Phase 13: GPU service deployment (requires this SA)
