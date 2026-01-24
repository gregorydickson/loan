# Feature Research: LangExtract + LightOnOCR Integration (v2.0)

**Domain:** Document extraction with source grounding and GPU-based OCR
**Researched:** 2026-01-24
**Confidence:** HIGH (verified with official documentation and GitHub repositories)

## Executive Summary

This research covers feature requirements for adding LangExtract-based extraction and LightOnOCR GPU OCR service to the existing loan document extraction system. The key value propositions are:

1. **LangExtract:** Character-level source grounding for complete audit traceability
2. **LightOnOCR:** GPU-accelerated OCR for high-quality scanned document processing

The existing Docling + Gemini pipeline remains valuable for fast, simple document processing. The v2.0 milestone adds LangExtract as an alternative extraction path for compliance-focused workflows and LightOnOCR for scanned document quality improvement.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist when adopting LangExtract and LightOnOCR. Missing these = integration feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Character-level offset tracking** | Core LangExtract value prop - every extraction maps to exact source location | MEDIUM | Extends existing page-level `SourceReference` to include `start_char` and `end_char` offsets |
| **Few-shot example-based schema** | LangExtract enforces schemas via examples, not Pydantic models | LOW | Define loan extraction examples once; model learns field patterns |
| **Multi-pass extraction** | Expected for recall improvement on long documents | LOW | Configure `extraction_passes=2-5` for thorough extraction |
| **HTML visualization output** | LangExtract generates interactive visualizations for audit | LOW | Generate self-contained HTML showing highlighted extractions |
| **High-quality scanned document OCR** | Primary LightOnOCR use case | MEDIUM | Replace Docling OCR path with LightOnOCR for scanned docs |
| **Extraction method selection API** | Users need to choose between Docling+Gemini vs LangExtract | LOW | Query param or request body field: `extraction_method: "docling" | "langextract"` |
| **Confidence scores per extraction** | Already have this; LangExtract should maintain parity | LOW | Map LangExtract confidence to existing 0.0-1.0 scale |
| **Chunking for long documents** | LangExtract handles internally via `max_char_buffer` | LOW | Configure chunk size (1000-3000 chars) for loan documents |

### Differentiators (Competitive Advantage)

Features that set LangExtract + LightOnOCR apart from current Docling + Gemini approach.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Precise source grounding with visual audit** | Every extracted field links to exact character range in source; interactive HTML shows highlighted spans | MEDIUM | Critical for compliance review - click on any extracted value to see exact source location |
| **End-to-end GPU OCR (no pipeline fragmentation)** | LightOnOCR is fully differentiable, no brittle pipeline stages | MEDIUM | Single model handles text+layout vs traditional OCR + layout + parsing chain |
| **Schema enforcement via controlled generation** | Gemini's controlled generation guarantees valid JSON matching schema | LOW | No more schema violation errors or hallucinated field names |
| **Parallel chunk processing** | `max_workers` enables concurrent LLM calls across chunks | LOW | 10-20x throughput improvement for long documents vs sequential |
| **Multi-sample merge for recall** | Multiple extraction passes catch entities missed in single pass | LOW | LangExtract runs stochastic extraction multiple times, merges results |
| **Auditability for regulated industries** | Character-level provenance enables compliance verification | LOW | Every loan amount, SSN, income figure traceable to exact source text |
| **OCR cost efficiency** | LightOnOCR: <$0.01 per 1,000 pages on GPU | MEDIUM | 10-100x cheaper than proprietary OCR APIs for scanned documents |
| **vLLM deployment for OCR** | Standard vLLM serving for LightOnOCR on Cloud Run GPU | MEDIUM | Production-ready inference server with batching |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems in this domain.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Real-time character-level updates** | "Show extraction as it happens" | WebSocket complexity; LLM extraction is batch-oriented; adds latency | Async processing with status polling; show results after completion |
| **Universal extraction schema** | "One schema for all loan doc types" | Loan apps, W-2s, bank statements have different structures; generic schema loses precision | Document-type-specific few-shot examples (loan app examples, W-2 examples) |
| **Always use LangExtract** | "New = better, replace Docling path" | LangExtract requires text input (no native PDF); Docling handles structure recovery | Docling for layout/table recovery, LangExtract for semantic extraction on text output |
| **Always use LightOnOCR** | "GPU = better, replace all OCR" | Native digital PDFs don't need OCR; GPU cold start adds latency | Auto-detect scanned vs digital; LightOnOCR only for scanned docs |
| **Character offsets for all fields** | "Consistency means offsets everywhere" | Many fields (SSN, phone) are synthetic/normalized, not verbatim from text | Offset tracking for entity mentions; acknowledge normalized fields have no direct offset |
| **Custom LangExtract model fine-tuning** | "Train on our specific loan docs" | Fine-tuning Gemini not supported; few-shot examples are the customization mechanism | Add domain-specific few-shot examples; iterate on example quality |
| **Bounding box extraction from LightOnOCR** | "Visual grounding like V7 Go" | LightOnOCR-2-1B base doesn't include bbox; requires -bbox variant and more memory | Use LightOnOCR for text extraction; if visual grounding needed, consider LightOnOCR-2-1B-bbox variant |

