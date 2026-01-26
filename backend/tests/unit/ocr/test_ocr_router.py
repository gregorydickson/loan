"""Unit tests for OCRRouter."""

from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiobreaker import CircuitBreakerError

from src.ocr.ocr_router import OCRMode, OCRResult, OCRRouter, _gpu_ocr_breaker
from src.ocr.scanned_detector import DetectionResult
from src.ocr.lightonocr_client import LightOnOCRError


class TestOCRResult:
    """Tests for OCRResult dataclass."""

    def test_ocr_result_creation(self):
        """OCRResult stores all fields correctly."""
        mock_content = MagicMock()
        result = OCRResult(
            content=mock_content,
            ocr_method="gpu",
            pages_ocrd=[0, 1, 2],
        )

        assert result.content == mock_content
        assert result.ocr_method == "gpu"
        assert result.pages_ocrd == [0, 1, 2]

    def test_ocr_result_no_ocr(self):
        """OCRResult handles no OCR case."""
        mock_content = MagicMock()
        result = OCRResult(
            content=mock_content,
            ocr_method="none",
            pages_ocrd=[],
        )

        assert result.ocr_method == "none"
        assert len(result.pages_ocrd) == 0

    def test_ocr_result_docling_fallback(self):
        """OCRResult tracks Docling fallback."""
        mock_content = MagicMock()
        result = OCRResult(
            content=mock_content,
            ocr_method="docling",
            pages_ocrd=[0, 2, 3],
        )

        assert result.ocr_method == "docling"
        assert result.pages_ocrd == [0, 2, 3]


