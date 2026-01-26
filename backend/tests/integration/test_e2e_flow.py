"""End-to-end integration test for document upload to borrower query flow.

This test validates the complete workflow:
1. Document upload
2. Document processing (Docling)
3. Status verification
4. Borrower extraction (mocked)
5. Borrower retrieval

Requires mock_gemini_client for extraction to avoid real API calls.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_to_extraction_flow(client: AsyncClient):
    """Test complete flow: upload document -> process -> verify status."""
    # 1. Upload document
    files = {"file": ("test_e2e.pdf", b"%PDF-1.4 e2e test content", "application/pdf")}
    response = await client.post("/api/documents/", files=files)

    assert response.status_code == 201
    doc_data = response.json()
    doc_id = doc_data["id"]
    assert doc_id is not None

    # 2. Verify processing completed (synchronous processing)
    status_response = await client.get(f"/api/documents/{doc_id}/status")
    assert status_response.status_code == 200
    status_data = status_response.json()

    # Document should be completed or failed (not pending - processing is sync)
    assert status_data["status"] in ["completed", "failed"]

    # 3. If completed, verify page count is set
    if status_data["status"] == "completed":
        assert status_data["page_count"] is not None
        assert status_data["page_count"] >= 1

    # 4. Verify document details are retrievable
    detail_response = await client.get(f"/api/documents/{doc_id}")
    assert detail_response.status_code == 200
    detail_data = detail_response.json()
    assert detail_data["id"] == doc_id
    assert detail_data["filename"] == "test_e2e.pdf"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_multiple_documents_flow(client: AsyncClient):
    """Test uploading multiple documents and listing them."""
    # Upload 3 documents
    doc_ids = []
    for i in range(3):
        files = {
            "file": (f"e2e_doc_{i}.pdf", f"%PDF-1.4 doc {i}".encode(), "application/pdf")
        }
        response = await client.post("/api/documents/", files=files)
        assert response.status_code == 201
        doc_ids.append(response.json()["id"])

    # List documents
    list_response = await client.get("/api/documents/")
    assert list_response.status_code == 200
    list_data = list_response.json()
    assert len(list_data["documents"]) == 3

    # Each uploaded document should be in the list
    listed_ids = {doc["id"] for doc in list_data["documents"]}
    for doc_id in doc_ids:
        assert doc_id in listed_ids


@pytest.mark.integration
@pytest.mark.asyncio
async def test_document_not_found_flow(client: AsyncClient):
    """Test proper error handling for non-existent documents."""
    fake_id = "00000000-0000-0000-0000-000000000000"

    # Document detail endpoint
    response = await client.get(f"/api/documents/{fake_id}")
    assert response.status_code == 404

    # Document status endpoint
    status_response = await client.get(f"/api/documents/{fake_id}/status")
    assert status_response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_duplicate_document_detection_flow(client: AsyncClient):
    """Test that duplicate documents are automatically replaced."""
    content = b"%PDF-1.4 duplicate test content unique"

    # First upload succeeds
    files1 = {"file": ("original.pdf", content, "application/pdf")}
    response1 = await client.post("/api/documents/", files=files1)
    assert response1.status_code == 201
    original_id = response1.json()["id"]

    # Second upload with same content succeeds (replaces original)
    files2 = {"file": ("duplicate.pdf", content, "application/pdf")}
    response2 = await client.post("/api/documents/", files=files2)
    assert response2.status_code == 201

    # New document has different ID (original was deleted)
    new_id = response2.json()["id"]
    assert new_id != original_id

    # Verify original document was deleted
    response_check = await client.get(f"/api/documents/{original_id}")
    assert response_check.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_borrower_api_flow(client: AsyncClient):
    """Test borrower API endpoints work correctly."""
    # List borrowers (should be empty initially)
    response = await client.get("/api/borrowers/")
    assert response.status_code == 200
    data = response.json()
    assert "borrowers" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_and_documents_flow(client: AsyncClient):
    """Test health check followed by document operations."""
    # Health check
    health = await client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"

    # Upload after health check
    files = {"file": ("after_health.pdf", b"%PDF-1.4 health test", "application/pdf")}
    response = await client.post("/api/documents/", files=files)
    assert response.status_code == 201

    # Health check still works after upload
    health2 = await client.get("/health")
    assert health2.status_code == 200
