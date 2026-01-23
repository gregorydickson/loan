# Feature Research: Loan Document Extraction System

**Domain:** AI-powered loan document data extraction
**Researched:** 2026-01-23
**Confidence:** HIGH (verified with multiple industry sources)

## Executive Summary

Document extraction systems for financial/loan documents have a well-established feature landscape. For a **3-day portfolio project** demonstrating production-ready practices, the key is to implement table stakes features thoroughly while adding 1-2 high-visibility differentiators that showcase technical sophistication without overcomplicating the architecture.

The PRD already captures most table stakes. This research identifies **what makes features production-ready** vs merely functional, and highlights **portfolio-specific optimizations** that maximize impact for evaluators.

---

## Feature Landscape

### Table Stakes (Users/Evaluators Expect These)

Features users assume exist. Missing these = product feels incomplete or amateurish.

| Feature | Why Expected | Complexity | Priority | Notes |
|---------|--------------|------------|----------|-------|
| **Multi-format document ingestion** | Loan documents come as PDFs, scans, images | MEDIUM | P1 | PRD covers via Docling. Support PDF, DOCX, images. Scanned document handling is critical. |
| **Structured data extraction** | Core value proposition | HIGH | P1 | Extract borrower name, address, income, account numbers. PRD defines BorrowerRecord schema. |
| **Source attribution/traceability** | Auditors and evaluators need to verify extractions | MEDIUM | P1 | **Critical differentiator when done well.** Link each extracted field to page, section, snippet. |
| **Confidence scoring** | Production systems flag uncertain extractions | MEDIUM | P1 | Score each extraction. PRD formula: 0.5 base + field completeness bonuses. |
| **Document status tracking** | Users need to know processing state | LOW | P1 | PENDING -> PROCESSING -> COMPLETED/FAILED states. Show in UI. |
| **Search/query interface** | Users need to find borrowers/documents | MEDIUM | P1 | Search by name, account number, loan number. Basic filtering and pagination. |
| **Error handling & recovery** | Production systems don't crash silently | MEDIUM | P1 | Graceful failures, meaningful error messages, retry logic for LLM calls. |
| **REST API** | Standard interface for integration | MEDIUM | P1 | OpenAPI/Swagger docs auto-generated. Clean endpoint design. |
| **Basic validation** | Extracted data should be format-valid | LOW | P1 | SSN format, phone format, zip code format validation. |

### Differentiators (Competitive Advantage / Portfolio Standouts)

Features that set the product apart. These demonstrate production-readiness and technical sophistication.

| Feature | Value Proposition | Complexity | Priority | Notes |
|---------|-------------------|------------|----------|-------|
| **Visual source linking in UI** | Click extracted field -> see highlighted source in document | HIGH | P2 | **Huge portfolio impact.** Evaluators love seeing evidence trails. Requires storing bounding boxes or text positions. |
| **Human-in-the-loop review workflow** | Low-confidence extractions flagged for manual review | MEDIUM | P2 | Flag records with confidence < 0.7. Show review queue in UI. Demonstrates production thinking. |
| **Cross-document entity resolution** | Same borrower across multiple docs merged correctly | HIGH | P3 | Dedupe by SSN/account match, fuzzy name matching. Complex but impressive when done. |
| **Architecture visualization in UI** | Interactive system diagram, pipeline flow, scaling strategy | MEDIUM | P1* | **PRD requires this as bonus.** High-impact for evaluators. Low technical risk. |
| **Document classification** | Auto-categorize document types (W-2, tax return, bank statement) | MEDIUM | P3 | Useful for routing but not core to demo. Could add later. |
| **Batch processing with progress** | Upload multiple docs, see aggregate progress | MEDIUM | P3 | Nice for demo but adds UI complexity. |
| **Income trend analysis** | Visualize income history over time | LOW | P2 | Recharts integration per PRD. Simple but looks impressive. |
| **Model selection intelligence** | Auto-choose Flash vs Pro based on document complexity | MEDIUM | P2 | PRD has ComplexityClassifier. Good demo of cost optimization thinking. |
| **Audit logging** | Immutable log of all processing decisions | MEDIUM | P3 | Production-critical but less visible in demo. |

