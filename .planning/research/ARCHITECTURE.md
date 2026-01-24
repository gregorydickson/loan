# Architecture Research: v2.0 LangExtract + LightOnOCR Integration

**Domain:** Document extraction pipeline enhancement
**Researched:** 2026-01-24
**Confidence:** HIGH (verified with official docs and existing codebase)

## Executive Summary

This document details the architecture for integrating LangExtract and LightOnOCR into the existing loan document extraction system. The v2.0 milestone adds:

1. **LangExtract** - Google's extraction library with character-level source grounding
2. **LightOnOCR** - Dedicated GPU Cloud Run service for high-quality OCR
3. **Dual extraction pipeline** - Docling and LangExtract coexisting with API selection
4. **CloudBuild deployment** - Replacing Terraform with gcloud CLI scripts

The architecture maintains backward compatibility while enabling enhanced extraction capabilities.

---

## System Overview

### Current v1.0 Architecture (Reference)

```
                              Upload Request
                                    |
                                    v
+------------------------------------------------------------------+
|                        Cloud Run Backend                          |
|  +------------------+    +------------------+    +--------------+ |
|  | /api/documents   |--->| DocumentService  |--->| GCS Client   | |
|  | (upload endpoint)|    |                  |    | (upload)     | |
|  +------------------+    +------------------+    +--------------+ |
|                                    |                              |
|                                    v                              |
|                          +------------------+                     |
|                          | Cloud Tasks      |                     |
|                          | (queue task)     |                     |
|                          +------------------+                     |
+------------------------------------------------------------------+
                                    |
                                    v
+------------------------------------------------------------------+
|                   Cloud Tasks Handler (async)                     |
|  +------------------+    +------------------+    +--------------+ |
|  | /api/tasks/      |--->| DoclingProcessor |--->| Borrower     | |
|  | process-document |    | (text extraction)|    | Extractor    | |
|  +------------------+    +------------------+    | (LLM)        | |
|                                                  +--------------+ |
|                                                        |          |
|                                                        v          |
|                                                  +--------------+ |
|                                                  | PostgreSQL   | |
|                                                  | (persist)    | |
|                                                  +--------------+ |
+------------------------------------------------------------------+
```

### v2.0 Architecture (Dual Pipeline + OCR Service)

```
                              Upload Request
                      ?method=docling|langextract
                         ?ocr=auto|force|skip
                                    |
                                    v
+------------------------------------------------------------------+
|                        Cloud Run Backend                          |
|  +------------------+    +------------------+                     |
|  | /api/documents   |--->| ExtractionRouter |----+                |
|  | (upload endpoint)|    | (method select)  |    |                |
|  +------------------+    +------------------+    |                |
|                                    |             |                |
|                                    v             v                |
|                          +------------------+  +-------------+    |
|                          | Cloud Tasks      |  | OCR Router  |    |
|                          | (queue task)     |  | (ocr param) |    |
|                          +------------------+  +-------------+    |
+------------------------------------------------------------------+
           |                                            |
           |                                            v
           |                               +------------------------+
           |                               | Cloud Run OCR Service  |
           |                               | (L4 GPU - optional)    |
           |                               | +--------------------+ |
           |                               | | LightOnOCR-2-1B    | |
           |                               | | (1B param model)   | |
           |                               | +--------------------+ |
           |                               +------------------------+
           |                                            |
           v                                            v
+------------------------------------------------------------------+
|                   Cloud Tasks Handler (async)                     |
|  +-----------------------------------------------------------------+
|  |                    Extraction Method Router                     |
|  +-----------------------------------------------------------------+
|       |                                               |            |
|       v                                               v            |
|  +------------------+                    +------------------+      |
|  | DOCLING PATH     |                    | LANGEXTRACT PATH |      |
|  | DoclingProcessor |                    | LangExtract      |      |
|  | + BorrowerExtract|                    | + Gemini 2.5     |      |
|  | (page+snippet)   |                    | (char offsets)   |      |
|  +------------------+                    +------------------+      |
|       |                                               |            |
|       v                                               v            |
|  +------------------+                    +------------------+      |
|  | SourceReference  |                    | SourceReference  |      |
|  | - page_number    |                    | - page_number    |      |
|  | - snippet        |                    | - snippet        |      |
|  | - (no offsets)   |                    | - char_start     |      |
|  +------------------+                    | - char_end       |      |
|                                          +------------------+      |
|                      |                              |              |
|                      +-------------+----------------+              |
|                                    |                               |
|                                    v                               |
|                          +------------------+                      |
|                          | PostgreSQL       |                      |
|                          | (unified storage)|                      |
|                          +------------------+                      |
+------------------------------------------------------------------+
```

