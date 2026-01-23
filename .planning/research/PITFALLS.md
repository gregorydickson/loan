# Pitfalls Research: LLM-Based Loan Document Extraction

**Domain:** AI-powered document extraction (loans/mortgage documents)
**Researched:** 2026-01-23
**Confidence:** HIGH (verified across multiple authoritative sources)

---

## Critical Pitfalls (Severity: CRITICAL)

These cause project failure, data corruption, or complete rewrites. Address in Phase 1-2.

---

### Pitfall 1: Using LLMs as OCR (The Faithfulness Trap)

**What goes wrong:**
LLMs "understand" documents rather than faithfully extracting what's there. They hallucinate plausible-looking data that doesn't exist in the source document. For loan documents containing financial figures like $38,000,000, an LLM might output $88,000,000 - a single digit error that's catastrophic in lending.

**Why it happens:**
Developers assume LLMs can do everything. LLMs are trained to generate plausible text, not to be faithful extractors. They fill in gaps with "reasonable" values rather than admitting uncertainty.

**How to avoid:**
- **Use Docling for extraction, Gemini for reasoning** - Docling extracts raw text/tables faithfully; Gemini structures and interprets
- **Never ask the LLM to "read" the document** - Pass pre-extracted text, not the raw document
- **Implement grounding validation** - Every extracted value must trace to exact source text

**Warning signs:**
- Extracted numbers that "look right" but differ from source
- LLM adding context that wasn't in the document
- Consistent formatting in output even when source format varies
- Test with documents containing uncommon values (unusual numbers, rare names)

**Phase to address:** Phase 1 (Document Ingestion) - Establish Docling as the extraction layer before LLM touches anything

