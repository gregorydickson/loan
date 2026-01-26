# Multi-stage FastAPI Docker build for Cloud Run
# Source: FastAPI deployment docs + Cloud Run best practices

# Stage 1: Build
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies (gcc for C extensions, libpq-dev for asyncpg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project configuration
COPY pyproject.toml ./

# Install Python dependencies to /install prefix
RUN pip install --prefix=/install --no-cache-dir .

# Stage 2: Runtime
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install runtime dependencies:
# - libpq5: PostgreSQL client library for asyncpg
# - tesseract-ocr: OCR engine required by Docling for PDF processing
# - tesseract-ocr-eng: English language data for Tesseract
# - libgl1: OpenGL library required by OpenCV (Docling dependency)
# - libglib2.0-0: GLib required by various imaging libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY src/ ./src/
COPY examples/ ./examples/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Pre-compile Python bytecode for faster startup
RUN python -m compileall -q ./src/ ./examples/

# Pre-download Docling models from HuggingFace Hub to artifacts directory
# CRITICAL: Without this, Docling tries to download at runtime which fails in Cloud Run
# Docling requires two model sets with specific folder names:
# 1. docling-project--docling-layout-heron (layout analysis)
# 2. docling-project--docling-models (table structure v2.3.0)
RUN mkdir -p /app/artifacts && \
    python -c "from huggingface_hub import snapshot_download; \
    from pathlib import Path; \
    snapshot_download('docling-project/docling-layout-heron', \
        local_dir=Path('/app/artifacts/docling-project--docling-layout-heron'), \
        revision='main'); \
    snapshot_download('docling-project/docling-models', \
        local_dir=Path('/app/artifacts/docling-project--docling-models'), \
        revision='v2.3.0')" && \
    chown -R app:app /app/artifacts

# Switch to non-root user
USER app

# Cloud Run provides PORT environment variable
ENV PORT=8080
# Ensure /app is in PYTHONPATH for examples module import
ENV PYTHONPATH=/app
# Point Docling to pre-downloaded models
ENV DOCLING_ARTIFACTS_PATH=/app/artifacts
# Force HuggingFace Hub to use offline mode (backup in case Docling still tries network)
ENV HF_HUB_OFFLINE=1
ENV TRANSFORMERS_OFFLINE=1

# Use exec form for proper signal handling
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
