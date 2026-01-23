"""API module with REST endpoints."""

from src.api.documents import router as documents_router

__all__ = ["documents_router"]
