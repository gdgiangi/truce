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
        
        if not aiohttp:
            raise ValueError("aiohttp package required for Brave Grounding API")
        
        # Rate limiter: 2 requests per second per Brave documentation
        self.rate_limiter = RateLimiter(max_calls=2, time_window=1.0)
        self.base_url = "https://api.search.brave.com/res/v1/chat/completions"

    async def search(
        self,
        query: str,
        count: int = 30,  # Increased from 20 to 30 for more comprehensive results
        offset: int = 0,
        time_window: Optional[TimeWindow] = None,
    ) -> List[Dict[str, Any]]:
        """Search and gather evidence using Brave AI Grounding API with proper implementation."""
        # Respect rate limits
        await self.rate_limiter.acquire()
        
        # Construct query for evidence gathering with emphasis on diverse perspectives
        evidence_query = f"Find comprehensive evidence and diverse perspectives about: {query}"
        if time_window and time_window.start:
            days_ago = (datetime.now(timezone.utc) - time_window.start).days
            if days_ago <= 30:
                evidence_query += f" (focus on recent sources from the past {days_ago} days)"
        evidence_query += " Please provide multiple reliable sources including academic, journalistic, governmental, and expert perspectives with detailed citations."
        
        try:
            headers = {
                "x-subscription-token": self.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
            }
            
            payload = {
                "stream": False,
                "messages": [
                    {
                        "role": "user", 
                        "content": evidence_query
                    }
                ],
                "model": "brave"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"Brave API error {response.status}: {error_text}")
                        return []
                    
                    result = await response.json()
                    
                    # Extract content and citations from response
                    if result.get("choices") and len(result["choices"]) > 0:
                        content = result["choices"][0]["message"]["content"]
                        return self._parse_grounded_response(content, query)
                    else:
                        print("No choices in Brave API response")
                        return []
            
        except Exception as e:
            print(f"Brave Grounding API error: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _parse_grounded_response(self, content: str, query: str) -> List[Dict[str, Any]]:
        """Parse Brave AI Grounding response and extract sources."""
        results = []
        
        # Look for citation patterns in the content
        # The Brave API may embed citations in different formats
        citation_patterns = [
            r'\[(\d+)\]\s*(.+?)(?=\[\d+\]|$)',  # [1] Citation text
            r'<citation[^>]*>([^<]+)</citation>',  # <citation>...</citation>
            r'Source:\s*(.+?)(?=\n|$)',  # Source: ...
        ]
        
        citation_number = 1
        for pattern in citation_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL)
            for match in matches:
                citation_text = match.group(1) if len(match.groups()) == 1 else match.group(2)
                citation_text = citation_text.strip()
                
                if len(citation_text) < 10:  # Skip very short citations
                    continue
                
                # Try to extract URL from citation text
                url_match = re.search(r'https?://[^\s\)]+', citation_text)
                url = url_match.group(0) if url_match else f"https://search.brave.com/grounded#{citation_number}"
                
                # Extract publisher from URL or citation text
                publisher = self._extract_publisher(url)
                if publisher == "Unknown":
                    # Try to extract from citation text
                    domain_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', citation_text)
                    if domain_match:
                        publisher = domain_match.group(1)
                
                result = {
                    "url": url,
                    "title": f"Source {citation_number}: {citation_text[:100]}...",
                    "snippet": citation_text[:500] if len(citation_text) > 500 else citation_text,
                    "publisher": publisher,
                    "published_at": datetime.now(timezone.utc),
                    "citation_number": citation_number,
                    "grounded": True,
                }
                results.append(result)
                citation_number += 1
        
        # If no structured citations found, but we have substantial content, 
        # create results based on content analysis
        if not results and content and len(content) > 100:
            # Split content into sentences and look for factual statements
            sentences = re.split(r'[.!?]+', content)
            fact_sentences = [s.strip() for s in sentences if len(s.strip()) > 50 and any(keyword in s.lower() for keyword in ['according to', 'reported', 'study', 'data', 'research', 'found'])]
            
            for i, sentence in enumerate(fact_sentences[:5]):  # Limit to 5 factual statements
                result = {
                    "url": f"https://search.brave.com/grounded#{i+1}",
                    "title": f"Grounded Fact {i+1}: {query}",
                    "snippet": sentence,
                    "publisher": "Brave AI Grounding",
                    "published_at": datetime.now(timezone.utc),
                    "grounded_content": True,
                }
                results.append(result)
        
        # Fallback: if we have any substantial content, create at least one result
        if not results and content and len(content) > 50:
            result = {
                "url": "https://search.brave.com/grounded",
                "title": f"AI-Generated Analysis: {query}",
                "snippet": content[:500] + "..." if len(content) > 500 else content,
                "publisher": "Brave AI Grounding",
                "published_at": datetime.now(timezone.utc),
                "grounded_content": content,
                "ai_generated": True,
            }
            results.append(result)
        
        print(f"Parsed grounded response into {len(results)} search results")
        return results

    def _extract_publisher(self, url: str) -> str:
        """Extract publisher name from URL."""
        try:
            domain = urlparse(url).netloc.lower()
            # Remove www. prefix
            domain = re.sub(r"^www\.", "", domain)
            
            # Map common domains to friendly names - expanded for more comprehensive source recognition
            domain_map = {
                # Canadian News Media
                "cbc.ca": "CBC News",
                "theglobeandmail.com": "The Globe and Mail",
                "globalnews.ca": "Global News",
                "ctvnews.ca": "CTV News",
                "thestar.com": "Toronto Star",
                "nationalpost.com": "National Post",
                "macleans.ca": "Maclean's",
                "citynews.ca": "CityNews",
                "cp24.com": "CP24",
                "660news.com": "660 News",
                "newstalk770.com": "Newstalk 770",
                "calgaryherald.com": "Calgary Herald",
                "edmontonjournal.com": "Edmonton Journal",
                "vancouversun.com": "Vancouver Sun",
                "ottawacitizen.com": "Ottawa Citizen",
                "leaderpost.com": "Regina Leader-Post",
                "thechronicleherald.ca": "The Chronicle Herald",
                
                # Government and Official Sources
                "statcan.gc.ca": "Statistics Canada",
                "rcmp-grc.gc.ca": "RCMP",
                "canada.ca": "Government of Canada",
                "justice.gc.ca": "Department of Justice Canada",
                "parl.ca": "Parliament of Canada",
                "pco-bcp.gc.ca": "Privy Council Office",
                "publicsafety.gc.ca": "Public Safety Canada",
                
                # Academic and Research
                "policyoptions.irpp.org": "Policy Options",
                "irpp.org": "Institute for Research on Public Policy",
                "fraserinstitute.org": "Fraser Institute",
                "policyalternatives.ca": "Canadian Centre for Policy Alternatives",
                "utoronto.ca": "University of Toronto",
                "ubc.ca": "University of British Columbia",
                "mcgill.ca": "McGill University",
                "yorku.ca": "York University",
                
                # International Credible Sources
                "reuters.com": "Reuters",
                "apnews.com": "Associated Press",
                "bbc.com": "BBC",
                "theguardian.com": "The Guardian",
                "nytimes.com": "The New York Times",
                "washingtonpost.com": "The Washington Post",
                "economist.com": "The Economist",
                "oecd.org": "Organisation for Economic Co-operation and Development",
                "who.int": "World Health Organization",
                "worldbank.org": "World Bank",
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
