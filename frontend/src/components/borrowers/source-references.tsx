"use client";

import Link from "next/link";
import { FileText } from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { SourceReference } from "@/lib/api/types";

interface SourceReferencesProps {
  sources: SourceReference[];
  borrowerName?: string;
}

interface GroupedSources {
  [documentId: string]: SourceReference[];
}

function truncateSnippet(snippet: string, maxLength = 150): string {
  if (snippet.length <= maxLength) return snippet;
  return snippet.slice(0, maxLength).trim() + "...";
}

export function SourceReferences({
  sources,
  borrowerName,
}: SourceReferencesProps) {
  // Group sources by document ID
  const groupedSources = sources.reduce<GroupedSources>((acc, source) => {
    if (!acc[source.document_id]) {
      acc[source.document_id] = [];
    }
    acc[source.document_id].push(source);
    return acc;
  }, {});

  const documentIds = Object.keys(groupedSources);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Source Documents</CardTitle>
      </CardHeader>
      <CardContent>
        {documentIds.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No source documents found.
          </p>
        ) : (
          <div className="space-y-6">
            {documentIds.map((documentId) => (
              <div key={documentId} className="space-y-3">
                {/* Document link */}
                <Link
                  href={`/documents/${documentId}`}
                  className="flex items-center gap-2 text-sm font-medium text-primary hover:underline"
                >
                  <FileText className="h-4 w-4" />
                  Document: {documentId.slice(0, 8)}...
                </Link>

                {/* References from this document */}
                <div className="ml-6 space-y-3 border-l-2 border-muted pl-4">
                  {groupedSources[documentId].map((source) => (
                    <div key={source.id} className="space-y-1">
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span>Page {source.page_number}</span>
                        {source.section && (
                          <>
                            <span>&bull;</span>
                            <span>{source.section}</span>
                          </>
                        )}
                      </div>
                      <p className="text-sm">
                        {truncateSnippet(source.snippet)}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
