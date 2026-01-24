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
    participant Frontend
    participant API
    participant Docling
    participant GCS
    participant Gemini
    participant PostgreSQL

    User->>Frontend: Upload Document
    Frontend->>API: POST /api/documents
    API->>GCS: Store Original File
    API->>Docling: Process Document
    Docling->>API: Extracted Text + Pages
    API->>PostgreSQL: Save Document Record
    API->>Frontend: Document ID + Status

    Note over API,Gemini: Extraction Phase
    API->>Gemini: Send Document Text
    Gemini->>API: Structured Borrower Data
    API->>PostgreSQL: Save Borrowers + Sources
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
            <CardTitle>2. Text Extraction</CardTitle>
            <CardDescription>
              Docling document parsing
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            <ul className="list-inside list-disc space-y-2">
              <li>Docling processes document with layout analysis</li>
              <li>Text extracted page by page with position data</li>
              <li>Tables, forms, and images handled automatically</li>
              <li>Page content stored for source attribution</li>
              <li>Status updated to PROCESSING</li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>3. LLM Extraction</CardTitle>
            <CardDescription>
              Gemini structured data extraction
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            <ul className="list-inside list-disc space-y-2">
              <li>Document complexity analyzed (page count, content type)</li>
              <li>Flash model selected for standard docs, Pro for complex</li>
              <li>Structured prompts request borrower + income data</li>
              <li>JSON schema enforces output structure</li>
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

      {/* Source Attribution */}
      <div className="rounded-lg border bg-muted/50 p-6">
        <h2 className="text-lg font-semibold">Source Attribution</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Every extracted data field includes source attribution showing the
          exact document, page, and text snippet where the data was found. This
          enables full traceability and human verification of extracted data.
        </p>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
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
