# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-23)

**Core value:** Accurate extraction of borrower data with complete traceability - every extracted field must include source attribution showing which document and page it came from.
**Current focus:** Phase 5 - Frontend Dashboard (COMPLETE)

## Current Position

Phase: 5 of 7 (Frontend Dashboard)
Plan: 4 of 4 in current phase
Status: Phase complete
Last activity: 2026-01-24 - Completed 05-04-PLAN.md

Progress: [████████████████████████░░░░] 80%

## Performance Metrics

**Velocity:**
- Total plans completed: 19
- Average duration: 7.0 min
- Total execution time: 2.22 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation | 3 | 17 min | 5.7 min |
| 02-document-ingestion-pipeline | 4 | 34 min | 8.5 min |
| 03-llm-extraction-validation | 5 | 49 min | 9.8 min |
| 04-data-storage-rest-api | 3 | 18 min | 6.0 min |
| 05-frontend-dashboard | 4 | 15 min | 3.8 min |

**Recent Trend:**
- Last 5 plans: 5 min, 3 min, 3 min, 5 min, 6 min
- Trend: Frontend plans averaging 3.8 min (fastest phase)

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

**Phase 04-03 Decisions:**
- Search endpoint before {borrower_id} to avoid "search" interpreted as UUID
- income_count computed from len(income_records) for list views
- Search returns len(borrowers) as total (no separate count query)

**Phase 05-01 Decisions:**
- QueryClient staleTime 60s with retry 1 for queries, 0 for mutations
- API client uses NEXT_PUBLIC_API_URL env var with localhost:8000 default
- Sidebar uses usePathname for active state highlighting
- Dashboard calls API directly without hooks (hooks created in later plans)

**Phase 05-02 Decisions:**
- Status polling uses refetchInterval callback returning 2000ms or false based on status
- DocumentTable uses Link components in cells for full row clickability
- Upload zone shows truncated document ID in success message for verification
- Detail page polls status only when document is pending/processing

**Phase 05-03 Decisions:**
- Search uses useDeferredValue with ref tracking to avoid effect state updates
- Pagination only shown in list mode, not search mode
- Confidence badge colors: default (green) >= 0.7, secondary (yellow) >= 0.5, destructive (red) < 0.5
- Income timeline sorted descending by year (newest first)
- Source references grouped by document_id to reduce visual clutter
- Detail page uses two-column layout on desktop (lg:grid-cols-2), stacked on mobile

**Phase 05-04 Decisions:**
- Mermaid initialized in useEffect to avoid SSR errors
- Error boundary shows raw chart on render failure for debugging
- Neutral theme and loose security level for Mermaid
- DecisionCard is server component (no interactivity needed)

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-01-24 16:00 UTC
Stopped at: Completed 05-04-PLAN.md (Architecture Documentation Pages)
Resume file: None
