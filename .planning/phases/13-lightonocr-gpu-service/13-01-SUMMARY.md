---
phase: 13-lightonocr-gpu-service
plan: 01
subsystem: infra
tags: [vllm, lightonocr, cloud-run, gpu, docker, l4, ocr]

# Dependency graph
requires:
  - phase: 10-v2.0-setup
    provides: CloudBuild foundation, GPU quota check
provides:
  - LightOnOCR Dockerfile with vLLM base and model baked in
  - Cloud Run GPU deployment script with L4 configuration
  - Service account setup script for GPU service
affects: [14-api-integration, 15-testing, 16-deployment]

# Tech tracking
tech-stack:
  added: [vllm/vllm-openai:v0.11.2, lightonai/LightOnOCR-2-1B]
  patterns: [model-baked-in-image, scale-to-zero-gpu, service-to-service-iam]

key-files:
  created:
    - infrastructure/lightonocr-gpu/Dockerfile
    - infrastructure/lightonocr-gpu/deploy.sh
    - infrastructure/lightonocr-gpu/.dockerignore
    - infrastructure/scripts/setup-lightonocr-sa.sh
  modified: []

key-decisions:
  - "vLLM v0.11.2 base image with transformers from source for LightOnOCR-2-1B"
  - "Model downloaded at build time for faster cold starts (baked into image)"
  - "8 vCPU, 32Gi memory, L4 GPU for optimal LightOnOCR performance"
  - "Scale-to-zero (min_instances=0) for cost management"
  - "240-second startup probe to handle model loading time"

patterns-established:
  - "GPU service deployment: separate service account + backend IAM binding"
  - "Artifact Registry image naming: {region}-docker.pkg.dev/{project}/{repo}/{service}:latest"

# Metrics
duration: 3min
completed: 2026-01-25
---

# Phase 13 Plan 01: LightOnOCR GPU Infrastructure Summary

**vLLM-based Docker image with baked-in LightOnOCR-2-1B model, Cloud Run GPU deployment script with L4 configuration, and service account setup**

## Performance

- **Duration:** 3 min
- **Started:** 2026-01-25T12:56:47Z
- **Completed:** 2026-01-25T12:59:31Z
- **Tasks:** 2
- **Files created:** 4

## Accomplishments

- Created Dockerfile with vLLM v0.11.2 base image and LightOnOCR-2-1B model baked in
- Deploy script with full Cloud Run GPU configuration (L4, 8 vCPU, 32Gi, scale-to-zero)
- Service account setup with backend IAM binding for service-to-service authentication

## Task Commits

Each task was committed atomically:

1. **Task 1: Create LightOnOCR Dockerfile** - `ff5ac3b0` (feat)
2. **Task 2: Create deployment script and service account setup** - `d834b86e` (feat)

## Files Created/Modified

- `infrastructure/lightonocr-gpu/Dockerfile` - vLLM-based container with LightOnOCR-2-1B model
- `infrastructure/lightonocr-gpu/deploy.sh` - Cloud Run GPU deployment with L4 configuration
- `infrastructure/lightonocr-gpu/.dockerignore` - Exclude unnecessary files from build context
- `infrastructure/scripts/setup-lightonocr-sa.sh` - Service account creation for GPU service

## Decisions Made

1. **vLLM v0.11.2 base image** - Official vLLM image with CUDA support, matches RESEARCH.md recommendation
2. **Transformers from source** - Required for LightOnOCR-2-1B per model card
3. **Model baked into image** - Downloaded at build time for faster cold starts (avoiding runtime download)
4. **8 vCPU / 32Gi memory** - Recommended configuration per RESEARCH.md for 1B parameter model
5. **240-second startup probe** - Extended timeout to handle model loading after cold start
6. **Artifact Registry repo** - Uses cloud-run-source-deploy (default repo) for consistency

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all tasks completed successfully.

## User Setup Required

None - no external service configuration required. Scripts are ready to run when deployment is needed.

## Next Phase Readiness

- Infrastructure artifacts complete, ready for Phase 14 (API Integration)
- Deployment requires: Docker running, gcloud authenticated, GPU quota available
- Backend integration will need LIGHTONOCR_SERVICE_URL environment variable

---
*Phase: 13-lightonocr-gpu-service*
*Completed: 2026-01-25*
