"""Unit tests for ComplexityClassifier.

Tests document complexity classification for model routing:
- Multi-borrower detection patterns
- Page count thresholds
- Poor scan quality indicators
- Handwritten content detection
- Combined complexity triggers
- Pattern compilation and matching
"""

import pytest

from src.extraction.complexity_classifier import (
    ComplexityAssessment,
    ComplexityClassifier,
    ComplexityLevel,
)


class TestStandardDocuments:
    """Tests for documents classified as STANDARD complexity."""

    @pytest.fixture
    def classifier(self) -> ComplexityClassifier:
        """Create classifier instance."""
        return ComplexityClassifier()

    def test_simple_single_borrower_is_standard(self, classifier):
        """Simple single-borrower document is STANDARD."""
        text = """
        Borrower Name: John Smith
        Address: 123 Main St, Austin, TX 78701
        Income: $100,000 annually
        """
        assessment = classifier.classify(text, page_count=1)
        assert assessment.level == ComplexityLevel.STANDARD
        assert assessment.estimated_borrowers == 1
        assert assessment.has_handwritten is False
        assert assessment.has_poor_quality is False
        assert "Standard single-borrower document" in assessment.reasons

    def test_short_document_is_standard(self, classifier):
        """Short document (≤10 pages) is STANDARD."""
        text = "Borrower Name: John Smith"
        assessment = classifier.classify(text, page_count=10)
        assert assessment.level == ComplexityLevel.STANDARD
        assert assessment.page_count == 10

    def test_empty_text_is_standard(self, classifier):
        """Empty text is STANDARD."""
        assessment = classifier.classify("", page_count=1)
        assert assessment.level == ComplexityLevel.STANDARD
        assert assessment.estimated_borrowers == 1


class TestMultiBorrowerDetection:
    """Tests for multi-borrower pattern detection."""

    @pytest.fixture
    def classifier(self) -> ComplexityClassifier:
        """Create classifier instance."""
        return ComplexityClassifier()

    def test_coborrower_keyword_triggers_complex(self, classifier):
        """'co-borrower' keyword triggers COMPLEX."""
        text = "Primary borrower: John Smith\nCo-borrower: Jane Smith"
        assessment = classifier.classify(text, page_count=1)
        assert assessment.level == ComplexityLevel.COMPLEX
        assert assessment.estimated_borrowers == 2
        assert any("Multiple borrower" in r for r in assessment.reasons)

    def test_coborrower_case_insensitive(self, classifier):
        """Co-borrower detection is case-insensitive."""
        text = "CO-BORROWER: Jane Smith"
        assessment = classifier.classify(text, page_count=1)
        assert assessment.level == ComplexityLevel.COMPLEX
        assert assessment.estimated_borrowers == 2

    def test_joint_applicant_triggers_complex(self, classifier):
        """'joint applicant' keyword triggers COMPLEX."""
        text = "Joint applicant information: Jane Smith"
        assessment = classifier.classify(text, page_count=1)
        assert assessment.level == ComplexityLevel.COMPLEX
        assert assessment.estimated_borrowers == 2

    def test_spouse_keyword_triggers_complex(self, classifier):
        """'spouse' keyword triggers COMPLEX."""
        text = "Spouse income: $50,000"
        assessment = classifier.classify(text, page_count=1)
        assert assessment.level == ComplexityLevel.COMPLEX
        assert assessment.estimated_borrowers == 2

    def test_borrower_2_triggers_complex(self, classifier):
        """'borrower 2' keyword triggers COMPLEX."""
        text = "Borrower 1: John\nBorrower 2: Jane"
        assessment = classifier.classify(text, page_count=1)
        assert assessment.level == ComplexityLevel.COMPLEX
        assert assessment.estimated_borrowers == 2

    def test_second_borrower_triggers_complex(self, classifier):
        """'second borrower' keyword triggers COMPLEX."""
        text = "Second borrower details: Jane Smith"
        assessment = classifier.classify(text, page_count=1)
        assert assessment.level == ComplexityLevel.COMPLEX
        assert assessment.estimated_borrowers == 2

    def test_multiple_borrower_patterns_counted(self, classifier):
        """Multiple borrower patterns increase count."""
        text = """
        Co-borrower: Jane Smith
        Spouse income: $50,000
        Joint applicant
        """
        assessment = classifier.classify(text, page_count=1)
        assert assessment.level == ComplexityLevel.COMPLEX
        # 1 base + 3 indicators = 4 estimated borrowers
        assert assessment.estimated_borrowers == 4


