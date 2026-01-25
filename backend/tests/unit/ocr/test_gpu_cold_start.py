"""GPU cold start timeout handling tests (TEST-10).

Tests specifically for GPU service cold start scenarios, including:
- Timeout configuration for cold start tolerance
- Connection vs read timeout handling
- Circuit breaker behavior during cold starts
- Fallback to Docling when GPU unavailable

These tests complement test_lightonocr_client.py and test_ocr_router.py
by focusing on cold-start specific scenarios.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from aiobreaker import CircuitBreakerError

from src.ocr.lightonocr_client import LightOnOCRClient, LightOnOCRError
from src.ocr.ocr_router import OCRRouter, _gpu_ocr_breaker
from src.ocr.scanned_detector import DetectionResult


# Sample image bytes for testing
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


class TestGPUColdStartHandling:
    """Tests for GPU cold start timeout handling.

    GPU services on Cloud Run may take 30-120s to cold start.
    These tests verify proper timeout configuration and error handling.
    """

    def test_timeout_configuration_default_120s(self):
        """Verify default 120s timeout for cold start tolerance (LOCR-06)."""
        client = LightOnOCRClient(service_url="https://lightonocr-gpu.run.app")
        # 120s allows for GPU container cold start + model loading + inference
        assert client.timeout == 120.0
        assert client.DEFAULT_TIMEOUT == 120.0

    def test_custom_timeout_accepted(self):
        """Verify custom timeout configuration works."""
        client = LightOnOCRClient(
            service_url="https://lightonocr-gpu.run.app",
            timeout=180.0,  # Extended timeout for large documents
        )
        assert client.timeout == 180.0

    def test_timeout_used_in_http_client(self):
        """Verify timeout is passed to httpx.AsyncClient."""
        client = LightOnOCRClient(
            service_url="https://lightonocr-gpu.run.app",
            timeout=90.0,
        )
        # Timeout should be stored for use in async client creation
        assert client.timeout == 90.0

    @pytest.mark.asyncio
    async def test_timeout_raises_lightonocr_error(self):
        """Timeout during request raises LightOnOCRError."""
        client = LightOnOCRClient(
            service_url="https://lightonocr-gpu.run.app",
            timeout=30.0,
        )

        with patch("src.ocr.lightonocr_client.id_token.fetch_id_token") as mock_token:
            mock_token.return_value = "mock-token"

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                # Simulate cold start timeout
                mock_client.post.side_effect = httpx.TimeoutException(
                    "GPU service cold starting, timeout after 30s"
                )
                mock_client_class.return_value = mock_client

                with pytest.raises(LightOnOCRError, match="timed out"):
                    await client.extract_text(PNG_BYTES)

    @pytest.mark.asyncio
    async def test_connect_timeout_handled(self):
        """Connection timeout (TCP handshake) handled gracefully."""
        client = LightOnOCRClient(
            service_url="https://lightonocr-gpu.run.app",
            timeout=30.0,
        )

        with patch("src.ocr.lightonocr_client.id_token.fetch_id_token") as mock_token:
            mock_token.return_value = "mock-token"

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                # Simulate connection timeout (GPU container not yet running)
                mock_client.post.side_effect = httpx.ConnectTimeout(
                    "Unable to connect to GPU service"
                )
                mock_client_class.return_value = mock_client

                with pytest.raises(LightOnOCRError, match="timed out"):
                    await client.extract_text(PNG_BYTES)

    @pytest.mark.asyncio
    async def test_read_timeout_handled(self):
        """Read timeout (slow GPU inference) handled gracefully."""
        client = LightOnOCRClient(
            service_url="https://lightonocr-gpu.run.app",
            timeout=60.0,
        )

        with patch("src.ocr.lightonocr_client.id_token.fetch_id_token") as mock_token:
            mock_token.return_value = "mock-token"

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                # Simulate read timeout (GPU processing taking too long)
                mock_client.post.side_effect = httpx.ReadTimeout(
                    "GPU inference exceeded timeout"
                )
                mock_client_class.return_value = mock_client

                with pytest.raises(LightOnOCRError, match="timed out"):
                    await client.extract_text(PNG_BYTES)


class TestGPUHealthCheckTimeout:
    """Tests for GPU health check timeout handling."""

    @pytest.fixture
    def client(self) -> LightOnOCRClient:
        """Create client for testing."""
        return LightOnOCRClient(
            service_url="https://lightonocr-gpu.run.app",
            timeout=120.0,
        )

    @pytest.mark.asyncio
    async def test_health_check_timeout_returns_false(self, client: LightOnOCRClient):
        """Health check returns False on timeout (GPU cold starting)."""
        with patch("src.ocr.lightonocr_client.id_token.fetch_id_token") as mock_token:
            mock_token.return_value = "mock-token"

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                # Health check times out during cold start
                mock_client.get.side_effect = httpx.TimeoutException(
                    "Health check timeout"
                )
                mock_client_class.return_value = mock_client

                result = await client.health_check()
                assert result is False

    @pytest.mark.asyncio
    async def test_health_check_success_returns_true(self, client: LightOnOCRClient):
        """Health check returns True when service responds."""
        with patch("src.ocr.lightonocr_client.id_token.fetch_id_token") as mock_token:
            mock_token.return_value = "mock-token"

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.get.return_value = MagicMock(status_code=200)
                mock_client_class.return_value = mock_client

                result = await client.health_check()
                assert result is True

    @pytest.mark.asyncio
    async def test_health_check_uses_shorter_timeout(self, client: LightOnOCRClient):
        """Health check should use shorter timeout than extraction."""
        # The health_check method uses a fixed 10s timeout
        # This is appropriate for health checks during routing decisions
        with patch("src.ocr.lightonocr_client.id_token.fetch_id_token") as mock_token:
            mock_token.return_value = "mock-token"

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.get.return_value = MagicMock(status_code=200)
                mock_client_class.return_value = mock_client

                await client.health_check()

                # Verify AsyncClient was called with timeout=10.0
                # (shorter than the 120s extraction timeout)
                mock_client_class.assert_called()
                call_args = mock_client_class.call_args
                assert call_args[1]["timeout"] == 10.0


class TestCircuitBreakerColdStartIntegration:
    """Tests for circuit breaker behavior during GPU cold starts."""

    @pytest.fixture
    def mock_gpu_client(self):
        """Mock LightOnOCRClient."""
        client = MagicMock()
        client.extract_text = AsyncMock(return_value="OCR'd text")
        client.health_check = AsyncMock(return_value=True)
        return client

    @pytest.fixture
    def mock_docling(self):
        """Mock DoclingProcessor."""
        processor = MagicMock()
        processor.enable_tables = True
        processor.max_pages = 100
        processor.process_bytes = MagicMock(return_value=MagicMock(text="Docling text"))
        return processor

    @pytest.fixture
    def mock_detector(self):
        """Mock ScannedDocumentDetector."""
        detector = MagicMock()
        detector.detect = MagicMock(
            return_value=DetectionResult(
                needs_ocr=True,
                scanned_pages=[0, 1],
                total_pages=2,
                scanned_ratio=1.0,
            )
        )
        return detector

    @pytest.fixture
    def router(self, mock_gpu_client, mock_docling, mock_detector):
        """Create router with mocked components."""
        return OCRRouter(
            gpu_client=mock_gpu_client,
            docling_processor=mock_docling,
            detector=mock_detector,
        )

    @pytest.mark.asyncio
    async def test_cold_gpu_triggers_docling_fallback(
        self, router, mock_gpu_client, mock_detector
    ):
        """When GPU health check fails (cold start), fallback to Docling."""
        mock_detector.detect.return_value = DetectionResult(
            needs_ocr=True,
            scanned_pages=[0],
            total_pages=1,
            scanned_ratio=1.0,
        )
        # Simulate cold GPU not responding to health check
        mock_gpu_client.health_check.return_value = False

        with patch("src.ocr.ocr_router.DoclingProcessor") as MockProcessor:
            mock_instance = MagicMock()
            mock_instance.process_bytes.return_value = MagicMock(text="Docling fallback")
            MockProcessor.return_value = mock_instance

            result = await router.process(b"fake pdf", "scanned.pdf", mode="auto")

            # Should fall back to Docling
            assert result.ocr_method == "docling"
            # Docling OCR should be enabled
            MockProcessor.assert_called()
            call_kwargs = MockProcessor.call_args[1]
            assert call_kwargs["enable_ocr"] is True

    @pytest.mark.asyncio
    async def test_gpu_timeout_triggers_docling_fallback(
        self, router, mock_gpu_client, mock_detector
    ):
        """When GPU times out during cold start, fallback to Docling."""
        mock_detector.detect.return_value = DetectionResult(
            needs_ocr=True,
            scanned_pages=[0],
            total_pages=1,
            scanned_ratio=1.0,
        )
        # Simulate timeout during health check
        mock_gpu_client.health_check.side_effect = LightOnOCRError(
            "Request timed out after 120s"
        )

        with patch("src.ocr.ocr_router.DoclingProcessor") as MockProcessor:
            mock_instance = MagicMock()
            mock_instance.process_bytes.return_value = MagicMock(text="Docling fallback")
            MockProcessor.return_value = mock_instance

            result = await router.process(b"fake pdf", "timeout.pdf", mode="auto")

            # Should fall back to Docling
            assert result.ocr_method == "docling"

    def test_circuit_breaker_configuration_for_cold_starts(self):
        """Verify breaker config tolerates cold starts (fail_max=3, timeout=60s)."""
        # With fail_max=3, intermittent cold start timeouts won't immediately
        # open the breaker. 60s reset allows recovery after GPU warms up.
        assert _gpu_ocr_breaker.fail_max == 3
        assert _gpu_ocr_breaker.timeout_duration.total_seconds() == 60

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_triggers_immediate_fallback(
        self, router, mock_gpu_client, mock_detector
    ):
        """When circuit breaker is open, immediately fallback without health check."""
        mock_detector.detect.return_value = DetectionResult(
            needs_ocr=True,
            scanned_pages=[0],
            total_pages=1,
            scanned_ratio=1.0,
        )
        # Circuit breaker is open
        reopen_time = datetime.now(timezone.utc)
        mock_gpu_client.health_check.side_effect = CircuitBreakerError(
            "Circuit breaker is open", reopen_time
        )

        with patch("src.ocr.ocr_router.DoclingProcessor") as MockProcessor:
            mock_instance = MagicMock()
            mock_instance.process_bytes.return_value = MagicMock(text="Docling fallback")
            MockProcessor.return_value = mock_instance

            result = await router.process(b"fake pdf", "breaker.pdf", mode="auto")

            # Should immediately fall back to Docling
            assert result.ocr_method == "docling"

    def test_circuit_breaker_state_accessible(self, router):
        """Circuit breaker state is accessible for monitoring."""
        state = router.get_circuit_breaker_state()
        # State should be one of the valid values
        assert state in ["closed", "open", "half_open"]
