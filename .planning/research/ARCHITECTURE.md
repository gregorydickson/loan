# Architecture Research: Loan Document Extraction System

**Domain:** LLM-powered document extraction for loan processing
**Researched:** 2026-01-23
**Confidence:** HIGH (verified with official documentation and multiple sources)

## System Overview

Production document extraction systems follow a **modular, multi-stage pipeline architecture** that separates concerns between ingestion, processing, extraction, validation, and storage. The key insight from industry practice is that **hybrid architectures outperform purely AI-driven solutions** - combining LLM semantic understanding with deterministic validation.

```
                            ┌─────────────────────────────────────────────────────────────┐
                            │                      API Layer (FastAPI)                      │
                            │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
                            │  │ Upload   │  │ Status   │  │ Borrower │  │ Document │     │
                            │  │ Endpoint │  │ Endpoint │  │ Query    │  │ Query    │     │
                            │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘     │
                            └───────┼─────────────┼─────────────┼─────────────┼───────────┘
                                    │             │             │             │
┌───────────────────────────────────┼─────────────┼─────────────┼─────────────┼───────────┐
│                            Processing Layer (Async)          │             │            │
│  ┌────────────────────────────────┴─────────────┴────────────┴┐            │            │
│  │                      Cloud Tasks Queue                      │            │            │
│  └────────────────────────────────┬────────────────────────────┘            │            │
│                                   │                                         │            │
│  ┌────────────────────────────────▼────────────────────────────────────────┐│            │
│  │                         Document Pipeline                                ││            │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ││            │
│  │  │ Ingestion│→│ Docling  │→│ Classify │→│ Extract  │→│ Validate │  ││            │
│  │  │ Service  │  │ Processor│  │ Complex. │  │ (Gemini) │  │ Results  │  ││            │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘  ││            │
│  └─────────────────────────────────────────────────────────────────────────┘│            │
└─────────────────────────────────────────────────────────────────────────────┼────────────┘
                                                                              │
┌─────────────────────────────────────────────────────────────────────────────┼────────────┐
│                              Storage Layer                                  │            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────────────┴──────────┐ │
│  │ Cloud Storage│  │ PostgreSQL   │  │              Query Service                      │ │
│  │ (Documents)  │  │ (Structured) │  │  (Borrowers, Extractions, Source Links)         │ │
│  └──────────────┘  └──────────────┘  └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | Communicates With | Build Phase |
|-----------|----------------|-------------------|-------------|
| **API Layer** | HTTP endpoints, request validation, response formatting | Cloud Tasks, Query Service, PostgreSQL | Phase 1 |
| **Upload Service** | Accept documents, store in GCS, enqueue processing | GCS, Cloud Tasks | Phase 1 |
| **Cloud Tasks Queue** | Async job management, retries, ordering | Document Pipeline workers | Phase 1 |
| **Ingestion Service** | Fetch documents from GCS, prepare for processing | GCS, Docling Processor | Phase 2 |
| **Docling Processor** | Parse PDFs/DOCX to structured text with layout | Complexity Classifier | Phase 2 |
| **Complexity Classifier** | Route simple vs complex documents to appropriate LLM | Extraction Service | Phase 3 |
| **Extraction Service** | LLM orchestration, prompt management, structured output | Gemini API, Validation Service | Phase 3 |
| **Validation Service** | Schema validation, confidence scoring, deterministic checks | Storage Service | Phase 3 |
| **Storage Service** | Persist extractions with source attribution | PostgreSQL | Phase 2 |
| **Query Service** | Borrower lookup, document search, traceability queries | PostgreSQL, API Layer | Phase 4 |

## Recommended Project Structure

Based on the PRD and standard patterns for document extraction systems:

```
backend/
├── src/
│   ├── __init__.py
│   ├── config.py                    # Environment, model configs
│   ├── main.py                      # FastAPI app initialization
│   │
│   ├── api/                         # HTTP Layer
│   │   ├── __init__.py
│   │   ├── dependencies.py          # Dependency injection
│   │   └── routes/
│   │       ├── documents.py         # Upload, status endpoints
│   │       ├── borrowers.py         # Borrower query endpoints
│   │       └── health.py            # Health checks
│   │
│   ├── ingestion/                   # Document Intake
│   │   ├── __init__.py
│   │   ├── document_service.py      # Upload handling, GCS storage
│   │   └── docling_processor.py     # Docling wrapper
│   │
│   ├── extraction/                  # LLM Extraction
│   │   ├── __init__.py
│   │   ├── llm_client.py            # Gemini API wrapper
│   │   ├── complexity_classifier.py # Route to Pro vs Flash
│   │   ├── prompts.py               # Prompt templates
│   │   ├── extractor.py             # Main extraction orchestration
│   │   ├── validation.py            # Schema + deterministic validation
│   │   └── schemas.py               # Pydantic extraction schemas
│   │
│   ├── storage/                     # Persistence
│   │   ├── __init__.py
│   │   ├── models.py                # SQLAlchemy models
│   │   ├── repositories.py          # Data access patterns
│   │   └── gcs_client.py            # Cloud Storage client
│   │
│   └── models/                      # Domain Models
│       ├── __init__.py
│       ├── borrower.py              # Borrower domain model
│       └── document.py              # Document domain model
│
├── tests/
│   ├── unit/                        # Pure unit tests
│   ├── integration/                 # DB + service tests
│   └── e2e/                         # Full pipeline tests
│
└── pyproject.toml
```

### Structure Rationale

- **api/**: Thin HTTP layer - validates input, calls services, formats output. No business logic.
- **ingestion/**: Owns document intake. Docling is isolated here, making it swappable.
- **extraction/**: The "brain" - LLM orchestration, prompting, validation. Most complex component.
- **storage/**: Repository pattern isolates PostgreSQL details from business logic.
- **models/**: Domain models shared across layers. Not tied to DB schema.

## Architectural Patterns

### Pattern 1: Hybrid LLM + Deterministic Validation

**What:** Combine LLM semantic extraction with regex/rule-based validation for critical fields.

**When to use:** Always for production systems extracting structured data.

**Trade-offs:**
- Pro: Significantly higher accuracy, catches LLM hallucinations
- Pro: Deterministic rules provide guardrails and auditability
- Con: More code to maintain (prompts + rules)

**Example:**
```python
# extraction/validation.py
from typing import Literal
from pydantic import BaseModel, field_validator
import re

