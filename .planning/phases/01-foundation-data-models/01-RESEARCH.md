# Phase 1: Foundation & Data Models - Research

**Researched:** 2026-01-23
**Domain:** Python project setup, Pydantic data models, Next.js frontend scaffolding, Docker development environment
**Confidence:** HIGH

---

## Summary

This research covers the foundational setup for a Python/TypeScript full-stack application with FastAPI backend and Next.js frontend. The key focus areas are: modern Python project configuration via pyproject.toml, Pydantic v2 data models for extraction output, Docker Compose for local PostgreSQL/Redis, and Next.js 15 with shadcn/ui.

The standard approach uses pyproject.toml with setuptools or hatchling as the build backend, Pydantic v2 models with explicit field definitions and JSON serialization, Docker Compose with health checks for service dependencies, and Next.js App Router with TypeScript strict mode. The 3-day deadline constraint means foundation must be bulletproof to avoid debugging dependency conflicts later.

**Primary recommendation:** Use the exact dependency versions from STACK.md research, enable editable installs for development, configure pytest-asyncio with `asyncio_mode = "auto"`, and use Docker Compose health checks with `depends_on: condition: service_healthy` to ensure proper startup order.

---

## Standard Stack

The established libraries/tools for this domain (versions locked per project research):

### Core Backend
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12 | Runtime | Stable, good performance, required by Docling/google-genai |
| FastAPI | 0.128.0 | REST framework | Async-first, Pydantic v2 native, auto-docs |
| Pydantic | 2.12.5+ | Data validation | JSON Schema generation, FastAPI integration, Gemini structured output |
| pydantic-settings | 2.7.0+ | Environment config | .env file support, type-safe configuration |
| SQLAlchemy | 2.0.46 | ORM | Async support via asyncpg, mature ecosystem |
| asyncpg | 0.31.0 | PostgreSQL driver | Purpose-built for asyncio, fast |
| uvicorn | 0.34.0+ | ASGI server | Standard for FastAPI, hot reload support |

### Core Frontend
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 15.x | React framework | App Router, React Server Components |
| React | 18.x | UI library | Stable with Next.js 15, widely supported |
| TypeScript | 5.x | Type safety | Standard for modern React |
| shadcn/ui | latest | UI components | Copy-paste ownership, Tailwind, accessible |
| TanStack Query | 5.x | Server state | Caching, refetching, mutations |
| Tailwind CSS | 3.x | Styling | Utility-first, shadcn/ui foundation |

### Development Tools
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| pytest | 8.3.0+ | Testing | De facto standard, plugin ecosystem |
| pytest-asyncio | 1.3.0+ | Async test support | Required for async FastAPI tests |
| pytest-cov | 6.0.0+ | Coverage | Coverage reporting for CI |
| mypy | 1.14.0+ | Type checking | Strict mode for production code |
| ruff | 0.8.0+ | Linter/formatter | Fast, replaces flake8/black/isort |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-multipart | 0.0.18+ | File uploads | Required for FastAPI UploadFile |
| httpx | 0.28.x | HTTP client | Testing, external API calls |
| structlog | 25.5.0+ | Logging | Structured async logging |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| setuptools | hatchling | Hatchling simpler for pure Python, setuptools more feature-rich |
| pip | uv | uv much faster but newer, pip more widely supported |
| Tailwind v3 | Tailwind v4 | v4 newer but may have shadcn compatibility issues |

**Installation (Backend):**
```bash
pip install -e ".[dev]"
```

**Installation (Frontend):**
```bash
npm install
npx shadcn@latest init
```

---

## Architecture Patterns

### Recommended Backend Structure

