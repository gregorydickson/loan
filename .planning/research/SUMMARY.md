# Project Research Summary

**Project:** Loan Document Extraction System
**Domain:** AI-powered document extraction for financial/loan documents
**Researched:** 2026-01-23
**Confidence:** HIGH

## Executive Summary

This loan document extraction system leverages modern AI infrastructure to convert unstructured financial documents (PDFs, scanned images) into structured borrower records. Industry best practices establish a **hybrid architecture**: Docling handles faithful text extraction while Gemini 3.0 provides semantic understanding with native structured output. This separation prevents the critical hallucination problem where LLMs fabricate financial data.

The recommended approach uses **FastAPI** for async processing, **PostgreSQL** with full source attribution, **Cloud Run** for serverless deployment, and **Next.js 15** with shadcn/ui for the frontend. The key differentiator for portfolio evaluation is comprehensive traceability—every extracted field links to its source document location, building trust and enabling audit trails. Cost optimization through document complexity classification routes 80-90% of documents to cheaper Flash models while reserving Pro for truly complex cases.

The primary risk is **data hallucination** at scale—LLMs are trained to generate plausible content, not faithful extraction. Mitigation requires Docling for text extraction (never raw PDFs to LLMs), hybrid validation combining Pydantic schemas with regex checks for financial fields, and mandatory source attribution with verification. The 3-day timeline demands ruthless scope control: core extraction working by end of day 1, quality/validation systems on day 2, polish and deployment on day 3.

## Key Findings

### Recommended Stack

The stack leverages production-proven technologies optimized for document extraction use cases. **Docling** (IBM Research, v2.70.0) handles document-to-text conversion with layout understanding and automatic OCR, eliminating the need to send raw PDFs to LLMs. **Gemini 3.0** provides native structured output with Pydantic models, removing separate parsing/validation layers. The architecture is fully async (FastAPI + asyncpg + SQLAlchemy 2.0) for scalability, with Cloud Run providing serverless deployment.

**Core technologies:**
- **Docling 2.70.0**: Document parsing (PDF/DOCX/images) — production-grade layout analysis, table extraction, native LangChain integration
- **google-genai 1.60.0**: Gemini 3.0 client — native Pydantic structured output, replaces deprecated SDK
- **FastAPI 0.128.0**: Async REST API — Pydantic validation, auto-generated OpenAPI docs, 15-20k req/s performance
- **SQLAlchemy 2.0.46 + asyncpg**: Async ORM — full async support, battle-tested PostgreSQL integration
- **Next.js 15.5**: Frontend framework — App Router with React Server Components, TypeScript-first
- **Cloud Run + Cloud SQL + GCS**: GCP infrastructure — serverless auto-scaling, managed database, durable storage

**Key insight from research:** Never use LLMs for OCR. Docling extracts text faithfully; Gemini reasons about that text. This separation prevents the catastrophic hallucination problem where LLMs invent financial figures.

### Expected Features

Production document extraction systems have a well-defined feature landscape. For a 3-day portfolio project, the strategy is implementing table stakes thoroughly while adding 1-2 high-visibility differentiators that showcase production readiness.

**Must have (table stakes):**
- **Multi-format document ingestion** — PDFs, DOCX, scanned images via Docling
- **Structured data extraction** — BorrowerRecord schema with name, address, income, account numbers
- **Source attribution/traceability** — Link each extracted field to page, section, text snippet
- **Confidence scoring** — Flag uncertain extractions (PRD formula: 0.5 base + completeness bonuses)
- **Document status tracking** — PENDING → PROCESSING → COMPLETED/FAILED lifecycle
- **Search/query interface** — Find borrowers by name, account number, loan number
- **Error handling & recovery** — Graceful failures, retry logic for LLM calls
- **REST API with OpenAPI docs** — FastAPI auto-generates, demonstrates clean endpoint design

**Should have (competitive differentiators):**
- **Architecture visualization in UI** — Interactive system diagram, pipeline flow (PRD bonus deliverable)
- **Human-in-the-loop review workflow** — Flag low-confidence extractions (<0.7) for manual review
- **Income trend visualization** — Recharts timeline showing income history
- **Model selection intelligence** — Auto-route to Flash vs Pro based on document complexity
- **Visual source linking** — Click extracted field to see highlighted source in document (high complexity, impressive when done)

