"""Confidence scoring for extracted borrower data.

This module calculates confidence scores for extraction results based on:
- Field completeness (required and optional fields)
- Multi-source corroboration
- Format validation status

Records below the review threshold are flagged for manual review.
"""

from dataclasses import dataclass

from src.models.borrower import BorrowerRecord


@dataclass
class ConfidenceBreakdown:
    """Detailed breakdown of confidence score calculation.

    Attributes:
        base_score: Starting score (always 0.5)
        required_fields_bonus: Bonus for complete required fields (up to 0.2)
        optional_fields_bonus: Bonus for optional fields (up to 0.15)
        multi_source_bonus: Bonus for multiple sources (0.1 if source_count > 1)
        validation_bonus: Bonus for all formats valid (0.15)
        total: Final confidence score (capped at 1.0)
        requires_review: True if total < REVIEW_THRESHOLD (0.7)
    """

    base_score: float
    required_fields_bonus: float
    optional_fields_bonus: float
    multi_source_bonus: float
    validation_bonus: float
    total: float
    requires_review: bool


class ConfidenceCalculator:
    """Calculates confidence scores for extracted borrower records.

    Scoring breakdown:
    - Base score: 0.5 (always applied)
    - Required fields: +0.1 each for name, address (max 0.2)
    - Optional fields: +0.05 each for income_history, account_numbers, loan_numbers (max 0.15)
    - Multi-source: +0.1 if extracted from multiple documents
    - Validation: +0.15 if all field formats pass validation

    Records scoring below REVIEW_THRESHOLD (0.7) are flagged for manual review.

    Example:
        calculator = ConfidenceCalculator()
        breakdown = calculator.calculate(
            record=borrower_record,
            format_validation_passed=True,
            source_count=2
        )
        if breakdown.requires_review:
            queue_for_review(record)
    """

    REVIEW_THRESHOLD = 0.7
    BASE_SCORE = 0.5

    # Bonus caps
    REQUIRED_FIELDS_MAX = 0.2
    OPTIONAL_FIELDS_MAX = 0.15

    # Per-field bonuses
    REQUIRED_FIELD_BONUS = 0.1  # per required field
    OPTIONAL_FIELD_BONUS = 0.05  # per optional field
    MULTI_SOURCE_BONUS = 0.1
    VALIDATION_BONUS = 0.15

    def calculate(
        self,
        record: BorrowerRecord,
        format_validation_passed: bool,
        source_count: int,
    ) -> ConfidenceBreakdown:
        """Calculate confidence score for a borrower record.

        Args:
            record: The extracted BorrowerRecord to score
            format_validation_passed: Whether all field formats passed validation
            source_count: Number of source documents for this record

        Returns:
            ConfidenceBreakdown with detailed score components and review flag
        """
        # Required fields bonus (max 0.2)
        required_bonus = 0.0
        if record.name and len(record.name) > 1:
            required_bonus += self.REQUIRED_FIELD_BONUS
        if record.address is not None:
            required_bonus += self.REQUIRED_FIELD_BONUS
        required_bonus = min(required_bonus, self.REQUIRED_FIELDS_MAX)

        # Optional fields bonus (max 0.15)
        optional_bonus = 0.0
        if record.income_history:  # Non-empty list
            optional_bonus += self.OPTIONAL_FIELD_BONUS
        if record.account_numbers:  # Non-empty list
            optional_bonus += self.OPTIONAL_FIELD_BONUS
        if record.loan_numbers:  # Non-empty list
            optional_bonus += self.OPTIONAL_FIELD_BONUS
        optional_bonus = min(optional_bonus, self.OPTIONAL_FIELDS_MAX)

        # Multi-source bonus
        multi_source_bonus = self.MULTI_SOURCE_BONUS if source_count > 1 else 0.0

        # Validation bonus
        validation_bonus = self.VALIDATION_BONUS if format_validation_passed else 0.0

        # Calculate total (capped at 1.0)
        total = min(
            self.BASE_SCORE
            + required_bonus
            + optional_bonus
            + multi_source_bonus
            + validation_bonus,
            1.0,
        )

        return ConfidenceBreakdown(
            base_score=self.BASE_SCORE,
            required_fields_bonus=required_bonus,
            optional_fields_bonus=optional_bonus,
            multi_source_bonus=multi_source_bonus,
            validation_bonus=validation_bonus,
            total=total,
            requires_review=total < self.REVIEW_THRESHOLD,
        )
