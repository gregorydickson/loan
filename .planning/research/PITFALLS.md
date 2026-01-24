# Pitfalls Research: v2.0 LangExtract, LightOnOCR, and CloudBuild Migration

**Domain:** Document extraction system enhancement — adding LangExtract, GPU OCR, and IaC migration
**Researched:** 2026-01-24
**Confidence:** MEDIUM (LangExtract is new library with limited production experience reports)

---

## Critical Pitfalls (Severity: CRITICAL)

These cause project failure, data corruption, or complete rewrites. Must address in early phases.

---

### Pitfall 1: Character Offset Mismatch Between Docling and LangExtract

**What goes wrong:**
LangExtract provides character offsets (`char_interval`) relative to the raw text it receives. But Docling's markdown export transforms the document text — adding markdown formatting, removing whitespace, reordering elements. The character offsets from LangExtract don't map back to the original document or to Docling's page boundaries.

**Why it happens:**
- Docling's `export_to_markdown()` produces formatted text, not verbatim extraction
- LangExtract offsets are relative to its input string, not the source document
- Current `SourceReference` model tracks page numbers, not character offsets
- No intermediate representation preserves both structure and original positions

**How to avoid:**
- **Use Docling's raw text mode** — Extract unformatted text with position tracking
- **Store dual offsets** — Both Docling-relative and original-document-relative positions
- **Build offset translation layer** — Map LangExtract offsets back through Docling's transformations
- **Verify with substring matching** — Extracted text must exactly match source at reported offset

**Warning signs:**
- Character offset points to middle of a word
- Extracted snippet doesn't match text at reported position
- Offsets exceed document length
- Same offset reported for extractions from different pages

**Phase to address:** Phase 1 (LangExtract Integration) — Design offset tracking architecture before any extraction code