**Defer (v2+):**
- **Cross-document entity resolution** — Merge same borrower across documents (fuzzy matching complexity)
- **Real-time streaming extraction** — WebSocket overhead not justified for demo
- **Full PII encryption** — Use disclaimers for portfolio, note production requirements
- **Multi-tenant architecture** — Single-tenant sufficient, document multi-tenant patterns
- **Custom model fine-tuning** — Use well-crafted prompts with structured output instead

**Portfolio-specific insight:** Architecture visualization page has very high evaluator impact for low technical risk—mostly static content with Mermaid diagrams. Income timeline charts using Recharts look impressive but are straightforward to implement.

### Architecture Approach

Industry practice establishes a **modular, multi-stage pipeline architecture** separating ingestion, processing, extraction, validation, and storage. Hybrid architectures (LLM + deterministic validation) outperform purely AI-driven solutions. The key pattern is **async processing with status tracking**—upload returns immediately, processing happens via Cloud Tasks queue, client polls for results.

**Major components:**
1. **API Layer (FastAPI)** — HTTP endpoints, request validation, response formatting; thin layer with no business logic
2. **Ingestion Service (Docling)** — Document intake, multi-format parsing, layout analysis; produces structured DoclingDocument
3. **Extraction Service (Gemini)** — LLM orchestration with structured output, prompt management, complexity-based model routing
4. **Validation Service** — Hybrid validation combining Pydantic schemas with deterministic regex checks for critical fields (SSN, loan numbers)
5. **Storage Service (PostgreSQL)** — Repository pattern isolating database, stores borrowers/extractions/income_history/source_links
6. **Query Service** — Borrower lookup, document search, source attribution resolution

**Data flow:** Client uploads → store in GCS → enqueue Cloud Task → Docling extracts text → complexity classifier routes to Flash/Pro → Gemini extracts with structured output → hybrid validation → persist with source links → client queries results.

**Key architectural patterns from research:**
- **Hybrid LLM + Deterministic Validation**: Combine semantic extraction with regex validation for critical fields
- **Source Attribution Chain**: Every field links to document_id, page_number, bounding_box, text_snippet
- **Dynamic Model Selection**: Route documents to Flash/Pro based on complexity classifier (cost optimization)
- **Async Processing with Status Tracking**: Separate upload (sync) from processing (async) with polling

**Anti-patterns to avoid:** Synchronous processing (causes timeouts), trusting LLM output without validation (hallucination), losing source attribution (breaks trust), monolithic prompts (hard to debug), ignoring document quality signals (poor OCR needs different handling).

### Critical Pitfalls

The most dangerous pitfalls cause project failure, data corruption, or complete rewrites. All must be addressed in Phases 1-2.

1. **Using LLMs as OCR (The Faithfulness Trap)** — LLMs hallucinate plausible-looking data that doesn't exist. For $38M loan amounts, LLM might output $88M. **Prevention:** Use Docling for extraction, Gemini for reasoning. Never send raw PDFs to LLMs. Implement grounding validation linking every value to source text.

2. **Source Attribution Theater (Fake Provenance)** — System claims to track sources but LLM invents page numbers and snippets. Research shows 50-90% of LLM citations are not fully supported. **Prevention:** Track which text chunk produced each extraction, verify snippets fuzzy-match actual document text, validate page numbers exist.

3. **Structured Output Silent Failures** — Gemini returns `None` instead of structured output when response exceeds `max_output_tokens`. API returns 200 but `response.parsed` is `None`. No error raised—data silently lost. **Prevention:** Set generous max_output_tokens (8192+ for loan docs), explicit None checks, retry with chunking on None response.

4. **Numeric Extraction Catastrophe** — Income figures, loan amounts, account numbers extracted incorrectly. OCR mistakes (0/O/D confusion), format ambiguity (1,234 vs 1.234), unit confusion (monthly vs annual). **Prevention:** Explicit format instructions in prompts, cross-validation rules (monthly × 12 ≈ annual), range checks, require unit specification, preserve original text.

5. **"It Works on Test Docs" Trap** — Perfect on clean PDFs, fails on real loan packages with scanned images, stamps, handwriting, rotated pages. Docling can silently fail returning empty markdown. **Prevention:** Test with production-like documents on day 1, include ugly test cases, implement quality scoring, graceful degradation.

