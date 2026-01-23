"""Unit tests for DoclingProcessor.

These tests use mock to avoid actual Docling processing in unit tests.
Integration tests will test actual document processing.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.ingestion.docling_processor import (
    DoclingProcessor,
    DocumentContent,
    DocumentProcessingError,
    PageContent,
)


class TestDoclingProcessorInit:
    """Tests for DoclingProcessor initialization."""

    def test_default_configuration(self):
        """Test default processor configuration."""
        processor = DoclingProcessor()
        assert processor.enable_ocr is True
        assert processor.enable_tables is True
        assert processor.max_pages == 100

    def test_custom_configuration(self):
        """Test custom processor configuration."""
        processor = DoclingProcessor(
            enable_ocr=False,
            enable_tables=False,
            max_pages=50,
        )
        assert processor.enable_ocr is False
        assert processor.enable_tables is False
        assert processor.max_pages == 50


class TestDoclingProcessorProcess:
    """Tests for DoclingProcessor.process method."""

    def test_file_not_found_raises_error(self):
        """Test that missing file raises DocumentProcessingError."""
        processor = DoclingProcessor()
        with pytest.raises(DocumentProcessingError) as exc_info:
            processor.process(Path("/nonexistent/file.pdf"))
        assert "File not found" in str(exc_info.value)

    @patch("src.ingestion.docling_processor.DocumentConverter")
    def test_successful_pdf_processing_with_page_text(
        self, mock_converter_class: MagicMock, tmp_path: Path
    ):
        """Test successful PDF processing extracts page-level text."""
        # Create a test file
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 test content")

        # Mock the converter and result
        mock_converter = MagicMock()
        mock_converter_class.return_value = mock_converter

        # Create mock page items with provenance
        mock_item1 = MagicMock()
        mock_item1.text = "Content on page 1"
        mock_prov1 = MagicMock()
        mock_prov1.page_no = 1
        mock_item1.prov = [mock_prov1]

        mock_item2 = MagicMock()
        mock_item2.text = "Content on page 2"
        mock_prov2 = MagicMock()
        mock_prov2.page_no = 2
        mock_item2.prov = [mock_prov2]

        mock_doc = MagicMock()
        mock_doc.export_to_markdown.return_value = (
            "# Test Document\n\nContent on page 1\n\nContent on page 2"
        )
        mock_doc.pages = {1: MagicMock(), 2: MagicMock()}  # 2 pages
        mock_doc.tables = []
        mock_doc.iterate_items.return_value = [(mock_item1, 0), (mock_item2, 0)]

        mock_result = MagicMock()
        mock_result.status.name = "SUCCESS"
        mock_result.document = mock_doc
        mock_result.errors = []

        mock_converter.convert.return_value = mock_result

        # Process the document
        processor = DoclingProcessor()
        result = processor.process(test_file)

        # Verify result
        assert isinstance(result, DocumentContent)
        assert result.text == "# Test Document\n\nContent on page 1\n\nContent on page 2"
        assert result.page_count == 2
        assert len(result.pages) == 2

        # CRITICAL: Verify page text is NOT empty (Blocker 1 fix)
        assert result.pages[0].page_number == 1
        assert result.pages[0].text == "Content on page 1"
        assert result.pages[1].page_number == 2
        assert result.pages[1].text == "Content on page 2"

        assert result.metadata["status"] == "SUCCESS"

    @patch("src.ingestion.docling_processor.DocumentConverter")
    def test_conversion_failure_raises_error(
        self, mock_converter_class: MagicMock, tmp_path: Path
    ):
        """Test that conversion failure raises DocumentProcessingError."""
        test_file = tmp_path / "bad.pdf"
        test_file.write_bytes(b"not a pdf")

        mock_converter = MagicMock()
        mock_converter_class.return_value = mock_converter

        mock_result = MagicMock()
        mock_result.status.name = "FAILURE"
        mock_result.errors = ["Invalid PDF format"]

        mock_converter.convert.return_value = mock_result

        processor = DoclingProcessor()
        with pytest.raises(DocumentProcessingError) as exc_info:
            processor.process(test_file)

        assert "conversion failed" in str(exc_info.value).lower()

    @patch("src.ingestion.docling_processor.DocumentConverter")
    def test_converter_exception_raises_error(
        self, mock_converter_class: MagicMock, tmp_path: Path
    ):
        """Test that converter exception is wrapped in DocumentProcessingError."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4")

        mock_converter = MagicMock()
        mock_converter_class.return_value = mock_converter
        mock_converter.convert.side_effect = RuntimeError("Memory error")

        processor = DoclingProcessor()
        with pytest.raises(DocumentProcessingError) as exc_info:
            processor.process(test_file)

        assert "Conversion failed" in str(exc_info.value)

    @patch("src.ingestion.docling_processor.DocumentConverter")
    def test_page_text_extraction_failure_graceful(
        self, mock_converter_class: MagicMock, tmp_path: Path
    ):
        """Test that page text extraction failure doesn't crash processing (INGEST-14)."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4")

        mock_converter = MagicMock()
        mock_converter_class.return_value = mock_converter

        # Mock document with pages but iterate_items raises exception
        mock_doc = MagicMock()
        mock_doc.export_to_markdown.return_value = "Full text"
        mock_doc.pages = {1: MagicMock()}
        mock_doc.tables = []
        mock_doc.iterate_items.side_effect = RuntimeError("Iteration failed")

        mock_result = MagicMock()
        mock_result.status.name = "SUCCESS"
        mock_result.document = mock_doc

        mock_converter.convert.return_value = mock_result

        processor = DoclingProcessor()
        # Should NOT raise - graceful degradation
        result = processor.process(test_file)

        assert result.page_count == 1
        assert len(result.pages) == 1
        # Page text will be empty due to failure, but processing completed
        assert result.pages[0].text == ""


class TestDoclingProcessorProcessBytes:
    """Tests for DoclingProcessor.process_bytes method."""

    @patch("src.ingestion.docling_processor.DocumentConverter")
    def test_process_bytes_creates_temp_file(self, mock_converter_class: MagicMock):
        """Test that process_bytes creates temp file with correct suffix."""
        mock_converter = MagicMock()
        mock_converter_class.return_value = mock_converter

        mock_doc = MagicMock()
        mock_doc.export_to_markdown.return_value = "Content"
        mock_doc.pages = {}
        mock_doc.tables = []
        mock_doc.iterate_items.return_value = []

        mock_result = MagicMock()
        mock_result.status.name = "SUCCESS"
        mock_result.document = mock_doc

        mock_converter.convert.return_value = mock_result

        processor = DoclingProcessor()
        result = processor.process_bytes(b"test data", "document.pdf")

        assert isinstance(result, DocumentContent)
        # Verify convert was called (temp file was created)
        mock_converter.convert.assert_called_once()


class TestPageContent:
    """Tests for PageContent model."""

    def test_page_content_creation(self):
        """Test creating PageContent with all fields."""
        page = PageContent(
            page_number=1,
            text="Page content",
            tables=[{"headers": ["A"], "rows": [["1"]]}],
        )
        assert page.page_number == 1
        assert page.text == "Page content"
        assert len(page.tables) == 1

    def test_page_content_defaults(self):
        """Test PageContent default values."""
        page = PageContent(page_number=1)
        assert page.text == ""
        assert page.tables == []


class TestDocumentContent:
    """Tests for DocumentContent model."""

    def test_document_content_creation(self):
        """Test creating DocumentContent."""
        content = DocumentContent(
            text="# Document",
            pages=[PageContent(page_number=1, text="Page 1 text")],
            page_count=1,
            tables=[],
            metadata={"status": "SUCCESS"},
        )
        assert content.text == "# Document"
        assert content.page_count == 1
        assert len(content.pages) == 1
        assert content.pages[0].text == "Page 1 text"

    def test_document_content_defaults(self):
        """Test DocumentContent default values."""
        content = DocumentContent(text="test", page_count=0)
        assert content.pages == []
        assert content.tables == []
        assert content.metadata == {}
