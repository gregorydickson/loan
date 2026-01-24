"""Unit tests for Pydantic data models.

Tests cover:
- Field validation constraints (zip code, state, amounts, periods, confidence)
- JSON serialization round-trip
- Dict serialization with mode='json'
- Nested model structures
- Default values and optional fields
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.models import (
    Address,
    BorrowerRecord,
    DocumentMetadata,
    IncomeRecord,
    SourceReference,
)

# =============================================================================
# Address Validation Tests
# =============================================================================


class TestAddressValidation:
    """Tests for Address model validation."""

    def test_valid_address_all_fields(self) -> None:
        """Valid address with all fields passes validation."""
        address = Address(
            street="123 Main St",
            city="Austin",
            state="TX",
            zip_code="78701",
        )
        assert address.street == "123 Main St"
        assert address.city == "Austin"
        assert address.state == "TX"
        assert address.zip_code == "78701"
        assert address.country == "USA"

    def test_invalid_state_code_too_long(self) -> None:
        """State code with 3 characters raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Address(
                street="123 Main St",
                city="Austin",
                state="TEX",  # Invalid: too long
                zip_code="78701",
            )
        assert "state" in str(exc_info.value)

    def test_invalid_state_code_too_short(self) -> None:
        """State code with 1 character raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Address(
                street="123 Main St",
                city="Austin",
                state="T",  # Invalid: too short
                zip_code="78701",
            )
        assert "state" in str(exc_info.value)

    def test_invalid_zip_code_four_digits(self) -> None:
        """ZIP code with 4 digits raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Address(
                street="123 Main St",
                city="Austin",
                state="TX",
                zip_code="7870",  # Invalid: only 4 digits
            )
        assert "zip_code" in str(exc_info.value)

    def test_valid_zip_code_five_plus_four(self) -> None:
        """Valid 5+4 ZIP code passes validation."""
        address = Address(
            street="123 Main St",
            city="Austin",
            state="TX",
            zip_code="78701-6789",
        )
        assert address.zip_code == "78701-6789"

    def test_invalid_zip_code_wrong_plus_four_format(self) -> None:
        """ZIP+4 with wrong format (too few digits after dash) raises error."""
        with pytest.raises(ValidationError) as exc_info:
            Address(
                street="123 Main St",
                city="Austin",
                state="TX",
                zip_code="78701-67",  # Invalid: only 2 digits after dash
            )
        assert "zip_code" in str(exc_info.value)


# =============================================================================
# IncomeRecord Validation Tests
# =============================================================================


