# Phase 9: Cloud Tasks Background Processing - Context

**Gathered:** 2026-01-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Move document extraction from synchronous processing to asynchronous background queue with retry logic. Upload endpoint returns immediately with PENDING status, extraction runs in Cloud Tasks worker, status updates to COMPLETED or FAILED after processing finishes.

This closes the gap identified in v1.0 audit where synchronous processing violates INGEST-08 and INGEST-10 requirements.

</domain>

<decisions>
## Implementation Decisions

### Simplicity First
- Demo/portfolio app — prioritize straightforward implementation over production complexity
- Leverage existing Cloud Tasks infrastructure from Phase 6
- Minimal changes to frontend (polling already works)

### Status Tracking
- Keep current frontend polling approach (no changes needed)
- Frontend polls `/api/documents/{id}/status` every 2 seconds while PENDING/PROCESSING
- Backend updates document status in database (PENDING → PROCESSING → COMPLETED/FAILED)

### Retry Logic
- **5 retry attempts** total (generous for demo quality)
- Exponential backoff between retries
- Cloud Tasks queue configuration handles retry mechanics
- Retries cover transient failures: rate limits, network issues, temporary API errors

### Failure Handling
- Document status set to FAILED after all retries exhausted
- `error_message` field stores what went wrong
- UI displays failure state with error message
- No separate logging infrastructure — error stored in database

### Queue Ordering
- **FIFO processing** (first uploaded, first processed)
- Upload timestamp determines processing order
- Cloud Tasks maintains queue order naturally

### Claude's Discretion
- Exact exponential backoff parameters (min/max delay)
- Task timeout duration
- How to transition status PENDING → PROCESSING (beginning of task vs after acquiring resources)
- Whether to cleanup partial extraction results on retry

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for Cloud Tasks integration.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-cloud-tasks-background-processing*
*Context gathered: 2026-01-24*
