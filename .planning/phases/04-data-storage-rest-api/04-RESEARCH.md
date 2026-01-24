# Phase 4: Data Storage & REST API - Research

**Researched:** 2026-01-24
**Domain:** FastAPI REST API with SQLAlchemy async repositories
**Confidence:** HIGH

## Summary

This phase extends the existing document upload API to include:
1. BorrowerRepository for persisting extracted borrower data with relationships
2. Complete REST API endpoints for documents and borrowers
3. Search functionality with pagination

The codebase already has a solid foundation:
- DocumentRepository with async CRUD operations (exists)
- SQLAlchemy ORM models for all entities (exists)
- Alembic async migrations configured (exists)
- FastAPI app with health check and document upload endpoints (exists)
- Dependency injection pattern established (exists)

**Primary recommendation:** Extend the existing repository pattern with BorrowerRepository using `selectinload()` for eager loading relationships, and add borrower endpoints following the established document endpoint patterns.

## Standard Stack

The established libraries/tools for this domain:

### Core (Already Configured)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | >=0.128.0 | REST API framework | Async-first, auto-docs, Pydantic integration |
| SQLAlchemy | >=2.0.46 | ORM with async support | Industry standard, mature async support |
| Pydantic | >=2.12.0 | Request/response validation | Type-safe, FastAPI native |
| asyncpg | >=0.31.0 | PostgreSQL async driver | Fastest Python PostgreSQL driver |
| Alembic | >=1.18.0 | Database migrations | SQLAlchemy native, async support |

### Supporting (Already in pyproject.toml)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | >=0.28.0 | Async HTTP client | Testing API endpoints |
| structlog | >=25.5.0 | Structured logging | Request/error logging |
| python-multipart | >=0.0.18 | File uploads | Already used for document upload |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| offset pagination | cursor pagination | Cursor better for large datasets but more complex; offset fine for expected volume |
| manual search | fastapi-filter | Library adds complexity; manual search adequate for name/account queries |
| custom pagination | fastapi-pagination | Library overhead not needed for simple pagination |

**Installation:** All dependencies already in pyproject.toml - no new dependencies required.

## Architecture Patterns

### Recommended Project Structure (Existing + New)
```
backend/src/
├── api/
│   ├── __init__.py
│   ├── dependencies.py      # (exists) Add BorrowerRepository dependency
│   ├── documents.py         # (exists) Add /status endpoint
│   └── borrowers.py         # (NEW) Borrower endpoints
├── storage/
│   ├── models.py            # (exists) Complete
│   ├── database.py          # (exists) Complete
│   └── repositories.py      # (exists) Add BorrowerRepository
├── main.py                  # (exists) Add CORS, borrower router
└── ...
```

### Pattern 1: Repository with Eager Loading
**What:** Use `selectinload()` for one-to-many relationships in async SQLAlchemy
**When to use:** When fetching borrowers with related income_records, account_numbers, source_references
**Example:**
```python
# Source: SQLAlchemy 2.0 Documentation - Relationship Loading Techniques
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def get_by_id_with_relations(self, borrower_id: UUID) -> Borrower | None:
    """Get borrower with all related entities eagerly loaded."""
    result = await self.session.execute(
        select(Borrower)
        .where(Borrower.id == borrower_id)
        .options(
            selectinload(Borrower.income_records),
            selectinload(Borrower.account_numbers),
            selectinload(Borrower.source_references)
            .selectinload(SourceReference.document),  # Nested eager load
        )
    )
    return result.scalar_one_or_none()
```

### Pattern 2: Pydantic Response Models with from_attributes
**What:** Use `ConfigDict(from_attributes=True)` for ORM model conversion
**When to use:** All response models that map to SQLAlchemy models
**Example:**
```python
# Source: Pydantic V2 Documentation
from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from uuid import UUID

class BorrowerResponse(BaseModel):
    """Response model for borrower details."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    confidence_score: Decimal
    # Related entities as nested models
    income_records: list["IncomeResponse"]
    account_numbers: list["AccountResponse"]
```