**Timeline-specific pitfall:** **Scope Creep Death Spiral** — adding features daily without removing others leads to incomplete extraction, incomplete UI, incomplete everything. 52% of projects experience scope creep with 43% significantly impacting success. **Prevention:** Write MVP scope first hour, maintain "Not in v1" list, time-box features to 2 hours max, daily checkpoint on day 3 ship readiness.

## Implications for Roadmap

Based on component dependencies and pitfall mitigation requirements, I recommend a 5-phase roadmap structure:

### Phase 1: Foundation & Document Ingestion
**Rationale:** Establish core infrastructure before extraction logic. Docling integration must happen first to prevent LLM-as-OCR pitfall. Database schema with source attribution must be designed upfront—retrofitting provenance is painful.

**Delivers:** Working document upload → GCS storage → Docling processing pipeline with status tracking. Database schema with borrowers/extractions/source_links tables.

**Addresses features:**
- Multi-format document ingestion (FEATURES.md table stakes)
- Document status tracking lifecycle
- Storage foundation for source attribution

**Avoids pitfalls:**
- Pitfall 1 (LLM as OCR) — establishes Docling as extraction layer
- Pitfall 11 (Docling silent failures) — add validation checks upfront
- Pitfall 5 (test doc trap) — include real documents in integration tests

**Research flag:** LOW — Docling and FastAPI are well-documented with clear patterns.

### Phase 2: LLM Extraction Engine
**Rationale:** Core value proposition depends on extraction working correctly. Build LLM client with all safety measures (None handling, rate limiting, retries) from day one. Complexity classifier enables cost optimization demo.

**Delivers:** Gemini client with structured output, prompt templates for loan documents, complexity classifier routing to Flash/Pro, extraction orchestration connecting Docling → Gemini → results.

**Uses stack:**
- google-genai 1.60.0 with Pydantic structured output
- tenacity for exponential backoff retries
- Complexity classifier pattern from ARCHITECTURE.md

**Implements:** Extraction Service component from architecture

**Avoids pitfalls:**
- Pitfall 3 (structured output None) — explicit None handling in client
- Pitfall 6 (cost explosion) — development caching, model tiering
- Pitfall 8 (rate limiting) — client-side rate limiting with jitter
- Pitfall 7 (non-deterministic tests) — record/replay for integration tests

**Research flag:** LOW — Gemini structured output is officially documented, patterns are established.

### Phase 3: Validation & Source Attribution
**Rationale:** Validation prevents bad data from reaching storage. Source attribution is the key portfolio differentiator—demonstrates production thinking and enables trust.

**Delivers:** Hybrid validation service (Pydantic + regex), confidence scoring implementation, source links storage (page_number, text_snippet, bounding_box), field-level provenance tracking.

**Addresses features:**
- Source attribution/traceability (FEATURES.md table stakes, critical when done well)
- Confidence scoring with PRD formula
- Basic validation (SSN, phone, zip formats)

**Implements:** Validation Service component, completes Storage Service with source_links

**Avoids pitfalls:**
- Pitfall 2 (source attribution theater) — verify snippets match document text
- Pitfall 4 (numeric catastrophe) — cross-validation rules, range checks
- Pitfall 9 (deduplication failures) — multi-signal matching (SSN definitive, name+address fuzzy)

**Research flag:** MEDIUM — Source attribution verification requires careful design. Test thoroughly with real documents.

### Phase 4: Query API & Search
**Rationale:** Extraction is useless without query capabilities. REST API with OpenAPI docs demonstrates clean endpoint design. Search functionality is table stakes for document systems.

**Delivers:** Borrower query endpoints, document search by name/account/loan number, source link resolution, pagination, filtering by confidence level.

**Addresses features:**
- Search/query interface (FEATURES.md table stakes)
- REST API with OpenAPI docs
- Error handling & recovery

**Implements:** Query Service component, completes API Layer

**Avoids pitfalls:**
- Performance trap: Unbounded result sets — implement pagination from start

**Research flag:** LOW — REST API patterns are standard, FastAPI documentation is comprehensive.

### Phase 5: Frontend Dashboard & Architecture Visualization
**Rationale:** Portfolio requires visible demo. Architecture visualization is PRD bonus deliverable with high evaluator impact for low technical risk.

