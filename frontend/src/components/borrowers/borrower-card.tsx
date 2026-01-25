"use client";

import Link from "next/link";
import { format } from "date-fns";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { BorrowerSummary, BorrowerDetailResponse } from "@/lib/api/types";
import { getConfidenceBadgeVariant } from "@/lib/formatting";

interface BorrowerCardProps {
  borrower: BorrowerSummary | BorrowerDetailResponse;
  disableLink?: boolean;
}

export function BorrowerCard({ borrower, disableLink = false }: BorrowerCardProps) {
  const confidenceScore = parseFloat(borrower.confidence_score);

  // Compute income count: BorrowerSummary has income_count, BorrowerDetailResponse has income_records array
  const incomeCount = "income_count" in borrower
    ? borrower.income_count
    : borrower.income_records?.length ?? 0;

  const cardContent = (
    <Card className={disableLink ? "" : "hover:shadow-md transition-shadow cursor-pointer"}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <CardTitle className="text-lg">{borrower.name}</CardTitle>
          <Badge variant={getConfidenceBadgeVariant(confidenceScore)}>
            {(confidenceScore * 100).toFixed(0)}%
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>{incomeCount} income records</span>
          <span>{format(new Date(borrower.created_at), "MMM d, yyyy")}</span>
        </div>
      </CardContent>
    </Card>
  );

  if (disableLink) {
    return cardContent;
  }

  return (
    <Link href={`/borrowers/${borrower.id}`}>
      {cardContent}
    </Link>
  );
}
