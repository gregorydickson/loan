# GPU Quota Status

**Checked:** 2026-01-24
**Project:** memorygraph-prod
**Region:** us-central1

## Current L4 GPU Quota

| Metric | Limit | Usage |
|--------|-------|-------|
| NVIDIA_L4_GPUS | 1 | 0 |
| PREEMPTIBLE_NVIDIA_L4_GPUS | 1 | 0 |
| COMMITTED_NVIDIA_L4_GPUS | 1 | 0 |

## Cloud Run GPU Support

us-central1 region supports the following GPU accelerators:
- nvidia-l4 (NVIDIA L4)
- nvidia-a100-80gb (NVIDIA A100 80GB)
- nvidia-rtx-pro-6000 (NVIDIA RTX Pro 6000)

**Status:** GPU support is enabled for Cloud Run in this region.

## Quota Assessment

**Current Quota:** 1 L4 GPU
**Required for Phase 13:** 1 L4 GPU (minimum for LightOnOCR service)
**Status:** Sufficient - no request needed

The current quota of 1 L4 GPU in us-central1 is sufficient for deploying the LightOnOCR Cloud Run GPU service in Phase 13.

## Notes

- LightOnOCR-2-1B model requires approximately 4-8GB VRAM for inference
- L4 GPU provides 24GB VRAM, well above requirements
- Cloud Run GPU supports scale-to-zero (min_instances=0) to minimize costs
- No quota increase request is required at this time

## Future Considerations

If multiple concurrent GPU instances are needed for horizontal scaling, a quota increase request would be required:

1. Go to: https://console.cloud.google.com/iam-admin/quotas
2. Filter: "NvidiaL4GpuAllocNoZonalRedundancyPerProjectRegion"
3. Select region: us-central1
4. Request additional GPUs as needed
5. Justification: "LightOnOCR GPU service for document OCR processing"

---
*Required for: Phase 13 LightOnOCR GPU Service*
*GPU Type: NVIDIA L4 (24GB VRAM)*
