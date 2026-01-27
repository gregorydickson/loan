# Loan Document Extraction System - System Design

**Version:** 2.0
**Last Updated:** 2026-01-27
**Authors:** Development Team

---

## Document Status

This document has been **VALIDATED and EXPANDED** against the actual codebase as of 2026-01-27.

### Changes from Previous Version
- ✅ Validated all component references against actual implementation
- ⚠️ **CRITICAL CORRECTION**: OCR fallback behavior corrected (see Section: OCR Service Architecture)
- ✅ Expanded v2.0 dual pipeline details
- ✅ Added monitoring and observability section
- ✅ Added testing strategy details
- ✅ Expanded error handling scenarios
- ✅ Added API design principles section

---

## Architecture Overview

### Executive Summary

The Loan Document Extraction System is an AI-powered platform that transforms unstructured loan documents into structured borrower data. At its core, the system solves a real problem in financial services: loan documents arrive in various formats (PDFs, Word documents, scanned images) with borrower information scattered across multiple pages in inconsistent layouts. Manually extracting this data is tedious, error-prone, and doesn't scale.

Our solution combines Docling for production-grade document parsing with Google's Gemini 3.0 LLM for intelligent data extraction. The system processes documents through a multi-stage pipeline that preserves complete traceability - every extracted field (SSN, income figures, account numbers) links back to its source document and page number. This source attribution is essential for audit trails and manual review workflows.

The architecture follows cloud-native principles: serverless compute on Cloud Run for cost efficiency, managed PostgreSQL for reliable storage, and Infrastructure as Code via Terraform for reproducible deployments. The frontend provides a clean dashboard for document uploads, status tracking, and borrower data exploration.

### High-Level Architecture

```mermaid
flowchart TB
    subgraph Frontend["Frontend Layer"]
        UI[Next.js Dashboard]
        Upload[Document Upload]
        Browse[Borrower Browser]
    end

    subgraph Backend["Backend Layer (FastAPI)"]
        API[REST API Routes]
        DocService[Document Service]
        ExtractService[Extraction Service]
        Repos[Repository Layer]
    end

    subgraph Processing["Document Processing"]
        Docling[Docling Processor]
        Classifier[Complexity Classifier]
        Chunker[Document Chunker]
        Gemini[Gemini LLM Client]
        Validator[Field Validator]
        Dedup[Deduplicator]
    end

    subgraph Storage["Data Storage"]
        GCS[(Cloud Storage)]
        PostgreSQL[(PostgreSQL)]
    end

    subgraph Infrastructure["GCP Infrastructure"]
        CloudRun[Cloud Run Services]
        CloudSQL[Cloud SQL]
        SecretMgr[Secret Manager]
        CloudTasks[Cloud Tasks Queue]
    end

    UI --> API
    Upload --> API
    Browse --> API

    API --> DocService
    API --> ExtractService
    DocService --> Repos
    ExtractService --> Repos

    DocService --> Docling
    DocService --> GCS

    ExtractService --> Classifier
    Classifier --> Chunker
    Chunker --> Gemini
    Gemini --> Validator
    Validator --> Dedup
    Dedup --> Repos

    Repos --> PostgreSQL

    CloudRun -.-> Backend
    CloudRun -.-> Frontend
    CloudSQL -.-> PostgreSQL
    SecretMgr -.-> Backend
```

### Technology Stack

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Frontend Framework** | Next.js | 14+ | React server components, App Router for modern SSR |
| **UI Components** | shadcn/ui | Latest | Accessible, customizable component library |
| **Styling** | Tailwind CSS | 4.0 | Utility-first CSS framework |
| **Backend Framework** | FastAPI | 0.115+ | Async Python API with OpenAPI docs |
| **Document Processing** | Docling | 2.70+ | PDF, DOCX, image parsing with OCR |
| **LLM Provider** | Google Gemini | 3.0 | Flash and Pro models for extraction |
| **Database** | PostgreSQL | 16 | Relational storage with ACID guarantees |
| **ORM** | SQLAlchemy | 2.0+ | Async ORM with repository pattern |
| **Cloud Platform** | Google Cloud | - | Cloud Run, Cloud SQL, Cloud Storage |
| **Infrastructure** | Terraform | 1.6+ | Infrastructure as Code |
| **Container Runtime** | Docker | - | Multi-stage builds for backend/frontend |
| **v2.0: Structured Extraction** | LangExtract | Latest | Character-level source grounding |
| **v2.0: GPU OCR** | LightOnOCR | 2-1B | Vision-language OCR model via vLLM |
| **Circuit Breaker** | aiobreaker | Latest | Fault tolerance for GPU service |
| **Retry Logic** | tenacity | Latest | Exponential backoff for transient errors |

---

## v2.0 Dual Extraction Pipeline

### Overview

v2.0 introduces a dual extraction pipeline allowing users to choose between:
- **Docling** (default): Fast, cost-effective extraction for standard documents
- **LangExtract**: Character-level source grounding for audit-sensitive use cases

This dual approach provides flexibility between cost/speed and precision/traceability based on document requirements.

### Pipeline Selection Flow

```mermaid
flowchart TD
    A[Document Upload] --> B{method param?}
    B -->|docling| C[Docling Pipeline]
    B -->|langextract| D[LangExtract Pipeline]
    B -->|auto| E{Document Analysis}
    E -->|simple| C
    E -->|complex| D

    C --> F{ocr param?}
    D --> F
    F -->|skip| G[Direct Text Extraction]
    F -->|auto| H[Scanned Detection]
    F -->|force| I[GPU OCR]
    H -->|scanned| I
    H -->|native| G
    I --> J[LightOnOCR Service]
    J -->|success| K[OCR Text]
    J -->|failure| L[Error: GPU Required]
    G --> M[Extraction]
    K --> M
    M --> N[BorrowerRecord + SourceReference]
```

### Character Offset Storage (DOCS-09)

LangExtract extractions include character-level offsets for precise source attribution:

```
SourceReference:
  - document_id: UUID
  - page_number: int
  - section_type: str
  - char_start: int | null  # Character offset (LangExtract only)
  - char_end: int | null    # Character offset (LangExtract only)
  - snippet: str            # Extracted text snippet
```

For Docling extractions, `char_start` and `char_end` remain null (backward compatible with v1.0).

**Usage:**
- When `char_start`/`char_end` are populated, UI can highlight exact source text
- Offsets are relative to the document's extracted markdown content
- OffsetTranslator component handles coordinate transformation between raw text and Docling markdown

**Character Offset Precision:**
Character offsets enable:
1. **Exact Text Highlighting**: UI can highlight the precise substring in the original document
2. **Audit Trail**: Compliance teams can verify exact source of extracted data
3. **Dispute Resolution**: Users can see exactly what the system read

### OCR Service Architecture

**⚠️ CRITICAL NOTE**: The system does NOT fall back to Docling OCR when GPU service fails. This is a design decision to keep container images small by excluding RapidOCR models. Scanned documents require a healthy GPU service to process.

```mermaid
flowchart LR
    A[Backend] -->|HTTP| B[LightOnOCR Cloud Run]
    B -->|vLLM| C[LightOnOCR-2-1B]
    A -->|on failure| D[Raise DocumentProcessingError]
    B -.->|scale-to-zero| E[0 instances when idle]
```

LightOnOCR runs on L4 GPU with scale-to-zero configuration:
- **Cold start:** 60-120 seconds when scaling from zero
- **Health check with retry:** Up to 180 seconds (3 minutes) wait time for cold starts
- **Circuit breaker:** 3 failures triggers open state (60 second timeout)
- **Memory:** 32Gi with 80% GPU utilization target
- **Authentication:** Internal-only via service account OIDC tokens

**Circuit Breaker States:**

| State | Behavior | Trigger |
|-------|----------|---------|
| **Closed** | All requests pass through to GPU service | Normal operation |
| **Open** | All requests immediately raise `CircuitBreakerError` | 3 consecutive failures |
| **Half-Open** | Single test request allowed through | After 60 second timeout |

**Error Handling:**
When GPU OCR fails, the system:
1. Logs error with document ID and failure reason
2. Raises `DocumentProcessingError` with descriptive message
3. Document status set to `FAILED` with error message
4. User sees clear error indicating GPU service is required

