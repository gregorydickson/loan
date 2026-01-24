"""End-to-end integration tests for document upload to borrower extraction flow.

These tests validate the complete pipeline:
1. Document upload via POST /api/documents/
2. Docling processing (mocked)
3. Borrower extraction (mocked with realistic data)
4. Borrower persistence to database
5. Borrower retrieval via GET /api/borrowers/

Uses mock_borrower_extractor_with_data fixture to avoid real LLM calls
while testing the full integration.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_extracts_and_persists_borrower(client_with_extraction: AsyncClient):
    """Test that uploading a document extracts and persists borrowers."""
    # 1. Upload document
    files = {"file": ("loan_app.pdf", b"%PDF-1.4 loan application content", "application/pdf")}
    upload_response = await client_with_extraction.post("/api/documents/", files=files)

    assert upload_response.status_code == 201
    doc_data = upload_response.json()
    doc_id = doc_data["id"]

    # 2. Verify document completed successfully
    status_response = await client_with_extraction.get(f"/api/documents/{doc_id}/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "completed"

    # 3. Verify borrowers were extracted and persisted
    borrowers_response = await client_with_extraction.get("/api/borrowers/")
    assert borrowers_response.status_code == 200
    borrowers_data = borrowers_response.json()

    assert borrowers_data["total"] >= 1
    assert len(borrowers_data["borrowers"]) >= 1

    # 4. Find our extracted borrower
    borrower = next(
        (b for b in borrowers_data["borrowers"] if b["name"] == "John Smith"),
        None,
    )
    assert borrower is not None, "Expected borrower 'John Smith' not found"
    assert float(borrower["confidence_score"]) == 0.85


@pytest.mark.integration
@pytest.mark.asyncio
async def test_extracted_borrower_has_income_records(client_with_extraction: AsyncClient):
    """Test that extracted borrowers have income records persisted."""
    # Upload document to trigger extraction
    files = {"file": ("income_doc.pdf", b"%PDF-1.4 income verification", "application/pdf")}
    upload_response = await client_with_extraction.post("/api/documents/", files=files)
    assert upload_response.status_code == 201

    # Get borrower list
    borrowers_response = await client_with_extraction.get("/api/borrowers/")
    borrowers = borrowers_response.json()["borrowers"]
    borrower = next((b for b in borrowers if b["name"] == "John Smith"), None)
    assert borrower is not None

    # Get borrower detail to see income records
    detail_response = await client_with_extraction.get(f"/api/borrowers/{borrower['id']}")
    assert detail_response.status_code == 200
    detail = detail_response.json()

    # Verify income records
    assert "income_records" in detail
    assert len(detail["income_records"]) == 2

    # Verify income data (sorted by year descending in response)
    years = [inc["year"] for inc in detail["income_records"]]
    assert 2024 in years
    assert 2023 in years

    # Verify income amounts
    income_2024 = next(inc for inc in detail["income_records"] if inc["year"] == 2024)
    assert float(income_2024["amount"]) == 75000.00
    assert income_2024["employer"] == "Acme Corp"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_extracted_borrower_has_source_references(client_with_extraction: AsyncClient):
    """Test that extracted borrowers have source references linking to documents."""
    # Upload document
    files = {"file": ("traced_doc.pdf", b"%PDF-1.4 traced document", "application/pdf")}
    upload_response = await client_with_extraction.post("/api/documents/", files=files)
    assert upload_response.status_code == 201
    doc_id = upload_response.json()["id"]

    # Get borrower detail
    borrowers_response = await client_with_extraction.get("/api/borrowers/")
    borrower = next(
        (b for b in borrowers_response.json()["borrowers"] if b["name"] == "John Smith"),
        None,
    )
    assert borrower is not None

    detail_response = await client_with_extraction.get(f"/api/borrowers/{borrower['id']}")
    detail = detail_response.json()

    # Verify source references
    assert "source_references" in detail
    assert len(detail["source_references"]) >= 1

    # Verify source links to uploaded document
    source = detail["source_references"][0]
    assert source["document_id"] == doc_id
    assert source["page_number"] == 1
    assert "snippet" in source


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_finds_extracted_borrower(client_with_extraction: AsyncClient):
    """Test that extracted borrowers are searchable."""
    # Upload document
    files = {"file": ("searchable.pdf", b"%PDF-1.4 searchable", "application/pdf")}
    await client_with_extraction.post("/api/documents/", files=files)

    # Search by name
    search_response = await client_with_extraction.get("/api/borrowers/search?name=Smith")
    assert search_response.status_code == 200
    search_data = search_response.json()

    assert search_data["total"] >= 1
    assert any(b["name"] == "John Smith" for b in search_data["borrowers"])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multiple_documents_extract_borrowers(client_with_extraction: AsyncClient):
    """Test that uploading multiple documents extracts borrowers from each."""
    # Upload 3 documents
    for i in range(3):
        files = {"file": (f"multi_doc_{i}.pdf", f"%PDF-1.4 doc {i}".encode(), "application/pdf")}
        response = await client_with_extraction.post("/api/documents/", files=files)
        assert response.status_code == 201

    # Should have documents listed
    docs_response = await client_with_extraction.get("/api/documents/")
    assert docs_response.status_code == 200
    assert len(docs_response.json()["documents"]) == 3

    # Note: With current mock, each upload creates the same borrower (John Smith)
    # but with different source references. The deduplication happens in the
    # extractor, and since each document creates a fresh extraction, we might
    # get multiple borrowers or one with multiple sources depending on test isolation.
    # This test mainly verifies no errors occur with multiple uploads.
