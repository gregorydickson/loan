"""Integration tests for document deletion autoflush fix.

This module tests the fix for the IntegrityError that occurred when deleting
documents with borrowers while there were pending AccountNumber objects in
the SQLAlchemy session.

Bug: When re-uploading a duplicate file, the document service calls
repository.delete() to remove the existing document. This triggered
session.get(Borrower) which auto-flushed pending objects, causing
AccountNumber objects without borrower_id to violate NOT NULL constraint.

Fix: Wrapped session.get() in session.no_autoflush context manager to
prevent premature flush of pending objects.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_reupload_duplicate_with_borrowers_no_autoflush_error(
    client_with_extraction: AsyncClient,
):
    """Test that re-uploading duplicate file with borrowers doesn't cause autoflush error.

    This is a regression test for the IntegrityError:
    "null value in column 'borrower_id' of relation 'account_numbers'
     violates not-null constraint"

    The bug occurred because:
    1. Upload creates Document and Borrower with AccountNumbers
    2. Re-uploading same file (same hash) triggers delete of existing document
    3. Delete calls session.get(Borrower) which auto-flushes pending objects
    4. If there are pending AccountNumbers without borrower_id, flush fails

    The fix uses session.no_autoflush to prevent premature flush.
    """
    # Create PDF content with specific hash
    content = b"%PDF-1.4\ntest content for autoflush regression test"

    # 1. First upload - creates document with borrowers and account numbers
    files = {"file": ("borrower_doc.pdf", content, "application/pdf")}
    response1 = await client_with_extraction.post(
        "/api/documents/?method=docling&ocr=auto",
        files=files
    )
    assert response1.status_code == 201, f"First upload failed: {response1.json()}"
    doc1_id = response1.json()["id"]

    # Verify borrowers were created with account numbers
    borrowers_response = await client_with_extraction.get("/api/borrowers/")
    assert borrowers_response.status_code == 200
    borrowers_data = borrowers_response.json()
    borrowers = borrowers_data.get("borrowers", [])
    assert len(borrowers) >= 1, "Expected at least one borrower from extraction"

    # Verify account numbers exist
    borrower_id = borrowers[0]["id"]
    borrower_detail = await client_with_extraction.get(f"/api/borrowers/{borrower_id}")
    assert borrower_detail.status_code == 200
    borrower_data = borrower_detail.json()
    assert len(borrower_data["account_numbers"]) > 0, "Expected account numbers"

    # 2. Re-upload same file - this triggers the delete path that had the bug
    # The document service will:
    #   - Detect duplicate hash
    #   - Call repository.delete(existing.id)
    #   - session.get(Borrower) should NOT trigger autoflush
    files2 = {"file": ("borrower_doc.pdf", content, "application/pdf")}
    response2 = await client_with_extraction.post(
        "/api/documents/?method=docling&ocr=auto",
        files=files2
    )

    # Should succeed with 201, not fail with 500 IntegrityError
    assert response2.status_code == 201, (
        f"Re-upload failed with {response2.status_code}: {response2.json()}"
    )
    doc2_id = response2.json()["id"]

    # Should create new document (different ID)
    assert doc2_id != doc1_id, "Re-upload should create new document"

    # Old document should be deleted
    check_old = await client_with_extraction.get(f"/api/documents/{doc1_id}")
    assert check_old.status_code == 404, "Old document should be deleted"

    # New document should exist
    check_new = await client_with_extraction.get(f"/api/documents/{doc2_id}")
    assert check_new.status_code == 200, "New document should exist"

    # Borrowers should still exist (re-created from new document)
    borrowers_after = await client_with_extraction.get("/api/borrowers/")
    assert borrowers_after.status_code == 200
    borrowers_after_data = borrowers_after.json()
    assert len(borrowers_after_data.get("borrowers", [])) >= 1, "Borrowers should be re-created"


@pytest.mark.asyncio
async def test_delete_document_with_multiple_borrowers_and_accounts(
    client_with_three_borrowers: AsyncClient,
):
    """Test deleting document with multiple borrowers and account numbers.

    This tests the no_autoflush fix with a more complex scenario:
    - Multiple borrowers
    - Multiple account numbers per borrower
    - Multiple income records

    Ensures session.get() in delete loop doesn't trigger autoflush.
    """
    content = b"%PDF-1.4\ntest content for multi-borrower delete test"

    # Upload document that creates 3 borrowers
    files = {"file": ("multi_borrower.pdf", content, "application/pdf")}
    response = await client_with_three_borrowers.post(
        "/api/documents/?method=docling&ocr=auto",
        files=files
    )
    assert response.status_code == 201
    doc_id = response.json()["id"]

    # Verify multiple borrowers were created
    borrowers_response = await client_with_three_borrowers.get("/api/borrowers/")
    assert borrowers_response.status_code == 200
    borrowers_data = borrowers_response.json()
    borrowers = borrowers_data.get("borrowers", [])
    assert len(borrowers) == 3, "Expected 3 borrowers"

    # Each borrower should have account numbers
    for borrower in borrowers:
        detail = await client_with_three_borrowers.get(f"/api/borrowers/{borrower['id']}")
        assert detail.status_code == 200
        assert len(detail.json()["account_numbers"]) > 0

    # Delete the document - should cascade delete all borrowers and accounts
    # This exercises the loop: for borrower_id in borrower_ids
    delete_response = await client_with_three_borrowers.delete(
        f"/api/documents/{doc_id}"
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True

    # All borrowers should be deleted
    borrowers_after = await client_with_three_borrowers.get("/api/borrowers/")
    assert borrowers_after.status_code == 200
    borrowers_after_data = borrowers_after.json()
    assert len(borrowers_after_data.get("borrowers", [])) == 0, "All borrowers should be deleted"


@pytest.mark.asyncio
async def test_reupload_multiple_times_no_autoflush_error(
    client_with_extraction: AsyncClient,
):
    """Test multiple re-uploads of same file don't cause autoflush errors.

    This ensures the fix is robust across multiple delete/create cycles.
    """
    content = b"%PDF-1.4\ntest content for multiple reupload test"

    # Upload and re-upload same file 3 times
    doc_ids = []
    for i in range(3):
        files = {"file": (f"doc_{i}.pdf", content, "application/pdf")}
        response = await client_with_extraction.post(
            "/api/documents/?method=docling&ocr=auto",
            files=files
        )
        assert response.status_code == 201, (
            f"Upload {i+1} failed: {response.status_code}"
        )
        doc_ids.append(response.json()["id"])

    # Each upload should create new document
    assert len(set(doc_ids)) == 3, "Each upload should create unique document"

    # Only the last document should exist
    for i, doc_id in enumerate(doc_ids[:-1]):
        check = await client_with_extraction.get(f"/api/documents/{doc_id}")
        assert check.status_code == 404, f"Document {i+1} should be deleted"

    # Last document should exist
    check_last = await client_with_extraction.get(f"/api/documents/{doc_ids[-1]}")
    assert check_last.status_code == 200, "Last document should exist"


@pytest.mark.asyncio
async def test_direct_delete_with_borrowers_no_autoflush(
    client_with_extraction: AsyncClient,
):
    """Test direct document deletion (not via re-upload) with borrowers.

    This tests the delete path when called directly via DELETE endpoint,
    ensuring no_autoflush works in this scenario too.
    """
    content = b"%PDF-1.4\ntest content for direct delete test"

    # Upload document with borrowers
    files = {"file": ("direct_delete.pdf", content, "application/pdf")}
    response = await client_with_extraction.post(
        "/api/documents/?method=docling&ocr=auto",
        files=files
    )
    assert response.status_code == 201
    doc_id = response.json()["id"]

    # Verify borrowers exist
    borrowers_before = await client_with_extraction.get("/api/borrowers/")
    borrowers_before_data = borrowers_before.json()
    assert len(borrowers_before_data.get("borrowers", [])) >= 1

    # Delete document directly
    delete_response = await client_with_extraction.delete(f"/api/documents/{doc_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True

    # Document should be deleted
    check_doc = await client_with_extraction.get(f"/api/documents/{doc_id}")
    assert check_doc.status_code == 404

    # Borrowers should be deleted (cascade)
    borrowers_after = await client_with_extraction.get("/api/borrowers/")
    borrowers_after_data = borrowers_after.json()
    assert len(borrowers_after_data.get("borrowers", [])) == 0


@pytest.mark.asyncio
async def test_delete_empty_document_no_borrowers(client: AsyncClient):
    """Test deleting document without borrowers (baseline case).

    This should work regardless of autoflush fix, but verifies basic delete.
    """
    content = b"%PDF-1.4\ntest content without borrowers"

    # Upload document (mock extractor returns no borrowers)
    files = {"file": ("no_borrowers.pdf", content, "application/pdf")}
    response = await client.post("/api/documents/", files=files)
    assert response.status_code == 201
    doc_id = response.json()["id"]

    # Delete should succeed
    delete_response = await client.delete(f"/api/documents/{doc_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True

    # Document should be deleted
    check_doc = await client.get(f"/api/documents/{doc_id}")
    assert check_doc.status_code == 404
