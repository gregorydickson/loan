"use client";

import { useDeferredValue, useRef, useEffect } from "react";
import { Search, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";

interface BorrowerSearchProps {
  value: string;
  onChange: (value: string) => void;
  onSearch: (searchTerm: string) => void;
  isSearching?: boolean;
}

export function BorrowerSearch({
  value,
  onChange,
  onSearch,
  isSearching = false,
}: BorrowerSearchProps) {
  const deferredValue = useDeferredValue(value);
  const previousDeferredRef = useRef(deferredValue);

  useEffect(() => {
    // Only trigger search when deferred value actually changes
    if (previousDeferredRef.current !== deferredValue) {
      previousDeferredRef.current = deferredValue;

      // Trigger search for 2+ chars or clear for empty
      if (deferredValue.length >= 2 || deferredValue.length === 0) {
        onSearch(deferredValue);
      }
    }
  }, [deferredValue, onSearch]);

  return (
    <div className="relative">
      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        placeholder="Search borrowers by name (min 2 characters)..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="pl-9 pr-9"
      />
      {isSearching && (
        <Loader2 className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-muted-foreground" />
      )}
    </div>
  );
}
