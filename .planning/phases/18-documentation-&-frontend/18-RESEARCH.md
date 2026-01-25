# Phase 18: Documentation & Frontend - Research

**Researched:** 2026-01-25
**Domain:** Technical Documentation, Frontend UI Components, ADR Patterns
**Confidence:** HIGH

## Summary

This phase focuses on completing v2.0 documentation and adding extraction method/OCR selection to the frontend upload UI. The research investigated three main areas:

1. **Documentation Standards**: The project already uses MADR-format ADRs in `docs/ARCHITECTURE_DECISIONS.md` with 17 existing decisions. New ADRs for LangExtract, LightOnOCR, and CloudBuild should follow this established pattern with Status, Context, Decision, Consequences, and Alternatives sections.

2. **API Documentation**: The backend already has dual pipeline support implemented with `method` and `ocr` query parameters on the upload endpoint. Documentation should focus on user guides with practical examples, not just API reference.

3. **Frontend Enhancement**: The existing upload component uses `react-dropzone` with shadcn/ui styling. Adding extraction method/OCR selection requires shadcn Select components with controlled state integration to pass parameters to the upload API.

**Primary recommendation:** Leverage existing documentation patterns and shadcn/ui components - this is primarily a content creation and component enhancement phase, not new architecture.

## Standard Stack

The established libraries/tools for this domain:

### Core (Already in Project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| shadcn/ui | Latest | UI components (Select, Dialog) | Already used in project |
| react-dropzone | Latest | File upload with drag-and-drop | Already in UploadZone component |
| @tanstack/react-query | Latest | API state management | Already used for mutations/queries |
| Tailwind CSS | 4.0 | Styling | Already configured |

### Documentation Tools
| Tool | Purpose | When to Use |
|------|---------|-------------|
| Markdown | All documentation | Default for all guides |
| Mermaid | Architecture diagrams | SYSTEM_DESIGN.md already uses |
| MADR format | ADR structure | Match existing ADRs |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Markdown docs | Docusaurus | Overkill for portfolio project, increases complexity |
| shadcn Select | Custom dropdown | Would break design system consistency |
| MADR format | Y-statements | Project already uses MADR, stick with it |

**Installation:**
No new packages required - all dependencies already installed.

## Architecture Patterns

### Recommended Documentation Structure
```
docs/
├── SYSTEM_DESIGN.md              # Existing - update with dual pipeline
├── ARCHITECTURE_DECISIONS.md     # Existing - add ADRs 018-020
├── cloudbuild-deployment-guide.md # Existing - complete
├── terraform-to-gcloud-inventory.md # Existing
├── api/
│   └── extraction-method-guide.md  # NEW: User guide for method/ocr params
├── guides/
│   ├── few-shot-examples.md       # NEW: Creating/updating examples
│   └── gpu-service-cost.md        # NEW: Cost management guide
└── migration/
    └── terraform-migration.md     # NEW: State archival procedures
```

### Pattern 1: ADR Structure (Match Existing)
**What:** MADR-format architecture decision records
**When to use:** Any significant technical decision
**Example:**
```markdown
## ADR-018: Use LangExtract for Structured Extraction

### Status
Accepted

### Context
[Problem statement - 2-3 sentences describing the challenge]

### Decision
[Solution chosen with key implementation details]

### Consequences
**Positive:**
- [Benefit 1]
- [Benefit 2]

**Negative:**
- [Tradeoff 1]
- [Tradeoff 2]

### Alternatives Considered
| Option | Pros | Cons |
|--------|------|------|
| [Alternative] | [Pros] | [Cons] |
```

### Pattern 2: User Guide Structure
**What:** Task-oriented documentation with examples
**When to use:** API user documentation
**Example:**
```markdown
# Extraction Method Selection Guide

## Quick Reference
| Method | When to Use | Cost | Accuracy |
|--------|-------------|------|----------|
| docling | Standard docs, fastest | Low | Good |
| langextract | Complex docs, audit trail | Medium | Better |

## Examples

### Basic Upload (default Docling)
curl -X POST /api/documents/ -F "file=@loan.pdf"

### LangExtract with Auto OCR
curl -X POST "/api/documents/?method=langextract&ocr=auto" -F "file=@scan.pdf"
```