**Delivers:** Next.js dashboard with document/borrower lists, borrower detail view with source references, income timeline visualization (Recharts), architecture pages (system diagram, pipeline flow, scaling strategy), confidence badges, processing status indicators.

**Addresses features:**
- Architecture visualization in UI (FEATURES.md P1 for portfolio)
- Income trend visualization (FEATURES.md P2, high impact)
- Human-in-the-loop visual indicators (flag confidence <0.7)

**Uses stack:**
- Next.js 15 with App Router
- shadcn/ui components
- Recharts for income timeline
- Mermaid diagrams for architecture

**Avoids pitfalls:**
- Pitfall 13 (premature infrastructure) — core extraction working before UI
- Pitfall 12 (scope creep) — focus on MVP, defer complex features like visual source linking

**Research flag:** LOW — Frontend patterns are well-established, shadcn/ui documentation is excellent.

### Phase Ordering Rationale

**Sequential dependencies dictate order:**
1. Foundation must come first — database schema changes are expensive later (Pitfall 10: schema lock-in)
2. Docling before LLM — prevents LLM-as-OCR anti-pattern, established in Phase 1
3. Extraction before validation — nothing to validate without extraction
4. Storage before query — nothing to query without persisted data
5. Frontend last — requires stable API contracts, demonstrates working extraction

**Groupings based on architecture patterns:**
- Phases 1-2 form the **ingestion → extraction pipeline** (async processing pattern)
- Phase 3 adds **quality assurance layer** (hybrid validation pattern)
- Phase 4 exposes **data access layer** (repository pattern)
- Phase 5 provides **presentation layer** (decoupled from backend)

**Pitfall mitigation strategy:**
- **Day 1 focus (Phases 1-2):** Avoid critical pitfalls (1, 3, 4, 5, 11) — core extraction working
- **Day 2 focus (Phases 3-4):** Avoid quality pitfalls (2, 6, 7, 8) — validation and API
- **Day 3 focus (Phase 5):** Avoid timeline pitfalls (12, 13) — polish and deploy

**What to explicitly defer to v2:**
- Visual source linking (high complexity, defer per FEATURES.md)
- Cross-document entity resolution (complex fuzzy matching)
- Batch upload processing
- Real-time streaming updates
- Comprehensive audit logging
- Full PII encryption (use disclaimers, note production requirements)

### Research Flags

**Phases needing deeper research during planning:**
- **Phase 3 (Validation):** Source attribution verification patterns need careful design. Research how to efficiently verify text snippets match document content without re-processing. Consider fuzzy matching libraries.

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (Foundation):** Database schemas, FastAPI setup, Docling integration are well-documented
- **Phase 2 (LLM Extraction):** Gemini structured output, retry patterns are officially documented
- **Phase 4 (Query API):** REST API patterns, pagination, filtering are standard
- **Phase 5 (Frontend):** Next.js, shadcn/ui, Recharts have comprehensive documentation

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All recommendations from official documentation (Docling PyPI, Gemini API docs, FastAPI release notes). Versions verified as of Jan 2026. Python 3.10+ requirement confirmed. |
| Features | HIGH | Based on analysis of production IDP platforms (Docsumo, Amazon Textract, Infrrd) and multiple industry sources. Table stakes vs differentiators validated across 10+ sources. Portfolio recommendations from recruiter expectation research. |
| Architecture | HIGH | Patterns verified in official docs (Gemini structured output, FastAPI async, SQLAlchemy async). Pipeline architecture validated across multiple IDP implementation guides. Anti-patterns identified from real project failures. |
| Pitfalls | HIGH | Critical pitfalls verified from academic research (SafePassage paper), official issue trackers (Gemini GitHub), and practitioner blog posts with specific failure examples. Timeline pitfalls from project management research (scope creep statistics). |

**Overall confidence:** HIGH

Research is grounded in official documentation, verified with multiple authoritative sources, and cross-checked against real-world implementations. The recommended stack uses stable, production-proven technologies. Architecture patterns are established industry practice for document extraction systems.

### Gaps to Address

**During Phase 3 planning (Validation):**
- **Source attribution verification performance** — Need to determine if fuzzy matching text snippets against full document is performant enough, or if we need to store chunk indices. Consider testing with RapidFuzz library for efficient fuzzy matching at scale.

