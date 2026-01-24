"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  uploadDocument,
  listDocuments,
  getDocumentStatus,
  getDocument,
} from "@/lib/api/documents";
import type {
  DocumentUploadResponse,
  DocumentResponse,
  DocumentStatusResponse,
  DocumentListResponse,
} from "@/lib/api/types";

/**
 * Hook for uploading documents.
 *
 * On success, invalidates the documents list query to trigger a refresh.
 */
export function useUploadDocument() {
  const queryClient = useQueryClient();

  return useMutation<DocumentUploadResponse, Error, File>({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return uploadDocument(formData);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

/**
 * Hook for fetching the list of documents with pagination.
 *
 * @param limit - Maximum documents to return (default 100)
 * @param offset - Number of documents to skip (default 0)
 */
export function useDocuments(limit = 100, offset = 0) {
  return useQuery<DocumentListResponse>({
    queryKey: ["documents", limit, offset],
    queryFn: () => listDocuments(limit, offset),
  });
}

/**
 * Hook for polling document processing status.
 *
 * Polls every 2 seconds while document is pending or processing.
 * Stops polling when status is completed or failed.
 *
 * @param documentId - Document UUID to poll, or null to disable
 */
export function useDocumentStatus(documentId: string | null) {
  return useQuery<DocumentStatusResponse>({
    queryKey: ["document-status", documentId],
    queryFn: () => getDocumentStatus(documentId!),
    enabled: !!documentId,
    refetchInterval: (query) => {
      const data = query.state.data;
      // Stop polling when processing completes
      if (data?.status === "completed" || data?.status === "failed") {
        return false;
      }
      return 2000; // Poll every 2 seconds while processing
    },
  });
}

/**
 * Hook for fetching a single document by ID.
 *
 * @param id - Document UUID
 */
export function useDocument(id: string) {
  return useQuery<DocumentResponse>({
    queryKey: ["document", id],
    queryFn: () => getDocument(id),
    enabled: !!id,
  });
}
