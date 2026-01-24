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
import type { BorrowerSummary } from "@/lib/api/types";

function getConfidenceBadgeVariant(
  score: number
): "default" | "secondary" | "destructive" {
  if (score >= 0.7) return "default";
  if (score >= 0.5) return "secondary";
  return "destructive";
}

interface BorrowerCardProps {
  borrower: BorrowerSummary;
}

export function BorrowerCard({ borrower }: BorrowerCardProps) {
  const confidenceScore = parseFloat(borrower.confidence_score);

  return (
    <Link href={`/borrowers/${borrower.id}`}>
      <Card className="hover:shadow-md transition-shadow cursor-pointer">
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
            <span>{borrower.income_count} income records</span>
            <span>{format(new Date(borrower.created_at), "MMM d, yyyy")}</span>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