**Why No Docling OCR Fallback?**
- RapidOCR models add ~500MB to container image
- GPU service provides superior OCR quality
- Clear error messages guide users to retry when service is available
- Cost optimization: avoid including models for rare fallback scenarios

### v2.0 Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **ExtractionRouter** | `backend/src/extraction/extraction_router.py` | Dispatches to Docling or LangExtract based on method parameter |
| **OCRRouter** | `backend/src/ocr/ocr_router.py` | Routes to LightOnOCR GPU service with circuit breaker protection |
| **LangExtractProcessor** | `backend/src/extraction/langextract_processor.py` | Wraps langextract library with few-shot examples |
| **LightOnOCRClient** | `backend/src/ocr/lightonocr_client.py` | HTTP client for GPU OCR service with retry logic |
| **ScannedDetector** | `backend/src/ocr/scanned_detector.py` | Detects scanned vs native PDF documents |
| **OffsetTranslator** | `backend/src/extraction/offset_translator.py` | Translates LangExtract offsets to Docling markdown coordinates |

### Extraction Router Error Handling

The `ExtractionRouter` implements sophisticated retry and fallback logic:

**Error Classification:**
- **Transient Errors** (retryable): 503, 429, timeout, rate limit
  - Retry 3 times with exponential backoff (2s, 4s, 8s)
  - If all retries fail in auto mode, fall back to Docling
- **Fatal Errors** (non-retryable): 400, 401, validation errors
  - Immediate fallback to Docling in auto mode
  - Raise error immediately in langextract-only mode

**Mode Behaviors:**
- `method=langextract`: No fallback, raises errors directly
- `method=docling`: Uses Docling only, no LangExtract attempt
- `method=auto`: Try LangExtract with Docling fallback on any error

### API Parameters

Upload endpoint supports dual pipeline selection:

```
POST /api/documents?method={method}&ocr={ocr}

method: "docling" (default) | "langextract" | "auto"
  - docling: Use Docling extraction (v1.0 behavior)
  - langextract: Use LangExtract (no fallback, fails on error)
  - auto: Try LangExtract, fall back to Docling on error

ocr: "auto" (default) | "force" | "skip"
  - auto: Detect scanned pages and apply GPU OCR if needed
  - force: Always apply GPU OCR regardless of content
  - skip: Never apply OCR (fastest, native PDFs only)
```

**Examples:**
```bash
# Default: Docling extraction with auto OCR detection
curl -F "file=@loan.pdf" http://api/documents

# LangExtract with forced OCR (for poor quality native PDFs)
curl -F "file=@loan.pdf" "http://api/documents?method=langextract&ocr=force"

# Fast path: Docling without OCR (native PDF, no scanned content)
curl -F "file=@loan.pdf" "http://api/documents?method=docling&ocr=skip"
```

---

## Component Interaction

### Document Upload and Extraction Flow

The following sequence diagram shows how a document flows through the system from upload to extracted borrower data:

```mermaid
sequenceDiagram
    participant User
    participant Frontend as Next.js Frontend
    participant API as FastAPI Backend
    participant GCS as Cloud Storage
    participant Docling as Docling Processor
    participant LLM as Gemini LLM
    participant DB as PostgreSQL

    User->>Frontend: Upload document
    Frontend->>API: POST /api/documents (multipart)

    API->>API: Compute SHA-256 hash
    API->>DB: Check for duplicate hash

    alt Document exists
        DB-->>API: Existing document found
        API->>DB: Delete existing document
        Note over API,DB: Duplicate replacement policy
    end

    API->>GCS: Store original file
    GCS-->>API: Storage URI
    API->>DB: Create document record (status: pending)

    API->>Docling: Process document
    Docling->>Docling: Extract text with page boundaries
    Docling->>Docling: Run OCR if needed
    Docling-->>API: DocumentContent (text, pages, tables)

    API->>DB: Update status: processing

    API->>LLM: Assess complexity
    LLM-->>API: ComplexityAssessment

    loop For each chunk
        API->>LLM: Extract borrowers (Flash or Pro)
        LLM-->>API: ExtractedBorrowers
    end

    API->>API: Deduplicate borrowers
    API->>API: Validate fields (SSN, phone, ZIP)
    API->>API: Calculate confidence scores
    API->>API: Check consistency

    API->>DB: Store borrowers with sources
    API->>DB: Update status: completed

    API-->>Frontend: Document response

    Frontend-->>User: Show status/results
```

---

## Data Flow

### Entity Relationship Model

The system uses a relational model that maintains complete traceability from extracted data back to source documents:

```mermaid
erDiagram
    Document ||--o{ BorrowerDocument : "extracted_from"
    Borrower ||--o{ BorrowerDocument : "appears_in"
    Borrower ||--o{ IncomeRecord : "has"
    Borrower ||--o{ SourceReference : "traced_to"
    Document ||--o{ SourceReference : "contains"
    Borrower ||--o{ AccountNumber : "has"

    Document {
        uuid id PK
        string filename
        string file_hash UK
        enum file_type
        int file_size_bytes
        string gcs_uri
        enum status
        string error_message
        int page_count
        datetime created_at
        datetime processed_at
        string extraction_method "v2.0: docling/langextract"
        boolean ocr_processed "v2.0: OCR applied flag"
    }

    Borrower {
        uuid id PK
        string name
        string ssn_hash "SHA-256 hashed"
        string address_json "JSON serialized Address"
        decimal confidence_score "0.00-1.00"
        datetime created_at
    }

    IncomeRecord {
        uuid id PK
        uuid borrower_id FK
        decimal amount "12,2 precision"
        string period "monthly/annual/etc"
        int year
        string source_type "W-2/1099/paystub/etc"
        string employer
    }

    AccountNumber {
        uuid id PK
        uuid borrower_id FK
        string number
        string account_type "loan/bank/credit"
    }

    SourceReference {
        uuid id PK
        uuid borrower_id FK
        uuid document_id FK
        int page_number
        string section "section name"
        string snippet "extracted text"
        int char_start "v2.0: character offset (nullable)"
        int char_end "v2.0: character offset (nullable)"
    }

    BorrowerDocument {
        uuid borrower_id FK
        uuid document_id FK
    }
```

### Source Attribution Chain

Every piece of extracted data traces back to its origin. This is critical for audit trails and manual verification:

1. **Document Upload**: Original file stored in GCS with SHA-256 hash for deduplication
2. **Page Extraction**: Docling preserves page boundaries during text extraction
3. **Chunk Processing**: Each chunk knows its character position in the original document
4. **LLM Extraction**: Borrower data extracted with page number and text snippet
5. **Source Reference**: Created linking borrower field → document → page → snippet
6. **v2.0 Character Offsets**: LangExtract adds precise char_start/char_end for exact positioning

This chain allows a reviewer to click on any extracted field (like an SSN or income amount) and see exactly which page and section of which document it came from. With v2.0 character offsets, the UI can highlight the exact text span.

### Data Quality Pipeline

Data flows through multiple validation stages:

1. **Format Validation**: SSN (XXX-XX-XXXX), phone (US format via phonenumbers library), ZIP (5-digit or 5+4)
2. **Deduplication**: Matches borrowers across chunks using SSN > account numbers > fuzzy name matching
3. **Consistency Checks**: Flags income anomalies (>50% drop or >300% spike), address conflicts
4. **Confidence Scoring**: Combines field completeness, validation results, and source count into 0.0-1.0 score

Records with confidence below 0.7 are flagged for manual review.

**Deduplication Algorithm Priority:**
```python
# Priority order for matching duplicates across chunks:
1. Exact SSN match (highest confidence)
2. Overlapping account numbers (2+ matching accounts)
3. Fuzzy name match (90%+) + same ZIP code
4. Very high name match (95%+) alone
5. Moderate name match (80%+) + last 4 SSN digits match

# Uses rapidfuzz library for efficient fuzzy string matching
```

---

## Document Extraction Pipeline

### Pipeline Overview

The extraction pipeline transforms raw documents into structured borrower records through a series of coordinated stages:

