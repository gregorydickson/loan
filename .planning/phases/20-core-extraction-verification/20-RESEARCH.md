# Phase 20: Core Extraction Verification - Research

**Researched:** 2026-01-25
**Domain:** End-to-end document extraction verification, Chrome browser testing, production API testing
**Confidence:** HIGH

## Summary

Phase 20 focuses on **manual end-to-end verification** of the document extraction flows in production. Unlike automated testing phases, this phase requires human interaction via Chrome browser to verify that:

1. The production frontend URL loads and renders correctly
2. Document upload flow completes through the UI
3. Both extraction methods (Docling and LangExtract) process documents and return structured data
4. Scanned document handling triggers the GPU OCR service

The research confirms that the codebase already has all extraction infrastructure deployed (Phase 19 verified). The key challenge is addressing **known blockers** before verification can succeed:
- Database not configured (API endpoints return 500)
- Gemini API key placeholder (extraction will fail)

This phase is primarily **verification work, not development**. The testing approach follows standard manual QA patterns: navigate to URLs, interact with UI, observe responses, document results.

**Primary recommendation:** Before testing extraction flows, resolve the database and Gemini API key configuration. Then use Chrome browser with DevTools open to observe network requests and verify each requirement sequentially.

## Standard Stack

The established tools for this verification phase:

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| Chrome Browser | Latest | Primary test browser | Developer tools, network inspection, console logging |
| Chrome DevTools | Built-in | Network/console inspection | Observe API calls, debug CORS, view responses |
| curl | System | Command-line API testing | Baseline verification before UI testing |
| gcloud CLI | Latest | Secret/config management | Update database URL and Gemini API key |

### Supporting
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| Cloud Logging | GCP Console | Debug backend errors | When API calls fail with 500 |
| FastAPI Docs UI | Production | API exploration | Direct API testing at /docs |

### Production URLs (from Phase 19)
| Service | URL | Purpose |
|---------|-----|---------|
| Backend API | https://loan-backend-prod-fjz2snvxjq-uc.a.run.app | REST API endpoints |
| Frontend UI | https://loan-frontend-prod-fjz2snvxjq-uc.a.run.app | Document upload interface |
| GPU OCR | https://lightonocr-gpu-fjz2snvxjq-uc.a.run.app | Scanned document processing |
| API Docs | https://loan-backend-prod-fjz2snvxjq-uc.a.run.app/docs | FastAPI Swagger UI |

## Architecture Patterns

### Verification Workflow
```
1. Prerequisites
   ├── Fix database-url secret (point to loan_extraction DB)
   ├── Update gemini-api-key secret (real API key)
   └── Verify CloudBuild deployed CORS fixes

2. Baseline Verification (curl)
   ├── curl $BACKEND_URL/health → 200 + {"status":"healthy"}
   ├── curl $BACKEND_URL/api/documents/ → 200 + document list
   └── curl $FRONTEND_URL → 200 + HTML

3. Chrome Browser Testing
   ├── TEST-01: Navigate to frontend, verify page loads
   ├── TEST-02: Upload document, observe response
   ├── TEST-03: Test Docling extraction (method=docling)
   ├── TEST-04: Test LangExtract extraction (method=langextract)
   └── TEST-05: Test scanned document (triggers GPU OCR)

4. Results Documentation
   └── Document pass/fail with evidence for each requirement
```

### Pattern 1: Browser-Based Manual Testing
**What:** Use Chrome browser with DevTools to verify UI and API flows
**When to use:** All TEST-XX requirements
**Example:**
```
1. Open Chrome DevTools (F12)
2. Go to Network tab
3. Navigate to https://loan-frontend-prod-fjz2snvxjq-uc.a.run.app
4. Observe:
   - Page load completes with 200
   - No console errors
   - UI renders correctly
5. Document evidence: Screenshot + Network HAR export
```

### Pattern 2: Document Upload Verification
**What:** Upload a test document through the UI and verify processing
**When to use:** TEST-02, TEST-03, TEST-04
**Example:**
```
1. Navigate to Documents page
2. Select extraction method (Docling or LangExtract)
3. Select OCR mode (auto for native PDFs, force for scanned)
4. Drag and drop test PDF or click to select
5. Observe:
   - Upload indicator shows "Uploading..."
   - Success message appears with document ID
   - Document appears in list with status "completed"
   - Network shows POST /api/documents/ returning 201
6. Verify extraction data:
   - Click document to view details
   - Check borrower data was extracted
   - For LangExtract: verify char_start/char_end offsets present
```

