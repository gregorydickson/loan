"""Tests for BorrowerExtractor orchestration pipeline.

Tests cover:
- Simple document extraction
- Model routing (Flash vs Pro)
- Chunking for large documents
- Source attribution
- Deduplication integration
- Validation error tracking
- Confidence score calculation
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.extraction.chunker import DocumentChunker, TextChunk
from src.extraction.complexity_classifier import (
    ComplexityAssessment,
    ComplexityClassifier,
    ComplexityLevel,
)
from src.extraction.confidence import ConfidenceCalculator
from src.extraction.deduplication import BorrowerDeduplicator
from src.extraction.extractor import BorrowerExtractor, ExtractionResult
from src.extraction.llm_client import GeminiClient, LLMResponse
from src.extraction.schemas import (
    BorrowerExtractionResult,
    ExtractedAddress,
    ExtractedBorrower,
    ExtractedIncome,
)
from src.extraction.validation import FieldValidator
from src.ingestion.docling_processor import DocumentContent, PageContent


@pytest.fixture
def mock_llm_client() -> MagicMock:
    """Create a mock GeminiClient."""
    return MagicMock(spec=GeminiClient)


@pytest.fixture
def mock_classifier() -> MagicMock:
    """Create a mock ComplexityClassifier."""
    classifier = MagicMock(spec=ComplexityClassifier)
    classifier.classify.return_value = ComplexityAssessment(
        level=ComplexityLevel.STANDARD,
        reasons=["Standard single-borrower document"],
        page_count=1,
        estimated_borrowers=1,
        has_handwritten=False,
        has_poor_quality=False,
    )
    return classifier


@pytest.fixture
def mock_chunker() -> MagicMock:
    """Create a mock DocumentChunker that returns document as single chunk."""
    chunker = MagicMock(spec=DocumentChunker)
    chunker.chunk.return_value = [
        TextChunk(
            text="Sample document text",
            start_char=0,
            end_char=20,
            chunk_index=0,
            total_chunks=1,
        )
    ]
    return chunker


@pytest.fixture
def real_validator() -> FieldValidator:
    """Create a real FieldValidator for integration tests."""
    return FieldValidator()


@pytest.fixture
def real_confidence_calc() -> ConfidenceCalculator:
    """Create a real ConfidenceCalculator for integration tests."""
    return ConfidenceCalculator()


@pytest.fixture
def real_deduplicator() -> BorrowerDeduplicator:
    """Create a real BorrowerDeduplicator for integration tests."""
    return BorrowerDeduplicator()


@pytest.fixture
def sample_document() -> DocumentContent:
    """Create a sample DocumentContent for testing."""
    return DocumentContent(
        text="John Smith, SSN: 123-45-6789, Address: 123 Main St, Austin TX 78701",
        pages=[
            PageContent(page_number=1, text="John Smith, SSN: 123-45-6789"),
        ],
        page_count=1,
        tables=[],
        metadata={},
    )


@pytest.fixture
def sample_extraction_response() -> LLMResponse:
    """Create a sample LLMResponse with extracted borrower."""
    extraction_result = BorrowerExtractionResult(
        borrowers=[
            ExtractedBorrower(
                name="John Smith",
                ssn="123-45-6789",
                phone="512-555-1234",
                email="john@example.com",
                address=ExtractedAddress(
                    street="123 Main St",
                    city="Austin",
                    state="TX",
                    zip_code="78701",
                ),
                income_history=[
                    ExtractedIncome(
                        amount=75000.0,
                        period="annual",
                        year=2024,
                        source_type="employment",
                        employer="Acme Corp",
                    )
                ],
                account_numbers=["ACC-001"],
                loan_numbers=["LOAN-001"],
            )
        ],
        extraction_notes=None,
    )

    return LLMResponse(
        content="{}",
        parsed=extraction_result,
        input_tokens=100,
        output_tokens=50,
        latency_ms=500,
        model_used="gemini-3-flash-preview",
        finish_reason="STOP",
    )


@pytest.fixture
def extractor(
    mock_llm_client: MagicMock,
    mock_classifier: MagicMock,
    mock_chunker: MagicMock,
    real_validator: FieldValidator,
    real_confidence_calc: ConfidenceCalculator,
    real_deduplicator: BorrowerDeduplicator,
) -> BorrowerExtractor:
    """Create a BorrowerExtractor with mocked LLM and real validation."""
    return BorrowerExtractor(
        llm_client=mock_llm_client,
        classifier=mock_classifier,
        chunker=mock_chunker,
        validator=real_validator,
        confidence_calc=real_confidence_calc,
        deduplicator=real_deduplicator,
    )


class TestSimpleExtraction:
    """Tests for basic document extraction."""

    def test_extract_simple_document(
        self,
        extractor: BorrowerExtractor,
        mock_llm_client: MagicMock,
        sample_document: DocumentContent,
        sample_extraction_response: LLMResponse,
    ) -> None:
        """Simple document extraction returns borrower with correct data."""
        mock_llm_client.extract.return_value = sample_extraction_response

        result = extractor.extract(
            document=sample_document,
            document_id=uuid4(),
            document_name="test.pdf",
        )

        assert len(result.borrowers) == 1
        borrower = result.borrowers[0]
        assert borrower.name == "John Smith"
        assert borrower.ssn == "123-45-6789"
        assert borrower.phone == "512-555-1234"

    def test_extract_returns_extraction_result(
        self,
        extractor: BorrowerExtractor,
        mock_llm_client: MagicMock,
        sample_document: DocumentContent,
        sample_extraction_response: LLMResponse,
    ) -> None:
        """Extraction returns ExtractionResult with metadata."""
        mock_llm_client.extract.return_value = sample_extraction_response

        result = extractor.extract(
            document=sample_document,
            document_id=uuid4(),
            document_name="test.pdf",
        )

        assert isinstance(result, ExtractionResult)
        assert result.complexity is not None
        assert result.chunks_processed == 1
        assert result.total_tokens > 0


class TestModelRouting:
    """Tests for Flash vs Pro model selection."""

    def test_uses_flash_for_simple_documents(
        self,
        extractor: BorrowerExtractor,
        mock_llm_client: MagicMock,
        mock_classifier: MagicMock,
        sample_document: DocumentContent,
        sample_extraction_response: LLMResponse,
    ) -> None:
        """Simple documents use Flash model (use_pro=False)."""
        mock_classifier.classify.return_value = ComplexityAssessment(
            level=ComplexityLevel.STANDARD,
            reasons=["Standard single-borrower document"],
            page_count=1,
            estimated_borrowers=1,
            has_handwritten=False,
            has_poor_quality=False,
        )
        mock_llm_client.extract.return_value = sample_extraction_response

        extractor.extract(
            document=sample_document,
            document_id=uuid4(),
            document_name="test.pdf",
        )

        # Check that use_pro=False was passed
        call_args = mock_llm_client.extract.call_args
        assert call_args.kwargs.get("use_pro") is False

    def test_uses_pro_for_complex_documents(
        self,
        extractor: BorrowerExtractor,
        mock_llm_client: MagicMock,
        mock_classifier: MagicMock,
        sample_document: DocumentContent,
        sample_extraction_response: LLMResponse,
    ) -> None:
        """Complex documents use Pro model (use_pro=True)."""
        mock_classifier.classify.return_value = ComplexityAssessment(
            level=ComplexityLevel.COMPLEX,
            reasons=["Multiple borrower indicators found (2)"],
            page_count=15,
            estimated_borrowers=2,
            has_handwritten=True,
            has_poor_quality=False,
        )
        mock_llm_client.extract.return_value = sample_extraction_response

        extractor.extract(
            document=sample_document,
            document_id=uuid4(),
            document_name="test.pdf",
        )

        # Check that use_pro=True was passed
        call_args = mock_llm_client.extract.call_args
        assert call_args.kwargs.get("use_pro") is True


class TestChunking:
    """Tests for document chunking behavior."""

    def test_chunking_triggered_for_large_docs(
        self,
        mock_llm_client: MagicMock,
        mock_classifier: MagicMock,
        real_validator: FieldValidator,
        real_confidence_calc: ConfidenceCalculator,
        real_deduplicator: BorrowerDeduplicator,
        sample_extraction_response: LLMResponse,
    ) -> None:
        """Large documents are split into multiple chunks."""
        # Use real chunker to test chunking behavior
        real_chunker = DocumentChunker(max_chars=100, overlap_chars=20)

        extractor = BorrowerExtractor(
            llm_client=mock_llm_client,
            classifier=mock_classifier,
            chunker=real_chunker,
            validator=real_validator,
            confidence_calc=real_confidence_calc,
            deduplicator=real_deduplicator,
        )

        # Create a document larger than chunk size
        long_text = "John Smith " * 50  # ~500 chars
        document = DocumentContent(
            text=long_text,
            pages=[],
            page_count=1,
            tables=[],
            metadata={},
        )

        mock_llm_client.extract.return_value = sample_extraction_response

        result = extractor.extract(
            document=document,
            document_id=uuid4(),
            document_name="test.pdf",
        )

        # Should have processed multiple chunks
        assert result.chunks_processed > 1


class TestSourceAttribution:
    """Tests for source reference tracking."""

    def test_source_attribution_added(
        self,
        extractor: BorrowerExtractor,
        mock_llm_client: MagicMock,
        sample_document: DocumentContent,
        sample_extraction_response: LLMResponse,
    ) -> None:
        """Extracted borrowers have source references."""
        mock_llm_client.extract.return_value = sample_extraction_response

        doc_id = uuid4()
        result = extractor.extract(
            document=sample_document,
            document_id=doc_id,
            document_name="loan_app.pdf",
        )

        assert len(result.borrowers) == 1
        borrower = result.borrowers[0]

        assert len(borrower.sources) >= 1
        source = borrower.sources[0]
        assert source.document_id == doc_id
        assert source.document_name == "loan_app.pdf"
        assert source.page_number >= 1
        assert len(source.snippet) > 0


class TestDeduplication:
    """Tests for deduplication integration."""

    def test_deduplication_applied(
        self,
        mock_llm_client: MagicMock,
        mock_classifier: MagicMock,
        real_validator: FieldValidator,
        real_confidence_calc: ConfidenceCalculator,
        real_deduplicator: BorrowerDeduplicator,
        sample_document: DocumentContent,
    ) -> None:
        """Duplicate borrowers from multiple chunks are merged."""
        # Create chunker that returns 2 chunks
        mock_chunker = MagicMock(spec=DocumentChunker)
        mock_chunker.chunk.return_value = [
            TextChunk(text="Chunk 1", start_char=0, end_char=10, chunk_index=0, total_chunks=2),
            TextChunk(text="Chunk 2", start_char=10, end_char=20, chunk_index=1, total_chunks=2),
        ]

        extractor = BorrowerExtractor(
            llm_client=mock_llm_client,
            classifier=mock_classifier,
            chunker=mock_chunker,
            validator=real_validator,
            confidence_calc=real_confidence_calc,
            deduplicator=real_deduplicator,
        )

        # Both chunks extract same borrower (same SSN)
        extraction_result = BorrowerExtractionResult(
            borrowers=[
                ExtractedBorrower(
                    name="John Smith",
                    ssn="123-45-6789",
                )
            ],
        )

        mock_llm_client.extract.return_value = LLMResponse(
            content="{}",
            parsed=extraction_result,
            input_tokens=50,
            output_tokens=25,
            latency_ms=250,
            model_used="gemini-3-flash-preview",
            finish_reason="STOP",
        )

        result = extractor.extract(
            document=sample_document,
            document_id=uuid4(),
            document_name="test.pdf",
        )

        # Should have merged to 1 borrower despite 2 chunks
        assert len(result.borrowers) == 1
        # Should have 2 sources (one from each chunk)
        assert len(result.borrowers[0].sources) == 2


class TestValidation:
    """Tests for validation error tracking."""

    def test_validation_errors_tracked(
        self,
        extractor: BorrowerExtractor,
        mock_llm_client: MagicMock,
        sample_document: DocumentContent,
    ) -> None:
        """Invalid SSN format is tracked in validation errors."""
        # Use an SSN that's invalid for our FieldValidator but passes Pydantic
        # pattern (has the right format but FieldValidator may flag other issues)
        # OR test with completely invalid format that gets caught at Pydantic level
        extraction_result = BorrowerExtractionResult(
            borrowers=[
                ExtractedBorrower(
                    name="John Smith",
                    ssn="invalid-ssn",  # Invalid format - caught by Pydantic
                    phone="not-a-phone",  # Invalid format
                )
            ],
        )

        mock_llm_client.extract.return_value = LLMResponse(
            content="{}",
            parsed=extraction_result,
            input_tokens=50,
            output_tokens=25,
            latency_ms=250,
            model_used="gemini-3-flash-preview",
            finish_reason="STOP",
        )

        result = extractor.extract(
            document=sample_document,
            document_id=uuid4(),
            document_name="test.pdf",
        )

        # Invalid SSN causes Pydantic validation error, borrower is not added
        # but the error should be tracked
        assert len(result.validation_errors) >= 1
        error_fields = {e.field for e in result.validation_errors}
        # SSN is caught by Pydantic pattern validation
        assert "ssn" in error_fields


class TestConfidenceScoring:
    """Tests for confidence score calculation."""

    def test_confidence_calculated(
        self,
        extractor: BorrowerExtractor,
        mock_llm_client: MagicMock,
        sample_document: DocumentContent,
        sample_extraction_response: LLMResponse,
    ) -> None:
        """Borrowers have calculated confidence scores."""
        mock_llm_client.extract.return_value = sample_extraction_response

        result = extractor.extract(
            document=sample_document,
            document_id=uuid4(),
            document_name="test.pdf",
        )

        assert len(result.borrowers) == 1
        borrower = result.borrowers[0]

        # Confidence should be calculated (not initial 0.5)
        # With valid SSN, phone, address, income - should be high
        assert borrower.confidence_score >= 0.7

    def test_low_confidence_for_minimal_data(
        self,
        extractor: BorrowerExtractor,
        mock_llm_client: MagicMock,
        sample_document: DocumentContent,
    ) -> None:
        """Minimal data results in lower confidence score."""
        # Use a borrower with minimal valid data (no SSN since invalid ones
        # get rejected by Pydantic pattern validation)
        extraction_result = BorrowerExtractionResult(
            borrowers=[
                ExtractedBorrower(
                    name="J",  # Very short name
                    # No SSN, no phone, no address, no income
                )
            ],
        )

        mock_llm_client.extract.return_value = LLMResponse(
            content="{}",
            parsed=extraction_result,
            input_tokens=50,
            output_tokens=25,
            latency_ms=250,
            model_used="gemini-3-flash-preview",
            finish_reason="STOP",
        )

        result = extractor.extract(
            document=sample_document,
            document_id=uuid4(),
            document_name="test.pdf",
        )

        assert len(result.borrowers) == 1
        borrower = result.borrowers[0]

        # Should have lower confidence due to missing data
        # Base (0.5) + possibly name bonus if len>1 + validation bonus (0.15)
        # No address, no income = lower score
        assert borrower.confidence_score < 0.8


class TestIncomeConversion:
    """Tests for income data conversion."""

    def test_income_float_to_decimal(
        self,
        extractor: BorrowerExtractor,
        mock_llm_client: MagicMock,
        sample_document: DocumentContent,
        sample_extraction_response: LLMResponse,
    ) -> None:
        """Income amounts are converted from float to Decimal."""
        mock_llm_client.extract.return_value = sample_extraction_response

        result = extractor.extract(
            document=sample_document,
            document_id=uuid4(),
            document_name="test.pdf",
        )

        assert len(result.borrowers) == 1
        assert len(result.borrowers[0].income_history) == 1

        income = result.borrowers[0].income_history[0]
        assert isinstance(income.amount, Decimal)
        assert income.amount == Decimal("75000")


class TestPageEstimation:
    """Tests for page number estimation."""

    def test_page_from_pages_list(
        self,
        extractor: BorrowerExtractor,
        mock_llm_client: MagicMock,
        sample_extraction_response: LLMResponse,
    ) -> None:
        """Page number is determined from pages list when available."""
        document = DocumentContent(
            text="Page 1 content. Page 2 content with John Smith.",
            pages=[
                PageContent(page_number=1, text="Page 1 content."),
                PageContent(page_number=2, text="Page 2 content with John Smith."),
            ],
            page_count=2,
            tables=[],
            metadata={},
        )

        mock_llm_client.extract.return_value = sample_extraction_response

        result = extractor.extract(
            document=document,
            document_id=uuid4(),
            document_name="test.pdf",
        )

        # Source should reference page 1 (chunk starts at char 0)
        assert result.borrowers[0].sources[0].page_number == 1
