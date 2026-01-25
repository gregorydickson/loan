# Extraction Method Selection Guide

This guide helps API users choose the right extraction method and OCR settings for their loan documents.

## Quick Reference

| Method | Best For | Speed | Cost | Accuracy |
|--------|----------|-------|------|----------|
| `docling` | Standard PDFs, fast processing | Fast | Low | Good |
| `langextract` | Complex docs, audit trail needed | Moderate | Medium | Better |
| `auto` | Let system decide | Varies | Varies | Optimal |

## Method Parameter

The `method` query parameter selects the extraction pipeline.

### `?method=docling` (Default)

The Docling-based extraction pipeline. This is the v1.0 default and remains the default for backward compatibility.

- **Best for:** Standard loan documents with clear structure
- **Output:** Extracted fields without character offsets
- **Performance:** Fast, single-pass extraction

### `?method=langextract`

The LangExtract structured extraction pipeline with character offset tracking.

- **Best for:** Complex documents requiring audit trail
- **Output:** Extracted fields with `char_start` and `char_end` offsets
- **Performance:** Moderate, uses few-shot learning for domain adaptation

### `?method=auto`

Automatic method selection based on document characteristics (future enhancement).

- **Behavior:** Currently defaults to LangExtract, falls back to Docling on failure
- **Best for:** When you want optimal handling without manual selection

## OCR Mode Parameter

The `ocr` query parameter controls Optical Character Recognition for scanned documents.

### `?ocr=auto` (Default)

Automatically detect scanned pages and apply OCR only when needed.

- **Best for:** Mixed document sets (some native, some scanned)
- **Cost:** GPU cost only for scanned documents
- **Cold start:** 60-120 seconds if GPU service needs to warm up

### `?ocr=force`

Always apply OCR regardless of document content.

- **Best for:** Poor quality scans, faded documents, inconsistent scan quality
- **Cost:** GPU cost for every document
- **When to use:** When auto-detection misses scanned content

### `?ocr=skip`

Never apply OCR, assume all text is extractable.

- **Best for:** Native digital PDFs (created digitally, not scanned)
- **Cost:** Zero GPU cost
- **Caution:** Scanned documents will fail extraction with this setting

## Curl Examples

### Default Docling Extraction

```bash
curl -X POST "http://localhost:8000/api/documents/" \
  -F "file=@loan.pdf"
```

This uses `method=docling` and `ocr=auto` by default.

### LangExtract with Character Offsets

```bash
curl -X POST "http://localhost:8000/api/documents/?method=langextract" \
  -F "file=@loan.pdf"
```

Returns extracted fields with `char_start` and `char_end` for each extraction.

### LangExtract with Forced OCR

```bash
curl -X POST "http://localhost:8000/api/documents/?method=langextract&ocr=force" \
  -F "file=@scan.pdf"
```

Use for scanned documents when you want character offset tracking.

### Skip OCR for Native PDFs

```bash
curl -X POST "http://localhost:8000/api/documents/?method=docling&ocr=skip" \
  -F "file=@digital.pdf"
```

Fastest processing for documents known to be native digital PDFs.

### Auto Method Selection

```bash
curl -X POST "http://localhost:8000/api/documents/?method=auto&ocr=auto" \
  -F "file=@unknown.pdf"
```

Let the system choose the best extraction method and OCR handling.

## Response Differences

### Docling Response

```json
{
  "id": "uuid",
  "filename": "loan.pdf",
  "status": "completed",
  "extraction_method": "docling",
  "ocr_processed": false,
  "extractions": [
    {
      "field": "borrower_name",
      "value": "John Smith"
    }
  ]
}
```

### LangExtract Response

```json
{
  "id": "uuid",
  "filename": "loan.pdf",
  "status": "completed",
  "extraction_method": "langextract",
  "ocr_processed": false,
  "extractions": [
    {
      "field": "borrower_name",
      "value": "John Smith",
      "char_start": 1523,
      "char_end": 1533,
      "page": 1,
      "confidence": 0.95
    }
  ]
}
```

The LangExtract response includes:
- `char_start`: Starting character position in the source text
- `char_end`: Ending character position in the source text
- `page`: Page number where the extraction was found
- `confidence`: Model confidence score for the extraction

These offsets enable:
- Highlighting extracted text in the original document
- Audit trails showing exactly where data came from
- Verification workflows where users can confirm extractions

## Decision Flowchart

Use this guide to select the right parameters:

```
Start
  |
  v
Do you need character offsets for audit trail?
  |
  +-- YES --> method=langextract
  |
  +-- NO --> Is document volume high (>100/day)?
              |
              +-- YES --> method=docling (faster)
              |
              +-- NO --> method=langextract (better accuracy)

Then:

Is the document scanned?
  |
  +-- YES --> ocr=force (always OCR)
  |
  +-- NO --> Is it definitely native digital?
              |
              +-- YES --> ocr=skip (save GPU cost)
              |
              +-- NO --> ocr=auto (let system detect)
```

## Common Use Cases

### High-Volume Loan Processing

```bash
# Fast processing, no audit trail needed
curl -X POST "http://localhost:8000/api/documents/?method=docling&ocr=skip" \
  -F "file=@loan.pdf"
```

### Compliance-Focused Extraction

```bash
# Full audit trail with character offsets
curl -X POST "http://localhost:8000/api/documents/?method=langextract&ocr=auto" \
  -F "file=@loan.pdf"
```

### Mixed Document Queue

```bash
# Let system optimize both method and OCR
curl -X POST "http://localhost:8000/api/documents/?method=auto&ocr=auto" \
  -F "file=@document.pdf"
```

### Scanned Document Recovery

```bash
# Force OCR for difficult scans
curl -X POST "http://localhost:8000/api/documents/?method=langextract&ocr=force" \
  -F "file=@old_scan.pdf"
```

## Error Handling

### Method-Specific Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `extraction_failed: LangExtract timeout` | LangExtract service overloaded | Retry or use `method=docling` |
| `ocr_failed: GPU service unavailable` | GPU cold start or circuit breaker open | Wait 2 minutes and retry |
| `no_text_extracted` | OCR=skip on scanned document | Change to `ocr=auto` or `ocr=force` |

### Fallback Behavior

When `method=auto` is used:
1. System attempts LangExtract first
2. On transient errors (timeout, 503, rate limit), retries 3 times
3. On fatal errors, falls back to Docling automatically
4. Final extraction method used is recorded in response

## Performance Considerations

| Scenario | Method | OCR | Avg Time | GPU Cost |
|----------|--------|-----|----------|----------|
| Native PDF, fast | docling | skip | 2-5s | $0 |
| Native PDF, audit | langextract | skip | 5-15s | $0 |
| Scanned PDF | any | force | 30-90s | ~$0.01 |
| Mixed (first request) | any | auto | 60-120s | ~$0.01 |
| Mixed (warm GPU) | any | auto | 15-30s | ~$0.01 |

Cold start time only applies to first OCR request after GPU scale-to-zero.

## See Also

- [Few-Shot Examples Guide](../guides/few-shot-examples.md) - Customizing LangExtract extractions
- [GPU Service Cost Guide](../guides/gpu-service-cost.md) - Managing OCR costs
- [CloudBuild Deployment Guide](../cloudbuild-deployment-guide.md) - Deploying the extraction service
