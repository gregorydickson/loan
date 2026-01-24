# Phase 9: Cloud Tasks Background Processing - Research

**Researched:** 2026-01-24
**Domain:** Google Cloud Tasks / Async Task Processing
**Confidence:** HIGH

## Summary

This phase moves document extraction from synchronous processing to asynchronous background processing using Google Cloud Tasks. The infrastructure is already provisioned in Phase 6 (Terraform `cloud_tasks.tf` creates a `document-processing` queue with retry configuration). The task is to wire the Python application to enqueue extraction tasks on upload and process them via a dedicated handler endpoint.

The key changes are: (1) DocumentService.upload() queues a Cloud Task instead of calling BorrowerExtractor directly, (2) a new `/api/tasks/process-document` endpoint receives and processes tasks, and (3) document status transitions through PENDING -> PROCESSING -> COMPLETED/FAILED as the task executes. Cloud Run's built-in OIDC token validation simplifies authentication - the service account just needs `roles/run.invoker`.

**Primary recommendation:** Use the `google-cloud-tasks` library (v2.21.0) to create HTTP target tasks with OIDC authentication. Let Cloud Run handle token validation automatically. Configure 5 retry attempts with exponential backoff (min 10s, max 300s, 4 doublings).

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| google-cloud-tasks | 2.21.0 | Cloud Tasks client | Official Google client, typed Python API |

### Supporting (Already In Use)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic | 2.12+ | Task payload validation | Request/response schemas |
| FastAPI | 0.128+ | Task handler endpoint | Already the API framework |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Cloud Tasks | Pub/Sub | Pub/Sub is more complex (push/pull), Cloud Tasks is simpler for HTTP targets |
| Cloud Tasks | Celery + Redis | Celery adds dependency, Cloud Tasks is managed/native |
| fastapi-cloud-tasks | Manual integration | Library adds abstraction we don't need; manual is clearer |

**Installation:**
```bash
# Add to pyproject.toml dependencies
pip install google-cloud-tasks>=2.21.0
```

## Architecture Patterns

### Recommended Project Structure
```
backend/src/
├── ingestion/
│   ├── document_service.py      # MODIFY: Replace sync extraction with task enqueueing
│   └── cloud_tasks_client.py    # NEW: Cloud Tasks client wrapper
├── api/
│   ├── documents.py             # MODIFY: Return PENDING status immediately
│   └── tasks.py                 # NEW: Task handler endpoint
└── config.py                    # MODIFY: Add Cloud Tasks settings
```

### Pattern 1: Cloud Tasks Client Wrapper
**What:** Encapsulate Cloud Tasks API behind a simple client class
**When to use:** All task creation operations
**Example:**
```python
# Source: Google Cloud Tasks documentation
import json
from google.cloud import tasks_v2
from google.protobuf import duration_pb2

class CloudTasksClient:
    """Client for creating Cloud Tasks to process documents."""

    def __init__(
        self,
        project_id: str,
        location: str,
        queue_id: str,
        service_url: str,
        service_account_email: str,
    ) -> None:
        self.client = tasks_v2.CloudTasksClient()
        self.queue_path = self.client.queue_path(project_id, location, queue_id)
        self.service_url = service_url
        self.service_account_email = service_account_email

    def create_document_processing_task(
        self,
        document_id: str,
        filename: str,
    ) -> tasks_v2.Task:
        """Create a task to process a document."""
        payload = json.dumps({
            "document_id": document_id,
            "filename": filename,
        }).encode()

        # Task with OIDC authentication for Cloud Run
        task = tasks_v2.Task(
            http_request=tasks_v2.HttpRequest(
                http_method=tasks_v2.HttpMethod.POST,
                url=f"{self.service_url}/api/tasks/process-document",
                headers={"Content-Type": "application/json"},
                body=payload,
                oidc_token=tasks_v2.OidcToken(
                    service_account_email=self.service_account_email,
                    audience=self.service_url,
                ),
            ),
            # 10-minute timeout per attempt (Cloud Tasks default)
            dispatch_deadline=duration_pb2.Duration(seconds=600),
        )

        return self.client.create_task(
            tasks_v2.CreateTaskRequest(
                parent=self.queue_path,
                task=task,
            )
        )
```

