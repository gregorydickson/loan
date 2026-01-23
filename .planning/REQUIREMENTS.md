# Requirements: Loan Document Data Extraction System

**Defined:** 2026-01-23
**Core Value:** Accurate extraction of borrower data with complete traceability - every extracted field must include source attribution showing which document and page it came from.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Foundation

- [ ] **FOUND-01**: Project structure created with backend, frontend, infrastructure, docs directories
- [ ] **FOUND-02**: Backend pyproject.toml with all dependencies and dev tools configured
- [ ] **FOUND-03**: Backend config.py with Pydantic Settings for environment variables
- [ ] **FOUND-04**: Frontend package.json with Next.js 14+, React 18, TanStack Query, shadcn/ui
- [ ] **FOUND-05**: Frontend configuration files (next.config.js, tailwind.config.ts)
- [ ] **FOUND-06**: Docker-compose for local PostgreSQL and Redis development
- [ ] **FOUND-07**: Git repo initialized with appropriate .gitignore

### Document Ingestion

- [ ] **INGEST-01**: Docling processor wraps DocumentConverter for PDF processing
- [ ] **INGEST-02**: Docling processor handles DOCX files with layout preservation
- [ ] **INGEST-03**: Docling processor handles image files (PNG/JPG) with OCR
- [ ] **INGEST-04**: Docling processor extracts tables with structure
- [ ] **INGEST-05**: Docling processor returns page-level metadata
- [ ] **INGEST-06**: Document service uploads files to Google Cloud Storage
- [ ] **INGEST-07**: Document service creates database record with metadata
- [ ] **INGEST-08**: Document service queues processing task in Cloud Tasks
- [ ] **INGEST-09**: Document service detects duplicates via file hash (SHA-256)
- [ ] **INGEST-10**: Document service handles processing errors gracefully
- [ ] **INGEST-11**: GCS client uploads files and returns gs:// URI
- [ ] **INGEST-12**: GCS client downloads files by URI
- [ ] **INGEST-13**: GCS client generates signed URLs for temporary access
- [ ] **INGEST-14**: GCS client checks file existence

### LLM Extraction

- [ ] **EXTRACT-01**: Gemini client initializes with google-genai SDK (not deprecated google-generativeai)
- [ ] **EXTRACT-02**: Gemini client supports gemini-3-flash-preview model
- [ ] **EXTRACT-03**: Gemini client supports gemini-3-pro-preview model
- [ ] **EXTRACT-04**: Gemini client implements retry with exponential backoff (max 3 attempts)
- [ ] **EXTRACT-05**: Gemini client handles rate limiting (429) with 60s wait
- [ ] **EXTRACT-06**: Gemini client handles server errors (5xx) with 10s wait
- [ ] **EXTRACT-07**: Gemini client handles timeout with chunk size reduction
- [ ] **EXTRACT-08**: Gemini client handles None response when max_output_tokens exceeded
- [ ] **EXTRACT-09**: Gemini client tracks token usage (input/output)
- [ ] **EXTRACT-10**: Gemini client returns structured response with latency metrics
- [ ] **EXTRACT-11**: Complexity classifier identifies simple single-borrower documents
- [ ] **EXTRACT-12**: Complexity classifier identifies complex multi-borrower documents
- [ ] **EXTRACT-13**: Complexity classifier identifies poor scan quality documents
- [ ] **EXTRACT-14**: Complexity classifier identifies handwritten sections
- [ ] **EXTRACT-15**: Complexity classifier returns STANDARD or COMPLEX level
- [ ] **EXTRACT-16**: Extraction prompts render with document text
- [ ] **EXTRACT-17**: Extraction prompts include Pydantic schema for structured output
- [ ] **EXTRACT-18**: Extraction prompts handle special characters safely
- [ ] **EXTRACT-19**: Extractor assesses document complexity before extraction
- [ ] **EXTRACT-20**: Extractor chunks large documents (4000 tokens, 200 overlap)
- [ ] **EXTRACT-21**: Extractor calls appropriate model (Flash for standard, Pro for complex)
- [ ] **EXTRACT-22**: Extractor aggregates results from multiple chunks
- [ ] **EXTRACT-23**: Extractor deduplicates borrower records (SSN/account match, fuzzy name match)
- [ ] **EXTRACT-24**: Extractor tracks source attribution (document ID, page, section, snippet)
- [ ] **EXTRACT-25**: Extractor calculates confidence scores (0.0-1.0 range)
- [ ] **EXTRACT-26**: Confidence score increases for complete required fields
- [ ] **EXTRACT-27**: Confidence score increases for complete optional fields
- [ ] **EXTRACT-28**: Confidence score increases for multi-source confirmation
- [ ] **EXTRACT-29**: Confidence score increases for format validation passing

