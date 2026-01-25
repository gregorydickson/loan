# LightOnOCR GPU Service Dockerfile
# vLLM-based container for serving LightOnOCR-2-1B model on Cloud Run GPU
#
# Build: docker build -t lightonocr-gpu .
# Run locally: docker run -p 8000:8000 --gpus all lightonocr-gpu
#
# Source: https://cloud.google.com/run/docs/tutorials/gpu-gemma2-with-vllm

# Base vLLM image with CUDA support
FROM vllm/vllm-openai:v0.11.2

# LightOnOCR-2 may work with latest stable transformers 4.x
# vLLM 0.11.2 requires transformers<5,>=4.56.0
# The model card suggests from source but we'll try stable 4.57.1 first
RUN pip install --upgrade transformers==4.57.1

# Additional dependencies for image processing
RUN pip install pillow pypdfium2

# Download model at build time for faster cold starts
# Model is ~2GB, stored in /model-cache
ENV HF_HOME=/model-cache
RUN python3 -c "from huggingface_hub import snapshot_download; snapshot_download('lightonai/LightOnOCR-2-1B')"

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
# --gpu-memory-utilization 0.85: reduce from default 0.9 to leave headroom
# --max-num-seqs 16: reduce concurrent sequences for memory efficiency
# --max-model-len 4096: limit context length for memory efficiency
ENTRYPOINT ["python3", "-m", "vllm.entrypoints.openai.api_server", \
    "--port", "8000", \
    "--model", "lightonai/LightOnOCR-2-1B", \
    "--limit-mm-per-prompt", "{\"image\": 1}", \
    "--mm-processor-cache-gb", "0", \
    "--no-enable-prefix-caching", \
    "--gpu-memory-utilization", "0.80", \
    "--max-num-seqs", "8", \
    "--max-model-len", "4096"]
