# Phase 13: LightOnOCR GPU Service - Research

**Researched:** 2026-01-25
**Domain:** Cloud Run GPU Deployment, vLLM Serving, LightOnOCR Model, Service-to-Service Authentication
**Confidence:** HIGH

## Summary

Phase 13 deploys a dedicated Cloud Run GPU service for high-quality OCR using the LightOnOCR-2-1B model via vLLM inference. Research confirms this is a well-supported deployment pattern with Google providing detailed documentation and codelabs for vLLM on Cloud Run GPU.

Cloud Run GPU (L4) is now GA with automatic 3 GPU quota granted. The L4 GPU provides 24GB VRAM which is ample for the 1B parameter LightOnOCR-2-1B model. Scale-to-zero is fully supported, and GPU instances start in approximately 5 seconds (plus model loading time). vLLM v0.11.1+ officially supports LightOnOCR, with the LightOnOCR-2-1B model requiring transformers installed from source.

Per the CONTEXT.md decisions, this is a POC deployment with simple synchronous request/response pattern, basic Cloud Run logs, and vLLM defaults for resource management.

**Primary recommendation:** Use the vLLM official Docker image with custom layer for transformers from source, deploy with `gcloud run deploy` using `--gpu=1 --gpu-type=nvidia-l4`, and use service account authentication for internal service-to-service calls.

## Standard Stack

The established tools for this GPU service deployment:

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| vLLM | 0.11.2+ | LightOnOCR model serving | Official support since v0.11.1, OpenAI-compatible API |
| LightOnOCR-2-1B | latest | End-to-end OCR model | State-of-the-art performance, 9x smaller than competitors |
| Cloud Run GPU | L4 | GPU compute platform | Scale-to-zero, no reservations, 24GB VRAM |
| gcloud CLI | latest | Deployment and configuration | Official GCP tooling |

### Supporting
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| Docker | latest | Container image building | Image with vLLM + transformers from source |
| Artifact Registry | - | Container image storage | Required for Cloud Run deployments |
| transformers | from source | Model dependencies | LightOnOCR-2-1B requires source install |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| vLLM | Transformers directly | vLLM provides OpenAI-compatible API, batching, production serving |
| Cloud Run GPU | Vertex AI Endpoints | Vertex is always-on, no scale-to-zero, higher cost |
| L4 GPU | A100 GPU | L4 is cheaper, sufficient for 1B model, available without reservation |

**Installation/Deployment:**
```bash
# Build custom Docker image
docker build -t lightonocr-gpu .

# Push to Artifact Registry
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/lightonocr-gpu:latest

# Deploy to Cloud Run
gcloud run deploy lightonocr-gpu \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/lightonocr-gpu:latest \
  --gpu=1 --gpu-type=nvidia-l4 \
  --cpu=8 --memory=32Gi \
  --min-instances=0 --max-instances=3 \
  --no-allow-unauthenticated
```

## Architecture Patterns

### Recommended Project Structure
```
backend/
  src/
    ocr/
      lightonocr_client.py    # HTTP client for GPU service
      __init__.py

infrastructure/
  lightonocr-gpu/
    Dockerfile                # vLLM + transformers from source
    cloudbuild.yaml           # CloudBuild deployment (Phase 16)
```

### Pattern 1: Dockerfile for LightOnOCR GPU Service
**What:** Docker image based on vLLM official image with transformers from source
**When to use:** Building the GPU service container
**Example:**
```dockerfile
# Source: Google Cloud vLLM tutorial + LightOnOCR requirements
FROM vllm/vllm-openai:v0.11.2

# LightOnOCR-2 requires transformers from source
RUN pip install git+https://github.com/huggingface/transformers.git
RUN pip install pillow pypdfium2

# Download model at build time for faster cold starts
ENV HF_HOME=/model-cache
RUN huggingface-cli download lightonai/LightOnOCR-2-1B

# Run in offline mode after download
ENV HF_HUB_OFFLINE=1

# vLLM entrypoint with LightOnOCR-specific flags
ENTRYPOINT python3 -m vllm.entrypoints.openai.api_server \
    --port ${PORT:-8000} \
    --model lightonai/LightOnOCR-2-1B \
    --limit-mm-per-prompt '{"image": 1}' \
    --mm-processor-cache-gb 0 \
    --no-enable-prefix-caching
```

