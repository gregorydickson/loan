# Product Requirements Document
## Loan Document Data Extraction System
### Optimized for Claude Code CLI Agent

---

| Field | Value |
|-------|-------|
| **Version** | 3.0 |
| **Date** | January 2026 |
| **Methodology** | Test-Driven Development (TDD) |
| **Target Corpus** | Loan Documents |
| **Agent** | Claude Code CLI |
| **Document Processing** | Docling |
| **Deployment** | Google Cloud Platform |

---

## Project Goals & Requirements

### Overview
Build an unstructured data extraction system using a provided document corpus. This implementation uses the **Loan Documents** dataset to extract structured borrower information.

### Timeline
- **Deadline:** 7 days from receipt
- **Expected effort:** 4–8 hours

### Problem Description
The provided folder contains a corpus of documents with variable formatting, mixed file types, and structured data embedded within unstructured text. The goal is to design and implement a system that extracts meaningful, structured data from these documents.

The solution includes logic for parsing unstructured data as well as an API interface to serve the processed data in a meaningful form.

### Selected Dataset: Loan Documents

**Objective:** Analyze the documents and produce a structured record for each borrower that includes:
- Extracted PII: name, address
- Full income history
- Associated account/loan numbers
- Clear reference to the original document(s) from which the information was sourced

### Required Deliverables

#### 1. System Design Document (Markdown)
- ✅ Architecture overview, including component diagram
- ✅ Data pipeline design covering ingestion, processing, storage, and retrieval
- ✅ AI/LLM integration strategy and model selection rationale
- ✅ Approach for handling document format variability
- ✅ Scaling considerations for 10x and 100x document volume
- ✅ Key technical trade-offs and reasoning
- ✅ Error handling strategy and data quality validation approach

#### 2. Working Implementation
- ✅ Document ingestion pipeline
- ✅ Extraction logic using AI/LLM tooling (Gemini 3.0)
- ✅ Structured output generation (PostgreSQL database-backed)
- ✅ Basic query or retrieval interface (FastAPI REST API)
- ✅ Test coverage for critical paths (>80% target)

#### 3. README
- ✅ Setup and run instructions
- ✅ Summary of architectural and implementation decisions

### Bonus
- ✅ GCP deployment infrastructure with Terraform
- ✅ High-fidelity frontend UI for data visualization

---

## Agent Execution Instructions

This PRD is designed for autonomous execution by Claude Code CLI. Every task follows this pattern:

```
1. IMPLEMENT  → Write tests first (TDD), then implementation
2. SIMPLIFY   → Run code-simplifier plugin on modified files
3. REVIEW     → Run automated code review checks
4. FIX        → Address issues found in review
5. VERIFY     → Run pytest and mypy to confirm all passing
```

**All tasks are agent-executable. No manual intervention required.**

**Code-Simplifier Plugin Usage:**
```
Use the code-simplifier plugin on <file_or_directory>
```

**Verification Commands:**
```bash
pytest tests/ -v --cov=src                    # Test suite
mypy src/ --strict                            # Type checking
```

---

## Technology Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Document Processing** | Docling | Production-grade document parsing (PDF, DOCX, images) with layout understanding |
| **Backend Framework** | FastAPI | Async support, auto-docs, Pydantic validation |
| **Frontend Framework** | Next.js 14 + React | App router, server components, excellent DX |
| **UI Components** | shadcn/ui + Tailwind | High-fidelity, accessible, customizable |
| **LLM Provider** | Gemini 3.0 Pro Preview | State-of-the-art reasoning for complex extraction tasks |
| **Database** | Cloud SQL (PostgreSQL) | Managed, scalable, GCP-native |
| **File Storage** | Cloud Storage (GCS) | Durable, scalable document storage |
| **Compute** | Cloud Run | Serverless, auto-scaling, cost-effective |
| **Task Queue** | Cloud Tasks | Async document processing |
| **Testing** | pytest + pytest-asyncio | TDD workflow, async support |
| **Type Checking** | mypy (strict mode) | Catch errors early |

---

## Project Structure

```
loan-extraction-system/
├── backend/
│   ├── src/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── main.py
│   │   ├── ingestion/
│   │   │   ├── __init__.py
│   │   │   ├── docling_processor.py
│   │   │   └── document_service.py
│   │   ├── extraction/
│   │   │   ├── __init__.py
│   │   │   ├── llm_client.py
│   │   │   ├── complexity_classifier.py
│   │   │   ├── prompts.py
│   │   │   ├── extractor.py
│   │   │   ├── validation.py
│   │   │   └── schemas.py
│   │   ├── storage/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── repositories.py
│   │   │   └── gcs_client.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes/
│   │   │   │   ├── documents.py
│   │   │   │   ├── borrowers.py
│   │   │   │   └── health.py
│   │   │   └── dependencies.py
│   │   └── models/
│   │       ├── __init__.py
│   │       ├── borrower.py
│   │       └── document.py
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── e2e/
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   ├── documents/
│   │   │   ├── borrowers/
│   │   │   ├── architecture/
│   │   │   │   ├── page.tsx
│   │   │   │   ├── decisions/
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── pipeline/
│   │   │   │   │   └── page.tsx
│   │   │   │   └── scaling/
│   │   │   │       └── page.tsx
│   │   │   └── api/
│   │   ├── components/
│   │   │   ├── ui/
│   │   │   ├── documents/
│   │   │   ├── borrowers/
│   │   │   └── architecture/
│   │   └── lib/
│   ├── package.json
│   ├── tailwind.config.ts
│   ├── Dockerfile
│   └── next.config.js
├── infrastructure/
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── cloud_run.tf
│   │   ├── cloud_sql.tf
│   │   ├── cloud_storage.tf
│   │   ├── cloud_tasks.tf
│   │   └── iam.tf
│   └── scripts/
│       ├── deploy.sh
│       └── setup-gcp.sh
├── docs/
│   ├── SYSTEM_DESIGN.md
│   ├── ARCHITECTURE_DECISIONS.md
│   └── API.md
└── README.md
```

---

## Phase 0: Project Setup

### Tasks

#### Task 0.1: Create Project Structure

- [ ] **0.1.1 IMPLEMENT**: Create directory structure
  ```bash
  mkdir -p loan-extraction-system/{backend/{src/{ingestion,extraction,storage,api/routes,models},tests/{unit,integration,e2e}},frontend/{src/{app/{documents,borrowers,architecture/{decisions,pipeline,scaling},api},components/{ui,documents,borrowers,architecture},lib}},infrastructure/{terraform,scripts},docs}
  ```

- [ ] **0.1.2 IMPLEMENT**: Create backend pyproject.toml
  ```toml
  [project]
  name = "loan-extraction-backend"
  version = "0.1.0"
  requires-python = ">=3.11"
  dependencies = [
      "fastapi>=0.109.0",
      "uvicorn[standard]>=0.27.0",
      "pydantic>=2.5.0",
      "pydantic-settings>=2.1.0",
      "sqlalchemy[asyncio]>=2.0.25",
      "asyncpg>=0.29.0",
      "alembic>=1.13.0",
      "python-multipart>=0.0.6",
      "docling>=2.15.0",
      "google-genai>=0.2.0",
      "google-cloud-storage>=2.14.0",
      "google-cloud-tasks>=2.16.0",
      "google-cloud-secret-manager>=2.18.0",
      "tenacity>=8.2.3",
      "structlog>=24.1.0",
      "httpx>=0.26.0",
  ]

  [project.optional-dependencies]
  dev = [
      "pytest>=8.0.0",
      "pytest-asyncio>=0.23.0",
      "pytest-cov>=4.1.0",
      "mypy>=1.8.0",
      "types-google-cloud-ndb>=2.3.0",
  ]

  [tool.pytest.ini_options]
  asyncio_mode = "auto"
  testpaths = ["tests"]
  addopts = "-v --cov=src --cov-report=term-missing"

  [tool.mypy]
  python_version = "3.11"
  strict = true
  ```

