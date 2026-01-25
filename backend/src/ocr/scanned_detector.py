"""Scanned document detection via text extraction ratio.

LOCR-05: Scanned document detection implemented (auto OCR routing)
"""

import logging
from dataclasses import dataclass

import pypdfium2 as pdfium

logger = logging.getLogger(__name__)


@dataclass
class DetectionResult:
    """Result of scanned document detection.

    Attributes:
        needs_ocr: True if document should be routed to OCR
        scanned_pages: List of 0-indexed page numbers that are scanned
        total_pages: Total number of pages in document
        scanned_ratio: Ratio of scanned pages to total pages
    """

    needs_ocr: bool
    scanned_pages: list[int]
    total_pages: int
    scanned_ratio: float


class ScannedDocumentDetector:
    """Detect scanned/image-based pages in PDF documents.

    LOCR-05: Scanned document detection implemented (auto OCR routing)

    Uses text extraction ratio: if extractable characters per page
    is below threshold, the page is likely a scanned image.

    Example:
        detector = ScannedDocumentDetector()
        result = detector.detect(pdf_bytes)
        if result.needs_ocr:
            # Route to GPU OCR or Docling OCR
            ...
    """

    # Minimum characters per page to consider it "native" (has text layer)
    MIN_CHARS_THRESHOLD = 50

    # Ratio of scanned pages to trigger full-document OCR
    SCANNED_PAGE_RATIO_THRESHOLD = 0.5

    def __init__(
        self,
        min_chars_threshold: int = MIN_CHARS_THRESHOLD,
        scanned_ratio_threshold: float = SCANNED_PAGE_RATIO_THRESHOLD,
    ):
        """Initialize detector with configurable thresholds.

        Args:
            min_chars_threshold: Minimum characters per page to consider native
            scanned_ratio_threshold: Ratio of scanned pages to trigger OCR
        """
        self.min_chars_threshold = min_chars_threshold
        self.scanned_ratio_threshold = scanned_ratio_threshold

    def _page_needs_ocr(self, page: pdfium.PdfPage) -> bool:
        """Check if a single page needs OCR.

        Args:
            page: pypdfium2 PdfPage object

        Returns:
            True if page appears to be scanned (needs OCR)
        """
        try:
            textpage = page.get_textpage()
            text = textpage.get_text_bounded()

            # If we extracted meaningful text, page has a text layer
            if text and len(text.strip()) >= self.min_chars_threshold:
                return False

            return True
        except Exception as e:
            # If text extraction fails, assume page is scanned
            logger.warning("Text extraction failed for page, assuming scanned: %s", str(e))
            return True

    def detect(self, pdf_bytes: bytes) -> DetectionResult:
        """Analyze PDF for OCR need.

        LOCR-05: Scanned document detection implemented (auto OCR routing)

        Args:
            pdf_bytes: Raw PDF file bytes

        Returns:
            DetectionResult with needs_ocr flag and page-level details
        """
        if not pdf_bytes:
            logger.warning("Empty PDF bytes provided")
            return DetectionResult(
                needs_ocr=False,
                scanned_pages=[],
                total_pages=0,
                scanned_ratio=0.0,
            )

        try:
            pdf = pdfium.PdfDocument(pdf_bytes)
        except Exception as e:
            logger.error("Failed to parse PDF: %s", str(e))
            # If we can't parse the PDF, assume it needs OCR
            return DetectionResult(
                needs_ocr=True,
                scanned_pages=[],
                total_pages=0,
                scanned_ratio=1.0,
            )

        total_pages = len(pdf)
        if total_pages == 0:
            return DetectionResult(
                needs_ocr=False,
                scanned_pages=[],
                total_pages=0,
                scanned_ratio=0.0,
            )

        scanned_pages: list[int] = []

        for i in range(total_pages):
            page = pdf[i]
            if self._page_needs_ocr(page):
                scanned_pages.append(i)

        # Document needs OCR if majority of pages are scanned
        scanned_ratio = len(scanned_pages) / total_pages
        needs_ocr = scanned_ratio >= self.scanned_ratio_threshold

        logger.info(
            "PDF detection: %d/%d pages scanned (%.1f%%), needs_ocr=%s",
            len(scanned_pages),
            total_pages,
            scanned_ratio * 100,
            needs_ocr,
        )

        return DetectionResult(
            needs_ocr=needs_ocr,
            scanned_pages=scanned_pages,
            total_pages=total_pages,
            scanned_ratio=scanned_ratio,
        )

    def detect_page(self, pdf_bytes: bytes, page_index: int) -> bool:
        """Check if a specific page needs OCR.

        Args:
            pdf_bytes: Raw PDF file bytes
            page_index: 0-indexed page number

        Returns:
            True if page needs OCR
        """
        try:
            pdf = pdfium.PdfDocument(pdf_bytes)
            if page_index < 0 or page_index >= len(pdf):
                logger.warning("Page index %d out of range", page_index)
                return True

            page = pdf[page_index]
            return self._page_needs_ocr(page)
        except Exception as e:
            logger.error("Failed to check page %d: %s", page_index, str(e))
            return True
