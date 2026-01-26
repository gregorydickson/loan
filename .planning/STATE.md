# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-25)

**Core value:** Accurate extraction of borrower data with complete traceability - every extracted field must include source attribution showing which document and page it came from.
**Current focus:** v2.1 Production Deployment & Verification - Phase 20 COMPLETE, ready for Phase 21

## Current Position

Milestone: v2.1 Production Deployment & Verification
Phase: 20 of 21 (Core Extraction Verification) - COMPLETE
Plan: 3 of 3 complete (Phase 20 COMPLETE)
Status: In progress - ready for Phase 21
Last activity: 2026-01-26 - Completed 20-03-PLAN.md (Extraction Results Verification)

Progress: [####################] 100% (v1.0 + v2.0) | v2.1: [##################--] 90% (Phases 19-20 complete, Phase 21 remaining)

## Performance Metrics

**Velocity:**
- Total plans completed: 71 (v1.0: 36, v2.0: 28, v2.1: 7)
- Average duration: 4.5 min
- Total execution time: ~8 hours

**By Milestone:**

| Milestone | Phases | Plans | Total Time | Shipped |
|-----------|--------|-------|------------|---------|
| v1.0 MVP | 1-9 | 36 | ~4 hours | 2026-01-24 |
| v2.0 LangExtract | 10-18 | 28 | ~2 hours | 2026-01-25 |
| v2.1 Deployment | 19-21 | 7/10 | ~2 hours | In Progress |

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
- [20-03]: TEST-05 marked PARTIAL PASS - GPU infrastructure deployed, backend integration deferred to Phase 15
- [20-03]: All core extraction functionality (Docling + LangExtract) verified working in production

### Pending Todos

- Execute Phase 21 (Final Verification)

### Blockers/Concerns

- GPU OCR integration incomplete (infrastructure deployed, backend integration deferred to Phase 15)
- This is non-blocking for v2.1 milestone completion

## Session Continuity

Last session: 2026-01-26T07:15:00Z
Stopped at: Completed 20-03-PLAN.md (Extraction Results Verification)
Resume file: None
Next action: Execute Phase 21 (Final Verification)

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

## Phase 20 Completion Summary

All Phase 20 verification tests completed:

| Test | Requirement | Status | Notes |
|------|-------------|--------|-------|
| TEST-01 | Frontend loads | PASS | Verified in 20-02 |
| TEST-02 | Upload works | PASS | Verified in 20-02 |
| TEST-03 | Docling extraction | PASS | Structured borrower data extracted |
| TEST-04 | LangExtract + offsets | PASS | char_start/char_end present |
| TEST-05 | GPU OCR | PARTIAL | Infrastructure ready, integration deferred |

**Phase 20 Overall:** 4/5 PASS, 1/5 PARTIAL PASS

**Production fixes applied during Phase 20:**
- dc6925d0: DocumentStatus enum mapping
- afa19566: Tesseract OCR dependencies
- 98873b1b: Disabled RapidOCR downloads
- 088b1d24: Error logging + memory increase
- d5f5a2f4: Partial borrower persistence
- 404cc975: Pre-download Docling models

Ready for final verification in Phase 21.
