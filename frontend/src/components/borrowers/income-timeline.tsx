"use client";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { IncomeRecord } from "@/lib/api/types";

interface IncomeTimelineProps {
  records: IncomeRecord[];
}

function formatCurrency(amount: string): string {
  const num = parseFloat(amount);
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(num);
}

function formatPeriod(period: string): string {
  const lowerPeriod = period.toLowerCase();
  if (lowerPeriod === "monthly") return "/month";
  if (lowerPeriod === "annual" || lowerPeriod === "yearly") return "/year";
  if (lowerPeriod === "weekly") return "/week";
  if (lowerPeriod === "biweekly") return "/2 weeks";
  return `/${period}`;
}

export function IncomeTimeline({ records }: IncomeTimelineProps) {
  // Sort by year descending (newest first)
  const sortedRecords = [...records].sort((a, b) => b.year - a.year);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Income History</CardTitle>
      </CardHeader>
      <CardContent>
        {sortedRecords.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No income records found.
          </p>
        ) : (
          <div className="relative border-l-2 border-muted pl-6 space-y-6">
            {sortedRecords.map((record) => (
              <div key={record.id} className="relative">
                {/* Timeline dot */}
                <div className="absolute -left-[31px] h-4 w-4 rounded-full border-2 border-background bg-primary" />

                {/* Content */}
                <div className="space-y-1">
                  <div className="flex items-baseline justify-between">
                    <span className="font-bold text-lg">{record.year}</span>
                    <span className="font-bold text-lg">
                      {formatCurrency(record.amount)}
                      <span className="text-sm font-normal text-muted-foreground">
                        {formatPeriod(record.period)}
                      </span>
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {record.source_type}
                    {record.employer && ` - ${record.employer}`}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