class BorrowerExtraction(BaseModel):
    """Schema for extracted borrower data with deterministic validation."""

    name: str
    ssn: str | None = None
    address: str
    income_amount: float | None = None
    loan_number: str
    confidence: float

    @field_validator('ssn')
    @classmethod
    def validate_ssn(cls, v: str | None) -> str | None:
        """Deterministic SSN format validation."""
        if v is None:
            return None
        # Remove common separators and validate format
        cleaned = re.sub(r'[-\s]', '', v)
        if not re.match(r'^\d{9}$', cleaned):
            return None  # Reject invalid SSN format
        return f"{cleaned[:3]}-{cleaned[3:5]}-{cleaned[5:]}"

    @field_validator('loan_number')
    @classmethod
    def validate_loan_number(cls, v: str) -> str:
        """Validate loan number format (deterministic)."""
        # Common loan number patterns
        if not re.match(r'^[A-Z]{2,4}[-]?\d{6,12}$', v.upper()):
            raise ValueError(f"Invalid loan number format: {v}")
        return v.upper()
```

### Pattern 2: Source Attribution Chain

**What:** Every extracted field links back to source document, page, and bounding box.

**When to use:** Required for loan document systems - enables audit trails and trust.

**Trade-offs:**
- Pro: Full traceability, enables human review
- Pro: Builds trust in extraction results
- Con: Larger storage footprint
- Con: More complex extraction prompts

**Example:**
```python
# models/extraction.py
from dataclasses import dataclass
from typing import TypedDict

