# Stack Research: Loan Document Extraction System v2.0

**Domain:** LLM-powered document extraction for financial/loan documents
**Researched:** 2026-01-24
**Confidence:** HIGH (verified with official sources)
**Scope:** v2.0 additions - LangExtract, LightOnOCR GPU service, CloudBuild deployment

---

## Executive Summary

v2.0 adds three major stack components to the existing Docling + Gemini pipeline:

1. **LangExtract** (v1.1.1) - Google's source-grounded extraction library with character-level offsets, replacing/augmenting the native Gemini structured output approach for precise attribution
2. **LightOnOCR-2-1B** - State-of-the-art OCR model (1B params) for scanned documents, deployed as a separate Cloud Run GPU service
3. **CloudBuild + gcloud CLI** - Replaces Terraform for infrastructure deployment with native GCP tooling

**Key insight:** LangExtract provides character-level source grounding that our current Gemini implementation lacks. LightOnOCR-2-1B delivers superior OCR quality for degraded scans (outperforms all competitors on OlmOCR-Bench at 83.2%). CloudBuild simplifies deployment without sacrificing reproducibility.

---

## v2.0 Stack Additions

### LangExtract - Source-Grounded Extraction

| Attribute | Value |
|-----------|-------|
| **Package** | `langextract` |
| **Version** | 1.1.1 (Nov 2025) |
| **Python** | >=3.10 |
| **License** | Apache 2.0 |
| **Source** | [github.com/google/langextract](https://github.com/google/langextract) |

**Why LangExtract over native Gemini structured output:**
- **Character-level offsets**: Every extracted field maps to exact `(start_char, end_char)` in source text
- **Interactive visualization**: Generates self-contained HTML for review with highlighted source spans
- **Long-document handling**: Built-in chunking strategy with parallel processing for recall optimization
- **Few-shot schema definition**: Define extraction via examples, not just Pydantic models
- **Multi-pass extraction**: Configurable passes over smaller contexts for higher recall

**Recommended Gemini model for LangExtract:**
```python
model_id="gemini-2.5-flash"  # Best speed-cost-quality balance
# or "gemini-2.5-pro" for complex reasoning tasks
```

**Integration with existing stack:**
- Complements (not replaces) current Docling + Gemini pipeline
- API endpoint parameter selects extraction method: `?method=docling` vs `?method=langextract`
- Both methods store to same PostgreSQL schema with enhanced source attribution

### LightOnOCR-2-1B - GPU OCR Service

| Attribute | Value |
|-----------|-------|
| **Model** | `lightonai/LightOnOCR-2-1B` |
| **Parameters** | 1B |
| **Tensor Type** | BF16 |
| **Performance** | 83.2 on OlmOCR-Bench (SOTA) |
| **Speed** | 5.71 pages/sec on H100 |
| **License** | Apache 2.0 |
| **Source** | [huggingface.co/lightonai/LightOnOCR-2-1B](https://huggingface.co/lightonai/LightOnOCR-2-1B) |

**Why LightOnOCR-2-1B:**
- **Best-in-class accuracy**: Outperforms Chandra-9B (9x larger), DeepSeek OCR, PaddleOCR-VL
- **Scanned document specialty**: Trained on 16M+ annotated pages including old scans, math, tables
- **End-to-end model**: No brittle OCR pipeline - direct image-to-text with natural ordering
- **Cost-effective**: <$0.01 per 1,000 pages at H100 speeds

**Model variants:**
| Variant | Use Case |
|---------|----------|
| `LightOnOCR-2-1B` | Default OCR-only - best for clean transcription |
| `LightOnOCR-2-1B-bbox` | Outputs text + bounding boxes for figures/images |
| `LightOnOCR-2-1B-bbox-soup` | Merged checkpoint - balanced OCR + bbox |

**Deployment architecture:**
- Separate Cloud Run service with L4 GPU
- Called by main backend when `ocr_mode=force` or `ocr_mode=auto` detects scanned document
- Returns plain text that feeds into LangExtract/Gemini extraction

### Cloud Run GPU (L4) Requirements

| Requirement | Value |
|-------------|-------|
| **GPU Type** | nvidia-l4 (NVIDIA L4, 24GB VRAM) |
| **Min CPU** | 4 vCPUs |
| **Min Memory** | 16 GiB |
| **Recommended** | 8 vCPUs, 32 GiB |
| **Pre-installed Driver** | NVIDIA 535.216.03 (CUDA 12.2) |
| **Cold Start** | ~5 seconds (GPU ready) |
| **Model Load** | ~19 seconds (Time-to-First-Token for 4B model) |

**Available regions:**
- us-central1 (Iowa) - recommended
- us-east4 (Northern Virginia)
- europe-west1 (Belgium)
- europe-west4 (Netherlands)
- asia-southeast1 (Singapore)
- asia-south1 (Mumbai, invitation-only)

**Quota:** 3 GPUs automatically granted per region on first deployment (no request needed).

### CloudBuild Deployment Stack

| Component | Purpose |
|-----------|---------|
| **cloudbuild.yaml** | Build configuration - replaces Terraform provisioning |
| **gcloud run deploy** | Service deployment command |
| **Artifact Registry** | Container image storage |
| **Secret Manager** | API keys, credentials |

**Why CloudBuild over Terraform:**
- **Native GCP integration**: No external tooling dependencies
- **Simpler for Cloud Run**: Direct `gcloud run deploy` vs Terraform state management
- **Built-in CI/CD**: GitHub triggers, automatic builds on push
- **Cost**: No state storage costs, no Terraform Cloud fees
- **Speed**: Faster iteration for Cloud Run deployments

**What Terraform did that CloudBuild handles differently:**
| Terraform Resource | CloudBuild Equivalent |
|--------------------|-----------------------|
| Cloud Run Service | `gcloud run deploy` in cloudbuild.yaml |
| Cloud SQL | Pre-created via console or one-time gcloud script |
| Cloud Storage bucket | Pre-created via console or one-time gcloud script |
| IAM bindings | `gcloud projects add-iam-policy-binding` |
| Service accounts | `gcloud iam service-accounts create` |
| Secrets | `gcloud secrets create` |

**Migration approach:** Keep infrastructure (Cloud SQL, VPC, etc.) as one-time gcloud scripts. Use CloudBuild only for application deployment. This hybrid approach avoids re-provisioning costs while simplifying the deployment pipeline.

---

## Installation - v2.0 Additions

### Backend - New Dependencies

```bash
# LangExtract for source-grounded extraction
pip install langextract>=1.1.1

# LightOnOCR service dependencies (separate requirements for GPU service)
pip install \
    pillow>=10.0.0 \
    pypdfium2>=4.0.0

# Transformers from source (required for LightOnOCR model class)
pip install git+https://github.com/huggingface/transformers

# Optional: vLLM for optimized inference
pip install vllm>=0.11.0
```

### LightOnOCR GPU Service - Dockerfile

```dockerfile
FROM vllm/vllm-openai:v0.11.0

# Or for custom deployment without vLLM:
# FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

ENV HF_HOME=/model-cache
ENV HF_HUB_OFFLINE=1

# Download model at build time for faster cold starts
RUN --mount=type=secret,id=HF_TOKEN HF_TOKEN=$(cat /run/secrets/HF_TOKEN) \
    huggingface-cli download lightonai/LightOnOCR-2-1B

# For vLLM serving:
ENTRYPOINT python3 -m vllm.entrypoints.openai.api_server \
    --port ${PORT:-8000} \
    --model lightonai/LightOnOCR-2-1B \
    --gpu-memory-utilization 0.85 \
    --max-num-seqs 64 \
    --max-model-len 4096 \
    --limit-mm-per-prompt '{"image": 1}'
```

### CloudBuild Configuration

```yaml
# cloudbuild.yaml - Main backend service
steps:
  # Build the backend image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', '${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPO}/backend:${SHORT_SHA}', './backend']

  # Push to Artifact Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', '${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPO}/backend:${SHORT_SHA}']

  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'loan-extraction-backend'
      - '--image=${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPO}/backend:${SHORT_SHA}'
      - '--region=${_REGION}'
      - '--platform=managed'
      - '--allow-unauthenticated'
      - '--cpu=2'
      - '--memory=4Gi'
      - '--set-env-vars=DATABASE_URL=${_DATABASE_URL}'

substitutions:
  _REGION: us-central1
  _REPO: loan-extraction

options:
  logging: CLOUD_LOGGING_ONLY
```

```yaml
# cloudbuild-ocr.yaml - LightOnOCR GPU service
steps:
  # Build OCR service image with model baked in
  - name: 'gcr.io/cloud-builders/docker'
    id: build
    entrypoint: 'bash'
    secretEnv: ['HF_TOKEN']
    args:
      - -c
      - |
        SECRET_TOKEN="$$HF_TOKEN" docker buildx build \
          --tag=${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPO}/ocr:${SHORT_SHA} \
          --secret id=HF_TOKEN \
          -f ./services/ocr/Dockerfile \
          ./services/ocr

  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', '${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPO}/ocr:${SHORT_SHA}']

  # Deploy with GPU
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'beta'
      - 'run'
      - 'deploy'
      - 'loan-extraction-ocr'
      - '--image=${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPO}/ocr:${SHORT_SHA}'
      - '--region=${_REGION}'
      - '--platform=managed'
      - '--no-allow-unauthenticated'
      - '--cpu=8'
      - '--memory=32Gi'
      - '--gpu=1'
      - '--gpu-type=nvidia-l4'
      - '--max-instances=3'
      - '--no-cpu-throttling'
      - '--startup-probe=tcpSocket.port=8000,initialDelaySeconds=120,failureThreshold=3,timeoutSeconds=60,periodSeconds=30'

availableSecrets:
  secretManager:
    - versionName: 'projects/${PROJECT_ID}/secrets/HF_TOKEN/versions/latest'
      env: 'HF_TOKEN'

substitutions:
  _REGION: us-central1
  _REPO: loan-extraction

options:
  machineType: 'E2_HIGHCPU_32'
  logging: CLOUD_LOGGING_ONLY
```

---

## Configuration Examples

### LangExtract with Few-Shot Examples

```python
import langextract as lx
from typing import TypedDict

# Define extraction schema via examples
class LoanBorrowerExtraction(TypedDict):
    name: str
    ssn_last4: str
    address: str
    employer: str
    annual_income: float
    loan_amount: float

# Few-shot examples define the schema
examples = [
    lx.data.ExampleData(
        text="John Smith (SSN: ***-**-1234) residing at 123 Main St...",
        extractions=[
            lx.data.Extraction(
                class_name="LoanBorrower",
                attributes={
                    "name": "John Smith",
                    "ssn_last4": "1234",
                    "address": "123 Main St",
                }
            )
        ]
    )
]

# Extract with source grounding
result = lx.extract(
    text_or_documents=document_text,
    prompt_description="Extract borrower information from loan documents",
    examples=examples,
    model_id="gemini-2.5-flash",
    extraction_passes=2,  # Multi-pass for recall
    max_workers=4,  # Parallel processing
)

# Each extraction includes character offsets
for extraction in result.extractions:
    print(f"{extraction.class_name}: {extraction.attributes}")
    print(f"  Source: chars {extraction.start_offset}-{extraction.end_offset}")

# Generate interactive visualization
lx.visualize(result, output_path="extraction_review.html")
```

### LightOnOCR Inference (Direct)

```python
import torch
from transformers import LightOnOcrForConditionalGeneration, LightOnOcrProcessor
from PIL import Image

device = "cuda" if torch.cuda.is_available() else "cpu"
dtype = torch.bfloat16 if device == "cuda" else torch.float32

model = LightOnOcrForConditionalGeneration.from_pretrained(
    "lightonai/LightOnOCR-2-1B",
    torch_dtype=dtype
).to(device)
processor = LightOnOcrProcessor.from_pretrained("lightonai/LightOnOCR-2-1B")

def ocr_document_page(image_path: str) -> str:
    """Extract text from a document image."""
    image = Image.open(image_path)

    conversation = [{"role": "user", "content": [{"type": "image", "url": image_path}]}]
    inputs = processor.apply_chat_template(
        conversation,
        add_generation_prompt=True,
        tokenize=True,
        return_tensors="pt"
    )
    inputs = {
        k: v.to(device=device, dtype=dtype) if v.is_floating_point() else v.to(device)
        for k, v in inputs.items()
    }

    output_ids = model.generate(**inputs, max_new_tokens=4096)
    generated_ids = output_ids[0, inputs["input_ids"].shape[1]:]
    return processor.decode(generated_ids, skip_special_tokens=True)
```

### LightOnOCR via vLLM (Recommended for Production)

```python
import httpx
import base64
from pathlib import Path

async def ocr_via_vllm(image_path: str, ocr_service_url: str) -> str:
    """Call LightOnOCR service deployed on Cloud Run with vLLM."""
    image_bytes = Path(image_path).read_bytes()
    image_b64 = base64.b64encode(image_bytes).decode()

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{ocr_service_url}/v1/chat/completions",
            json={
                "model": "lightonai/LightOnOCR-2-1B",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
                        ]
                    }
                ],
                "max_tokens": 4096,
            }
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
```

### CloudBuild Deployment Commands

```bash
# One-time infrastructure setup (replaces Terraform)
./infrastructure/scripts/setup-gcp.sh

# Deploy backend (triggered by push or manual)
gcloud builds submit --config=cloudbuild.yaml --region=us-central1

# Deploy OCR GPU service
gcloud builds submit --config=cloudbuild-ocr.yaml --region=us-central1

# Manual deploy with local image
gcloud run deploy loan-extraction-backend \
  --image=us-central1-docker.pkg.dev/$PROJECT_ID/loan-extraction/backend:latest \
  --region=us-central1 \
  --platform=managed

# Deploy OCR with GPU
gcloud beta run deploy loan-extraction-ocr \
  --image=us-central1-docker.pkg.dev/$PROJECT_ID/loan-extraction/ocr:latest \
  --region=us-central1 \
  --gpu=1 \
  --gpu-type=nvidia-l4 \
  --cpu=8 \
  --memory=32Gi \
  --max-instances=3 \
  --no-cpu-throttling
```

---

## Version Compatibility Matrix - v2.0 Additions

| Package | Version | Requires | Notes |
|---------|---------|----------|-------|
| langextract | 1.1.1 | Python >=3.10 | Google's extraction library |
| transformers | source | Python >=3.9 | Required from git for LightOnOCR model class |
| vllm | 0.11.0+ | CUDA 12.x | For optimized LightOnOCR serving |
| pillow | 10.0.0+ | - | Image processing for OCR |
| pypdfium2 | 4.0.0+ | - | PDF to image conversion |

**LightOnOCR Model Requirements:**
- GPU: 6-8 GB VRAM minimum for 1B model in BF16 (~2GB weights + overhead)
- L4 GPU (24GB) provides ample headroom for batching and context

**Transformers Compatibility Warning:**
As of Jan 2026, `LightOnOcrForConditionalGeneration` and `LightOnOcrProcessor` require transformers installed from source:
```bash
pip install git+https://github.com/huggingface/transformers
```
This is expected to be in transformers v4.58+ when released.

---

## Existing Stack (Unchanged from v1.0)

### Core Technologies (No Changes)

| Technology | Version | Purpose |
|------------|---------|---------|
| **Docling** | 2.70.0 | Document parsing - KEPT for non-LangExtract path |
| **google-genai** | 1.60.0 | Gemini API client |
| **FastAPI** | 0.128.0 | REST API framework |
| **SQLAlchemy** | 2.0.46 | ORM with async support |
| **asyncpg** | 0.31.0 | Async PostgreSQL driver |
| **Pydantic** | 2.12.5 | Data validation |
| **Next.js** | 15.x | Frontend framework |

### GCP Infrastructure (Unchanged)

| Service | Purpose |
|---------|---------|
| **Cloud Run** | Serverless compute (now with GPU option for OCR) |
| **Cloud SQL** | PostgreSQL database |
| **Cloud Storage** | Document storage |
| **Cloud Tasks** | Async job queue |
| **Secret Manager** | Secrets storage |

---

## What NOT to Add

| Avoid | Why | What to Do Instead |
|-------|-----|-------------------|
| **Terraform for v2.0** | Adds complexity for Cloud Run-only deployments | CloudBuild + gcloud scripts |
| **Custom OCR pipeline** | LightOnOCR is end-to-end, no Tesseract/PyMuPDF needed | Use LightOnOCR model directly |
| **LangChain** | LangExtract is lighter, purpose-built for extraction | Use langextract directly |
| **Multiple GPU types** | L4 is optimal for 1B model size | Standardize on nvidia-l4 |
| **Always-on GPU instances** | Expensive for sporadic usage | Use scale-to-zero with min_instances=0 |
| **Self-hosted model fine-tuning** | Out of scope; LightOnOCR works well out-of-box | Use pre-trained model |

---

## Cost Analysis - v2.0 Additions

### LangExtract (uses Gemini)

Same as existing Gemini costs - LangExtract is a wrapper, not a separate service.

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| gemini-2.5-flash | $0.075 | $0.30 |
| gemini-2.5-pro | $1.25 | $5.00 |

### LightOnOCR on Cloud Run GPU

| Resource | Cost | Notes |
|----------|------|-------|
| L4 GPU | $0.51/hour | While instance running |
| 8 vCPU | $0.06/hour | Required minimum with GPU |
| 32 GB RAM | $0.004/hour | Required minimum with GPU |
| **Total** | ~$0.58/hour | Scale-to-zero when idle |

**Per-page cost (at 5.71 pages/sec):**
- 1 hour = 20,556 pages
- Cost per 1,000 pages: ~$0.028
- Compare to external OCR APIs: $0.50-2.00 per 1,000 pages

### CloudBuild

| Resource | Cost | Notes |
|----------|------|-------|
| Build minutes | $0.003/min (E2) | ~5 min per build |
| Per deployment | ~$0.015 | Negligible |

---

## Sources

### HIGH Confidence (Official Documentation)

- [LangExtract GitHub](https://github.com/google/langextract) - v1.1.1, Apache 2.0
- [LangExtract PyPI](https://pypi.org/project/langextract/) - v1.1.1, Python >=3.10
- [LightOnOCR-2-1B HuggingFace](https://huggingface.co/lightonai/LightOnOCR-2-1B) - Model card, usage
- [Cloud Run GPU Docs](https://docs.cloud.google.com/run/docs/configuring/services/gpu) - L4 configuration
- [CloudBuild Deploy to Cloud Run](https://docs.cloud.google.com/build/docs/deploying-builds/deploy-cloud-run) - Configuration
- [vLLM Cloud Run Codelab](https://codelabs.developers.google.com/codelabs/how-to-run-inference-cloud-run-gpu-vllm) - GPU deployment patterns

### MEDIUM Confidence (Verified with Multiple Sources)

- [LangExtract Blog](https://developers.googleblog.com/introducing-langextract-a-gemini-powered-information-extraction-library/) - Feature overview
- [LightOnOCR Paper](https://arxiv.org/abs/2601.14251) - Architecture, benchmarks
- [Cloud Run GPU GA Blog](https://cloud.google.com/blog/products/serverless/cloud-run-gpus-are-now-generally-available) - L4 availability
- [Transformers Releases](https://github.com/huggingface/transformers/releases) - v4.57.6 latest stable

### LOW Confidence (Community Sources - Verify Before Use)

- LightOnOCR GPU memory estimates for L4 (extrapolated from H100 benchmarks)
- Cold start times vary by model size and container configuration
- vLLM optimization settings may need tuning for LightOnOCR specifically

---

*Stack research for: Loan Document Extraction System v2.0*
*Researched: 2026-01-24*
*Confidence: HIGH*