### Pattern 3: Search with Optional Query Parameters
**What:** Use optional parameters for flexible search
**When to use:** GET endpoints with search/filter functionality
**Example:**
```python
# Source: FastAPI Query Parameters Documentation
from typing import Annotated
from fastapi import Query

@router.get("/search")
async def search_borrowers(
    name: Annotated[str | None, Query(min_length=2)] = None,
    account_number: Annotated[str | None, Query(min_length=3)] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> BorrowerListResponse:
    """Search borrowers by name or account number."""
    ...
```

### Pattern 4: Transaction Management
**What:** Repository uses flush(), session dependency commits/rollbacks
**When to use:** All database operations
**Example:**
```python
# Source: Existing codebase pattern (repositories.py, database.py)
# Repository: uses flush() to get generated values without committing
async def create(self, borrower: Borrower) -> Borrower:
    self.session.add(borrower)
    await self.session.flush()  # Gets ID without commit
    await self.session.refresh(borrower)
    return borrower

# Database session dependency: commits on success, rollbacks on error
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()  # Caller's changes committed
        except Exception:
            await session.rollback()
            raise
```

### Anti-Patterns to Avoid
- **Lazy loading in async:** Async SQLAlchemy does NOT support lazy loading. Always use eager loading (`selectinload`, `joinedload`) or face greenlet errors.
- **commit() in repositories:** Let the session dependency handle commit/rollback. Repository should only flush().
- **Wildcard CORS in production:** Always specify exact origins, never use `["*"]` with credentials.
- **Raw SQL for search:** Use SQLAlchemy's `ilike()` or `contains()` for search queries.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Offset pagination | Custom pagination logic | Query with `.offset().limit()` | Already in DocumentRepository |
| Name search | Manual string matching | SQLAlchemy `ilike()` | Case-insensitive, SQL-injection safe |
| Error responses | Custom error format | FastAPI HTTPException | Consistent format, auto-docs |
| CORS handling | Custom headers | CORSMiddleware | Handles preflight, credentials |
| UUID validation | Regex validation | FastAPI path parameter typing | Auto-validates UUID format |

**Key insight:** The existing codebase already has patterns for most operations. BorrowerRepository should mirror DocumentRepository patterns.

## Common Pitfalls

### Pitfall 1: Greenlet Error with Lazy Loading
**What goes wrong:** `MissingGreenlet: greenlet_spawn has not been called` when accessing relationships
**Why it happens:** Async SQLAlchemy doesn't support lazy loading; relationships accessed after session closes
**How to avoid:** Always use `selectinload()` or `joinedload()` for relationships needed in response
**Warning signs:** Error only appears at runtime when serializing response

### Pitfall 2: N+1 Query Problem
**What goes wrong:** Database queries multiply with each related entity
**Why it happens:** Not using eager loading for nested relationships
**How to avoid:** Use `selectinload()` chaining: `.options(selectinload(A.bs).selectinload(B.cs))`
**Warning signs:** Slow responses that get worse with more data

### Pitfall 3: CORS Middleware Order
**What goes wrong:** CORS errors persist despite configuration
**Why it happens:** CORSMiddleware not added first; other middleware throws error before CORS headers added
**How to avoid:** Add CORSMiddleware FIRST, before all other middleware and router includes
**Warning signs:** Browser shows CORS error but server logs show different error

### Pitfall 4: Decimal JSON Serialization
**What goes wrong:** `Object of type Decimal is not JSON serializable`
**Why it happens:** Pydantic needs explicit Decimal handling
**How to avoid:** Use `Decimal` type in Pydantic model (already handled in existing models)
**Warning signs:** Error when returning borrower with confidence_score

