# Phase 16: CloudBuild Deployment - Research

**Researched:** 2026-01-25
**Domain:** Cloud Build CI/CD, Cloud Run Deployment, GitHub Triggers, Secret Manager, Rollback Procedures
**Confidence:** HIGH

## Summary

Phase 16 migrates from Terraform to CloudBuild + gcloud CLI for all service deployments (backend, frontend, GPU). The research confirms this is a well-documented, standard pattern with Google providing extensive documentation and examples for CloudBuild-to-Cloud-Run deployments.

CloudBuild configuration uses a `cloudbuild.yaml` file with build steps for Docker image creation, Artifact Registry push, and `gcloud run deploy` invocation. GitHub triggers can automatically invoke builds on push to main branch. Secret Manager integrates via `availableSecrets` and `secretEnv` fields in the build configuration. Cloud Run provides built-in revision-based rollback via `gcloud run services update-traffic`.

Per the CONTEXT.md decisions, this is a proof-of-concept deployment with simple patterns: single GitHub trigger on push to main, independent service deployments (no orchestration), manual rollback procedures, and no multi-environment complexity.

**Primary recommendation:** Create three separate cloudbuild.yaml files (backend, frontend, GPU service), each handling build and deploy in a single configuration. Use GitHub triggers via `gcloud builds triggers create github` or Developer Connect. Use `gcloud run services update-traffic SERVICE --to-revisions REVISION=100` for rollback.

## Standard Stack

The established tools for CloudBuild deployment:

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| Cloud Build | latest | CI/CD automation | Native GCP, GitHub integration, managed infrastructure |
| gcloud CLI | latest | Deployment commands | Official GCP tooling, all Cloud Run features |
| cloudbuild.yaml | v1 schema | Build configuration | Declarative, version-controlled, trigger-compatible |
| Secret Manager | latest | Secrets at build/runtime | Native GCP, CloudBuild integration |

### Supporting
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| gcr.io/cloud-builders/docker | latest | Docker image building | Standard CloudBuild step |
| gcr.io/google.com/cloudsdktool/cloud-sdk | latest | gcloud commands in builds | Deploy step, infrastructure commands |
| Artifact Registry | latest | Container image storage | Required for Cloud Run deployments |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| CloudBuild | GitHub Actions | CloudBuild has native GCP integration, no cross-platform secrets |
| cloudbuild.yaml per service | Single multi-service config | Per-service allows independent deployments (per CONTEXT.md) |
| GitHub trigger | Cloud Scheduler | Push-based is simpler for POC |

**Setup Commands:**
```bash
# Enable required APIs
gcloud services enable cloudbuild.googleapis.com run.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com

# Configure Docker authentication
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet

# Create Artifact Registry repository (if not exists)
gcloud artifacts repositories create loan-repo \
    --repository-format=docker \
    --location=${REGION} \
    --description="Loan extraction Docker images"
```

## Architecture Patterns

### Recommended Project Structure
```
infrastructure/
  cloudbuild/
    backend-cloudbuild.yaml      # Backend service build and deploy
    frontend-cloudbuild.yaml     # Frontend service build and deploy
    gpu-cloudbuild.yaml          # GPU service build and deploy
    setup-service-account.sh     # CloudBuild SA permissions (exists)
  scripts/
    setup-gcp.sh                 # One-time GCP setup (exists)
    provision-infra.sh           # One-time gcloud CLI for VPC, Cloud SQL
    rollback.sh                  # Rollback helper script

backend/
  Dockerfile                     # Backend container (exists)

frontend/
  Dockerfile                     # Frontend container (exists)

infrastructure/lightonocr-gpu/
  Dockerfile                     # GPU service container (exists)
```

