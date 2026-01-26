# Loan Document Data Extraction System

## What This Is

A production-deployed AI-powered system that extracts structured borrower information from unstructured loan documents. Processes PDF, DOCX, and image files using dual extraction pipelines: Docling (page-level attribution) and LangExtract (character-level precision with Gemini 3.0). LightOnOCR GPU service handles scanned documents with scale-to-zero cost optimization. Stores structured data in PostgreSQL, serves via FastAPI REST API, and presents through a modern Next.js frontend. Fully deployed on Google Cloud Platform with CloudBuild CI/CD automation.

Built as a portfolio project to demonstrate full-stack engineering capabilities, test-driven development practices, cloud-native architecture, and production deployment proficiency.

## Core Value

**Accurate extraction of borrower data with complete traceability.** Every extracted field (PII, income history, account/loan numbers) must include source attribution showing which document and page it came from, with confidence scoring to flag data needing manual review.

## Current State (v2.1 Shipped)

**Latest Version:** v2.1 Production Deployment & Verification (shipped 2026-01-26)

**System Capabilities:**
- Dual extraction pipelines: Docling (fast, page-level attribution) and LangExtract (precise, character-level attribution)
- LightOnOCR GPU service for high-quality OCR of scanned documents (scale-to-zero enabled)
- API-based extraction method selection with backward-compatible defaults
- CloudBuild CI/CD with GitHub triggers replacing Terraform for application deployments
- Production deployment on GCP with all services running and verified
- 86.98% test coverage, mypy strict compliance, 490 passing tests

**Production URLs:**
- Backend: https://loan-backend-prod-fjz2snvxjq-uc.a.run.app
- Frontend: https://loan-frontend-prod-fjz2snvxjq-uc.a.run.app
- GPU OCR: https://lightonocr-gpu-fjz2snvxjq-uc.a.run.app

## Next Milestone Goals

**Potential areas for improvement:**
- Custom domain and SSL certificates for production URLs
- Advanced monitoring and alerting (beyond Cloud Logging)
- Load testing and performance optimization
- Multi-region deployment for higher availability
- Additional extraction features or data quality improvements

## Requirements

### Validated

#### v1.0 Requirements (Shipped 2026-01-24)
- ✓ Foundation & Data Models (17 requirements) — v1.0
- ✓ Document Ingestion Pipeline (28 requirements) — v1.0
- ✓ LLM Extraction & Validation (38 requirements) — v1.0
- ✓ Data Storage & REST API (32 requirements) — v1.0
- ✓ Frontend Dashboard (37 requirements) — v1.0
- ✓ GCP Infrastructure (27 requirements) — v1.0
- ✓ Documentation & Testing (48 requirements) — v1.0
- ✓ Pipeline Integration (44 requirements) — v1.0
- ✓ Async Background Processing (2 requirements) — v1.0

**Total v1.0:** 222/222 requirements (100%)

#### v2.0 Requirements (Shipped 2026-01-25)
- ✓ LangExtract Integration (12 requirements) — v2.0
- ✓ LightOnOCR GPU Service (12 requirements) — v2.0
- ✓ Dual Pipeline Integration (12 requirements) — v2.0
- ✓ CloudBuild Deployment (12 requirements) — v2.0
- ✓ Testing & Quality (12 requirements) — v2.0
- ✓ Documentation (12 requirements) — v2.0

**Total v2.0:** 72/72 requirements (100%)

#### v2.1 Requirements (Shipped 2026-01-26)
- ✓ Production Deployment (6 requirements: DEPLOY-01 through DEPLOY-06) — v2.1
- ✓ Chrome-Based Verification (9 requirements: TEST-01 through TEST-09) — v2.1

**Total v2.1:** 15/15 requirements (100%)

### Active

(No active requirements - ready for next milestone)

### Out of Scope

- **Real-time processing** — Asynchronous queue-based processing is sufficient for the use case
- **Multi-tenancy** — Single deployment model, no tenant isolation needed
- **Mobile native apps** — Web-first approach, responsive design covers mobile browsers
- **Custom LLM fine-tuning** — Using Gemini models as-is without custom training
- **User authentication** — Public demo application, no user accounts
- **Audit logging** — Basic application logs sufficient, no compliance audit trail
- **Data encryption at rest beyond GCP defaults** — GCP's default encryption is adequate
- **Advanced analytics/reporting** — Basic querying sufficient, no BI dashboards
- **Webhook notifications** — Polling-based status checks sufficient

## Context

**v2.1 Shipped (2026-01-26):**
- Production deployment to GCP (memorygraph-prod project) with all services running
- Complete infrastructure: VPC, service account, Artifact Registry, Cloud SQL, secrets
- Database configured: loan_extraction database with schema migrations
- GPU OCR integration wired: scanned pages processed via LightOnOCR service
- Character-level source attribution UI: char_start/char_end fields exposed with badge indicator
- All 15 v2.1 requirements satisfied (100%: 6 deployment + 9 verification)
- 3 phases (11 plans) executed in 1.5 days (2026-01-25 → 2026-01-26)
- ~50 commits including production fixes and feature additions

