"use client";

import { MermaidDiagram } from "@/components/architecture/mermaid-diagram";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const scaledArchitectureChart = `
graph LR
    subgraph "Load Balanced"
        LB[Cloud Load Balancer]
        CR1[Cloud Run 1]
        CR2[Cloud Run 2]
        CR3[Cloud Run N]
    end

    subgraph "Async Processing"
        CT[Cloud Tasks]
        Worker1[Worker 1]
        Worker2[Worker N]
    end

    subgraph "Shared Services"
        Redis[(Redis Cache)]
        CloudSQL[(Cloud SQL)]
        GCS[Cloud Storage]
    end

    LB --> CR1
    LB --> CR2
    LB --> CR3
    CR1 --> CT
    CT --> Worker1
    CT --> Worker2
    Worker1 --> CloudSQL
    Worker2 --> CloudSQL
    Worker1 --> GCS
    Redis -.-> CR1
    Redis -.-> CR2
`;

const scalingTiers = [
  {
    name: "Current",
    badge: "Production Ready",
    variant: "default" as const,
    capacity: "~10 concurrent uploads",
    throughput: "~50 documents/hour",
    description:
      "Single Cloud Run instance with synchronous processing. Suitable for initial deployment and testing.",
    architecture: [
      "Single Cloud Run container (2 vCPU, 4GB RAM)",
      "Synchronous document processing",
      "PostgreSQL Cloud SQL (db-f1-micro)",
      "Cloud Storage standard bucket",
    ],
    costEstimate: "$50-100/month",
  },
  {
    name: "10x Scale",
    badge: "Medium Volume",
    variant: "secondary" as const,
    capacity: "~100 concurrent uploads",
    throughput: "~500 documents/hour",
    description:
      "Multiple Cloud Run instances with async processing via Cloud Tasks. Handles medium-volume production workloads.",
    architecture: [
      "Auto-scaling Cloud Run (2-10 instances)",
      "Cloud Tasks for async processing",
      "Dedicated worker containers for extraction",
      "PostgreSQL Cloud SQL (db-g1-small)",
      "Redis Memorystore for caching",
    ],
    costEstimate: "$200-500/month",
  },
  {
    name: "100x Scale",
    badge: "High Volume",
    variant: "outline" as const,
    capacity: "~1000 concurrent uploads",
    throughput: "~5000 documents/hour",
    description:
      "Fully distributed architecture with dedicated workers, caching, and batch processing optimization.",
    architecture: [
      "Load-balanced Cloud Run fleet (10-50 instances)",
      "Dedicated extraction worker pool",
      "Pub/Sub for event-driven processing",
      "PostgreSQL Cloud SQL (db-n1-standard-4)",
      "Redis cluster for distributed caching",
      "Batch processing for bulk uploads",
    ],
    costEstimate: "$1000-3000/month",
  },
];

export default function ScalingPage() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Scaling Analysis</h1>
        <p className="mt-2 text-muted-foreground">
          Scaling strategy from initial deployment to high-volume production
        </p>
      </div>

      {/* Scaling Tiers */}
      <div className="grid gap-6">
        {scalingTiers.map((tier) => (
          <Card key={tier.name}>
            <CardHeader>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <CardTitle className="flex items-center gap-3">
                    {tier.name}
                    <Badge variant={tier.variant}>{tier.badge}</Badge>
                  </CardTitle>
                  <CardDescription className="mt-2">
                    {tier.description}
                  </CardDescription>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold">{tier.throughput}</p>
                  <p className="text-sm text-muted-foreground">throughput</p>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid gap-6 md:grid-cols-2">
                <div>
                  <h4 className="mb-2 font-medium">Architecture</h4>
                  <ul className="list-inside list-disc space-y-1 text-sm text-muted-foreground">
                    {tier.architecture.map((item, index) => (
                      <li key={index}>{item}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h4 className="mb-2 font-medium">Metrics</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Capacity</span>
                      <span className="font-medium">{tier.capacity}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Cost</span>
                      <span className="font-medium">{tier.costEstimate}</span>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Scaled Architecture Diagram */}
      <div className="rounded-lg border bg-white p-6">
        <h2 className="mb-4 text-xl font-semibold">
          Scaled Architecture (100x)
        </h2>
        <p className="mb-6 text-sm text-muted-foreground">
          High-volume architecture with load balancing, async processing, and
          shared services for maximum throughput.
        </p>
        <MermaidDiagram
          chart={scaledArchitectureChart}
          className="flex justify-center overflow-x-auto"
        />
      </div>

      {/* Cost Projections Table */}
      <div className="rounded-lg border">
        <div className="border-b p-4">
          <h2 className="text-lg font-semibold">Cost Projections</h2>
          <p className="text-sm text-muted-foreground">
            Estimated monthly costs by component (GCP pricing, us-central1)
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/50">
              <tr>
                <th className="px-4 py-3 text-left font-medium">Component</th>
                <th className="px-4 py-3 text-right font-medium">Current</th>
                <th className="px-4 py-3 text-right font-medium">10x Scale</th>
                <th className="px-4 py-3 text-right font-medium">100x Scale</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              <tr>
                <td className="px-4 py-3">Cloud Run</td>
                <td className="px-4 py-3 text-right">$20-40</td>
                <td className="px-4 py-3 text-right">$80-150</td>
                <td className="px-4 py-3 text-right">$400-800</td>
              </tr>
              <tr>
                <td className="px-4 py-3">Cloud SQL (PostgreSQL)</td>
                <td className="px-4 py-3 text-right">$10-20</td>
                <td className="px-4 py-3 text-right">$50-100</td>
                <td className="px-4 py-3 text-right">$200-400</td>
              </tr>
              <tr>
                <td className="px-4 py-3">Cloud Storage</td>
                <td className="px-4 py-3 text-right">$5-10</td>
                <td className="px-4 py-3 text-right">$20-50</td>
                <td className="px-4 py-3 text-right">$100-300</td>
              </tr>
              <tr>
                <td className="px-4 py-3">Gemini API</td>
                <td className="px-4 py-3 text-right">$10-20</td>
                <td className="px-4 py-3 text-right">$50-150</td>
                <td className="px-4 py-3 text-right">$300-1000</td>
              </tr>
              <tr>
                <td className="px-4 py-3">Redis (Memorystore)</td>
                <td className="px-4 py-3 text-right">-</td>
                <td className="px-4 py-3 text-right">$30-50</td>
                <td className="px-4 py-3 text-right">$100-200</td>
              </tr>
              <tr className="bg-muted/50 font-medium">
                <td className="px-4 py-3">Total</td>
                <td className="px-4 py-3 text-right">$50-100</td>
                <td className="px-4 py-3 text-right">$200-500</td>
                <td className="px-4 py-3 text-right">$1000-3000</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Scaling Recommendations */}
      <div className="rounded-lg border bg-muted/50 p-6">
        <h2 className="text-lg font-semibold">Scaling Recommendations</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          <div>
            <h3 className="font-medium">Start Simple</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Begin with Current tier. Synchronous processing is simpler to
              debug and sufficient for initial volumes.
            </p>
          </div>
          <div>
            <h3 className="font-medium">Monitor Latency</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Move to 10x when average processing time exceeds 30s or queue
              depth grows consistently.
            </p>
          </div>
          <div>
            <h3 className="font-medium">Scale Gradually</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Add async processing before horizontal scaling. Redis caching
              reduces Gemini API costs.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
