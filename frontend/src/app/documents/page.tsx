"use client";

import { FileText } from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { UploadZone } from "@/components/documents/upload-zone";
import { DocumentTable } from "@/components/documents/document-table";
import { useDocuments } from "@/hooks/use-documents";

/**
 * Documents page with upload zone and document list.
 *
 * Displays drag-and-drop upload area and a table of all documents.
 * Upload triggers automatic list refresh via query invalidation.
 */
export default function DocumentsPage() {
  const { data, isLoading, error } = useDocuments();

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold">Documents</h1>

      {/* Upload Section */}
      <Card>
        <CardHeader>
          <CardTitle>Upload Document</CardTitle>
        </CardHeader>
        <CardContent>
          <UploadZone />
        </CardContent>
      </Card>

      {/* Document List Section */}
      <Card>
        <CardHeader>
          <CardTitle>Document List</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <LoadingSkeleton />
          ) : error ? (
            <ErrorState message={error.message} />
          ) : data?.documents.length === 0 ? (
            <EmptyState />
          ) : (
            <DocumentTable documents={data?.documents ?? []} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

/**
 * Loading skeleton for document list.
 */
function LoadingSkeleton() {
  return (
    <div className="space-y-3">
      <Skeleton className="h-10 w-full" />
      <Skeleton className="h-10 w-full" />
      <Skeleton className="h-10 w-full" />
    </div>
  );
}

/**
 * Empty state when no documents exist.
 */
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <FileText className="h-12 w-12 text-muted-foreground mb-4" />
      <h3 className="text-lg font-medium">No documents yet</h3>
      <p className="text-sm text-muted-foreground">
        Upload your first document using the upload zone above.
      </p>
    </div>
  );
}

/**
 * Error state when document fetch fails.
 */
function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <p className="text-destructive">Failed to load documents</p>
      <p className="text-sm text-muted-foreground">{message}</p>
    </div>
  );
}
