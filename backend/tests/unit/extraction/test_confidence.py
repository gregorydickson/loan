"""Unit tests for ConfidenceCalculator.

Tests confidence score calculation for extracted borrower records:
- Base scoring logic with field completeness
- Required fields bonus (name, address)
- Optional fields bonus (income, accounts, loans)
- Multi-source corroboration bonus
- Format validation bonus
- Review threshold flagging
- Bonus capping logic
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from src.extraction.confidence import ConfidenceBreakdown, ConfidenceCalculator
from src.models.borrower import Address, BorrowerRecord, IncomeRecord


class TestConfidenceCalculatorBasics:
    """Tests for basic confidence calculation functionality."""

    @pytest.fixture
    def calculator(self) -> ConfidenceCalculator:
        """Create calculator instance."""
        return ConfidenceCalculator()

    def test_minimal_record_gets_base_score_only(self, calculator):
        """Minimal record (1-char name) gets only base score of 0.5."""
        record = BorrowerRecord(
            id=uuid4(),
            name="J",  # Single char (min valid)
            confidence_score=Decimal("0.0"),
            extracted_at=datetime.now(UTC),
        )
        breakdown = calculator.calculate(
            record=record, format_validation_passed=False, source_count=1
        )
        assert breakdown.base_score == 0.5
        assert breakdown.required_fields_bonus == 0.0
        assert breakdown.optional_fields_bonus == 0.0
        assert breakdown.multi_source_bonus == 0.0
        assert breakdown.validation_bonus == 0.0
        assert breakdown.total == 0.5
        assert breakdown.requires_review is True  # Below 0.7 threshold

    def test_single_char_name_does_not_get_bonus(self, calculator):
        """Name with 1 character doesn't get required field bonus."""
        record = BorrowerRecord(
            id=uuid4(),
            name="J",  # Single char
            confidence_score=Decimal("0.0"),
            extracted_at=datetime.now(UTC),
        )
        breakdown = calculator.calculate(
            record=record, format_validation_passed=False, source_count=1
        )
        assert breakdown.required_fields_bonus == 0.0

    def test_valid_name_gets_bonus(self, calculator):
        """Name with 2+ characters gets required field bonus."""
        record = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            confidence_score=Decimal("0.0"),
            extracted_at=datetime.now(UTC),
        )
        breakdown = calculator.calculate(
            record=record, format_validation_passed=False, source_count=1
        )
        assert breakdown.required_fields_bonus == 0.1

    def test_address_gets_required_field_bonus(self, calculator):
        """Record with address (but single-char name) gets address bonus only."""
        record = BorrowerRecord(
            id=uuid4(),
            name="J",  # Single char (doesn't get name bonus)
            address=Address(
                street="123 Main St", city="Austin", state="TX", zip_code="78701"
            ),
            confidence_score=Decimal("0.0"),
            extracted_at=datetime.now(UTC),
        )
        breakdown = calculator.calculate(
            record=record, format_validation_passed=False, source_count=1
        )
        assert breakdown.required_fields_bonus == 0.1

    def test_name_and_address_get_max_required_bonus(self, calculator):
        """Record with name and address gets max required bonus (0.2)."""
        record = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            address=Address(
                street="123 Main St", city="Austin", state="TX", zip_code="78701"
            ),
            confidence_score=Decimal("0.0"),
            extracted_at=datetime.now(UTC),
        )
        breakdown = calculator.calculate(
            record=record, format_validation_passed=False, source_count=1
        )
        assert breakdown.required_fields_bonus == 0.2  # Capped at max