### Pitfall 5: Missing 404 on Not Found
**What goes wrong:** 500 error instead of 404 when entity not found
**Why it happens:** Not checking if query result is None before processing
**How to avoid:** Always check `if not result: raise HTTPException(status_code=404, ...)`
**Warning signs:** Generic server error in API response

## Code Examples

Verified patterns from official sources and existing codebase:

### BorrowerRepository Create with Relations
```python
# Based on existing DocumentRepository pattern
from collections.abc import Sequence
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.storage.models import (
    Borrower, IncomeRecord, AccountNumber, SourceReference
)

class BorrowerRepository:
    """Repository for Borrower database operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        borrower: Borrower,
        income_records: list[IncomeRecord],
        account_numbers: list[AccountNumber],
        source_references: list[SourceReference],
    ) -> Borrower:
        """Create borrower with all related entities in single transaction."""
        # Add borrower first
        self.session.add(borrower)
        await self.session.flush()  # Get borrower.id

        # Set foreign keys and add related entities
        for record in income_records:
            record.borrower_id = borrower.id
            self.session.add(record)

        for account in account_numbers:
            account.borrower_id = borrower.id
            self.session.add(account)

        for source in source_references:
            source.borrower_id = borrower.id
            self.session.add(source)

        await self.session.flush()
        await self.session.refresh(borrower)
        return borrower
```

### BorrowerRepository Get with Eager Loading
```python
# Source: SQLAlchemy 2.0 Relationship Loading Techniques
async def get_by_id(self, borrower_id: UUID) -> Borrower | None:
    """Get borrower by ID with all relationships loaded."""
    result = await self.session.execute(
        select(Borrower)
        .where(Borrower.id == borrower_id)
        .options(
            selectinload(Borrower.income_records),
            selectinload(Borrower.account_numbers),
            selectinload(Borrower.source_references)
            .selectinload(SourceReference.document),
        )
    )
    return result.scalar_one_or_none()
```

### Search by Name (Case-Insensitive)
```python
# Source: SQLAlchemy ilike() documentation
async def search_by_name(
    self, name: str, limit: int = 100, offset: int = 0
) -> Sequence[Borrower]:
    """Search borrowers by name (case-insensitive partial match)."""
    result = await self.session.execute(
        select(Borrower)
        .where(Borrower.name.ilike(f"%{name}%"))
        .options(selectinload(Borrower.income_records))
        .order_by(Borrower.name)
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()
```

### Search by Account Number
```python
# Source: SQLAlchemy relationship filtering
async def search_by_account(
    self, account_number: str, limit: int = 100, offset: int = 0
) -> Sequence[Borrower]:
    """Search borrowers by account number."""
    result = await self.session.execute(
        select(Borrower)
        .join(Borrower.account_numbers)
        .where(AccountNumber.number.ilike(f"%{account_number}%"))
        .options(
            selectinload(Borrower.income_records),
            selectinload(Borrower.account_numbers),
        )
        .offset(offset)
        .limit(limit)
    )
    return result.unique().scalars().all()  # unique() needed after join
```

### FastAPI CORS Configuration
```python
# Source: FastAPI CORS Documentation
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(...)

# MUST be added FIRST before routers
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",      # Next.js dev
        "http://localhost:5173",      # Vite dev
        # Add production origins here
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Then add routers
app.include_router(documents_router)
app.include_router(borrowers_router)
```

### Custom Exception Handlers
```python
# Source: FastAPI Error Handling Documentation
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

class EntityNotFoundError(Exception):
    """Raised when a requested entity is not found."""
    def __init__(self, entity_type: str, entity_id: str):
        self.entity_type = entity_type
        self.entity_id = entity_id

@app.exception_handler(EntityNotFoundError)
async def entity_not_found_handler(
    request: Request, exc: EntityNotFoundError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "detail": f"{exc.entity_type} not found: {exc.entity_id}"
        },
    )
```