class SourceLocation(TypedDict):
    """Where an extraction came from."""
    document_id: str
    page_number: int
    bounding_box: dict[str, float] | None  # {x, y, width, height}
    text_snippet: str  # Actual text that was extracted from

@dataclass
class ExtractedField:
    """A single extracted field with provenance."""
    field_name: str
    value: str | float | None
    confidence: float
    source: SourceLocation
    extraction_method: Literal["llm", "deterministic", "hybrid"]
```

### Pattern 3: Dynamic Model Selection (Complexity Routing)

**What:** Route documents to appropriate LLM based on complexity assessment.

**When to use:** When you have cost/latency constraints and varying document complexity.

**Trade-offs:**
- Pro: Cost optimization (Flash is cheaper than Pro)
- Pro: Latency optimization for simple documents
- Con: Classification overhead
- Con: Risk of misrouting complex documents

**Example:**
```python
# extraction/complexity_classifier.py
from enum import Enum
from dataclasses import dataclass

class DocumentComplexity(Enum):
    SIMPLE = "simple"    # Single borrower, clear format -> Flash
    STANDARD = "standard"  # Multiple sections, some ambiguity -> Flash
    COMPLEX = "complex"   # Multiple borrowers, tables, poor quality -> Pro

@dataclass
class ClassificationResult:
    complexity: DocumentComplexity
    reasoning: str
    recommended_model: str

def classify_document_complexity(
    page_count: int,
    has_tables: bool,
    has_handwriting: bool,
    text_quality_score: float,  # 0-1, from Docling
    detected_borrowers: int
) -> ClassificationResult:
    """Route document to appropriate model based on complexity."""

    # Simple heuristics - can be enhanced with ML
    if (page_count <= 3 and
        not has_tables and
        not has_handwriting and
        text_quality_score > 0.8 and
        detected_borrowers <= 1):
        return ClassificationResult(
            complexity=DocumentComplexity.SIMPLE,
            reasoning="Single borrower, clear text, few pages",
            recommended_model="gemini-2.5-flash-lite"
        )

    if (has_handwriting or
        text_quality_score < 0.5 or
        detected_borrowers > 2 or
        page_count > 20):
        return ClassificationResult(
            complexity=DocumentComplexity.COMPLEX,
            reasoning="Handwriting/poor quality/many borrowers",
            recommended_model="gemini-3.0-pro-preview"
        )

    return ClassificationResult(
        complexity=DocumentComplexity.STANDARD,
        reasoning="Standard complexity document",
        recommended_model="gemini-2.5-flash"
    )
```

### Pattern 4: Async Processing with Status Tracking

**What:** Separate upload (sync) from processing (async) with status polling.

**When to use:** Always for document processing - extraction takes seconds to minutes.

**Trade-offs:**
- Pro: Immediate upload response, scalable processing
- Pro: Natural retry/recovery semantics
- Con: Client must poll for results
- Con: More infrastructure (queue, workers)

**Example:**
```python
# api/routes/documents.py
from fastapi import APIRouter, UploadFile, BackgroundTasks
from pydantic import BaseModel
from typing import Literal
import uuid

router = APIRouter()

class DocumentStatus(BaseModel):
    document_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    progress_percent: int
    error_message: str | None = None

class UploadResponse(BaseModel):
    document_id: str
    status_url: str
    message: str

@router.post("/documents/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile,
    document_service: DocumentService = Depends(get_document_service),
    task_queue: TaskQueue = Depends(get_task_queue),
) -> UploadResponse:
    """Upload document, return immediately, process async."""

    # 1. Store document in GCS
    document_id = str(uuid.uuid4())
    gcs_path = await document_service.store_document(document_id, file)

    # 2. Create tracking record
    await document_service.create_document_record(
        document_id=document_id,
        filename=file.filename,
        gcs_path=gcs_path,
        status="pending"
    )

    # 3. Enqueue processing task
    await task_queue.enqueue(
        task_type="process_document",
        payload={"document_id": document_id, "gcs_path": gcs_path}
    )

    return UploadResponse(
        document_id=document_id,
        status_url=f"/documents/{document_id}/status",
        message="Document uploaded, processing started"
    )
