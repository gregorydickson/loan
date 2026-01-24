# Requirements: Loan Document Data Extraction System

**Defined:** 2026-01-24
**Core Value:** Accurate extraction of borrower data with complete traceability - every extracted field must include source attribution showing which document and page it came from.

## v2.0 Requirements

Requirements for v2.0 milestone: LangExtract extraction pipeline, LightOnOCR GPU service, and CloudBuild deployment.

### LangExtract Integration

- [ ] **LXTR-01**: System stores character-level offsets (char_start, char_end) in SourceReference model
- [ ] **LXTR-02**: SourceReference schema supports nullable character offsets for backward compatibility
- [ ] **LXTR-03**: LangExtractProcessor integrates with Gemini 3.0 Flash for extraction
- [ ] **LXTR-04**: Few-shot examples defined for loan document entities (borrower, income, accounts)
- [ ] **LXTR-05**: Few-shot examples use verbatim text from sample documents
- [ ] **LXTR-06**: Multi-pass extraction configurable (2-5 passes) for thoroughness
- [ ] **LXTR-07**: LangExtract generates HTML visualization with highlighted source spans
- [ ] **LXTR-08**: Character offsets verified via substring matching at reported positions
- [ ] **LXTR-09**: Offset translation layer handles Docling markdown vs raw text alignment
- [ ] **LXTR-10**: Parallel chunk processing implemented for long documents
- [ ] **LXTR-11**: LangExtract extraction errors logged with fallback to Docling
- [ ] **LXTR-12**: Few-shot examples stored in examples/ directory with versioning

### LightOnOCR GPU Service

- [ ] **LOCR-01**: LightOnOCR Cloud Run service deployed with L4 GPU (24GB VRAM)
- [ ] **LOCR-02**: vLLM serving infrastructure configured for LightOnOCR-2-1B model
- [ ] **LOCR-03**: GPU service has minimum 4 vCPU, 16 GiB memory configuration
- [ ] **LOCR-04**: GPU service scales to zero (min_instances=0) to avoid $485/month baseline
- [ ] **LOCR-05**: Scanned document detection implemented (auto OCR routing)
- [ ] **LOCR-06**: LightOnOCRClient in backend communicates with GPU service via HTTP
- [ ] **LOCR-07**: GPU service requires internal-only authentication (service account or VPC)
- [ ] **LOCR-08**: Cold start monitoring and alerting configured
- [ ] **LOCR-09**: GPU quota increased for L4 GPUs (request submitted pre-development)
- [ ] **LOCR-10**: vLLM batching configured for cost-efficient throughput
- [ ] **LOCR-11**: Fallback to Docling OCR when GPU service unavailable
- [ ] **LOCR-12**: OCR quality metrics tracked (accuracy, processing time, cost)

### Dual Pipeline Integration

- [ ] **DUAL-01**: Extraction method selection via ?method=docling|langextract query parameter
- [ ] **DUAL-02**: OCR mode selection via ?ocr=auto|force|skip query parameter
- [ ] **DUAL-03**: ExtractionRouter dispatches to correct extraction method based on parameters
- [ ] **DUAL-04**: OCRRouter determines OCR need based on mode and document type
- [ ] **DUAL-05**: Document model tracks extraction_method metadata
- [ ] **DUAL-06**: Document model tracks ocr_processed boolean flag
- [ ] **DUAL-07**: Both extraction methods produce BorrowerRecord with SourceReference
- [ ] **DUAL-08**: LangExtract path populates character offsets, Docling path leaves null
- [ ] **DUAL-09**: Existing v1.0 Docling extraction continues to work unchanged
- [ ] **DUAL-10**: API documentation includes method and OCR selection examples
- [ ] **DUAL-11**: Cloud Tasks payload enhanced with method and OCR parameters
- [ ] **DUAL-12**: Frontend supports extraction method selection in upload UI

### CloudBuild Deployment

- [ ] **CBLD-01**: cloudbuild.yaml created for backend service deployment
- [ ] **CBLD-02**: cloudbuild.yaml created for frontend service deployment
- [ ] **CBLD-03**: cloudbuild.yaml created for LightOnOCR GPU service deployment
- [ ] **CBLD-04**: Terraform state archived with documentation before migration
- [ ] **CBLD-05**: Terraform-managed resources inventoried and mapped to gcloud equivalents
- [ ] **CBLD-06**: One-time gcloud CLI scripts created for infrastructure provisioning (Cloud SQL, VPC)
- [ ] **CBLD-07**: GitHub trigger configured for automatic builds on push to main
- [ ] **CBLD-08**: CloudBuild service account configured with necessary permissions
- [ ] **CBLD-09**: Secret Manager integration configured for CloudBuild
- [ ] **CBLD-10**: Multi-service deployment orchestration implemented
- [ ] **CBLD-11**: Rollback procedures documented for CloudBuild deployments
- [ ] **CBLD-12**: Terraform directory archived to /archive/terraform/ with migration date