```mermaid
flowchart LR
    subgraph Ingestion["1. Ingestion"]
        Upload[File Upload]
        Hash[SHA-256 Hash]
        Store[GCS Storage]
        Parse[Docling Parse]
    end

    subgraph Analysis["2. Analysis"]
        Complexity[Complexity Assessment]
        Chunk[Document Chunking]
    end

    subgraph Extraction["3. Extraction"]
        LLM[LLM Extraction]
        Validate[Field Validation]
    end

    subgraph Consolidation["4. Consolidation"]
        Dedup[Deduplication]
        Consistency[Consistency Check]
        Score[Confidence Scoring]
    end

    subgraph Storage["5. Storage"]
        DB[(PostgreSQL)]
    end

    Upload --> Hash --> Store --> Parse
    Parse --> Complexity --> Chunk
    Chunk --> LLM --> Validate
    Validate --> Dedup --> Consistency --> Score
    Score --> DB
```

### Stage Details

#### Stage 1: Document Ingestion

**File Upload and Hashing**
- Accept PDF, DOCX, PNG, JPG files via multipart form upload
- Compute SHA-256 hash before any processing for duplicate detection
- Store original file in Google Cloud Storage with structured path: `documents/{year}/{month}/{document_id}/{filename}`
- Max file size: Configurable (default 50MB for demo, production typically 100MB+)

**Duplicate Handling**
When duplicate hash detected:
1. Existing document with same hash is deleted (cascade deletes borrowers, references)
2. New upload proceeds with fresh processing
3. Rationale: Allows users to re-process documents with updated settings

