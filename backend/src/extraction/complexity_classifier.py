"""Document complexity classification for LLM model routing.

This module provides heuristic-based classification to determine which
Gemini model to use for extraction:
- STANDARD: Use gemini-3-flash-preview (faster, cheaper)
- COMPLEX: Use gemini-3-pro-preview (better reasoning)

Complexity triggers:
- Multiple borrowers detected
- Large documents (>10 pages)
- Poor scan quality indicators
- Handwritten content detection
"""

import re
from dataclasses import dataclass
from enum import Enum


class ComplexityLevel(str, Enum):
    """Document complexity levels for model selection."""

    STANDARD = "standard"  # Use gemini-3-flash-preview
    COMPLEX = "complex"  # Use gemini-3-pro-preview


@dataclass
class ComplexityAssessment:
    """Result of complexity classification."""

    level: ComplexityLevel
    reasons: list[str]
    page_count: int
    estimated_borrowers: int
    has_handwritten: bool
    has_poor_quality: bool


class ComplexityClassifier:
    """Classifies document complexity for model selection.

    Heuristics based on:
    - Number of potential borrowers (co-borrower indicators)
    - Document length (page count)
    - Scan quality indicators
    - Handwritten content detection

    Example:
        classifier = ComplexityClassifier()
        assessment = classifier.classify(document_text, page_count=5)
        if assessment.level == ComplexityLevel.COMPLEX:
            use_pro_model = True
    """

    # Patterns indicating multiple borrowers
    MULTI_BORROWER_PATTERNS = [
        r"co-borrower",
        r"joint\s+applicant",
        r"spouse",
        r"borrower\s+2",
        r"second\s+borrower",
    ]

    # Patterns indicating poor scan quality
    POOR_QUALITY_PATTERNS = [
        r"\[illegible\]",
        r"\[unclear\]",
        r"\?\?\?",
        r"[^\w\s]{5,}",  # Many consecutive special chars
    ]

    # Patterns indicating handwritten content
    HANDWRITTEN_PATTERNS = [
        r"\[handwritten\]",
        r"signature:",
        r"signed:",
    ]

    def __init__(self) -> None:
        """Initialize classifier with compiled regex patterns."""
        # Compile patterns for efficiency
        self._multi_borrower_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.MULTI_BORROWER_PATTERNS
        ]
        self._poor_quality_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.POOR_QUALITY_PATTERNS
        ]
        self._handwritten_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.HANDWRITTEN_PATTERNS
        ]

    def classify(self, text: str, page_count: int) -> ComplexityAssessment:
        """Classify document complexity based on text and metadata.

        Args:
            text: Full document text (from Docling)
            page_count: Number of pages in document

        Returns:
            ComplexityAssessment with level and reasons
        """
        reasons: list[str] = []

        # Check for multiple borrowers
        borrower_indicators = sum(
            1 for pattern in self._multi_borrower_compiled if pattern.search(text)
        )
        estimated_borrowers = 1 + borrower_indicators

        if borrower_indicators > 0:
            reasons.append(
                f"Multiple borrower indicators found ({borrower_indicators})"
            )

        # Check page count (>10 pages = complex)
        if page_count > 10:
            reasons.append(f"Large document ({page_count} pages)")

        # Check for poor scan quality
        poor_quality_count = sum(
            len(pattern.findall(text)) for pattern in self._poor_quality_compiled
        )
        has_poor_quality = poor_quality_count > 3

        if has_poor_quality:
            reasons.append(f"Poor scan quality indicators ({poor_quality_count})")

        # Check for handwritten content
        handwritten_count = sum(
            len(pattern.findall(text)) for pattern in self._handwritten_compiled
        )
        has_handwritten = handwritten_count > 0

        if has_handwritten:
            reasons.append(f"Handwritten content detected ({handwritten_count})")

        # Determine complexity level
        level = ComplexityLevel.STANDARD
        if (
            estimated_borrowers > 1
            or page_count > 10
            or has_poor_quality
            or has_handwritten
        ):
            level = ComplexityLevel.COMPLEX

        return ComplexityAssessment(
            level=level,
            reasons=reasons if reasons else ["Standard single-borrower document"],
            page_count=page_count,
            estimated_borrowers=estimated_borrowers,
            has_handwritten=has_handwritten,
            has_poor_quality=has_poor_quality,
        )
