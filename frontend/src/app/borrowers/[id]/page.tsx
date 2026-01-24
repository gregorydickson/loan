"use client";

import { use } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { BorrowerCard } from "@/components/borrowers/borrower-card";
import { IncomeTimeline } from "@/components/borrowers/income-timeline";
import { SourceReferences } from "@/components/borrowers/source-references";
import { useBorrower } from "@/hooks/use-borrowers";

interface BorrowerPageProps {
  params: Promise<{ id: string }>;
}

function getConfidenceBadgeVariant(
  score: number
): "default" | "secondary" | "destructive" {
  if (score >= 0.7) return "default";
  if (score >= 0.5) return "secondary";
  return "destructive";
}

interface ParsedAddress {
  street?: string;
  city?: string;
  state?: string;
  zip?: string;
}

function parseAddress(addressJson: string | null): ParsedAddress | null {
  if (!addressJson) return null;
  try {
    return JSON.parse(addressJson) as ParsedAddress;
  } catch {
    return null;
  }
}

function formatAddress(address: ParsedAddress | null): string {
  if (!address) return "No address on file";
  const parts = [
    address.street,
    address.city,
    address.state,
    address.zip,
  ].filter(Boolean);
  return parts.length > 0 ? parts.join(", ") : "No address on file";
}

export default function BorrowerDetailPage({ params }: BorrowerPageProps) {
  const { id } = use(params);
  const { data: borrower, isLoading, isError } = useBorrower(id);

  if (isLoading) {
    return (
      <div className="space-y-6">
        {/* Back button */}
        <Link href="/borrowers">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Borrowers
          </Button>
        </Link>

        {/* Loading skeleton */}
        <div className="space-y-4">
          <Skeleton className="h-10 w-64" />
          <Skeleton className="h-6 w-48" />
        </div>
        <div className="grid gap-6 lg:grid-cols-2">
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
        </div>
      </div>
    );
  }

  if (isError || !borrower) {
    return (
      <div className="space-y-6">
        {/* Back button */}
        <Link href="/borrowers">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Borrowers
          </Button>
        </Link>

        {/* Error message */}
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-muted-foreground">
              Failed to load borrower details. The borrower may not exist.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const confidenceScore = parseFloat(borrower.confidence_score);
  const address = parseAddress(borrower.address_json);

  return (
    <div className="space-y-6">
      {/* Back button */}
      <Link href="/borrowers">
        <Button variant="ghost" size="sm">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Borrowers
        </Button>
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{borrower.name}</h1>
          <p className="mt-1 text-muted-foreground">
            {formatAddress(address)}
          </p>
        </div>
        <Badge
          variant={getConfidenceBadgeVariant(confidenceScore)}
          className="text-sm"
        >
          {(confidenceScore * 100).toFixed(0)}% confidence
        </Badge>
      </div>

      {/* Borrower Card Summary */}
      <BorrowerCard borrower={borrower} disableLink />

      {/* Summary Card */}
      <Card>
        <CardHeader>
          <CardTitle>Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <dt className="text-sm font-medium text-muted-foreground">
                Income Records
              </dt>
              <dd className="mt-1 text-lg font-semibold">
                {borrower.income_records.length}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">
                Account Numbers
              </dt>
              <dd className="mt-1 text-lg font-semibold">
                {borrower.account_numbers.length}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">
                Source Documents
              </dt>
              <dd className="mt-1 text-lg font-semibold">
                {new Set(borrower.source_references.map((s) => s.document_id)).size}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">
                Confidence Score
              </dt>
              <dd className="mt-1 text-lg font-semibold">
                {(confidenceScore * 100).toFixed(0)}%
              </dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      {/* Account Numbers (if present) */}
      {borrower.account_numbers.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Account Numbers</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {borrower.account_numbers.map((account) => (
                <Badge key={account.id} variant="outline">
                  {account.account_type}: {account.number}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Two-column layout for timeline and sources */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Income Timeline */}
        <IncomeTimeline records={borrower.income_records} />

        {/* Source References */}
        <SourceReferences
          sources={borrower.source_references}
          borrowerName={borrower.name}
        />
      </div>
    </div>
  );
}
