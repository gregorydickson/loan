# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-25)

**Core value:** Accurate extraction of borrower data with complete traceability - every extracted field must include source attribution showing which document and page it came from.
**Current focus:** Planning next milestone

## Current Position

Milestone: Next milestone (TBD)
Phase: Not started
Plan: Not started
Status: Ready to plan next milestone
Last activity: 2026-01-25 - v2.0 milestone archived

Progress: [####################] 100% (v1.0 + v2.0 shipped)

## Performance Metrics

**Velocity:**
- Total plans completed: 64 (v1.0: 36, v2.0: 28)
- Average duration: 4.5 min
- Total execution time: 5.52 hours

**By Phase (v1.0):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation | 3 | 17 min | 5.7 min |
| 02-document-ingestion-pipeline | 4 | 34 min | 8.5 min |
| 03-llm-extraction-validation | 5 | 49 min | 9.8 min |
| 04-data-storage-rest-api | 3 | 18 min | 6.0 min |
| 05-frontend-dashboard | 5 | 16 min | 3.2 min |
| 06-gcp-infrastructure | 4 | 30 min | 7.5 min |
| 07-documentation-testing | 5 | 35 min | 7.0 min |
| 08-wire-document-to-extraction-pipeline | 3 | 19 min | 6.3 min |
| 09-cloud-tasks-background-processing | 4 | 21 min | 5.3 min |

**v2.0 Phase 10 Complete:**

| Plan | Name | Duration | Status |
|------|------|----------|--------|
| 10-01 | GPU Quota Check | 5 min | Complete |
| 10-02 | Terraform Archival | 3 min | Complete |
| 10-03 | CloudBuild Foundation | 8 min | Complete |
| 10-04 | vLLM Validation Scripts | 4 min | Complete |
| 10-05 | Gap Closure: Service Account | 2 min | Complete |

**Phase 10 Total:** 22 min (5 plans, avg 4.4 min/plan)

**v2.0 Phase 11 Complete:**

| Plan | Name | Duration | Status |
|------|------|----------|--------|
| 11-01 | Schema Updates | 4 min | Complete |
| 11-02 | Few-shot Examples | 5 min | Complete |
| 11-03 | LangExtractProcessor + OffsetTranslator | 6 min | Complete |
| 11-04 | Verification Tests | 5 min | Complete |

**Phase 11 Total:** 20 min (4 plans, avg 5.0 min/plan)

**v2.0 Phase 12 Complete:**

| Plan | Name | Duration | Status |
|------|------|----------|--------|
| 12-01 | ExtractionConfig Dataclass | 4 min | Complete |
| 12-02 | HTML Visualization Wrapper | 3 min | Complete |
| 12-03 | Extraction Router with Fallback | 4 min | Complete |

**Phase 12 Total:** 11 min (3 plans, avg 3.7 min/plan)

**v2.0 Phase 13 Complete:**

| Plan | Name | Duration | Status |
|------|------|----------|--------|
| 13-01 | LightOnOCR GPU Infrastructure | 3 min | Complete |
| 13-02 | Cloud Run GPU Deployment | 45 min | Complete |
| 13-03 | LightOnOCR Client | 4 min | Complete |

**Phase 13 Total:** 52 min (3 plans, avg 17.3 min/plan)

**Note:** Monitoring/metrics deferred as operational enhancement. API integration handled in Phase 14 (OCRRouter).

**v2.0 Phase 14 Complete:**

| Plan | Name | Duration | Status |
|------|------|----------|--------|
| 14-01 | Scanned Document Detection | 4 min | Complete |
| 14-02 | OCR Router | 6 min | Complete |

**Phase 14 Total:** 10 min (2 plans, avg 5.0 min/plan)

**v2.0 Phase 15 Complete:**

| Plan | Name | Duration | Status |
|------|------|----------|--------|
| 15-01 | Schema & API Parameters | 3 min | Complete |
| 15-02 | Service Layer Integration | 8 min | Complete |

**Phase 15 Total:** 11 min (2 plans, avg 5.5 min/plan)

**v2.0 Phase 16 Complete:**

| Plan | Name | Duration | Status |
|------|------|----------|--------|
| 16-01 | CloudBuild YAML Configs | 5 min | Complete |
| 16-02 | Infrastructure Scripts & Rollback | 3 min | Complete |
| 16-03 | GitHub Triggers & Deployment Guide | 3 min | Complete |

**Phase 16 Total:** 11 min (3 plans, avg 3.7 min/plan)

**v2.0 Phase 17 Complete:**

| Plan | Name | Duration | Status |
|------|------|----------|--------|
| 17-01 | Test Baseline & mypy Strict | 9 min | Complete |
| 17-02 | Few-shot & LangExtract Testing | 4 min | Complete |
| 17-03 | GPU Cold Start & TEST Requirements | 4 min | Complete |

**Phase 17 Total:** 17 min (3 plans, avg 5.7 min/plan)

**v2.0 Phase 18 Complete:**

| Plan | Name | Duration | Status |
|------|------|----------|--------|
| 18-01 | User-Facing Documentation | 4 min | Complete |
| 18-02 | v2.0 Architecture & Migration Documentation | 3 min | Complete |
| 18-03 | Frontend Integration | 4 min | Complete |

**Phase 18 Total:** 11 min (3 plans, avg 3.7 min/plan)

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting v2.0 work:

- [v1.0]: Docling for document processing - successful, continues as one of dual pipelines
- [v1.0]: Gemini 3.0 with dynamic model selection - successful, extends to LangExtract
- [v1.0]: Cloud Tasks for async processing - successful, extends to dual pipeline with method params
- [v2.0]: Dual extraction pipelines (Docling + LangExtract) with API-based selection
- [v2.0]: LightOnOCR as dedicated GPU service with scale-to-zero for cost management
- [v2.0]: CloudBuild replaces Terraform for application deployments
- [10-02]: Terraform state remains in GCS, not copied locally for recovery capability
- [10-03]: CloudBuild uses dedicated cloudbuild-deployer service account with 5 least-privilege IAM roles
- [10-04]: Local vLLM validation skipped (no GPU), deferred to Phase 13 cloud deployment
- [10-05]: CloudBuild service account created in GCP with 5 IAM roles, closes CBLD-08 gap
- [10-05]: Gap closure executed setup-service-account.sh, CBLD-08 now satisfied
- [11-02]: Few-shot examples use ExampleData/Extraction from langextract.data
- [11-02]: All extraction_text values must be verbatim substrings (validated programmatically)
- [11-03]: OffsetTranslator uses difflib.SequenceMatcher for Docling markdown alignment
- [11-03]: LangExtractProcessor maps GOOGLE_API_KEY to LANGEXTRACT_API_KEY
- [11-04]: Unit tests use mock dataclasses for LangExtract API isolation
- [12-01]: ExtractionConfig uses dataclass with __post_init__ validation (not Pydantic)
- [12-01]: extraction_passes range 2-5, max_workers range 1-50, max_char_buffer range 500-5000
- [12-02]: Use lx.visualize() directly - handles overlapping spans, animation, legend
- [12-02]: Handle both Jupyter (.data) and standalone (str()) return contexts
- [12-03]: Transient errors (503, 429, timeout, overloaded, rate limit) retry 3x with exponential backoff
- [12-03]: Fatal errors trigger immediate fallback without retry
- [12-03]: method='auto' (default) tries LangExtract first, falls back to Docling on failure
- [13-03]: Use id_token.fetch_id_token for Cloud Run OIDC authentication
- [13-03]: 120s default timeout for GPU cold start tolerance
- [13-03]: Detect PNG vs JPEG via magic bytes for proper data URI encoding
- [13-01]: vLLM v0.11.2 base image with transformers from source for LightOnOCR-2-1B
- [13-01]: Model baked into Docker image for faster cold starts
- [13-01]: 8 vCPU, 32Gi memory, L4 GPU, 240s startup probe
- [13-02]: Cloud Build used for GPU image build (local disk space constraints)
- [13-02]: Transformers pinned to 4.57.1 for vLLM compatibility
- [13-02]: GPU memory utilization 80%, max_seqs=8 to prevent OOM on L4
- [14-01]: MIN_CHARS_THRESHOLD=50 for scanned page detection
- [14-01]: SCANNED_RATIO_THRESHOLD=0.5 triggers full-document OCR
- [14-01]: Conservative error handling: assume scanned on parse/extraction failures
- [14-01]: pypdfium2 (via Docling) for text extraction - no new dependencies
- [14-02]: aiobreaker uses timeout_duration parameter (not reset_timeout)
- [14-02]: Circuit breaker: fail_max=3, timeout_duration=60s
- [14-02]: OCR modes: auto (detect), force (always OCR), skip (never OCR)
- [14-02]: Circuit breaker state exposed as lowercase string via .name.lower()
- [15-01]: Default method=docling preserves v1.0 backward compatibility (DUAL-09)
- [15-01]: Nullable columns allow legacy documents to coexist without migration
- [15-01]: ExtractionMethod includes 'auto' option for future auto-detection
- [15-02]: DUAL-04: OCRRouter runs BEFORE extraction when ocr != 'skip'
- [15-02]: ProcessDocumentRequest defaults ensure backward compat with queued tasks
- [15-02]: OCR-then-extract pipeline pattern for dual pipeline
- [16-02]: All gcloud commands use existence checks for idempotency
- [17-01]: Use mypy overrides with follow_imports=skip for untyped libraries
- [17-01]: Add type:ignore[untyped-decorator] for aiobreaker circuit breaker
- [17-01]: Convert difflib Match namedtuples to explicit tuple[int,int,int] for type safety
- [17-02]: Validate extraction_text as exact substring (not fuzzy match)
- [17-02]: Mock ExtractionRouter for E2E tests to isolate from real LLM calls
- [17-02]: Include regression tests for Docling default method (DUAL-09)
- [17-03]: GPU cold start tests focus on scenarios not covered by lightonocr_client tests
- [17-03]: Comprehensive TEST verification runs each test file individually
- [18-01]: Documentation organized by audience (docs/api/ for users, docs/guides/ for operators)
- [18-02]: ADRs follow existing MADR format for consistency with v1.0 documentation
- [18-02]: System design includes Mermaid diagrams for dual pipeline visualization
- [18-03]: Default values (docling, auto) match v1.0 behavior for backward compatibility
- [18-03]: Select dropdowns disabled during upload pending state
- [18-03]: Dynamic description text updates based on method selection

### Pending Todos

None - ready for next milestone.

### Blockers/Concerns

None - v2.0 shipped successfully.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 001 | use the code-simplifier agent to review the project | 2026-01-25 | c526ec2 | [001-use-the-code-simplifier-agent-to-review-](./quick/001-use-the-code-simplifier-agent-to-review-/) |
| 002 | implement code simplification quick wins | 2026-01-25 | ff60a13 | [002-run-the-code-simplifier-agent-on-the-pro](./quick/002-run-the-code-simplifier-agent-on-the-pro/) |
| 003 | update README with ASCII art and emojis | 2026-01-25 | 25a3893 | [003-update-the-readme-with-ascii-art-extensi](./quick/003-update-the-readme-with-ascii-art-extensi/) |

## Phase 17 Completion Summary

**Plans:** 3 of 3 complete
**Requirements Satisfied:** All 12 TEST requirements (TEST-01 through TEST-12)

**Deliverables (17-01):**
- backend/tests/unit/test_document_service.py - Fixed constructor calls
- backend/pyproject.toml - mypy overrides configuration
- 6 source files with type annotations/fixes

**Deliverables (17-02):**
- backend/tests/unit/extraction/test_few_shot_examples.py (17 tests)
- backend/tests/integration/test_e2e_langextract.py (8 tests)
- Updated backend/tests/integration/conftest.py with LangExtract fixtures

**Deliverables (17-03):**
- backend/tests/unit/ocr/test_gpu_cold_start.py (14 tests)
- Comprehensive TEST requirement verification

**Final Metrics:**
- Total tests: 490 passed, 1 skipped
- Coverage: 86.98% (threshold: 80%)
- mypy: Success - 0 errors in 41 source files

**Total Phase 17:** 17 min (3 plans, avg 5.7 min/plan)

## Phase 16 Completion Summary

**Plans:** 3 of 3 complete
**Requirements Satisfied:** CBLD-01, CBLD-02, CBLD-03, CBLD-05, CBLD-06, CBLD-07, CBLD-09, CBLD-10, CBLD-11

**Deliverables (16-01):**
- backend-cloudbuild.yaml with VPC egress and Secret Manager
- frontend-cloudbuild.yaml with NEXT_PUBLIC_API_URL
- gpu-cloudbuild.yaml with L4 GPU configuration

**Deliverables (16-02):**
- docs/terraform-to-gcloud-inventory.md (CBLD-05)
- infrastructure/scripts/provision-infra.sh (CBLD-06)
- infrastructure/scripts/rollback.sh (CBLD-11)

**Deliverables (16-03):**
- infrastructure/scripts/setup-github-triggers.sh (CBLD-07)
- docs/cloudbuild-deployment-guide.md (CBLD-10, CBLD-11)

**Total Phase 16:** 11 min (3 plans, avg 3.7 min/plan)

## Phase 15 Completion Summary

**Plans:** 2 of 2 complete
**Requirements Satisfied:** DUAL-04, DUAL-05, DUAL-08, DUAL-09

**Deliverables (15-01):**
- Document model with extraction_method and ocr_processed columns
- Alembic migration 003_add_extraction_metadata.py
- Upload endpoint with method and ocr query parameters
- ExtractionMethod and OCRMode type aliases

**Deliverables (15-02):**
- Cloud Tasks payload with method/ocr parameters
- DocumentService wired to OCRRouter and ExtractionRouter
- Task handler using OCRRouter before extraction (DUAL-04)
- Full dual pipeline wiring from API to extraction
- 6 integration tests for DUAL-08 character offset verification

**Total Phase 15:** 11 min, 6 integration tests

## Phase 18-02 Completion Summary

**Plan:** 18-02 (v2.0 Architecture & Migration Documentation)
**Duration:** 3 min
**Requirements Satisfied:** DOCS-04, DOCS-06, DOCS-07, DOCS-09, DOCS-12

**Deliverables:**
- docs/ARCHITECTURE_DECISIONS.md - ADR-018, ADR-019, ADR-020 added
- docs/SYSTEM_DESIGN.md - v2.0 dual pipeline section with Mermaid diagrams
- docs/migration/terraform-migration.md - Terraform to CloudBuild migration guide

## Phase 18-01 Completion Summary

**Plan:** 18-01 (User-Facing Documentation)
**Duration:** 4 min
**Requirements Satisfied:** DOCS-01, DOCS-02, DOCS-05, DOCS-08, DOCS-10, DOCS-11, DUAL-10

**Deliverables:**
- docs/api/extraction-method-guide.md - Method selection guide with curl examples
- docs/guides/few-shot-examples.md - Few-shot example creation guide
- docs/guides/gpu-service-cost.md - GPU cost management strategies
- docs/guides/lightonocr-deployment.md - LightOnOCR deployment guide

## Phase 18-03 Completion Summary

**Plan:** 18-03 (Frontend Integration)
**Duration:** 4 min
**Requirements Satisfied:** DUAL-12

**Deliverables:**
- frontend/src/components/ui/select.tsx - shadcn Select component
- frontend/src/lib/api/types.ts - ExtractionMethod, OCRMode types
- frontend/src/lib/api/documents.ts - uploadDocumentWithParams function
- frontend/src/hooks/use-documents.ts - Extended useUploadDocument with params
- frontend/src/components/documents/upload-zone.tsx - Method/OCR Select dropdowns

**User Verification:** UI tested and approved via checkpoint

## v2.0 Milestone Complete

**Phases:** 10 through 18 (9 phases, 28 plans)
**Total Duration:** ~2 hours
**Requirements Satisfied:** All DUAL, CBLD, TEST, DOCS requirements

**Key Deliverables:**
- Dual extraction pipelines (Docling + LangExtract)
- LightOnOCR GPU service with scale-to-zero
- CloudBuild deployment replacing Terraform
- Comprehensive test coverage (86.98%)
- Full documentation suite
- Frontend extraction method selection

## Session Continuity

Last session: 2026-01-25T20:30:00Z
Stopped at: Completed quick task 003 (README with ASCII art and emojis)
Resume file: None
Next action: v2.0 milestone complete - ready for production deployment