- [ ] **0.1.3 IMPLEMENT**: Create frontend package.json
  ```json
  {
    "name": "loan-extraction-frontend",
    "version": "0.1.0",
    "private": true,
    "scripts": {
      "dev": "next dev",
      "build": "next build",
      "start": "next start",
      "lint": "next lint",
      "test": "vitest"
    },
    "dependencies": {
      "next": "14.1.0",
      "react": "^18.2.0",
      "react-dom": "^18.2.0",
      "@tanstack/react-query": "^5.17.0",
      "lucide-react": "^0.312.0",
      "recharts": "^2.10.0",
      "class-variance-authority": "^0.7.0",
      "clsx": "^2.1.0",
      "tailwind-merge": "^2.2.0"
    },
    "devDependencies": {
      "@types/node": "^20.11.0",
      "@types/react": "^18.2.48",
      "autoprefixer": "^10.4.17",
      "postcss": "^8.4.33",
      "tailwindcss": "^3.4.1",
      "typescript": "^5.3.3",
      "vitest": "^1.2.0"
    }
  }
  ```

- [ ] **0.1.4 IMPLEMENT**: Create configuration files
  - Create `backend/src/config.py` with Pydantic Settings
  - Create `backend/.env.example` with required variables
  - Create `frontend/.env.example` with API URL

- [ ] **0.1.5 SIMPLIFY**: Run code-simplifier plugin on `backend/src/config.py`

- [ ] **0.1.6 VERIFY**: Install dependencies and verify setup
  ```bash
  cd backend && pip install -e ".[dev]"
  cd frontend && npm install
  pytest --collect-only
  mypy src/ --strict
  ```

---

## Phase 1: Document Ingestion with Docling

### Phase Overview

Use Docling for document processing. Docling handles PDF, DOCX, images, and more with layout understanding and table extraction built-in.

### Acceptance Criteria
- Docling processes PDF, DOCX, PNG/JPG documents
- Extracted text preserves structure (tables, sections)
- Documents are stored in GCS with metadata in PostgreSQL
- Processing errors are handled gracefully

---

#### Task 1.1: Docling Processor

##### 1.1.1 IMPLEMENT: Docling Wrapper Tests
- [ ] Create `backend/tests/unit/test_docling_processor.py`
  ```python
  """
  Tests for Docling document processor wrapper.
  
  Test cases:
  - test_process_pdf_returns_structured_content
  - test_process_docx_returns_structured_content
  - test_process_image_with_ocr
  - test_process_extracts_tables
  - test_process_invalid_file_raises_error
  - test_process_returns_page_metadata
  - test_process_handles_large_documents
  """
  ```

##### 1.1.2 IMPLEMENT: Docling Processor Class
- [ ] Create `backend/src/ingestion/docling_processor.py`
  ```python
  """
  Docling-based document processor.
  
  Classes:
  - DoclingProcessor: Wraps Docling for document conversion
    - process(file_path: Path) -> DocumentContent
    - process_bytes(data: bytes, filename: str) -> DocumentContent
  
  - DocumentContent(BaseModel):
    - text: str
    - tables: list[TableData]
    - pages: list[PageContent]
    - metadata: DocumentMetadata
  
  Uses docling.document_converter.DocumentConverter
  Configures pipeline for OCR when needed
  """
  ```

##### 1.1.3 SIMPLIFY: Run code-simplifier plugin on `backend/src/ingestion/docling_processor.py`

##### 1.1.4 REVIEW: Run automated checks
- [ ] Run `mypy backend/src/ingestion/docling_processor.py --strict`
- [ ] Verify all functions have type hints and docstrings

##### 1.1.5 FIX: Address any mypy errors or missing type hints

##### 1.1.6 VERIFY: Run tests
- [ ] Run `pytest backend/tests/unit/test_docling_processor.py -v` — ALL PASS
- [ ] Run `mypy backend/src/ingestion/ --strict` — NO ERRORS

---

#### Task 1.2: Document Service

##### 1.2.1 IMPLEMENT: Document Service Tests
- [ ] Create `backend/tests/unit/test_document_service.py`
  ```python
  """
  Tests for document service orchestration.
  
  Test cases:
  - test_upload_document_stores_in_gcs
  - test_upload_document_creates_db_record
  - test_upload_document_queues_processing
  - test_get_document_status
  - test_process_document_extracts_content
  - test_process_document_updates_status
  - test_duplicate_document_detected_by_hash
  """
  ```

##### 1.2.2 IMPLEMENT: Document Service
- [ ] Create `backend/src/ingestion/document_service.py`
  ```python
  """
  Document ingestion orchestration service.
  
  Classes:
  - DocumentService:
    - upload(file: UploadFile) -> DocumentRecord
    - process(document_id: UUID) -> ProcessingResult
    - get_status(document_id: UUID) -> ProcessingStatus
    
  Coordinates:
  - GCS upload
  - Database record creation
  - Docling processing
  - Cloud Tasks queuing
  """
  ```

##### 1.2.3 SIMPLIFY: Run code-simplifier plugin on `backend/src/ingestion/document_service.py`

##### 1.2.4 REVIEW: Run automated checks
- [ ] Run `mypy backend/src/ingestion/document_service.py --strict`

##### 1.2.5 FIX: Address any issues

##### 1.2.6 VERIFY: Run tests
- [ ] Run `pytest backend/tests/unit/test_document_service.py -v` — ALL PASS

---

#### Task 1.3: GCS Storage Client

##### 1.3.1 IMPLEMENT: GCS Client Tests
- [ ] Create `backend/tests/unit/test_gcs_client.py`
  ```python
  """
  Tests for Google Cloud Storage client.
  
  Test cases:
  - test_upload_file_returns_gcs_uri
  - test_download_file_returns_bytes
  - test_delete_file_removes_object
  - test_generate_signed_url
  - test_file_exists_check
  Mock GCS client for unit tests.
  """
  ```

##### 1.3.2 IMPLEMENT: GCS Client
- [ ] Create `backend/src/storage/gcs_client.py`
  ```python
  """
  Google Cloud Storage client wrapper.
  
  Classes:
  - GCSClient:
    - upload(data: bytes, path: str) -> str (returns gs:// URI)
    - download(path: str) -> bytes
    - delete(path: str) -> None
    - get_signed_url(path: str, expiration: int) -> str
    - exists(path: str) -> bool
  """
  ```

##### 1.3.3 SIMPLIFY: Run code-simplifier plugin on `backend/src/storage/gcs_client.py`

##### 1.3.4 REVIEW: Run `mypy backend/src/storage/gcs_client.py --strict`

##### 1.3.5 FIX: Address any issues

##### 1.3.6 VERIFY: Run tests
- [ ] Run `pytest backend/tests/unit/test_gcs_client.py -v` — ALL PASS

