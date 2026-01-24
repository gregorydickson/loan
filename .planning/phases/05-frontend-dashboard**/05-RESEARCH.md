# Phase 5: Frontend Dashboard - Research

**Researched:** 2026-01-24
**Domain:** Next.js 16 + Tailwind v4 + shadcn/ui + TanStack Query for document management UI
**Confidence:** HIGH

## Summary

This phase builds a Next.js 16 frontend dashboard with drag-and-drop document upload, borrower management, and architecture visualization. The existing frontend has a solid foundation with Next.js 16, React 19, Tailwind v4, and shadcn/ui already configured in new-york style.

The standard approach combines:
1. **react-dropzone** for drag-and-drop file upload with shadcn/ui styling
2. **TanStack Query v5** for server state management with mutations and polling
3. **shadcn/ui Data Table** with @tanstack/react-table for borrower lists
4. **Mermaid.js** for architecture diagrams (client-side rendering)

The existing frontend at `/frontend` already has:
- Next.js 16.1.4 with React 19.2.3 configured
- Tailwind v4 with tw-animate-css installed
- shadcn/ui new-york style with CSS variables (components.json configured)
- Button component already installed
- App Router structure at `/src/app`

**Primary recommendation:** Use react-dropzone + shadcn/ui styling for upload, TanStack Query v5 for API communication with polling, and @tanstack/react-table for data tables. Type-safe API client with manual TypeScript types matching backend Pydantic models.

## Standard Stack

The established libraries/tools for this domain:

### Core (To Install)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @tanstack/react-query | ^5.x | Server state management | Industry standard, mutations, polling, caching |
| @tanstack/react-table | ^8.x | Headless table logic | Powers shadcn/ui data table, sorting/filtering |
| react-dropzone | ^14.x | Drag-and-drop file upload | Most popular, well-maintained, hooks-based |
| mermaid | ^10.x or ^11.x | Architecture diagrams | Standard for code-based diagrams |

### Supporting (To Install)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| zod | ^3.x | Schema validation | Form validation, API response validation |
| date-fns | ^3.x | Date formatting | Displaying timestamps |

### Already Installed
| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| next | 16.1.4 | Framework | Configured |
| react | 19.2.3 | UI library | Configured |
| tailwindcss | ^4 | Styling | Configured with tw-animate-css |
| lucide-react | ^0.563.0 | Icons | Configured |
| clsx, tailwind-merge | latest | Class utilities | Configured |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| react-dropzone | UploadThing | UploadThing is a service with backend; we have our own FastAPI backend |
| react-dropzone | native HTML5 drag-drop | More code, less features, no validation |
| Manual fetch | SWR | TanStack Query has better mutations support |
| Mermaid | D3.js | D3 more powerful but much more complex |
| Manual types | openapi-ts | Adds build step; manual types adequate for small API |

**Installation:**
```bash
cd frontend
npm install @tanstack/react-query @tanstack/react-table react-dropzone mermaid zod date-fns
```

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/
├── app/
│   ├── layout.tsx              # Root layout with QueryClientProvider
│   ├── page.tsx                # Dashboard home (/)
│   ├── documents/
│   │   ├── page.tsx            # Document list/upload (/documents)
│   │   └── [id]/
│   │       └── page.tsx        # Document detail (/documents/[id])
│   ├── borrowers/
│   │   ├── page.tsx            # Borrower list (/borrowers)
│   │   └── [id]/
│   │       └── page.tsx        # Borrower detail (/borrowers/[id])
│   └── architecture/
│       ├── page.tsx            # Architecture overview
│       ├── decisions/
│       │   └── page.tsx        # Design decisions (ADRs)
│       ├── pipeline/
│       │   └── page.tsx        # Data pipeline diagram
│       └── scaling/
│           └── page.tsx        # Scaling strategy
├── components/
│   ├── ui/                     # shadcn/ui components
│   │   ├── button.tsx          # (exists)
│   │   ├── card.tsx
│   │   ├── table.tsx
│   │   ├── input.tsx
│   │   ├── dialog.tsx
│   │   ├── tabs.tsx
│   │   ├── badge.tsx
│   │   ├── skeleton.tsx
│   │   └── progress.tsx
│   ├── layout/
│   │   ├── sidebar.tsx         # Navigation sidebar
│   │   └── header.tsx          # Page header
│   ├── documents/
│   │   ├── upload-zone.tsx     # Drag-and-drop upload
│   │   ├── document-table.tsx  # Document list table
│   │   └── status-badge.tsx    # Processing status badge
│   ├── borrowers/
│   │   ├── borrower-card.tsx   # Borrower summary card
│   │   ├── borrower-table.tsx  # Borrower list with search
│   │   ├── income-timeline.tsx # Income history visualization
│   │   └── source-references.tsx # Source document links
│   └── architecture/
│       ├── system-diagram.tsx  # Mermaid system architecture
│       ├── pipeline-flow.tsx   # Mermaid pipeline diagram
│       ├── decision-card.tsx   # ADR display card
│       └── scaling-chart.tsx   # Performance projections
├── lib/
│   ├── api/
│   │   ├── client.ts           # Base fetch client
│   │   ├── documents.ts        # Document API functions
│   │   ├── borrowers.ts        # Borrower API functions
│   │   └── types.ts            # TypeScript types for API
│   ├── utils.ts                # (exists) - cn() function
│   └── query-client.ts         # TanStack Query configuration
└── hooks/
    ├── use-documents.ts        # Document query/mutation hooks
    └── use-borrowers.ts        # Borrower query hooks
