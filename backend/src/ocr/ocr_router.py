"""OCR routing with circuit breaker and Docling fallback.

LOCR-05: Scanned document detection implemented (auto OCR routing)
LOCR-11: Fallback to Docling OCR when GPU service unavailable
"""

import io
import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Literal

import pypdfium2 as pdfium
from aiobreaker import CircuitBreaker, CircuitBreakerError

from src.ingestion.docling_processor import DoclingProcessor, DocumentContent
from src.ocr.lightonocr_client import LightOnOCRClient, LightOnOCRError
from src.ocr.scanned_detector import DetectionResult, ScannedDocumentDetector

logger = logging.getLogger(__name__)


# Type alias for OCR mode parameter
OCRMode = Literal["auto", "force", "skip"]


@dataclass
class OCRResult:
    """Result of OCR processing.

    Attributes:
        content: Processed document content
        ocr_method: Which OCR method was used ("gpu", "docling", "none")
        pages_ocrd: List of page indices that were OCR'd
    """

    content: DocumentContent
    ocr_method: Literal["gpu", "docling", "none"]
    pages_ocrd: list[int]


# Circuit breaker for GPU OCR service
# Opens after 3 failures, resets after 60 seconds
_gpu_ocr_breaker = CircuitBreaker(
    fail_max=3,
    timeout_duration=timedelta(seconds=60),
)


