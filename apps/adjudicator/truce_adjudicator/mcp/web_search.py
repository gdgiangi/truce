"""Real web search implementation using Brave AI Grounding API."""

import asyncio
import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

from dotenv import load_dotenv

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

try:
    import aiohttp
    from bs4 import BeautifulSoup
except ImportError:
    aiohttp = None
    BeautifulSoup = None

from ..models import TimeWindow

load_dotenv()


class RateLimiter:
    """Rate limiter for API calls."""
    
    def __init__(self, max_calls: int, time_window: float):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire permission to make an API call, blocking if necessary."""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            
            # Remove old calls outside the time window
            self.calls = [call_time for call_time in self.calls if now - call_time < self.time_window]
            
            # If we're at the limit, wait until we can make another call
            if len(self.calls) >= self.max_calls:
                sleep_time = self.calls[0] + self.time_window - now + 0.1  # Small buffer
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    return await self.acquire()  # Retry after waiting
            
            # Record this call
            self.calls.append(now)


class BraveGroundingAPI:
    """Brave AI Grounding API client for evidence-based search with citations."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("BRAVE_SEARCH_API_KEY")
        if not self.api_key:
            raise ValueError("Brave Search API key not configured")
        
        if not AsyncOpenAI:
            raise ValueError("OpenAI package required for Brave Grounding API")
            
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://api.search.brave.com/res/v1",
        )
        
        # Rate limiter: 2 requests per second per Brave documentation
        self.rate_limiter = RateLimiter(max_calls=2, time_window=1.0)

    async def search(
        self,
        query: str,
        count: int = 20,
        offset: int = 0,
        time_window: Optional[TimeWindow] = None,
    ) -> List[Dict[str, Any]]:
        """Search and gather evidence using Brave AI Grounding API with streaming citations."""
        # Respect rate limits
        await self.rate_limiter.acquire()
        
        # Construct query for evidence gathering
        evidence_query = f"Find current evidence and reliable sources about: {query}"
        if time_window and time_window.start:
            days_ago = (datetime.now(timezone.utc) - time_window.start).days
            if days_ago <= 30:
                evidence_query += f" (focus on recent sources from the past {days_ago} days)"
        evidence_query += " Please provide multiple reliable sources with citations."
        
        try:
            # Use streaming to capture citations
            citations = []
            content_parts = []
            
            stream = await self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user", 
                        "content": evidence_query
                    }
                ],
                model="brave",
                stream=True,
                extra_body={
                    "country": "ca",  # Focus on Canadian sources
                    "language": "en",
                    "enable_entities": True,
                    "enable_citations": True,
                    "enable_research": False,  # Use single search for speed
                },
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    delta = chunk.choices[0].delta.content
                    
                    # Parse citation markers
                    if delta.startswith("<citation>") and delta.endswith("</citation>"):
                        try:
                            citation_data = json.loads(
                                delta.removeprefix("<citation>").removesuffix("</citation>")
                            )
                            citations.append(citation_data)
                        except json.JSONDecodeError:
                            continue
                    else:
                        # Collect regular content
                        content_parts.append(delta)
            
            # Convert citations to search results format
            return self._convert_citations_to_results(citations, "".join(content_parts), query)
            
        except Exception as e:
            print(f"Brave Grounding API error: {e}")
            return []

    def _convert_citations_to_results(self, citations: List[Dict[str, Any]], content: str, query: str) -> List[Dict[str, Any]]:
        """Convert Brave Grounding API citations to search results format."""
        results = []
        
        # Process each citation
        for citation in citations:
            # Extract citation data
            # Citation format from Brave API: {start_index, end_index, number, url, favicon, snippet}
            url = citation.get("url", "")
            snippet = citation.get("snippet", "")
            number = citation.get("number", 0)
            
            if not url:
                continue
                
            # Extract title and publisher from URL and snippet
            title = f"Source {number}: {url}"
            publisher = self._extract_publisher(url)
            
            # Use snippet from citation if available, otherwise extract from content
            if not snippet and content:
                # Try to extract relevant text around the citation
                start_idx = citation.get("start_index", 0)
                end_idx = citation.get("end_index", 0)
                if start_idx < len(content) and end_idx <= len(content) and start_idx < end_idx:
                    # Extract a bit more context around the citation
                    context_start = max(0, start_idx - 50)
                    context_end = min(len(content), end_idx + 50)
                    snippet = content[context_start:context_end].strip()
            
            result = {
                "url": url,
                "title": title,
                "snippet": snippet or "Evidence source from Brave Grounding",
                "publisher": publisher,
                "published_at": datetime.now(timezone.utc),  # Current time as we don't have publish date
                "citation_number": number,
                "grounded": True,
            }
            results.append(result)
        
        # If no citations found but we have content, create a general result
        if not results and content and len(content) > 50:
            result = {
                "url": "https://search.brave.com/grounded",
                "title": f"Grounded Evidence: {query}",
                "snippet": content[:500] + "..." if len(content) > 500 else content,
                "publisher": "Brave AI Grounding",
                "published_at": datetime.now(timezone.utc),
                "grounded_content": content,
                "grounded": True,
            }
            results.append(result)
            
        print(f"Converted {len(citations)} citations to {len(results)} search results")
        return results

    def _extract_publisher(self, url: str) -> str:
        """Extract publisher name from URL."""
        try:
            domain = urlparse(url).netloc.lower()
            # Remove www. prefix
            domain = re.sub(r"^www\.", "", domain)
            
            # Map common domains to friendly names
            domain_map = {
                "cbc.ca": "CBC News",
                "theglobeandmail.com": "The Globe and Mail",
                "globalnews.ca": "Global News",
                "ctvnews.ca": "CTV News",
                "thestar.com": "Toronto Star",
                "nationalpost.com": "National Post",
                "macleans.ca": "Maclean's",
                "statcan.gc.ca": "Statistics Canada",
                "rcmp-grc.gc.ca": "RCMP",
                "canada.ca": "Government of Canada",
                "citynews.ca": "CityNews",
                "policyoptions.irpp.org": "Policy Options",
            }
            
            return domain_map.get(domain, domain.replace(".com", "").replace(".ca", "").title())
        except Exception:
            return "Unknown"

    def _parse_relative_time(self, time_str: str) -> Optional[datetime]:
        """Parse relative time strings like '2 days ago' into datetime."""
        try:
            time_str = time_str.lower().strip()
            now = datetime.now(timezone.utc)
            
            match = re.search(r"(\d+)", time_str)
            if not match:
                return None
            
            num = int(match.group(1))
            
            if "minute" in time_str:
                return now - timedelta(minutes=num)
            elif "hour" in time_str:
                return now - timedelta(hours=num)
            elif "day" in time_str:
                return now - timedelta(days=num)
            elif "week" in time_str:
                return now - timedelta(weeks=num)
            elif "month" in time_str:
                return now - timedelta(days=num * 30)  # Approximate
            elif "year" in time_str:
                return now - timedelta(days=num * 365)  # Approximate
        except Exception:
            pass
        return None


