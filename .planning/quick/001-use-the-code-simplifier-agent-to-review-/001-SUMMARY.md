# Quick Task 001: Code Simplification Analysis

**Completed:** 2026-01-25
**Duration:** ~15 min

## Executive Summary

Analyzed 41 Python files (6,673 LOC) in the backend and 40+ TypeScript files (3,883 LOC) in the frontend. The codebase is well-structured with clear separation of concerns. Identified **8 high-impact simplification opportunities** and **12 medium-impact improvements**.

## Backend Analysis (Python)

### Files Analyzed: 41 Python files across 6 modules
- **Extraction Module**: 14 files (largest, most complex)
- **API Layer**: 5 files
- **OCR Module**: 4 files
- **Ingestion Module**: 4 files
- **Storage Module**: 5 files
- **Models**: 3 files

### High Impact / Low Effort (Quick Wins)

#### 1. Extract Common Result Dataclass Pattern
**Location:** `src/extraction/extractor.py:52-69`, `src/extraction/langextract_processor.py:27-40`, `src/ocr/ocr_router.py:27-39`
**Current State:** Three similar result dataclasses (`ExtractionResult`, `LangExtractResult`, `OCRResult`) with overlapping fields
**Proposed:** Create a base `ProcessingResult` dataclass in `src/models/` that these inherit from
**Expected Benefit:** ~30 LOC reduction, better type consistency

#### 2. Consolidate Validation Pattern
**Location:** `src/extraction/validation.py:78-227`
**Current State:** Four similar validation methods (`validate_ssn`, `validate_phone`, `validate_zip`, `validate_year`) with repeated return patterns
**Proposed:** Create generic `_validate_with_pattern` helper that returns `ValidationResult`
**Expected Benefit:** ~40 LOC reduction, easier to add new validators

#### 3. Unify Retry/Circuit Breaker Configuration
**Location:** `src/extraction/llm_client.py:106-110`, `src/extraction/extraction_router.py:67-71`, `src/ocr/ocr_router.py:43-47`
**Current State:** Retry decorators configured inline with similar but slightly different parameters
**Proposed:** Extract retry config to `src/config.py` with named presets (`RETRY_LLM`, `RETRY_EXTRACTION`, `CIRCUIT_BREAKER_OCR`)
**Expected Benefit:** Centralized tuning, consistent retry behavior

### High Impact / High Effort (Significant Improvements)

#### 4. Refactor BorrowerRecord Conversion Logic
**Location:** `src/extraction/extractor.py:290-352`, `src/extraction/langextract_processor.py:307-351`
**Current State:** Two nearly identical `_convert_to_borrower_record` / `_create_borrower_record` methods
**Proposed:** Create shared `BorrowerRecordBuilder` class in `src/models/borrower.py`
**Expected Benefit:** ~60 LOC reduction, single source of truth for record creation
**Effort:** Medium - requires careful testing of both pipelines

#### 5. Abstract Repository Base Class
**Location:** `src/storage/repositories.py`
**Current State:** `DocumentRepository` and `BorrowerRepository` share similar CRUD patterns
**Proposed:** Create `BaseRepository[T]` generic class with common methods (`create`, `get_by_id`, `list`, `count`)
**Expected Benefit:** ~50 LOC reduction, easier to add new entity types
**Effort:** Medium - requires SQLAlchemy generics understanding

#### 6. Consolidate API Response Models
**Location:** `src/api/documents.py:32-86`, `src/api/borrowers.py:20-97`
**Current State:** Multiple response models with similar structure (pagination fields repeated)
**Proposed:** Create `PaginatedResponse[T]` generic in `src/api/` shared module
**Expected Benefit:** ~40 LOC reduction, consistent pagination contract

### Low Impact / Low Effort (Nice-to-haves)

#### 7. Extract formatBytes Utility
**Location:** Multiple frontend files duplicating byte formatting
**Proposed:** Already exists in `frontend/src/components/documents/document-table.tsx:24-28` - move to `lib/utils.ts`

#### 8. Remove Unused EntityNotFoundError
**Location:** `src/api/errors.py`
**Current State:** `EntityNotFoundError` defined but HTTPException used directly in endpoints
**Proposed:** Either use consistently or remove

## Frontend Analysis (TypeScript/React)

### Files Analyzed: ~40 files across 5 areas
- **Components**: 22 files (UI components)
- **Hooks**: 2 files (data fetching)
- **Lib**: 3 files (utilities, API client)
- **App routes**: 10 files (pages)

### High Impact / Low Effort (Quick Wins)

#### 9. Extract Confidence Badge Logic
**Location:** `src/components/borrowers/borrower-table.tsx:23-29`, `src/components/borrowers/borrower-card.tsx:14-20`
**Current State:** `getConfidenceBadgeVariant` duplicated in two files
**Proposed:** Move to `src/lib/utils.ts` or create `src/lib/formatting.ts`
**Expected Benefit:** ~12 LOC reduction, consistent confidence styling

