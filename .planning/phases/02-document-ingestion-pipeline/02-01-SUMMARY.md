---
phase: 02-document-ingestion-pipeline
plan: 01
subsystem: database
tags: [sqlalchemy, postgresql, alembic, asyncpg, orm, async]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: "Project structure, config.py with database_url, Pydantic models"
provides:
  - SQLAlchemy ORM models for document pipeline (Document, Borrower, IncomeRecord, AccountNumber, SourceReference)
  - Async database engine and session factory with dependency injection
  - Alembic async migration configuration
  - DocumentRepository with async CRUD operations
  - Unit tests for repository pattern
affects: [02-02-file-upload-api, 02-03-document-processing, 03-extraction-engine]

# Tech tracking
tech-stack:
  added: [aiosqlite]
  patterns: [Repository pattern, async session factory, FastAPI dependency injection]

key-files:
  created:
    - backend/src/storage/models.py
    - backend/src/storage/database.py
    - backend/src/storage/repositories.py
    - backend/alembic/versions/001_initial_schema.py
    - backend/tests/unit/test_repositories.py
  modified:
    - backend/pyproject.toml
    - backend/src/storage/__init__.py

key-decisions:
  - "Use datetime.UTC alias instead of deprecated timezone.utc"
  - "expire_on_commit=False for async sessions to prevent lazy loading issues"
  - "Repository uses flush() not commit() - caller controls transaction"
  - "SQLite in-memory with aiosqlite for fast unit tests"

patterns-established:
  - "Repository pattern: Repositories take AsyncSession in constructor, use flush() to get generated values"
  - "DBSession type alias: Annotated[AsyncSession, Depends(get_db_session)] for FastAPI DI"
  - "Model definitions: Use Mapped[T] and mapped_column() for SQLAlchemy 2.0 style"

# Metrics
duration: 6min
completed: 2026-01-23
---

# Phase 2 Plan 01: Database Layer Summary

**SQLAlchemy 2.0 ORM with 5 tables (documents, borrowers, income_records, account_numbers, source_references), async PostgreSQL engine, DocumentRepository with full CRUD, and 13 unit tests**

## Performance

- **Duration:** 6 min
- **Started:** 2026-01-23T22:24:36Z
- **Completed:** 2026-01-23T22:30:56Z
- **Tasks:** 3
- **Files modified:** 10

## Accomplishments
- SQLAlchemy 2.0 async-compatible ORM models with proper type annotations
- Alembic async migration creating 5 tables with unique constraint on file_hash
- DocumentRepository with create, get_by_id, get_by_hash, update_status, list_documents, list_pending
- 13 comprehensive unit tests with 100% repository coverage

## Task Commits

Each task was committed atomically:

1. **Task 1: SQLAlchemy ORM models and database setup** - `76374f07` (feat)
2. **Task 2: Alembic async migration with initial schema** - `fabeda71` (feat)
3. **Task 3: DocumentRepository with async CRUD and unit tests** - `28b8c83e` (feat)

## Files Created/Modified
- `backend/src/storage/models.py` - ORM models: Document, Borrower, IncomeRecord, AccountNumber, SourceReference, DocumentStatus enum
- `backend/src/storage/database.py` - Async engine, session factory, get_db_session dependency, DBSession type alias
- `backend/src/storage/repositories.py` - DocumentRepository with async CRUD methods
- `backend/src/storage/__init__.py` - Module exports
- `backend/alembic.ini` - Alembic configuration with PostgreSQL URL
- `backend/alembic/env.py` - Async migration environment with settings integration
- `backend/alembic/versions/001_initial_schema.py` - Initial migration creating all tables
- `backend/tests/unit/test_repositories.py` - 13 unit tests for DocumentRepository
- `backend/pyproject.toml` - Added aiosqlite dev dependency

## Decisions Made
- Used `datetime.UTC` alias instead of `timezone.utc` to satisfy ruff UP017 lint rule
- Set `expire_on_commit=False` on async session factory (critical for async - prevents lazy loading issues)
- Repository uses `flush()` instead of `commit()` so caller controls transaction boundaries
- Used SQLite in-memory with aiosqlite for unit tests (fast, isolated, no PostgreSQL needed)
- Import UUID directly instead of TYPE_CHECKING block (SQLAlchemy needs it at runtime for annotation resolution)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed UUID import for SQLAlchemy runtime annotation**
- **Found during:** Task 1 (ORM models)
- **Issue:** Using `TYPE_CHECKING` block for UUID caused "Could not de-stringify annotation 'UUID'" error
- **Fix:** Import UUID directly from uuid module, not in TYPE_CHECKING block
- **Files modified:** backend/src/storage/models.py
- **Verification:** Models import successfully
- **Committed in:** 76374f07 (Task 1 commit)

**2. [Rule 1 - Bug] Fixed datetime.UTC lint error**
- **Found during:** Task 1 (ORM models)
- **Issue:** ruff UP017 flagged `timezone.utc` as deprecated
- **Fix:** Changed to `datetime.UTC` alias
- **Files modified:** backend/src/storage/models.py, backend/src/storage/repositories.py
- **Verification:** ruff check passes
- **Committed in:** 76374f07, 28b8c83e

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Minor fixes for runtime compatibility and linting. No scope creep.

## Issues Encountered
- pyenv python command not found - used python3 explicitly for verification commands

## User Setup Required

None - database layer uses existing PostgreSQL from docker-compose.

## Next Phase Readiness
- Database models ready for file upload API (02-02)
- DocumentRepository ready for use in upload endpoints
- Migration verified against PostgreSQL - tables created successfully
- All unit tests passing (13/13)

---
*Phase: 02-document-ingestion-pipeline*
*Completed: 2026-01-23*