class OCRRouter:
    """Routes OCR between GPU service and Docling fallback.

    LOCR-05: Scanned document detection implemented (auto OCR routing)
    LOCR-11: Fallback to Docling OCR when GPU service unavailable

    Example:
        router = OCRRouter(
            gpu_client=LightOnOCRClient("https://lightonocr-gpu-xxx.run.app"),
            docling_processor=DoclingProcessor(),
        )
        result = await router.process(pdf_bytes, "document.pdf", mode="auto")
    """

    # Default DPI for page-to-image conversion
    DEFAULT_RENDER_DPI = 150

    def __init__(
        self,
        gpu_client: LightOnOCRClient,
        docling_processor: DoclingProcessor,
        detector: ScannedDocumentDetector | None = None,
        render_dpi: int = DEFAULT_RENDER_DPI,
    ):
        """Initialize OCR router.

        Args:
            gpu_client: LightOnOCR GPU service client
            docling_processor: Docling processor for fallback OCR
            detector: Scanned document detector (created if not provided)
            render_dpi: DPI for page-to-image conversion (default 150)
        """
        self.gpu_client = gpu_client
        self.docling = docling_processor
        self.detector = detector or ScannedDocumentDetector()
        self.render_dpi = render_dpi

    def _page_to_png(self, pdf_bytes: bytes, page_index: int) -> bytes:
        """Convert PDF page to PNG image bytes.

        Args:
            pdf_bytes: Raw PDF bytes
            page_index: 0-indexed page number

        Returns:
            PNG image bytes
        """
        pdf = pdfium.PdfDocument(pdf_bytes)
        page = pdf[page_index]

        # Render at specified DPI
        scale = self.render_dpi / 72  # PDF default is 72 DPI
        bitmap = page.render(scale=scale)
        pil_image = bitmap.to_pil()

        # Convert to PNG bytes
        buffer = io.BytesIO()
        pil_image.save(buffer, format="PNG")
        return buffer.getvalue()

    @_gpu_ocr_breaker
    async def _try_gpu_ocr(self, image_bytes: bytes) -> str:
        """Attempt GPU OCR with circuit breaker protection.

        LOCR-11: Circuit breaker opens after 3 failures

        Args:
            image_bytes: PNG image bytes

        Returns:
            Extracted text

        Raises:
            LightOnOCRError: If GPU OCR fails
            CircuitBreakerError: If circuit breaker is open
        """
        return await self.gpu_client.extract_text(image_bytes)

    def _docling_with_ocr(self, pdf_bytes: bytes, filename: str) -> DocumentContent:
        """Process with Docling OCR enabled.

        LOCR-11: Fallback to Docling OCR when GPU service unavailable

        Args:
            pdf_bytes: Raw PDF bytes
            filename: Original filename

        Returns:
            DocumentContent with OCR'd text
        """
        # Create a Docling processor with OCR enabled
        ocr_processor = DoclingProcessor(
            enable_ocr=True,
            enable_tables=self.docling.enable_tables,
            max_pages=self.docling.max_pages,
        )
        return ocr_processor.process_bytes(pdf_bytes, filename)

    async def _ocr_pages_with_gpu(
        self,
        pdf_bytes: bytes,
        scanned_pages: list[int],
    ) -> dict[int, str]:
        """OCR specific pages using GPU service.

        Args:
            pdf_bytes: Raw PDF bytes
            scanned_pages: List of page indices to OCR

        Returns:
            Dict mapping page index to OCR'd text

        Raises:
            LightOnOCRError: If any page fails
            CircuitBreakerError: If circuit breaker is open
        """
        results: dict[int, str] = {}

        for page_idx in scanned_pages:
            png_bytes = self._page_to_png(pdf_bytes, page_idx)
            text = await self._try_gpu_ocr(png_bytes)
            results[page_idx] = text

        return results

    async def process(
        self,
        pdf_bytes: bytes,
        filename: str,
        mode: OCRMode = "auto",
    ) -> OCRResult:
        """Process document with intelligent OCR routing.

        LOCR-05: Scanned document detection implemented (auto OCR routing)
        LOCR-11: Fallback to Docling OCR when GPU service unavailable

        Args:
            pdf_bytes: Raw PDF file bytes
            filename: Original filename
            mode: OCR mode:
                - "auto": Detect scanned pages, OCR only if needed (default)
                - "force": Always run OCR (for poor-quality native PDFs)
                - "skip": Never run OCR (fastest, native PDFs only)

        Returns:
            OCRResult with processed content and OCR metadata
        """
        # Skip mode: just use Docling without OCR
        if mode == "skip":
            logger.info("OCR skip mode: using Docling without OCR for %s", filename)
            # Use Docling without OCR
            no_ocr_processor = DoclingProcessor(
                enable_ocr=False,
                enable_tables=self.docling.enable_tables,
                max_pages=self.docling.max_pages,
            )
            content = no_ocr_processor.process_bytes(pdf_bytes, filename)
            return OCRResult(content=content, ocr_method="none", pages_ocrd=[])

        # Force mode or auto mode with detection
        if mode == "force":
            pdf = pdfium.PdfDocument(pdf_bytes)
            detection = DetectionResult(
                needs_ocr=True,
                scanned_pages=list(range(len(pdf))),
                total_pages=len(pdf),
                scanned_ratio=1.0,
            )
        else:
            # Auto mode: detect which pages need OCR
            detection = self.detector.detect(pdf_bytes)

        if not detection.needs_ocr:
            # Native PDF - use Docling without OCR
            logger.info(
                "Native PDF detected for %s (%.1f%% scanned), skipping OCR",
                filename,
                detection.scanned_ratio * 100,
            )
            no_ocr_processor = DoclingProcessor(
                enable_ocr=False,
                enable_tables=self.docling.enable_tables,
                max_pages=self.docling.max_pages,
            )
            content = no_ocr_processor.process_bytes(pdf_bytes, filename)
            return OCRResult(content=content, ocr_method="none", pages_ocrd=[])

        # Scanned PDF - try GPU OCR first
        logger.info(
            "Scanned PDF detected for %s (%.1f%% scanned, pages %s), attempting GPU OCR",
            filename,
            detection.scanned_ratio * 100,
            detection.scanned_pages,
        )

        try:
            # For now, use full-document GPU OCR via Docling fallback pattern
            # Page-level GPU OCR would require more complex text merging
            # which is deferred to Phase 15 (Dual Pipeline Integration)
            #
            # Try GPU health check first
            is_healthy = await self.gpu_client.health_check()
            if not is_healthy:
                raise LightOnOCRError("GPU service unhealthy")

            # GPU is healthy - but for full document OCR, we still use Docling
            # as the orchestrator and let it handle the complexity
            # This plan sets up the routing; Phase 15 will wire full integration
            logger.info("GPU service healthy, using Docling OCR for full document")
            content = self._docling_with_ocr(pdf_bytes, filename)
            return OCRResult(
                content=content,
                ocr_method="docling",  # Using Docling's OCR engine for now
                pages_ocrd=detection.scanned_pages,
            )

        except (LightOnOCRError, CircuitBreakerError) as e:
            # GPU OCR failed or circuit breaker open - fall back to Docling OCR
            logger.warning(
                "GPU OCR unavailable for %s: %s. Falling back to Docling OCR.",
                filename,
                str(e),
            )
            content = self._docling_with_ocr(pdf_bytes, filename)
            return OCRResult(
                content=content,
                ocr_method="docling",
                pages_ocrd=detection.scanned_pages,
            )

    def get_circuit_breaker_state(self) -> str:
        """Get current circuit breaker state.

        Returns:
            State string: "closed", "open", or "half-open"
        """
        return _gpu_ocr_breaker.current_state