---

#### Task 1.4: Phase 1 Integration

##### 1.4.1 IMPLEMENT: Integration tests
- [ ] Create `backend/tests/integration/test_ingestion_pipeline.py`
  ```python
  """
  Integration tests for document ingestion pipeline.
  
  Test cases:
  - test_full_pdf_ingestion_flow
  - test_full_docx_ingestion_flow
  - test_ingestion_with_processing_error_recovery
  """
  ```

##### 1.4.2 SIMPLIFY: Run code-simplifier plugin on `backend/src/ingestion/`

##### 1.4.3 VERIFY: Phase 1 complete
- [ ] Run `pytest backend/tests/ -v --cov=src/ingestion` — ALL PASS, >80% coverage
- [ ] Run `mypy backend/src/ingestion/ --strict` — NO ERRORS

### ✅ PHASE 1 SIGN-OFF
- [ ] All tasks completed
- [ ] All tests passing
- [ ] Type checks passing

---

## Phase 2: LLM Extraction Engine

### Phase Overview

Build the extraction engine using Gemini 3.0 Pro Preview to extract structured borrower data from processed documents.

### Acceptance Criteria
- LLM client handles Gemini API with retries
- Structured output validated against Pydantic schema
- Source attribution tracked for all extractions
- Confidence scoring implemented

---

#### Task 2.1: Pydantic Models

##### 2.1.1 IMPLEMENT: Borrower Models Tests
- [ ] Create `backend/tests/unit/test_borrower_models.py`
  ```python
  """
  Test cases:
  - test_borrower_record_validates_complete_data
  - test_borrower_record_handles_partial_data
  - test_address_model_validation
  - test_income_record_validation
  - test_source_reference_validation
  - test_model_json_serialization
  """
  ```

##### 2.1.2 IMPLEMENT: Borrower Models
- [ ] Create `backend/src/models/borrower.py`
  ```python
  """
  Pydantic models for borrower data.
  
  Models:
  - Address: street, city, state, zip_code, country
  - IncomeRecord: amount, period, year, source_type, employer
  - SourceReference: document_id, document_name, page_number, section, snippet
  - BorrowerRecord: id, name, address, income_history, account_numbers, 
                    loan_numbers, sources, confidence_score, extracted_at
  """
  ```

##### 2.1.3 SIMPLIFY: Run code-simplifier plugin on `backend/src/models/borrower.py`

##### 2.1.4 VERIFY: Run tests and type checks
- [ ] Run `pytest backend/tests/unit/test_borrower_models.py -v` — ALL PASS
- [ ] Run `mypy backend/src/models/ --strict` — NO ERRORS

---

#### Task 2.2: Gemini LLM Client

##### 2.2.1 IMPLEMENT: LLM Client Tests
- [ ] Create `backend/tests/unit/test_llm_client.py`
  ```python
  """
  Test cases:
  - test_client_initializes_with_api_key
  - test_extract_returns_structured_response
  - test_client_retries_on_rate_limit
  - test_client_retries_on_server_error
  - test_client_tracks_token_usage
  - test_client_timeout_handling
  Mock google.genai client for unit tests.
  """
  ```

##### 2.2.2 IMPLEMENT: LLM Client
- [ ] Create `backend/src/extraction/llm_client.py`
  ```python
  """
  Gemini API client with retry logic.

  Classes:
  - GeminiClient:
    - extract(text: str, schema: type[BaseModel], use_pro: bool = True) -> BaseModel
    - Uses google.genai SDK (from google-genai package)
    - Implements retry with tenacity (exponential backoff)
    - Tracks token usage and costs
    - Configurable timeout
    - Model selection based on task complexity

  - LLMResponse:
    - content: str
    - input_tokens: int
    - output_tokens: int
    - latency_ms: int
    - model_used: str

  Error Recovery Strategy:
  - Retry with exponential backoff (max 3 attempts)
  - On rate limit (429): Wait 60s, then retry
  - On server error (5xx): Wait 10s, then retry
  - On timeout: Reduce chunk size by 50%, retry
  - On parsing error: Return partial results with error flag
  - On all failures: Log error, return empty result with error metadata

  Model Selection Strategy:
  - gemini-3-pro-preview: For complex documents with multiple borrowers,
    cross-referenced data, or unclear formatting. High reasoning capability.
  - gemini-3-flash-preview: For standard loan documents with clear structure.
    Faster and more cost-effective for routine extraction.

  Configuration:
  - Model: gemini-3-pro-preview (default) or gemini-3-flash-preview
  - Temperature: 0.1 (for consistent extraction)
  - Max output tokens: 8192
  - Response MIME type: application/json
  - Response schema: Pydantic model for structured output

  Example Usage:
  ```python
  from google import genai
  from google.genai import types

  client = genai.Client(api_key=settings.gemini_api_key)

  # Use Pro for complex extraction
  response = client.models.generate_content(
      model='gemini-3-pro-preview',
      contents=complex_document_text,
      config=types.GenerateContentConfig(
          response_mime_type='application/json',
          response_schema=BorrowerRecord,
          temperature=0.1,
      ),
  )
  parsed_result = response.parsed  # Returns Pydantic object

  # Use Flash for standard documents
  response = client.models.generate_content(
      model='gemini-3-flash-preview',
      contents=standard_document_text,
      config=types.GenerateContentConfig(
          response_mime_type='application/json',
          response_schema=BorrowerRecord,
          temperature=0.1,
      ),
  )
  ```
  """
  ```

##### 2.2.3 SIMPLIFY: Run code-simplifier plugin on `backend/src/extraction/llm_client.py`

##### 2.2.4 REVIEW: Run `mypy backend/src/extraction/llm_client.py --strict`

##### 2.2.5 FIX: Address any issues

##### 2.2.6 VERIFY: Run tests
- [ ] Run `pytest backend/tests/unit/test_llm_client.py -v` — ALL PASS

---

#### Task 2.3: Document Complexity Classifier

##### 2.3.1 IMPLEMENT: Complexity Classifier Tests
- [ ] Create `backend/tests/unit/test_complexity_classifier.py`
  ```python
  """
  Test cases:
  - test_simple_single_borrower_classified_as_standard
  - test_multiple_borrowers_classified_as_complex
  - test_poor_scan_quality_classified_as_complex
  - test_handwritten_sections_classified_as_complex
  - test_standard_form_classified_as_standard
  - test_mixed_document_types_classified_as_complex
  """
  ```

##### 2.3.2 IMPLEMENT: Complexity Classifier
- [ ] Create `backend/src/extraction/complexity_classifier.py`
  ```python
  """
  Document complexity classifier for model selection.

  Classes:
  - ComplexityClassifier:
    - classify(document: DocumentContent) -> ComplexityLevel
    - Returns: STANDARD or COMPLEX

  Classification Heuristics:
  - STANDARD (use gemini-3-flash-preview):
    - Single borrower indicated
    - Clear standard form structure
    - Good scan quality
    - Typed/printed text
    - < 10 pages

  - COMPLEX (use gemini-3-pro-preview):
    - Multiple borrowers indicated
    - Non-standard or mixed document formats
    - Poor scan quality or handwritten sections
    - > 10 pages
    - Tables with complex cross-references
    - Conflicting information that needs reasoning

  Fast heuristic-based approach using document metadata and structure analysis.
  """
  ```

