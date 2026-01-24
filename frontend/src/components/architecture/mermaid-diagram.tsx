"use client";

import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";
import { cn } from "@/lib/utils";

interface MermaidDiagramProps {
  chart: string;
  className?: string;
}

export function MermaidDiagram({ chart, className }: MermaidDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [isRendered, setIsRendered] = useState(false);

  useEffect(() => {
    // Initialize mermaid with neutral theme
    mermaid.initialize({
      startOnLoad: false,
      theme: "neutral",
      securityLevel: "loose",
    });
  }, []);

  useEffect(() => {
    const renderDiagram = async () => {
      if (!containerRef.current) return;

      setError(null);
      setIsRendered(false);

      try {
        // Clear previous content
        containerRef.current.innerHTML = chart;

        // Run mermaid rendering
        await mermaid.run({
          nodes: [containerRef.current],
        });

        setIsRendered(true);
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to render diagram";
        setError(errorMessage);
        console.error("Mermaid rendering error:", err);
      }
    };

    renderDiagram();
  }, [chart]);

  if (error) {
    return (
      <div
        className={cn(
          "rounded-lg border border-destructive/50 bg-destructive/10 p-4",
          className
        )}
      >
        <p className="text-sm font-medium text-destructive">
          Error rendering diagram
        </p>
        <p className="mt-1 text-xs text-muted-foreground">{error}</p>
        <pre className="mt-2 overflow-auto text-xs">{chart}</pre>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={cn(
        "mermaid overflow-auto",
        !isRendered && "opacity-0",
        className
      )}
    >
      {chart}
    </div>
  );
}
