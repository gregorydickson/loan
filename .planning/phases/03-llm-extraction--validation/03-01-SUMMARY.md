---
phase: 03-llm-extraction-validation
plan: 01
subsystem: extraction
tags: [gemini, llm, extraction, api-client, retry, structured-output]
depends_on:
  requires: [01-03, 02-01]
  provides: [GeminiClient, LLMResponse]
  affects: [03-02, 03-03, 03-04]
tech-stack:
  added: [google-genai]
  patterns: [structured-output, retry-with-backoff, dataclass-response]
key-files:
  created:
    - backend/src/extraction/__init__.py
    - backend/src/extraction/llm_client.py
    - backend/tests/extraction/test_llm_client.py
  modified: []
decisions:
  - key: type-safe-token-extraction
    choice: Helper function for usage_metadata access
    rationale: google-genai returns Optional usage_metadata, helper avoids None checks
  - key: tenacity-retry-error
    choice: Let RetryError propagate after exhaustion
    rationale: Caller can catch RetryError to distinguish from single-attempt failure
metrics:
  duration: 10 min
  completed: 2026-01-24
---

# Phase 3 Plan 1: Gemini LLM Client Summary

Production-ready Gemini API client with structured output support, retry logic, and comprehensive unit tests using mocked API.

## What Was Built

### GeminiClient Class
- `FLASH_MODEL = "gemini-3-flash-preview"` and `PRO_MODEL = "gemini-3-pro-preview"` constants
- `__init__(api_key: str | None)` - Initializes with explicit key or uses env (GEMINI_API_KEY/GOOGLE_API_KEY)
- `extract(text, schema, use_pro, system_instruction)` - Sync extraction with tenacity retry
- `extract_async(...)` - Async extraction using `client.aio.models.generate_content`

### LLMResponse Dataclass
- `content: str` - Raw JSON response text
- `parsed: BaseModel | None` - Parsed Pydantic model (None if truncated)
- `input_tokens: int` - Input token count
- `output_tokens: int` - Output token count
- `latency_ms: int` - Request latency in milliseconds
- `model_used: str` - Model that processed the request
- `finish_reason: str` - Why generation stopped (STOP, MAX_TOKENS, etc.)

### Key Implementation Details
- **Temperature = 1.0**: Critical for Gemini 3 models (lower causes looping)
- **No max_output_tokens**: Would cause None response with structured output
- **Retry logic**: `wait_exponential_jitter(initial=1, max=60, jitter=5)`, `stop_after_attempt(3)`
- **Type-safe token extraction**: Helper function handles None usage_metadata

## Test Coverage

14 unit tests with 98% coverage on llm_client.py:

| Test Class | Tests | Coverage |
|------------|-------|----------|
| TestGeminiClientInit | 2 | Default and explicit API key |
| TestGeminiClientExtract | 6 | Response, model selection, None handling, parsing, system_instruction |
| TestGeminiClientRetry | 2 | Retry on APIError, exhaustion raises RetryError |
| TestGeminiClientAsync | 2 | Async response and None handling |
| TestLLMResponse | 2 | Dataclass creation |

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

1. **Type-safe token extraction**: Added `_get_token_counts()` helper to handle optional `usage_metadata` without mypy errors
2. **RetryError propagation**: After retries exhausted, tenacity raises `RetryError` wrapping the original `APIError` - tests updated to expect this

## Technical Notes

### Imports
```python
from google import genai
from google.genai import errors, types
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter
```

### Response Handling
```python
# None response indicates truncation
if response.text is None:
    return LLMResponse(parsed=None, finish_reason="MAX_TOKENS", ...)

# Otherwise parse JSON into Pydantic model
parsed = schema.model_validate_json(response.text)
```

### APIError Constructor
```python
# For tests: APIError(code=429, response_json={"message": "Rate limited"})
# response_json must have 'message' or 'error.message' key
```

## Next Phase Readiness

- GeminiClient ready for use in 03-02 (Complexity Classifier)
- LLMResponse standardizes extraction output for downstream processing
- Retry logic handles rate limiting automatically

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `backend/src/extraction/__init__.py` | 13 | Package exports GeminiClient, LLMResponse |
| `backend/src/extraction/llm_client.py` | 253 | Client implementation with retry |
| `backend/tests/extraction/test_llm_client.py` | 392 | 14 unit tests with mocked API |

## Commits

1. `ac97fa42` - feat(03-01): create extraction package with GeminiClient and LLMResponse
2. `e7088961` - test(03-01): add comprehensive unit tests for GeminiClient
3. `19f0fb69` - fix(03-01): add type-safe token count extraction