### Pattern 2: Cloud Run Deployment Command
**What:** gcloud command with all required GPU and authentication flags
**When to use:** Initial deployment and updates
**Example:**
```bash
# Source: https://cloud.google.com/run/docs/tutorials/gpu-gemma2-with-vllm
gcloud run deploy lightonocr-gpu \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/lightonocr-gpu:latest \
  --service-account ${SA_EMAIL} \
  --cpu=8 \
  --memory=32Gi \
  --gpu=1 \
  --gpu-type=nvidia-l4 \
  --port=8000 \
  --region ${REGION} \
  --no-allow-unauthenticated \
  --min-instances=0 \
  --max-instances=3 \
  --no-cpu-throttling \
  --no-gpu-zonal-redundancy \
  --startup-probe tcpSocket.port=8000,initialDelaySeconds=240,failureThreshold=1,timeoutSeconds=240,periodSeconds=240
```

### Pattern 3: LightOnOCRClient HTTP Client
**What:** Python client in backend to call GPU service
**When to use:** From backend when OCR is needed for scanned documents
**Example:**
```python
# Source: vLLM OpenAI-compatible API docs
import httpx
import base64
from pathlib import Path
from google.auth.transport.requests import Request
from google.auth import default

class LightOnOCRClient:
    """Client for LightOnOCR GPU service using vLLM OpenAI-compatible API."""

    def __init__(self, service_url: str, timeout: float = 120.0):
        self.service_url = service_url.rstrip("/")
        self.timeout = timeout

    async def _get_id_token(self) -> str:
        """Get ID token for Cloud Run authentication."""
        credentials, _ = default()
        credentials.refresh(Request())
        return credentials.id_token

    async def extract_text(self, image_bytes: bytes) -> str:
        """Extract text from image using LightOnOCR.

        Args:
            image_bytes: PNG or JPEG image bytes

        Returns:
            Extracted text from the image
        """
        base64_image = base64.b64encode(image_bytes).decode("utf-8")

        # Detect content type
        content_type = "image/png" if image_bytes[:8] == b'\x89PNG\r\n\x1a\n' else "image/jpeg"

        payload = {
            "model": "lightonai/LightOnOCR-2-1B",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {
                        "url": f"data:{content_type};base64,{base64_image}"
                    }}
                ]
            }],
            "max_tokens": 4096
        }

        id_token = await self._get_id_token()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.service_url}/v1/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {id_token}"}
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
```

### Pattern 4: Service-to-Service Authentication
**What:** OIDC authentication between backend and GPU service
**When to use:** All requests from backend to GPU service
**Example:**
```python
# Source: https://cloud.google.com/run/docs/securing/service-identity
from google.auth.transport.requests import Request
from google.oauth2 import id_token

def get_auth_headers(target_audience: str) -> dict:
    """Get authorization headers for Cloud Run service.

    Args:
        target_audience: The GPU service URL

    Returns:
        Headers dict with Bearer token
    """
    token = id_token.fetch_id_token(Request(), target_audience)
    return {"Authorization": f"Bearer {token}"}
```

### Anti-Patterns to Avoid
- **Pre-downloading model to GCS then copying:** Use HuggingFace download at build time for simplicity (POC)
- **Custom batching logic:** Let vLLM handle batching automatically with defaults
- **Complex health checks:** Use simple TCP socket probe, vLLM provides /health endpoint
- **VPC complexity for POC:** Use service account authentication, not internal ingress

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Model serving | Custom Flask/FastAPI wrapper | vLLM OpenAI-compatible server | Production-grade, handles batching, memory management |
| Image preprocessing | Custom resize/format code | LightOnOCR handles it | Model optimized for various input sizes |
| Authentication | Custom token validation | google-auth library + Cloud Run IAM | Built-in OIDC, no token management |
| Cold start tracking | Custom metrics | Cloud Run built-in metrics | Available in Cloud Console |
| GPU memory management | Manual CUDA allocation | vLLM automatic management | vLLM optimizes GPU utilization |

**Key insight:** vLLM + Cloud Run GPU provides a turnkey solution. The POC should use defaults and built-in features rather than customizing.

## Common Pitfalls