---

## Component Responsibilities

### New Components

| Component | Responsibility | Integration Point |
|-----------|----------------|-------------------|
| **ExtractionRouter** | Dispatch to Docling or LangExtract based on `?method` param | DocumentService |
| **LangExtractProcessor** | LangExtract API wrapper with few-shot examples | Parallel to DoclingProcessor |
| **OCRRouter** | Decide when to invoke LightOnOCR preprocessing | Before extraction |
| **LightOnOCRClient** | HTTP client for GPU OCR service | Called by OCRRouter |
| **LightOnOCR Service** | Standalone Cloud Run GPU service | Separate deployment |

### Modified Components

| Component | Modification | Reason |
|-----------|--------------|--------|
| **DocumentService** | Add `extraction_method` and `ocr_mode` params | Support dual pipeline |
| **SourceReference** | Add `char_start`, `char_end` nullable columns | Character offset storage |
| **CloudTasksClient** | Add method/ocr params to task payload | Route in async handler |
| **tasks.py** | Branch extraction logic by method | Dual pipeline execution |
| **config.py** | Add OCR service URL config | Service discovery |

### Unchanged Components

| Component | Reason |
|-----------|--------|
| **DoclingProcessor** | Continues to work exactly as before |
| **BorrowerExtractor** | Used by Docling path only |
| **GCSClient** | Shared by both paths |
| **PostgreSQL models** | Extended, not replaced |

---

## Data Flow

### Flow 1: Docling Path (Default, Backward Compatible)

```
Request: POST /api/documents/?method=docling&ocr=skip
                    |
                    v
1. DocumentService.upload()
   - Validate file
   - Hash check
   - Upload to GCS
   - Create Document record (PENDING)
   - Queue Cloud Task with method=docling
                    |
                    v
2. Cloud Task Handler (process_document)
   - Download from GCS
   - DoclingProcessor.process_bytes()
   - BorrowerExtractor.extract()
   - Persist borrowers with SourceReference
     (page_number, snippet, no char offsets)
   - Update Document status = COMPLETED
```

### Flow 2: LangExtract Path (New, Character Offsets)

```
Request: POST /api/documents/?method=langextract&ocr=auto
                    |
                    v
1. DocumentService.upload()
   - Validate file
   - Hash check
   - Upload to GCS
   - Create Document record (PENDING)
   - Queue Cloud Task with method=langextract, ocr=auto
                    |
                    v
2. Cloud Task Handler (process_document)
   - Download from GCS
   - IF ocr=auto or ocr=force:
       - Check if scanned (image-based PDF)
       - Call LightOnOCR service for text extraction
       - Store OCR text as document_text
   - LangExtractProcessor.extract()
       - Build few-shot examples from examples/
       - Call lx.extract() with Gemini 2.5 Flash
       - Get extractions with character offsets
   - Persist borrowers with SourceReference
     (page_number, snippet, char_start, char_end)
   - Update Document status = COMPLETED
```

### Flow 3: OCR Preprocessing (Optional)

```
Document Type Detection:
                    |
                    v
+-------------------+-------------------+
| Scanned/Image PDF |   Native Text PDF |
+-------------------+-------------------+
        |                    |
        v                    v
   Call OCR Service      Skip OCR
   (LightOnOCR)          (use Docling/
        |                 LangExtract directly)
        v
   Store OCR text
   in document record
        |
        v
   Continue to extraction
```

---

## API Changes

### Upload Endpoint Enhancement

