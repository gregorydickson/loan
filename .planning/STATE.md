# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-25)

**Core value:** Accurate extraction of borrower data with complete traceability - every extracted field must include source attribution showing which document and page it came from.
**Current focus:** v2.1 Production Deployment & Verification - Phase 19

## Current Position

Milestone: v2.1 Production Deployment & Verification
Phase: 19 of 21 (Production Deployment Verification)
Plan: 1 of 3 complete
Status: In progress
Last activity: 2026-01-25 - Completed 19-01-PLAN.md (Backend Deployment)

Progress: [####################] 100% (v1.0 + v2.0) | v2.1: [###.......] 33%

## Performance Metrics

**Velocity:**
- Total plans completed: 65 (v1.0: 36, v2.0: 28, v2.1: 1)
- Average duration: 4.6 min
- Total execution time: 6.77 hours

**By Milestone:**

| Milestone | Phases | Plans | Total Time | Shipped |
|-----------|--------|-------|------------|---------|
| v1.0 MVP | 1-9 | 36 | ~4 hours | 2026-01-24 |
| v2.0 LangExtract | 10-18 | 28 | ~2 hours | 2026-01-25 |
| v2.1 Deployment | 19-21 | 1/3 | 75 min | In Progress |

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

### Pending Todos

- Provide real Gemini API key to gemini-api-key secret
- Configure database for loan application (create loan_extraction database or update connection string)
- Run database migrations after database is configured

### Blockers/Concerns

- **Database not configured**: API endpoints return 500 - database-url points to memorygraph_auth which lacks loan schema
- **Gemini API key placeholder**: Extraction functionality won't work until real key provided

## Session Continuity

Last session: 2026-01-25T23:45:00Z
Stopped at: Completed 19-01-PLAN.md (Backend Deployment)
Resume file: None
Next action: Execute Plan 19-02 (Frontend Deployment)

## Backend URL for Plan 19-02

```
BACKEND_URL=https://loan-backend-prod-793446666872.us-central1.run.app
```
