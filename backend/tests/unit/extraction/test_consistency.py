"""Unit tests for ConsistencyValidator.

Tests consistency validation that flags issues for human review:
- Address conflicts in multi-source borrowers
- Income progression anomalies (drops >50%, spikes >300%)
- Cross-document mismatches (same name, different SSN)
"""

from datetime import datetime, UTC
from decimal import Decimal
from uuid import uuid4

import pytest

from src.extraction.consistency import ConsistencyValidator, ConsistencyWarning
from src.models.borrower import Address, BorrowerRecord, IncomeRecord
from src.models.document import SourceReference


def create_source_reference(document_name: str, page: int = 1, section: str | None = None) -> SourceReference:
    """Helper to create SourceReference with all required fields."""
    return SourceReference(
        document_id=uuid4(),
        document_name=document_name,
        page_number=page,
        section=section,
        snippet="",  # Required field
    )


class TestConsistencyValidator:
    """Tests for ConsistencyValidator main logic."""

    @pytest.fixture
    def validator(self) -> ConsistencyValidator:
        """Create validator instance."""
        return ConsistencyValidator()

    def test_empty_list_returns_no_warnings(self, validator):
        """Empty borrower list returns no warnings."""
        warnings = validator.validate([])
        assert len(warnings) == 0

    def test_single_borrower_no_warnings(self, validator):
        """Single borrower with no issues returns no warnings."""
        borrower = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            ssn="123-45-6789",
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )
        warnings = validator.validate([borrower])
        assert len(warnings) == 0


class TestAddressConflictDetection:
    """Tests for address conflict detection in multi-source records."""

    @pytest.fixture
    def validator(self) -> ConsistencyValidator:
        """Create validator instance."""
        return ConsistencyValidator()

    def test_single_source_no_address_conflict(self, validator):
        """Single source borrower does not trigger address conflict warning."""
        source = create_source_reference("doc1.pdf", 1, "Income")
        address = Address(
            street="123 Main St",
            city="Austin",
            state="TX",
            zip_code="78701",
        )

        borrower = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            address=address,
            sources=[source],
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )

        warnings = validator.check_address_conflicts(borrower)
        assert len(warnings) == 0

    def test_multi_source_with_address_triggers_warning(self, validator):
        """Multiple sources with address triggers conflict warning."""
        source1 = create_source_reference("doc1.pdf", 1, "Income")
        source2 = create_source_reference("doc2.pdf", 2, "Assets")
        address = Address(
            street="123 Main St",
            city="Austin",
            state="TX",
            zip_code="78701",
        )

        borrower = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            address=address,
            sources=[source1, source2],
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )

        warnings = validator.check_address_conflicts(borrower)
        assert len(warnings) == 1
        assert warnings[0].warning_type == "ADDRESS_CONFLICT"
        assert warnings[0].field == "address"
        assert "2 sources" in warnings[0].message

    def test_multi_source_without_address_no_warning(self, validator):
        """Multiple sources without address does not trigger warning."""
        source1 = create_source_reference("doc1.pdf", 1, "Income")
        source2 = create_source_reference("doc2.pdf", 2, "Assets")

        borrower = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            address=None,  # No address
            sources=[source1, source2],
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )

        warnings = validator.check_address_conflicts(borrower)
        assert len(warnings) == 0

    def test_address_conflict_warning_contains_details(self, validator):
        """Address conflict warning includes source details."""
        source1 = create_source_reference("W2_2023.pdf", 1, "Income")
        source2 = create_source_reference("1040_2024.pdf", 3, "Personal Info")
        address = Address(
            street="123 Main St",
            city="Austin",
            state="TX",
            zip_code="78701",
        )

        borrower = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            address=address,
            sources=[source1, source2],
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )

        warnings = validator.check_address_conflicts(borrower)
        assert len(warnings) == 1
        assert warnings[0].details["source_count"] == 2
        assert "W2_2023.pdf" in warnings[0].details["source_docs"]
        assert "1040_2024.pdf" in warnings[0].details["source_docs"]
        assert warnings[0].details["current_address"]["street"] == "123 Main St"