##### 2.3.3 SIMPLIFY: Run code-simplifier plugin on `backend/src/extraction/complexity_classifier.py`

##### 2.3.4 VERIFY: Run tests
- [ ] Run `pytest backend/tests/unit/test_complexity_classifier.py -v` — ALL PASS

---

#### Task 2.4: Extraction Prompts

##### 2.4.1 IMPLEMENT: Prompt Templates Tests
- [ ] Create `backend/tests/unit/test_prompts.py`
  ```python
  """
  Test cases:
  - test_extraction_prompt_renders_with_text
  - test_extraction_prompt_includes_schema
  - test_prompt_handles_special_characters
  """
  ```

##### 2.4.2 IMPLEMENT: Prompt Templates
- [ ] Create `backend/src/extraction/prompts.py`
  ```python
  """
  Extraction prompt templates.
  
  Constants:
  - BORROWER_EXTRACTION_SYSTEM_PROMPT
  - BORROWER_EXTRACTION_USER_PROMPT_TEMPLATE
  
  Functions:
  - build_extraction_prompt(document_text: str, schema: dict) -> tuple[str, str]
  """
  ```

##### 2.4.3 SIMPLIFY: Run code-simplifier plugin on `backend/src/extraction/prompts.py`

##### 2.4.4 VERIFY: Run tests
- [ ] Run `pytest backend/tests/unit/test_prompts.py -v` — ALL PASS

---

#### Task 2.5: Extraction Orchestrator

##### 2.5.1 IMPLEMENT: Extractor Tests
- [ ] Create `backend/tests/unit/test_extractor.py`
  ```python
  """
  Test cases:
  - test_extract_single_borrower
  - test_extract_multiple_borrowers
  - test_extract_with_chunking_for_large_docs
  - test_extract_deduplicates_results
  - test_extract_tracks_source_attribution
  - test_extract_calculates_confidence
  - test_extract_handles_extraction_failure
  """
  ```

##### 2.5.2 IMPLEMENT: Extractor Service
- [ ] Create `backend/src/extraction/extractor.py`
  ```python
  """
  Borrower extraction orchestrator.

  Classes:
  - BorrowerExtractor:
    - extract(document: DocumentContent, document_id: UUID) -> list[BorrowerRecord]
    - Assesses document complexity to select appropriate model
    - Chunks large documents
    - Calls LLM for each chunk (gemini-3-flash-preview default, gemini-3-pro-preview for complex)
    - Aggregates and deduplicates results
    - Tracks source attribution
    - Calculates confidence scores

  Chunking Strategy:
  - Max chunk size: 4000 tokens (~16,000 characters)
  - Overlap: 200 tokens to prevent data splitting
  - Split on paragraph boundaries when possible
  - Preserve table structures within single chunk
  - Track chunk position for source attribution

  Confidence Scoring Formula:
  - Base score: 0.5
  - +0.1 per complete required field (name, address)
  - +0.05 per complete optional field (income, account numbers)
  - +0.1 if multiple source documents confirm same data
  - +0.15 if data passes field format validation
  - Range: 0.0 to 1.0
  - Threshold for manual review: < 0.7

  Deduplication Logic:
  - Primary: Exact SSN/account number match
  - Secondary: Fuzzy name match (>90% similarity) + address match
  - Fallback: Name + last 4 of SSN/account
  - When duplicates found: Merge data, keep highest confidence fields
  - Track all source references from merged records
  """
  ```

##### 2.5.3 SIMPLIFY: Run code-simplifier plugin on `backend/src/extraction/extractor.py`

##### 2.5.4 REVIEW: Run `mypy backend/src/extraction/extractor.py --strict`

##### 2.5.5 FIX: Address any issues

##### 2.5.6 VERIFY: Run tests
- [ ] Run `pytest backend/tests/unit/test_extractor.py -v` — ALL PASS

---

#### Task 2.6: Data Quality Validation

##### 2.6.1 IMPLEMENT: Validation Rules Tests
- [ ] Create `backend/tests/unit/test_validation.py`
  ```python
  """
  Tests for data quality validation.

  Test cases:
  - test_ssn_format_validation
  - test_phone_number_format_validation
  - test_zip_code_format_validation
  - test_date_format_validation
  - test_confidence_threshold_flagging
  - test_cross_document_consistency_check
  """
  ```

##### 2.6.2 IMPLEMENT: Validation Service
- [ ] Create `backend/src/extraction/validation.py`
  ```python
  """
  Data quality validation service.

  Classes:
  - FieldValidator:
    - Validates SSN format (XXX-XX-XXXX)
    - Validates phone number format (various US formats)
    - Validates zip code format (XXXXX or XXXXX-XXXX)
    - Validates date formats
    - Uses regex patterns for format checking

  - ConfidenceValidator:
    - Flags records with confidence < 0.7 for manual review
    - Tracks validation reasons

  - ConsistencyValidator:
    - Checks borrower data consistency across documents
    - Validates income progression is logical
    - Flags conflicting addresses for same borrower

  - ValidationResult:
    - is_valid: bool
    - errors: list[ValidationError]
    - warnings: list[ValidationWarning]
    - requires_review: bool
  """
  ```

##### 2.6.3 SIMPLIFY: Run code-simplifier plugin on `backend/src/extraction/validation.py`

##### 2.6.4 VERIFY: Tests pass
- [ ] Run `pytest backend/tests/unit/test_validation.py -v` — ALL PASS

---

#### Task 2.7: Phase 2 Integration

##### 2.7.1 IMPLEMENT: Integration tests
- [ ] Create `backend/tests/integration/test_extraction_pipeline.py`
  ```python
  """
  Integration tests for extraction pipeline.

  Test cases:
  - test_standard_document_uses_flash_model
  - test_complex_document_uses_pro_model
  - test_model_selection_based_on_complexity
  - test_full_extraction_pipeline_end_to_end
  """
  ```

##### 2.7.2 SIMPLIFY: Run code-simplifier plugin on `backend/src/extraction/`

##### 2.7.3 VERIFY: Phase 2 complete
- [ ] Run `pytest backend/tests/ -v --cov=src/extraction` — ALL PASS, >80% coverage
- [ ] Run `mypy backend/src/extraction/ --strict` — NO ERRORS

### ✅ PHASE 2 SIGN-OFF
- [ ] All tasks completed
- [ ] All tests passing

---

## Phase 3: Database & Storage Layer

### Phase Overview

Implement PostgreSQL database models and repositories for storing extracted data.

---

#### Task 3.1: SQLAlchemy Models

##### 3.1.1 IMPLEMENT: Database Models Tests
- [ ] Create `backend/tests/unit/test_db_models.py`

##### 3.1.2 IMPLEMENT: Database Models
- [ ] Create `backend/src/storage/models.py`
  ```python
  """
  SQLAlchemy ORM models.
  
  Models:
  - Document: id, filename, file_hash, gcs_uri, status, created_at, processed_at
  - Borrower: id, name, address_json, confidence_score, created_at
  - IncomeRecord: id, borrower_id (FK), amount, period, year, source_type, employer
  - AccountNumber: id, borrower_id (FK), number, number_type
  - SourceReference: id, borrower_id (FK), document_id (FK), page, section, snippet
  """
  ```

##### 3.1.3 SIMPLIFY: Run code-simplifier plugin on `backend/src/storage/models.py`