### Pattern 2: Task Handler Endpoint
**What:** FastAPI endpoint that receives and processes Cloud Tasks
**When to use:** Processing queued document extraction
**Example:**
```python
# Source: Cloud Run service-to-service authentication docs
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from uuid import UUID

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

class ProcessDocumentRequest(BaseModel):
    document_id: UUID
    filename: str

@router.post(
    "/process-document",
    status_code=status.HTTP_200_OK,
    summary="Process document (Cloud Tasks handler)",
)
async def process_document(
    request: Request,
    payload: ProcessDocumentRequest,
    # Dependencies for extraction...
) -> dict:
    """Handle document processing task from Cloud Tasks.

    Cloud Run validates OIDC token automatically - just check
    that the request came from expected source via headers.

    Must return 2xx for success, 4xx/5xx triggers retry.
    """
    # Log task metadata for debugging
    task_name = request.headers.get("X-CloudTasks-TaskName", "unknown")
    retry_count = int(request.headers.get("X-CloudTasks-TaskRetryCount", "0"))

    logger.info(
        "Processing document task",
        document_id=str(payload.document_id),
        task_name=task_name,
        retry_count=retry_count,
    )

    # Update status to PROCESSING
    await document_repository.update_status(
        payload.document_id,
        DocumentStatus.PROCESSING,
    )

    try:
        # Run extraction (existing logic from document_service)
        # ... extraction code ...

        await document_repository.update_status(
            payload.document_id,
            DocumentStatus.COMPLETED,
        )
        return {"status": "completed"}

    except Exception as e:
        # Let Cloud Tasks retry by returning 5xx
        # After max retries, mark as FAILED
        if retry_count >= 4:  # 5 total attempts (0-indexed)
            await document_repository.update_status(
                payload.document_id,
                DocumentStatus.FAILED,
                error_message=str(e),
            )
            return {"status": "failed", "error": str(e)}

        # Re-raise to trigger retry
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Extraction failed (attempt {retry_count + 1}): {e}",
        )
```

### Pattern 3: Upload Returns Immediately with PENDING
**What:** Modify upload endpoint to queue task and return immediately
**When to use:** Document upload workflow
**Example:**
```python
# Source: Existing document_service.py pattern
async def upload(
    self,
    filename: str,
    content: bytes,
    content_type: str | None = None,
) -> Document:
    """Upload document, queue for processing, return immediately."""
    # 1-6: Existing validation, hash, GCS upload...

    # 7. Queue processing task (instead of sync extraction)
    try:
        self.cloud_tasks_client.create_document_processing_task(
            document_id=str(document_id),
            filename=filename,
        )
    except Exception as e:
        logger.error("Failed to queue task: %s", e)
        # Still return document - task can be retried manually
        await self.repository.update_status(
            document_id,
            DocumentStatus.FAILED,
            error_message=f"Failed to queue processing: {e}",
        )

    # Return immediately with PENDING status
    return document
```

### Anti-Patterns to Avoid
- **Processing in upload endpoint:** The whole point is async. Upload should queue and return immediately.
- **Custom OIDC token validation:** Cloud Run handles this automatically via IAM. Don't verify tokens manually.
- **Returning 2xx on failure:** Cloud Tasks only retries on 4xx/5xx. Return 503 to trigger retry.
- **Ignoring retry count:** Check `X-CloudTasks-TaskRetryCount` header to detect final retry and set FAILED status.
- **Not setting dispatch_deadline:** Default is 10 min, but be explicit. Max is 30 min.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Task queuing | Custom HTTP client | google-cloud-tasks | Handles auth, retries, serialization |
| OIDC validation | Token verification code | Cloud Run IAM | Automatic validation, no code needed |
| Retry logic | Custom retry loop | Cloud Tasks queue config | Exponential backoff built-in |
| Task deduplication | Manual tracking | Cloud Tasks task names | Built-in deduplication window |
| Task timeout | Manual timer | dispatch_deadline | Cloud Tasks enforces automatically |

**Key insight:** Cloud Tasks handles all the hard parts (retry, backoff, timeout, auth). The code just creates tasks and handles success/failure responses.

## Common Pitfalls

### Pitfall 1: Returning 200 OK When Task Fails
**What goes wrong:** Task fails but returns 200, so Cloud Tasks thinks it succeeded and doesn't retry
**Why it happens:** Natural instinct to return JSON with error message
**How to avoid:**
- Return 2xx ONLY when task completed successfully
- Return 503 Service Unavailable to trigger retry
- Return 4xx for permanent failures (bad data) that shouldn't retry
**Warning signs:** Tasks disappear without retrying, FAILED status never set

