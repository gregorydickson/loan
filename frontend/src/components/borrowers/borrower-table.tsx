"use client";

import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  createColumnHelper,
} from "@tanstack/react-table";
import { format } from "date-fns";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { BorrowerSummary } from "@/lib/api/types";

const columnHelper = createColumnHelper<BorrowerSummary>();

function getConfidenceBadgeVariant(
  score: number
): "default" | "secondary" | "destructive" {
  if (score >= 0.7) return "default";
  if (score >= 0.5) return "secondary";
  return "destructive";
}

const columns = [
  columnHelper.accessor("name", {
    header: "Name",
    cell: (info) => <span className="font-medium">{info.getValue()}</span>,
  }),
  columnHelper.accessor("confidence_score", {
    header: "Confidence",
    cell: (info) => {
      const score = parseFloat(info.getValue());
      return (
        <Badge variant={getConfidenceBadgeVariant(score)}>
          {(score * 100).toFixed(0)}%
        </Badge>
      );
    },
  }),
  columnHelper.accessor("income_count", {
    header: "Income Records",
    cell: (info) => info.getValue(),
  }),
  columnHelper.accessor("created_at", {
    header: "Created",
    cell: (info) => format(new Date(info.getValue()), "MMM d, yyyy"),
  }),
];

interface BorrowerTableProps {
  borrowers: BorrowerSummary[];
  onRowClick?: (id: string) => void;
}

export function BorrowerTable({ borrowers, onRowClick }: BorrowerTableProps) {
  const table = useReactTable({
    data: borrowers,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <Table>
      <TableHeader>
        {table.getHeaderGroups().map((headerGroup) => (
          <TableRow key={headerGroup.id}>
            {headerGroup.headers.map((header) => (
              <TableHead key={header.id}>
                {header.isPlaceholder
                  ? null
                  : flexRender(
                      header.column.columnDef.header,
                      header.getContext()
                    )}
              </TableHead>
            ))}
          </TableRow>
        ))}
      </TableHeader>
      <TableBody>
        {table.getRowModel().rows.length === 0 ? (
          <TableRow>
            <TableCell colSpan={columns.length} className="h-24 text-center">
              No borrowers found.
            </TableCell>
          </TableRow>
        ) : (
          table.getRowModel().rows.map((row) => (
            <TableRow
              key={row.id}
              onClick={() => onRowClick?.(row.original.id)}
              className={onRowClick ? "cursor-pointer" : ""}
            >
              {row.getVisibleCells().map((cell) => (
                <TableCell key={cell.id}>
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </TableCell>
              ))}
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  );
}
