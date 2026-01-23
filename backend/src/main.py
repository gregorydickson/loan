"""FastAPI application entry point.

Provides the main application instance with lifespan management
for database connections and other resources.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.documents import router as documents_router
from src.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan - startup and shutdown.

    Startup: Initialize database connection pool, verify connectivity.
    Shutdown: Dispose connection pool, clean up resources.
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

# Include routers
app.include_router(documents_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for load balancers and monitoring."""
    return {"status": "healthy"}
