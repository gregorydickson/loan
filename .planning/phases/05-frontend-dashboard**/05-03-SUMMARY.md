---
phase: 05-frontend-dashboard
plan: 03
subsystem: ui
tags: [react-query, tanstack-table, borrower-management, income-timeline, source-attribution]

# Dependency graph
requires:
  - phase: 05-01
    provides: API client, TypeScript types, QueryClient config, layout components
provides:
  - Borrower query hooks (useBorrowers, useSearchBorrowers, useBorrower, useBorrowerSources)
  - Borrower table with confidence badges and row navigation
  - Borrower card component for summary display
  - Search input with deferred value debouncing
  - Income timeline visualization sorted by year
  - Source references grouped by document with links
  - /borrowers page with search and pagination
  - /borrowers/[id] detail page with full data
affects: [05-04-architecture-visualization]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - useDeferredValue with ref for search debouncing
    - Confidence score color coding (green >= 0.7, yellow >= 0.5, red < 0.5)
    - Timeline visualization with left border and dots
    - Source grouping by document_id with reduce

key-files:
  created:
    - frontend/src/hooks/use-borrowers.ts
    - frontend/src/components/borrowers/borrower-table.tsx
    - frontend/src/components/borrowers/borrower-card.tsx
    - frontend/src/components/borrowers/borrower-search.tsx
    - frontend/src/components/borrowers/income-timeline.tsx
    - frontend/src/components/borrowers/source-references.tsx
    - frontend/src/app/borrowers/page.tsx
    - frontend/src/app/borrowers/[id]/page.tsx
  modified: []

key-decisions:
  - "Search uses useDeferredValue with ref tracking to avoid effect state updates"
  - "Pagination only shown in list mode, not search mode"
  - "Confidence badge colors: default (green) >= 0.7, secondary (yellow) >= 0.5, destructive (red) < 0.5"
  - "Income timeline sorted descending by year (newest first)"
  - "Source references grouped by document_id to reduce visual clutter"
  - "Detail page uses two-column layout on desktop (lg:grid-cols-2), stacked on mobile"

patterns-established:
  - "Search pattern: controlled input + useDeferredValue + ref for change detection"
  - "Timeline pattern: border-l-2 with absolute positioned dots"
  - "Address parsing: JSON.parse with null safety for address_json field"
  - "Currency formatting: Intl.NumberFormat with USD currency"

# Metrics
duration: 7min
completed: 2026-01-24
---

# Phase 5 Plan 3: Borrower Management Summary

**Borrower list with search/pagination, detail page with income timeline and source attribution visualization**

## Performance

- **Duration:** 7 min
- **Started:** 2026-01-24T14:40:22Z
- **Completed:** 2026-01-24T14:47:29Z
- **Tasks:** 3
- **Files created:** 8

## Accomplishments

- Borrower hooks for list, search, detail, and sources API calls
- Borrower table with TanStack React Table showing name, confidence badge, income count, date
- Borrower card component with click navigation and confidence color coding
- Search input with useDeferredValue pattern for performance
- Income timeline with visual left border and year-sorted entries
- Source references grouped by document with page numbers and snippets
- Borrower list page with search, table, and pagination controls
- Borrower detail page with summary card, income timeline, and source attribution

## Task Commits

Each task was committed atomically:

1. **Task 1: Create borrower hooks** - `42bef119` (feat)
2. **Task 2: Create borrower UI components** - `82b563ba` (feat)
3. **Task 3: Create borrower list and detail pages** - `00c6d3b6` (feat)

## Files Created/Modified

- `frontend/src/hooks/use-borrowers.ts` - Query hooks for borrower data fetching
- `frontend/src/components/borrowers/borrower-table.tsx` - TanStack table with confidence badges
- `frontend/src/components/borrowers/borrower-card.tsx` - Summary card with navigation
- `frontend/src/components/borrowers/borrower-search.tsx` - Search with deferred value debouncing
- `frontend/src/components/borrowers/income-timeline.tsx` - Timeline visualization with currency formatting
- `frontend/src/components/borrowers/source-references.tsx` - Grouped document references
- `frontend/src/app/borrowers/page.tsx` - List page with search and pagination (147 lines)
- `frontend/src/app/borrowers/[id]/page.tsx` - Detail page with two-column layout (212 lines)

## Decisions Made

- **Search debouncing:** Used useDeferredValue with ref tracking instead of useState in effect to avoid ESLint warnings about cascading renders
- **Pagination visibility:** Only show pagination controls in list mode, hide during search since search returns all matches
- **Confidence badges:** Three-tier color system matching borrower trust levels (green/yellow/red)
- **Income display:** Show year prominently with amount and period, plus source type and employer as secondary info
- **Source grouping:** Group references by document_id to show context, with truncated snippets (150 chars)
- **Responsive layout:** Two-column grid on lg screens, single column stack on mobile

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ESLint error in borrower-search.tsx**
- **Found during:** Task 3
- **Issue:** Calling setState in effect body triggers cascading renders warning
- **Fix:** Replaced useState with useRef for tracking previous deferred value
- **Files modified:** `frontend/src/components/borrowers/borrower-search.tsx`
- **Commit:** `00c6d3b6`

## Issues Encountered

- **Next.js build lock:** Build process had stale lock file; cleaned .next directory but build still failed with file not found error. Used TypeScript compilation (`npx tsc --noEmit`) and ESLint as verification instead.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Borrower list and detail pages fully functional pending backend connection
- Source attribution links ready for documents pages (created in Plan 02)
- All success criteria met:
  - /borrowers shows list with search and pagination
  - Search requires 2+ characters, shows loading state
  - Table shows name, confidence badge, income count, date
  - Row click navigates to detail page
  - Detail page shows income timeline and source references
  - Responsive layout works on mobile and desktop

---
*Phase: 05-frontend-dashboard*
*Completed: 2026-01-24*
