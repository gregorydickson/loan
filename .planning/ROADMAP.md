# Roadmap: Loan Document Data Extraction System

## Milestones

- [x] **v1.0 MVP** - Phases 1-9 (shipped 2026-01-24)
- [x] **v2.0 LangExtract & CloudBuild** - Phases 10-18 (shipped 2026-01-25)
- [ ] **v2.1 Production Deployment & Verification** - Phases 19-21 (in progress)

## Phases

<details>
<summary>v1.0 MVP (Phases 1-9) - SHIPPED 2026-01-24</summary>

Complete full-stack loan document extraction system with 222 requirements, 92% test coverage, and GCP infrastructure.

</details>

<details>
<summary>v2.0 LangExtract & CloudBuild (Phases 10-18) - SHIPPED 2026-01-25</summary>

Dual extraction pipelines (Docling + LangExtract), LightOnOCR GPU service with scale-to-zero, CloudBuild CI/CD migration. 72 requirements, 86.98% coverage, 490 tests.

</details>

### v2.1 Production Deployment & Verification (In Progress)

**Milestone Goal:** Deploy all services to GCP production and verify functionality through comprehensive Chrome-based testing.

- [ ] **Phase 19: Production Deployment Verification** - Verify and deploy all services to GCP production
- [ ] **Phase 20: Core Extraction Verification** - Verify upload and extraction flows via Chrome
- [ ] **Phase 21: UI Feature Verification** - Verify source attribution and dashboard features

## Phase Details

### Phase 19: Production Deployment Verification
**Goal**: All services running and accessible in GCP production environment
**Depends on**: Phase 18 (v2.0 complete)
**Requirements**: DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04, DEPLOY-05, DEPLOY-06
**Success Criteria** (what must be TRUE):
  1. Cloud Run service list shows backend, frontend, and GPU OCR services in production project
  2. Each service responds to health check endpoint with 200 status
  3. Backend connects successfully to Cloud SQL database
  4. Frontend loads in browser and communicates with backend API
  5. GPU OCR service is configured with L4 GPU and scale-to-zero enabled
**Plans**: 4 plans

Plans:
- [ ] 19-01-PLAN.md - Check deployments and deploy backend
- [ ] 19-02-PLAN.md - Deploy frontend with backend URL
- [ ] 19-03-PLAN.md - Deploy GPU service with L4 GPU
- [ ] 19-04-PLAN.md - Verify secrets and comprehensive health check

### Phase 20: Core Extraction Verification
**Goal**: End-to-end document extraction flows work correctly in production
**Depends on**: Phase 19
**Requirements**: TEST-01, TEST-02, TEST-03, TEST-04, TEST-05
**Success Criteria** (what must be TRUE):
  1. Production frontend URL loads successfully in Chrome browser
  2. User can upload a PDF document and receive confirmation
  3. Docling extraction method processes document and returns structured borrower data
  4. LangExtract extraction method processes document and returns data with character offsets
  5. Scanned document triggers GPU OCR service and extracts text successfully
**Plans**: TBD

Plans:
- [ ] 20-01: TBD

### Phase 21: UI Feature Verification
**Goal**: All frontend features display extraction results correctly
**Depends on**: Phase 20
**Requirements**: TEST-06, TEST-07, TEST-08, TEST-09
**Success Criteria** (what must be TRUE):
  1. Source attribution UI shows page numbers for extracted fields
  2. Character-level offsets display correctly for LangExtract results (highlighting works)
  3. Borrower data appears in dashboard list with correct field values
  4. Extraction visualizations render without errors (charts, timelines, confidence indicators)
**Plans**: TBD

Plans:
- [ ] 21-01: TBD

## Progress

**Execution Order:** 19 -> 20 -> 21

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 19. Production Deployment Verification | v2.1 | 4/4 | ✓ Complete | 2026-01-26 |
| 20. Core Extraction Verification | v2.1 | 0/TBD | Ready | - |
| 21. UI Feature Verification | v2.1 | 0/TBD | Not started | - |

---
*Roadmap created: 2026-01-25*
*Last updated: 2026-01-26 - Phase 19 complete (all services deployed and verified)*
