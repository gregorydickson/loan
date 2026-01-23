# Stack Research: Loan Document Extraction System

**Domain:** LLM-powered document extraction for financial/loan documents
**Researched:** 2026-01-23
**Confidence:** HIGH (verified with official sources)

---

## Executive Summary

The recommended stack leverages **Docling** for document processing, **Gemini 3.0** for LLM extraction with native structured output, **FastAPI** for the backend, **PostgreSQL** with async SQLAlchemy for persistence, and **Next.js 15** with shadcn/ui for the frontend. This stack is production-proven, well-supported, and optimized for document extraction use cases.

**Key insight:** Docling handles the document-to-text conversion (OCR, layout, tables), while Gemini 3.0's native structured output mode directly produces validated Pydantic models - eliminating the need for separate validation/parsing layers.

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Docling** | 2.70.0 | Document parsing (PDF, DOCX, images) | IBM Research library with production-grade PDF understanding, table extraction, layout analysis. Native LangChain/LlamaIndex integration. MIT licensed. Handles OCR automatically. |
| **google-genai** | 1.60.0 | Gemini 3.0 API client | Official unified SDK for Gemini models. Native Pydantic structured output support. Replaces deprecated google-generativeai. |
| **FastAPI** | 0.128.0 | REST API framework | Async-first, Pydantic validation, auto-generated OpenAPI docs. 15-20k req/s performance. Industry standard for Python APIs. |
| **SQLAlchemy** | 2.0.46 | ORM with async support | Full async support via asyncpg. Mature, battle-tested, excellent PostgreSQL support. |
| **asyncpg** | 0.31.0 | Async PostgreSQL driver | Purpose-built for asyncio. Recommended driver for SQLAlchemy async. |
| **Pydantic** | 2.12.5 | Data validation & serialization | Powers FastAPI validation. Direct integration with Gemini structured output. JSON Schema generation for LLM prompts. |
| **Next.js** | 15.5 or 16.x | Frontend framework | App Router with React Server Components. Turbopack for fast builds. TypeScript-first. Consider 16.x for latest features. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **tenacity** | 9.0.0+ | Retry with exponential backoff | Always - LLM APIs need retry logic for rate limits and transient failures |
| **instructor** | 1.14.4 | Structured LLM output helper | Optional - Use if Gemini native structured output is insufficient. Adds automatic retries on validation failure |
| **structlog** | 25.5.0 | Structured logging | Always - Async logging with contextvars for request tracing |
| **Alembic** | 1.18.1 | Database migrations | Always - Async template available for SQLAlchemy async |
| **httpx** | 0.28.x | Async HTTP client | For external API calls, health checks |
| **python-multipart** | 0.0.18 | File upload parsing | Required for FastAPI file uploads |
| **@tanstack/react-query** | 5.90.x | Server state management | Always - Handles caching, refetching, optimistic updates |
| **shadcn/ui** | latest | UI component library | Always - Copy-paste components with Tailwind. Accessible, customizable |
| **recharts** | 2.15.x | Data visualization | For dashboard charts, income timelines |

### GCP Infrastructure

| Service | Purpose | Why |
|---------|---------|-----|
| **Cloud Run** | Serverless compute | Auto-scaling, pay-per-use, simple deployment. Up to 24h for jobs. |
| **Cloud SQL (PostgreSQL)** | Managed database | Automatic backups, high availability, GCP-native |
| **Cloud Storage (GCS)** | Document storage | Durable, scalable, signed URLs for secure access |
| **Cloud Tasks** | Async job queue | Decouples document processing from upload requests |
| **Secret Manager** | Secrets storage | API keys, database credentials |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **pytest** | Testing framework | With pytest-asyncio for async test support |
| **pytest-asyncio** | Async test support | Version 1.3.0+, requires Python >=3.10 |
| **pytest-cov** | Coverage reporting | Target >80% coverage |
| **mypy** | Static type checking | Use strict mode for production code |
| **ruff** | Linter + formatter | Fast, replaces flake8/black/isort |

---

## Installation

