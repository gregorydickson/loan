"""TDD unit tests for SSN normalization.

Tests the normalize_ssn function that fixes the SSN validation inconsistency.
"""

import pytest

from src.extraction.validation import FieldValidator


class TestSSNNormalization:
    """Test SSN normalization functionality."""

    def test_ssn_without_dashes_is_normalized(self):
        """Test that SSN without dashes gets normalized to XXX-XX-XXXX format."""
        validator = FieldValidator()

        # Test SSN without dashes
        result = validator.normalize_ssn("987654321")
        assert result == "987-65-4321"

    def test_ssn_with_dashes_is_unchanged(self):
        """Test that SSN with dashes remains unchanged."""
        validator = FieldValidator()

        # Test SSN with dashes
        result = validator.normalize_ssn("123-45-6789")
        assert result == "123-45-6789"

    def test_ssn_none_returns_none(self):
        """Test that None SSN returns None."""
        validator = FieldValidator()

        result = validator.normalize_ssn(None)
        assert result is None

    def test_invalid_length_ssn_returns_as_is(self):
        """Test that invalid length SSN is returned as-is for validation to catch."""
        validator = FieldValidator()

        # Too short
        result = validator.normalize_ssn("12345")
        assert result == "12345"

        # Too long
        result = validator.normalize_ssn("1234567890")
        assert result == "1234567890"
