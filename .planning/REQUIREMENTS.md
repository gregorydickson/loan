# Requirements: Loan Document Data Extraction System

**Defined:** 2026-01-25
**Core Value:** Accurate extraction of borrower data with complete traceability - every extracted field must include source attribution showing which document and page it came from.

## v2.1 Requirements (Production Deployment & Verification)

Requirements for production deployment and Chrome-based verification testing.

### Deployment

- [ ] **DEPLOY-01**: Check for existing Cloud Run deployments in production project
- [ ] **DEPLOY-02**: Deploy backend API to Cloud Run in production (if not already deployed)
- [ ] **DEPLOY-03**: Deploy frontend to Cloud Run in production (if not already deployed)
- [ ] **DEPLOY-04**: Deploy GPU OCR service to Cloud Run in production (if not already deployed)
- [ ] **DEPLOY-05**: Configure production environment variables and secrets
- [ ] **DEPLOY-06**: Verify all services are accessible and return healthy status

### Chrome-Based Verification

- [ ] **TEST-01**: Navigate to production frontend URL using Chrome
- [ ] **TEST-02**: Verify document upload flow completes successfully
- [ ] **TEST-03**: Test Docling extraction method end-to-end (upload → extraction → results)
- [ ] **TEST-04**: Test LangExtract extraction method end-to-end (upload → extraction → results)
- [ ] **TEST-05**: Upload scanned document and verify GPU OCR service processes it
- [ ] **TEST-06**: Validate source attribution UI displays page references correctly
- [ ] **TEST-07**: Validate character-level offsets display for LangExtract results
- [ ] **TEST-08**: Verify extracted borrower data appears in dashboard
- [ ] **TEST-09**: Verify extraction visualizations render correctly

## v1.0 Requirements (Shipped 2026-01-24)

- [x] Foundation & Data Models (17 requirements) - v1.0
- [x] Document Ingestion Pipeline (28 requirements) - v1.0
- [x] LLM Extraction & Validation (38 requirements) - v1.0
- [x] Data Storage & REST API (32 requirements) - v1.0
- [x] Frontend Dashboard (37 requirements) - v1.0
- [x] GCP Infrastructure (27 requirements) - v1.0
- [x] Documentation & Testing (48 requirements) - v1.0
- [x] Pipeline Integration (44 requirements) - v1.0
- [x] Async Background Processing (2 requirements) - v1.0

**Total v1.0:** 222/222 requirements (100%)

## v2.0 Requirements (Shipped 2026-01-25)

- [x] LangExtract Integration (12 requirements) - v2.0
- [x] LightOnOCR GPU Service (12 requirements) - v2.0
- [x] Dual Pipeline Integration (12 requirements) - v2.0
- [x] CloudBuild Deployment (12 requirements) - v2.0
- [x] Testing & Quality (12 requirements) - v2.0
- [x] Documentation (12 requirements) - v2.0

**Total v2.0:** 72/72 requirements (100%)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Custom domain & SSL | Production URLs use Cloud Run default domains (*.run.app) for this milestone |
| Monitoring & alerting | Cloud Logging provides basic observability; advanced monitoring deferred |
| Cost tracking dashboards | Basic GCP billing alerts sufficient for portfolio project |
| Load testing | Portfolio project scale doesn't require performance testing |
| Multi-region deployment | Single region deployment adequate for demo/portfolio |
| Automated rollback | Manual rollback via CloudBuild sufficient for v2.1 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DEPLOY-01 | Phase 19 | Pending |
| DEPLOY-02 | Phase 19 | Pending |
| DEPLOY-03 | Phase 19 | Pending |
| DEPLOY-04 | Phase 19 | Pending |
| DEPLOY-05 | Phase 19 | Pending |
| DEPLOY-06 | Phase 19 | Pending |
| TEST-01 | Phase 20 | Pending |
| TEST-02 | Phase 20 | Pending |
| TEST-03 | Phase 20 | Pending |
| TEST-04 | Phase 20 | Pending |
| TEST-05 | Phase 20 | Pending |
| TEST-06 | Phase 21 | Pending |
| TEST-07 | Phase 21 | Pending |
| TEST-08 | Phase 21 | Pending |
| TEST-09 | Phase 21 | Pending |

**Coverage:**
- v2.1 requirements: 15 total
- Mapped to phases: 15 (100%)
- Unmapped: 0

---
*Requirements defined: 2026-01-25*
*Last updated: 2026-01-25 - Traceability updated with phase mappings*