---

## Feature Dependencies

```
[LangExtract Character Offsets]
    |-- requires --> [Docling Text with Page Boundaries]
    |-- requires --> [Few-shot Example Definition]
    |-- enables --> [HTML Visualization]
    |-- enables --> [Enhanced SourceReference Model]

[LightOnOCR GPU Service]
    |-- requires --> [Cloud Run GPU (L4/T4)]
    |-- requires --> [vLLM Deployment]
    |-- enables --> [Scanned Document Path]
    |-- enhances --> [Document Ingestion Pipeline]

[Extraction Method Selection]
    |-- requires --> [LangExtract Integration]
    |-- requires --> [Existing Docling+Gemini Path]
    |-- enables --> [API Method Parameter]

[Few-shot Examples]
    |-- defines --> [Loan Application Schema]
    |-- defines --> [Income Verification Schema]
    |-- defines --> [W-2/Tax Document Schema]
```

### Dependency Notes

- **LangExtract requires Docling preprocessing:** LangExtract works on raw text strings only. Docling converts PDF/DOCX to structured text with page metadata. The integration pipeline: Docling -> LangExtract -> character offsets mapped back to pages.

- **LightOnOCR requires GPU infrastructure:** Cannot run on standard Cloud Run instances. Requires L4 GPU (24GB VRAM) or similar. Deploy as separate service with GPU allocation.

- **Few-shot examples drive extraction quality:** Unlike Pydantic schemas, LangExtract learns from examples. Quality of examples directly impacts extraction accuracy. Start with 2-3 well-crafted examples per document type.

- **Character offsets require careful chunking:** Offsets are relative to chunk start. Must track chunk position in full document to provide document-level offsets.

---

## When to Use LangExtract vs Docling+Gemini

### Use LangExtract When:

| Scenario | Why LangExtract | Notes |
|----------|-----------------|-------|
| **Compliance/audit requirements** | Character-level traceability for every extracted value | Regulated industries (finance, healthcare) require provenance |
| **Long documents (10+ pages)** | Multi-pass extraction catches entities missed in single pass | `extraction_passes=3-5` improves recall |
| **Need to verify extraction visually** | Interactive HTML visualization shows highlighted spans | Click any value to see exact source location |
| **Complex multi-entity documents** | Chunking + parallel processing handles entity density | Loan apps with multiple borrowers, co-signers |
| **Few-shot schema customization** | Define extraction via examples, no code changes | Add new field types by providing examples |

### Use Docling+Gemini (Current Path) When:

| Scenario | Why Docling+Gemini | Notes |
|----------|-------------------|-------|
| **Simple documents** | Faster, lower cost for straightforward extraction | Single borrower, clear structure |
| **Table-heavy documents** | Docling's TableFormer excels at table recovery | Financial statements, asset schedules |
| **Page-level attribution sufficient** | If character offsets aren't required, simpler path | Internal processing without audit trail |
| **Cold start latency matters** | Docling is simpler to deploy, faster startup | High-volume, latency-sensitive workloads |

### Decision Matrix

| Factor | Docling+Gemini | LangExtract |
|--------|----------------|-------------|
| Source grounding | Page + snippet | Character offset |
| Long document handling | Manual chunking | Built-in multi-pass |
| Schema definition | Pydantic models | Few-shot examples |
| Visualization | None | Interactive HTML |
| Audit compliance | Basic | Full traceability |
| Deployment complexity | Standard | Requires Docling frontend |

**Recommendation:** Offer both paths via API selection. Default to LangExtract for compliance-focused workflows, Docling+Gemini for simple/fast workflows.

---

## When to Use LightOnOCR vs Docling OCR

### Use LightOnOCR When:

