---
phase: 03-llm-extraction--validation
plan: 02
subsystem: extraction
tags: [gemini, llm, regex, chunking, preprocessing]

# Dependency graph
requires:
  - phase: 02-document-ingestion-pipeline
    provides: DocumentContent with text and page_count
provides:
  - ComplexityClassifier for model routing (Flash vs Pro)
  - EXTRACTION_SYSTEM_PROMPT and build_extraction_prompt
  - DocumentChunker with paragraph-aware overlap
affects:
  - 03-03 (validation/confidence needs classification)
  - 03-04 (extractor orchestrator uses all three)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Compiled regex patterns for O(n) text scanning"
    - "Dataclass for structured classification results"
    - "Paragraph-aware chunking with rfind"

key-files:
  created:
    - backend/src/extraction/complexity_classifier.py
    - backend/src/extraction/prompts.py
    - backend/src/extraction/chunker.py
    - backend/tests/extraction/test_complexity_classifier.py
    - backend/tests/extraction/test_chunker.py
  modified: []

key-decisions:
  - "Compiled regex patterns at init time for efficiency"
  - "Threshold >3 for poor quality indicators (not >=)"
  - "Threshold >10 pages for complex documents (not >=)"
  - "Last 20% of chunk searched for paragraph breaks"

patterns-established:
  - "ComplexityLevel enum with str base for JSON serialization"
  - "Compiled patterns as class instance attributes"
  - "TextChunk dataclass with position metadata for aggregation"

# Metrics
duration: 5min
completed: 2026-01-24
---

# Phase 3 Plan 2: Document Preprocessing Summary

**ComplexityClassifier for Flash/Pro model routing, prompt templates with brace escaping, DocumentChunker with 200-token overlap at paragraph boundaries**

## Performance

- **Duration:** 5 min
- **Started:** 2026-01-24T03:47:02Z
- **Completed:** 2026-01-24T03:52:28Z
- **Tasks:** 3/3
- **Files created:** 5

## Accomplishments

- ComplexityClassifier routes documents to STANDARD (Flash) or COMPLEX (Pro) based on borrower count, page count, scan quality, and handwritten content
- Prompt templates with safe brace escaping prevent string format injection from document text
- DocumentChunker splits large documents at paragraph boundaries with 200-token overlap to avoid entity splitting

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ComplexityClassifier for model routing** - `3ac68a1a` (feat)
2. **Task 2: Create extraction prompt templates** - `db87b5a0` (feat)
3. **Task 3: Create DocumentChunker with overlap** - `52775021` (feat)

## Files Created

- `backend/src/extraction/complexity_classifier.py` - ComplexityLevel enum, ComplexityAssessment dataclass, ComplexityClassifier with regex patterns
- `backend/src/extraction/prompts.py` - EXTRACTION_SYSTEM_PROMPT constant, build_extraction_prompt function with brace escaping
- `backend/src/extraction/chunker.py` - TextChunk dataclass, DocumentChunker with paragraph-aware splitting
- `backend/tests/extraction/test_complexity_classifier.py` - 17 tests covering all classification scenarios
- `backend/tests/extraction/test_chunker.py` - 15 tests covering chunking edge cases

## Decisions Made

- **Compiled regex at init:** Patterns compiled once in `__init__` rather than per-call for O(n) scanning efficiency
- **Poor quality threshold >3:** Requires more than 3 indicators to flag as poor quality (avoids false positives)
- **Page threshold >10:** Documents with 11+ pages trigger COMPLEX routing
- **Last 20% search zone:** Paragraph breaks only considered if in final 20% of max_chars to maximize chunk content
- **Case-insensitive matching:** All pattern matching uses re.IGNORECASE for document text normalization

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Test `test_paragraph_boundary_preferred` initially failed due to incorrect test setup (paragraph at position 70 not in last 20% of 100-char chunk). Fixed test to place paragraph at position 85.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- ComplexityClassifier ready for use by extraction orchestrator
- Prompt templates ready for GeminiClient integration
- DocumentChunker ready for large document handling
- All exports available from `src.extraction` package

---
*Phase: 03-llm-extraction--validation*
*Plan: 02*
*Completed: 2026-01-24*