##### 3.1.4 VERIFY: Run tests and type checks
- [ ] Run `pytest backend/tests/unit/test_db_models.py -v` — ALL PASS
- [ ] Run `mypy backend/src/storage/models.py --strict` — NO ERRORS

---

#### Task 3.2: Repositories

##### 3.2.1 IMPLEMENT: Repository Tests
- [ ] Create `backend/tests/unit/test_repositories.py`

##### 3.2.2 IMPLEMENT: Repositories
- [ ] Create `backend/src/storage/repositories.py`
  ```python
  """
  Data access layer with async SQLAlchemy.
  
  Classes:
  - DocumentRepository: create, get_by_id, get_by_hash, update_status, list
  - BorrowerRepository: create, get_by_id, search, list_with_pagination
  - Handles transactions and error wrapping
  """
  ```

##### 3.2.3 SIMPLIFY: Run code-simplifier plugin on `backend/src/storage/repositories.py`

##### 3.2.4 VERIFY: Run tests
- [ ] Run `pytest backend/tests/unit/test_repositories.py -v` — ALL PASS

---

#### Task 3.3: Database Migrations

##### 3.3.1 IMPLEMENT: Alembic Setup
- [ ] Initialize Alembic: `alembic init alembic`
- [ ] Configure `alembic.ini` for async PostgreSQL
- [ ] Create initial migration: `alembic revision --autogenerate -m "initial schema"`

##### 3.3.2 VERIFY: Migration applies cleanly
- [ ] Test migration up/down locally

### ✅ PHASE 3 SIGN-OFF
- [ ] All tasks completed
- [ ] All tests passing

---

## Phase 4: REST API

### Phase Overview

Build FastAPI endpoints for document upload and borrower querying.

---

#### Task 4.1: API Setup

##### 4.1.1 IMPLEMENT: FastAPI App
- [ ] Create `backend/src/main.py`
  ```python
  """
  FastAPI application entry point.
  
  - CORS middleware configured
  - Exception handlers for custom errors
  - OpenAPI documentation
  - Health check endpoint
  - Lifespan for DB connection pool
  """
  ```

##### 4.1.2 IMPLEMENT: Dependencies
- [ ] Create `backend/src/api/dependencies.py`
  ```python
  """
  FastAPI dependency injection.
  
  Dependencies:
  - get_db_session: Async SQLAlchemy session
  - get_document_service: DocumentService instance
  - get_borrower_repository: BorrowerRepository instance
  """
  ```

##### 4.1.3 SIMPLIFY: Run code-simplifier plugin on `backend/src/main.py` and `backend/src/api/dependencies.py`

##### 4.1.4 VERIFY: App starts without errors

---

#### Task 4.2: Document Endpoints

##### 4.2.1 IMPLEMENT: Document Routes Tests
- [ ] Create `backend/tests/unit/test_document_routes.py`
  ```python
  """
  Test cases:
  - test_upload_document_returns_201
  - test_upload_invalid_file_returns_400
  - test_get_document_status_returns_status
  - test_get_document_not_found_returns_404
  - test_list_documents_with_pagination
  """
  ```

##### 4.2.2 IMPLEMENT: Document Routes
- [ ] Create `backend/src/api/routes/documents.py`
  ```python
  """
  Document API endpoints.
  
  Endpoints:
  - POST /api/documents - Upload document for processing
  - GET /api/documents/{id} - Get document details
  - GET /api/documents/{id}/status - Get processing status
  - GET /api/documents - List documents with pagination
  """
  ```

##### 4.2.3 SIMPLIFY: Run code-simplifier plugin on `backend/src/api/routes/documents.py`

##### 4.2.4 VERIFY: Run tests
- [ ] Run `pytest backend/tests/unit/test_document_routes.py -v` — ALL PASS

---

#### Task 4.3: Borrower Endpoints

##### 4.3.1 IMPLEMENT: Borrower Routes Tests
- [ ] Create `backend/tests/unit/test_borrower_routes.py`
  ```python
  """
  Test cases:
  - test_list_borrowers_returns_paginated_results
  - test_get_borrower_returns_full_details
  - test_get_borrower_not_found_returns_404
  - test_get_borrower_sources_returns_documents
  - test_search_borrowers_by_name
  - test_search_borrowers_by_account_number
  """
  ```

##### 4.3.2 IMPLEMENT: Borrower Routes
- [ ] Create `backend/src/api/routes/borrowers.py`
  ```python
  """
  Borrower API endpoints.
  
  Endpoints:
  - GET /api/borrowers - List borrowers with pagination
  - GET /api/borrowers/{id} - Get borrower details
  - GET /api/borrowers/{id}/sources - Get source documents
  - GET /api/borrowers/search - Search by name, account, loan number
  """
  ```

##### 4.3.3 SIMPLIFY: Run code-simplifier plugin on `backend/src/api/routes/borrowers.py`

##### 4.3.4 VERIFY: Run tests
- [ ] Run `pytest backend/tests/unit/test_borrower_routes.py -v` — ALL PASS

---

#### Task 4.4: Phase 4 Integration

##### 4.4.1 IMPLEMENT: E2E API Tests
- [ ] Create `backend/tests/e2e/test_api.py`
  ```python
  """
  End-to-end API tests.
  
  Test cases:
  - test_full_upload_to_query_flow
  - test_upload_process_and_search
  """
  ```

##### 4.4.2 SIMPLIFY: Run code-simplifier plugin on `backend/src/api/`

##### 4.4.3 VERIFY: Phase 4 complete
- [ ] Run `pytest backend/tests/ -v` — ALL PASS
- [ ] Run `mypy backend/src/ --strict` — NO ERRORS

### ✅ PHASE 4 SIGN-OFF
- [ ] All tasks completed
- [ ] All tests passing

---

## Phase 5: Frontend UI

### Phase Overview

Build a high-fidelity Next.js frontend with pages for document management, borrower viewing, and architecture documentation.

---

#### Task 5.1: Project Setup

##### 5.1.1 IMPLEMENT: Next.js Configuration
- [ ] Create `frontend/next.config.js` with API proxy configuration
- [ ] Create `frontend/tailwind.config.ts` with custom theme
- [ ] Create `frontend/src/app/layout.tsx` with navigation

##### 5.1.2 IMPLEMENT: shadcn/ui Components
- [ ] Initialize shadcn/ui: `npx shadcn-ui@latest init`
- [ ] Add components: button, card, table, input, dialog, tabs, badge, skeleton

##### 5.1.3 IMPLEMENT: API Client
- [ ] Create `frontend/src/lib/api.ts`
  ```typescript
  /**
   * Type-safe API client using fetch.
   * 
   * Functions:
   * - uploadDocument(file: File): Promise<DocumentResponse>
   * - getDocumentStatus(id: string): Promise<StatusResponse>
   * - listBorrowers(params: ListParams): Promise<PaginatedBorrowers>
   * - getBorrower(id: string): Promise<BorrowerDetail>
   * - searchBorrowers(query: string): Promise<BorrowerDetail[]>
   */
  ```

##### 5.1.4 SIMPLIFY: Run code-simplifier plugin on `frontend/src/lib/api.ts`

---

#### Task 5.2: Document Management Pages

