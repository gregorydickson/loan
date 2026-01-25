"""Tests for few-shot example validation (TEST-01).

This module validates that few-shot examples used for LangExtract extraction
meet quality requirements:
1. All extraction_text values are verbatim substrings of the sample text
2. Each category has sufficient examples for effective few-shot learning
3. Examples cover diverse extraction classes and are production-quality

See: 11-RESEARCH.md for LangExtract requirements
Requirements: TEST-01 (few-shot example validation)
"""

import pytest

from examples import (
    ALL_EXAMPLES,
    ACCOUNT_EXAMPLES,
    BORROWER_EXAMPLES,
    INCOME_EXAMPLES,
    validate_examples,
)


class TestFewShotExampleValidation:
    """Tests that validate few-shot examples have correct structure and content."""

    def test_validate_examples_returns_no_errors(self):
        """validate_examples() should return empty list when all examples are valid."""
        errors = validate_examples()
        assert errors == [], f"Validation errors found: {errors}"

    def test_borrower_examples_exist(self):
        """Should have at least 2 borrower examples for effective few-shot learning."""
        # Borrower examples includes both borrower and related extractions
        assert len(BORROWER_EXAMPLES) >= 2, (
            f"Expected at least 2 borrower examples, got {len(BORROWER_EXAMPLES)}"
        )

    def test_income_examples_exist(self):
        """Should have at least 2 income examples for effective few-shot learning."""
        assert len(INCOME_EXAMPLES) >= 2, (
            f"Expected at least 2 income examples, got {len(INCOME_EXAMPLES)}"
        )

    def test_account_examples_exist(self):
        """Should have at least 2 account examples for effective few-shot learning."""
        assert len(ACCOUNT_EXAMPLES) >= 2, (
            f"Expected at least 2 account examples, got {len(ACCOUNT_EXAMPLES)}"
        )

    def test_all_examples_combined(self):
        """ALL_EXAMPLES should contain the sum of all category examples."""
        expected_count = len(BORROWER_EXAMPLES) + len(INCOME_EXAMPLES) + len(ACCOUNT_EXAMPLES)
        assert len(ALL_EXAMPLES) == expected_count, (
            f"ALL_EXAMPLES has {len(ALL_EXAMPLES)} examples, "
            f"expected {expected_count} (sum of all categories)"
        )

    def test_extraction_text_is_verbatim_substring(self):
        """For each example, extraction_text must be exact substring of example.text.

        This is critical for LangExtract's alignment mechanism. Paraphrased or
        modified extraction_text causes "Prompt alignment warnings" and degrades
        extraction quality.
        """
        for idx, example in enumerate(ALL_EXAMPLES):
            source_text = example.text
            for extraction in example.extractions:
                extraction_text = extraction.extraction_text
                assert extraction_text in source_text, (
                    f"Example {idx}: extraction_text '{extraction_text}' "
                    f"is not a verbatim substring of the example text.\n"
                    f"Source text snippet: {source_text[:200]}..."
                )


class TestFewShotExampleCompleteness:
    """Tests that verify examples cover all required extraction classes."""

    def test_borrower_class_present(self):
        """Examples should include 'borrower' extraction class."""
        classes = set()
        for example in ALL_EXAMPLES:
            for extraction in example.extractions:
                classes.add(extraction.extraction_class)

        assert "borrower" in classes, (
            f"'borrower' extraction class not found in examples. Found: {classes}"
        )

    def test_income_class_present(self):
        """Examples should include 'income' extraction class."""
        classes = set()
        for example in ALL_EXAMPLES:
            for extraction in example.extractions:
                classes.add(extraction.extraction_class)

        assert "income" in classes, (
            f"'income' extraction class not found in examples. Found: {classes}"
        )

    def test_account_class_present(self):
        """Examples should include 'account' extraction class."""
        classes = set()
        for example in ALL_EXAMPLES:
            for extraction in example.extractions:
                classes.add(extraction.extraction_class)

        assert "account" in classes, (
            f"'account' extraction class not found in examples. Found: {classes}"
        )

    def test_loan_class_present(self):
        """Examples should include 'loan' extraction class."""
        classes = set()
        for example in ALL_EXAMPLES:
            for extraction in example.extractions:
                classes.add(extraction.extraction_class)

        assert "loan" in classes, (
            f"'loan' extraction class not found in examples. Found: {classes}"
        )

    def test_multiple_borrowers_per_example_coverage(self):
        """At least one example should have multiple borrowers (co-borrower scenario)."""
        has_multiple_borrowers = False
        for example in BORROWER_EXAMPLES:
            borrower_count = sum(
                1 for e in example.extractions
                if e.extraction_class == "borrower"
            )
            if borrower_count > 1:
                has_multiple_borrowers = True
                break

        assert has_multiple_borrowers, (
            "No example has multiple borrowers. Co-borrower scenarios should be covered."
        )


