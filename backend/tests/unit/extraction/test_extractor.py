"""Unit tests for BorrowerExtractor orchestrator.

Tests the main extraction pipeline that coordinates:
- ComplexityClassifier (model routing)
- DocumentChunker (splitting large docs)
- GeminiClient (LLM extraction)
- BorrowerDeduplicator (merging duplicates)
- FieldValidator (format validation)
- ConfidenceCalculator (scoring)
- ConsistencyValidator (data quality checks)
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError as PydanticValidationError

from src.extraction.chunker import TextChunk
from src.extraction.complexity_classifier import (
    ComplexityAssessment,
    ComplexityLevel,
)
from src.extraction.confidence import ConfidenceBreakdown
from src.extraction.consistency import ConsistencyWarning
from src.extraction.deduplication import BorrowerDeduplicator
from src.extraction.extractor import BorrowerExtractor, ExtractionResult
from src.extraction.llm_client import LLMResponse
from src.extraction.schemas import (
    BorrowerExtractionResult,
    ExtractedAddress,
    ExtractedBorrower,
    ExtractedIncome,
)
from src.extraction.validation import ValidationError, ValidationResult
from src.ingestion.docling_processor import DocumentContent, PageContent
from src.models.borrower import BorrowerRecord


class TestBorrowerExtractorInitialization:
    """Tests for BorrowerExtractor initialization."""

    def test_initializes_with_all_components(self):
        """Creates extractor with all required components."""
        llm_client = MagicMock()
        classifier = MagicMock()
        chunker = MagicMock()
        validator = MagicMock()
        confidence_calc = MagicMock()
        deduplicator = MagicMock()
        consistency_validator = MagicMock()

        extractor = BorrowerExtractor(
            llm_client=llm_client,
            classifier=classifier,
            chunker=chunker,
            validator=validator,
            confidence_calc=confidence_calc,
            deduplicator=deduplicator,
            consistency_validator=consistency_validator,
        )

        assert extractor.llm_client is llm_client
        assert extractor.classifier is classifier
        assert extractor.chunker is chunker
        assert extractor.validator is validator
        assert extractor.confidence_calc is confidence_calc
        assert extractor.deduplicator is deduplicator
        assert extractor.consistency_validator is consistency_validator


class TestBasicExtractionFlow:
    """Tests for basic end-to-end extraction flow."""

    @pytest.fixture
    def mock_components(self):
        """Create mocked components for extractor."""
        components = {
            "llm_client": MagicMock(),
            "classifier": MagicMock(),
            "chunker": MagicMock(),
            "validator": MagicMock(),
            "confidence_calc": MagicMock(),
            "deduplicator": MagicMock(),
            "consistency_validator": MagicMock(),
        }
        return components

    @pytest.fixture
    def extractor(self, mock_components):
        """Create BorrowerExtractor with mocked components."""
        return BorrowerExtractor(**mock_components)

    def test_extract_basic_flow(self, extractor, mock_components):
        """Extract completes basic flow successfully."""
        # Setup document
        document = DocumentContent(
            text="John Smith, SSN: 123-45-6789",
            page_count=1,
            pages=[],
        )

        # Mock complexity assessment
        assessment = ComplexityAssessment(
            level=ComplexityLevel.STANDARD,
            reasons=["Single borrower"],
            page_count=1,
            estimated_borrowers=1,
            has_handwritten=False,
            has_poor_quality=False,
        )
        mock_components["classifier"].classify.return_value = assessment

        # Mock chunking (single chunk)
        chunk = TextChunk(
            text=document.text,
            start_char=0,
            end_char=len(document.text),
            chunk_index=0,
            total_chunks=1,
        )
        mock_components["chunker"].chunk.return_value = [chunk]

        # Mock LLM extraction
        extracted_borrower = ExtractedBorrower(
            name="John Smith",
            ssn="123456789",  # Without dashes
            phone=None,
            email=None,
            address=None,
            income_history=[],
            account_numbers=[],
            loan_numbers=[],
        )
        extraction_result = BorrowerExtractionResult(borrowers=[extracted_borrower])
        llm_response = LLMResponse(
            content='{"borrowers": [...]}',
            parsed=extraction_result,
            input_tokens=50,
            output_tokens=100,
            latency_ms=200,
            model_used="gemini-3-flash-preview",
            finish_reason="STOP",
        )
        mock_components["llm_client"].extract.return_value = llm_response

        # Mock validator (SSN normalization)
        mock_components["validator"].normalize_ssn.return_value = "123-45-6789"
        mock_components["validator"].validate_ssn.return_value = ValidationResult(
            is_valid=True
        )
        mock_components["validator"].validate_phone.return_value = ValidationResult(
            is_valid=True
        )

        # Mock deduplication (no duplicates)
        def dedup_passthrough(records):
            return records

        mock_components["deduplicator"].deduplicate.side_effect = dedup_passthrough

        # Mock consistency validation
        mock_components["consistency_validator"].validate.return_value = []

        # Mock confidence calculation
        breakdown = ConfidenceBreakdown(
            base_score=0.5,
            required_fields_bonus=0.2,
            optional_fields_bonus=0.0,
            multi_source_bonus=0.0,
            validation_bonus=0.15,
            total=0.85,
            requires_review=False,
        )
        mock_components["confidence_calc"].calculate.return_value = breakdown

        # Execute
        result = extractor.extract(
            document=document,
            document_id=uuid4(),
            document_name="test.pdf",
        )

        # Assertions
        assert isinstance(result, ExtractionResult)
        assert len(result.borrowers) == 1
        assert result.borrowers[0].name == "John Smith"
        assert result.borrowers[0].ssn == "123-45-6789"
        assert result.complexity.level == ComplexityLevel.STANDARD
        assert result.chunks_processed == 1
        assert result.total_tokens == 150  # 50 input + 100 output
        assert len(result.validation_errors) == 0
        assert len(result.consistency_warnings) == 0


class TestComplexityAssessment:
    """Tests for complexity assessment and model selection."""

    @pytest.fixture
    def extractor_with_mocks(self):
        """Create extractor with mocked components."""
        components = {
            "llm_client": MagicMock(),
            "classifier": MagicMock(),
            "chunker": MagicMock(),
            "validator": MagicMock(),
            "confidence_calc": MagicMock(),
            "deduplicator": MagicMock(),
            "consistency_validator": MagicMock(),
        }

        # Setup defaults
        components["chunker"].chunk.return_value = [
            TextChunk(text="text", start_char=0, end_char=4, chunk_index=0, total_chunks=1)
        ]
        components["llm_client"].extract.return_value = LLMResponse(
            content="{}",
            parsed=BorrowerExtractionResult(borrowers=[]),
            input_tokens=10,
            output_tokens=10,
            latency_ms=100,
            model_used="model",
            finish_reason="STOP",
        )
        components["validator"].normalize_ssn.return_value = None
        components["deduplicator"].deduplicate.side_effect = lambda x: x
        components["consistency_validator"].validate.return_value = []
        components["confidence_calc"].calculate.return_value = ConfidenceBreakdown(
            base_score=0.5,
            required_fields_bonus=0.0,
            optional_fields_bonus=0.0,
            multi_source_bonus=0.0,
            validation_bonus=0.0,
            total=0.5,
            requires_review=True,
        )

        extractor = BorrowerExtractor(**components)
        return extractor, components

    def test_uses_flash_for_standard_complexity(self, extractor_with_mocks):
        """Uses Flash model for STANDARD complexity."""
        extractor, mocks = extractor_with_mocks

        # Mock standard complexity
        mocks["classifier"].classify.return_value = ComplexityAssessment(
            level=ComplexityLevel.STANDARD,
            reasons=[],
            page_count=1,
            estimated_borrowers=1,
            has_handwritten=False,
            has_poor_quality=False,
        )

        document = DocumentContent(text="test", page_count=1, pages=[])
        extractor.extract(document, uuid4(), "test.pdf")

        # Check LLM called with use_pro=False
        call_args = mocks["llm_client"].extract.call_args
        assert call_args[1]["use_pro"] is False

    def test_uses_pro_for_complex_documents(self, extractor_with_mocks):
        """Uses Pro model for COMPLEX documents."""
        extractor, mocks = extractor_with_mocks

        # Mock complex assessment
        mocks["classifier"].classify.return_value = ComplexityAssessment(
            level=ComplexityLevel.COMPLEX,
            reasons=["Multiple borrowers"],
            page_count=1,
            estimated_borrowers=2,
            has_handwritten=False,
            has_poor_quality=False,
        )

        document = DocumentContent(text="test", page_count=1, pages=[])
        extractor.extract(document, uuid4(), "test.pdf")

        # Check LLM called with use_pro=True
        call_args = mocks["llm_client"].extract.call_args
        assert call_args[1]["use_pro"] is True


class TestMultiChunkProcessing:
    """Tests for processing documents split into multiple chunks."""

    @pytest.fixture
    def extractor_with_mocks(self):
        """Create extractor with basic mocks."""
        components = {
            "llm_client": MagicMock(),
            "classifier": MagicMock(),
            "chunker": MagicMock(),
            "validator": MagicMock(),
            "confidence_calc": MagicMock(),
            "deduplicator": MagicMock(),
            "consistency_validator": MagicMock(),
        }

        # Defaults
        components["classifier"].classify.return_value = ComplexityAssessment(
            level=ComplexityLevel.STANDARD,
            reasons=[],
            page_count=1,
            estimated_borrowers=1,
            has_handwritten=False,
            has_poor_quality=False,
        )
        components["validator"].normalize_ssn.return_value = None
        components["validator"].validate_ssn.return_value = ValidationResult(is_valid=True)
        components["validator"].validate_phone.return_value = ValidationResult(is_valid=True)
        components["deduplicator"].deduplicate.side_effect = lambda x: x
        components["consistency_validator"].validate.return_value = []
        components["confidence_calc"].calculate.return_value = ConfidenceBreakdown(
            base_score=0.5,
            required_fields_bonus=0.0,
            optional_fields_bonus=0.0,
            multi_source_bonus=0.0,
            validation_bonus=0.0,
            total=0.5,
            requires_review=True,
        )

        return BorrowerExtractor(**components), components

    def test_processes_all_chunks(self, extractor_with_mocks):
        """Processes all chunks from chunker."""
        extractor, mocks = extractor_with_mocks

        # Mock 3 chunks
        chunks = [
            TextChunk(text="chunk1", start_char=0, end_char=6, chunk_index=0, total_chunks=3),
            TextChunk(text="chunk2", start_char=6, end_char=12, chunk_index=1, total_chunks=3),
            TextChunk(text="chunk3", start_char=12, end_char=18, chunk_index=2, total_chunks=3),
        ]
        mocks["chunker"].chunk.return_value = chunks

        # Mock LLM returns one borrower per chunk
        def extract_side_effect(*args, **kwargs):
            return LLMResponse(
                content="{}",
                parsed=BorrowerExtractionResult(
                    borrowers=[
                        ExtractedBorrower(
                            name="Borrower",
                            ssn=None,
                            phone=None,
                            email=None,
                            address=None,
                            income_history=[],
                            account_numbers=[],
                            loan_numbers=[],
                        )
                    ]
                ),
                input_tokens=10,
                output_tokens=20,
                latency_ms=100,
                model_used="model",
                finish_reason="STOP",
            )

        mocks["llm_client"].extract.side_effect = extract_side_effect

        document = DocumentContent(text="chunk1chunk2chunk3", page_count=1, pages=[])
        result = extractor.extract(document, uuid4(), "test.pdf")

        # Should process 3 chunks
        assert result.chunks_processed == 3
        # Should call LLM 3 times
        assert mocks["llm_client"].extract.call_count == 3
        # Should have 3 borrowers before deduplication
        assert len(result.borrowers) == 3

    def test_aggregates_tokens_across_chunks(self, extractor_with_mocks):
        """Aggregates token counts across all chunks."""
        extractor, mocks = extractor_with_mocks

        chunks = [
            TextChunk(text="c1", start_char=0, end_char=2, chunk_index=0, total_chunks=2),
            TextChunk(text="c2", start_char=2, end_char=4, chunk_index=1, total_chunks=2),
        ]
        mocks["chunker"].chunk.return_value = chunks

        # First chunk: 100 input, 50 output
        # Second chunk: 150 input, 75 output
        responses = [
            LLMResponse(
                content="{}",
                parsed=BorrowerExtractionResult(borrowers=[]),
                input_tokens=100,
                output_tokens=50,
                latency_ms=100,
                model_used="model",
                finish_reason="STOP",
            ),
            LLMResponse(
                content="{}",
                parsed=BorrowerExtractionResult(borrowers=[]),
                input_tokens=150,
                output_tokens=75,
                latency_ms=100,
                model_used="model",
                finish_reason="STOP",
            ),
        ]
        mocks["llm_client"].extract.side_effect = responses

        document = DocumentContent(text="c1c2", page_count=1, pages=[])
        result = extractor.extract(document, uuid4(), "test.pdf")

        # Total tokens: (100+150) + (50+75) = 375
        assert result.total_tokens == 375


class TestValidationErrorCollection:
    """Tests for validation error collection."""

    @pytest.fixture
    def extractor_with_mocks(self):
        """Create extractor with validation mocks."""
        components = {
            "llm_client": MagicMock(),
            "classifier": MagicMock(),
            "chunker": MagicMock(),
            "validator": MagicMock(),
            "confidence_calc": MagicMock(),
            "deduplicator": MagicMock(),
            "consistency_validator": MagicMock(),
        }

        # Defaults
        components["classifier"].classify.return_value = ComplexityAssessment(
            level=ComplexityLevel.STANDARD,
            reasons=[],
            page_count=1,
            estimated_borrowers=1,
            has_handwritten=False,
            has_poor_quality=False,
        )
        components["chunker"].chunk.return_value = [
            TextChunk(text="text", start_char=0, end_char=4, chunk_index=0, total_chunks=1)
        ]
        components["validator"].normalize_ssn.return_value = "123-45-6789"
        components["deduplicator"].deduplicate.side_effect = lambda x: x
        components["consistency_validator"].validate.return_value = []
        components["confidence_calc"].calculate.return_value = ConfidenceBreakdown(
            base_score=0.5,
            required_fields_bonus=0.0,
            optional_fields_bonus=0.0,
            multi_source_bonus=0.0,
            validation_bonus=0.0,
            total=0.5,
            requires_review=True,
        )

        return BorrowerExtractor(**components), components

    def test_collects_ssn_validation_errors(self, extractor_with_mocks):
        """Collects SSN validation errors."""
        extractor, mocks = extractor_with_mocks

        # Mock extracted borrower
        mocks["llm_client"].extract.return_value = LLMResponse(
            content="{}",
            parsed=BorrowerExtractionResult(
                borrowers=[
                    ExtractedBorrower(
                        name="John",
                        ssn="invalid",
                        phone=None,
                        email=None,
                        address=None,
                        income_history=[],
                        account_numbers=[],
                        loan_numbers=[],
                    )
                ]
            ),
            input_tokens=10,
            output_tokens=10,
            latency_ms=100,
            model_used="model",
            finish_reason="STOP",
        )

        # Mock SSN validation failure
        ssn_error = ValidationError(
            field="ssn",
            value="invalid",
            error_type="FORMAT",
            message="Invalid SSN format",
        )
        mocks["validator"].validate_ssn.return_value = ValidationResult(
            is_valid=False, errors=[ssn_error]
        )
        mocks["validator"].validate_phone.return_value = ValidationResult(is_valid=True)

        document = DocumentContent(text="test", page_count=1, pages=[])
        result = extractor.extract(document, uuid4(), "test.pdf")

        # Should collect validation error
        assert len(result.validation_errors) == 1
        assert result.validation_errors[0].field == "ssn"

    def test_collects_phone_validation_errors(self, extractor_with_mocks):
        """Collects phone validation errors."""
        extractor, mocks = extractor_with_mocks

        mocks["llm_client"].extract.return_value = LLMResponse(
            content="{}",
            parsed=BorrowerExtractionResult(
                borrowers=[
                    ExtractedBorrower(
                        name="John",
                        ssn=None,
                        phone="invalid",
                        email=None,
                        address=None,
                        income_history=[],
                        account_numbers=[],
                        loan_numbers=[],
                    )
                ]
            ),
            input_tokens=10,
            output_tokens=10,
            latency_ms=100,
            model_used="model",
            finish_reason="STOP",
        )

        mocks["validator"].validate_ssn.return_value = ValidationResult(is_valid=True)
        phone_error = ValidationError(
            field="phone",
            value="invalid",
            error_type="FORMAT",
            message="Invalid phone",
        )
        mocks["validator"].validate_phone.return_value = ValidationResult(
            is_valid=False, errors=[phone_error]
        )

        document = DocumentContent(text="test", page_count=1, pages=[])
        result = extractor.extract(document, uuid4(), "test.pdf")

        assert len(result.validation_errors) == 1
        assert result.validation_errors[0].field == "phone"


class TestPydanticValidationHandling:
    """Tests for handling Pydantic validation errors during conversion."""

    @pytest.fixture
    def extractor_with_mocks(self):
        """Create extractor with mocks."""
        components = {
            "llm_client": MagicMock(),
            "classifier": MagicMock(),
            "chunker": MagicMock(),
            "validator": MagicMock(),
            "confidence_calc": MagicMock(),
            "deduplicator": MagicMock(),
            "consistency_validator": MagicMock(),
        }

        components["classifier"].classify.return_value = ComplexityAssessment(
            level=ComplexityLevel.STANDARD,
            reasons=[],
            page_count=1,
            estimated_borrowers=1,
            has_handwritten=False,
            has_poor_quality=False,
        )
        components["chunker"].chunk.return_value = [
            TextChunk(text="text", start_char=0, end_char=4, chunk_index=0, total_chunks=1)
        ]
        components["deduplicator"].deduplicate.side_effect = lambda x: x
        components["consistency_validator"].validate.return_value = []
        components["confidence_calc"].calculate.return_value = ConfidenceBreakdown(
            base_score=0.5,
            required_fields_bonus=0.0,
            optional_fields_bonus=0.0,
            multi_source_bonus=0.0,
            validation_bonus=0.0,
            total=0.5,
            requires_review=True,
        )

        return BorrowerExtractor(**components), components

    def test_handles_pydantic_validation_error(self, extractor_with_mocks):
        """Handles Pydantic validation errors gracefully."""
        extractor, mocks = extractor_with_mocks

        # Mock extracted borrower with empty name (will fail Pydantic min_length=1)
        mocks["llm_client"].extract.return_value = LLMResponse(
            content="{}",
            parsed=BorrowerExtractionResult(
                borrowers=[
                    ExtractedBorrower(
                        name="",  # Will fail BorrowerRecord validation
                        ssn=None,
                        phone=None,
                        email=None,
                        address=None,
                        income_history=[],
                        account_numbers=[],
                        loan_numbers=[],
                    )
                ]
            ),
            input_tokens=10,
            output_tokens=10,
            latency_ms=100,
            model_used="model",
            finish_reason="STOP",
        )

        # normalize_ssn might be called but won't matter
        mocks["validator"].normalize_ssn.return_value = None

        document = DocumentContent(text="test", page_count=1, pages=[])
        result = extractor.extract(document, uuid4(), "test.pdf")

        # Should not crash, should collect validation error
        assert len(result.borrowers) == 0  # Borrower not added due to validation failure
        assert len(result.validation_errors) > 0  # Pydantic error collected


class TestPageNumberDetection:
    """Tests for _find_page_for_position helper."""

    @pytest.fixture
    def extractor(self):
        """Create minimal extractor for testing helpers."""
        return BorrowerExtractor(
            llm_client=MagicMock(),
            classifier=MagicMock(),
            chunker=MagicMock(),
            validator=MagicMock(),
            confidence_calc=MagicMock(),
            deduplicator=MagicMock(),
            consistency_validator=MagicMock(),
        )

    def test_finds_page_with_page_level_content(self, extractor):
        """Finds correct page when pages have text."""
        document = DocumentContent(
            text="Page1TextPage2TextPage3Text",
            page_count=3,
            pages=[
                PageContent(page_number=1, text="Page1Text"),  # 0-9
                PageContent(page_number=2, text="Page2Text"),  # 9-18
                PageContent(page_number=3, text="Page3Text"),  # 18-27
            ],
        )

        # Position 5 is in page 1
        assert extractor._find_page_for_position(document, 5) == 1
        # Position 12 is in page 2
        assert extractor._find_page_for_position(document, 12) == 2
        # Position 20 is in page 3
        assert extractor._find_page_for_position(document, 20) == 3

    def test_returns_last_page_for_position_beyond_pages(self, extractor):
        """Returns last page when position beyond all pages."""
        document = DocumentContent(
            text="Short",
            page_count=2,
            pages=[
                PageContent(page_number=1, text="Sho"),
                PageContent(page_number=2, text="rt"),
            ],
        )

        # Position 100 is beyond all pages
        assert extractor._find_page_for_position(document, 100) == 2

    def test_estimates_page_without_page_level_content(self, extractor):
        """Estimates page when no page-level content."""
        document = DocumentContent(
            text="A" * 1000,  # 1000 chars
            page_count=10,  # 10 pages
            pages=[],  # No page-level content
        )

        # ~100 chars per page
        # Position 250 should be ~page 3
        page = extractor._find_page_for_position(document, 250)
        assert 2 <= page <= 4  # Allow some estimation variance

    def test_returns_1_for_empty_document(self, extractor):
        """Returns page 1 for empty document."""
        document = DocumentContent(text="", page_count=0, pages=[])
        assert extractor._find_page_for_position(document, 0) == 1


class TestBorrowerRecordConversion:
    """Tests for _convert_to_borrower_record helper."""

    @pytest.fixture
    def extractor(self):
        """Create extractor with mock validator."""
        validator = MagicMock()
        validator.normalize_ssn.return_value = "123-45-6789"

        return BorrowerExtractor(
            llm_client=MagicMock(),
            classifier=MagicMock(),
            chunker=MagicMock(),
            validator=validator,
            confidence_calc=MagicMock(),
            deduplicator=MagicMock(),
            consistency_validator=MagicMock(),
        )

    def test_converts_basic_extracted_borrower(self, extractor):
        """Converts basic ExtractedBorrower to BorrowerRecord."""
        extracted = ExtractedBorrower(
            name="John Smith",
            ssn="123456789",
            phone="555-1234",
            email="john@example.com",
            address=None,
            income_history=[],
            account_numbers=[],
            loan_numbers=[],
        )

        doc_id = uuid4()
        record = extractor._convert_to_borrower_record(
            extracted=extracted,
            document_id=doc_id,
            document_name="test.pdf",
            page_number=1,
            snippet="snippet text",
        )

        assert isinstance(record, BorrowerRecord)
        assert record.name == "John Smith"
        assert record.ssn == "123-45-6789"  # Normalized
        assert record.phone == "555-1234"
        assert record.email == "john@example.com"
        assert len(record.sources) == 1
        assert record.sources[0].document_id == doc_id

    def test_converts_address(self, extractor):
        """Converts address from ExtractedAddress to Address."""
        extracted = ExtractedBorrower(
            name="John",
            ssn=None,
            phone=None,
            email=None,
            address=ExtractedAddress(
                street="123 Main St",
                city="Austin",
                state="TX",
                zip_code="78701",
            ),
            income_history=[],
            account_numbers=[],
            loan_numbers=[],
        )

        record = extractor._convert_to_borrower_record(
            extracted=extracted,
            document_id=uuid4(),
            document_name="test.pdf",
            page_number=1,
            snippet="snippet",
        )

        assert record.address is not None
        assert record.address.street == "123 Main St"
        assert record.address.city == "Austin"
        assert record.address.state == "TX"
        assert record.address.zip_code == "78701"

    def test_converts_income_history(self, extractor):
        """Converts income history with float to Decimal conversion."""
        extracted = ExtractedBorrower(
            name="John",
            ssn=None,
            phone=None,
            email=None,
            address=None,
            income_history=[
                ExtractedIncome(
                    amount=100000.50,  # Float
                    period="annual",
                    year=2024,
                    source_type="W2",
                    employer="ACME Corp",
                )
            ],
            account_numbers=[],
            loan_numbers=[],
        )

        record = extractor._convert_to_borrower_record(
            extracted=extracted,
            document_id=uuid4(),
            document_name="test.pdf",
            page_number=1,
            snippet="snippet",
        )

        assert len(record.income_history) == 1
        income = record.income_history[0]
        assert income.amount == Decimal("100000.50")
        assert income.period == "annual"
        assert income.year == 2024
        assert income.source_type == "W2"
        assert income.employer == "ACME Corp"

    def test_converts_account_and_loan_numbers(self, extractor):
        """Converts account and loan numbers to lists."""
        extracted = ExtractedBorrower(
            name="John",
            ssn=None,
            phone=None,
            email=None,
            address=None,
            income_history=[],
            account_numbers=["ACC123", "ACC456"],
            loan_numbers=["LOAN789"],
        )

        record = extractor._convert_to_borrower_record(
            extracted=extracted,
            document_id=uuid4(),
            document_name="test.pdf",
            page_number=1,
            snippet="snippet",
        )

        assert record.account_numbers == ["ACC123", "ACC456"]
        assert record.loan_numbers == ["LOAN789"]


class TestConsistencyValidation:
    """Tests for consistency validation integration."""

    @pytest.fixture
    def extractor_with_mocks(self):
        """Create extractor with mocks."""
        components = {
            "llm_client": MagicMock(),
            "classifier": MagicMock(),
            "chunker": MagicMock(),
            "validator": MagicMock(),
            "confidence_calc": MagicMock(),
            "deduplicator": MagicMock(),
            "consistency_validator": MagicMock(),
        }

        # Setup defaults
        components["classifier"].classify.return_value = ComplexityAssessment(
            level=ComplexityLevel.STANDARD,
            reasons=[],
            page_count=1,
            estimated_borrowers=1,
            has_handwritten=False,
            has_poor_quality=False,
        )
        components["chunker"].chunk.return_value = [
            TextChunk(text="text", start_char=0, end_char=4, chunk_index=0, total_chunks=1)
        ]
        components["llm_client"].extract.return_value = LLMResponse(
            content="{}",
            parsed=BorrowerExtractionResult(borrowers=[]),
            input_tokens=10,
            output_tokens=10,
            latency_ms=100,
            model_used="model",
            finish_reason="STOP",
        )
        components["validator"].normalize_ssn.return_value = None
        components["validator"].validate_ssn.return_value = ValidationResult(is_valid=True)
        components["validator"].validate_phone.return_value = ValidationResult(is_valid=True)
        components["deduplicator"].deduplicate.side_effect = lambda x: x
        components["confidence_calc"].calculate.return_value = ConfidenceBreakdown(
            base_score=0.5,
            required_fields_bonus=0.0,
            optional_fields_bonus=0.0,
            multi_source_bonus=0.0,
            validation_bonus=0.0,
            total=0.5,
            requires_review=True,
        )

        return BorrowerExtractor(**components), components

    def test_collects_consistency_warnings(self, extractor_with_mocks):
        """Collects consistency warnings from validator."""
        extractor, mocks = extractor_with_mocks

        # Mock consistency warnings
        borrower_id = uuid4()
        warnings = [
            ConsistencyWarning(
                warning_type="ADDRESS_CONFLICT",
                borrower_id=borrower_id,
                field="address",
                message="Multiple addresses found",
                details={"count": 2},
            )
        ]
        mocks["consistency_validator"].validate.return_value = warnings

        document = DocumentContent(text="test", page_count=1, pages=[])
        result = extractor.extract(document, uuid4(), "test.pdf")

        assert len(result.consistency_warnings) == 1
        assert result.consistency_warnings[0].warning_type == "ADDRESS_CONFLICT"


class TestExtractionResultStructure:
    """Tests for ExtractionResult dataclass."""

    def test_extraction_result_has_all_fields(self):
        """ExtractionResult contains all required fields."""
        assessment = ComplexityAssessment(
            level=ComplexityLevel.STANDARD,
            reasons=[],
            page_count=1,
            estimated_borrowers=1,
            has_handwritten=False,
            has_poor_quality=False,
        )

        result = ExtractionResult(
            borrowers=[],
            complexity=assessment,
            chunks_processed=1,
            total_tokens=100,
            validation_errors=[],
            consistency_warnings=[],
        )

        assert result.borrowers == []
        assert result.complexity.level == ComplexityLevel.STANDARD
        assert result.chunks_processed == 1
        assert result.total_tokens == 100
        assert result.validation_errors == []
        assert result.consistency_warnings == []