**Sources:**
- [LangExtract GitHub](https://github.com/google/langextract) — char_interval documentation
- [Docling + LangExtract Integration](https://dev.to/_aparna_pradhan_/the-perfect-extraction-unlocking-unstructured-data-with-docling-langextract-1j3b) — Integration challenges

---

### Pitfall 2: LangExtract Few-Shot Example Alignment Errors

**What goes wrong:**
LangExtract's extraction quality depends heavily on few-shot examples. If `extraction_text` values in examples don't appear verbatim in the example's source text, or aren't listed in order of appearance, LangExtract raises "Prompt alignment warnings" and extraction quality degrades dramatically.

**Why it happens:**
- Examples use paraphrased text instead of verbatim quotes
- Extraction order in examples doesn't match document order
- Example text edited for readability breaks alignment
- Copy-paste errors in example construction

**How to avoid:**
- **Use exact verbatim text from examples** — Copy directly from source, never paraphrase
- **List extractions in document order** — First extraction in text = first in example
- **Enable alignment warnings** — Don't suppress `Prompt alignment warnings`
- **Test examples against real extraction** — Each example should work as both training and test

**Warning signs:**
- "Prompt alignment warnings" in console output
- Good extraction on simple docs, poor on complex docs
- Extraction order doesn't match document order
- Missing fields that are clearly present in document

**Phase to address:** Phase 1 (LangExtract Integration) — Create validated example corpus before production use

**Sources:**
- [LangExtract Documentation](https://github.com/google/langextract) — Example alignment requirements
- [DataCamp LangExtract Tutorial](https://www.datacamp.com/tutorial/langextract) — Best practices for examples

---

### Pitfall 3: GPU Service Cold Start Cost Explosion

**What goes wrong:**
LightOnOCR GPU service on Cloud Run L4 costs $0.67/hour when running. With `min_instances=0` for cost savings, cold starts take 5-19 seconds. But keeping `min_instances=1` for latency costs $485/month ($0.67 x 24 x 30) for a service that might only process 100 documents/month.

**Why it happens:**
- GPU pricing is per-instance-lifetime, not per-request
- Cloud Run GPU instances have 10-minute idle timeout (vs 15 minutes for CPU)
- Cold starts include GPU driver loading + model loading + inference warmup
- No granular scaling between 0 and 1 instance

**How to avoid:**
- **Batch documents before OCR** — Collect 5-10 documents, then spin up GPU
- **Disable zonal redundancy** — Cuts GPU cost from $0.0002909/sec to $0.0001867/sec
- **Use GPU only for scanned documents** — Route digital PDFs to Docling's CPU OCR
- **Scheduled warm-up** — Ping GPU service before expected batch processing
- **Time-based min_instances** — 1 during business hours, 0 overnight

**Warning signs:**
- GPU costs exceeding document processing costs
- 99th percentile latency >20 seconds
- GPU idle time >80% in metrics
- All documents routed to GPU regardless of type

**Phase to address:** Phase 2 (LightOnOCR Service) — Design routing logic before deployment

**Sources:**
- [Cloud Run GPU Pricing](https://cloud.google.com/run/docs/configuring/services/gpu) — L4 GPU costs
- [Cloud Run GPU Best Practices](https://cloud.google.com/blog/products/serverless/cloud-run-gpus-are-now-generally-available) — Cost optimization

---

### Pitfall 4: Terraform State Orphaning During CloudBuild Migration

**What goes wrong:**
Existing infrastructure is managed by Terraform with remote state. Migrating to CloudBuild + gcloud CLI creates new resources without importing Terraform state. Result: duplicate resources, orphaned state, or — worst case — Terraform thinks resources are deleted and destroys production infrastructure on next `terraform apply`.

**Why it happens:**
- CloudBuild scripts create resources directly via gcloud CLI
- Terraform state doesn't know about CLI-created resources
- Someone runs `terraform apply` after CLI migration, causing drift
- State file not explicitly retired, team confusion

**How to avoid:**
- **Never run terraform after migration begins** — Revoke Terraform service account permissions
- **Export Terraform state as documentation** — `terraform state list` and `terraform show`
- **Tag all resources with creation method** — `created_by: cloudbuild` vs `created_by: terraform`
- **Incremental migration** — Migrate one resource type at a time, verify, proceed
- **State file archival** — Move state to read-only archive, not delete

**Warning signs:**
- Resources exist in both Terraform state and CloudBuild scripts
- Terraform plan shows "will destroy" for resources you need
- Duplicate resources (e.g., two Cloud Run services)
- "Resource already exists" errors from CloudBuild

**Phase to address:** Phase 3 (CloudBuild Migration) — Create explicit migration plan before any infrastructure changes

**Sources:**
- [Terraform State Migration Guide](https://scalr.com/guides/platform-engineers-guide-to-migrating-off-terraform-cloud-enterprise) — Migration best practices
- [Terraform Rollback Guide](https://scalr.com/learning-center/terraform-rollback-guide/) — Recovery from state issues

---

### Pitfall 5: Dual Extraction Method Inconsistent Results

**What goes wrong:**
Same document produces different borrower counts, different field values, or different confidence scores when processed by Docling+Gemini vs LangExtract. Users lose trust: "Which result is correct?" Testing becomes impossible: which method is the source of truth?

**Why it happens:**
- Different chunking strategies produce different context windows
- Gemini structured output vs LangExtract few-shot prompting yield different results
- Docling page-based attribution vs LangExtract character-offset attribution are incompatible
- No normalization layer between extraction methods

**How to avoid:**
- **Single result format** — Both methods produce identical `BorrowerRecord` structure
- **Normalization layer** — Post-extraction step that standardizes outputs
- **Canonical test suite** — Same documents, expected same results, both methods
- **Method metadata** — Every extraction records which method produced it
- **Confidence comparison** — Run both methods, use higher-confidence result

**Warning signs:**
- Same document yields 2 borrowers with one method, 3 with another
- Field values differ by more than formatting
- Page numbers from LangExtract don't match Docling pages
- Test passing for one method, failing for other

**Phase to address:** Phase 1 (LangExtract Integration) — Define normalization interface before implementing LangExtract extractor

**Sources:**
- [Docling + LangExtract Integration](https://dev.to/_aparna_pradhan_/the-perfect-extraction-unlocking-unstructured-data-with-docling-langextract-1j3b) — Integration architecture

---

## High Pitfalls (Severity: HIGH)

These cause significant delays, quality issues, or technical debt. Address early in development.

---

### Pitfall 6: LightOnOCR Transformers Integration Immaturity

**What goes wrong:**
LightOnOCR (released October 2025) has incomplete transformers integration. Auto-configuration fails with "Config not found for lightonocr". Training and fine-tuning interfaces are "coming soon". Production deployment requires manual workarounds.

**Why it happens:**
- Library is only 4 months old
- Transformers PR for LightOnOCR still has open issues
- Documentation assumes vLLM deployment, not direct Python usage
- Model architecture conflicts between Pixtral vision encoder and Qwen3 text decoder

**How to avoid:**
- **Use vLLM deployment** — Official supported method, avoid direct transformers usage
- **Pin exact versions** — `vllm==0.11.1` is officially supported, newer versions may break
- **Test inference before building service** — Verify model loads and runs correctly
- **Fallback to Docling OCR** — Don't make LightOnOCR required for MVP

**Warning signs:**
- "Config not found" errors at import time
- Attention mask warnings in inference
- Model loading works but inference fails
- Different results between local and deployed versions

**Phase to address:** Phase 2 (LightOnOCR Service) — Spike vLLM deployment before committing to architecture

**Sources:**
- [LightOnOCR Transformers PR](https://github.com/huggingface/transformers/pull/41621) — Integration status
- [LightOnOCR HuggingFace](https://huggingface.co/lightonai/LightOnOCR-1B-1025) — Deployment requirements

---

### Pitfall 7: LangExtract Multi-Pass Overlap Conflicts

**What goes wrong:**
LangExtract uses `extraction_passes > 1` to improve recall on long documents. Multiple passes find the same entity, creating duplicates. The "first-pass wins" strategy for overlapping character spans can discard higher-quality later extractions.

**Why it happens:**
- Multi-pass designed for recall, not precision
- Same borrower mentioned multiple times in document
- Different passes chunk document differently
- No intelligent merge strategy beyond character overlap

**How to avoid:**
- **Start with single pass** — Add passes only if recall is a problem
- **Post-extraction deduplication** — Use existing BorrowerDeduplicator after LangExtract
- **Tune chunk size before adding passes** — Larger chunks often better than multiple passes
- **Monitor duplicate rate** — Track how many extractions are duplicates

**Warning signs:**
- Same borrower extracted multiple times with slight variations
- Extraction count higher than expected borrower count
- Different confidence scores for same entity
- Processing time scales quadratically with passes

**Phase to address:** Phase 1 (LangExtract Integration) — Configure single-pass first, add multi-pass only if needed

**Sources:**
- [LangExtract Documentation](https://github.com/google/langextract) — Multi-pass extraction behavior

---

### Pitfall 8: CloudBuild YAML Type Coercion Errors

**What goes wrong:**
CloudBuild config fails with "json: cannot unmarshal number into Go value of type string". Values that look correct in YAML are parsed incorrectly. Build fails before any actual deployment.

**Why it happens:**
- YAML type inference differs from CloudBuild expectations
- Numeric values without quotes become numbers
- Environment variable substitutions have type requirements
- Different behavior between local YAML parsing and CloudBuild

**How to avoid:**
- **Quote all string values** — Even if they look like strings, quote them
- **Use explicit substitution syntax** — `${_VAR}` not `$_VAR`
- **Validate locally first** — `gcloud builds submit --dry-run`
- **Test minimal config** — Start with hello-world, add complexity incrementally

**Warning signs:**
- "cannot unmarshal" errors
- Builds fail immediately without running steps
- Works locally, fails in CloudBuild
- Substitution variables not expanded

**Phase to address:** Phase 3 (CloudBuild Migration) — Create validated cloudbuild.yaml template

**Sources:**
- [Cloud Build Terraform Integration](https://medium.com/google-cloud/integrating-our-application-ci-cd-pipelines-and-terraform-gitops-with-cloud-build-35e8d38b8468) — YAML gotchas

---

### Pitfall 9: GPU Quota Denial Blocking Deployment

**What goes wrong:**
Cloud Run GPU deployment fails: "Quota exceeded for nvidia-l4 GPUs". Default quota is 3 GPUs per region. Quota increase requests take 24-48 hours to process, blocking the entire OCR feature.

**Why it happens:**
- Projects using GPUs for first time get only 3 GPU quota
- Quota is per-region, spreading load across regions doesn't help
- Zonal redundancy doubles effective GPU usage
- Quota increases are manual review, not automatic

**How to avoid:**
- **Request quota early** — Submit increase request before development starts
- **Disable zonal redundancy** — Use 1 GPU instead of 2 for dev/staging
- **Start in one region** — Expand to multi-region after quota approved
- **Have CPU fallback ready** — Docling OCR as backup when GPU unavailable

**Warning signs:**
- Deployment succeeds but pod never starts
- "Quota exceeded" in Cloud Run logs
- Works in one environment but not another
- Intermittent deployment failures (quota race conditions)

**Phase to address:** Phase 0 (Setup) — Request GPU quota before any LightOnOCR development

**Sources:**
- [Cloud Run GPU Documentation](https://docs.google.com/run/docs/configuring/services/gpu) — Quota limitations

---

### Pitfall 10: SourceReference Schema Migration Complexity

**What goes wrong:**
Current `SourceReference` model has `page_number` and `snippet`. Adding `char_start` and `char_end` for LangExtract requires database migration. But existing records don't have character offsets, and Docling-extracted records will never have them. Schema becomes inconsistent.

**Why it happens:**
- Two extraction methods have different capabilities
- Cannot backfill character offsets for existing records
- Nullable fields create optional handling throughout codebase
- API consumers don't know which method produced which record

**How to avoid:**
- **Version the source reference** — `SourceReferenceV1` (page-based) vs `SourceReferenceV2` (character-based)
- **Use union type** — `source: PageSource | CharacterSource`
- **Add extraction_method field** — Record which method produced each extraction
- **Migrate incrementally** — New extractions get new schema, old records unchanged

**Warning signs:**
- Frequent "is not None" checks in code
- Different code paths for different source types
- API response format varies by record
- Test coverage gaps on older records

**Phase to address:** Phase 1 (LangExtract Integration) — Design schema evolution before any database changes

---

## Medium Pitfalls (Severity: MEDIUM)

These cause friction and quality issues. Address during implementation.

---

### Pitfall 11: LightOnOCR Image Preprocessing Mismatches

**What goes wrong:**
LightOnOCR expects images rendered at 1540px longest dimension with maintained aspect ratio. PDF pages rendered at different resolutions or cropped produce degraded OCR quality. Scanned documents at 300 DPI vs 72 DPI behave differently.

**Why it happens:**
- Model trained on specific image characteristics
- Different PDF renderers produce different pixel dimensions
- Existing Docling pipeline may resize images differently
- No validation that images meet requirements

**How to avoid:**
- **Standardize preprocessing** — All PDF pages through same rendering pipeline
- **Validate dimensions before OCR** — Reject/resize images that don't meet requirements
- **Test with actual scanned documents** — Not just clean digital PDFs
- **Compare against Docling OCR quality** — Baseline for quality regression

**Warning signs:**
- OCR quality varies between documents of similar visual quality
- Some pages have excellent OCR, others are garbage
- Processing time varies wildly for similar page counts
- Different results for same PDF rendered different ways

**Phase to address:** Phase 2 (LightOnOCR Service) — Implement preprocessing pipeline before production deployment

---

### Pitfall 12: API Method Selection Parameter Conflicts

**What goes wrong:**
API accepts `extraction_method` and `ocr_method` parameters. Users specify conflicting combinations (e.g., LangExtract method with Docling OCR but LangExtract expects LightOnOCR). Invalid combinations cause confusing errors.

**Why it happens:**
- Method dependencies not encoded in API schema
- Frontend doesn't validate combinations
- Error messages don't explain valid combinations
- Testing covers happy paths, not conflict cases

**How to avoid:**
- **Define valid combinations explicitly** — Enum of supported configurations
- **Validate at API boundary** — Reject invalid combinations with helpful error
- **Default to recommended combination** — Smart defaults reduce user error
- **Document compatibility matrix** — Which methods work with which OCR options

**Warning signs:**
- User bug reports about "it doesn't work"
- Same document succeeds with one combination, fails with another
- Error messages don't mention parameter conflicts
- Tests pass because they only use valid combinations

**Phase to address:** Phase 4 (API Enhancement) — Define valid method combinations in schema

---

### Pitfall 13: LangExtract Rate Limit Differences from Gemini Direct

**What goes wrong:**
LangExtract uses Gemini API internally but has its own rate limiting behavior. Existing rate limiting code designed for direct Gemini calls doesn't account for LangExtract's multi-call patterns (chunking, multiple passes). Rate limits hit unexpectedly.

**Why it happens:**
- LangExtract makes multiple Gemini calls per document
- Chunking multiplies API calls
- Multi-pass extraction multiplies again
- Existing rate limiter counts documents, not underlying API calls

**How to avoid:**
- **Request Tier 2 quota** — LangExtract recommends this for production
- **Configure chunk size for rate limits** — Larger chunks = fewer API calls
- **Monitor actual API call count** — Not just document count
- **Add buffer for LangExtract overhead** — 3-5x more calls than direct Gemini

**Warning signs:**
- Rate limiting at lower document throughput than expected
- Works fine for single documents, fails for batches
- Gemini quota dashboard shows higher usage than expected
- Inconsistent failures at batch boundaries

**Phase to address:** Phase 1 (LangExtract Integration) — Configure rate limiting based on actual API call patterns

**Sources:**
- [LangExtract Documentation](https://github.com/google/langextract) — Tier 2 quota recommendation

---

### Pitfall 14: CloudBuild Service Account Permission Gaps

**What goes wrong:**
CloudBuild can't deploy to Cloud Run, access Secret Manager, or push to Artifact Registry. Build fails with permission denied. Permissions that worked for Terraform don't automatically work for CloudBuild.

**Why it happens:**
- CloudBuild uses different service account than Terraform
- IAM permissions are method-specific (API vs gcloud)
- Secret Manager requires explicit accessor permission
- Artifact Registry push needs repository-level permissions

**How to avoid:**
- **Use dedicated CloudBuild service account** — Not default compute service account
- **Grant minimal required permissions** — Run invoker, secret accessor, artifact registry writer
- **Test permissions before full migration** — Deploy hello-world first
- **Document IAM configuration** — Part of migration runbook

**Warning signs:**
- "Permission denied" at different build steps
- Works for some resources, fails for others
- Same commands work locally but fail in CloudBuild
- Intermittent failures (IAM propagation delays)

**Phase to address:** Phase 3 (CloudBuild Migration) — Configure service account permissions first

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip character offset storage | Faster implementation | Can't do character-level highlighting | Never for LangExtract integration |
| Single extraction method | Simpler code | Stuck if method has issues | MVP only, add flexibility immediately after |
| GPU always-on | No cold starts | $485/month baseline cost | Only if processing >1000 docs/month |
| CloudBuild without Terraform | Simpler deployment | No drift detection | If team commits to no Terraform forever |
| Same schema for both methods | Less migration work | Nullable fields everywhere | Never — use versioned schemas |
| Skip OCR method routing | All docs use GPU | Wasted GPU on digital PDFs | Never for production |

---

## Integration Gotchas

Common mistakes when connecting new components to existing system.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| LangExtract + Docling | Pass markdown to LangExtract | Pass raw text to preserve offset accuracy |
| LangExtract + Existing Extractor | Replace BorrowerExtractor | Add LangExtractExtractor as alternative |
| LightOnOCR + DoclingProcessor | Replace Docling OCR | Route scanned docs to LightOnOCR, keep Docling for rest |
| CloudBuild + Secrets | Hardcode secrets in yaml | Use Secret Manager substitutions |
| New schema + Old data | Force migration of all records | Coexist with version field |
| GPU service + Existing API | New endpoint | New parameter on existing endpoint |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| LangExtract on every document | Works for testing | Route only complex docs to LangExtract | >50 docs/day |
| GPU service for all OCR | Fast processing | Route only scanned docs to GPU | >$100/month GPU cost |
| Single-threaded LangExtract | Works fine | Use parallel chunk processing | Documents >20 pages |
| Synchronous OCR routing | Simple code | Async decision with caching | Latency >5 seconds |
| No LangExtract result caching | Fresh results | Cache by (doc_hash, example_hash) | Reprocessing same docs |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **LangExtract integration:** Often missing character offset storage — verify offsets saved to database
- [ ] **LightOnOCR service:** Often missing image preprocessing — verify images meet 1540px requirement
- [ ] **CloudBuild pipeline:** Often missing rollback capability — verify can deploy previous version
- [ ] **Dual extraction:** Often missing method comparison — verify same doc produces comparable results
- [ ] **GPU routing:** Often missing cost monitoring — verify GPU usage tracked in dashboard
- [ ] **Schema migration:** Often missing backward compatibility — verify old records still work
- [ ] **API method selection:** Often missing validation — verify invalid combinations rejected
- [ ] **Few-shot examples:** Often missing alignment verification — verify no prompt warnings

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Character offset mismatch | MEDIUM | Add offset translation layer, reprocess recent documents |
| Few-shot example misalignment | LOW | Fix examples, rerun affected extractions |
| GPU cost overrun | LOW | Add routing logic, reduce min_instances to 0 |
| Terraform state orphaning | HIGH | Manually import resources or recreate with new names |
| Dual method inconsistency | MEDIUM | Pick primary method, deprecate secondary |
| LightOnOCR integration failure | MEDIUM | Fall back to Docling OCR, defer GPU service |
| CloudBuild permission failure | LOW | Grant missing permissions, retry |
| GPU quota denial | MEDIUM | Use CPU fallback, escalate quota request |
| Schema migration issues | HIGH | Add version field, maintain dual schema |
| Rate limit exhaustion | LOW | Request quota increase, add backoff |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Character offset mismatch | Phase 1 (LangExtract) | Offset points to correct text |
| Few-shot example alignment | Phase 1 (LangExtract) | No prompt warnings in logs |
| GPU cold start cost | Phase 2 (LightOnOCR) | Routing logic in place |
| Terraform state orphaning | Phase 3 (CloudBuild) | State archived, permissions revoked |
| Dual method inconsistency | Phase 1 (LangExtract) | Normalization layer exists |
| LightOnOCR immaturity | Phase 2 (LightOnOCR) | vLLM deployment working |
| Multi-pass overlap | Phase 1 (LangExtract) | Deduplication integrated |
| CloudBuild YAML errors | Phase 3 (CloudBuild) | Validated template exists |
| GPU quota denial | Phase 0 (Setup) | Quota request submitted |
| Schema migration | Phase 1 (LangExtract) | Versioned schema in place |

---

## v2.0 Execution Strategy

Based on pitfall analysis, recommended approach:

### Phase 0: Pre-Development Setup (Before Coding)
- Request GPU quota increase for Cloud Run L4
- Archive Terraform state, document current infrastructure
- Create CloudBuild service account with permissions
- Validate LightOnOCR loads in vLLM locally

### Phase 1: LangExtract Integration (Highest Risk)
- Design character offset storage schema with versioning
- Create validated few-shot example corpus from real loan docs
- Build LangExtract extractor parallel to existing BorrowerExtractor
- Implement offset translation layer between Docling and LangExtract
- Test with same documents as existing Docling pipeline

### Phase 2: LightOnOCR Service (Second Highest Risk)
- Spike vLLM deployment on Cloud Run with GPU
- Implement image preprocessing pipeline (1540px normalization)
- Create OCR routing logic (scanned vs digital documents)
- Add cost monitoring and alerts
- Test cold start latency, optimize as needed

### Phase 3: CloudBuild Migration (Lower Risk)
- Create cloudbuild.yaml from Terraform configuration
- Test deployment of each component individually
- Implement rollback capability
- Migrate one environment at a time (dev -> staging -> prod)
- Revoke Terraform service account permissions after migration

### Phase 4: API Enhancement (Lowest Risk)
- Add method selection parameters with validation
- Implement valid combination enforcement
- Add method metadata to responses
- Update frontend to expose method selection
- Add comparison mode for testing

**What to explicitly defer:**
- Fine-tuning LightOnOCR for loan documents (library support "coming soon")
- Multi-region GPU deployment (start single-region, expand later)
- Advanced LangExtract features like multi-pass (start single-pass)
- Automatic method selection (start with explicit selection)

---

## Sources

### LangExtract
- [LangExtract GitHub](https://github.com/google/langextract) — Official repository and documentation
- [Google Developers Blog: Introducing LangExtract](https://developers.googleblog.com/introducing-langextract-a-gemini-powered-information-extraction-library/) — Launch announcement
- [DataCamp LangExtract Tutorial](https://www.datacamp.com/tutorial/langextract) — Configuration best practices
- [Docling + LangExtract Integration](https://dev.to/_aparna_pradhan_/the-perfect-extraction-unlocking-unstructured-data-with-docling-langextract-1j3b) — Integration architecture

### LightOnOCR
- [LightOnOCR HuggingFace](https://huggingface.co/lightonai/LightOnOCR-1B-1025) — Model card and requirements
- [LightOnOCR Blog](https://www.lighton.ai/lighton-blogs/making-knowledge-machine-readable) — Architecture and capabilities
- [LightOnOCR Transformers PR](https://github.com/huggingface/transformers/pull/41621) — Integration status

### Cloud Run GPU
- [Cloud Run GPU Documentation](https://docs.google.com/run/docs/configuring/services/gpu) — Configuration and requirements
- [Cloud Run GPUs GA Announcement](https://cloud.google.com/blog/products/serverless/cloud-run-gpus-are-now-generally-available) — Best practices
- [NVIDIA Cloud Run Blog](https://developer.nvidia.com/blog/google-cloud-run-adds-support-for-nvidia-l4-gpus-nvidia-nim-and-serverless-ai-inference-deployments-at-scale/) — L4 GPU deployment

### CloudBuild Migration
- [Terraform to CloudBuild Integration](https://medium.com/google-cloud/integrating-our-application-ci-cd-pipelines-and-terraform-gitops-with-cloud-build-35e8d38b8468) — GitOps patterns
- [Terraform Migration Guide](https://scalr.com/guides/platform-engineers-guide-to-migrating-off-terraform-cloud-enterprise) — State management
- [Terraform Rollback Guide](https://scalr.com/learning-center/terraform-rollback-guide/) — Recovery strategies

### Zero-Downtime Deployment
- [Zero Downtime with Terraform](https://www.hashicorp.com/en/blog/zero-downtime-updates-with-terraform) — Deployment patterns
- [Cloud Deployment Best Practices 2025](https://octopus.com/devops/cloud-deployment/) — Modern deployment strategies

---

*Pitfalls research for: v2.0 LangExtract, LightOnOCR, and CloudBuild Migration*
*Researched: 2026-01-24*
*Confidence: MEDIUM (LangExtract is new, limited production experience reports)*