### Pitfall 2: Not Checking Retry Count Before Setting FAILED
**What goes wrong:** Document marked FAILED on first retry attempt
**Why it happens:** Exception caught, status set to FAILED, then 5xx returned
**How to avoid:**
- Check `X-CloudTasks-TaskRetryCount` header
- Only set FAILED status on final retry (count >= max_attempts - 1)
- Let intermediate failures return 5xx without updating status
**Warning signs:** Documents marked FAILED after first transient error

### Pitfall 3: Task Timeout Exceeds Processing Time
**What goes wrong:** Task times out before extraction completes
**Why it happens:** Large documents take longer than default 10-minute timeout
**How to avoid:**
- Set `dispatch_deadline` appropriately (max 30 min for Cloud Tasks)
- For very long operations, consider Cloud Run jobs instead
- Monitor task duration in Cloud Logging
**Warning signs:** Tasks fail with timeout errors in logs

### Pitfall 4: Queue Rate Limiting Causes Delays
**What goes wrong:** Tasks queue up and process slowly
**Why it happens:** Default rate limits may be too conservative
**How to avoid:**
- Existing queue config: 10 dispatches/sec, 5 concurrent (should be fine)
- Monitor queue depth in Cloud Console
- Adjust if uploads spike higher than expected
**Warning signs:** Long delay between upload and processing start

### Pitfall 5: Service Account Missing Permissions
**What goes wrong:** Task creation fails with permission denied
**Why it happens:** Service account needs both enqueuer and invoker roles
**How to avoid:**
- Verify IAM: `roles/cloudtasks.enqueuer` (to create tasks)
- Verify IAM: `roles/run.invoker` (to invoke Cloud Run)
- Both already configured in Phase 6 Terraform
**Warning signs:** 403 errors in task creation or execution

### Pitfall 6: Duplicate Task Execution
**What goes wrong:** Same document processed multiple times
**Why it happens:** Cloud Tasks prioritizes "at least once" delivery
**How to avoid:**
- Check document status before processing (skip if already PROCESSING/COMPLETED)
- Use idempotent operations where possible
- Accept that >99.999% execute exactly once, design for rare duplicates
**Warning signs:** Multiple borrower records from same document

## Code Examples

Verified patterns from official sources:

### Configuration Settings
```python
# Source: Existing config.py pattern + Cloud Tasks docs
class Settings(BaseSettings):
    # ... existing settings ...

    # Cloud Tasks settings
    gcp_project_id: str = Field(
        default="",
        description="GCP project ID for Cloud Tasks",
    )
    gcp_location: str = Field(
        default="us-central1",
        description="GCP region for Cloud Tasks queue",
    )
    cloud_tasks_queue: str = Field(
        default="document-processing",
        description="Cloud Tasks queue name",
    )
    cloud_run_service_url: str = Field(
        default="",
        description="Cloud Run backend service URL for task callbacks",
    )
    cloud_run_service_account: str = Field(
        default="",
        description="Service account email for OIDC token",
    )
```

### Task Creation with OIDC Token
```python
# Source: Google Cloud Tasks documentation
from google.cloud import tasks_v2
from google.protobuf import duration_pb2
import json

def create_http_task_with_token(
    project: str,
    location: str,
    queue: str,
    url: str,
    payload: dict,
    service_account_email: str,
) -> tasks_v2.Task:
    """Create an HTTP target task with OIDC authentication."""
    client = tasks_v2.CloudTasksClient()

    task = tasks_v2.Task(
        http_request=tasks_v2.HttpRequest(
            http_method=tasks_v2.HttpMethod.POST,
            url=url,
            headers={"Content-Type": "application/json"},
            body=json.dumps(payload).encode(),
            oidc_token=tasks_v2.OidcToken(
                service_account_email=service_account_email,
                audience=url.split("/api/")[0],  # Base URL as audience
            ),
        ),
        dispatch_deadline=duration_pb2.Duration(seconds=600),  # 10 min
    )

    return client.create_task(
        tasks_v2.CreateTaskRequest(
            parent=client.queue_path(project, location, queue),
            task=task,
        )
    )
```

