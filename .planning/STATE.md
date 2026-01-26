# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-25)

**Core value:** Accurate extraction of borrower data with complete traceability - every extracted field must include source attribution showing which document and page it came from.
**Current focus:** v2.1 Production Deployment & Verification - Phase 19 COMPLETE

## Current Position

Milestone: v2.1 Production Deployment & Verification
Phase: 19 of 21 (Production Deployment Verification) - COMPLETE
Plan: 4 of 4 complete
Status: Phase complete
Last activity: 2026-01-26 - Completed 19-04-PLAN.md (Secrets Verification and Health Check)

Progress: [####################] 100% (v1.0 + v2.0) | v2.1: [############--------] 60% (Phase 19 complete, 20-21 remaining)

## Performance Metrics

**Velocity:**
- Total plans completed: 70 (v1.0: 36, v2.0: 28, v2.1: 6)
- Average duration: 4.5 min
- Total execution time: ~7.5 hours

**By Milestone:**

| Milestone | Phases | Plans | Total Time | Shipped |
|-----------|--------|-------|------------|---------|
| v1.0 MVP | 1-9 | 36 | ~4 hours | 2026-01-24 |
| v2.0 LangExtract | 10-18 | 28 | ~2 hours | 2026-01-25 |
| v2.1 Deployment | 19-21 | 4/10 | ~90 min | In Progress |

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
- [19-01]: Placeholder gemini-api-key needs real key for extraction functionality
- [19-03]: GPU service already deployed with correct configuration - verified instead of redeployed
- [19-04]: Application config (database, API key) deferred - deployment verification complete

### Pending Todos

- Provide real Gemini API key to gemini-api-key secret
- Configure database for loan application (create loan_extraction database or update connection string)
- Run database migrations after database is configured

### Blockers/Concerns

- **Database not configured**: API endpoints return 500 - database-url points to memorygraph_auth which lacks loan schema
- **Gemini API key placeholder**: Extraction functionality won't work until real key provided

## Session Continuity

Last session: 2026-01-26T02:32:46Z
Stopped at: Completed 19-04-PLAN.md (Secrets Verification and Health Check)
Resume file: None
Next action: Execute Phase 20 (Core Extraction Verification)

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

## Phase 19 Completion Summary

All DEPLOY requirements satisfied:

| Requirement | Description | Status |
|-------------|-------------|--------|
| DEPLOY-01 | Cloud Run services deployed | PASS |
| DEPLOY-02 | Backend deployed | PASS |
| DEPLOY-03 | Frontend deployed | PASS |
| DEPLOY-04 | GPU service with L4 | PASS |
| DEPLOY-05 | Secrets configured | PASS |
| DEPLOY-06 | Health checks pass | PASS |

User approved services ready for Phase 20.
