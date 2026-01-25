# Roadmap: Loan Document Data Extraction System

## Milestones

- **v1.0 MVP** - Phases 1-9 (shipped 2026-01-24)
- **v2.0 LangExtract & CloudBuild** - Phases 10-18 (in progress)

## Phases

<details>
<summary>v1.0 MVP (Phases 1-9) - SHIPPED 2026-01-24</summary>

See: `.planning/milestones/v1.0-ROADMAP.md`

**Summary:**
- Phase 1: Foundation & Data Models (3 plans)
- Phase 2: Document Ingestion Pipeline (4 plans)
- Phase 3: LLM Extraction & Validation (5 plans)
- Phase 4: Data Storage & REST API (3 plans)
- Phase 5: Frontend Dashboard (5 plans)
- Phase 6: GCP Infrastructure (4 plans)
- Phase 7: Documentation & Testing (5 plans)
- Phase 8: Wire Document-to-Extraction Pipeline (3 plans)
- Phase 9: Cloud Tasks Background Processing (4 plans)

**Total:** 36 plans, 222 requirements, 9,357 LOC

</details>

## v2.0 LangExtract & CloudBuild (In Progress)

**Milestone Goal:** Add LangExtract-based extraction pipeline with character-level source grounding, optional LightOnOCR GPU service for scanned documents, and migrate from Terraform to CloudBuild + CLI deployment.

**Phase Numbering:** 10-18 (continuing from v1.0)

- [x] **Phase 10: v2.0 Setup & Preparation** - GPU quota, Terraform archival, CloudBuild foundation
- [x] **Phase 11: LangExtract Core Integration** - Character offset storage, Gemini integration, few-shot examples
- [x] **Phase 12: LangExtract Advanced Features** - Multi-pass extraction, HTML visualization, parallel processing
- [ ] **Phase 13: LightOnOCR GPU Service** - Cloud Run GPU deployment, vLLM serving, client integration
- [x] **Phase 14: OCR Routing & Fallback** - Scanned document detection, Docling OCR fallback
- [x] **Phase 15: Dual Pipeline Integration** - Method selection API, output normalization, Cloud Tasks enhancement
- [ ] **Phase 16: CloudBuild Deployment** - CloudBuild configs, GitHub triggers, rollback procedures
- [ ] **Phase 17: Testing & Quality** - Comprehensive tests for all new features, >80% coverage
- [ ] **Phase 18: Documentation & Frontend** - Guides, ADRs, frontend method selection UI

## Phase Details

### Phase 10: v2.0 Setup & Preparation

**Goal**: Prepare infrastructure and prerequisites for v2.0 development (GPU quota, Terraform archival, CloudBuild foundation)
**Depends on**: v1.0 complete
**Requirements**: LOCR-09, CBLD-04, CBLD-08, CBLD-12
**Success Criteria** (what must be TRUE):
  1. GPU quota request submitted and approved for L4 GPUs in target region
  2. Terraform state archived to /archive/terraform/ with migration documentation
  3. CloudBuild service account created with necessary permissions
  4. vLLM validated to load LightOnOCR model locally
**Plans**: 5 plans (4 original + 1 gap closure)

Plans:
- [x] 10-01-PLAN.md - GPU quota check and request
- [x] 10-02-PLAN.md - Terraform state archival
- [x] 10-03-PLAN.md - CloudBuild service account setup (script created)
- [x] 10-04-PLAN.md - vLLM validation scripts and testing
- [x] 10-05-PLAN.md - Gap closure: Execute CloudBuild service account script (CBLD-08)

### Phase 11: LangExtract Core Integration

**Goal**: Integrate LangExtract with Gemini 3.0 Flash for character-level source-grounded extraction
**Depends on**: Phase 10
**Requirements**: LXTR-01, LXTR-02, LXTR-03, LXTR-04, LXTR-05, LXTR-08, LXTR-09, LXTR-12
**Success Criteria** (what must be TRUE):
  1. SourceReference model stores char_start/char_end with nullable fields for backward compatibility
  2. LangExtractProcessor extracts borrower data using Gemini 3.0 Flash
  3. Few-shot examples defined in examples/ directory for loan document entities
  4. Character offsets verified via substring matching at reported positions
  5. Offset translation layer handles Docling text vs raw text alignment