*Priority P1 for architecture visualization because PRD lists high-fidelity UI as bonus deliverable.

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems for a 3-day portfolio project.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Real-time streaming extraction** | "Watch extraction happen live" | Adds WebSocket complexity, minimal demo value, LLM calls are batched anyway | Polling-based status updates are fine |
| **Full PII encryption at rest** | "Handle sensitive data properly" | 3-day scope, adds key management complexity, portfolio disclaimers are acceptable | Note PII considerations in docs, use disclaimer |
| **Multi-tenant architecture** | "Production would need this" | Massive scope creep, unnecessary for demo | Single-tenant with note about multi-tenant patterns |
| **Custom model fine-tuning** | "Better extraction accuracy" | Requires training data, time, infrastructure | Use well-crafted prompts with structured output |
| **Complex workflow orchestration** | "Enterprise-grade processing" | Celery/temporal adds operational complexity | Cloud Tasks for async, simple status machine |
| **Document versioning** | "Track document updates" | Adds complexity to data model, rare use case for extraction | Simple overwrite, note limitation |
| **Full RBAC/permissions** | "Production security" | Auth adds days of work | API keys or basic auth, note production would need RBAC |
| **LLM as OCR** | "Just send image to GPT/Gemini" | LLMs hallucinate numbers, miss table structure | Docling for OCR, LLM for reasoning |
| **Real-time chat with documents** | "RAG-style Q&A" | Different product entirely, scope creep | Stick to structured extraction |

---

## Feature Dependencies

```
[Document Ingestion]
    |
    +-- requires --> [Multi-format parsing (Docling)]
    |
    v
[Text/Table Extraction]
    |
    +-- requires --> [Document processing complete]
    |
    v
[LLM Extraction]
    |
    +-- requires --> [Extracted text available]
    +-- requires --> [Pydantic schemas defined]
    |
    v
[Source Attribution] <-- requires -- [Page/section metadata from parsing]
    |
    v
[Confidence Scoring] <-- requires -- [Extraction complete]
    |
    v
[Validation] <-- requires -- [Extracted records]
    |
    v
[Storage]
    |
    +-- requires --> [Database schema]
    +-- requires --> [Validated records]
    |
    v
[Search/Query API]
    |
    +-- requires --> [Stored records]
    |
    v
[UI Visualization]
    |
    +-- requires --> [API endpoints]
    +-- enhances --> [Source Attribution] (visual linking)
```

### Dependency Notes

- **Docling before LLM**: Never skip OCR. LLMs hallucinate numbers and miss table structure. Docling extracts text faithfully, LLM reasons about it.
- **Source Attribution early**: Track page/section during parsing, not as afterthought. Retrofitting is painful.
- **Confidence Scoring at extraction**: Calculate during LLM response processing, not in separate pass.
- **Validation before storage**: Catch format errors before persisting bad data.
- **UI depends on stable API**: Design API contracts before building frontend. OpenAPI spec helps parallel work.

---

## MVP Definition

### Launch With (Day 1-2 Core)

Minimum viable product that proves the concept works.

- [x] **Document upload endpoint** - Accept PDF/DOCX/images, store in GCS
- [x] **Docling processing** - Convert to structured text with table preservation
- [x] **LLM extraction with Gemini** - Extract BorrowerRecord fields with structured output
- [x] **Source attribution** - Track document_id, page_number, section for each extraction
- [x] **Confidence scoring** - Implement formula from PRD
- [x] **PostgreSQL storage** - Borrowers, documents, income records, source references
- [x] **Basic REST API** - CRUD for documents and borrowers, search endpoint
- [x] **Basic validation** - Format validation for SSN, phone, zip

### Add After Core Works (Day 2-3 Polish)

Features to add once core is stable.

- [ ] **Frontend dashboard** - Document list, borrower list, status indicators
- [ ] **Borrower detail view** - Show all extracted data with source references
- [ ] **Architecture pages** - System diagram, pipeline flow, scaling strategy
- [ ] **Low-confidence flagging** - Visual indicator for records needing review
- [ ] **Income timeline visualization** - Recharts component showing income history
- [ ] **Search with filters** - Filter by name, account, confidence level
- [ ] **Document detail with extraction preview** - Show what was extracted from each doc

### Future Consideration (Post-Demo)

Features to defer until project timeline extends.

- [ ] **Visual source linking** - Click field to see highlighted source text (complex UI work)
- [ ] **Entity resolution/deduplication** - Merge same borrower across documents
- [ ] **Batch upload** - Upload ZIP of multiple documents
- [ ] **Export functionality** - CSV/JSON export of extracted data
- [ ] **Webhook notifications** - Notify external systems on processing complete
- [ ] **Comprehensive audit logging** - Full processing decision trail

---

## Feature Prioritization Matrix

