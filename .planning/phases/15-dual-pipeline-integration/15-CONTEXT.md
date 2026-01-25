# Phase 15: Dual Pipeline Integration - Context

**Gathered:** 2026-01-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Enable API-based extraction method selection with consistent output across both Docling and LangExtract pipelines. Users can choose extraction method and OCR mode via query parameters. Both pipelines produce normalized BorrowerRecord output.

</domain>

<decisions>
## Implementation Decisions

### Proof of Concept Approach
- Keep everything simple - this is a proof of concept
- Minimal viable implementation to demonstrate dual pipeline capability
- No over-engineering or premature optimization

### Claude's Discretion
- API parameter naming and structure
- Routing logic and priority rules
- Error handling and fallback behavior
- Metadata tracking and observability
- Default values for method/ocr parameters
- Output normalization strategy
- Backward compatibility approach

</decisions>

<specifics>
## Specific Ideas

No specific requirements - open to standard approaches. Focus on simplicity and getting it working.

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope.

</deferred>

---

*Phase: 15-dual-pipeline-integration*
*Context gathered: 2026-01-25*
