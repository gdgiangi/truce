"""FastMCP server for Brave Search API integration."""

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from fastmcp import FastMCP
from dotenv import load_dotenv
import aiohttp

load_dotenv()

# Initialize the FastMCP server
mcp = FastMCP(
    name="Brave Search Server",
    instructions="A research assistant that can search the web using Brave Search API. "
                 "Use web_search to find information, sources, and evidence about any topic."
)

class BraveSearchAPI:
    """Brave Search API client for web search."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("BRAVE_SEARCH_API_KEY")
        if not self.api_key:
            raise ValueError("Brave Search API key not configured")
        
        self.base_url = "https://api.search.brave.com/res/v1/web/search"

    async def search(
        self,
        query: str,
        count: int = 10,
        offset: int = 0,
        time_window: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search the web using Brave Search API."""
        
        headers = {
            "X-Subscription-Token": self.api_key,
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
        }
        
        params = {
            "q": query,
            "count": min(count, 20),  # Brave API limit
            "offset": offset,
            "search_lang": "en",
            "country": "US",
            "safesearch": "moderate",
        }
        
        # Add time filter if provided
        if time_window:
            params["tf"] = time_window
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, headers=headers, params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise RuntimeError(f"Brave API error {response.status}: {error_text}")
                    
                    result = await response.json()
                    
                    # Parse web search results
                    sources = []
                    web_results = result.get("web", {}).get("results", [])
                    
                    for item in web_results:
                        source = {
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "snippet": item.get("description", ""),
                            "publisher": self._extract_publisher(item.get("url", "")),
                            "published_at": item.get("age"),  # Brave provides relative time
                            "domain": self._extract_domain(item.get("url", "")),
                            "search_query": query,
                            "retrieved_at": datetime.now(timezone.utc).isoformat(),
                        }
                        sources.append(source)
                    
                    return sources
                    
        except Exception as e:
            raise RuntimeError(f"Brave Search API error: {str(e)}")

    def _extract_publisher(self, url: str) -> str:
        """Extract publisher name from URL."""
        try:
            domain = urlparse(url).netloc.lower()
            domain = domain.replace("www.", "")
            
            # Map common domains to friendly names
            domain_map = {
                # News Media
                "cbc.ca": "CBC News",
                "theglobeandmail.com": "The Globe and Mail",
                "globalnews.ca": "Global News",
                "ctvnews.ca": "CTV News",
                "thestar.com": "Toronto Star",
                "nationalpost.com": "National Post",
                "reuters.com": "Reuters",
                "apnews.com": "Associated Press",
                "bbc.com": "BBC",
                "nytimes.com": "The New York Times",
                
                # Government
                "statcan.gc.ca": "Statistics Canada",
                "canada.ca": "Government of Canada",
                "justice.gc.ca": "Department of Justice Canada",
                
                # Academic
                "policyoptions.irpp.org": "Policy Options",
                "fraserinstitute.org": "Fraser Institute",
            }
            
            return domain_map.get(domain, domain.replace(".com", "").replace(".ca", "").title())
        except Exception:
            return "Unknown"

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            return urlparse(url).netloc.lower()
        except Exception:
            return ""


# Initialize the API client
try:
    brave_api = BraveSearchAPI()
except ValueError as e:
    print(f"Warning: {e}")
    brave_api = None


@mcp.tool
async def web_search(
    query: str,
    count: int = 10,
    time_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search the web for information about a topic using Brave Search.
    
    Args:
        query: The search query to find information about
        count: Number of results to return (max 20)
        time_filter: Time filter for results - options: "pd" (past day), "pw" (past week), 
                    "pm" (past month), "py" (past year), or None for all time
    
    Returns:
        Dictionary containing search results with titles, URLs, snippets, and metadata
    """
    if not brave_api:
        return {
            "error": "Brave Search API not configured. Please set BRAVE_SEARCH_API_KEY environment variable.",
            "results": []
        }
    
    try:
        results = await brave_api.search(
            query=query,
            count=min(count, 20),
            time_window=time_filter
        )
        
        return {
            "query": query,
            "count": len(results),
            "results": results,
            "search_timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as e:
        return {
            "error": f"Search failed: {str(e)}",
            "query": query,
            "results": []
        }


@mcp.tool
async def search_multiple_perspectives(
    claim: str,
    perspectives: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Search for multiple perspectives on a claim or topic.
    
    Args:
        claim: The claim or topic to research
        perspectives: List of perspective types to search for. If None, uses default set.
    
    Returns:
        Dictionary containing search results from different perspectives
    """
    if not brave_api:
        return {
            "error": "Brave Search API not configured. Please set BRAVE_SEARCH_API_KEY environment variable.",
            "perspectives": {}
        }
    
    if perspectives is None:
        perspectives = [
            "research study evidence",
            "government official data",
            "news investigative reporting",
            "expert academic analysis",
            "fact check verification"
        ]
    
    results_by_perspective = {}
    
    for perspective in perspectives:
        search_query = f"{perspective} {claim}"
        
        try:
            results = await brave_api.search(
                query=search_query,
                count=5
            )
            
            results_by_perspective[perspective] = {
                "query": search_query,
                "count": len(results),
                "results": results
            }
            
            # Rate limit: 1 request per second for Free plan
            await asyncio.sleep(1.1)  # 1.1 seconds to be safe
            
        except Exception as e:
            results_by_perspective[perspective] = {
                "query": search_query,
                "error": str(e),
                "results": []
            }
    
    return {
        "claim": claim,
        "perspectives": results_by_perspective,
        "search_timestamp": datetime.now(timezone.utc).isoformat(),
    }


@mcp.tool
async def targeted_source_search(
    query: str,
    source_types: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Search for information from specific types of sources.
    
    Args:
        query: The search query
        source_types: List of source types to target. If None, uses default set.
    
    Returns:
        Dictionary containing search results organized by source type
    """
    if not brave_api:
        return {
            "error": "Brave Search API not configured. Please set BRAVE_SEARCH_API_KEY environment variable.",
            "source_results": {}
        }
    
    if source_types is None:
        source_types = [
            "site:statcan.gc.ca",  # Statistics Canada
            "site:canada.ca",      # Government of Canada
            "site:cbc.ca",         # CBC News
            "site:theglobeandmail.com",  # Globe and Mail
            "site:reuters.com",    # Reuters
            "site:apnews.com",     # Associated Press
        ]
    
    source_results = {}
    
    for source_type in source_types:
        search_query = f"{source_type} {query}"
        
        try:
            results = await brave_api.search(
                query=search_query,
                count=5
            )
            
            source_results[source_type] = {
                "query": search_query,
                "count": len(results),
                "results": results
            }
            
            # Rate limit: 1 request per second for Free plan
            await asyncio.sleep(1.1)  # 1.1 seconds to be safe
            
        except Exception as e:
            source_results[source_type] = {
                "query": search_query,
                "error": str(e),
                "results": []
            }
    
    return {
        "original_query": query,
        "source_results": source_results,
        "search_timestamp": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    # Run the server with HTTP transport for Docker
    mcp.run(transport="http", host="0.0.0.0", port=8888)