class TestIncomeRecordValidation:
    """Tests for IncomeRecord model validation."""

    def test_valid_income_record(self) -> None:
        """Valid income record passes validation."""
        income = IncomeRecord(
            amount=Decimal("75000.00"),
            period="annual",
            year=2024,
            source_type="employment",
            employer="Acme Corp",
        )
        assert income.amount == Decimal("75000.00")
        assert income.period == "annual"
        assert income.year == 2024
        assert income.employer == "Acme Corp"

    def test_zero_amount_raises_error(self) -> None:
        """Zero income amount raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            IncomeRecord(
                amount=Decimal("0"),
                period="annual",
                year=2024,
                source_type="employment",
            )
        assert "amount" in str(exc_info.value)

    def test_negative_amount_raises_error(self) -> None:
        """Negative income amount raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            IncomeRecord(
                amount=Decimal("-1000"),
                period="annual",
                year=2024,
                source_type="employment",
            )
        assert "amount" in str(exc_info.value)

    def test_invalid_period_raises_error(self) -> None:
        """Invalid income period raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            IncomeRecord(
                amount=Decimal("50000"),
                period="daily",  # Invalid: not in allowed set
                year=2024,
                source_type="employment",
            )
        assert "period" in str(exc_info.value)

    def test_period_is_lowercased(self) -> None:
        """Period value is automatically lowercased."""
        income = IncomeRecord(
            amount=Decimal("50000"),
            period="ANNUAL",  # Uppercase should be normalized
            year=2024,
            source_type="employment",
        )
        assert income.period == "annual"

    def test_period_mixed_case_normalized(self) -> None:
        """Mixed case period is normalized to lowercase."""
        income = IncomeRecord(
            amount=Decimal("6000"),
            period="BiWeekly",
            year=2024,
            source_type="employment",
        )
        assert income.period == "biweekly"


# =============================================================================
# SourceReference Validation Tests
# =============================================================================


class TestSourceReferenceValidation:
    """Tests for SourceReference model validation."""

    def test_valid_source_reference(self) -> None:
        """Valid source reference passes validation."""
        doc_id = uuid4()
        source = SourceReference(
            document_id=doc_id,
            document_name="loan_application.pdf",
            page_number=1,
            section="Personal Information",
            snippet="John Doe, 123 Main St",
        )
        assert source.document_id == doc_id
        assert source.page_number == 1
        assert source.section == "Personal Information"

    def test_page_number_zero_raises_error(self) -> None:
        """Page number 0 raises ValidationError (must be >= 1)."""
        with pytest.raises(ValidationError) as exc_info:
            SourceReference(
                document_id=uuid4(),
                document_name="test.pdf",
                page_number=0,  # Invalid: must be >= 1
                snippet="test snippet",
            )
        assert "page_number" in str(exc_info.value)

    def test_snippet_over_max_length_raises_error(self) -> None:
        """Snippet over 500 characters raises ValidationError."""
        long_snippet = "x" * 501
        with pytest.raises(ValidationError) as exc_info:
            SourceReference(
                document_id=uuid4(),
                document_name="test.pdf",
                page_number=1,
                snippet=long_snippet,
            )
        assert "snippet" in str(exc_info.value)

    def test_snippet_exactly_max_length_passes(self) -> None:
        """Snippet exactly at max length passes validation."""
        snippet_500 = "x" * 500
        source = SourceReference(
            document_id=uuid4(),
            document_name="test.pdf",
            page_number=1,
            snippet=snippet_500,
        )
        assert len(source.snippet) == 500


# =============================================================================
# BorrowerRecord Tests
# =============================================================================


class TestBorrowerRecordComplete:
    """Tests for complete BorrowerRecord with all nested objects."""

    def test_full_borrower_record(self) -> None:
        """Create full BorrowerRecord with all nested objects."""
        doc_id = uuid4()
        borrower = BorrowerRecord(
            name="John Doe",
            ssn="123-45-6789",
            phone="(512) 555-1234",
            email="john.doe@example.com",
            address=Address(
                street="123 Main St",
                city="Austin",
                state="TX",
                zip_code="78701",
            ),
            income_history=[
                IncomeRecord(
                    amount=Decimal("75000"),
                    period="annual",
                    year=2024,
                    source_type="employment",
                    employer="Acme Corp",
                ),
                IncomeRecord(
                    amount=Decimal("72000"),
                    period="annual",
                    year=2023,
                    source_type="employment",
                    employer="Acme Corp",
                ),
            ],
            account_numbers=["****1234", "****5678"],
            loan_numbers=["LN-2024-001"],
            sources=[
                SourceReference(
                    document_id=doc_id,
                    document_name="loan_app.pdf",
                    page_number=1,
                    snippet="John Doe, 123 Main St",
                ),
            ],
            confidence_score=0.85,
        )

        assert borrower.name == "John Doe"
        assert borrower.ssn == "123-45-6789"
        assert borrower.address is not None
        assert borrower.address.city == "Austin"
        assert len(borrower.income_history) == 2
        assert borrower.income_history[0].amount == Decimal("75000")
        assert len(borrower.sources) == 1
        assert isinstance(borrower.sources[0], SourceReference)
        assert borrower.confidence_score == 0.85

    def test_borrower_record_minimal(self) -> None:
        """Create BorrowerRecord with only required fields."""
        borrower = BorrowerRecord(
            name="Jane Doe",
            confidence_score=0.5,
        )

        assert borrower.name == "Jane Doe"
        assert borrower.ssn is None
        assert borrower.phone is None
        assert borrower.email is None
        assert borrower.address is None
        assert borrower.income_history == []
        assert borrower.account_numbers == []
        assert borrower.loan_numbers == []
        assert borrower.sources == []
        assert borrower.confidence_score == 0.5
        assert borrower.id is not None  # Auto-generated UUID
        assert borrower.extracted_at is not None  # Auto-generated timestamp


class TestBorrowerRecordSSNValidation:
    """Tests for SSN pattern validation."""

    def test_valid_ssn_format(self) -> None:
        """Valid SSN format passes validation."""
        borrower = BorrowerRecord(
            name="Test User",
            ssn="123-45-6789",
            confidence_score=0.8,
        )
        assert borrower.ssn == "123-45-6789"

    def test_invalid_ssn_format_no_dashes(self) -> None:
        """SSN without dashes raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            BorrowerRecord(
                name="Test User",
                ssn="123456789",  # Invalid: missing dashes
                confidence_score=0.8,
            )
        assert "ssn" in str(exc_info.value)

    def test_invalid_ssn_format_wrong_pattern(self) -> None:
        """SSN with wrong dash pattern raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            BorrowerRecord(
                name="Test User",
                ssn="12-345-6789",  # Invalid: wrong dash positions
                confidence_score=0.8,
            )
        assert "ssn" in str(exc_info.value)


# =============================================================================
# JSON Serialization Tests
# =============================================================================


class TestModelJsonRoundtrip:
    """Tests for JSON serialization and deserialization."""

    def test_borrower_json_roundtrip(self) -> None:
        """BorrowerRecord serializes to JSON and deserializes back correctly."""
        original = BorrowerRecord(
            name="John Doe",
            address=Address(
                street="123 Main St",
                city="Austin",
                state="TX",
                zip_code="78701",
            ),
            income_history=[
                IncomeRecord(
                    amount=Decimal("75000"),
                    period="annual",
                    year=2024,
                    source_type="employment",
                    employer="Acme Corp",
                ),
            ],
            sources=[
                SourceReference(
                    document_id=uuid4(),
                    document_name="loan_app.pdf",
                    page_number=1,
                    snippet="John Doe, 123 Main St",
                ),
            ],
            confidence_score=0.85,
        )

        # Serialize to JSON string
        json_str = original.model_dump_json()
        assert isinstance(json_str, str)

        # Deserialize back
        restored = BorrowerRecord.model_validate_json(json_str)

        # Verify all fields match
        assert restored.name == original.name
        assert restored.confidence_score == original.confidence_score
        assert restored.id == original.id
        assert original.address is not None
        assert restored.address is not None
        assert restored.address.street == original.address.street
        assert restored.address.city == original.address.city
        assert len(restored.income_history) == 1
        assert restored.income_history[0].amount == original.income_history[0].amount
        assert len(restored.sources) == 1
        assert restored.sources[0].document_name == original.sources[0].document_name

    def test_model_dict_json_mode_serialization(self) -> None:
        """model_dump(mode='json') produces JSON-compatible dict."""
        borrower = BorrowerRecord(
            name="John Doe",
            address=Address(
                street="123 Main St",
                city="Austin",
                state="TX",
                zip_code="78701",
            ),
            income_history=[
                IncomeRecord(
                    amount=Decimal("75000.50"),
                    period="annual",
                    year=2024,
                    source_type="employment",
                ),
            ],
            confidence_score=0.85,
        )

        json_dict = borrower.model_dump(mode="json")

        # Datetime should be serialized to ISO string
        assert isinstance(json_dict["extracted_at"], str)
        assert "T" in json_dict["extracted_at"]  # ISO format contains T

        # UUID should be serialized to string
        assert isinstance(json_dict["id"], str)

        # Decimal should be serialized (as string by default in JSON mode)
        # Note: Pydantic serializes Decimal as string in JSON mode
        income_amount = json_dict["income_history"][0]["amount"]
        assert income_amount == "75000.50" or income_amount == 75000.5


# =============================================================================
# Confidence Score Bounds Tests
# =============================================================================


class TestConfidenceScoreBounds:
    """Tests for confidence_score field validation bounds."""

    def test_confidence_score_zero_passes(self) -> None:
        """confidence_score=0.0 passes validation."""
        borrower = BorrowerRecord(
            name="Test User",
            confidence_score=0.0,
        )
        assert borrower.confidence_score == 0.0

    def test_confidence_score_one_passes(self) -> None:
        """confidence_score=1.0 passes validation."""
        borrower = BorrowerRecord(
            name="Test User",
            confidence_score=1.0,
        )
        assert borrower.confidence_score == 1.0

    def test_confidence_score_negative_raises_error(self) -> None:
        """confidence_score=-0.1 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            BorrowerRecord(
                name="Test User",
                confidence_score=-0.1,
            )
        assert "confidence_score" in str(exc_info.value)

    def test_confidence_score_above_one_raises_error(self) -> None:
        """confidence_score=1.1 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            BorrowerRecord(
                name="Test User",
                confidence_score=1.1,
            )
        assert "confidence_score" in str(exc_info.value)


# =============================================================================
# DocumentMetadata Tests
# =============================================================================


class TestDocumentMetadataStatus:
    """Tests for DocumentMetadata status validation."""

    def test_valid_status_pending(self) -> None:
        """Status 'pending' passes validation."""
        doc = DocumentMetadata(
            filename="test.pdf",
            file_hash="abc123",
            file_type="pdf",
            file_size_bytes=1024,
            status="pending",
        )
        assert doc.status == "pending"

    def test_valid_status_completed(self) -> None:
        """Status 'completed' passes validation."""
        doc = DocumentMetadata(
            filename="test.pdf",
            file_hash="abc123",
            file_type="pdf",
            file_size_bytes=1024,
            status="completed",
        )
        assert doc.status == "completed"

    def test_valid_status_processing(self) -> None:
        """Status 'processing' passes validation."""
        doc = DocumentMetadata(
            filename="test.pdf",
            file_hash="abc123",
            file_type="pdf",
            file_size_bytes=1024,
            status="processing",
        )
        assert doc.status == "processing"

    def test_valid_status_failed(self) -> None:
        """Status 'failed' passes validation."""
        doc = DocumentMetadata(
            filename="test.pdf",
            file_hash="abc123",
            file_type="pdf",
            file_size_bytes=1024,
            status="failed",
            error_message="Processing error",
        )
        assert doc.status == "failed"
        assert doc.error_message == "Processing error"

    def test_invalid_status_raises_error(self) -> None:
        """Invalid status 'unknown' raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            DocumentMetadata(
                filename="test.pdf",
                file_hash="abc123",
                file_type="pdf",
                file_size_bytes=1024,
                status="unknown",  # type: ignore[arg-type]  # Intentional invalid value
            )
        assert "status" in str(exc_info.value)

    def test_valid_file_types(self) -> None:
        """All valid file types pass validation."""
        from typing import Literal

        file_types: list[Literal["pdf", "docx", "png", "jpg", "jpeg"]] = [
            "pdf",
            "docx",
            "png",
            "jpg",
            "jpeg",
        ]
        for file_type in file_types:
            doc = DocumentMetadata(
                filename=f"test.{file_type}",
                file_hash="abc123",
                file_type=file_type,
                file_size_bytes=1024,
            )
            assert doc.file_type == file_type

    def test_invalid_file_type_raises_error(self) -> None:
        """Invalid file type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            DocumentMetadata(
                filename="test.txt",
                file_hash="abc123",
                file_type="txt",  # type: ignore[arg-type]  # Intentional invalid value
                file_size_bytes=1024,
            )
        assert "file_type" in str(exc_info.value)

    def test_default_status_is_pending(self) -> None:
        """Default status is 'pending' when not specified."""
        doc = DocumentMetadata(
            filename="test.pdf",
            file_hash="abc123",
            file_type="pdf",
            file_size_bytes=1024,
        )
        assert doc.status == "pending"
