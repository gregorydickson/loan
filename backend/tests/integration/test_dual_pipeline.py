"""Integration tests for dual pipeline extraction.

DUAL-08: LangExtract path populates character offsets, Docling path leaves null

These tests verify the character offset behavior for each extraction pipeline:
- LangExtract: Should populate char_start/char_end in SourceReference
- Docling: May leave char_start/char_end as None (page-level references)
"""

import pytest
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

from src.extraction.extraction_router import ExtractionRouter
from src.extraction.extractor import BorrowerExtractor, ExtractionResult
from src.extraction.langextract_processor import LangExtractProcessor, LangExtractResult
from src.extraction.complexity_classifier import ComplexityAssessment, ComplexityLevel
from src.ingestion.docling_processor import DocumentContent, PageContent
from src.models.borrower import Address, BorrowerRecord, IncomeRecord
from src.models.document import SourceReference


@pytest.fixture
def sample_document() -> DocumentContent:
    """Create a sample DocumentContent for testing extraction."""
    return DocumentContent(
        text="""
# Loan Application

## Borrower Information

Name: John Smith
SSN: 123-45-6789
Address: 123 Main St, Austin, TX 78701

## Income Verification

Employer: Acme Corp
Annual Salary: $75,000
Year: 2024
        """,
        pages=[
            PageContent(
                page_number=1,
                text="Loan Application - Borrower Information - John Smith",
                tables=[],
            )
        ],
        page_count=1,
        tables=[],
        metadata={"status": "SUCCESS"},
    )


@pytest.fixture
def mock_langextract_result() -> LangExtractResult:
    """Create a mock LangExtractResult WITH character offsets (DUAL-08).

    LangExtract results SHOULD have char_start/char_end populated.
    """
    doc_id = uuid4()
    return LangExtractResult(
        borrowers=[
            BorrowerRecord(
                id=uuid4(),
                name="John Smith",
                ssn="123-45-6789",
                address=Address(
                    street="123 Main St",
                    city="Austin",
                    state="TX",
                    zip_code="78701",
                ),
                income_history=[
                    IncomeRecord(
                        amount=Decimal("75000.00"),
                        period="annual",
                        year=2024,
                        source_type="employment",
                        employer="Acme Corp",
                    )
                ],
                account_numbers=[],
                loan_numbers=[],
                sources=[
                    SourceReference(
                        document_id=doc_id,
                        document_name="test.pdf",
                        page_number=1,
                        snippet="Name: John Smith",
                        char_start=45,  # LangExtract populates these
                        char_end=61,
                    )
                ],
                confidence_score=0.9,
            )
        ],
        raw_extractions=None,
        alignment_warnings=[],
    )


@pytest.fixture
def mock_docling_result() -> ExtractionResult:
    """Create a mock ExtractionResult WITHOUT character offsets.

    Docling results may NOT have char_start/char_end populated
    (page-level references only).
    """
    doc_id = uuid4()
    return ExtractionResult(
        borrowers=[
            BorrowerRecord(
                id=uuid4(),
                name="John Smith",
                ssn="123-45-6789",
                address=Address(
                    street="123 Main St",
                    city="Austin",
                    state="TX",
                    zip_code="78701",
                ),
                income_history=[
                    IncomeRecord(
                        amount=Decimal("75000.00"),
                        period="annual",
                        year=2024,
                        source_type="employment",
                        employer="Acme Corp",
                    )
                ],
                account_numbers=[],
                loan_numbers=[],
                sources=[
                    SourceReference(
                        document_id=doc_id,
                        document_name="test.pdf",
                        page_number=1,
                        snippet="John Smith, SSN: 123-45-6789, employed at Acme Corp",
                        char_start=None,  # Docling doesn't populate these
                        char_end=None,
                    )
                ],
                confidence_score=0.85,
            )
        ],
        complexity=ComplexityAssessment(
            level=ComplexityLevel.STANDARD,
            reasons=["Test document"],
            page_count=1,
            estimated_borrowers=1,
            has_handwritten=False,
            has_poor_quality=False,
        ),
        chunks_processed=1,
        total_tokens=100,
        validation_errors=[],
        consistency_warnings=[],
    )


