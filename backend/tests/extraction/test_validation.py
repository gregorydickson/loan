"""Tests for field validation module."""

from datetime import UTC, datetime

import pytest

from src.extraction.validation import FieldValidator, ValidationError, ValidationResult


class TestFieldValidator:
    """Tests for FieldValidator class."""

    @pytest.fixture
    def validator(self) -> FieldValidator:
        """Create a FieldValidator instance."""
        return FieldValidator()

    # SSN validation tests

    def test_ssn_valid_with_dashes(self, validator: FieldValidator) -> None:
        """SSN with dashes is valid without warnings."""
        result = validator.validate_ssn("123-45-6789")
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_ssn_valid_without_dashes(self, validator: FieldValidator) -> None:
        """SSN without dashes is valid but produces warning."""
        result = validator.validate_ssn("123456789")
        assert result.is_valid is True
        assert result.errors == []
        assert len(result.warnings) == 1
        assert "dashes" in result.warnings[0].lower()

    def test_ssn_invalid_format(self, validator: FieldValidator) -> None:
        """SSN with wrong format returns FORMAT error."""
        result = validator.validate_ssn("12345")
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].field == "ssn"
        assert result.errors[0].error_type == "FORMAT"
        assert result.errors[0].value == "12345"

    def test_ssn_invalid_letters(self, validator: FieldValidator) -> None:
        """SSN with letters returns FORMAT error."""
        result = validator.validate_ssn("123-AB-6789")
        assert result.is_valid is False
        assert result.errors[0].error_type == "FORMAT"

    # Phone validation tests

    def test_phone_valid_formats(self, validator: FieldValidator) -> None:
        """Various valid US phone formats are accepted."""
        # Use real area codes (212=NYC, 310=LA, 713=Houston) for valid tests
        valid_phones = [
            "(212) 555-1234",
            "310-555-1234",
            "+1 713 555 1234",
            "2125551234",
            "1-212-555-1234",
        ]
        for phone in valid_phones:
            result = validator.validate_phone(phone)
            assert result.is_valid is True, f"Phone '{phone}' should be valid"
            assert result.errors == []

    def test_phone_invalid(self, validator: FieldValidator) -> None:
        """Too short phone number returns error."""
        result = validator.validate_phone("123")
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].field == "phone"

    def test_phone_invalid_area_code(self, validator: FieldValidator) -> None:
        """Invalid area code returns INVALID error."""
        # 000 is not a valid area code
        result = validator.validate_phone("000-123-4567")
        assert result.is_valid is False
        assert result.errors[0].field == "phone"

    # ZIP validation tests

    def test_zip_valid_5digit(self, validator: FieldValidator) -> None:
        """5-digit ZIP code is valid."""
        result = validator.validate_zip("12345")
        assert result.is_valid is True
        assert result.errors == []

    def test_zip_valid_9digit(self, validator: FieldValidator) -> None:
        """9-digit ZIP+4 code is valid."""
        result = validator.validate_zip("12345-6789")
        assert result.is_valid is True
        assert result.errors == []

    def test_zip_invalid(self, validator: FieldValidator) -> None:
        """4-digit ZIP returns FORMAT error."""
        result = validator.validate_zip("1234")
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].field == "zip_code"
        assert result.errors[0].error_type == "FORMAT"

    def test_zip_invalid_letters(self, validator: FieldValidator) -> None:
        """ZIP with letters returns FORMAT error."""
        result = validator.validate_zip("1234A")
        assert result.is_valid is False
        assert result.errors[0].error_type == "FORMAT"

    # Year validation tests

    def test_year_valid_current(self, validator: FieldValidator) -> None:
        """Current year is valid."""
        current_year = datetime.now(UTC).year
        result = validator.validate_year(current_year)
        assert result.is_valid is True
        assert result.errors == []

    def test_year_valid_past(self, validator: FieldValidator) -> None:
        """Recent past year (2020) is valid."""
        result = validator.validate_year(2020)
        assert result.is_valid is True
        assert result.errors == []

    def test_year_invalid_too_old(self, validator: FieldValidator) -> None:
        """Year before MIN_YEAR (1900) returns RANGE error."""
        result = validator.validate_year(1900)
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].field == "year"
        assert result.errors[0].error_type == "RANGE"
        assert "1950" in result.errors[0].message

    def test_year_invalid_future(self, validator: FieldValidator) -> None:
        """Year too far in future returns RANGE error."""
        current_year = datetime.now(UTC).year
        future_year = current_year + 5
        result = validator.validate_year(future_year)
        assert result.is_valid is False
        assert result.errors[0].error_type == "RANGE"
        assert "future" in result.errors[0].message.lower()

    def test_year_allows_next_year(self, validator: FieldValidator) -> None:
        """Current year + 1 is valid (for projected income)."""
        current_year = datetime.now(UTC).year
        result = validator.validate_year(current_year + 1)
        assert result.is_valid is True
        assert result.errors == []

    # None value tests

    def test_none_values_valid(self, validator: FieldValidator) -> None:
        """None values are valid for all optional fields."""
        assert validator.validate_ssn(None).is_valid is True
        assert validator.validate_phone(None).is_valid is True
        assert validator.validate_zip(None).is_valid is True
        assert validator.validate_year(None).is_valid is True


class TestValidationError:
    """Tests for ValidationError dataclass."""

    def test_validation_error_fields(self) -> None:
        """ValidationError has all required fields."""
        error = ValidationError(
            field="ssn",
            value="invalid",
            error_type="FORMAT",
            message="Invalid format",
        )
        assert error.field == "ssn"
        assert error.value == "invalid"
        assert error.error_type == "FORMAT"
        assert error.message == "Invalid format"


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_validation_result_defaults(self) -> None:
        """ValidationResult has correct defaults."""
        result = ValidationResult(is_valid=True)
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_validation_result_with_errors(self) -> None:
        """ValidationResult can hold errors."""
        error = ValidationError("field", "value", "TYPE", "message")
        result = ValidationResult(is_valid=False, errors=[error])
        assert result.is_valid is False
        assert len(result.errors) == 1
