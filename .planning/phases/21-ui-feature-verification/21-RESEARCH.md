# Phase 21: UI Feature Verification - Research

**Researched:** 2026-01-26
**Domain:** Frontend UI verification, source attribution display, character-level highlighting, dashboard features
**Confidence:** HIGH

## Summary

Phase 21 focuses on **manual browser-based verification** of frontend UI features related to extraction results display. The phase verifies that source attribution UI correctly displays page numbers, character-level offsets enable text highlighting for LangExtract results, borrower data renders correctly in the dashboard, and extraction visualizations (timelines, confidence indicators) work without errors.

The research reveals a **critical gap**: the backend API does not expose `char_start`/`char_end` fields in the SourceReferenceResponse even though the database stores them. This means TEST-07 (character-level offset display/highlighting) cannot pass with the current API implementation. The frontend types also lack these fields. This needs to be addressed before verification can succeed.

The existing frontend uses Next.js 16.1 with React 19, TanStack React Query for data fetching, TanStack React Table for tabular displays, and shadcn/ui components (Radix primitives + Tailwind). Playwright e2e tests already exist for smoke testing. The source attribution UI displays page numbers and snippets but does not currently implement character-level text highlighting.

**Primary recommendation:** Before running TEST-07 verification, the API must be updated to include char_start/char_end in SourceReferenceResponse, and the frontend must implement highlighting using these offsets. TEST-06, TEST-08, and TEST-09 can proceed with current implementation.

## Standard Stack

The established tools/libraries for this verification phase:

### Core
| Tool/Library | Version | Purpose | Why Standard |
|--------------|---------|---------|--------------|
| Chrome Browser | Latest | Primary verification browser | DevTools network inspection, console debugging |
| Chrome DevTools | Built-in | Network/API inspection | Observe REST responses, verify data structure |
| Playwright | 1.50.0 | E2E test automation | Already configured in frontend (smoke.spec.ts) |

### Frontend Implementation Stack
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Next.js | 16.1.4 | React framework | App routing, SSR/CSR |
| React | 19.2.3 | UI components | Component rendering |
| TanStack React Query | 5.90.20 | Data fetching | API calls, caching |
| TanStack React Table | 8.21.3 | Table display | Borrower list |
| date-fns | 4.1.0 | Date formatting | Timestamps |
| lucide-react | 0.563.0 | Icons | UI icons |
| react-dropzone | 14.3.8 | File upload | Document upload zone |
| mermaid | 11.12.2 | Diagrams | Architecture visualizations |

### Text Highlighting (for char_start/char_end)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| react-highlight-words | 0.20.0 | Text highlighting | Search result highlighting |
| Custom CSS spans | N/A | Character offset highlighting | Source attribution display |

**Installation (if needed):**
```bash
cd frontend && npm install react-highlight-words
```

## Architecture Patterns

### Existing UI Component Structure
```
frontend/src/
├── app/                    # Next.js App Router pages
│   ├── borrowers/         # Borrower list and detail pages
│   │   ├── page.tsx       # List with BorrowerTable
│   │   └── [id]/page.tsx  # Detail with IncomeTimeline, SourceReferences
│   └── documents/         # Document list and detail pages
│       ├── page.tsx       # List with upload-zone
│       └── [id]/page.tsx  # Document detail view
├── components/
│   ├── borrowers/         # Borrower-specific components
│   │   ├── borrower-table.tsx    # TanStack Table display
│   │   ├── borrower-card.tsx     # Summary card
│   │   ├── income-timeline.tsx   # Timeline visualization
│   │   └── source-references.tsx # Source attribution display
│   └── documents/
│       ├── upload-zone.tsx       # Drag-drop upload
│       └── status-badge.tsx      # Processing status
└── lib/
    ├── api/
    │   ├── types.ts       # TypeScript types
    │   ├── borrowers.ts   # Borrower API calls
    │   └── documents.ts   # Document API calls
    └── formatting.ts      # Shared formatters
```

### Pattern 1: Source Attribution Display (Current)
**What:** SourceReferences component displays page numbers and snippets
**Current Implementation:**
```tsx
// Source: frontend/src/components/borrowers/source-references.tsx (lines 70-84)
<div className="flex items-center gap-2 text-xs text-muted-foreground">
  <span>Page {source.page_number}</span>
  {source.section && (
    <>
      <span>&bull;</span>
      <span>{source.section}</span>
    </>
  )}
</div>
<p className="text-sm">{truncateSnippet(source.snippet)}</p>
```

**Missing:** Character offset highlighting - char_start/char_end not in TypeScript types or API response

