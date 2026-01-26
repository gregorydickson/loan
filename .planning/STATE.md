# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-25)

**Core value:** Accurate extraction of borrower data with complete traceability - every extracted field must include source attribution showing which document and page it came from.
**Current focus:** v2.1 Production Deployment & Verification - Phase 20 Plan 01 COMPLETE

## Current Position

Milestone: v2.1 Production Deployment & Verification
Phase: 20 of 21 (Core Extraction Verification)
Plan: 1 of 2 complete
Status: In progress
Last activity: 2026-01-26 - Completed 20-01-PLAN.md (Production Configuration Resolution)

Progress: [####################] 100% (v1.0 + v2.0) | v2.1: [##############------] 70% (20-01 complete, 20-02 and 21 remaining)

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

### Pending Todos

- Execute Phase 20-02 (Extraction Testing)
- Execute Phase 21 (Final Verification)

### Blockers/Concerns

None - all configuration blockers resolved in 20-01.

## Session Continuity

Last session: 2026-01-26T03:47:00Z
Stopped at: Completed 20-01-PLAN.md (Production Configuration Resolution)
Resume file: None
Next action: Execute Phase 20-02 (Extraction Testing)

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

## Phase 20-01 Completion Summary

Production configuration blockers resolved:

| Configuration | Status | Details |
|---------------|--------|---------|
| Database | CONFIGURED | loan_extraction database created |
| database-url secret | v5 | Valid connection string |
| gemini-api-key secret | v2 | Real API key (placeholder disabled) |
| API /documents/ | 200 | Returns empty list (working) |

Ready for extraction verification testing in 20-02.
