"""FastAPI application entry point.

Provides the main application instance with lifespan management
for database connections and other resources.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from src.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan - startup and shutdown.

    Startup: Initialize database connection pool, verify connectivity.
    Shutdown: Dispose connection pool, clean up resources.

    Database engine will be added in Phase 01-03 after models are defined.
    """
    # Startup
    if settings.debug:
        print(f"Starting application on {settings.api_host}:{settings.api_port}")

    yield  # Application runs

    # Shutdown
    if settings.debug:
        print("Shutting down application")


app = FastAPI(
    title="Loan Document Extraction API",
    description="Extract borrower data from loan documents with source attribution",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for load balancers and monitoring."""
    return {"status": "healthy"}