### Pitfall 1: Insufficient Startup Probe Timeout
**What goes wrong:** Container killed before model loads
**Why it happens:** LightOnOCR model loading takes 30-60 seconds, default probes time out
**How to avoid:** Use `--startup-probe tcpSocket.port=8000,initialDelaySeconds=240,failureThreshold=1,timeoutSeconds=240,periodSeconds=240`
**Warning signs:** Container restarts repeatedly, "deadline exceeded" errors

### Pitfall 2: Missing transformers from Source
**What goes wrong:** Model fails to load with import errors
**Why it happens:** LightOnOCR-2-1B requires transformers features not in stable release
**How to avoid:** Add `pip install git+https://github.com/huggingface/transformers.git` to Dockerfile
**Warning signs:** "ModuleNotFoundError" or "AttributeError" during model loading

### Pitfall 3: External Traffic to Internal Service
**What goes wrong:** Backend cannot reach GPU service with internal ingress
**Why it happens:** Cloud Run to Cloud Run requires VPC egress for internal ingress
**How to avoid:** Use `--no-allow-unauthenticated` instead of `--ingress internal` for POC (simpler auth-based security)
**Warning signs:** 404 errors from backend to GPU service

### Pitfall 4: Cold Start OOM
**What goes wrong:** Container crashes during model loading
**Why it happens:** Model download + loading exceeds memory during initialization
**How to avoid:** Use 32Gi memory, download model at build time (not runtime)
**Warning signs:** "Killed" status, OOM errors in logs

### Pitfall 5: Wrong Image Format
**What goes wrong:** OCR returns garbled text or errors
**Why it happens:** Image not properly encoded or wrong content type
**How to avoid:** Use base64 encoding with correct data URI prefix (`data:image/png;base64,` or `data:image/jpeg;base64,`)
**Warning signs:** Model returns empty or nonsensical text

## Code Examples

Verified patterns from official sources:

### vLLM Health Check Test
```bash
# Source: vLLM docs - check if server is ready
curl -sf http://localhost:8000/health

# Check loaded models
curl -sf http://localhost:8000/v1/models | jq '.data[0].id'
# Expected: "lightonai/LightOnOCR-2-1B"
```

### OCR Request via curl
```bash
# Source: vLLM multimodal API docs
# Encode image to base64
IMAGE_B64=$(base64 -i document.png)

# Send OCR request
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"lightonai/LightOnOCR-2-1B\",
    \"messages\": [{
      \"role\": \"user\",
      \"content\": [{
        \"type\": \"image_url\",
        \"image_url\": {\"url\": \"data:image/png;base64,${IMAGE_B64}\"}
      }]
    }],
    \"max_tokens\": 4096
  }"
```

### Cloud Run Service Account Setup
```bash
# Source: Cloud Run service identity docs
PROJECT_ID=$(gcloud config get-value project)

# Create service account for GPU service
gcloud iam service-accounts create lightonocr-gpu \
  --display-name="LightOnOCR GPU Service"

SA_EMAIL="lightonocr-gpu@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant invoker role to backend service account
BACKEND_SA="backend-service@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud run services add-iam-policy-binding lightonocr-gpu \
  --member="serviceAccount:${BACKEND_SA}" \
  --role="roles/run.invoker" \
  --region=${REGION}
```