```

### Pattern 1: TanStack Query Provider Setup
**What:** Configure QueryClient with appropriate defaults for mutations and polling
**When to use:** App-level provider in root layout
**Example:**
```typescript
// Source: TanStack Query v5 Documentation
// lib/query-client.ts
import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60, // 1 minute
      retry: 1,
    },
    mutations: {
      retry: 0,
    },
  },
});

// app/layout.tsx (Client Component wrapper needed)
"use client";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "@/lib/query-client";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}
```

### Pattern 2: File Upload with useMutation
**What:** Upload file via mutation with progress tracking
**When to use:** Document upload component
**Example:**
```typescript
// Source: TanStack Query v5 Mutations + react-dropzone
// hooks/use-documents.ts
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { uploadDocument } from "@/lib/api/documents";

export function useUploadDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return uploadDocument(formData);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

// components/documents/upload-zone.tsx
"use client";
import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { useUploadDocument } from "@/hooks/use-documents";

export function UploadZone() {
  const { mutate, isPending, isSuccess, error } = useUploadDocument();

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      mutate(acceptedFiles[0]);
    }
  }, [mutate]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "image/png": [".png"],
      "image/jpeg": [".jpg", ".jpeg"],
    },
    maxFiles: 1,
    disabled: isPending,
  });

  return (
    <div
      {...getRootProps()}
      className={cn(
        "border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors",
        isDragActive && "border-primary bg-primary/5",
        isPending && "opacity-50 cursor-not-allowed"
      )}
    >
      <input {...getInputProps()} />
      {isPending ? (
        <p>Uploading...</p>
      ) : isDragActive ? (
        <p>Drop the file here...</p>
      ) : (
        <p>Drag and drop a file here, or click to select</p>
      )}
    </div>
  );
}
```

### Pattern 3: Polling for Document Status
**What:** Poll document status until processing completes
**When to use:** After upload, while status is PENDING or PROCESSING
**Example:**
```typescript
// Source: TanStack Query v5 refetchInterval
// hooks/use-documents.ts
import { useQuery } from "@tanstack/react-query";

export function useDocumentStatus(documentId: string | null) {
  return useQuery({
    queryKey: ["document-status", documentId],
    queryFn: () => getDocumentStatus(documentId!),
    enabled: !!documentId,
    refetchInterval: (query) => {
      const data = query.state.data;
      // Stop polling when processing completes
      if (data?.status === "completed" || data?.status === "failed") {
        return false;
      }
      return 2000; // Poll every 2 seconds while processing
    },
  });
}
```

### Pattern 4: Data Table with Server-Side Data
**What:** shadcn/ui table with TanStack Table for client-side sorting/filtering
**When to use:** Borrower list, document list
**Example:**
```typescript
// Source: shadcn/ui Data Table Documentation
// columns.tsx
"use client";
import { ColumnDef } from "@tanstack/react-table";
import { Badge } from "@/components/ui/badge";
import type { BorrowerSummary } from "@/lib/api/types";