##### 5.2.1 IMPLEMENT: Document Upload Page
- [ ] Create `frontend/src/app/documents/page.tsx`
  ```typescript
  /**
   * Document management page.
   * 
   * Features:
   * - Drag-and-drop file upload
   * - Upload progress indicator
   * - Document list with status badges
   * - Click to view document details
   */
  ```

##### 5.2.2 IMPLEMENT: Document Detail Page
- [ ] Create `frontend/src/app/documents/[id]/page.tsx`
  ```typescript
  /**
   * Document detail page.
   * 
   * Features:
   * - Processing status with progress
   * - Extracted borrowers list
   * - Link to view document in GCS
   * - Processing error display
   */
  ```

##### 5.2.3 IMPLEMENT: Document Components
- [ ] Create `frontend/src/components/documents/upload-zone.tsx`
- [ ] Create `frontend/src/components/documents/document-table.tsx`
- [ ] Create `frontend/src/components/documents/status-badge.tsx`

##### 5.2.4 SIMPLIFY: Run code-simplifier plugin on `frontend/src/app/documents/`

---

#### Task 5.3: Borrower Pages

##### 5.3.1 IMPLEMENT: Borrower List Page
- [ ] Create `frontend/src/app/borrowers/page.tsx`
  ```typescript
  /**
   * Borrower list page.
   * 
   * Features:
   * - Search bar (name, account, loan number)
   * - Paginated table of borrowers
   * - Confidence score indicator
   * - Quick view of key fields
   */
  ```

##### 5.3.2 IMPLEMENT: Borrower Detail Page
- [ ] Create `frontend/src/app/borrowers/[id]/page.tsx`
  ```typescript
  /**
   * Borrower detail page.
   * 
   * Features:
   * - Full borrower information display
   * - Income history timeline
   * - Account/loan numbers list
   * - Source documents with links
   * - Confidence score breakdown
   */
  ```

##### 5.3.3 IMPLEMENT: Borrower Components
- [ ] Create `frontend/src/components/borrowers/borrower-card.tsx`
- [ ] Create `frontend/src/components/borrowers/income-timeline.tsx`
- [ ] Create `frontend/src/components/borrowers/source-references.tsx`
- [ ] Create `frontend/src/components/borrowers/search-bar.tsx`

##### 5.3.4 SIMPLIFY: Run code-simplifier plugin on `frontend/src/app/borrowers/`

---

#### Task 5.4: Architecture Documentation Pages

##### 5.4.1 IMPLEMENT: Architecture Overview Page
- [ ] Create `frontend/src/app/architecture/page.tsx`
  ```typescript
  /**
   * Architecture overview page.
   *
   * Content:
   * - Interactive system diagram using Mermaid component diagram
   * - Component descriptions
   * - Technology stack table
   * - Links to detailed sections
   *
   * Mermaid Diagram:
   * - Shows all major components (Frontend, Backend API, LLM Client,
   *   Docling Processor, Database, GCS)
   * - Connection arrows showing data flow
   * - Labeled with technologies used
   */
  ```

##### 5.4.2 IMPLEMENT: Design Decisions Page
- [ ] Create `frontend/src/app/architecture/decisions/page.tsx`
  ```typescript
  /**
   * Architecture Decision Records (ADRs) page.
   * 
   * Content:
   * - Why Docling for document processing
   * - Why Claude 3.5 Sonnet for extraction
   * - Why PostgreSQL over alternatives
   * - Why Cloud Run over GKE
   * - Trade-offs and alternatives considered
   */
  ```

##### 5.4.3 IMPLEMENT: Data Pipeline Page
- [ ] Create `frontend/src/app/architecture/pipeline/page.tsx`
  ```typescript
  /**
   * Data pipeline visualization page.
   *
   * Content:
   * - Interactive pipeline flowchart using Mermaid
   * - Step-by-step flow explanation
   * - Data transformation examples
   * - Error handling strategy
   *
   * Mermaid Flowchart:
   * - Upload → GCS Storage → Docling Processing → LLM Extraction
   *   → Validation → Database Storage → API Retrieval
   * - Decision nodes for error handling
   * - Retry loops shown clearly
   */
  ```

##### 5.4.4 IMPLEMENT: Scaling Strategy Page
- [ ] Create `frontend/src/app/architecture/scaling/page.tsx`
  ```typescript
  /**
   * Scaling considerations page.
   *
   * Content:
   * - Current architecture limits
   * - 10x scaling strategy with Mermaid architecture diagram
   * - 100x scaling strategy with Mermaid architecture diagram
   * - Cost projections chart
   * - Performance benchmarks
   *
   * Mermaid Diagrams:
   * - Current: Single Cloud Run instance + Cloud SQL
   * - 10x: Multiple Cloud Run instances + read replicas
   * - 100x: Regional deployment + Cloud Tasks + caching layer
   */
  ```

##### 5.4.5 IMPLEMENT: Architecture Components
- [ ] Create `frontend/src/components/architecture/system-diagram.tsx`
- [ ] Create `frontend/src/components/architecture/pipeline-flow.tsx`
- [ ] Create `frontend/src/components/architecture/decision-card.tsx`
- [ ] Create `frontend/src/components/architecture/scaling-chart.tsx`

##### 5.4.6 SIMPLIFY: Run code-simplifier plugin on `frontend/src/app/architecture/`

---

#### Task 5.5: Dashboard Home Page

##### 5.5.1 IMPLEMENT: Dashboard Page
- [ ] Create `frontend/src/app/page.tsx`
  ```typescript
  /**
   * Main dashboard page.
   * 
   * Features:
   * - Quick stats (documents processed, borrowers extracted)
   * - Recent documents with status
   * - Quick search
   * - Links to main sections
   */
  ```

##### 5.5.2 IMPLEMENT: Navigation
- [ ] Create `frontend/src/components/nav/sidebar.tsx`
- [ ] Create `frontend/src/components/nav/header.tsx`

##### 5.5.3 SIMPLIFY: Run code-simplifier plugin on `frontend/src/app/page.tsx`

---

#### Task 5.6: Phase 5 Verification

##### 5.6.1 VERIFY: Frontend builds and runs
- [ ] Run `npm run build` — NO ERRORS
- [ ] Run `npm run dev` — App starts successfully
- [ ] Manually verify all pages render correctly

##### 5.6.2 IMPLEMENT: Frontend Smoke Tests
- [ ] Create `frontend/src/__tests__/smoke.test.tsx`
  ```typescript
  /**
   * Frontend smoke tests.
   *
   * Test cases:
   * - test_home_page_renders
   * - test_documents_page_renders
   * - test_borrowers_page_renders
   * - test_architecture_overview_page_renders
   * - test_architecture_decisions_page_renders
   * - test_architecture_pipeline_page_renders
   * - test_architecture_scaling_page_renders
   *
   * Run with: npm test
   */
  ```

##### 5.6.3 VERIFY: Run frontend tests
- [ ] Run `npm test` — ALL PASS

### ✅ PHASE 5 SIGN-OFF
- [ ] All pages implemented
- [ ] Build succeeds
- [ ] UI is responsive and functional

---

## Phase 6: GCP Infrastructure

### Phase Overview

Create Terraform configuration for deploying to Google Cloud Platform.

---

#### Task 6.1: Terraform Setup

##### 6.1.1 IMPLEMENT: Terraform Configuration
- [ ] Create `infrastructure/terraform/main.tf`
  ```hcl
  # Provider configuration
  # Project settings
  # Enable required APIs
  ```