**Docling Processing**
- Create fresh DocumentConverter per document (prevents memory leaks per GitHub issue #2209)
- Extract text as Markdown preserving structure (headings, tables, lists)
- Maintain page-level text boundaries for source attribution
- Run OCR automatically on scanned/image-based documents
- Configuration: `enable_ocr=True`, `enable_tables=True`, `max_pages=100`

**Page Boundary Preservation:**
Docling outputs page markers:
```markdown
## Page 1

[page 1 content here...]

## Page 2

[page 2 content here...]
```

These markers are critical for source attribution - the system parses them to determine which page each extracted field came from.

#### Stage 2: Complexity Assessment

**Classification Criteria**
- **STANDARD** (use Flash model): Single-borrower, clear scan, <10 pages
- **COMPLEX** (use Pro model): Triggers if any of:
  - Multiple borrower indicators (co-borrower, joint applicant, spouse mentions)
  - Large documents (>10 pages)
  - Poor scan quality (>3 illegible markers, garbled characters)
  - Handwritten content detected

**Complexity Assessment Prompt:**
The classifier uses a structured prompt that asks Gemini to analyze:
1. Number of distinct borrower entities mentioned
2. Document length and structure complexity
3. Scan quality indicators (garbled text, unreadable sections)
4. Presence of handwritten content

**Chunking Strategy**
- Maximum chunk size: 16,000 characters (~4,000 tokens at 4 chars/token)
- Overlap between chunks: 800 characters (~200 tokens)
- Paragraph-aware splitting: Searches last 20% of chunk for `\n\n` to avoid splitting entities
- Each chunk tracks its start/end character positions in original document

**Why Chunking?**
- Gemini context window is 2M tokens but large contexts degrade performance
- Smaller chunks provide better extraction quality
- Overlap ensures entities spanning chunk boundaries aren't lost
- Enables parallel processing (future optimization)

#### Stage 3: LLM Extraction

**Gemini API Client**
- Models: `gemini-3-flash-preview` (default) or `gemini-3-pro-preview` (complex docs)
- Temperature: 1.0 (required for Gemini 3 optimal performance)
- Response format: `application/json` with Pydantic schema for structured output
- Retry logic: Exponential backoff with jitter (1s initial, 60s max, 3 attempts)
- **IMPORTANT**: No `max_output_tokens` set (causes None response with structured output)

**Structured Output Schema:**
```python
class ExtractedBorrower(BaseModel):
    name: str
    ssn: str | None
    phone: str | None
    email: str | None
    address: Address | None
    income_records: list[IncomeRecord]
    account_numbers: list[AccountNumber]
    page_number: int  # Which page this data came from
```

**Extraction Prompt Engineering:**
The prompt includes:
1. **Role**: "You are a document extraction specialist..."
2. **Task**: "Extract all borrower information from loan documents..."
3. **Schema**: Pydantic model JSON schema defining exact structure
4. **Field Guidance**: What each field should contain with examples
5. **Edge Cases**: How to handle missing data, multiple borrowers, etc.

**v2.0: LangExtract Few-Shot Learning**
LangExtract uses few-shot examples instead of schema:
- Examples define extraction patterns by example
- Library handles schema inference from examples
- Character offsets computed automatically by library
- Examples stored in `examples/__init__.py`

#### Stage 4: Validation

**Field Validation**
- **SSN**: Regex `^\d{3}-?\d{2}-?\d{4}$`, warns if dashes missing, normalizes to XXX-XX-XXXX format
- **Phone**: phonenumbers library for robust US validation, normalizes to E.164 format
- **ZIP**: `^\d{5}(-\d{4})?$` for 5-digit or 5+4 format
- **Year**: Range check 1950 to current year + 1
- **Email**: Basic RFC 5322 validation

**SSN Normalization:**
```python
# Input variations handled:
"123456789"     → "123-45-6789"
"123 45 6789"   → "123-45-6789"
"123-45-6789"   → "123-45-6789" (already normalized)
```

**Deduplication**
Priority order for matching duplicates:
1. Exact SSN match
2. Overlapping account numbers (2+ shared accounts)
3. Fuzzy name (90%+) + same ZIP code
4. Very high name match (95%+) alone
5. Moderate name (80%+) + last 4 SSN digits match

Uses rapidfuzz library for efficient fuzzy matching.

**Merge Strategy:**
When duplicates detected:
- Combine all income records (keep all, mark source document)
- Union of account numbers (deduplicated)
- Take address from highest confidence source
- Aggregate all source references
- Recalculate confidence score based on merged data

**Consistency Checking**
Runs after deduplication to flag issues for human review:
- **Income Anomalies**:
  - Drop >50% year-over-year → flag "significant_income_drop"
  - Spike >300% year-over-year → flag "significant_income_spike"
- **Address Conflicts**: Different addresses in same document for same borrower
- **SSN Conflicts**: Different SSNs for same name (by fuzzy match)

Inconsistencies are logged but don't block processing. They're stored as warnings in the database for UI display.

#### Stage 5: Confidence Scoring

Formula components:
- **Field Completeness** (40%): Weighted by field importance
  - High importance: SSN, name (5 points each)
  - Medium importance: phone, address (3 points each)
  - Low importance: email, account numbers (1 point each)
- **Format Validation** (30%): Bonus for passing all format checks
  - All validations pass: 30 points
  - Some failures: proportional reduction
- **Source Count** (20%): Bonus for data corroborated across multiple sources
  - 1 source: 0 points
  - 2 sources: 10 points
  - 3+ sources: 20 points
- **No Penalties** (10%): Bonus for no validation warnings
  - No warnings: 10 points
  - Has warnings: 0 points

**Score Calculation:**
```
confidence = (completeness_score + validation_score + source_score + penalty_score) / 100
confidence = min(max(confidence, 0.0), 1.0)  # Clamp to [0.0, 1.0]
```

Records with confidence < 0.7 are flagged for manual review.

**Confidence Score Interpretation:**
- **0.9-1.0**: Excellent - all fields complete, validated, multiple sources
- **0.8-0.9**: Good - most fields complete, validated
- **0.7-0.8**: Acceptable - key fields present, may have minor issues
- **Below 0.7**: Review Required - missing critical fields or validation failures

---

## AI/LLM Integration

### Model Selection Strategy

The system uses dynamic model selection to balance cost and accuracy:

| Scenario | Model | Rationale |
|----------|-------|-----------|
| Single borrower, clear scan, <10 pages | Flash | Faster, cheaper, sufficient accuracy |
| Multiple borrowers detected | Pro | Better at tracking multiple entities |
| Poor scan quality | Pro | Superior reasoning through noise |
| Handwritten content | Pro | Better OCR interpretation |
| Large documents (>10 pages) | Pro | Better context handling |

**Cost-Benefit Analysis:**
- Flash: ~$0.001 per 5-page document
- Pro: ~$0.012 per 5-page document (12x more expensive)
- Complexity classifier routes 70-80% documents to Flash
- Average cost per document: ~$0.003 (assuming 75% Flash, 25% Pro)

### Prompt Engineering

**System Prompt Structure:**
```
You are a document extraction specialist for loan documents.

Your task is to extract borrower information including:
- Personal details (name, SSN, phone, email)
- Address information
- Income records with employer and timeframe
- Account numbers (loan, bank, credit)

Guidelines:
- Extract all borrowers found (there may be multiple)
- If a field is not present, omit it or use null
- For income, specify the period (monthly/annual/etc)
- Preserve exact formatting of SSN and account numbers
- Use the page number where you found the data

[JSON schema provided via structured output]
```

**Structured Output Benefits:**
- Guarantees valid JSON matching expected structure
- No post-processing parsing needed
- Eliminates common LLM errors (invalid JSON, incorrect types)
- Validation happens at Pydantic layer with clear error messages

**Few-Shot vs Structured Output:**
- **Docling Pipeline**: Uses structured output with JSON schema
- **LangExtract Pipeline**: Uses few-shot examples
- LangExtract examples show input/output pairs demonstrating extraction patterns
- Examples include character offset annotations for training

### Cost Analysis

| Model | Input Cost | Output Cost | Avg Doc (5 pages) | Notes |
|-------|------------|-------------|-------------------|-------|
| Flash | $0.10/1M tokens | $0.40/1M tokens | ~$0.001 | Default for standard docs |
| Pro | $1.25/1M tokens | $5.00/1M tokens | ~$0.012 | 12x more expensive |

**Token Estimation:**
```
5-page loan document:
- Input: ~10,000 characters = ~2,500 tokens
- Prompt overhead: ~500 tokens
- Output: ~500 tokens (structured JSON)
- Total per chunk: ~3,500 tokens

Flash cost: (3000 * 0.10/1M) + (500 * 0.40/1M) = $0.0005
Pro cost: (3000 * 1.25/1M) + (500 * 5.00/1M) = $0.0062
```

**Cost Optimization Strategies:**
1. Complexity classifier routes 70-80% of documents to Flash
2. Chunking prevents token limit issues without sacrificing context
3. Structured output reduces output tokens vs free-form responses
4. Future: Cache common document structures to reduce input tokens

### Token Usage Tracking

Every LLM call tracks:
- `input_tokens`: Prompt size including document chunk
- `output_tokens`: Response size (structured JSON)
- `latency_ms`: Request duration (network + processing)
- `model_used`: Which model was called (flash/pro)
- `finish_reason`: Why generation stopped (stop/length/error)

This data feeds into:
- Cost monitoring dashboards
- Performance optimization (identify slow requests)
- Model comparison (Flash vs Pro accuracy)
- Capacity planning (tokens/day usage trends)

**Monitoring Metrics:**
```
# Prometheus metrics (future implementation)
llm_request_duration_seconds{model="flash"}
llm_request_tokens_total{model="flash", type="input"}
llm_request_tokens_total{model="flash", type="output"}
llm_request_errors_total{model="flash", error_type="rate_limit"}
llm_cost_usd_total{model="flash"}
```

---

## Error Handling

### Error Categories and Recovery

| Error Type | Detection | Recovery Strategy | User Impact |
|------------|-----------|-------------------|-------------|
| **Rate Limit (429)** | Gemini API response | Exponential backoff with jitter, 3 retries | Brief delay, transparent |
| **Server Error (500)** | Gemini API response | Retry up to 3 times, fail document if exhausted | Document marked failed |
| **Timeout** | Request exceeds limit | Retry with smaller chunk size (future) | Document marked failed |
| **Validation Failure** | Pydantic ValidationError | Log error, continue with valid records | Partial data saved |
| **Parse Error** | JSON decode failure | Mark document failed, log raw response | Document marked failed |
| **Document Corruption** | Docling exception | Mark document failed with error message | Clear error message |
| **GPU Service Down** | LightOnOCR health check failure | CircuitBreaker prevents cascading failures | Document marked failed with retry instructions |
| **GPU Cold Start** | Health check timeout | Extended wait (up to 180s) with retries | Slower processing, transparent |

### Status Tracking

Documents progress through states:

```
PENDING → PROCESSING → COMPLETED
                    → FAILED (with error_message)
```

**State Transitions:**
- **PENDING**: Document uploaded, in queue (Cloud Tasks) or about to process (sync mode)
- **PROCESSING**: Active extraction in progress
- **COMPLETED**: Extraction succeeded, borrowers stored
- **FAILED**: Extraction failed at any stage, error_message contains details

The frontend polls document status every 2 seconds while processing, stops polling when terminal state (COMPLETED/FAILED) reached.

**Status API Optimization:**
Separate lightweight status endpoint (`GET /api/documents/{id}/status`) returns only:
- document_id
- status
- page_count (if completed)
- error_message (if failed)

This avoids loading full document + relationships for frequent polls.

### Graceful Degradation

When errors occur during extraction:
1. **Chunk-Level Failures**: Individual chunk failures don't fail entire document
   - Other chunks continue processing
   - Partial borrower data saved from successful chunks
2. **Validation Errors**: Logged but valid data is preserved
   - Invalid fields omitted, valid fields stored
   - Confidence score reflects completeness
3. **Consistency Warnings**: Flag issues without blocking storage
   - Warnings stored as metadata
   - UI displays warnings for human review
4. **Transient LLM Errors**: Exponential backoff with jitter
   - Retries with increasing delays (1s, 2s, 4s)
   - Max 3 attempts before failing

### Error Response Format

```json
{
  "id": "uuid",
  "filename": "loan.pdf",
  "status": "failed",
  "error_message": "Document processing failed: GPU OCR service unavailable. The document appears to be scanned and requires OCR. Please retry when the service is available.",
  "details": {
    "error_type": "ocr_service_unavailable",
    "retryable": true,
    "retry_after": "60s"
  }
}
```

---

## Scaling Analysis

### Current Architecture Characteristics

**Bottlenecks Identified:**
1. **Docling Processing**: CPU-intensive, ~2-5s per page depending on complexity
2. **LLM API Calls**: Network-bound, ~1-3s per chunk (Flash), ~3-8s (Pro)
3. **GPU OCR**: Cold start penalty (60-120s), GPU memory constraints
4. **Database Writes**: Minimal overhead, async SQLAlchemy handles well

**Current Capacity (Single Instance):**
- ~100-200 documents/day with sequential processing
- Limited by Cloud Run cold start latency on first request
- GPU service scale-to-zero adds latency for scanned documents

### 10x Scale Projections (1,000-2,000 docs/day)

| Resource | Current | 10x Projection | Mitigation |
|----------|---------|----------------|------------|
| **Cloud Run Instances** | 0-1 | 3-5 concurrent | Auto-scaling handles this automatically |
| **LLM API Costs** | ~$1/day | ~$10-15/day | Complexity classifier optimization already in place |
| **Database Connections** | 1-2 | 10-20 | Connection pooling (already configured, max 20) |
| **GCS Storage** | ~100 MB/day | ~1 GB/day | Lifecycle policies (NEARLINE at 90d, DELETE at 365d) |
| **PostgreSQL Storage** | ~50 MB/day | ~500 MB/day | Cloud SQL auto-resize enabled |
| **GPU Service** | 0-1 instance | 1-2 instances | Auto-scaling with min_instances=0, max_instances=3 |

**Optimizations Already In Place:**
- `selectinload()` for eager loading prevents N+1 queries
- Repository pattern enables query optimization without API changes
- Async SQLAlchemy for non-blocking database operations
- Circuit breaker prevents GPU service overload
- Connection pooling prevents database connection exhaustion

### 100x Scale Projections (10,000-20,000 docs/day)

| Resource | 100x Projection | Required Changes |
|----------|-----------------|------------------|
| **Cloud Run** | 10-15 concurrent | Increase max_instance_count from 10 to 50 |
| **Cloud Tasks** | 10/s rate, 5 concurrent | Already handles backpressure, increase rate limit |
| **Database** | 100-200 connections | Move to Cloud SQL HA, increase tier to db-n1-standard-4 |
| **LLM Costs** | $100-150/day | Batch processing, caching common patterns |
| **GCS** | 10 GB/day | Already handled by lifecycle policies |
| **GPU Service** | 3-5 concurrent | Increase max_instances, consider regional deployment |

**Architecture Changes Needed at 100x:**
1. **Batch Processing**: Group documents for bulk LLM calls
   - Submit 5-10 documents in single batch
   - Reduces per-request overhead
   - Requires batch endpoint in Gemini API
2. **Result Caching**: Cache extraction results for similar documents
   - Hash document content similarity
   - Reuse extraction for template-based documents
   - 20-30% cache hit rate expected
3. **Read Replicas**: Add Cloud SQL read replica for query load
   - Route all GET requests to replica
   - Master handles writes only
4. **CDN**: Put frontend behind Cloud CDN for static assets
   - Reduce Cloud Run frontend load
   - Improve global latency
5. **Async Processing**: Move all extraction to Cloud Tasks
   - Currently: Sync in dev, async in prod via Tasks
   - Change: Always async, immediate 202 response

### Scaling Projections Table

| Scale | Docs/Day | Est. Monthly Cost | Architecture Tier | Key Changes |
|-------|----------|-------------------|-------------------|-------------|
| Current | 100-200 | $50-100 | Single instances, sync processing | None |
| 10x | 1,000-2,000 | $300-500 | Auto-scaling, connection pooling | None (already supported) |
| 100x | 10,000-20,000 | $2,000-3,000 | Queue-based, read replicas, caching | Batch processing, caching |
| 1000x | 100,000+ | $15,000+ | Distributed processing, custom models | Regional deployment, dedicated LLM |

**1000x Scale Considerations:**
At 100k+ docs/day, architectural paradigm shifts required:
- **Custom LLM Deployment**: Fine-tune own models, deploy on GKE with GPUs
- **Distributed Processing**: Multi-region Cloud Run deployments
- **Data Sharding**: Partition database by customer/region
- **Event Streaming**: Replace Cloud Tasks with Pub/Sub for real-time processing
- **Cost Optimization**: Self-hosted OCR models, bulk LLM contracts

---

## Security Considerations

### Network Security

**VPC Configuration:**
- Private VPC with CIDR 10.0.0.0/16 for internal resources
- Cloud SQL has private IP only (no public endpoint)
- Cloud Run uses Direct VPC Egress for database access
- `PRIVATE_RANGES_ONLY` egress policy limits outbound traffic to:
  - Cloud SQL private IP
  - Google APIs (via Private Google Access)
  - GPU OCR service (via internal service account auth)

**Access Control:**
- Cloud Run services publicly accessible (demo application)
- Database access only from Cloud Run service account
- GPU OCR service: Internal-only, OIDC token auth
- No SSH or bastion hosts needed (Cloud SQL proxy for admin access)

**Service Account Permissions:**
```
backend-sa@project.iam.gserviceaccount.com:
  - Cloud SQL Client (cloudsql.client)
  - Secret Manager Secret Accessor (secretmanager.secretAccessor)
  - Storage Object Admin (storage.objectAdmin) for GCS bucket
  - Service Account Token Creator (iam.serviceAccountTokenCreator) for GPU service auth

gpu-ocr-sa@project.iam.gserviceaccount.com:
  - Cloud Run Invoker (run.invoker) - limited to backend-sa only
```

### Secrets Management

All sensitive configuration stored in Google Secret Manager:
- `DATABASE_URL`: PostgreSQL connection string with password
- `GEMINI_API_KEY`: Google AI API key for LLM access

**Secret Access Pattern:**
```
Terraform → Secret Manager (secret data)
         → Cloud Run (secret mount as env var via secret_key_ref)
         → Backend application (reads from environment)
```

Secrets:
- Never stored in Terraform state (state file contains only secret name/reference)
- Never logged (FastAPI startup logs filter secret values)
- Rotatable without code changes (update secret, restart service)
- Versioned in Secret Manager for rollback capability

### Container Security

**Non-Root Execution:**
```dockerfile
# Backend
RUN useradd --create-home --shell /bin/bash appuser
USER appuser
WORKDIR /home/appuser/app

# Frontend
USER node
WORKDIR /app
```

**Minimal Base Images:**
- Backend: `python:3.12-slim` (smaller attack surface than full python image)
- Frontend: `node:20-alpine` (minimal Linux, no unnecessary packages)
- GPU OCR: `nvidia/cuda:12.1.0-runtime-ubuntu22.04` (only CUDA runtime, no build tools)

**Dependency Scanning:**
```bash
# Trivy vulnerability scanning
trivy image gcr.io/project/backend:latest
trivy image gcr.io/project/frontend:latest

# Python dependency audit
pip-audit --requirement requirements.txt
```

### Data Handling

**PII Considerations:**
- **SSN**: Stored as SHA-256 hash (`ssn_hash` column), original SSN never persisted
- **Address**: Stored as JSON in `address_json` column (not indexed for privacy)
- **Income**: Stored as structured records (amounts visible for processing)
- **Documents**: Original files stored in GCS (contain full PII)
- **Logs**: Structured logging with field filtering (PII fields redacted)

**SSN Hashing Strategy:**
```python
import hashlib

def hash_ssn(ssn: str) -> str:
    """Hash SSN with SHA-256 for privacy.

    Original SSN never stored in database.
    Hash enables duplicate detection without storing plaintext.
    """
    normalized = ssn.replace("-", "").replace(" ", "")
    return hashlib.sha256(normalized.encode()).hexdigest()
```

**GCS File Encryption:**
- Default: Google-managed encryption keys (GMEK)
- All data encrypted at rest automatically
- TLS 1.3 for data in transit
- Files not publicly accessible (Uniform bucket-level access)

**Production Recommendations (not implemented in demo):**
1. **Field-Level Encryption**: Encrypt SSN at application level before hashing
   - Use Google Cloud KMS for key management
   - Envelope encryption for performance
2. **Data Retention Policies**: Automatic purging of old records
   - Documents >365 days deleted from GCS
   - Database records archived after 730 days
3. **Audit Logging**: Track PII access for compliance
   - Cloud Audit Logs for GCS access
   - Application-level access logs for database queries
4. **RBAC**: Role-based access control for multi-tenant deployment
   - Customer admins can only see own documents
   - System admins have full access

**GDPR/CCPA Considerations:**
For production deployment with EU/CA users:
- Right to erasure: DELETE endpoint permanently removes all data
- Right to access: Export endpoint provides all data for a borrower
- Data minimization: Only collect necessary fields
- Consent tracking: Add consent_date, consent_ip fields to Borrower table

---

## Deployment Architecture

### Infrastructure as Code

All GCP resources managed via Terraform:

```
infrastructure/terraform/
├── main.tf              # Provider config, API enablement, backend config
├── variables.tf         # Input variables with descriptions and defaults
├── vpc.tf               # Private network, subnets, Private Google Access
├── iam.tf               # Service accounts, IAM roles, bindings
├── cloud_sql.tf         # PostgreSQL instance with private IP
├── secrets.tf           # Secret Manager secrets (DB URL, API keys)
├── cloud_storage.tf     # Document storage bucket with lifecycle policies
├── cloud_tasks.tf       # Processing queue for async document handling
├── cloud_run.tf         # Backend and frontend services with VPC connector
└── outputs.tf           # Deployed URLs, connection strings
```

**State Management:**
```hcl
terraform {
  backend "gcs" {
    bucket  = "stackpoint-tf-state"
    prefix  = "loan-system/terraform/state"
  }
}
```

- Remote state in GCS bucket (versioned for rollback)
- State locking via GCS object locking (prevents concurrent applies)
- Sensitive values marked to avoid logging (`sensitive = true`)

**Terraform Module Organization:**
Each `.tf` file is a logical module:
- `vpc.tf`: All networking resources
- `iam.tf`: All identity and access management
- `cloud_run.tf`: All compute resources

This organization:
- Makes changes easier to review (related resources together)
- Enables partial applies (`terraform apply -target=module.vpc`)
- Improves readability (clear separation of concerns)

### Cloud Run Configuration

**Backend Service:**
```hcl
resource "google_cloud_run_service" "backend" {
  name     = "loan-backend"
  location = var.region

  template {
    spec {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/loan-repo/backend:${var.image_tag}"

        resources {
          limits = {
            memory = "1Gi"
            cpu    = "1"
          }
        }

        startup_probe {
          http_get {
            path = "/health"
          }
          initial_delay_seconds = 10
          timeout_seconds       = 5
          period_seconds        = 10
          failure_threshold     = 3
        }
      }

      service_account_name = google_service_account.backend.email

      vpc_access {
        connector = google_vpc_access_connector.connector.id
        egress    = "private-ranges-only"
      }
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = "0"
        "autoscaling.knative.dev/maxScale" = "10"
      }
    }
  }
}
```

**Key Configuration Details:**
- **Memory**: 1Gi for backend (Docling processing needs memory for PDF parsing)
- **CPU**: 1 vCPU (sufficient for async I/O bound operations)
- **Scaling**: 0-10 instances (scale to zero when idle, up to 10 under load)
- **Startup Probe**: Health check on `/health` endpoint
  - 10s initial delay (allow app to initialize)
  - 5s timeout per check
  - 3 failures before marking unhealthy
- **VPC Connector**: Private connectivity to Cloud SQL
- **Egress**: `private-ranges-only` restricts outbound to VPC + Google APIs

**Frontend Service:**
```hcl
resource "google_cloud_run_service" "frontend" {
  name     = "loan-frontend"
  location = var.region

  template {
    spec {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/loan-repo/frontend:${var.image_tag}"

        resources {
          limits = {
            memory = "512Mi"
            cpu    = "1"
          }
        }

        env {
          name  = "NEXT_PUBLIC_API_URL"
          value = google_cloud_run_service.backend.status[0].url
        }
      }
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = "0"
        "autoscaling.knative.dev/maxScale" = "5"
      }
    }
  }
}
```

**Key Configuration Details:**
- **Memory**: 512Mi (less than backend, mostly serving static assets)
- **CPU**: 1 vCPU
- **Scaling**: 0-5 instances (lower than backend, frontend is lighter)
- **Environment**: `NEXT_PUBLIC_API_URL` points to backend URL
  - Uses Terraform reference to backend service (automatic dependency)
  - Value baked into Next.js build at deploy time

### Deployment Workflow

```mermaid
flowchart LR
    subgraph Build["Build Phase"]
        Code[Git Push/Tag]
        Docker[Docker Build]
        Push[Push to Artifact Registry]
    end

    subgraph Deploy["Deploy Phase"]
        TF[Terraform Apply]
        Backend[Deploy Backend]
        Frontend[Deploy Frontend]
        Migrate[Run DB Migrations]
    end

    subgraph Verify["Verify Phase"]
        Health[Health Checks]
        Smoke[Smoke Tests]
        Rollback[Rollback on Failure]
    end

    Code --> Docker --> Push
    Push --> TF --> Backend
    Backend --> Frontend
    Frontend --> Migrate
    Migrate --> Health --> Smoke
    Smoke -->|failure| Rollback
```

**Deployment Commands:**
```bash
# 1. Build and push images
export GIT_SHA=$(git rev-parse --short HEAD)
export PROJECT_ID="your-gcp-project"
export REGION="us-central1"

./infrastructure/scripts/build.sh $PROJECT_ID $REGION $GIT_SHA

# 2. Initialize Terraform (first time only)
cd infrastructure/terraform
terraform init -backend-config="bucket=${PROJECT_ID}-tf-state"

# 3. Deploy infrastructure
terraform apply \
  -var="project_id=${PROJECT_ID}" \
  -var="region=${REGION}" \
  -var="image_tag=${GIT_SHA}"

# 4. Run database migrations
export DATABASE_URL=$(terraform output -raw database_url)
cd ../../backend
alembic upgrade head

# 5. Smoke test
export BACKEND_URL=$(cd ../infrastructure/terraform && terraform output -raw backend_url)
curl ${BACKEND_URL}/health
```

**Build Script Details:**
```bash
#!/bin/bash
# infrastructure/scripts/build.sh

PROJECT_ID=$1
REGION=$2
TAG=$3

REPO="${REGION}-docker.pkg.dev/${PROJECT_ID}/loan-repo"

# Build backend
docker build -t ${REPO}/backend:${TAG} -f backend/Dockerfile backend/
docker push ${REPO}/backend:${TAG}

# Build frontend (requires backend URL)
BACKEND_URL=$(gcloud run services describe loan-backend \
  --platform managed \
  --region ${REGION} \
  --format 'value(status.url)')

docker build \
  --build-arg NEXT_PUBLIC_API_URL=${BACKEND_URL} \
  -t ${REPO}/frontend:${TAG} \
  -f frontend/Dockerfile \
  frontend/
docker push ${REPO}/frontend:${TAG}
```

**Zero-Downtime Deployment:**
Cloud Run provides automatic zero-downtime deployments:
1. New revision created with new image
2. Traffic gradually shifted to new revision (default: immediate)
3. Health checks verify new revision is healthy
4. Old revision remains available for rollback
5. Old revision deleted after traffic migration completes

**Rollback Process:**
```bash
# List revisions
gcloud run revisions list --service=loan-backend --region=us-central1

# Rollback to previous revision
gcloud run services update-traffic loan-backend \
  --to-revisions=loan-backend-00023-abc=100 \
  --region=us-central1
```

### Database Migration Strategy

**Alembic Migration Workflow:**
```bash
# Generate migration from model changes
alembic revision --autogenerate -m "Add extraction_method field"

# Review migration script
cat alembic/versions/abc123_add_extraction_method.py

# Apply migration
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

**Migration Best Practices:**
1. **Backward Compatible**: Add nullable columns first, backfill data, then make non-nullable
2. **Incremental**: Small migrations, easy to rollback
3. **Tested**: Test migration on staging environment first
4. **Automated**: Run migrations as part of deployment pipeline
5. **Zero-Downtime**: Avoid locking tables for long periods

**Example Migration:**
```python
# alembic/versions/abc123_add_extraction_method.py
def upgrade():
    # Step 1: Add nullable column
    op.add_column('documents',
        sa.Column('extraction_method', sa.String(20), nullable=True))

    # Step 2: Backfill existing records
    op.execute("UPDATE documents SET extraction_method = 'docling' WHERE extraction_method IS NULL")

    # Step 3: Make non-nullable (future migration)
    # op.alter_column('documents', 'extraction_method', nullable=False)

def downgrade():
    op.drop_column('documents', 'extraction_method')
```

---

## Monitoring and Observability

### Health Check Endpoints

**Backend Health Check:**
```
GET /health

Response:
{
  "status": "healthy",
  "database": "connected",
  "version": "2.0.0",
  "timestamp": "2026-01-27T10:30:00Z"
}
```

**GPU OCR Service Health Check:**
```
GET /health

Response:
{
  "status": "healthy",
  "model_loaded": true,
  "gpu_available": true,
  "vllm_version": "0.3.0"
}
```

### Logging Strategy

**Structured Logging:**
```python
import logging
import json

logger = logging.getLogger(__name__)

# Structured log format
logger.info("Document processing started", extra={
    "document_id": str(document.id),
    "filename": document.filename,
    "file_size_bytes": document.file_size_bytes,
    "extraction_method": "docling",
})
```

**Log Levels:**
- **DEBUG**: Detailed diagnostic information (disabled in production)
- **INFO**: General informational messages (document processing started/completed)
- **WARNING**: Potentially harmful situations (validation warnings, retry attempts)
- **ERROR**: Error events (LLM failures, database errors)
- **CRITICAL**: Severe errors (service unavailable, data corruption)

**PII Redaction:**
```python
# Log filter to redact sensitive fields
class PIIFilter(logging.Filter):
    def filter(self, record):
        # Redact SSN from log messages
        if hasattr(record, 'ssn'):
            record.ssn = "***-**-" + record.ssn[-4:]
        return True

logger.addFilter(PIIFilter())
```

### Metrics Collection

**Application Metrics (to implement):**
```python
from prometheus_client import Counter, Histogram, Gauge

# Document processing metrics
documents_processed = Counter(
    'documents_processed_total',
    'Total documents processed',
    ['status', 'extraction_method']
)

processing_duration = Histogram(
    'document_processing_duration_seconds',
    'Document processing duration',
    ['extraction_method']
)

# LLM metrics
llm_requests = Counter(
    'llm_requests_total',
    'Total LLM API requests',
    ['model', 'status']
)

llm_tokens = Counter(
    'llm_tokens_total',
    'Total tokens consumed',
    ['model', 'type']  # type: input/output
)

llm_cost = Counter(
    'llm_cost_usd_total',
    'Total LLM cost in USD',
    ['model']
)

# GPU OCR metrics
gpu_ocr_requests = Counter(
    'gpu_ocr_requests_total',
    'Total GPU OCR requests',
    ['status']
)

circuit_breaker_state = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 2=half_open)',
    ['service']
)
```

**Cloud Run Metrics (automatic):**
- Request count
- Request latency (p50, p95, p99)
- Instance count
- CPU utilization
- Memory utilization
- Startup latency
- Error rate (5xx responses)

### Alerting Rules (to implement)

**Critical Alerts:**
```yaml
# Error rate alert
- alert: HighErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
  for: 5m
  annotations:
    summary: "High error rate detected"
    description: "{{ $value }}% of requests failing"

