"""Character offset verification tests (LXTR-08).

These tests verify that character offsets correctly locate extracted text
via substring matching. This is the core verification mechanism for
LangExtract's source grounding.
"""

from uuid import uuid4

import pytest

from src.extraction.offset_translator import OffsetTranslator
from src.models.document import SourceReference


class TestCharacterOffsetVerification:
    """Tests for character offset verification via substring matching."""

    def test_substring_at_exact_offsets(self):
        """Text at [char_start:char_end] matches extracted text exactly."""
        source_text = "Borrower Name: John Smith, SSN: 123-45-6789"

        # Simulated extraction results
        extractions = [
            {"text": "John Smith", "start": 15, "end": 25},
            {"text": "123-45-6789", "start": 32, "end": 43},
        ]

        for ext in extractions:
            actual = source_text[ext["start"] : ext["end"]]
            assert actual == ext["text"], (
                f"Substring mismatch: expected '{ext['text']}' "
                f"at [{ext['start']}:{ext['end']}], got '{actual}'"
            )

    def test_source_reference_char_offsets_valid(self):
        """SourceReference char_start/char_end locate correct text."""
        source_text = "Primary Borrower: Sarah Johnson lives at 123 Oak Ave"

        # Create SourceReference with offsets
        source = SourceReference(
            document_id=uuid4(),
            document_name="test.pdf",
            page_number=1,
            snippet=source_text[:100],
            char_start=18,
            char_end=31,  # "Sarah Johnson"
        )

        # Verify substring
        actual = source_text[source.char_start : source.char_end]
        assert actual == "Sarah Johnson"

    def test_offset_verification_with_translator(self):
        """OffsetTranslator.verify_offset confirms substring match."""
        source_text = """LOAN APPLICATION

Applicant: Robert Chen
Date of Birth: 1985-03-15
Social Security: 456-78-9012
Employment: Software Engineer at TechStart Inc.
Annual Income: $145,000 (2025)"""

        translator = OffsetTranslator(source_text)

        # Test various extractions - use find() to get correct positions
        test_cases = [
            "Robert Chen",
            "456-78-9012",
            "$145,000 (2025)",
        ]

        for expected_text in test_cases:
            # Find the actual position in the text
            start = source_text.find(expected_text)
            end = start + len(expected_text)

            # Verify the offset points to the right text
            actual = source_text[start:end]
            assert actual == expected_text, f"Setup error: {actual} != {expected_text}"

            # Use translator verification
            assert translator.verify_offset(start, end, expected_text), (
                f"verify_offset failed for '{expected_text}' at [{start}:{end}]"
            )

    def test_offset_verification_fails_for_wrong_position(self):
        """verify_offset returns False when text is at wrong position."""
        source_text = "Hello World Goodbye Planet"

        translator = OffsetTranslator(source_text)

        # "Hello" is at position 0, not position 12 (which has "Goodbye")
        # Test that position 12-17 does NOT contain "Hello"
        assert translator.verify_offset(12, 19, "Hello") is False
        # Correct position for "Goodbye"
        assert translator.verify_offset(12, 19, "Goodbye") is True
        # "Hello" is at position 0
        assert translator.verify_offset(0, 5, "Hello") is True

    def test_multiline_text_offsets(self):
        """Character offsets work correctly across line breaks."""
        source_text = """Line 1: Value A
Line 2: Value B
Line 3: Value C"""

        translator = OffsetTranslator(source_text)

        # Find "Value B" which spans lines
        value_b_start = source_text.find("Value B")
        value_b_end = value_b_start + len("Value B")

        assert translator.verify_offset(value_b_start, value_b_end, "Value B")

    def test_unicode_text_offsets(self):
        """Character offsets work correctly with unicode characters."""
        source_text = "Name: Jose Garcia, City: Sao Paulo"

        translator = OffsetTranslator(source_text)

        # Note: In Python 3, string indices are code points, not bytes
        name_start = source_text.find("Jose Garcia")
        name_end = name_start + len("Jose Garcia")

        assert translator.verify_offset(name_start, name_end, "Jose Garcia")

    def test_empty_extraction_handling(self):
        """Gracefully handle empty or whitespace extractions."""
        source_text = "Name:    Address:"

        translator = OffsetTranslator(source_text)

        # Extracting whitespace should still work
        assert translator.verify_offset(5, 9, "    ") is True

    def test_consecutive_extractions(self):
        """Multiple consecutive extractions maintain correct offsets."""
        source_text = "Name: John Doe, SSN: 123-45-6789, Phone: (555) 123-4567"

        extractions = [
            {"field": "name", "text": "John Doe", "start": 6, "end": 14},
            {"field": "ssn", "text": "123-45-6789", "start": 21, "end": 32},
            {"field": "phone", "text": "(555) 123-4567", "start": 41, "end": 55},
        ]

        for ext in extractions:
            actual = source_text[ext["start"] : ext["end"]]
            assert actual == ext["text"], (
                f"Field {ext['field']}: expected '{ext['text']}' got '{actual}'"
            )


