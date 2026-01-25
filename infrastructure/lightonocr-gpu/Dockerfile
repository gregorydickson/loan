# LightOnOCR GPU Service Dockerfile
# vLLM-based container for serving LightOnOCR-2-1B model on Cloud Run GPU
#
# Build: docker build -t lightonocr-gpu .
# Run locally: docker run -p 8000:8000 --gpus all lightonocr-gpu
#
# Source: https://cloud.google.com/run/docs/tutorials/gpu-gemma2-with-vllm

# Base vLLM image with CUDA support
FROM vllm/vllm-openai:v0.11.2

# LightOnOCR-2 requires transformers from source (not stable release)
# See: https://huggingface.co/lightonai/LightOnOCR-2-1B
RUN pip install git+https://github.com/huggingface/transformers.git

# Additional dependencies for image processing
RUN pip install pillow pypdfium2

# Download model at build time for faster cold starts
# Model is ~2GB, stored in /model-cache
ENV HF_HOME=/model-cache
RUN huggingface-cli download lightonai/LightOnOCR-2-1B

# Run in offline mode after download (no network needed at runtime)
ENV HF_HUB_OFFLINE=1

# Expose vLLM server port
EXPOSE 8000

# vLLM entrypoint with LightOnOCR-specific flags:
# --port: Cloud Run injects PORT env var, default 8000
# --model: LightOnOCR-2-1B from HuggingFace
# --limit-mm-per-prompt: one image per request (OCR use case)
# --mm-processor-cache-gb 0: disable multimodal cache (single images)
# --no-enable-prefix-caching: disable prefix caching (one-off OCR requests)
ENTRYPOINT ["python3", "-m", "vllm.entrypoints.openai.api_server", \
    "--port", "8000", \
    "--model", "lightonai/LightOnOCR-2-1B", \
    "--limit-mm-per-prompt", "{\"image\": 1}", \
    "--mm-processor-cache-gb", "0", \
    "--no-enable-prefix-caching"]