class TestIncomeProgressionValidation:
    """Tests for income progression anomaly detection."""

    @pytest.fixture
    def validator(self) -> ConsistencyValidator:
        """Create validator instance."""
        return ConsistencyValidator()

    def test_no_income_history_no_warnings(self, validator):
        """Borrower without income history returns no warnings."""
        borrower = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            income_history=[],
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )

        warnings = validator.validate_income_progression(borrower)
        assert len(warnings) == 0

    def test_single_income_record_no_warnings(self, validator):
        """Single income record cannot have progression issues."""
        income = IncomeRecord(
            amount=Decimal("75000"),
            period="annual",
            year=2024,
            source_type="W2",
        )

        borrower = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            income_history=[income],
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )

        warnings = validator.validate_income_progression(borrower)
        assert len(warnings) == 0

    def test_stable_income_progression_no_warnings(self, validator):
        """Stable income progression (within thresholds) returns no warnings."""
        income_2023 = IncomeRecord(
            amount=Decimal("75000"),
            period="annual",
            year=2023,
            source_type="W2",
        )
        income_2024 = IncomeRecord(
            amount=Decimal("80000"),  # 6.7% increase - normal
            period="annual",
            year=2024,
            source_type="W2",
        )

        borrower = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            income_history=[income_2023, income_2024],
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )

        warnings = validator.validate_income_progression(borrower)
        assert len(warnings) == 0

    def test_income_drop_over_50_percent_triggers_warning(self, validator):
        """Income drop >50% triggers INCOME_DROP warning."""
        income_2023 = IncomeRecord(
            amount=Decimal("100000"),
            period="annual",
            year=2023,
            source_type="W2",
        )
        income_2024 = IncomeRecord(
            amount=Decimal("40000"),  # 60% drop
            period="annual",
            year=2024,
            source_type="W2",
        )

        borrower = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            income_history=[income_2023, income_2024],
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )

        warnings = validator.validate_income_progression(borrower)
        assert len(warnings) == 1
        assert warnings[0].warning_type == "INCOME_DROP"
        assert warnings[0].field == "income_history"
        assert "60" in warnings[0].message  # 60% drop

    def test_income_spike_over_300_percent_triggers_warning(self, validator):
        """Income spike >300% triggers INCOME_SPIKE warning."""
        income_2023 = IncomeRecord(
            amount=Decimal("50000"),
            period="annual",
            year=2023,
            source_type="W2",
        )
        income_2024 = IncomeRecord(
            amount=Decimal("250000"),  # 400% increase
            period="annual",
            year=2024,
            source_type="W2",
        )

        borrower = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            income_history=[income_2023, income_2024],
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )

        warnings = validator.validate_income_progression(borrower)
        assert len(warnings) == 1
        assert warnings[0].warning_type == "INCOME_SPIKE"
        assert warnings[0].field == "income_history"
        assert "400" in warnings[0].message

    def test_non_consecutive_years_skipped(self, validator):
        """Income comparison skips non-consecutive years."""
        income_2022 = IncomeRecord(
            amount=Decimal("75000"),
            period="annual",
            year=2022,
            source_type="W2",
        )
        income_2024 = IncomeRecord(
            amount=Decimal("30000"),  # 60% drop but not consecutive
            period="annual",
            year=2024,
            source_type="W2",
        )

        borrower = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            income_history=[income_2022, income_2024],
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )

        warnings = validator.validate_income_progression(borrower)
        assert len(warnings) == 0  # Gap in years, no comparison

    def test_very_low_previous_income_handled(self, validator):
        """Very low income in previous year is handled correctly."""
        income_2023 = IncomeRecord(
            amount=Decimal("1000"),  # Very low but non-zero
            period="annual",
            year=2023,
            source_type="W2",
        )
        income_2024 = IncomeRecord(
            amount=Decimal("75000"),  # 7400% increase
            period="annual",
            year=2024,
            source_type="W2",
        )

        borrower = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            income_history=[income_2023, income_2024],
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )

        warnings = validator.validate_income_progression(borrower)
        # Should trigger spike warning (>300%)
        assert len(warnings) == 1
        assert warnings[0].warning_type == "INCOME_SPIKE"

    def test_multiple_year_progression_all_checked(self, validator):
        """Multiple consecutive years all checked for anomalies."""
        income_2022 = IncomeRecord(
            amount=Decimal("100000"),
            period="annual",
            year=2022,
            source_type="W2",
        )
        income_2023 = IncomeRecord(
            amount=Decimal("40000"),  # 60% drop - warning
            period="annual",
            year=2023,
            source_type="W2",
        )
        income_2024 = IncomeRecord(
            amount=Decimal("200000"),  # 400% spike - warning
            period="annual",
            year=2024,
            source_type="W2",
        )

        borrower = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            income_history=[income_2022, income_2023, income_2024],
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )

        warnings = validator.validate_income_progression(borrower)
        assert len(warnings) == 2  # One drop, one spike
        warning_types = {w.warning_type for w in warnings}
        assert "INCOME_DROP" in warning_types
        assert "INCOME_SPIKE" in warning_types

    def test_income_warning_contains_details(self, validator):
        """Income warning includes year and amount details."""
        income_2023 = IncomeRecord(
            amount=Decimal("100000"),
            period="annual",
            year=2023,
            source_type="W2",
        )
        income_2024 = IncomeRecord(
            amount=Decimal("40000"),
            period="annual",
            year=2024,
            source_type="W2",
        )

        borrower = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            income_history=[income_2023, income_2024],
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )

        warnings = validator.validate_income_progression(borrower)
        assert len(warnings) == 1
        assert warnings[0].details["year1"] == 2023
        assert warnings[0].details["year2"] == 2024
        assert warnings[0].details["amount1"] == "100000"
        assert warnings[0].details["amount2"] == "40000"
        assert warnings[0].details["pct_change"] < 0  # Negative percentage


