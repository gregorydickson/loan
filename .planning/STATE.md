# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-24)

**Core value:** Accurate extraction of borrower data with complete traceability - every extracted field must include source attribution showing which document and page it came from.
**Current focus:** Phase 14 - OCR Routing & Fallback (Complete)

## Current Position

Milestone: v2.0 LangExtract & CloudBuild
Phase: 14 of 18 (OCR Routing & Fallback)
Plan: 2 of 2 in current phase
Status: Phase Complete
Last activity: 2026-01-25 - Completed 14-02-PLAN.md (OCR Router)

Progress: [#############=====..] 79% (v1.0 complete + Phase 10 + Phase 11 + Phase 12 + Phase 13 partial + Phase 14)

## Performance Metrics

**Velocity:**
- Total plans completed: 51 (v1.0: 36, v2.0: 15)
- Average duration: 4.9 min
- Total execution time: 4.69 hours

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

### Pending Todos

None yet.

### Blockers/Concerns

None - Phase 14 complete, ready for Phase 15.

## Phase 14 Completion Summary

**Plans:** 2 of 2 complete
**Requirements Satisfied:** LOCR-05, LOCR-11

**Deliverables (14-01):**
- ScannedDocumentDetector class with pypdfium2 text ratio detection
- DetectionResult dataclass for structured output
- Page-level and document-level detection
- Configurable thresholds (MIN_CHARS_THRESHOLD, SCANNED_RATIO_THRESHOLD)
- 17 unit tests

**Deliverables (14-02):**
- OCRRouter with circuit breaker protection (fail_max=3, 60s timeout)
- OCRMode type alias: auto, force, skip
- OCRResult dataclass for tracking OCR method used
- Automatic Docling fallback on GPU unavailability
- 18 unit tests

**Total Phase 14:** 10 min, 35 unit tests

## Session Continuity

Last session: 2026-01-25T15:47:00Z
Stopped at: Completed 14-02-PLAN.md (OCR Router)
Resume file: None
Next action: Phase 15 (Dual Pipeline Integration) or Phase 13-04 (API Integration)
