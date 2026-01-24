---
phase: 03-llm-extraction-validation
plan: 04
subsystem: extraction
tags: [orchestrator, extraction, deduplication, gemini, llm, validation]

dependencies:
  requires: ["03-01", "03-02", "03-03"]
  provides:
    - BorrowerExtractor orchestrating full extraction pipeline
    - Gemini-compatible extraction schemas
    - BorrowerDeduplicator with multi-strategy matching
  affects: ["03-05", "04-xx"]

tech-stack:
  added: []
  patterns:
    - Pipeline orchestration pattern (classify -> chunk -> extract -> dedupe -> validate)
    - Pydantic validation error handling (graceful degradation)
    - Fuzzy matching with rapidfuzz for deduplication

key-files:
  created:
    - backend/src/extraction/schemas.py
    - backend/src/extraction/deduplication.py
  modified:
    - backend/src/extraction/extractor.py
    - backend/src/extraction/__init__.py
    - backend/tests/extraction/test_extractor.py
    - backend/tests/extraction/test_deduplication.py

decisions:
  - decision: Gemini-compatible schemas separate from storage models
    rationale: LLM output needs simpler types (no UUIDs, sources); conversion happens in extractor
  - decision: Multi-strategy deduplication (SSN > account > fuzzy name)
    rationale: Different matching strategies for different confidence levels
  - decision: Pydantic validation errors caught and tracked
    rationale: Invalid LLM output shouldn't crash extraction; errors should be visible

metrics:
  duration: 14 min
  completed: 2026-01-24
---

# Phase 03 Plan 04: Extraction Orchestrator Summary

**One-liner:** BorrowerExtractor orchestrating classify -> chunk -> extract -> deduplicate -> validate pipeline with Gemini-compatible schemas and fuzzy deduplication

## What Was Built

### 1. Gemini-Compatible Extraction Schemas (schemas.py)
- `ExtractedAddress` - Simple address for LLM output
- `ExtractedIncome` - Income with float (not Decimal) for JSON compatibility
- `ExtractedBorrower` - Complete borrower without UUIDs/sources
- `BorrowerExtractionResult` - Top-level schema for Gemini structured output
- Uses `Optional[T] = None` pattern (not `Field(default=...)`) for Gemini compatibility

### 2. BorrowerDeduplicator (deduplication.py)
Multi-strategy duplicate detection with priority ordering:
1. **Exact SSN match** - Highest confidence
2. **Account number overlap** - Any shared account number
3. **Fuzzy name (90%+) + same ZIP** - Address corroboration
4. **Very high name (95%+)** - Name alone sufficient
5. **Moderate name (80%+) + last 4 SSN** - Partial identifier match

Merge behavior:
- Higher confidence record used as base
- Income histories combined (deduped)
- Account/loan numbers unioned
- Sources merged from all records
- Missing fields filled from other record

### 3. BorrowerExtractor Orchestrator (extractor.py)
Complete extraction pipeline:
1. **Complexity assessment** - Route to Flash or Pro model
2. **Document chunking** - Split large docs with overlap
3. **LLM extraction** - Call Gemini for each chunk
4. **Deduplication** - Merge duplicates across chunks
5. **Validation** - Check SSN, phone, ZIP formats
6. **Confidence scoring** - Calculate based on completeness

Key features:
- Pydantic validation errors caught and tracked (not crash)
- Source attribution added to every borrower
- Page number estimation from character position
- Token usage tracking across all chunks

### 4. Module Exports (__init__.py)
Comprehensive exports for all extraction components:
- Core: `BorrowerExtractor`, `ExtractionResult`
- LLM: `GeminiClient`, `LLMResponse`
- Classification: `ComplexityClassifier`, `ComplexityLevel`
- Chunking: `DocumentChunker`, `TextChunk`
- Validation: `FieldValidator`, `ValidationError`
- Confidence: `ConfidenceCalculator`, `ConfidenceBreakdown`
- Deduplication: `BorrowerDeduplicator`
- Schemas: `ExtractedBorrower`, `BorrowerExtractionResult`

## Test Coverage

### Deduplication Tests (17 tests)
- No duplicates for different borrowers
- SSN-based matching
- Account number matching
- Fuzzy name + ZIP matching
- High name similarity matching
- Merge behavior verification
- Confidence handling

### Extractor Tests (15 tests)
- Simple document extraction
- Model routing (Flash vs Pro)
- Chunking for large documents
- Source attribution
- Deduplication integration
- Validation error tracking
- Confidence scoring
- Income conversion (float -> Decimal)
- Page estimation
- Consistency integration

**Total: 127 tests passing across all extraction modules**

## Deviations from Plan

### [Rule 3 - Blocking] ConsistencyValidator Integration

**Found during:** Task 3 test execution
**Issue:** Prior session (03-05) added `consistency_validator` as required parameter to BorrowerExtractor
**Fix:** Updated test fixtures to include `real_consistency_validator` fixture and pass to all BorrowerExtractor instantiations
**Commit:** 0cbfed2a

## Commits

| Hash | Message |
|------|---------|
| dbd519e8 | feat(03-04): create Gemini-compatible extraction schemas |
| df1459a2 | feat(03-04): add BorrowerDeduplicator with fuzzy matching |
| 22a6eb41 | feat(03-04): add BorrowerExtractor orchestrator and tests |
| 0cbfed2a | fix(03-04): update extractor tests for consistency_validator |

## Key Artifacts

```
backend/src/extraction/
  schemas.py          - Gemini-compatible Pydantic schemas
  deduplication.py    - Multi-strategy borrower deduplicator
  extractor.py        - Main orchestrator (updated with consistency)
  __init__.py         - Comprehensive module exports

backend/tests/extraction/
  test_deduplication.py  - 17 tests for deduplication
  test_extractor.py      - 15 tests for extractor
```

## Success Criteria Verification

- [x] BorrowerExtractor.extract() takes DocumentContent and returns ExtractionResult
- [x] Complexity assessment routes to appropriate model (Flash/Pro)
- [x] Large documents chunked with overlap
- [x] Chunk results aggregated and deduplicated
- [x] Source attribution added to all borrowers
- [x] Confidence scores calculated based on completeness and validation
- [x] Validation errors tracked per extraction
- [x] EXTRACT-19 through EXTRACT-29 requirements addressed
- [x] 20+ unit tests passing across all extraction modules (127 total)

## Next Phase Readiness

Plan 03-05 (Consistency Validation) work was already started by prior session:
- ConsistencyValidator is implemented
- Already integrated into BorrowerExtractor
- Tests for consistency integration passing

The extraction pipeline is complete and ready for:
- API integration (Phase 4)
- End-to-end testing with real documents
- Performance optimization if needed
