"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { BorrowerTable } from "@/components/borrowers/borrower-table";
import { BorrowerSearch } from "@/components/borrowers/borrower-search";
import { useBorrowers, useSearchBorrowers } from "@/hooks/use-borrowers";

export default function BorrowersPage() {
  const router = useRouter();
  const [searchInput, setSearchInput] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [limit] = useState(10);
  const [offset, setOffset] = useState(0);

  // Determine if we're in search mode
  const isSearchMode = searchTerm.length >= 2;

  // Fetch borrowers list (default view)
  const {
    data: listData,
    isLoading: isListLoading,
    isError: isListError,
  } = useBorrowers(limit, offset);

  // Fetch search results (search mode)
  const {
    data: searchData,
    isLoading: isSearchLoading,
    isFetching: isSearchFetching,
  } = useSearchBorrowers(searchTerm);

  // Use search data when in search mode, otherwise use list data
  const data = isSearchMode ? searchData : listData;
  const isLoading = isSearchMode ? isSearchLoading : isListLoading;
  const borrowers = data?.borrowers ?? [];
  const total = data?.total ?? 0;

  const handleSearch = useCallback((term: string) => {
    setSearchTerm(term);
    // Reset pagination when search changes
    setOffset(0);
  }, []);

  const handleRowClick = useCallback(
    (id: string) => {
      router.push(`/borrowers/${id}`);
    },
    [router]
  );

  // Pagination calculations
  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.ceil(total / limit);
  const hasPrevious = offset > 0;
  const hasNext = offset + limit < total;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Borrowers</h1>
        <p className="mt-2 text-muted-foreground">
          View and search extracted borrower data with source attribution
        </p>
      </div>

      {/* Search */}
      <BorrowerSearch
        value={searchInput}
        onChange={setSearchInput}
        onSearch={handleSearch}
        isSearching={isSearchFetching}
      />

      {/* Results */}
      <Card>
        <CardHeader>
          <CardTitle>
            {isSearchMode
              ? `Search Results (${total})`
              : `All Borrowers (${total})`}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : isListError ? (
            <div className="py-8 text-center">
              <p className="text-muted-foreground">
                Failed to load borrowers. Please try again.
              </p>
            </div>
          ) : borrowers.length === 0 ? (
            <div className="py-8 text-center">
              <p className="text-muted-foreground">
                {isSearchMode
                  ? "No borrowers found matching your search."
                  : "No borrowers found."}
              </p>
            </div>
          ) : (
            <>
              <BorrowerTable borrowers={borrowers} onRowClick={handleRowClick} />

              {/* Pagination controls - only show for list view, not search */}
              {!isSearchMode && totalPages > 1 && (
                <div className="flex items-center justify-between pt-4">
                  <span className="text-sm text-muted-foreground">
                    Page {currentPage} of {totalPages}
                  </span>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setOffset(Math.max(0, offset - limit))}
                      disabled={!hasPrevious}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setOffset(offset + limit)}
                      disabled={!hasNext}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
