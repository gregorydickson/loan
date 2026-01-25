---
phase: 13-lightonocr-gpu-service
plan: 02
subsystem: infra
tags: [cloud-run, gpu, vllm, lightonocr, l4, deployment, gcp]

# Dependency graph
requires:
  - phase: 13-01
    provides: Dockerfile, deploy.sh, service account setup scripts
provides:
  - Running LightOnOCR GPU service on Cloud Run
  - Service URL for client configuration
  - Health endpoint verification
affects: [13-03, 13-04, 14-api-integration]

# Tech tracking
tech-stack:
  added: []
  patterns: [cloud-build-deployment, gpu-memory-optimization, cold-start-handling]

key-files:
  created: []
  modified:
    - infrastructure/lightonocr-gpu/cloudbuild.yaml (created during deployment)

key-decisions:
  - "Cloud Build used instead of local docker build (local disk space constraints)"
  - "Transformers pinned to 4.57.1 for vLLM compatibility"
  - "GPU memory utilization reduced to 80% and max_seqs=8 to prevent OOM"

patterns-established:
  - "Cloud Build for GPU images: cloudbuild.yaml with 32GB memory machine"
  - "vLLM memory settings: --gpu-memory-utilization 0.8 --max-num-seqs 8 for L4"

# Metrics
duration: 45min
completed: 2026-01-25
---

# Phase 13 Plan 02: Cloud Run GPU Deployment Summary

**LightOnOCR GPU service deployed to Cloud Run with L4 GPU, vLLM serving LightOnOCR-2-1B model, scale-to-zero configuration, and IAM authentication**

## Performance

- **Duration:** ~45 min (includes build/push/deploy time with checkpoint)
- **Started:** 2026-01-25T13:00:00Z
- **Completed:** 2026-01-25T13:45:00Z
- **Tasks:** 2 (1 auto + 1 checkpoint)
- **Files modified:** 1 (cloudbuild.yaml created for build)

## Accomplishments

- Deployed LightOnOCR GPU service to Cloud Run with L4 GPU
- Service running at: https://lightonocr-gpu-fjz2snvxjq-uc.a.run.app
- Health endpoint verified and responding
- Scale-to-zero enabled (min_instances=0) for cost management
- Service requires authentication (IAM-protected)

## Service Details

**Service URL:** `https://lightonocr-gpu-fjz2snvxjq-uc.a.run.app`

**Configuration:**
- CPU: 8 vCPU
- Memory: 32 GiB
- GPU: 1 x nvidia-l4
- Min instances: 0 (scale-to-zero)
- Max instances: 3
- Authentication: Required (IAM)

## Task Commits

Each task was committed atomically:

1. **Task 1: Execute GPU service deployment** - `e8b7982b` (feat)
2. **Task 2: Verification checkpoint** - User approved service deployment

## Files Created/Modified

- `infrastructure/lightonocr-gpu/cloudbuild.yaml` - Cloud Build configuration for GPU image

## Decisions Made

1. **Cloud Build instead of local build** - Local disk space insufficient for large image build; Cloud Build provides 32GB+ disk and faster push to Artifact Registry
2. **Transformers pinned to 4.57.1** - Required for vLLM compatibility; latest version caused import errors
3. **GPU memory reduced to 80%** - Prevents OOM during inference; default 90% caused crashes
4. **max_seqs reduced to 8** - Limits concurrent requests to prevent memory exhaustion on L4 GPU

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Cloud Build used for image build**
- **Found during:** Task 1 (Docker build)
- **Issue:** Local machine lacked sufficient disk space for ~10GB Docker image build
- **Fix:** Created cloudbuild.yaml and used `gcloud builds submit` instead of local docker build
- **Files modified:** infrastructure/lightonocr-gpu/cloudbuild.yaml
- **Committed in:** e8b7982b

**2. [Rule 1 - Bug] Transformers version pinned to 4.57.1**
- **Found during:** Task 1 (vLLM startup)
- **Issue:** Latest transformers broke vLLM model loading with import errors
- **Fix:** Pinned transformers==4.57.1 in Dockerfile
- **Files modified:** infrastructure/lightonocr-gpu/Dockerfile
- **Committed in:** e8b7982b

**3. [Rule 1 - Bug] GPU memory settings adjusted for L4**
- **Found during:** Task 1 (Model inference)
- **Issue:** Default vLLM settings caused OOM on L4 GPU
- **Fix:** Added --gpu-memory-utilization 0.8 --max-num-seqs 8 to vLLM arguments
- **Files modified:** infrastructure/lightonocr-gpu/deploy.sh
- **Committed in:** e8b7982b

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 blocking)
**Impact on plan:** All auto-fixes necessary for successful deployment. No scope creep.

## Issues Encountered

- Docker image build required Cloud Build due to local disk constraints (~10GB image size)
- vLLM/transformers version compatibility required pinning
- L4 GPU memory constraints required tuning vLLM parameters

All issues resolved during execution.

## Authentication Gates

During execution, these authentication requirements were handled:

1. GCP Cloud Build: Used existing gcloud authentication
2. Cloud Run deployment: Used existing gcloud authentication
3. Health check: Used `gcloud auth print-identity-token` for service authentication

## User Setup Required

None - service is deployed and running. Client configuration uses service URL.

## Next Phase Readiness

- GPU service deployed and healthy
- Service URL available for 13-03 (LightOnOCR Client): `https://lightonocr-gpu-fjz2snvxjq-uc.a.run.app`
- 13-04 (API Integration) can proceed with backend configuration
- Backend needs LIGHTONOCR_SERVICE_URL environment variable set to service URL

**Requirements Satisfied:**
- LOCR-01: Cloud Run GPU service deployed with L4 GPU
- LOCR-02: vLLM serving LightOnOCR-2-1B model
- LOCR-04: Service scales to zero (min_instances=0)
- LOCR-07: Service requires authentication

---
*Phase: 13-lightonocr-gpu-service*
*Completed: 2026-01-25*