| Feature | User/Evaluator Value | Implementation Cost | Priority | Rationale |
|---------|---------------------|---------------------|----------|-----------|
| Multi-format ingestion | HIGH | MEDIUM | P1 | Core functionality, Docling handles heavy lifting |
| LLM extraction | HIGH | MEDIUM | P1 | Core value prop, Gemini structured output simplifies |
| Source attribution | HIGH | LOW | P1 | Key differentiator when visible, low effort with proper design |
| Confidence scoring | MEDIUM | LOW | P1 | Simple formula, adds production credibility |
| REST API with docs | HIGH | LOW | P1 | FastAPI auto-generates OpenAPI, minimal effort |
| Basic validation | MEDIUM | LOW | P1 | Regex patterns, quick win |
| Frontend dashboard | HIGH | MEDIUM | P1 | Portfolio requires visible demo |
| Architecture pages | HIGH | LOW | P1 | PRD bonus, high evaluator impact, mostly static content |
| Search functionality | MEDIUM | LOW | P1 | Basic SQL queries, expected feature |
| Income visualization | MEDIUM | LOW | P2 | Recharts makes this easy, looks impressive |
| HITL review workflow | MEDIUM | MEDIUM | P2 | Shows production thinking, badge + queue UI |
| Complexity-based model selection | LOW | MEDIUM | P2 | Cost optimization demo, but subtle |
| Visual source linking | HIGH | HIGH | P3 | Impressive but complex, defer |
| Entity resolution | MEDIUM | HIGH | P3 | Complex, defer unless time permits |
| Batch processing | LOW | MEDIUM | P3 | Nice to have, not core demo |

**Priority key:**
- P1: Must have for launch (complete by end of day 2)
- P2: Should have, add if time permits (day 3)
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

Comparison with production IDP (Intelligent Document Processing) platforms.

| Feature | Infrrd/Docsumo | Amazon Textract | Our Approach |
|---------|---------------|-----------------|--------------|
| OCR + Layout | Custom models | Native | Docling (production-grade, open source) |
| LLM Extraction | Internal models | Not included | Gemini 3.0 Pro/Flash with structured output |
| Source Attribution | Visual highlighting | Bounding boxes | Page/section/snippet references (text-based) |
| Confidence Scoring | ML-based | Per-field confidence | Formula-based (simpler, explainable) |
| HITL Review | Full workflow builder | Not included | Basic flagging and queue (simplified) |
| Document Classification | 100+ document types | 50+ lending docs | Implicit via extraction (document agnostic) |
| Integration | Enterprise APIs | AWS ecosystem | REST API with OpenAPI spec |
| Deployment | Cloud SaaS | AWS managed | GCP Cloud Run (serverless) |
| Cost Model | Per-page pricing | Per-page pricing | Gemini token-based (transparent) |

### Our Niche

We're not competing with enterprise IDP platforms. Our demo showcases:
1. **Modern AI-native architecture** - LLM-first extraction with structured output
2. **Full traceability** - Every extraction linked to source
3. **Production patterns** - Async processing, error handling, confidence scoring
4. **Cloud-native deployment** - Serverless, scalable infrastructure
5. **Code quality** - TDD, type hints, clean architecture

---

## Portfolio-Specific Recommendations

### What Makes This Project Stand Out

Based on recruiter expectations for 2025-2026:

1. **Live demo is essential** - Deploy to Cloud Run, have working URL
2. **Visual elements matter** - Architecture diagrams, data visualizations, clean UI
3. **Documentation quality** - Clear README, system design doc, API docs
4. **End-to-end implementation** - Not just ML model, but full pipeline to UI
5. **Production patterns** - Error handling, validation, confidence scoring show maturity

### High-Impact, Low-Effort Wins

| Win | Effort | Impact | How |
|-----|--------|--------|-----|
| Architecture visualization page | 4 hours | Very High | Static React components with Mermaid diagrams |
| Income timeline chart | 2 hours | High | Recharts line chart, looks impressive |
| Confidence badges in UI | 1 hour | Medium | Color-coded badges (green/yellow/red) |
| Processing status indicators | 1 hour | Medium | Animated spinner, status badges |
| OpenAPI documentation | 0 hours | High | FastAPI generates automatically |
| System design markdown | 3 hours | Very High | PRD requires, evaluators read this |

### Features to Skip for Portfolio

| Skip | Why |
|------|-----|
| Complex auth | Time sink, evaluators don't care |
| Full PII compliance | Add disclaimer instead |
| Batch processing | Single doc upload is fine for demo |
| Real-time updates | Polling is sufficient |
| Multi-tenant | Note in docs as "production consideration" |

---

## Sources

