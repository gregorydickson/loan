---
phase: 18-documentation-frontend
plan: 01
subsystem: documentation
tags:
  - docs
  - api-guide
  - extraction-methods
  - gpu-cost
  - few-shot
  - deployment-guide

dependency-graph:
  requires:
    - Phase 11 (LangExtract Core)
    - Phase 13 (LightOnOCR GPU)
    - Phase 14 (OCR Routing)
    - Phase 15 (API Integration)
    - Phase 16 (CloudBuild)
  provides:
    - User guide for extraction method selection
    - Few-shot example creation documentation
    - GPU cost management strategies
    - LightOnOCR deployment procedures
  affects:
    - API users
    - Operations teams
    - Future developers

tech-stack:
  added:
    - None (documentation only)
  patterns:
    - Markdown documentation format
    - Decision flowcharts in text
    - Cost estimation tables

key-files:
  created:
    - docs/api/extraction-method-guide.md
    - docs/guides/few-shot-examples.md
    - docs/guides/gpu-service-cost.md
    - docs/guides/lightonocr-deployment.md

decisions:
  - decision: "Organize docs by audience (api/ for users, guides/ for operators)"
    rationale: "Clear separation of concerns, easier navigation"

metrics:
  duration: "4 min"
  completed: "2026-01-25"
---

# Phase 18 Plan 01: User-Facing Documentation Summary

API documentation and operational guides for v2.0 dual extraction pipeline.

## One-Liner

User-facing documentation covering extraction method selection, few-shot example creation, GPU cost management, and LightOnOCR deployment.

## Key Deliverables

### 1. Extraction Method Selection Guide

**File:** `docs/api/extraction-method-guide.md`

- Quick reference table comparing docling, langextract, and auto methods
- Method parameter usage with `?method=docling|langextract|auto`
- OCR mode parameter usage with `?ocr=auto|force|skip`
- Curl examples for all method/ocr combinations
- Response differences section showing character offset fields
- Decision flowchart for parameter selection
- Common use cases and error handling

### 2. Few-Shot Examples Guide

**File:** `docs/guides/few-shot-examples.md`

- Overview of few-shot learning for domain adaptation
- ExampleData and Extraction structure documentation
- **CRITICAL:** extraction_text MUST be exact substring requirement
- Loan entity types: borrower, income, account, loan
- Step-by-step workflow for creating new examples
- Validation command and troubleshooting

### 3. GPU Service Cost Guide

**File:** `docs/guides/gpu-service-cost.md`

- L4 GPU pricing (~$0.50/hour when running)
- Scale-to-zero cost model ($0 when idle)
- Per-document cost estimates (~$0.01-0.02)
- Monthly cost scenarios for different volumes
- Optimization strategies: ocr=skip, batching, monitoring
- Budget alert configuration

### 4. LightOnOCR Deployment Guide

**File:** `docs/guides/lightonocr-deployment.md`

- Prerequisites: GPU quota, service account, Artifact Registry
- CloudBuild deployment steps
- Configuration reference:
  - vCPU: 8
  - Memory: 32Gi
  - GPU: nvidia-l4 (1)
  - Min instances: 0 (scale-to-zero)
  - Startup probe: 240s timeout
- Troubleshooting: cold starts, OOM, model loading, quota

## Requirements Satisfied

| Requirement | Description | How Satisfied |
|-------------|-------------|---------------|
| DOCS-01 | API method selection guidance | Extraction method guide with decision flowchart |
| DOCS-02 | Few-shot example documentation | Complete guide with entity types and workflow |
| DOCS-05 | LightOnOCR deployment guide | Step-by-step deployment with troubleshooting |
| DOCS-08 | API curl examples | 7+ curl examples with method/ocr params |
| DOCS-10 | GPU cost management | Cost guide with scale-to-zero strategies |
| DOCS-11 | Few-shot versioning procedures | Version control and tagging strategies |
| DUAL-10 | Method selection documentation | User guide links API params to extraction pipelines |

## Tasks Completed

| Task | Name | Duration | Commit |
|------|------|----------|--------|
| 1 | Create Extraction Method Selection Guide | 2 min | 7e66b799 |
| 2 | Create Few-Shot Example Guide | 1 min | 5d97468c |
| 3 | Create GPU Service Cost and Deployment Guides | 1 min | e8a458d0 |

## Verification Results

- [x] docs/api/extraction-method-guide.md exists with method/ocr parameter documentation
- [x] docs/guides/few-shot-examples.md exists with verbatim text requirement
- [x] docs/guides/gpu-service-cost.md exists with scale-to-zero cost strategies
- [x] docs/guides/lightonocr-deployment.md exists with L4 GPU deployment steps
- [x] All guides follow markdown format consistent with existing docs/
- [x] 7 curl examples with method and ocr parameters

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

1. **Documentation directory structure:** Created `docs/api/` for API user documentation and `docs/guides/` for operational guides, providing clear separation by audience.

2. **Cross-linking:** All guides include See Also sections linking to related documentation for easy navigation.

## Next Phase Readiness

This is the final plan of Phase 18. Documentation deliverables are complete.

**Phase 18 remaining plans:**
- None - this was the only plan in Phase 18

**Project completion status:**
- v2.0 dual extraction pipeline fully documented
- All user-facing documentation in place
- Operational guides for GPU service management complete