### Pattern 2: Character Offset Highlighting (To Implement)
**What:** Highlight specific text within snippet using char_start/char_end
**When to use:** LangExtract results where precise source grounding is needed
**Example Pattern:**
```tsx
// Hypothetical implementation using offsets
interface HighlightedSnippetProps {
  snippet: string;
  char_start: number | null;
  char_end: number | null;
}

function HighlightedSnippet({ snippet, char_start, char_end }: HighlightedSnippetProps) {
  if (char_start === null || char_end === null) {
    return <p className="text-sm">{snippet}</p>;
  }

  // Calculate relative positions within snippet
  return (
    <p className="text-sm">
      {snippet.slice(0, char_start)}
      <mark className="bg-yellow-200">{snippet.slice(char_start, char_end)}</mark>
      {snippet.slice(char_end)}
    </p>
  );
}
```

### Pattern 3: Timeline Visualization (Implemented)
**What:** Income history displayed as vertical timeline
**Current Implementation:**
```tsx
// Source: frontend/src/components/borrowers/income-timeline.tsx (lines 34-77)
<div className="relative border-l-2 border-muted pl-6 space-y-6">
  {sortedRecords.map((record) => (
    <div key={record.id} className="relative">
      {/* Timeline dot */}
      <div className="absolute -left-[31px] h-4 w-4 rounded-full border-2 border-background bg-primary" />
      {/* Content */}
      <div className="space-y-1">
        <span className="font-bold text-lg">{record.year}</span>
        <span className="font-bold text-lg">{formatCurrency(record.amount)}</span>
      </div>
    </div>
  ))}
</div>
```

### Pattern 4: Confidence Indicator (Implemented)
**What:** Color-coded badge showing extraction confidence
**Current Implementation:**
```tsx
// Source: frontend/src/lib/formatting.ts (lines 16-22)
export function getConfidenceBadgeVariant(score: number): "default" | "secondary" | "destructive" {
  if (score >= 0.7) return "default";     // Green - high confidence
  if (score >= 0.5) return "secondary";   // Yellow - medium confidence
  return "destructive";                   // Red - low confidence
}
```

### Anti-Patterns to Avoid
- **Testing char offsets before API exposes them:** Will fail silently - fields missing from response
- **Assuming highlighting works without implementation:** UI component exists but doesn't use offsets
- **Checking visualizations without data:** Timelines/indicators need actual borrower data in database

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Text highlighting | Custom regex-based highlighter | react-highlight-words or CSS mark spans | Edge cases with overlapping highlights, special characters |
| Date formatting | Custom date strings | date-fns format() | Timezone handling, locale support |
| API state management | useState + fetch | TanStack React Query | Caching, refetching, loading states |
| Table rendering | Custom loops | TanStack React Table | Sorting, pagination, accessibility |
| E2E testing | Selenium scripts | Playwright | Modern API, built-in waiting, network interception |

**Key insight:** The frontend already has a solid component library. Verification should test existing components, not require building new ones (except char_start/char_end highlighting if API is updated).

## Common Pitfalls

### Pitfall 1: API Missing char_start/char_end Fields
**What goes wrong:** TEST-07 fails - character offset display cannot be verified
**Why it happens:** Backend SourceReferenceResponse model (src/api/borrowers.py:43-52) does not include char_start/char_end fields even though database stores them
**How to avoid:**
1. Update SourceReferenceResponse to include char_start/char_end
2. Update frontend TypeScript types to include char_start/char_end
3. Implement highlighting in SourceReferences component
**Warning signs:** API response has page_number and snippet but no char_start/char_end

### Pitfall 2: Testing Dashboard Without Extracted Data
**What goes wrong:** TEST-08 fails - "No borrowers found" even though upload worked
**Why it happens:** Documents uploaded but extraction failed or borrower not persisted
**How to avoid:**
1. Verify at least one document shows status "completed"
2. Check API: `curl $BACKEND_URL/api/borrowers/` returns non-empty list
3. If empty, check extraction logs for errors
**Warning signs:** Documents page shows completed but Borrowers page empty

### Pitfall 3: Visualization Errors with Missing Data
**What goes wrong:** TEST-09 fails - Income timeline shows error or blank
**Why it happens:** income_records array empty or malformed data
**How to avoid:**
1. Verify borrower has income_records: `curl $BACKEND_URL/api/borrowers/{id}`
2. Check data types match (amount as string decimal, year as integer)
3. Test with borrower that has >0 income records
**Warning signs:** Timeline renders but shows "No income records found"