### Python Client with Retry
```python
# Source: Best practice for GPU service calls with cold starts
import httpx
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

class LightOnOCRClient:

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60)
    )
    async def extract_text(self, image_bytes: bytes) -> str:
        """Extract text with retry for cold start tolerance."""
        # ... implementation from Pattern 3
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Multi-stage OCR pipelines | End-to-end VLM OCR | LightOnOCR Oct 2025 | Single model, no pipeline complexity |
| Always-on GPU instances | Scale-to-zero Cloud Run GPU | Cloud Run GPU GA 2025 | Pay only when processing |
| Custom model serving | vLLM OpenAI-compatible | vLLM maturity 2024-2025 | Production-grade serving with minimal code |
| Quota pre-approval | Auto-grant 3 L4 GPUs | Cloud Run GPU GA | No wait for quota |

**Deprecated/outdated:**
- LightOnOCR-1B-1025: Superseded by LightOnOCR-2-1B with RLVR training (better accuracy)
- Manual GPU instance management: Cloud Run handles all infrastructure
- Complex batching configuration: vLLM defaults are well-optimized

## Open Questions

Things that couldn't be fully resolved:

1. **Exact Cold Start Time for LightOnOCR-2-1B on L4**
   - What we know: GPU instance starts in ~5 seconds, model loading varies (30-60s typical)
   - What's unclear: Total cold start with LightOnOCR-2-1B specifically on L4
   - Recommendation: Measure during deployment; tolerate up to 2 minutes for POC

2. **Optimal max_tokens for OCR**
   - What we know: LightOnOCR documentation uses 4096 in examples
   - What's unclear: Whether 4096 is sufficient for full-page dense documents
   - Recommendation: Start with 4096, increase if truncation observed

3. **Image Preprocessing Best Practices**
   - What we know: Target longest dimension 1540px, maintain aspect ratio
   - What's unclear: Whether vLLM/LightOnOCR handle resize automatically
   - Recommendation: Send original images initially; add resize if needed

## Sources

### Primary (HIGH confidence)
- [Cloud Run GPU Documentation](https://docs.cloud.google.com/run/docs/configuring/services/gpu) - GPU specs, requirements, pricing
- [vLLM Cloud Run Tutorial](https://cloud.google.com/run/docs/tutorials/gpu-gemma2-with-vllm) - Deployment pattern, Dockerfile, gcloud commands
- [Google Codelabs vLLM GPU](https://codelabs.developers.google.com/codelabs/how-to-run-inference-cloud-run-gpu-vllm) - Complete deployment walkthrough
- [LightOnOCR-2-1B Model Card](https://huggingface.co/lightonai/LightOnOCR-2-1B) - Model specs, vLLM flags, requirements
- [vLLM OpenAI-Compatible Server](https://docs.vllm.ai/en/stable/serving/openai_compatible_server/) - API format, multimodal inputs
- [Cloud Run Service Identity](https://docs.cloud.google.com/run/docs/configuring/services/service-identity) - Service account setup

### Secondary (MEDIUM confidence)
- [Cloud Run GPUs GA Blog](https://cloud.google.com/blog/products/serverless/cloud-run-gpus-are-now-generally-available) - GA announcement, auto-grant quota
- [Scale-to-Zero vLLM Article](https://medium.com/google-cloud/scale-to-zero-llm-inference-with-vllm-cloud-run-and-cloud-storage-fuse-42c7e62f6ec6) - Scale-to-zero patterns
- [vLLM GitHub Readiness Probes](https://github.com/vllm-project/vllm/issues/6073) - Health endpoint behavior

### Tertiary (LOW confidence)
- Cold start time estimates (varies by model size, hardware)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official Google Cloud and vLLM documentation with specific commands
- Architecture patterns: HIGH - Google Codelabs provides complete working examples
- Pitfalls: HIGH - Based on documented requirements and common issues
- Client implementation: MEDIUM - Follows standard patterns, not tested

**Research date:** 2026-01-25
**Valid until:** 2026-02-25 (30 days - stable infrastructure, model versions may update)

## Phase 13 Requirements Mapping

| Requirement | Research Finding | Confidence |
|-------------|------------------|------------|
| LOCR-01: L4 GPU 24GB | Cloud Run supports L4 with 24GB VRAM, auto-granted quota | HIGH |
| LOCR-02: vLLM for LightOnOCR-2-1B | vLLM v0.11.2+ supports model, transformers from source required | HIGH |
| LOCR-03: 4 vCPU, 16 GiB minimum | Documented minimum, recommend 8 vCPU / 32 GiB for model | HIGH |
| LOCR-04: Scale to zero | `--min-instances=0` supported, standard pattern | HIGH |
| LOCR-06: HTTP client in backend | OIDC auth + httpx async client pattern documented | HIGH |
| LOCR-07: Internal authentication | Service account + run.invoker role pattern | HIGH |
| LOCR-08: Cold start monitoring | Cloud Run built-in metrics (POC uses defaults) | MEDIUM |
| LOCR-10: vLLM batching | Use vLLM defaults (per CONTEXT.md POC decisions) | HIGH |
| LOCR-12: OCR quality metrics | Basic logging (per CONTEXT.md POC decisions) | MEDIUM |
