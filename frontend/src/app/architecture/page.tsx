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
flowchart LR
    subgraph Upload["📤 Upload"]
        A[Document Upload]
    end

    subgraph OCR["🖼️ OCR Layer"]
        B{Scanned?}
        C[LightOnOCR GPU]
        D[Docling OCR]
    end

    subgraph Extract["🤖 Extraction"]
        E{Method}
        F[Docling + Gemini]
        G[LangExtract + Gemini]
    end

    subgraph Store["💾 Storage"]
        H[Validation]
        I[(PostgreSQL)]
    end

    subgraph Serve["🌐 API"]
        J[FastAPI REST]
        K[Next.js Dashboard]
    end

    A --> B
    B -->|Yes| C
    B -->|No| E
    C --> E
    D -.->|Fallback| E
    E -->|docling| F
    E -->|langextract| G
    F --> H
    G --> H
    H --> I
    I --> J
    J --> K
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
          The system features a dual extraction pipeline with intelligent OCR
          routing. Documents flow through upload, OCR detection (LightOnOCR GPU
          with Docling fallback), extraction (Docling or LangExtract with
          Gemini), validation, and storage in PostgreSQL. The Next.js dashboard
          communicates via FastAPI REST endpoints.
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
            Next.js 14 with App Router, TanStack Query for data fetching, and
            shadcn/ui components
          </p>
        </div>
        <div className="rounded-lg border p-4">
          <h3 className="font-semibold">Backend</h3>
          <p className="text-sm text-muted-foreground">
            FastAPI with async support, SQLAlchemy ORM, and Pydantic validation.
            Dual extraction pipelines with auto-selection
          </p>
        </div>
        <div className="rounded-lg border p-4">
          <h3 className="font-semibold">OCR &amp; Processing</h3>
          <p className="text-sm text-muted-foreground">
            LightOnOCR GPU service with Docling fallback. Docling or LangExtract
            extraction with Gemini 3.0 Flash/Pro
          </p>
        </div>
        <div className="rounded-lg border p-4">
          <h3 className="font-semibold">Storage</h3>
          <p className="text-sm text-muted-foreground">
            PostgreSQL 16 for relational data with character-level source
            attribution. Cloud Storage for documents
          </p>
        </div>
      </div>
    </div>
  );
}