### Pitfall 4: Confidence Badge Color Mismatch
**What goes wrong:** Badge shows wrong color for confidence score
**Why it happens:** Score parsing issue - confidence_score is string (Decimal) not float
**How to avoid:** Frontend parses with `parseFloat(borrower.confidence_score)` (already implemented)
**Warning signs:** All badges same color regardless of score

### Pitfall 5: Source References Not Linked to Documents
**What goes wrong:** "Document: xxxx..." links lead to 404
**Why it happens:** Document was deleted or document_id foreign key mismatch
**How to avoid:**
1. Verify document exists before testing source attribution
2. Check source_references.document_id matches documents.id
**Warning signs:** Clicking document link shows error page

## Code Examples

### Verification: Check API Includes Char Offsets
```bash
# Source: Manual verification pattern
BACKEND_URL="https://loan-backend-prod-fjz2snvxjq-uc.a.run.app"

# Get a borrower with sources
BORROWER_ID=$(curl -s "$BACKEND_URL/api/borrowers/" | jq -r '.borrowers[0].id')

# Check if char_start/char_end in response
curl -s "$BACKEND_URL/api/borrowers/$BORROWER_ID" | jq '.source_references[0] | keys'
# Expected (if fixed): ["char_end", "char_start", "document_id", "id", "page_number", "section", "snippet"]
# Current (gap): ["document_id", "id", "page_number", "section", "snippet"]
```

### Verification: Dashboard Shows Correct Borrower Fields
```bash
# Get borrower list
curl -s "$BACKEND_URL/api/borrowers/" | jq '.borrowers[] | {name, confidence_score, income_count}'
# Should show non-empty borrower data with valid scores
```

### Playwright Test: Source Attribution Page Display
```typescript
// Source: Pattern for extending e2e/smoke.spec.ts
test('source references display page numbers', async ({ page }) => {
  // Navigate to a borrower detail page with known sources
  await page.goto('/borrowers/[known-borrower-id]');

  // Verify source references card exists
  await expect(page.getByText('Source Documents')).toBeVisible();

  // Verify page number is displayed
  await expect(page.getByText(/Page \d+/)).toBeVisible();
});
```

### Playwright Test: Income Timeline Renders
```typescript
test('income timeline visualization renders', async ({ page }) => {
  await page.goto('/borrowers/[known-borrower-id]');

  // Verify timeline exists
  await expect(page.getByText('Income History')).toBeVisible();

  // Verify at least one income record displays
  await expect(page.locator('.rounded-full.bg-primary')).toBeVisible(); // Timeline dot
});
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Page-level source attribution | Character-level offsets | v2.0 (LangExtract) | Precise highlighting possible |
| Static confidence values | Dynamic confidence badges | v1.0 | Visual feedback on extraction quality |
| No income history | Income timeline visualization | v1.0 | Better borrower data display |
| Manual API testing only | Playwright E2E tests | v2.0 | Automated smoke testing |

**Current gap:**
- char_start/char_end stored in DB but not exposed in API response
- Frontend has types but they lack offset fields
- SourceReferences component doesn't implement highlighting

## Critical Gap: Character Offset API Exposure

### Problem
TEST-07 requires "Character-level offsets display correctly for LangExtract results (highlighting works)".

**Current state:**
1. Database has char_start/char_end columns (storage/models.py:178-179)
2. Pydantic model has char_start/char_end (models/document.py:34-43)
3. LangExtract populates these fields (langextract_processor.py:260-261)
4. **BUT** API response model omits them (api/borrowers.py:43-52)
5. **AND** Frontend types don't include them (lib/api/types.ts:74-80)

### Required Changes

**Backend (api/borrowers.py):**
```python
class SourceReferenceResponse(BaseModel):
    # ... existing fields ...
    char_start: int | None  # ADD THIS
    char_end: int | None    # ADD THIS
