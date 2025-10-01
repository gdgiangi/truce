import { SearchBar } from "@/components/search-bar";
import { SearchResults } from "@/components/search-results";

interface SearchResponse {
  query: string;
  claims: any[];
  evidence: any[];
  suggestion_slug?: string;
}

const adjudicatorUrl = process.env.ADJUDICATOR_API_URL || "http://localhost:8000";

async function fetchSearchResults(query: string, autoCreate = false): Promise<SearchResponse | null> {
  try {
    const params = new URLSearchParams({ 
      q: query,
      auto_create: autoCreate.toString()
    });
    const response = await fetch(`${adjudicatorUrl}/search?${params.toString()}`, {
      cache: "no-store",
    });

    if (!response.ok) {
      return null;
    }

    return response.json();
  } catch (error) {
    console.error("Search fetch error", error);
    return null;
  }
}



export default async function SearchPage({ searchParams }: { searchParams?: Record<string, string | string[] | undefined> }) {
  const rawQuery = searchParams?.q;
  const query = Array.isArray(rawQuery) ? rawQuery[0] : rawQuery ?? "";

  const trimmed = query.trim();
  const results = trimmed ? await fetchSearchResults(trimmed) : null;

  return (
    <div className="container mx-auto px-4 py-10">
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-8">
        <div className="flex flex-col gap-3">
          <h1 className="text-3xl font-semibold">Search</h1>
          <p className="text-muted-foreground">Find claims and supporting evidence, or create new comprehensive analyses.</p>
          <SearchBar initialQuery={trimmed} />
        </div>

                <SearchResults initialQuery={trimmed} initialResults={results} />
      </div>
    </div>
  );
}
