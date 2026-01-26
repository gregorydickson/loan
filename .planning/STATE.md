# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-25)

**Core value:** Accurate extraction of borrower data with complete traceability - every extracted field must include source attribution showing which document and page it came from.
**Current focus:** v2.1 Production Deployment & Verification - Phase 21 Plan 01 COMPLETE

## Current Position

Milestone: v2.1 Production Deployment & Verification
Phase: 21 of 21 (UI Feature Verification)
Plan: 1 of 2 complete
Status: In progress - ready for Plan 21-02
Last activity: 2026-01-26 - Completed 21-01-PLAN.md (API and Frontend Offset Fields)

Progress: [####################] 100% (v1.0 + v2.0) | v2.1: [###################-] 95% (Plan 21-02 remaining)

## Performance Metrics

**Velocity:**
- Total plans completed: 73 (v1.0: 36, v2.0: 28, v2.1: 9)
- Average duration: 4.5 min
- Total execution time: ~8.5 hours

**By Milestone:**

| Milestone | Phases | Plans | Total Time | Shipped |
|-----------|--------|-------|------------|---------|
| v1.0 MVP | 1-9 | 36 | ~4 hours | 2026-01-24 |
| v2.0 LangExtract | 10-18 | 28 | ~2 hours | 2026-01-25 |
| v2.1 Deployment | 19-21 | 9/10 | ~2.5 hours | In Progress |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting v2.1 work:

- [v2.0]: CloudBuild replaces Terraform for application deployments
- [v2.0]: Dual extraction pipelines (Docling + LangExtract) with API-based selection
- [v2.0]: LightOnOCR as dedicated GPU service with scale-to-zero for cost management
- [18-03]: Default values (docling, auto) match v1.0 behavior for backward compatibility
- [19-01]: Used memorygraph-prod GCP project for deployment (user decision)
- [19-01]: Created loan-specific Artifact Registry repository and VPC infrastructure
- [19-03]: GPU service already deployed with correct configuration - verified instead of redeployed
- [19-04]: Application config (database, API key) deferred - deployment verification complete
- [20-01]: Created new loan_extraction database (option-a) instead of reusing existing database
- [20-01]: Used postgres user with password auth for database connectivity
- [20-02]: Pre-download Docling models during Docker build (not at runtime) for Cloud Run reliability
- [20-02]: Increased Cloud Run memory to 4Gi for Docling processing requirements
- [20-03]: TEST-05 marked PARTIAL PASS - GPU infrastructure deployed, backend integration completed in 20-04
- [20-03]: All core extraction functionality (Docling + LangExtract) verified working in production
- [20-04]: GPU OCR integration wired - scanned pages now processed via LightOnOCR GPU service
- [21-01]: Badge indicator vs text highlighting - chose badge for simplicity (char offsets are document-level, not snippet-level)

### Pending Todos

- Execute Plan 21-02 (UI Feature Verification - manual browser testing)

### Blockers/Concerns

None - Phase 21 Plan 01 complete, API and frontend deployed with char offset support

## Session Continuity

Last session: 2026-01-26T17:55:36Z
Stopped at: Completed 21-01-PLAN.md (API and Frontend Offset Fields)
Resume file: None
Next action: Execute Plan 21-02 (UI Feature Verification)

## Production Service URLs

```
BACKEND_URL=https://loan-backend-prod-fjz2snvxjq-uc.a.run.app
FRONTEND_URL=https://loan-frontend-prod-fjz2snvxjq-uc.a.run.app
GPU_URL=https://lightonocr-gpu-fjz2snvxjq-uc.a.run.app
```

## GPU Service Configuration

```yaml
Service: lightonocr-gpu
Region: us-central1
GPU: nvidia-l4 (1 GPU)
CPU: 8, Memory: 32Gi
Scaling: min=0 (scale-to-zero), max=3
Model: LightOnOCR-2-1B via vLLM
Health: /health returns 200
```

## Phase 21 Progress

| Plan | Name | Status | Notes |
|------|------|--------|-------|
| 21-01 | API and Frontend Offset Fields | COMPLETE | char_start/char_end exposed in API, badge indicator in UI |
| 21-02 | UI Feature Verification | PENDING | Manual browser testing for TEST-06 through TEST-09 |

**Plan 21-01 Commits:**
- 0c9fbc30: feat(21-01): expose char_start/char_end in API response
- 3fd06d4d: feat(21-01): add char_start/char_end to frontend and display badge

**Deployments (21-01):**
- Backend: Build 793308eb (SUCCESS, 29 min)
- Frontend: Build 18427397 (SUCCESS, 5 min)

## Phase 20 Completion Summary

All Phase 20 verification tests completed:

| Test | Requirement | Status | Notes |
|------|-------------|--------|-------|
| TEST-01 | Frontend loads | PASS | Verified in 20-02 |
| TEST-02 | Upload works | PASS | Verified in 20-02 |
| TEST-03 | Docling extraction | PASS | Structured borrower data extracted |
| TEST-04 | LangExtract + offsets | PASS | char_start/char_end present |
| TEST-05 | GPU OCR | PASS | Backend integration wired in 20-04 (code verified) |

**Phase 20 Overall:** 5/5 PASS (all requirements verified in code)

**Production fixes applied during Phase 20:**
- dc6925d0: DocumentStatus enum mapping
- afa19566: Tesseract OCR dependencies
- 98873b1b: Disabled RapidOCR downloads
- 088b1d24: Error logging + memory increase
- d5f5a2f4: Partial borrower persistence
- 404cc975: Pre-download Docling models
- ed59d8cf: GPU OCR integration wiring
- fc132cb2: GPU OCR integration tests

Ready for final UI verification in Plan 21-02.
