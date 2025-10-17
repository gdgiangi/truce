"""Explorer MCP toolchain for gathering diverse sources."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from ..models import Evidence, TimeWindow
from .web_search import get_brave_search, get_content_extractor


@dataclass
class ExplorerSource:
    """Normalized source representation from explorer tooling."""

    title: str
    url: str
    snippet: str
    publisher: str
    domain: str
    published_at: Optional[datetime]
    retrieved_at: datetime
    normalized_url: str
    content_hash: str

    def to_evidence(self, provenance: str) -> Evidence:
        """Convert source into an Evidence record."""
        return Evidence(
            url=self.url,
            publisher=self.publisher,
            published_at=self.published_at,
            retrieved_at=self.retrieved_at,
            title=self.title,
            domain=self.domain,
            snippet=self.snippet,
            provenance=provenance,
            normalized_url=self.normalized_url,
            content_hash=self.content_hash,
        )


class ExplorerToolset:
    """Real MCP toolset for web search and content extraction."""

    def __init__(self):
        self.search_api = get_brave_search()
        self.content_extractor = get_content_extractor()

    async def search_web(
        self,
        claim_text: str,
        time_window: Optional[TimeWindow] = None,
        session_id: Optional[str] = None,
        strategy: str = "direct",
    ) -> List[Dict[str, Any]]:
        """Search the web for sources related to the claim with agent reporting."""
        if not self.search_api:
            # No API configured - report error but don't fail completely
            error_msg = "Web search API not configured. Please set BRAVE_SEARCH_API_KEY environment variable."
            print(error_msg)
            if session_id:
                from ..main import emit_agent_update

                await emit_agent_update(
                    session_id,
                    "Search Agent",
                    f"Search API unavailable for {strategy} strategy",
                    "Configuration missing but continuing with other strategies",
                    strategy,
                    [],
                    error_msg,
                )
            return []

        try:
            if session_id:
                from ..main import emit_agent_update

                await emit_agent_update(
                    session_id,
                    "Search Agent",
                    f"Starting {strategy} search for evidence",
                    f"Querying web sources using {strategy} strategy for: {claim_text}",
                    strategy,
                )

            results = await self.search_api.search(
                claim_text, count=15, time_window=time_window
            )

            if session_id:
                if results:
                    source_domains = [
                        result.get("publisher", "Unknown") for result in results[:3]
                    ]
                    await emit_agent_update(
                        session_id,
                        "Search Agent",
                        f"Found {len(results)} sources via {strategy} search",
                        f"Successfully retrieved sources from diverse domains: {', '.join(source_domains)}",
                        strategy,
                        source_domains,
                    )
                else:
                    # Don't report as error - just informational
                    await emit_agent_update(
                        session_id,
                        "Search Agent",
                        f"No results from {strategy} search",
                        f"Search query returned no results for {strategy} strategy. Continuing with other strategies.",
                        strategy,
                        [],
                    )

            if not results:
                print(f"Web search returned no results for: {claim_text} ({strategy})")
            return results
        except Exception as e:
            error_msg = f"Web search failed: {str(e)}"
            print(error_msg)
            if session_id:
                from ..main import emit_agent_update

                # Don't classify as critical error - just report issue
                await emit_agent_update(
                    session_id,
                    "Search Agent",
                    f"Search issue in {strategy} strategy",
                    f"Encountered technical issue but continuing with other strategies: {str(e)}",
                    strategy,
                    [],
                )
            return []

    async def fetch_page(self, url: str) -> Dict[str, Any]:
        """Fetch and extract content from a web page."""
        if not self.content_extractor:
            return {
                "snippet": "Content extraction not available.",
                "publisher": "Unknown",
                "title": url,
                "published_at": None,
            }

        try:
            content = await self.content_extractor.fetch_page_content(url)
            return content
        except Exception as e:
            print(f"Page fetch failed for {url}: {e}")
            return {
                "snippet": "Content extraction failed.",
                "publisher": "Unknown",
                "title": url,
                "published_at": None,
            }

    async def expand_links(self, url: str) -> List[Dict[str, Any]]:
        """Expand a URL into related resources (limited implementation)."""
        # For now, return empty list. This could be extended with:
        # - RSS feed discovery
        # - Related article extraction
        # - Social media post expansion
        return []

    async def deduplicate_sources(
        self, sources: Sequence[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Remove duplicate URLs while annotating normalized data."""
        unique: List[Dict[str, Any]] = []
        seen: set[str] = set()
        now = datetime.utcnow()

        for item in sources:
            candidate_url = item.get("url")
            if not candidate_url:
                continue
            normalized = normalize_url(candidate_url)
            if normalized in seen:
                continue
            seen.add(normalized)
            hydrated = dict(item)
            hydrated["normalized_url"] = normalized
            hydrated.setdefault("publisher", "Unknown")
            hydrated.setdefault("snippet", "")
            hydrated.setdefault("title", item.get("title") or candidate_url)
            hydrated.setdefault("published_at", item.get("published_at"))
            hydrated["domain"] = extract_domain(candidate_url)
            hydrated.setdefault("retrieved_at", now)
            hydrated["content_hash"] = compute_content_hash(
                hydrated["title"], hydrated["snippet"]
            )
            unique.append(hydrated)

        return unique


