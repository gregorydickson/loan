---
phase: 03-llm-extraction-validation
plan: 05
subsystem: extraction
tags: [consistency, validation, data-quality, cross-document, income-validation]

dependency-graph:
  requires: [03-03, 03-04]  # FieldValidator, ConfidenceCalculator, BorrowerExtractor
  provides: [ConsistencyValidator, ConsistencyWarning]
  affects: [04-01, 04-02]  # API endpoints will expose consistency warnings

tech-stack:
  added: []  # No new dependencies
  patterns:
    - dataclass-warnings  # ConsistencyWarning dataclass
    - post-dedup-validation  # Consistency check after merge
    - multi-strategy-detection  # Address, income, cross-doc checks

key-files:
  created:
    - backend/src/extraction/consistency.py
    - backend/tests/extraction/test_consistency.py
  modified:
    - backend/src/extraction/extractor.py
    - backend/src/extraction/__init__.py
    - backend/tests/extraction/test_extractor.py

decisions:
  - id: income-thresholds
    choice: 50% drop threshold, 300% spike threshold
    rationale: Balances catching anomalies vs false positives
  - id: multi-source-flagging
    choice: Flag any borrower with >1 source + address
    rationale: Conservative - merged records need human verification
  - id: cross-doc-ssn-only
    choice: Only compare SSN last-4 for cross-doc mismatch
    rationale: SSN is definitive identifier; other fields too fuzzy

metrics:
  duration: 14 min 20 sec
  completed: 2026-01-24
---

# Phase 3 Plan 05: Consistency Validation Summary

**One-liner:** ConsistencyValidator flagging address conflicts, income anomalies, and cross-document mismatches for human review

## What Was Built

### ConsistencyValidator (`consistency.py`)
Data quality checks that FLAG issues for review (not auto-resolve):

| Check | Trigger | Warning Type |
|-------|---------|--------------|
| Address Conflict | Borrower has >1 source + address | ADDRESS_CONFLICT |
| Income Drop | >50% year-over-year decline | INCOME_DROP |
| Income Spike | >300% year-over-year increase | INCOME_SPIKE |
| Cross-Document Mismatch | Same name, different SSN last-4 | CROSS_DOC_MISMATCH |

### ConsistencyWarning Dataclass
```python
@dataclass
class ConsistencyWarning:
    warning_type: str      # ADDRESS_CONFLICT, INCOME_DROP, etc.
    borrower_id: UUID      # Which borrower has the issue
    field: str             # Field with inconsistency
    message: str           # Human-readable description
    details: dict          # Additional context
```

### Integration with BorrowerExtractor
- Added `consistency_validator` as required dependency
- Step 4.5 added after deduplication: `consistency_warnings = self.consistency_validator.validate(merged)`
- `ExtractionResult.consistency_warnings` returns typed `list[ConsistencyWarning]`

## Implementation Details

### Validation Flow
```
1. LLM extracts borrowers from chunks
2. BorrowerDeduplicator merges definite duplicates (same SSN, etc.)
3. ConsistencyValidator FLAGS potential issues (same name different SSN, etc.)
4. FieldValidator validates format, ConfidenceCalculator scores
5. ExtractionResult returned with borrowers + validation_errors + consistency_warnings
```

### Key Design: Detect vs Resolve
- **Deduplicator MERGES** records that are definitely the same person
- **ConsistencyValidator FLAGS** records that MIGHT have issues
- Merging is automatic; flagging is for human review

### Test Coverage
- **19 consistency unit tests**: All validation scenarios, thresholds, edge cases
- **3 integration tests**: Income drop detection, multi-source flagging, clean data

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create ConsistencyValidator class | 70659379 | consistency.py, test_consistency.py |
| 2 | Wire ConsistencyValidator into BorrowerExtractor | 02529f03 | extractor.py, __init__.py |
| 3 | Add extractor integration tests | 0cbfed2a | test_extractor.py |

## Deviations from Plan

### [Rule 3 - Blocking] Missing 03-04 Dependency
**Found during:** Plan initialization
**Issue:** Plan 03-04 (BorrowerExtractor, BorrowerDeduplicator) was not complete
**Fix:** Completed 03-04 tasks (schemas, deduplication, extractor) before 03-05
**Commits:** dbd519e8, df1459a2, 22a6eb41

## Verification Results

```bash
# Import verification
$ python3 -c "from src.extraction import ConsistencyValidator, ConsistencyWarning"
# OK

$ python3 -c "from src.extraction import ExtractionResult; print(ExtractionResult.__dataclass_fields__.keys())"
# dict_keys(['borrowers', 'complexity', 'chunks_processed', 'total_tokens', 'validation_errors', 'consistency_warnings'])

# All tests pass
$ pytest tests/extraction/test_consistency.py tests/extraction/test_extractor.py -v
# 34 passed
```

## Requirements Addressed

From 03-RESEARCH.md:
- **VALID-07**: Cross-document consistency (same name, different identifiers)
- **VALID-08**: Income progression validation (drops/spikes flagged)
- **VALID-09**: Address conflict detection (multi-source borrowers)

Key principle: "Conflicts are reported for review, not silently resolved"

## Next Steps

**Phase 03 Complete!** All 5 plans executed:
1. 03-01: GeminiClient with retry and structured output
2. 03-02: ComplexityClassifier and DocumentChunker
3. 03-03: FieldValidator and ConfidenceCalculator
4. 03-04: BorrowerExtractor orchestrator
5. 03-05: ConsistencyValidator

**Phase 04 (Extraction API)** will:
- Expose extraction via REST endpoints
- Return consistency_warnings in API response
- Add extraction status tracking
