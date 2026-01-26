"""Test for delete and re-upload scenario.

Tests that re-uploading a file (whether deleted or not) always succeeds
by overwriting the existing document.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_delete_and_reupload_same_file(client: AsyncClient):
    """Test that deleting a document allows re-uploading the same file."""
    # Create a PDF with specific content
    content = b"%PDF-1.4\ntest content for delete-reupload test"

    # 1. Upload document
    files = {"file": ("test.pdf", content, "application/pdf")}
    response1 = await client.post("/api/documents/", files=files)
    assert response1.status_code == 201
    doc_id = response1.json()["id"]

    # 2. Delete the document
    delete_response = await client.delete(f"/api/documents/{doc_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True

    # 3. Re-upload the same file - should succeed, not return 409
    files2 = {"file": ("test.pdf", content, "application/pdf")}
    response2 = await client.post("/api/documents/", files=files2)

    # This should succeed with 201, not fail with 409
    assert response2.status_code == 201, f"Expected 201, got {response2.status_code}: {response2.json()}"

    # Should create a new document with different ID
    new_doc_id = response2.json()["id"]
    assert new_doc_id != doc_id
