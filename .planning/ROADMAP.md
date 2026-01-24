# Roadmap: Loan Document Data Extraction System

## Overview

This roadmap transforms the loan document extraction system from concept to deployed production-ready application across 7 phases. Starting with foundation and data models, we build the document ingestion pipeline with Docling, then add LLM extraction with Gemini 3.0, expose borrower data through a REST API, present everything through a Next.js frontend, deploy to GCP infrastructure, and complete with comprehensive documentation and testing. Each phase delivers a coherent, verifiable capability building toward the core value: accurate extraction of borrower data with complete traceability.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [x] **Phase 1: Foundation & Data Models** - Project scaffolding, dependencies, and Pydantic schemas for extraction output
- [x] **Phase 2: Document Ingestion Pipeline** - Docling integration, GCS storage, document database layer
- [x] **Phase 3: LLM Extraction & Validation** - Gemini client, complexity classifier, extractor, data validation
- [x] **Phase 4: Data Storage & REST API** - Borrower repositories, complete API endpoints
- [ ] **Phase 5: Frontend Dashboard** - Next.js UI with document/borrower management and architecture visualization
- [ ] **Phase 6: GCP Infrastructure** - Terraform configuration, Cloud Run deployment, CI/CD scripts
- [ ] **Phase 7: Documentation & Testing** - System design docs, architecture decisions, comprehensive test suite

## Phase Details

### Phase 1: Foundation & Data Models ✅
**Goal**: Establish project structure with all dependencies and define the Pydantic schemas that represent extracted borrower data
**Depends on**: Nothing (first phase)
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04, FOUND-05, FOUND-06, FOUND-07, MODEL-01, MODEL-02, MODEL-03, MODEL-04, MODEL-05, MODEL-06, MODEL-07
**Success Criteria** (what must be TRUE):
  1. Running `python -c "import src"` succeeds in backend directory
  2. Running `npm run dev` starts frontend development server
  3. Running `docker-compose up` starts PostgreSQL and Redis locally
  4. BorrowerRecord Pydantic model validates sample borrower JSON with all fields
  5. All Pydantic models serialize to JSON and deserialize correctly
**Plans**: 3 plans
**Status**: Complete (2026-01-23)

Plans:
- [x] 01-01-PLAN.md - Backend project structure, pyproject.toml, Docker Compose
- [x] 01-02-PLAN.md - Frontend Next.js project with shadcn/ui
- [x] 01-03-PLAN.md - Pydantic data models with unit tests

### Phase 2: Document Ingestion Pipeline ✅
**Goal**: Process uploaded documents (PDF, DOCX, images) through Docling and store in GCS with database tracking
**Depends on**: Phase 1
**Requirements**: INGEST-01, INGEST-02, INGEST-03, INGEST-04, INGEST-05, INGEST-06, INGEST-07, INGEST-08, INGEST-09, INGEST-10, INGEST-11, INGEST-12, INGEST-13, INGEST-14, DB-01, DB-02, DB-03, DB-04, DB-05, DB-06, DB-07, DB-08, DB-09, DB-10, DB-11, DB-12
**Success Criteria** (what must be TRUE):
  1. Uploading a PDF file creates a document record in database with status PENDING
  2. Docling processes the uploaded PDF and extracts text with page boundaries preserved
  3. Document files are stored in GCS with retrievable gs:// URI
  4. Duplicate uploads (same file hash) are detected and rejected
  5. Failed document processing gracefully records error status without crashing
**Plans**: 4 plans
**Status**: Complete (2026-01-23)

Plans:
- [x] 02-01-PLAN.md - Database models and Alembic setup (SQLAlchemy models, migrations, DocumentRepository)
- [x] 02-02-PLAN.md - Docling processor and GCS client (document conversion, file storage)
- [x] 02-03-PLAN.md - Document service and upload API (orchestration, POST /api/documents endpoint)
- [x] 02-04-PLAN.md - Gap closure: Wire Docling processing into upload flow, add end-to-end tests