class TestPageCountThreshold:
    """Tests for page count threshold (>10 = complex)."""

    @pytest.fixture
    def classifier(self) -> ComplexityClassifier:
        """Create classifier instance."""
        return ComplexityClassifier()

    def test_eleven_pages_is_complex(self, classifier):
        """11 pages triggers COMPLEX."""
        text = "Single borrower document"
        assessment = classifier.classify(text, page_count=11)
        assert assessment.level == ComplexityLevel.COMPLEX
        assert any("Large document (11 pages)" in r for r in assessment.reasons)

    def test_fifty_pages_is_complex(self, classifier):
        """50 pages triggers COMPLEX."""
        text = "Single borrower document"
        assessment = classifier.classify(text, page_count=50)
        assert assessment.level == ComplexityLevel.COMPLEX
        assert any("Large document (50 pages)" in r for r in assessment.reasons)

    def test_exactly_ten_pages_is_standard(self, classifier):
        """Exactly 10 pages is still STANDARD."""
        text = "Single borrower document"
        assessment = classifier.classify(text, page_count=10)
        assert assessment.level == ComplexityLevel.STANDARD


class TestPoorQualityDetection:
    """Tests for poor scan quality indicators."""

    @pytest.fixture
    def classifier(self) -> ComplexityClassifier:
        """Create classifier instance."""
        return ComplexityClassifier()

    def test_illegible_markers_trigger_complex(self, classifier):
        """Multiple [illegible] markers trigger COMPLEX."""
        text = """
        Name: [illegible]
        Address: [illegible]
        Income: [illegible]
        Employer: [illegible]
        """
        assessment = classifier.classify(text, page_count=1)
        assert assessment.level == ComplexityLevel.COMPLEX
        assert assessment.has_poor_quality is True
        assert any("Poor scan quality" in r for r in assessment.reasons)

    def test_unclear_markers_trigger_complex(self, classifier):
        """Multiple [unclear] markers trigger COMPLEX."""
        text = """
        [unclear] text here
        [unclear] more text
        [unclear] even more
        [unclear] last one
        """
        assessment = classifier.classify(text, page_count=1)
        assert assessment.level == ComplexityLevel.COMPLEX
        assert assessment.has_poor_quality is True

    def test_question_marks_trigger_complex(self, classifier):
        """Multiple ??? patterns trigger COMPLEX."""
        text = "Name: ??? Income: ??? Address: ??? Employer: ???"
        assessment = classifier.classify(text, page_count=1)
        assert assessment.level == ComplexityLevel.COMPLEX
        assert assessment.has_poor_quality is True

    def test_many_special_chars_trigger_complex(self, classifier):
        """Many consecutive special characters trigger COMPLEX."""
        text = """
        Text @#$%^ garbage
        More &*()! noise
        Even }{[]| more
        Last ~`!@# one
        """
        assessment = classifier.classify(text, page_count=1)
        assert assessment.level == ComplexityLevel.COMPLEX
        assert assessment.has_poor_quality is True

    def test_few_quality_issues_is_standard(self, classifier):
        """3 or fewer quality indicators is STANDARD (threshold is >3)."""
        text = "[illegible] text and [unclear] text and ??? text"
        assessment = classifier.classify(text, page_count=1)
        assert assessment.level == ComplexityLevel.STANDARD
        assert assessment.has_poor_quality is False


class TestHandwrittenDetection:
    """Tests for handwritten content indicators."""

    @pytest.fixture
    def classifier(self) -> ComplexityClassifier:
        """Create classifier instance."""
        return ComplexityClassifier()

    def test_handwritten_marker_triggers_complex(self, classifier):
        """[handwritten] marker triggers COMPLEX."""
        text = "Name: [handwritten] John Smith"
        assessment = classifier.classify(text, page_count=1)
        assert assessment.level == ComplexityLevel.COMPLEX
        assert assessment.has_handwritten is True
        assert any("Handwritten content" in r for r in assessment.reasons)

    def test_signature_marker_triggers_complex(self, classifier):
        """'signature:' marker triggers COMPLEX."""
        text = "Signature: [handwritten signature]"
        assessment = classifier.classify(text, page_count=1)
        assert assessment.level == ComplexityLevel.COMPLEX
        assert assessment.has_handwritten is True

    def test_signed_marker_triggers_complex(self, classifier):
        """'signed:' marker triggers COMPLEX."""
        text = "Signed: John Smith (handwritten)"
        assessment = classifier.classify(text, page_count=1)
        assert assessment.level == ComplexityLevel.COMPLEX
        assert assessment.has_handwritten is True

    def test_multiple_handwritten_markers_counted(self, classifier):
        """Multiple handwritten markers are counted."""
        text = """
        [handwritten] note
        Signature: John
        Signed: Jane
        """
        assessment = classifier.classify(text, page_count=1)
        assert assessment.level == ComplexityLevel.COMPLEX
        assert "Handwritten content detected (3)" in assessment.reasons