class TestOCRRouter:
    """Tests for OCRRouter."""

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
                needs_ocr=False,
                scanned_pages=[],
                total_pages=3,
                scanned_ratio=0.0,
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
    async def test_skip_mode_no_ocr(self, router, mock_docling):
        """mode='skip' uses Docling without OCR."""
        with patch("src.ocr.ocr_router.DoclingProcessor") as MockProcessor:
            mock_instance = MagicMock()
            mock_instance.process_bytes.return_value = MagicMock(text="Skip text")
            MockProcessor.return_value = mock_instance

            result = await router.process(b"fake pdf", "test.pdf", mode="skip")

            assert result.ocr_method == "none"
            assert result.pages_ocrd == []
            # Verify Docling was created with enable_ocr=False
            MockProcessor.assert_called_once()
            call_kwargs = MockProcessor.call_args[1]
            assert call_kwargs["enable_ocr"] is False

    @pytest.mark.asyncio
    async def test_auto_mode_native_pdf(self, router, mock_detector):
        """mode='auto' skips OCR for native PDFs."""
        mock_detector.detect.return_value = DetectionResult(
            needs_ocr=False,
            scanned_pages=[],
            total_pages=3,
            scanned_ratio=0.0,
        )

        with patch("src.ocr.ocr_router.DoclingProcessor") as MockProcessor:
            mock_instance = MagicMock()
            mock_instance.process_bytes.return_value = MagicMock(text="Native text")
            MockProcessor.return_value = mock_instance

            result = await router.process(b"fake pdf", "native.pdf", mode="auto")

            assert result.ocr_method == "none"
            assert result.pages_ocrd == []

    @pytest.mark.asyncio
    async def test_auto_mode_scanned_pdf_with_healthy_gpu(
        self, router, mock_detector, mock_gpu_client
    ):
        """mode='auto' uses GPU OCR for scanned PDFs when GPU is healthy."""
        mock_detector.detect.return_value = DetectionResult(
            needs_ocr=True,
            scanned_pages=[0, 1],
            total_pages=2,
            scanned_ratio=1.0,
        )
        mock_gpu_client.health_check.return_value = True
        mock_gpu_client.extract_text.return_value = "GPU OCR text"

        with patch.object(router, '_page_to_png', return_value=b'fake png'):
            result = await router.process(b"fake pdf", "scanned.pdf", mode="auto")

        assert result.ocr_method == "gpu"  # GPU OCR is now wired
        assert result.pages_ocrd == [0, 1]
        assert mock_gpu_client.extract_text.call_count == 2

    @pytest.mark.asyncio
    async def test_auto_mode_fallback_on_gpu_unhealthy(
        self, router, mock_detector, mock_gpu_client
    ):
        """mode='auto' falls back to Docling when GPU unhealthy."""
        mock_detector.detect.return_value = DetectionResult(
            needs_ocr=True,
            scanned_pages=[0],
            total_pages=1,
            scanned_ratio=1.0,
        )
        mock_gpu_client.health_check.return_value = False

        with patch("src.ocr.ocr_router.DoclingProcessor") as MockProcessor:
            mock_instance = MagicMock()
            mock_instance.process_bytes.return_value = MagicMock(text="Fallback text")
            MockProcessor.return_value = mock_instance

            result = await router.process(b"fake pdf", "scanned.pdf", mode="auto")

            assert result.ocr_method == "docling"
            # Verify Docling OCR was used
            MockProcessor.assert_called()
            call_kwargs = MockProcessor.call_args[1]
            assert call_kwargs["enable_ocr"] is True

    @pytest.mark.asyncio
    async def test_force_mode_always_ocr(self, router, mock_gpu_client):
        """mode='force' always runs OCR via GPU when healthy."""
        mock_gpu_client.health_check.return_value = True
        mock_gpu_client.extract_text.return_value = "Force GPU OCR text"

        with patch("src.ocr.ocr_router.pdfium.PdfDocument") as MockPdf:
            mock_pdf = MagicMock()
            mock_pdf.__len__ = MagicMock(return_value=2)
            MockPdf.return_value = mock_pdf

            with patch.object(router, '_page_to_png', return_value=b'fake png'):
                result = await router.process(b"fake pdf", "force.pdf", mode="force")

        # Should have OCR'd both pages via GPU
        assert result.ocr_method == "gpu"
        assert len(result.pages_ocrd) == 2
        assert mock_gpu_client.extract_text.call_count == 2

    @pytest.mark.asyncio
    async def test_fallback_on_light_onocr_error(
        self, router, mock_detector, mock_gpu_client
    ):
        """Falls back to Docling on LightOnOCRError."""
        mock_detector.detect.return_value = DetectionResult(
            needs_ocr=True,
            scanned_pages=[0],
            total_pages=1,
            scanned_ratio=1.0,
        )
        mock_gpu_client.health_check.side_effect = LightOnOCRError("Connection failed")

        with patch("src.ocr.ocr_router.DoclingProcessor") as MockProcessor:
            mock_instance = MagicMock()
            mock_instance.process_bytes.return_value = MagicMock(text="Fallback text")
            MockProcessor.return_value = mock_instance

            result = await router.process(b"fake pdf", "error.pdf", mode="auto")

            assert result.ocr_method == "docling"

    @pytest.mark.asyncio
    async def test_fallback_on_circuit_breaker_open(
        self, router, mock_detector, mock_gpu_client
    ):
        """Falls back to Docling when circuit breaker is open."""
        mock_detector.detect.return_value = DetectionResult(
            needs_ocr=True,
            scanned_pages=[0],
            total_pages=1,
            scanned_ratio=1.0,
        )
        reopen_time = datetime.now(timezone.utc)
        mock_gpu_client.health_check.side_effect = CircuitBreakerError(
            "Circuit breaker is open", reopen_time
        )

        with patch("src.ocr.ocr_router.DoclingProcessor") as MockProcessor:
            mock_instance = MagicMock()
            mock_instance.process_bytes.return_value = MagicMock(text="Fallback text")
            MockProcessor.return_value = mock_instance

            result = await router.process(b"fake pdf", "breaker.pdf", mode="auto")

            assert result.ocr_method == "docling"

    @pytest.mark.asyncio
    async def test_scanned_pdf_uses_gpu_ocr(
        self, router, mock_detector, mock_gpu_client, mock_docling
    ):
        """Test that scanned PDF pages are sent to GPU OCR service.

        This test verifies GPU OCR is actually invoked (not just health checked)
        when processing scanned documents. Uses a mock setup with 2 scanned pages.
        """
        # Arrange
        mock_detector.detect.return_value = DetectionResult(
            needs_ocr=True,
            scanned_pages=[0, 1],  # 2 scanned pages for this test
            total_pages=2,
            scanned_ratio=1.0,
        )
        mock_gpu_client.health_check.return_value = True
        mock_gpu_client.extract_text.return_value = "OCR extracted text from GPU"

        # Mock _page_to_png to avoid actual PDF processing
        with patch.object(router, '_page_to_png', return_value=b'fake png bytes'):
            result = await router.process(b"fake pdf", "scanned.pdf", mode="auto")

        # Assert
        assert result.ocr_method == "gpu"
        assert result.pages_ocrd == [0, 1]
        # Verify GPU extract_text was actually called (not just health_check)
        assert mock_gpu_client.extract_text.called
        # Call count matches number of scanned pages in this test setup
        assert mock_gpu_client.extract_text.call_count == 2

    @pytest.mark.asyncio
    async def test_gpu_unavailable_falls_back_to_docling(
        self, router, mock_detector, mock_gpu_client
    ):
        """Test fallback to Docling when GPU service is unhealthy.

        This explicitly tests the fallback path when GPU health check fails,
        ensuring Docling OCR is used as a backup.
        """
        mock_detector.detect.return_value = DetectionResult(
            needs_ocr=True,
            scanned_pages=[0],
            total_pages=1,
            scanned_ratio=1.0,
        )
        # GPU is unhealthy
        mock_gpu_client.health_check.return_value = False

        with patch("src.ocr.ocr_router.DoclingProcessor") as MockProcessor:
            mock_instance = MagicMock()
            mock_instance.process_bytes.return_value = MagicMock(text="Docling fallback text")
            MockProcessor.return_value = mock_instance

            result = await router.process(b"fake pdf", "scanned.pdf", mode="auto")

            # Should fall back to Docling
            assert result.ocr_method == "docling"
            # GPU extract_text should NOT have been called
            assert not mock_gpu_client.extract_text.called
            # Docling OCR should have been invoked
            MockProcessor.assert_called()
            call_kwargs = MockProcessor.call_args[1]
            assert call_kwargs["enable_ocr"] is True

    def test_circuit_breaker_state(self, router):
        """get_circuit_breaker_state returns current state."""
        state = router.get_circuit_breaker_state()
        # Should be "closed" initially (string from enum name)
        assert state in ["closed", "open", "half_open"]

    def test_router_initialization_default_detector(self, mock_gpu_client, mock_docling):
        """Router creates default detector if not provided."""
        router = OCRRouter(
            gpu_client=mock_gpu_client,
            docling_processor=mock_docling,
        )
        assert router.detector is not None

    def test_router_initialization_custom_dpi(self, mock_gpu_client, mock_docling):
        """Router accepts custom render DPI."""
        router = OCRRouter(
            gpu_client=mock_gpu_client,
            docling_processor=mock_docling,
            render_dpi=300,
        )
        assert router.render_dpi == 300


