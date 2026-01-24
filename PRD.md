# Product Requirements Document
## Loan Document Data Extraction System
### Optimized for Parallel Subagent Execution

---

| Field | Value |
|-------|-------|
| **Version** | 4.0 |
| **Date** | January 2026 |
| **Methodology** | Test-Driven Development (TDD) |
| **Target Corpus** | Loan Documents |
| **Agent** | Claude Code CLI with Parallel Subagents |
| **Document Processing** | Docling |
| **Deployment** | Google Cloud Platform |

---

## Parallel Execution Strategy

This PRD is optimized for **parallel subagent execution**. Tasks are organized with:
- ✅ **Explicit dependencies** - Tasks list what they depend on
- ✅ **Parallelization markers** - Clear indicators of what can run concurrently
- ✅ **Atomic boundaries** - Each task is self-contained with clear inputs/outputs
- ✅ **Blocking relationships** - Prerequisites are explicitly marked

### Agent Coordination Pattern
```
1. SPAWN     → Launch multiple subagents in parallel for independent tasks
2. IMPLEMENT → Each agent writes tests first (TDD), then implementation
3. SIMPLIFY  → Run code-simplifier plugin on modified files
4. VERIFY    → Run pytest and mypy to confirm passing
5. SYNC      → Wait for dependencies before proceeding to next phase
```

---

## Project Goals & Requirements

### Overview
Build an unstructured data extraction system using a provided document corpus. This implementation uses the **Loan Documents** dataset to extract structured borrower information.

### Timeline
- **Deadline:** 7 days from receipt
- **Expected effort:** 4–8 hours (with parallel execution)

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
- [ ] Architecture overview, including component diagram
- [ ] Data pipeline design covering ingestion, processing, storage, and retrieval
- [ ] AI/LLM integration strategy and model selection rationale
- [ ] Approach for handling document format variability
- [ ] Scaling considerations for 10x and 100x document volume
- [ ] Key technical trade-offs and reasoning
- [ ] Error handling strategy and data quality validation approach

#### 2. Working Implementation
- [ ] Document ingestion pipeline
- [ ] Extraction logic using AI/LLM tooling (Gemini 3.0)
- [ ] Structured output generation (PostgreSQL database-backed)
- [ ] Basic query or retrieval interface (FastAPI REST API)
- [ ] Test coverage for critical paths (>80% target)

#### 3. README
- [ ] Setup and run instructions
- [ ] Summary of architectural and implementation decisions

### Bonus
- [ ] GCP deployment infrastructure with Terraform
- [ ] High-fidelity frontend UI for data visualization

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

**⚡ PARALLELIZATION:** All tasks in this phase can run in parallel

### Dependencies
- None (initial setup)

### Tasks

#### Task 0.1: Create Project Structure
**Can run in parallel with:** 0.2, 0.3

- [ ] **0.1.1 IMPLEMENT**: Create directory structure
  ```bash
  mkdir -p loan-extraction-system/{backend/{src/{ingestion,extraction,storage,api/routes,models},tests/{unit,integration,e2e}},frontend/{src/{app/{documents,borrowers,architecture/{decisions,pipeline,scaling},api},components/{ui,documents,borrowers,architecture},lib}},infrastructure/{terraform,scripts},docs}
  ```

#### Task 0.2: Backend Configuration
**Can run in parallel with:** 0.1, 0.3

- [ ] **0.2.1 IMPLEMENT**: Create backend pyproject.toml
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

- [ ] **0.2.2 IMPLEMENT**: Create backend config
  - Create `backend/src/config.py` with Pydantic Settings
  - Create `backend/.env.example` with required variables

- [ ] **0.2.3 SIMPLIFY**: Run code-simplifier plugin on `backend/src/config.py`

#### Task 0.3: Frontend Configuration
**Can run in parallel with:** 0.1, 0.2

- [ ] **0.3.1 IMPLEMENT**: Create frontend package.json
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

- [ ] **0.3.2 IMPLEMENT**: Create frontend config
  - Create `frontend/.env.example` with API URL

#### Task 0.4: Verify Setup
**Depends on:** 0.1, 0.2, 0.3

- [ ] **0.4.1 VERIFY**: Install dependencies and verify setup
  ```bash
  cd backend && pip install -e ".[dev]"
  cd frontend && npm install
  pytest --collect-only
  mypy src/ --strict
  ```

### ✅ PHASE 0 SIGN-OFF
- [ ] All tasks completed
- [ ] Dependencies installed
- [ ] Project structure created

---

## Phase 1: Document Ingestion with Docling