### Data Validation

- [ ] **VALID-01**: Validator checks SSN format (XXX-XX-XXXX)
- [ ] **VALID-02**: Validator checks phone number format (various US formats)
- [ ] **VALID-03**: Validator checks zip code format (XXXXX or XXXXX-XXXX)
- [ ] **VALID-04**: Validator checks date formats
- [ ] **VALID-05**: Validator flags records with confidence < 0.7 for manual review
- [ ] **VALID-06**: Validator tracks validation errors with reasons
- [ ] **VALID-07**: Validator checks borrower data consistency across documents
- [ ] **VALID-08**: Validator validates income progression is logical
- [ ] **VALID-09**: Validator flags conflicting addresses for same borrower

### Data Models

- [ ] **MODEL-01**: BorrowerRecord Pydantic model with all fields (name, address, income, accounts, sources)
- [ ] **MODEL-02**: Address Pydantic model with structured fields
- [ ] **MODEL-03**: IncomeRecord Pydantic model with amount, period, year, source type
- [ ] **MODEL-04**: SourceReference Pydantic model with document ID, page, section, snippet
- [ ] **MODEL-05**: BorrowerRecord includes confidence score field
- [ ] **MODEL-06**: BorrowerRecord includes extracted_at timestamp
- [ ] **MODEL-07**: All models support JSON serialization

### Database Storage

- [ ] **DB-01**: Document SQLAlchemy model with id, filename, file_hash, gcs_uri, status
- [ ] **DB-02**: Document model includes created_at and processed_at timestamps
- [ ] **DB-03**: Borrower SQLAlchemy model with id, name, address_json, confidence_score
- [ ] **DB-04**: IncomeRecord SQLAlchemy model with borrower foreign key
- [ ] **DB-05**: AccountNumber SQLAlchemy model with borrower foreign key and type
- [ ] **DB-06**: SourceReference SQLAlchemy model with borrower and document foreign keys
- [ ] **DB-07**: SourceReference includes page, section, snippet fields
- [ ] **DB-08**: DocumentRepository creates document records
- [ ] **DB-09**: DocumentRepository retrieves documents by ID
- [ ] **DB-10**: DocumentRepository retrieves documents by file hash
- [ ] **DB-11**: DocumentRepository updates document status
- [ ] **DB-12**: DocumentRepository lists documents with pagination
- [ ] **DB-13**: BorrowerRepository creates borrower records with related entities
- [ ] **DB-14**: BorrowerRepository retrieves borrowers by ID with relationships
- [ ] **DB-15**: BorrowerRepository searches borrowers by name
- [ ] **DB-16**: BorrowerRepository searches borrowers by account number
- [ ] **DB-17**: BorrowerRepository lists borrowers with pagination
- [ ] **DB-18**: Repositories handle transactions with automatic rollback on error
- [ ] **DB-19**: Alembic migrations configured for async PostgreSQL
- [ ] **DB-20**: Initial migration creates all tables

### REST API

