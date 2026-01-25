# Few-Shot Examples Guide

This guide explains how to create and maintain few-shot examples for the LangExtract extraction pipeline.

## Overview

### What Are Few-Shot Examples?

Few-shot examples are curated document samples that teach LangExtract how to extract structured data from loan documents. Instead of defining extraction schemas in code, you show the model what correct extractions look like through concrete examples.

### Why They Matter

LangExtract uses few-shot learning for domain adaptation:
- **Accuracy:** Examples teach the model your specific document formats and terminology
- **Consistency:** Same extraction patterns applied across all documents
- **Customization:** Add new entity types without changing extraction code

### Location

Few-shot examples are stored in:
```
backend/examples/
  __init__.py           # Main exports and validation
  borrower_examples.py  # Borrower extraction examples
  income_examples.py    # Income extraction examples
  account_examples.py   # Account/loan number examples
```

## Example Structure

Each example uses LangExtract's `ExampleData` and `Extraction` classes:

```python
import langextract as lx

example = lx.data.ExampleData(
    text="... document text ...",
    extractions=[
        lx.data.Extraction(
            extraction_class="borrower",
            extraction_text="John Smith",  # MUST be exact substring of text
            attributes={
                "ssn": "123-45-6789",
                "street": "123 Main St",
                "city": "Dallas",
                "state": "TX",
                "zip_code": "75201",
            },
        ),
    ],
)
```

### ExampleData Fields

| Field | Type | Description |
|-------|------|-------------|
| `text` | `str` | Full document text or relevant excerpt |
| `extractions` | `list[Extraction]` | List of extractions from this text |

### Extraction Fields

| Field | Type | Description |
|-------|------|-------------|
| `extraction_class` | `str` | Entity type (borrower, income, account, loan) |
| `extraction_text` | `str` | **EXACT** substring from the text field |
| `attributes` | `dict` | Key-value pairs of extracted attributes |

## Verbatim Text Requirement

**CRITICAL: The `extraction_text` MUST be an exact substring of the `text` field.**

This is validated by `validate_examples()` and will fail if the text is paraphrased or modified in any way.

### Why This Matters

LangExtract uses character offsets to locate extractions in the source document. If `extraction_text` doesn't match exactly:
- Validation will fail
- Extraction quality will degrade
- Character offsets in responses will be incorrect

### Examples

**CORRECT:**
```python
# If text contains: "Borrower Name: Sarah Johnson"
extraction_text="Sarah Johnson"  # Exact match
```

**INCORRECT:**
```python
# If text contains: "Borrower Name: Sarah Johnson"
extraction_text="sarah johnson"  # Wrong - lowercase
extraction_text="Sarah  Johnson"  # Wrong - extra space
extraction_text="S. Johnson"  # Wrong - abbreviated
```

### Validation Command

Run this to verify all examples are valid:

```bash
cd backend && python -c "from examples import validate_examples; validate_examples()"
```

If any extraction_text is not found in its source text, you'll see:
```
ERROR: extraction_text 'S. Johnson' not found in example text for class 'borrower'
```

## Entity Types

### Borrower

Extracted from loan application sections containing personal information.

```python
lx.data.Extraction(
    extraction_class="borrower",
    extraction_text="Sarah Johnson",  # Name as it appears in document
    attributes={
        "ssn": "987-65-4321",           # Format: XXX-XX-XXXX
        "street": "456 Oak Avenue, Apartment 12B",
        "city": "Houston",
        "state": "TX",
        "zip_code": "77001",
        "phone": "(713) 555-9876",
        "email": "sarah.johnson@email.com",
    },
)
```

### Income

Extracted from income verification sections.

```python
lx.data.Extraction(
    extraction_class="income",
    extraction_text="$125,000 (2025)",  # Amount as it appears
    attributes={
        "amount": "125000",              # Numeric only
        "period": "annual",              # annual, monthly, weekly
        "year": "2025",
        "source_type": "employment",     # employment, self-employment, other
        "employer": "TechCorp Industries",
    },
)
```

### Account

Extracted from account information sections.

```python
lx.data.Extraction(
    extraction_class="account",
    extraction_text="1234567890",  # Account number as it appears
    attributes={
        "account_type": "checking",  # checking, savings, business_checking
    },
)
```

### Loan

Extracted from loan identification sections.

```python
lx.data.Extraction(
    extraction_class="loan",
    extraction_text="LN-2025-001234",  # Loan number as it appears
    attributes={
        "loan_type": "mortgage",  # mortgage, auto, personal, line_of_credit
    },
)
```

## Creating New Examples

Follow this workflow to add new examples:

### 1. Identify Representative Document

Select a loan document that represents:
- A document format you frequently process
- A new edge case that current examples don't cover
- A specific extraction pattern that needs improvement

### 2. Extract Relevant Text Section

