# Project Research Summary

**Project:** Loan Document Extraction System v2.0
**Domain:** LLM-powered document extraction with source grounding and GPU OCR
**Researched:** 2026-01-24
**Confidence:** HIGH

## Executive Summary

The v2.0 milestone enhances an existing production-ready loan document extraction system with three major capabilities: LangExtract for character-level source grounding, LightOnOCR GPU service for high-quality scanned document processing, and CloudBuild deployment to replace Terraform. This is a brownfield enhancement, not a greenfield project — the v1.0 Docling + Gemini pipeline remains fully functional and valuable for simple document processing.

The research reveals a clear technical strategy: dual extraction pipelines coexisting with API-based selection. LangExtract provides character-level offsets enabling complete audit traceability for compliance-focused workflows, while the existing Docling path handles simple documents faster and cheaper. LightOnOCR deployed as a dedicated GPU Cloud Run service processes scanned documents with state-of-the-art quality (83.2% on OlmOCR-Bench), routing only when needed to manage costs. CloudBuild simplifies deployment without sacrificing reproducibility, replacing Terraform for Cloud Run services while keeping infrastructure provisioning as one-time scripts.

The critical risks are integration-focused, not greenfield risks. Character offset alignment between LangExtract and Docling requires careful offset translation. GPU cold start costs ($0.67/hour) must be managed through smart routing (scanned vs digital document detection). Terraform state orphaning during migration requires explicit archival and service account revocation. Few-shot example quality directly determines LangExtract accuracy — examples must use verbatim text in document order or prompt alignment warnings degrade extraction quality. These are addressable through deliberate architecture decisions in early phases, not intractable technical challenges.

## Key Findings

### Recommended Stack

**v2.0 adds three major components to existing v1.0 stack:**

**LangExtract (v1.1.1)** provides character-level source grounding that the current Gemini structured output approach lacks. Every extracted field maps to exact `(char_start, char_end)` positions in source text, enabling interactive HTML visualizations where users click any value to see its exact source location. Built-in chunking with multi-pass extraction improves recall on long documents (10+ page loan applications with multiple borrowers). Few-shot schema definition is more flexible than Pydantic models for domain customization.

**LightOnOCR-2-1B** is a 1B parameter vision-language model delivering state-of-the-art OCR quality (83.2% on OlmOCR-Bench, outperforming models 9x larger). End-to-end architecture eliminates brittle OCR pipelines — direct image-to-text with natural reading order. Deployed as dedicated Cloud Run GPU service (L4 GPU, 24GB VRAM) with vLLM serving for production-grade batching and optimization. Cost-effective at <$0.01 per 1,000 pages, but requires smart routing to avoid $485/month baseline if kept always-on.

**CloudBuild + gcloud CLI** replaces Terraform for application deployment while keeping infrastructure provisioning as one-time scripts. Native GCP integration eliminates external tooling dependencies. Direct `gcloud run deploy` commands in cloudbuild.yaml provide faster iteration than Terraform state management. Built-in CI/CD with GitHub triggers enables automatic builds on push. Hybrid approach avoids re-provisioning costs (Cloud SQL, VPC remain as-is) while simplifying the deployment pipeline.

**Core technologies:**
- **LangExtract 1.1.1**: Source-grounded extraction with character offsets — Google's purpose-built library for LLM extraction with precise attribution
- **LightOnOCR-2-1B**: GPU OCR model (1B params, BF16) — SOTA quality for scanned documents, vLLM deployment
- **CloudBuild**: Native GCP CI/CD — Replaces Terraform for Cloud Run deployments
- **Gemini 2.5 Flash**: LLM backend for LangExtract — Best speed-cost-quality balance ($0.075 per 1M input tokens)
- **Cloud Run GPU (L4)**: Serverless GPU compute — 24GB VRAM, scale-to-zero, $0.67/hour when running

**Existing v1.0 stack (unchanged):**
- Docling 2.70.0, FastAPI 0.128.0, SQLAlchemy 2.0.46, PostgreSQL, Cloud Storage, Cloud Tasks

### Expected Features

