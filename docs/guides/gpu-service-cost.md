# GPU Service Cost Management Guide

This guide covers cost estimation and optimization strategies for the LightOnOCR GPU service.

## Cost Overview

The LightOnOCR service uses NVIDIA L4 GPUs for OCR processing of scanned documents.

### Pricing Components

| Component | Cost | Notes |
|-----------|------|-------|
| L4 GPU (running) | ~$0.50/hour | Billed per second while instances are active |
| L4 GPU (idle) | $0 | Scale-to-zero eliminates idle costs |
| Cold start | 60-120 seconds | No additional cost, just latency |

### Scale-to-Zero

The GPU service is configured with `min_instances=0`, meaning:
- **Zero cost when idle:** No charges when no OCR requests are being processed
- **Automatic scaling:** Service spins up on first request
- **Cold start penalty:** First request after idle period takes 60-120 seconds

This is ideal for intermittent OCR workloads where documents aren't processed continuously.

## Cost Estimation

### Per-Document Cost

Assuming average OCR processing time of 1-2 minutes:

| Document Type | Processing Time | Estimated Cost |
|---------------|-----------------|----------------|
| Single page scan | 30-60 seconds | ~$0.01 |
| Multi-page scan (5-10 pages) | 1-2 minutes | ~$0.01-0.02 |
| Large document (20+ pages) | 3-5 minutes | ~$0.03-0.05 |

### Monthly Cost Scenarios

| Volume | Documents/Month | Estimated Monthly Cost |
|--------|-----------------|------------------------|
| Light | 100 | $1-2 |
| Moderate | 500 | $5-10 |
| Heavy | 1,000 | $10-20 |
| High | 5,000 | $50-100 |

**Note:** These estimates assume:
- Scale-to-zero between processing batches
- Average 1-2 minute processing per document
- Mix of single and multi-page documents

## Cost Optimization Strategies

### 1. Use OCR Only When Needed

The biggest cost savings come from avoiding GPU processing entirely for native digital PDFs.

```bash
# Skip OCR for native PDFs (zero GPU cost)
curl -X POST "http://localhost:8000/api/documents/?ocr=skip" -F "file=@native.pdf"

# Auto-detect scanned pages (OCR only if needed)
curl -X POST "http://localhost:8000/api/documents/?ocr=auto" -F "file=@mixed.pdf"
```

**Recommendation:** Use `ocr=auto` (default) to automatically detect scanned documents. Only scanned documents incur GPU costs.

### 2. Batch Documents During Active Periods

Maximize GPU utilization by processing documents in batches rather than one at a time:

| Processing Pattern | Cold Starts/Day | Est. Daily Cost (100 docs) |
|-------------------|-----------------|----------------------------|
| Individual processing | 100 | Higher (many cold starts) |
| Hourly batches (4 batches of 25) | 4 | Lower (fewer cold starts) |
| Single daily batch | 1 | Lowest (minimal cold starts) |

**Strategy:**
- Queue documents in Cloud Tasks
- Process batches on a schedule (e.g., every hour)
- Keep GPU warm within batches by processing sequentially

### 3. Monitor Running Instances

Set up alerts when GPU instances run longer than expected:

```bash
# Create alert policy for sustained GPU usage
gcloud monitoring policies create \
  --display-name="GPU instance sustained usage" \
  --condition-display-name="GPU running >30 minutes" \
  --condition-filter='metric.type="run.googleapis.com/container/instance_count" AND resource.type="cloud_run_revision" AND resource.labels.service_name="lightonocr-gpu"' \
  --condition-threshold-value=1 \
  --condition-threshold-comparison=COMPARISON_GT \
  --condition-threshold-duration=1800s
```

### 4. Set Budget Alerts

Configure budget alerts for GPU-related charges:

```bash
# Create budget with alert thresholds
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="GPU OCR Budget" \
  --budget-amount=50USD \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90 \
  --threshold-rule=percent=100
```

## Monitoring Setup

### Cloud Run Metrics

Key metrics to monitor for cost control:

