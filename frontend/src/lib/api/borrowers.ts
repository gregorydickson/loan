/**
 * Borrower API client functions.
 */

import { apiClient } from "./client";
import type {
  BorrowerListResponse,
  BorrowerDetailResponse,
  BorrowerSourcesResponse,
} from "./types";

/**
 * List borrowers with pagination.
 *
 * @param limit - Maximum borrowers to return (default 100)
 * @param offset - Number of borrowers to skip (default 0)
 * @returns Paginated list of borrowers
 */
export async function listBorrowers(
  limit = 100,
  offset = 0
): Promise<BorrowerListResponse> {
  const params = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });
  return apiClient<BorrowerListResponse>(`/api/borrowers/?${params}`);
}

export interface BorrowerSearchParams {
  name?: string;
  account_number?: string;
  limit?: number;
  offset?: number;
}

/**
 * Search borrowers by name or account number.
 *
 * At least one of name or account_number must be provided.
 *
 * @param params - Search parameters
 * @returns Paginated list of matching borrowers
 */
export async function searchBorrowers(
  params: BorrowerSearchParams
): Promise<BorrowerListResponse> {
  const searchParams = new URLSearchParams();

  if (params.name) {
    searchParams.set("name", params.name);
  }
  if (params.account_number) {
    searchParams.set("account_number", params.account_number);
  }
  if (params.limit !== undefined) {
    searchParams.set("limit", params.limit.toString());
  }
  if (params.offset !== undefined) {
    searchParams.set("offset", params.offset.toString());
  }

  return apiClient<BorrowerListResponse>(
    `/api/borrowers/search?${searchParams}`
  );
}

/**
 * Get borrower details by ID.
 *
 * @param id - Borrower UUID
 * @returns Full borrower details with relationships
 */
export async function getBorrower(id: string): Promise<BorrowerDetailResponse> {
  return apiClient<BorrowerDetailResponse>(`/api/borrowers/${id}`);
}

/**
 * Get source documents for a borrower.
 *
 * @param id - Borrower UUID
 * @returns Source references for traceability
 */
export async function getBorrowerSources(
  id: string
): Promise<BorrowerSourcesResponse> {
  return apiClient<BorrowerSourcesResponse>(`/api/borrowers/${id}/sources`);
}
