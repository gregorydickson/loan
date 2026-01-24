"""Tests for document complexity classification."""

import pytest

from src.extraction.complexity_classifier import (
    ComplexityAssessment,
    ComplexityClassifier,
    ComplexityLevel,
)


@pytest.fixture
def classifier() -> ComplexityClassifier:
    """Create a fresh classifier for each test."""
    return ComplexityClassifier()


class TestComplexityClassifier:
    """Test suite for ComplexityClassifier."""

    def test_simple_document_is_standard(self, classifier: ComplexityClassifier):
        """Single borrower, short doc should be STANDARD."""
        text = """
        Borrower: John Smith
        SSN: 123-45-6789
        Address: 123 Main St, Austin, TX 78701
        Annual Income: $85,000
        """
        assessment = classifier.classify(text, page_count=3)

        assert assessment.level == ComplexityLevel.STANDARD
        assert assessment.estimated_borrowers == 1
        assert assessment.has_handwritten is False
        assert assessment.has_poor_quality is False
        assert "Standard single-borrower document" in assessment.reasons

    def test_multi_borrower_is_complex(self, classifier: ComplexityClassifier):
        """Document with co-borrower indicators should be COMPLEX."""
        text = """
        Borrower: John Smith
        SSN: 123-45-6789

        Co-Borrower: Jane Smith
        SSN: 987-65-4321
        Address: 123 Main St, Austin, TX 78701
        """
        assessment = classifier.classify(text, page_count=5)

        assert assessment.level == ComplexityLevel.COMPLEX
        assert assessment.estimated_borrowers == 2
        assert "Multiple borrower indicators" in assessment.reasons[0]

    def test_joint_applicant_is_complex(self, classifier: ComplexityClassifier):
        """Document with joint applicant should be COMPLEX."""
        text = """
        Primary Applicant: John Smith
        Joint Applicant: Jane Smith
        Combined Income: $150,000
        """
        assessment = classifier.classify(text, page_count=4)

        assert assessment.level == ComplexityLevel.COMPLEX
        assert assessment.estimated_borrowers == 2

    def test_spouse_indicator_is_complex(self, classifier: ComplexityClassifier):
        """Document mentioning spouse should be COMPLEX."""
        text = """
        Borrower: John Smith
        Spouse: Jane Smith
        Combined Assets: $500,000
        """
        assessment = classifier.classify(text, page_count=3)

        assert assessment.level == ComplexityLevel.COMPLEX
        assert assessment.estimated_borrowers == 2

    def test_borrower_2_is_complex(self, classifier: ComplexityClassifier):
        """Document with 'Borrower 2' section should be COMPLEX."""
        text = """
        Borrower 1: John Smith
        SSN: 123-45-6789

        Borrower 2: Jane Smith
        SSN: 987-65-4321
        """
        assessment = classifier.classify(text, page_count=4)

        assert assessment.level == ComplexityLevel.COMPLEX
        assert assessment.estimated_borrowers == 2

    def test_large_document_is_complex(self, classifier: ComplexityClassifier):
        """Document with >10 pages should be COMPLEX."""
        text = "Simple borrower document with minimal content."
        assessment = classifier.classify(text, page_count=15)

        assert assessment.level == ComplexityLevel.COMPLEX
        assert assessment.page_count == 15
        assert any("Large document" in r for r in assessment.reasons)

    def test_exactly_10_pages_is_standard(self, classifier: ComplexityClassifier):
        """Document with exactly 10 pages should be STANDARD."""
        text = "Simple single borrower document."
        assessment = classifier.classify(text, page_count=10)

        assert assessment.level == ComplexityLevel.STANDARD
        assert assessment.page_count == 10

    def test_poor_quality_is_complex(self, classifier: ComplexityClassifier):
        """Document with multiple poor quality indicators should be COMPLEX."""
        text = """
        Borrower: John Smith
        SSN: [illegible]
        Address: [unclear] Main St
        Phone: ???
        Income: $85,000 [illegible] per year
        """
        assessment = classifier.classify(text, page_count=3)

        assert assessment.level == ComplexityLevel.COMPLEX
        assert assessment.has_poor_quality is True
        assert any("Poor scan quality" in r for r in assessment.reasons)

    def test_few_quality_indicators_not_poor(self, classifier: ComplexityClassifier):
        """Few quality indicators (<=3) should not trigger poor quality flag."""
        text = """
        Borrower: John Smith
        SSN: [illegible]
        Address: 123 Main St, Austin, TX
        """
        assessment = classifier.classify(text, page_count=3)

        # Only 1 quality indicator, threshold is >3
        assert assessment.has_poor_quality is False

    def test_handwritten_is_complex(self, classifier: ComplexityClassifier):
        """Document with handwritten content markers should be COMPLEX."""
        text = """
        Borrower: John Smith
        signature: John Smith
        Date: 01/15/2026
        """
        assessment = classifier.classify(text, page_count=2)

        assert assessment.level == ComplexityLevel.COMPLEX
        assert assessment.has_handwritten is True
        assert any("Handwritten content" in r for r in assessment.reasons)

    def test_signed_is_handwritten(self, classifier: ComplexityClassifier):
        """Document with 'signed:' marker should be flagged as handwritten."""
        text = """
        Loan Agreement
        Borrower: John Smith

        signed: John Smith
        Date: 01/15/2026
        """
        assessment = classifier.classify(text, page_count=3)

        assert assessment.has_handwritten is True

    def test_handwritten_marker_is_complex(self, classifier: ComplexityClassifier):
        """Document with [handwritten] annotation should be COMPLEX."""
        text = """
        Borrower: John Smith
        Notes: [handwritten] Additional income from rental property
        """
        assessment = classifier.classify(text, page_count=2)

        assert assessment.level == ComplexityLevel.COMPLEX
        assert assessment.has_handwritten is True

    def test_reasons_populated(self, classifier: ComplexityClassifier):
        """Verify reasons list explains classification correctly."""
        text = """
        Borrower: John Smith
        Co-Borrower: Jane Smith
        signature: John Smith
        """
        assessment = classifier.classify(text, page_count=15)

        # Should have multiple reasons
        assert len(assessment.reasons) >= 2
        # Check specific reasons present
        reason_text = " ".join(assessment.reasons).lower()
        assert "borrower" in reason_text
        assert "handwritten" in reason_text or "large" in reason_text

    def test_multiple_multi_borrower_indicators(
        self, classifier: ComplexityClassifier
    ):
        """Multiple different borrower indicators should sum correctly."""
        text = """
        Borrower: John Smith
        Co-Borrower: Jane Smith
        Second Borrower: Mike Johnson
        Joint Applicant: Sarah Davis
        """
        assessment = classifier.classify(text, page_count=5)

        # Each unique pattern match adds 1 to estimated borrowers
        assert assessment.estimated_borrowers >= 4

    def test_case_insensitive_patterns(self, classifier: ComplexityClassifier):
        """Pattern matching should be case-insensitive."""
        text = """
        BORROWER: John Smith
        CO-BORROWER: Jane Smith
        SIGNATURE: John Smith
        """
        assessment = classifier.classify(text, page_count=3)

        assert assessment.level == ComplexityLevel.COMPLEX
        assert assessment.estimated_borrowers == 2
        assert assessment.has_handwritten is True

    def test_special_char_quality_indicator(self, classifier: ComplexityClassifier):
        """Many consecutive special characters should indicate poor quality."""
        text = """
        Borrower: John Smith
        Address: @#$%^&*()
        Phone: !@#$%
        Income: ^^^^^^
        Notes: <<<<<>>>>>
        """
        assessment = classifier.classify(text, page_count=3)

        # Multiple sequences of 5+ special chars
        assert assessment.has_poor_quality is True

    def test_empty_text_is_standard(self, classifier: ComplexityClassifier):
        """Empty text should be classified as STANDARD."""
        assessment = classifier.classify("", page_count=1)

        assert assessment.level == ComplexityLevel.STANDARD
        assert assessment.estimated_borrowers == 1