### Pattern 1: Backend CloudBuild Configuration
**What:** Build and deploy backend service to Cloud Run
**When to use:** Every push to main affecting backend
**Example:**
```yaml
# Source: https://docs.cloud.google.com/build/docs/deploying-builds/deploy-cloud-run
steps:
  # Build the backend image
  - name: 'gcr.io/cloud-builders/docker'
    id: 'build-backend'
    args:
      - 'build'
      - '-t'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/loan-repo/backend:${SHORT_SHA}'
      - '-t'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/loan-repo/backend:latest'
      - './backend'

  # Push to Artifact Registry
  - name: 'gcr.io/cloud-builders/docker'
    id: 'push-backend'
    args:
      - 'push'
      - '--all-tags'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/loan-repo/backend'

  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    id: 'deploy-backend'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'loan-backend-prod'
      - '--image'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/loan-repo/backend:${SHORT_SHA}'
      - '--region'
      - '${_REGION}'
      - '--service-account'
      - 'loan-cloud-run@${PROJECT_ID}.iam.gserviceaccount.com'
      - '--network'
      - '${PROJECT_ID}-vpc'
      - '--subnet'
      - 'cloud-run-subnet'
      - '--vpc-egress'
      - 'private-ranges-only'
      - '--allow-unauthenticated'
      - '--cpu'
      - '1'
      - '--memory'
      - '1Gi'
      - '--min-instances'
      - '0'
      - '--max-instances'
      - '10'
      - '--set-secrets'
      - 'DATABASE_URL=database-url:latest,GEMINI_API_KEY=gemini-api-key:latest'

substitutions:
  _REGION: us-central1

images:
  - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/loan-repo/backend:${SHORT_SHA}'
  - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/loan-repo/backend:latest'

options:
  logging: CLOUD_LOGGING_ONLY
  machineType: 'E2_HIGHCPU_8'
```

### Pattern 2: Frontend CloudBuild Configuration
**What:** Build and deploy frontend service to Cloud Run
**When to use:** Every push to main affecting frontend
**Example:**
```yaml
steps:
  # Build the frontend image
  - name: 'gcr.io/cloud-builders/docker'
    id: 'build-frontend'
    args:
      - 'build'
      - '-t'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/loan-repo/frontend:${SHORT_SHA}'
      - '-t'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/loan-repo/frontend:latest'
      - './frontend'

  # Push to Artifact Registry
  - name: 'gcr.io/cloud-builders/docker'
    id: 'push-frontend'
    args:
      - 'push'
      - '--all-tags'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/loan-repo/frontend'

  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    id: 'deploy-frontend'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'loan-frontend-prod'
      - '--image'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/loan-repo/frontend:${SHORT_SHA}'
      - '--region'
      - '${_REGION}'
      - '--allow-unauthenticated'
      - '--cpu'
      - '1'
      - '--memory'
      - '512Mi'
      - '--min-instances'
      - '0'
      - '--max-instances'
      - '5'
      - '--set-env-vars'
      - 'NEXT_PUBLIC_API_URL=${_BACKEND_URL}'

substitutions:
  _REGION: us-central1
  _BACKEND_URL: ''  # Set via trigger or at runtime

images:
  - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/loan-repo/frontend:${SHORT_SHA}'
  - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/loan-repo/frontend:latest'

options:
  logging: CLOUD_LOGGING_ONLY
```

