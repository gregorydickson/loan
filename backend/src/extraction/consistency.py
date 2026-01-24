"""Consistency validation for cross-document and within-record data checks.

This module provides validation that DETECTS and FLAGS inconsistencies
for human review. Unlike deduplication which automatically merges records,
consistency validation surfaces potential issues:

- Address conflicts when a borrower has multiple source documents
- Unusual income progression (large drops or spikes)
- Cross-document mismatches (same name but different identifiers)

VALID-07, VALID-08, VALID-09: Conflicts are reported for review, not silently resolved.
"""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from src.models.borrower import BorrowerRecord


@dataclass
class ConsistencyWarning:
    """A consistency issue detected during validation.

    Attributes:
        warning_type: Category of warning (ADDRESS_CONFLICT, INCOME_DROP,
                     INCOME_SPIKE, CROSS_DOC_MISMATCH)
        borrower_id: UUID of the borrower with the issue
        field: Field name with inconsistency (address, income_history)
        message: Human-readable description of the issue
        details: Additional context (conflicting values, source docs, etc.)
    """

    warning_type: str
    borrower_id: UUID
    field: str
    message: str
    details: dict[str, Any]


class ConsistencyValidator:
    """Validates borrower data for logical consistency.

    Detects and flags issues for human review:
    - Address conflicts: Borrower with multiple sources may have merged
      conflicting addresses
    - Income progression: Flags unusual year-over-year changes (>50% drop
      or >300% increase)
    - Cross-document mismatches: Same name appearing with different SSNs

    Unlike BorrowerDeduplicator which automatically merges, this validator
    surfaces potential issues WITHOUT resolving them.

    Example:
        validator = ConsistencyValidator()
        warnings = validator.validate(borrowers)
        for warning in warnings:
            if warning.warning_type == "INCOME_DROP":
                flag_for_review(warning)
    """

    # Income change thresholds
    INCOME_DROP_THRESHOLD = 0.5  # Flag if drops more than 50%
    INCOME_SPIKE_THRESHOLD = 3.0  # Flag if increases more than 300%

    def validate(self, borrowers: list[BorrowerRecord]) -> list[ConsistencyWarning]:
        """Run all consistency checks on a list of borrowers.

        Args:
            borrowers: List of borrower records to validate

        Returns:
            List of ConsistencyWarning objects for all detected issues
        """
        warnings: list[ConsistencyWarning] = []

        for borrower in borrowers:
            # Check for address conflicts (multi-source borrowers)
            warnings.extend(self.check_address_conflicts(borrower))

            # Check for income progression anomalies
            warnings.extend(self.validate_income_progression(borrower))

        # Check for cross-document consistency (same name, different SSN)
        warnings.extend(self.check_cross_document_consistency(borrowers))

        return warnings

    def check_address_conflicts(
        self, borrower: BorrowerRecord
    ) -> list[ConsistencyWarning]:
        """Check for potential address conflicts in multi-source records.

        When a borrower has been extracted from multiple sources (documents),
        there's a possibility that different addresses were present in different
        documents. This flags such cases for human verification.

        Args:
            borrower: Borrower record to check

        Returns:
            List of warnings if borrower has multiple sources
        """
        warnings: list[ConsistencyWarning] = []

        # Only flag if borrower has multiple sources AND has an address
        if len(borrower.sources) > 1 and borrower.address is not None:
            source_docs = [s.document_name for s in borrower.sources]

            warnings.append(
                ConsistencyWarning(
                    warning_type="ADDRESS_CONFLICT",
                    borrower_id=borrower.id,
                    field="address",
                    message=(
                        f"Borrower '{borrower.name}' has {len(borrower.sources)} sources - "
                        "verify address is correct"
                    ),
                    details={
                        "source_count": len(borrower.sources),
                        "current_address": {
                            "street": borrower.address.street,
                            "city": borrower.address.city,
                            "state": borrower.address.state,
                            "zip_code": borrower.address.zip_code,
                        },
                        "source_docs": source_docs,
                    },
                )
            )

        return warnings

    def validate_income_progression(
        self, borrower: BorrowerRecord
    ) -> list[ConsistencyWarning]:
        """Check for unusual income changes between consecutive years.

        Flags:
        - Income drops of more than 50% year-over-year
        - Income increases of more than 300% year-over-year

        These may be legitimate (job change, promotion) but warrant review.

        Args:
            borrower: Borrower record to check

        Returns:
            List of warnings for any unusual income progression
        """
        warnings: list[ConsistencyWarning] = []

        # Need at least 2 income records to compare
        if len(borrower.income_history) < 2:
            return warnings

        # Sort income by year
        sorted_income = sorted(borrower.income_history, key=lambda i: i.year)

        # Compare consecutive years
        for i in range(1, len(sorted_income)):
            prev = sorted_income[i - 1]
            curr = sorted_income[i]

            # Skip if years are not consecutive
            if curr.year != prev.year + 1:
                continue

            # Skip if previous amount is zero (can't calculate percentage)
            if prev.amount == 0:
                continue

            # Calculate year-over-year change
            change_ratio = float(curr.amount / prev.amount)
            pct_change = (change_ratio - 1) * 100

            # Check for significant drop
            if change_ratio < (1 - self.INCOME_DROP_THRESHOLD):
                warnings.append(
                    ConsistencyWarning(
                        warning_type="INCOME_DROP",
                        borrower_id=borrower.id,
                        field="income_history",
                        message=(
                            f"Income dropped {abs(pct_change):.0f}% from "
                            f"{prev.year} to {curr.year}"
                        ),
                        details={
                            "year1": prev.year,
                            "amount1": str(prev.amount),
                            "year2": curr.year,
                            "amount2": str(curr.amount),
                            "pct_change": round(pct_change, 1),
                        },
                    )
                )

            # Check for significant spike
            elif change_ratio > self.INCOME_SPIKE_THRESHOLD:
                warnings.append(
                    ConsistencyWarning(
                        warning_type="INCOME_SPIKE",
                        borrower_id=borrower.id,
                        field="income_history",
                        message=(
                            f"Income increased {pct_change:.0f}% from "
                            f"{prev.year} to {curr.year} - verify accuracy"
                        ),
                        details={
                            "year1": prev.year,
                            "amount1": str(prev.amount),
                            "year2": curr.year,
                            "amount2": str(curr.amount),
                            "pct_change": round(pct_change, 1),
                        },
                    )
                )

        return warnings

    def check_cross_document_consistency(
        self, borrowers: list[BorrowerRecord]
    ) -> list[ConsistencyWarning]:
        """Check for same-name borrowers with different identifiers.

        When the same name appears in multiple records with different SSNs,
        this could indicate:
        - Different people with the same name
        - Data entry errors
        - OCR/extraction mistakes

        Note: The deduplicator already merged records with matching SSNs,
        so these are records that specifically did NOT merge.

        Args:
            borrowers: List of borrower records to check

        Returns:
            List of warnings for potential identity mismatches
        """
        warnings: list[ConsistencyWarning] = []

        # Group borrowers by normalized name
        name_groups: dict[str, list[BorrowerRecord]] = {}
        for borrower in borrowers:
            normalized_name = borrower.name.lower().strip()
            if normalized_name not in name_groups:
                name_groups[normalized_name] = []
            name_groups[normalized_name].append(borrower)

        # Check groups with multiple records (same name, different IDs)
        for _name, group in name_groups.items():
            if len(group) < 2:
                continue

            # Collect SSN last-4 digits for records that have SSN
            ssn_records = [
                (b, b.ssn.replace("-", "")[-4:])
                for b in group
                if b.ssn
            ]

            # If we have multiple records with SSNs, check for mismatch
            if len(ssn_records) >= 2:
                ssn_values = {ssn for _, ssn in ssn_records}

                # If there are different last-4 SSN values, flag it
                if len(ssn_values) > 1:
                    record_ids = [str(b.id) for b in group]

                    warnings.append(
                        ConsistencyWarning(
                            warning_type="CROSS_DOC_MISMATCH",
                            borrower_id=group[0].id,  # Use first record's ID
                            field="ssn",
                            message=(
                                f"Multiple records for '{group[0].name}' with "
                                "different identifiers - may be different people "
                                "or data error"
                            ),
                            details={
                                "name": group[0].name,
                                "record_ids": record_ids,
                                "ssn_last4_values": list(ssn_values),
                            },
                        )
                    )

        return warnings