class ExplorerAgent:
    """Lead Verifier subagent responsible for assembling diverse evidence."""

    def __init__(
        self,
        tools: Optional[ExplorerToolset] = None,
        target_count: int = 20,  # Increased from 8 to 20 for more comprehensive evidence
        domain_share: float = 0.25,  # Reduced from 0.4 to 0.25 for more diverse sources
    ) -> None:
        self.tools = tools or ExplorerToolset()
        self.target_count = target_count
        self.domain_share = domain_share

    async def gather_sources(
        self,
        claim_text: str,
        time_window: Optional[TimeWindow] = None,
        session_id: Optional[str] = None,
    ) -> List[ExplorerSource]:
        """Gather, deduplicate, and diversify sources for a claim using multiple search strategies."""
        candidates: List[Dict[str, Any]] = []

        # Strategy 1: Direct claim search
        search_results = await self.tools.search_web(
            claim_text, time_window, session_id, "direct"
        )
        for result in search_results:
            enriched = await self.tools.fetch_page(result.get("url", ""))
            # Only merge enriched data if it provides actual content
            # Preserve original search result data if enrichment returns fallback values
            merged = dict(result)  # Start with original data
            if (
                enriched.get("snippet")
                and enriched["snippet"] != "Content available at source."
            ):
                merged["snippet"] = enriched["snippet"]
            if enriched.get("publisher") and enriched["publisher"] != "Unknown":
                merged["publisher"] = enriched["publisher"]
            if enriched.get("title") and enriched["title"] != result.get("url"):
                merged["title"] = enriched["title"]
            if enriched.get("published_at"):
                merged["published_at"] = enriched["published_at"]

            merged["search_strategy"] = "direct"
            candidates.append(merged)
            expansions = await self.tools.expand_links(result.get("url", ""))
            if expansions:
                candidates.extend(expansions)

        # Strategy 2: Academic and research perspective
        academic_query = f"research study analysis {claim_text}"
        academic_results = await self.tools.search_web(
            academic_query, time_window, session_id, "academic"
        )
        for result in academic_results[:10]:  # Limit to prevent too many results
            result["search_strategy"] = "academic"
            candidates.append(result)

        # Strategy 3: Government and official sources
        gov_query = f"government official statistics {claim_text}"
        gov_results = await self.tools.search_web(
            gov_query, time_window, session_id, "government"
        )
        for result in gov_results[:10]:
            result["search_strategy"] = "government"
            candidates.append(result)

        # Strategy 4: News and journalistic coverage
        news_query = f"news report investigation {claim_text}"
        news_results = await self.tools.search_web(
            news_query, time_window, session_id, "news"
        )
        for result in news_results[:10]:
            result["search_strategy"] = "news"
            candidates.append(result)

        # Final processing and summary
        if session_id:
            from ..main import emit_agent_update

            await emit_agent_update(
                session_id,
                "Evidence Coordinator",
                f"Consolidating {len(candidates)} sources from all agents",
                f"Deduplicating and diversifying evidence from {len(set(c.get('search_strategy', 'unknown') for c in candidates))} different search strategies",
                "consolidation",
                [],
            )

        deduped = await self.tools.deduplicate_sources(candidates)
        explorer_sources = [self._build_source(item) for item in deduped]

        window = time_window or TimeWindow()
        filtered = self._apply_time_window(explorer_sources, window)
        diversified = self._enforce_domain_diversity(filtered, self.target_count)
        final_sources = diversified[: self.target_count]

        if session_id:
            await emit_agent_update(
                session_id,
                "Evidence Coordinator",
                f"Evidence gathering complete: {len(final_sources)} diverse sources collected",
                f"Successfully coordinated {len(set(c.get('search_strategy', 'unknown') for c in candidates))} search agents to gather comprehensive evidence",
                "complete",
                [source.publisher for source in final_sources[:3]],
            )

        return final_sources

    def _apply_time_window(
        self, sources: Sequence[ExplorerSource], window: TimeWindow
    ) -> List[ExplorerSource]:
        if not window.start and not window.end:
            return list(sources)

        filtered: List[ExplorerSource] = []
        for source in sources:
            published = source.published_at
            if not published:
                filtered.append(source)
                continue
            if window.start and published < window.start:
                continue
            if window.end and published > window.end:
                continue
            filtered.append(source)
        return filtered

    def _enforce_domain_diversity(
        self, sources: Sequence[ExplorerSource], target_count: int
    ) -> List[ExplorerSource]:
        if not sources:
            return []

        max_per_domain = max(1, math.floor(target_count * self.domain_share))
        domain_counts: Dict[str, int] = {}
        selected: List[ExplorerSource] = []

        for source in sources:
            domain = source.domain
            count = domain_counts.get(domain, 0)
            if count >= max_per_domain:
                continue
            domain_counts[domain] = count + 1
            selected.append(source)
            if len(selected) >= target_count:
                break

        return selected

    def _build_source(self, item: Dict[str, Any]) -> ExplorerSource:
        published_at = item.get("published_at")
        if isinstance(published_at, str):
            try:
                published_at = datetime.fromisoformat(published_at)
            except ValueError:
                published_at = None

        retrieved_at = item.get("retrieved_at")
        if isinstance(retrieved_at, str):
            try:
                retrieved_at = datetime.fromisoformat(retrieved_at)
            except ValueError:
                retrieved_at = datetime.utcnow()
        elif retrieved_at is None:
            retrieved_at = datetime.utcnow()

        normalized_url = item.get("normalized_url") or normalize_url(
            item.get("url", "")
        )
        content_hash = item.get("content_hash") or compute_content_hash(
            item.get("title", ""), item.get("snippet", "")
        )

        return ExplorerSource(
            title=item.get("title", item.get("url", "")),
            url=item.get("url", ""),
            snippet=item.get("snippet", ""),
            publisher=item.get("publisher", "Unknown"),
            domain=item.get("domain", extract_domain(item.get("url", ""))),
            published_at=published_at,
            retrieved_at=retrieved_at,
            normalized_url=normalized_url,
            content_hash=content_hash,
        )