##### 6.1.2 IMPLEMENT: Variables
- [ ] Create `infrastructure/terraform/variables.tf`
  ```hcl
  # Variables:
  # - project_id
  # - region
  # - environment (dev/staging/prod)
  # - db_instance_tier
  # - cloud_run_cpu
  # - cloud_run_memory
  ```

---

#### Task 6.2: Cloud SQL

##### 6.2.1 IMPLEMENT: Cloud SQL Configuration
- [ ] Create `infrastructure/terraform/cloud_sql.tf`
  ```hcl
  # PostgreSQL instance
  # Database creation
  # User creation
  # Private IP configuration
  # Backup configuration
  ```

---

#### Task 6.3: Cloud Storage

##### 6.3.1 IMPLEMENT: GCS Configuration
- [ ] Create `infrastructure/terraform/cloud_storage.tf`
  ```hcl
  # Document storage bucket
  # Lifecycle rules (archive after 90 days)
  # IAM bindings for Cloud Run
  # CORS configuration
  ```

---

#### Task 6.4: Cloud Run

##### 6.4.1 IMPLEMENT: Cloud Run Backend
- [ ] Create `infrastructure/terraform/cloud_run.tf`
  ```hcl
  # Backend service
  # - Container configuration
  # - Environment variables from Secret Manager
  # - Cloud SQL connection
  # - Autoscaling settings
  
  # Frontend service
  # - Container configuration
  # - Environment variables
  # - Autoscaling settings
  ```

---

#### Task 6.5: Cloud Tasks

##### 6.5.1 IMPLEMENT: Cloud Tasks Configuration
- [ ] Create `infrastructure/terraform/cloud_tasks.tf`
  ```hcl
  # Task queue for document processing
  # Retry configuration
  # Rate limiting
  ```

---

#### Task 6.6: IAM & Security

##### 6.6.1 IMPLEMENT: IAM Configuration
- [ ] Create `infrastructure/terraform/iam.tf`
  ```hcl
  # Service accounts
  # - Backend service account
  # - Cloud Tasks invoker
  # IAM bindings
  # Secret Manager secrets
  ```

---

#### Task 6.7: Outputs

##### 6.7.1 IMPLEMENT: Terraform Outputs
- [ ] Create `infrastructure/terraform/outputs.tf`
  ```hcl
  # Output values:
  # - Backend URL
  # - Frontend URL
  # - Database connection string
  # - Storage bucket name
  ```

---

#### Task 6.8: Deployment Scripts

##### 6.8.1 IMPLEMENT: Setup Script
- [ ] Create `infrastructure/scripts/setup-gcp.sh`
  ```bash
  #!/bin/bash
  # Enable required GCP APIs
  # Create Terraform state bucket
  # Initialize Terraform
  ```

##### 6.8.2 IMPLEMENT: Deploy Script
- [ ] Create `infrastructure/scripts/deploy.sh`
  ```bash
  #!/bin/bash
  # Build and push Docker images
  # Apply Terraform
  # Run database migrations
  # Verify deployment
  ```

---

#### Task 6.9: Dockerfiles

##### 6.9.1 IMPLEMENT: Backend Dockerfile
- [ ] Create `backend/Dockerfile`
  ```dockerfile
  # Multi-stage build
  # Python 3.11 slim base
  # Install dependencies
  # Copy source
  # Run with uvicorn
  ```

##### 6.9.2 IMPLEMENT: Frontend Dockerfile
- [ ] Create `frontend/Dockerfile`
  ```dockerfile
  # Multi-stage build
  # Node 20 alpine base
  # Build Next.js
  # Run with next start
  ```

---

#### Task 6.10: Phase 6 Verification

##### 6.10.1 VERIFY: Terraform validates
- [ ] Run `terraform init`
- [ ] Run `terraform validate` — NO ERRORS
- [ ] Run `terraform plan` — Review resources

### ✅ PHASE 6 SIGN-OFF
- [ ] All Terraform files created
- [ ] Terraform validates successfully
- [ ] Deployment scripts ready

---

## Phase 7: Documentation & Final Integration

### Phase Overview

Complete all documentation and perform final integration testing.

---

#### Task 7.1: System Design Document

##### 7.1.1 IMPLEMENT: SYSTEM_DESIGN.md
- [ ] Create `docs/SYSTEM_DESIGN.md`
  ```markdown
  # System Design Document

  ## Architecture Overview
  - Mermaid component diagram showing all major components
  - Data flow description
  - Technology stack

  ## Data Pipeline Design
  - Mermaid flowchart of entire pipeline
  - Ingestion with Docling
  - LLM extraction with Claude
  - Validation layer
  - Storage in PostgreSQL
  - API retrieval

  ## AI/LLM Integration Strategy
  - Model selection rationale (Gemini 3.0 Pro Preview / Flash Preview)
  - Dynamic model selection: Pro for complex docs, Flash for standard docs
  - Structured output with Pydantic schema validation
  - Prompt engineering approach
  - Chunking strategy (4000 tokens, 200 token overlap)
  - Confidence scoring formula
  - Error recovery strategy
  - Context caching for common document templates

  ## Document Format Handling
  - Docling capabilities
  - Supported formats (PDF, DOCX, PNG/JPG)
  - OCR for images
  - Table extraction

  ## Data Quality Validation
  - Field format validation (SSN, phone, zip, dates)
  - Confidence thresholds (< 0.7 requires review)
  - Cross-document consistency checking
  - Deduplication logic

  ## Scaling Considerations
  - Current architecture (baseline)
  - 10x scaling strategy with Mermaid diagram
  - 100x scaling strategy with Mermaid diagram
  - Bottleneck analysis

  ## Cost Analysis
  ### Per-Document Costs (Gemini 3.0 Pro Preview)
  - Input: ~2000 tokens avg @ $1.25/1M tokens = $0.0025
  - Output: ~500 tokens avg @ $5/1M tokens = $0.0025
  - Total per document: ~$0.005

  ### Per-Document Costs (Gemini 3.0 Flash Preview - Recommended Default)
  - Input: ~2000 tokens avg @ $0.075/1M tokens = $0.00015
  - Output: ~500 tokens avg @ $0.30/1M tokens = $0.00015
  - Total per document: ~$0.0003

  ### Hybrid Strategy (80% Flash, 20% Pro for Complex Docs)
  - Average cost per document: ~$0.0012
  - Balances cost and accuracy for mixed document complexity

  ### Scaling Projections (Hybrid Strategy)
  - 1,000 docs/month: ~$1.20/month
  - 10,000 docs/month (10x): ~$12/month
  - 100,000 docs/month (100x): ~$120/month

  ### Scaling Projections (Flash Only - Maximum Savings)
  - 1,000 docs/month: ~$0.30/month
  - 10,000 docs/month (10x): ~$3/month
  - 100,000 docs/month (100x): ~$30/month

  ### Cost Optimization Strategies
  - Default to gemini-3-flash-preview for standard loan documents
  - Use gemini-3-pro-preview only for complex multi-borrower scenarios
  - Implement document complexity classifier to route intelligently
  - Use context caching for common document templates (up to 75% cost reduction)
  - Batch processing to reduce API overhead
  - Implement result caching with document hash
  - Enable prompt caching for system instructions and schemas

  ## Error Handling
  - Processing failures with retry logic
  - LLM errors (rate limits, timeouts, server errors)
  - Data validation errors
  - Recovery strategies
  ```

