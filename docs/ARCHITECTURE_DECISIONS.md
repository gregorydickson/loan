# Architecture Decision Records

This document captures the key architectural decisions made during the development of the Loan Document Data Extraction System. Each decision follows the MADR (Markdown Any Decision Records) format to ensure consistent documentation of context, rationale, and consequences.

## Index

- [ADR-001: Use Docling for Document Processing](#adr-001-use-docling-for-document-processing)
- [ADR-002: Use Gemini 3.0 with Dynamic Model Selection](#adr-002-use-gemini-30-with-dynamic-model-selection)
- [ADR-003: Use PostgreSQL for Relational Storage](#adr-003-use-postgresql-for-relational-storage)
- [ADR-004: Deploy on Cloud Run with Serverless Architecture](#adr-004-deploy-on-cloud-run-with-serverless-architecture)
- [ADR-005: Use Next.js 14 App Router for Frontend](#adr-005-use-nextjs-14-app-router-for-frontend)
- [ADR-006: Async Database Sessions with expire_on_commit=False](#adr-006-async-database-sessions-with-expire_on_commitfalse)
- [ADR-007: Repository Pattern with Caller-Controlled Transactions](#adr-007-repository-pattern-with-caller-controlled-transactions)
- [ADR-008: Document Chunking Strategy (4000 tokens, 200 overlap)](#adr-008-document-chunking-strategy-4000-tokens-200-overlap)
- [ADR-009: Deduplication Priority Order (SSN > Account > Fuzzy Name)](#adr-009-deduplication-priority-order-ssn--account--fuzzy-name)
- [ADR-010: Confidence Threshold 0.7 for Review Flagging](#adr-010-confidence-threshold-07-for-review-flagging)
- [ADR-011: CORS Configuration for Local Development](#adr-011-cors-configuration-for-local-development)
- [ADR-012: selectinload() for Eager Loading Relationships](#adr-012-selectinload-for-eager-loading-relationships)

---

## ADR-001: Use Docling for Document Processing

### Status

Accepted

### Context

The system needs to process diverse document formats (PDF, DOCX, and images) to extract text content while preserving structural information like tables, sections, and page boundaries. Document processing is the foundation of the extraction pipeline, and the chosen solution must handle:

- Multi-format support (PDF, DOCX, PNG/JPG)
- OCR for scanned documents and images
- Table extraction with structure preservation
- Page-level metadata for source attribution
- Production-grade reliability for loan documents

Several options were evaluated:

1. **PyPDF2 + python-docx**: Lightweight libraries for specific formats
2. **Unstructured.io**: Cloud-based document processing platform
3. **Apache Tika**: Java-based document processing toolkit
4. **Docling**: IBM's production-grade document understanding library

### Decision

Use Docling (>=2.70.0) as the document processing engine. Create a fresh DocumentConverter instance per document to avoid memory leaks (addressing GitHub issue #2209). Extract page text via `iterate_items()` with provenance tracking for source attribution.

### Consequences

**Positive:**
- Production-grade PDF/DOCX/image parsing with unified API
- Built-in OCR capabilities for scanned documents
- Table extraction with structure preservation (critical for income data)
- Page-level provenance metadata enables source attribution
- Active development by IBM with regular updates

**Negative:**
- Heavy dependency (~500MB with models)
- Slower cold starts on Cloud Run due to model loading
- Requires fresh DocumentConverter per document (memory management)
- Learning curve for provenance-based content extraction

### Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| PyPDF2 + python-docx | Lightweight, fast startup | No OCR, poor table support, separate APIs per format |
| Unstructured.io | Excellent extraction quality | Cloud-based with per-document costs, vendor lock-in |
| Apache Tika | Mature, wide format support | Java runtime required, complex deployment |

---

## ADR-002: Use Gemini 3.0 with Dynamic Model Selection

### Status

Accepted

### Context

The system requires intelligent extraction of structured borrower data (PII, income history, account numbers) from unstructured document text. This requires a Large Language Model capable of:

- Understanding complex document structures
- Extracting entities with high accuracy
- Generating structured output matching Pydantic schemas
- Handling varying document complexity (simple vs. multi-borrower, poor scans)

Cost and performance considerations require balancing extraction quality against API expenses.

### Decision

Use Google Gemini 3.0 with dynamic model selection:
- **gemini-3-flash-preview**: Default for standard loan documents with clear structure (faster, cheaper)
- **gemini-3-pro-preview**: For complex documents with multiple borrowers, poor scan quality, or cross-referenced data (higher reasoning capability)

Critical configuration decisions:
- Temperature=1.0 (lower values cause response looping with Gemini 3)
- No max_output_tokens limit (causes None response with structured output)
- Type-safe token extraction via helper function (handles None usage_metadata)
- RetryError propagation after exhaustion for caller distinction

### Consequences

**Positive:**
- State-of-the-art reasoning capabilities for complex extraction
- Cost optimization through dynamic model selection
- Native structured output support matching Pydantic schemas
- Excellent performance on loan document extraction tasks

**Negative:**
- API costs scale with document volume
- Temperature=1.0 requirement is counterintuitive
- No max_output_tokens is unusual for LLM configuration
- Vendor dependency on Google's API availability

### Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| OpenAI GPT-4 | Excellent quality, mature ecosystem | Higher cost, no dynamic model selection benefit |
| Claude (Anthropic) | Strong reasoning, long context | Different API patterns, no GCP integration |
| Local models (Llama, Mistral) | No API costs, data privacy | Lower extraction quality, infrastructure overhead |
| Azure OpenAI | Enterprise features, SLA | Similar cost to GPT-4, more complex setup |

---

## ADR-003: Use PostgreSQL for Relational Storage

### Status

Accepted

### Context

The system stores structured borrower data with complex relationships:
- Borrowers have multiple income records across years
- Borrowers have multiple account/loan numbers
- Every extracted field requires source attribution (document, page, section)
- Queries need to efficiently join across these relationships

The storage solution must support:
- ACID transactions for data integrity
- Efficient joins for relationship queries
- Async access patterns for the FastAPI backend
- Managed deployment for production reliability

### Decision

Use PostgreSQL with async SQLAlchemy ORM:
- Cloud SQL (PostgreSQL 16) for managed production deployment
- SQLite with aiosqlite for fast unit testing (in-memory)
- Repository pattern with caller-controlled transactions
- `selectinload()` for eager relationship loading to prevent N+1 queries

### Consequences

**Positive:**
- ACID transactions ensure data integrity across related records
- Foreign key constraints maintain referential integrity
- Efficient joins for source attribution queries
- Cloud SQL provides automated backups, point-in-time recovery
- Mature async SQLAlchemy support

**Negative:**
- Schema migrations required for changes (Alembic)
- More complex than document stores for simple use cases
- Cloud SQL has minimum instance costs even at low usage

### Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| MongoDB | Flexible schema, document model | Poor join support, eventual consistency concerns |
| DynamoDB | Serverless, auto-scaling | Limited query patterns, no joins, vendor lock-in |
| Firestore | Real-time updates, GCP native | Poor for relational data, limited query capabilities |
| SQLite (production) | Simple, serverless | Single-writer limitation, not suitable for Cloud Run scaling |

---

## ADR-004: Deploy on Cloud Run with Serverless Architecture

### Status

Accepted

### Context

The system requires a deployment platform that:
- Scales automatically based on demand
- Minimizes operational overhead
- Supports containerized workloads
- Integrates with GCP services (Cloud SQL, Cloud Storage, Secret Manager)
- Provides cost-effective pricing for variable workloads

### Decision

Deploy on Cloud Run using the v2 API with:
- Direct VPC egress for Cloud SQL private IP access (no VPC Connector cost)
- Backend: 1Gi memory for Docling processing, scale 0-10 instances
- Frontend: 512Mi memory, scale 0-5 instances
- Startup probe on /health endpoint with 10s initial delay
- Secret injection via secret_key_ref for DATABASE_URL and GEMINI_API_KEY
- PRIVATE_RANGES_ONLY egress for secure Cloud SQL connectivity

### Consequences

**Positive:**
- Serverless auto-scaling with pay-per-use pricing
- No cluster management overhead (unlike GKE)
- Scale to zero when idle reduces costs
- Native GCP integration (IAM, Secret Manager, Cloud SQL)
- Direct VPC egress eliminates VPC Connector costs

**Negative:**
- Cold start latency (especially with Docling model loading)
- 1Gi memory limit may constrain very large document processing
- Stateless model requires external storage for all state
- Limited to 60-minute request timeout

### Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| GKE (Kubernetes) | Full container orchestration, more control | Cluster management overhead, base cost even when idle |
| Cloud Functions | Event-driven, tighter GCP integration | Limited runtime, no container flexibility |
| Compute Engine | Full control, any configuration | Manual scaling, operational overhead |
| App Engine | Managed, simpler deployment | Less container control, older platform |

---

## ADR-005: Use Next.js 14 App Router for Frontend

### Status

Accepted

### Context

The frontend needs to provide:
- Document upload and management interface
- Borrower search and detail views
- Income visualization with source attribution
- Architecture documentation pages
- Responsive design for desktop and tablet

The framework choice affects development velocity, performance, and deployment complexity.

### Decision

Use Next.js 14+ with App Router:
- Server components reduce client bundle size
- App router provides better code organization
- shadcn/ui (new-york style) with CSS variables for components
- Tailwind CSS v4 for styling
- Inter font for typography
- Standalone output mode for optimized Docker runtime (~100MB vs ~500MB)

Frontend-specific patterns:
- QueryClient with staleTime 60s, retry 1 for queries, 0 for mutations
- API client uses NEXT_PUBLIC_API_URL env var with localhost:8000 default
- useDeferredValue with ref tracking for search to avoid effect state updates

### Consequences

**Positive:**
- Server components reduce client JavaScript bundle
- App router enables intuitive file-based routing
- shadcn/ui provides high-quality, accessible components
- Tailwind v4 with CSS variables enables theme customization
- Standalone build produces small, optimized Docker images

**Negative:**
- App router has learning curve vs pages router
- Server/client component boundaries require careful planning
- shadcn/ui components are copied, not installed (manual updates)
- Tailwind v4 is newer, some ecosystem tools still catching up

### Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Vite + React | Faster dev server, simpler mental model | No SSR built-in, more setup for production |
| Remix | Excellent data loading, nested routes | Smaller ecosystem, different patterns |
| Plain React (CRA) | Simple, familiar | Deprecated, no SSR, larger bundles |
| Astro | Content-focused, fast static sites | Less suitable for interactive dashboards |

---

## ADR-006: Async Database Sessions with expire_on_commit=False

### Status

Accepted

### Context

SQLAlchemy async sessions have a fundamental challenge with lazy loading. When using `expire_on_commit=True` (the default), all loaded objects are expired after commit, causing issues when accessing relationships after the transaction completes. This is particularly problematic with async sessions where:

- Lazy loading is not supported in async mode
- Accessing expired attributes raises errors or triggers sync I/O
- Response serialization happens after commit, requiring access to related objects

### Decision

Configure async sessions with `expire_on_commit=False`:
- Objects remain accessible after commit
- Explicitly load relationships before commit using eager loading strategies
- Accept slight staleness risk in favor of reliable async operation

### Consequences

**Positive:**
- Objects remain accessible after transaction commit
- No unexpected lazy loading exceptions in async context
- Simpler code without defensive reloads
- Compatible with FastAPI response serialization patterns

**Negative:**
- Objects may contain stale data if database changed after commit
- Must be mindful of object lifecycle in long-running operations
- Breaks "session is truth" mental model from sync SQLAlchemy

### Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Default expire_on_commit=True | Guarantees fresh data | Causes lazy loading errors in async |
| Detach and serialize immediately | Clean separation | More complex code, redundant loading |
| Use sync sessions | Avoids async complexity | Blocks event loop, poor performance |

---

## ADR-007: Repository Pattern with Caller-Controlled Transactions

### Status

Accepted

### Context

The system needs clean separation between data access logic and business logic. Key considerations:
- Multiple repository operations may need to be atomic
- Services orchestrate business logic across repositories
- Transaction boundaries should be explicit and controlled
- Testing should be easy with predictable transaction behavior

### Decision

Implement the Repository pattern where:
- Repositories use `flush()` not `commit()` - changes are staged but not committed
- Caller (service or route) controls transaction boundaries via `session.commit()`
- Enables atomic operations across multiple repositories in single transaction

### Consequences

**Positive:**
- Clean separation of concerns (data access vs. business logic)
- Flexible transaction boundaries controlled at service level
- Multiple repository operations can be atomic
- Easy to test repositories in isolation

**Negative:**
- Caller must remember to commit (no auto-commit safety net)
- Slightly more verbose service code
- Risk of uncommitted changes if exception handling incomplete

### Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Repository commits internally | Simpler caller code | No cross-repository atomicity |
| Unit of Work pattern | Explicit transaction container | More complex abstraction |
| Auto-commit sessions | Simple, no manual commits | Poor control, implicit transactions |

---

## ADR-008: Document Chunking Strategy (4000 tokens, 200 overlap)

### Status

Accepted

### Context

Large loan documents often exceed LLM context limits. A document chunking strategy is required to:
- Split documents into processable segments
- Preserve entity boundaries (borrowers, income records)
- Maintain context between chunks
- Balance chunk size against extraction quality

### Decision

Implement chunking with:
- 4000 token maximum per chunk (leaves room for prompt and response)
- 200 token overlap between chunks to preserve entities at boundaries
- Paragraph break detection in last 20% of chunk for clean splits
- Threshold >10 pages for triggering chunking (avoid unnecessary splits)
- Threshold >3 poor quality indicators for flagging complex documents

### Consequences

**Positive:**
- Large documents processable within LLM limits
- Overlap preserves entities that span chunk boundaries
- Paragraph-aware splitting maintains readability
- Configurable thresholds adapt to different document types

**Negative:**
- Overlap increases total token usage (cost)
- Entities at boundaries may be extracted twice (requires deduplication)
- Chunk boundaries may split related information
- Configuration tuning required for optimal results

### Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| No chunking | Simpler, no boundary issues | Fails on large documents |
| Page-based chunking | Natural boundaries | Pages may be too small or large |
| Semantic chunking | Context-aware splits | More complex, slower |
| Sliding window | Even coverage | High token usage, complex merging |

---

## ADR-009: Deduplication Priority Order (SSN > Account > Fuzzy Name)

### Status

Accepted

### Context

The same borrower may appear multiple times across loan documents:
- Different documents reference the same person
- Multiple extractions from chunked documents
- Name variations (John Smith vs. J. Smith)

A reliable deduplication strategy is needed to consolidate borrower records while avoiding false merges.

### Decision

Apply deduplication in strict priority order:
1. **SSN match** (highest confidence): Exact SSN matches are definitive
2. **Account number match**: Same loan/account numbers indicate same borrower
3. **Fuzzy name match (90%+)**: Name similarity with high threshold
4. **High name match (95%+)**: Very similar names without other identifiers

Page finding uses text search fallback to character position estimation when exact matches fail.

### Consequences

**Positive:**
- Unique identifiers (SSN, account) take precedence
- Reduces false positives from name-only matching
- Clear, predictable merge behavior
- Handles name variations gracefully

**Negative:**
- Requires SSN or account for highest confidence merges
- May miss duplicates with different SSNs (data entry errors)
- Fuzzy matching thresholds may need tuning
- No probabilistic scoring (binary match/no-match)

### Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Name-only matching | Simple, always available | High false positive rate |
| Machine learning matching | Learns patterns | Training data required, less predictable |
| Manual review all | Most accurate | Doesn't scale, defeats automation |
| Single identifier only | Simple logic | Misses valid matches |

---

## ADR-010: Confidence Threshold 0.7 for Review Flagging

### Status

Accepted

### Context

LLM extractions vary in quality based on:
- Document clarity (scanned vs. digital)
- Data formatting consistency
- Ambiguous or conflicting information
- Missing required fields

A mechanism is needed to flag uncertain extractions for human review while allowing confident extractions to proceed automatically.

### Decision

Use 0.7 as the confidence threshold:
- Extractions with confidence >= 0.7 proceed automatically
- Extractions with confidence < 0.7 are flagged for human review
- Confidence is computed from field completeness, format validation, and extraction certainty

### Consequences

**Positive:**
- Balances automation with accuracy
- Reduces manual review burden for clear documents
- Predictable threshold for quality control
- Easily adjustable based on operational needs

**Negative:**
- Threshold may be too conservative (unnecessary reviews)
- Threshold may be too lenient (missed errors)
- Single threshold may not suit all field types
- Requires monitoring and tuning over time

### Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Review all | Maximum accuracy | Defeats automation purpose |
| No review | Maximum throughput | Quality issues go uncaught |
| Field-specific thresholds | Tailored to data type | More complex, harder to explain |
| Probabilistic sampling | Statistical quality control | May miss consistent errors |

---

## ADR-011: CORS Configuration for Local Development

### Status

Accepted

### Context

During local development, the frontend and backend run on different ports:
- Backend: localhost:8000 (FastAPI)
- Frontend: localhost:3000 (Next.js dev server)
- Alternative frontend: localhost:5173 (Vite)

Browsers enforce same-origin policy, requiring explicit CORS configuration for cross-origin requests.

### Decision

Configure CORS middleware in FastAPI with multiple development origins:
- localhost:3000 (Next.js)
- localhost:5173 (Vite)
- 127.0.0.1 variants of both ports
- CORS middleware added FIRST before exception handlers and routers

### Consequences

**Positive:**
- Seamless local development with frontend/backend split
- Supports multiple frontend development tools
- No browser security warnings during development
- Explicit origin list (not wildcard) for better security

**Negative:**
- Must remember to update for production origins
- Ordering dependency (must be first middleware)
- Multiple origin configurations to maintain

### Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Wildcard (*) origins | Simple, works everywhere | Security risk, not recommended |
| Proxy through frontend | No CORS needed | More complex setup, hides real requests |
| Same-origin deployment only | No CORS complexity | Can't develop locally with split services |

---

## ADR-012: selectinload() for Eager Loading Relationships

### Status

Accepted

### Context

Borrower queries need to load related data:
- Income records (multiple per borrower)
- Account numbers (multiple per borrower)
- Source references with nested document relationships

SQLAlchemy offers multiple eager loading strategies, each with different performance characteristics.

### Decision

Use `selectinload()` for all relationship loading:
- Prevents N+1 query problems
- Uses efficient IN clause for related records
- Chain selectinload for nested relationships (e.g., source_references -> document)
- search_by_name loads only income_records (list view optimization)
- search_by_account uses unique() to prevent duplicate borrowers from joins

### Consequences

**Positive:**
- Predictable query patterns (one query per relationship level)
- No N+1 performance degradation
- Efficient for collections of any size
- Clear loading intent in query code

**Negative:**
- More verbose query building
- Must explicitly specify all needed relationships
- May over-fetch for simple use cases
- Chained loading can get complex for deep hierarchies

### Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Lazy loading | Simple queries, load on demand | N+1 problems, not async-compatible |
| joinedload() | Single query for all data | Cartesian product explosion with collections |
| subqueryload() | Efficient for large collections | Generates complex subqueries |
| Lazy loading with batching | Balances simplicity and performance | More complex, less predictable |