### Pattern 3: GPU Service CloudBuild Configuration
**What:** Build and deploy GPU service to Cloud Run with L4 GPU
**When to use:** Every push to main affecting GPU service
**Example:**
```yaml
steps:
  # Build the GPU service image (long build due to model download)
  - name: 'gcr.io/cloud-builders/docker'
    id: 'build-gpu'
    args:
      - 'build'
      - '-t'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/loan-repo/lightonocr-gpu:${SHORT_SHA}'
      - '-t'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/loan-repo/lightonocr-gpu:latest'
      - './infrastructure/lightonocr-gpu'
    timeout: '3600s'  # Model download can take time

  # Push to Artifact Registry
  - name: 'gcr.io/cloud-builders/docker'
    id: 'push-gpu'
    args:
      - 'push'
      - '--all-tags'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/loan-repo/lightonocr-gpu'

  # Deploy to Cloud Run with GPU
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    id: 'deploy-gpu'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'lightonocr-gpu'
      - '--image'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/loan-repo/lightonocr-gpu:${SHORT_SHA}'
      - '--region'
      - '${_REGION}'
      - '--service-account'
      - 'lightonocr-gpu@${PROJECT_ID}.iam.gserviceaccount.com'
      - '--no-allow-unauthenticated'
      - '--cpu'
      - '8'
      - '--memory'
      - '32Gi'
      - '--gpu'
      - '1'
      - '--gpu-type'
      - 'nvidia-l4'
      - '--min-instances'
      - '0'
      - '--max-instances'
      - '3'
      - '--no-cpu-throttling'
      - '--no-gpu-zonal-redundancy'
      - '--port'
      - '8000'
      - '--startup-probe'
      - 'tcpSocket.port=8000,initialDelaySeconds=240,failureThreshold=1,timeoutSeconds=240,periodSeconds=240'

substitutions:
  _REGION: us-central1

images:
  - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/loan-repo/lightonocr-gpu:${SHORT_SHA}'
  - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/loan-repo/lightonocr-gpu:latest'

timeout: '4800s'  # 80 minutes for full GPU build

options:
  logging: CLOUD_LOGGING_ONLY
  machineType: 'E2_HIGHCPU_32'  # Larger machine for faster model download
```

### Pattern 4: GitHub Trigger Creation
**What:** Create GitHub trigger for automatic builds on push to main
**When to use:** One-time setup per service
**Example:**
```bash
# Source: https://docs.cloud.google.com/build/docs/automating-builds/create-manage-triggers
# Using Developer Connect (recommended for new projects)

# First connect GitHub repository (one-time via Console)
# Then create triggers:

gcloud builds triggers create github \
    --name="backend-deploy" \
    --region=${REGION} \
    --repository="projects/${PROJECT_ID}/locations/${REGION}/connections/${CONNECTION_NAME}/repositories/loan" \
    --branch-pattern="^main$" \
    --build-config="infrastructure/cloudbuild/backend-cloudbuild.yaml" \
    --service-account="projects/${PROJECT_ID}/serviceAccounts/cloudbuild-deployer@${PROJECT_ID}.iam.gserviceaccount.com" \
    --included-files="backend/**,infrastructure/cloudbuild/backend-cloudbuild.yaml"

gcloud builds triggers create github \
    --name="frontend-deploy" \
    --region=${REGION} \
    --repository="projects/${PROJECT_ID}/locations/${REGION}/connections/${CONNECTION_NAME}/repositories/loan" \
    --branch-pattern="^main$" \
    --build-config="infrastructure/cloudbuild/frontend-cloudbuild.yaml" \
    --service-account="projects/${PROJECT_ID}/serviceAccounts/cloudbuild-deployer@${PROJECT_ID}.iam.gserviceaccount.com" \
    --included-files="frontend/**,infrastructure/cloudbuild/frontend-cloudbuild.yaml"

gcloud builds triggers create github \
    --name="gpu-deploy" \
    --region=${REGION} \
    --repository="projects/${PROJECT_ID}/locations/${REGION}/connections/${CONNECTION_NAME}/repositories/loan" \
    --branch-pattern="^main$" \
    --build-config="infrastructure/cloudbuild/gpu-cloudbuild.yaml" \
    --service-account="projects/${PROJECT_ID}/serviceAccounts/cloudbuild-deployer@${PROJECT_ID}.iam.gserviceaccount.com" \
    --included-files="infrastructure/lightonocr-gpu/**,infrastructure/cloudbuild/gpu-cloudbuild.yaml"
```

### Pattern 5: Secret Manager Integration
**What:** Access secrets at build time or runtime via gcloud
**When to use:** Database credentials, API keys
**Example:**
```yaml
# Runtime secrets via --set-secrets flag (recommended for Cloud Run)
# Secrets are mounted as environment variables at container start
args:
  - '--set-secrets'
  - 'DATABASE_URL=database-url:latest,GEMINI_API_KEY=gemini-api-key:latest'

# Build-time secrets via availableSecrets (if needed during build)
steps:
  - name: 'gcr.io/cloud-builders/docker'
    entrypoint: 'bash'
    args:
      - '-c'
      - 'docker build --build-arg API_KEY=$$API_KEY -t myimage .'
    secretEnv: ['API_KEY']

availableSecrets:
  secretManager:
    - versionName: projects/${PROJECT_ID}/secrets/api-key/versions/latest
      env: 'API_KEY'
```