Source: [FastAPI Official Docs](https://fastapi.tiangolo.com/tutorial/bigger-applications/)

```
backend/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Pydantic Settings configuration
│   ├── models/              # Pydantic data models (extraction output)
│   │   ├── __init__.py
│   │   ├── borrower.py      # BorrowerRecord, Address, IncomeRecord
│   │   └── document.py      # DocumentContent, SourceReference
│   ├── api/                 # API layer (later phases)
│   │   ├── __init__.py
│   │   ├── routes/
│   │   └── dependencies.py
│   ├── ingestion/           # Document processing (later phases)
│   ├── extraction/          # LLM extraction (later phases)
│   └── storage/             # Database layer (later phases)
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Shared fixtures
│   └── unit/
│       ├── __init__.py
│       └── test_models.py
├── pyproject.toml
├── Dockerfile
└── .env.example
```

### Recommended Frontend Structure

Source: [Next.js Docs](https://nextjs.org/docs) + [shadcn/ui Installation](https://ui.shadcn.com/docs/installation/next)

```
frontend/
├── src/
│   ├── app/                 # Next.js App Router pages
│   │   ├── layout.tsx       # Root layout with providers
│   │   ├── page.tsx         # Home page
│   │   └── globals.css      # Global styles + Tailwind
│   ├── components/
│   │   └── ui/              # shadcn/ui components (auto-generated)
│   └── lib/
│       ├── utils.ts         # shadcn cn() utility
│       └── api.ts           # API client (later phases)
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── next.config.js
├── components.json          # shadcn/ui config
└── Dockerfile
```

### Pattern 1: Pydantic Model with Nested Types

**What:** Define data models with explicit field types and nested structures
**When to use:** All extraction output models
**Example:**
```python
# Source: https://docs.pydantic.dev/latest/concepts/models/
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class Address(BaseModel):
    """Structured address from loan documents."""
    street: str = Field(..., min_length=1, description="Street address line")
    city: str = Field(..., min_length=1)
    state: str = Field(..., min_length=2, max_length=2, description="Two-letter state code")
    zip_code: str = Field(..., pattern=r"^\d{5}(-\d{4})?$")
    country: str = Field(default="USA")


class IncomeRecord(BaseModel):
    """Single income entry from loan documents."""
    amount: Decimal = Field(..., gt=0, description="Income amount in USD")
    period: str = Field(..., description="Income period: annual, monthly, weekly")
    year: int = Field(..., ge=1900, le=2100)
    source_type: str = Field(..., description="Employment, self-employment, other")
    employer: str | None = Field(default=None)

    @field_validator("period")
    @classmethod
    def validate_period(cls, v: str) -> str:
        allowed = {"annual", "monthly", "weekly", "biweekly"}
        if v.lower() not in allowed:
            raise ValueError(f"period must be one of {allowed}")
        return v.lower()


class SourceReference(BaseModel):
    """Attribution to source document for traceability."""
    document_id: UUID
    document_name: str
    page_number: int = Field(..., ge=1)
    section: str | None = Field(default=None)
    snippet: str = Field(..., max_length=500, description="Text snippet for context")


class BorrowerRecord(BaseModel):
    """Complete borrower extraction result."""
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1)
    address: Address | None = Field(default=None)
    income_history: list[IncomeRecord] = Field(default_factory=list)
    account_numbers: list[str] = Field(default_factory=list)
    loan_numbers: list[str] = Field(default_factory=list)
    sources: list[SourceReference] = Field(default_factory=list)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"from_attributes": True}  # ORM mode for SQLAlchemy
```

### Pattern 2: Pydantic Settings Configuration

**What:** Type-safe environment configuration with .env support
**When to use:** Application configuration
**Example:**
```python
# Source: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/loan_extraction",
        description="Async PostgreSQL connection URL",
    )
    db_pool_size: int = Field(default=20, ge=1, le=100)
    db_max_overflow: int = Field(default=10, ge=0, le=50)

    # Redis
    redis_url: RedisDsn = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # API
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000, ge=1, le=65535)
    debug: bool = Field(default=False)

    # Gemini (for later phases)
    gemini_api_key: str = Field(default="", description="Google AI API key")


settings = Settings()
```

### Pattern 3: pyproject.toml Configuration

**What:** Modern Python project configuration
**When to use:** All Python projects
**Example:**
```toml
# Source: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/
[build-system]
requires = ["setuptools>=75.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "loan-extraction-backend"
version = "0.1.0"
description = "Loan document data extraction system backend"
readme = "README.md"
requires-python = ">=3.10"
license = "MIT"

dependencies = [
    "fastapi>=0.128.0",
    "uvicorn[standard]>=0.34.0",
    "pydantic>=2.12.0",
    "pydantic-settings>=2.7.0",
    "sqlalchemy[asyncio]>=2.0.46",
    "asyncpg>=0.31.0",
    "alembic>=1.18.0",
    "python-multipart>=0.0.18",
    "httpx>=0.28.0",
    "structlog>=25.5.0",
    # Phase 2+ dependencies (include now to avoid conflicts later)
    "docling>=2.70.0",
    "google-genai>=1.60.0",
    "google-cloud-storage>=2.18.0",
    "tenacity>=9.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=1.3.0",
    "pytest-cov>=6.0.0",
    "mypy>=1.14.0",
    "ruff>=0.8.0",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["src*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
addopts = "-v --cov=src --cov-report=term-missing --cov-fail-under=80"

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]
exclude = ["tests/", "alembic/"]

[tool.pydantic-mypy]
init_forbid_extra = true
init_typed = true
warn_required_dynamic_aliases = true

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]
ignore = ["E501"]  # Line length handled by formatter

[tool.ruff.format]
quote-style = "double"
```

### Pattern 4: Docker Compose with Health Checks

**What:** Local development environment with proper service dependencies
**When to use:** Local development
**Example:**
```yaml
# Source: https://docs.docker.com/compose/how-tos/startup-order/
version: "3.8"

services:
  postgres:
    image: postgres:16-alpine
    container_name: loan-postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: loan_extraction
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d loan_extraction"]
      interval: 5s
      timeout: 5s
      retries: 5
      start_period: 10s

  redis:
    image: redis:7-alpine
    container_name: loan-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 3

volumes:
  postgres_data:
  redis_data:
```

### Anti-Patterns to Avoid

- **Using requirements.txt for application dependencies:** Use pyproject.toml for reproducible builds and proper dependency resolution
- **Mixing sync and async database drivers:** Use asyncpg exclusively with SQLAlchemy async, never psycopg2
- **Sharing AsyncSession across concurrent tasks:** Create new sessions per request/task
- **Missing health checks in Docker Compose:** Services may start before databases are ready
- **Using deprecated google-generativeai:** Use google-genai 1.60.0+ instead
- **Pydantic v1 patterns:** Use v2 syntax (model_dump not dict, model_validate not parse_obj)

---

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Environment config | Manual os.environ parsing | pydantic-settings | Type validation, .env support, nested configs |
| JSON serialization | Custom encoder classes | Pydantic model_dump_json() | Handles datetime, UUID, Decimal automatically |
| Field validation | if/else validation logic | Pydantic Field() + validators | Declarative, generates JSON Schema |
| API documentation | Manual OpenAPI writing | FastAPI auto-generation | Always in sync with code |
| Datetime handling | naive datetime.now() | datetime.now(timezone.utc) | Timezone-aware, avoids deprecation warnings |
| UUID generation | Manual string handling | uuid4() with Pydantic UUID type | Type safety, automatic serialization |

**Key insight:** Pydantic v2 handles most data transformation needs - datetime serialization, UUID conversion, nested model validation. Don't write custom serializers unless you have a specific format requirement not covered by `model_dump(mode='json')`.

---

## Common Pitfalls

### Pitfall 1: Editable Install Without Build Backend
**What goes wrong:** `pip install -e .` fails with "Project has a 'pyproject.toml' and its build backend is missing the 'build_editable' hook"
**Why it happens:** pyproject.toml missing or misconfigured [build-system] table
**How to avoid:** Always include:
```toml
[build-system]
requires = ["setuptools>=75.0", "wheel"]
build-backend = "setuptools.build_meta"
```
**Warning signs:** Error message about PEP 660 or build_editable hook

### Pitfall 2: asyncpg Connection Pool Not Released
**What goes wrong:** Application runs out of database connections after task cancellations
**Why it happens:** asyncpg connections not returned to pool when asyncio task is cancelled
**How to avoid:** Use proper context managers and consider shielding cleanup:
```python
async with AsyncSession(engine) as session:
    async with session.begin():
        # ... database operations
```
**Warning signs:** "Too many connections" errors under load, connections growing over time

### Pitfall 3: pytest-asyncio Mode Not Set
**What goes wrong:** Async tests fail with "coroutine was never awaited" or require manual @pytest.mark.asyncio
**Why it happens:** pytest-asyncio 1.0+ changed default behavior
**How to avoid:** Set in pyproject.toml:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```
**Warning signs:** Having to add @pytest.mark.asyncio to every test

### Pitfall 4: Pydantic v1 vs v2 API Confusion
**What goes wrong:** Code using deprecated methods fails or behaves unexpectedly
**Why it happens:** Many tutorials/examples still show v1 patterns
**How to avoid:** Use v2 patterns exclusively:
| v1 Pattern | v2 Pattern |
|------------|------------|
| `.dict()` | `.model_dump()` |
| `.json()` | `.model_dump_json()` |
| `parse_obj()` | `model_validate()` |
| `Config` class | `model_config = ConfigDict(...)` |
| `validator` | `field_validator` or `model_validator` |
**Warning signs:** Deprecation warnings in Pydantic output

### Pitfall 5: Next.js TypeScript Paths Not Working
**What goes wrong:** "Module not found: Can't resolve '@/components/...'"
**Why it happens:** Missing baseUrl in tsconfig.json
**How to avoid:** Ensure tsconfig.json has:
```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```
**Warning signs:** Absolute imports failing while relative imports work

### Pitfall 6: Docker Compose Services Starting Before DB Ready
**What goes wrong:** Application fails to connect to database on startup
**Why it happens:** `depends_on` without condition only waits for container start, not service ready
**How to avoid:** Use health check condition:
```yaml
depends_on:
  postgres:
    condition: service_healthy
```
**Warning signs:** Intermittent startup failures, "connection refused" on first boot

### Pitfall 7: mypy Missing Pydantic Plugin
**What goes wrong:** False positives about BaseModel.__init__ signatures
**Why it happens:** mypy doesn't understand Pydantic's dynamic field generation
**How to avoid:** Enable plugin in pyproject.toml:
```toml
[tool.mypy]
plugins = ["pydantic.mypy"]

[tool.pydantic-mypy]
init_forbid_extra = true
init_typed = true
```
**Warning signs:** Type errors on valid Pydantic model instantiation

---

## Code Examples

Verified patterns from official sources:

### Pydantic Model JSON Serialization

Source: [Pydantic Serialization Docs](https://docs.pydantic.dev/latest/concepts/serialization/)

```python
from datetime import datetime, timezone
from uuid import uuid4
from pydantic import BaseModel, Field

class BorrowerRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    confidence_score: float
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Create instance
borrower = BorrowerRecord(name="John Doe", confidence_score=0.85)

# Serialize to Python dict (keeps datetime as datetime object)
data_dict = borrower.model_dump()
# {'id': '...', 'name': 'John Doe', 'confidence_score': 0.85, 'extracted_at': datetime(...)}

# Serialize to JSON-compatible dict (datetime becomes ISO string)
json_dict = borrower.model_dump(mode='json')
# {'id': '...', 'name': 'John Doe', 'confidence_score': 0.85, 'extracted_at': '2026-01-23T...'}

# Serialize directly to JSON string
json_str = borrower.model_dump_json()
# '{"id":"...","name":"John Doe","confidence_score":0.85,"extracted_at":"2026-01-23T..."}'

# Deserialize from dict
borrower2 = BorrowerRecord.model_validate(json_dict)

# Deserialize from JSON string
borrower3 = BorrowerRecord.model_validate_json(json_str)
```

### FastAPI App Entry Point with Lifespan

Source: [FastAPI Docs](https://fastapi.tiangolo.com/advanced/events/)

```python
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.config import settings

# Create async engine
engine = create_async_engine(
    str(settings.database_url),
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan - startup and shutdown."""
    # Startup: verify database connection
    async with engine.begin() as conn:
        # Could run initial checks here
        pass

    yield  # Application runs

    # Shutdown: dispose connection pool
    await engine.dispose()


app = FastAPI(
    title="Loan Document Extraction API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}
```

### Next.js 15 Root Layout with Providers

Source: [Next.js Docs](https://nextjs.org/docs/app/building-your-application/routing/layouts-and-templates)

```typescript
// src/app/layout.tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Loan Document Extraction",
  description: "Extract borrower data from loan documents",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <main className="min-h-screen bg-background">
          {children}
        </main>
      </body>
    </html>
  );
}
```

### shadcn/ui Button Usage

Source: [shadcn/ui Docs](https://ui.shadcn.com/docs/components/button)

```typescript
// After running: npx shadcn@latest add button
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="space-y-4 text-center">
        <h1 className="text-4xl font-bold">Loan Document Extraction</h1>
        <p className="text-muted-foreground">
          Upload documents to extract borrower data
        </p>
        <Button size="lg">Get Started</Button>
      </div>
    </div>
  );
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| requirements.txt | pyproject.toml | PEP 621 (2021), widespread 2023+ | Single source of truth for project config |
| Pydantic v1 | Pydantic v2 | July 2023 | 5-50x faster, new API surface |
| google-generativeai | google-genai | 2025 | Unified SDK, Pydantic structured output |
| Next.js Pages Router | App Router | Next.js 13 (2022), stable 14+ | Server Components, streaming |
| setup.py | pyproject.toml [project] | PEP 621/660 | Declarative config, no Python execution |
| Flask | FastAPI | 2018+ adoption | Async native, auto-validation, auto-docs |
| psycopg2 | asyncpg | For async apps | Non-blocking PostgreSQL |

**Deprecated/outdated:**
- `google-generativeai` package: Use `google-genai` 1.60.0+
- Pydantic `.dict()`, `.json()`: Use `.model_dump()`, `.model_dump_json()`
- `datetime.utcnow()`: Use `datetime.now(timezone.utc)`
- `Optional[X]` syntax: Prefer `X | None` in Python 3.10+
- Next.js `pages/` directory: Use `app/` with App Router for new projects

---

## Open Questions

Things that couldn't be fully resolved:

1. **Exact Docling version compatibility with Python 3.12**
   - What we know: Docling 2.70.0 requires Python >=3.10
   - What's unclear: Any edge cases with 3.12 specifically
   - Recommendation: Install early in Phase 1, test `import docling` succeeds

2. **shadcn/ui Tailwind v4 compatibility**
   - What we know: shadcn/ui works with Tailwind v3, v4 support in progress
   - What's unclear: Whether to use v3 or v4 for this project
   - Recommendation: Use Tailwind v3 (stable), match create-next-app defaults

3. **pytest-asyncio fixture scope changes in 1.3.0**
   - What we know: Default loop scope changed in recent versions
   - What's unclear: Best practice for test isolation
   - Recommendation: Explicitly set `asyncio_default_fixture_loop_scope = "function"`

---

## Sources

### Primary (HIGH confidence)
- [Python Packaging Guide - pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) - Build system, project metadata
- [Pydantic v2 Models](https://docs.pydantic.dev/latest/concepts/models/) - Model definition, validation, serialization
- [Pydantic v2 Serialization](https://docs.pydantic.dev/latest/concepts/serialization/) - JSON output patterns
- [FastAPI Bigger Applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/) - Project structure, APIRouter
- [shadcn/ui Next.js Installation](https://ui.shadcn.com/docs/installation/next) - Frontend setup
- [pytest-asyncio Configuration](https://pytest-asyncio.readthedocs.io/en/latest/reference/configuration.html) - Test mode settings
- [Docker Compose Startup Order](https://docs.docker.com/compose/how-tos/startup-order/) - Health checks

### Secondary (MEDIUM confidence)
- [FastAPI Best Practices GitHub](https://github.com/zhanymkanov/fastapi-best-practices) - Community patterns verified with official docs
- [Pydantic mypy Integration](https://docs.pydantic.dev/latest/integrations/mypy/) - Plugin configuration
- [Next.js TypeScript](https://nextjs.org/docs/pages/api-reference/config/typescript) - tsconfig paths

### Tertiary (LOW confidence)
- Various Medium articles on FastAPI structure - Patterns vary, use official docs as authority
- GitHub issues on asyncpg connection pooling - Specific edge cases, may not apply

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Versions from project STACK.md research, verified with official sources
- Architecture: HIGH - Patterns from official FastAPI/Next.js/Pydantic documentation
- Pitfalls: HIGH - Documented issues with official workarounds

**Research date:** 2026-01-23
**Valid until:** 2026-02-23 (30 days - stable technologies)