### Cloud Tasks Headers for Debugging
```python
# Source: Google Cloud Tasks documentation
# Headers sent by Cloud Tasks with each request:
CLOUD_TASKS_HEADERS = {
    "X-CloudTasks-QueueName": "Queue name",
    "X-CloudTasks-TaskName": "Task name (unique ID)",
    "X-CloudTasks-TaskRetryCount": "Retry attempt number (0-indexed)",
    "X-CloudTasks-TaskExecutionCount": "Total execution attempts",
    "X-CloudTasks-TaskETA": "Scheduled execution time",
}

def log_task_context(request: Request) -> None:
    """Log Cloud Tasks metadata for debugging."""
    logger.info(
        "Task context",
        queue=request.headers.get("X-CloudTasks-QueueName"),
        task_name=request.headers.get("X-CloudTasks-TaskName"),
        retry_count=request.headers.get("X-CloudTasks-TaskRetryCount"),
    )
```

### Existing Queue Configuration (Terraform)
```hcl
# Source: infrastructure/terraform/cloud_tasks.tf (Phase 6)
# Already configured with appropriate retry settings
resource "google_cloud_tasks_queue" "document_processing" {
  name     = "document-processing"
  location = var.region

  rate_limits {
    max_dispatches_per_second = 10
    max_concurrent_dispatches = 5
  }

  retry_config {
    max_attempts       = 5
    max_retry_duration = "3600s"  # 1 hour total retry window
    max_backoff        = "3600s"  # 1 hour maximum backoff
    min_backoff        = "10s"    # 10 second minimum backoff
    max_doublings      = 5        # Exponential backoff doublings
  }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Sync processing in upload | Async via Cloud Tasks | This phase | Non-blocking uploads |
| Custom retry logic | Cloud Tasks retry config | This phase | Managed exponential backoff |
| Manual auth tokens | OIDC with Cloud Run validation | GCP feature | No custom auth code needed |

**Deprecated/outdated:**
- `fastapi-cloud-tasks` library: Adds unnecessary abstraction for simple use case
- Manual OIDC token verification: Cloud Run handles this automatically with IAM
- App Engine task targets: HTTP targets are the current standard

## Open Questions

Things that couldn't be fully resolved:

1. **Task Timeout for Large Documents**
   - What we know: Docling + LLM extraction can take 30+ seconds for complex documents
   - What's unclear: Whether 10-minute default timeout is sufficient for all cases
   - Recommendation: Start with 10 min (600s), monitor in Cloud Logging, increase if needed

2. **Cleanup on Retry**
   - What we know: If extraction partially succeeds then fails, partial borrowers may exist
   - What's unclear: Whether to delete partial results before retry
   - Recommendation: Check for existing borrowers from same document, skip if found (idempotent)

3. **PROCESSING Status Transition**
   - What we know: Document should be PROCESSING while task runs
   - What's unclear: Set PROCESSING at task start or after acquiring resources?
   - Recommendation: Set PROCESSING immediately in task handler (simplest, most informative)

## Sources

### Primary (HIGH confidence)
- [Google Cloud Tasks documentation](https://docs.cloud.google.com/tasks/docs/creating-http-target-tasks) - HTTP target task creation
- [Cloud Run triggering with Tasks](https://docs.cloud.google.com/run/docs/triggering/using-tasks) - Cloud Run integration
- [Cloud Tasks Python client](https://pypi.org/project/google-cloud-tasks/) - v2.21.0 (Jan 2026)
- [Cloud Tasks queue configuration](https://docs.cloud.google.com/tasks/docs/configuring-queues) - Retry parameters
- [Cloud Run service-to-service auth](https://docs.cloud.google.com/run/docs/authenticating/service-to-service) - OIDC validation

### Secondary (MEDIUM confidence)
- [Cloud Tasks common pitfalls](https://docs.cloud.google.com/tasks/docs/common-pitfalls) - Known issues
- Existing codebase: `infrastructure/terraform/cloud_tasks.tf` - Queue already configured
- Existing codebase: `infrastructure/terraform/iam.tf` - IAM roles already granted
- Existing codebase: `backend/src/ingestion/document_service.py` - Current sync implementation

### Tertiary (LOW confidence)
- None - all findings verified with official documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official Google library, well-documented
- Architecture: HIGH - Follows Google Cloud documentation patterns
- Pitfalls: HIGH - Verified from official docs + existing codebase analysis

**Research date:** 2026-01-24
**Valid until:** 2026-02-24 (30 days - Cloud Tasks API is stable)
