import { Badge } from "@/components/ui/badge";
import type { DocumentStatus } from "@/lib/api/types";

/**
 * Status configuration for document processing states.
 */
const statusConfig: Record<
  DocumentStatus,
  { label: string; variant: "default" | "secondary" | "destructive" | "outline" }
> = {
  pending: { label: "Pending", variant: "secondary" },
  processing: { label: "Processing", variant: "outline" },
  completed: { label: "Completed", variant: "default" },
  failed: { label: "Failed", variant: "destructive" },
};

interface StatusBadgeProps {
  status: DocumentStatus;
}

/**
 * Badge component displaying document processing status.
 *
 * Maps status to appropriate colors:
 * - pending: secondary (gray)
 * - processing: outline (border)
 * - completed: default (primary/green)
 * - failed: destructive (red)
 */
export function StatusBadge({ status }: StatusBadgeProps) {
  const config = statusConfig[status];
  return <Badge variant={config.variant}>{config.label}</Badge>;
}