Copy the exact text from the document. Include enough context for the model to understand the structure:

```python
SAMPLE_TEXT = """LOAN APPLICATION - BORROWER INFORMATION

Primary Borrower: Sarah Johnson
Social Security Number: 987-65-4321
Current Address: 456 Oak Avenue, Apartment 12B, Houston, TX 77001
Phone: (713) 555-9876

EMPLOYMENT INFORMATION
Employer: TechCorp Industries
Annual Salary: $125,000 (2025)
"""
```

### 3. Mark Extraction Spans

For each piece of information to extract, identify the **exact** text span:

```python
# extraction_text must be EXACT substring of SAMPLE_TEXT
extractions = [
    lx.data.Extraction(
        extraction_class="borrower",
        extraction_text="Sarah Johnson",  # Copy exact text
        attributes={"ssn": "987-65-4321"},
    ),
]
```

### 4. Validate Examples

Run validation to ensure all extraction_text values are exact substrings:

```bash
cd backend && python -c "
from examples import validate_examples
errors = validate_examples()
if errors:
    for e in errors:
        print(f'ERROR: {e}')
else:
    print('All examples valid')
"
```

### 5. Test Extraction

Test that the new example improves extraction quality:

```bash
cd backend && python -c "
from examples import ALL_EXAMPLES
import langextract as lx

# Create extractor with examples
extractor = lx.Extractor(examples=ALL_EXAMPLES)

# Test with sample document
with open('test_loan.pdf', 'rb') as f:
    result = extractor.extract(f.read())
    print(result)
"
```

### 6. Commit with Descriptive Message

```bash
git add backend/examples/
git commit -m "feat(examples): add self-employed borrower example

- New example for self-employment income patterns
- Covers multi-year income verification format
- Includes business account extraction
"
```

## Versioning Strategy

### Version Control

Examples are version-controlled in git alongside the application code:
- Changes to examples are tracked in commit history
- Pull requests show example diffs for review
- Rollback is possible through git revert

### Commit Hash Traceability

Each extraction result includes the commit hash of the example set used:
- Allows auditing which examples produced a specific extraction
- Enables A/B testing of example changes

### Tagging Major Changes

For significant example set changes, create a git tag:

```bash
# Tag major example updates
git tag -a examples-v1.2 -m "Add multi-borrower examples"
git push origin examples-v1.2
```

## Best Practices

### DO

- **Copy text exactly** from source documents
- **Include full context** in the text field
- **Validate before committing** with `validate_examples()`
- **Test extraction quality** after adding examples
- **Document unusual patterns** in code comments

### DON'T

- **Don't paraphrase** extraction_text
- **Don't normalize** whitespace or formatting
- **Don't abbreviate** names or numbers
- **Don't include sensitive real data** - anonymize PII
- **Don't skip validation** - broken examples degrade quality

## Troubleshooting

### Validation Fails

**Symptom:** `extraction_text 'X' not found in example text`

**Cause:** The extraction_text is not an exact substring of text

**Fix:**
1. Open the example file
2. Find the extraction that failed
3. Copy the exact text from the `text` field
4. Replace the `extraction_text` value

### Extraction Quality Degrades

**Symptom:** New extractions are less accurate after adding examples

**Cause:** New examples may conflict with existing patterns

**Fix:**
1. Review new examples for consistency with existing ones
2. Ensure attribute names match across similar extractions
3. Consider removing conflicting examples

### Attribute Not Extracted

**Symptom:** An attribute appears in examples but not in extraction results

**Cause:** The attribute may not be consistently represented across examples

**Fix:**
1. Add more examples showing the attribute pattern
2. Ensure the attribute is consistently named across all examples

## Example File Template

Use this template when creating a new example file:

```python
"""Few-shot examples for [ENTITY TYPE] extraction using LangExtract.

This module provides few-shot examples that teach LangExtract how to extract
[ENTITY TYPE] information from loan documents. All extraction_text values
MUST be verbatim substrings of the sample text.
"""

import langextract as lx

# Sample document excerpt - describe what this example represents
SAMPLE_TEXT_1 = """[PASTE EXACT DOCUMENT TEXT HERE]
"""

ENTITY_EXAMPLES = [
    lx.data.ExampleData(
        text=SAMPLE_TEXT_1,
        extractions=[
            lx.data.Extraction(
                extraction_class="entity_type",
                extraction_text="[EXACT TEXT]",  # Must be in SAMPLE_TEXT_1
                attributes={
                    "attribute1": "value1",
                    "attribute2": "value2",
                },
            ),
        ],
    ),
]
```

## See Also

- [Extraction Method Guide](../api/extraction-method-guide.md) - Choosing between Docling and LangExtract
- [GPU Service Cost Guide](./gpu-service-cost.md) - Cost management for OCR processing
- [LangExtract Documentation](https://langextract.dev) - Official LangExtract docs