**Sources:**
- [Don't Use LLMs as OCR: Lessons Learned](https://medium.com/@martia_es/dont-use-llms-as-ocr-lessons-learned-from-extracting-complex-documents-db2d1fafcdfb)
- [SafePassage: High-Fidelity Information Extraction](https://arxiv.org/html/2510.00276)

---

### Pitfall 2: Source Attribution Theater (Fake Provenance)

**What goes wrong:**
System claims to track where data came from, but the attribution is invented. LLM generates page numbers, section references, or snippets that don't correspond to actual document locations. Research shows 50-90% of LLM responses are not fully supported by cited sources.

**Why it happens:**
LLMs are helpful - when asked for a source, they'll provide one. They don't distinguish between "remembering" where they saw something vs. generating a plausible-sounding citation. Without verification, fake provenance looks identical to real provenance.

**How to avoid:**
- **Chunk-level tracking** - When extracting, track which exact text chunk produced each extraction
- **String matching verification** - Every source snippet must fuzzy-match to actual document text
- **Page/section validation** - Verify cited page numbers exist and contain relevant content
- **Implement SafePassage pattern** - Extract, then verify extraction against original text

**Warning signs:**
- Source references to page numbers beyond document length
- Identical snippets cited for very different extractions
- Source text doesn't mention the extracted value
- Clean, well-formatted citations (real documents are messy)

**Phase to address:** Phase 2 (Extraction Engine) - Build attribution into the extraction pipeline, not as an afterthought

**Sources:**
- [SourceCheckup: Automated Framework for LLM Citation Assessment](https://www.nature.com/articles/s41467-025-58551-6)
- [Awesome LLM Attributions Survey](https://github.com/HITsz-TMG/awesome-llm-attributions)

---

### Pitfall 3: Structured Output Silent Failures

**What goes wrong:**
Gemini returns `None` instead of structured output when response exceeds `max_output_tokens`. API returns success (200), but `response.text` and `response.parsed` are both `None`. No error raised - data silently lost.

**Why it happens:**
Structured output mode has different failure semantics than text mode. When output truncation would produce invalid JSON, the API returns nothing rather than partial results. Complex loan documents with multiple borrowers can exceed token limits unexpectedly.

**How to avoid:**
- **Set generous max_output_tokens** - 8192 minimum for loan documents
- **Explicit None checks** - Always check `if response.parsed is None` before proceeding
- **Implement retry with chunking** - On None response, split input and retry
- **Monitor token usage** - Track actual vs. expected output tokens

**Warning signs:**
- Processing "succeeds" but produces no borrowers
- Works on simple test docs, fails on production docs
- Intermittent "no data extracted" without errors
- Token usage near limits in monitoring

**Phase to address:** Phase 2 (LLM Client) - Build None-handling into the client from day one

**Sources:**
- [Structured Output Returns None When max_output_tokens Exceeded](https://github.com/googleapis/python-genai/issues/1039)
- [Gemini API Structured Output Documentation](https://ai.google.dev/gemini-api/docs/structured-output)

---

### Pitfall 4: Numeric Extraction Catastrophe

**What goes wrong:**
Income figures, loan amounts, and account numbers extracted incorrectly. These errors compound - wrong income affects DTI calculations, wrong loan amounts affect everything. In lending, a 10% error rate means 10% of loans have materially wrong data.

**Why it happens:**
- OCR mistakes: 0/O/D confusion, 1/l/I confusion, 8/B confusion
- Format ambiguity: Is "1,234" one thousand or one-point-two-three-four?
- Unit confusion: Monthly vs. annual income, thousands vs. actual amounts
- Missing negatives: Deductions extracted as positive numbers

**How to avoid:**
- **Explicit format instructions** - Tell Gemini the expected numeric formats in prompts
- **Cross-validation rules** - Monthly income x 12 should approximately equal annual
- **Range checks** - Loan amounts should be reasonable for document type
- **Require unit specification** - Force extraction of units alongside values
- **Original text preservation** - Store the exact source text for every number

**Warning signs:**
- Income values that don't multiply correctly across periods
- Account numbers with unusual lengths
- Values that seem "too round" or "too precise"
- Inconsistent decimal separators

**Phase to address:** Phase 2 (Validation Service) - Build numeric validation as a required post-extraction step

**Sources:**
- [Designing an LLM-Based Document Extraction System](https://medium.com/@dikshithraj03/turning-messy-documents-into-structured-data-with-llms-d8a6242a31cc)
- [LLMs for Financial Document Analysis](https://intuitionlabs.ai/articles/llm-financial-document-analysis)

---

## High Pitfalls (Severity: HIGH)

These cause significant delays, quality issues, or technical debt. Address in Phase 2-3.

---

### Pitfall 5: The "It Works on Test Docs" Trap

**What goes wrong:**
System works perfectly on clean sample documents but fails on real loan packages. Real packages contain: scanned PDFs with varying quality, multiple documents merged into single PDFs, handwritten annotations, stamps/watermarks, and rotated pages.

**Why it happens:**
Test documents are usually clean digital PDFs. Real loan packages are messy. Docling's OCR has known issues with image-heavy PDFs and can silently fail, returning empty markdown.

**How to avoid:**
- **Test with production-like documents early** - Day 1, not day 3
- **Include "ugly" test cases** - Scanned docs, rotated pages, mixed formats
- **Implement quality scoring** - Detect when extraction confidence is low
- **Graceful degradation** - Return partial results with flags, not failures

**Warning signs:**
- High success rate on unit tests, low success on integration tests
- "Works locally, fails in Kubernetes" (Docling image processing issues)
- Empty extractions without errors
- Very fast processing times (nothing was actually extracted)

**Phase to address:** Phase 1 (Integration Tests) - Include real document samples in test suite

**Sources:**
- [Docling PDF Extraction Issues](https://github.com/docling-project/docling/issues/564)
- [PDF Data Extraction Benchmark 2025](https://procycons.com/en/blogs/pdf-data-extraction-benchmark/)

---

### Pitfall 6: LLM Cost Explosion

**What goes wrong:**
Development testing burns through API budget. A single large loan package (500+ pages) costs $5-10 in API calls during iterative development. With the 3-day timeline, uncontrolled testing can exhaust budget before shipping.

**Why it happens:**
- Re-running full extraction on every code change
- Not implementing caching during development
- Using Pro model for everything (vs. Flash for simple docs)
- Not truncating/sampling during development

**How to avoid:**
- **Development mode caching** - Cache Gemini responses keyed by (prompt_hash, document_hash)
- **Model tiering from day one** - Use Flash for standard docs, Pro only for complex
- **Token budgets per environment** - Dev: $10/day, staging: $50/day
- **Sample mode** - Extract from first 10 pages only during development
- **Mock mode for unit tests** - Never hit real API in unit tests

**Warning signs:**
- Daily API costs exceeding $20
- Same document processed multiple times in logs
- Pro model used for all documents
- No difference in cost between dev and production

**Phase to address:** Phase 2 (LLM Client) - Build cost controls into client architecture

**Sources:**
- [LLM Cost Optimization Guide 2025](https://futureagi.com/blogs/llm-cost-optimization-2025)
- [Taming the Beast: Cost Optimization for LLM API Calls](https://medium.com/@ajayverma23/taming-the-beast-cost-optimization-strategies-for-llm-api-calls-in-production-11f16dbe2c39)

---

### Pitfall 7: Non-Deterministic Test Failures

**What goes wrong:**
Tests pass, then fail, then pass again. Same input produces different outputs. CI becomes unreliable. Team loses trust in test suite and starts ignoring failures.

**Why it happens:**
LLMs are inherently non-deterministic. Even with temperature=0, responses can vary. Traditional unit test assertions (`assertEqual`) don't work for LLM outputs.

**How to avoid:**
- **Separate deterministic and non-deterministic tests** - Unit tests should be deterministic (mock LLM)
- **Use semantic similarity for LLM outputs** - "Paris" matches "The capital is Paris"
- **Record/replay for integration tests** - Use VCR pattern to record API responses
- **Threshold-based assertions** - "Confidence > 0.7" not "confidence == 0.85"
- **Run non-deterministic tests multiple times** - Pass if 8/10 runs succeed

**Warning signs:**
- Flaky tests in CI
- Tests that pass locally but fail in CI
- Exact string matching on LLM outputs
- Engineers skipping test runs

**Phase to address:** Phase 2 (Test Infrastructure) - Design test architecture for non-determinism

**Sources:**
- [Testing LLM Applications: A Practical Guide](https://langfuse.com/blog/2025-10-21-testing-llm-applications)
- [Beyond Traditional Testing: Non-Deterministic Software](https://dev.to/aws/beyond-traditional-testing-addressing-the-challenges-of-non-deterministic-software-583a)

---

### Pitfall 8: Rate Limiting Surprises

**What goes wrong:**
System works in development, crashes in production under load. Gemini API has per-minute rate limits. Batch processing of 100 documents triggers 429 errors and cascading failures.

**Why it happens:**
- Development tests one document at a time
- Rate limits are per-project, not per-request
- Exponential backoff without jitter causes thundering herd
- No circuit breaker means repeated failures

**How to avoid:**
- **Implement rate limiting client-side** - Don't rely on API rejections
- **Use leaky bucket algorithm** - Smooth traffic, don't burst
- **Add jitter to retries** - Randomize backoff timing
- **Queue with Cloud Tasks** - Decouple ingestion from processing
- **Monitor rate limit headers** - Track remaining quota

**Warning signs:**
- 429 errors in logs
- Processing time variance (fast, then slow, then fast)
- Successful small batches, failed large batches
- Retries without backoff in code

**Phase to address:** Phase 2 (LLM Client) - Build rate limiting into client, Phase 4 (API) - Add Cloud Tasks queue

**Sources:**
- [API Rate Limits Best Practices 2025](https://orq.ai/blog/api-rate-limit)
- [Apigee LLM Token Policies](https://docs.cloud.google.com/apigee/docs/api-platform/tutorials/using-ai-token-policies)

---

## Medium Pitfalls (Severity: MEDIUM)

These cause friction and quality issues. Address in Phase 3-4.

---

### Pitfall 9: Multi-Borrower Deduplication Failures

**What goes wrong:**
Same borrower appears multiple times in output. Or worse, two different borrowers get merged. Loan documents often mention the same person multiple times across different documents (application, verification letters, tax forms).

**Why it happens:**
- Name variations: "John Smith", "John Q. Smith", "J. Smith"
- Address variations: "123 Main St" vs "123 Main Street, Apt 4B"
- Insufficient matching signals after extraction
- LLM extracts each mention as separate person

**How to avoid:**
- **Multi-signal matching** - SSN match is definitive; name+address is fuzzy
- **Fuzzy name matching** - Use phonetic matching (Soundex) + edit distance
- **Address normalization** - Standardize before comparison
- **Confidence-weighted merging** - Higher confidence extractions win conflicts
- **Human review queue** - Low-confidence merges get flagged

**Warning signs:**
- More borrowers extracted than documents suggest
- Borrowers with very similar names
- Same SSN appearing in multiple borrower records
- Address variations for same apparent person

**Phase to address:** Phase 2 (Extractor) - Build deduplication into extraction pipeline

---

### Pitfall 10: Schema Evolution Lock-in

**What goes wrong:**
Initial schema doesn't capture all needed fields. Adding new fields requires database migrations, API changes, frontend updates, and re-extraction of all documents. The 3-day timeline doesn't allow for schema pivots.

**Why it happens:**
- Rushing to implement without analyzing full document corpus
- Treating loan docs as homogeneous when they vary significantly
- Not planning for fields discovered late in development

**How to avoid:**
- **Spend 2-4 hours on corpus analysis first** - What fields actually appear?
- **Use JSONB for flexible fields** - Core fields in columns, extras in JSON
- **Design for extension** - `metadata: dict` field for unknown fields
- **Version your schemas** - Allow old and new extractions to coexist

**Warning signs:**
- Discovering new field types on day 2
- Frequent Alembic migrations
- "We didn't think about X" conversations
- Hard-coded field lists

**Phase to address:** Phase 0 (Planning) - Analyze corpus before defining schemas

---

### Pitfall 11: Docling Silent Failures

**What goes wrong:**
Docling returns empty results without raising errors. Processing appears to succeed but no content is extracted. This is particularly common with certain image types embedded in PDFs.

**Why it happens:**
- Specific image formats trigger processing failures
- OCR pipeline silently skips problematic pages
- Kubernetes deployment missing required system dependencies
- Memory limits exceeded on large documents

**How to avoid:**
- **Validate extraction results** - Check content length, not just success status
- **Page-by-page processing with validation** - Detect which pages failed
- **System dependency checklist** - Ensure all OCR dependencies installed
- **Memory monitoring** - Track memory usage during processing
- **Fallback extraction method** - PyPDF2 as backup for text-only PDFs

**Warning signs:**
- Empty markdown output without errors
- Very fast processing (nothing was processed)
- Works locally, fails in container
- Inconsistent results across documents

**Phase to address:** Phase 1 (Docling Processor) - Add validation and fallback handling

**Sources:**
- [Docling Empty Markdown Issue](https://github.com/docling-project/docling/issues/2311)
- [Docling PDF with OCR Extraction Issues](https://github.com/docling-project/docling/discussions/2182)

---

## Timeline-Specific Pitfalls (3-Day Deadline)

---

### Pitfall 12: Scope Creep Death Spiral

**What goes wrong:**
Day 1: "Let's also add confidence scoring!" Day 2: "We need a dashboard!" Day 3: Incomplete extraction, incomplete UI, incomplete everything. 52% of projects experience scope creep, with 43% significantly impacting success.

**Why it happens:**
- Good ideas emerge during implementation
- Stakeholder requests seem small ("just add...")
- No clear definition of "done"
- Fear of shipping "incomplete" product

**How to avoid:**
- **Write down MVP scope in first hour** - What ships on day 3?
- **"Not in v1" list** - Explicitly list what you're NOT building
- **Time-box features** - If it takes >2 hours, defer it
- **Daily checkpoint** - Are we on track for day 3 ship?
- **Say "Yes, in v2"** - Acknowledge good ideas without committing

**Warning signs:**
- "While we're at it..." conversations
- Features added without removing others
- End of day 1 with no working extraction
- Working on UI before extraction works

**Phase to address:** Phase 0 (Planning) - Lock scope before coding starts

**Sources:**
- [Navigating Scope Creep in Software Projects](https://medium.com/@denismwg/navigating-scope-creep-in-software-projects-5-strategies-that-work-ec8a35684fdb)
- [What Is Scope Creep - Asana 2025](https://asana.com/resources/what-is-scope-creep)

---

### Pitfall 13: Premature Infrastructure Investment

**What goes wrong:**
Day 1 spent on Terraform, Docker, CI/CD. Day 2 realizes extraction doesn't work. Day 3 scrambling to fix core functionality with no time for integration.

**Why it happens:**
- "Do it right the first time" mindset
- Infrastructure feels productive (things are being created!)
- Fear of "doing it wrong" without proper setup
- Following PRD phases in strict order

**How to avoid:**
- **Core functionality first** - Extraction working locally before any infra
- **Infrastructure on day 2.5** - After core is proven
- **Use managed services** - Cloud Run, Cloud SQL require minimal config
- **Script, don't Terraform** - Manual deploy scripts are fine for day 3

**Warning signs:**
- Terraform files before Python files
- Docker builds before extraction runs
- CI/CD setup before tests exist
- More time in GCP console than VSCode

**Phase to address:** Phase 0 (Planning) - Prioritize core functionality over infrastructure

---

### Pitfall 14: Over-Testing Before Working

**What goes wrong:**
Extensive test suite for code that doesn't work yet. Tests become maintenance burden as implementation changes. TDD is good, but not when exploring unknowns.

**Why it happens:**
- PRD specifies TDD workflow
- Testing feels like progress
- Fear of shipping untested code
- Misunderstanding TDD granularity

**How to avoid:**
- **Spike first, test second** - For unknowns, prototype without tests
- **Test interfaces, not implementations** - Tests for stable boundaries
- **Integration tests over unit tests initially** - Verify end-to-end works
- **80% coverage target is for day 3** - Not day 1

**Warning signs:**
- More test code than implementation code on day 1
- Frequent test rewrites due to implementation changes
- High coverage but extraction doesn't work
- "Tests pass but I don't know if it works"

**Phase to address:** Phase 1-2 - Test critical paths, defer comprehensive testing

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoded prompts | Fast iteration | Prompt changes require code deploy | MVP only, extract to config immediately after |
| Synchronous extraction | Simple architecture | Can't handle large documents | Never for production |
| No retry logic | Simpler code | Any API hiccup causes failure | Never |
| Global error handling | Quick error recovery | Masks root causes | Never |
| String concatenation for prompts | Easy to write | Injection vulnerabilities | Never |
| Single model for all docs | No complexity classifier needed | 3-5x cost on simple docs | MVP acceptable if budget allows |

---

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Gemini API | Using chat format for extraction | Use structured output with response_mime_type |
| Gemini API | Assuming temperature=0 is deterministic | Still varies; design for non-determinism |
| Docling | Assuming PDF = text | Many PDFs are image-only, require OCR |
| Cloud Storage | Signed URLs without expiration | Always set reasonable expiration (15 min) |
| Cloud SQL | Synchronous connections in async code | Use asyncpg with connection pooling |
| Cloud Tasks | Assuming at-most-once delivery | Design for at-least-once (idempotency) |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Loading full document into memory | Works fine locally | Stream processing, chunk-based extraction | Documents >100MB |
| Sequential page processing | Simple code flow | Parallel page extraction with asyncio.gather | Documents >50 pages |
| No caching of Docling results | Works, just slow | Cache extracted text keyed by document hash | >10 documents/batch |
| LLM call per page | Fine for small docs | Batch pages into chunks, single LLM call | >20 pages |
| Unbounded result sets | Fast on test data | Pagination with default limit=50 | >1000 borrowers |

---

## Security Mistakes

Domain-specific security issues for loan document processing.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Logging extracted PII | SSNs, income in logs exposed | Structured logging with PII redaction |
| Storing raw documents indefinitely | Data breach exposure | Retention policy, encrypted at rest |
| LLM prompts containing PII | PII sent to third-party API | Anonymize identifiers before LLM call |
| No input validation on upload | Malicious files processed | File type validation, size limits, virus scan |
| GCS buckets with public access | Documents publicly accessible | Private buckets, signed URLs only |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Extraction works:** Often missing error handling for malformed documents - verify with corrupted PDF
- [ ] **Source attribution:** Often missing verification that citations are accurate - verify snippets exist in source
- [ ] **API returns data:** Often missing pagination - verify with 100+ borrowers
- [ ] **Tests pass:** Often missing integration tests - verify full flow works, not just units
- [ ] **Deployment works:** Often missing health checks - verify Cloud Run restarts on failure
- [ ] **Database stores data:** Often missing indices - verify query performance at scale
- [ ] **Frontend displays:** Often missing error states - verify behavior when API fails
- [ ] **Confidence scoring:** Often missing calibration - verify scores correlate with actual accuracy

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Hallucinated data in production | HIGH | Flag all records from affected period, re-extract with validation, manual review |
| Source attribution broken | MEDIUM | Add verification layer, re-process recent extractions, backfill provenance |
| Rate limit exhaustion | LOW | Implement backoff, wait for quota reset, request limit increase |
| Silent Docling failures | MEDIUM | Add validation checks, reprocess failed documents with fallback method |
| Schema needs new field | MEDIUM | Add JSONB column for flexibility, migrate incrementally |
| Test suite unreliable | MEDIUM | Separate deterministic/non-deterministic tests, implement recording/replay |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| LLMs as OCR | Phase 1 (Ingestion) | Docling extracts, LLM receives text |
| Source attribution theater | Phase 2 (Extraction) | Every extraction has verifiable source |
| Structured output None | Phase 2 (LLM Client) | None handling in client code |
| Numeric catastrophe | Phase 2 (Validation) | Cross-validation rules pass |
| "Works on test docs" | Phase 1 (Integration) | Real document samples in test suite |
| Cost explosion | Phase 2 (LLM Client) | Cost tracking and caching in place |
| Non-deterministic tests | Phase 2 (Tests) | Flaky test rate <5% |
| Rate limiting | Phase 2 (LLM Client) | Client-side rate limiting active |
| Deduplication failures | Phase 2 (Extractor) | Dedup logic with tests |
| Schema lock-in | Phase 0 (Planning) | Flexible schema with JSONB |
| Docling silent failures | Phase 1 (Processor) | Validation checks in place |
| Scope creep | Phase 0 (Planning) | Written MVP scope document |
| Premature infrastructure | Phase 0 (Planning) | Core working before infra |

---

## 3-Day Execution Strategy

Based on pitfall analysis, recommended approach:

### Day 1: Core Extraction (Pitfalls 1, 4, 5, 11)
- Morning: Docling processor with real document samples
- Afternoon: Gemini client with structured output + None handling
- Evening: Basic extraction working end-to-end

### Day 2: Quality & Integration (Pitfalls 2, 3, 6, 7)
- Morning: Source attribution with verification
- Afternoon: Validation service for numerics
- Evening: API endpoints with error handling

### Day 3: Polish & Ship (Pitfalls 12, 13)
- Morning: Integration tests, fix issues
- Afternoon: Minimal viable frontend
- Evening: Deploy to Cloud Run, documentation

**What to explicitly defer:**
- Complex deduplication logic (use simple exact-match)
- Comprehensive confidence scoring (use simple heuristics)
- Terraform (manual GCP setup is fine)
- >80% test coverage (focus on critical paths)

---

## Sources

### LLM Extraction and Hallucination
- [Don't Use LLMs as OCR](https://medium.com/@martia_es/dont-use-llms-as-ocr-lessons-learned-from-extracting-complex-documents-db2d1fafcdfb)
- [SafePassage: High-Fidelity Information Extraction](https://arxiv.org/html/2510.00276)
- [Challenges in Structured Document Data Extraction at Scale](https://zilliz.com/blog/challenges-in-structured-document-data-extraction-at-scale-llms)
- [Document Data Extraction 2026: LLMs vs OCRs](https://www.vellum.ai/blog/document-data-extraction-llms-vs-ocrs)

### Gemini API Specifics
- [Gemini Structured Output Documentation](https://ai.google.dev/gemini-api/docs/structured-output)
- [Structured Output Returns None Issue](https://github.com/googleapis/python-genai/issues/1039)
- [Improving Structured Outputs in Gemini API](https://blog.google/technology/developers/gemini-api-structured-outputs/)

### Docling Issues
- [PDF Extraction Benchmark 2025](https://procycons.com/en/blogs/pdf-data-extraction-benchmark/)
- [Docling vs Graphlit Comparison](https://www.graphlit.com/vs/docling)
- [Docling GitHub Issues](https://github.com/docling-project/docling/issues)

### Source Attribution
- [SourceCheckup: Automated Citation Assessment](https://www.nature.com/articles/s41467-025-58551-6)
- [Awesome LLM Attributions](https://github.com/HITsz-TMG/awesome-llm-attributions)

### Cost Management
- [LLM Cost Optimization Guide 2025](https://futureagi.com/blogs/llm-cost-optimization-2025)
- [Token Optimization Strategies](https://www.glukhov.org/post/2025/11/cost-effective-llm-applications/)

### Testing LLM Applications
- [Testing LLM Applications: Practical Guide](https://langfuse.com/blog/2025-10-21-testing-llm-applications)
- [LLM Testing in 2025](https://orq.ai/blog/llm-testing)
- [Beyond Traditional Testing](https://dev.to/aws/beyond-traditional-testing-addressing-the-challenges-of-non-deterministic-software-583a)

### Loan Document Processing
- [Mortgage Document Processing](https://unstract.com/blog/mortgage-document-processing-and-automation-with-unstract/)
- [Data Extraction in Lending](https://www.docsumo.com/blogs/data-extraction/lending-industry)

### Project Management
- [Scope Creep in Software Projects](https://medium.com/@denismwg/navigating-scope-creep-in-software-projects-5-strategies-that-work-ec8a35684fdb)
- [What Is Scope Creep - Asana](https://asana.com/resources/what-is-scope-creep)

---

*Pitfalls research for: LLM-Based Loan Document Extraction System*
*Researched: 2026-01-23*
*Confidence: HIGH*
