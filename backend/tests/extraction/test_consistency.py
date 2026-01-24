"""Tests for ConsistencyValidator cross-document and within-record checks.

Tests cover:
- No warnings for clean single-source data
- Address conflict detection for multi-source borrowers
- Income drop detection (>50% year-over-year)
- Income spike detection (>300% year-over-year)
- Stable income progression (no warnings for normal changes)
- Cross-document same-name different-SSN detection
- Cross-document same-name same-SSN (no warning)
- Combined validation returning all warnings
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from src.extraction.consistency import ConsistencyValidator, ConsistencyWarning
from src.models.borrower import Address, BorrowerRecord, IncomeRecord
from src.models.document import SourceReference


@pytest.fixture
def validator() -> ConsistencyValidator:
    """Create a ConsistencyValidator instance."""
    return ConsistencyValidator()


def _make_source(doc_name: str = "test.pdf", page: int = 1) -> SourceReference:
    """Create a SourceReference for testing."""
    return SourceReference(
        document_id=uuid4(),
        document_name=doc_name,
        page_number=page,
        snippet="Sample text...",
    )


def _make_address(zip_code: str = "75001") -> Address:
    """Create an Address for testing."""
    return Address(
        street="123 Main St",
        city="Dallas",
        state="TX",
        zip_code=zip_code,
    )


def _make_income(year: int, amount: Decimal) -> IncomeRecord:
    """Create an IncomeRecord for testing."""
    return IncomeRecord(
        amount=amount,
        period="annual",
        year=year,
        source_type="employment",
    )


def _make_borrower(
    name: str = "John Smith",
    ssn: str | None = None,
    address: Address | None = None,
    sources: list[SourceReference] | None = None,
    income_history: list[IncomeRecord] | None = None,
) -> BorrowerRecord:
    """Create a BorrowerRecord for testing."""
    return BorrowerRecord(
        id=uuid4(),
        name=name,
        ssn=ssn,
        address=address,
        sources=sources or [_make_source()],
        income_history=income_history or [],
        confidence_score=0.8,
    )


class TestNoWarningsForCleanData:
    """Tests for data that should not trigger warnings."""

    def test_no_warnings_for_single_source(
        self, validator: ConsistencyValidator
    ) -> None:
        """Single source borrower with stable income generates no warnings."""
        borrower = _make_borrower(
            address=_make_address(),
            sources=[_make_source()],
            income_history=[
                _make_income(2023, Decimal("50000")),
                _make_income(2024, Decimal("52000")),  # 4% increase - normal
            ],
        )

        warnings = validator.validate([borrower])

        assert len(warnings) == 0

    def test_no_warnings_for_empty_list(
        self, validator: ConsistencyValidator
    ) -> None:
        """Empty borrower list generates no warnings."""
        warnings = validator.validate([])
        assert len(warnings) == 0


class TestAddressConflicts:
    """Tests for address conflict detection."""

    def test_address_conflict_multiple_sources(
        self, validator: ConsistencyValidator
    ) -> None:
        """Borrower with 3 sources is flagged for address verification."""
        borrower = _make_borrower(
            name="Jane Doe",
            address=_make_address("75001"),
            sources=[
                _make_source("doc1.pdf"),
                _make_source("doc2.pdf"),
                _make_source("doc3.pdf"),
            ],
        )

        warnings = validator.validate([borrower])

        assert len(warnings) == 1
        warning = warnings[0]
        assert warning.warning_type == "ADDRESS_CONFLICT"
        assert warning.field == "address"
        assert "Jane Doe" in warning.message
        assert warning.details["source_count"] == 3
        assert warning.details["current_address"]["zip_code"] == "75001"

    def test_no_warning_for_single_source_with_address(
        self, validator: ConsistencyValidator
    ) -> None:
        """Single source borrower with address is not flagged."""
        borrower = _make_borrower(
            address=_make_address(),
            sources=[_make_source()],
        )

        warnings = validator.check_address_conflicts(borrower)

        assert len(warnings) == 0

    def test_no_warning_for_multi_source_without_address(
        self, validator: ConsistencyValidator
    ) -> None:
        """Multi-source borrower without address is not flagged."""
        borrower = _make_borrower(
            address=None,
            sources=[_make_source("doc1.pdf"), _make_source("doc2.pdf")],
        )

        warnings = validator.check_address_conflicts(borrower)

        assert len(warnings) == 0


class TestIncomeProgression:
    """Tests for income progression validation."""

    def test_income_drop_detected(
        self, validator: ConsistencyValidator
    ) -> None:
        """60% income drop is flagged."""
        borrower = _make_borrower(
            income_history=[
                _make_income(2023, Decimal("100000")),
                _make_income(2024, Decimal("40000")),  # 60% drop
            ],
        )

        warnings = validator.validate_income_progression(borrower)

        assert len(warnings) == 1
        warning = warnings[0]
        assert warning.warning_type == "INCOME_DROP"
        assert "60%" in warning.message
        assert warning.details["year1"] == 2023
        assert warning.details["year2"] == 2024

    def test_income_spike_detected(
        self, validator: ConsistencyValidator
    ) -> None:
        """400% income increase is flagged."""
        borrower = _make_borrower(
            income_history=[
                _make_income(2023, Decimal("50000")),
                _make_income(2024, Decimal("250000")),  # 400% increase
            ],
        )

        warnings = validator.validate_income_progression(borrower)

        assert len(warnings) == 1
        warning = warnings[0]
        assert warning.warning_type == "INCOME_SPIKE"
        assert "400%" in warning.message

    def test_stable_income_no_warning(
        self, validator: ConsistencyValidator
    ) -> None:
        """10% income change is fine - no warning."""
        borrower = _make_borrower(
            income_history=[
                _make_income(2023, Decimal("50000")),
                _make_income(2024, Decimal("55000")),  # 10% increase
            ],
        )

        warnings = validator.validate_income_progression(borrower)

        assert len(warnings) == 0

    def test_boundary_50_percent_drop_not_flagged(
        self, validator: ConsistencyValidator
    ) -> None:
        """Exactly 50% drop is at threshold - not flagged (needs >50%)."""
        borrower = _make_borrower(
            income_history=[
                _make_income(2023, Decimal("100000")),
                _make_income(2024, Decimal("50000")),  # Exactly 50% drop
            ],
        )

        warnings = validator.validate_income_progression(borrower)

        # 50% drop is at threshold (drops more than 50% means <50% remaining)
        # 50000/100000 = 0.5, which is not < 0.5, so no warning
        assert len(warnings) == 0

    def test_boundary_300_percent_increase_not_flagged(
        self, validator: ConsistencyValidator
    ) -> None:
        """Exactly 300% increase (4x) is at threshold - not flagged."""
        borrower = _make_borrower(
            income_history=[
                _make_income(2023, Decimal("50000")),
                _make_income(2024, Decimal("150000")),  # 3x = 200% increase
            ],
        )

        warnings = validator.validate_income_progression(borrower)

        # 3x is at threshold (> 3.0 needed)
        assert len(warnings) == 0

    def test_non_consecutive_years_skipped(
        self, validator: ConsistencyValidator
    ) -> None:
        """Non-consecutive years are not compared."""
        borrower = _make_borrower(
            income_history=[
                _make_income(2021, Decimal("100000")),
                _make_income(2024, Decimal("30000")),  # Big gap, but not consecutive
            ],
        )

        warnings = validator.validate_income_progression(borrower)

        assert len(warnings) == 0

    def test_single_income_no_warning(
        self, validator: ConsistencyValidator
    ) -> None:
        """Single income record can't be compared - no warning."""
        borrower = _make_borrower(
            income_history=[_make_income(2024, Decimal("50000"))],
        )

        warnings = validator.validate_income_progression(borrower)

        assert len(warnings) == 0