### Pattern 3: Frontend Select with Upload Integration
**What:** Controlled select components passing params to mutation
**When to use:** Upload UI with method/OCR selection
**Example:**
```typescript
// Source: shadcn/ui Select + existing project patterns
function UploadZone() {
  const [method, setMethod] = useState<ExtractionMethod>("docling");
  const [ocr, setOcr] = useState<OCRMode>("auto");

  const onDrop = useCallback((files: File[]) => {
    mutate({ file: files[0], method, ocr });
  }, [mutate, method, ocr]);

  return (
    <div className="space-y-4">
      <div className="flex gap-4">
        <Select value={method} onValueChange={setMethod}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Extraction method" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="docling">Docling (Fast)</SelectItem>
            <SelectItem value="langextract">LangExtract (Precise)</SelectItem>
          </SelectContent>
        </Select>

        <Select value={ocr} onValueChange={setOcr}>
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="OCR mode" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="auto">Auto OCR</SelectItem>
            <SelectItem value="force">Force OCR</SelectItem>
            <SelectItem value="skip">Skip OCR</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Existing dropzone */}
    </div>
  );
}
```

### Anti-Patterns to Avoid
- **ADR sprawl:** Don't create separate ADR files - add to existing ARCHITECTURE_DECISIONS.md
- **Duplicate documentation:** Don't duplicate OpenAPI docs - reference them
- **Uncontrolled selects:** Always use controlled state for form components

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Dropdown UI | Custom dropdown | shadcn Select | Accessibility, keyboard nav, positioning |
| Form validation | Manual checks | react-hook-form (if needed) | Already available, handles edge cases |
| API state | useState + fetch | @tanstack/react-query | Already used, handles caching/retry |
| Diagrams | Custom SVG | Mermaid in Markdown | Already used in SYSTEM_DESIGN.md |

**Key insight:** This phase is primarily content creation and minor UI enhancement. The infrastructure exists - don't over-engineer.

## Common Pitfalls

### Pitfall 1: Inconsistent ADR Numbering
**What goes wrong:** ADRs added with incorrect numbering or duplicate IDs
**Why it happens:** Not checking existing ADRs before adding new ones
**How to avoid:** Check ARCHITECTURE_DECISIONS.md index, continue from ADR-017
**Warning signs:** Multiple ADRs with same number, gaps in sequence

### Pitfall 2: Documenting Code Instead of Decisions
**What goes wrong:** ADRs describe implementation instead of rationale
**Why it happens:** Writing ADRs after implementation as documentation
**How to avoid:** Focus on "why" not "how" - code shows how, ADR explains why
**Warning signs:** ADR reads like code comments, no alternatives section

### Pitfall 3: Breaking Upload Mutation Interface
**What goes wrong:** Adding params breaks existing mutation signature
**Why it happens:** Not updating useUploadDocument hook to accept params
**How to avoid:** Extend mutation to accept optional params with defaults
**Warning signs:** TypeScript errors, existing upload still works

### Pitfall 4: Forgetting API URL Parameters
**What goes wrong:** Frontend sends params but API doesn't receive them
**Why it happens:** Params sent in body instead of query string
**How to avoid:** API expects `?method=X&ocr=Y` query params
**Warning signs:** method/ocr always default values in API logs

### Pitfall 5: Incomplete Few-Shot Documentation
**What goes wrong:** Guide doesn't explain verbatim text requirement
**Why it happens:** Missing critical LXTR-05 requirement
**How to avoid:** Document that extraction_text MUST be exact substring
**Warning signs:** validate_examples() failures after following guide

## Code Examples

Verified patterns from official sources and existing project code:

