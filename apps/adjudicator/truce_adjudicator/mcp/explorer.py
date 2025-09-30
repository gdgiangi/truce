"""Explorer MCP toolchain for gathering diverse sources."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Any, Dict, Iterable, List, Optional, Sequence
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from ..models import Evidence, TimeWindow


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
    """Minimal MCP toolset stubs used by the explorer agent."""

    async def search_web(
        self, claim_text: str, time_window: Optional[TimeWindow] = None
    ) -> List[Dict[str, Any]]:
        """Return seed results for the claim (static sample)."""
        return list(_DEFAULT_SEARCH_RESULTS)

    async def fetch_page(self, url: str) -> Dict[str, Any]:
        """Fetch metadata for a URL (static enrichment)."""
        entry = next((item for item in _DEFAULT_SEARCH_RESULTS if item["url"] == url), None)
        if entry:
            return {
                "snippet": entry["snippet"],
                "publisher": entry["publisher"],
                "title": entry["title"],
                "published_at": entry.get("published_at"),
            }
        return {
            "snippet": "Summary unavailable.",
            "publisher": "Unknown",
            "title": url,
            "published_at": None,
        }

    async def expand_links(self, url: str) -> List[Dict[str, Any]]:
        """Expand a URL into related resources (empty stub by default)."""
        return []

    async def deduplicate_sources(self, sources: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
        target_count: int = 8,
        domain_share: float = 0.4,
    ) -> None:
        self.tools = tools or ExplorerToolset()
        self.target_count = target_count
        self.domain_share = domain_share

    async def gather_sources(
        self, claim_text: str, time_window: Optional[TimeWindow] = None
    ) -> List[ExplorerSource]:
        """Gather, deduplicate, and diversify sources for a claim."""
        search_results = await self.tools.search_web(claim_text, time_window)
        candidates: List[Dict[str, Any]] = []

        for result in search_results:
            enriched = await self.tools.fetch_page(result.get("url", ""))
            merged = {**result, **enriched}
            candidates.append(merged)
            expansions = await self.tools.expand_links(result.get("url", ""))
            if expansions:
                candidates.extend(expansions)

        deduped = await self.tools.deduplicate_sources(candidates)
        explorer_sources = [self._build_source(item) for item in deduped]

        window = time_window or TimeWindow()
        filtered = self._apply_time_window(explorer_sources, window)
        diversified = self._enforce_domain_diversity(filtered, self.target_count)
        return diversified[: self.target_count]

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

        normalized_url = item.get("normalized_url") or normalize_url(item.get("url", ""))
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