class ContentExtractor:
    """Extract and clean content from web pages."""

    def __init__(self):
        if aiohttp:
            self.timeout = aiohttp.ClientTimeout(total=10)
        else:
            self.timeout = None
        # Rate limit page fetching to be respectful
        self.rate_limiter = RateLimiter(max_calls=3, time_window=1.0)

    async def fetch_page_content(self, url: str) -> Dict[str, Any]:
        """Fetch and extract content from a web page."""
        if not aiohttp:
            return self._fallback_content(url)
        
        # Respect rate limits
        await self.rate_limiter.acquire()
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Truce Bot 1.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        return self._fallback_content(url)
                    
                    content_type = response.headers.get("content-type", "")
                    if "text/html" not in content_type:
                        return self._fallback_content(url)
                    
                    html = await response.text()
                    return self._extract_content(html, url)
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
            return self._fallback_content(url)

    def _extract_content(self, html: str, url: str) -> Dict[str, Any]:
        """Extract title, snippet, and metadata from HTML."""
        if not BeautifulSoup:
            return self._fallback_content(url)
            
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # Extract title
            title = ""
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.get_text().strip()
            
            # Extract meta description as snippet
            snippet = ""
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc and hasattr(meta_desc, 'get'):
                content = meta_desc.get("content")
                if content:
                    snippet = str(content).strip()
            
            # If no meta description, extract from first paragraph
            if not snippet:
                p_tags = soup.find_all("p")
                for p in p_tags:
                    text = p.get_text().strip()
                    if len(text) > 50:  # Skip very short paragraphs
                        snippet = text[:500]  # Truncate long paragraphs
                        break
            
            # Extract published date from various meta tags
            published_at = None
            date_selectors = [
                ("meta", {"property": "article:published_time"}),
                ("meta", {"name": "date"}),
                ("meta", {"name": "publish-date"}),
                ("time", {"datetime": True}),
            ]
            
            for tag_name, attrs in date_selectors:
                tag = soup.find(tag_name, attrs)
                if tag and hasattr(tag, 'get'):
                    date_str = tag.get("content") or tag.get("datetime")
                    if date_str:
                        try:
                            date_str = str(date_str)
                            published_at = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                            break
                        except Exception:
                            continue
            
            return {
                "title": title or url,
                "snippet": snippet or "Content available at source.",
                "published_at": published_at,
                "publisher": self._extract_site_name(soup, url),
            }
        except Exception as e:
            print(f"Failed to parse HTML for {url}: {e}")
            return self._fallback_content(url)

    def _extract_site_name(self, soup: Any, url: str) -> str:
        """Extract site name from HTML meta tags or URL."""
        # Try meta tags first
        site_name_selectors = [
            ("meta", {"property": "og:site_name"}),
            ("meta", {"name": "application-name"}),
            ("meta", {"name": "site_name"}),
        ]
        
        for tag_name, attrs in site_name_selectors:
            tag = soup.find(tag_name, attrs)
            if tag and hasattr(tag, 'get'):
                content = tag.get("content")
                if content:
                    return str(content).strip()
        
        # Fall back to domain extraction
        try:
            domain = urlparse(url).netloc.lower()
            domain = re.sub(r"^www\.", "", domain)
            return domain.replace(".com", "").replace(".ca", "").title()
        except Exception:
            return "Unknown"

    def _fallback_content(self, url: str) -> Dict[str, Any]:
        """Return fallback content when extraction fails."""
        return {
            "title": url,
            "snippet": "Content available at source.",
            "published_at": None,
            "publisher": "Unknown",
        }


# Global instances
_brave_search = None
_content_extractor = None

def get_brave_search() -> Optional[BraveGroundingAPI]:
    """Get or create BraveGroundingAPI instance."""
    global _brave_search
    if _brave_search is None:
        try:
            _brave_search = BraveGroundingAPI()
        except ValueError as e:
            print(f"Brave Grounding API not available: {e}")
            return None
    return _brave_search

def get_content_extractor() -> ContentExtractor:
    """Get or create ContentExtractor instance."""
    global _content_extractor
    if _content_extractor is None:
        _content_extractor = ContentExtractor()
    return _content_extractor
