"use client";

import { use } from "react";
import Link from "next/link";
import { ArrowLeft, FileText, AlertCircle, Loader2 } from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/documents/status-badge";
import { useDocument, useDocumentStatus } from "@/hooks/use-documents";

interface DocumentDetailPageProps {
  params: Promise<{ id: string }>;
}

/**
 * Format bytes to human-readable string (B, KB, MB).
 */
function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Document detail page showing full metadata.
 *
 * Displays document information including filename, status, file type,
 * size, page count, and any error messages.
 */
export default function DocumentDetailPage({
  params,
}: DocumentDetailPageProps) {
  const { id } = use(params);
  const { data: document, isLoading, error } = useDocument(id);

  // Poll status for documents that are still processing
  const { data: statusData } = useDocumentStatus(
    document?.status === "pending" || document?.status === "processing"
      ? id
      : null
  );

  // Use polled status if available, otherwise fall back to document status
  const currentStatus = statusData?.status ?? document?.status;

  if (isLoading) {
    return <LoadingSkeleton />;
  }

  if (error) {
    return <ErrorState message={error.message} />;
  }

  if (!document) {
    return <ErrorState message="Document not found" />;
  }

  return (
    <div className="p-6 space-y-6">
      {/* Back navigation */}
      <div className="flex items-center gap-2">
        <Link
          href="/documents"
          className="flex items-center gap-1 text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Documents
        </Link>
      </div>

      {/* Header with filename and status */}
      <div className="flex items-center gap-4 flex-wrap">
        <h1 className="text-3xl font-bold">{document.filename}</h1>
        <StatusBadge status={currentStatus ?? document.status} />
        {(currentStatus === "pending" || currentStatus === "processing") && (
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        )}
      </div>

      {/* Document Details Card */}
      <Card>
        <CardHeader>
          <CardTitle>Document Details</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <DetailItem label="File Type" value={document.file_type} />
            <DetailItem
              label="File Size"
              value={formatBytes(document.file_size_bytes)}
            />
            <DetailItem
              label="Page Count"
              value={
                statusData?.page_count ?? document.page_count ?? "Unknown"
              }
            />
            <DetailItem label="Document ID" value={document.id} mono />
            {document.file_hash && (
              <DetailItem
                label="File Hash"
                value={`${document.file_hash.slice(0, 16)}...`}
                mono
              />
            )}
            {document.gcs_uri && (
              <div className="col-span-full">
                <DetailItem label="GCS URI" value={document.gcs_uri} mono />
              </div>
            )}
          </dl>
        </CardContent>
      </Card>

      {/* Error Card (shown only if failed) */}
      {(statusData?.error_message || document.error_message) && (
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              Processing Error
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {statusData?.error_message || document.error_message}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

/**
 * Detail item component for consistent formatting.
 */
function DetailItem({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string | number;
  mono?: boolean;
}) {
  return (
    <div>
      <dt className="text-sm font-medium text-muted-foreground">{label}</dt>
      <dd className={mono ? "font-mono text-sm" : undefined}>{value}</dd>
    </div>
  );
}

/**
 * Loading skeleton for document detail page.
 */
function LoadingSkeleton() {
  return (
    <div className="p-6 space-y-6">
      <Skeleton className="h-4 w-32" />
      <Skeleton className="h-10 w-64" />
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-40" />
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

/**
 * Error state component.
 */
function ErrorState({ message }: { message: string }) {
  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-2">
        <Link
          href="/documents"
          className="flex items-center gap-1 text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Documents
        </Link>
      </div>
      <Card className="border-destructive">
        <CardContent className="pt-6">
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <FileText className="h-12 w-12 text-destructive mb-4" />
            <h3 className="text-lg font-medium text-destructive">Error</h3>
            <p className="text-sm text-muted-foreground">{message}</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