```python
@router.post("/")
async def upload_document(
    file: UploadFile,
    service: DocumentServiceDep,
    method: Literal["docling", "langextract"] = Query(
        default="docling",
        description="Extraction method: docling (v1, page+snippet) or langextract (v2, char offsets)"
    ),
    ocr: Literal["auto", "force", "skip"] = Query(
        default="skip",
        description="OCR mode: auto (detect scanned), force (always OCR), skip (no OCR)"
    ),
) -> DocumentUploadResponse:
    """Upload document with extraction method selection."""
```

### API Decision Logic

| Parameter | Value | Behavior |
|-----------|-------|----------|
| `method=docling` | Default | Use Docling + BorrowerExtractor (v1 path) |
| `method=langextract` | New | Use LangExtract + Gemini 2.5 (v2 path) |
| `ocr=skip` | Default | No OCR preprocessing (faster) |
| `ocr=auto` | New | Detect if scanned, OCR if needed |
| `ocr=force` | New | Always preprocess with OCR |

### Cloud Tasks Payload Enhancement

```python
class ProcessDocumentRequest(BaseModel):
    document_id: UUID
    filename: str
    extraction_method: Literal["docling", "langextract"] = "docling"
    ocr_mode: Literal["auto", "force", "skip"] = "skip"
```

---

## Database Schema Changes

### SourceReference Table Enhancement

```sql
-- Migration: Add character offset columns
ALTER TABLE source_references
ADD COLUMN char_start INTEGER NULL,
ADD COLUMN char_end INTEGER NULL;

-- Index for offset-based queries
CREATE INDEX ix_source_references_char_range
ON source_references (document_id, char_start, char_end)
WHERE char_start IS NOT NULL;
```

### SQLAlchemy Model Update

```python
class SourceReference(Base):
    __tablename__ = "source_references"

    # ... existing columns ...

    # NEW: Character-level offset for precise grounding
    char_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

### Document Table Enhancement

```sql
-- Track extraction method used
ALTER TABLE documents
ADD COLUMN extraction_method VARCHAR(20) DEFAULT 'docling',
ADD COLUMN ocr_processed BOOLEAN DEFAULT FALSE;
```

---

## LangExtract Integration Pattern

### LangExtractProcessor Class

```python
# src/extraction/langextract_processor.py
import langextract as lx
from pathlib import Path
from uuid import UUID

class LangExtractProcessor:
    """LangExtract-based borrower extraction with character offsets."""

    def __init__(
        self,
        examples_dir: Path = Path("examples/loan_extraction"),
        model_id: str = "gemini-2.5-flash",
    ):
        self.model_id = model_id
        self.examples = self._load_examples(examples_dir)
        self.prompt = self._build_prompt()

    def _load_examples(self, examples_dir: Path) -> list[lx.data.ExampleData]:
        """Load few-shot examples from examples directory."""
        examples = []
        for example_file in examples_dir.glob("*.json"):
            # Load example text and expected extractions
            # Format: {"text": "...", "extractions": [...]}
            ...
        return examples

    def _build_prompt(self) -> str:
        return """
        Extract borrower information from loan documents.
        For each borrower, extract:
        - Full name
        - SSN (if present)
        - Phone number
        - Email
        - Address (street, city, state, zip)
        - Income records (amount, period, year, source, employer)
        - Account numbers
        - Loan numbers

        Map each extraction to its exact location in the source text.
        """

    def extract(
        self,
        text: str,
        document_id: UUID,
        document_name: str,
    ) -> ExtractionResult:
        """Extract borrowers with character-level offsets."""
        result = lx.extract(
            text_or_documents=text,
            prompt_description=self.prompt,
            examples=self.examples,
            model_id=self.model_id,
            max_char_buffer=2000,  # Context window around extractions
            extraction_passes=2,   # Multiple passes for recall
        )

        # Convert LangExtract result to BorrowerRecord
        borrowers = []
        for extraction in result.extractions:
            borrower = self._convert_extraction(
                extraction,
                document_id,
                document_name,
            )
            borrowers.append(borrower)

        return ExtractionResult(
            borrowers=borrowers,
            extraction_method="langextract",
        )

    def _convert_extraction(
        self,
        extraction: lx.data.Extraction,
        document_id: UUID,
        document_name: str,
    ) -> BorrowerRecord:
        """Convert LangExtract extraction to BorrowerRecord with offsets."""
        # LangExtract provides char_start, char_end for each field
        sources = [
            SourceReference(
                document_id=document_id,
                document_name=document_name,
                page_number=self._offset_to_page(extraction.char_start),
                snippet=extraction.source_text[:200],
                char_start=extraction.char_start,
                char_end=extraction.char_end,
            )
        ]

        return BorrowerRecord(
            name=extraction.fields.get("name"),
            # ... map other fields ...
            sources=sources,
        )