### Intelligent Document Processing (IDP)
- [Docsumo IDP Market Report 2025](https://www.docsumo.com/blogs/intelligent-document-processing/intelligent-document-processing-market-report-2025)
- [IDP Trends 2025 - AlgoDocs](https://algodocs.com/intelligent-document-processing-trends-2025-2/)
- [Infrrd IDP Platform](https://www.infrrd.ai/intelligent-document-processing-automation-software)
- [IDP Use Cases 2025 - Cleveroad](https://www.cleveroad.com/blog/idp-use-cases/)
- [IDP in Lending - Docsumo](https://www.docsumo.com/blogs/intelligent-document-processing/lending-industry)

### Mortgage/Loan Document Processing
- [AI Mortgage Document Processing - Ascendix](https://ascendixtech.com/ai-mortgage-document-processing/)
- [Mortgage Automation 2026 - ABBYY](https://www.abbyy.com/blog/ai-mortgage-process-automation/)
- [Mortgage Document Automation - Unstract](https://unstract.com/blog/mortgage-document-processing-and-automation-with-unstract/)
- [AWS Bedrock Mortgage Processing](https://aws.amazon.com/blogs/machine-learning/autonomous-mortgage-processing-using-amazon-bedrock-data-automation-and-amazon-bedrock-agents/)
- [Mortgage Data Extraction - Astera](https://www.astera.com/by-use-case/mortgage-data-extraction/)

### Confidence Scoring & Source Attribution
- [Microsoft Document Analysis - Confidence & Grounding](https://learn.microsoft.com/en-us/azure/ai-services/content-understanding/document/analyzer-improvement)
- [Audit Trails for Financial Compliance - Medium](https://lawrence-emenike.medium.com/audit-trails-and-explainability-for-compliance-building-the-transparency-layer-financial-services-d24961bad987)
- [Data Extraction Best Practices for Auditors - DataSnipper](https://www.datasnipper.com/resources/data-extraction-invoices-best-practices)

### LLM Extraction Pitfalls
- [Don't Use LLMs as OCR - Medium](https://medium.com/@martia_es/dont-use-llms-as-ocr-lessons-learned-from-extracting-complex-documents-db2d1fafcdfb)
- [LLMs for PDF Extraction 2026 - Unstract](https://unstract.com/blog/comparing-approaches-for-using-llms-for-structured-data-extraction-from-pdfs/)
- [Why LLMs Suck at OCR - Pulse AI](https://www.runpulse.com/blog/why-llms-suck-at-ocr)
- [Best LLM Document Parsers 2025 - Reducto](https://llms.reducto.ai/best-llm-ready-document-parsers-2025)
- [LLM Extraction Challenges at Scale - Zilliz](https://zilliz.com/blog/challenges-in-structured-document-data-extraction-at-scale-llms)

### Human-in-the-Loop (HITL)
- [HITL for AI Document Processing - Unstract](https://unstract.com/blog/human-in-the-loop-hitl-for-ai-document-processing/)
- [HITL Best Practices - Parseur](https://parseur.com/blog/hitl-best-practices)
- [HITL Guide 2026 - Parseur](https://parseur.com/blog/human-in-the-loop-ai)
- [Human Review for Document Processing - Sensible](https://www.sensible.so/blog/human-review-document-processing)
- [HITL - Docsumo](https://www.docsumo.com/platform/features/human-in-the-loop)

### Entity Resolution & Deduplication
- [Dedupe Python Library](https://github.com/dedupeio/dedupe)
- [Zingg Entity Resolution](https://github.com/zinggAI/zingg)
- [Entity Resolution Guide - Spot Intelligence](https://spotintelligence.com/2024/01/22/entity-resolution/)
- [Entity Resolution for Legal Documents - Instructor](https://python.useinstructor.com/examples/entity_resolution/)

### Portfolio Project Best Practices
- [ML Portfolio Projects 2025 - Medium](https://medium.com/@santosh.rout.cr7/ml-engineer-portfolio-projects-that-will-get-you-hired-in-2025-d1f2e20d6c79)
- [Tech Portfolio 2025 - TieTalent](https://tietalent.com/en/blog/220/beyond-the-ats-how-to-build-a-tech-portfolio)
- [Data Science Portfolio - Refonte Learning](https://www.refontelearning.com/blog/how-to-build-a-data-science-portfolio-that-gets-you-hired)
- [Projects That Impress Recruiters - NareshIT](https://nareshit.com/blogs/portfolio-projects-to-impress-recruiters-guide-nareshit)

### Document Extraction APIs
- [Best Document Extraction APIs - Eden AI](https://www.edenai.co/post/best-document-data-extraction-apis)
- [Amazon Textract Lending Docs](https://docs.aws.amazon.com/textract/latest/dg/lending-document-classification-extraction.html)
- [Data Extraction in Lending - Docsumo](https://www.docsumo.com/blogs/data-extraction/lending-industry)
- [Fintech Document Extraction - Sensible](https://www.sensible.so/solutions/financial-services)

---

*Feature research for: Loan Document Extraction System*
*Researched: 2026-01-23*
*Confidence: HIGH*
