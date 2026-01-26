# LightOnOCR Service Deployment Guide

This guide provides step-by-step instructions to deploy and configure the LightOnOCR GPU service for the loan document extraction system.

## Overview

The LightOnOCR service enables high-quality OCR for scanned documents using GPU acceleration. When the backend detects scanned documents, it routes them through the LightOnOCR service for superior text extraction.

## Architecture

```
Backend Service → LightOnOCR GPU Service (Cloud Run + L4 GPU) → Text Extraction
     ↓ (fallback if unavailable)
Docling Local OCR
```

## Prerequisites

### 1. GCP Project Access

Ensure you have the following roles in the `stackpoint-loan-dev` project:
- `roles/run.admin` - Deploy Cloud Run services
- `roles/iam.serviceAccountUser` - Use service accounts
- `roles/cloudbuild.builds.editor` - Trigger builds
- `roles/artifactregistry.writer` - Push container images

Check your current access:
```bash
gcloud projects get-iam-policy stackpoint-loan-dev \
  --flatten="bindings[].members" \
  --filter="bindings.members:$(gcloud config get-value account)" \
  --format="table(bindings.role)"
```

### 2. L4 GPU Quota

Check GPU quota availability:
```bash
gcloud compute regions describe us-central1 \
  --project=stackpoint-loan-dev \
  --format="table(quotas.metric,quotas.limit,quotas.usage)" \
  | grep -i l4
```

Expected output should show `NVIDIA_L4_GPUS` with limit ≥ 1.

If quota is 0, request it via: https://console.cloud.google.com/iam-admin/quotas?project=stackpoint-loan-dev

### 3. Required APIs

Enable required APIs:
```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  compute.googleapis.com \
  --project=stackpoint-loan-dev
```

### 4. Service Accounts

Create the LightOnOCR GPU service account:
```bash
cd infrastructure/scripts
./setup-lightonocr-sa.sh stackpoint-loan-dev
```

Verify it was created:
```bash
gcloud iam service-accounts describe lightonocr-gpu@stackpoint-loan-dev.iam.gserviceaccount.com \
  --project=stackpoint-loan-dev
```

### 5. Artifact Registry Repository

Verify the container repository exists:
```bash
gcloud artifacts repositories describe loan-repo \
  --location=us-central1 \
  --project=stackpoint-loan-dev
```

If it doesn't exist, create it:
```bash
gcloud artifacts repositories create loan-repo \
  --repository-format=docker \
  --location=us-central1 \
  --project=stackpoint-loan-dev \
  --description="Loan application container images"
```

## Deployment Steps

### Step 1: Deploy LightOnOCR GPU Service

**Option A: Using CloudBuild (Recommended)**

This approach uses Cloud Build for building the large container image remotely:

```bash
cd /Users/gregorydickson/stackpoint/loan

gcloud builds submit \
  --config=infrastructure/cloudbuild/gpu-cloudbuild.yaml \
  --project=stackpoint-loan-dev \
  --substitutions=SHORT_SHA=$(git rev-parse --short HEAD) \
  .
```

**Build time:** 30-60 minutes (vLLM base image is ~8GB + model download ~2GB)

**Option B: Using Deploy Script**

For more control or debugging:

```bash
cd infrastructure/lightonocr-gpu
PROJECT_ID=stackpoint-loan-dev REGION=us-central1 ./deploy.sh
```

### Step 2: Verify GPU Service Deployment

Get the service URL:
```bash
SERVICE_URL=$(gcloud run services describe lightonocr-gpu \
  --region=us-central1 \
  --project=stackpoint-loan-dev \
  --format="value(status.url)")

echo "LightOnOCR Service URL: $SERVICE_URL"
```

Test health endpoint:
```bash
TOKEN=$(gcloud auth print-identity-token)
curl -sf -H "Authorization: Bearer $TOKEN" ${SERVICE_URL}/health

# Expected output: {"status":"ok"} or similar
```

Test the models endpoint:
```bash
curl -sf -H "Authorization: Bearer $TOKEN" ${SERVICE_URL}/v1/models

# Expected output should include "lightonai/LightOnOCR-2-1B"
```

### Step 3: Verify IAM Permissions

Ensure the backend service account can invoke the GPU service:

```bash
gcloud run services get-iam-policy lightonocr-gpu \
  --region=us-central1 \
  --project=stackpoint-loan-dev \
  --filter="bindings.members:serviceAccount:loan-cloud-run@stackpoint-loan-dev.iam.gserviceaccount.com" \
  --flatten="bindings[].members"
```

