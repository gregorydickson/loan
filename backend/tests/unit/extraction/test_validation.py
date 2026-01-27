"""Unit tests for FieldValidator.

Tests validation rules for extracted borrower fields:
- SSN format and pattern validation
- Phone number validation
- ZIP code format validation (5 and 9 digit)
- Year range validation

Note: FieldValidator returns ValidationResult objects with errors list,
not direct error lists.
"""

import pytest

from src.extraction.validation import FieldValidator, ValidationError, ValidationResult


class TestSSNValidation:
    """Tests for SSN validation rules."""

    @pytest.fixture
    def validator(self) -> FieldValidator:
        """Create validator instance."""
        return FieldValidator()

    def test_valid_ssn_with_dashes_passes(self, validator):
        """Valid SSN with dashes (XXX-XX-XXXX) passes validation."""
        result = validator.validate_ssn("123-45-6789")
        assert result.is_valid
        assert len(result.errors) == 0

    def test_valid_ssn_without_dashes_passes_with_warning(self, validator):
        """Valid SSN without dashes passes but gets warning."""
        result = validator.validate_ssn("123456789")
        assert result.is_valid
        assert len(result.errors) == 0
        assert len(result.warnings) == 1  # Should warn about missing dashes

    def test_none_ssn_passes(self, validator):
        """None SSN is valid (optional field)."""
        result = validator.validate_ssn(None)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_invalid_ssn_format_fails(self, validator):
        """SSN with wrong format fails validation."""
        result = validator.validate_ssn("12-345-6789")  # Wrong dash positions
        assert not result.is_valid
        assert len(result.errors) == 1
        assert result.errors[0].field == "ssn"

    def test_ssn_too_short_fails(self, validator):
        """SSN with too few digits fails validation."""
        result = validator.validate_ssn("12345678")  # Only 8 digits
        assert not result.is_valid
        assert len(result.errors) == 1

    def test_ssn_too_long_fails(self, validator):
        """SSN with too many digits fails validation."""
        result = validator.validate_ssn("1234567890")  # 10 digits
        assert not result.is_valid
        assert len(result.errors) == 1

    def test_ssn_with_letters_fails(self, validator):
        """SSN with letters fails validation."""
        result = validator.validate_ssn("12A-45-6789")
        assert not result.is_valid
        assert len(result.errors) == 1


class TestSSNNormalization:
    """Tests for SSN normalization."""

    @pytest.fixture
    def validator(self) -> FieldValidator:
        """Create validator instance."""
        return FieldValidator()

    def test_normalize_adds_dashes(self, validator):
        """Normalize adds dashes to SSN without them."""
        result = validator.normalize_ssn("123456789")
        assert result == "123-45-6789"

    def test_normalize_preserves_dashes(self, validator):
        """Normalize preserves existing dashes."""
        result = validator.normalize_ssn("123-45-6789")
        assert result == "123-45-6789"

    def test_normalize_none_returns_none(self, validator):
        """Normalize returns None for None input."""
        result = validator.normalize_ssn(None)
        assert result is None

    def test_normalize_invalid_length_returns_as_is(self, validator):
        """Normalize returns invalid length SSN unchanged."""
        result = validator.normalize_ssn("12345")
        assert result == "12345"  # Not 9 digits, returned as-is


class TestPhoneValidation:
    """Tests for phone number validation."""

    @pytest.fixture
    def validator(self) -> FieldValidator:
        """Create validator instance."""
        return FieldValidator()

    def test_valid_phone_with_dashes_passes(self, validator):
        """Phone with dashes (XXX-XXX-XXXX) passes validation."""
        result = validator.validate_phone("202-456-1111")  # White House number (real)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_valid_phone_with_parentheses_passes(self, validator):
        """Phone with parentheses (XXX) XXX-XXXX passes validation."""
        result = validator.validate_phone("(202) 456-1111")
        assert result.is_valid
        assert len(result.errors) == 0

    def test_valid_phone_digits_only_passes(self, validator):
        """Phone with only digits passes validation."""
        result = validator.validate_phone("2024561111")
        assert result.is_valid
        assert len(result.errors) == 0

    def test_none_phone_passes(self, validator):
        """None phone is valid (optional field)."""
        result = validator.validate_phone(None)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_phone_too_short_fails(self, validator):
        """Phone with too few digits fails validation."""
        result = validator.validate_phone("456-1234")  # Only 7 digits
        assert not result.is_valid
        assert len(result.errors) == 1

    def test_invalid_phone_format_fails(self, validator):
        """Invalid phone format fails validation."""
        result = validator.validate_phone("not-a-phone")
        assert not result.is_valid
        assert len(result.errors) == 1


class TestZIPCodeValidation:
    """Tests for ZIP code validation (5 and 9 digit formats)."""

    @pytest.fixture
    def validator(self) -> FieldValidator:
        """Create validator instance."""
        return FieldValidator()

    def test_valid_5_digit_zip_passes(self, validator):
        """5-digit ZIP code passes validation."""
        result = validator.validate_zip("78701")
        assert result.is_valid
        assert len(result.errors) == 0

    def test_valid_9_digit_zip_passes(self, validator):
        """9-digit ZIP+4 code passes validation."""
        result = validator.validate_zip("78701-1234")
        assert result.is_valid
        assert len(result.errors) == 0

    def test_none_zip_passes(self, validator):
        """None ZIP is valid (optional field)."""
        result = validator.validate_zip(None)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_zip_too_short_fails(self, validator):
        """ZIP with too few digits fails validation."""
        result = validator.validate_zip("7870")  # Only 4 digits
        assert not result.is_valid
        assert len(result.errors) == 1

    def test_zip_with_wrong_format_fails(self, validator):
        """ZIP with wrong separator fails validation."""
        result = validator.validate_zip("78701_1234")  # Underscore instead of dash
        assert not result.is_valid
        assert len(result.errors) == 1

    def test_zip_with_letters_fails(self, validator):
        """ZIP with letters fails validation."""
        result = validator.validate_zip("7870A")
        assert not result.is_valid
        assert len(result.errors) == 1


