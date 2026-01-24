# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-23)

**Core value:** Accurate extraction of borrower data with complete traceability - every extracted field must include source attribution showing which document and page it came from.
**Current focus:** Phase 4 - Data Storage & REST API

## Current Position

Phase: 4 of 7 (Data Storage & REST API)
Plan: 2 of 3 in current phase
Status: In progress
Last activity: 2026-01-24 - Completed 04-02-PLAN.md (CORS, Exception Handlers, Status Endpoint)

Progress: [██████████████░░░░░░░░░░░░░░░] 50%

## Performance Metrics

**Velocity:**
- Total plans completed: 14
- Average duration: 7.7 min
- Total execution time: 1.80 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation | 3 | 17 min | 5.7 min |
| 02-document-ingestion-pipeline | 4 | 34 min | 8.5 min |
| 03-llm-extraction-validation | 5 | 49 min | 9.8 min |
| 04-data-storage-rest-api | 2 | 13 min | 6.5 min |

**Recent Trend:**
- Last 5 plans: 10 min, 14 min, 14 min, 8 min, 5 min
- Trend: Fast for API plans

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Docling for document processing (production-grade PDF/DOCX/image parsing)
- Gemini 3.0 with dynamic model selection (Flash for standard, Pro for complex)
- PostgreSQL for relational storage with source attribution
- FastAPI for async REST API
- Next.js 14 App Router for frontend
- Cloud Run for serverless deployment

**Phase 01-01 Decisions:**
- setuptools>=75.0 as build backend for editable installs
- All Phase 2+ dependencies in pyproject.toml to prevent conflicts
- PostgreSQL 16-alpine and Redis 7-alpine for local dev

**Phase 01-02 Decisions:**
- Next.js 16 + Tailwind v4 (latest from create-next-app, shadcn compatible)
- shadcn/ui new-york style with CSS variables
- Inter font for typography

**Phase 01-03 Decisions:**
- ConfigDict(from_attributes=True) for ORM compatibility
- Decimal for income amounts (precision preservation)
- field_validator for period normalization to lowercase
- Literal types for status/file_type enums

**Phase 02-01 Decisions:**
- datetime.UTC alias instead of deprecated timezone.utc
- expire_on_commit=False for async sessions (prevents lazy loading issues)
- Repository uses flush() not commit() - caller controls transaction
- SQLite in-memory with aiosqlite for fast unit tests

**Phase 02-02 Decisions:**
- Fresh DocumentConverter per document (memory-safe, avoids GitHub #2209 leak)
- Page text via iterate_items() with provenance (actual content extraction)
- Application Default Credentials for GCS (works on Cloud Run)

**Phase 02-03 Decisions:**
- Upload returns PENDING immediately (Docling processing is async via Cloud Tasks)
- SHA-256 hash computed before DB insert for early duplicate detection
- Mock GCS client when bucket not configured (enables local development)

**Phase 02-04 Decisions:**
- Synchronous processing instead of async Cloud Tasks (simpler for Phase 2)
- Upload returns final status (COMPLETED/FAILED), not PENDING
- Include page_count and error_message in upload response
- DoclingProcessor injection via FastAPI dependencies

**Phase 03-01 Decisions:**
- Type-safe token extraction via helper function (handles None usage_metadata)
- Let RetryError propagate after exhaustion (caller can distinguish from single-attempt failure)
- Temperature=1.0 for Gemini 3 (lower causes looping)
- No max_output_tokens (causes None response with structured output)

**Phase 03-02 Decisions:**
- Compiled regex patterns at init time for O(n) efficiency
- Threshold >3 for poor quality indicators (avoids false positives)
- Threshold >10 pages for complex documents
- Last 20% of chunk searched for paragraph breaks

**Phase 03-03 Decisions:**
- phonenumbers library for robust US phone validation (handles all formats)
- Pre-compiled regex patterns at class level for performance
- Year validation range 1950 to current+1 (historical + projected income)
- Confidence threshold 0.7 for review flagging

**Phase 03-04 Decisions:**
- Separate ExtractedBorrower (LLM output) from BorrowerRecord (storage) schemas
- No Field(default=...) in extraction schemas (Gemini compatibility)
- Deduplication priority: SSN > account > fuzzy name (90%+) > high name match (95%+)
- Page finding via text search fallback to char position estimation

**Phase 03-05 Decisions:**
- Income drop >50% or spike >300% flagged as warnings
- Consistency runs AFTER deduplication (flags review items, doesn't resolve)
- Cross-document checks use normalized names for matching

**Phase 04-01 Decisions:**
- selectinload() for all relationship loading to prevent N+1 queries
- Chained selectinload for nested document relationship on SourceReference
- search_by_name loads only income_records (list view optimization)
- search_by_account uses unique() to prevent duplicate borrowers from joins

**Phase 04-02 Decisions:**
- CORS origins include localhost:3000, localhost:5173, and 127.0.0.1 variants
- CORS middleware added FIRST before exception handlers and routers
- Status endpoint placed BEFORE /{document_id} to avoid route conflicts
- EntityNotFoundError re-exported from dependencies.py for API convenience

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-01-24 13:50 UTC
Stopped at: Completed 04-02-PLAN.md (CORS, Exception Handlers, Status Endpoint)
Resume file: None