If not set, add the binding:
```bash
gcloud run services add-iam-policy-binding lightonocr-gpu \
  --member="serviceAccount:loan-cloud-run@stackpoint-loan-dev.iam.gserviceaccount.com" \
  --role=roles/run.invoker \
  --region=us-central1 \
  --project=stackpoint-loan-dev
```

### Step 4: Configure Backend Environment

Update the backend deployment configuration with the LightOnOCR service URL.

First, get the service URL:
```bash
SERVICE_URL=$(gcloud run services describe lightonocr-gpu \
  --region=us-central1 \
  --project=stackpoint-loan-dev \
  --format="value(status.url)")

echo "Export this for the next step:"
echo "LIGHTONOCR_SERVICE_URL=$SERVICE_URL"
```

### Step 5: Deploy Backend with OCR Configuration

Deploy the backend with the LightOnOCR service URL:

```bash
cd /Users/gregorydickson/stackpoint/loan

# Get the LightOnOCR URL (from Step 4)
LIGHTONOCR_URL=$(gcloud run services describe lightonocr-gpu \
  --region=us-central1 \
  --project=stackpoint-loan-dev \
  --format="value(status.url)")

# Get the frontend URL (if already deployed)
FRONTEND_URL=$(gcloud run services describe loan-frontend-prod \
  --region=us-central1 \
  --project=stackpoint-loan-dev \
  --format="value(status.url)" 2>/dev/null || echo "")

# Deploy backend with OCR configuration
gcloud builds submit \
  --config=infrastructure/cloudbuild/backend-cloudbuild.yaml \
  --project=stackpoint-loan-dev \
  --substitutions=SHORT_SHA=$(git rev-parse --short HEAD),_LIGHTONOCR_SERVICE_URL=${LIGHTONOCR_URL},_FRONTEND_URL=${FRONTEND_URL} \
  backend/
```

### Step 6: Verify End-to-End Integration

Check backend logs to ensure OCR router initialized:
```bash
gcloud run services logs loan-backend-prod \
  --region=us-central1 \
  --project=stackpoint-loan-dev \
  --limit=50 \
  | grep -i "ocr\|lightonocr"
```

Expected log entries:
- OCR router initialization messages
- LightOnOCR client configuration

Test with a scanned document upload through the API.

## Configuration Reference

### Backend Environment Variables

After deployment, the backend should have these environment variables set:

| Variable | Value | Purpose |
|----------|-------|---------|
| `LIGHTONOCR_SERVICE_URL` | `https://lightonocr-gpu-xxx.run.app` | GPU OCR service endpoint |
| `GCP_PROJECT_ID` | `stackpoint-loan-dev` | GCP project for Cloud Tasks |
| `GCP_LOCATION` | `us-central1` | Region for Cloud Tasks |
| `CLOUD_RUN_SERVICE_URL` | Backend service URL | For task callbacks |
| `GCS_BUCKET` | `stackpoint-loan-documents` | Document storage |

### GPU Service Configuration

| Setting | Value | Rationale |
|---------|-------|-----------|
| vCPU | 8 | Sufficient for model serving |
| Memory | 32Gi | Headroom for L4 GPU + model |
| GPU | nvidia-l4 (1) | Cost-effective GPU |
| Min instances | 0 | Scale-to-zero for cost savings |
| Max instances | 3 | Limit concurrent GPU usage |
| Startup probe | 240s | Time for model loading |

## Troubleshooting

### Issue: Permission Denied on Project

**Symptom:**
```
ERROR: [user@email.com] does not have permission to access namespaces instance [stackpoint-loan-dev]
```

**Solution:**
Contact project owner to grant you the required roles listed in Prerequisites.

### Issue: GPU Quota Exceeded

**Symptom:**
```
ERROR: GPU quota exceeded for NVIDIA_L4_GPUS
```

**Solution:**
1. Check current quota:
   ```bash
   gcloud compute regions describe us-central1 \
     --project=stackpoint-loan-dev \
     --format="table(quotas.metric,quotas.limit,quotas.usage)" \
     | grep -i l4
   ```

2. Request quota increase via GCP Console if limit is 0

3. Or reduce max-instances in deployment:
   ```bash
   gcloud run services update lightonocr-gpu \
     --region=us-central1 \
     --project=stackpoint-loan-dev \
     --max-instances=1
   ```

### Issue: Cold Start Timeouts

**Symptom:** First request after idle period times out

**Solution:**
1. The client is configured with 120s timeout for cold starts
2. If still timing out, consider setting min-instances=1 (increases cost):
   ```bash
   gcloud run services update lightonocr-gpu \
     --region=us-central1 \
     --project=stackpoint-loan-dev \
     --min-instances=1
   ```

### Issue: Authentication Failures

