# Loan Document Data Extraction System

## What This Is

A production-grade AI-powered system that extracts structured borrower information from unstructured loan documents. Processes PDF, DOCX, and image files using Docling for document understanding and Gemini 3.0 for intelligent data extraction. Stores structured data in PostgreSQL, serves via FastAPI REST API, and presents through a modern Next.js frontend. Fully deployed on Google Cloud Platform with Infrastructure as Code.

Built as a portfolio project to demonstrate full-stack engineering capabilities, test-driven development practices, parallel execution optimization, and cloud-native architecture.

## Core Value

**Accurate extraction of borrower data with complete traceability.** Every extracted field (PII, income history, account/loan numbers) must include source attribution showing which document and page it came from, with confidence scoring to flag data needing manual review.

## Requirements

### Validated

(None yet — ship to validate)

### Active

#### System Design & Documentation
- [ ] Architecture overview with component diagrams showing all major system components
- [ ] Data pipeline design covering ingestion → processing → storage → retrieval
- [ ] AI/LLM integration strategy with model selection rationale (Gemini 3.0 Pro vs Flash)
- [ ] Document format handling approach for PDF, DOCX, images
- [ ] Scaling analysis for 10x and 100x document volumes with cost projections
- [ ] Technical trade-offs documentation with reasoning
- [ ] Error handling strategy and data quality validation approach
- [ ] README with setup/run instructions and architecture summary

#### Document Ingestion Pipeline
- [ ] Docling integration for processing PDF, DOCX, PNG/JPG documents
- [ ] Text extraction preserving structure (tables, sections, page boundaries)
- [ ] Document storage in Google Cloud Storage with metadata
- [ ] Document metadata tracking in PostgreSQL (filename, hash, status, timestamps)
- [ ] Duplicate detection via file hashing
- [ ] Processing error handling with graceful degradation

#### LLM Extraction Engine
- [ ] Gemini API client with retry logic and exponential backoff
- [ ] Document complexity classification for dynamic model selection
- [ ] Structured output generation validated against Pydantic schemas
- [ ] Chunking strategy for large documents (4000 tokens, 200 token overlap)
- [ ] Source attribution tracking (document ID, page number, section, snippet)
- [ ] Confidence scoring algorithm (0.0-1.0 scale, <0.7 flagged for review)
- [ ] Deduplication logic for borrower records across multiple documents
- [ ] Data quality validation (SSN, phone, zip code format checking)

#### Data Storage Layer
- [ ] PostgreSQL database with async SQLAlchemy ORM
- [ ] Models: Document, Borrower, IncomeRecord, AccountNumber, SourceReference
- [ ] Repository pattern for data access with transaction management
- [ ] Database migrations with Alembic
- [ ] Efficient querying with pagination support

#### REST API
- [ ] FastAPI application with OpenAPI documentation
- [ ] Document upload endpoint with multipart form support
- [ ] Document status tracking endpoint
- [ ] Document listing with pagination
- [ ] Borrower listing with pagination and search
- [ ] Borrower detail endpoint with full income/account history
- [ ] Source reference endpoint showing originating documents
- [ ] Health check endpoint
- [ ] CORS configuration for frontend
- [ ] Error handling with meaningful status codes

#### Frontend UI
- [ ] Next.js 14 app with server components and app router
- [ ] shadcn/ui + Tailwind CSS for high-fidelity design
- [ ] Document upload page with drag-and-drop
- [ ] Document list with status badges and processing indicators
- [ ] Borrower list with search and pagination
- [ ] Borrower detail page with income timeline visualization
- [ ] Source reference display linking back to documents
- [ ] Architecture documentation pages (overview, decisions, pipeline, scaling)
- [ ] Responsive design for desktop and tablet

#### GCP Infrastructure
- [ ] Terraform configuration for all GCP resources
- [ ] Cloud SQL (PostgreSQL) with automated backups
- [ ] Cloud Storage bucket for document storage with lifecycle policies
- [ ] Cloud Run for serverless backend deployment with auto-scaling
- [ ] Cloud Run for frontend deployment
- [ ] Cloud Tasks queue for asynchronous document processing
- [ ] IAM roles and security configuration following least-privilege
- [ ] Deployment scripts for automated CI/CD
- [ ] Dockerfiles for backend and frontend with multi-stage builds

#### Testing & Quality
- [ ] Test-driven development workflow (tests written first)
- [ ] Unit test coverage >80% for backend
- [ ] Integration tests for pipeline flows
- [ ] End-to-end API tests
- [ ] mypy strict mode type checking with zero errors
- [ ] Frontend smoke tests for critical paths
- [ ] Code simplification pass for clarity and maintainability