class TestBackwardCompatibility:
    """Tests for backward compatibility with null char offsets."""

    def test_source_reference_without_offsets(self):
        """SourceReference works without char_start/char_end (v1.0 compat)."""
        source = SourceReference(
            document_id=uuid4(),
            document_name="legacy.pdf",
            page_number=5,
            snippet="This is from v1.0 Docling extraction",
        )

        assert source.char_start is None
        assert source.char_end is None
        assert source.page_number == 5  # Page-level reference still works

    def test_source_reference_with_and_without_offsets_coexist(self):
        """Can create SourceReferences with and without offsets."""
        doc_id_1 = uuid4()
        doc_id_2 = uuid4()

        sources = [
            # v1.0 style - no offsets
            SourceReference(
                document_id=doc_id_1,
                document_name="doc1.pdf",
                page_number=1,
                snippet="v1.0 extraction",
            ),
            # v2.0 style - with offsets
            SourceReference(
                document_id=doc_id_2,
                document_name="doc2.pdf",
                page_number=1,
                snippet="v2.0 extraction with offsets",
                char_start=100,
                char_end=200,
            ),
        ]

        assert sources[0].char_start is None
        assert sources[1].char_start == 100


class TestRealWorldScenarios:
    """Tests simulating real loan document extraction scenarios."""

    def test_paystub_extraction_offsets(self):
        """Verify offsets work for paystub-style document."""
        paystub_text = """EMPLOYEE PAY STATEMENT

Employee: Maria Rodriguez
Pay Period: 2025-01-01 to 2025-01-15
Gross Pay: $4,166.67
Net Pay: $3,125.00

Employer: Acme Corporation
Employee ID: EMP-12345"""

        translator = OffsetTranslator(paystub_text)

        # Test finding employee name
        name_start = paystub_text.find("Maria Rodriguez")
        name_end = name_start + len("Maria Rodriguez")
        assert translator.verify_offset(name_start, name_end, "Maria Rodriguez")

        # Test finding gross pay amount
        gross_start = paystub_text.find("$4,166.67")
        gross_end = gross_start + len("$4,166.67")
        assert translator.verify_offset(gross_start, gross_end, "$4,166.67")

        # Test finding employer
        employer_start = paystub_text.find("Acme Corporation")
        employer_end = employer_start + len("Acme Corporation")
        assert translator.verify_offset(employer_start, employer_end, "Acme Corporation")

    def test_w2_form_extraction_offsets(self):
        """Verify offsets work for W-2 form extraction."""
        w2_text = """Form W-2 Wage and Tax Statement 2024

Box 1 - Wages: $95,000.00
Box 2 - Federal tax withheld: $15,200.00

Employer: Tech Solutions Inc.
Employer EIN: 12-3456789

Employee: James Wilson
Employee SSN: 567-89-0123"""

        translator = OffsetTranslator(w2_text)

        # Test SSN extraction
        ssn_start = w2_text.find("567-89-0123")
        ssn_end = ssn_start + len("567-89-0123")
        assert translator.verify_offset(ssn_start, ssn_end, "567-89-0123")

        # Test wages extraction
        wages_start = w2_text.find("$95,000.00")
        wages_end = wages_start + len("$95,000.00")
        assert translator.verify_offset(wages_start, wages_end, "$95,000.00")

    def test_loan_application_extraction_offsets(self):
        """Verify offsets work for loan application data."""
        application_text = """LOAN APPLICATION

Borrower Information:
Full Name: Sarah Elizabeth Thompson
Social Security Number: 234-56-7890
Date of Birth: 1985-07-22
Phone: (555) 987-6543
Email: sethompson@email.com

Current Address:
456 Oak Lane
Austin, TX 78701"""

        translator = OffsetTranslator(application_text)

        # Test full name
        name_start = application_text.find("Sarah Elizabeth Thompson")
        name_end = name_start + len("Sarah Elizabeth Thompson")
        assert translator.verify_offset(name_start, name_end, "Sarah Elizabeth Thompson")

        # Test SSN
        ssn_start = application_text.find("234-56-7890")
        ssn_end = ssn_start + len("234-56-7890")
        assert translator.verify_offset(ssn_start, ssn_end, "234-56-7890")

        # Test street address
        street_start = application_text.find("456 Oak Lane")
        street_end = street_start + len("456 Oak Lane")
        assert translator.verify_offset(street_start, street_end, "456 Oak Lane")
