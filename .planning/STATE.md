# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-24)

**Core value:** Accurate extraction of borrower data with complete traceability - every extracted field must include source attribution showing which document and page it came from.
**Current focus:** Phase 16 - CloudBuild Deployment (In Progress)

## Current Position

Milestone: v2.0 LangExtract & CloudBuild
Phase: 16 of 18 (CloudBuild Deployment)
Plan: 3 of 3 in current phase
Status: Phase Complete
Last activity: 2026-01-25 - Completed 16-03-PLAN.md (GitHub Triggers & Deployment Guide)

Progress: [################==..] 87% (v1.0 complete + Phase 10 + Phase 11 + Phase 12 + Phase 13 partial + Phase 14 + Phase 15 + Phase 16)

## Performance Metrics

**Velocity:**
- Total plans completed: 55 (v1.0: 36, v2.0: 19)
- Average duration: 4.7 min
- Total execution time: 4.97 hours

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

**v2.0 Phase 13 In Progress:**

| Plan | Name | Duration | Status |
|------|------|----------|--------|
| 13-01 | LightOnOCR GPU Infrastructure | 3 min | Complete |
| 13-02 | Cloud Run GPU Deployment | 45 min | Complete |
| 13-03 | LightOnOCR Client | 4 min | Complete |
| 13-04 | API Integration | - | Pending |

**Phase 13 Progress:** 3 of 4 plans complete

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

### Pending Todos

None yet.

### Blockers/Concerns

None - Phase 16 complete.

## Phase 16 Completion Summary

**Plans:** 3 of 3 complete
**Requirements Satisfied:** CBLD-05, CBLD-06, CBLD-07, CBLD-10, CBLD-11

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

## Session Continuity

Last session: 2026-01-25T17:26:00Z
Stopped at: Completed 16-03-PLAN.md (GitHub Triggers & Deployment Guide)
Resume file: None
Next action: Phase 17 (Frontend Integration) or Phase 18 (Testing & Verification)
