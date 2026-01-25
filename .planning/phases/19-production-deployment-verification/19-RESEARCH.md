# Phase 19: Production Deployment Verification - Research

**Researched:** 2026-01-25
**Domain:** GCP Cloud Run Deployment Verification, gcloud CLI, Health Checks, Secret Manager
**Confidence:** HIGH

## Summary

Phase 19 focuses on verifying and deploying all services (backend, frontend, GPU OCR) to GCP production and ensuring they are accessible and healthy. This is primarily an operational verification phase rather than code development - the infrastructure (CloudBuild configs, Dockerfiles, provisioning scripts) was already created in Phase 16.

The research confirms that the project already has:
- CloudBuild configurations for all three services (`backend-cloudbuild.yaml`, `frontend-cloudbuild.yaml`, `gpu-cloudbuild.yaml`)
- Dockerfiles for all services with proper health check endpoints
- Infrastructure provisioning script (`provision-infra.sh`) for VPC, Cloud SQL, Cloud Tasks
- Rollback scripts and deployment helpers

The deployment verification follows a standard pattern: (1) check existing deployments with `gcloud run services list`, (2) deploy missing services via CloudBuild or manual `gcloud builds submit`, (3) verify health endpoints respond with 200 status, (4) verify Cloud SQL connectivity, (5) verify GPU configuration.

**Primary recommendation:** Use `gcloud run services list` and `gcloud run services describe` commands to check deployment status, then trigger CloudBuild for any missing services. Verify health endpoints via curl with appropriate authentication.

## Standard Stack

The established tools for deployment verification:

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| gcloud CLI | latest | All GCP operations | Official GCP tooling, comprehensive service management |
| curl | system | Health check verification | Universal, simple HTTP testing |
| Cloud Build | latest | Automated deployments | Native GCP, existing configs in project |

### Supporting
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| jq | system | JSON parsing | Parsing gcloud JSON output |
| Cloud Logging | latest | Debug failed deployments | When services fail health checks |

### Existing Project Assets
| Asset | Location | Purpose |
|-------|----------|---------|
| Backend CloudBuild | `infrastructure/cloudbuild/backend-cloudbuild.yaml` | Build and deploy backend |
| Frontend CloudBuild | `infrastructure/cloudbuild/frontend-cloudbuild.yaml` | Build and deploy frontend |
| GPU CloudBuild | `infrastructure/cloudbuild/gpu-cloudbuild.yaml` | Build and deploy GPU service |
| Provision Script | `infrastructure/scripts/provision-infra.sh` | One-time infrastructure setup |
| Rollback Script | `infrastructure/scripts/rollback.sh` | Rollback helper |

**Verification Commands:**
```bash
# List all Cloud Run services in project
gcloud run services list --region=us-central1 --format="table(SERVICE,REGION,URL,LAST_DEPLOYED_BY,LAST_DEPLOYED_AT)"

# Get specific service URL
gcloud run services describe loan-backend-prod --region=us-central1 --format="value(status.url)"

# Check service health
BACKEND_URL=$(gcloud run services describe loan-backend-prod --region=us-central1 --format="value(status.url)")
curl -s "${BACKEND_URL}/health"
```

## Architecture Patterns

### Deployment Verification Workflow
```
1. Check Existing Deployments
   └── gcloud run services list --region=us-central1

2. For Each Missing Service
   ├── Trigger CloudBuild
   │   └── gcloud builds submit --config=infrastructure/cloudbuild/SERVICE-cloudbuild.yaml .
   └── Wait for deployment
       └── gcloud builds list --limit=1 --ongoing

3. Verify Health Endpoints
   ├── Backend: curl $BACKEND_URL/health
   ├── Frontend: curl $FRONTEND_URL (200 response)
   └── GPU: curl -H "Authorization: Bearer $TOKEN" $GPU_URL/health

4. Verify Connectivity
   ├── Backend -> Cloud SQL: Check logs for DB connection
   └── Frontend -> Backend: Load frontend, verify API calls

5. Verify GPU Configuration
   └── gcloud run services describe lightonocr-gpu --format="yaml" | grep gpu
```

### Pattern 1: Check Existing Deployments
**What:** List all Cloud Run services to verify deployment state
**When to use:** First step in verification
**Example:**
```bash
# Source: https://docs.cloud.google.com/sdk/gcloud/reference/run/services/list

# Check if services exist
gcloud run services list --region=us-central1 --format="table(SERVICE,URL)"

# Expected output for fully deployed system:
# SERVICE             URL
# loan-backend-prod   https://loan-backend-prod-xxx-uc.a.run.app
# loan-frontend-prod  https://loan-frontend-prod-xxx-uc.a.run.app
# lightonocr-gpu      https://lightonocr-gpu-xxx-uc.a.run.app
```

