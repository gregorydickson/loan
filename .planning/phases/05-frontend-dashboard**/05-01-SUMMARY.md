---
phase: 05-frontend-dashboard
plan: 01
subsystem: ui
tags: [react-query, shadcn-ui, next.js, tailwind, typescript, api-client]

# Dependency graph
requires:
  - phase: 04-data-storage-rest-api
    provides: REST API endpoints for documents and borrowers
provides:
  - QueryClientProvider for data fetching
  - Sidebar navigation component
  - API client with typed functions
  - Dashboard home page with stats
affects: [05-02, 05-03, 05-04]

# Tech tracking
tech-stack:
  added: [@tanstack/react-query, @tanstack/react-table, react-dropzone, mermaid, zod, date-fns]
  patterns: [QueryClientProvider wrapper, typed API client, client component sidebar with active state]

key-files:
  created: [
    frontend/src/lib/query-client.ts,
    frontend/src/lib/api/client.ts,
    frontend/src/lib/api/types.ts,
    frontend/src/lib/api/documents.ts,
    frontend/src/lib/api/borrowers.ts,
    frontend/src/components/providers.tsx,
    frontend/src/components/layout/sidebar.tsx,
    frontend/src/components/layout/header.tsx,
    frontend/src/components/ui/card.tsx,
    frontend/src/components/ui/table.tsx,
    frontend/src/components/ui/input.tsx,
    frontend/src/components/ui/dialog.tsx,
    frontend/src/components/ui/tabs.tsx,
    frontend/src/components/ui/badge.tsx,
    frontend/src/components/ui/skeleton.tsx,
    frontend/src/components/ui/progress.tsx,
    frontend/src/components/ui/separator.tsx
  ]
  modified: [
    frontend/package.json,
    frontend/src/app/layout.tsx,
    frontend/src/app/page.tsx
  ]

key-decisions:
  - "QueryClient staleTime 60s with retry 1 for queries, 0 for mutations"
  - "API client uses NEXT_PUBLIC_API_URL env var with localhost:8000 default"
  - "Sidebar uses usePathname for active state highlighting"
  - "Dashboard calls API directly without hooks (hooks created in later plans)"

patterns-established:
  - "Client component pattern: 'use client' directive for React Query hooks"
  - "API client pattern: typed apiClient<T> with error handling"
  - "Layout pattern: fixed sidebar with ml-64 main content"

# Metrics
duration: 3min
completed: 2026-01-24
---

# Phase 5 Plan 1: App Shell and API Foundation Summary

**TanStack Query integration with typed API client, shadcn/ui components, and dashboard shell with navigation sidebar**

## Performance

- **Duration:** 3 min
- **Started:** 2026-01-24T14:33:44Z
- **Completed:** 2026-01-24T14:37:29Z
- **Tasks:** 3
- **Files modified:** 20

## Accomplishments
- Installed TanStack Query, React Table, react-dropzone, mermaid, zod, date-fns
- Added 9 shadcn/ui components (card, table, input, dialog, tabs, badge, skeleton, progress, separator)
- Created typed API client with functions for documents and borrowers endpoints
- Built navigation sidebar with Documents, Borrowers, Architecture links
- Created dashboard home page displaying summary stats (total documents, total borrowers, recent uploads)

## Task Commits

Each task was committed atomically:

1. **Task 1: Install dependencies and add shadcn components** - `ea272412` (chore)
2. **Task 2: Create API client and TypeScript types** - `2a9978af` (feat)
3. **Task 3: Create layout components and update app shell** - `cc5dd8b5` (feat)

## Files Created/Modified

**API Layer:**
- `frontend/src/lib/query-client.ts` - QueryClient configuration
- `frontend/src/lib/api/client.ts` - Base API fetch client with error handling
- `frontend/src/lib/api/types.ts` - TypeScript types matching backend Pydantic models
- `frontend/src/lib/api/documents.ts` - Document API functions (upload, getStatus, get, list)
- `frontend/src/lib/api/borrowers.ts` - Borrower API functions (list, search, get, getSources)

**Layout Components:**
- `frontend/src/components/providers.tsx` - QueryClientProvider wrapper (client component)
- `frontend/src/components/layout/sidebar.tsx` - Navigation sidebar with active state
- `frontend/src/components/layout/header.tsx` - Page header component

**App Shell:**
- `frontend/src/app/layout.tsx` - Updated with Providers and Sidebar
- `frontend/src/app/page.tsx` - Dashboard home with summary stats cards

**shadcn/ui Components:**
- 9 new components in `frontend/src/components/ui/`

## Decisions Made

- **QueryClient settings:** staleTime 60s (1 min cache), retry 1 for queries, 0 for mutations
- **API base URL:** Uses NEXT_PUBLIC_API_URL env var, defaults to http://localhost:8000
- **Sidebar active state:** Uses usePathname() to highlight current route
- **Dashboard data fetching:** Calls API functions directly without custom hooks (hooks will be created in plans 02 and 03)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- App shell is ready with navigation and QueryClientProvider
- API client is ready for use in feature pages
- Next plan (05-02) can build Documents page using existing API functions
- shadcn/ui components available for all feature pages

---
*Phase: 05-frontend-dashboard*
*Completed: 2026-01-24*