def normalize_url(url: str) -> str:
    """Normalize URL for deduplication purposes."""
    if not url:
        return ""
    parsed = urlparse(url)
    netloc = (parsed.hostname or "").lower()
    path = parsed.path.rstrip("/") or "/"
    query_pairs = sorted(parse_qsl(parsed.query))
    normalized_query = urlencode(query_pairs)
    normalized = urlunparse(
        (
            parsed.scheme.lower() or "https",
            netloc,
            path,
            parsed.params,
            normalized_query,
            "",
        )
    )
    return normalized


def extract_domain(url: str) -> str:
    parsed = urlparse(url)
    return (parsed.hostname or "").lower()


def compute_content_hash(title: str, snippet: str) -> str:
    digest = sha256()
    digest.update((title or "").strip().lower().encode("utf-8"))
    digest.update((snippet or "").strip().lower().encode("utf-8"))
    return digest.hexdigest()


_DEFAULT_SEARCH_RESULTS: List[Dict[str, Any]] = [
    {
        "title": "Statistics Canada releases 2024 crime severity findings",
        "url": "https://www150.statcan.gc.ca/n1/daily-quotidien/240801/dq240801a-eng.htm",
        "snippet": "Statistics Canada reports a modest decline in the national crime severity index with regional variation across provinces.",
        "publisher": "Statistics Canada",
        "published_at": datetime(2024, 8, 1),
    },
    {
        "title": "CBC explainer: Why violent crime perceptions differ from stats",
        "url": "https://www.cbc.ca/news/canada/crime-severity-index-2024-explainer",
        "snippet": "Analysis of crime data and public opinion outlining why many Canadians feel crime is rising despite mixed indicators.",
        "publisher": "CBC News",
        "published_at": datetime(2024, 7, 18),
    },
    {
        "title": "Globe and Mail opinion: Crime trends in Canadian cities",
        "url": "https://www.theglobeandmail.com/opinion/article-crime-trends-canada-2024/",
        "snippet": "Editorial assessing policy responses to fluctuating violent crime rates across major Canadian metropolitan areas.",
        "publisher": "The Globe and Mail",
        "published_at": datetime(2024, 7, 5),
    },
    {
        "title": "RCMP annual report on violent crime",
        "url": "https://www.rcmp-grc.gc.ca/en/news/2024/rcmp-annual-report-violent-crime",
        "snippet": "The RCMP details enforcement actions, clearance rates, and areas of concern with violent offences nationwide.",
        "publisher": "RCMP",
        "published_at": datetime(2024, 6, 22),
    },
    {
        "title": "Global News: Fact-checking crime claims",
        "url": "https://globalnews.ca/news/10293876/canada-crime-rate-fact-check-2024/",
        "snippet": "Fact-check exploring multiple datasets to evaluate whether violent crime is increasing or stabilizing.",
        "publisher": "Global News",
        "published_at": datetime(2024, 6, 15),
    },
    {
        "title": "Macleans feature on community safety",
        "url": "https://www.macleans.ca/society/crime/community-safety-index-2024/",
        "snippet": "Magazine feature linking socioeconomic indicators with community safety outcomes across Canada.",
        "publisher": "Maclean's",
        "published_at": datetime(2024, 5, 30),
    },
    {
        "title": "Toronto Star investigation into crime stats transparency",
        "url": "https://www.thestar.com/news/investigations/2024/05/14/violent-crime-statistics-transparency.html",
        "snippet": "Investigation into how provincial agencies communicate violent crime data to the public.",
        "publisher": "Toronto Star",
        "published_at": datetime(2024, 5, 14),
    },
    {
        "title": "CTV News timeline: Violent crime hotspots",
        "url": "https://www.ctvnews.ca/canada/violent-crime-hotspots-2024-timeline-1.6854321",
        "snippet": "CTV compiles a timeline of notable violent crime incidents across Canada in 2023-2024.",
        "publisher": "CTV News",
        "published_at": datetime(2024, 4, 28),
    },
    {
        "title": "Policy Options review of justice reforms",
        "url": "https://policyoptions.irpp.org/magazines/june-2024/justice-reforms-and-violent-crime/",
        "snippet": "Academic review of recent justice reforms and their relationship to violent crime outcomes.",
        "publisher": "Policy Options",
        "published_at": datetime(2024, 4, 2),
    },
    {
        "title": "CityNews panel: Experts debate crime narratives",
        "url": "https://toronto.citynews.ca/2024/03/21/experts-debate-crime-narratives/",
        "snippet": "Panel of criminologists discuss discrepancies between media narratives and statistical trends.",
        "publisher": "CityNews",
        "published_at": datetime(2024, 3, 21),
    },
]