**⚡ PARALLELIZATION:** Tasks 1.1, 1.2, 1.3 can run in parallel. Task 1.4 depends on all three.

### Phase Overview
Use Docling for document processing. Docling handles PDF, DOCX, images, and more with layout understanding and table extraction built-in.

### Dependencies
- Phase 0 complete

### Acceptance Criteria
- Docling processes PDF, DOCX, PNG/JPG documents
- Extracted text preserves structure (tables, sections)
- Documents are stored in GCS with metadata in PostgreSQL
- Processing errors are handled gracefully

---

#### Task 1.1: Docling Processor
**Can run in parallel with:** 1.2, 1.3
**Dependencies:** None

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

##### 1.1.4 VERIFY: Run tests
- [ ] Run `pytest backend/tests/unit/test_docling_processor.py -v` — ALL PASS
- [ ] Run `mypy backend/src/ingestion/docling_processor.py --strict` — NO ERRORS

---

#### Task 1.2: Document Service
**Can run in parallel with:** 1.1, 1.3
**Dependencies:** None (mocks GCS and Docling for unit tests)

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

##### 1.2.4 VERIFY: Run tests
- [ ] Run `pytest backend/tests/unit/test_document_service.py -v` — ALL PASS
- [ ] Run `mypy backend/src/ingestion/document_service.py --strict` — NO ERRORS

---

#### Task 1.3: GCS Storage Client
**Can run in parallel with:** 1.1, 1.2
**Dependencies:** None

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

##### 1.3.4 VERIFY: Run tests
- [ ] Run `pytest backend/tests/unit/test_gcs_client.py -v` — ALL PASS
- [ ] Run `mypy backend/src/storage/gcs_client.py --strict` — NO ERRORS

---

#### Task 1.4: Phase 1 Integration
**Depends on:** 1.1, 1.2, 1.3

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

**⚡ PARALLELIZATION:** Tasks 2.1-2.6 can largely run in parallel. Task 2.7 depends on all previous tasks.

### Phase Overview
Build the extraction engine using Gemini 3.0 Pro Preview to extract structured borrower data from processed documents.

### Dependencies
- Phase 0 complete (for project structure)

### Acceptance Criteria
- LLM client handles Gemini API with retries
- Structured output validated against Pydantic schema
- Source attribution tracked for all extractions
- Confidence scoring implemented

---