class TestCrossDocumentConsistency:
    """Tests for cross-document consistency checks."""

    def test_same_name_different_ssn_flagged(
        self, validator: ConsistencyValidator
    ) -> None:
        """Same name with different SSNs is flagged for review."""
        borrowers = [
            _make_borrower(name="John Smith", ssn="123-45-6789"),
            _make_borrower(name="John Smith", ssn="987-65-4321"),
        ]

        warnings = validator.check_cross_document_consistency(borrowers)

        assert len(warnings) == 1
        warning = warnings[0]
        assert warning.warning_type == "CROSS_DOC_MISMATCH"
        assert "John Smith" in warning.message
        assert len(warning.details["ssn_last4_values"]) == 2
        assert "6789" in warning.details["ssn_last4_values"]
        assert "4321" in warning.details["ssn_last4_values"]

    def test_same_name_same_ssn_not_flagged(
        self, validator: ConsistencyValidator
    ) -> None:
        """Same name with same SSN is fine (deduplicator should have merged)."""
        borrowers = [
            _make_borrower(name="John Smith", ssn="123-45-6789"),
            _make_borrower(name="John Smith", ssn="123-45-6789"),  # Same SSN
        ]

        warnings = validator.check_cross_document_consistency(borrowers)

        # Same last-4 SSN means only 1 unique value, so no warning
        assert len(warnings) == 0

    def test_different_names_same_ssn_pattern_not_flagged(
        self, validator: ConsistencyValidator
    ) -> None:
        """Different names are in different groups - not compared."""
        borrowers = [
            _make_borrower(name="John Smith", ssn="123-45-6789"),
            _make_borrower(name="Jane Doe", ssn="987-65-6789"),  # Same last 4
        ]

        warnings = validator.check_cross_document_consistency(borrowers)

        assert len(warnings) == 0

    def test_same_name_one_with_ssn_not_flagged(
        self, validator: ConsistencyValidator
    ) -> None:
        """Same name but only one has SSN - can't compare, no warning."""
        borrowers = [
            _make_borrower(name="John Smith", ssn="123-45-6789"),
            _make_borrower(name="John Smith", ssn=None),
        ]

        warnings = validator.check_cross_document_consistency(borrowers)

        # Only 1 record with SSN in the group, can't compare
        assert len(warnings) == 0

    def test_name_normalization(
        self, validator: ConsistencyValidator
    ) -> None:
        """Names are normalized for comparison (case-insensitive, stripped)."""
        borrowers = [
            _make_borrower(name="John Smith", ssn="123-45-6789"),
            _make_borrower(name="JOHN SMITH", ssn="987-65-4321"),  # Different case
            _make_borrower(name="  john smith  ", ssn="555-55-5555"),  # Extra spaces
        ]

        warnings = validator.check_cross_document_consistency(borrowers)

        assert len(warnings) == 1
        # All 3 should be in same group with 3 different SSN last-4s
        assert len(warnings[0].details["ssn_last4_values"]) == 3


