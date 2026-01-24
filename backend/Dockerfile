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

# Install runtime dependencies only (libpq5 for asyncpg runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Pre-compile Python bytecode for faster startup
RUN python -m compileall -q ./src/

# Switch to non-root user
USER app

# Cloud Run provides PORT environment variable
ENV PORT=8080

# Use exec form for proper signal handling
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
