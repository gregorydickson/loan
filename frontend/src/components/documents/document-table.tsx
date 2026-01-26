"use client";

import Link from "next/link";
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  type ColumnDef,
} from "@tanstack/react-table";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "./status-badge";
import { useDeleteDocument } from "@/hooks/use-documents";
import type { DocumentResponse } from "@/lib/api/types";

/**
 * Format bytes to human-readable string (B, KB, MB).
 */
function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface DocumentTableProps {
  documents: DocumentResponse[];
}

/**
 * Table component for displaying document list.
 *
 * Each row is clickable and navigates to the document detail page.
 * Includes delete button for each document.
 */
export function DocumentTable({ documents }: DocumentTableProps) {
  const deleteDocument = useDeleteDocument();

  /**
   * Handle document deletion with confirmation.
   */
  const handleDelete = (
    e: React.MouseEvent,
    documentId: string,
    filename: string
  ) => {
    e.preventDefault();
    e.stopPropagation();
    if (confirm(`Delete "${filename}"? This will also remove extracted borrowers.`)) {
      deleteDocument.mutate(documentId);
    }
  };

  /**
   * Column definitions for the document table.
   */
  const columns: ColumnDef<DocumentResponse>[] = [
    {
      accessorKey: "filename",
      header: "Filename",
      cell: ({ row }) => (
        <span className="font-medium">{row.getValue("filename")}</span>
      ),
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => <StatusBadge status={row.getValue("status")} />,
    },
    {
      accessorKey: "page_count",
      header: "Pages",
      cell: ({ row }) => {
        const pageCount = row.getValue("page_count") as number | null;
        return pageCount !== null ? pageCount : "-";
      },
    },
    {
      accessorKey: "file_size_bytes",
      header: "Size",
      cell: ({ row }) => formatBytes(row.getValue("file_size_bytes")),
    },
    {
      accessorKey: "file_type",
      header: "Type",
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) => (
        <Button
          variant="ghost"
          size="sm"
          className="text-red-600 hover:text-red-700 hover:bg-red-50"
          onClick={(e) =>
            handleDelete(e, row.original.id, row.original.filename)
          }
          disabled={deleteDocument.isPending}
        >
          Delete
        </Button>
      ),
    },
  ];

  const table = useReactTable({
    data: documents,
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
        {table.getRowModel().rows.length ? (
          table.getRowModel().rows.map((row) => (
            <TableRow
              key={row.id}
              className="cursor-pointer"
              data-state={row.getIsSelected() && "selected"}
            >
              {row.getVisibleCells().map((cell, index) => (
                <TableCell key={cell.id}>
                  {/* Wrap first cell in link for accessibility, others just render */}
                  {index === 0 ? (
                    <Link
                      href={`/documents/${row.original.id}`}
                      className="block -m-2 p-2"
                    >
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </Link>
                  ) : (
                    <Link
                      href={`/documents/${row.original.id}`}
                      className="block -m-2 p-2"
                      tabIndex={-1}
                    >
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </Link>
                  )}
                </TableCell>
              ))}
            </TableRow>
          ))
        ) : (
          <TableRow>
            <TableCell colSpan={columns.length} className="h-24 text-center">
              No documents found.
            </TableCell>
          </TableRow>
        )}
      </TableBody>
    </Table>
  );
}