export const borrowerColumns: ColumnDef<BorrowerSummary>[] = [
  {
    accessorKey: "name",
    header: "Name",
  },
  {
    accessorKey: "confidence_score",
    header: "Confidence",
    cell: ({ row }) => {
      const score = parseFloat(row.getValue("confidence_score"));
      return (
        <Badge variant={score >= 0.7 ? "default" : "destructive"}>
          {(score * 100).toFixed(0)}%
        </Badge>
      );
    },
  },
  {
    accessorKey: "income_count",
    header: "Income Records",
  },
  {
    accessorKey: "created_at",
    header: "Created",
    cell: ({ row }) => formatDate(row.getValue("created_at")),
  },
];
```

### Pattern 5: Mermaid Diagram in Client Component
**What:** Render Mermaid diagrams client-side
**When to use:** Architecture visualization pages
**Example:**
```typescript
// Source: Mermaid.js + Next.js App Router
// components/architecture/system-diagram.tsx
"use client";
import { useEffect, useRef } from "react";
import mermaid from "mermaid";

interface MermaidDiagramProps {
  chart: string;
}

export function MermaidDiagram({ chart }: MermaidDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    mermaid.initialize({ startOnLoad: false, theme: "neutral" });

    if (containerRef.current) {
      mermaid.run({ nodes: [containerRef.current] });
    }
  }, [chart]);

  return (
    <div ref={containerRef} className="mermaid">
      {chart}
    </div>
  );
}

// Usage:
const architectureChart = `
graph TB
    subgraph Frontend
        UI[Next.js Dashboard]
    end
    subgraph Backend
        API[FastAPI]
        DB[(PostgreSQL)]
        GCS[Cloud Storage]
    end
    subgraph Processing
        Docling[Docling Parser]
        Gemini[Gemini LLM]
    end
    UI --> API
    API --> DB
    API --> GCS
    API --> Docling
    API --> Gemini
`;
```

### Anti-Patterns to Avoid
- **Polling without stop condition:** Always check status and disable `refetchInterval` when complete
- **useQuery for mutations:** File upload is a mutation, not a query - use `useMutation`
- **Server Component for interactive UI:** Upload zone, data tables must be Client Components
- **Lazy loading Mermaid:** Initialize mermaid in useEffect, not at module level (SSR issue)
- **FormData in Server Action for external API:** Use fetch directly to FastAPI backend, not Server Actions

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Drag-and-drop file zone | Custom drag events | react-dropzone | File validation, accessibility, edge cases |
| Server state management | useState + useEffect | TanStack Query | Caching, deduplication, refetching |
| Table sorting/filtering | Manual array operations | @tanstack/react-table | Pagination, column visibility, performance |
| Status polling | setInterval | TanStack Query refetchInterval | Automatic cleanup, conditional polling |
| Diagram rendering | SVG manipulation | Mermaid.js | Complex layout, syntax, responsive |
| Progress indicators | Custom CSS animation | shadcn/ui Progress | Accessibility, consistency |

**Key insight:** The React ecosystem has mature solutions for data fetching, file upload, and tables. Hand-rolling these leads to edge cases, accessibility issues, and maintenance burden.

## Common Pitfalls

### Pitfall 1: Mermaid SSR Errors
**What goes wrong:** `ReferenceError: document is not defined` during build
**Why it happens:** Mermaid uses browser APIs, Next.js pre-renders on server
**How to avoid:** Use `"use client"` directive, initialize mermaid in `useEffect`
**Warning signs:** Build errors, hydration mismatches

### Pitfall 2: TanStack Query Provider Missing
**What goes wrong:** `No QueryClient set, use QueryClientProvider to set one`
**Why it happens:** QueryClientProvider must wrap the app, but App Router layouts are Server Components
**How to avoid:** Create a Client Component `Providers` wrapper that wraps children
**Warning signs:** Runtime error on first query/mutation

### Pitfall 3: File Upload Content-Type Header
**What goes wrong:** Backend receives empty file or 422 error
**Why it happens:** Setting `Content-Type: application/json` instead of letting browser set multipart/form-data
**How to avoid:** Do NOT set Content-Type header when using FormData - browser sets it automatically with boundary
**Warning signs:** 422 Validation Error from FastAPI

### Pitfall 4: Status Badge Not Updating
**What goes wrong:** Badge shows stale status after upload completes
**Why it happens:** Query cache not invalidated after mutation
**How to avoid:** Call `queryClient.invalidateQueries({ queryKey: ["documents"] })` in mutation `onSuccess`
**Warning signs:** Manual page refresh shows correct status

### Pitfall 5: Tailwind v4 Class Not Working
**What goes wrong:** Some Tailwind classes don't apply
**Why it happens:** Tailwind v4 has different syntax; some classes renamed
**How to avoid:** Use `size-*` instead of `w-* h-*`, check Tailwind v4 docs for renamed utilities
**Warning signs:** Styles missing, warnings in dev console

### Pitfall 6: Data Table Type Errors
**What goes wrong:** TypeScript errors with `ColumnDef` and row accessors
**Why it happens:** Column accessorKey must match exact property names in data type
**How to avoid:** Define explicit type parameter: `ColumnDef<BorrowerSummary>[]`
**Warning signs:** Type errors on `row.getValue()` or `accessorKey`

## Code Examples

Verified patterns from official sources:

### API Client with Type Safety
```typescript
// Source: Standard fetch pattern + FastAPI OpenAPI
// lib/api/types.ts
export interface DocumentUploadResponse {
  id: string;
  filename: string;
  file_hash: string;
  file_size_bytes: number;
  status: "pending" | "processing" | "completed" | "failed";
  page_count: number | null;
  error_message: string | null;
  message: string;
}