```

### Few-Shot Example Structure

```json
// examples/loan_extraction/example_001.json
{
  "text": "BORROWER INFORMATION\n\nName: John Michael Smith\nSSN: 123-45-6789\nAddress: 456 Oak Street, Austin, TX 78701\n\nEMPLOYMENT\nEmployer: TechCorp Inc.\nAnnual Salary: $85,000",
  "extractions": [
    {
      "type": "borrower",
      "fields": {
        "name": "John Michael Smith",
        "ssn": "123-45-6789",
        "address": {
          "street": "456 Oak Street",
          "city": "Austin",
          "state": "TX",
          "zip": "78701"
        },
        "income": {
          "amount": 85000,
          "period": "annual",
          "employer": "TechCorp Inc."
        }
      },
      "char_start": 24,
      "char_end": 53
    }
  ]
}
```

---

## LightOnOCR Service Architecture

### Standalone GPU Service

```yaml
# cloud-run-ocr-service.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: loan-ocr-service
spec:
  template:
    metadata:
      annotations:
        run.googleapis.com/execution-environment: gen2
        autoscaling.knative.dev/minScale: "0"
        autoscaling.knative.dev/maxScale: "3"
    spec:
      containerConcurrency: 1  # OCR is memory-intensive
      timeoutSeconds: 300
      containers:
        - image: us-central1-docker.pkg.dev/PROJECT/loan-repo/ocr-service:latest
          resources:
            limits:
              cpu: "8"
              memory: "32Gi"
              nvidia.com/gpu: "1"
          env:
            - name: MODEL_ID
              value: "lightonai/LightOnOCR-2-1B"
      nodeSelector:
        run.googleapis.com/accelerator: nvidia-l4
```

### OCR Service API

```python
# ocr_service/main.py
from fastapi import FastAPI, UploadFile
from transformers import LightOnOcrForConditionalGeneration, LightOnOcrProcessor
import torch

app = FastAPI(title="LightOnOCR Service")

# Load model at startup (cold start ~5s with pre-installed drivers)
device = "cuda" if torch.cuda.is_available() else "cpu"
dtype = torch.bfloat16 if device == "cuda" else torch.float32

model = LightOnOcrForConditionalGeneration.from_pretrained(
    "lightonai/LightOnOCR-2-1B",
    torch_dtype=dtype,
).to(device)
processor = LightOnOcrProcessor.from_pretrained("lightonai/LightOnOCR-2-1B")

@app.post("/ocr")
async def ocr_document(file: UploadFile) -> dict:
    """Process document with LightOnOCR."""
    content = await file.read()

    # Convert PDF pages to images
    images = convert_pdf_to_images(content, max_dimension=1540)

    # Process each page
    pages = []
    for i, image in enumerate(images):
        text = process_image(image)
        pages.append({"page_number": i + 1, "text": text})

    return {
        "pages": pages,
        "full_text": "\n\n".join(p["text"] for p in pages),
    }

def process_image(image) -> str:
    """OCR a single image."""
    conversation = [{"role": "user", "content": [{"type": "image", "image": image}]}]
    inputs = processor.apply_chat_template(
        conversation,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    )
    inputs = {k: v.to(device=device, dtype=dtype) if v.is_floating_point() else v.to(device)
              for k, v in inputs.items()}

    output_ids = model.generate(**inputs, max_new_tokens=4096)
    generated_ids = output_ids[0, inputs["input_ids"].shape[1]:]
    return processor.decode(generated_ids, skip_special_tokens=True)