#### Task 2.1: Pydantic Models
**Can run in parallel with:** 2.2, 2.3, 2.4
**Dependencies:** None

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
**Can run in parallel with:** 2.1, 2.3, 2.4
**Dependencies:** None

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
  """
  ```

##### 2.2.3 SIMPLIFY: Run code-simplifier plugin on `backend/src/extraction/llm_client.py`

##### 2.2.4 VERIFY: Run tests
- [ ] Run `pytest backend/tests/unit/test_llm_client.py -v` — ALL PASS
- [ ] Run `mypy backend/src/extraction/llm_client.py --strict` — NO ERRORS

---

#### Task 2.3: Document Complexity Classifier
**Can run in parallel with:** 2.1, 2.2, 2.4
**Dependencies:** None

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
**Can run in parallel with:** 2.1, 2.2, 2.3
**Dependencies:** None

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
**Depends on:** 2.1 (uses BorrowerRecord), 2.2 (uses LLM client), 2.3 (uses classifier)
**Can run in parallel with:** 2.6

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

##### 2.5.4 VERIFY: Run tests
- [ ] Run `pytest backend/tests/unit/test_extractor.py -v` — ALL PASS
- [ ] Run `mypy backend/src/extraction/extractor.py --strict` — NO ERRORS

---

#### Task 2.6: Data Quality Validation
**Depends on:** 2.1 (validates BorrowerRecord)
**Can run in parallel with:** 2.5

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
**Depends on:** 2.1, 2.2, 2.3, 2.4, 2.5, 2.6

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

**⚡ PARALLELIZATION:** Tasks 3.1 and 3.2 can run in parallel. Task 3.3 depends on 3.1.

### Phase Overview
Implement PostgreSQL database models and repositories for storing extracted data.

### Dependencies
- Phase 0 complete

---

#### Task 3.1: SQLAlchemy Models
**Can run in parallel with:** 3.2
**Dependencies:** None

##### 3.1.1 IMPLEMENT: Database Models Tests
- [ ] Create `backend/tests/unit/test_db_models.py`
  ```python
  """
  Test cases:
  - test_document_model_creation
  - test_borrower_model_creation
  - test_income_record_relationship
  - test_account_number_relationship
  - test_source_reference_relationship
  - test_json_serialization
  """
  ```

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
**Can run in parallel with:** 3.1
**Dependencies:** None (mocks DB for unit tests)

##### 3.2.1 IMPLEMENT: Repository Tests
- [ ] Create `backend/tests/unit/test_repositories.py`
  ```python
  """
  Test cases:
  - test_document_repository_create
  - test_document_repository_get_by_id
  - test_document_repository_get_by_hash
  - test_borrower_repository_create
  - test_borrower_repository_search
  - test_borrower_repository_pagination
  - test_transaction_rollback_on_error
  """
  ```

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
**Depends on:** 3.1

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

**⚡ PARALLELIZATION:** Tasks 4.2 and 4.3 can run in parallel. Task 4.4 depends on all previous tasks.

### Phase Overview
Build FastAPI endpoints for document upload and borrower querying.

### Dependencies
- Phase 1 (document service)
- Phase 2 (extraction models)
- Phase 3 (database repositories)

---

#### Task 4.1: API Setup
**Dependencies:** Phase 3
**Must complete before:** 4.2, 4.3

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
**Can run in parallel with:** 4.3
**Depends on:** 4.1

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
**Can run in parallel with:** 4.2
**Depends on:** 4.1

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
**Depends on:** 4.1, 4.2, 4.3

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

**⚡ PARALLELIZATION:** Tasks 5.2, 5.3, 5.4, 5.5 can all run in parallel after 5.1 completes.

### Phase Overview
Build a high-fidelity Next.js frontend with pages for document management, borrower viewing, and architecture documentation.

### Dependencies
- Phase 0 complete
- Phase 4 complete (API endpoints available)

---

#### Task 5.1: Project Setup
**Must complete before:** 5.2, 5.3, 5.4, 5.5

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
**Can run in parallel with:** 5.3, 5.4, 5.5
**Depends on:** 5.1

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

##### 5.2.3 IMPLEMENT: Document Components
- [ ] Create `frontend/src/components/documents/upload-zone.tsx`
- [ ] Create `frontend/src/components/documents/document-table.tsx`
- [ ] Create `frontend/src/components/documents/status-badge.tsx`

##### 5.2.4 SIMPLIFY: Run code-simplifier plugin on `frontend/src/app/documents/`

---

#### Task 5.3: Borrower Pages
**Can run in parallel with:** 5.2, 5.4, 5.5
**Depends on:** 5.1

##### 5.3.1 IMPLEMENT: Borrower List Page
- [ ] Create `frontend/src/app/borrowers/page.tsx`

##### 5.3.2 IMPLEMENT: Borrower Detail Page
- [ ] Create `frontend/src/app/borrowers/[id]/page.tsx`

##### 5.3.3 IMPLEMENT: Borrower Components
- [ ] Create `frontend/src/components/borrowers/borrower-card.tsx`
- [ ] Create `frontend/src/components/borrowers/income-timeline.tsx`
- [ ] Create `frontend/src/components/borrowers/source-references.tsx`
- [ ] Create `frontend/src/components/borrowers/search-bar.tsx`

##### 5.3.4 SIMPLIFY: Run code-simplifier plugin on `frontend/src/app/borrowers/`

---

#### Task 5.4: Architecture Documentation Pages
**Can run in parallel with:** 5.2, 5.3, 5.5
**Depends on:** 5.1

##### 5.4.1 IMPLEMENT: Architecture Overview Page
- [ ] Create `frontend/src/app/architecture/page.tsx`

##### 5.4.2 IMPLEMENT: Design Decisions Page
- [ ] Create `frontend/src/app/architecture/decisions/page.tsx`

##### 5.4.3 IMPLEMENT: Data Pipeline Page
- [ ] Create `frontend/src/app/architecture/pipeline/page.tsx`

##### 5.4.4 IMPLEMENT: Scaling Strategy Page
- [ ] Create `frontend/src/app/architecture/scaling/page.tsx`

##### 5.4.5 IMPLEMENT: Architecture Components
- [ ] Create `frontend/src/components/architecture/system-diagram.tsx`
- [ ] Create `frontend/src/components/architecture/pipeline-flow.tsx`
- [ ] Create `frontend/src/components/architecture/decision-card.tsx`
- [ ] Create `frontend/src/components/architecture/scaling-chart.tsx`

##### 5.4.6 SIMPLIFY: Run code-simplifier plugin on `frontend/src/app/architecture/`

---

#### Task 5.5: Dashboard Home Page
**Can run in parallel with:** 5.2, 5.3, 5.4
**Depends on:** 5.1

##### 5.5.1 IMPLEMENT: Dashboard Page
- [ ] Create `frontend/src/app/page.tsx`

##### 5.5.2 IMPLEMENT: Navigation
- [ ] Create `frontend/src/components/nav/sidebar.tsx`
- [ ] Create `frontend/src/components/nav/header.tsx`

##### 5.5.3 SIMPLIFY: Run code-simplifier plugin on `frontend/src/app/page.tsx`

---

#### Task 5.6: Phase 5 Verification
**Depends on:** 5.2, 5.3, 5.4, 5.5

##### 5.6.1 VERIFY: Frontend builds and runs
- [ ] Run `npm run build` — NO ERRORS
- [ ] Run `npm run dev` — App starts successfully
- [ ] Manually verify all pages render correctly

##### 5.6.2 IMPLEMENT: Frontend Smoke Tests
- [ ] Create `frontend/src/__tests__/smoke.test.tsx`

##### 5.6.3 VERIFY: Run frontend tests
- [ ] Run `npm test` — ALL PASS

### ✅ PHASE 5 SIGN-OFF
- [ ] All pages implemented
- [ ] Build succeeds
- [ ] UI is responsive and functional

---

## Phase 6: GCP Infrastructure

**⚡ PARALLELIZATION:** Tasks 6.2-6.7 can all run in parallel after 6.1 completes. Tasks 6.8 and 6.9 can run in parallel.

### Phase Overview
Create Terraform configuration for deploying to Google Cloud Platform.

### Dependencies
- Phase 0 complete

---

#### Task 6.1: Terraform Setup
**Must complete before:** 6.2-6.7

##### 6.1.1 IMPLEMENT: Terraform Configuration
- [ ] Create `infrastructure/terraform/main.tf`

##### 6.1.2 IMPLEMENT: Variables
- [ ] Create `infrastructure/terraform/variables.tf`

---

#### Task 6.2: Cloud SQL
**Can run in parallel with:** 6.3, 6.4, 6.5, 6.6, 6.7
**Depends on:** 6.1

##### 6.2.1 IMPLEMENT: Cloud SQL Configuration
- [ ] Create `infrastructure/terraform/cloud_sql.tf`

---

#### Task 6.3: Cloud Storage
**Can run in parallel with:** 6.2, 6.4, 6.5, 6.6, 6.7
**Depends on:** 6.1

##### 6.3.1 IMPLEMENT: GCS Configuration
- [ ] Create `infrastructure/terraform/cloud_storage.tf`

---

#### Task 6.4: Cloud Run
**Can run in parallel with:** 6.2, 6.3, 6.5, 6.6, 6.7
**Depends on:** 6.1

##### 6.4.1 IMPLEMENT: Cloud Run Backend
- [ ] Create `infrastructure/terraform/cloud_run.tf`

---

#### Task 6.5: Cloud Tasks
**Can run in parallel with:** 6.2, 6.3, 6.4, 6.6, 6.7
**Depends on:** 6.1

##### 6.5.1 IMPLEMENT: Cloud Tasks Configuration
- [ ] Create `infrastructure/terraform/cloud_tasks.tf`

---

#### Task 6.6: IAM & Security
**Can run in parallel with:** 6.2, 6.3, 6.4, 6.5, 6.7
**Depends on:** 6.1

##### 6.6.1 IMPLEMENT: IAM Configuration
- [ ] Create `infrastructure/terraform/iam.tf`

---

#### Task 6.7: Outputs
**Can run in parallel with:** 6.2, 6.3, 6.4, 6.5, 6.6
**Depends on:** 6.1

##### 6.7.1 IMPLEMENT: Terraform Outputs
- [ ] Create `infrastructure/terraform/outputs.tf`

---

#### Task 6.8: Deployment Scripts
**Can run in parallel with:** 6.9
**Depends on:** 6.1

##### 6.8.1 IMPLEMENT: Setup Script
- [ ] Create `infrastructure/scripts/setup-gcp.sh`

##### 6.8.2 IMPLEMENT: Deploy Script
- [ ] Create `infrastructure/scripts/deploy.sh`

---

#### Task 6.9: Dockerfiles
**Can run in parallel with:** 6.8
**Dependencies:** None

##### 6.9.1 IMPLEMENT: Backend Dockerfile
- [ ] Create `backend/Dockerfile`

##### 6.9.2 IMPLEMENT: Frontend Dockerfile
- [ ] Create `frontend/Dockerfile`

---

#### Task 6.10: Phase 6 Verification
**Depends on:** 6.2-6.9

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

**⚡ PARALLELIZATION:** Tasks 7.1, 7.2, 7.3 can all run in parallel. Task 7.4 depends on Phases 1-4. Task 7.5 depends on all tasks.

### Phase Overview
Complete all documentation and perform final integration testing.

### Dependencies
- All previous phases (1-6) complete

---

#### Task 7.1: System Design Document
**Can run in parallel with:** 7.2, 7.3
**Dependencies:** None (documentation)

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
  - LLM extraction with Gemini
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

  ## Cost Analysis
  ### Gemini 3.0 Flash Preview (Recommended Default)
  - Input: ~2000 tokens avg @ $0.075/1M tokens = $0.00015
  - Output: ~500 tokens avg @ $0.30/1M tokens = $0.00015
  - Total per document: ~$0.0003

  ### Scaling Projections
  - 1,000 docs/month: ~$0.30/month
  - 10,000 docs/month (10x): ~$3/month
  - 100,000 docs/month (100x): ~$30/month
  ```

---

#### Task 7.2: Architecture Decisions Document
**Can run in parallel with:** 7.1, 7.3
**Dependencies:** None (documentation)

##### 7.2.1 IMPLEMENT: ARCHITECTURE_DECISIONS.md
- [ ] Create `docs/ARCHITECTURE_DECISIONS.md`
  ```markdown
  # Architecture Decision Records

  ## ADR-001: Docling for Document Processing
  ## ADR-002: Gemini 3.0 Preview Models for Extraction
  ## ADR-003: PostgreSQL for Storage
  ## ADR-004: Cloud Run for Compute
  ## ADR-005: Next.js for Frontend
  ```

---

#### Task 7.3: README
**Can run in parallel with:** 7.1, 7.2
**Dependencies:** None (documentation)

##### 7.3.1 IMPLEMENT: README.md
- [ ] Create `README.md`

---

#### Task 7.4: Final Integration Test
**Depends on:** Phases 1-4
**Can run in parallel with:** 7.1, 7.2, 7.3

##### 7.4.1 IMPLEMENT: Full E2E Test
- [ ] Create and run comprehensive E2E test

##### 7.4.2 VERIFY: All tests pass
- [ ] Run `pytest backend/tests/ -v --cov=src` — ALL PASS, >80% coverage
- [ ] Run `mypy backend/src/ --strict` — NO ERRORS

##### 7.4.3 IMPLEMENT: Sample Loan Documents Integration Test
- [ ] Create `backend/tests/integration/test_sample_loan_docs.py`

##### 7.4.4 VERIFY: Sample document tests pass
- [ ] Run `pytest backend/tests/integration/test_sample_loan_docs.py -v` — ALL PASS

---

#### Task 7.5: Final Code Simplification
**Depends on:** All previous tasks

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
- [ ] LLM extraction logic (Gemini)
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

## Parallel Execution Summary

### Phase 0: 3 parallel tracks
- Track 1: Directory structure (0.1)
- Track 2: Backend config (0.2)
- Track 3: Frontend config (0.3)

### Phase 1: 3 parallel tracks
- Track 1: Docling processor (1.1)
- Track 2: Document service (1.2)
- Track 3: GCS client (1.3)

### Phase 2: 6 parallel tracks
- Track 1: Pydantic models (2.1)
- Track 2: LLM client (2.2)
- Track 3: Complexity classifier (2.3)
- Track 4: Prompts (2.4)
- Track 5: Extractor (2.5) - after 2.1, 2.2, 2.3
- Track 6: Validation (2.6) - after 2.1

### Phase 3: 2 parallel tracks
- Track 1: SQLAlchemy models (3.1)
- Track 2: Repositories (3.2)

### Phase 4: 2 parallel tracks (after 4.1)
- Track 1: Document endpoints (4.2)
- Track 2: Borrower endpoints (4.3)

### Phase 5: 4 parallel tracks (after 5.1)
- Track 1: Document pages (5.2)
- Track 2: Borrower pages (5.3)
- Track 3: Architecture pages (5.4)
- Track 4: Dashboard (5.5)

### Phase 6: 8 parallel tracks (after 6.1)
- Track 1: Cloud SQL (6.2)
- Track 2: Cloud Storage (6.3)
- Track 3: Cloud Run (6.4)
- Track 4: Cloud Tasks (6.5)
- Track 5: IAM (6.6)
- Track 6: Outputs (6.7)
- Track 7: Scripts (6.8)
- Track 8: Dockerfiles (6.9)

### Phase 7: 3 parallel tracks
- Track 1: System design doc (7.1)
- Track 2: Architecture decisions (7.2)
- Track 3: README (7.3)
- Track 4: Integration tests (7.4) - independent

---

*Document Version: 4.0 | Optimized for Parallel Subagent Execution with Docling + Gemini + GCP*
