"""Borrower deduplication using fuzzy matching for extracted records.

This module provides deduplication of borrower records extracted from
multiple document chunks. It identifies and merges duplicate records
based on:
1. Exact SSN match (highest priority)
2. Overlapping account numbers
3. Fuzzy name matching + same ZIP code
4. Very high name similarity (95%+)
5. Name match (80%+) + last 4 SSN digits match

NOTE: Deduplication MERGES records that are definitely the same person.
Consistency VALIDATION (Plan 03-05) flags potential issues for human review.
These are separate concerns.
"""

from rapidfuzz import fuzz, utils

from src.models.borrower import BorrowerRecord, IncomeRecord


class BorrowerDeduplicator:
    """Deduplicates borrower records using multi-strategy matching.

    Matching strategies (in priority order):
    1. Exact SSN match - if both have SSN and they match
    2. Account number overlap - any shared account number
    3. Fuzzy name (90%+) + same ZIP - high name match with address corroboration
    4. Very high name match (95%+) - strong name similarity alone
    5. Name match (80%+) + last 4 SSN - moderate name + partial SSN match

    Uses rapidfuzz for efficient string similarity calculation.

    Example:
        dedup = BorrowerDeduplicator()
        merged = dedup.deduplicate(extracted_records)
    """

    NAME_THRESHOLD = 90  # Fuzzy match threshold for name + zip
    HIGH_NAME_THRESHOLD = 95  # Threshold for name-only match
    MODERATE_NAME_THRESHOLD = 80  # Threshold for name + partial SSN

    def deduplicate(self, records: list[BorrowerRecord]) -> list[BorrowerRecord]:
        """Deduplicate a list of borrower records.

        Iterates through records, checking each against already-processed
        records. Duplicates are merged; unique records are added to result.

        Args:
            records: List of BorrowerRecords to deduplicate

        Returns:
            Deduplicated list with duplicates merged
        """
        if not records:
            return []

        merged_list: list[BorrowerRecord] = []

        for record in records:
            duplicate_index: int | None = None

            # Check against all already-merged records
            for i, existing in enumerate(merged_list):
                if self._is_duplicate(record, existing):
                    duplicate_index = i
                    break

            if duplicate_index is not None:
                # Merge with existing record
                merged_list[duplicate_index] = self._merge_records(
                    merged_list[duplicate_index], record
                )
            else:
                # Add as new unique record
                merged_list.append(record)

        return merged_list

    def _is_duplicate(self, a: BorrowerRecord, b: BorrowerRecord) -> bool:
        """Determine if two records represent the same person.

        Uses multiple matching strategies in priority order.

        Args:
            a: First borrower record
            b: Second borrower record

        Returns:
            True if records are duplicates, False otherwise
        """
        # Strategy 1: Exact SSN match
        if a.ssn and b.ssn and a.ssn == b.ssn:
            return True

        # Strategy 2: Overlapping account numbers
        if a.account_numbers and b.account_numbers:
            a_accounts = set(a.account_numbers)
            b_accounts = set(b.account_numbers)
            if a_accounts & b_accounts:  # Non-empty intersection
                return True

        # Calculate name similarity once for remaining strategies
        name_score = fuzz.token_sort_ratio(
            a.name.lower(),
            b.name.lower(),
            processor=utils.default_process,
        )

        # Strategy 3: Fuzzy name (90%+) + same ZIP code
        if name_score >= self.NAME_THRESHOLD:
            a_zip = a.address.zip_code if a.address else None
            b_zip = b.address.zip_code if b.address else None
            if a_zip and b_zip and a_zip[:5] == b_zip[:5]:  # Compare first 5 digits
                return True

        # Strategy 4: Very high name match (95%+) without address
        if name_score >= self.HIGH_NAME_THRESHOLD:
            return True

        # Strategy 5: Moderate name match (80%+) + last 4 SSN match
        if name_score >= self.MODERATE_NAME_THRESHOLD and a.ssn and b.ssn:
            # Compare last 4 digits of SSN (XXXX from XXX-XX-XXXX)
            a_last4 = a.ssn.replace("-", "")[-4:]
            b_last4 = b.ssn.replace("-", "")[-4:]
            if a_last4 == b_last4:
                return True

        return False

    def _merge_records(
        self, existing: BorrowerRecord, new: BorrowerRecord
    ) -> BorrowerRecord:
        """Merge two duplicate borrower records.

        Uses the record with higher confidence as base, then fills in
        missing data from the other record.

        Args:
            existing: Already-processed record
            new: New record to merge in

        Returns:
            Merged BorrowerRecord with combined data
        """
        # Use higher confidence record as base
        if new.confidence_score > existing.confidence_score:
            base, other = new, existing
        else:
            base, other = existing, new

        # Merge income histories (avoid duplicates)
        merged_income = list(base.income_history)
        for income in other.income_history:
            if not self._income_exists(income, merged_income):
                merged_income.append(income)

        # Union account and loan numbers
        merged_accounts = list(set(base.account_numbers) | set(other.account_numbers))
        merged_loans = list(set(base.loan_numbers) | set(other.loan_numbers))

        # Combine sources
        merged_sources = list(base.sources) + [
            s for s in other.sources if s not in base.sources
        ]

        # Fill in missing optional fields
        merged_ssn = base.ssn or other.ssn
        merged_phone = base.phone or other.phone
        merged_email = base.email or other.email
        merged_address = base.address or other.address

        # Keep max confidence
        max_confidence = max(base.confidence_score, other.confidence_score)

        return BorrowerRecord(
            id=base.id,  # Keep base record's ID
            name=base.name,  # Keep base name (higher confidence)
            ssn=merged_ssn,
            phone=merged_phone,
            email=merged_email,
            address=merged_address,
            income_history=merged_income,
            account_numbers=merged_accounts,
            loan_numbers=merged_loans,
            sources=merged_sources,
            confidence_score=max_confidence,
            extracted_at=base.extracted_at,  # Keep original extraction time
        )

    def _income_exists(
        self, income: IncomeRecord, income_list: list[IncomeRecord]
    ) -> bool:
        """Check if an income record already exists in the list.

        Compares amount, period, year, and source_type for equality.

        Args:
            income: Income record to check
            income_list: List to search in

        Returns:
            True if matching income exists, False otherwise
        """
        for existing in income_list:
            if (
                existing.amount == income.amount
                and existing.period == income.period
                and existing.year == income.year
                and existing.source_type == income.source_type
            ):
                return True
        return False