**Plans**: 4 plans

Plans:
- [x] 11-01-PLAN.md - Schema updates (char_start/char_end in SourceReference)
- [x] 11-02-PLAN.md - Few-shot examples for LangExtract
- [x] 11-03-PLAN.md - LangExtractProcessor and OffsetTranslator
- [x] 11-04-PLAN.md - Verification tests for character offsets

### Phase 12: LangExtract Advanced Features

**Goal**: Complete LangExtract capabilities with multi-pass extraction, visualization, and parallel processing
**Depends on**: Phase 11
**Requirements**: LXTR-06, LXTR-07, LXTR-10, LXTR-11
**Success Criteria** (what must be TRUE):
  1. Multi-pass extraction configurable (2-5 passes) for thoroughness
  2. LangExtract generates HTML visualization with highlighted source spans
  3. Parallel chunk processing improves throughput for long documents
  4. LangExtract errors fall back to Docling extraction gracefully
**Plans**: 3 plans

Plans:
- [x] 12-01-PLAN.md - ExtractionConfig and LangExtractProcessor enhancement (LXTR-06, LXTR-10)
- [x] 12-02-PLAN.md - LangExtractVisualizer for HTML visualization (LXTR-07)
- [x] 12-03-PLAN.md - ExtractionRouter with fallback to Docling (LXTR-11)

### Phase 13: LightOnOCR GPU Service

**Goal**: Deploy dedicated Cloud Run GPU service with LightOnOCR model for high-quality scanned document OCR
**Depends on**: Phase 10 (GPU quota)
**Requirements**: LOCR-01, LOCR-02, LOCR-03, LOCR-04, LOCR-06, LOCR-07, LOCR-08, LOCR-10, LOCR-12
**Success Criteria** (what must be TRUE):
  1. LightOnOCR Cloud Run service deployed with L4 GPU (24GB VRAM)
  2. vLLM serving infrastructure configured for LightOnOCR-2-1B model
  3. GPU service scales to zero (min_instances=0) to minimize baseline costs
  4. Backend LightOnOCRClient communicates with GPU service via HTTP
  5. Cold start monitoring and OCR quality metrics tracked
**Plans**: 3 plans

Plans:
- [x] 13-01-PLAN.md - Docker image and deployment scripts (Dockerfile, deploy.sh, service account)
- [x] 13-02-PLAN.md - Deploy GPU service to Cloud Run (execution + verification)
- [x] 13-03-PLAN.md - LightOnOCRClient backend implementation with unit tests
- [ ] 13-04-PLAN.md - API Integration (pending)

### Phase 14: OCR Routing & Fallback

**Goal**: Implement intelligent OCR routing with scanned document detection and Docling fallback
**Depends on**: Phase 13
**Requirements**: LOCR-05, LOCR-11
**Success Criteria** (what must be TRUE):
  1. Scanned documents detected automatically and routed to GPU OCR
  2. Native PDFs skip GPU OCR (use direct text extraction)
  3. Docling OCR used as fallback when GPU service unavailable
**Plans**: 2 plans

Plans:
- [x] 14-01-PLAN.md - ScannedDocumentDetector with pypdfium2 text ratio detection
- [x] 14-02-PLAN.md - OCRRouter with circuit breaker and Docling fallback

### Phase 15: Dual Pipeline Integration

**Goal**: Enable API-based extraction method selection with consistent output across pipelines
**Depends on**: Phase 12, Phase 14
**Requirements**: DUAL-01, DUAL-02, DUAL-03, DUAL-04, DUAL-05, DUAL-06, DUAL-07, DUAL-08, DUAL-09, DUAL-11
**Success Criteria** (what must be TRUE):
  1. Extraction method selectable via ?method=docling|langextract query parameter
  2. OCR mode selectable via ?ocr=auto|force|skip query parameter
  3. ExtractionRouter dispatches to correct extraction method
  4. Document model tracks extraction_method and ocr_processed metadata
  5. Both extraction methods produce normalized BorrowerRecord with SourceReference
  6. Existing v1.0 Docling extraction continues to work unchanged (regression safe)
