---
phase: 07-documentation-testing
plan: 04
subsystem: testing
tags: [pytest, playwright, coverage, e2e, integration]

# Dependency graph
requires:
  - 01: Foundation models and infrastructure
  - 02: Document ingestion pipeline
  - 03: Extraction pipeline
  - 04: Data storage and API
  - 05: Frontend dashboard
provides:
  - comprehensive-test-suite
  - coverage-configuration
  - e2e-tests
  - frontend-smoke-tests
affects:
  - ci-cd: Tests can run in parallel with pytest-xdist

# Tech tracking
tech-stack:
  added:
    - pytest-xdist: Parallel test execution
    - "@playwright/test": Frontend E2E testing
  patterns:
    - Coverage-driven development with 80% threshold
    - Integration tests with mock dependencies
    - Smoke tests for frontend validation

# File tracking
key-files:
  created:
    - backend/tests/integration/test_e2e_flow.py
    - backend/tests/integration/test_sample_documents.py
    - backend/tests/fixtures/sample_docs/.gitkeep
    - frontend/e2e/smoke.spec.ts
    - frontend/playwright.config.ts
  modified:
    - backend/pyproject.toml
    - backend/tests/integration/test_documents_api.py
    - frontend/package.json

# Decisions
decisions:
  - coverage-threshold: 80% minimum enforced via fail_under
  - parallel-tests: pytest-xdist enabled for faster CI
  - frontend-e2e: Playwright for smoke tests with webServer config
  - sample-docs: Fixture directory with .gitkeep, tests skip gracefully

# Metrics
metrics:
  duration: 13min
  completed: 2026-01-24
---

# Phase 07 Plan 04: Test Coverage Expansion Summary

**One-liner:** Comprehensive test suite with 91% backend coverage, E2E integration tests, and Playwright frontend smoke tests.

## What Was Built

### 1. Coverage Infrastructure
- Added pytest-xdist for parallel test execution
- Configured coverage with fail_under=80 threshold
- Branch coverage enabled with meaningful exclusions
- Coverage HTML report generation

### 2. Integration Tests
- **Document Status Tests:** Added TestDocumentStatus class for GET /api/documents/{id}/status
- **E2E Flow Tests:** Created test_e2e_flow.py with 6 end-to-end scenarios
  - Upload to extraction flow
  - Multiple document upload
  - Error handling for not found
  - Duplicate detection
  - Borrower API flow
  - Health check integration
- **Sample Document Tests:** Created test_sample_documents.py
  - PDF/DOCX/image type support
  - Graceful skip when no sample documents present

### 3. Frontend Smoke Tests
- Playwright configuration with webServer auto-start
- smoke.spec.ts with test categories:
  - Dashboard smoke tests
  - Document upload smoke tests
  - API integration smoke tests
  - Navigation smoke tests

## Coverage Results

| Module | Coverage | Status |
|--------|----------|--------|
| src/api/borrowers.py | 100% | Excellent |
| src/storage/repositories.py | 100% | Excellent |
| src/extraction/ | 84-100% | Good |
| src/ingestion/ | 89-100% | Good |
| **Total** | **91%** | **Exceeds 80% target** |

## Test Statistics

- **Total Tests:** 283 passed, 1 skipped
- **Execution Time:** ~42 seconds
- **Coverage:** 91% (exceeds 80% requirement)

## Deviations from Plan

None - plan executed exactly as written.

## Key Files

### Backend
- `backend/pyproject.toml` - Coverage and pytest-xdist configuration
- `backend/tests/integration/test_e2e_flow.py` - E2E integration tests
- `backend/tests/integration/test_sample_documents.py` - Sample document tests
- `backend/tests/integration/test_documents_api.py` - Extended with status tests

### Frontend
- `frontend/playwright.config.ts` - Playwright E2E configuration
- `frontend/e2e/smoke.spec.ts` - Dashboard and upload smoke tests
- `frontend/package.json` - Added Playwright and test scripts

## Verification Commands

```bash
# Run all backend tests with coverage
cd backend && pytest --cov=src --cov-fail-under=80

# Run tests in parallel
cd backend && pytest -n auto

# Run frontend smoke tests
cd frontend && npm run test:e2e
```

## Next Phase Readiness

Phase 7 Plan 04 complete. Ready for:
- Plan 05: Performance benchmarks and optimization
- CI/CD integration with test coverage gates
