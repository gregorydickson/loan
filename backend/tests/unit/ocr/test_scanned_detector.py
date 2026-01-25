"""Unit tests for ScannedDocumentDetector."""

import pytest
from unittest.mock import MagicMock, patch

from src.ocr.scanned_detector import DetectionResult, ScannedDocumentDetector


class TestDetectionResult:
    """Tests for DetectionResult dataclass."""

    def test_detection_result_creation(self):
        """DetectionResult stores all fields correctly."""
        result = DetectionResult(
            needs_ocr=True,
            scanned_pages=[0, 2, 4],
            total_pages=5,
            scanned_ratio=0.6,
        )

        assert result.needs_ocr is True
        assert result.scanned_pages == [0, 2, 4]
        assert result.total_pages == 5
        assert result.scanned_ratio == 0.6

    def test_detection_result_empty_document(self):
        """DetectionResult handles empty document."""
        result = DetectionResult(
            needs_ocr=False,
            scanned_pages=[],
            total_pages=0,
            scanned_ratio=0.0,
        )

        assert result.needs_ocr is False
        assert len(result.scanned_pages) == 0


class TestScannedDocumentDetector:
    """Tests for ScannedDocumentDetector."""

    @pytest.fixture
    def detector(self):
        """Create detector with default thresholds."""
        return ScannedDocumentDetector()

    @pytest.fixture
    def custom_detector(self):
        """Create detector with custom thresholds."""
        return ScannedDocumentDetector(
            min_chars_threshold=100,
            scanned_ratio_threshold=0.3,
        )

    def test_init_default_thresholds(self, detector):
        """Default thresholds are set correctly."""
        assert detector.min_chars_threshold == 50
        assert detector.scanned_ratio_threshold == 0.5

    def test_init_custom_thresholds(self, custom_detector):
        """Custom thresholds are set correctly."""
        assert custom_detector.min_chars_threshold == 100
        assert custom_detector.scanned_ratio_threshold == 0.3

    def test_detect_empty_bytes(self, detector):
        """Empty bytes returns needs_ocr=False."""
        result = detector.detect(b"")

        assert result.needs_ocr is False
        assert result.scanned_pages == []
        assert result.total_pages == 0

    @patch("src.ocr.scanned_detector.pdfium.PdfDocument")
    def test_detect_native_pdf(self, mock_pdf_class, detector):
        """Native PDF with text layer returns needs_ocr=False."""
        # Mock a 3-page PDF with good text on all pages
        mock_pdf = MagicMock()
        mock_pdf.__len__ = MagicMock(return_value=3)

        # Create mock pages with text
        mock_pages = []
        for i in range(3):
            mock_page = MagicMock()
            mock_textpage = MagicMock()
            mock_textpage.get_text_bounded.return_value = "A" * 100  # Lots of text
            mock_page.get_textpage.return_value = mock_textpage
            mock_pages.append(mock_page)

        mock_pdf.__getitem__ = MagicMock(side_effect=lambda x: mock_pages[x])
        mock_pdf_class.return_value = mock_pdf

        result = detector.detect(b"fake pdf bytes")

        assert result.needs_ocr is False
        assert result.scanned_pages == []
        assert result.total_pages == 3
        assert result.scanned_ratio == 0.0

    @patch("src.ocr.scanned_detector.pdfium.PdfDocument")
    def test_detect_scanned_pdf(self, mock_pdf_class, detector):
        """Scanned PDF with no text returns needs_ocr=True."""
        # Mock a 3-page PDF with no text on any page
        mock_pdf = MagicMock()
        mock_pdf.__len__ = MagicMock(return_value=3)

        mock_pages = []
        for i in range(3):
            mock_page = MagicMock()
            mock_textpage = MagicMock()
            mock_textpage.get_text_bounded.return_value = ""  # No text
            mock_page.get_textpage.return_value = mock_textpage
            mock_pages.append(mock_page)

        mock_pdf.__getitem__ = MagicMock(side_effect=lambda x: mock_pages[x])
        mock_pdf_class.return_value = mock_pdf

        result = detector.detect(b"fake pdf bytes")

        assert result.needs_ocr is True
        assert result.scanned_pages == [0, 1, 2]
        assert result.total_pages == 3
        assert result.scanned_ratio == 1.0

    @patch("src.ocr.scanned_detector.pdfium.PdfDocument")
    def test_detect_mixed_pdf(self, mock_pdf_class, detector):
        """Mixed PDF with some scanned pages."""
        # Mock a 4-page PDF: pages 0,2 have text, pages 1,3 are scanned
        mock_pdf = MagicMock()
        mock_pdf.__len__ = MagicMock(return_value=4)

        def create_page(has_text):
            mock_page = MagicMock()
            mock_textpage = MagicMock()
            mock_textpage.get_text_bounded.return_value = "A" * 100 if has_text else ""
            mock_page.get_textpage.return_value = mock_textpage
            return mock_page

        mock_pages = [
            create_page(True),   # Page 0: native
            create_page(False),  # Page 1: scanned
            create_page(True),   # Page 2: native
            create_page(False),  # Page 3: scanned
        ]

        mock_pdf.__getitem__ = MagicMock(side_effect=lambda x: mock_pages[x])
        mock_pdf_class.return_value = mock_pdf

        result = detector.detect(b"fake pdf bytes")

        # 50% scanned = exactly at threshold, so needs_ocr=True
        assert result.needs_ocr is True
        assert result.scanned_pages == [1, 3]
        assert result.total_pages == 4
        assert result.scanned_ratio == 0.5

    @patch("src.ocr.scanned_detector.pdfium.PdfDocument")
    def test_detect_below_threshold(self, mock_pdf_class, detector):
        """PDF with scanned pages below threshold returns needs_ocr=False."""
        # Mock a 4-page PDF: 3 native, 1 scanned (25% < 50%)
        mock_pdf = MagicMock()
        mock_pdf.__len__ = MagicMock(return_value=4)

        def create_page(has_text):
            mock_page = MagicMock()
            mock_textpage = MagicMock()
            mock_textpage.get_text_bounded.return_value = "A" * 100 if has_text else ""
            mock_page.get_textpage.return_value = mock_textpage
            return mock_page

        mock_pages = [
            create_page(True),
            create_page(True),
            create_page(True),
            create_page(False),  # Only page 3 is scanned
        ]

        mock_pdf.__getitem__ = MagicMock(side_effect=lambda x: mock_pages[x])
        mock_pdf_class.return_value = mock_pdf

        result = detector.detect(b"fake pdf bytes")

        # 25% < 50% threshold
        assert result.needs_ocr is False
        assert result.scanned_pages == [3]
        assert result.total_pages == 4
        assert result.scanned_ratio == 0.25

    @patch("src.ocr.scanned_detector.pdfium.PdfDocument")
    def test_detect_pdf_parse_error(self, mock_pdf_class, detector):
        """PDF parse error returns needs_ocr=True (conservative)."""
        mock_pdf_class.side_effect = Exception("Invalid PDF")

        result = detector.detect(b"invalid bytes")

        assert result.needs_ocr is True
        assert result.scanned_ratio == 1.0

    @patch("src.ocr.scanned_detector.pdfium.PdfDocument")
    def test_detect_page_specific(self, mock_pdf_class, detector):
        """detect_page checks specific page."""
        mock_pdf = MagicMock()
        mock_pdf.__len__ = MagicMock(return_value=2)

        # Page 0 has text, page 1 is scanned
        mock_page0 = MagicMock()
        mock_textpage0 = MagicMock()
        mock_textpage0.get_text_bounded.return_value = "A" * 100
        mock_page0.get_textpage.return_value = mock_textpage0

        mock_page1 = MagicMock()
        mock_textpage1 = MagicMock()
        mock_textpage1.get_text_bounded.return_value = ""
        mock_page1.get_textpage.return_value = mock_textpage1

        mock_pdf.__getitem__ = MagicMock(side_effect=lambda x: [mock_page0, mock_page1][x])
        mock_pdf_class.return_value = mock_pdf

        assert detector.detect_page(b"fake pdf", 0) is False  # Native
        assert detector.detect_page(b"fake pdf", 1) is True   # Scanned

    @patch("src.ocr.scanned_detector.pdfium.PdfDocument")
    def test_detect_page_out_of_range(self, mock_pdf_class, detector):
        """detect_page returns True for out-of-range page (conservative)."""
        mock_pdf = MagicMock()
        mock_pdf.__len__ = MagicMock(return_value=2)
        mock_pdf_class.return_value = mock_pdf

        assert detector.detect_page(b"fake pdf", 5) is True
        assert detector.detect_page(b"fake pdf", -1) is True

    def test_threshold_boundary(self):
        """Threshold boundary: exactly at threshold triggers OCR."""
        detector = ScannedDocumentDetector(scanned_ratio_threshold=0.5)

        # 50% scanned should trigger OCR (>= threshold)
        with patch("src.ocr.scanned_detector.pdfium.PdfDocument") as mock_pdf_class:
            mock_pdf = MagicMock()
            mock_pdf.__len__ = MagicMock(return_value=2)

            # One scanned, one native = 50%
            def create_page(has_text):
                mock_page = MagicMock()
                mock_textpage = MagicMock()
                mock_textpage.get_text_bounded.return_value = "A" * 100 if has_text else ""
                mock_page.get_textpage.return_value = mock_textpage
                return mock_page

            mock_pages = [create_page(True), create_page(False)]
            mock_pdf.__getitem__ = MagicMock(side_effect=lambda x: mock_pages[x])
            mock_pdf_class.return_value = mock_pdf

            result = detector.detect(b"fake pdf")
            assert result.needs_ocr is True
            assert result.scanned_ratio == 0.5

    @patch("src.ocr.scanned_detector.pdfium.PdfDocument")
    def test_text_extraction_exception(self, mock_pdf_class, detector):
        """Text extraction exception assumes page is scanned."""
        mock_pdf = MagicMock()
        mock_pdf.__len__ = MagicMock(return_value=1)

        mock_page = MagicMock()
        mock_page.get_textpage.side_effect = Exception("Text extraction failed")

        mock_pdf.__getitem__ = MagicMock(return_value=mock_page)
        mock_pdf_class.return_value = mock_pdf

        result = detector.detect(b"fake pdf")

        assert result.needs_ocr is True
        assert result.scanned_pages == [0]

    @patch("src.ocr.scanned_detector.pdfium.PdfDocument")
    def test_detect_page_parse_error(self, mock_pdf_class, detector):
        """detect_page returns True on PDF parse error."""
        mock_pdf_class.side_effect = Exception("Parse failed")

        assert detector.detect_page(b"invalid", 0) is True

    @patch("src.ocr.scanned_detector.pdfium.PdfDocument")
    def test_custom_threshold_applied(self, mock_pdf_class, custom_detector):
        """Custom thresholds affect detection."""
        # With min_chars=100 and scanned_ratio=0.3
        mock_pdf = MagicMock()
        mock_pdf.__len__ = MagicMock(return_value=3)

        def create_page(char_count):
            mock_page = MagicMock()
            mock_textpage = MagicMock()
            mock_textpage.get_text_bounded.return_value = "A" * char_count
            mock_page.get_textpage.return_value = mock_textpage
            return mock_page

        # 50 chars < 100 threshold, so these pages are "scanned"
        mock_pages = [
            create_page(50),   # Below 100 threshold
            create_page(150),  # Above 100 threshold
            create_page(50),   # Below 100 threshold
        ]

        mock_pdf.__getitem__ = MagicMock(side_effect=lambda x: mock_pages[x])
        mock_pdf_class.return_value = mock_pdf

        result = custom_detector.detect(b"fake pdf")

        # 2/3 = 66.7% > 30% threshold
        assert result.needs_ocr is True
        assert result.scanned_pages == [0, 2]
        assert result.scanned_ratio == pytest.approx(2/3)

    @patch("src.ocr.scanned_detector.pdfium.PdfDocument")
    def test_empty_pdf_no_pages(self, mock_pdf_class, detector):
        """Empty PDF (0 pages) returns needs_ocr=False."""
        mock_pdf = MagicMock()
        mock_pdf.__len__ = MagicMock(return_value=0)
        mock_pdf_class.return_value = mock_pdf

        result = detector.detect(b"empty pdf")

        assert result.needs_ocr is False
        assert result.scanned_pages == []
        assert result.total_pages == 0
        assert result.scanned_ratio == 0.0