**v2.0 Shipped (2026-01-25):**
- Dual extraction pipelines (Docling + LangExtract) with API method selection
- LightOnOCR GPU service deployed with L4 GPU and scale-to-zero cost optimization
- CloudBuild CI/CD migration complete (replaces Terraform for application deployments)
- 95,818 lines of code across backend (Python), frontend (TypeScript), infrastructure (CloudBuild YAML)
- 86.98% test coverage with 490 passing tests
- All 72 v2.0 requirements satisfied (100%)
- 9 phases (28 plans) executed in 1 day (2026-01-25)

**v1.0 Shipped (2026-01-24):**
- Complete full-stack loan document extraction system
- 9,357 lines of code
- 92% test coverage with 283 passing tests
- All 222 v1.0 requirements satisfied (100%)
- 9 phases (36 plans) executed in 2 days (2026-01-23 → 2026-01-24)

**Tech Stack:**
- Backend: FastAPI + PostgreSQL + SQLAlchemy (async)
- LLM: Gemini 3.0 (Flash for standard docs, Pro for complex)
- Extraction: Docling (page-level) + LangExtract (character-level with Gemini 3.0 Flash)
- OCR: LightOnOCR GPU service (Cloud Run L4) with Docling fallback
- Frontend: Next.js 14 App Router + shadcn/ui + Tailwind CSS
- Infrastructure: GCP (Cloud Run + Cloud SQL + Cloud Storage + Cloud Tasks)
- CI/CD: CloudBuild with GitHub triggers
- IaC: gcloud CLI scripts for infrastructure, CloudBuild for applications

**Implementation Highlights:**
- Character-level source attribution with LangExtract (char_start/char_end offsets)
- Few-shot example-based extraction schema definition
- Dual pipeline architecture with backward-compatible defaults
- GPU service with scale-to-zero ($0 baseline vs $485/month always-on)
- Circuit breaker pattern for GPU OCR fallback to Docling
- Comprehensive test coverage (86.98%) with mypy strict compliance

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
| Test-first TDD approach | Tests define contracts before implementation, catching errors early and providing confidence for aggressive timeline. | ✓ Good — v1.0: 283 tests (92% coverage), v2.0: 490 tests (86.98% coverage); mypy strict compliance |
| Cloud Tasks for async processing | Decouples upload from extraction; handles retries with exponential backoff; OIDC auth for Cloud Run endpoints. | ✓ Good — Upload returns instantly; retry logic handles transient failures; dual-mode (sync fallback) enables local dev; extended with method/ocr params in v2.0 |
| Phase 8 Gap Closure (v1.0) | Wired orphaned extraction subsystem into upload flow; added E2E tests. | ✓ Good — Closed 44 blocked requirements; all E2E flows now working; zero orphaned code |
| LangExtract for character-level attribution (v2.0) | Provides precise source grounding with char_start/char_end offsets vs page-level attribution. | ✓ Good — Few-shot examples enable schema customization; offset translation handles Docling markdown alignment; fallback to Docling on errors |
| LightOnOCR as dedicated GPU service (v2.0) | Cloud Run with L4 GPU, scale-to-zero, circuit breaker fallback to Docling OCR. | ✓ Good — $0 baseline cost vs $485/month always-on; vLLM batching improves throughput; 120s timeout handles cold starts |
| CloudBuild replaces Terraform (v2.0) | Application deployments via CloudBuild + GitHub triggers, infrastructure via gcloud CLI scripts. | ✓ Good — Separation of concerns (infra vs apps); GitHub integration for CI/CD; idempotent gcloud scripts; Terraform state archived for recovery |
| Production deployment to memorygraph-prod (v2.1) | Used existing GCP project with loan-specific infrastructure (loan-repo, loan-backend-prod, loan-frontend-prod). | ✓ Good — Leveraged existing project infrastructure; isolated resources with loan-specific naming; complete VPC and service account setup |
| New loan_extraction database (v2.1) | Created dedicated database instead of reusing memorygraph_auth database. | ✓ Good — Clean schema separation; isolated from other applications; clear ownership and migration path |
| Pre-download Docling models in Docker build (v2.1) | Download models during build phase, not at Cloud Run startup. | ✓ Good — Eliminates runtime download failures; faster container startup; more reliable production deployments |
| GPU OCR integration wiring (v2.1) | Wired LightOnOCR client in ocr_router.py with _merge_gpu_ocr_results() for hybrid document support. | ✓ Good — Closed verification gap; scanned pages now processed via GPU service; proper text merging with native pages |
| Semantic badge color variants (v2.1) | Added success/warning badge variants instead of using monochrome theme colors. | ✓ Good — Visual differentiation of confidence scores; green/yellow/red semantic meaning; improved UX clarity |

---
*Last updated: 2026-01-26 after v2.1 milestone completion*
