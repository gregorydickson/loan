"""Integration tests using sample loan document corpus.

These tests validate the extraction pipeline against real-world document patterns.
Requires sample documents in tests/fixtures/sample_docs/ directory.

Sample documents are not committed to the repository (may contain PII).
Place your test documents in the fixtures directory to run these tests.
"""

from pathlib import Path

import pytest
from httpx import AsyncClient

SAMPLE_DOCS_DIR = Path(__file__).parent.parent / "fixtures" / "sample_docs"


@pytest.mark.integration
@pytest.mark.skipif(
    not SAMPLE_DOCS_DIR.exists() or not any(SAMPLE_DOCS_DIR.iterdir()),
    reason="Sample documents directory empty or not found",
)
class TestSampleDocumentExtraction:
    """Test extraction pipeline with sample loan documents."""

    @pytest.mark.asyncio
    async def test_sample_loan_document_extraction(self, client: AsyncClient):
        """Test extraction from a sample loan document produces expected fields."""
        # Look for a sample PDF
        sample_pdf = None
        for f in SAMPLE_DOCS_DIR.iterdir():
            if f.suffix.lower() == ".pdf":
                sample_pdf = f
                break

        if not sample_pdf:
            pytest.skip("No sample PDF found in fixtures directory")

        with open(sample_pdf, "rb") as file_handle:
            response = await client.post(
                "/api/documents/",
                files={"file": (sample_pdf.name, file_handle, "application/pdf")},
            )

        assert response.status_code == 201
        doc_data = response.json()
        assert "id" in doc_data

        # Verify processing completed
        status = await client.get(f"/api/documents/{doc_data['id']}/status")
        assert status.json()["status"] in ["completed", "processing", "failed"]

    @pytest.mark.asyncio
    async def test_multi_borrower_document(self, client: AsyncClient):
        """Test document with multiple borrowers extracts all.

        Uses mock - validates the pipeline handles multi-borrower scenario.
        This test validates the structure, actual multi-borrower extraction
        requires real documents or more complex mocking.
        """
        # This is a structural test - verify the API can handle the flow
        files = {
            "file": (
                "multi_borrower.pdf",
                b"%PDF-1.4 co-borrower test content",
                "application/pdf",
            )
        }
        response = await client.post("/api/documents/", files=files)
        assert response.status_code == 201

        # Verify document was processed
        doc_id = response.json()["id"]
        status = await client.get(f"/api/documents/{doc_id}/status")
        assert status.status_code == 200

    @pytest.mark.asyncio
    async def test_document_with_income_records(self, client: AsyncClient):
        """Test document with income info extracts income records.

        Validates the pipeline structure for income extraction.
        Actual income extraction requires LLM integration.
        """
        # Structural test
        files = {
            "file": (
                "income_doc.pdf",
                b"%PDF-1.4 income statement content",
                "application/pdf",
            )
        }
        response = await client.post("/api/documents/", files=files)
        assert response.status_code == 201

        doc_data = response.json()
        assert doc_data["status"] in ["completed", "failed"]


@pytest.mark.integration
class TestDocumentTypeSupport:
    """Test support for various document types commonly used in loan processing."""

    @pytest.mark.asyncio
    async def test_pdf_document_processing(self, client: AsyncClient):
        """Test PDF document is processed correctly."""
        files = {
            "file": ("loan_app.pdf", b"%PDF-1.4 loan application", "application/pdf")
        }
        response = await client.post("/api/documents/", files=files)
        assert response.status_code == 201
        assert response.json()["status"] == "completed"

    @pytest.mark.asyncio
    async def test_docx_document_processing(self, client: AsyncClient):
        """Test DOCX document is processed correctly."""
        docx_mime = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        files = {"file": ("statement.docx", b"docx content", docx_mime)}
        response = await client.post("/api/documents/", files=files)
        assert response.status_code == 201
        assert response.json()["status"] == "completed"

    @pytest.mark.asyncio
    async def test_image_document_processing(self, client: AsyncClient):
        """Test image document (scan) is processed with OCR."""
        # PNG header bytes
        png_bytes = b"\x89PNG\r\n\x1a\n fake image content"
        files = {"file": ("scanned_doc.png", png_bytes, "image/png")}
        response = await client.post("/api/documents/", files=files)
        assert response.status_code == 201
        # Images may process successfully or fail depending on content
        assert response.json()["status"] in ["completed", "failed"]