# Database connection failures
- alert: DatabaseConnectionFailure
  expr: database_connection_errors_total > 10
  for: 1m
  annotations:
    summary: "Database connection failures"

# GPU service circuit breaker open
- alert: GPUServiceCircuitBreakerOpen
  expr: circuit_breaker_state{service="gpu_ocr"} == 1
  for: 5m
  annotations:
    summary: "GPU OCR service circuit breaker open"
    description: "Scanned documents will fail to process"
```

**Warning Alerts:**
```yaml
# High LLM costs
- alert: HighLLMCosts
  expr: rate(llm_cost_usd_total[1h]) > 1.0
  for: 15m
  annotations:
    summary: "High LLM API costs"
    description: "${{ $value }}/hour LLM spending"

# Low confidence scores
- alert: HighLowConfidenceRate
  expr: rate(documents_processed_total{confidence="<0.7"}[1h]) > 0.3
  for: 30m
  annotations:
    summary: "High rate of low confidence extractions"
```

### Distributed Tracing (future)

**OpenTelemetry Integration:**
```python
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Instrument FastAPI app
FastAPIInstrumentor.instrument_app(app)

# Manual span creation
tracer = trace.get_tracer(__name__)

async def process_document(document_id: UUID):
    with tracer.start_as_current_span("process_document") as span:
        span.set_attribute("document_id", str(document_id))

        with tracer.start_as_current_span("docling_processing"):
            content = docling_processor.process(...)

        with tracer.start_as_current_span("llm_extraction"):
            borrowers = await llm_client.extract(...)

        return borrowers