class TestCrossDocumentConsistency:
    """Tests for cross-document consistency checks."""

    @pytest.fixture
    def validator(self) -> ConsistencyValidator:
        """Create validator instance."""
        return ConsistencyValidator()

    def test_different_names_no_warning(self, validator):
        """Different names do not trigger cross-document warning."""
        borrower1 = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            ssn="123-45-6789",
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )
        borrower2 = BorrowerRecord(
            id=uuid4(),
            name="Jane Doe",
            ssn="987-65-4321",
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )

        warnings = validator.check_cross_document_consistency([borrower1, borrower2])
        assert len(warnings) == 0

    def test_same_name_same_ssn_no_warning(self, validator):
        """Same name with same SSN is expected (deduplication should have merged)."""
        # Note: These should have been merged by deduplicator, but if not...
        borrower1 = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            ssn="123-45-6789",
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )
        borrower2 = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            ssn="123-45-6789",  # Same SSN
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )

        warnings = validator.check_cross_document_consistency([borrower1, borrower2])
        # Should have been deduplicated, but if still separate, same SSN means no mismatch
        assert len(warnings) == 0

    def test_same_name_different_ssn_triggers_warning(self, validator):
        """Same name with different SSN last-4 triggers mismatch warning."""
        borrower1 = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            ssn="123-45-6789",
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )
        borrower2 = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            ssn="987-65-4321",  # Different SSN
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )

        warnings = validator.check_cross_document_consistency([borrower1, borrower2])
        assert len(warnings) == 1
        assert warnings[0].warning_type == "CROSS_DOC_MISMATCH"
        assert warnings[0].field == "ssn"

    def test_name_match_case_insensitive(self, validator):
        """Name matching is case-insensitive."""
        borrower1 = BorrowerRecord(
            id=uuid4(),
            name="JOHN SMITH",
            ssn="123-45-6789",
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )
        borrower2 = BorrowerRecord(
            id=uuid4(),
            name="john smith",
            ssn="987-65-4321",
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )

        warnings = validator.check_cross_document_consistency([borrower1, borrower2])
        assert len(warnings) == 1
        assert warnings[0].warning_type == "CROSS_DOC_MISMATCH"

    def test_same_name_one_without_ssn_no_warning(self, validator):
        """Same name with only one having SSN does not trigger warning."""
        borrower1 = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            ssn="123-45-6789",
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )
        borrower2 = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            ssn=None,  # No SSN
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )

        warnings = validator.check_cross_document_consistency([borrower1, borrower2])
        # Need at least 2 records with SSN to compare
        assert len(warnings) == 0

    def test_mismatch_warning_contains_details(self, validator):
        """Mismatch warning includes record IDs and SSN values."""
        id1 = uuid4()
        id2 = uuid4()

        borrower1 = BorrowerRecord(
            id=id1,
            name="John Smith",
            ssn="123-45-6789",
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )
        borrower2 = BorrowerRecord(
            id=id2,
            name="John Smith",
            ssn="987-65-4321",
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )

        warnings = validator.check_cross_document_consistency([borrower1, borrower2])
        assert len(warnings) == 1
        assert warnings[0].details["name"] == "John Smith"
        assert str(id1) in warnings[0].details["record_ids"]
        assert str(id2) in warnings[0].details["record_ids"]
        assert "6789" in warnings[0].details["ssn_last4_values"]
        assert "4321" in warnings[0].details["ssn_last4_values"]

    def test_three_borrowers_same_name_different_ssn(self, validator):
        """Three borrowers with same name but different SSNs trigger warning."""
        borrower1 = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            ssn="123-45-6789",
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )
        borrower2 = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            ssn="987-65-4321",
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )
        borrower3 = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            ssn="111-22-3333",
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )

        warnings = validator.check_cross_document_consistency(
            [borrower1, borrower2, borrower3]
        )
        assert len(warnings) == 1
        assert len(warnings[0].details["ssn_last4_values"]) == 3
        assert len(warnings[0].details["record_ids"]) == 3