```

## Data Flow

### Primary Flow: Document Upload to Extraction

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           Upload Phase (Sync)                                 │
│                                                                               │
│  [Client] ──POST /upload──▶ [API] ──store──▶ [GCS]                           │
│                               │                                               │
│                               ├──create record──▶ [PostgreSQL]               │
│                               │                                               │
│                               └──enqueue──▶ [Cloud Tasks]                    │
│                                                                               │
│  Response: {document_id, status_url}                                         │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         Processing Phase (Async)                              │
│                                                                               │
│  [Cloud Tasks] ──invoke──▶ [Worker Endpoint]                                 │
│                                  │                                            │
│                                  ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  Pipeline Steps:                                                         │ │
│  │                                                                          │ │
│  │  1. [Fetch from GCS] ──raw bytes──▶ [Docling]                           │ │
│  │                                         │                                │ │
│  │  2. [Docling] ──DoclingDocument──▶ [Complexity Classifier]              │ │
│  │                                         │                                │ │
│  │  3. [Classifier] ──model selection──▶ [Extraction Service]              │ │
│  │                                         │                                │ │
│  │  4. [Extractor] ──prompt + schema──▶ [Gemini API]                       │ │
│  │                                         │                                │ │
│  │  5. [Gemini] ──structured JSON──▶ [Validation Service]                  │ │
│  │                                         │                                │ │
│  │  6. [Validator] ──validated data──▶ [Storage Service]                   │ │
│  │                                         │                                │ │
│  │  7. [Storage] ──persist──▶ [PostgreSQL]                                 │ │
│  │                              (borrowers, extractions, source_links)      │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│  Update status: "completed" or "failed"                                      │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           Query Phase (Sync)                                  │
│                                                                               │
│  [Client] ──GET /borrowers──▶ [API] ──query──▶ [PostgreSQL]                  │
│                                 │                                             │
│                                 └──▶ Response with source_links               │
│                                      (each field traceable to document)       │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Docling Processing Flow (Detail)

```
[PDF/DOCX Bytes]
      │
      ▼
┌─────────────────────────────────────────────────────┐
│              Docling Processing Pipeline             │
│                                                      │
│  1. Backend Selection (PDF, DOCX, Image, etc.)      │
│                    │                                 │
│                    ▼                                 │
│  2. Text Extraction (programmatic + OCR fallback)   │
│                    │                                 │
│                    ▼                                 │
│  3. Layout Analysis (DocLayNet model)               │
│     - Headers, paragraphs, tables, figures          │
│                    │                                 │
│                    ▼                                 │
│  4. Table Structure Recognition (TableFormer)       │
│                    │                                 │
│                    ▼                                 │
│  5. Reading Order Detection                         │
│                    │                                 │
│                    ▼                                 │
│  6. Document Assembly → DoclingDocument             │
└─────────────────────────────────────────────────────┘
      │
      ▼
[DoclingDocument: structured text with layout info]
      │
      ├──▶ export_to_markdown() → LLM input
      │
      └──▶ export_to_json() → Full structure with positions
```

## Database Schema Design

### Core Tables for Source Attribution

```sql
-- Documents: Original uploads
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(255) NOT NULL,
    gcs_path VARCHAR(500) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    page_count INTEGER,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    error_message TEXT
);

-- Borrowers: Extracted entities
CREATE TABLE borrowers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    ssn_hash VARCHAR(64),  -- Hashed for security
    address TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Extractions: Raw extraction results per document
CREATE TABLE extractions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id),
    borrower_id UUID REFERENCES borrowers(id),
    extraction_data JSONB NOT NULL,  -- Full structured output
    model_used VARCHAR(100) NOT NULL,
    overall_confidence FLOAT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Source Links: Field-level provenance