**During Phase 2 implementation:**
- **Complexity classifier calibration** — The heuristics in ARCHITECTURE.md (page count, tables, handwriting detection) are reasonable but may need tuning based on actual document corpus. Plan to instrument classifier decisions and analyze routing accuracy after first 50 documents processed.

**During Phase 5 (Frontend):**
- **Visual source linking scope** — Research marked this as high complexity (FEATURES.md). If time permits on day 3, explore lightweight implementation showing source snippets without full PDF highlight capability. Defer full visual linking to v2 if scope risk emerges.

**Overall gap mitigation strategy:**
- Accept research uncertainty in non-critical areas (classifier tuning, performance optimization)
- Focus on critical path (extraction accuracy, source attribution correctness)
- Build instrumentation early to validate research assumptions with real data
- Plan fallbacks (simpler attribution if performance is issue, basic classifier if tuning needed)

## Sources

### Primary (HIGH confidence)

**Stack research:**
- [Docling PyPI](https://pypi.org/project/docling/) — v2.70.0 verified, Python 3.10+ requirement
- [google-genai PyPI](https://pypi.org/project/google-genai/) — v1.60.0, replaces deprecated SDK
- [Gemini API Structured Output](https://ai.google.dev/gemini-api/docs/structured-output) — Native Pydantic support
- [FastAPI Documentation](https://fastapi.tiangolo.com/) — v0.128.0, async patterns
- [SQLAlchemy Async Docs](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) — asyncpg integration

**Features research:**
- [IDP Market Report 2025 - Docsumo](https://www.docsumo.com/blogs/intelligent-document-processing/intelligent-document-processing-market-report-2025)
- [IDP in Lending - Docsumo](https://www.docsumo.com/blogs/intelligent-document-processing/lending-industry)
- [Amazon Textract Lending Docs](https://docs.aws.amazon.com/textract/latest/dg/lending-document-classification-extraction.html)

**Architecture research:**
- [Docling GitHub Repository](https://github.com/docling-project/docling) — Architecture and processing pipeline
- [Gemini API Documentation](https://ai.google.dev/gemini-api/docs/gemini-3) — Model capabilities
- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/) — Async processing

**Pitfalls research:**
- [Don't Use LLMs as OCR - Medium](https://medium.com/@martia_es/dont-use-llms-as-ocr-lessons-learned-from-extracting-complex-documents-db2d1fafcdfb)
- [SafePassage: High-Fidelity Information Extraction](https://arxiv.org/html/2510.00276) — Academic research on LLM faithfulness
- [SourceCheckup: Citation Assessment](https://www.nature.com/articles/s41467-025-58551-6) — LLM attribution accuracy
- [Gemini Structured Output Issue](https://github.com/googleapis/python-genai/issues/1039) — None response behavior

### Secondary (MEDIUM confidence)

**Features research:**
- [AI Mortgage Document Processing - Ascendix](https://ascendixtech.com/ai-mortgage-document-processing/)
- [HITL for AI Document Processing - Unstract](https://unstract.com/blog/human-in-the-loop-hitl-for-ai-document-processing/)
- [ML Portfolio Projects 2025 - Medium](https://medium.com/@santosh.rout.cr7/ml-engineer-portfolio-projects-that-will-get-you-hired-in-2025-d1f2e20d6c79)

**Architecture research:**
- [LLMs for PDF Extraction - Unstract](https://unstract.com/blog/comparing-approaches-for-using-llms-for-structured-data-extraction-from-pdfs/)
- [Data Extraction in Lending - Docsumo](https://www.docsumo.com/blogs/data-extraction/lending-industry)

**Pitfalls research:**
- [LLM Cost Optimization 2025 - FutureAGI](https://futureagi.com/blogs/llm-cost-optimization-2025)
- [Testing LLM Applications - Langfuse](https://langfuse.com/blog/2025-10-21-testing-llm-applications)
- [Scope Creep in Software Projects - Medium](https://medium.com/@denismwg/navigating-scope-creep-in-software-projects-5-strategies-that-work-ec8a35684fdb)

### Tertiary (LOW confidence - verify before use)

- Specific token counts per document type — varies significantly by document characteristics
- Exact accuracy comparisons between OCR methods — benchmarks show wide variance
- Cost projections at scale — depends heavily on actual document complexity distribution

---
*Research completed: 2026-01-23*
*Ready for roadmap: yes*
