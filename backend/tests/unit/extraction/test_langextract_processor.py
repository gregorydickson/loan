"""Unit tests for LangExtractProcessor.

Uses mocking to test without external API calls.
"""

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.extraction.langextract_processor import LangExtractProcessor, LangExtractResult
from src.models.borrower import BorrowerRecord
from src.models.document import SourceReference


@dataclass
class MockCharInterval:
    """Mock CharInterval from LangExtract."""

    start_pos: int
    end_pos: int


@dataclass
class MockExtraction:
    """Mock Extraction from LangExtract."""

    extraction_class: str
    extraction_text: str
    attributes: dict[str, Any] | None = None
    char_interval: MockCharInterval | None = None
    alignment_status: str = "match_exact"


@dataclass
class MockAnnotatedDocument:
    """Mock AnnotatedDocument from LangExtract."""

    extractions: list[MockExtraction]


class TestLangExtractProcessor:
    """Tests for LangExtractProcessor class."""

    @patch("src.extraction.langextract_processor.lx")
    def test_extract_returns_borrower_with_offsets(self, mock_lx):
        """extract() returns BorrowerRecord with char_start/char_end populated."""
        # Setup mock
        mock_result = MockAnnotatedDocument(
            extractions=[
                MockExtraction(
                    extraction_class="borrower",
                    extraction_text="John Smith",
                    attributes={
                        "ssn": "123-45-6789",
                        "phone": "(214) 555-1234",
                        "street": "123 Main St",
                        "city": "Dallas",
                        "state": "TX",
                        "zip_code": "75201",
                    },
                    char_interval=MockCharInterval(start_pos=10, end_pos=20),
                ),
            ]
        )
        mock_lx.extract.return_value = mock_result

        # Execute
        processor = LangExtractProcessor(api_key="test-key")
        result = processor.extract(
            document_text="Borrower: John Smith, SSN: 123-45-6789",
            document_id=uuid4(),
            document_name="test.pdf",
        )

        # Verify
        assert len(result.borrowers) == 1
        borrower = result.borrowers[0]
        assert borrower.name == "John Smith"
        assert borrower.ssn == "123-45-6789"
        assert len(borrower.sources) == 1

        source = borrower.sources[0]
        assert source.char_start == 10
        assert source.char_end == 20

    @patch("src.extraction.langextract_processor.lx")
    def test_extract_handles_income_extractions(self, mock_lx):
        """extract() processes income extractions and adds to borrower."""
        mock_result = MockAnnotatedDocument(
            extractions=[
                MockExtraction(
                    extraction_class="borrower",
                    extraction_text="Jane Doe",
                    attributes={"ssn": "987-65-4321"},
                    char_interval=MockCharInterval(start_pos=0, end_pos=8),
                ),
                MockExtraction(
                    extraction_class="income",
                    extraction_text="$85,000 (2025)",
                    attributes={
                        "amount": "85000",
                        "period": "annual",
                        "year": "2025",
                        "source_type": "employment",
                        "employer": "TechCorp",
                    },
                ),
            ]
        )
        mock_lx.extract.return_value = mock_result

        processor = LangExtractProcessor(api_key="test-key")
        result = processor.extract(
            document_text="Jane Doe earns $85,000 (2025)",
            document_id=uuid4(),
            document_name="test.pdf",
        )

        assert len(result.borrowers) == 1
        borrower = result.borrowers[0]
        assert len(borrower.income_history) == 1
        income = borrower.income_history[0]
        assert income.amount == 85000
        assert income.year == 2025
        assert income.employer == "TechCorp"

    @patch("src.extraction.langextract_processor.lx")
    def test_extract_handles_account_extractions(self, mock_lx):
        """extract() processes account and loan number extractions."""
        mock_result = MockAnnotatedDocument(
            extractions=[
                MockExtraction(
                    extraction_class="borrower",
                    extraction_text="Bob Builder",
                    attributes={},
                    char_interval=MockCharInterval(start_pos=0, end_pos=11),
                ),
                MockExtraction(
                    extraction_class="account",
                    extraction_text="1234567890",
                    attributes={"account_type": "checking"},
                ),
                MockExtraction(
                    extraction_class="loan",
                    extraction_text="LN-2025-001",
                    attributes={"loan_type": "mortgage"},
                ),
            ]
        )
        mock_lx.extract.return_value = mock_result

        processor = LangExtractProcessor(api_key="test-key")
        result = processor.extract(
            document_text="Bob Builder, Account: 1234567890, Loan: LN-2025-001",
            document_id=uuid4(),
            document_name="test.pdf",
        )

        assert len(result.borrowers) == 1
        borrower = result.borrowers[0]
        assert "1234567890" in borrower.account_numbers
        assert "LN-2025-001" in borrower.loan_numbers

    @patch("src.extraction.langextract_processor.lx")
    def test_extract_handles_extraction_failure(self, mock_lx):
        """extract() returns empty result on LangExtract failure."""
        mock_lx.extract.side_effect = Exception("API error")

        processor = LangExtractProcessor(api_key="test-key")
        result = processor.extract(
            document_text="Some document",
            document_id=uuid4(),
            document_name="test.pdf",
        )

        assert len(result.borrowers) == 0
        assert len(result.alignment_warnings) == 1
        assert "Extraction failed" in result.alignment_warnings[0]

    @patch("src.extraction.langextract_processor.lx")
    def test_extract_tracks_fuzzy_alignment_warnings(self, mock_lx):
        """extract() tracks fuzzy alignment in warnings."""
        mock_result = MockAnnotatedDocument(
            extractions=[
                MockExtraction(
                    extraction_class="borrower",
                    extraction_text="John Smith",
                    attributes={},
                    char_interval=MockCharInterval(start_pos=0, end_pos=10),
                    alignment_status="match_fuzzy",
                ),
            ]
        )
        mock_lx.extract.return_value = mock_result

        processor = LangExtractProcessor(api_key="test-key")
        result = processor.extract(
            document_text="John Smith is the borrower",
            document_id=uuid4(),
            document_name="test.pdf",
        )

        assert len(result.borrowers) == 1
        # Check for fuzzy alignment warning
        assert any("Fuzzy alignment" in w for w in result.alignment_warnings)

    @patch("src.extraction.langextract_processor.lx")
    def test_extract_no_char_interval(self, mock_lx):
        """extract() handles extractions without char_interval."""
        mock_result = MockAnnotatedDocument(
            extractions=[
                MockExtraction(
                    extraction_class="borrower",
                    extraction_text="Alice Wonder",
                    attributes={"ssn": "111-22-3333"},
                    char_interval=None,  # No offsets
                ),
            ]
        )
        mock_lx.extract.return_value = mock_result

        processor = LangExtractProcessor(api_key="test-key")
        result = processor.extract(
            document_text="Alice Wonder",
            document_id=uuid4(),
            document_name="test.pdf",
        )

        assert len(result.borrowers) == 1
        borrower = result.borrowers[0]
        source = borrower.sources[0]
        assert source.char_start is None
        assert source.char_end is None


