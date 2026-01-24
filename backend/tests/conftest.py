"""Shared pytest fixtures for loan extraction backend tests.

This module provides:
- Async test client for FastAPI application testing
- Test database session management
- Mock fixtures for external services (Gemini, GCS)

Async fixtures will be added as needed in later phases.
"""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create async test client for FastAPI application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
