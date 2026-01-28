"""Unit tests for LightOnOCRClient.

Tests use mocks to avoid actual GPU service calls.
"""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.ocr.lightonocr_client import LightOnOCRClient, LightOnOCRError


# Sample image bytes (PNG magic header)
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
JPEG_BYTES = b"\xff\xd8\xff" + b"\x00" * 100


class TestLightOnOCRClient:
    """Tests for LightOnOCRClient."""

    @pytest.fixture
    def client(self) -> LightOnOCRClient:
        """Create client for testing."""
        return LightOnOCRClient(
            service_url="https://lightonocr-gpu-test.run.app",
            timeout=30.0,
        )

    @pytest.fixture
    def mock_id_token(self):
        """Mock OIDC ID token."""
        with patch("src.ocr.lightonocr_client.id_token.fetch_id_token") as mock:
            mock.return_value = "mock-token-12345"
            yield mock

    def test_content_type_detection_png(self, client: LightOnOCRClient):
        """Test PNG content type detection."""
        assert client._detect_content_type(PNG_BYTES) == "image/png"

    def test_content_type_detection_jpeg(self, client: LightOnOCRClient):
        """Test JPEG content type detection."""
        assert client._detect_content_type(JPEG_BYTES) == "image/jpeg"

    def test_content_type_detection_unknown(self, client: LightOnOCRClient):
        """Test unknown format defaults to JPEG."""
        assert client._detect_content_type(b"unknown") == "image/jpeg"

    @pytest.mark.asyncio
    async def test_extract_text_success(self, client: LightOnOCRClient, mock_id_token):
        """Test successful text extraction."""
        mock_response = {
            "choices": [{"message": {"content": "Extracted loan document text"}}]
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
            )
            mock_client_class.return_value = mock_client

            result = await client.extract_text(PNG_BYTES)

            assert result == "Extracted loan document text"
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "/v1/chat/completions" in call_args[0][0]
            assert call_args[1]["headers"]["Authorization"] == "Bearer mock-token-12345"

    @pytest.mark.asyncio
    async def test_extract_text_empty_bytes(self, client: LightOnOCRClient):
        """Test error on empty image bytes."""
        with pytest.raises(LightOnOCRError, match="Empty image bytes"):
            await client.extract_text(b"")

    @pytest.mark.asyncio
    async def test_extract_text_auth_failure(self, client: LightOnOCRClient):
        """Test authentication failure handling."""
        with patch("src.ocr.lightonocr_client.id_token.fetch_id_token") as mock:
            mock.side_effect = Exception("Auth failed")

            with pytest.raises(LightOnOCRError, match="Authentication failed"):
                await client.extract_text(PNG_BYTES)

    @pytest.mark.asyncio
    async def test_extract_text_http_error(self, client: LightOnOCRClient, mock_id_token):
        """Test HTTP error handling."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = MagicMock(
                status_code=500,
                text="Internal server error",
            )
            mock_client_class.return_value = mock_client

            with pytest.raises(LightOnOCRError, match="status 500"):
                await client.extract_text(PNG_BYTES)

    @pytest.mark.asyncio
    async def test_extract_text_timeout(self, client: LightOnOCRClient, mock_id_token):
        """Test timeout handling."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.side_effect = httpx.TimeoutException("Connection timed out")
            mock_client_class.return_value = mock_client

            with pytest.raises(LightOnOCRError, match="timed out"):
                await client.extract_text(PNG_BYTES)

    @pytest.mark.asyncio
    async def test_extract_text_request_error(self, client: LightOnOCRClient, mock_id_token):
        """Test request error handling."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.side_effect = httpx.RequestError("Connection failed")
            mock_client_class.return_value = mock_client

            with pytest.raises(LightOnOCRError, match="Request failed"):
                await client.extract_text(PNG_BYTES)

    @pytest.mark.asyncio
    async def test_extract_text_invalid_response(self, client: LightOnOCRClient, mock_id_token):
        """Test invalid response format handling."""
        mock_response = {"invalid": "response"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
            )
            mock_client_class.return_value = mock_client

            with pytest.raises(LightOnOCRError, match="Invalid response format"):
                await client.extract_text(PNG_BYTES)

    @pytest.mark.asyncio
    async def test_extract_text_base64_encoding(self, client: LightOnOCRClient, mock_id_token):
        """Test image is base64 encoded in request."""
        mock_response = {"choices": [{"message": {"content": "text"}}]}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
            )
            mock_client_class.return_value = mock_client

            await client.extract_text(PNG_BYTES)

            # Verify base64 encoding in request payload
            call_args = mock_client.post.call_args
            payload = call_args[1]["json"]
            image_url = payload["messages"][0]["content"][0]["image_url"]["url"]
            assert image_url.startswith("data:image/png;base64,")
            # Verify it's valid base64
            base64_part = image_url.split(",")[1]
            decoded = base64.b64decode(base64_part)
            assert decoded == PNG_BYTES

    @pytest.mark.asyncio
    async def test_extract_text_jpeg_content_type(self, client: LightOnOCRClient, mock_id_token):
        """Test JPEG image uses correct content type in request."""
        mock_response = {"choices": [{"message": {"content": "text"}}]}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
            )
            mock_client_class.return_value = mock_client

            await client.extract_text(JPEG_BYTES)

            # Verify JPEG content type in request payload
            call_args = mock_client.post.call_args
            payload = call_args[1]["json"]
            image_url = payload["messages"][0]["content"][0]["image_url"]["url"]
            assert image_url.startswith("data:image/jpeg;base64,")

    @pytest.mark.asyncio
    async def test_health_check_success(self, client: LightOnOCRClient, mock_id_token):
        """Test health check success."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            # Make get() return a proper awaitable response with JSON
            response = MagicMock(status_code=200)
            response.json.return_value = {
                "data": [{"id": "lightonai/LightOnOCR-2-1B"}]  # MODEL_ID from LightOnOCRClient
            }
            mock_client.get = AsyncMock(return_value=response)
            mock_client_class.return_value = mock_client

            result = await client.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, client: LightOnOCRClient, mock_id_token):
        """Test health check failure."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = MagicMock(status_code=503)
            mock_client_class.return_value = mock_client

            result = await client.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_health_check_exception(self, client: LightOnOCRClient, mock_id_token):
        """Test health check with exception."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.side_effect = Exception("Network error")
            mock_client_class.return_value = mock_client

            result = await client.health_check()
            assert result is False

    def test_service_url_trailing_slash(self):
        """Test service URL trailing slash is stripped."""
        client = LightOnOCRClient(service_url="https://example.run.app/")
        assert client.service_url == "https://example.run.app"

    def test_custom_timeout(self):
        """Test custom timeout configuration."""
        client = LightOnOCRClient(service_url="https://example.run.app", timeout=60.0)
        assert client.timeout == 60.0

    def test_custom_max_tokens(self):
        """Test custom max_tokens configuration."""
        client = LightOnOCRClient(service_url="https://example.run.app", max_tokens=8192)
        assert client.max_tokens == 8192

    def test_default_values(self):
        """Test default timeout and max_tokens values."""
        client = LightOnOCRClient(service_url="https://example.run.app")
        assert client.timeout == 120.0
        assert client.max_tokens == 3072

    def test_model_id_constant(self):
        """Test MODEL_ID constant is set correctly."""
        assert LightOnOCRClient.MODEL_ID == "lightonai/LightOnOCR-2-1B"

    @pytest.mark.asyncio
    async def test_extract_text_model_in_payload(self, client: LightOnOCRClient, mock_id_token):
        """Test model ID is included in request payload."""
        mock_response = {"choices": [{"message": {"content": "text"}}]}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
            )
            mock_client_class.return_value = mock_client

            await client.extract_text(PNG_BYTES)

            call_args = mock_client.post.call_args
            payload = call_args[1]["json"]
            assert payload["model"] == "lightonai/LightOnOCR-2-1B"
            assert payload["max_tokens"] == 3072

    @pytest.mark.asyncio
    async def test_extract_text_http_404(self, client: LightOnOCRClient, mock_id_token):
        """Test 404 error handling."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = MagicMock(
                status_code=404,
                text="Not Found",
            )
            mock_client_class.return_value = mock_client

            with pytest.raises(LightOnOCRError, match="status 404"):
                await client.extract_text(PNG_BYTES)

    @pytest.mark.asyncio
    async def test_extract_text_empty_choices(self, client: LightOnOCRClient, mock_id_token):
        """Test response with empty choices array."""
        mock_response = {"choices": []}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
            )
            mock_client_class.return_value = mock_client

            with pytest.raises(LightOnOCRError, match="Invalid response format"):
                await client.extract_text(PNG_BYTES)