| Metric | What It Shows | Cost Relevance |
|--------|---------------|----------------|
| `instance_count` | Active GPU instances | Direct cost driver |
| `request_latency` | Processing time | Proxy for billing duration |
| `request_count` | OCR requests | Volume indicator |
| `billable_instance_time` | Actual billing time | Direct cost measurement |

### Dashboard Setup

Create a monitoring dashboard:

```bash
# Export dashboard config (sample)
cat <<EOF > gpu-cost-dashboard.json
{
  "displayName": "GPU Service Cost",
  "mosaicLayout": {
    "tiles": [
      {
        "widget": {
          "title": "Active Instances",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"run.googleapis.com/container/instance_count\" resource.labels.service_name=\"lightonocr-gpu\""
                }
              }
            }]
          }
        }
      },
      {
        "widget": {
          "title": "Request Latency",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"run.googleapis.com/request_latencies\" resource.labels.service_name=\"lightonocr-gpu\""
                }
              }
            }]
          }
        }
      }
    ]
  }
}
EOF

# Create dashboard
gcloud monitoring dashboards create --config-from-file=gpu-cost-dashboard.json
```

### Alert on Sustained Usage

Detect when GPU stays running longer than expected:

```bash
# Alert if GPU runs continuously for 1 hour
gcloud monitoring policies create \
  --display-name="GPU continuous usage alert" \
  --condition-display-name="GPU instance running >1 hour" \
  --condition-filter='
    metric.type="run.googleapis.com/container/billable_instance_time"
    resource.type="cloud_run_revision"
    resource.labels.service_name="lightonocr-gpu"
  ' \
  --condition-aggregation-alignment-period=3600s \
  --condition-aggregation-per-series-aligner=ALIGN_RATE \
  --condition-threshold-value=3600 \
  --condition-threshold-comparison=COMPARISON_GT \
  --notification-channels=CHANNEL_ID
```

## Cost vs. Latency Trade-offs

### Option A: Minimize Cost (Scale-to-Zero)

**Configuration:**
```yaml
min_instances: 0
max_instances: 3
```

**Behavior:**
- GPU shuts down when idle
- First request waits 60-120 seconds
- Lowest cost for intermittent workloads

**Best for:** <100 documents/day, batch processing

### Option B: Minimize Latency (Warm Instance)

**Configuration:**
```yaml
min_instances: 1
max_instances: 3
```

**Behavior:**
- One GPU always running (~$0.50/hour = ~$360/month)
- All requests respond immediately (no cold start)
- Higher cost but consistent latency

**Best for:** >1000 documents/day, real-time processing needs

### Option C: Scheduled Warm-up

**Strategy:**
- Keep `min_instances: 0`
- Use Cloud Scheduler to send warm-up requests before peak hours
- GPU stays warm during business hours, scales to zero overnight

```bash
# Create warm-up job for business hours
gcloud scheduler jobs create http gpu-warmup \
  --schedule="0 8 * * 1-5" \
  --uri="https://lightonocr-gpu-xxx.run.app/health" \
  --oidc-service-account-email=scheduler@PROJECT_ID.iam.gserviceaccount.com \
  --oidc-token-audience="https://lightonocr-gpu-xxx.run.app"
```

## Quick Cost Reference

| Scenario | Monthly Cost Estimate |
|----------|----------------------|
| 50 docs/month, all scanned | $0.50-1.00 |
| 100 docs/month, 50% scanned | $0.50-1.00 |
| 500 docs/month, 30% scanned | $2-4 |
| 1000 docs/month, 20% scanned | $3-6 |
| 5000 docs/month, 10% scanned | $5-10 |
| Always-on instance (no scale-to-zero) | ~$360/month |

## See Also

- [LightOnOCR Deployment Guide](./lightonocr-deployment.md) - Deploying the GPU service
- [Extraction Method Guide](../api/extraction-method-guide.md) - OCR parameter usage
- [CloudBuild Deployment Guide](../cloudbuild-deployment-guide.md) - Full deployment workflow