### Pattern 6: Rollback Procedure
**What:** Rollback to previous Cloud Run revision
**When to use:** When a deployment causes issues
**Example:**
```bash
# Source: https://docs.cloud.google.com/run/docs/rollouts-rollbacks-traffic-migration

# List revisions to find rollback target
gcloud run revisions list --service=loan-backend-prod --region=${REGION} --limit=5

# Rollback by directing 100% traffic to previous revision
gcloud run services update-traffic loan-backend-prod \
    --region=${REGION} \
    --to-revisions=loan-backend-prod-00042-abc=100

# Or use LATEST to restore after fix
gcloud run services update-traffic loan-backend-prod \
    --region=${REGION} \
    --to-revisions=LATEST=100
```

### Anti-Patterns to Avoid
- **Monorepo single trigger:** Use separate triggers with `--included-files` for independent service deploys
- **Build-time secrets for runtime data:** Use `--set-secrets` for runtime secrets, not `availableSecrets`
- **Complex orchestration layer:** Per CONTEXT.md, services deploy independently
- **Canary/blue-green for POC:** Simple revision-based rollback is sufficient

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Image tagging | Manual version schemes | `${SHORT_SHA}` substitution | Built-in, git-traceable |
| Secrets in builds | Environment files, plain text | Secret Manager + `--set-secrets` | Secure, auditable, rotatable |
| VPC connectivity | Manual IP config | Direct VPC egress + `--network/--subnet` | Native Cloud Run feature |
| Build caching | Custom cache layers | CloudBuild kaniko or standard caching | Built-in optimization |
| Rollback automation | Custom scripts | `gcloud run services update-traffic` | Native Cloud Run feature |
| Deployment notifications | Custom webhooks | CloudBuild GitHub integration | Automatic status on commits |

**Key insight:** CloudBuild + gcloud CLI provides a complete CI/CD solution. The POC should use native GCP features rather than custom tooling.

## Common Pitfalls

### Pitfall 1: Missing CloudBuild Service Account Permissions
**What goes wrong:** Build fails with permission denied errors
**Why it happens:** CloudBuild SA needs Cloud Run Admin, Artifact Registry Writer, Secret Manager accessor
**How to avoid:** Run `setup-service-account.sh` or grant roles via gcloud:
```bash
ROLES=("roles/run.developer" "roles/iam.serviceAccountUser" "roles/artifactregistry.writer" "roles/secretmanager.secretAccessor")
for role in "${ROLES[@]}"; do
    gcloud projects add-iam-policy-binding ${PROJECT_ID} \
        --member="serviceAccount:cloudbuild-deployer@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="$role"
done
```
**Warning signs:** "PERMISSION_DENIED" in build logs

### Pitfall 2: Frontend NEXT_PUBLIC_API_URL Not Set at Build Time
**What goes wrong:** Frontend cannot connect to backend API
**Why it happens:** Next.js bakes NEXT_PUBLIC_* vars at build time, not runtime
**How to avoid:** Set `_BACKEND_URL` substitution in trigger or use dynamic runtime config
**Warning signs:** Frontend shows undefined API URL, network errors

### Pitfall 3: VPC Egress Not Configured for Cloud SQL
**What goes wrong:** Backend cannot connect to Cloud SQL via private IP
**Why it happens:** Cloud Run needs VPC access to reach private Cloud SQL
**How to avoid:** Include `--network`, `--subnet`, and `--vpc-egress` flags in deploy command
**Warning signs:** Connection timeout errors to database

