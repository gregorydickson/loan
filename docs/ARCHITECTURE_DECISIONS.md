# Architecture Decision Records

This document captures the key architectural decisions made during the development of the Loan Document Data Extraction System. Each decision follows the MADR (Markdown Any Decision Records) format to ensure consistent documentation of context, rationale, and consequences.

## Index

- [ADR-001: Use Docling for Document Processing](#adr-001-use-docling-for-document-processing)
- [ADR-002: Use Gemini 3.0 with Dynamic Model Selection](#adr-002-use-gemini-30-with-dynamic-model-selection)
- [ADR-003: Use PostgreSQL for Relational Storage](#adr-003-use-postgresql-for-relational-storage)
- [ADR-004: Deploy on Cloud Run with Serverless Architecture](#adr-004-deploy-on-cloud-run-with-serverless-architecture)
- [ADR-005: Use Next.js 14 App Router for Frontend](#adr-005-use-nextjs-14-app-router-for-frontend)

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