**Plans**: 2 plans

Plans:
- [x] 15-01-PLAN.md - Database schema + API query parameters
- [x] 15-02-PLAN.md - Cloud Tasks enhancement + service wiring

### Phase 16: CloudBuild Deployment

**Goal**: Migrate from Terraform to CloudBuild + gcloud CLI for all service deployments
**Depends on**: Phase 13 (GPU service to deploy), Phase 15 (services complete)
**Requirements**: CBLD-01, CBLD-02, CBLD-03, CBLD-05, CBLD-06, CBLD-07, CBLD-09, CBLD-10, CBLD-11
**Success Criteria** (what must be TRUE):
  1. cloudbuild.yaml configs created for backend, frontend, and GPU services
  2. GitHub trigger configured for automatic builds on push to main
  3. Secret Manager integration configured for CloudBuild
  4. Multi-service deployment orchestration works correctly
  5. Rollback procedures documented and tested
**Plans**: 3 plans

Plans:
- [ ] 16-01-PLAN.md - CloudBuild configuration files (backend, frontend, GPU)
- [ ] 16-02-PLAN.md - Infrastructure scripts (provision-infra.sh, rollback.sh, Terraform inventory)
- [ ] 16-03-PLAN.md - GitHub triggers and deployment guide

### Phase 17: Testing & Quality

**Goal**: Achieve comprehensive test coverage for all v2.0 features with type safety
**Depends on**: Phase 15, Phase 16
**Requirements**: TEST-01, TEST-02, TEST-03, TEST-04, TEST-05, TEST-06, TEST-07, TEST-08, TEST-09, TEST-10, TEST-11, TEST-12
**Success Criteria** (what must be TRUE):
  1. LangExtract processor unit tests pass with few-shot example validation
  2. Character offset verification tests confirm substring matching works
  3. E2E tests pass for both Docling and LangExtract extraction paths
  4. Dual pipeline method selection tests verify correct routing
  5. Test coverage maintained >80% for new code, mypy strict passes
**Plans**: TBD

### Phase 18: Documentation & Frontend

**Goal**: Complete v2.0 documentation and frontend extraction method selection UI
**Depends on**: Phase 17
**Requirements**: DOCS-01, DOCS-02, DOCS-03, DOCS-04, DOCS-05, DOCS-06, DOCS-07, DOCS-08, DOCS-09, DOCS-10, DOCS-11, DOCS-12, DUAL-10, DUAL-12
**Success Criteria** (what must be TRUE):
  1. Extraction method selection guide available for API users
  2. Few-shot example creation guide documents loan document patterns
  3. CloudBuild deployment guide provides step-by-step instructions
  4. ADRs created for LangExtract, LightOnOCR, CloudBuild decisions
  5. Frontend supports extraction method and OCR mode selection in upload UI
**Plans**: TBD

## Progress

**Execution Order:** Phases execute in numeric order: 10 -> 11 -> 12 -> 13 -> 14 -> 15 -> 16 -> 17 -> 18

Note: Phases 11-12 (LangExtract) and Phase 13 (LightOnOCR) can be developed in parallel after Phase 10 completes.

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 10. v2.0 Setup & Preparation | v2.0 | 5/5 | Complete | 2026-01-25 |
| 11. LangExtract Core Integration | v2.0 | 4/4 | Complete | 2026-01-25 |
| 12. LangExtract Advanced Features | v2.0 | 3/3 | Complete | 2026-01-25 |
| 13. LightOnOCR GPU Service | v2.0 | 3/4 | In Progress | - |
| 14. OCR Routing & Fallback | v2.0 | 2/2 | Complete | 2026-01-25 |
| 15. Dual Pipeline Integration | v2.0 | 2/2 | Complete | 2026-01-25 |
| 16. CloudBuild Deployment | v2.0 | 0/3 | Not started | - |
| 17. Testing & Quality | v2.0 | 0/TBD | Not started | - |
| 18. Documentation & Frontend | v2.0 | 0/TBD | Not started | - |

---
*Roadmap created: 2026-01-24*
*Last updated: 2026-01-25*