### Out of Scope

- **Real-time processing** — Asynchronous queue-based processing is sufficient for the use case
- **Multi-tenancy** — Single deployment model, no tenant isolation needed
- **Mobile native apps** — Web-first approach, responsive design covers mobile browsers
- **Custom OCR beyond Docling** — Docling's built-in OCR capabilities are sufficient
- **Custom LLM fine-tuning** — Using Gemini models as-is without custom training
- **User authentication** — Public demo application, no user accounts
- **Audit logging** — Basic application logs sufficient, no compliance audit trail
- **Data encryption at rest beyond GCP defaults** — GCP's default encryption is adequate
- **Advanced analytics/reporting** — Basic querying sufficient, no BI dashboards
- **Webhook notifications** — Polling-based status checks sufficient

## Context

**Portfolio Project Format:** Originally designed as a take-home technical assessment with 7-day timeframe and 4-8 hours expected effort. Being executed as a learning project with 3-day hard deadline to demonstrate rapid full-stack development capabilities.

**Document Corpus:** Loan documents with variable formatting, mixed file types (PDF, DOCX, images), and structured data embedded in unstructured text. Documents include borrower PII, income history, account numbers, and loan numbers across multiple pages and forms.

**Parallel Execution Optimization:** PRD explicitly designed for Claude Code's parallel subagent spawning capabilities. Each phase identifies tasks that can run concurrently with clear dependency markers and blocking relationships.

**TDD Approach:** Test-driven development workflow where tests are written first to define expected behavior, then implementation follows. This accelerates development by providing clear success criteria and catching errors early.

**AI Model Strategy:** Using Gemini 3.0 with dynamic model selection:
- **gemini-3-flash-preview**: Default for standard loan documents with clear structure (faster, cheaper)
- **gemini-3-pro-preview**: For complex documents with multiple borrowers, poor scan quality, or cross-referenced data (higher reasoning capability)

**GCP Resources Available:** Google Cloud Platform account configured with:
- Gemini API access through Google AI Studio
- Project quota for Cloud SQL, Cloud Run, Cloud Storage, Cloud Tasks
- Terraform state bucket for infrastructure management
- Service account keys for deployment automation

## Constraints

- **Timeline: 3 days hard deadline** — All 7 phases must complete: setup, ingestion, extraction, storage, API, frontend, infrastructure, documentation
- **Tech Stack: Fixed per PRD** — Docling for processing, Gemini 3.0 for extraction, FastAPI + PostgreSQL backend, Next.js frontend, GCP deployment
- **Test Coverage: >80% target** — Backend unit tests must cover critical paths with pytest
- **Type Safety: mypy strict mode** — Zero type errors allowed, full type annotations required
- **TDD Workflow: Tests first** — Implementation follows test definition for all features
- **GCP Deployment: Required** — Must have working Terraform configuration and deployment scripts
- **Completeness: No simplifications** — All requirements equally critical, portfolio piece must be production-ready
- **Documentation: Comprehensive** — System design, architecture decisions, README, API docs all required

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Docling for document processing | Production-grade PDF/DOCX/image parsing with layout understanding and table extraction built-in. Eliminates need for custom OCR pipeline. | — Pending |
| Gemini 3.0 with dynamic model selection | State-of-the-art reasoning for complex extraction. Flash model for cost efficiency on standard docs, Pro model for complex cases requiring deeper reasoning. | — Pending |
| PostgreSQL over NoSQL | Structured relational data (borrowers → income/accounts → documents) benefits from ACID transactions and foreign key constraints. Cloud SQL provides managed solution. | — Pending |
| FastAPI over Flask/Django | Modern async support crucial for LLM API calls. Auto-generated OpenAPI docs. Pydantic integration for type-safe validation. | — Pending |
| Next.js 14 App Router | Server components reduce client bundle size. App router provides better code organization. shadcn/ui offers high-quality accessible components. | — Pending |
| Cloud Run over GKE/Compute Engine | Serverless auto-scaling with pay-per-use pricing. No cluster management overhead. Suitable for demo/portfolio scale. | — Pending |
| Monorepo structure | Backend, frontend, infrastructure in single repo simplifies dependency management and deployment coordination for portfolio project. | — Pending |
| Test-first TDD approach | Tests define contracts before implementation, catching errors early and providing confidence for aggressive 3-day timeline. | — Pending |

---
*Last updated: 2026-01-23 after initialization*