```bash
# Backend - Core dependencies
pip install \
    fastapi>=0.128.0 \
    uvicorn[standard]>=0.34.0 \
    pydantic>=2.12.0 \
    pydantic-settings>=2.7.0 \
    sqlalchemy[asyncio]>=2.0.46 \
    asyncpg>=0.31.0 \
    alembic>=1.18.0 \
    python-multipart>=0.0.18 \
    docling>=2.70.0 \
    google-genai>=1.60.0 \
    google-cloud-storage>=2.18.0 \
    google-cloud-tasks>=2.18.0 \
    google-cloud-secret-manager>=2.21.0 \
    tenacity>=9.0.0 \
    structlog>=25.5.0 \
    httpx>=0.28.0

# Backend - Dev dependencies
pip install -D \
    pytest>=8.3.0 \
    pytest-asyncio>=1.3.0 \
    pytest-cov>=6.0.0 \
    mypy>=1.14.0 \
    ruff>=0.8.0

# Frontend
npm install \
    next@15 \
    react@18 \
    react-dom@18 \
    @tanstack/react-query@5 \
    recharts@2 \
    lucide-react \
    class-variance-authority \
    clsx \
    tailwind-merge

# Frontend - Dev dependencies
npm install -D \
    typescript@5 \
    @types/node@22 \
    @types/react@18 \
    tailwindcss@3 \
    autoprefixer \
    postcss
```

---

## Alternatives Considered

| Category | Recommended | Alternative | When to Use Alternative |
|----------|-------------|-------------|-------------------------|
| **Document Processing** | Docling | Unstructured.io | If you need hosted processing or broader file format support |
| **Document Processing** | Docling | LlamaParse | If deeply integrated with LlamaIndex ecosystem |
| **Document Processing** | Docling | PyMuPDF + Tesseract | If you need minimal dependencies and simple PDFs only |
| **LLM Provider** | Gemini 3.0 | Claude 3.5 Sonnet | Better for complex reasoning tasks; no native structured output (use tool mode) |
| **LLM Provider** | Gemini 3.0 | GPT-4o | OpenAI ecosystem preference; similar capabilities |
| **LLM Provider** | Gemini 3.0 | Open source (Qwen2.5-VL) | Privacy requirements; need self-hosted; higher ops burden |
| **Structured Output** | Native Gemini | Instructor | If you need complex retry logic, multi-provider support, or validation error feedback loops |
| **ORM** | SQLAlchemy | SQLModel | Simpler API, but less mature async support |
| **Frontend** | Next.js 15 | Remix | Preference for web standards, simpler mental model |
| **Frontend** | Next.js 15 | SvelteKit | Smaller bundle size, but smaller ecosystem |
| **UI Components** | shadcn/ui | Radix UI direct | More control, but more setup work |
| **Cloud Provider** | GCP | AWS | If AWS ecosystem preference; Lambda + S3 + RDS equivalent |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **google-generativeai** (old SDK) | Deprecated. New unified SDK is google-genai | google-genai 1.60.0+ |
| **Pydantic v1** | EOL, missing features. FastAPI deprecation warnings | Pydantic v2.12+ |
| **Flask** | Sync by default, manual validation, no async without extensions | FastAPI |
| **psycopg2** (sync driver) | Blocks async event loop | asyncpg for async, psycopg3 if sync needed |
| **PyPDF2 / pdfminer** | Basic text extraction only, no layout understanding | Docling |
| **Tesseract alone** | OCR only, no document understanding | Docling (includes OCR) |
| **LangChain for extraction** | Overkill for structured extraction; adds complexity | google-genai with native structured output |
| **Create React App** | Deprecated, no SSR, poor DX | Next.js |
| **Material UI (MUI)** | Heavy, opinionated styling, hard to customize | shadcn/ui + Tailwind |
| **REST polling for status** | Inefficient for long-running tasks | WebSockets or Cloud Tasks callbacks |

---

## Stack Patterns by Use Case

**For simple, well-formatted loan documents:**
- Use Gemini 3.0 Flash Preview (`gemini-3-flash-preview`)
- Single-pass extraction
- Cost: ~$0.0003 per document

**For complex, multi-borrower, or poor-quality scans:**
- Use Gemini 3.0 Pro Preview (`gemini-3-pro-preview`)
- Document complexity classifier selects model automatically
- May need multi-pass with chunk overlap
- Cost: ~$0.003 per document

**For high-volume batch processing:**
- Cloud Run Jobs (not Services)
- Parallel processing with Cloud Tasks
- Consider context caching for repeated document templates

**For real-time interactive extraction:**
- Cloud Run Services with min instances > 0
- WebSocket for progress updates
- Optimistic UI updates with React Query

---

## Version Compatibility Matrix