class TestOptionalFieldsBonuses:
    """Tests for optional fields bonus calculation."""

    @pytest.fixture
    def calculator(self) -> ConfidenceCalculator:
        """Create calculator instance."""
        return ConfidenceCalculator()

    def test_income_history_gets_bonus(self, calculator):
        """Record with income history gets optional field bonus."""
        record = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            income_history=[
                IncomeRecord(
                    amount=Decimal("100000"),
                    period="annual",
                    year=2024,
                    source_type="W2",
                )
            ],
            confidence_score=Decimal("0.0"),
            extracted_at=datetime.now(UTC),
        )
        breakdown = calculator.calculate(
            record=record, format_validation_passed=False, source_count=1
        )
        assert breakdown.optional_fields_bonus == 0.05

    def test_account_numbers_get_bonus(self, calculator):
        """Record with account numbers gets optional field bonus."""
        record = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            account_numbers=["12345"],
            confidence_score=Decimal("0.0"),
            extracted_at=datetime.now(UTC),
        )
        breakdown = calculator.calculate(
            record=record, format_validation_passed=False, source_count=1
        )
        assert breakdown.optional_fields_bonus == 0.05

    def test_loan_numbers_get_bonus(self, calculator):
        """Record with loan numbers gets optional field bonus."""
        record = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            loan_numbers=["LOAN123"],
            confidence_score=Decimal("0.0"),
            extracted_at=datetime.now(UTC),
        )
        breakdown = calculator.calculate(
            record=record, format_validation_passed=False, source_count=1
        )
        assert breakdown.optional_fields_bonus == 0.05

    def test_all_optional_fields_get_max_bonus(self, calculator):
        """All optional fields reach max bonus of 0.15."""
        record = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            income_history=[
                IncomeRecord(
                    amount=Decimal("100000"),
                    period="annual",
                    year=2024,
                    source_type="W2",
                )
            ],
            account_numbers=["12345"],
            loan_numbers=["LOAN123"],
            confidence_score=Decimal("0.0"),
            extracted_at=datetime.now(UTC),
        )
        breakdown = calculator.calculate(
            record=record, format_validation_passed=False, source_count=1
        )
        assert breakdown.optional_fields_bonus == 0.15  # Capped at max

    def test_empty_lists_get_no_bonus(self, calculator):
        """Empty lists don't get optional field bonuses."""
        record = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            income_history=[],  # Empty list
            account_numbers=[],  # Empty list
            loan_numbers=[],  # Empty list
            confidence_score=Decimal("0.0"),
            extracted_at=datetime.now(UTC),
        )
        breakdown = calculator.calculate(
            record=record, format_validation_passed=False, source_count=1
        )
        assert breakdown.optional_fields_bonus == 0.0


class TestMultiSourceBonus:
    """Tests for multi-source corroboration bonus."""

    @pytest.fixture
    def calculator(self) -> ConfidenceCalculator:
        """Create calculator instance."""
        return ConfidenceCalculator()

    def test_single_source_no_bonus(self, calculator):
        """Single source (source_count=1) gets no multi-source bonus."""
        record = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            confidence_score=Decimal("0.0"),
            extracted_at=datetime.now(UTC),
        )
        breakdown = calculator.calculate(
            record=record, format_validation_passed=False, source_count=1
        )
        assert breakdown.multi_source_bonus == 0.0

    def test_two_sources_get_bonus(self, calculator):
        """Two sources get multi-source bonus."""
        record = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            confidence_score=Decimal("0.0"),
            extracted_at=datetime.now(UTC),
        )
        breakdown = calculator.calculate(
            record=record, format_validation_passed=False, source_count=2
        )
        assert breakdown.multi_source_bonus == 0.1

    def test_many_sources_get_same_bonus(self, calculator):
        """Many sources still get same 0.1 bonus (not multiplied)."""
        record = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            confidence_score=Decimal("0.0"),
            extracted_at=datetime.now(UTC),
        )
        breakdown = calculator.calculate(
            record=record, format_validation_passed=False, source_count=5
        )
        assert breakdown.multi_source_bonus == 0.1  # Fixed bonus, not scaled


class TestValidationBonus:
    """Tests for format validation bonus."""

    @pytest.fixture
    def calculator(self) -> ConfidenceCalculator:
        """Create calculator instance."""
        return ConfidenceCalculator()

    def test_validation_passed_gets_bonus(self, calculator):
        """Format validation passed gets bonus."""
        record = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            confidence_score=Decimal("0.0"),
            extracted_at=datetime.now(UTC),
        )
        breakdown = calculator.calculate(
            record=record, format_validation_passed=True, source_count=1
        )
        assert breakdown.validation_bonus == 0.15

    def test_validation_failed_no_bonus(self, calculator):
        """Format validation failed gets no bonus."""
        record = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            confidence_score=Decimal("0.0"),
            extracted_at=datetime.now(UTC),
        )
        breakdown = calculator.calculate(
            record=record, format_validation_passed=False, source_count=1
        )
        assert breakdown.validation_bonus == 0.0