**v2.0 focuses on enhanced extraction capabilities and deployment modernization, not net-new end-user features.**

**Must have (table stakes):**
- **Character-level offset tracking** — Core LangExtract value prop; extends SourceReference with char_start/char_end fields
- **Few-shot example-based schema** — LangExtract enforces schemas via examples, not just Pydantic models
- **Multi-pass extraction** — Configurable passes (2-5) for thorough extraction on long documents
- **High-quality scanned document OCR** — Primary LightOnOCR use case; replaces Docling OCR for scanned docs
- **Extraction method selection API** — Query param or request field: `extraction_method: "docling" | "langextract"`
- **HTML visualization output** — LangExtract generates interactive visualizations for audit with highlighted source spans

**Should have (competitive advantage):**
- **Precise source grounding with visual audit** — Every field links to exact character range; click any value to see source
- **End-to-end GPU OCR** — Single model vs traditional OCR + layout + parsing chain (no pipeline fragmentation)
- **Auditability for regulated industries** — Character-level provenance enables compliance verification
- **OCR cost efficiency** — <$0.01 per 1,000 pages vs $0.50-2.00 for proprietary OCR APIs
- **Parallel chunk processing** — 10-20x throughput improvement for long documents via concurrent LLM calls

**Defer (v2+):**
- **Real-time character-level updates** — WebSocket complexity; LLM extraction is batch-oriented
- **Bounding box extraction** — Requires LightOnOCR-2-1B-bbox variant and more memory
- **Custom model fine-tuning** — LightOnOCR fine-tuning support "coming soon"; few-shot examples are the customization mechanism
- **Extraction method comparison UI** — Start with explicit selection, add comparison mode later

**Anti-features (commonly requested but problematic):**
- **Always use LangExtract** — Docling is faster/cheaper for simple docs; offer dual paths with selection
- **Always use LightOnOCR** — Native PDFs don't need OCR; GPU cold start adds latency; auto-detect scanned vs digital
- **Universal extraction schema** — Different loan doc types have different structures; use document-type-specific few-shot examples

### Architecture Approach

**Dual extraction pipeline with API-based method selection.** Existing Docling + Gemini path continues to work unchanged. LangExtract path added as parallel alternative, selected via `?method=langextract` query parameter. Both paths store to the same PostgreSQL schema with extended SourceReference model (char_start/char_end nullable columns for backward compatibility). LightOnOCR deployed as separate Cloud Run GPU service, called only when `ocr_mode=auto` detects scanned document or `ocr_mode=force` is specified.

**Integration flow:**
1. Document upload with method selection (`docling` or `langextract`) and OCR mode (`auto`, `force`, `skip`)
2. Cloud Tasks queue async processing with method/OCR params in payload
3. If OCR needed: call LightOnOCR GPU service (separate Cloud Run instance with L4 GPU)
4. Route to extraction method: DoclingProcessor (v1) or LangExtractProcessor (v2)
5. Both methods produce BorrowerRecord with SourceReference, but LangExtract includes character offsets
6. Store to PostgreSQL with extraction_method metadata

**Major components:**
1. **ExtractionRouter** — Dispatches to Docling or LangExtract based on `?method` param
2. **LangExtractProcessor** — Wrapper around LangExtract API with few-shot examples from `examples/` directory
3. **LightOnOCR GPU Service** — Standalone FastAPI service with vLLM deployment, scales to zero when idle
4. **LightOnOCRClient** — HTTP client in backend for GPU OCR service communication
5. **Enhanced SourceReference** — Adds char_start/char_end nullable columns, maintains backward compatibility
6. **CloudBuild Deployment** — cloudbuild.yaml configs for backend, frontend, OCR service with gcloud CLI commands

**Key architectural patterns:**
- **Parallel paths, unified storage** — Different extraction methods converge at database layer
- **Optional enhancement** — Character offsets are nullable; v1 records work without migration
- **Smart routing** — Scanned document detection routes to GPU OCR only when needed
- **Separation of concerns** — OCR service is completely independent, communicates via HTTP
- **CloudBuild hybrid** — Application deployment via CloudBuild, infrastructure as one-time gcloud scripts

