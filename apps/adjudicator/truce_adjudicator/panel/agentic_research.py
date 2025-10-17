"""Agentic research system for panel agents using FastMCP Brave Search server."""

import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple
from uuid import UUID, uuid4

from fastmcp import Client
from dotenv import load_dotenv

from ..models import Claim, Evidence, TimeWindow

load_dotenv()


class AgenticResearcher:
    """Agentic researcher that uses FastMCP Brave Search server to conduct independent research."""

    def __init__(
        self,
        agent_name: str,
        mcp_server_url: Optional[str] = None,
        max_search_turns: int = 5,
        max_sources_per_turn: int = 8,
    ):
        """
        Initialize an agentic researcher.

        Args:
            agent_name: Name/identifier for this research agent
            mcp_server_url: URL of the FastMCP Brave Search server
            max_search_turns: Maximum number of research turns
            max_sources_per_turn: Maximum sources to collect per turn
        """
        self.agent_name = agent_name
        self.mcp_server_url = mcp_server_url or "http://localhost:8888/mcp"
        self.max_search_turns = max_search_turns
        self.max_sources_per_turn = max_sources_per_turn
        self.research_log: List[Dict[str, Any]] = []
        self.collected_sources: List[Dict[str, Any]] = []

    async def conduct_research(
        self,
        claim: Claim,
        time_window: Optional[TimeWindow] = None,
        session_id: Optional[str] = None,
    ) -> List[Evidence]:
        """
        Conduct multi-turn agentic research on a claim.

        Args:
            claim: The claim to research
            time_window: Optional time window filter
            session_id: Optional session ID for progress updates

        Returns:
            List of Evidence objects collected during research
        """
        try:
            # Create client with explicit URL
            print(f"Connecting to MCP server at: {self.mcp_server_url}")
            client = Client(self.mcp_server_url)

            async with client:
                # Note: FastMCP HTTP transport doesn't require explicit ping
                # Connection will be verified when first tool is called
                print(f"MCP client initialized for {self.agent_name}")

                # Start research process
                if session_id:
                    await self._emit_progress(
                        session_id,
                        f"Starting agentic research for {self.agent_name}",
                        f"Beginning independent research on: {claim.text}",
                    )

                # Initial research plan
                research_plan = await self._plan_research(claim, client)

                # Execute research turns
                for turn in range(self.max_search_turns):
                    if session_id:
                        await self._emit_progress(
                            session_id,
                            f"{self.agent_name} - Research Turn {turn + 1}",
                            f"Executing search strategy: {research_plan.get('current_strategy', 'exploratory')}",
                        )

                    # Execute current research turn
                    turn_sources = await self._execute_research_turn(
                        claim, client, turn, research_plan, time_window
                    )

                    # Analyze findings and update research plan
                    analysis = await self._analyze_turn_results(turn_sources, claim)
                    research_plan = await self._update_research_plan(
                        research_plan, analysis
                    )

                    # Check if research is sufficient
                    if (
                        analysis.get("sufficient_evidence", False)
                        and len(self.collected_sources) >= 5
                    ):
                        if session_id:
                            await self._emit_progress(
                                session_id,
                                f"{self.agent_name} - Research Complete",
                                f"Sufficient evidence collected after {turn + 1} turns",
                            )
                        break

                # Convert to Evidence objects
                evidence_list = await self._convert_to_evidence(claim)

                if session_id:
                    await self._emit_progress(
                        session_id,
                        f"{self.agent_name} - Research Summary",
                        f"Collected {len(evidence_list)} evidence items from {len(self.research_log)} research actions",
                    )

                return evidence_list

        except Exception as e:
            print(f"Research error for {self.agent_name}: {e}")
            if session_id:
                await self._emit_progress(
                    session_id,
                    f"{self.agent_name} - Research Error",
                    f"Research failed: {str(e)}",
                )
            return []

    async def _plan_research(self, claim: Claim, client: Client) -> Dict[str, Any]:
        """Create initial research plan based on the claim."""
        return {
            "original_claim": claim.text,
            "current_strategy": "broad_search",
            "search_queries_used": [],
            "perspectives_explored": [],
            "gaps_identified": [],
            "next_actions": [
                "broad_search",
                "perspective_search",
                "targeted_verification",
            ],
        }

    async def _execute_research_turn(
        self,
        claim: Claim,
        client: Client,
        turn: int,
        research_plan: Dict[str, Any],
        time_window: Optional[TimeWindow],
    ) -> List[Dict[str, Any]]:
        """Execute one turn of research."""
        turn_sources = []

        try:
            if turn == 0:
                # First turn: Broad search
                result = await client.call_tool(
                    "web_search",
                    {
                        "query": claim.text,
                        "count": self.max_sources_per_turn,
                        "time_filter": self._get_time_filter(time_window),
                    },
                )

                # Access result.data for structured output (FastMCP pattern)
                if result and result.data:
                    data = result.data if isinstance(result.data, dict) else {}
                    results = data.get("results", [])
                    turn_sources.extend(results)
                    self.research_log.append(
                        {
                            "turn": turn,
                            "action": "broad_search",
                            "query": claim.text,
                            "results_count": len(results),
                        }
                    )

            elif turn == 1:
                # Second turn: Multiple perspectives
                result = await client.call_tool(
                    "search_multiple_perspectives",
                    {
                        "claim": claim.text,
                        "perspectives": [
                            "research study evidence",
                            "government official data",
                            "fact check verification",
                            "expert academic analysis",
                        ],
                    },
                )

                # Access result.data for structured output
                if result and result.data:
                    data = result.data if isinstance(result.data, dict) else {}
                    perspectives = data.get("perspectives", {})
                    for perspective, perspective_data in perspectives.items():
                        turn_sources.extend(perspective_data.get("results", []))

                    self.research_log.append(
                        {
                            "turn": turn,
                            "action": "perspective_search",
                            "perspectives": list(perspectives.keys()),
                            "total_results": len(turn_sources),
                        }
                    )

            elif turn == 2:
                # Third turn: Targeted source search
                result = await client.call_tool(
                    "targeted_source_search",
                    {
                        "query": claim.text,
                        "source_types": [
                            "site:statcan.gc.ca",
                            "site:canada.ca",
                            "site:cbc.ca",
                            "site:reuters.com",
                        ],
                    },
                )

                # Access result.data for structured output
                if result and result.data:
                    data = result.data if isinstance(result.data, dict) else {}
                    source_results = data.get("source_results", {})
                    for source_type, source_data in source_results.items():
                        turn_sources.extend(source_data.get("results", []))

                    self.research_log.append(
                        {
                            "turn": turn,
                            "action": "targeted_source_search",
                            "source_types": list(source_results.keys()),
                            "total_results": len(turn_sources),
                        }
                    )

            else:
                # Later turns: Focus on gaps or specific aspects
                gap_query = await self._identify_research_gap(claim, research_plan)

                result = await client.call_tool(
                    "web_search",
                    {
                        "query": gap_query,
                        "count": max(3, self.max_sources_per_turn // 2),
                        "time_filter": self._get_time_filter(time_window),
                    },
                )

                # Access result.data for structured output
                if result and result.data:
                    data = result.data if isinstance(result.data, dict) else {}
                    results = data.get("results", [])
                    turn_sources.extend(results)
                    self.research_log.append(
                        {
                            "turn": turn,
                            "action": "gap_search",
                            "query": gap_query,
                            "results_count": len(results),
                        }
                    )

            # Store sources from this turn
            for source in turn_sources:
                source["research_turn"] = turn
                source["agent"] = self.agent_name

            self.collected_sources.extend(turn_sources)

        except Exception as e:
            print(f"Research turn {turn} failed for {self.agent_name}: {e}")
            self.research_log.append(
                {
                    "turn": turn,
                    "action": "error",
                    "error": str(e),
                }
            )

        return turn_sources

    async def _analyze_turn_results(
        self, turn_sources: List[Dict[str, Any]], claim: Claim
    ) -> Dict[str, Any]:
        """Analyze results from a research turn to guide next actions."""
        # Simple heuristic analysis for now
        total_sources = len(self.collected_sources)
        unique_domains = len(set(s.get("domain", "") for s in self.collected_sources))

        analysis = {
            "total_sources_collected": total_sources,
            "unique_domains": unique_domains,
            "turn_sources": len(turn_sources),
            "sufficient_evidence": total_sources >= 8 and unique_domains >= 4,
            "needs_more_perspectives": unique_domains < 3,
            "needs_official_sources": not any(
                "gov" in s.get("domain", "") or "statcan" in s.get("domain", "")
                for s in self.collected_sources
            ),
        }

        return analysis

    async def _update_research_plan(
        self, current_plan: Dict[str, Any], analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update research plan based on analysis."""
        next_actions = []

        if analysis.get("needs_official_sources"):
            next_actions.append("government_sources")
        if analysis.get("needs_more_perspectives"):
            next_actions.append("alternative_perspectives")
        if not analysis.get("sufficient_evidence"):
            next_actions.append("detailed_search")

        current_plan["analysis"] = analysis
        current_plan["next_actions"] = next_actions

        return current_plan

    async def _identify_research_gap(
        self, claim: Claim, research_plan: Dict[str, Any]
    ) -> str:
        """Identify what aspect needs more research."""
        gaps = research_plan.get("next_actions", [])

        if "government_sources" in gaps:
            return f"government statistics data {claim.text}"
        elif "alternative_perspectives" in gaps:
            return f"counterargument opposing view {claim.text}"
        else:
            return f"detailed analysis verification {claim.text}"

    async def _convert_to_evidence(self, claim: Claim) -> List[Evidence]:
        """Convert collected sources to Evidence objects."""
        evidence_list = []

        for source in self.collected_sources:
            try:
                published_at = None
                if source.get("published_at"):
                    # Try to parse published_at if it's a string
                    if isinstance(source["published_at"], str):
                        try:
                            published_at = datetime.fromisoformat(
                                source["published_at"].replace("Z", "+00:00")
                            )
                        except:
                            published_at = None
                    else:
                        published_at = source["published_at"]

                evidence = Evidence(
                    id=uuid4(),
                    url=source.get("url", ""),
                    publisher=source.get("publisher", "Unknown"),
                    published_at=published_at,
                    retrieved_at=datetime.fromisoformat(
                        source.get("retrieved_at", datetime.now().isoformat())
                    ),
                    title=source.get("title", ""),
                    domain=source.get("domain", ""),
                    snippet=source.get("snippet", ""),
                    provenance=f"{self.agent_name}_research",
                    normalized_url=source.get("url", ""),  # Could be normalized
                    content_hash="",  # Could compute hash
                )

                evidence_list.append(evidence)

            except Exception as e:
                print(f"Failed to convert source to evidence: {e}")
                continue

        return evidence_list

    def _get_time_filter(self, time_window: Optional[TimeWindow]) -> Optional[str]:
        """Convert TimeWindow to Brave API time filter."""
        if not time_window or not time_window.start:
            return None

        days_ago = (datetime.now() - time_window.start.replace(tzinfo=None)).days

        if days_ago <= 1:
            return "pd"  # past day
        elif days_ago <= 7:
            return "pw"  # past week
        elif days_ago <= 30:
            return "pm"  # past month
        elif days_ago <= 365:
            return "py"  # past year
        else:
            return None  # all time

    async def _emit_progress(self, session_id: str, title: str, message: str):
        """Emit progress update (placeholder for now)."""
        try:
            from ..main import emit_agent_update

            await emit_agent_update(
                session_id=session_id,
                agent_name=self.agent_name,
                action=title,
                reasoning=message,
                search_strategy="agentic_research",
                sources_found=[],
            )
        except ImportError:
            # Fallback if emit_agent_update is not available
            print(f"{self.agent_name}: {title} - {message}")


class SharedEvidencePool:
    """Shared pool of evidence collected by all agentic researchers."""

    def __init__(self):
        self.evidence_pool: List[Evidence] = []
        self.source_hashes: set[str] = set()

    async def add_evidence(self, evidence_list: List[Evidence], agent_name: str) -> int:
        """Add evidence from an agent to the shared pool, deduplicating by URL."""
        added_count = 0

        for evidence in evidence_list:
            # Simple deduplication by URL
            url_hash = hash(evidence.url)

            if url_hash not in self.source_hashes:
                self.source_hashes.add(url_hash)

                # Update provenance to show it came from agent research
                evidence.provenance = f"agentic_research_{agent_name}"
                self.evidence_pool.append(evidence)
                added_count += 1

        return added_count

    def get_all_evidence(self) -> List[Evidence]:
        """Get all evidence from the shared pool."""
        return self.evidence_pool.copy()

    def get_evidence_summary(self) -> Dict[str, Any]:
        """Get summary statistics about collected evidence."""
        domains = set(e.domain for e in self.evidence_pool)
        publishers = set(e.publisher for e in self.evidence_pool)

        return {
            "total_evidence": len(self.evidence_pool),
            "unique_domains": len(domains),
            "unique_publishers": len(publishers),
            "domains": list(domains),
            "publishers": list(publishers),
        }