### Pattern 3: GPU OCR Cold Start Handling
**What:** First request to GPU service will have 60-120s cold start
**When to use:** TEST-05 (scanned document)
**Example:**
```
1. Ensure GPU service has been idle (scale-to-zero)
2. Upload scanned PDF with ocr=force
3. Observe:
   - Upload succeeds immediately (async processing)
   - Status shows "processing" while OCR runs
   - After 1-2 minutes, status becomes "completed"
   - If status stays "processing" >5 min, check Cloud Logging
4. Evidence: Note processing time, check ocr_processed=true in response
```

### Anti-Patterns to Avoid
- **Testing before prerequisites fixed:** Database errors will fail all API calls
- **Expecting instant GPU OCR:** Cold start can take 2+ minutes on first request
- **Ignoring CORS errors:** Check browser console for CORS failures from frontend
- **Skipping DevTools:** Network tab reveals actual API responses vs UI display

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| API testing | Custom scripts | FastAPI /docs UI | Interactive, documented, handles auth |
| Network inspection | Proxy tools | Chrome DevTools | Built-in, standard, captures all requests |
| Screenshot capture | Custom tooling | Chrome screenshot (Ctrl+Shift+P) | Device emulation, full page capture |
| Log viewing | SSH to containers | GCP Cloud Logging console | Aggregated, searchable, filtered |

**Key insight:** This is manual verification, not automation. Use existing browser and GCP tools.

## Common Pitfalls

### Pitfall 1: Database Not Configured
**What goes wrong:** All API endpoints return 500 "Internal server error"
**Why it happens:** database-url secret points to memorygraph_auth DB, not loan_extraction
**How to avoid:**
```bash
# Create loan_extraction database on Cloud SQL instance
# Then update the secret:
echo "postgresql+asyncpg://user:pass@/loan_extraction?host=/cloudsql/memorygraph-prod:us-central1:memorygraph-db" | \
  gcloud secrets versions add database-url --data-file=-
```
**Warning signs:** Health check passes (200) but document list fails (500)

### Pitfall 2: Gemini API Key Placeholder
**What goes wrong:** LangExtract extraction fails with authentication error
**Why it happens:** gemini-api-key secret contains "PLACEHOLDER" not real key
**How to avoid:**
```bash
# Get your Gemini API key from https://makersuite.google.com/app/apikey
echo "YOUR_ACTUAL_API_KEY" | gcloud secrets versions add gemini-api-key --data-file=-
```
**Warning signs:** Docling works but LangExtract fails, error mentions "authentication"

### Pitfall 3: CORS Blocking Frontend Requests
**What goes wrong:** Frontend loads but API calls fail with CORS errors
**Why it happens:** Backend CORS middleware not matching frontend origin
**How to avoid:** Phase 19 fixed this with `allow_origin_regex=r"https://.*\.run\.app"`
**Warning signs:** Console shows "Access-Control-Allow-Origin" errors

### Pitfall 4: GPU Service Cold Start Timeout
**What goes wrong:** Scanned document upload seems stuck in "processing"
**Why it happens:** GPU service takes 60-120s cold start, timeout may occur
**How to avoid:**
- First request: expect 2-3 minute delay
- Subsequent requests (within 15 min): should be fast
- If stuck >5 min: check Cloud Logging for GPU service errors
**Warning signs:** Status stays "processing" indefinitely

### Pitfall 5: Using Wrong Test Documents
**What goes wrong:** Extraction returns empty data or fails
**Why it happens:** Test document doesn't contain extractable loan data
**How to avoid:** Use sample documents from loan-docs/Loan 214/:
- Native PDF: `Paystub- John Homeowner (Current).pdf`
- Complex PDF: `1040 and Schedule C (2023 and 2024) - John and Mary Homeowner.pdf`
- For scanned: create a scanned version or use old physical scans
**Warning signs:** Extraction completes but no borrower data found

### Pitfall 6: Testing LangExtract Without Understanding Offsets
**What goes wrong:** Verification claims "pass" but offsets not actually verified
**Why it happens:** LangExtract response includes char_start/char_end but tester doesn't check
**How to avoid:** Explicitly verify in response:
```json
{
  "extractions": [
    {
      "field": "borrower_name",
      "value": "John Homeowner",
      "char_start": 1523,
      "char_end": 1537
    }
  ]
}
```
**Warning signs:** LangExtract "passes" but response has no offset fields

## Code Examples

### Baseline API Verification (curl)

