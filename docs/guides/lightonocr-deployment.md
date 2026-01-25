# LightOnOCR GPU Service Deployment Guide

This guide covers deploying and managing the LightOnOCR GPU service on Cloud Run.

## Overview

LightOnOCR is a vLLM-based OCR service that uses the LightOnOCR-2-1B model to extract text from scanned documents. It runs on Cloud Run with NVIDIA L4 GPU.

### Architecture

```
Document Upload
      |
      v
Backend Service
      |
      | (scanned document detected)
      v
LightOnOCR GPU Service (Cloud Run)
      |
      | (OCR'd text)
      v
Continue to extraction pipeline
```

## Prerequisites

Before deploying, ensure you have:

### 1. L4 GPU Quota

Request L4 GPU quota in your target region:

```bash
# Check current quota
gcloud compute regions describe us-central1 \
  --format="table(quotas.metric,quotas.limit,quotas.usage)" \
  | grep -i gpu
```

If quota is 0, [request quota increase](https://console.cloud.google.com/iam-admin/quotas) for:
- **Metric:** `NVIDIA_L4_GPUS`
- **Region:** `us-central1`
- **Requested limit:** 1 (minimum for single instance)

See [GPU Quota Request Guide](../gpu-quota-request.md) for detailed instructions.

### 2. Service Account

Create a service account for the GPU service:

```bash
# Create service account
gcloud iam service-accounts create lightonocr-gpu \
  --display-name="LightOnOCR GPU Service Account"

# Grant required roles
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:lightonocr-gpu@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```

### 3. Artifact Registry Repository

Ensure the container repository exists:

```bash
# Create repository if not exists
gcloud artifacts repositories create loan-repo \
  --repository-format=docker \
  --location=us-central1 \
  --description="Loan application container images"
```

### 4. Enable Required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com
```

## Deployment Steps

### Option 1: CloudBuild (Recommended)

Use CloudBuild for automated builds and deployments:

```bash
# Build and deploy GPU image
gcloud builds submit \
  --config=infrastructure/cloudbuild/gpu-cloudbuild.yaml \
  --substitutions=SHORT_SHA=$(git rev-parse --short HEAD) \
  .
```

**Build time:** 30-60 minutes (vLLM base image + model download)

### Option 2: Manual Deployment

For debugging or custom configurations:

```bash
# Step 1: Build image
docker build -t us-central1-docker.pkg.dev/PROJECT_ID/loan-repo/lightonocr-gpu:latest \
  ./infrastructure/lightonocr-gpu

# Step 2: Push to Artifact Registry
docker push us-central1-docker.pkg.dev/PROJECT_ID/loan-repo/lightonocr-gpu:latest

# Step 3: Deploy to Cloud Run
gcloud run deploy lightonocr-gpu \
  --image=us-central1-docker.pkg.dev/PROJECT_ID/loan-repo/lightonocr-gpu:latest \
  --region=us-central1 \
  --service-account=lightonocr-gpu@PROJECT_ID.iam.gserviceaccount.com \
  --no-allow-unauthenticated \
  --cpu=8 \
  --memory=32Gi \
  --gpu=1 \
  --gpu-type=nvidia-l4 \
  --port=8000 \
  --min-instances=0 \
  --max-instances=3 \
  --no-cpu-throttling \
  --no-gpu-zonal-redundancy \
  --startup-probe='tcpSocket.port=8000,initialDelaySeconds=240,failureThreshold=1,timeoutSeconds=240,periodSeconds=240'
```

### Verify Deployment

```bash
# Check service status
gcloud run services describe lightonocr-gpu --region=us-central1

# Get service URL
gcloud run services describe lightonocr-gpu \
  --region=us-central1 \
  --format="value(status.url)"
```

## Configuration Reference

### Cloud Run Settings

| Setting | Value | Rationale |
|---------|-------|-----------|
| vCPU | 8 | Sufficient for model serving |
| Memory | 32Gi | Headroom for L4 GPU + model |
| GPU | nvidia-l4 (1) | Smallest GPU with good vLLM support |
| Min instances | 0 | Scale-to-zero for cost savings |
| Max instances | 3 | Limit concurrent GPU usage |
| Startup probe | 240s | Time for model loading |

### vLLM Configuration

The Dockerfile configures vLLM with these flags:

| Flag | Value | Purpose |
|------|-------|---------|
| `--model` | `lightonai/LightOnOCR-2-1B` | Model to serve |
| `--gpu-memory-utilization` | `0.80` | Leave headroom for peaks |
| `--max-num-seqs` | `8` | Prevent OOM on L4 |
| `--max-model-len` | `4096` | Limit context for memory |
| `--limit-mm-per-prompt` | `{"image": 1}` | One image per OCR request |
| `--no-enable-prefix-caching` | - | Disable for one-off requests |

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `HF_HOME` | Model cache directory (`/model-cache`) |
| `HF_HUB_OFFLINE` | Prevents runtime model downloads |

## Cold Start Behavior

The GPU service uses scale-to-zero, which means:

1. **First request after idle:** 60-120 second cold start
2. **Subsequent requests:** Normal latency (~5-30 seconds per page)
3. **After ~15 minutes idle:** Instance scales down, next request cold starts

### Client Configuration

The backend client (`lightonocr_client.py`) is configured for cold starts:

- **Default timeout:** 120 seconds
- **Retry logic:** 3 attempts with exponential backoff
- **Circuit breaker:** Opens after 3 consecutive failures

## Troubleshooting

### Cold Start Timeouts

**Symptom:** First request fails with timeout error

**Solution:**
1. Increase client timeout in `lightonocr_client.py`:
   ```python
   DEFAULT_TIMEOUT = 180  # Increase from 120
   ```
2. Or use warm-up requests before processing batches

### OOM Errors

**Symptom:** Service crashes with out-of-memory error

**Solution:**
1. Reduce `max_seqs` in Dockerfile:
   ```
   --max-num-seqs 4  # Reduce from 8
   ```
2. Reduce `max-model-len`:
   ```
   --max-model-len 2048  # Reduce from 4096
   ```
3. Process documents sequentially rather than in parallel

### Model Loading Failures

**Symptom:** Service fails to start, logs show model loading errors

**Solutions:**

1. **Check Artifact Registry permissions:**
   ```bash
   gcloud artifacts repositories get-iam-policy loan-repo \
     --location=us-central1
   ```

2. **Verify model cached in image:**
   ```bash
   # Check image layers
   gcloud artifacts docker images describe \
     us-central1-docker.pkg.dev/PROJECT_ID/loan-repo/lightonocr-gpu:latest \
     --show-package-vulnerability
   ```

3. **Rebuild image if model download failed:**
   ```bash
   gcloud builds submit \
     --config=infrastructure/cloudbuild/gpu-cloudbuild.yaml \
     --no-cache \
     --substitutions=SHORT_SHA=$(git rev-parse --short HEAD) \
     .
   ```

### GPU Quota Exceeded

**Symptom:** Deployment fails with "GPU quota exceeded"

**Solutions:**

1. **Check current quota:**
   ```bash
   gcloud compute regions describe us-central1 \
     --format="table(quotas.metric,quotas.limit,quotas.usage)" \
     | grep -i l4
   ```

2. **Request quota increase** if at limit

3. **Reduce max_instances** if quota is limited:
   ```bash
   gcloud run services update lightonocr-gpu \
     --region=us-central1 \
     --max-instances=1
   ```

### Service Not Responding

**Symptom:** Requests hang or return 502/503 errors

**Solutions:**

1. **Check service logs:**
   ```bash
   gcloud run services logs lightonocr-gpu \
     --region=us-central1 \
     --limit=100
   ```

2. **Verify startup probe settings:**
   ```bash
   gcloud run services describe lightonocr-gpu \
     --region=us-central1 \
     --format="yaml(spec.template.spec.containers.startupProbe)"
   ```

3. **Force new revision:**
   ```bash
   gcloud run services update lightonocr-gpu \
     --region=us-central1 \
     --revision-suffix=$(date +%s)
   ```

## Monitoring

### Key Metrics

| Metric | Alert Threshold | Action |
|--------|-----------------|--------|
| Instance count > 0 for 1hr+ | Normal workload | Review if unexpected |
| Request latency > 120s | Cold start | Consider min-instances=1 |
| Memory utilization > 90% | Near OOM | Reduce max_seqs |
| Error rate > 5% | Service issues | Check logs |

### Useful Commands

```bash
# View recent logs
gcloud run services logs lightonocr-gpu --region=us-central1 --limit=50

# Check current revision
gcloud run services describe lightonocr-gpu \
  --region=us-central1 \
  --format="value(status.latestReadyRevisionName)"

# List revisions
gcloud run revisions list --service=lightonocr-gpu --region=us-central1

# Scale to zero immediately (for testing)
gcloud run services update lightonocr-gpu \
  --region=us-central1 \
  --max-instances=0

# Restore scaling
gcloud run services update lightonocr-gpu \
  --region=us-central1 \
  --max-instances=3
```

## Rollback

If a deployment causes issues:

```bash
# List recent revisions
gcloud run revisions list --service=lightonocr-gpu --region=us-central1 --limit=5

# Roll back to previous revision
gcloud run services update-traffic lightonocr-gpu \
  --region=us-central1 \
  --to-revisions=PREVIOUS_REVISION_NAME=100
```

## See Also

- [GPU Service Cost Guide](./gpu-service-cost.md) - Cost management strategies
- [Extraction Method Guide](../api/extraction-method-guide.md) - Using OCR parameters
- [CloudBuild Deployment Guide](../cloudbuild-deployment-guide.md) - Full deployment workflow
- [GPU Quota Request Guide](../gpu-quota-request.md) - Requesting L4 GPU quota