| Scenario | Why LightOnOCR | Notes |
|----------|----------------|-------|
| **Scanned documents** | End-to-end VLM architecture handles noise, skew, low quality | W-2s, pay stubs, bank statements often scanned |
| **High-volume OCR workloads** | 5.71 pages/sec on H100; <$0.01/1000 pages | Cost-effective for batch processing |
| **Complex layouts** | Handles tables, multi-column, forms without pipeline | Financial documents with varied layouts |
| **GPU infrastructure available** | Requires L4/T4/A100 GPU allocation | Cloud Run GPU or dedicated VM |

### Use Docling OCR (Current Path) When:

| Scenario | Why Docling | Notes |
|----------|-------------|-------|
| **Native digital PDFs** | No OCR needed; Docling extracts text directly | Most loan applications are digital-origin |
| **No GPU available** | Docling runs on CPU | Dev environments, cost-sensitive deploys |
| **Cold start matters** | Docling is lighter than LightOnOCR model | Real-time processing needs |
| **DOCX/PPTX input** | Docling handles multiple formats | LightOnOCR is image-only |

### Auto-Selection Logic

```python
def select_ocr_method(document: DocumentMetadata) -> Literal["docling", "lightonocr"]:
    """Auto-select OCR method based on document characteristics."""
    # Images always need OCR
    if document.file_type in ["png", "jpg", "jpeg"]:
        return "lightonocr"  # Best quality for images

    # PDFs: check if scanned
    if document.file_type == "pdf":
        # If extractable text is minimal, likely scanned
        if is_scanned_pdf(document):
            return "lightonocr"
        return "docling"  # Native PDF, no OCR needed

    # DOCX doesn't need OCR
    return "docling"
```

**Recommendation:** Implement scanned document detection. Route scanned docs to LightOnOCR GPU service, native docs to Docling CPU path. Expose manual override via API.

---

## MVP Definition

### Launch With (v2.0)

Minimum viable LangExtract + LightOnOCR integration.

- [ ] **LangExtract basic integration** - Extract borrowers with character offsets
- [ ] **Few-shot examples for loan docs** - 3 examples covering common patterns
- [ ] **Enhanced SourceReference model** - Add `start_char`, `end_char` fields
- [ ] **Extraction method selection API** - `extraction_method` parameter on upload/extract endpoints
- [ ] **LightOnOCR Cloud Run service** - Deployed with L4 GPU
- [ ] **Scanned document detection** - Auto-route to LightOnOCR
- [ ] **HTML visualization generation** - Save to GCS alongside extraction results

### Add After Validation (v2.x)

Features to add once core is working.

- [ ] **Multi-pass extraction config** - Expose `extraction_passes` via API for recall tuning
- [ ] **Parallel chunk workers** - Configure `max_workers` for throughput optimization
- [ ] **Document-type-specific examples** - Separate example sets for W-2, bank statements, pay stubs
- [ ] **Visualization in dashboard** - Embed HTML viewer in Next.js frontend
- [ ] **Extraction method comparison** - Side-by-side results from both methods

### Future Consideration (v3+)

Features to defer until product-market fit is established.

- [ ] **Bounding box extraction** - LightOnOCR-2-1B-bbox for visual grounding
- [ ] **Cross-document entity resolution** - Link same borrower across multiple documents
- [ ] **Example library management** - UI for adding/editing few-shot examples
- [ ] **Extraction analytics** - Track accuracy metrics by document type and method

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Character-level source offsets | HIGH | MEDIUM | P1 |
| Few-shot example schema | HIGH | LOW | P1 |
| Extraction method selection API | HIGH | LOW | P1 |
| LightOnOCR service deployment | MEDIUM | HIGH | P1 |
| Scanned document detection | MEDIUM | MEDIUM | P1 |
| HTML visualization | MEDIUM | LOW | P2 |
| Multi-pass extraction | MEDIUM | LOW | P2 |
| Document-type examples | MEDIUM | MEDIUM | P2 |
| Dashboard visualization | LOW | MEDIUM | P3 |
| Bounding box extraction | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for v2.0 launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## Integration with Existing Features

The v2.0 features build on the existing v1.0 system:

### Existing Features (v1.0 - Already Built)

