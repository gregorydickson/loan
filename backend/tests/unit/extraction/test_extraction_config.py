"""Unit tests for ExtractionConfig dataclass validation.

Tests boundary validation for extraction_passes, max_workers, and max_char_buffer
fields per LXTR-06 and LXTR-10 requirements.
"""

import pytest

from src.extraction.extraction_config import ExtractionConfig


class TestExtractionConfigDefaults:
    """Tests for ExtractionConfig default values."""

    def test_default_values(self) -> None:
        """Verify default configuration values are correct."""
        config = ExtractionConfig()
        assert config.extraction_passes == 2
        assert config.max_workers == 10
        assert config.max_char_buffer == 1000

    def test_custom_valid_values(self) -> None:
        """Verify custom values within valid ranges are accepted."""
        config = ExtractionConfig(
            extraction_passes=4,
            max_workers=25,
            max_char_buffer=2500,
        )
        assert config.extraction_passes == 4
        assert config.max_workers == 25
        assert config.max_char_buffer == 2500


class TestExtractionPassesValidation:
    """Tests for extraction_passes field validation (2-5 range)."""

    def test_extraction_passes_minimum(self) -> None:
        """Verify extraction_passes=2 (minimum) is valid."""
        config = ExtractionConfig(extraction_passes=2)
        assert config.extraction_passes == 2

    def test_extraction_passes_maximum(self) -> None:
        """Verify extraction_passes=5 (maximum) is valid."""
        config = ExtractionConfig(extraction_passes=5)
        assert config.extraction_passes == 5

    def test_extraction_passes_below_minimum(self) -> None:
        """Verify extraction_passes=1 raises ValueError."""
        with pytest.raises(ValueError) as excinfo:
            ExtractionConfig(extraction_passes=1)
        assert "extraction_passes must be 2-5" in str(excinfo.value)
        assert "got 1" in str(excinfo.value)

    def test_extraction_passes_above_maximum(self) -> None:
        """Verify extraction_passes=6 raises ValueError."""
        with pytest.raises(ValueError) as excinfo:
            ExtractionConfig(extraction_passes=6)
        assert "extraction_passes must be 2-5" in str(excinfo.value)
        assert "got 6" in str(excinfo.value)


class TestMaxWorkersValidation:
    """Tests for max_workers field validation (1-50 range)."""

    def test_max_workers_minimum(self) -> None:
        """Verify max_workers=1 (minimum) is valid."""
        config = ExtractionConfig(max_workers=1)
        assert config.max_workers == 1

    def test_max_workers_maximum(self) -> None:
        """Verify max_workers=50 (maximum) is valid."""
        config = ExtractionConfig(max_workers=50)
        assert config.max_workers == 50

    def test_max_workers_below_minimum(self) -> None:
        """Verify max_workers=0 raises ValueError."""
        with pytest.raises(ValueError) as excinfo:
            ExtractionConfig(max_workers=0)
        assert "max_workers must be 1-50" in str(excinfo.value)
        assert "got 0" in str(excinfo.value)

    def test_max_workers_above_maximum(self) -> None:
        """Verify max_workers=51 raises ValueError."""
        with pytest.raises(ValueError) as excinfo:
            ExtractionConfig(max_workers=51)
        assert "max_workers must be 1-50" in str(excinfo.value)
        assert "got 51" in str(excinfo.value)


class TestMaxCharBufferValidation:
    """Tests for max_char_buffer field validation (500-5000 range)."""

    def test_max_char_buffer_boundaries(self) -> None:
        """Verify max_char_buffer 500 and 5000 (boundaries) are valid."""
        config_min = ExtractionConfig(max_char_buffer=500)
        assert config_min.max_char_buffer == 500

        config_max = ExtractionConfig(max_char_buffer=5000)
        assert config_max.max_char_buffer == 5000

    def test_max_char_buffer_out_of_range(self) -> None:
        """Verify max_char_buffer 499 and 5001 raise ValueError."""
        with pytest.raises(ValueError) as excinfo:
            ExtractionConfig(max_char_buffer=499)
        assert "max_char_buffer must be 500-5000" in str(excinfo.value)
        assert "got 499" in str(excinfo.value)

        with pytest.raises(ValueError) as excinfo:
            ExtractionConfig(max_char_buffer=5001)
        assert "max_char_buffer must be 500-5000" in str(excinfo.value)
        assert "got 5001" in str(excinfo.value)
