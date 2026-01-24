"""FastAPI application entry point.

Provides the main application instance with lifespan management
for database connections and other resources.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.documents import router as documents_router
from src.api.errors import EntityNotFoundError
from src.config import settings

logger = structlog.get_logger()


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

# CORS middleware - MUST be added first, before exception handlers and routers
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev
        "http://localhost:5173",  # Vite dev
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Custom exception handlers
@app.exception_handler(EntityNotFoundError)
async def entity_not_found_handler(
    request: Request, exc: EntityNotFoundError
) -> JSONResponse:
    """Handle EntityNotFoundError with 404 response."""
    return JSONResponse(
        status_code=404,
        content={"detail": f"{exc.entity_type} not found: {exc.entity_id}"},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Handle unhandled exceptions with 500 response and logging."""
    logger.error("Unhandled exception", exc_info=exc, path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Include routers
app.include_router(documents_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for load balancers and monitoring."""
    return {"status": "healthy"}
