"""Tests for verification caching and time-window behaviour."""

from datetime import datetime, timedelta
from typing import Tuple

import pytest
from fastapi.testclient import TestClient

from truce_adjudicator import search_index
from truce_adjudicator.main import app, claims_db, generate_slug
from truce_adjudicator.models import Claim, Evidence, ModelAssessment, VerdictType
from truce_adjudicator.verification import reset_cache

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    """Ensure in-memory stores and caches are reset between tests."""
    claims_db.clear()
    search_index.reset()
    reset_cache()
    yield
    claims_db.clear()
    search_index.reset()
    reset_cache()


@pytest.fixture
def seeded_claim() -> Tuple[str, Evidence, Evidence]:
    """Create a claim with two evidence items for testing."""
    slug = generate_slug("Cache Verification Test Claim")
    claim = Claim(
        text="Cache verification test claim",
        topic="testing",
        entities=[],
    )

    now = datetime.utcnow()
    recent_evidence = Evidence(
        url="https://example.com/recent",
        publisher="Example Publisher",
        published_at=now - timedelta(days=1),
        snippet="Recent evidence supporting the claim.",
        provenance="unit-test",
    )
    older_evidence = Evidence(
        url="https://example.com/older",
        publisher="Example Publisher",
        published_at=now - timedelta(days=365 * 5),
        snippet="Older evidence that should be filtered out.",
        provenance="unit-test",
    )

    claim.evidence.extend([recent_evidence, older_evidence])
    claim.model_assessments.append(
        ModelAssessment(
            model_name="gpt-5",
            verdict=VerdictType.SUPPORTS,
            confidence=0.8,
            citations=[recent_evidence.id],
            rationale="Model assessment supporting the claim with sufficient rationale text to pass validation.",
        )
    )

    claims_db[slug] = claim
    search_index.index_claim(slug, claim.text)
    search_index.index_evidence_batch(
        slug,
        [
            {
                "evidence_id": str(recent_evidence.id),
                "snippet": recent_evidence.snippet,
                "publisher": recent_evidence.publisher,
                "url": recent_evidence.url,
            },
            {
                "evidence_id": str(older_evidence.id),
                "snippet": older_evidence.snippet,
                "publisher": older_evidence.publisher,
                "url": older_evidence.url,
            },
        ],
    )

    return slug, recent_evidence, older_evidence


def test_cache_hit_after_initial_verification(seeded_claim):
    slug, _, _ = seeded_claim

    first = client.post(f"/claims/{slug}/verify")
    assert first.status_code == 200
    first_payload = first.json()
    assert first_payload["cached"] is False

    second = client.post(f"/claims/{slug}/verify")
    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["cached"] is True
    assert second_payload["verification_id"] == first_payload["verification_id"]


def test_force_refresh_produces_new_verification(seeded_claim):
    slug, _, _ = seeded_claim

    baseline = client.post(f"/claims/{slug}/verify")
    baseline_payload = baseline.json()

    refreshed = client.post(f"/claims/{slug}/verify", params={"force": "true"})
    refreshed_payload = refreshed.json()

    assert refreshed_payload["cached"] is False
    assert refreshed_payload["verification_id"] != baseline_payload["verification_id"]


def test_time_window_filters_evidence(seeded_claim):
    slug, recent_evidence, older_evidence = seeded_claim

    start = (recent_evidence.published_at - timedelta(days=2)).isoformat()
    end = (recent_evidence.published_at + timedelta(days=1)).isoformat()

    response = client.post(
        f"/claims/{slug}/verify",
        params={"time_start": start, "time_end": end},
    )
    assert response.status_code == 200
    payload = response.json()

    evidence_ids = {uuid for uuid in payload["evidence_ids"]}
    assert str(recent_evidence.id) in evidence_ids
    assert str(older_evidence.id) not in evidence_ids


def test_fresh_evidence_discovery_after_cached_verification(seeded_claim, monkeypatch):
    """Test that the system discovers fresh evidence even after a cached verification exists."""
    from datetime import datetime
    from unittest.mock import AsyncMock

    from truce_adjudicator.main import explorer_agent
    from truce_adjudicator.mcp.explorer import ExplorerSource

    slug, _, _ = seeded_claim

    # First verification to establish a cached result
    first_response = client.post(f"/claims/{slug}/verify")
    assert first_response.status_code == 200
    first_payload = first_response.json()
    assert first_payload["cached"] is False
    initial_evidence_count = len(first_payload["evidence_ids"])

    # Second verification should return cached result but still attempt to gather new sources
    second_response = client.post(f"/claims/{slug}/verify")
    assert second_response.status_code == 200
    second_payload = second_response.json()
    assert second_payload["cached"] is True
    assert second_payload["verification_id"] == first_payload["verification_id"]

    # Mock explorer agent to return new evidence
    now = datetime.utcnow()
    new_explorer_source = ExplorerSource(
        title="Fresh discovery",
        url="https://fresh.com/new-article",
        snippet="Newly discovered evidence",
        publisher="Fresh News",
        domain="fresh.com",
        published_at=now,
        retrieved_at=now,
        normalized_url="https://fresh.com/new-article",
        content_hash="fresh-hash-123",
    )

    monkeypatch.setattr(
        explorer_agent, "gather_sources", AsyncMock(return_value=[new_explorer_source])
    )

    # Third verification should discover new evidence and create a new verification record
    third_response = client.post(f"/claims/{slug}/verify")
    assert third_response.status_code == 200
    third_payload = third_response.json()

    # Should not be cached since evidence set changed
    assert third_payload["cached"] is False
    assert third_payload["verification_id"] != first_payload["verification_id"]

    # Should have more evidence than before
    new_evidence_count = len(third_payload["evidence_ids"])
    assert new_evidence_count > initial_evidence_count

    # Verify the claim object was updated with new evidence
    claim = claims_db[slug]
    found_fresh_evidence = any(
        evidence.url == "https://fresh.com/new-article" for evidence in claim.evidence
    )
    assert found_fresh_evidence
