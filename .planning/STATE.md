# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-24)

**Core value:** Accurate extraction of borrower data with complete traceability - every extracted field must include source attribution showing which document and page it came from.
**Current focus:** Phase 11 - LangExtract Core Integration

## Current Position

Milestone: v2.0 LangExtract & CloudBuild
Phase: 11 of 18 (LangExtract Core Integration)
Plan: 2 of 4 in current phase
Status: In progress
Last activity: 2026-01-25 - Completed 11-02-PLAN.md (few-shot examples)

Progress: [##########=====.....] 63% (v1.0 complete + Phase 10 + 11-01 + 11-02)

## Performance Metrics

**Velocity:**
- Total plans completed: 41 (v1.0: 36, v2.0: 5)
- Average duration: 5.4 min
- Total execution time: 4.0 hours

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

### Pending Todos

None yet.

### Blockers/Concerns

From research (address in Phase 11):
- LangExtract offset alignment with Docling markdown - addressed in 11-03 OffsetTranslator

## Phase 11 Planning Summary

**Plans:** 4 plans in 3 waves
**Requirements:** LXTR-01, LXTR-02, LXTR-03, LXTR-04, LXTR-05, LXTR-08, LXTR-09, LXTR-12

**Wave Structure:**
- Wave 1 (parallel): 11-01 (schema), 11-02 (examples)
- Wave 2: 11-03 (LangExtractProcessor + OffsetTranslator)
- Wave 3: 11-04 (verification tests)

**Plan Summary:**
| Plan | Objective | Tasks | Files |
|------|-----------|-------|-------|
| 11-01 | Schema updates for char_start/char_end | 2 | document.py, models.py, migration |
| 11-02 | Few-shot examples for LangExtract | 3 | examples/*.py |
| 11-03 | LangExtractProcessor + OffsetTranslator | 3 | langextract_processor.py, offset_translator.py |
| 11-04 | Verification tests | 3 | test_*.py |

## Session Continuity

Last session: 2026-01-25
Stopped at: Completed 11-02-PLAN.md (few-shot examples)
Resume file: None
Next action: Continue Phase 11 execution (11-03, 11-04)
