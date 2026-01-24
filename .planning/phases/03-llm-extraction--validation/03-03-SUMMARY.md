---
phase: 03-llm-extraction-validation
plan: 03
subsystem: extraction
tags: [validation, confidence, phonenumbers, data-quality]

dependency-graph:
  requires: [01-03]  # BorrowerRecord models
  provides: [FieldValidator, ConfidenceCalculator, ValidationResult, ConfidenceBreakdown]
  affects: [03-04, 03-05]  # Orchestration and API plans

tech-stack:
  added:
    - phonenumbers>=8.0.0  # US phone validation
    - rapidfuzz>=3.0.0      # Fuzzy matching for dedup
  patterns:
    - dataclass-based-results  # ValidationResult, ConfidenceBreakdown
    - compiled-regex           # Pre-compiled patterns in FieldValidator

key-files:
  created:
    - backend/src/extraction/validation.py
    - backend/src/extraction/confidence.py
    - backend/tests/extraction/test_validation.py
    - backend/tests/extraction/test_confidence.py
    - backend/src/extraction/__init__.py
    - backend/tests/extraction/__init__.py
  modified:
    - backend/pyproject.toml

decisions:
  - id: phonenumbers-library
    choice: phonenumbers library for phone validation
    rationale: Handles all US formats, validates against NANP rules
  - id: compiled-regex
    choice: Pre-compiled regex patterns at class level
    rationale: Performance - avoids recompilation per validation call
  - id: year-range
    choice: 1950 to current+1 for income year validation
    rationale: Covers historical records, allows projected income

metrics:
  duration: 5 min 27 sec
  completed: 2026-01-24
---

# Phase 3 Plan 03: Validation & Confidence Scoring Summary

**One-liner:** Field validation (SSN/phone/zip/year) and confidence scoring (0.0-1.0) with review threshold flagging

## What Was Built

### FieldValidator (`validation.py`)
Format validation for extracted borrower data fields:

- **SSN validation**: Checks XXX-XX-XXXX format (dashes optional), warns if missing dashes
- **Phone validation**: Uses phonenumbers library for robust US number validation (handles all common formats)
- **ZIP validation**: Accepts 5-digit (XXXXX) and 5+4 (XXXXX-XXXX) formats
- **Year validation**: Ensures income years are in reasonable range (1950 to current+1)

Each validation returns a `ValidationResult` with:
- `is_valid: bool` - Whether validation passed
- `errors: list[ValidationError]` - Detailed error info (field, value, error_type, message)
- `warnings: list[str]` - Non-fatal issues (e.g., SSN without dashes)

### ConfidenceCalculator (`confidence.py`)
Scores extraction confidence based on data completeness:

| Component | Points | Condition |
|-----------|--------|-----------|
| Base | 0.5 | Always applied |
| Required fields | +0.1 each (max 0.2) | name (>1 char), address present |
| Optional fields | +0.05 each (max 0.15) | income_history, account_numbers, loan_numbers |
| Multi-source | +0.1 | source_count > 1 |
| Validation | +0.15 | All formats pass |
| **Max total** | **1.0** | Capped |

Records with `total < 0.7` are flagged with `requires_review=True`.

## Implementation Details

### Dependencies Added
```toml
"rapidfuzz>=3.0.0",   # Fast fuzzy matching (for dedup in Plan 04)
"phonenumbers>=8.0.0" # Robust US phone validation
```

### Key Patterns
1. **Compiled regex at class level** - SSN_PATTERN, ZIP_PATTERN compiled once
2. **Dataclass results** - ValidationResult and ConfidenceBreakdown for structured returns
3. **None-safe validation** - All validators return valid for None (optional fields)
4. **UTC datetime** - Uses `datetime.now(UTC).year` for year validation

### Test Coverage
- **20 validation tests**: SSN (4), phone (3), ZIP (4), year (5), none values (1), dataclasses (3)
- **10 confidence tests**: Scoring scenarios, threshold behavior, bonus caps

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add rapidfuzz and phonenumbers dependencies | 323c27b1 | pyproject.toml |
| 2 | Create FieldValidator for format validation | a9efd7e3 | validation.py, test_validation.py |
| 3 | Create ConfidenceCalculator for scoring | 0409f375 | confidence.py, test_confidence.py |

## Verification Results

```bash
# Import verification
$ python3 -c "from src.extraction.validation import FieldValidator, ValidationResult"
# OK

$ python3 -c "from src.extraction.confidence import ConfidenceCalculator, ConfidenceBreakdown"
# OK

# All tests pass
$ pytest tests/extraction/test_validation.py tests/extraction/test_confidence.py -v
# 30 passed
```

## Requirements Addressed

From 03-RESEARCH.md:
- **VALID-01**: SSN format validation (XXX-XX-XXXX)
- **VALID-02**: Phone validation via phonenumbers library
- **VALID-03**: ZIP code format (XXXXX[-XXXX])
- **VALID-04**: Year validation (income years 1950-current+1)
- **VALID-05**: Validation errors with field, value, type, message
- **VALID-06**: Confidence scoring with review threshold

From EXTRACT requirements:
- **EXTRACT-25**: Confidence score 0.0-1.0
- **EXTRACT-26**: Review flag for low confidence
- **EXTRACT-27**: Field completeness scoring
- **EXTRACT-28**: Multi-source bonus
- **EXTRACT-29**: Validation bonus

## Deviations from Plan

None - plan executed exactly as written.

## Next Steps

**Plan 03-04 (Extraction Orchestrator)** will integrate these components:
- Use FieldValidator to validate extracted fields
- Use ConfidenceCalculator to score and flag records
- Coordinate LLM extraction with validation pipeline
