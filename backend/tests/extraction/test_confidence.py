"""Tests for confidence scoring module."""

from decimal import Decimal

import pytest

from src.extraction.confidence import ConfidenceBreakdown, ConfidenceCalculator
from src.models.borrower import Address, BorrowerRecord, IncomeRecord


class TestConfidenceCalculator:
    """Tests for ConfidenceCalculator class."""

    @pytest.fixture
    def calculator(self) -> ConfidenceCalculator:
        """Create a ConfidenceCalculator instance."""
        return ConfidenceCalculator()

    @pytest.fixture
    def minimal_record(self) -> BorrowerRecord:
        """Record with only name (minimum required)."""
        return BorrowerRecord(
            name="John Doe",
            confidence_score=0.5,  # Placeholder, will be calculated
        )

    @pytest.fixture
    def complete_record(self) -> BorrowerRecord:
        """Record with all fields populated."""
        return BorrowerRecord(
            name="John Doe",
            ssn="123-45-6789",
            phone="212-555-1234",
            address=Address(
                street="123 Main St",
                city="New York",
                state="NY",
                zip_code="10001",
            ),
            income_history=[
                IncomeRecord(
                    amount=Decimal("75000"),
                    period="annual",
                    year=2024,
                    source_type="employment",
                    employer="Acme Corp",
                )
            ],
            account_numbers=["1234567890"],
            loan_numbers=["LOAN-001"],
            confidence_score=1.0,  # Placeholder
        )

    def test_minimal_record_low_confidence(
        self, calculator: ConfidenceCalculator, minimal_record: BorrowerRecord
    ) -> None:
        """Record with only name has low confidence (~0.6)."""
        breakdown = calculator.calculate(
            record=minimal_record,
            format_validation_passed=False,
            source_count=1,
        )
        # Base 0.5 + name 0.1 = 0.6
        assert breakdown.total == pytest.approx(0.6, abs=0.01)
        assert breakdown.requires_review is True

    def test_complete_record_high_confidence(
        self, calculator: ConfidenceCalculator, complete_record: BorrowerRecord
    ) -> None:
        """Record with all fields + valid + multi-source gets 1.0."""
        breakdown = calculator.calculate(
            record=complete_record,
            format_validation_passed=True,
            source_count=2,
        )
        # Base 0.5 + required 0.2 + optional 0.15 + multi 0.1 + validation 0.15 = 1.1 -> capped at 1.0
        assert breakdown.total == 1.0
        assert breakdown.requires_review is False

    def test_review_threshold(
        self, calculator: ConfidenceCalculator, minimal_record: BorrowerRecord
    ) -> None:
        """Score 0.65 triggers requires_review=True."""
        # Minimal with validation = 0.5 + 0.1 + 0.15 = 0.75 (above threshold)
        # Without validation = 0.5 + 0.1 = 0.6 (below threshold)
        breakdown = calculator.calculate(
            record=minimal_record,
            format_validation_passed=False,
            source_count=1,
        )
        assert breakdown.total == pytest.approx(0.6, abs=0.01)
        assert breakdown.requires_review is True

    def test_no_review_above_threshold(
        self, calculator: ConfidenceCalculator
    ) -> None:
        """Score 0.75 does not trigger requires_review."""
        # Record with name + validation bonus = 0.5 + 0.1 + 0.15 = 0.75
        record = BorrowerRecord(name="John Doe", confidence_score=0.5)
        breakdown = calculator.calculate(
            record=record,
            format_validation_passed=True,
            source_count=1,
        )
        assert breakdown.total == pytest.approx(0.75, abs=0.01)
        assert breakdown.requires_review is False

    def test_bonus_capped_at_max(
        self, calculator: ConfidenceCalculator, complete_record: BorrowerRecord
    ) -> None:
        """Individual bonuses don't exceed their caps."""
        breakdown = calculator.calculate(
            record=complete_record,
            format_validation_passed=True,
            source_count=2,
        )
        # Required fields max is 0.2
        assert breakdown.required_fields_bonus <= 0.2
        # Optional fields max is 0.15
        assert breakdown.optional_fields_bonus <= 0.15

    def test_total_capped_at_one(
        self, calculator: ConfidenceCalculator, complete_record: BorrowerRecord
    ) -> None:
        """Total confidence never exceeds 1.0."""
        breakdown = calculator.calculate(
            record=complete_record,
            format_validation_passed=True,
            source_count=2,
        )
        # Sum would be 1.1, but should be capped
        assert breakdown.total == 1.0
        assert breakdown.total <= 1.0

    def test_multi_source_bonus_applied(
        self, calculator: ConfidenceCalculator, minimal_record: BorrowerRecord
    ) -> None:
        """Multi-source bonus is applied when source_count > 1."""
        single_source = calculator.calculate(
            record=minimal_record,
            format_validation_passed=False,
            source_count=1,
        )
        multi_source = calculator.calculate(
            record=minimal_record,
            format_validation_passed=False,
            source_count=2,
        )
        assert multi_source.total - single_source.total == pytest.approx(0.1, abs=0.01)
        assert multi_source.multi_source_bonus == 0.1
        assert single_source.multi_source_bonus == 0.0

    def test_validation_bonus_applied(
        self, calculator: ConfidenceCalculator, minimal_record: BorrowerRecord
    ) -> None:
        """Validation bonus is applied when format_validation_passed=True."""
        no_validation = calculator.calculate(
            record=minimal_record,
            format_validation_passed=False,
            source_count=1,
        )
        with_validation = calculator.calculate(
            record=minimal_record,
            format_validation_passed=True,
            source_count=1,
        )
        assert with_validation.total - no_validation.total == pytest.approx(0.15, abs=0.01)
        assert with_validation.validation_bonus == 0.15
        assert no_validation.validation_bonus == 0.0

    def test_address_bonus(self, calculator: ConfidenceCalculator) -> None:
        """Address presence adds to required fields bonus."""
        no_address = BorrowerRecord(name="John Doe", confidence_score=0.5)
        with_address = BorrowerRecord(
            name="John Doe",
            address=Address(
                street="123 Main St",
                city="City",
                state="TX",
                zip_code="12345",
            ),
            confidence_score=0.5,
        )

        breakdown_no_addr = calculator.calculate(
            record=no_address, format_validation_passed=False, source_count=1
        )
        breakdown_with_addr = calculator.calculate(
            record=with_address, format_validation_passed=False, source_count=1
        )

        assert breakdown_with_addr.required_fields_bonus == 0.2  # name + address
        assert breakdown_no_addr.required_fields_bonus == 0.1  # name only


class TestConfidenceBreakdown:
    """Tests for ConfidenceBreakdown dataclass."""

    def test_breakdown_fields(self) -> None:
        """ConfidenceBreakdown has all required fields."""
        breakdown = ConfidenceBreakdown(
            base_score=0.5,
            required_fields_bonus=0.2,
            optional_fields_bonus=0.15,
            multi_source_bonus=0.1,
            validation_bonus=0.15,
            total=1.0,
            requires_review=False,
        )
        assert breakdown.base_score == 0.5
        assert breakdown.required_fields_bonus == 0.2
        assert breakdown.optional_fields_bonus == 0.15
        assert breakdown.multi_source_bonus == 0.1
        assert breakdown.validation_bonus == 0.15
        assert breakdown.total == 1.0
        assert breakdown.requires_review is False
