"use client";

import { useQuery } from "@tanstack/react-query";
import {
  listBorrowers,
  searchBorrowers,
  getBorrower,
  getBorrowerSources,
} from "@/lib/api/borrowers";
import type {
  BorrowerListResponse,
  BorrowerDetailResponse,
  BorrowerSourcesResponse,
} from "@/lib/api/types";

/**
 * Hook to fetch paginated list of borrowers.
 *
 * @param limit - Maximum borrowers to return (default 10)
 * @param offset - Number of borrowers to skip (default 0)
 * @returns Query result with borrower list
 */
export function useBorrowers(limit = 10, offset = 0) {
  return useQuery<BorrowerListResponse>({
    queryKey: ["borrowers", limit, offset],
    queryFn: () => listBorrowers(limit, offset),
  });
}

/**
 * Hook to search borrowers by name.
 *
 * @param searchTerm - Name to search for (minimum 2 characters)
 * @returns Query result with matching borrowers
 */
export function useSearchBorrowers(searchTerm: string) {
  return useQuery<BorrowerListResponse>({
    queryKey: ["borrowers", "search", searchTerm],
    queryFn: () => searchBorrowers({ name: searchTerm }),
    enabled: searchTerm.length >= 2,
  });
}

/**
 * Hook to fetch single borrower details.
 *
 * @param id - Borrower UUID
 * @returns Query result with borrower details including income records and sources
 */
export function useBorrower(id: string) {
  return useQuery<BorrowerDetailResponse>({
    queryKey: ["borrower", id],
    queryFn: () => getBorrower(id),
    enabled: !!id,
  });
}

/**
 * Hook to fetch source documents for a borrower.
 *
 * @param id - Borrower UUID
 * @returns Query result with source references
 */
export function useBorrowerSources(id: string) {
  return useQuery<BorrowerSourcesResponse>({
    queryKey: ["borrower-sources", id],
    queryFn: () => getBorrowerSources(id),
    enabled: !!id,
  });
}