export interface DocumentStatusResponse {
  id: string;
  status: "pending" | "processing" | "completed" | "failed";
  page_count: number | null;
  error_message: string | null;
}

export interface BorrowerSummary {
  id: string;
  name: string;
  confidence_score: string; // Decimal as string from API
  created_at: string;
  income_count: number;
}

export interface BorrowerListResponse {
  borrowers: BorrowerSummary[];
  total: number;
  limit: number;
  offset: number;
}

// lib/api/client.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function apiClient<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  return response.json();
}

// lib/api/documents.ts
export async function uploadDocument(
  formData: FormData
): Promise<DocumentUploadResponse> {
  // Note: Do NOT set Content-Type header - let browser handle it
  const response = await fetch(`${API_BASE}/api/documents/`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Upload failed");
  }

  return response.json();
}

export async function getDocumentStatus(
  id: string
): Promise<DocumentStatusResponse> {
  return apiClient(`/api/documents/${id}/status`);
}
```

### Status Badge Component
```typescript
// Source: shadcn/ui Badge + requirements
// components/documents/status-badge.tsx
import { Badge } from "@/components/ui/badge";

type DocumentStatus = "pending" | "processing" | "completed" | "failed";

const statusConfig: Record<DocumentStatus, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  pending: { label: "Pending", variant: "secondary" },
  processing: { label: "Processing", variant: "outline" },
  completed: { label: "Completed", variant: "default" },
  failed: { label: "Failed", variant: "destructive" },
};

export function StatusBadge({ status }: { status: DocumentStatus }) {
  const config = statusConfig[status];
  return <Badge variant={config.variant}>{config.label}</Badge>;
}
```

### Borrower Search with Debounce
```typescript
// Source: TanStack Query + controlled input pattern
// components/borrowers/borrower-search.tsx
"use client";
import { useState, useDeferredValue } from "react";
import { useQuery } from "@tanstack/react-query";
import { Input } from "@/components/ui/input";
import { searchBorrowers } from "@/lib/api/borrowers";

export function BorrowerSearch() {
  const [searchTerm, setSearchTerm] = useState("");
  const deferredSearch = useDeferredValue(searchTerm);

  const { data, isLoading } = useQuery({
    queryKey: ["borrowers", "search", deferredSearch],
    queryFn: () => searchBorrowers({ name: deferredSearch }),
    enabled: deferredSearch.length >= 2,
  });

  return (
    <div>
      <Input
        placeholder="Search borrowers by name..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
      />
      {/* Results rendering */}
    </div>
  );
}
```

### Income Timeline Component
```typescript
// Source: Requirements UI-23
// components/borrowers/income-timeline.tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { IncomeRecord } from "@/lib/api/types";

interface IncomeTimelineProps {
  records: IncomeRecord[];
}