### Phase 3: LLM Extraction & Validation ✅
**Goal**: Extract structured borrower data from document text using Gemini 3.0 with complexity-based model selection and hybrid validation
**Depends on**: Phase 2
**Requirements**: EXTRACT-01, EXTRACT-02, EXTRACT-03, EXTRACT-04, EXTRACT-05, EXTRACT-06, EXTRACT-07, EXTRACT-08, EXTRACT-09, EXTRACT-10, EXTRACT-11, EXTRACT-12, EXTRACT-13, EXTRACT-14, EXTRACT-15, EXTRACT-16, EXTRACT-17, EXTRACT-18, EXTRACT-19, EXTRACT-20, EXTRACT-21, EXTRACT-22, EXTRACT-23, EXTRACT-24, EXTRACT-25, EXTRACT-26, EXTRACT-27, EXTRACT-28, EXTRACT-29, VALID-01, VALID-02, VALID-03, VALID-04, VALID-05, VALID-06, VALID-07, VALID-08, VALID-09
**Success Criteria** (what must be TRUE):
  1. Simple loan documents route to Flash model, complex documents to Pro model
  2. Extracted borrower records include source attribution (document ID, page number, text snippet)
  3. Confidence scores calculated for each extraction (0.0-1.0 scale)
  4. SSN, phone, and zip code formats validated with errors tracked
  5. Large documents chunked and results aggregated correctly
  6. Consistency validation flags address conflicts, income anomalies, and cross-document mismatches
**Plans**: 5 plans
**Status**: Complete (2026-01-24)

Plans:
- [x] 03-01-PLAN.md - Gemini client with retry and error handling
- [x] 03-02-PLAN.md - Complexity classifier, prompt templates, and document chunker
- [x] 03-03-PLAN.md - Validation service and confidence scoring
- [x] 03-04-PLAN.md - Extraction orchestrator with deduplication
- [x] 03-05-PLAN.md - Consistency validation (address conflicts, income progression, cross-document checks)

### Phase 4: Data Storage & REST API ✅
**Goal**: Persist extracted borrower data with relationships and expose through searchable REST endpoints
**Depends on**: Phase 3
**Requirements**: DB-13, DB-14, DB-15, DB-16, DB-17, DB-18, DB-19, DB-20, API-01, API-02, API-03, API-04, API-05, API-06, API-07, API-08, API-09, API-10, API-11, API-12, API-13, API-14, API-15, API-16, API-17, API-18, API-19, API-20, API-21, API-22, API-23, API-24
**Success Criteria** (what must be TRUE):
  1. POST /api/documents accepts file upload and returns document ID
  2. GET /api/borrowers/{id} returns full borrower with income history and source references
  3. GET /api/borrowers/search returns filtered results by name or account number
  4. OpenAPI documentation accessible at /docs with all endpoints documented
  5. Invalid requests return appropriate HTTP status codes (400, 404, 500)
**Plans**: 3 plans
**Status**: Complete (2026-01-24)

Plans:
- [x] 04-01-PLAN.md - BorrowerRepository with CRUD and search operations
- [x] 04-02-PLAN.md - CORS middleware, exception handlers, document status endpoint
- [x] 04-03-PLAN.md - Borrower API endpoints with search and pagination

### Phase 5: Frontend Dashboard
**Goal**: Provide a visual interface for document upload, borrower browsing, and architecture documentation
**Depends on**: Phase 4
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05, UI-06, UI-07, UI-08, UI-09, UI-10, UI-11, UI-12, UI-13, UI-14, UI-15, UI-16, UI-17, UI-18, UI-19, UI-20, UI-21, UI-22, UI-23, UI-24, UI-25, UI-26, UI-27, UI-28, UI-29, UI-30, UI-31, UI-32, UI-33, UI-34, UI-35, UI-36, UI-37
**Success Criteria** (what must be TRUE):
  1. User can drag-and-drop a PDF file to upload and see processing status
  2. User can browse borrower list with search and click to view details
  3. Borrower detail page shows income timeline visualization and source references
  4. Architecture pages display system diagram, pipeline flow, and scaling analysis
  5. All pages render correctly on desktop and tablet viewports