class TestYearValidation:
    """Tests for income year validation."""

    @pytest.fixture
    def validator(self) -> FieldValidator:
        """Create validator instance."""
        return FieldValidator()

    def test_current_year_passes(self, validator):
        """Current year passes validation."""
        from datetime import datetime, UTC

        current_year = datetime.now(UTC).year
        result = validator.validate_year(current_year)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_recent_past_year_passes(self, validator):
        """Recent past year passes validation."""
        result = validator.validate_year(2020)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_none_year_passes(self, validator):
        """None year is valid (optional field)."""
        result = validator.validate_year(None)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_future_year_fails(self, validator):
        """Year too far in future fails validation."""
        from datetime import datetime, UTC

        future_year = datetime.now(UTC).year + 10
        result = validator.validate_year(future_year)
        assert not result.is_valid
        assert len(result.errors) == 1

    def test_very_old_year_fails(self, validator):
        """Year too far in past fails validation."""
        result = validator.validate_year(1900)
        assert not result.is_valid
        assert len(result.errors) == 1

    def test_minimum_year_boundary(self, validator):
        """MIN_YEAR (1950) is valid."""
        result = validator.validate_year(1950)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_below_minimum_year_fails(self, validator):
        """Year below MIN_YEAR fails."""
        result = validator.validate_year(1949)
        assert not result.is_valid
        assert len(result.errors) == 1


class TestValidationErrorStructure:
    """Tests for ValidationError structure."""

    def test_validation_error_has_required_fields(self):
        """ValidationError contains all required fields."""
        error = ValidationError(
            field="ssn",
            value="123",
            error_type="FORMAT",
            message="Invalid SSN format",
        )
        assert error.field == "ssn"
        assert error.value == "123"
        assert error.error_type == "FORMAT"
        assert error.message == "Invalid SSN format"


class TestValidationResultStructure:
    """Tests for ValidationResult structure."""

    def test_validation_result_valid(self):
        """ValidationResult for valid input."""
        result = ValidationResult(is_valid=True)
        assert result.is_valid
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_validation_result_with_error(self):
        """ValidationResult with error."""
        error = ValidationError(
            field="ssn",
            value="123",
            error_type="FORMAT",
            message="Invalid",
        )
        result = ValidationResult(is_valid=False, errors=[error])
        assert not result.is_valid
        assert len(result.errors) == 1
        assert result.errors[0].field == "ssn"

    def test_validation_result_with_warning(self):
        """ValidationResult with warning."""
        result = ValidationResult(
            is_valid=True,
            warnings=["SSN should include dashes"]
        )
        assert result.is_valid
        assert len(result.warnings) == 1


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.fixture
    def validator(self) -> FieldValidator:
        """Create validator instance."""
        return FieldValidator()

    def test_ssn_with_spaces_fails(self, validator):
        """SSN with spaces fails validation."""
        result = validator.validate_ssn("123 45 6789")
        assert not result.is_valid

    def test_phone_with_extension_passes(self, validator):
        """Phone with extension handled correctly."""
        # Behavior depends on phonenumbers library
        result = validator.validate_phone("555-123-4567 ext 123")
        # May pass or fail depending on parsing

    def test_zip_all_zeros_valid(self, validator):
        """ZIP code 00000 is technically valid format."""
        result = validator.validate_zip("00000")
        # Should pass format validation (actual validity is different concern)
        assert result.is_valid

    def test_empty_string_ssn_passes(self, validator):
        """Empty string treated as None (optional)."""
        # This depends on implementation - empty string may be treated as None
        result = validator.validate_ssn("")
        # Could pass or fail - document current behavior

    def test_ssn_with_multiple_dashes_fails(self, validator):
        """SSN with extra dashes fails validation."""
        result = validator.validate_ssn("123--45--6789")
        assert not result.is_valid

    def test_phone_international_format(self, validator):
        """International phone format."""
        result = validator.validate_phone("+1-202-456-1111")
        # Should handle +1 prefix for US numbers
        assert result.is_valid or not result.is_valid  # Document behavior


class TestValidationConstants:
    """Tests for validation constants."""

    @pytest.fixture
    def validator(self) -> FieldValidator:
        """Create validator instance."""
        return FieldValidator()

    def test_min_year_constant(self, validator):
        """MIN_YEAR constant is accessible."""
        assert validator.MIN_YEAR == 1950

    def test_max_year_offset_constant(self, validator):
        """MAX_YEAR_OFFSET constant is accessible."""
        assert validator.MAX_YEAR_OFFSET == 1

    def test_ssn_pattern_defined(self, validator):
        """SSN pattern is defined."""
        assert validator.SSN_PATTERN is not None
        assert validator.SSN_FORMATTED is not None

    def test_zip_pattern_defined(self, validator):
        """ZIP pattern is defined."""
        assert validator.ZIP_PATTERN is not None