class TestLangExtractProcessorInitialization:
    """Tests for LangExtractProcessor initialization."""

    def test_init_with_api_key(self):
        """__init__ accepts API key parameter."""
        processor = LangExtractProcessor(api_key="test-key-123")
        assert processor._model_id == "gemini-3.0-flash"

    @patch.dict("os.environ", {"GOOGLE_API_KEY": "env-key"}, clear=False)
    def test_init_uses_google_api_key_env(self):
        """__init__ uses GOOGLE_API_KEY env var when no key provided."""
        processor = LangExtractProcessor()
        # Should not raise - uses env var
        assert processor is not None

    def test_examples_loaded(self):
        """__init__ loads few-shot examples."""
        processor = LangExtractProcessor(api_key="test")
        assert len(processor.examples) > 0


class TestLangExtractResultDataclass:
    """Tests for LangExtractResult dataclass."""

    def test_result_with_borrowers(self):
        """LangExtractResult stores borrowers correctly."""
        borrower = BorrowerRecord(
            name="Test User",
            ssn="123-45-6789",
            confidence_score=0.9,
            sources=[
                SourceReference(
                    document_id=uuid4(),
                    document_name="test.pdf",
                    page_number=1,
                    snippet="Test snippet",
                )
            ],
        )

        result = LangExtractResult(
            borrowers=[borrower],
            raw_extractions=None,
            alignment_warnings=["Test warning"],
        )

        assert len(result.borrowers) == 1
        assert result.borrowers[0].name == "Test User"
        assert len(result.alignment_warnings) == 1

    def test_result_empty(self):
        """LangExtractResult can be empty."""
        result = LangExtractResult(borrowers=[])

        assert len(result.borrowers) == 0
        assert result.raw_extractions is None
        assert len(result.alignment_warnings) == 0