class TestReviewThreshold:
    """Tests for review flagging logic."""

    @pytest.fixture
    def calculator(self) -> ConfidenceCalculator:
        """Create calculator instance."""
        return ConfidenceCalculator()

    def test_below_threshold_requires_review(self, calculator):
        """Score below 0.7 requires review."""
        record = BorrowerRecord(
            id=uuid4(),
            name="John Smith",  # 0.5 + 0.1 = 0.6
            confidence_score=Decimal("0.0"),
            extracted_at=datetime.now(UTC),
        )
        breakdown = calculator.calculate(
            record=record, format_validation_passed=False, source_count=1
        )
        assert breakdown.total == 0.6
        assert breakdown.requires_review is True

    def test_at_threshold_no_review(self, calculator):
        """Score at exactly 0.7 does not require review."""
        record = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            address=Address(
                street="123 Main St", city="Austin", state="TX", zip_code="78701"
            ),
            # 0.5 base + 0.2 required = 0.7 exactly
            confidence_score=Decimal("0.0"),
            extracted_at=datetime.now(UTC),
        )
        breakdown = calculator.calculate(
            record=record, format_validation_passed=False, source_count=1
        )
        assert breakdown.total == 0.7
        assert breakdown.requires_review is False

    def test_above_threshold_no_review(self, calculator):
        """Score above 0.7 does not require review."""
        record = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            address=Address(
                street="123 Main St", city="Austin", state="TX", zip_code="78701"
            ),
            income_history=[
                IncomeRecord(
                    amount=Decimal("100000"),
                    period="annual",
                    year=2024,
                    source_type="W2",
                )
            ],
            # 0.5 base + 0.2 required + 0.05 optional = 0.75
            confidence_score=Decimal("0.0"),
            extracted_at=datetime.now(UTC),
        )
        breakdown = calculator.calculate(
            record=record, format_validation_passed=False, source_count=1
        )
        assert breakdown.total == 0.75
        assert breakdown.requires_review is False


class TestMaximumScore:
    """Tests for score capping at 1.0."""

    @pytest.fixture
    def calculator(self) -> ConfidenceCalculator:
        """Create calculator instance."""
        return ConfidenceCalculator()

    def test_perfect_record_capped_at_one(self, calculator):
        """Perfect record with all bonuses is capped at 1.0."""
        record = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            address=Address(
                street="123 Main St", city="Austin", state="TX", zip_code="78701"
            ),
            income_history=[
                IncomeRecord(
                    amount=Decimal("100000"),
                    period="annual",
                    year=2024,
                    source_type="W2",
                )
            ],
            account_numbers=["12345"],
            loan_numbers=["LOAN123"],
            confidence_score=Decimal("0.0"),
            extracted_at=datetime.now(UTC),
        )
        # 0.5 base + 0.2 required + 0.15 optional + 0.1 multi + 0.15 validation
        # = 1.1, but capped at 1.0
        breakdown = calculator.calculate(
            record=record, format_validation_passed=True, source_count=2
        )
        assert breakdown.total == 1.0  # Capped
        assert breakdown.requires_review is False

    def test_breakdown_shows_actual_bonuses(self, calculator):
        """Breakdown shows actual bonuses before capping."""
        record = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            address=Address(
                street="123 Main St", city="Austin", state="TX", zip_code="78701"
            ),
            income_history=[
                IncomeRecord(
                    amount=Decimal("100000"),
                    period="annual",
                    year=2024,
                    source_type="W2",
                )
            ],
            account_numbers=["12345"],
            loan_numbers=["LOAN123"],
            confidence_score=Decimal("0.0"),
            extracted_at=datetime.now(UTC),
        )
        breakdown = calculator.calculate(
            record=record, format_validation_passed=True, source_count=2
        )
        # Individual bonuses should be correct even though total is capped
        assert breakdown.base_score == 0.5
        assert breakdown.required_fields_bonus == 0.2
        assert breakdown.optional_fields_bonus == 0.15
        assert breakdown.multi_source_bonus == 0.1
        assert breakdown.validation_bonus == 0.15
        assert breakdown.total == 1.0  # Sum would be 1.1, but capped


class TestConfidenceBreakdownStructure:
    """Tests for ConfidenceBreakdown dataclass."""

    def test_breakdown_has_all_fields(self):
        """ConfidenceBreakdown contains all required fields."""
        breakdown = ConfidenceBreakdown(
            base_score=0.5,
            required_fields_bonus=0.2,
            optional_fields_bonus=0.1,
            multi_source_bonus=0.1,
            validation_bonus=0.15,
            total=1.0,
            requires_review=False,
        )
        assert breakdown.base_score == 0.5
        assert breakdown.required_fields_bonus == 0.2
        assert breakdown.optional_fields_bonus == 0.1
        assert breakdown.multi_source_bonus == 0.1
        assert breakdown.validation_bonus == 0.15
        assert breakdown.total == 1.0
        assert breakdown.requires_review is False


class TestConfidenceConstants:
    """Tests for ConfidenceCalculator constants."""

    def test_constants_are_accessible(self):
        """All calculator constants are accessible."""
        calculator = ConfidenceCalculator()
        assert calculator.REVIEW_THRESHOLD == 0.7
        assert calculator.BASE_SCORE == 0.5
        assert calculator.REQUIRED_FIELDS_MAX == 0.2
        assert calculator.OPTIONAL_FIELDS_MAX == 0.15
        assert calculator.REQUIRED_FIELD_BONUS == 0.1
        assert calculator.OPTIONAL_FIELD_BONUS == 0.05
        assert calculator.MULTI_SOURCE_BONUS == 0.1
        assert calculator.VALIDATION_BONUS == 0.15
