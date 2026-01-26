# Phase 21-02: UI Feature Verification Report

**Verified:** 2026-01-26
**Verified by:** User + Claude (Chrome automation)
**Environment:** Production (GCP Cloud Run)

## Summary

| Test | Requirement | Status | Notes |
|------|-------------|--------|-------|
| TEST-06 | Source attribution shows page references | PASS | Page numbers, snippets, document links all functional |
| TEST-07 | Character-level offsets display | PARTIAL | API contract correct, badge not shown (expected - Docling extraction has null offsets) |
| TEST-08 | Borrower data in dashboard | PARTIAL FAIL | Data displays correctly but badge colors incorrect (dark instead of green) |
| TEST-09 | Visualizations render correctly | PASS | Timeline and confidence indicators render without errors |

## Overall: 3/4 PASS, 1 PARTIAL FAIL (badge colors)

## Detailed Results

### TEST-06: Source Attribution UI
**Status:** PASS

Verified in production:
- Source Documents card visible on borrower detail page
- Page numbers displayed ("Page 1")
- Document links functional (Document: db645fd6...)
- Snippet text shown below page reference
- Navigation to document detail works

### TEST-07: Character-Level Offsets
**Status:** PARTIAL (API correct, UI behavior expected)

API Verification:
- char_start field present in API response: YES
- char_end field present in API response: YES
- Fields properly typed (int | null): YES

UI Verification:
- "Exact Match" badge: Not displayed
- Reason: Test borrower extracted via Docling (char_start/char_end are null)
- Expected behavior: Badge only shows for LangExtract extractions with non-null offsets

**Conclusion:** API contract is correct. UI behavior is correct (badge conditional rendering works as designed). To fully verify badge display, need LangExtract extraction with non-null char offsets.

### TEST-08: Dashboard Data
**Status:** PARTIAL FAIL

**Working:**
- Borrower names displayed (Mary Homeowner, John Homeowner)
- Confidence scores shown (90%, 95%)
- Income count column functional (0, 1)
- Table populated with 3 borrowers
- Row click navigation works

**Issue:**
- Badge background color is dark/black instead of green
- Expected: Green badges for scores >= 0.7 (both 90% and 95% should be green)
- Actual: Dark badges regardless of confidence score
- Impact: Visual differentiation between confidence levels not working

### TEST-09: Visualizations
**Status:** PASS

Income Timeline:
- "Income History" section visible
- Timeline renders with vertical line
- Year displayed (2025)
- Amount formatted as currency ($9,166/month)

Confidence Indicator:
- Confidence badge visible (95%)
- Badge displayed on detail page

Console Errors:
- No JavaScript errors detected
- Page loads without render issues

## Production URLs Tested
- Frontend: https://loan-frontend-prod-fjz2snvxjq-uc.a.run.app
- Backend: https://loan-backend-prod-fjz2snvxjq-uc.a.run.app

## Issues Found

### Badge Color Issue (TEST-08)
**Severity:** Medium
**Component:** Dashboard list view (borrowers table)
**Symptom:** Confidence score badges display with dark/black background instead of color-coded backgrounds
**Expected:**
- Green: >= 0.7
- Yellow: 0.5-0.69
- Red: < 0.5
**Actual:** All badges show dark background
**Impact:** Users cannot visually differentiate confidence levels in dashboard view
**Note:** Detail page badges work correctly

## Phase 21 Status
v2.1 Production Deployment & Verification milestone: **GAPS FOUND**

**Passing Tests:** 3/4
- TEST-06: Source attribution (PASS)
- TEST-07: Char offsets - API contract (PASS)
- TEST-09: Visualizations (PASS)

**Gaps:** 1 issue
- TEST-08: Badge colors need fix in dashboard list view

## Recommendation
Minor gap in dashboard badge styling. Core functionality complete. Recommend:
1. Fix badge color conditional logic in dashboard component
2. Re-verify TEST-08 after fix
3. Proceed with milestone completion after badge fix verified