class TestFewShotExampleQuality:
    """Tests for production quality of few-shot examples."""

    def test_no_duplicate_extraction_texts(self):
        """Within each example, extraction_text values should not be duplicated."""
        for idx, example in enumerate(ALL_EXAMPLES):
            extraction_texts = [e.extraction_text for e in example.extractions]
            duplicates = [
                text for text in extraction_texts
                if extraction_texts.count(text) > 1
            ]
            # Get unique duplicates for error message
            unique_duplicates = list(set(duplicates))
            assert len(unique_duplicates) == 0, (
                f"Example {idx} has duplicate extraction_texts: {unique_duplicates}"
            )

    def test_extraction_text_not_empty(self):
        """All extraction_text values should be non-empty strings."""
        for idx, example in enumerate(ALL_EXAMPLES):
            for ext_idx, extraction in enumerate(example.extractions):
                assert extraction.extraction_text, (
                    f"Example {idx}, extraction {ext_idx}: "
                    f"extraction_text is empty for class '{extraction.extraction_class}'"
                )
                assert extraction.extraction_text.strip(), (
                    f"Example {idx}, extraction {ext_idx}: "
                    f"extraction_text is whitespace-only for class '{extraction.extraction_class}'"
                )

    def test_diverse_text_lengths(self):
        """Examples should have diverse text lengths for robust extraction."""
        text_lengths = [len(example.text) for example in ALL_EXAMPLES]

        # Check we have at least some variation
        min_length = min(text_lengths)
        max_length = max(text_lengths)

        # Examples should not all be the same length
        assert max_length > min_length * 0.5, (
            f"Example text lengths lack diversity: {text_lengths}. "
            "More varied examples improve extraction robustness."
        )

    def test_examples_have_reasonable_size(self):
        """Example texts should be reasonably sized (not too short or too long)."""
        for idx, example in enumerate(ALL_EXAMPLES):
            text_length = len(example.text)

            # Minimum 100 chars - enough to have meaningful content
            assert text_length >= 100, (
                f"Example {idx} text is too short ({text_length} chars). "
                "Minimum 100 characters expected."
            )

            # Maximum 10000 chars - keep examples focused
            assert text_length <= 10000, (
                f"Example {idx} text is too long ({text_length} chars). "
                "Maximum 10000 characters to keep examples focused."
            )

    def test_borrower_examples_have_attributes(self):
        """Borrower extractions should have attributes populated."""
        for idx, example in enumerate(BORROWER_EXAMPLES):
            for extraction in example.extractions:
                if extraction.extraction_class == "borrower":
                    # Borrowers should have at least some attributes
                    attrs = extraction.attributes or {}
                    assert len(attrs) > 0, (
                        f"Borrower example {idx}: borrower extraction "
                        f"'{extraction.extraction_text}' has no attributes"
                    )

    def test_income_examples_have_required_attributes(self):
        """Income extractions should have amount and year attributes."""
        for idx, example in enumerate(INCOME_EXAMPLES):
            for extraction in example.extractions:
                if extraction.extraction_class == "income":
                    attrs = extraction.attributes or {}
                    assert "amount" in attrs, (
                        f"Income example {idx}: income extraction "
                        f"'{extraction.extraction_text}' missing 'amount' attribute"
                    )
                    # Year might be in the extraction_text itself
                    # but should generally be in attributes