- [ ] **API-01**: FastAPI application configured with CORS middleware
- [ ] **API-02**: FastAPI exception handlers for custom errors
- [ ] **API-03**: OpenAPI documentation auto-generated and accessible
- [ ] **API-04**: Health check endpoint returns service status
- [ ] **API-05**: Lifespan manager handles database connection pool
- [ ] **API-06**: Dependency injection provides database session
- [ ] **API-07**: Dependency injection provides DocumentService instance
- [ ] **API-08**: Dependency injection provides BorrowerRepository instance
- [ ] **API-09**: POST /api/documents endpoint accepts file upload
- [ ] **API-10**: POST /api/documents returns 201 with document ID
- [ ] **API-11**: POST /api/documents validates file type and size
- [ ] **API-12**: GET /api/documents/{id} returns document details
- [ ] **API-13**: GET /api/documents/{id}/status returns processing status
- [ ] **API-14**: GET /api/documents lists documents with pagination
- [ ] **API-15**: GET /api/documents returns 404 for non-existent document
- [ ] **API-16**: GET /api/borrowers lists borrowers with pagination
- [ ] **API-17**: GET /api/borrowers/{id} returns full borrower details
- [ ] **API-18**: GET /api/borrowers/{id} includes income history
- [ ] **API-19**: GET /api/borrowers/{id} includes account numbers
- [ ] **API-20**: GET /api/borrowers/{id} includes source references
- [ ] **API-21**: GET /api/borrowers/{id}/sources returns source documents
- [ ] **API-22**: GET /api/borrowers/search supports name query
- [ ] **API-23**: GET /api/borrowers/search supports account number query
- [ ] **API-24**: API returns meaningful HTTP status codes (400, 404, 500)

### Frontend UI

- [ ] **UI-01**: Next.js app with app router configured
- [ ] **UI-02**: Layout component with navigation header
- [ ] **UI-03**: shadcn/ui components installed (button, card, table, input, dialog, tabs, badge, skeleton)
- [ ] **UI-04**: Tailwind CSS configured with custom theme
- [ ] **UI-05**: Type-safe API client using fetch with typed responses
- [ ] **UI-06**: API client handles uploadDocument
- [ ] **UI-07**: API client handles getDocumentStatus
- [ ] **UI-08**: API client handles listBorrowers with pagination
- [ ] **UI-09**: API client handles getBorrower
- [ ] **UI-10**: API client handles searchBorrowers
- [ ] **UI-11**: Document upload page at /documents with drag-and-drop
- [ ] **UI-12**: Document upload shows progress indicator
- [ ] **UI-13**: Document list shows status badges (pending, processing, complete, error)
- [ ] **UI-14**: Document list is clickable to view details
- [ ] **UI-15**: Document detail page at /documents/[id]
- [ ] **UI-16**: Upload zone component handles file selection
- [ ] **UI-17**: Document table component displays list with sorting
- [ ] **UI-18**: Status badge component shows appropriate colors
- [ ] **UI-19**: Borrower list page at /borrowers with search
- [ ] **UI-20**: Borrower list supports pagination
- [ ] **UI-21**: Borrower detail page at /borrowers/[id]
- [ ] **UI-22**: Borrower card component displays summary
- [ ] **UI-23**: Income timeline component visualizes income history
- [ ] **UI-24**: Source references component links to documents
- [ ] **UI-25**: Search bar component filters borrowers
- [ ] **UI-26**: Architecture overview page at /architecture
- [ ] **UI-27**: Design decisions page at /architecture/decisions
- [ ] **UI-28**: Data pipeline page at /architecture/pipeline with flow diagram
- [ ] **UI-29**: Scaling strategy page at /architecture/scaling
- [ ] **UI-30**: System diagram component shows architecture
- [ ] **UI-31**: Pipeline flow component shows processing steps
- [ ] **UI-32**: Decision card component displays ADRs
- [ ] **UI-33**: Scaling chart component shows performance projections
- [ ] **UI-34**: Dashboard home page at / with summary stats
- [ ] **UI-35**: Sidebar navigation component
- [ ] **UI-36**: Header component with branding
- [ ] **UI-37**: All pages responsive for desktop and tablet