**Plans**: 4 plans

Plans:
- [ ] 05-01-PLAN.md — App shell, layout, and API client (Wave 1)
- [ ] 05-02-PLAN.md — Document upload and list pages (Wave 2)
- [ ] 05-03-PLAN.md — Borrower list and detail pages (Wave 2)
- [ ] 05-04-PLAN.md — Architecture documentation pages (Wave 2)

### Phase 6: GCP Infrastructure
**Goal**: Deploy the complete system to Google Cloud Platform with infrastructure as code
**Depends on**: Phase 5
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, INFRA-06, INFRA-07, INFRA-08, INFRA-09, INFRA-10, INFRA-11, INFRA-12, INFRA-13, INFRA-14, INFRA-15, INFRA-16, INFRA-17, INFRA-18, INFRA-19, INFRA-20, INFRA-21, INFRA-22, INFRA-23, INFRA-24, INFRA-25, INFRA-26, INFRA-27
**Success Criteria** (what must be TRUE):
  1. terraform apply creates all GCP resources without errors
  2. Backend Cloud Run service responds to health check at deployed URL
  3. Frontend Cloud Run service serves the dashboard at deployed URL
  4. Document uploads flow through the complete pipeline to extracted borrowers
  5. Deployment scripts automate the full deploy process
**Plans**: TBD

Plans:
- [ ] 06-01: Terraform configuration for GCP resources
- [ ] 06-02: Dockerfiles for backend and frontend
- [ ] 06-03: Deployment scripts and CI/CD setup

### Phase 7: Documentation & Testing
**Goal**: Complete system documentation and achieve >80% test coverage with type safety
**Depends on**: Phase 6
**Requirements**: DOCS-01, DOCS-02, DOCS-03, DOCS-04, DOCS-05, DOCS-06, DOCS-07, DOCS-08, DOCS-09, DOCS-10, DOCS-11, DOCS-12, DOCS-13, DOCS-14, DOCS-15, DOCS-16, DOCS-17, DOCS-18, DOCS-19, DOCS-20, DOCS-21, DOCS-22, DOCS-23, DOCS-24, DOCS-25, DOCS-26, DOCS-27, DOCS-28, TEST-01, TEST-02, TEST-03, TEST-04, TEST-05, TEST-06, TEST-07, TEST-08, TEST-09, TEST-10, TEST-11, TEST-12, TEST-13, TEST-14, TEST-15, TEST-16, TEST-17, TEST-18, TEST-19, TEST-20
**Success Criteria** (what must be TRUE):
  1. SYSTEM_DESIGN.md contains architecture overview, pipeline description, and scaling analysis
  2. ARCHITECTURE_DECISIONS.md contains ADRs for Docling, Gemini, PostgreSQL, Cloud Run, Next.js
  3. README.md includes complete setup and run instructions
  4. pytest coverage report shows >80% backend coverage
  5. mypy strict mode passes with zero errors
**Plans**: TBD

Plans:
- [ ] 07-01: System design documentation
- [ ] 07-02: Architecture decision records
- [ ] 07-03: Unit and integration tests
- [ ] 07-04: End-to-end tests and quality verification

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Data Models | 3/3 | ✅ Complete | 2026-01-23 |
| 2. Document Ingestion Pipeline | 4/4 | ✅ Complete | 2026-01-23 |
| 3. LLM Extraction & Validation | 5/5 | ✅ Complete | 2026-01-24 |
| 4. Data Storage & REST API | 3/3 | ✅ Complete | 2026-01-24 |
| 5. Frontend Dashboard | 0/4 | Planned | - |
| 6. GCP Infrastructure | 0/3 | Not started | - |
| 7. Documentation & Testing | 0/4 | Not started | - |

---
*Roadmap created: 2026-01-23*
*Last updated: 2026-01-24 (Phase 5 planned)*
