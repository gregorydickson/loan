---
phase: 21-ui-feature-verification
verified: 2026-01-26T20:30:00Z
status: gaps_found
score: 7/8 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 3/4 tests passing
  gaps_closed: []
  gaps_remaining:
    - "Dashboard badge colors display dark instead of semantic colors (green/yellow/red)"
  regressions: []
gaps:
  - truth: "Extraction visualizations render without errors (charts, timelines, confidence indicators)"
    status: partial
    reason: "Dashboard confidence badges render but use dark/monochrome theme color instead of semantic success/warning/error colors"
    artifacts:
      - path: "frontend/src/app/globals.css"
        issue: "Theme defines --primary as dark gray (oklch 0.205) instead of semantic green color"
      - path: "frontend/src/components/ui/badge.tsx"
        issue: "Badge component correctly uses variant='default' for high confidence, but 'default' maps to 'bg-primary' which is dark gray"
    missing:
      - "Update CSS theme to define semantic colors for success/warning/error"
      - "Either: (1) add success/warning/error badge variants, or (2) redefine primary/secondary/destructive to be semantic colors"
      - "Ensure dashboard badges visually differentiate confidence levels (green >= 0.7, yellow 0.5-0.69, red < 0.5)"
human_verification:
  - test: "Navigate to production frontend dashboard at https://loan-frontend-prod-fjz2snvxjq-uc.a.run.app/borrowers and verify badge colors"
    expected: "Confidence badges should display green for scores >= 70%, yellow for 50-69%, red for < 50%"
    why_human: "Visual color perception requires human verification - automated tests can't verify actual rendered colors match semantic intent"
---

# Phase 21: UI Feature Verification Report

**Phase Goal:** All frontend features display extraction results correctly
**Verified:** 2026-01-26T20:30:00Z
**Status:** gaps_found
**Re-verification:** Yes — after Plan 21-02 execution with 1 gap remaining

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Source attribution UI shows page numbers for extracted fields | ✓ VERIFIED | SourceReferences component renders page numbers (line 72), document links (lines 59-65), and snippets (lines 85-87) |
| 2 | Character-level offsets display correctly for LangExtract results | ✓ VERIFIED | API returns char_start/char_end fields (borrowers.py:53-54), frontend types match (types.ts:80-81), "Exact Match" badge conditionally rendered (source-references.tsx:79-83) |
| 3 | Borrower data appears in dashboard list with correct field values | ✓ VERIFIED | BorrowerTable renders names, confidence scores, income counts, dates (borrower-table.tsx:24-47), data fetched from /api/borrowers endpoint (borrowers.py:102-133) |
| 4 | Extraction visualizations render without errors | ⚠️ PARTIAL | IncomeTimeline component exists and renders (income-timeline.tsx:34-78), confidence badges render (borrower-table.tsx:34-36), BUT badge colors use dark theme instead of semantic colors |