### GCP Infrastructure

- [ ] **INFRA-01**: Terraform main.tf with provider configuration
- [ ] **INFRA-02**: Terraform variables.tf with project_id, region, etc.
- [ ] **INFRA-03**: Cloud SQL PostgreSQL instance configured
- [ ] **INFRA-04**: Cloud SQL includes automated backups
- [ ] **INFRA-05**: Cloud SQL connection for Cloud Run configured
- [ ] **INFRA-06**: Cloud Storage bucket for documents created
- [ ] **INFRA-07**: Cloud Storage bucket has lifecycle policies
- [ ] **INFRA-08**: Cloud Storage bucket has IAM permissions
- [ ] **INFRA-09**: Cloud Run service for backend configured
- [ ] **INFRA-10**: Cloud Run backend has environment variables
- [ ] **INFRA-11**: Cloud Run backend has auto-scaling configured
- [ ] **INFRA-12**: Cloud Run backend has Cloud SQL connection
- [ ] **INFRA-13**: Cloud Run service for frontend configured
- [ ] **INFRA-14**: Cloud Run frontend has backend API URL
- [ ] **INFRA-15**: Cloud Tasks queue for document processing
- [ ] **INFRA-16**: Cloud Tasks queue has appropriate rate limits
- [ ] **INFRA-17**: IAM service account for backend created
- [ ] **INFRA-18**: IAM roles assigned following least-privilege
- [ ] **INFRA-19**: IAM allows backend to access GCS and Cloud SQL
- [ ] **INFRA-20**: Terraform outputs include service URLs
- [ ] **INFRA-21**: Terraform outputs include database connection string
- [ ] **INFRA-22**: Setup script (setup-gcp.sh) provisions GCP project
- [ ] **INFRA-23**: Deploy script (deploy.sh) automates deployment
- [ ] **INFRA-24**: Backend Dockerfile with multi-stage build
- [ ] **INFRA-25**: Backend Dockerfile optimized for Cloud Run
- [ ] **INFRA-26**: Frontend Dockerfile with multi-stage build
- [ ] **INFRA-27**: Frontend Dockerfile uses Next.js standalone output

### Documentation

- [ ] **DOCS-01**: SYSTEM_DESIGN.md includes architecture overview
- [ ] **DOCS-02**: SYSTEM_DESIGN.md includes component diagram (Mermaid)
- [ ] **DOCS-03**: SYSTEM_DESIGN.md describes data flow
- [ ] **DOCS-04**: SYSTEM_DESIGN.md documents technology stack
- [ ] **DOCS-05**: SYSTEM_DESIGN.md includes pipeline flowchart (Mermaid)
- [ ] **DOCS-06**: SYSTEM_DESIGN.md describes ingestion with Docling
- [ ] **DOCS-07**: SYSTEM_DESIGN.md describes LLM extraction with Gemini
- [ ] **DOCS-08**: SYSTEM_DESIGN.md describes validation layer
- [ ] **DOCS-09**: SYSTEM_DESIGN.md describes storage in PostgreSQL
- [ ] **DOCS-10**: SYSTEM_DESIGN.md describes API retrieval
- [ ] **DOCS-11**: SYSTEM_DESIGN.md documents AI/LLM integration strategy
- [ ] **DOCS-12**: SYSTEM_DESIGN.md explains model selection rationale
- [ ] **DOCS-13**: SYSTEM_DESIGN.md explains dynamic model selection
- [ ] **DOCS-14**: SYSTEM_DESIGN.md documents prompt engineering approach
- [ ] **DOCS-15**: SYSTEM_DESIGN.md documents chunking strategy
- [ ] **DOCS-16**: SYSTEM_DESIGN.md documents confidence scoring formula
- [ ] **DOCS-17**: SYSTEM_DESIGN.md documents error recovery strategy
- [ ] **DOCS-18**: SYSTEM_DESIGN.md includes cost analysis (Flash vs Pro)
- [ ] **DOCS-19**: SYSTEM_DESIGN.md includes scaling projections (10x, 100x)
- [ ] **DOCS-20**: ARCHITECTURE_DECISIONS.md includes ADR-001 (Docling)
- [ ] **DOCS-21**: ARCHITECTURE_DECISIONS.md includes ADR-002 (Gemini)
- [ ] **DOCS-22**: ARCHITECTURE_DECISIONS.md includes ADR-003 (PostgreSQL)
- [ ] **DOCS-23**: ARCHITECTURE_DECISIONS.md includes ADR-004 (Cloud Run)
- [ ] **DOCS-24**: ARCHITECTURE_DECISIONS.md includes ADR-005 (Next.js)
- [ ] **DOCS-25**: README.md includes setup instructions
- [ ] **DOCS-26**: README.md includes run instructions (local and GCP)
- [ ] **DOCS-27**: README.md includes architecture summary
- [ ] **DOCS-28**: README.md includes API usage examples

