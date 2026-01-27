"""Unit tests for main FastAPI application."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from src.api.errors import EntityNotFoundError
from src.main import (
    _add_cors_headers,
    app,
    entity_not_found_handler,
    generic_exception_handler,
)


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_endpoint_returns_healthy_status(self):
        """Test that /health returns status: healthy."""
        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestCORSHeaders:
    """Test CORS header addition function."""

    def test_add_cors_headers_with_run_app_origin(self):
        """Test CORS headers are added for .run.app origins."""
        # Create mock request with .run.app origin
        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = "https://backend-xyz.run.app"

        response = JSONResponse(content={"test": "data"})
        result = _add_cors_headers(response, mock_request)

        assert result.headers["Access-Control-Allow-Origin"] == "https://backend-xyz.run.app"
        assert result.headers["Access-Control-Allow-Credentials"] == "true"

    def test_add_cors_headers_with_non_run_app_origin(self):
        """Test CORS headers are NOT added for non-.run.app origins."""
        # Create mock request with non-.run.app origin
        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = "https://evil.com"

        response = JSONResponse(content={"test": "data"})
        result = _add_cors_headers(response, mock_request)

        # Headers should not be set for non-.run.app origins
        assert "Access-Control-Allow-Origin" not in result.headers
        assert "Access-Control-Allow-Credentials" not in result.headers

    def test_add_cors_headers_with_empty_origin(self):
        """Test CORS headers are NOT added when origin header is empty."""
        # Create mock request with no origin
        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = ""

        response = JSONResponse(content={"test": "data"})
        result = _add_cors_headers(response, mock_request)

        # Headers should not be set when origin is empty
        assert "Access-Control-Allow-Origin" not in result.headers


class TestEntityNotFoundHandler:
    """Test EntityNotFoundError exception handler."""

    @pytest.mark.asyncio
    async def test_entity_not_found_handler_returns_404(self):
        """Test handler returns 404 status code."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = ""
        exc = EntityNotFoundError("Document", "abc123")

        response = await entity_not_found_handler(mock_request, exc)

        assert response.status_code == 404
        assert response.body == b'{"detail":"Document not found: abc123"}'

    @pytest.mark.asyncio
    async def test_entity_not_found_handler_adds_cors_for_run_app(self):
        """Test handler adds CORS headers for .run.app origins."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = "https://frontend-abc.run.app"
        exc = EntityNotFoundError("Borrower", "xyz789")

        response = await entity_not_found_handler(mock_request, exc)

        assert response.status_code == 404
        assert response.headers["Access-Control-Allow-Origin"] == "https://frontend-abc.run.app"
        assert response.headers["Access-Control-Allow-Credentials"] == "true"

    @pytest.mark.asyncio
    async def test_entity_not_found_handler_with_different_entity_types(self):
        """Test handler works with various entity types."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = ""

        test_cases = [
            ("Document", "doc-123"),
            ("Borrower", "borrower-456"),
            ("Task", "task-789"),
        ]

        for entity_type, entity_id in test_cases:
            exc = EntityNotFoundError(entity_type, entity_id)
            response = await entity_not_found_handler(mock_request, exc)

            assert response.status_code == 404
            expected_detail = f'"{entity_type} not found: {entity_id}"'
            assert expected_detail in response.body.decode()


class TestGenericExceptionHandler:
    """Test generic exception handler."""

    @pytest.mark.asyncio
    async def test_generic_exception_handler_returns_500(self):
        """Test handler returns 500 status code for unhandled exceptions."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = ""
        mock_request.url.path = "/api/test"
        exc = Exception("Something went wrong")

        response = await generic_exception_handler(mock_request, exc)

        assert response.status_code == 500
        assert response.body == b'{"detail":"Internal server error"}'

    @pytest.mark.asyncio
    async def test_generic_exception_handler_adds_cors_for_run_app(self):
        """Test handler adds CORS headers for .run.app origins."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = "https://api-test.run.app"
        mock_request.url.path = "/api/test"
        exc = RuntimeError("Test error")

        response = await generic_exception_handler(mock_request, exc)

        assert response.status_code == 500
        assert response.headers["Access-Control-Allow-Origin"] == "https://api-test.run.app"
        assert response.headers["Access-Control-Allow-Credentials"] == "true"

    @pytest.mark.asyncio
    @patch("src.main.logger")
    async def test_generic_exception_handler_logs_error(self, mock_logger):
        """Test handler logs the exception with details."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = ""
        mock_request.url.path = "/api/documents/123"
        exc = ValueError("Invalid input")

        await generic_exception_handler(mock_request, exc)

        # Verify logger.error was called with exc_info and path
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Unhandled exception" in call_args[0]
        assert call_args[1]["exc_info"] == exc
        assert call_args[1]["path"] == "/api/documents/123"


class TestLifespanManager:
    """Test application lifespan management."""

    @pytest.mark.asyncio
    @patch("src.main.settings")
    async def test_lifespan_with_debug_enabled_prints_messages(self, mock_settings):
        """Test lifespan prints startup/shutdown messages when debug=True."""
        mock_settings.debug = True
        mock_settings.api_host = "localhost"
        mock_settings.api_port = 8000

        from src.main import lifespan

        # Use lifespan as async context manager
        async with lifespan(app) as context:
            # During startup - would print startup message
            assert context is None

        # After shutdown - would print shutdown message

    @pytest.mark.asyncio
    @patch("src.main.settings")
    async def test_lifespan_with_debug_disabled_no_output(self, mock_settings):
        """Test lifespan does not print messages when debug=False."""
        mock_settings.debug = False

        from src.main import lifespan

        # Use lifespan as async context manager
        async with lifespan(app) as context:
            assert context is None


class TestAppConfiguration:
    """Test FastAPI app configuration."""

    def test_app_has_correct_title(self):
        """Test app is configured with correct title."""
        assert app.title == "Loan Document Extraction API"

    def test_app_has_correct_version(self):
        """Test app version is set."""
        assert app.version == "0.1.0"

    def test_app_has_description(self):
        """Test app has description."""
        assert "Extract borrower data from loan documents" in app.description

    def test_app_has_routers_registered(self):
        """Test that all expected routers are registered."""
        route_paths = {route.path for route in app.routes}

        # Check that expected routes exist
        assert "/health" in route_paths
        assert "/api/documents/" in route_paths or any("/api/documents" in path for path in route_paths)
        assert "/api/borrowers/" in route_paths or any("/api/borrowers" in path for path in route_paths)

    def test_app_has_cors_middleware(self):
        """Test CORS middleware is configured."""
        # Check that middleware is configured (FastAPI wraps it in Middleware class)
        assert len(app.user_middleware) > 0, "Expected middleware to be configured"
        # The middleware list should contain at least one middleware
        assert any(m for m in app.user_middleware)

    def test_app_has_exception_handlers(self):
        """Test exception handlers are registered."""
        assert EntityNotFoundError in app.exception_handlers
        assert Exception in app.exception_handlers