class TestCombinedComplexityTriggers:
    """Tests for multiple complexity factors combined."""

    @pytest.fixture
    def classifier(self) -> ComplexityClassifier:
        """Create classifier instance."""
        return ComplexityClassifier()

    def test_multiple_triggers_all_listed(self, classifier):
        """Multiple complexity triggers are all listed in reasons."""
        text = """
        Co-borrower: Jane Smith
        [illegible] [illegible] [illegible] [illegible]
        [handwritten] signature
        """
        assessment = classifier.classify(text, page_count=15)
        assert assessment.level == ComplexityLevel.COMPLEX
        assert len(assessment.reasons) == 4  # Multi-borrower, large doc, poor quality, handwritten
        assert any("Multiple borrower" in r for r in assessment.reasons)
        assert any("Large document" in r for r in assessment.reasons)
        assert any("Poor scan quality" in r for r in assessment.reasons)
        assert any("Handwritten" in r for r in assessment.reasons)

    def test_any_single_trigger_makes_complex(self, classifier):
        """Any single complexity trigger makes document COMPLEX."""
        # Test each trigger independently
        texts_and_pages = [
            ("Co-borrower: Jane", 1),  # Multi-borrower
            ("Simple text", 11),  # Page count
            ("[illegible] [illegible] [illegible] [illegible]", 1),  # Poor quality
            ("[handwritten] note", 1),  # Handwritten
        ]
        for text, pages in texts_and_pages:
            assessment = classifier.classify(text, pages)
            assert assessment.level == ComplexityLevel.COMPLEX


class TestComplexityAssessmentStructure:
    """Tests for ComplexityAssessment dataclass."""

    def test_assessment_has_all_fields(self):
        """ComplexityAssessment contains all required fields."""
        assessment = ComplexityAssessment(
            level=ComplexityLevel.COMPLEX,
            reasons=["Multiple borrowers"],
            page_count=15,
            estimated_borrowers=2,
            has_handwritten=True,
            has_poor_quality=False,
        )
        assert assessment.level == ComplexityLevel.COMPLEX
        assert assessment.reasons == ["Multiple borrowers"]
        assert assessment.page_count == 15
        assert assessment.estimated_borrowers == 2
        assert assessment.has_handwritten is True
        assert assessment.has_poor_quality is False


class TestComplexityLevelEnum:
    """Tests for ComplexityLevel enum."""

    def test_complexity_levels_defined(self):
        """ComplexityLevel enum has expected values."""
        assert ComplexityLevel.STANDARD == "standard"
        assert ComplexityLevel.COMPLEX == "complex"

    def test_enum_string_values(self):
        """ComplexityLevel values are strings."""
        assert isinstance(ComplexityLevel.STANDARD.value, str)
        assert isinstance(ComplexityLevel.COMPLEX.value, str)


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.fixture
    def classifier(self) -> ComplexityClassifier:
        """Create classifier instance."""
        return ComplexityClassifier()

    def test_zero_pages_is_standard(self, classifier):
        """0 pages is STANDARD (edge case)."""
        text = "Some text"
        assessment = classifier.classify(text, page_count=0)
        assert assessment.level == ComplexityLevel.STANDARD

    def test_negative_pages_is_standard(self, classifier):
        """Negative pages is STANDARD (shouldn't happen but handled)."""
        text = "Some text"
        assessment = classifier.classify(text, page_count=-1)
        assert assessment.level == ComplexityLevel.STANDARD

    def test_very_long_text_single_page(self, classifier):
        """Very long text on single page is STANDARD if no triggers."""
        text = "A" * 100000  # 100k characters
        assessment = classifier.classify(text, page_count=1)
        assert assessment.level == ComplexityLevel.STANDARD

    def test_unicode_text_handled(self, classifier):
        """Unicode text is handled correctly."""
        text = "Borrower: José García\nSpouse: María García"
        assessment = classifier.classify(text, page_count=1)
        assert assessment.level == ComplexityLevel.COMPLEX  # Spouse triggers
        assert assessment.estimated_borrowers == 2

    def test_patterns_at_text_boundaries(self, classifier):
        """Patterns at text start/end are detected."""
        text_start = "co-borrower at start"
        text_end = "at end co-borrower"
        for text in [text_start, text_end]:
            assessment = classifier.classify(text, page_count=1)
            assert assessment.level == ComplexityLevel.COMPLEX

    def test_partial_pattern_matches_not_counted(self, classifier):
        """Partial pattern matches are not counted."""
        text = "borrower1 (no space) and coborrower (no dash)"
        assessment = classifier.classify(text, page_count=1)
        # These shouldn't match the patterns
        assert assessment.estimated_borrowers == 1
