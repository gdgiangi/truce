"""Tests for the explorer MCP agent and integration into verification."""

from datetime import datetime, timedelta
from typing import List
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from truce_adjudicator.main import app, claims_db, explorer_agent
from truce_adjudicator import search_index
from truce_adjudicator.models import Claim, TimeWindow
from truce_adjudicator.mcp.explorer import ExplorerAgent, ExplorerSource, ExplorerToolset
from truce_adjudicator.verification import reset_cache

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    """Reset global state between tests."""
    claims_db.clear()
    search_index.reset()
    reset_cache()
    yield
    claims_db.clear()
    search_index.reset()
    reset_cache()


@pytest.mark.asyncio
async def test_explorer_agent_invokes_toolchain(monkeypatch):
    """Ensure explorer agent calls the full MCP toolchain."""
    toolset = ExplorerToolset()
    mock_result = {
        "title": "Example article",
        "url": "https://example.com/news/1",
        "snippet": "Base snippet",
        "publisher": "Example",
        "published_at": datetime(2024, 6, 1),
    }
    toolset.search_web = AsyncMock(return_value=[mock_result])
    toolset.fetch_page = AsyncMock(return_value={
        "snippet": "Fetched snippet",
        "publisher": "Example",
        "title": "Example article",
        "published_at": datetime(2024, 6, 1),
    })
    toolset.expand_links = AsyncMock(return_value=[])
    toolset.deduplicate_sources = AsyncMock(
        return_value=[
            {
                "title": "Example article",
                "url": "https://example.com/news/1",
                "snippet": "Fetched snippet",
                "publisher": "Example",
                "published_at": datetime(2024, 6, 1),
                "domain": "example.com",
                "normalized_url": "https://example.com/news/1",
                "retrieved_at": datetime.utcnow(),
                "content_hash": "hash",
            }
        ]
    )

    agent = ExplorerAgent(tools=toolset, target_count=1)
    sources = await agent.gather_sources("test claim", TimeWindow())

    assert len(sources) == 1
    toolset.search_web.assert_awaited()
    toolset.fetch_page.assert_awaited()
    toolset.expand_links.assert_awaited()
    toolset.deduplicate_sources.assert_awaited()


def test_domain_diversity_enforced():
    """Domain share heuristic caps contributions from a single domain."""
    agent = ExplorerAgent(target_count=6, domain_share=0.4)

    now = datetime.utcnow()
    sources: List[ExplorerSource] = []
    for idx in range(6):
        sources.append(
            ExplorerSource(
                title=f"Same domain {idx}",
                url=f"https://same.com/article-{idx}",
                snippet="Snippet",
                publisher="Same",
                domain="same.com",
                published_at=now,
                retrieved_at=now,
                normalized_url=f"https://same.com/article-{idx}",
                content_hash=f"hash-{idx}",
            )
        )
    for idx in range(3):
        sources.append(
            ExplorerSource(
                title=f"Other domain {idx}",
                url=f"https://other{idx}.com/article",
                snippet="Snippet",
                publisher="Other",
                domain=f"other{idx}.com",
                published_at=now,
                retrieved_at=now,
                normalized_url=f"https://other{idx}.com/article",
                content_hash=f"other-hash-{idx}",
            )
        )

    diversified = agent._enforce_domain_diversity(sources, target_count=6)

    domain_counts = {}
    for source in diversified:
        domain_counts[source.domain] = domain_counts.get(source.domain, 0) + 1

    assert diversified  # should keep some results
    assert all(count <= 2 for count in domain_counts.values())


def test_verify_persists_explorer_evidence(monkeypatch):
    """Explorer sources become Evidence records during verification."""
    slug = "agentic-claim"
    claim = Claim(text="Agentic flow", topic="testing", entities=[])
    claims_db[slug] = claim
    search_index.index_claim(slug, claim.text)

    now = datetime.utcnow()
    explorer_sources = [
        ExplorerSource(
            title="Unique source",
            url="https://unique.com/article",
            snippet="Fresh insight",
            publisher="Unique",
            domain="unique.com",
            published_at=now,
            retrieved_at=now,
            normalized_url="https://unique.com/article",
            content_hash="hash-unique",
        ),
        ExplorerSource(
            title="Duplicate URL",
            url="https://unique.com/article",
            snippet="Fresh insight",
            publisher="Unique",
            domain="unique.com",
            published_at=now,
            retrieved_at=now,
            normalized_url="https://unique.com/article",
            content_hash="hash-unique",
        ),
    ]

    monkeypatch.setattr(
        explorer_agent,
        "gather_sources",
        AsyncMock(return_value=explorer_sources),
    )

    response = client.post(f"/claims/{slug}/verify")
    assert response.status_code == 200

    # Only one unique evidence should persist
    assert len(claim.evidence) == 1
    evidence = claim.evidence[0]
    assert evidence.domain == "unique.com"
    assert evidence.title == "Unique source"
    assert evidence.provenance == "mcp-explorer"
