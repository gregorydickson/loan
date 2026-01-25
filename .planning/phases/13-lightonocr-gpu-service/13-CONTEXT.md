# Phase 13: LightOnOCR GPU Service - Context

**Gathered:** 2026-01-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Deploy a dedicated Cloud Run GPU service for high-quality OCR on scanned loan documents using the LightOnOCR-2-1B model via vLLM serving infrastructure. This is a proof of concept deployment with scale-to-zero capability.

</domain>

<decisions>
## Implementation Decisions

### POC Philosophy
- Keep implementation simple - this is a proof of concept
- Prioritize getting it working over optimization
- Defer advanced features (batching, async, complex monitoring) to future phases

### Service Architecture
- Single synchronous endpoint: POST /ocr
- Accepts image, returns OCR text immediately
- No async processing, no job queues
- Simple request/response pattern

### Error Handling
- Return HTTP error codes + error message
- Caller handles retries and fallback logic
- No internal retry logic or circuit breakers
- Errors: 400 (bad input), 500 (processing failure), 503 (model not ready)

### Resource Management
- Use vLLM defaults for GPU memory and batch sizing
- Accept vLLM's automatic resource management
- No explicit GPU memory limits or batch size configuration
- Scale-to-zero (min_instances=0) for cost management

### Observability
- Basic Cloud Run logs only
- No custom metrics or dashboards
- No cold start tracking (POC can tolerate cold starts)
- Standard logging for requests and errors

### Claude's Discretion
- Exact Cloud Run configuration (CPU, memory, concurrency)
- Request timeout values
- vLLM server initialization parameters
- Docker image structure and dependencies
- Health check endpoint implementation

</decisions>

<specifics>
## Specific Ideas

- L4 GPU with 24GB VRAM (from Phase 10 quota request)
- LightOnOCR-2-1B model from Hugging Face
- Deploy to same region as main services for latency

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope

</deferred>

---

*Phase: 13-lightonocr-gpu-service*
*Context gathered: 2026-01-25*