### Pattern 2: Deploy Missing Service via CloudBuild
**What:** Trigger CloudBuild to deploy a service
**When to use:** When service not found in list
**Example:**
```bash
# Deploy backend
gcloud builds submit \
    --config=infrastructure/cloudbuild/backend-cloudbuild.yaml \
    --substitutions=SHORT_SHA=$(git rev-parse --short HEAD) \
    .

# Deploy frontend (requires backend URL)
BACKEND_URL=$(gcloud run services describe loan-backend-prod --region=us-central1 --format="value(status.url)")
gcloud builds submit \
    --config=infrastructure/cloudbuild/frontend-cloudbuild.yaml \
    --substitutions=SHORT_SHA=$(git rev-parse --short HEAD),_BACKEND_URL=$BACKEND_URL \
    .

# Deploy GPU service (long build time ~30-60 min)
gcloud builds submit \
    --config=infrastructure/cloudbuild/gpu-cloudbuild.yaml \
    --substitutions=SHORT_SHA=$(git rev-parse --short HEAD) \
    .
```

### Pattern 3: Verify Health Endpoints
**What:** Check that each service responds to health checks
**When to use:** After deployment completes
**Example:**
```bash
# Backend health check (public endpoint)
BACKEND_URL=$(gcloud run services describe loan-backend-prod --region=us-central1 --format="value(status.url)")
curl -s "${BACKEND_URL}/health"
# Expected: {"status": "healthy"}

# Frontend check (loads page)
FRONTEND_URL=$(gcloud run services describe loan-frontend-prod --region=us-central1 --format="value(status.url)")
curl -s -o /dev/null -w "%{http_code}" "${FRONTEND_URL}"
# Expected: 200

# GPU service health (requires authentication)
GPU_URL=$(gcloud run services describe lightonocr-gpu --region=us-central1 --format="value(status.url)")
TOKEN=$(gcloud auth print-identity-token)
curl -s -H "Authorization: Bearer ${TOKEN}" "${GPU_URL}/health"
# Expected: {"status": "ok"} or similar from vLLM
```

### Pattern 4: Verify GPU Configuration
**What:** Check GPU settings are correct
**When to use:** After GPU service is deployed
**Example:**
```bash
# Source: https://docs.cloud.google.com/run/docs/configuring/services/gpu

# Check GPU configuration
gcloud run services describe lightonocr-gpu --region=us-central1 \
    --format="yaml(spec.template.spec.containers[0].resources)"

# Expected output should include:
# resources:
#   limits:
#     cpu: "8"
#     memory: 32Gi
#     nvidia.com/gpu: "1"

# Verify scale-to-zero (min-instances = 0)
gcloud run services describe lightonocr-gpu --region=us-central1 \
    --format="value(spec.template.metadata.annotations.'autoscaling.knative.dev/minScale')"
# Expected: 0
```

### Pattern 5: Verify Secret Manager Configuration
**What:** Check that required secrets exist and are accessible
**When to use:** Before testing backend connectivity
**Example:**
```bash
# Source: https://docs.cloud.google.com/run/docs/configuring/services/secrets

# List secrets
gcloud secrets list --format="table(name,createTime)"
# Expected secrets: database-url, gemini-api-key

# Verify backend has secret access (check IAM)
gcloud secrets get-iam-policy database-url \
    --format="table(bindings.members,bindings.role)" | grep loan-cloud-run

# Check secret is mounted to service
gcloud run services describe loan-backend-prod --region=us-central1 \
    --format="yaml(spec.template.spec.containers[0].env)"
```

### Anti-Patterns to Avoid
- **Testing GPU health without auth token:** GPU service requires IAM authentication
- **Assuming services exist:** Always check with `gcloud run services list` first
- **Skipping Cloud SQL verification:** Backend may start but fail on first DB query
- **Ignoring build logs:** Check `gcloud builds log BUILD_ID` when deployments fail

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Deployment scripts | Custom deploy.sh | CloudBuild configs | Already exist, tested, idempotent |
| Health check verification | Custom monitoring | curl + gcloud | Simple, reliable, scriptable |
| Secret verification | Manual checks | `gcloud secrets` commands | Auditable, consistent |
| Infrastructure creation | Manual console clicks | provision-infra.sh | Already scripted, idempotent |

**Key insight:** This phase is verification, not creation. Use existing scripts and CloudBuild configs.

## Common Pitfalls

### Pitfall 1: GPU Service Cold Start Timeout
**What goes wrong:** Health check to GPU service times out
**Why it happens:** GPU service scale-to-zero means cold start of 10-40 seconds
**How to avoid:** Wait for cold start, use longer timeout (60s+) for first health check
**Warning signs:** "Connection reset" or timeout errors on first request