```

### OCR Client in Backend

```python
# src/ingestion/ocr_client.py
import httpx
from pydantic import BaseModel

class OCRResult(BaseModel):
    pages: list[dict]
    full_text: str

class LightOnOCRClient:
    """Client for LightOnOCR GPU service."""

    def __init__(self, service_url: str, timeout: float = 300.0):
        self.service_url = service_url
        self.timeout = timeout

    async def ocr_document(self, content: bytes, filename: str) -> OCRResult:
        """Send document to OCR service."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            files = {"file": (filename, content)}
            response = await client.post(
                f"{self.service_url}/ocr",
                files=files,
            )
            response.raise_for_status()
            return OCRResult(**response.json())

    async def is_scanned_document(self, content: bytes) -> bool:
        """Detect if document needs OCR (image-based PDF)."""
        # Quick heuristic: check for text layer in PDF
        # Or call OCR service's detection endpoint
        ...
```

---

## CloudBuild Deployment Pattern

### Project Structure

```
infrastructure/
+-- terraform/           # DEPRECATED - kept for reference
|   +-- ...
+-- cloudbuild/          # NEW - CloudBuild configs
|   +-- backend.yaml
|   +-- frontend.yaml
|   +-- ocr-service.yaml
|   +-- deploy-all.yaml
+-- scripts/             # NEW - gcloud CLI scripts
    +-- deploy-backend.sh
    +-- deploy-frontend.sh
    +-- deploy-ocr.sh
    +-- setup-infrastructure.sh
```

### Backend CloudBuild Config

```yaml
# infrastructure/cloudbuild/backend.yaml
steps:
  # Build Docker image
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-t'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/loan-repo/backend:${SHORT_SHA}'
      - '-t'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/loan-repo/backend:latest'
      - '-f'
      - 'backend/Dockerfile'
      - 'backend/'

  # Push to Artifact Registry
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - '--all-tags'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/loan-repo/backend'

  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: 'gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'loan-backend-${_ENVIRONMENT}'
      - '--image=${_REGION}-docker.pkg.dev/${PROJECT_ID}/loan-repo/backend:${SHORT_SHA}'
      - '--region=${_REGION}'
      - '--platform=managed'
      - '--memory=2Gi'
      - '--cpu=2'
      - '--min-instances=0'
      - '--max-instances=10'
      - '--set-secrets=DATABASE_URL=database-url:latest,GEMINI_API_KEY=gemini-api-key:latest'
      - '--set-env-vars=GCS_BUCKET=${_GCS_BUCKET},CLOUD_TASKS_QUEUE=${_CLOUD_TASKS_QUEUE}'
      - '--vpc-egress=private-ranges-only'
      - '--network=${_VPC_NETWORK}'
      - '--subnet=${_SUBNET}'
      - '--allow-unauthenticated'

substitutions:
  _REGION: 'us-central1'
  _ENVIRONMENT: 'prod'
  _GCS_BUCKET: ''
  _CLOUD_TASKS_QUEUE: ''
  _VPC_NETWORK: ''
  _SUBNET: ''

options:
  logging: CLOUD_LOGGING_ONLY
```

### OCR Service CloudBuild Config

```yaml
# infrastructure/cloudbuild/ocr-service.yaml
steps:
  # Build OCR service image
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-t'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/loan-repo/ocr-service:${SHORT_SHA}'
      - '-f'
      - 'ocr_service/Dockerfile'
      - 'ocr_service/'

  # Push to Artifact Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', '${_REGION}-docker.pkg.dev/${PROJECT_ID}/loan-repo/ocr-service:${SHORT_SHA}']

  # Deploy GPU service to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: 'gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'loan-ocr-${_ENVIRONMENT}'
      - '--image=${_REGION}-docker.pkg.dev/${PROJECT_ID}/loan-repo/ocr-service:${SHORT_SHA}'
      - '--region=${_REGION}'
      - '--platform=managed'
      - '--memory=32Gi'
      - '--cpu=8'
      - '--gpu=1'
      - '--gpu-type=nvidia-l4'
      - '--min-instances=0'
      - '--max-instances=3'
      - '--concurrency=1'
      - '--timeout=300'
      - '--no-allow-unauthenticated'  # Internal only

substitutions:
  _REGION: 'us-central1'
  _ENVIRONMENT: 'prod'
```

### Deploy All Script

```bash
#!/bin/bash
# infrastructure/scripts/deploy-all.sh

set -euo pipefail

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID}"
REGION="${REGION:-us-central1}"
ENVIRONMENT="${ENVIRONMENT:-prod}"

echo "=== Deploying Loan Extraction System v2.0 ==="

# 1. Deploy OCR service first (backend depends on its URL)
echo "Deploying OCR service..."
gcloud builds submit \
  --config=infrastructure/cloudbuild/ocr-service.yaml \
  --substitutions="_REGION=${REGION},_ENVIRONMENT=${ENVIRONMENT}"

# Get OCR service URL
OCR_URL=$(gcloud run services describe "loan-ocr-${ENVIRONMENT}" \
  --region="${REGION}" --format='value(status.url)')

# 2. Deploy backend with OCR service URL
echo "Deploying backend..."
gcloud builds submit \
  --config=infrastructure/cloudbuild/backend.yaml \
  --substitutions="_REGION=${REGION},_ENVIRONMENT=${ENVIRONMENT},_OCR_SERVICE_URL=${OCR_URL}"

# Get backend URL
BACKEND_URL=$(gcloud run services describe "loan-backend-${ENVIRONMENT}" \
  --region="${REGION}" --format='value(status.url)')

# 3. Deploy frontend with backend URL
echo "Deploying frontend..."
gcloud builds submit \
  --config=infrastructure/cloudbuild/frontend.yaml \
  --substitutions="_REGION=${REGION},_ENVIRONMENT=${ENVIRONMENT},_BACKEND_URL=${BACKEND_URL}"

echo "=== Deployment complete ==="
```

---

## Build Order & Dependencies

### Phase Sequencing

```
Phase 1: Database Schema Migration
+-- Add char_start, char_end to source_references
+-- Add extraction_method, ocr_processed to documents
+-- Create indexes
    |
    v
Phase 2: LangExtract Integration
+-- Create LangExtractProcessor
+-- Create few-shot examples
+-- Unit tests for extraction
+-- Integration with Gemini 2.5 Flash
    |
    v
Phase 3: OCR Service
+-- Create ocr_service/ directory
+-- LightOnOCR model wrapper
+-- FastAPI service
+-- Dockerfile with CUDA
+-- Local testing
    |
    v
Phase 4: Dual Pipeline Wiring
+-- ExtractionRouter in DocumentService
+-- OCRRouter logic
+-- LightOnOCRClient
+-- Cloud Tasks payload update
+-- Task handler branching
+-- E2E tests
    |
    v
Phase 5: API Enhancement
+-- Add ?method and ?ocr query params
+-- Response model updates
+-- OpenAPI documentation
+-- Frontend integration
    |
    v
Phase 6: CloudBuild Migration
+-- Create cloudbuild/ configs
+-- Create deploy scripts
+-- IAM permissions
+-- Deprecate Terraform
```

### Dependency Graph

```
                    +-------------------+
                    | Schema Migration  |
                    +-------------------+
                            |
              +-------------+-------------+
              |                           |
              v                           v
    +-------------------+       +-------------------+
    | LangExtract       |       | OCR Service       |
    | Integration       |       | (independent)     |
    +-------------------+       +-------------------+
              |                           |
              +-------------+-------------+
                            |
                            v
                  +-------------------+
                  | Dual Pipeline     |
                  | Wiring            |
                  +-------------------+
                            |
                            v
                  +-------------------+
                  | API Enhancement   |
                  +-------------------+
                            |
                            v
                  +-------------------+
                  | CloudBuild        |
                  | Migration         |
                  +-------------------+
```

---

## Scaling Considerations

| Scale | Backend | OCR Service | Notes |
|-------|---------|-------------|-------|
| 0-100 docs/day | min=0, max=3 | min=0, max=1 | Scale to zero saves cost |
| 100-1000 docs/day | min=1, max=5 | min=0, max=2 | Keep backend warm |
| 1000+ docs/day | min=2, max=10 | min=1, max=3 | OCR warm reduces latency |

### GPU Cost Management

- **Instance-based billing**: GPU charged for entire instance lifecycle
- **Scale to zero**: Saves cost when not processing
- **Cold start**: ~5 seconds with pre-installed drivers
- **Concurrency=1**: OCR is memory-intensive, process one at a time
- **Consider**: Batch multiple pages in single request to amortize cold start

### Cloud Run GPU Requirements

From official documentation:
- **GPU Type**: NVIDIA L4 (24 GB VRAM)
- **Minimum CPU**: 4 (8 recommended)
- **Minimum Memory**: 16 GiB (32 GiB recommended)
- **Billing**: Instance-based (charged for entire lifecycle)
- **Cold Start**: ~5 seconds with pre-installed drivers

### Supported GPU Regions

- us-central1 (Iowa)
- us-east4 (Northern Virginia)
- europe-west1 (Belgium)
- europe-west4 (Netherlands)
- asia-southeast1 (Singapore)

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Tight Coupling Extraction Methods

**What people do:** Share code between Docling and LangExtract paths
**Why it's wrong:** Different data models (page-based vs char-offset-based)
**Do this instead:** Keep paths separate, unify only at storage layer

### Anti-Pattern 2: Synchronous OCR Calls

**What people do:** Call OCR service in upload request handler
**Why it's wrong:** OCR takes 10-30 seconds, HTTP timeout risk
**Do this instead:** Always queue OCR via Cloud Tasks

### Anti-Pattern 3: GPU Service in Backend

**What people do:** Include LightOnOCR model in backend container
**Why it's wrong:** 2GB+ model, slow cold starts, high memory
**Do this instead:** Separate GPU service, call via HTTP

### Anti-Pattern 4: Blocking on OCR Detection

**What people do:** Detect if scanned before queueing task
**Why it's wrong:** Detection itself requires parsing, slows upload
**Do this instead:** Pass ocr=auto, let task handler decide

---

## Integration Points Summary

| From | To | Method | Purpose |
|------|-----|--------|---------|
| DocumentService | Cloud Tasks | Queue | Async processing |
| Task Handler | LightOnOCR Service | HTTP POST | OCR preprocessing |
| Task Handler | LangExtractProcessor | Direct call | Text extraction |
| Task Handler | DoclingProcessor | Direct call | Text extraction (v1) |
| LangExtractProcessor | Gemini 2.5 API | HTTP | LLM extraction |
| All Extractors | PostgreSQL | SQLAlchemy | Persist results |

---

## Sources

### LangExtract
- [GitHub - google/langextract](https://github.com/google/langextract) - Official repository with API documentation
- [Google Developers Blog - Introducing LangExtract](https://developers.googleblog.com/en/introducing-langextract-a-gemini-powered-information-extraction-library/) - Feature overview and architecture

### LightOnOCR
- [Hugging Face - LightOnOCR-2-1B](https://huggingface.co/lightonai/LightOnOCR-2-1B) - Model card with inference examples
- [LightOn Blog - Making Knowledge Machine-Readable](https://www.lighton.ai/lighton-blogs/making-knowledge-machine-readable) - Performance benchmarks

### Cloud Run GPU
- [Cloud Run GPU Support](https://docs.cloud.google.com/run/docs/configuring/services/gpu) - Configuration and requirements

### CloudBuild
- [Deploying to Cloud Run using Cloud Build](https://docs.cloud.google.com/build/docs/deploying-builds/deploy-cloud-run) - Deployment patterns

---
*Architecture research for: v2.0 LangExtract + LightOnOCR Integration*
*Researched: 2026-01-24*