CREATE TABLE source_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    extraction_id UUID NOT NULL REFERENCES extractions(id),
    field_name VARCHAR(100) NOT NULL,
    field_value TEXT,
    confidence FLOAT NOT NULL,
    page_number INTEGER NOT NULL,
    bounding_box JSONB,  -- {x, y, width, height}
    text_snippet TEXT NOT NULL,  -- Actual source text
    extraction_method VARCHAR(50) NOT NULL  -- 'llm', 'deterministic', 'hybrid'
);

-- Income History: Structured income records
CREATE TABLE income_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    borrower_id UUID NOT NULL REFERENCES borrowers(id),
    extraction_id UUID NOT NULL REFERENCES extractions(id),
    employer_name VARCHAR(255),
    income_amount DECIMAL(12, 2),
    income_period VARCHAR(50),  -- 'annual', 'monthly', 'biweekly'
    start_date DATE,
    end_date DATE,
    confidence FLOAT NOT NULL
);

-- Indexes for common queries
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_extractions_document ON extractions(document_id);
CREATE INDEX idx_extractions_borrower ON extractions(borrower_id);
CREATE INDEX idx_source_links_extraction ON source_links(extraction_id);
CREATE INDEX idx_source_links_field ON source_links(field_name);
CREATE INDEX idx_income_borrower ON income_history(borrower_id);
```

### Schema Rationale

- **documents**: Tracks upload lifecycle, links to GCS storage
- **borrowers**: Deduplicated borrower entities (may span multiple documents)
- **extractions**: One-to-many with documents, stores full extraction per processing run
- **source_links**: Field-level provenance - enables "show me where this came from"
- **income_history**: Normalized income records for structured queries

## Scaling Considerations

| Scale | Documents/Day | Architecture Adjustments |
|-------|---------------|--------------------------|
| 0-100 | ~100 | Single Cloud Run instance, direct Gemini calls |
| 100-1K | ~1,000 | Cloud Tasks for async, connection pooling, basic caching |
| 1K-10K | ~10,000 | Multiple workers, batched Gemini calls, read replicas |
| 10K+ | ~100,000+ | Dedicated extraction service, model caching, sharded storage |

### First Bottleneck: LLM API Rate Limits

**What breaks:** Gemini API has rate limits per minute/day. At scale, you'll hit them.

**How to fix:**
- Implement exponential backoff with jitter
- Batch documents in Cloud Tasks with rate limiting
- Consider dedicated quota or enterprise agreement
- Cache extraction results for duplicate documents (hash-based)

### Second Bottleneck: Docling Processing Time

**What breaks:** Docling's AI models (layout, table extraction) are CPU-intensive.

**How to fix:**
- Run Docling workers on GPU-enabled instances
- Pre-process common document types
- Consider docling-serve for distributed processing
- Cache DoclingDocument results for re-processing

## Anti-Patterns to Avoid

### Anti-Pattern 1: Synchronous Document Processing

**What people do:** Process documents in the upload request handler.

**Why it's wrong:** Document processing takes 5-60+ seconds. HTTP timeouts, client frustration, no recovery on failure.

**Do this instead:** Accept upload, store in GCS, enqueue for async processing, return document_id immediately.

### Anti-Pattern 2: Trusting LLM Output Without Validation

**What people do:** Take LLM JSON output and store directly.

**Why it's wrong:** LLMs hallucinate. SSNs, loan numbers, amounts can be fabricated or malformed.

**Do this instead:** Hybrid validation - Pydantic schema validation + deterministic regex checks for critical fields. Set to null if validation fails rather than storing wrong data.

### Anti-Pattern 3: Losing Source Attribution

**What people do:** Extract data, store only the values without provenance.

**Why it's wrong:** Users ask "where did this number come from?" and you can't answer. Breaks trust, makes debugging impossible.

**Do this instead:** Store source_links for every extracted field - document_id, page_number, text_snippet, bounding_box.

### Anti-Pattern 4: Monolithic Prompt Engineering

**What people do:** One giant prompt that extracts everything at once.

**Why it's wrong:** Hard to debug, hard to improve incrementally, higher token costs on failures.

**Do this instead:** Modular extraction - separate prompts for borrower info, income history, loan details. Compose results.

### Anti-Pattern 5: Ignoring Document Quality Signals

**What people do:** Process all documents identically regardless of quality.

**Why it's wrong:** Scanned documents with poor OCR quality need different handling than digital PDFs.

**Do this instead:** Classify document quality upfront. Route poor-quality docs to more capable (expensive) models. Flag very low quality for human review.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Gemini API | REST via google-generativeai SDK | Use structured output with Pydantic schemas |
| Cloud Storage | google-cloud-storage SDK | Store raw documents, use signed URLs for downloads |
| Cloud Tasks | google-cloud-tasks SDK or fastapi-cloud-tasks | HTTP callbacks to worker endpoints |
| Cloud SQL | SQLAlchemy async with asyncpg | Connection pooling essential |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| API -> Ingestion | Direct function call | Same process, sync for upload |
| Ingestion -> Extraction | Via Cloud Tasks | Async, decoupled |
| Extraction -> Storage | Direct function call | Same worker process |
| API -> Query | Direct function call | Sync database queries |

## Build Order Dependencies

Based on component dependencies, recommended build order:

```
Phase 1: Foundation
├── Project setup, config management
├── PostgreSQL schema + SQLAlchemy models
├── GCS client for document storage
├── Basic FastAPI app with health endpoint
└── Cloud Tasks queue setup