### Pitfall 2: Frontend Cannot Reach Backend
**What goes wrong:** Frontend loads but API calls fail
**Why it happens:** NEXT_PUBLIC_API_URL not set correctly at build time
**How to avoid:** Verify `_BACKEND_URL` substitution was passed to frontend build
**Warning signs:** Browser console shows CORS errors or undefined API URL

### Pitfall 3: Backend Cannot Reach Cloud SQL
**What goes wrong:** Backend returns 500 on database queries
**Why it happens:** VPC egress not configured or Cloud SQL not running
**How to avoid:** Verify VPC settings in service config, check Cloud SQL instance status
**Warning signs:** "Connection refused" or timeout errors in Cloud Logging

### Pitfall 4: Missing IAM Permissions
**What goes wrong:** Service starts but fails on secret access or GPU auth
**Why it happens:** Service account lacks required roles
**How to avoid:** Verify IAM bindings for service accounts
**Warning signs:** "PERMISSION_DENIED" in logs

### Pitfall 5: CloudBuild Fails Silently
**What goes wrong:** Build appears to succeed but service not deployed
**Why it happens:** Build succeeded but deploy step failed
**How to avoid:** Check build logs for all steps, verify service URL exists
**Warning signs:** Build shows success but `gcloud run services list` missing service

### Pitfall 6: Using Wrong Project
**What goes wrong:** Services deployed to wrong GCP project
**Why it happens:** gcloud config project not set correctly
**How to avoid:** Always verify project with `gcloud config get-value project`
**Warning signs:** Services not found where expected

## Code Examples

Verified patterns from official sources:

### Complete Verification Script
```bash
#!/bin/bash
# verify-production.sh - Production deployment verification script
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID environment variable}"
REGION="${REGION:-us-central1}"

echo "Verifying production deployment for: $PROJECT_ID"
gcloud config set project "$PROJECT_ID"

# Step 1: Check existing services
echo ""
echo "[1/5] Checking deployed services..."
gcloud run services list --region="$REGION" --format="table(SERVICE,URL)"

# Step 2: Verify backend
echo ""
echo "[2/5] Verifying backend..."
if BACKEND_URL=$(gcloud run services describe loan-backend-prod --region="$REGION" --format="value(status.url)" 2>/dev/null); then
    HEALTH=$(curl -s "${BACKEND_URL}/health" || echo '{"error": "failed"}')
    echo "Backend URL: $BACKEND_URL"
    echo "Health: $HEALTH"
else
    echo "ERROR: Backend not deployed"
fi

# Step 3: Verify frontend
echo ""
echo "[3/5] Verifying frontend..."
if FRONTEND_URL=$(gcloud run services describe loan-frontend-prod --region="$REGION" --format="value(status.url)" 2>/dev/null); then
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${FRONTEND_URL}")
    echo "Frontend URL: $FRONTEND_URL"
    echo "HTTP Status: $STATUS"
else
    echo "ERROR: Frontend not deployed"
fi

# Step 4: Verify GPU service
echo ""
echo "[4/5] Verifying GPU service..."
if GPU_URL=$(gcloud run services describe lightonocr-gpu --region="$REGION" --format="value(status.url)" 2>/dev/null); then
    echo "GPU URL: $GPU_URL"

    # Check GPU configuration
    GPU_CONFIG=$(gcloud run services describe lightonocr-gpu --region="$REGION" \
        --format="value(spec.template.spec.containers[0].resources.limits.'nvidia.com/gpu')")
    echo "GPU Count: $GPU_CONFIG"

    MIN_INSTANCES=$(gcloud run services describe lightonocr-gpu --region="$REGION" \
        --format="value(spec.template.metadata.annotations.'autoscaling.knative.dev/minScale')" 2>/dev/null || echo "0")
    echo "Min Instances: $MIN_INSTANCES (scale-to-zero: $([ "$MIN_INSTANCES" = "0" ] && echo "yes" || echo "no"))"

    # Health check with auth (may timeout on cold start)
    TOKEN=$(gcloud auth print-identity-token)
    GPU_HEALTH=$(curl -s --max-time 60 -H "Authorization: Bearer ${TOKEN}" "${GPU_URL}/health" 2>/dev/null || echo '{"error": "timeout or auth failed"}')
    echo "Health: $GPU_HEALTH"
else
    echo "ERROR: GPU service not deployed"
fi

# Step 5: Summary
echo ""
echo "[5/5] Summary"
echo "=============================================="
gcloud run services list --region="$REGION" --format="table(SERVICE,URL,LAST_DEPLOYED_AT)"
```