```bash
# Source: Production URLs from Phase 19

# Set URLs
BACKEND_URL="https://loan-backend-prod-fjz2snvxjq-uc.a.run.app"
FRONTEND_URL="https://loan-frontend-prod-fjz2snvxjq-uc.a.run.app"
GPU_URL="https://lightonocr-gpu-fjz2snvxjq-uc.a.run.app"

# Health check (should work regardless of DB config)
curl -s "${BACKEND_URL}/health"
# Expected: {"status":"healthy"}

# Document list (requires working DB)
curl -s "${BACKEND_URL}/api/documents/"
# Expected: {"documents":[],"total":0,"limit":100,"offset":0}
# If 500: database not configured

# Frontend loads
curl -s -o /dev/null -w "%{http_code}" "${FRONTEND_URL}"
# Expected: 200
```

### Document Upload via curl

```bash
# Upload with Docling extraction (default)
curl -X POST "${BACKEND_URL}/api/documents/" \
  -F "file=@/path/to/loan-docs/Loan 214/Paystub- John Homeowner (Current).pdf"

# Upload with LangExtract extraction
curl -X POST "${BACKEND_URL}/api/documents/?method=langextract" \
  -F "file=@/path/to/loan-docs/Loan 214/Paystub- John Homeowner (Current).pdf"

# Upload with forced OCR (for scanned documents)
curl -X POST "${BACKEND_URL}/api/documents/?method=docling&ocr=force" \
  -F "file=@/path/to/scanned-document.pdf"
```

### Check Document Status

```bash
# Get document by ID (from upload response)
DOC_ID="uuid-from-upload-response"
curl -s "${BACKEND_URL}/api/documents/${DOC_ID}"

# Check processing status
curl -s "${BACKEND_URL}/api/documents/${DOC_ID}/status"
# Expected: {"id":"...","status":"completed","page_count":2,"error_message":null}
```

### Fix Database Configuration

```bash
# Option 1: Update secret to point to correct database
# (Assumes loan_extraction database exists on Cloud SQL instance)
DB_URL="postgresql+asyncpg://postgres:PASSWORD@/loan_extraction?host=/cloudsql/memorygraph-prod:us-central1:memorygraph-db"
echo "$DB_URL" | gcloud secrets versions add database-url --data-file=-

# Option 2: Create database and run migrations
# Connect to Cloud SQL instance and create database:
# CREATE DATABASE loan_extraction;
# Then run alembic migrations from backend
```

### Fix Gemini API Key

```bash
# Get your API key from Google AI Studio
# https://makersuite.google.com/app/apikey

# Update the secret
GEMINI_KEY="your-actual-api-key"
echo "$GEMINI_KEY" | gcloud secrets versions add gemini-api-key --data-file=-

# Verify secret updated
gcloud secrets versions list gemini-api-key
```

## Test Document Inventory

Sample documents available in `loan-docs/Loan 214/`:

| Document | Type | Size | Best For |
|----------|------|------|----------|
| Paystub- John Homeowner (Current).pdf | Native PDF | 143KB | Quick upload test |
| W2 2024- John Homeowner.pdf | Native PDF | 181KB | Income extraction |
| EVOE - John Homeowner.pdf | Native PDF | 50KB | Employment verification |
| 1040 and Schedule C (2023 and 2024).pdf | Complex PDF | 621KB | Multi-page extraction |
| Checking - John Mary Homeowner (Current).pdf | Native PDF | 133KB | Account numbers |
| Title Report.pdf | Large PDF | 3.5MB | Stress test |

**For scanned document testing (TEST-05):**
- Create a scanned version by printing and scanning any above PDF
- Or use a known scanned document from your test files
- Alternatively: take a photo of a printed document and convert to PDF

## Verification Checklist

### Prerequisites
- [ ] Set GCP project: `gcloud config set project memorygraph-prod`
- [ ] Fix database-url secret (point to loan_extraction DB with schema)
- [ ] Fix gemini-api-key secret (real API key, not placeholder)
- [ ] Verify CORS fixes deployed via CloudBuild

### TEST-01: Frontend URL Loads
- [ ] Navigate to https://loan-frontend-prod-fjz2snvxjq-uc.a.run.app
- [ ] Page renders without errors
- [ ] Sidebar navigation visible (Documents, Borrowers, Architecture)
- [ ] No console errors in DevTools

### TEST-02: Document Upload Flow
- [ ] Click on Documents page
- [ ] Upload zone visible with method/OCR selectors
- [ ] Drag and drop or click to select a PDF
- [ ] Upload indicator shows progress
- [ ] Success message appears with document ID
- [ ] Document appears in list