### Borrower Response Models
```python
# Based on existing DocumentResponse patterns
from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from uuid import UUID
from datetime import datetime

class IncomeRecordResponse(BaseModel):
    """Income record in borrower response."""
    model_config = ConfigDict(from_attributes=True)

    amount: Decimal
    period: str
    year: int
    source_type: str
    employer: str | None

class AccountNumberResponse(BaseModel):
    """Account number in borrower response."""
    model_config = ConfigDict(from_attributes=True)

    number: str
    account_type: str

class SourceReferenceResponse(BaseModel):
    """Source reference in borrower response."""
    model_config = ConfigDict(from_attributes=True)

    document_id: UUID
    page_number: int
    section: str | None
    snippet: str

class BorrowerResponse(BaseModel):
    """Full borrower details response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    confidence_score: Decimal
    created_at: datetime
    income_records: list[IncomeRecordResponse]
    account_numbers: list[AccountNumberResponse]
    source_references: list[SourceReferenceResponse]

class BorrowerListResponse(BaseModel):
    """Paginated list of borrowers."""
    borrowers: list[BorrowerResponse]
    total: int
    limit: int
    offset: int
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `orm_mode = True` | `from_attributes=True` | Pydantic v2 (2023) | Already using correct approach |
| `lazy="joined"` default | Explicit `selectinload()` | SQLAlchemy 2.0 | Must specify loading strategy |
| Sync SQLAlchemy | Async SQLAlchemy | SQLAlchemy 1.4/2.0 | Already using async |
| `class Config:` | `model_config = ConfigDict(...)` | Pydantic v2 | Already using correct approach |

**Deprecated/outdated:**
- `orm_mode` in Pydantic - renamed to `from_attributes` (already correct in codebase)
- Lazy loading in async context - not supported, use eager loading

## Open Questions

Things that couldn't be fully resolved:

1. **Total count for pagination**
   - What we know: Current DocumentListResponse uses `len(documents)` which is incorrect for true total
   - What's unclear: Whether to add COUNT query for accurate totals (performance tradeoff)
   - Recommendation: Add separate COUNT query; expected volume is low enough that performance is acceptable

2. **Search across multiple fields**
   - What we know: Requirements specify name and account_number search separately
   - What's unclear: Whether combined search is needed (name AND account_number)
   - Recommendation: Implement as separate query params; can add combined logic if needed

3. **Document status endpoint redundancy**
   - What we know: API-13 requires `GET /api/documents/{id}/status`, but API-12 `GET /api/documents/{id}` already includes status
   - What's unclear: Whether /status is required for polling or if /id suffices
   - Recommendation: Implement /status endpoint for API spec compliance; could be lightweight version

## Sources

### Primary (HIGH confidence)
- FastAPI Official Documentation - CORS, Error Handling, Query Parameters
- SQLAlchemy 2.0 Documentation - [Relationship Loading Techniques](https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html)
- Pydantic V2 Documentation - [Models, from_attributes](https://docs.pydantic.dev/latest/concepts/models/)
- Existing codebase (repositories.py, documents.py, models.py)

### Secondary (MEDIUM confidence)
- [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices) - Repository pattern, dependency injection
- [FastAPI Error Handling Patterns](https://betterstack.com/community/guides/scaling-python/error-handling-fastapi/) - Exception handlers
- [SQLModel Pagination Tutorial](https://sqlmodel.tiangolo.com/tutorial/fastapi/limit-and-offset/) - Offset/limit patterns

### Tertiary (LOW confidence)
- Medium articles on FastAPI patterns (verified against official docs)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Already configured in pyproject.toml
- Architecture: HIGH - Patterns established in existing codebase
- Pitfalls: HIGH - Well-documented async SQLAlchemy gotchas
- Code examples: HIGH - Based on official docs and existing codebase patterns

**Research date:** 2026-01-24
**Valid until:** 2026-02-24 (30 days - stable domain)
