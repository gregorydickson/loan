"""Docling wrapper for document conversion with memory-safe patterns.

CRITICAL: Create a fresh DocumentConverter instance for each document to avoid
memory leaks (see GitHub issue #2209). Do NOT reuse converter instances.
"""

import tempfile
from pathlib import Path
from typing import Any

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions

# Docling imports
from docling.document_converter import DocumentConverter, PdfFormatOption
from pydantic import BaseModel, Field


class PageContent(BaseModel):
    """Content extracted from a single page."""

    page_number: int = Field(..., ge=1, description="1-indexed page number")
    text: str = Field(default="", description="Text content from this page")
    tables: list[dict[str, Any]] = Field(
        default_factory=list, description="Tables extracted from this page"
    )


class DocumentContent(BaseModel):
    """Complete document extraction result."""

    text: str = Field(..., description="Full document text as markdown")
    pages: list[PageContent] = Field(
        default_factory=list, description="Page-by-page content"
    )
    page_count: int = Field(..., ge=0, description="Total number of pages")
    tables: list[dict[str, Any]] = Field(
        default_factory=list, description="All tables from document"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Extraction metadata"
    )


class DocumentProcessingError(Exception):
    """Raised when document processing fails."""

    def __init__(self, message: str, details: str | None = None):
        self.message = message
        self.details = details
        super().__init__(message)


class DoclingProcessor:
    """Wrapper for Docling document conversion.

    IMPORTANT: This class creates a fresh DocumentConverter for each conversion
    to prevent memory leaks. Do NOT cache the converter instance.
    """

    def __init__(
        self,
        enable_ocr: bool = True,
        enable_tables: bool = True,
        max_pages: int = 100,
    ) -> None:
        """Initialize processor with configuration.

        Args:
            enable_ocr: Enable OCR for scanned/image documents
            enable_tables: Enable table structure extraction
            max_pages: Maximum pages to process (default 100, prevents hangs on large PDFs)
        """
        self.enable_ocr = enable_ocr
        self.enable_tables = enable_tables
        self.max_pages = max_pages

    def _create_converter(self) -> DocumentConverter:
        """Create a fresh converter instance (memory-safe pattern)."""
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = self.enable_ocr
        pipeline_options.do_table_structure = self.enable_tables

        format_options = {
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        }

        return DocumentConverter(format_options=format_options)

    def _extract_page_text(self, doc: Any, page_number: int) -> str:
        """Extract text content for a specific page.

        Docling's document model provides content through doc.pages which maps
        page numbers to page objects containing text items.

        Args:
            doc: Docling Document object
            page_number: 1-indexed page number

        Returns:
            Concatenated text from all items on the page
        """
        try:
            # Docling documents have iterate_items() that returns (item, level) tuples
            # Each item has a prov (provenance) with page_no
            page_texts: list[str] = []

            for item, _level in doc.iterate_items():
                # Check if item belongs to this page via provenance
                if hasattr(item, "prov") and item.prov:
                    for prov in item.prov:
                        if hasattr(prov, "page_no") and prov.page_no == page_number:
                            # Extract text from the item
                            if hasattr(item, "text") and item.text:
                                page_texts.append(item.text)
                            break

            return "\n".join(page_texts)
        except Exception:
            # Fallback: return empty string if page text extraction fails
            # This shouldn't crash the overall processing
            return ""

    def process(self, file_path: Path) -> DocumentContent:
        """Process a document file and extract structured content.

        Args:
            file_path: Path to the document file (PDF, DOCX, PNG, JPG)

        Returns:
            DocumentContent with text, pages, tables, and metadata

        Raises:
            DocumentProcessingError: If conversion fails
        """
        if not file_path.exists():
            raise DocumentProcessingError(f"File not found: {file_path}")

        # Create fresh converter to avoid memory leaks
        converter = self._create_converter()

        try:
            result = converter.convert(
                source=file_path,
                raises_on_error=False,
                max_num_pages=self.max_pages,
            )
        except Exception as e:
            raise DocumentProcessingError(
                f"Conversion failed for {file_path.name}",
                details=str(e),
            ) from e

        # Check for conversion errors
        if result.status.name == "FAILURE":
            error_details = (
                "; ".join(str(e) for e in result.errors) if result.errors else "Unknown error"
            )
            raise DocumentProcessingError(
                f"Document conversion failed: {file_path.name}",
                details=error_details,
            )

        doc = result.document

        # Extract page-level content
        pages: list[PageContent] = []
        all_tables: list[dict[str, Any]] = []

        # Get page count from document
        page_count = 0
        if hasattr(doc, "pages") and doc.pages:
            # doc.pages is a dict mapping page_no to Page objects
            page_count = len(doc.pages)

        # Extract text as markdown (preserves structure)
        try:
            full_text = doc.export_to_markdown()
        except Exception:
            full_text = ""

        # Build page content with ACTUAL page text (not empty strings!)
        # Docling page numbers are 1-indexed
        for page_no in range(1, page_count + 1):
            page_text = self._extract_page_text(doc, page_no)
            pages.append(
                PageContent(
                    page_number=page_no,
                    text=page_text,
                    tables=[],
                )
            )

        # Extract tables if available
        if hasattr(doc, "tables"):
            for table in doc.tables:
                table_data: dict[str, Any] = {
                    "rows": [],
                    "headers": [],
                }
                if hasattr(table, "data"):
                    table_data["rows"] = table.data
                all_tables.append(table_data)

        return DocumentContent(
            text=full_text,
            pages=pages,
            page_count=page_count,
            tables=all_tables,
            metadata={
                "status": result.status.name,
                "source_file": file_path.name,
            },
        )

    def process_bytes(
        self,
        data: bytes,
        filename: str,
    ) -> DocumentContent:
        """Process document from bytes (for uploaded files).

        Args:
            data: Raw file bytes
            filename: Original filename (used to determine file type)

        Returns:
            DocumentContent with extracted data
        """
        suffix = Path(filename).suffix or ".pdf"

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
            tmp.write(data)
            tmp.flush()
            return self.process(Path(tmp.name))