### TEST-03: Docling Extraction
- [ ] Select method=docling, ocr=auto
- [ ] Upload Paystub PDF
- [ ] Status becomes "completed"
- [ ] extraction_method shows "docling"
- [ ] Borrower data extracted (check Borrowers page)

### TEST-04: LangExtract Extraction
- [ ] Select method=langextract, ocr=auto
- [ ] Upload same or different PDF
- [ ] Status becomes "completed"
- [ ] extraction_method shows "langextract"
- [ ] Response includes char_start/char_end offsets
- [ ] Borrower data extracted with source references

### TEST-05: Scanned Document + GPU OCR
- [ ] Prepare scanned PDF (or use ocr=force on any PDF)
- [ ] Select ocr=force
- [ ] Upload document
- [ ] Status shows "processing" (may take 1-2 min)
- [ ] Status becomes "completed"
- [ ] ocr_processed shows true
- [ ] Text was extracted successfully

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Selenium scripts | Manual browser testing | Phase 20 | Faster for one-time verification |
| Postman collections | FastAPI /docs UI | v2.0 | Interactive, auto-generated |
| Local testing | Production testing | Phase 19 | Real environment verification |
| Single extraction | Dual pipeline | v2.0 | Method selection in UI |

**Note:** This phase is intentionally manual testing. Future phases could add Playwright E2E automation.

## Open Questions

Things that couldn't be fully resolved:

1. **Database Schema Migration**
   - What we know: Need loan_extraction database with proper schema
   - What's unclear: Whether to create new DB or update existing database-url
   - Recommendation: Check with user - may need to run alembic migrations

2. **Scanned Document Source**
   - What we know: TEST-05 requires a scanned document
   - What's unclear: Whether loan-docs folder has any truly scanned PDFs
   - Recommendation: Create scanned test doc or use ocr=force on native PDF

3. **GPU Cold Start Timing**
   - What we know: 60-120 seconds typical
   - What's unclear: Exact timing for first request after long idle
   - Recommendation: Allow up to 5 minutes, check logs if longer

## Sources

### Primary (HIGH confidence)
- Phase 19 VERIFICATION.md - Production URLs and deployment status
- Phase 19 RESEARCH.md - gcloud CLI patterns, health check patterns
- Codebase exploration - extraction_router.py, documents.py, upload-zone.tsx
- docs/api/extraction-method-guide.md - Method and OCR parameter documentation

### Secondary (MEDIUM confidence)
- [API Testing Checklist Best Practices](https://www.techtarget.com/searchapparchitecture/tip/API-testing-checklist-and-best-practices) - Manual testing patterns
- [Creating API Test Cases Guide](https://www.stackhawk.com/blog/creating-test-cases-for-api-testing-a-comprehensive-guide-with-examples/) - Test case structure

### Tertiary (LOW confidence)
- [E2E Testing Tools 2026](https://www.virtuosoqa.com/post/best-end-to-end-testing-tools) - Tool landscape (not used in this phase)

## Metadata

**Confidence breakdown:**
- Prerequisites (database, API key): HIGH - Directly observed in Phase 19 verification
- Testing workflow: HIGH - Based on existing codebase and documentation
- GPU cold start: MEDIUM - Timing varies, documented from Phase 19
- Scanned document availability: LOW - Need to verify test files exist

**Research date:** 2026-01-25
**Valid until:** 2026-02-25 (30 days - stable verification patterns)

## Requirements Mapping

| Requirement | Research Finding | Confidence |
|-------------|------------------|------------|
| TEST-01: Navigate to frontend URL | Use Chrome, verify page loads, no console errors | HIGH |
| TEST-02: Document upload flow | Use upload-zone component, observe network, verify success message | HIGH |
| TEST-03: Docling extraction E2E | method=docling, verify status=completed, extraction_method=docling | HIGH |
| TEST-04: LangExtract extraction E2E | method=langextract, verify char_start/char_end offsets in response | HIGH |
| TEST-05: Scanned document + GPU OCR | ocr=force, expect 1-2 min processing, verify ocr_processed=true | MEDIUM |

## Blockers Summary

**Must fix before testing:**

1. **Database configuration**
   - Current: database-url points to memorygraph_auth (wrong schema)
   - Fix: Update secret to point to loan_extraction database with migrations run
   - Impact: Without this, all API endpoints return 500

2. **Gemini API key**
   - Current: gemini-api-key contains "PLACEHOLDER"
   - Fix: Update secret with real API key from Google AI Studio
   - Impact: Without this, LangExtract extraction fails

**Optional but recommended:**
- Verify CORS CloudBuild completed (check builds list)
- Prepare scanned test document for TEST-05
