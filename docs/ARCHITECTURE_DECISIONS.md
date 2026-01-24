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
- [ADR-013: Private VPC for Cloud SQL (No Public IP)](#adr-013-private-vpc-for-cloud-sql-no-public-ip)
- [ADR-014: Secret Manager for Credentials](#adr-014-secret-manager-for-credentials)
- [ADR-015: pytest-asyncio Auto Mode for Testing](#adr-015-pytest-asyncio-auto-mode-for-testing)
- [ADR-016: In-Memory SQLite for Unit Tests](#adr-016-in-memory-sqlite-for-unit-tests)
- [ADR-017: Income Anomaly Thresholds (50% drop, 300% spike)](#adr-017-income-anomaly-thresholds-50-drop-300-spike)

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

---

## ADR-013: Private VPC for Cloud SQL (No Public IP)

### Status

Accepted

### Context

The Cloud SQL PostgreSQL instance contains sensitive borrower data (PII, SSNs, income history). Security best practices require:
- Minimizing attack surface
- Network-level access control
- No direct internet exposure for database

GCP offers two connectivity modes:
- Public IP with authorized networks
- Private IP via VPC peering

### Decision

Configure Cloud SQL with private IP only:
- `ipv4_enabled=false` in Terraform configuration
- VPC peering between project VPC and Cloud SQL services
- Cloud Run accesses via direct VPC egress with PRIVATE_RANGES_ONLY
- No public IP means no internet-accessible attack surface

### Consequences

**Positive:**
- Database not accessible from public internet
- Reduced attack surface for sensitive data
- Compliant with security best practices
- Network-level isolation from other GCP projects

**Negative:**
- Cannot connect directly from local development machines
- Requires Cloud SQL Auth Proxy for local access
- More complex initial setup
- Debugging production requires VPC access

### Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Public IP with authorized networks | Simple local connectivity | Internet-accessible, requires IP management |
| Private IP + Cloud SQL Proxy | Secure, local access via proxy | Extra component to manage |
| Private IP + VPN | Secure tunnel for all access | Complex VPN setup |

---

## ADR-014: Secret Manager for Credentials

### Status

Accepted

### Context

The application requires sensitive credentials:
- DATABASE_URL (PostgreSQL connection string with password)
- GEMINI_API_KEY (API key for LLM service)
- Potentially other service credentials

These credentials should not be:
- Hardcoded in source code
- Stored in Terraform state files
- Visible in container environment dumps

### Decision

Store all credentials in Google Cloud Secret Manager:
- Create secrets via Terraform (secret exists, not the value)
- Secret values added manually or via secure pipeline
- Cloud Run injects secrets via `secret_key_ref` in environment variables
- Per-secret IAM bindings for Cloud Run service account

### Consequences

**Positive:**
- Credentials not in source control
- Credentials not in Terraform state
- Audit trail for secret access
- Rotation without redeployment (via secret versions)
- Fine-grained IAM for secret access

**Negative:**
- Manual step to populate secret values
- Additional GCP service to manage
- Requires proper IAM setup
- Local development needs alternative credential source

### Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Environment variables in Terraform | Simple, all-in-one | Secrets visible in state, source control risk |
| Kubernetes secrets | K8s native | Cloud Run doesn't use K8s secrets |
| HashiCorp Vault | Feature-rich, multi-cloud | Additional infrastructure |
| .env files in containers | Simple | Baked into images, rotation requires rebuild |

---

## ADR-015: pytest-asyncio Auto Mode for Testing

### Status

Accepted

### Context

The backend uses async/await extensively:
- Async database sessions (SQLAlchemy)
- Async HTTP clients (httpx)
- Async FastAPI endpoints

Testing async code requires proper event loop management. pytest-asyncio offers two modes:
- Strict mode: Requires explicit `@pytest.mark.asyncio` on each test
- Auto mode: Automatically handles async fixtures and tests

### Decision

Configure pytest-asyncio with `asyncio_mode = "auto"` in pyproject.toml:
- Async fixtures automatically get event loops
- Async tests run without explicit marks
- Consistent async handling across all test files

### Consequences

**Positive:**
- Less boilerplate (no `@pytest.mark.asyncio` everywhere)
- Consistent async handling
- Easier to write async tests correctly
- Fixtures and tests use same event loop

**Negative:**
- Implicit behavior may surprise developers used to strict mode
- All async defs treated as tests (watch naming)
- Harder to mix sync and async in same module

### Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Strict mode | Explicit, clear intent | Verbose, easy to forget marks |
| Manual event loop | Full control | Complex, error-prone |
| anyio testing | Multi-async-framework support | Different patterns, less pytest integration |

---

## ADR-016: In-Memory SQLite for Unit Tests

### Status

Accepted

### Context

Unit tests require fast, isolated database access:
- Each test should start with clean state
- Tests should not affect each other
- Test suite should run quickly (hundreds of tests)
- Schema should match production (mostly)

Options include:
- PostgreSQL in Docker
- SQLite file-based
- SQLite in-memory
- Mock database entirely

### Decision

Use SQLite with aiosqlite for in-memory async testing:
- `sqlite+aiosqlite:///:memory:` connection string
- Fresh database per test fixture
- Tables created from SQLAlchemy models
- Fast execution (no disk, no network)

### Consequences

**Positive:**
- Very fast test execution
- Perfect isolation (each test gets fresh DB)
- No external dependencies
- Works in CI without Docker

**Negative:**
- SQLite differs from PostgreSQL in some behaviors
- Some PostgreSQL-specific features not testable
- In-memory DB lost after test (no debugging persistence)
- May miss PostgreSQL-specific bugs

### Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| PostgreSQL in Docker | Production parity | Slower, requires Docker in CI |
| SQLite file-based | Persistence for debugging | Slower, cleanup complexity |
| Mock database | Fastest | No real SQL testing, fake behavior |
| Test containers | Real PostgreSQL, isolated | Slower startup, requires Docker |

---

## ADR-017: Income Anomaly Thresholds (50% drop, 300% spike)

### Status

Accepted

### Context

Loan underwriting requires accurate income assessment. Borrowers may have:
- Legitimate income changes (job change, promotion)
- Data entry errors
- Fraudulent income inflation

The system should flag suspicious income patterns for review while not flagging normal variations.

### Decision

Implement income anomaly detection with specific thresholds:
- **50% drop**: Flag if year-over-year income decreases more than 50%
- **300% spike**: Flag if year-over-year income increases more than 300%

Consistency checks run AFTER deduplication and flag items for review without auto-resolving.

Cross-document checks use normalized names for matching.

### Consequences

**Positive:**
- Catches significant anomalies (data errors, potential fraud)
- Allows normal income variations (raises, bonuses)
- Clear, explainable thresholds
- Flags for review, doesn't reject

**Negative:**
- May miss sophisticated manipulation
- May flag legitimate major career changes
- Single threshold may not suit all income types
- Requires human review to resolve flags

### Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| No anomaly detection | Simple, no false positives | Misses errors and fraud |
| Tighter thresholds (20%/150%) | Catches more variations | Too many false positives |
| Industry-specific thresholds | Tailored accuracy | Complex rules, more maintenance |
| ML-based detection | Learns patterns | Training data, less explainable |

---

## Decision Log by Phase

This table maps each ADR to the development phase where the decision originated.

| Phase | ADRs |
|-------|------|
| 01. Foundation & Data Models | ADR-005 (Next.js), ADR-015 (pytest-asyncio), ADR-016 (In-Memory SQLite) |
| 02. Document Ingestion Pipeline | ADR-001 (Docling), ADR-006 (expire_on_commit), ADR-007 (Repository Pattern) |
| 03. LLM Extraction & Validation | ADR-002 (Gemini), ADR-008 (Chunking), ADR-009 (Deduplication), ADR-010 (Confidence), ADR-017 (Anomaly Thresholds) |
| 04. Data Storage & REST API | ADR-003 (PostgreSQL), ADR-011 (CORS), ADR-012 (selectinload) |
| 05. Frontend Dashboard | (Covered by ADR-005) |
| 06. GCP Infrastructure | ADR-004 (Cloud Run), ADR-013 (Private VPC), ADR-014 (Secret Manager) |
| 07. Documentation & Testing | (Meta-documentation of all above) |

---

*Last updated: 2026-01-24*
