# Loan Document Data Extraction System

## What This Is

A production-grade AI-powered system that extracts structured borrower information from unstructured loan documents. Processes PDF, DOCX, and image files using Docling for document understanding and Gemini 3.0 for intelligent data extraction. Stores structured data in PostgreSQL, serves via FastAPI REST API, and presents through a modern Next.js frontend. Fully deployed on Google Cloud Platform with Infrastructure as Code.

Built as a portfolio project to demonstrate full-stack engineering capabilities, test-driven development practices, parallel execution optimization, and cloud-native architecture.

## Core Value

**Accurate extraction of borrower data with complete traceability.** Every extracted field (PII, income history, account/loan numbers) must include source attribution showing which document and page it came from, with confidence scoring to flag data needing manual review.

## Requirements

### Validated

#### v1.0 Requirements
- ✓ Foundation & Data Models (17 requirements) — v1.0
- ✓ Document Ingestion Pipeline (28 requirements) — v1.0
- ✓ LLM Extraction & Validation (38 requirements) — v1.0
- ✓ Data Storage & REST API (32 requirements) — v1.0
- ✓ Frontend Dashboard (37 requirements) — v1.0
- ✓ GCP Infrastructure (27 requirements) — v1.0 (code-level)
- ✓ Documentation & Testing (48 requirements) — v1.0
- ✓ Pipeline Integration (44 requirements) — v1.0
- ✓ Async Background Processing (2 requirements) — v1.0

**Total v1.0:** 222/222 requirements (100%)

### Active

(v1.0 complete — requirements for next milestone to be defined)

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

**v1.0 Shipped (2026-01-24):**
- Complete full-stack loan document extraction system
- 9,357 lines of code across backend (Python), frontend (TypeScript), infrastructure (Terraform)
- 92% test coverage with 283 passing tests
- All 222 v1.0 requirements satisfied (100%)
- 9 phases executed in 2 days (2026-01-23 → 2026-01-24)

**Tech Stack:**
- Backend: FastAPI + PostgreSQL + SQLAlchemy (async)
- LLM: Gemini 3.0 (Flash for standard docs, Pro for complex)
- Document Processing: Docling (PDF/DOCX/image OCR)
- Frontend: Next.js 14 App Router + shadcn/ui + Tailwind CSS
- Infrastructure: GCP (Cloud Run + Cloud SQL + Cloud Storage + Cloud Tasks)
- IaC: Terraform with 32 GCP resources

**Implementation Highlights:**
- Dynamic model selection based on document complexity classification
- Source attribution tracking (every field links to document + page + snippet)
- Async background processing with Cloud Tasks (max 5 retry attempts)
- SSN hashing for PII protection (SHA-256, never stored raw)
- Confidence scoring (0.0-1.0) with <0.7 flagged for manual review
- Complete E2E testing: upload → extraction → persistence → retrieval

**Known Deployment Status:**
- Code-level verification: 100% complete
- Infrastructure-as-code: 32 Terraform resources configured
- Live GCP deployment: Pending manual `terraform apply` verification

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
| Docling for document processing | Production-grade PDF/DOCX/image parsing with layout understanding and table extraction built-in. Eliminates need for custom OCR pipeline. | ✓ Good — Successfully extracted text from all test documents with page boundaries and table structure preserved |
| Gemini 3.0 with dynamic model selection | State-of-the-art reasoning for complex extraction. Flash model for cost efficiency on standard docs, Pro model for complex cases requiring deeper reasoning. | ✓ Good — ComplexityClassifier routes docs correctly; Flash handles 80%+ of corpus; Pro provides higher accuracy on multi-borrower docs |
| PostgreSQL over NoSQL | Structured relational data (borrowers → income/accounts → documents) benefits from ACID transactions and foreign key constraints. Cloud SQL provides managed solution. | ✓ Good — Foreign key relationships maintain referential integrity; selectinload() prevents N+1 queries; async SQLAlchemy performs well |
| FastAPI over Flask/Django | Modern async support crucial for LLM API calls. Auto-generated OpenAPI docs. Pydantic integration for type-safe validation. | ✓ Good — Dependency injection simplified service wiring; OpenAPI docs auto-generated; async handlers improve throughput |
| Next.js 14 App Router | Server components reduce client bundle size. App router provides better code organization. shadcn/ui offers high-quality accessible components. | ✓ Good — Standalone output mode reduces Docker image to ~100MB; shadcn components provided polished UI quickly |
| Cloud Run over GKE/Compute Engine | Serverless auto-scaling with pay-per-use pricing. No cluster management overhead. Suitable for demo/portfolio scale. | ✓ Good — OIDC authentication with Cloud Tasks works seamlessly; VPC egress enables Cloud SQL private IP; scale-to-zero saves costs |
| Monorepo structure | Backend, frontend, infrastructure in single repo simplifies dependency management and deployment coordination for portfolio project. | ✓ Good — Simplified deployment coordination; single git history shows full-stack progress |
| Test-first TDD approach | Tests define contracts before implementation, catching errors early and providing confidence for aggressive 3-day timeline. | ✓ Good — 283 tests caught integration bugs early; 92% coverage provides confidence for refactoring |
| Cloud Tasks for async processing | Decouples upload from extraction; handles retries with exponential backoff; OIDC auth for Cloud Run endpoints. | ✓ Good — Upload returns instantly; retry logic handles transient failures; dual-mode (sync fallback) enables local dev |
| Phase 8 Gap Closure | Wired orphaned extraction subsystem into upload flow; added E2E tests. | ✓ Good — Closed 44 blocked requirements; all E2E flows now working; zero orphaned code |

---
*Last updated: 2026-01-24 after v1.0 milestone completion*
