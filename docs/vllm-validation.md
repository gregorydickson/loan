# vLLM LightOnOCR Validation Guide

## Purpose

Validate that vLLM can serve the LightOnOCR-2-1B model locally before cloud deployment.

## Requirements

- NVIDIA GPU with 8GB+ VRAM (L4 in cloud has 24GB)
- CUDA drivers installed
- Python 3.12+

## Installation

```bash
# Create virtual environment
uv venv --python 3.12 --seed
source .venv/bin/activate

# Install vLLM (version 0.11.2+ required for LightOnOCR support)
uv pip install vllm==0.11.2
```

## Serving the Model

Start vLLM server with LightOnOCR:

```bash
vllm serve lightonai/LightOnOCR-2-1B \
    --limit-mm-per-prompt '{"image": 1}' \
    --mm-processor-cache-gb 0 \
    --no-enable-prefix-caching \
    --port 8000
```

**Flags explained:**
- `--limit-mm-per-prompt '{"image": 1}'`: One image per request (OCR use case)
- `--mm-processor-cache-gb 0`: Disable multimodal cache (saves memory)
- `--no-enable-prefix-caching`: Disable prefix caching (not useful for OCR)

## Testing

Run validation script:

```bash
./scripts/validate-vllm.sh
```

Or test manually:

```bash
# Test with a simple image (base64 encoded)
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "lightonai/LightOnOCR-2-1B",
    "messages": [{"role": "user", "content": [
      {"type": "text", "text": "Extract all text from this image"},
      {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
    ]}],
    "max_tokens": 2000
  }'
```

## Expected Output

Successful validation shows:
1. Model loads without CUDA OOM errors
2. Server responds on port 8000
3. API returns extracted text from test image

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| CUDA out of memory | Insufficient GPU VRAM | Use GPU with 8GB+ VRAM |
| Model not supported | vLLM version too old | Upgrade to vLLM 0.11.2+ |
| Connection refused | Server not running | Start vLLM serve command |

## Cloud Deployment

Once validated locally, the same model serves on Cloud Run with L4 GPU (Phase 13).