### Testing & Quality

- [ ] **TEST-01**: Docling processor unit tests cover all file types
- [ ] **TEST-02**: Document service unit tests mock GCS and Docling
- [ ] **TEST-03**: GCS client unit tests mock Google Cloud Storage
- [ ] **TEST-04**: Ingestion integration tests cover full pipeline
- [ ] **TEST-05**: LLM client unit tests mock Gemini API
- [ ] **TEST-06**: Complexity classifier unit tests cover edge cases
- [ ] **TEST-07**: Extractor unit tests cover chunking and deduplication
- [ ] **TEST-08**: Validation unit tests cover all format checks
- [ ] **TEST-09**: Extraction integration tests use Flash and Pro models
- [ ] **TEST-10**: Database models unit tests cover relationships
- [ ] **TEST-11**: Repository unit tests mock database
- [ ] **TEST-12**: Document routes unit tests cover all endpoints
- [ ] **TEST-13**: Borrower routes unit tests cover search functionality
- [ ] **TEST-14**: E2E API tests cover upload-to-query flow
- [ ] **TEST-15**: Sample loan documents integration test with real corpus
- [ ] **TEST-16**: Frontend smoke tests cover critical paths
- [ ] **TEST-17**: pytest coverage report shows >80% backend coverage
- [ ] **TEST-18**: mypy strict mode passes with zero errors
- [ ] **TEST-19**: Frontend builds successfully with npm run build
- [ ] **TEST-20**: Terraform validates successfully

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Advanced Features