### Pitfall 4: GPU Service Build Timeout
**What goes wrong:** GPU image build times out
**Why it happens:** Model download (~2GB) during build takes significant time
**How to avoid:** Set `timeout: '3600s'` on build step, use larger machine type
**Warning signs:** Build fails with "deadline exceeded"

### Pitfall 5: Trigger Fires for All Changes
**What goes wrong:** All services rebuild on every push
**Why it happens:** Missing `--included-files` filter on triggers
**How to avoid:** Use `--included-files="backend/**"` etc. to scope triggers
**Warning signs:** Unnecessary builds, wasted time and cost

### Pitfall 6: Secrets Not Accessible to Cloud Run Service
**What goes wrong:** Service fails to start with secret access errors
**Why it happens:** Service account needs secretmanager.secretAccessor role on specific secrets
**How to avoid:** Grant IAM binding on each secret:
```bash
gcloud secrets add-iam-policy-binding database-url \
    --member="serviceAccount:loan-cloud-run@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```
**Warning signs:** "Permission 'secretmanager.versions.access' denied" in logs

## Code Examples

Verified patterns from official sources:

### One-Time Infrastructure Provisioning Script
```bash
#!/bin/bash
# provision-infra.sh - One-time gcloud CLI infrastructure setup
# Run once to create VPC, Cloud SQL, and other foundational resources
# Source: Terraform configs mapped to gcloud equivalents

set -euo pipefail

PROJECT_ID="${1:?Usage: provision-infra.sh PROJECT_ID}"
REGION="${REGION:-us-central1}"

echo "Provisioning infrastructure for: $PROJECT_ID"

# Enable required APIs (idempotent)
gcloud services enable \
    compute.googleapis.com \
    run.googleapis.com \
    sqladmin.googleapis.com \
    secretmanager.googleapis.com \
    cloudtasks.googleapis.com \
    servicenetworking.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    --project="$PROJECT_ID"

# Create VPC network
gcloud compute networks create "${PROJECT_ID}-vpc" \
    --project="$PROJECT_ID" \
    --subnet-mode=custom \
    2>/dev/null || echo "VPC already exists"

# Create Cloud Run subnet
gcloud compute networks subnets create cloud-run-subnet \
    --project="$PROJECT_ID" \
    --network="${PROJECT_ID}-vpc" \
    --region="$REGION" \
    --range=10.0.0.0/24 \
    --enable-private-ip-google-access \
    2>/dev/null || echo "Subnet already exists"

# Allocate private IP range for VPC peering (Cloud SQL)
gcloud compute addresses create private-ip-address \
    --project="$PROJECT_ID" \
    --global \
    --purpose=VPC_PEERING \
    --addresses=10.1.0.0 \
    --prefix-length=16 \
    --network="${PROJECT_ID}-vpc" \
    2>/dev/null || echo "IP range already allocated"

# Create private VPC connection for Cloud SQL
gcloud services vpc-peerings connect \
    --service=servicenetworking.googleapis.com \
    --ranges=private-ip-address \
    --network="${PROJECT_ID}-vpc" \
    --project="$PROJECT_ID" \
    2>/dev/null || echo "VPC peering already exists"

# Create Cloud SQL instance with private IP
gcloud sql instances create loan-db-prod \
    --project="$PROJECT_ID" \
    --database-version=POSTGRES_16 \
    --tier=db-f1-micro \
    --region="$REGION" \
    --network="${PROJECT_ID}-vpc" \
    --no-assign-ip \
    --storage-type=SSD \
    --storage-size=10GB \
    --availability-type=ZONAL \
    --no-deletion-protection \
    2>/dev/null || echo "Cloud SQL instance already exists"

# Create database and user (secrets managed separately)
gcloud sql databases create loan_extraction \
    --instance=loan-db-prod \
    --project="$PROJECT_ID" \
    2>/dev/null || echo "Database already exists"

# Create Cloud Tasks queue
gcloud tasks queues create document-processing \
    --location="$REGION" \
    --project="$PROJECT_ID" \
    --max-dispatches-per-second=10 \
    --max-concurrent-dispatches=5 \
    --max-attempts=5 \
    --min-backoff=10s \
    --max-backoff=3600s \
    2>/dev/null || echo "Queue already exists"

echo "Infrastructure provisioning complete!"
```

