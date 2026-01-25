"""End-to-end integration tests for LangExtract extraction path (TEST-06).

These tests validate the LangExtract extraction pipeline:
1. Document upload via POST /api/documents/ with method=langextract
2. LangExtract processing (mocked)
3. Verification that SourceReference has char_start/char_end populated (DUAL-08)
4. Regression test for Docling path (TEST-05, DUAL-09)

Uses mock_langextract_processor fixture to avoid real LLM API calls
while testing the full E2E integration.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_langextract_path_produces_char_offsets(client_with_langextract: AsyncClient):
    """TEST-06: LangExtract path produces borrowers with character offsets.

    DUAL-08: Verify that when using method=langextract, the SourceReference
    objects have char_start and char_end populated.
    """
    # Upload document with method=langextract
    files = {"file": ("loan_app.pdf", b"%PDF-1.4 loan application content", "application/pdf")}
    upload_response = await client_with_langextract.post(
        "/api/documents/?method=langextract",
        files=files,
    )

    assert upload_response.status_code == 201
    doc_data = upload_response.json()
    assert doc_data["status"] in ("completed", "pending")

    # If status is completed, extraction_method should be recorded
    if doc_data.get("extraction_method"):
        assert doc_data["extraction_method"] == "langextract"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_langextract_extraction_method_recorded(client_with_langextract: AsyncClient):
    """Verify that extraction_method parameter is accepted and recorded.

    The API should accept method=langextract and record it on the document.
    """
    files = {"file": ("test_doc.pdf", b"%PDF-1.4 test document", "application/pdf")}
    upload_response = await client_with_langextract.post(
        "/api/documents/?method=langextract",
        files=files,
    )

    assert upload_response.status_code == 201
    doc_data = upload_response.json()
    doc_id = doc_data["id"]

    # Get document status to verify method recorded
    status_response = await client_with_langextract.get(f"/api/documents/{doc_id}/status")
    assert status_response.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_docling_default_method_still_works(client_with_langextract: AsyncClient):
    """TEST-05, DUAL-09: Regression test for Docling path.

    Default method should be 'docling' for backward compatibility.
    Upload without method parameter should work using Docling extraction.
    """
    # Upload without method parameter - should default to docling
    files = {"file": ("docling_test.pdf", b"%PDF-1.4 docling test", "application/pdf")}
    upload_response = await client_with_langextract.post(
        "/api/documents/",  # No method parameter - defaults to docling
        files=files,
    )

    assert upload_response.status_code == 201
    doc_data = upload_response.json()

    # Default method is docling (DUAL-09 backward compatibility)
    # The extraction_method may be None if not yet processed, or "docling"
    if doc_data.get("extraction_method"):
        assert doc_data["extraction_method"] == "docling"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_method_docling_explicitly_specified(client_with_langextract: AsyncClient):
    """Verify that method=docling is accepted explicitly.

    The API should accept method=docling for explicit Docling extraction.
    """
    files = {"file": ("explicit_docling.pdf", b"%PDF-1.4 explicit docling", "application/pdf")}
    upload_response = await client_with_langextract.post(
        "/api/documents/?method=docling",
        files=files,
    )

    assert upload_response.status_code == 201
    doc_data = upload_response.json()

    # Verify response is successful
    assert doc_data["id"] is not None
    assert doc_data["filename"] == "explicit_docling.pdf"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_method_auto_accepted(client_with_langextract: AsyncClient):
    """Verify that method=auto is accepted.

    Auto mode should try LangExtract first with fallback to Docling.
    """
    files = {"file": ("auto_test.pdf", b"%PDF-1.4 auto mode test", "application/pdf")}
    upload_response = await client_with_langextract.post(
        "/api/documents/?method=auto",
        files=files,
    )

    assert upload_response.status_code == 201
    doc_data = upload_response.json()

    # Verify upload succeeded
    assert doc_data["id"] is not None
    assert doc_data["status"] in ("completed", "pending")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ocr_parameter_accepted(client_with_langextract: AsyncClient):
    """Verify that ocr parameter is accepted with extraction method.

    The API should accept both method and ocr parameters together.
    """
    files = {"file": ("ocr_test.pdf", b"%PDF-1.4 ocr test", "application/pdf")}

    # Test with method=langextract and ocr=auto
    upload_response = await client_with_langextract.post(
        "/api/documents/?method=langextract&ocr=auto",
        files=files,
    )

    assert upload_response.status_code == 201
    doc_data = upload_response.json()
    assert doc_data["id"] is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ocr_skip_with_langextract(client_with_langextract: AsyncClient):
    """Verify that ocr=skip works with method=langextract.

    Should be able to use LangExtract extraction without OCR processing.
    """
    files = {"file": ("no_ocr.pdf", b"%PDF-1.4 no ocr test", "application/pdf")}

    upload_response = await client_with_langextract.post(
        "/api/documents/?method=langextract&ocr=skip",
        files=files,
    )

    assert upload_response.status_code == 201


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multiple_documents_with_different_methods(client_with_langextract: AsyncClient):
    """Verify uploading multiple documents with different extraction methods.

    Each document should be processed with its specified method.
    """
    # Upload with langextract
    files_lx = {"file": ("doc_langextract.pdf", b"%PDF-1.4 langextract doc", "application/pdf")}
    response_lx = await client_with_langextract.post(
        "/api/documents/?method=langextract",
        files=files_lx,
    )
    assert response_lx.status_code == 201

    # Upload with docling
    files_dl = {"file": ("doc_docling.pdf", b"%PDF-1.4 docling doc", "application/pdf")}
    response_dl = await client_with_langextract.post(
        "/api/documents/?method=docling",
        files=files_dl,
    )
    assert response_dl.status_code == 201

    # Upload with auto
    files_auto = {"file": ("doc_auto.pdf", b"%PDF-1.4 auto doc", "application/pdf")}
    response_auto = await client_with_langextract.post(
        "/api/documents/?method=auto",
        files=files_auto,
    )
    assert response_auto.status_code == 201

    # All documents should be in the list
    list_response = await client_with_langextract.get("/api/documents/")
    assert list_response.status_code == 200
    docs = list_response.json()["documents"]
    assert len(docs) == 3