### Critical Pitfalls

**Top 5 pitfalls from research with prevention strategies:**

1. **Character Offset Mismatch Between Docling and LangExtract** — LangExtract provides offsets relative to raw text, but Docling's markdown export transforms text (formatting, whitespace, reordering). Offsets won't map to original document. **Prevention:** Use Docling's raw text mode (not markdown), store dual offsets (Docling-relative and document-relative), build offset translation layer, verify with substring matching at reported positions. **Address in Phase 1.**

2. **LangExtract Few-Shot Example Alignment Errors** — Extraction quality degrades if example `extraction_text` values aren't verbatim quotes from source or aren't in document order. Raises "Prompt alignment warnings." **Prevention:** Use exact verbatim text (never paraphrase), list extractions in document order, enable alignment warnings (don't suppress), test each example works independently. **Address in Phase 1.**

3. **GPU Service Cold Start Cost Explosion** — L4 GPU costs $0.67/hour when running. Scale-to-zero saves cost but has 5-19 second cold starts. Keeping min_instances=1 costs $485/month for sporadic usage. **Prevention:** Batch documents before spinning up GPU, disable zonal redundancy in dev/staging, route only scanned docs to GPU (native PDFs use Docling), implement scheduled warm-up before expected batches. **Address in Phase 2.**

4. **Terraform State Orphaning During CloudBuild Migration** — Migrating to CloudBuild creates resources via gcloud CLI. Terraform state doesn't know about CLI-created resources. Running `terraform apply` after migration could destroy production infrastructure. **Prevention:** Never run terraform after migration begins (revoke service account permissions), export Terraform state as documentation, tag resources with creation method, incremental migration one resource at a time, archive state file read-only. **Address in Phase 3.**

5. **Dual Extraction Method Inconsistent Results** — Same document produces different borrower counts or field values from Docling vs LangExtract. Users ask "which is correct?" **Prevention:** Define single BorrowerRecord format for both methods, add normalization layer post-extraction, create canonical test suite (same docs expected same results both methods), record extraction_method metadata, consider confidence comparison (use higher-confidence result). **Address in Phase 1.**

**Additional high-severity pitfalls:**
- **LightOnOCR Transformers Integration Immaturity** — Library only 4 months old, incomplete transformers support. Use vLLM deployment (official method) not direct transformers. Pin exact versions (vllm==0.11.1).
- **GPU Quota Denial** — Default quota is 3 GPUs per region. Increase requests take 24-48 hours. Request quota in Phase 0 before development starts.
- **SourceReference Schema Migration Complexity** — Adding char_start/char_end requires migration. Existing records don't have offsets. Use versioned schema (SourceReferenceV1 vs V2) or nullable fields with version metadata.

## Implications for Roadmap

Based on research, the v2.0 milestone should be structured around risk mitigation and incremental enhancement:

### Phase 1: LangExtract Integration with Character Offsets
**Rationale:** Highest-risk component (offset alignment, few-shot examples). Must establish foundation before dependent features.
**Delivers:** LangExtract extraction working with character-level source grounding, stored in database.
**Addresses:**
- Character-level offset tracking (FEATURES: table stakes)
- Few-shot example-based schema (FEATURES: table stakes)
- Enhanced SourceReference model with versioning
**Avoids:**
- Character offset mismatch (PITFALL #1) — offset translation layer
- Few-shot example alignment errors (PITFALL #2) — validated example corpus
- Dual method inconsistency (PITFALL #5) — normalization layer
**Research flag:** SKIP detailed research — LangExtract API well-documented, focus on integration testing with real loan docs.

### Phase 2: LightOnOCR GPU Service Deployment
**Rationale:** Independent of LangExtract (can develop in parallel). High complexity due to GPU configuration and cost management.
**Delivers:** Dedicated Cloud Run GPU service with LightOnOCR model, accessible via HTTP API.
**Uses:**
- LightOnOCR-2-1B model (STACK)
- vLLM deployment pattern (STACK)
- Cloud Run L4 GPU configuration (STACK)
**Implements:**
- Scanned document detection and routing logic
- Image preprocessing pipeline (1540px normalization)
- Cost monitoring and GPU scaling controls
**Avoids:**
- GPU cold start cost explosion (PITFALL #3) — smart routing, scanned-only
- LightOnOCR immaturity (PITFALL #6) — vLLM deployment, not direct transformers
- GPU quota denial (PITFALL #9) — quota request in Phase 0
**Research flag:** SKIP detailed research — vLLM deployment well-documented in Cloud Run GPU codelabs.

### Phase 3: CloudBuild Deployment Migration
**Rationale:** Can proceed once services are working. Lower risk than LangExtract/OCR integration.
**Delivers:** CloudBuild configs for all services, gcloud CLI deployment scripts, Terraform deprecation.
**Uses:**
- cloudbuild.yaml for backend, frontend, OCR service (STACK)
- gcloud run deploy commands (STACK)
- Artifact Registry, Secret Manager (STACK)
**Implements:**
- CloudBuild service account with minimal permissions
- Deployment rollback capability
- Incremental migration (one environment at a time)
**Avoids:**
- Terraform state orphaning (PITFALL #4) — explicit archival, revoke permissions
- CloudBuild YAML type coercion (PITFALL #8) — validated template
- Service account permission gaps (PITFALL #14) — permissions-first approach
**Research flag:** SKIP detailed research — CloudBuild deployment to Cloud Run is standard pattern.

### Phase 4: API Enhancement and Method Selection
**Rationale:** Builds on completed extraction methods. Lowest risk, highest user-facing value.
**Delivers:** API parameters for method selection, validation, frontend integration.
**Addresses:**
- Extraction method selection API (FEATURES: table stakes)
- HTML visualization generation (FEATURES: table stakes)
- Method metadata in responses
**Implements:**
- Query param validation (`method` + `ocr` combinations)
- Valid combination enforcement
- Dashboard visualization viewer (embed LangExtract HTML)
**Avoids:**
- API method parameter conflicts (PITFALL #12) — explicit valid combination enum
**Research flag:** SKIP detailed research — standard FastAPI parameter handling.

### Phase Ordering Rationale

**Why LangExtract first:** Highest technical risk due to offset alignment complexity and few-shot example quality dependency. Establishes foundation for dual-pipeline architecture. Must validate offset translation layer before building dependent features.

**Why LightOnOCR second:** Independent of LangExtract (parallel development possible), but GPU deployment complexity and cost management require dedicated focus. Can proceed in parallel with Phase 1 if resources allow.

**Why CloudBuild third:** Depends on services being functional (can't deploy what doesn't work). Lower risk than integration work. Migration requires careful Terraform state management but is procedural, not exploratory.

**Why API enhancement last:** User-facing feature that ties together backend capabilities. Requires completed extraction methods to be useful. Lowest technical risk, highest user-facing value.

### Research Flags

**Phases likely needing deeper research during planning:**
- **None** — All phases involve well-documented technologies with official examples. LangExtract, vLLM, CloudBuild all have high-quality documentation and codelabs.

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (LangExtract):** Standard Python library integration; focus on testing with real loan docs
- **Phase 2 (LightOnOCR):** Standard vLLM deployment pattern; focus on cost optimization
- **Phase 3 (CloudBuild):** Standard CloudBuild to Cloud Run deployment; focus on Terraform migration safety
- **Phase 4 (API Enhancement):** Standard FastAPI parameter handling; focus on UX

**Phase 0 (Pre-Development Setup) required:**
- Request GPU quota increase for Cloud Run L4 (24-48 hour turnaround)
- Archive Terraform state and document current infrastructure
- Validate LightOnOCR loads in vLLM locally
- Create CloudBuild service account with permissions

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All technologies verified with official sources; LangExtract (GitHub), LightOnOCR (HuggingFace), CloudBuild (Google Cloud docs) |
| Features | HIGH | LangExtract capabilities documented in release announcement; LightOnOCR benchmarked on OlmOCR-Bench; CloudBuild patterns established |
| Architecture | HIGH | Integration patterns validated in community examples (Docling + LangExtract integration blog, vLLM Cloud Run codelab) |
| Pitfalls | MEDIUM | LangExtract only 4 months old with limited production experience reports; offset alignment warnings from integration blogs, not production postmortems |

**Overall confidence:** HIGH

The research is based on official documentation and verified sources. The main limitation is LangExtract's newness (released July 2025) — fewer production war stories than mature libraries. However, it's from Google with active development and clear documentation. LightOnOCR is even newer (October 2025) but transformers integration issues are documented and vLLM deployment is the official workaround.

### Gaps to Address

**Gaps identified during research:**

- **LangExtract offset behavior with Docling markdown** — Documentation shows examples with plain text, not with Docling's markdown export. The integration blog (dev.to) confirms offset alignment is a concern but doesn't provide complete solution. **Handling:** Validate offset translation layer with real loan docs in Phase 1 testing; may need to iterate on Docling text extraction mode.

- **LightOnOCR cold start time variability** — Documentation gives 5-19 second range for cold starts, but factors affecting this range aren't fully documented. **Handling:** Benchmark in Phase 2 with different model sizes and configurations; establish SLO based on actual measurements.

- **CloudBuild cost for large images** — Build time costs depend on image size and build frequency. Backend + OCR service images could be 2GB+. **Handling:** Monitor build costs in Phase 3; consider build caching strategies if costs exceed expectations.

- **Few-shot example count requirements** — LangExtract documentation shows 2-5 examples but doesn't specify how to determine optimal count for loan document complexity. **Handling:** Start with 3 examples in Phase 1, measure extraction quality, iterate based on recall/precision metrics.

## Sources

### Primary (HIGH confidence)
- [LangExtract GitHub](https://github.com/google/langextract) — v1.1.1, official API documentation, example code
- [LangExtract PyPI](https://pypi.org/project/langextract/) — v1.1.1, Python >=3.10 requirement
- [Google Developers Blog: Introducing LangExtract](https://developers.googleblog.com/introducing-langextract-a-gemini-powered-information-extraction-library/) — Feature overview, architecture
- [LightOnOCR-2-1B HuggingFace](https://huggingface.co/lightonai/LightOnOCR-2-1B) — Model card, deployment instructions, benchmarks
- [Cloud Run GPU Documentation](https://docs.cloud.google.com/run/docs/configuring/services/gpu) — L4 configuration, pricing, requirements
- [CloudBuild Deploy to Cloud Run](https://docs.cloud.google.com/build/docs/deploying-builds/deploy-cloud-run) — Official deployment patterns
- [vLLM Cloud Run Codelab](https://codelabs.developers.google.com/codelabs/how-to-run-inference-cloud-run-gpu-vllm) — GPU deployment with vLLM

### Secondary (MEDIUM confidence)
- [Docling + LangExtract Integration](https://dev.to/_aparna_pradhan_/the-perfect-extraction-unlocking-unstructured-data-with-docling-langextract-1j3b) — Integration challenges, offset alignment
- [LangExtract Critical Review](https://medium.com/@meghanaharishankara/googles-langextract-a-critical-review-from-the-trenches-e41fae3e03b0) — Real-world usage experience
- [LightOnOCR Blog](https://www.lighton.ai/lighton-blogs/making-knowledge-machine-readable) — Performance details
- [DataCamp LangExtract Tutorial](https://www.datacamp.com/tutorial/langextract) — Best practices for few-shot examples
- [Cloud Run GPU GA Blog](https://cloud.google.com/blog/products/serverless/cloud-run-gpus-are-now-generally-available) — Cost optimization strategies
- [Terraform Migration Guide](https://scalr.com/guides/platform-engineers-guide-to-migrating-off-terraform-cloud-enterprise) — State management best practices

### Tertiary (LOW confidence)
- LightOnOCR GPU memory estimates for L4 (extrapolated from H100 benchmarks) — needs validation
- Cold start times vary by model size and container configuration — needs measurement
- vLLM optimization settings may need tuning for LightOnOCR specifically — needs experimentation

---
*Research completed: 2026-01-24*
*Ready for roadmap: yes*