**Symptom:**
```
LightOnOCRError: Authentication failed
```

**Solution:**
1. Verify IAM binding exists:
   ```bash
   gcloud run services get-iam-policy lightonocr-gpu \
     --region=us-central1 \
     --project=stackpoint-loan-dev
   ```

2. Check backend service account in logs:
   ```bash
   gcloud run services logs loan-backend-prod \
     --region=us-central1 \
     --project=stackpoint-loan-dev \
     | grep -i "service account\|authentication"
   ```

3. Re-add IAM binding if missing (see Step 3)

### Issue: Service Not Responding

**Symptom:** Health check fails or requests return 502/503

**Solution:**
1. Check service status:
   ```bash
   gcloud run services describe lightonocr-gpu \
     --region=us-central1 \
     --project=stackpoint-loan-dev
   ```

2. View service logs:
   ```bash
   gcloud run services logs lightonocr-gpu \
     --region=us-central1 \
     --project=stackpoint-loan-dev \
     --limit=100
   ```

3. Look for startup errors, OOM issues, or model loading failures

4. Force new revision:
   ```bash
   gcloud run services update lightonocr-gpu \
     --region=us-central1 \
     --project=stackpoint-loan-dev \
     --revision-suffix=$(date +%s)
   ```

### Issue: Backend Not Using OCR Service

**Symptom:** Backend processes documents but never calls LightOnOCR

**Solution:**
1. Check if environment variable is set:
   ```bash
   gcloud run services describe loan-backend-prod \
     --region=us-central1 \
     --project=stackpoint-loan-dev \
     --format="yaml(spec.template.spec.containers[0].env)"
   ```

2. Look for `LIGHTONOCR_SERVICE_URL` in the output

3. If missing, redeploy backend with the URL (Step 5)

## Monitoring

### Key Metrics to Watch

| Metric | Threshold | Action |
|--------|-----------|--------|
| Instance count > 0 for 1hr+ | Normal workload | Review if unexpected |
| Request latency > 120s | Cold start issue | Consider min-instances=1 |
| Memory utilization > 90% | Near OOM | Check logs, reduce batch size |
| Error rate > 5% | Service issues | Check logs and health |

### Useful Commands

```bash
# View recent GPU service logs
gcloud run services logs lightonocr-gpu \
  --region=us-central1 \
  --project=stackpoint-loan-dev \
  --limit=50

# View recent backend logs
gcloud run services logs loan-backend-prod \
  --region=us-central1 \
  --project=stackpoint-loan-dev \
  --limit=50

# Check current revision
gcloud run services describe lightonocr-gpu \
  --region=us-central1 \
  --project=stackpoint-loan-dev \
  --format="value(status.latestReadyRevisionName)"

# List all revisions
gcloud run revisions list \
  --service=lightonocr-gpu \
  --region=us-central1 \
  --project=stackpoint-loan-dev
```

## Rollback

If deployment causes issues, roll back to previous revision:

```bash
# List recent revisions
gcloud run revisions list \
  --service=lightonocr-gpu \
  --region=us-central1 \
  --project=stackpoint-loan-dev \
  --limit=5

# Roll back to previous revision
gcloud run services update-traffic lightonocr-gpu \
  --region=us-central1 \
  --project=stackpoint-loan-dev \
  --to-revisions=PREVIOUS_REVISION_NAME=100
```

## Cost Optimization

### Current Configuration
- **Scale-to-zero enabled**: Service scales down after ~15 minutes of idle time
- **Cost during idle**: $0/month
- **Cost per hour active**: ~$1.50/hour (L4 GPU pricing)

### Recommendations
1. **Keep scale-to-zero**: Only pay when processing documents
2. **Accept cold starts**: 60-120s latency on first request is acceptable for batch processing
3. **Monitor usage**: If processing many documents daily, consider min-instances=1 for consistent performance
4. **Use batch processing**: Process multiple documents in sequence while instance is warm

## Next Steps

After successful deployment:

1. **Test with scanned documents**: Upload scanned PDFs through the UI
2. **Monitor performance**: Check latency and accuracy of OCR results
3. **Review costs**: Monitor GPU service usage in GCP billing
4. **Set up alerts**: Configure Cloud Monitoring alerts for errors and high latency
5. **Document results**: Record OCR quality improvements vs. Docling fallback

## Related Documentation

- [LightOnOCR Deployment Guide](./lightonocr-deployment.md) - Original deployment guide
- [Extraction Method Guide](../api/extraction-method-guide.md) - Using OCR parameters
- [System Design](../SYSTEM_DESIGN.md) - Overall architecture
- [GPU Service Cost Guide](./gpu-service-cost.md) - Cost management strategies
