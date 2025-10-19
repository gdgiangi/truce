"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Search, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";

const adjudicatorUrl = process.env.NEXT_PUBLIC_ADJUDICATOR_API_URL || 'http://localhost:8000';

interface SearchBarProps {
  initialQuery?: string;
  placeholder?: string;
  className?: string;
}

export function SearchBar({ initialQuery = "", placeholder = "Search claims and evidence", className = "" }: SearchBarProps) {
  const router = useRouter();
  const [query, setQuery] = useState(initialQuery);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    setQuery(initialQuery);
  }, [initialQuery]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed || isLoading) {
      return;
    }

    setIsLoading(true);

    try {
      // Start the async claim creation
      const response = await fetch(`${adjudicatorUrl}/claims/create-async`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: trimmed })
      });

      if (response.ok) {
        const { session_id } = await response.json();
        // Navigate to the analyzing page with session ID
        router.push(`/analyzing?session=${session_id}&q=${encodeURIComponent(trimmed)}`);
      } else {
        throw new Error('Failed to start claim creation');
      }
    } catch (error) {
      console.error("Failed to create claim:", error);
      setIsLoading(false);
    }
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
          disabled={isLoading}
        />
      </div>
      <Button type="submit" className="sm:w-32" disabled={isLoading}>
        {isLoading ? (
          <>
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            Analyzing
          </>
        ) : (
          "Search"
        )}
      </Button>
    </form>
  );
}