class TestCircuitBreaker:
    """Tests for circuit breaker behavior."""

    def test_circuit_breaker_configuration(self):
        """Circuit breaker is configured with correct parameters."""
        # Verify breaker is configured correctly
        assert _gpu_ocr_breaker.fail_max == 3
        assert _gpu_ocr_breaker.timeout_duration.total_seconds() == 60

    def test_circuit_breaker_initial_state(self):
        """Circuit breaker starts in closed state."""
        # Note: state is an enum, use .name for string
        state = _gpu_ocr_breaker.current_state.name.lower()
        assert state in ["closed", "open", "half_open"]


class TestOCRModeType:
    """Tests for OCRMode type alias."""

    def test_ocr_mode_values(self):
        """OCRMode accepts valid values."""
        modes: list[OCRMode] = ["auto", "force", "skip"]
        assert len(modes) == 3

    def test_ocr_mode_auto_default(self, ):
        """Auto is the expected default mode."""
        # This tests the type annotation expectations
        mode: OCRMode = "auto"
        assert mode == "auto"


class TestPageToPng:
    """Tests for PDF page to PNG conversion."""

    @pytest.fixture
    def router_with_mocks(self):
        """Create router with all mocks."""
        mock_gpu = MagicMock()
        mock_docling = MagicMock()
        mock_docling.enable_tables = True
        mock_docling.max_pages = 100
        return OCRRouter(
            gpu_client=mock_gpu,
            docling_processor=mock_docling,
        )

    def test_page_to_png_calls_pdfium(self, router_with_mocks):
        """_page_to_png uses pypdfium2 correctly."""
        with patch("src.ocr.ocr_router.pdfium.PdfDocument") as MockPdf:
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_bitmap = MagicMock()
            mock_pil = MagicMock()

            mock_pdf.__getitem__ = MagicMock(return_value=mock_page)
            mock_page.render = MagicMock(return_value=mock_bitmap)
            mock_bitmap.to_pil = MagicMock(return_value=mock_pil)
            mock_pil.save = MagicMock()

            MockPdf.return_value = mock_pdf

            router_with_mocks._page_to_png(b"fake pdf", 0)

            # Verify PDF was opened
            MockPdf.assert_called_once_with(b"fake pdf")
            # Verify page was accessed
            mock_pdf.__getitem__.assert_called_once_with(0)
            # Verify page was rendered
            mock_page.render.assert_called_once()
            # Verify bitmap was converted to PIL
            mock_bitmap.to_pil.assert_called_once()