```

**Frontend (lib/api/types.ts):**
```typescript
export interface SourceReference {
  // ... existing fields ...
  char_start: number | null;  // ADD THIS
  char_end: number | null;    // ADD THIS
}
```

**Frontend (source-references.tsx):**
```tsx
// Add highlighting when offsets present
{source.char_start !== null && source.char_end !== null ? (
  <HighlightedSnippet
    snippet={source.snippet}
    start={source.char_start}
    end={source.char_end}
  />
) : (
  <p className="text-sm">{truncateSnippet(source.snippet)}</p>
)}
```

## Open Questions

Things that require resolution:

1. **Should char_start/char_end fix be part of Phase 21 or a prerequisite?**
   - What we know: API gap exists, frontend can't display what API doesn't provide
   - What's unclear: Whether Phase 21 verifies "current behavior" or "expected behavior"
   - Recommendation: Fix API before verification, or mark TEST-07 as BLOCKED

2. **What constitutes "highlighting works" for TEST-07?**
   - What we know: char_start/char_end enable precise text marking
   - What's unclear: Is visual highlight required, or just offset data presence?
   - Recommendation: Define as "offsets displayed in UI AND extractable for highlighting"

3. **Which borrower/document IDs to use for verification?**
   - What we know: Need documents processed with method=langextract for char offsets
   - What's unclear: Whether production has such documents from Phase 20 testing
   - Recommendation: Note document IDs from Phase 20 TEST-04 verification

## Verification Checklist

### TEST-06: Source Attribution UI Shows Page References
- [ ] Navigate to borrower detail page: `/borrowers/{id}`
- [ ] Verify "Source Documents" card visible
- [ ] Verify "Page N" text visible for each source reference
- [ ] Click document link, verify navigation to document detail works
- [ ] Verify snippet text displays (truncated to 150 chars)

### TEST-07: Character-Level Offsets Display (BLOCKED without API fix)
- [ ] **PREREQUISITE**: Verify API returns char_start/char_end:
  ```bash
  curl -s "$BACKEND_URL/api/borrowers/{id}" | jq '.source_references[0] | has("char_start")'
  ```
- [ ] If API returns offsets: Verify UI highlights relevant text
- [ ] If API missing offsets: Mark as BLOCKED, document gap

### TEST-08: Borrower Data in Dashboard
- [ ] Navigate to `/borrowers`
- [ ] Verify table shows borrower names
- [ ] Verify confidence scores display as colored badges
- [ ] Verify income_count column shows numbers
- [ ] Click row, verify navigation to detail page works
- [ ] On detail page, verify name, address, confidence display correctly

### TEST-09: Extraction Visualizations Render
- [ ] Navigate to borrower detail with income records
- [ ] Verify "Income History" timeline renders
- [ ] Verify timeline dots (circles) visible
- [ ] Verify year and amount display formatted correctly
- [ ] Verify confidence badge shows appropriate color (green/yellow/red)
- [ ] Verify no JavaScript errors in console

## Sources

### Primary (HIGH confidence)
- frontend/src/components/borrowers/source-references.tsx - Source attribution component
- frontend/src/components/borrowers/income-timeline.tsx - Timeline visualization
- frontend/src/lib/api/types.ts - Frontend TypeScript types
- backend/src/api/borrowers.py - API response models
- backend/src/storage/models.py - Database models with char_start/char_end
- frontend/package.json - Frontend dependencies

### Secondary (MEDIUM confidence)
- [Chrome DevTools Manual Testing](https://www.ministryoftesting.com/articles/10-powerful-tests-with-chrome-devtools) - Testing patterns
- [React Highlight Words npm](https://www.npmjs.com/package/react-highlight-words) - Highlighting library
- [Text Selection with Character Offsets](https://medium.com/unprogrammer/a-simple-text-highlighting-component-with-react-e9f7a3c1791a) - Highlighting patterns

### Tertiary (LOW confidence)
- WebSearch results for React text highlighting - Pattern guidance only

## Metadata

**Confidence breakdown:**
- Source attribution UI (TEST-06): HIGH - Component exists, page_number displayed
- Character offsets (TEST-07): HIGH (gap identified) - API doesn't expose fields
- Dashboard features (TEST-08): HIGH - Components implemented, tested in smoke tests
- Visualizations (TEST-09): HIGH - Timeline and badges implemented and functional

**Research date:** 2026-01-26
**Valid until:** 2026-02-26 (30 days - stable frontend patterns)

## Requirements Mapping

| Requirement | Status | Research Finding | Confidence |
|-------------|--------|------------------|------------|
| TEST-06: Source attribution shows page references | VERIFIABLE | SourceReferences component displays page_number | HIGH |
| TEST-07: Character-level offsets display | BLOCKED | API SourceReferenceResponse missing char_start/char_end | HIGH |
| TEST-08: Borrower data in dashboard | VERIFIABLE | BorrowerTable, BorrowerCard, detail page implemented | HIGH |
| TEST-09: Visualizations render | VERIFIABLE | IncomeTimeline, confidence badges implemented | HIGH |

## Recommended Plan Structure

Given the gap identified for TEST-07, recommend structuring Phase 21 as:

**Plan 21-01: API and Type Updates (if fixing gap)**
- Update SourceReferenceResponse with char_start/char_end
- Update frontend TypeScript types
- Update SourceReferences component with highlighting
- Redeploy backend and frontend

**Plan 21-02: UI Feature Verification (all tests)**
- Manual Chrome-based verification of all TEST-06 through TEST-09
- Document evidence with screenshots
- Record pass/fail status for each requirement
