"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { FileText, Users, Clock } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { listDocuments } from "@/lib/api/documents";
import { listBorrowers } from "@/lib/api/borrowers";

export default function Home() {
  const { data: documentsData, isLoading: documentsLoading } = useQuery({
    queryKey: ["documents", { limit: 100, offset: 0 }],
    queryFn: () => listDocuments(100, 0),
  });

  const { data: borrowersData, isLoading: borrowersLoading } = useQuery({
    queryKey: ["borrowers", { limit: 100, offset: 0 }],
    queryFn: () => listBorrowers(100, 0),
  });

  const totalDocuments = documentsData?.total ?? 0;
  const totalBorrowers = borrowersData?.total ?? 0;
  const recentUploads =
    documentsData?.documents.filter(
      (doc) => doc.status === "pending" || doc.status === "processing"
    ).length ?? 0;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          Loan Document Intelligence Dashboard
        </h1>
        <p className="mt-2 text-muted-foreground">
          Extract and organize borrower data from loan documents with complete
          source traceability
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        {/* Total Documents */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Total Documents
            </CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {documentsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold">{totalDocuments}</div>
            )}
            <p className="text-xs text-muted-foreground">
              Uploaded for processing
            </p>
          </CardContent>
        </Card>

        {/* Total Borrowers */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Total Borrowers
            </CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {borrowersLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold">{totalBorrowers}</div>
            )}
            <p className="text-xs text-muted-foreground">
              Extracted from documents
            </p>
          </CardContent>
        </Card>

        {/* Recent Uploads */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Recent Uploads
            </CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {documentsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold">{recentUploads}</div>
            )}
            <p className="text-xs text-muted-foreground">
              Pending or processing
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Documents</CardTitle>
            <CardDescription>
              Upload and manage loan documents for extraction
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link
              href="/documents"
              className="inline-flex h-9 items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90"
            >
              View Documents
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Borrowers</CardTitle>
            <CardDescription>
              View extracted borrower data with source attribution
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link
              href="/borrowers"
              className="inline-flex h-9 items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90"
            >
              View Borrowers
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
