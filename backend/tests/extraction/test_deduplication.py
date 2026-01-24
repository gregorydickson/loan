"""Unit tests for BorrowerDeduplicator.

Tests cover:
- No duplicates: different borrowers stay separate
- SSN matching: same SSN merges records
- Account number matching: overlapping accounts merge
- Fuzzy name matching: similar names + same zip merge
- High name similarity: 95%+ names merge without address
- Merge behavior: data combined correctly
- Confidence handling: higher confidence record used as base
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from src.extraction.deduplication import BorrowerDeduplicator
from src.models.borrower import Address, BorrowerRecord, IncomeRecord
from src.models.document import SourceReference


@pytest.fixture
def deduplicator() -> BorrowerDeduplicator:
    """Create a BorrowerDeduplicator instance."""
    return BorrowerDeduplicator()


def _make_borrower(
    name: str,
    ssn: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    address: Address | None = None,
    income_history: list[IncomeRecord] | None = None,
    account_numbers: list[str] | None = None,
    loan_numbers: list[str] | None = None,
    confidence_score: float = 0.5,
) -> BorrowerRecord:
    """Helper to create a BorrowerRecord with minimal boilerplate."""
    source = SourceReference(
        document_id=uuid4(),
        document_name="test.pdf",
        page_number=1,
        snippet="Test snippet",
    )
    return BorrowerRecord(
        id=uuid4(),
        name=name,
        ssn=ssn,
        phone=phone,
        email=email,
        address=address,
        income_history=income_history or [],
        account_numbers=account_numbers or [],
        loan_numbers=loan_numbers or [],
        sources=[source],
        confidence_score=confidence_score,
    )


def _make_address(zip_code: str = "75001") -> Address:
    """Helper to create an Address."""
    return Address(
        street="123 Main St",
        city="Dallas",
        state="TX",
        zip_code=zip_code,
    )


def _make_income(
    amount: Decimal = Decimal("50000"),
    year: int = 2024,
    period: str = "annual",
    source_type: str = "employment",
    employer: str | None = None,
) -> IncomeRecord:
    """Helper to create an IncomeRecord."""
    return IncomeRecord(
        amount=amount,
        year=year,
        period=period,
        source_type=source_type,
        employer=employer,
    )


class TestNoDuplicates:
    """Tests for keeping different borrowers separate."""

    def test_no_duplicates_different_names(
        self, deduplicator: BorrowerDeduplicator
    ) -> None:
        """Different borrowers should remain separate."""
        records = [
            _make_borrower("John Smith"),
            _make_borrower("Jane Doe"),
            _make_borrower("Bob Johnson"),
        ]

        result = deduplicator.deduplicate(records)

        assert len(result) == 3
        names = {r.name for r in result}
        assert names == {"John Smith", "Jane Doe", "Bob Johnson"}

    def test_no_duplicates_similar_names_different_zip(
        self, deduplicator: BorrowerDeduplicator
    ) -> None:
        """Moderately similar names with different ZIP codes should stay separate."""
        # Use names that are ~85% similar (below 90% threshold)
        records = [
            _make_borrower(
                "John Allen Smith",
                address=_make_address("75001"),
            ),
            _make_borrower(
                "John B Smithson",  # ~85% similar, different zip
                address=_make_address("90210"),
            ),
        ]

        result = deduplicator.deduplicate(records)

        # Similar names (but <95%) with different zip should NOT merge
        assert len(result) == 2

    def test_empty_list_returns_empty(
        self, deduplicator: BorrowerDeduplicator
    ) -> None:
        """Empty input should return empty output."""
        result = deduplicator.deduplicate([])
        assert result == []


class TestExactSSNMatch:
    """Tests for SSN-based deduplication."""

    def test_exact_ssn_match_merges(
        self, deduplicator: BorrowerDeduplicator
    ) -> None:
        """Same SSN should merge records."""
        records = [
            _make_borrower("John Smith", ssn="123-45-6789"),
            _make_borrower("JOHN SMITH", ssn="123-45-6789"),  # Same SSN
        ]

        result = deduplicator.deduplicate(records)

        assert len(result) == 1
        assert result[0].ssn == "123-45-6789"

    def test_different_ssn_no_merge(
        self, deduplicator: BorrowerDeduplicator
    ) -> None:
        """Different SSNs with different names should not merge."""
        # Need different names to avoid 95%+ name match triggering merge
        records = [
            _make_borrower("John Allen Smith", ssn="123-45-6789"),
            _make_borrower("Robert James Wilson", ssn="987-65-4321"),
        ]

        result = deduplicator.deduplicate(records)

        assert len(result) == 2


class TestAccountNumberMatch:
    """Tests for account number-based deduplication."""

    def test_account_number_match_merges(
        self, deduplicator: BorrowerDeduplicator
    ) -> None:
        """Overlapping account numbers should merge records."""
        records = [
            _make_borrower(
                "John Smith",
                account_numbers=["ACC-001", "ACC-002"],
            ),
            _make_borrower(
                "J Smith",
                account_numbers=["ACC-002", "ACC-003"],  # Overlaps on ACC-002
            ),
        ]

        result = deduplicator.deduplicate(records)

        assert len(result) == 1
        # Account numbers should be unioned
        assert set(result[0].account_numbers) == {"ACC-001", "ACC-002", "ACC-003"}


class TestFuzzyNameMatch:
    """Tests for fuzzy name matching."""

    def test_fuzzy_name_match_with_same_zip(
        self, deduplicator: BorrowerDeduplicator
    ) -> None:
        """Similar names with same ZIP should merge."""
        records = [
            _make_borrower(
                "John Smith",
                address=_make_address("75001"),
            ),
            _make_borrower(
                "JOHN SMITH",  # Same name, different case
                address=_make_address("75001"),
            ),
        ]

        result = deduplicator.deduplicate(records)

        assert len(result) == 1

    def test_fuzzy_name_match_with_zip_plus_four(
        self, deduplicator: BorrowerDeduplicator
    ) -> None:
        """ZIP+4 should match on first 5 digits."""
        records = [
            _make_borrower(
                "John Smith",
                address=_make_address("75001"),
            ),
            _make_borrower(
                "John R Smith",
                address=_make_address("75001-1234"),  # ZIP+4
            ),
        ]

        result = deduplicator.deduplicate(records)

        assert len(result) == 1


class TestHighNameSimilarityNoAddress:
    """Tests for high name similarity without address."""

    def test_very_high_name_similarity_merges(
        self, deduplicator: BorrowerDeduplicator
    ) -> None:
        """95%+ name similarity should merge without address."""
        records = [
            _make_borrower("John Robert Smith"),
            _make_borrower("John Robert Smith"),  # Identical name
        ]

        result = deduplicator.deduplicate(records)

        assert len(result) == 1

    def test_moderate_name_similarity_no_merge_without_address(
        self, deduplicator: BorrowerDeduplicator
    ) -> None:
        """<95% name similarity without address should not merge."""
        records = [
            _make_borrower("John Smith"),
            _make_borrower("Jonathan Smithson"),  # Similar but <95%
        ]

        result = deduplicator.deduplicate(records)

        # Names are not 95%+ similar, no address to help
        assert len(result) == 2


class TestNameWithPartialSSN:
    """Tests for name + last 4 SSN matching."""

    def test_name_match_with_last_four_ssn_merges(
        self, deduplicator: BorrowerDeduplicator
    ) -> None:
        """80%+ name match with same last 4 SSN digits should merge."""
        records = [
            _make_borrower("John Smith", ssn="123-45-6789"),
            _make_borrower("John R Smith", ssn="999-99-6789"),  # Same last 4
        ]

        result = deduplicator.deduplicate(records)

        assert len(result) == 1


class TestMergeBehavior:
    """Tests for data merging during deduplication."""

    def test_merge_combines_income_histories(
        self, deduplicator: BorrowerDeduplicator
    ) -> None:
        """Income histories should be combined, avoiding duplicates."""
        income1 = _make_income(Decimal("50000"), 2023)
        income2 = _make_income(Decimal("55000"), 2024)
        income_dup = _make_income(Decimal("50000"), 2023)  # Same as income1

        records = [
            _make_borrower(
                "John Smith",
                ssn="123-45-6789",
                income_history=[income1],
            ),
            _make_borrower(
                "John Smith",
                ssn="123-45-6789",
                income_history=[income2, income_dup],
            ),
        ]

        result = deduplicator.deduplicate(records)

        assert len(result) == 1
        # Should have 2 unique incomes (income1/income_dup are same)
        assert len(result[0].income_history) == 2
        amounts = {i.amount for i in result[0].income_history}
        assert amounts == {Decimal("50000"), Decimal("55000")}

    def test_merge_unions_account_numbers(
        self, deduplicator: BorrowerDeduplicator
    ) -> None:
        """Account numbers should be unioned."""
        records = [
            _make_borrower(
                "John Smith",
                ssn="123-45-6789",
                account_numbers=["A1", "A2"],
                loan_numbers=["L1"],
            ),
            _make_borrower(
                "John Smith",
                ssn="123-45-6789",
                account_numbers=["A2", "A3"],
                loan_numbers=["L2"],
            ),
        ]

        result = deduplicator.deduplicate(records)

        assert len(result) == 1
        assert set(result[0].account_numbers) == {"A1", "A2", "A3"}
        assert set(result[0].loan_numbers) == {"L1", "L2"}

    def test_merge_fills_missing_fields(
        self, deduplicator: BorrowerDeduplicator
    ) -> None:
        """Missing fields should be filled from other record."""
        records = [
            _make_borrower(
                "John Smith",
                ssn="123-45-6789",
                phone="555-123-4567",
                email=None,
                address=None,
            ),
            _make_borrower(
                "John Smith",
                ssn="123-45-6789",
                phone=None,
                email="john@example.com",
                address=_make_address("75001"),
            ),
        ]

        result = deduplicator.deduplicate(records)

        assert len(result) == 1
        assert result[0].phone == "555-123-4567"
        assert result[0].email == "john@example.com"
        assert result[0].address is not None
        assert result[0].address.zip_code == "75001"

    def test_merge_combines_sources(
        self, deduplicator: BorrowerDeduplicator
    ) -> None:
        """Sources from both records should be combined."""
        records = [
            _make_borrower("John Smith", ssn="123-45-6789"),
            _make_borrower("John Smith", ssn="123-45-6789"),
        ]

        result = deduplicator.deduplicate(records)

        assert len(result) == 1
        # Each record had 1 source, merged should have 2
        assert len(result[0].sources) == 2


class TestConfidenceHandling:
    """Tests for confidence score handling during merge."""

    def test_higher_confidence_used_as_base(
        self, deduplicator: BorrowerDeduplicator
    ) -> None:
        """Higher confidence record should be used as merge base."""
        records = [
            _make_borrower(
                "John Smith",
                ssn="123-45-6789",
                confidence_score=0.6,
            ),
            _make_borrower(
                "John Robert Smith",  # Better name
                ssn="123-45-6789",
                confidence_score=0.9,
            ),
        ]

        result = deduplicator.deduplicate(records)

        assert len(result) == 1
        # Higher confidence record's name should be kept
        assert result[0].name == "John Robert Smith"
        assert result[0].confidence_score == 0.9

    def test_max_confidence_kept(
        self, deduplicator: BorrowerDeduplicator
    ) -> None:
        """Maximum confidence score should be preserved."""
        records = [
            _make_borrower(
                "John Smith",
                ssn="123-45-6789",
                confidence_score=0.3,
            ),
            _make_borrower(
                "John Smith",
                ssn="123-45-6789",
                confidence_score=0.8,
            ),
        ]

        result = deduplicator.deduplicate(records)

        assert len(result) == 1
        assert result[0].confidence_score == 0.8