### Deploy Single Service
```bash
# Source: Existing CloudBuild configs in infrastructure/cloudbuild/

# Deploy backend only
gcloud builds submit \
    --config=infrastructure/cloudbuild/backend-cloudbuild.yaml \
    --substitutions=SHORT_SHA=$(git rev-parse --short HEAD) \
    --async \
    .

# Watch build progress
gcloud builds list --limit=1 --format="table(id,status,startTime)"
gcloud builds log $(gcloud builds list --limit=1 --format="value(id)") --stream
```

### Check Cloud SQL Connectivity
```bash
# Verify Cloud SQL instance is running
gcloud sql instances describe loan-db-prod --format="value(state)"
# Expected: RUNNABLE

# Get private IP (used by backend via VPC)
gcloud sql instances describe loan-db-prod --format="value(ipAddresses[0].ipAddress)"

# Check backend logs for DB connection (after making a request)
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=loan-backend-prod" \
    --limit=10 --format="table(timestamp,textPayload)"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Terraform for deployments | CloudBuild + gcloud | v2.0 (Phase 16) | Already migrated in this project |
| VPC Connector | Direct VPC egress | Cloud Run 2024 | Used in cloudbuild configs |
| GPU quota requests | No quota required for L4 | 2025 GA | GPU available immediately |
| gcr.io images | Artifact Registry | 2024 deprecated | Used in cloudbuild configs |

**Deprecated/outdated:**
- Manual `gcloud run deploy` for each push: Use CloudBuild triggers
- VPC Access Connector: Direct VPC egress is simpler

## Open Questions

Things that couldn't be fully resolved:

1. **vLLM Health Endpoint Path**
   - What we know: vLLM provides OpenAI-compatible API
   - What's unclear: Exact health endpoint path (may be `/health` or `/v1/models`)
   - Recommendation: Try `/health` first, fall back to checking `/v1/models` response

2. **Cold Start Time for GPU Service**
   - What we know: 10-40 seconds typical, depends on image size and model loading
   - What's unclear: Exact time for LightOnOCR 2GB model
   - Recommendation: Use 60s timeout for first health check

3. **Existing Deployment State**
   - What we know: v2.0 shipped, CloudBuild configs exist
   - What's unclear: Whether services are already deployed to production
   - Recommendation: First step is always `gcloud run services list`

## Sources

### Primary (HIGH confidence)
- [gcloud run services list](https://docs.cloud.google.com/sdk/gcloud/reference/run/services/list) - Service listing
- [gcloud run services describe](https://docs.cloud.google.com/sdk/gcloud/reference/run/services/describe) - Service details
- [Cloud Run health checks](https://docs.cloud.google.com/run/docs/configuring/healthchecks) - Health check configuration
- [Cloud Run GPU support](https://docs.cloud.google.com/run/docs/configuring/services/gpu) - GPU configuration
- [Secret Manager for Cloud Run](https://docs.cloud.google.com/run/docs/configuring/services/secrets) - Secret configuration
- [Cloud Run managing services](https://docs.cloud.google.com/run/docs/managing/services) - Service management

### Secondary (MEDIUM confidence)
- [Simon Willison's gcloud run services list](https://til.simonwillison.net/cloudrun/gcloud-run-services-list) - Practical examples
- [Cloud Run GPUs GA announcement](https://cloud.google.com/blog/products/serverless/cloud-run-gpus-are-now-generally-available) - GPU GA status

### Project-Specific (HIGH confidence)
- `infrastructure/cloudbuild/backend-cloudbuild.yaml` - Existing backend deploy config
- `infrastructure/cloudbuild/frontend-cloudbuild.yaml` - Existing frontend deploy config
- `infrastructure/cloudbuild/gpu-cloudbuild.yaml` - Existing GPU deploy config
- `.planning/phases/16-cloudbuild-deployment/16-RESEARCH.md` - Prior deployment research

## Metadata

**Confidence breakdown:**
- Deployment verification commands: HIGH - Official gcloud documentation
- Health check patterns: HIGH - Standard HTTP/curl patterns
- GPU configuration: HIGH - Official Cloud Run GPU docs
- Cold start timing: MEDIUM - Varies by service and load

**Research date:** 2026-01-25
**Valid until:** 2026-02-25 (30 days - stable GCP services)

## Requirements Mapping

| Requirement | Research Finding | Confidence |
|-------------|------------------|------------|
| DEPLOY-01: Check existing deployments | `gcloud run services list` command | HIGH |
| DEPLOY-02: Deploy backend | Existing CloudBuild config, trigger if not deployed | HIGH |
| DEPLOY-03: Deploy frontend | Existing CloudBuild config with BACKEND_URL substitution | HIGH |
| DEPLOY-04: Deploy GPU service | Existing CloudBuild config, 30-60 min build time | HIGH |
| DEPLOY-05: Configure secrets | Already configured in CloudBuild --set-secrets, verify with gcloud | HIGH |
| DEPLOY-06: Verify health status | curl to /health endpoints, auth for GPU | HIGH |