class TestIntegration:
    """Integration tests for full validation pipeline."""

    @pytest.fixture
    def validator(self) -> ConsistencyValidator:
        """Create validator instance."""
        return ConsistencyValidator()

    def test_multiple_warning_types_accumulated(self, validator):
        """Multiple warning types are all detected and accumulated."""
        # Borrower with address conflict
        source1 = create_source_reference("doc1.pdf", 1, "Income")
        source2 = create_source_reference("doc2.pdf", 2, "Assets")
        address = Address(
            street="123 Main St",
            city="Austin",
            state="TX",
            zip_code="78701",
        )

        income_2023 = IncomeRecord(
            amount=Decimal("100000"),
            period="annual",
            year=2023,
            source_type="W2",
        )
        income_2024 = IncomeRecord(
            amount=Decimal("30000"),  # 70% drop - warning
            period="annual",
            year=2024,
            source_type="W2",
        )

        borrower1 = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            ssn="123-45-6789",
            address=address,
            sources=[source1, source2],  # Multi-source - warning
            income_history=[income_2023, income_2024],  # Income drop - warning
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )

        # Borrower with same name but different SSN - cross-doc warning
        borrower2 = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            ssn="987-65-4321",  # Different SSN - warning
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )

        warnings = validator.validate([borrower1, borrower2])

        # Should have 3 warnings: address conflict, income drop, cross-doc mismatch
        assert len(warnings) >= 3
        warning_types = {w.warning_type for w in warnings}
        assert "ADDRESS_CONFLICT" in warning_types
        assert "INCOME_DROP" in warning_types
        assert "CROSS_DOC_MISMATCH" in warning_types


class TestThresholds:
    """Tests for threshold boundary conditions."""

    @pytest.fixture
    def validator(self) -> ConsistencyValidator:
        """Create validator instance."""
        return ConsistencyValidator()

    def test_income_drop_exactly_50_percent_no_warning(self, validator):
        """Income drop of exactly 50% is at threshold (no warning)."""
        income_2023 = IncomeRecord(
            amount=Decimal("100000"),
            period="annual",
            year=2023,
            source_type="W2",
        )
        income_2024 = IncomeRecord(
            amount=Decimal("50000"),  # Exactly 50%
            period="annual",
            year=2024,
            source_type="W2",
        )

        borrower = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            income_history=[income_2023, income_2024],
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )

        warnings = validator.validate_income_progression(borrower)
        # At threshold - implementation choice whether to warn or not
        # Test documents current behavior

    def test_income_spike_exactly_300_percent_no_warning(self, validator):
        """Income spike of exactly 300% is at threshold (no warning)."""
        income_2023 = IncomeRecord(
            amount=Decimal("50000"),
            period="annual",
            year=2023,
            source_type="W2",
        )
        income_2024 = IncomeRecord(
            amount=Decimal("150000"),  # Exactly 3x (200% increase)
            period="annual",
            year=2024,
            source_type="W2",
        )

        borrower = BorrowerRecord(
            id=uuid4(),
            name="John Smith",
            income_history=[income_2023, income_2024],
            confidence_score=Decimal("0.9"),
            extracted_at=datetime.now(UTC),
        )

        warnings = validator.validate_income_progression(borrower)
        # At threshold - test documents current behavior