- **ADV-01**: Visual source linking - click extracted field to view document snippet
- **ADV-02**: HITL review workflow - manual review interface for low-confidence records
- **ADV-03**: Batch upload - multiple documents at once
- **ADV-04**: Export to Excel/CSV - borrower data export
- **ADV-05**: Real-time WebSocket status updates
- **ADV-06**: Advanced search - filters by confidence, date range, income range
- **ADV-07**: Audit trail - track all changes to borrower records
- **ADV-08**: Document comparison - diff two versions of same borrower
- **ADV-09**: Custom extraction templates - user-defined schemas
- **ADV-10**: Multi-language support - Spanish loan documents

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Real-time processing | Async queue-based processing sufficient, simpler architecture |
| Multi-tenancy | Single deployment model, no tenant isolation needed for portfolio project |
| Mobile native apps | Web-first with responsive design covers mobile browsers, no native needed |
| Custom OCR beyond Docling | Docling's built-in OCR capabilities sufficient for loan documents |
| Custom LLM fine-tuning | Using Gemini models as-is without custom training, faster iteration |
| User authentication | Public demo application, no user accounts or login required |
| Audit logging beyond basics | Application logs sufficient, no compliance audit trail needed |
| Data encryption beyond GCP defaults | GCP's default encryption adequate for demo/portfolio |
| Advanced analytics/BI dashboards | Basic querying sufficient, no complex reporting needed |
| Webhook notifications | Polling-based status checks sufficient for demo |
| Document versioning | Single version per document, no change history tracking |
| Collaborative editing | Single-user system, no concurrent editing scenarios |
| Rate limiting per user | No user accounts, rate limiting at API level only |
| A/B testing infrastructure | Single extraction approach, no experimentation framework |
| Custom deployment to non-GCP clouds | GCP-only deployment, no AWS/Azure support |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 1 | Pending |
| FOUND-02 | Phase 1 | Pending |
| FOUND-03 | Phase 1 | Pending |
| FOUND-04 | Phase 1 | Pending |
| FOUND-05 | Phase 1 | Pending |
| FOUND-06 | Phase 1 | Pending |
| FOUND-07 | Phase 1 | Pending |
| MODEL-01 | Phase 1 | Pending |
| MODEL-02 | Phase 1 | Pending |
| MODEL-03 | Phase 1 | Pending |
| MODEL-04 | Phase 1 | Pending |
| MODEL-05 | Phase 1 | Pending |
| MODEL-06 | Phase 1 | Pending |
| MODEL-07 | Phase 1 | Pending |
| INGEST-01 | Phase 2 | Pending |
| INGEST-02 | Phase 2 | Pending |
| INGEST-03 | Phase 2 | Pending |
| INGEST-04 | Phase 2 | Pending |
| INGEST-05 | Phase 2 | Pending |
| INGEST-06 | Phase 2 | Pending |
| INGEST-07 | Phase 2 | Pending |
| INGEST-08 | Phase 2 | Pending |
| INGEST-09 | Phase 2 | Pending |
| INGEST-10 | Phase 2 | Pending |
| INGEST-11 | Phase 2 | Pending |
| INGEST-12 | Phase 2 | Pending |
| INGEST-13 | Phase 2 | Pending |
| INGEST-14 | Phase 2 | Pending |
| DB-01 | Phase 2 | Pending |
| DB-02 | Phase 2 | Pending |
| DB-03 | Phase 2 | Pending |
| DB-04 | Phase 2 | Pending |
| DB-05 | Phase 2 | Pending |
| DB-06 | Phase 2 | Pending |
| DB-07 | Phase 2 | Pending |
| DB-08 | Phase 2 | Pending |
| DB-09 | Phase 2 | Pending |
| DB-10 | Phase 2 | Pending |
| DB-11 | Phase 2 | Pending |
| DB-12 | Phase 2 | Pending |
| EXTRACT-01 | Phase 3 | Pending |
| EXTRACT-02 | Phase 3 | Pending |
| EXTRACT-03 | Phase 3 | Pending |
| EXTRACT-04 | Phase 3 | Pending |
| EXTRACT-05 | Phase 3 | Pending |
| EXTRACT-06 | Phase 3 | Pending |
| EXTRACT-07 | Phase 3 | Pending |
| EXTRACT-08 | Phase 3 | Pending |
| EXTRACT-09 | Phase 3 | Pending |
| EXTRACT-10 | Phase 3 | Pending |
| EXTRACT-11 | Phase 3 | Pending |
| EXTRACT-12 | Phase 3 | Pending |
| EXTRACT-13 | Phase 3 | Pending |
| EXTRACT-14 | Phase 3 | Pending |
| EXTRACT-15 | Phase 3 | Pending |
| EXTRACT-16 | Phase 3 | Pending |
| EXTRACT-17 | Phase 3 | Pending |
| EXTRACT-18 | Phase 3 | Pending |
| EXTRACT-19 | Phase 3 | Pending |
| EXTRACT-20 | Phase 3 | Pending |
| EXTRACT-21 | Phase 3 | Pending |
| EXTRACT-22 | Phase 3 | Pending |
| EXTRACT-23 | Phase 3 | Pending |
| EXTRACT-24 | Phase 3 | Pending |
| EXTRACT-25 | Phase 3 | Pending |
| EXTRACT-26 | Phase 3 | Pending |
| EXTRACT-27 | Phase 3 | Pending |
| EXTRACT-28 | Phase 3 | Pending |
| EXTRACT-29 | Phase 3 | Pending |
| VALID-01 | Phase 3 | Pending |
| VALID-02 | Phase 3 | Pending |
| VALID-03 | Phase 3 | Pending |
| VALID-04 | Phase 3 | Pending |
| VALID-05 | Phase 3 | Pending |
| VALID-06 | Phase 3 | Pending |
| VALID-07 | Phase 3 | Pending |
| VALID-08 | Phase 3 | Pending |
| VALID-09 | Phase 3 | Pending |
| DB-13 | Phase 4 | Pending |
| DB-14 | Phase 4 | Pending |
| DB-15 | Phase 4 | Pending |
| DB-16 | Phase 4 | Pending |
| DB-17 | Phase 4 | Pending |
| DB-18 | Phase 4 | Pending |
| DB-19 | Phase 4 | Pending |
| DB-20 | Phase 4 | Pending |
| API-01 | Phase 4 | Pending |
| API-02 | Phase 4 | Pending |
| API-03 | Phase 4 | Pending |
| API-04 | Phase 4 | Pending |
| API-05 | Phase 4 | Pending |
| API-06 | Phase 4 | Pending |
| API-07 | Phase 4 | Pending |
| API-08 | Phase 4 | Pending |
| API-09 | Phase 4 | Pending |
| API-10 | Phase 4 | Pending |
| API-11 | Phase 4 | Pending |
| API-12 | Phase 4 | Pending |
| API-13 | Phase 4 | Pending |
| API-14 | Phase 4 | Pending |
| API-15 | Phase 4 | Pending |
| API-16 | Phase 4 | Pending |
| API-17 | Phase 4 | Pending |
| API-18 | Phase 4 | Pending |
| API-19 | Phase 4 | Pending |
| API-20 | Phase 4 | Pending |
| API-21 | Phase 4 | Pending |
| API-22 | Phase 4 | Pending |
| API-23 | Phase 4 | Pending |
| API-24 | Phase 4 | Pending |
| UI-01 | Phase 5 | Pending |
| UI-02 | Phase 5 | Pending |
| UI-03 | Phase 5 | Pending |
| UI-04 | Phase 5 | Pending |
| UI-05 | Phase 5 | Pending |
| UI-06 | Phase 5 | Pending |
| UI-07 | Phase 5 | Pending |
| UI-08 | Phase 5 | Pending |
| UI-09 | Phase 5 | Pending |
| UI-10 | Phase 5 | Pending |
| UI-11 | Phase 5 | Pending |
| UI-12 | Phase 5 | Pending |
| UI-13 | Phase 5 | Pending |
| UI-14 | Phase 5 | Pending |
| UI-15 | Phase 5 | Pending |
| UI-16 | Phase 5 | Pending |
| UI-17 | Phase 5 | Pending |
| UI-18 | Phase 5 | Pending |
| UI-19 | Phase 5 | Pending |
| UI-20 | Phase 5 | Pending |
| UI-21 | Phase 5 | Pending |
| UI-22 | Phase 5 | Pending |
| UI-23 | Phase 5 | Pending |
| UI-24 | Phase 5 | Pending |
| UI-25 | Phase 5 | Pending |
| UI-26 | Phase 5 | Pending |
| UI-27 | Phase 5 | Pending |
| UI-28 | Phase 5 | Pending |
| UI-29 | Phase 5 | Pending |
| UI-30 | Phase 5 | Pending |
| UI-31 | Phase 5 | Pending |
| UI-32 | Phase 5 | Pending |
| UI-33 | Phase 5 | Pending |
| UI-34 | Phase 5 | Pending |
| UI-35 | Phase 5 | Pending |
| UI-36 | Phase 5 | Pending |
| UI-37 | Phase 5 | Pending |
| INFRA-01 | Phase 6 | Pending |
| INFRA-02 | Phase 6 | Pending |
| INFRA-03 | Phase 6 | Pending |
| INFRA-04 | Phase 6 | Pending |
| INFRA-05 | Phase 6 | Pending |
| INFRA-06 | Phase 6 | Pending |
| INFRA-07 | Phase 6 | Pending |
| INFRA-08 | Phase 6 | Pending |
| INFRA-09 | Phase 6 | Pending |
| INFRA-10 | Phase 6 | Pending |
| INFRA-11 | Phase 6 | Pending |
| INFRA-12 | Phase 6 | Pending |
| INFRA-13 | Phase 6 | Pending |
| INFRA-14 | Phase 6 | Pending |
| INFRA-15 | Phase 6 | Pending |
| INFRA-16 | Phase 6 | Pending |
| INFRA-17 | Phase 6 | Pending |
| INFRA-18 | Phase 6 | Pending |
| INFRA-19 | Phase 6 | Pending |
| INFRA-20 | Phase 6 | Pending |
| INFRA-21 | Phase 6 | Pending |
| INFRA-22 | Phase 6 | Pending |
| INFRA-23 | Phase 6 | Pending |
| INFRA-24 | Phase 6 | Pending |
| INFRA-25 | Phase 6 | Pending |
| INFRA-26 | Phase 6 | Pending |
| INFRA-27 | Phase 6 | Pending |
| DOCS-01 | Phase 7 | Pending |
| DOCS-02 | Phase 7 | Pending |
| DOCS-03 | Phase 7 | Pending |
| DOCS-04 | Phase 7 | Pending |
| DOCS-05 | Phase 7 | Pending |
| DOCS-06 | Phase 7 | Pending |
| DOCS-07 | Phase 7 | Pending |
| DOCS-08 | Phase 7 | Pending |
| DOCS-09 | Phase 7 | Pending |
| DOCS-10 | Phase 7 | Pending |
| DOCS-11 | Phase 7 | Pending |
| DOCS-12 | Phase 7 | Pending |
| DOCS-13 | Phase 7 | Pending |
| DOCS-14 | Phase 7 | Pending |
| DOCS-15 | Phase 7 | Pending |
| DOCS-16 | Phase 7 | Pending |
| DOCS-17 | Phase 7 | Pending |
| DOCS-18 | Phase 7 | Pending |
| DOCS-19 | Phase 7 | Pending |
| DOCS-20 | Phase 7 | Pending |
| DOCS-21 | Phase 7 | Pending |
| DOCS-22 | Phase 7 | Pending |
| DOCS-23 | Phase 7 | Pending |
| DOCS-24 | Phase 7 | Pending |
| DOCS-25 | Phase 7 | Pending |
| DOCS-26 | Phase 7 | Pending |
| DOCS-27 | Phase 7 | Pending |
| DOCS-28 | Phase 7 | Pending |
| TEST-01 | Phase 7 | Pending |
| TEST-02 | Phase 7 | Pending |
| TEST-03 | Phase 7 | Pending |
| TEST-04 | Phase 7 | Pending |
| TEST-05 | Phase 7 | Pending |
| TEST-06 | Phase 7 | Pending |
| TEST-07 | Phase 7 | Pending |
| TEST-08 | Phase 7 | Pending |
| TEST-09 | Phase 7 | Pending |
| TEST-10 | Phase 7 | Pending |
| TEST-11 | Phase 7 | Pending |
| TEST-12 | Phase 7 | Pending |
| TEST-13 | Phase 7 | Pending |
| TEST-14 | Phase 7 | Pending |
| TEST-15 | Phase 7 | Pending |
| TEST-16 | Phase 7 | Pending |
| TEST-17 | Phase 7 | Pending |
| TEST-18 | Phase 7 | Pending |
| TEST-19 | Phase 7 | Pending |
| TEST-20 | Phase 7 | Pending |

**Coverage:**
- v1 requirements: 222 total
- Mapped to phases: 222/222
- Unmapped: 0

---
*Requirements defined: 2026-01-23*
*Last updated: 2026-01-23 after roadmap creation*
