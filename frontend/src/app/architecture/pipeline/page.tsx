"use client";

import { MermaidDiagram } from "@/components/architecture/mermaid-diagram";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const pipelineSequenceChart = `
sequenceDiagram
    participant User
    participant Frontend as Next.js Frontend
    participant API as FastAPI Backend
    participant GCS as Cloud Storage
    participant OCR as OCR Router
    participant GPU as LightOnOCR GPU
    participant Docling as Docling Processor
    participant LLM as Gemini LLM
    participant DB as PostgreSQL

    User->>Frontend: Upload document
    Frontend->>API: POST /api/documents (multipart)

    API->>API: Compute SHA-256 hash
    API->>DB: Check for duplicate hash

    alt Document exists
        DB-->>API: Existing document found
        API-->>Frontend: 409 Conflict
    else New document
        API->>GCS: Store original file
        GCS-->>API: Storage URI
        API->>DB: Create document record (status: pending)

        API->>OCR: Detect if scanned
        alt Scanned document
            OCR->>GPU: Request OCR
            GPU-->>OCR: OCR text (or error)
            alt GPU success
                OCR-->>API: OCR text
            else GPU failure
                OCR->>Docling: Fallback OCR
                Docling-->>API: OCR text
            end
        else Native text
            API->>Docling: Extract text directly
            Docling-->>API: Document text
        end

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

        API->>DB: Store borrowers with sources
        API->>DB: Update status: completed

        API-->>Frontend: Document response
    end

    Frontend-->>User: Show status/results
`;

