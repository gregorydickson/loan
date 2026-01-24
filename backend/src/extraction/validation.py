"""Field validation for extracted borrower data.

This module provides format validation for extracted fields:
- SSN: XXX-XX-XXXX format (with or without dashes)
- Phone: US phone numbers via phonenumbers library
- ZIP: XXXXX or XXXXX-XXXX format
- Year: Reasonable range (1950 to current+1)
"""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime

import phonenumbers
from phonenumbers import NumberParseException


@dataclass
class ValidationError:
    """Details about a validation failure.

    Attributes:
        field: Field name that failed validation (ssn, phone, zip_code, year)
        value: The invalid value that was provided
        error_type: Error category (FORMAT, LENGTH, INVALID, NANP, RANGE)
        message: Human-readable error message
    """

    field: str
    value: str
    error_type: str
    message: str


@dataclass
class ValidationResult:
    """Result of field validation.

    Attributes:
        is_valid: Whether the field passed validation
        errors: List of validation errors if invalid
        warnings: Non-fatal warnings (e.g., SSN without dashes)
    """

    is_valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class FieldValidator:
    """Validates extracted field formats.

    Validates common borrower data fields:
    - SSN: Social Security Numbers in XXX-XX-XXXX format
    - Phone: US phone numbers using phonenumbers library
    - ZIP: US ZIP codes (5-digit or 5+4)
    - Year: Income years within reasonable range

    Example:
        validator = FieldValidator()
        result = validator.validate_ssn("123-45-6789")
        if not result.is_valid:
            for error in result.errors:
                print(f"{error.field}: {error.message}")
    """

    # SSN patterns - with or without dashes
    SSN_PATTERN = re.compile(r"^\d{3}-?\d{2}-?\d{4}$")
    SSN_FORMATTED = re.compile(r"^\d{3}-\d{2}-\d{4}$")

    # ZIP code pattern - 5 digit or 5+4 format
    ZIP_PATTERN = re.compile(r"^\d{5}(-\d{4})?$")

    # Year range constants
    MIN_YEAR = 1950  # Reasonable minimum for income records
    MAX_YEAR_OFFSET = 1  # Allow current year + 1 for projected income

    def validate_ssn(self, ssn: str | None) -> ValidationResult:
        """Validate Social Security Number format.

        Args:
            ssn: SSN string to validate, or None

        Returns:
            ValidationResult with is_valid=True if None or valid format.
            Adds warning if SSN doesn't have dashes.
        """
        if ssn is None:
            return ValidationResult(is_valid=True)

        if not self.SSN_PATTERN.match(ssn):
            return ValidationResult(
                is_valid=False,
                errors=[
                    ValidationError(
                        field="ssn",
                        value=ssn,
                        error_type="FORMAT",
                        message="SSN must be in XXX-XX-XXXX format (dashes optional)",
                    )
                ],
            )

        result = ValidationResult(is_valid=True)

        # Add warning if not properly formatted with dashes
        if not self.SSN_FORMATTED.match(ssn):
            result.warnings.append(
                f"SSN '{ssn}' should include dashes (XXX-XX-XXXX format)"
            )

        return result

    def validate_phone(self, phone: str | None) -> ValidationResult:
        """Validate US phone number format.

        Uses phonenumbers library for robust validation of various formats.

        Args:
            phone: Phone number string to validate, or None

        Returns:
            ValidationResult with is_valid=True if None or valid US number.
        """
        if phone is None:
            return ValidationResult(is_valid=True)

        try:
            parsed = phonenumbers.parse(phone, "US")
        except NumberParseException as e:
            return ValidationResult(
                is_valid=False,
                errors=[
                    ValidationError(
                        field="phone",
                        value=phone,
                        error_type="FORMAT",
                        message=f"Invalid phone number format: {e}",
                    )
                ],
            )

        if not phonenumbers.is_valid_number(parsed):
            return ValidationResult(
                is_valid=False,
                errors=[
                    ValidationError(
                        field="phone",
                        value=phone,
                        error_type="INVALID",
                        message="Phone number is not a valid US number",
                    )
                ],
            )

        return ValidationResult(is_valid=True)

    def validate_zip(self, zip_code: str | None) -> ValidationResult:
        """Validate US ZIP code format.

        Args:
            zip_code: ZIP code string to validate, or None

        Returns:
            ValidationResult with is_valid=True if None or valid format.
            Accepts both 5-digit (12345) and 5+4 (12345-6789) formats.
        """
        if zip_code is None:
            return ValidationResult(is_valid=True)

        if not self.ZIP_PATTERN.match(zip_code):
            return ValidationResult(
                is_valid=False,
                errors=[
                    ValidationError(
                        field="zip_code",
                        value=zip_code,
                        error_type="FORMAT",
                        message="ZIP code must be XXXXX or XXXXX-XXXX format",
                    )
                ],
            )

        return ValidationResult(is_valid=True)

    def validate_year(self, year: int | None) -> ValidationResult:
        """Validate income year is within reasonable range.

        Args:
            year: Year to validate, or None

        Returns:
            ValidationResult with is_valid=True if None or within range.
            Valid range is MIN_YEAR (1950) to current year + MAX_YEAR_OFFSET (1).
        """
        if year is None:
            return ValidationResult(is_valid=True)

        current_year = datetime.now(UTC).year

        if year < self.MIN_YEAR:
            return ValidationResult(
                is_valid=False,
                errors=[
                    ValidationError(
                        field="year",
                        value=str(year),
                        error_type="RANGE",
                        message=f"Year {year} is before {self.MIN_YEAR}",
                    )
                ],
            )

        if year > current_year + self.MAX_YEAR_OFFSET:
            return ValidationResult(
                is_valid=False,
                errors=[
                    ValidationError(
                        field="year",
                        value=str(year),
                        error_type="RANGE",
                        message=f"Year {year} is in the future",
                    )
                ],
            )

        return ValidationResult(is_valid=True)
