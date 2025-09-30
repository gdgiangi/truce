import Link from "next/link";

import { SearchBar } from "@/components/search-bar";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface ClaimSearchHit {
  slug: string;
  text: string;
  score: number;
}

interface EvidenceSearchHit {
  claim_slug: string;
  evidence_id: string;
  snippet: string;
  publisher: string;
  url: string;
  score: number;
}

interface SearchResponse {
  query: string;
  claims: ClaimSearchHit[];
  evidence: EvidenceSearchHit[];
}

const adjudicatorUrl = process.env.ADJUDICATOR_API_URL || "http://localhost:8000";

async function fetchSearchResults(query: string): Promise<SearchResponse | null> {
  try {
    const params = new URLSearchParams({ q: query });
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

function formatScore(score: number): string {
  const relevance = 1 / (1 + Math.max(score, 0));
  return relevance.toFixed(2);
}

export default async function SearchPage({ searchParams }: { searchParams?: Record<string, string | string[] | undefined> }) {
  const rawQuery = searchParams?.q;
  const query = Array.isArray(rawQuery) ? rawQuery[0] : rawQuery ?? "";

  const trimmed = query.trim();
  const results = trimmed ? await fetchSearchResults(trimmed) : null;
  const hasResults = Boolean(results && (results.claims.length > 0 || results.evidence.length > 0));

  return (
    <div className="container mx-auto px-4 py-10">
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-8">
        <div className="flex flex-col gap-3">
          <h1 className="text-3xl font-semibold">Search</h1>
          <p className="text-muted-foreground">Find claims and supporting evidence across the Truce knowledge base.</p>
          <SearchBar initialQuery={trimmed} />
        </div>

        {!trimmed && (
          <Card className="border-dashed">
            <CardContent className="py-10 text-center text-muted-foreground">
              Enter a query to discover relevant claims and citations.
            </CardContent>
          </Card>
        )}

        {trimmed && !hasResults && (
          <Card>
            <CardContent className="py-10 text-center text-muted-foreground">
              No results found for <span className="font-medium">“{trimmed}”</span>. Try a different search term.
            </CardContent>
          </Card>
        )}

        {hasResults && results && (
          <div className="grid gap-8 lg:grid-cols-[1.2fr_1fr]">
            <div className="space-y-6">
              <h2 className="text-xl font-semibold">Claims</h2>
              {results.claims.map((claim) => (
                <Card key={claim.slug} className="transition hover:border-truce-400/60">
                  <CardHeader>
                    <CardTitle className="text-lg font-medium">
                      <Link href={`/claim/${claim.slug}`}>{claim.text}</Link>
                    </CardTitle>
                    <Badge variant="outline" className="w-fit">Relevance {formatScore(claim.score)}</Badge>
                  </CardHeader>
                </Card>
              ))}
              {results.claims.length === 0 && (
                <p className="text-sm text-muted-foreground">No direct claim matches.</p>
              )}
            </div>

            <div className="space-y-6">
              <h2 className="text-xl font-semibold">Evidence</h2>
              {results.evidence.map((evidence) => (
                <Card key={evidence.evidence_id} className="transition hover:border-truce-400/60">
                  <CardHeader className="space-y-2">
                    <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-muted-foreground">
                      <span>{evidence.publisher}</span>
                      <Badge variant="outline">Relevance {formatScore(evidence.score)}</Badge>
                    </div>
                    <CardTitle className="text-base font-medium leading-6">
                      <Link href={`/claim/${evidence.claim_slug}`}>{evidence.snippet}</Link>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <Link href={evidence.url} className="text-sm text-truce-600 hover:underline" target="_blank" rel="noopener noreferrer">
                      View source
                    </Link>
                  </CardContent>
                </Card>
              ))}
              {results.evidence.length === 0 && (
                <p className="text-sm text-muted-foreground">No supporting evidence found.</p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