class TestDualPipelineCharOffsets:
    """Test character offset behavior for dual pipeline (DUAL-08)."""

    def test_langextract_populates_char_offsets(
        self, sample_document: DocumentContent, mock_langextract_result: LangExtractResult
    ):
        """DUAL-08: LangExtract path populates character offsets.

        Verifies that when using LangExtract, the SourceReference
        objects have char_start and char_end populated.
        """
        # Mock LangExtractProcessor to return our mock result
        mock_langextract = MagicMock(spec=LangExtractProcessor)
        mock_langextract.extract = MagicMock(return_value=mock_langextract_result)

        # Mock BorrowerExtractor (won't be used for langextract method)
        mock_docling = MagicMock(spec=BorrowerExtractor)

        router = ExtractionRouter(
            langextract_processor=mock_langextract,
            docling_extractor=mock_docling,
        )

        # Extract using langextract method
        result = router.extract(
            document=sample_document,
            document_id=uuid4(),
            document_name="test.pdf",
            method="langextract",
        )

        # Verify result is LangExtractResult
        assert isinstance(result, LangExtractResult)
        assert len(result.borrowers) == 1

        # DUAL-08: LangExtract SHOULD populate char offsets
        borrower = result.borrowers[0]
        assert len(borrower.sources) > 0
        source = borrower.sources[0]

        # Verify character offsets are populated
        assert source.char_start is not None, (
            "LangExtract should populate char_start (DUAL-08)"
        )
        assert source.char_end is not None, (
            "LangExtract should populate char_end (DUAL-08)"
        )
        assert source.char_start < source.char_end, (
            "char_start should be less than char_end"
        )

    def test_docling_leaves_char_offsets_null(
        self, sample_document: DocumentContent, mock_docling_result: ExtractionResult
    ):
        """DUAL-08: Docling path leaves character offsets null (expected).

        Verifies that when using Docling, the SourceReference
        objects may have char_start and char_end as None.
        This is expected behavior - Docling provides page-level references.
        """
        # Mock LangExtractProcessor (won't be used for docling method)
        mock_langextract = MagicMock(spec=LangExtractProcessor)

        # Mock BorrowerExtractor to return our mock result
        mock_docling = MagicMock(spec=BorrowerExtractor)
        mock_docling.extract = MagicMock(return_value=mock_docling_result)

        router = ExtractionRouter(
            langextract_processor=mock_langextract,
            docling_extractor=mock_docling,
        )

        # Extract using docling method
        result = router.extract(
            document=sample_document,
            document_id=uuid4(),
            document_name="test.pdf",
            method="docling",
        )

        # Verify result is ExtractionResult
        assert isinstance(result, ExtractionResult)
        assert len(result.borrowers) == 1

        # Document that Docling doesn't populate char offsets (expected)
        borrower = result.borrowers[0]
        assert len(borrower.sources) > 0
        source = borrower.sources[0]

        # Docling doesn't populate char offsets - this is expected
        # We're documenting behavior, not asserting it must be None
        # (some documents might have offsets added later)
        if source.char_start is None:
            assert source.char_end is None, (
                "If char_start is None, char_end should also be None"
            )

    def test_auto_mode_tries_langextract_first(
        self, sample_document: DocumentContent, mock_langextract_result: LangExtractResult
    ):
        """Auto mode tries LangExtract first, falls back to Docling on failure.

        When using method='auto', ExtractionRouter should:
        1. Try LangExtract first
        2. If LangExtract succeeds, return LangExtractResult with char offsets
        """
        mock_langextract = MagicMock(spec=LangExtractProcessor)
        mock_langextract.extract = MagicMock(return_value=mock_langextract_result)

        mock_docling = MagicMock(spec=BorrowerExtractor)

        router = ExtractionRouter(
            langextract_processor=mock_langextract,
            docling_extractor=mock_docling,
        )

        # Extract using auto method
        result = router.extract(
            document=sample_document,
            document_id=uuid4(),
            document_name="test.pdf",
            method="auto",
        )

        # Should try LangExtract
        mock_langextract.extract.assert_called_once()

        # Verify char offsets are populated (from LangExtract)
        borrower = result.borrowers[0]
        source = borrower.sources[0]
        assert source.char_start is not None, "Auto mode should use LangExtract (DUAL-08)"
        assert source.char_end is not None, "Auto mode should use LangExtract (DUAL-08)"


class TestExtractionRouterMethodSelection:
    """Test ExtractionRouter method selection behavior."""

    def test_router_selects_langextract_when_specified(
        self, sample_document: DocumentContent
    ):
        """Router uses LangExtract when method='langextract'."""
        mock_langextract = MagicMock(spec=LangExtractProcessor)
        mock_langextract.extract = MagicMock(
            return_value=LangExtractResult(borrowers=[], alignment_warnings=[])
        )

        mock_docling = MagicMock(spec=BorrowerExtractor)

        router = ExtractionRouter(
            langextract_processor=mock_langextract,
            docling_extractor=mock_docling,
        )

        router.extract(
            document=sample_document,
            document_id=uuid4(),
            document_name="test.pdf",
            method="langextract",
        )

        mock_langextract.extract.assert_called_once()
        mock_docling.extract.assert_not_called()

    def test_router_selects_docling_when_specified(
        self, sample_document: DocumentContent, mock_docling_result: ExtractionResult
    ):
        """Router uses Docling when method='docling'."""
        mock_langextract = MagicMock(spec=LangExtractProcessor)

        mock_docling = MagicMock(spec=BorrowerExtractor)
        mock_docling.extract = MagicMock(return_value=mock_docling_result)

        router = ExtractionRouter(
            langextract_processor=mock_langextract,
            docling_extractor=mock_docling,
        )

        router.extract(
            document=sample_document,
            document_id=uuid4(),
            document_name="test.pdf",
            method="docling",
        )

        mock_docling.extract.assert_called_once()
        mock_langextract.extract.assert_not_called()

    def test_router_falls_back_on_langextract_failure(
        self, sample_document: DocumentContent, mock_docling_result: ExtractionResult
    ):
        """Router falls back to Docling when LangExtract fails in auto mode."""
        mock_langextract = MagicMock(spec=LangExtractProcessor)
        mock_langextract.extract = MagicMock(side_effect=Exception("LangExtract failed"))

        mock_docling = MagicMock(spec=BorrowerExtractor)
        mock_docling.extract = MagicMock(return_value=mock_docling_result)

        router = ExtractionRouter(
            langextract_processor=mock_langextract,
            docling_extractor=mock_docling,
        )

        # Auto mode should fall back to Docling
        result = router.extract(
            document=sample_document,
            document_id=uuid4(),
            document_name="test.pdf",
            method="auto",
        )

        # Both should be called (LangExtract tried, then Docling fallback)
        mock_langextract.extract.assert_called()
        mock_docling.extract.assert_called_once()

        # Result should be from Docling
        assert isinstance(result, ExtractionResult)
