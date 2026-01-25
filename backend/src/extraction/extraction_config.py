"""Configuration dataclass for LangExtract extraction settings.

This module provides the ExtractionConfig dataclass for configuring multi-pass
extraction and parallel processing parameters used by LangExtractProcessor.
"""

from dataclasses import dataclass


@dataclass
class ExtractionConfig:
    """Configuration for LangExtract extraction.

    Attributes:
        extraction_passes: Number of extraction passes (2-5). Higher values
            improve recall but increase cost and latency. Default is 2.
        max_workers: Number of parallel workers for chunk processing (1-50).
            Higher values improve speed on long documents but use more memory.
            Default is 10.
        max_char_buffer: Maximum characters per chunk (500-5000). Lower values
            give more precise offsets but require more API calls. Default is 1000.

    Raises:
        ValueError: If any parameter is outside its valid range.

    Example:
        >>> config = ExtractionConfig()
        >>> config.extraction_passes
        2
        >>> config = ExtractionConfig(extraction_passes=3, max_workers=20)
        >>> config.max_workers
        20
    """

    extraction_passes: int = 2
    max_workers: int = 10
    max_char_buffer: int = 1000

    def __post_init__(self) -> None:
        """Validate configuration parameters are within allowed ranges."""
        if not 2 <= self.extraction_passes <= 5:
            raise ValueError(
                f"extraction_passes must be 2-5, got {self.extraction_passes}"
            )
        if not 1 <= self.max_workers <= 50:
            raise ValueError(f"max_workers must be 1-50, got {self.max_workers}")
        if not 500 <= self.max_char_buffer <= 5000:
            raise ValueError(
                f"max_char_buffer must be 500-5000, got {self.max_char_buffer}"
            )