| Feature | Status | v2.0 Impact |
|---------|--------|-------------|
| Document upload (PDF/DOCX/image) | Complete | Add extraction_method parameter |
| Docling text extraction with pages | Complete | Serves as input to LangExtract |
| Gemini extraction with confidence | Complete | Alternative path preserved |
| SourceReference (page + snippet) | Complete | Extended with char offsets |
| Borrower search/query APIs | Complete | No changes needed |
| Next.js dashboard | Complete | Add visualization viewer |

### Integration Points

```
                    Document Upload
                           |
                    +------v------+
                    |  Detection  |
                    | (scanned?)  |
                    +------+------+
                           |
        +------------------+------------------+
        |                                     |
   Scanned                              Native PDF/DOCX
        |                                     |
+-------v-------+                    +--------v--------+
|  LightOnOCR   |                    |     Docling     |
|  (GPU Cloud   |                    |  (CPU-based)    |
|   Run L4)     |                    +--------+--------+
+-------+-------+                             |
        |                                     |
        +------------------+------------------+
                           |
                    Text + Metadata
                           |
                    +------v------+
                    |   Method    |
                    |  Selection  |
                    +------+------+
                           |
        +------------------+------------------+
        |                                     |
   LangExtract                        Docling+Gemini
   (character offsets,                (page attribution,
    multi-pass,                        simple/fast)
    visualization)
        |                                     |
+-------v-------+                    +--------v--------+
|   Enhanced    |                    |    Current      |
| BorrowerRecord|                    | BorrowerRecord  |
| (char offsets)|                    | (page+snippet)  |
+---------------+                    +-----------------+
```

---

## Competitor Feature Analysis

| Feature | Current System (Docling+Gemini) | LangExtract | LangChain Extraction | LlamaIndex |
|---------|--------------------------------|-------------|---------------------|------------|
| Source grounding | Page + 200-char snippet | Character offsets | No native grounding | Document metadata |
| Long doc handling | Manual chunking | Built-in multi-pass | Manual | Built-in nodes |
| Schema definition | Pydantic models | Few-shot examples | Pydantic | Pydantic |
| Visualization | None | Interactive HTML | None | None |
| Model support | Gemini only | Gemini, OpenAI, Ollama | Any LLM | Any LLM |
| Controlled generation | No | Yes (Gemini) | No | No |

**Our Approach (v2.0):**
- Keep Docling+Gemini as fast path for simple documents
- Add LangExtract for compliance-focused workflows with full traceability
- Expose selection via API; let users choose based on requirements
- LightOnOCR as dedicated GPU service for scanned document quality

---

## Sources

### LangExtract

- [Google LangExtract GitHub Repository](https://github.com/google/langextract) - Official source, verified features and API
- [Introducing LangExtract - Google Developers Blog](https://developers.googleblog.com/introducing-langextract-a-gemini-powered-information-extraction-library/) - July 2025 release announcement
- [LangExtract + Docling Integration](https://dev.to/_aparna_pradhan_/the-perfect-extraction-unlocking-unstructured-data-with-docling-langextract-1j3b) - Combined workflow documentation
- [LangExtract Critical Review](https://medium.com/@meghanaharishankara/googles-langextract-a-critical-review-from-the-trenches-e41fae3e03b0) - Real-world usage experience

### LightOnOCR

- [LightOnOCR-2-1B Hugging Face Model Card](https://huggingface.co/lightonai/LightOnOCR-2-1B) - Official model with deployment instructions
- [LightOnOCR Blog Post](https://www.lighton.ai/lighton-blogs/making-knowledge-machine-readable) - Architecture and performance details
- [LightOnOCR Hugging Face Blog](https://huggingface.co/blog/lightonai/lightonocr) - Technical deep dive

### Comparison and Selection

- [Docling vs LangExtract Comparison](https://github.com/google/langextract/issues/184) - Integration proposal with rationale
- [OCR Models Comparison 2025](https://www.e2enetworks.com/blog/complete-guide-open-source-ocr-models-2025) - GPU vs CPU OCR benchmarks
- [Document Analysis with Grounding - Azure](https://learn.microsoft.com/en-us/azure/ai-services/content-understanding/document/enrichments) - Industry grounding patterns

### Source Grounding and Compliance

- [Google Cloud Grounding Overview](https://cloud.google.com/vertex-ai/generative-ai/docs/grounding/overview) - Enterprise grounding patterns
- [Agentic Document Extraction for Financial Services](https://landing.ai/solutions/financial-services) - Compliance workflow integration

---
*Feature research for: LangExtract + LightOnOCR integration for loan document extraction*
*Researched: 2026-01-24*
*Confidence: HIGH*
