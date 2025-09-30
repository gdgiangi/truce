"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";

import { Button } from "@/components/ui/button";

interface SearchBarProps {
  initialQuery?: string;
  placeholder?: string;
  className?: string;
}

export function SearchBar({ initialQuery = "", placeholder = "Search claims and evidence", className = "" }: SearchBarProps) {
  const router = useRouter();
  const [query, setQuery] = useState(initialQuery);

  useEffect(() => {
    setQuery(initialQuery);
  }, [initialQuery]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) {
      return;
    }
    const params = new URLSearchParams({ q: trimmed });
    router.push(`/search?${params.toString()}`);
  };

  return (
    <form onSubmit={handleSubmit} className={`flex w-full flex-col gap-3 sm:flex-row ${className}`}>
      <div className="flex w-full flex-1 items-center gap-2 rounded-lg border border-input bg-background px-3 py-2 focus-within:border-truce-500 focus-within:ring-2 focus-within:ring-truce-500/40">
        <Search className="h-4 w-4 text-muted-foreground" />
        <input
          className="w-full bg-transparent text-sm outline-none"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={placeholder}
          aria-label={placeholder}
        />
      </div>
      <Button type="submit" className="sm:w-32">
        Search
      </Button>
    </form>
  );
}