### Testing & Quality

- [ ] **TEST-01**: LangExtract processor unit tests with few-shot example validation
- [ ] **TEST-02**: Character offset verification tests (substring matching)
- [ ] **TEST-03**: LightOnOCR GPU service integration tests
- [ ] **TEST-04**: Scanned document detection accuracy tests
- [ ] **TEST-05**: E2E tests for Docling extraction path (regression)
- [ ] **TEST-06**: E2E tests for LangExtract extraction path
- [ ] **TEST-07**: Dual pipeline method selection tests
- [ ] **TEST-08**: OCR routing logic tests (auto/force/skip)
- [ ] **TEST-09**: Character offset alignment validation tests
- [ ] **TEST-10**: GPU service cold start performance tests
- [ ] **TEST-11**: Test coverage maintained >80% for new code
- [ ] **TEST-12**: mypy strict mode compliance for all new code

### Documentation & Migration

- [ ] **DOCS-01**: Extraction method selection guide for API users
- [ ] **DOCS-02**: Few-shot example creation guide with loan document patterns
- [ ] **DOCS-03**: CloudBuild deployment guide with step-by-step instructions
- [ ] **DOCS-04**: Terraform migration guide with state archival procedures
- [ ] **DOCS-05**: LightOnOCR GPU service deployment guide
- [ ] **DOCS-06**: Architecture documentation updated with dual pipeline diagrams
- [ ] **DOCS-07**: ADRs created for LangExtract, LightOnOCR, CloudBuild decisions
- [ ] **DOCS-08**: API documentation updated with method and OCR parameters
- [ ] **DOCS-09**: Character offset storage schema documented
- [ ] **DOCS-10**: GPU service cost management guide
- [ ] **DOCS-11**: Few-shot example versioning and update procedures
- [ ] **DOCS-12**: v2.0 system design updates committed

## v1.0 Requirements (Validated)

- ✓ Foundation & Data Models (17 requirements) — v1.0
- ✓ Document Ingestion Pipeline (28 requirements) — v1.0
- ✓ LLM Extraction & Validation (38 requirements) — v1.0
- ✓ Data Storage & REST API (32 requirements) — v1.0
- ✓ Frontend Dashboard (37 requirements) — v1.0
- ✓ GCP Infrastructure (27 requirements) — v1.0
- ✓ Documentation & Testing (48 requirements) — v1.0
- ✓ Pipeline Integration (44 requirements) — v1.0
- ✓ Async Background Processing (2 requirements) — v1.0

**Total v1.0:** 222/222 requirements (100%)

## Future Requirements (v2.1+)

### Advanced LangExtract Features

- **LXTR-F01**: Bounding box extraction using LightOnOCR-bbox variant
- **LXTR-F02**: Real-time character-level updates via WebSocket
- **LXTR-F03**: Extraction method comparison UI (side-by-side Docling vs LangExtract)
- **LXTR-F04**: Few-shot example auto-generation from validated extractions

### Advanced OCR Features

- **LOCR-F01**: Custom LightOnOCR fine-tuning for loan document domain
- **LOCR-F02**: Batch OCR processing for multiple documents
- **LOCR-F03**: OCR quality prediction before GPU service call

### Infrastructure

- **CBLD-F01**: Multi-region deployment with CloudBuild
- **CBLD-F02**: Canary deployment strategy with traffic splitting
- **CBLD-F03**: Auto-rollback on health check failure

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time character-level updates | WebSocket complexity; LLM extraction is inherently batch-oriented |
| Always-use LangExtract mode | Docling is faster/cheaper for simple docs; dual paths provide flexibility |
| Always-use LightOnOCR mode | Native PDFs don't need OCR; GPU cold start adds latency and cost |
| Universal extraction schema | Different loan doc types have different structures; use document-type-specific few-shot examples |
| Bounding box extraction | Requires LightOnOCR-bbox variant and more memory; defer to v2.1+ |
| Custom model fine-tuning | LightOnOCR fine-tuning "coming soon"; few-shot examples are the customization mechanism |
| Multi-region deployment | Single-region sufficient for portfolio project |
| Terraform maintenance | Complete migration to CloudBuild; no hybrid Terraform/CloudBuild state |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

**Coverage:**
- v2.0 requirements: 60 total
- Mapped to phases: TBD
- Unmapped: TBD

---
*Requirements defined: 2026-01-24*
*Last updated: 2026-01-24 after initial definition*