```

**Trace Visualization:**
- Document upload → Docling processing → LLM extraction → Database write
- Identify bottlenecks (which stage takes longest?)
- Correlate errors across services
- Track request flow through system

---

## Testing Strategy

### Test Pyramid

```
       /\
      /  \  E2E Tests (5%)
     /    \  - Full document upload flow
    /------\  - UI integration tests
   /        \
  / Integration\ (25%)
 /   Tests      \ - API endpoint tests
/                \ - Database repository tests
/------------------\
/   Unit Tests (70%)\
- Extraction logic
- Validation functions
- Deduplication algorithm
```

### Unit Tests

**Coverage Target:** 90%+ for core business logic

**Test Structure:**
```python
# backend/tests/unit/test_validation.py
import pytest
from src.extraction.validation import validate_ssn, normalize_ssn

def test_validate_ssn_with_dashes():
    """SSN with dashes should pass validation."""
    assert validate_ssn("123-45-6789") == True

def test_validate_ssn_without_dashes():
    """SSN without dashes should pass validation."""
    assert validate_ssn("123456789") == True

def test_normalize_ssn():
    """Normalization should add dashes."""
    assert normalize_ssn("123456789") == "123-45-6789"
    assert normalize_ssn("123-45-6789") == "123-45-6789"

@pytest.mark.parametrize("invalid_ssn", [
    "12-34-5678",  # Wrong format
    "123-456-789",  # Wrong format
    "abc-de-fghi",  # Non-numeric
    "",  # Empty
])
def test_validate_ssn_invalid(invalid_ssn):
    """Invalid SSNs should fail validation."""
    assert validate_ssn(invalid_ssn) == False
