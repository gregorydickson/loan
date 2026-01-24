"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { GitBranch, Scale, FileCode } from "lucide-react";
import { cn } from "@/lib/utils";
import { MermaidDiagram } from "@/components/architecture/mermaid-diagram";

const subPages = [
  {
    name: "Pipeline",
    href: "/architecture/pipeline",
    icon: GitBranch,
    description: "Data processing flow",
  },
  {
    name: "Scaling",
    href: "/architecture/scaling",
    icon: Scale,
    description: "Scaling strategy",
  },
  {
    name: "Decisions",
    href: "/architecture/decisions",
    icon: FileCode,
    description: "Architecture decisions",
  },
];

const systemArchitectureChart = `
graph TB
    subgraph Frontend["Frontend (Next.js)"]
        UI[Dashboard UI]
        Upload[Document Upload]
        Browse[Borrower Browser]
    end

    subgraph Backend["Backend (FastAPI)"]
        API[REST API]
        Service[Document Service]
        Extraction[Extraction Engine]
    end

    subgraph Processing["Document Processing"]
        Docling[Docling Parser]
        Gemini[Gemini LLM]
        Validator[Data Validator]
    end

    subgraph Storage["Data Storage"]
        PostgreSQL[(PostgreSQL)]
        GCS[Cloud Storage]
    end

    UI --> API
    Upload --> API
    Browse --> API
    API --> Service
    Service --> Docling
    Service --> GCS
    Extraction --> Gemini
    Extraction --> Validator
    API --> PostgreSQL
`;

export default function ArchitecturePage() {
  const pathname = usePathname();

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          System Architecture
        </h1>
        <p className="mt-2 text-muted-foreground">
          Overview of the Loan Document Intelligence system architecture
        </p>
      </div>

      {/* Sub-page Navigation */}
      <div className="flex flex-wrap gap-4">
        {subPages.map((page) => {
          const isActive = pathname === page.href;
          return (
            <Link
              key={page.href}
              href={page.href}
              className={cn(
                "flex items-center gap-3 rounded-lg border px-4 py-3 transition-colors",
                isActive
                  ? "border-primary bg-primary/5"
                  : "border-border hover:border-primary/50 hover:bg-muted"
              )}
            >
              <page.icon className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="font-medium">{page.name}</p>
                <p className="text-xs text-muted-foreground">
                  {page.description}
                </p>
              </div>
            </Link>
          );
        })}
      </div>

      {/* System Architecture Diagram */}
      <div className="rounded-lg border bg-white p-6">
        <h2 className="mb-4 text-xl font-semibold">System Overview</h2>
        <p className="mb-6 text-sm text-muted-foreground">
          The system consists of a Next.js frontend, FastAPI backend, document
          processing pipeline with Docling and Gemini LLM, and PostgreSQL for
          data storage with Cloud Storage for document files.
        </p>
        <MermaidDiagram
          chart={systemArchitectureChart}
          className="flex justify-center"
        />
      </div>

      {/* Key Components */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg border p-4">
          <h3 className="font-semibold">Frontend</h3>
          <p className="text-sm text-muted-foreground">
            Next.js 16 with React 19, TanStack Query for data fetching, and
            shadcn/ui components
          </p>
        </div>
        <div className="rounded-lg border p-4">
          <h3 className="font-semibold">Backend</h3>
          <p className="text-sm text-muted-foreground">
            FastAPI with async support, SQLAlchemy ORM, and Pydantic validation
          </p>
        </div>
        <div className="rounded-lg border p-4">
          <h3 className="font-semibold">Processing</h3>
          <p className="text-sm text-muted-foreground">
            Docling for PDF/DOCX parsing, Gemini 3.0 for intelligent data
            extraction
          </p>
        </div>
        <div className="rounded-lg border p-4">
          <h3 className="font-semibold">Storage</h3>
          <p className="text-sm text-muted-foreground">
            PostgreSQL for relational data, Google Cloud Storage for document
            files
          </p>
        </div>
      </div>
    </div>
  );
}
