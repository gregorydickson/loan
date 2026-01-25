/**
 * Document API client functions.
 */

import { apiClient } from "./client";
import type {
  DocumentUploadResponse,
  DocumentStatusResponse,
  DocumentResponse,
  DocumentListResponse,
} from "./types";

/**
 * Upload a document for processing.
 *
 * Note: Do NOT set Content-Type header - browser will set multipart boundary.
 *
 * @param formData - FormData with file attached
 * @returns Upload response with document ID and status
 */
export async function uploadDocument(
  formData: FormData
): Promise<DocumentUploadResponse> {
  return apiClient<DocumentUploadResponse>("/api/documents/", {
    method: "POST",
    body: formData,
    // Do NOT set Content-Type - browser handles multipart boundary
  });
}

/**
 * Get document processing status (lightweight polling endpoint).
 *
 * @param id - Document UUID
 * @returns Status response with page count and error message if any
 */
export async function getDocumentStatus(
  id: string
): Promise<DocumentStatusResponse> {
  return apiClient<DocumentStatusResponse>(`/api/documents/${id}/status`);
}

/**
 * Get full document details by ID.
 *
 * @param id - Document UUID
 * @returns Full document details
 */
export async function getDocument(id: string): Promise<DocumentResponse> {
  return apiClient<DocumentResponse>(`/api/documents/${id}`);
}

/**
 * List documents with pagination.
 *
 * @param limit - Maximum documents to return (default 100)
 * @param offset - Number of documents to skip (default 0)
 * @returns Paginated list of documents
 */
export async function listDocuments(
  limit = 100,
  offset = 0
): Promise<DocumentListResponse> {
  const params = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });
  return apiClient<DocumentListResponse>(`/api/documents/?${params}`);
}

/**
 * Upload a document with extraction method and OCR parameters.
 *
 * @param formData - FormData with file attached
 * @param queryParams - Query string with method and ocr params
 * @returns Upload response with document ID and status
 */
export async function uploadDocumentWithParams(
  formData: FormData,
  queryParams: string
): Promise<DocumentUploadResponse> {
  return apiClient<DocumentUploadResponse>(`/api/documents/?${queryParams}`, {
    method: "POST",
    body: formData,
  });
}