### Extending useUploadDocument Hook
```typescript
// Source: frontend/src/hooks/use-documents.ts (extend existing)
type UploadParams = {
  file: File;
  method?: "docling" | "langextract" | "auto";
  ocr?: "auto" | "force" | "skip";
};

export function useUploadDocument() {
  const queryClient = useQueryClient();

  return useMutation<DocumentUploadResponse, Error, UploadParams>({
    mutationFn: async ({ file, method = "docling", ocr = "auto" }) => {
      const formData = new FormData();
      formData.append("file", file);
      // Pass as query params (API expects query not body)
      const params = new URLSearchParams({ method, ocr });
      return uploadDocumentWithParams(formData, params.toString());
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}
```

### Upload API Client Update
```typescript
// Source: frontend/src/lib/api/documents.ts (extend existing)
export async function uploadDocumentWithParams(
  formData: FormData,
  queryParams: string
): Promise<DocumentUploadResponse> {
  return apiClient<DocumentUploadResponse>(`/api/documents/?${queryParams}`, {
    method: "POST",
    body: formData,
  });
}
```

### shadcn Select Component Usage
```typescript
// Source: shadcn/ui docs + Radix primitives
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// If Select component not installed, add it:
// npx shadcn@latest add select

<Select value={value} onValueChange={setValue}>
  <SelectTrigger className="w-[180px]">
    <SelectValue placeholder="Select option" />
  </SelectTrigger>
  <SelectContent position="popper">
    <SelectItem value="option1">Option 1</SelectItem>
    <SelectItem value="option2">Option 2</SelectItem>
  </SelectContent>
</Select>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Terraform for all deploys | CloudBuild for services | v2.0 (2026-01) | Simpler CI/CD, document migration |
| Docling only extraction | Dual pipeline (Docling + LangExtract) | v2.0 (2026-01) | Need method selection UI |
| No OCR control | OCR mode parameter | v2.0 (2026-01) | Need OCR selection UI |

**Deprecated/outdated:**
- Terraform deployment (archived to /archive/terraform/)
- Single extraction method (v1.0 Docling-only)

## Open Questions

Things that couldn't be fully resolved:

1. **Select Component Installation Status**
   - What we know: Project uses shadcn/ui with button, card, table, input, dialog, tabs, badge, skeleton, progress, separator
   - What's unclear: Whether Select component is already installed
   - Recommendation: Check `frontend/src/components/ui/select.tsx` - if missing, run `npx shadcn@latest add select`

2. **Few-Shot Example Versioning Strategy**
   - What we know: LXTR-12 requires versioning, examples in `backend/examples/`
   - What's unclear: Specific versioning scheme (semver? timestamps?)
   - Recommendation: Document git-based versioning with commit hashes for traceability

## Sources

### Primary (HIGH confidence)
- Project files: `docs/ARCHITECTURE_DECISIONS.md` - existing ADR patterns
- Project files: `docs/cloudbuild-deployment-guide.md` - deployment guide format
- Project files: `frontend/src/components/documents/upload-zone.tsx` - existing UI patterns
- Project files: `backend/src/api/documents.py` - API params implementation
- Project files: `backend/examples/__init__.py` - few-shot example structure

### Secondary (MEDIUM confidence)
- [MADR Template](https://adr.github.io/madr/) - Official MADR format
- [shadcn/ui Select](https://ui.shadcn.com/docs/components/select) - Component API
- [AWS ADR Best Practices](https://aws.amazon.com/blogs/architecture/master-architecture-decision-records-adrs-best-practices-for-effective-decision-making/) - ADR guidance

### Tertiary (LOW confidence)
- None - all findings verified against project code or official docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - verified against existing project code
- Architecture: HIGH - patterns match existing project documentation
- Pitfalls: HIGH - derived from codebase analysis and API implementation

**Research date:** 2026-01-25
**Valid until:** 2026-02-25 (30 days - stable documentation patterns)