```

**Key Unit Test Areas:**
- Extraction logic (`extractor.py`, `langextract_processor.py`)
- Validation functions (`validation.py`)
- Deduplication algorithm (`deduplication.py`)
- Consistency checks (`consistency.py`)
- Confidence scoring (`confidence.py`)
- Chunking strategy (`chunker.py`)

### Integration Tests

**Database Integration:**
```python
# backend/tests/integration/test_repositories.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from src.storage.repositories import DocumentRepository
from src.storage.models import Document, DocumentStatus

@pytest.fixture
async def db_session():
    """Create test database session."""
    engine = create_async_engine("postgresql+asyncpg://test:test@localhost/test")
    async with AsyncSession(engine) as session:
        yield session

@pytest.mark.asyncio
async def test_create_document(db_session):
    """Test document creation in database."""
    repo = DocumentRepository(db_session)

    document = await repo.create(
        filename="test.pdf",
        file_hash="abc123",
        file_type="pdf",
        file_size_bytes=1024,
    )

    assert document.id is not None
    assert document.status == DocumentStatus.PENDING
    assert document.filename == "test.pdf"
```

**API Integration:**
```python
# backend/tests/integration/test_api.py
import pytest
from httpx import AsyncClient
from src.main import app

@pytest.mark.asyncio
async def test_upload_document():
    """Test document upload endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        files = {"file": ("test.pdf", b"fake pdf content", "application/pdf")}
        response = await client.post("/api/documents", files=files)

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["filename"] == "test.pdf"
```

### E2E Tests

**Full Flow Test:**
```python
# backend/tests/e2e/test_document_flow.py
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_document_processing():
    """Test complete document processing flow."""
    # 1. Upload document
    async with AsyncClient(app=app, base_url="http://test") as client:
        with open("tests/fixtures/sample_loan.pdf", "rb") as f:
            files = {"file": ("sample_loan.pdf", f, "application/pdf")}
            response = await client.post("/api/documents", files=files)

        assert response.status_code == 201
        document_id = response.json()["id"]

    # 2. Wait for processing (poll status)
    max_wait = 60  # seconds
    for _ in range(max_wait):
        response = await client.get(f"/api/documents/{document_id}/status")
        status = response.json()["status"]

        if status == "completed":
            break
        elif status == "failed":
            pytest.fail(f"Document processing failed: {response.json()['error_message']}")

        await asyncio.sleep(1)

    # 3. Verify extraction results
    response = await client.get(f"/api/documents/{document_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"

    # 4. Check borrowers extracted
    response = await client.get(f"/api/borrowers?document_id={document_id}")
    borrowers = response.json()["borrowers"]
    assert len(borrowers) > 0
    assert borrowers[0]["confidence_score"] >= 0.7
```

### Test Data Fixtures

**Sample Documents:**
```
backend/tests/fixtures/
├── simple_loan.pdf          # Single borrower, clear scan
├── complex_loan.pdf         # Multiple borrowers
├── scanned_loan.pdf         # Scanned document requiring OCR
├── handwritten_loan.pdf     # Partially handwritten
└── malformed_loan.pdf       # Corrupted file for error testing
```

**Mock LLM Responses:**
```python
# backend/tests/mocks/llm_responses.py
MOCK_EXTRACTION_RESPONSE = {
    "borrowers": [
        {
            "name": "John Doe",
            "ssn": "123-45-6789",
            "phone": "+1-555-0123",
            "email": "john.doe@example.com",
            "address": {
                "street": "123 Main St",
                "city": "Springfield",
                "state": "IL",
                "zip": "62701"
            },
            "income_records": [
                {
                    "amount": 75000.00,
                    "period": "annual",
                    "year": 2025,
                    "source_type": "W-2",
                    "employer": "Acme Corp"
                }
            ],
            "page_number": 1
        }
    ]
}
```

### Continuous Integration

**GitHub Actions Workflow:**
```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt
          pip install -r backend/requirements-dev.txt

      - name: Run unit tests
        run: pytest backend/tests/unit -v --cov=backend/src

      - name: Run integration tests
        run: pytest backend/tests/integration -v
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:test@localhost/postgres

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## API Design Principles

### RESTful Conventions

**Resource Naming:**
- Plural nouns: `/api/documents`, `/api/borrowers`
- Hierarchical relationships: `/api/documents/{id}/borrowers`
- Query parameters for filtering: `/api/borrowers?confidence_min=0.8`

**HTTP Methods:**
- `GET`: Retrieve resources (idempotent, safe)
- `POST`: Create new resources (non-idempotent)
- `PUT`: Full update (idempotent)
- `PATCH`: Partial update (idempotent)
- `DELETE`: Remove resources (idempotent)

**Status Codes:**
- `200 OK`: Successful GET request
- `201 Created`: Successful POST creating resource
- `202 Accepted`: Request accepted for async processing
- `400 Bad Request`: Invalid input (validation error)
- `404 Not Found`: Resource doesn't exist
- `409 Conflict`: Resource conflict (duplicate hash)
- `500 Internal Server Error`: Server-side error

### API Versioning Strategy

**Current Approach:** Implicit v1 (no version in URL)
```
POST /api/documents  # v1 implicit
```

**Future v2 Approach:** Explicit version in URL
```
POST /api/v2/documents  # v2 explicit
POST /api/documents     # v1 still works (backward compatible)
```

**Breaking Changes That Require New Version:**
- Removing fields from responses
- Changing field types (string → integer)
- Renaming fields
- Changing error response format

**Non-Breaking Changes:**
- Adding optional request parameters
- Adding new fields to responses
- Adding new endpoints
- Deprecating (but not removing) fields

### Pagination

**Standard Pagination:**
```
GET /api/documents?limit=100&offset=0

Response:
{
  "documents": [...],
  "total": 500,
  "limit": 100,
  "offset": 0,
  "has_more": true
}
```

**Cursor-Based Pagination (future):**
```
GET /api/documents?limit=100&cursor=eyJpZCI6IjEyMyJ9

Response:
{
  "documents": [...],
  "next_cursor": "eyJpZCI6IjIyMyJ9",
  "has_more": true
}
```

Benefits of cursor-based pagination:
- Stable pagination (no missing items when new documents added)
- Better performance (no OFFSET clause)
- Clearer semantics (cursor represents exact position)

### Error Response Format

**Standard Error Response:**
```json
{
  "error": {
    "code": "DOCUMENT_PROCESSING_FAILED",
    "message": "Document processing failed: GPU OCR service unavailable",
    "details": {
      "error_type": "ocr_service_unavailable",
      "retryable": true,
      "retry_after": "60s"
    },
    "timestamp": "2026-01-27T10:30:00Z",
    "request_id": "req_abc123"
  }
}
```

**Error Codes:**
- `VALIDATION_ERROR`: Input validation failed
- `DOCUMENT_PROCESSING_FAILED`: Processing error
- `RESOURCE_NOT_FOUND`: Requested resource doesn't exist
- `DUPLICATE_DOCUMENT`: Document with same hash already exists
- `SERVICE_UNAVAILABLE`: External service (LLM, OCR) unavailable
- `INTERNAL_ERROR`: Unexpected server error

---

## Appendix: Configuration Reference

### Environment Variables

| Variable | Description | Required | Default | Example |
|----------|-------------|----------|---------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Yes | - | `postgresql+asyncpg://user:pass@host/db` |
| `GEMINI_API_KEY` | Google AI API key | Yes | - | `AIza...` |
| `GCS_BUCKET` | Cloud Storage bucket name | Yes (prod) | - | `loan-documents-prod` |
| `CLOUD_TASKS_QUEUE` | Queue ID for async processing | No | - | `projects/proj/locations/us-central1/queues/documents` |
| `NEXT_PUBLIC_API_URL` | Backend URL for frontend | Yes (frontend) | - | `https://backend-xyz.run.app` |
| `LOG_LEVEL` | Logging verbosity | No | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `MAX_FILE_SIZE_MB` | Max upload file size | No | `50` | `100` |
| `GPU_OCR_URL` | LightOnOCR service URL | No | - | `https://lightonocr-xyz.run.app` |

### Terraform Variables

| Variable | Description | Type | Default | Required |
|----------|-------------|------|---------|----------|
| `project_id` | GCP project ID | string | - | Yes |
| `region` | GCP region | string | `us-central1` | No |
| `environment` | Environment name | string | `dev` | No |
| `image_tag` | Docker image tag | string | `latest` | No |
| `db_tier` | Cloud SQL machine type | string | `db-f1-micro` | No |
| `enable_gpu_ocr` | Deploy GPU OCR service | bool | `true` | No |

### Key Files Reference

| Path | Purpose | LOC |
|------|---------|-----|
| `backend/src/main.py` | FastAPI application entry point | ~100 |
| `backend/src/api/documents.py` | Document upload/list/delete endpoints | ~200 |
| `backend/src/api/borrowers.py` | Borrower query endpoints | ~150 |
| `backend/src/extraction/extractor.py` | Docling-based extraction orchestrator | ~400 |
| `backend/src/extraction/extraction_router.py` | v2.0 dual pipeline router | ~150 |
| `backend/src/extraction/langextract_processor.py` | LangExtract-based processor | ~300 |
| `backend/src/extraction/llm_client.py` | Gemini API client | ~250 |
| `backend/src/ocr/ocr_router.py` | OCR routing with circuit breaker | ~350 |
| `backend/src/ocr/lightonocr_client.py` | GPU OCR service client | ~150 |
| `backend/src/ingestion/docling_processor.py` | Document parsing | ~200 |
| `backend/src/ingestion/document_service.py` | Document upload orchestration | ~300 |
| `backend/src/storage/repositories.py` | Database access layer | ~400 |
| `backend/src/storage/models.py` | SQLAlchemy ORM models | ~200 |
| `frontend/src/app/` | Next.js App Router pages | ~800 |
| `infrastructure/terraform/` | Infrastructure as Code | ~1000 |

---

## Glossary

**Borrower**: Individual or entity seeking a loan, whose information is extracted from loan documents.

**Chunk**: Segment of document text processed independently by LLM (max 16,000 characters).

**Circuit Breaker**: Fault tolerance pattern that prevents cascading failures by stopping requests to failing services.

**Confidence Score**: 0.0-1.0 metric indicating extraction quality based on completeness, validation, and consistency.

**Deduplication**: Process of identifying and merging borrower records that represent the same person.

**Docling**: Open-source document processing library for PDF/DOCX parsing and OCR.

**LangExtract**: Google library for structured information extraction with character-level source grounding.

**LightOnOCR**: Vision-language model for OCR, deployed on GPU via vLLM.

**Source Reference**: Database record linking extracted field to originating document, page, and text snippet.

**Structured Output**: Gemini API feature guaranteeing JSON response matching provided schema.

**VPC Connector**: Serverless VPC Access connector enabling Cloud Run to access VPC resources (Cloud SQL).

---

## Change Log

### v2.0 (2026-01-27)
- Added dual extraction pipeline (Docling + LangExtract)
- Implemented character-level source grounding
- Added GPU OCR service with circuit breaker
- Corrected OCR fallback documentation
- Expanded monitoring and testing sections
- Added API design principles

### v1.0 (2026-01-25)
- Initial system design document
- Docling-based extraction pipeline
- Cloud Run deployment architecture
- Basic monitoring and error handling

---

**Document Validation Status**: ✅ Validated against codebase on 2026-01-27

**Next Review Date**: 2026-02-27
