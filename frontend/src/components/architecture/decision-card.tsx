import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

type DecisionStatus = "pending" | "adopted";

interface DecisionCardProps {
  title: string;
  decision: string;
  rationale: string;
  status: DecisionStatus;
}

const statusConfig: Record<
  DecisionStatus,
  { label: string; variant: "default" | "secondary" | "outline" }
> = {
  pending: { label: "Pending", variant: "secondary" },
  adopted: { label: "Adopted", variant: "default" },
};

export function DecisionCard({
  title,
  decision,
  rationale,
  status,
}: DecisionCardProps) {
  const config = statusConfig[status];

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <CardTitle className="text-lg">{title}</CardTitle>
          <Badge variant={config.variant}>{config.label}</Badge>
        </div>
        <CardDescription>{decision}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="text-sm text-muted-foreground">
          <span className="font-medium text-foreground">Rationale:</span>{" "}
          {rationale}
        </div>
      </CardContent>
    </Card>
  );
}