Phase 2: Ingestion Pipeline
├── Document upload endpoint
├── Docling integration
├── DoclingDocument handling
└── Status tracking

Phase 3: Extraction Core
├── Gemini client with structured output
├── Extraction prompts for loan documents
├── Complexity classifier
├── Validation service (hybrid)
└── Source attribution storage

Phase 4: Query Layer
├── Borrower query endpoints
├── Document search
├── Source link resolution
└── Export capabilities

Phase 5: Polish
├── Error handling improvements
├── Retry logic refinement
├── Performance optimization
└── Monitoring/observability
```

## Sources

### Official Documentation (HIGH confidence)
- [Docling GitHub Repository](https://github.com/docling-project/docling) - Core architecture and features
- [Gemini API Structured Output](https://ai.google.dev/gemini-api/docs/structured-output) - Schema definition and best practices
- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/) - Async processing patterns

### Industry Practice (MEDIUM confidence)
- [Designing an LLM-Based Document Extraction System](https://medium.com/@dikshithraj03/turning-messy-documents-into-structured-data-with-llms-d8a6242a31cc) - Hybrid architecture patterns
- [LLMs for Structured Data Extraction from PDFs](https://unstract.com/blog/comparing-approaches-for-using-llms-for-structured-data-extraction-from-pdfs/) - Pipeline approaches
- [Data Extraction in Lending](https://www.docsumo.com/blogs/data-extraction/lending-industry) - Loan-specific patterns
- [Extraction Schema Best Practices](https://landing.ai/developers/extraction-schema-best-practices-get-clean-structured-data-from-your-documents) - Schema design

### Architecture Patterns (MEDIUM confidence)
- [Google Developers Blog - Multi-Agent Patterns](https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/) - Sequential and generator-critic patterns
- [AWS IDP Explanation](https://aws.amazon.com/what-is/intelligent-document-processing/) - IDP component architecture
- [FastAPI and Celery Architecture](https://testdriven.io/blog/fastapi-and-celery/) - Async processing patterns
- [fastapi-cloud-tasks](https://github.com/Adori/fastapi-cloud-tasks) - Cloud Tasks integration

---
*Architecture research for: Loan Document Extraction System*
*Researched: 2026-01-23*