export default function PipelinePage() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Data Pipeline</h1>
        <p className="mt-2 text-muted-foreground">
          Document processing flow from upload to borrower data extraction
        </p>
      </div>

      {/* Pipeline Diagram */}
      <div className="rounded-lg border bg-white p-6">
        <h2 className="mb-4 text-xl font-semibold">Processing Flow</h2>
        <MermaidDiagram
          chart={pipelineSequenceChart}
          className="flex justify-center overflow-x-auto"
        />
      </div>

      {/* Pipeline Stages */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>1. Document Ingestion</CardTitle>
            <CardDescription>
              Upload and initial processing
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            <ul className="list-inside list-disc space-y-2">
              <li>User uploads PDF, DOCX, or image file via drag-and-drop</li>
              <li>File validated for type and size limits</li>
              <li>SHA-256 hash computed for duplicate detection</li>
              <li>Original file stored in Google Cloud Storage</li>
              <li>Document record created with PENDING status</li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>2. OCR Detection &amp; Routing</CardTitle>
            <CardDescription>
              Intelligent OCR layer selection
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            <ul className="list-inside list-disc space-y-2">
              <li>Scanned document detection using image analysis</li>
              <li>LightOnOCR GPU service for high-quality OCR (scale-to-zero)</li>
              <li>Circuit breaker with Docling OCR fallback on failures</li>
              <li>Native text extraction for non-scanned documents</li>
              <li>Status updated to PROCESSING</li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>3. Dual Extraction Pipeline</CardTitle>
            <CardDescription>
              Docling or LangExtract with Gemini
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            <ul className="list-inside list-disc space-y-2">
              <li>Method selection: docling (default), langextract, or auto</li>
              <li>Docling: Fast page-level attribution, lower cost</li>
              <li>LangExtract: Character-level offsets for audit trails</li>
              <li>Dynamic model selection: Flash (standard) or Pro (complex)</li>
              <li>Retry logic handles rate limits and transient failures</li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>4. Validation and Storage</CardTitle>
            <CardDescription>
              Data validation and persistence
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            <ul className="list-inside list-disc space-y-2">
              <li>Extracted data validated (SSN format, date ranges)</li>
              <li>Confidence scores assigned to each field</li>
              <li>Deduplication checks for existing borrowers</li>
              <li>Source references link fields to document pages</li>
              <li>Status updated to COMPLETED</li>
            </ul>
          </CardContent>
        </Card>
      </div>

      {/* Data Flow */}
      <div className="rounded-lg border bg-white p-6">
        <h2 className="mb-4 text-xl font-semibold">Data Flow & Classes</h2>
        <p className="mb-4 text-sm text-muted-foreground">
          Technical flow through the backend services and repositories showing
          class names and method calls
        </p>
        <pre className="overflow-x-auto rounded-lg bg-muted p-4 text-xs">
          <code>{`1. POST /api/documents (file upload)
   │
2. DocumentService.upload()
   ├── validate_file() → compute_file_hash() → check duplicate
   ├── GCSClient.upload() → gs://bucket/documents/{id}/{filename}
   └── DocumentRepository.create() → status: PENDING
   │
3. OCRRouter.process() [if scanned]
   ├── ScannedDetector.is_scanned() → analyze document
   ├── LightOnOCRClient.extract_text() → GPU OCR (scale-to-zero)
   │   └── Circuit breaker: 3 failures → fallback
   └── DoclingProcessor.extract_with_ocr() → fallback OCR
   │
4. ExtractionRouter.extract()
   ├── method="docling" → DoclingProcessor
   │   └── Page-level attribution (page_number)
   ├── method="langextract" → LangExtractProcessor
   │   └── Character-level offsets (char_start, char_end)
   └── method="auto" → ComplexityClassifier → select best
   │
5. BorrowerExtractor.extract()
   ├── ComplexityClassifier.assess() → STANDARD/COMPLEX
   ├── ModelSelector → Flash (standard) / Pro (complex)
   ├── DocumentChunker.chunk() → 16K chars, 800 overlap
   ├── Loop: for each chunk
   │   ├── GeminiClient.extract_borrowers()
   │   │   ├── Structured output (response_json_schema)
   │   │   ├── Temperature: 1.0
   │   │   └── Retry: exponential backoff, 3 attempts
   │   └── FieldValidator.validate() → SSN, phone, ZIP
   ├── BorrowerDeduplicator.deduplicate()
   │   ├── Priority: SSN → Account → Fuzzy name (90%+)
   │   └── rapidfuzz for name matching
   ├── ConsistencyChecker.check()
   │   ├── Income anomaly: 50% drop / 300% spike
   │   └── Address conflicts
   └── ConfidenceScorer.calculate() → 0.0-1.0 score
   │
6. BorrowerRepository.create()
   ├── Borrower record
   ├── IncomeRecord[] → multiple years/sources
   └── SourceReference[] → document_id, page, snippet, char_start/end
   │
7. DocumentRepository.update() → status: COMPLETED`}</code>
        </pre>
      </div>

      {/* Key Classes */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Service Layer</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            <ul className="list-inside list-disc space-y-1">
              <li>
                <code className="text-xs">DocumentService</code> - Upload
                orchestration
              </li>
              <li>
                <code className="text-xs">ExtractionRouter</code> - Pipeline
                selection
              </li>
              <li>
                <code className="text-xs">OCRRouter</code> - OCR method routing
              </li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Processing Layer</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            <ul className="list-inside list-disc space-y-1">
              <li>
                <code className="text-xs">DoclingProcessor</code> - Document
                parsing
              </li>
              <li>
                <code className="text-xs">LangExtractProcessor</code> -
                Character-level extraction
              </li>
              <li>
                <code className="text-xs">BorrowerExtractor</code> - LLM
                orchestration
              </li>
              <li>
                <code className="text-xs">GeminiClient</code> - API client
              </li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Data Layer</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            <ul className="list-inside list-disc space-y-1">
              <li>
                <code className="text-xs">DocumentRepository</code> - Document
                CRUD
              </li>
              <li>
                <code className="text-xs">BorrowerRepository</code> - Borrower
                CRUD
              </li>
              <li>
                <code className="text-xs">GCSClient</code> - Cloud Storage
              </li>
            </ul>
          </CardContent>
        </Card>
      </div>

      {/* Source Attribution */}
      <div className="rounded-lg border bg-muted/50 p-6">
        <h2 className="text-lg font-semibold">Source Attribution</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Every extracted data field includes source attribution showing the
          exact document, page, and text snippet where the data was found. This
          enables full traceability and human verification of extracted data.
          LangExtract provides character-level offsets (char_start/char_end) for
          precise text highlighting.
        </p>
        <div className="mt-4 grid gap-4 md:grid-cols-4">
          <div className="rounded border bg-background p-3">
            <p className="text-xs font-medium">Document Reference</p>
            <p className="text-sm text-muted-foreground">
              Links to source document file
            </p>
          </div>
          <div className="rounded border bg-background p-3">
            <p className="text-xs font-medium">Page Number</p>
            <p className="text-sm text-muted-foreground">
              Exact page where data found
            </p>
          </div>
          <div className="rounded border bg-background p-3">
            <p className="text-xs font-medium">Character Offsets</p>
            <p className="text-sm text-muted-foreground">
              Precise char_start/char_end (LangExtract)
            </p>
          </div>
          <div className="rounded border bg-background p-3">
            <p className="text-xs font-medium">Text Snippet</p>
            <p className="text-sm text-muted-foreground">
              Surrounding context text
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