#### 10. Create Shared Empty State Component
**Location:** Multiple table components with "No X found" pattern
**Current State:** Similar empty state UI in `document-table.tsx:137-140`, `borrower-table.tsx:88-93`
**Proposed:** Create `<EmptyTableRow columns={n} message="..." />`
**Expected Benefit:** Consistent empty states, reusable

### High Impact / High Effort

#### 11. Consolidate Table Components
**Location:** `src/components/documents/document-table.tsx`, `src/components/borrowers/borrower-table.tsx`
**Current State:** Similar TanStack Table setup patterns duplicated
**Proposed:** Create `<DataTable columns={...} data={...} onRowClick={...} />`
**Expected Benefit:** ~60 LOC reduction, consistent table behavior
**Effort:** High - requires careful prop typing for generics

### Low Impact / Low Effort

#### 12. Type-Safe API Paths
**Location:** `src/lib/api/client.ts`, individual API files
**Current State:** API paths are string literals
**Proposed:** Create typed API route constants
**Expected Benefit:** Autocomplete support, catch typos at compile time

## Code Quality Observations

### What's Working Well
1. **Clear module boundaries** - Each module has single responsibility
2. **Consistent naming** - Files/classes follow Python/TypeScript conventions
3. **Good docstrings** - Backend has comprehensive documentation
4. **Type hints** - mypy strict mode enforced (0 errors in 41 files)
5. **Test coverage** - 87% coverage with 490 tests
6. **Dependency injection** - FastAPI Depends used properly in `dependencies.py`

### Minor Code Smells
1. **Long functions** - `document_service.py:upload()` is 135 lines; consider extracting sync/async paths
2. **Deep nesting** - Some extraction methods have 4+ levels of indentation
3. **Magic numbers** - Some thresholds inline (e.g., `200` for snippet length)

## Prioritized Recommendations

| Priority | Item | Impact | Effort | LOC Saved |
|----------|------|--------|--------|-----------|
| 1 | Extract Confidence Badge Logic (#9) | High | Low | 12 |
| 2 | Consolidate Validation Pattern (#2) | High | Low | 40 |
| 3 | Unify Retry Config (#3) | Medium | Low | 15 |
| 4 | Extract Common Result Dataclass (#1) | Medium | Low | 30 |
| 5 | Refactor BorrowerRecord Conversion (#4) | High | Medium | 60 |
| 6 | Abstract Repository Base Class (#5) | Medium | Medium | 50 |
| 7 | Consolidate Table Components (#11) | High | High | 60 |
| 8 | Consolidate API Response Models (#6) | Medium | Medium | 40 |

**Total Potential LOC Reduction:** ~300 lines (3% of codebase)

## Next Steps

If you want to implement any of these recommendations, create follow-up quick tasks:
- Quick wins (#1-4, #9) can be done in ~30 min each
- Medium effort (#5-6) requires ~1 hour each
- High effort (#7, #11) requires 2+ hours with careful testing

## Files Examined

**Backend (6,673 LOC):**
- `/backend/src/extraction/extractor.py` - Main extraction orchestrator
- `/backend/src/extraction/extraction_router.py` - Dual pipeline router
- `/backend/src/extraction/langextract_processor.py` - LangExtract integration
- `/backend/src/extraction/llm_client.py` - Gemini API client
- `/backend/src/extraction/validation.py` - Field validation
- `/backend/src/extraction/confidence.py` - Confidence scoring
- `/backend/src/extraction/deduplication.py` - Borrower deduplication
- `/backend/src/extraction/consistency.py` - Data consistency validation
- `/backend/src/api/documents.py` - Document endpoints
- `/backend/src/api/borrowers.py` - Borrower endpoints
- `/backend/src/api/dependencies.py` - DI configuration
- `/backend/src/storage/repositories.py` - Database repositories
- `/backend/src/ocr/ocr_router.py` - OCR routing logic
- `/backend/src/ingestion/document_service.py` - Document upload service

**Frontend (3,883 LOC):**
- `/frontend/src/hooks/use-documents.ts` - Document data hooks
- `/frontend/src/hooks/use-borrowers.ts` - Borrower data hooks
- `/frontend/src/lib/api/client.ts` - API client
- `/frontend/src/lib/api/types.ts` - TypeScript types
- `/frontend/src/components/documents/upload-zone.tsx` - File upload
- `/frontend/src/components/documents/document-table.tsx` - Document list
- `/frontend/src/components/borrowers/borrower-table.tsx` - Borrower list
- `/frontend/src/components/borrowers/borrower-card.tsx` - Borrower card