---

#### Task 7.2: Architecture Decisions Document

##### 7.2.1 IMPLEMENT: ARCHITECTURE_DECISIONS.md
- [ ] Create `docs/ARCHITECTURE_DECISIONS.md`
  ```markdown
  # Architecture Decision Records

  ## ADR-001: Docling for Document Processing
  - Context: Need robust document parsing for PDF, DOCX, images
  - Decision: Use Docling library
  - Consequences: Production-grade parsing, table extraction, OCR support
  - Alternatives considered: PyPDF2 (limited), PDFPlumber (no DOCX), custom solution (too complex)
  - Mermaid diagram comparing processing capabilities

  ## ADR-002: Gemini 3.0 Preview Models for Extraction
  - Context: Need accurate structured data extraction from unstructured documents with varying complexity
  - Decision: Use Gemini 3.0 Flash Preview as default, Gemini 3.0 Pro Preview for complex cases
  - Consequences: State-of-the-art accuracy, native structured output, highly cost-effective, GCP-native integration
  - Alternatives considered: Claude 3.5 Sonnet (more expensive at $3/$15 per 1M tokens), GPT-4 (similar cost to Claude), Gemini 2.5 (previous generation), open-source models (less accurate)
  - Cost comparison: Gemini 3 Flash is 40x cheaper than Claude for input, 50x cheaper for output
  - Model selection strategy:
    - gemini-3-flash-preview: Default for standard loan documents (~80% of cases)
    - gemini-3-pro-preview: Complex multi-borrower docs, unclear formatting (~20% of cases)
  - GCP benefits: Seamless integration with Cloud Run, Cloud Tasks, Vertex AI for monitoring
  - Performance: Gemini 3 models include latest reasoning capabilities and improved structured output

  ## ADR-003: PostgreSQL for Storage
  - Context: Need relational storage for borrower data with complex relationships
  - Decision: Use PostgreSQL with SQLAlchemy
  - Consequences: ACID guarantees, complex queries, JSON support for flexible fields
  - Alternatives considered: MongoDB (no joins), DynamoDB (complex queries difficult)

  ## ADR-004: Cloud Run for Compute
  - Context: Need scalable, managed compute for API and background jobs
  - Decision: Use Cloud Run with Cloud Tasks
  - Consequences: Auto-scaling, pay-per-use, simpler than GKE
  - Alternatives considered: GKE (more complex), Cloud Functions (15min timeout)
  - Mermaid diagram showing deployment architecture

  ## ADR-005: Next.js for Frontend
  - Context: Need modern, performant frontend framework
  - Decision: Use Next.js 14 with App Router
  - Consequences: Server components, excellent performance, built-in API routes
  - Alternatives considered: React SPA (no SSR), Vue (smaller ecosystem)
  ```

---

#### Task 7.3: README

##### 7.3.1 IMPLEMENT: README.md
- [ ] Create `README.md`
  ```markdown
  # Loan Document Extraction System
  
  ## Overview
  Brief description of the system
  
  ## Quick Start
  Local development setup
  
  ## Architecture
  High-level architecture summary
  Link to full design docs
  
  ## API Documentation
  Key endpoints with examples
  
  ## Deployment
  GCP deployment instructions
  
  ## Development
  - Running tests
  - Code style
  - Contributing
  ```

---

#### Task 7.4: Final Integration Test

##### 7.4.1 IMPLEMENT: Full E2E Test
- [ ] Create and run comprehensive E2E test
  ```python
  """
  Full system integration test.
  
  Flow:
  1. Upload PDF document via API
  2. Wait for processing to complete
  3. Query borrowers via API
  4. Verify extraction accuracy
  5. Verify source attribution
  """
  ```

##### 7.4.2 VERIFY: All tests pass
- [ ] Run `pytest backend/tests/ -v --cov=src` — ALL PASS, >80% coverage
- [ ] Run `mypy backend/src/ --strict` — NO ERRORS

##### 7.4.3 IMPLEMENT: Sample Loan Documents Integration Test
- [ ] Create `backend/tests/integration/test_sample_loan_docs.py`
  ```python
  """
  Integration tests using real sample loan documents.

  Test flow:
  1. Process all PDFs in loan-docs/Loan 214/ directory
  2. Extract borrower data from each document
  3. Verify extraction accuracy against expected results
  4. Verify all source documents are tracked with page numbers
  5. Verify confidence scores > 0.7 for complete documents
  6. Verify deduplication merges same borrower across docs
  7. Generate detailed extraction report

  Expected outputs:
  - Borrower names extracted correctly
  - Addresses parsed and structured
  - Income history captured from all documents
  - Account and loan numbers identified
  - Source attribution includes page numbers and snippets

  Test cases:
  - test_process_all_sample_loan_documents
  - test_borrower_extraction_accuracy
  - test_source_attribution_completeness
  - test_confidence_scores_meet_threshold
  - test_income_history_completeness
  - test_cross_document_deduplication
  """
  ```

##### 7.4.4 VERIFY: Sample document tests pass
- [ ] Run `pytest backend/tests/integration/test_sample_loan_docs.py -v` — ALL PASS

---

#### Task 7.5: Final Code Simplification

##### 7.5.1 SIMPLIFY: Run code-simplifier on entire codebase
- [ ] Run code-simplifier plugin on `backend/src/`
- [ ] Run code-simplifier plugin on `frontend/src/`

##### 7.5.2 VERIFY: Final checks
- [ ] All tests pass
- [ ] All type checks pass
- [ ] Frontend builds successfully
- [ ] Terraform validates

### ✅ PHASE 7 SIGN-OFF
- [ ] Documentation complete
- [ ] All tests passing
- [ ] Code simplified

---

## Project Completion Checklist

### Deliverable 1: System Design Document
- [ ] Architecture overview with component diagram
- [ ] Data pipeline design
- [ ] AI/LLM integration strategy
- [ ] Document format handling approach
- [ ] Scaling considerations (10x, 100x)
- [ ] Technical trade-offs
- [ ] Error handling strategy

### Deliverable 2: Working Implementation
- [ ] Document ingestion pipeline (Docling)
- [ ] LLM extraction logic (Claude)
- [ ] Structured output generation (PostgreSQL)
- [ ] Query/retrieval API (FastAPI)
- [ ] High-fidelity UI (Next.js)
- [ ] Test coverage >80%

### Deliverable 3: README
- [ ] Setup instructions
- [ ] Architecture summary
- [ ] API usage examples

### Bonus: GCP Infrastructure
- [ ] Terraform configuration
- [ ] Deployment scripts
- [ ] Production-ready Dockerfiles

---

## Quick Reference Commands

```bash
# Backend
cd backend
pytest tests/ -v --cov=src                    # Run all tests
pytest tests/unit/test_MODULE.py -v           # Run specific tests
mypy src/ --strict                            # Type check

# Frontend  
cd frontend
npm run dev                                    # Development server
npm run build                                  # Production build
npm run test                                   # Run tests

# Infrastructure
cd infrastructure/terraform
terraform init                                 # Initialize
terraform validate                             # Validate
terraform plan                                 # Preview changes
terraform apply                                # Deploy

# Code Simplification
# Use the code-simplifier plugin on <file_or_directory>
```

---

*Document Version: 3.0 | Optimized for Claude Code CLI Agent with Docling + GCP*