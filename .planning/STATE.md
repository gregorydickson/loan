# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-24)

**Core value:** Accurate extraction of borrower data with complete traceability - every extracted field must include source attribution showing which document and page it came from.
**Current focus:** Phase 12 - LangExtract Advanced Features (COMPLETE)

## Current Position

Milestone: v2.0 LangExtract & CloudBuild
Phase: 12 of 18 (LangExtract Advanced Features)
Plan: 3 of 3 in current phase
Status: Phase Complete
Last activity: 2026-01-25 - Completed 12-03-PLAN.md (Extraction Router with Fallback)

Progress: [###########=======..] 70% (v1.0 complete + Phase 10 + Phase 11 + Phase 12)

## Performance Metrics

**Velocity:**
- Total plans completed: 47 (v1.0: 36, v2.0: 11)
- Average duration: 5.1 min
- Total execution time: 4.42 hours

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

### Pending Todos

None yet.

### Blockers/Concerns

None - Phase 12 complete.

## Phase 12 Completion Summary

**Plans:** 3 plans (all complete)
**Requirements Satisfied:** LXTR-06, LXTR-07, LXTR-10, LXTR-11

**Deliverables (12-01):**
- ExtractionConfig dataclass with validation
- Configurable multi-pass extraction (2-5 passes)
- Configurable parallel processing (max_workers 1-50)
- 12 unit tests for boundary validation

**Deliverables (12-02):**
- LangExtractVisualizer class wrapping lx.visualize()
- HTML visualization with highlighted source spans
- Empty placeholder HTML for no-extraction cases
- 8 unit tests with full mocking

**Deliverables (12-03):**
- ExtractionRouter with method selection (langextract, docling, auto)
- Tenacity retry with exponential backoff for transient errors
- Graceful fallback to Docling on LangExtract failures
- 25 unit tests for all router scenarios

## Session Continuity

Last session: 2026-01-25T12:13:25Z
Stopped at: Completed 12-03-PLAN.md (Extraction Router with Fallback)
Resume file: None
Next action: Phase 13 planning (API Integration)
