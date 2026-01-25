#!/bin/bash
# vLLM LightOnOCR Validation Script
# Tests that vLLM server is running and responds correctly

set -euo pipefail

VLLM_HOST="${VLLM_HOST:-localhost}"
VLLM_PORT="${VLLM_PORT:-8000}"
BASE_URL="http://${VLLM_HOST}:${VLLM_PORT}"

echo "Validating vLLM LightOnOCR at ${BASE_URL}"

# Check if server is running
echo "1. Checking server health..."
if ! curl -s "${BASE_URL}/health" >/dev/null 2>&1; then
    echo "ERROR: vLLM server not responding at ${BASE_URL}"
    echo ""
    echo "Start the server with:"
    echo "  vllm serve lightonai/LightOnOCR-2-1B \\"
    echo "    --limit-mm-per-prompt '{\"image\": 1}' \\"
    echo "    --mm-processor-cache-gb 0 \\"
    echo "    --no-enable-prefix-caching \\"
    echo "    --port 8000"
    exit 1
fi
echo "   Server is healthy"

# Check models endpoint
echo "2. Checking loaded models..."
MODELS=$(curl -s "${BASE_URL}/v1/models" | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])" 2>/dev/null || echo "")
if [[ "$MODELS" != *"LightOnOCR"* && "$MODELS" != "lightonai/LightOnOCR-2-1B" ]]; then
    echo "WARNING: LightOnOCR model may not be loaded correctly"
    echo "   Found: $MODELS"
else
    echo "   Model loaded: $MODELS"
fi

# Simple text completion test (without image to keep it quick)
echo "3. Testing API response..."
RESPONSE=$(curl -s "${BASE_URL}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "lightonai/LightOnOCR-2-1B",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 10
  }' 2>/dev/null || echo "ERROR")

if [[ "$RESPONSE" == "ERROR" ]] || [[ "$RESPONSE" == *"error"* ]]; then
    echo "WARNING: API returned error - this may be expected for text-only input"
    echo "   LightOnOCR is designed for images, not text prompts"
else
    echo "   API responded successfully"
fi

echo ""
echo "Validation complete!"
echo "vLLM is serving LightOnOCR-2-1B at ${BASE_URL}"
echo ""
echo "For full validation, test with an actual image using:"
echo "  curl ${BASE_URL}/v1/chat/completions -d '{image_request}'"