export function IncomeTimeline({ records }: IncomeTimelineProps) {
  // Sort by year descending
  const sorted = [...records].sort((a, b) => b.year - a.year);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Income History</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {sorted.map((record) => (
            <div key={record.id} className="flex justify-between items-center border-l-2 pl-4">
              <div>
                <p className="font-medium">{record.year}</p>
                <p className="text-sm text-muted-foreground">
                  {record.source_type} {record.employer && `- ${record.employer}`}
                </p>
              </div>
              <div className="text-right">
                <p className="font-bold">
                  ${parseFloat(record.amount).toLocaleString()}
                </p>
                <p className="text-sm text-muted-foreground">
                  /{record.period}
                </p>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pages Router | App Router | Next.js 13 (2022) | Server Components, layouts |
| Tailwind v3 config | Tailwind v4 @theme | Tailwind 4.0 (2024) | CSS-first config, OKLCH colors |
| tailwindcss-animate | tw-animate-css | shadcn/ui 2024 | Drop-in replacement |
| useFormState | useActionState | React 19 | Renamed hook for actions |
| React Query v4 | TanStack Query v5 | 2023 | Simplified API, better types |
| forwardRef pattern | ComponentProps | React 19 | Simpler ref forwarding |

**Deprecated/outdated:**
- `tailwindcss-animate`: Use `tw-animate-css` instead (already in project)
- `useFormState`: Renamed to `useActionState` in React 19
- Tailwind config file: v4 uses CSS @theme directive (already configured)
- `orm_mode` in Pydantic: Use `from_attributes` (backend already correct)

## Open Questions

Things that couldn't be fully resolved:

1. **Next.js 16 specific features**
   - What we know: Project uses Next.js 16.1.4, React 19.2.3
   - What's unclear: Any breaking changes from Next.js 15 in file uploads or API calls
   - Recommendation: Use standard fetch() patterns, monitor for issues

2. **Mermaid version compatibility**
   - What we know: v10+ works with Next.js, some layout issues reported
   - What's unclear: Best version for architecture diagrams
   - Recommendation: Start with mermaid@11, downgrade if issues

3. **Progress bar for file upload**
   - What we know: TanStack Query doesn't natively track upload progress
   - What's unclear: Whether to add axios for progress or keep it simple
   - Recommendation: Use simple isPending state; add axios only if progress bar UX is critical

4. **TypeScript types from OpenAPI**
   - What we know: Tools like hey-api/openapi-ts can auto-generate types
   - What's unclear: Whether complexity is worth it for small API
   - Recommendation: Manual types for v1; consider openapi-ts for v2 if API grows

## Sources

### Primary (HIGH confidence)
- [shadcn/ui Data Table](https://ui.shadcn.com/docs/components/data-table) - Table setup, columns, pagination
- [shadcn/ui Tailwind v4](https://ui.shadcn.com/docs/tailwind-v4) - Migration guide, CSS variables
- [TanStack Query v5 Mutations](https://tanstack.com/query/v5/docs/framework/react/guides/mutations) - useMutation API
- [TanStack Query Auto Refetching](https://tanstack.com/query/v4/docs/framework/react/examples/auto-refetching) - refetchInterval pattern
- Existing backend API at `/backend/src/api/documents.py` and `/backend/src/api/borrowers.py`

### Secondary (MEDIUM confidence)
- [react-dropzone npm](https://www.npmjs.com/package/react-dropzone) - useDropzone API
- [Next.js Forms Guide](https://nextjs.org/docs/app/guides/forms) - File upload patterns
- [Hey API Full-Stack Type Safety](https://abhayramesh.com/blog/type-safe-fullstack) - TypeScript generation approach
- [Mermaid Next.js Integration](https://www.andynanopoulos.com/blog/how-to-integrate-next-react-mermaid-markdown) - Client component setup

### Tertiary (LOW confidence)
- Various Medium/DEV articles on drag-drop patterns (verified against official docs)
- GitHub discussions on Tailwind v4 + shadcn/ui compatibility issues

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries are mature, widely used, well-documented
- Architecture: HIGH - Standard Next.js App Router patterns, established project structure
- Pitfalls: HIGH - Common issues well-documented in GitHub issues and community
- Code examples: HIGH - Based on official documentation and existing backend patterns

**Research date:** 2026-01-24
**Valid until:** 2026-02-14 (21 days - fast-moving frontend ecosystem)
