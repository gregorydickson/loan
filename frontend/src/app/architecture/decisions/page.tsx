import { DecisionCard } from "@/components/architecture/decision-card";

const decisions = [
  {
    title: "ADR-001: Docling for Document Processing",
    decision:
      "Use Docling as the primary document parsing library for PDF, DOCX, and image files.",
    rationale:
      "Production-grade document understanding with support for tables, forms, and complex layouts. Better accuracy than PyPDF2 or pdfplumber for structured extraction. MIT licensed with active maintenance.",
    status: "adopted" as const,
  },
  {
    title: "ADR-002: Gemini 3.0 with Dynamic Model Selection",
    decision:
      "Use Google Gemini 3.0 with Flash for standard documents and Pro for complex ones.",
    rationale:
      "Flash provides fast, cost-effective extraction for most documents. Pro handles complex cases with multiple borrowers or unusual formats. Dynamic selection balances cost and accuracy based on document complexity.",
    status: "adopted" as const,
  },
  {
    title: "ADR-003: PostgreSQL over NoSQL",
    decision:
      "Use PostgreSQL for all data storage including borrowers, income records, and source references.",
    rationale:
      "Strong relational integrity for borrower-income-source relationships. ACID compliance for financial data. JSON columns available when schema flexibility needed. Excellent async support via asyncpg.",
    status: "adopted" as const,
  },
  {
    title: "ADR-004: FastAPI over Flask/Django",
    decision:
      "Use FastAPI as the backend framework with Pydantic for validation.",
    rationale:
      "Native async support for concurrent document processing. Automatic OpenAPI documentation. Pydantic v2 for type-safe request/response handling. Better performance than Flask for I/O-bound workloads.",
    status: "adopted" as const,
  },
  {
    title: "ADR-005: Next.js 14+ App Router",
    decision:
      "Use Next.js with App Router for the frontend dashboard.",
    rationale:
      "React Server Components for optimal initial load. Built-in routing with layouts. Excellent TypeScript support. Large ecosystem and community. Vercel deployment path if needed.",
    status: "adopted" as const,
  },
  {
    title: "ADR-006: Cloud Run over GKE",
    decision:
      "Deploy to Google Cloud Run for serverless container hosting.",
    rationale:
      "Scale to zero reduces costs for variable workloads. No cluster management overhead. Automatic scaling during batch processing. Per-request billing model fits document processing use case.",
    status: "adopted" as const,
  },
  {
    title: "ADR-007: Test-First TDD Approach",
    decision:
      "Follow test-driven development with tests written before implementation.",
    rationale:
      "Ensures high code coverage from the start. Catches edge cases early in development. Makes refactoring safer. Documents expected behavior through tests. Faster long-term development velocity.",
    status: "adopted" as const,
  },
];

export default function DecisionsPage() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          Architecture Decisions
        </h1>
        <p className="mt-2 text-muted-foreground">
          Architecture Decision Records (ADRs) documenting key technical
          choices and their rationale
        </p>
      </div>

      {/* Decision Cards */}
      <div className="grid gap-4 md:grid-cols-2">
        {decisions.map((decision) => (
          <DecisionCard
            key={decision.title}
            title={decision.title}
            decision={decision.decision}
            rationale={decision.rationale}
            status={decision.status}
          />
        ))}
      </div>

      {/* Summary */}
      <div className="rounded-lg border bg-muted/50 p-6">
        <h2 className="text-lg font-semibold">Decision Summary</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          These decisions prioritize developer productivity, cost efficiency,
          and accuracy for the document intelligence use case. The stack
          leverages modern async Python (FastAPI) for the backend, React with
          Next.js for the frontend, and Google Cloud services for scalable
          infrastructure.
        </p>
      </div>
    </div>
  );
}
