"""API module with REST endpoints."""

from src.api.documents import router as documents_router
from src.api.tasks import router as tasks_router

__all__ = ["documents_router", "tasks_router"]