### Rollback Helper Script
```bash
#!/bin/bash
# rollback.sh - Helper for Cloud Run rollback
# Usage: ./rollback.sh SERVICE [REVISION]

set -euo pipefail

SERVICE="${1:?Usage: rollback.sh SERVICE [REVISION]}"
REGION="${REGION:-us-central1}"
REVISION="${2:-}"

if [[ -z "$REVISION" ]]; then
    echo "Available revisions for $SERVICE:"
    gcloud run revisions list --service="$SERVICE" --region="$REGION" --limit=5 --format="table(name,active,created)"
    echo ""
    read -p "Enter revision to rollback to: " REVISION
fi

echo "Rolling back $SERVICE to revision: $REVISION"
gcloud run services update-traffic "$SERVICE" \
    --region="$REGION" \
    --to-revisions="${REVISION}=100"

echo "Rollback complete. Verifying..."
gcloud run services describe "$SERVICE" --region="$REGION" --format="value(status.traffic)"
```

### CloudBuild Substitution Variables Reference
```yaml
# Built-in substitutions (available in all builds)
# $PROJECT_ID - GCP project ID
# $BUILD_ID - Unique build ID
# $PROJECT_NUMBER - Project number
# $LOCATION - Build region

# Trigger-only substitutions (available for triggered builds)
# $COMMIT_SHA - Full commit SHA
# $SHORT_SHA - First 7 characters of commit SHA
# $BRANCH_NAME - Branch that triggered build
# $TAG_NAME - Tag that triggered build (if tag trigger)
# $REPO_NAME - Repository name

# Custom substitutions (defined per build config)
substitutions:
  _REGION: us-central1
  _ENVIRONMENT: prod
  _BACKEND_URL: https://loan-backend-prod-xxx.run.app
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Terraform for Cloud Run | CloudBuild + gcloud deploy | This migration | Simpler, no state management |
| VPC Connector for Cloud SQL | Direct VPC egress | Cloud Run 2024 | No connector cost, simpler config |
| Build-time secrets | Runtime `--set-secrets` | Cloud Run 2023 | Secrets stay in Secret Manager |
| Manual image tagging | `${SHORT_SHA}` substitution | CloudBuild default | Git-traceable deployments |
| gcr.io Container Registry | Artifact Registry | Deprecated 2024 | Required for new projects |

**Deprecated/outdated:**
- gcr.io: Use Artifact Registry (`${REGION}-docker.pkg.dev`)
- VPC Access Connector: Use Direct VPC egress for simpler setup
- Terraform for Cloud Run deploys: CloudBuild is simpler for this use case

## Open Questions

Things that couldn't be fully resolved:

1. **GitHub Connection Name for Triggers**
   - What we know: Triggers require `--repository` with full path including connection name
   - What's unclear: Connection name must be set up in Console first
   - Recommendation: Document that GitHub connection is a one-time Console setup before triggers work

2. **NEXT_PUBLIC_API_URL for Frontend**
   - What we know: Next.js requires this at build time for NEXT_PUBLIC_* vars
   - What's unclear: Best pattern for getting backend URL into frontend build
   - Recommendation: Either use fixed URL or two-stage build (deploy backend, update frontend trigger)

3. **GPU Build Time**
   - What we know: Model download adds significant time to GPU service build
   - What's unclear: Exact build time on E2_HIGHCPU_32
   - Recommendation: Set generous timeout (3600s), measure in practice

## Terraform Resource Inventory

Mapping Terraform-managed resources to gcloud CLI equivalents:

| Terraform Resource | gcloud Equivalent | One-Time/Repeating |
|-------------------|-------------------|-------------------|
| `google_compute_network` | `gcloud compute networks create` | One-time |
| `google_compute_subnetwork` | `gcloud compute networks subnets create` | One-time |
| `google_compute_global_address` | `gcloud compute addresses create --global` | One-time |
| `google_service_networking_connection` | `gcloud services vpc-peerings connect` | One-time |
| `google_sql_database_instance` | `gcloud sql instances create` | One-time |
| `google_sql_database` | `gcloud sql databases create` | One-time |
| `google_sql_user` | `gcloud sql users create` | One-time |
| `google_cloud_tasks_queue` | `gcloud tasks queues create` | One-time |
| `google_storage_bucket` | `gcloud storage buckets create` | One-time |
| `google_secret_manager_secret` | `gcloud secrets create` | One-time |
| `google_cloud_run_v2_service` | `gcloud run deploy` (CloudBuild) | Repeating |
| `google_service_account` | `gcloud iam service-accounts create` | One-time |
| `google_project_iam_member` | `gcloud projects add-iam-policy-binding` | One-time |

## Sources

### Primary (HIGH confidence)
- [Deploying to Cloud Run using Cloud Build](https://docs.cloud.google.com/build/docs/deploying-builds/deploy-cloud-run) - Official deployment pattern
- [Use secrets from Secret Manager](https://docs.cloud.google.com/build/docs/securing-builds/use-secrets) - Secret integration
- [Create and manage build triggers](https://docs.cloud.google.com/build/docs/automating-builds/create-manage-triggers) - GitHub trigger setup
- [Rollouts, rollbacks, and traffic migration](https://docs.cloud.google.com/run/docs/rollouts-rollbacks-traffic-migration) - Rollback procedures
- [GPU support for services](https://docs.cloud.google.com/run/docs/configuring/services/gpu) - GPU deployment flags
- [Substituting variable values](https://docs.cloud.google.com/build/docs/configuring-builds/substitute-variable-values) - Built-in substitutions
- [Configure build step order](https://docs.cloud.google.com/build/docs/configuring-builds/configure-build-step-order) - waitFor and parallel steps

### Secondary (MEDIUM confidence)
- [Connecting to Private CloudSQL from Cloud Run](https://codelabs.developers.google.com/connecting-to-private-cloudsql-from-cloud-run) - VPC connectivity patterns
- [Direct VPC egress](https://docs.cloud.google.com/run/docs/configuring/vpc-direct-vpc) - Network configuration
- [Google Cloud Build Samples](https://github.com/GoogleCloudPlatform/cloud-build-samples) - Example configurations

### Tertiary (LOW confidence)
- Build time estimates (varies by machine type, network, model size)
- GitHub connection setup (Console-based, varies by org settings)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official Google Cloud documentation with specific commands
- Architecture patterns: HIGH - Documented patterns with complete YAML examples
- Pitfalls: HIGH - Based on documented requirements and common issues from forums
- Infrastructure provisioning: MEDIUM - Derived from Terraform configs, not all tested

**Research date:** 2026-01-25
**Valid until:** 2026-02-25 (30 days - stable infrastructure, API versions may update)

## Phase 16 Requirements Mapping

| Requirement | Research Finding | Confidence |
|-------------|------------------|------------|
| CBLD-01: Backend cloudbuild.yaml | Pattern 1 with docker build, push, gcloud run deploy | HIGH |
| CBLD-02: Frontend cloudbuild.yaml | Pattern 2 with NEXT_PUBLIC_API_URL handling | HIGH |
| CBLD-03: GPU service cloudbuild.yaml | Pattern 3 with GPU flags, extended timeout | HIGH |
| CBLD-05: Terraform inventory | Resource inventory table with gcloud equivalents | HIGH |
| CBLD-06: One-time gcloud scripts | provision-infra.sh example for VPC, Cloud SQL, etc. | MEDIUM |
| CBLD-07: GitHub trigger | Pattern 4 with gcloud builds triggers create | HIGH |
| CBLD-09: Secret Manager integration | Pattern 5 with --set-secrets and availableSecrets | HIGH |
| CBLD-10: Multi-service orchestration | Independent triggers per service (per CONTEXT.md) | HIGH |
| CBLD-11: Rollback procedures | Pattern 6 and rollback.sh helper script | HIGH |