| Package | Requires | Compatible With | Notes |
|---------|----------|-----------------|-------|
| Docling 2.70.0 | Python >=3.10 | SQLAlchemy, FastAPI | Dropped Python 3.9 support |
| google-genai 1.60.0 | Python >=3.10 | httpx, aiohttp | Use [aiohttp] extra for faster async |
| FastAPI 0.128.0 | Python >=3.9 | Pydantic v2 | Full Pydantic v2 native support |
| SQLAlchemy 2.0.46 | Python >=3.7 | asyncpg 0.31.0 | Use postgresql+asyncpg:// URL |
| pytest-asyncio 1.3.0 | Python >=3.10 | pytest 8.x | Use asyncio_mode = "auto" |
| Next.js 15.5 | Node.js >=18.17 | React 18/19 | App Router stable |
| shadcn/ui | Next.js 14/15/16 | Tailwind v3/v4 | May need tw-animate-css for v4 |

**Minimum Python Version:** 3.10 (required by Docling and google-genai)
**Recommended Python Version:** 3.12 (stable, good performance)

---

## Configuration Examples

### Gemini Client with Structured Output

```python
from google import genai
from pydantic import BaseModel

class BorrowerRecord(BaseModel):
    name: str
    address: str
    income_history: list[IncomeRecord]
    account_numbers: list[str]
    confidence_score: float

client = genai.Client(api_key="GEMINI_API_KEY")

response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents=document_text,
    config=genai.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=BorrowerRecord,
        temperature=0.1,  # Low temp for consistent extraction
    )
)

borrower = BorrowerRecord.model_validate_json(response.text)
```

### Async SQLAlchemy with FastAPI

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

engine = create_async_engine(
    "postgresql+asyncpg://user:pass@host/db",
    pool_size=20,
    max_overflow=10,
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

### Tenacity Retry for LLM Calls

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=1, max=60),
    retry=retry_if_exception_type((RateLimitError, ServerError)),
)
async def extract_with_retry(text: str) -> BorrowerRecord:
    return await gemini_client.extract(text, BorrowerRecord)
```

---

## Cost Analysis

### Gemini 3.0 Pricing (as of Jan 2026)

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| gemini-3-flash-preview | $0.075 | $0.30 |
| gemini-3-pro-preview | $2.00 | $12.00 |

### Per-Document Cost Estimates

| Scenario | Model | Avg Tokens | Cost/Doc |
|----------|-------|------------|----------|
| Simple loan doc (5 pages) | Flash | ~2000 in, 500 out | $0.0003 |
| Complex multi-borrower (15 pages) | Pro | ~6000 in, 1500 out | $0.03 |
| Image-heavy with OCR | Flash | ~3000 in, 500 out | $0.0004 |

### Monthly Cost Projections

| Volume | Simple Docs (Flash) | Complex Docs (Pro) |
|--------|--------------------|--------------------|
| 1,000/month | $0.30 | $30 |
| 10,000/month | $3 | $300 |
| 100,000/month | $30 | $3,000 |

**Recommendation:** Use complexity classifier to route 80-90% of documents to Flash, reserving Pro for truly complex cases. This optimizes cost while maintaining accuracy.

---

## Sources

### HIGH Confidence (Official Documentation)

- [Docling PyPI](https://pypi.org/project/docling/) - Version 2.70.0, Python requirements
- [google-genai PyPI](https://pypi.org/project/google-genai/) - Version 1.60.0, unified SDK
- [Gemini API Structured Output](https://ai.google.dev/gemini-api/docs/structured-output) - Native Pydantic support
- [FastAPI Release Notes](https://fastapi.tiangolo.com/release-notes/) - Version 0.128.0
- [SQLAlchemy Async Docs](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) - asyncpg integration
- [pytest-asyncio Docs](https://pytest-asyncio.readthedocs.io/) - Version 1.3.0
- [structlog Docs](https://www.structlog.org/) - Version 25.5.0, async support

### MEDIUM Confidence (Verified with Multiple Sources)

- [Gemini 3 Developer Guide](https://ai.google.dev/gemini-api/docs/gemini-3) - Model capabilities
- [Instructor Library](https://python.useinstructor.com/) - Gemini support, retry patterns
- [shadcn/ui Installation](https://ui.shadcn.com/docs/installation/next) - Next.js 15 support
- [Cloud Run Optimization](https://docs.cloud.google.com/run/docs/tips/python) - Python best practices

### LOW Confidence (Community Sources - Verify Before Use)

- Multimodal LLM vs OCR accuracy comparisons - benchmarks vary significantly
- Specific token counts per document - depends heavily on document characteristics

---

*Stack research for: Loan Document Extraction System*
*Researched: 2026-01-23*
*Confidence: HIGH*