class TestCombinedValidation:
    """Tests for validate() returning all warnings."""

    def test_validate_returns_all_warnings(
        self, validator: ConsistencyValidator
    ) -> None:
        """Combined validation captures all issue types."""
        # Create borrowers with multiple issues
        borrower1 = _make_borrower(
            name="Alice Johnson",
            address=_make_address(),
            sources=[_make_source("a.pdf"), _make_source("b.pdf")],  # Multi-source
            income_history=[
                _make_income(2023, Decimal("100000")),
                _make_income(2024, Decimal("30000")),  # 70% drop
            ],
        )

        borrower2 = _make_borrower(
            name="Bob Wilson",
            ssn="111-22-3333",
        )

        borrower3 = _make_borrower(
            name="Bob Wilson",  # Same name as borrower2
            ssn="444-55-6666",  # Different SSN
        )

        warnings = validator.validate([borrower1, borrower2, borrower3])

        # Should have:
        # - ADDRESS_CONFLICT for borrower1 (multi-source)
        # - INCOME_DROP for borrower1 (70% drop)
        # - CROSS_DOC_MISMATCH for Bob Wilson (same name, different SSN)
        assert len(warnings) == 3

        warning_types = {w.warning_type for w in warnings}
        assert warning_types == {"ADDRESS_CONFLICT", "INCOME_DROP", "CROSS_DOC_MISMATCH"}

    def test_validate_empty_for_clean_records(
        self, validator: ConsistencyValidator
    ) -> None:
        """Clean records with no issues return empty warnings list."""
        borrowers = [
            _make_borrower(
                name="Person 1",
                ssn="123-45-6789",
                sources=[_make_source()],
                income_history=[
                    _make_income(2023, Decimal("50000")),
                    _make_income(2024, Decimal("52000")),
                ],
            ),
            _make_borrower(
                name="Person 2",
                ssn="987-65-4321",
                sources=[_make_source()],
            ),
        ]

        warnings = validator.validate(borrowers)

        assert len(warnings) == 0