**Score:** 3.5/4 truths verified (TEST-08 partial due to badge color styling gap)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/src/api/borrowers.py` | SourceReferenceResponse with char_start/char_end | ✓ VERIFIED | Lines 43-54: char_start: int \| None, char_end: int \| None |
| `frontend/src/lib/api/types.ts` | SourceReference interface with char offsets | ✓ VERIFIED | Lines 74-82: char_start: number \| null, char_end: number \| null |
| `frontend/src/components/borrowers/source-references.tsx` | "Exact Match" badge for LangExtract | ✓ VERIFIED | Lines 79-83: conditional badge when char_start and char_end non-null |
| `frontend/src/components/borrowers/income-timeline.tsx` | Timeline visualization component | ✓ VERIFIED | Lines 34-78: renders timeline with dots, years, amounts, periods |
| `frontend/src/components/borrowers/borrower-table.tsx` | Dashboard table with confidence badges | ✓ VERIFIED | Lines 24-47: columns for name, confidence (with badge), income count, created date |
| `frontend/src/lib/formatting.ts` | Badge variant logic for confidence scores | ✓ VERIFIED | Lines 16-22: getConfidenceBadgeVariant returns default/secondary/destructive based on score thresholds |
| `frontend/src/components/ui/badge.tsx` | Badge component with variant styling | ⚠️ PARTIAL | Lines 7-27: Badge variants defined correctly, BUT default/secondary use theme colors |
| `frontend/src/app/globals.css` | Theme with semantic colors | ✗ GAP | Lines 57-58: --primary defined as dark gray (oklch 0.205 0 0) instead of semantic green |

**Artifact Score:** 7/8 verified (1 theme gap)

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| frontend/borrowers/[id]/page.tsx | SourceReferences component | Import and render | ✓ WIRED | Line 17 import, lines 209-212 render with borrower.source_references |
| frontend/borrowers/[id]/page.tsx | IncomeTimeline component | Import and render | ✓ WIRED | Line 16 import, line 206 render with borrower.income_records |
| frontend/borrowers/page.tsx | BorrowerTable component | Import and render | ✓ WIRED | Line 8 import, line 113 render with borrowers data |
| SourceReferences component | SourceReference type | Type import and usage | ✓ WIRED | Line 11 import, lines 14 and 74 usage |
| BorrowerTable component | getConfidenceBadgeVariant | Function import and call | ✓ WIRED | Line 20 import, line 34 call with score |
| backend borrowers.py | Database (ORM models) | SQLAlchemy query | ✓ WIRED | Lines 117, 209: repository.list_borrowers() and get_by_id() return ORM models with relationships |
| SourceReferenceResponse | Database SourceReference model | Pydantic from_attributes | ✓ WIRED | Line 46: model_config = ConfigDict(from_attributes=True) enables ORM → Pydantic |

**All key links verified as wired.**

### Requirements Coverage

| Requirement | Status | Blocking Issue |
|-------------|--------|----------------|
| TEST-06: Source attribution UI shows page references | ✓ SATISFIED | None |
| TEST-07: Character-level offsets display for LangExtract | ✓ SATISFIED | None (API contract complete, badge conditional rendering works) |
| TEST-08: Borrower data in dashboard | ⚠️ PARTIAL | Badge colors dark instead of semantic (visual differentiation issue) |
| TEST-09: Visualizations render correctly | ✓ SATISFIED | Timeline and confidence indicators render without errors |

**Requirements Score:** 3/4 satisfied (TEST-08 partial due to styling)

### Anti-Patterns Found

None detected. All implementations are substantive, properly typed, and follow React/TypeScript best practices.

### Human Verification Required

#### 1. Verify Dashboard Badge Colors in Production

**Test:** 
1. Open Chrome and navigate to https://loan-frontend-prod-fjz2snvxjq-uc.a.run.app/borrowers
2. Observe the "Confidence" column badge colors in the borrower table
3. Check if colors match expectations:
   - Score >= 70%: Should be green (success/high confidence)
   - Score 50-69%: Should be yellow/orange (warning/medium confidence)
   - Score < 50%: Should be red (error/low confidence)

**Expected:** Clear visual differentiation with semantic colors (green = good, yellow = caution, red = problem)

**Why human:** Automated verification can confirm CSS classes are applied and theme variables are defined, but cannot verify the actual rendered colors match semantic intent and provide appropriate visual feedback to users.

#### 2. Verify "Exact Match" Badge for LangExtract Results

**Test:**
1. Upload a document using LangExtract extraction method
2. Navigate to the borrower detail page
3. Check "Source Documents" section for "Exact Match" badge

**Expected:** Green "Exact Match" badge appears next to page numbers for LangExtract extractions with char offsets

**Why human:** Requires end-to-end flow with LangExtract extraction. Current production data may only have Docling extractions (char_start/char_end null), which correctly show no badge.

### Gaps Summary

#### Gap 1: Dashboard Badge Colors Use Dark Theme Instead of Semantic Colors

**Severity:** Medium (visual UX issue, not functional blocker)

**Root Cause:** The theme in `frontend/src/app/globals.css` defines CSS custom properties using a monochrome color palette:
- `--primary: oklch(0.205 0 0)` - very dark gray (lightness 0.205)
- `--secondary: oklch(0.97 0 0)` - very light gray (lightness 0.97)
- `--destructive: oklch(0.577 0.245 27.325)` - red-orange (has chroma/hue)

The Badge component correctly uses these theme colors, and `getConfidenceBadgeVariant()` correctly maps scores to variants:
- Score >= 0.7 → "default" variant → bg-primary → **dark gray** (should be green)
- Score >= 0.5 → "secondary" variant → bg-secondary → **light gray** (should be yellow)
- Score < 0.5 → "destructive" variant → bg-destructive → **red-orange** (correct!)

**Impact:** Users cannot visually differentiate confidence levels at a glance. High-confidence extractions (90%, 95%) show dark badges instead of reassuring green, reducing trust and usability.

**What's Working:**
- Logic: Badge variant selection based on score thresholds is correct
- Structure: Badge component variant system is properly implemented
- Data: Confidence scores flow from API to UI correctly
- Rendering: Badges display without errors

**What's Missing:**
1. Semantic color definitions in theme (green for success, yellow for warning)
2. Either:
   - Option A: Add "success"/"warning" badge variants and update `getConfidenceBadgeVariant()` to use them
   - Option B: Redefine "primary" and "secondary" theme colors to be semantic (green and yellow)

**Recommendation:** Option B is simpler - update the theme colors to be semantic. The "primary" color in most UI systems represents success/affirmative actions, so making it green is semantically appropriate.

**Note:** The detail page badges (borrower-card.tsx, borrowers/[id]/page.tsx) have the same issue but weren't specifically tested in Plan 21-02. They use the same Badge component and variant logic, so fixing the theme will resolve both.

---

## Re-Verification Notes

This is a re-verification after Plan 21-02 completed manual testing. Previous verification (21-02-VERIFICATION.md) found:
- TEST-06: PASS
- TEST-07: PARTIAL (API correct, awaits LangExtract data with char offsets)
- TEST-08: PARTIAL FAIL (badge colors dark)
- TEST-09: PASS

**Current structural verification confirms:**
- All claimed implementations exist in codebase
- API contract is correct (char_start/char_end fields present)
- Frontend types match API
- Components are properly wired and render without errors
- Badge color gap persists (confirmed as theme-level CSS issue)

**Gaps closed:** 0 (badge color issue not yet addressed)

**Gaps remaining:** 1 (dashboard badge colors)

**Regressions:** None

---

_Verified: 2026-01-26T20:30:00Z_
_Verifier: Claude (gsd-verifier)_
_Method: Structural code verification + previous manual test results_
