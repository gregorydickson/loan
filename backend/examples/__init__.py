"""Few-shot examples for LangExtract loan document extraction.

This package contains domain-specific few-shot examples that teach LangExtract
how to extract structured data from loan documents. Examples define extraction
schemas through concrete samples rather than code-defined schemas.

CRITICAL: All extraction_text values in examples MUST be verbatim substrings
of the sample text. LangExtract validates alignment and will produce warnings
if extraction_text is paraphrased or modified.

Example Categories:
- borrower_examples: Borrower personal information (name, SSN, address, phone, email)
- income_examples: Income records (employment, self-employment, other income)
- account_examples: Account and loan numbers (checking, savings, mortgage, auto)

Usage:
    from examples import BORROWER_EXAMPLES, INCOME_EXAMPLES, ACCOUNT_EXAMPLES
    from examples import ALL_EXAMPLES, validate_examples

    # Verify examples are valid
    errors = validate_examples()
    if errors:
        raise ValueError(f"Invalid examples: {errors}")

See: .planning/phases/11-langextract-core-integration/11-RESEARCH.md
Requirements: LXTR-04, LXTR-05, LXTR-12
"""

from examples.borrower_examples import BORROWER_EXAMPLES
from examples.income_examples import INCOME_EXAMPLES
from examples.account_examples import ACCOUNT_EXAMPLES

# Combined list of all examples for convenience
ALL_EXAMPLES = BORROWER_EXAMPLES + INCOME_EXAMPLES + ACCOUNT_EXAMPLES

__all__ = [
    "BORROWER_EXAMPLES",
    "INCOME_EXAMPLES",
    "ACCOUNT_EXAMPLES",
    "ALL_EXAMPLES",
    "validate_examples",
]


def validate_examples() -> list[str]:
    """Validate all examples have verbatim extraction_text.

    LangExtract requires extraction_text to exactly match substrings in the
    source text. This validation catches examples that have paraphrased or
    modified extraction text, which would cause "Prompt alignment warnings"
    and degrade extraction quality.

    Returns:
        List of error messages. Empty list means all examples are valid.

    Example:
        >>> errors = validate_examples()
        >>> if errors:
        ...     for e in errors:
        ...         print(f"ERROR: {e}")
        >>> else:
        ...     print("All examples valid")
    """
    errors = []
    for example in ALL_EXAMPLES:
        source_text = example.text
        for extraction in example.extractions:
            extraction_text = extraction.extraction_text
            if extraction_text not in source_text:
                # Truncate long texts for readability
                display_text = (
                    f"{extraction_text[:50]}..."
                    if len(extraction_text) > 50
                    else extraction_text
                )
                errors.append(
                    f"extraction_text '{display_text}' not found in example text "
                    f"for class '{extraction.extraction_class}'"
                )
    return errors
