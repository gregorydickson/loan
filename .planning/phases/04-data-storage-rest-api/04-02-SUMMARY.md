---
phase: 04-data-storage-rest-api
plan: 02
subsystem: api
tags:
  - fastapi
  - cors
  - error-handling
  - rest-api

dependency-graph:
  requires:
    - 04-01
  provides:
    - cors-middleware
    - exception-handlers
    - document-status-endpoint
  affects:
    - 04-03

tech-stack:
  added: []
  patterns:
    - cors-middleware-first
    - custom-exception-handlers
    - lightweight-polling-endpoint

file-tracking:
  created:
    - backend/src/api/errors.py
  modified:
    - backend/src/main.py
    - backend/src/api/documents.py
    - backend/src/api/dependencies.py

decisions:
  - title: CORS origins list
    choice: localhost:3000 and localhost:5173 with 127.0.0.1 variants
    reason: Cover both Next.js (3000) and Vite (5173) dev servers

metrics:
  duration: 5 min
  completed: 2026-01-24
---

# Phase 04 Plan 02: CORS, Exception Handlers, and Status Endpoint Summary

CORS middleware for frontend integration, custom exception handlers for consistent error responses, and lightweight status endpoint for polling.

## Completed Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create errors.py module | 185b7a81 | backend/src/api/errors.py |
| 2 | Add CORS middleware and exception handlers | aff96ebf | backend/src/main.py |
| 3 | Add document status endpoint | ce33273b | backend/src/api/documents.py, backend/src/api/dependencies.py |

## Decisions Made

1. **CORS origins configuration**: Included localhost:3000 (Next.js), localhost:5173 (Vite), and their 127.0.0.1 equivalents for complete local development coverage.

2. **Exception handler order**: CORS middleware added FIRST before exception handlers and routers per FastAPI best practice.

3. **Status endpoint placement**: Placed /{document_id}/status route BEFORE /{document_id} to avoid route conflict (FastAPI matches routes in order).

4. **EntityNotFoundError re-export**: Re-exported from dependencies.py for convenient API module imports.

## Key Files

### backend/src/api/errors.py (created)
```python
class EntityNotFoundError(Exception):
    """Raised when a requested entity is not found."""
    def __init__(self, entity_type: str, entity_id: str):
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(f"{entity_type} not found: {entity_id}")
```

### backend/src/main.py (modified)
- Added CORSMiddleware with frontend origins
- Added @app.exception_handler(EntityNotFoundError) returning 404
- Added @app.exception_handler(Exception) for 500 errors with logging
- Imports structlog for structured error logging

### backend/src/api/documents.py (modified)
- Added DocumentStatusResponse model (lightweight: id, status, page_count, error_message)
- Added GET /{document_id}/status endpoint for efficient polling

### backend/src/api/dependencies.py (modified)
- Re-exports EntityNotFoundError for API module convenience
- Added __all__ list for explicit exports

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

1. errors.py importable: PASS
2. CORS middleware active: PASS (CORSMiddleware in app.user_middleware)
3. Status endpoint exists: PASS (/api/documents/{document_id}/status in routes)
4. main.py imports from errors.py: PASS (line 16)
5. EntityNotFoundError handler registered: PASS

## Next Phase Readiness

Plan 04-02 complete. Phase 04 API foundation is now ready:
- CORS configured for frontend integration
- Custom exception handlers provide consistent error format
- Status endpoint enables efficient polling without full document fetch
- Error types available for import from dependencies.py

Ready to proceed with 04-03 (borrower API endpoints) if needed.
